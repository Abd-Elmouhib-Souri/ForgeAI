"""
Post-analysis pipeline contracts (Plan Sprint 4 -> Architecture Sprint 5).

Observed product REDs these contracts close (project 31, 23 Sept 2026):

  R1  Analysis reached 100 % but Plan / Architecture stayed empty until the
      user clicked each button (Sprint 4 generated after the "completed"
      commit; Sprint 5 never generated automatically).
  R2  groq/compound-mini decommissioned (HTTP 404 model_not_found) + Gemini
      quota exhausted (429) surfaced as one generic "service indisponible";
      the real cause was invisible.
  R3  Three immediate Solution Architect retries against open circuits.
  R4  No automatic recovery once quotas refill; retry tasks lost on restart.

Every contract is universal: no project, sector, country or model name
drives behaviour (model ids below are opaque fixtures).
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.llm.provider import LLMModelConfig, LLMProvider, LLMUnavailableError
from app.services import llm_failure_classifier as clf
from app.services import post_analysis_pipeline as pl
from app.services import solution_architecture_plan_service as sa_service


# =============================================================================
# Fakes: in-memory session factory (no database, no network, no LLM)
# =============================================================================

class FakeStore:
    def __init__(self, *projects):
        self.projects = {p.id: p for p in projects}
        self.commits = 0


class FakeSession:
    def __init__(self, store: FakeStore):
        self.store = store

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, _model, project_id):
        return self.store.projects.get(project_id)

    async def commit(self):
        self.store.commits += 1

    async def execute(self, _statement):
        # resume_pending() query: completed projects with a pipeline key.
        rows = [
            (p.id, p.analysis_run_id, p.analysis_data)
            for p in self.store.projects.values()
            if p.analysis_status == "completed"
            and isinstance(p.analysis_data, dict)
            and p.analysis_data.get(pl.PIPELINE_KEY) is not None
        ]
        return SimpleNamespace(all=lambda: rows)


def make_project(project_id=1, run_id="run-1", pipeline=True):
    data = {"summary": "neutral"}
    if pipeline:
        data[pl.PIPELINE_KEY] = pl.initial_pipeline_state(run_id)
    return SimpleNamespace(
        id=project_id,
        analysis_status="completed",
        analysis_run_id=run_id,
        analysis_data=data,
    )


class Recorder:
    """Scripted generator: each call pops the next outcome."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def __call__(self, project_id, analysis_data):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def make_pipeline(store, pm, sa, delays):
    async def fake_sleep(seconds):
        # Record the scheduled delay, never actually wait or re-run.
        delays.append(seconds)
        raise asyncio.CancelledError

    return pl.PostAnalysisPipeline(
        session_factory=lambda: FakeSession(store),
        pm_generator=pm,
        sa_generator=sa,
        sleep=fake_sleep,
    )


async def drain():
    # Let scheduled tasks reach fake_sleep and finish.
    for _ in range(5):
        await asyncio.sleep(0)


def quota_error():
    # Exact shape of the 23 Sept incident: one model decommissioned,
    # the other out of quota.
    return LLMUnavailableError(
        "all failed",
        {"groq:model-a": "configuration", "gemini:model-b": "temporary"},
    )


def stages(project):
    return project.analysis_data[pl.PIPELINE_KEY]["stages"]


PM_OK = ({"current": "pm-artifact"}, False)
PM_DEGRADED = ({"current": "pm-fallback"}, True)
SA_OK = {"canonical": "sa-artifact"}


# =============================================================================
# C1 — failure classification (R2)
# =============================================================================

def test_c1_quota_plus_decommissioned_model_is_retryable_and_names_the_model():
    info = clf.classify(quota_error())
    assert info.code == clf.LLM_QUOTA_OR_UNAVAILABLE
    assert info.retryable is True
    assert info.misconfigured_models == ("groq:model-a",)


def test_c1_every_model_misconfigured_is_not_retryable():
    info = clf.classify(LLMUnavailableError("x", {"a:m": "configuration", "b:n": "circuit_open:configuration"}))
    assert info.code == clf.LLM_CONFIGURATION_ERROR
    assert info.retryable is False


def test_c1_open_circuits_keep_their_original_cause():
    info = clf.classify(LLMUnavailableError("x", {"a:m": "circuit_open:configuration", "b:n": "circuit_open:temporary"}))
    assert info.code == clf.LLM_QUOTA_OR_UNAVAILABLE
    assert info.misconfigured_models == ("a:m",)


def test_c1_provider_error_is_found_through_the_exception_chain():
    try:
        try:
            raise quota_error()
        except LLMUnavailableError as inner:
            raise sa_service.SolutionArchitecturePlanError("generation_retryable", "wrapped") from inner
    except sa_service.SolutionArchitecturePlanError as outer:
        assert clf.classify(outer).code == clf.LLM_QUOTA_OR_UNAVAILABLE
        assert clf.is_provider_unavailable(outer) is True


def test_c1_context_and_content_errors_are_distinct():
    ctx = sa_service.SolutionArchitecturePlanError("project_context_missing", "missing")
    bad = sa_service.SolutionArchitecturePlanError("generation_retryable", "does not satisfy schema")
    assert clf.classify(ctx).code == clf.CONTEXT_INVALID and not clf.classify(ctx).retryable
    assert clf.classify(bad).code == clf.INVALID_MODEL_OUTPUT and clf.classify(bad).retryable
    assert clf.is_provider_unavailable(bad) is False


# =============================================================================
# C2 — provider reports per-model failure kinds (R2)
# =============================================================================

@pytest.mark.asyncio
async def test_c2_invoke_raises_typed_error_with_each_model_kind(monkeypatch):
    configs = [
        LLMModelConfig("groq", "model-a", 600, "k", 1),
        LLMModelConfig("gemini", "model-b", 600, "k", 2),
    ]
    provider = object.__new__(LLMProvider)
    provider.model_configs = configs
    LLMProvider._shared_health.clear()

    class _Failing:
        def __init__(self, message):
            self.message = message

        async def ainvoke(self, prompt):
            raise RuntimeError(self.message)

    async def fake_model(config, *, structured=False):
        return _Failing("Error code: 404 - model_not_found" if config.provider == "groq" else "429 quota exceeded")

    monkeypatch.setattr(provider, "_get_or_create_model", fake_model)
    with pytest.raises(LLMUnavailableError) as caught:
        await provider.invoke("prompt", "test")
    assert caught.value.failures == {"groq:model-a": "configuration", "gemini:model-b": "temporary"}
    assert isinstance(caught.value, RuntimeError)  # backward compatible

    # Second call: groq circuit is open; its cause stays visible.
    with pytest.raises(LLMUnavailableError) as again:
        await provider.invoke("prompt", "test")
    assert again.value.failures["groq:model-a"] == "circuit_open:configuration"
    LLMProvider._shared_health.clear()


# =============================================================================
# C3 — Solution Architect stops immediate retries when no model answers (R3)
# =============================================================================

@pytest.mark.asyncio
async def test_c3_provider_unavailability_is_not_retried_immediately(monkeypatch):
    calls = []

    async def fail_provider(*, project_id, context):
        calls.append(1)
        raise sa_service.SolutionArchitecturePlanError("generation_retryable", "x") from quota_error()

    monkeypatch.setattr(sa_service, "_build_packet", lambda data: object())
    monkeypatch.setattr(sa_service.solution_architecture_context_builder, "build", lambda packet: object())
    monkeypatch.setattr(sa_service, "_generate_once", fail_provider)

    with pytest.raises(sa_service.SolutionArchitecturePlanError) as caught:
        await sa_service.generate(project_id=1, analysis_data={})
    assert len(calls) == 1
    # Real cause stays reachable for the pipeline and the API.
    assert clf.classify(caught.value).code == clf.LLM_QUOTA_OR_UNAVAILABLE


@pytest.mark.asyncio
async def test_c3_content_errors_keep_their_bounded_retries(monkeypatch):
    calls = []

    async def fail_content(*, project_id, context):
        calls.append(1)
        raise sa_service.SolutionArchitecturePlanError("generation_retryable", "invalid JSON shape")

    monkeypatch.setattr(sa_service, "_build_packet", lambda data: object())
    monkeypatch.setattr(sa_service.solution_architecture_context_builder, "build", lambda packet: object())
    monkeypatch.setattr(sa_service, "_generate_once", fail_content)

    with pytest.raises(sa_service.SolutionArchitecturePlanError):
        await sa_service.generate(project_id=1, analysis_data={})
    assert len(calls) == sa_service.MAX_GENERATION_ATTEMPTS


# =============================================================================
# C4 — automatic pipeline (R1, R4)
# =============================================================================

@pytest.mark.asyncio
async def test_c4_happy_path_runs_plan_then_architecture_automatically():
    project = make_project()
    store, delays = FakeStore(project), []
    order = []

    async def pm(pid, data):
        order.append("pm")
        return PM_OK

    async def sa(pid, data):
        order.append("sa")
        return SA_OK

    await make_pipeline(store, pm, sa, delays).run(1, "run-1")

    assert order == ["pm", "sa"]
    assert stages(project)["project_manager"]["status"] == pl.COMPLETED
    assert stages(project)["solution_architecture"]["status"] == pl.COMPLETED
    assert project.analysis_data["project_manager"] == PM_OK[0]
    assert project.analysis_data["solution_architecture"] == SA_OK
    assert delays == []


@pytest.mark.asyncio
async def test_c4_quota_failure_waits_with_backoff_instead_of_failing():
    project = make_project()
    store, delays = FakeStore(project), []
    sa = Recorder(sa_service.SolutionArchitecturePlanError("generation_temporarily_unavailable", "x"))
    sa.outcomes[0].__cause__ = quota_error()
    pipeline = make_pipeline(store, Recorder(PM_OK), sa, delays)

    await pipeline.run(1, "run-1")
    await drain()

    state = stages(project)["solution_architecture"]
    assert state["status"] == pl.WAITING_RETRY
    assert state["error_code"] == clf.LLM_QUOTA_OR_UNAVAILABLE
    assert state["misconfigured_models"] == ["groq:model-a"]
    assert state["next_retry_at"] is not None
    assert delays and 55 <= delays[-1] <= pl.RETRY_DELAYS_SECONDS[0]


@pytest.mark.asyncio
async def test_c4_retry_after_quota_refill_completes_the_stage(monkeypatch):
    project = make_project()
    store, delays = FakeStore(project), []
    sa = Recorder(quota_error(), SA_OK)
    pipeline = make_pipeline(store, Recorder(PM_OK), sa, delays)
    await pipeline.run(1, "run-1")
    await drain()

    # Time passes beyond next_retry_at: the scheduled wake-up re-runs.
    later = pl.utc_now() + timedelta(seconds=pl.RETRY_DELAYS_SECONDS[0] + 1)
    monkeypatch.setattr(pl, "utc_now", lambda: later)
    await pipeline.run(1, "run-1")

    assert sa.calls == 2
    assert stages(project)["solution_architecture"]["status"] == pl.COMPLETED
    assert stages(project)["solution_architecture"]["attempts"] == 2


@pytest.mark.asyncio
async def test_c4_not_due_retry_is_not_run_early():
    project = make_project()
    store, delays = FakeStore(project), []
    sa = Recorder(quota_error(), SA_OK)
    pipeline = make_pipeline(store, Recorder(PM_OK), sa, delays)
    await pipeline.run(1, "run-1")
    await drain()
    await pipeline.run(1, "run-1")  # immediate wake-up (e.g. restart)
    await drain()
    assert sa.calls == 1  # nothing burned before next_retry_at


@pytest.mark.asyncio
async def test_c4_provider_down_on_plan_does_not_burn_architecture_attempt():
    project = make_project()
    store, delays = FakeStore(project), []
    sa = Recorder(SA_OK)
    await make_pipeline(store, Recorder(quota_error()), sa, delays).run(1, "run-1")
    await drain()
    assert stages(project)["project_manager"]["status"] == pl.WAITING_RETRY
    assert sa.calls == 0
    assert stages(project)["solution_architecture"]["status"] == pl.PENDING


@pytest.mark.asyncio
async def test_c4_fallback_plan_is_degraded_architecture_still_runs_then_upgrade(monkeypatch):
    project = make_project()
    store, delays = FakeStore(project), []
    pm = Recorder(PM_DEGRADED, PM_OK)
    sa = Recorder(SA_OK)
    pipeline = make_pipeline(store, pm, sa, delays)
    await pipeline.run(1, "run-1")
    await drain()

    assert stages(project)["project_manager"]["status"] == pl.DEGRADED
    assert stages(project)["project_manager"]["error_code"] == pl.AI_FALLBACK_USED
    assert project.analysis_data["project_manager"] == PM_DEGRADED[0]  # usable now
    assert stages(project)["solution_architecture"]["status"] == pl.COMPLETED
    assert delays  # upgrade scheduled

    later = pl.utc_now() + timedelta(seconds=pl.RETRY_DELAYS_SECONDS[0] + 1)
    monkeypatch.setattr(pl, "utc_now", lambda: later)
    await pipeline.run(1, "run-1")
    assert stages(project)["project_manager"]["status"] == pl.COMPLETED
    assert project.analysis_data["project_manager"] == PM_OK[0]
    assert sa.calls == 1  # completed architecture never regenerated


@pytest.mark.asyncio
async def test_c4_configuration_failure_stops_and_is_resumed_at_startup():
    project = make_project()
    store, delays = FakeStore(project), []
    config_error = LLMUnavailableError("x", {"a:m": "configuration"})
    pipeline = make_pipeline(store, Recorder(config_error), Recorder(SA_OK), delays)
    await pipeline.run(1, "run-1")
    await drain()
    assert stages(project)["project_manager"]["status"] == pl.FAILED
    assert stages(project)["project_manager"]["error_code"] == clf.LLM_CONFIGURATION_ERROR
    assert delays == []  # waiting cannot fix a broken model id

    # Backend restart after fixing .env: resume re-queues the stage.
    resumed = await pipeline.resume_pending()
    await drain()
    assert resumed == 1
    assert stages(project)["project_manager"]["status"] == pl.PENDING
    assert delays and delays[-1] >= pl.STARTUP_RESUME_DELAY_SECONDS


@pytest.mark.asyncio
async def test_c4_retries_are_bounded():
    project = make_project()
    store, delays = FakeStore(project), []
    pipeline = make_pipeline(
        store, Recorder(PM_OK), Recorder(*[quota_error() for _ in range(pl.MAX_AUTOMATIC_ATTEMPTS)]), delays
    )
    for _ in range(pl.MAX_AUTOMATIC_ATTEMPTS):
        state = stages(project)["solution_architecture"]
        state["next_retry_at"] = None  # force "due" without waiting
        await pipeline.run(1, "run-1")
        await drain()
    state = stages(project)["solution_architecture"]
    assert state["attempts"] == pl.MAX_AUTOMATIC_ATTEMPTS
    assert state["status"] == pl.FAILED


@pytest.mark.asyncio
async def test_c4_newer_analysis_run_invalidates_in_flight_pipeline():
    project = make_project()
    store, delays = FakeStore(project), []

    async def pm(pid, data):
        project.analysis_run_id = "run-2"  # user relaunched the analysis
        return PM_OK

    sa = Recorder(SA_OK)
    await make_pipeline(store, pm, sa, delays).run(1, "run-1")
    assert "project_manager" not in project.analysis_data  # stale result dropped
    assert sa.calls == 0


@pytest.mark.asyncio
async def test_c4_one_run_at_a_time_per_project():
    project = make_project()
    store, delays = FakeStore(project), []
    gate = asyncio.Event()

    async def slow_pm(pid, data):
        await gate.wait()
        return PM_OK

    sa = Recorder(SA_OK)
    pipeline = make_pipeline(store, slow_pm, sa, delays)
    first = asyncio.create_task(pipeline.run(1, "run-1"))
    await drain()
    await pipeline.run(1, "run-1")  # concurrent trigger returns immediately
    gate.set()
    await first
    assert sa.calls == 1


# =============================================================================
# C5 — public state reconciles with artifact truth
# =============================================================================

def test_c5_legacy_project_without_pipeline_is_not_started():
    state = pl.effective_state(project_id=1, analysis_status="completed", analysis_data={"summary": "x"})
    assert state["status"] == pl.NOT_STARTED
    assert {s["status"] for s in state["stages"].values()} == {pl.NOT_STARTED}


def test_c5_fresh_artifact_wins_over_stale_failure(monkeypatch):
    data = {pl.PIPELINE_KEY: pl.initial_pipeline_state("r")}
    data[pl.PIPELINE_KEY]["stages"]["solution_architecture"].update(status=pl.FAILED, error_code="x")
    monkeypatch.setattr(pl, "sa_artifact_status", lambda d: pl.COMPLETED)
    monkeypatch.setattr(pl, "pm_artifact_status", lambda pid, d: pl.COMPLETED)
    state = pl.effective_state(project_id=1, analysis_status="completed", analysis_data=data)
    assert state["stages"]["solution_architecture"]["status"] == pl.COMPLETED
    assert state["stages"]["solution_architecture"]["error_code"] is None
    assert state["status"] == pl.COMPLETED


def test_c5_running_analysis_never_exposes_a_pipeline_status():
    state = pl.effective_state(project_id=1, analysis_status="running", analysis_data=None)
    assert state["status"] == pl.NOT_STARTED


# =============================================================================
# C6 — analysis completion wiring (R1 race condition)
# =============================================================================

def test_c6_completion_commit_carries_pipeline_state_and_starts_it():
    from app.routers import projects

    source = inspect.getsource(projects.run_project_analysis_background)
    state_pos = source.index("final_analysis_data[PIPELINE_KEY] = initial_pipeline_state(run_id)")
    completed_pos = source.index('project.analysis_status = "completed"')
    start_pos = source.index("post_analysis_pipeline.start(project.id, run_id)")
    commit_pos = source.index("await db.commit()", completed_pos)
    assert state_pos < completed_pos < commit_pos < start_pos
    # The old inline, unreferenced Sprint 4 generation is gone.
    assert "_generate_sprint4_plan_automatically" not in inspect.getsource(projects)
    assert "asyncio.create_task" not in source


def test_c6_solution_architect_error_payload_names_the_real_reason():
    from fastapi import HTTPException

    from app.routers import solution_architect

    error = sa_service.SolutionArchitecturePlanError("generation_temporarily_unavailable", "x")
    error.__cause__ = quota_error()
    with pytest.raises(HTTPException) as caught:
        solution_architect._raise_plan_error(error)
    assert caught.value.status_code == 503
    assert caught.value.detail["reason"] == clf.LLM_QUOTA_OR_UNAVAILABLE
    assert caught.value.detail["misconfigured_models"] == ["groq:model-a"]


# =============================================================================
# C7 — Groq fallback model honours GROQ_API_BASE (found by the HTTP proof)
# =============================================================================

def test_c7_groq_fallback_uses_the_same_endpoint_as_the_primary(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "GROQ_API_KEY", "k")
    monkeypatch.setattr(settings, "GROQ_API_BASE", "http://proxy.invalid")
    monkeypatch.setattr(settings, "GROQ_MODEL", "primary-model")
    monkeypatch.setattr(settings, "GROQ_FALLBACK_MODEL", "fallback-model")
    groq = [c for c in LLMProvider().model_configs if c.provider == "groq"]
    assert [c.model_name for c in groq] == ["primary-model", "fallback-model"]
    assert {c.base_url for c in groq} == {"http://proxy.invalid"}
