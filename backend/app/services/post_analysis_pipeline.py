"""
Post-analysis pipeline: Plan produit (Sprint 4) -> Architecture technique (Sprint 5).

Why this service exists
-----------------------
Before it, once the strategic analysis reached 100 %:

* the Sprint 4 plan was generated inline, *after* the analysis had already
  been committed as "completed", so the frontend loaded /project-manager
  once, got a 404 and never reloaded (race condition);
* the Solution Architecture was never generated automatically;
* a quota failure produced 3 immediate retries against open circuits,
  then a generic "service indisponible" with no automatic recovery;
* retry tasks were fire-and-forget ``asyncio.create_task`` calls with no
  strong reference (the event loop may garbage-collect them) and were lost
  on every backend restart.

What it does
------------
* Persists one explicit state per stage in ``analysis_data["pipeline"]``:
  pending -> running -> completed | degraded | waiting_retry | failed.
* Runs the stages sequentially (limits LLM bursts on free quotas).
* Classifies failures (quota / configuration / invalid output / context)
  with ``llm_failure_classifier`` and schedules delayed retries with a
  growing backoff instead of hammering open circuits.
* Treats a Sprint 4 plan built by the deterministic outage fallback as
  "degraded" and upgrades it automatically once the AI answers again.
* Resumes unfinished work at backend startup.
* Never overrides artifact truth: a fresh plan/architecture that already
  exists (e.g. regenerated manually) is reported as completed.

Doctrine kept: LLM proposes -> policies validate -> deterministic engines
decide. This service only orchestrates existing authorities; it never
changes planning, architecture or policy decisions.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Mapping

from sqlalchemy.future import select

from app.database import AsyncSessionLocal
from app.models import Project
from app.services import solution_architecture_plan_service as sa_service
from app.services.llm_failure_classifier import (
    LLM_CONFIGURATION_ERROR,
    classify,
)
from app.services.project_management_plan_service import (
    project_management_plan_service as pm_service,
)

logger = logging.getLogger(__name__)

PIPELINE_KEY = "pipeline"
PIPELINE_VERSION = 1

STAGE_PROJECT_MANAGER = "project_manager"
STAGE_SOLUTION_ARCHITECTURE = "solution_architecture"
STAGES: tuple[str, ...] = (STAGE_PROJECT_MANAGER, STAGE_SOLUTION_ARCHITECTURE)

# Stage statuses (stable API contract, mirrored by the frontend).
PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
DEGRADED = "degraded"
WAITING_RETRY = "waiting_retry"
FAILED = "failed"
NOT_STARTED = "not_started"

# Growing backoff between automatic attempts. Free quotas refill per
# minute (RPM/TPM) or per day (RPD): short waits first, then longer ones.
# len(RETRY_DELAYS_SECONDS) + 1 == maximum automatic attempts per stage.
RETRY_DELAYS_SECONDS: tuple[int, ...] = (60, 300, 900, 1800, 3600)
MAX_AUTOMATIC_ATTEMPTS = len(RETRY_DELAYS_SECONDS) + 1

# Delay before resuming unfinished stages after a backend (re)start, so the
# app finishes booting and reloader restarts do not stampede providers.
STARTUP_RESUME_DELAY_SECONDS = 15

# Warning emitted by ProjectManagementPlanService when the AI Product Owner
# was unavailable and the conservative deterministic candidate was used.
PM_DETERMINISTIC_FALLBACK_WARNING = "product_owner_ai_unavailable_deterministic_fallback"
# error_code of a DEGRADED stage: usable fallback artifact, AI upgrade pending.
AI_FALLBACK_USED = "ai_fallback_used"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Pure state helpers (no I/O) — unit-tested directly
# ---------------------------------------------------------------------------

def new_stage_state() -> dict[str, Any]:
    return {
        "status": PENDING,
        "attempts": 0,
        "error_code": None,
        "misconfigured_models": [],
        "next_retry_at": None,
        "started_at": None,
        "finished_at": None,
        "updated_at": _iso(utc_now()),
    }


def initial_pipeline_state(run_id: str | None) -> dict[str, Any]:
    """State written in the SAME commit that marks the analysis completed."""
    return {
        "version": PIPELINE_VERSION,
        "run_id": run_id,
        "stages": {stage: new_stage_state() for stage in STAGES},
        "updated_at": _iso(utc_now()),
    }


def _stored_pipeline(analysis_data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(analysis_data, Mapping):
        return None
    pipeline = analysis_data.get(PIPELINE_KEY)
    if not isinstance(pipeline, Mapping) or not isinstance(pipeline.get("stages"), Mapping):
        return None
    # Deep-enough copy: callers mutate stage dicts before persisting.
    return {
        **dict(pipeline),
        "stages": {
            stage: dict(pipeline["stages"].get(stage) or new_stage_state())
            for stage in STAGES
        },
    }


def pm_artifact_status(project_id: int, analysis_data: Mapping[str, Any] | None) -> str | None:
    """COMPLETED / DEGRADED when a fresh Sprint 4 plan exists, else None."""
    if not isinstance(analysis_data, Mapping):
        return None
    try:
        plan = pm_service.deserialize_current(analysis_data.get(STAGE_PROJECT_MANAGER))
        if plan is None or pm_service.is_stale(
            plan=plan, project_id=project_id, analysis_data=analysis_data
        ):
            return None
    except Exception:  # corrupt legacy envelope: treat as absent
        return None
    return DEGRADED if PM_DETERMINISTIC_FALLBACK_WARNING in (plan.warnings or []) else COMPLETED


def sa_artifact_status(analysis_data: Mapping[str, Any] | None) -> str | None:
    """COMPLETED when a fresh canonical architecture exists, else None."""
    if not isinstance(analysis_data, Mapping):
        return None
    try:
        canonical = sa_service.deserialize_current(analysis_data.get(sa_service.ANALYSIS_DATA_KEY))
        if canonical is None or sa_service.is_stale(canonical=canonical, analysis_data=analysis_data):
            return None
    except Exception:
        return None
    return COMPLETED


def artifact_status(stage: str, project_id: int, analysis_data: Mapping[str, Any] | None) -> str | None:
    if stage == STAGE_PROJECT_MANAGER:
        return pm_artifact_status(project_id, analysis_data)
    return sa_artifact_status(analysis_data)


def overall_status(stages: Mapping[str, Mapping[str, Any]]) -> str:
    statuses = [str(stage.get("status")) for stage in stages.values()]
    if all(status == NOT_STARTED for status in statuses):
        return NOT_STARTED
    for status in (RUNNING, PENDING, WAITING_RETRY, FAILED, DEGRADED):
        if status in statuses:
            return status
    return COMPLETED


def effective_state(
    *,
    project_id: int,
    analysis_status: str | None,
    analysis_data: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Public pipeline view = stored state reconciled with artifact truth.

    * Projects analysed before this pipeline existed have no stored state:
      their stages are derived from the artifacts alone ("not_started" when
      nothing exists yet), so the UI can offer to launch the pipeline.
    * A fresh artifact always wins over a stale failure/wait record (e.g.
      the user regenerated the architecture manually).
    """
    stored = _stored_pipeline(analysis_data)
    stages: dict[str, dict[str, Any]] = {}
    for stage in STAGES:
        state = dict(stored["stages"][stage]) if stored else {
            **new_stage_state(),
            "status": NOT_STARTED,
            "updated_at": None,
        }
        truth = artifact_status(stage, project_id, analysis_data)
        if truth and state.get("status") != RUNNING:
            # Keep "degraded" bookkeeping (next upgrade attempt) when the
            # stored state already says degraded; otherwise trust the artifact.
            if not (truth == DEGRADED and state.get("status") == DEGRADED):
                state.update({"status": truth, "error_code": None, "misconfigured_models": []})
                if truth == COMPLETED:
                    state["next_retry_at"] = None
        stages[stage] = state
    return {
        "version": PIPELINE_VERSION,
        "analysis_status": analysis_status,
        "status": overall_status(stages) if analysis_status == "completed" else NOT_STARTED,
        "stages": stages,
        "max_automatic_attempts": MAX_AUTOMATIC_ATTEMPTS,
    }


def retry_delay_seconds(attempts: int) -> int | None:
    """Delay before attempt number ``attempts + 1``; None once exhausted."""
    if attempts < 1 or attempts > len(RETRY_DELAYS_SECONDS):
        return None
    return RETRY_DELAYS_SECONDS[attempts - 1]


# ---------------------------------------------------------------------------
# Default generators (real authorities). Injectable for tests.
# ---------------------------------------------------------------------------

async def generate_project_manager_envelope(
    project_id: int, analysis_data: Mapping[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Returns (new "project_manager" envelope, degraded?)."""
    envelope = analysis_data.get(STAGE_PROJECT_MANAGER)
    previous = pm_service.deserialize_current(envelope if isinstance(envelope, Mapping) else None)
    plan = await pm_service.generate(
        project_id=project_id,
        analysis_data=dict(analysis_data),
        settings=previous.settings if previous else None,
        revision=(previous.revision + 1) if previous else 1,
    )
    new_envelope = pm_service.serialize_with_history(
        current=plan,
        previous_envelope=envelope if isinstance(envelope, Mapping) else None,
    )
    return new_envelope, PM_DETERMINISTIC_FALLBACK_WARNING in (plan.warnings or [])


async def generate_solution_architecture_envelope(
    project_id: int, analysis_data: Mapping[str, Any]
) -> dict[str, Any]:
    canonical = await sa_service.generate(project_id=project_id, analysis_data=dict(analysis_data))
    return sa_service.serialize(canonical)


PMGenerator = Callable[[int, Mapping[str, Any]], Awaitable[tuple[dict[str, Any], bool]]]
SAGenerator = Callable[[int, Mapping[str, Any]], Awaitable[dict[str, Any]]]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PostAnalysisPipeline:
    def __init__(
        self,
        *,
        session_factory=AsyncSessionLocal,
        pm_generator: PMGenerator = generate_project_manager_envelope,
        sa_generator: SAGenerator = generate_solution_architecture_envelope,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._session_factory = session_factory
        self._pm_generator = pm_generator
        self._sa_generator = sa_generator
        self._sleep = sleep
        # One run at a time per project (automatic + manual trigger).
        self._locks: dict[int, asyncio.Lock] = {}
        # Strong references: asyncio only keeps weak refs to tasks, so an
        # unreferenced retry task can be garbage-collected mid-sleep.
        self._scheduled: dict[int, asyncio.Task] = {}
        self._background: set[asyncio.Task] = set()

    # ---------------- scheduling ----------------

    def start(self, project_id: int, run_id: str | None) -> asyncio.Task:
        """Fire the pipeline now (called right after analysis completion)."""
        return self._spawn(self.run(project_id, run_id))

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
        return task

    def schedule(self, project_id: int, run_id: str | None, delay_seconds: float) -> None:
        """(Re)schedule one delayed run per project; a newer one replaces it."""
        previous = self._scheduled.get(project_id)
        current = asyncio.current_task()
        if previous is not None and not previous.done() and previous is not current:
            previous.cancel()

        async def _delayed() -> None:
            try:
                await self._sleep(max(0.0, float(delay_seconds)))
                await self.run(project_id, run_id)
            except asyncio.CancelledError:
                pass
            finally:
                if self._scheduled.get(project_id) is asyncio.current_task():
                    self._scheduled.pop(project_id, None)

        self._scheduled[project_id] = self._spawn(_delayed())

    # ---------------- persistence ----------------

    async def _load(self, db, project_id: int) -> Project | None:
        return await db.get(Project, project_id)

    @staticmethod
    def _is_current(project: Project | None, run_id: str | None) -> bool:
        # A newer analysis run (or a reset) invalidates this pipeline run.
        return (
            project is not None
            and project.analysis_status == "completed"
            and (run_id is None or project.analysis_run_id == run_id)
        )

    async def _write_stage(
        self,
        project_id: int,
        run_id: str | None,
        stage: str,
        updates: Mapping[str, Any],
        artifact: dict[str, Any] | None = None,
    ) -> bool:
        """Re-read, verify run ownership, update one stage (+ artifact), commit."""
        async with self._session_factory() as db:
            project = await self._load(db, project_id)
            if not self._is_current(project, run_id):
                return False
            analysis_data = dict(project.analysis_data or {})
            pipeline = _stored_pipeline(analysis_data) or initial_pipeline_state(run_id)
            state = pipeline["stages"][stage]
            state.update(dict(updates))
            state["updated_at"] = _iso(utc_now())
            pipeline["updated_at"] = state["updated_at"]
            analysis_data[PIPELINE_KEY] = pipeline
            if artifact is not None:
                analysis_data[stage] = artifact
            # Full reassignment: SQLAlchemy JSON columns do not track
            # in-place mutation.
            project.analysis_data = analysis_data
            await db.commit()
            return True

    # ---------------- execution ----------------

    async def run(self, project_id: int, run_id: str | None) -> None:
        lock = self._locks.setdefault(project_id, asyncio.Lock())
        if lock.locked():
            logger.info("[Pipeline] already running | project_id=%s", project_id)
            return
        async with lock:
            try:
                wake_at = await self._run_locked(project_id, run_id)
            except Exception:
                # The orchestrator must never crash the event loop; every
                # expected failure is already persisted per stage.
                logger.exception("[Pipeline] unexpected orchestration error | project_id=%s", project_id)
                return
        # One wake-up per project: the earliest due retry/upgrade. At wake-up
        # every stage is re-evaluated, so later-due stages are re-queued.
        if wake_at is not None:
            self.schedule(project_id, run_id, max(0.0, (wake_at - utc_now()).total_seconds()))

    async def _run_locked(self, project_id: int, run_id: str | None) -> datetime | None:
        wakes: list[datetime] = []
        for stage in STAGES:
            async with self._session_factory() as db:
                project = await self._load(db, project_id)
                if not self._is_current(project, run_id):
                    logger.info("[Pipeline] stale run stopped | project_id=%s", project_id)
                    return None
                analysis_data = dict(project.analysis_data or {})

            stored = _stored_pipeline(analysis_data) or initial_pipeline_state(run_id)
            state = stored["stages"][stage]
            truth = artifact_status(stage, project_id, analysis_data)

            # Artifact truth first: never regenerate what is already fresh.
            if truth == COMPLETED:
                if state.get("status") != COMPLETED:
                    await self._write_stage(project_id, run_id, stage, {
                        "status": COMPLETED, "error_code": None, "misconfigured_models": [],
                        "next_retry_at": None, "finished_at": _iso(utc_now()),
                    })
                continue

            status = state.get("status")
            attempts = int(state.get("attempts") or 0)
            if status == COMPLETED:
                continue  # generated by this run; a new analysis resets it
            if status == FAILED:
                continue  # needs a manual retry (POST /pipeline/run)
            if status == DEGRADED and attempts >= MAX_AUTOMATIC_ATTEMPTS:
                continue  # keep the usable fallback plan
            next_retry = _parse_iso(state.get("next_retry_at"))
            if status in (WAITING_RETRY, DEGRADED) and next_retry and next_retry > utc_now():
                wakes.append(next_retry)  # not due yet: look at the next stage
                continue

            outcome, wake = await self._run_stage(project_id, run_id, stage, analysis_data, attempts)
            if outcome is None:
                return None  # run superseded by a newer analysis
            if wake is not None:
                wakes.append(wake)
            if outcome == WAITING_RETRY:
                # Providers unavailable: the next stage would fail the same
                # way and burn one of its attempts. Stop this round.
                break
        return min(wakes) if wakes else None

    async def _run_stage(
        self,
        project_id: int,
        run_id: str | None,
        stage: str,
        analysis_data: Mapping[str, Any],
        attempts: int,
    ) -> tuple[str | None, datetime | None]:
        attempt = attempts + 1
        if not await self._write_stage(project_id, run_id, stage, {
            "status": RUNNING, "attempts": attempt, "started_at": _iso(utc_now()),
            "next_retry_at": None,
        }):
            return None, None
        logger.info("[Pipeline] stage started | project_id=%s stage=%s attempt=%s", project_id, stage, attempt)

        try:
            if stage == STAGE_PROJECT_MANAGER:
                artifact, degraded = await self._pm_generator(project_id, analysis_data)
            else:
                artifact, degraded = await self._sa_generator(project_id, analysis_data), False
        except Exception as exc:
            return await self._handle_failure(project_id, run_id, stage, attempt, exc)

        if degraded:
            # A usable deterministic plan now; upgrade to the AI plan later.
            delay = retry_delay_seconds(attempt)
            next_retry = utc_now() + timedelta(seconds=delay) if delay else None
            if not await self._write_stage(project_id, run_id, stage, {
                "status": DEGRADED, "error_code": AI_FALLBACK_USED,
                "misconfigured_models": [], "finished_at": _iso(utc_now()),
                "next_retry_at": _iso(next_retry),
            }, artifact=artifact):
                return None, None
            logger.warning("[Pipeline] stage degraded | project_id=%s stage=%s next=%s", project_id, stage, _iso(next_retry))
            return DEGRADED, next_retry

        if not await self._write_stage(project_id, run_id, stage, {
            "status": COMPLETED, "error_code": None, "misconfigured_models": [],
            "finished_at": _iso(utc_now()), "next_retry_at": None,
        }, artifact=artifact):
            return None, None
        logger.info("[Pipeline] stage completed | project_id=%s stage=%s", project_id, stage)
        return COMPLETED, None

    async def _handle_failure(
        self, project_id: int, run_id: str | None, stage: str, attempt: int, exc: Exception
    ) -> tuple[str | None, datetime | None]:
        info = classify(exc)
        delay = retry_delay_seconds(attempt) if info.retryable else None
        status = WAITING_RETRY if delay else FAILED
        next_retry = utc_now() + timedelta(seconds=delay) if delay else None
        logger.warning(
            "[Pipeline] stage failed | project_id=%s stage=%s attempt=%s code=%s next=%s detail=%s",
            project_id, stage, attempt, info.code, _iso(next_retry), info.detail,
        )
        if not await self._write_stage(project_id, run_id, stage, {
            "status": status,
            "error_code": info.code,
            "misconfigured_models": list(info.misconfigured_models),
            "finished_at": _iso(utc_now()),
            "next_retry_at": _iso(next_retry),
        }):
            return None, None
        return status, next_retry

    # ---------------- manual trigger & startup ----------------

    async def reset_for_manual_run(self, project_id: int) -> bool:
        """
        Manual "Relancer": every stage that is not already fresh restarts
        from zero attempts. Returns False when the analysis is not completed.
        """
        async with self._session_factory() as db:
            project = await self._load(db, project_id)
            if project is None or project.analysis_status != "completed":
                return False
            analysis_data = dict(project.analysis_data or {})
            pipeline = _stored_pipeline(analysis_data) or initial_pipeline_state(project.analysis_run_id)
            pipeline["run_id"] = project.analysis_run_id
            for stage in STAGES:
                if artifact_status(stage, project_id, analysis_data) == COMPLETED:
                    continue
                if pipeline["stages"][stage].get("status") == RUNNING:
                    continue
                pipeline["stages"][stage] = new_stage_state()
            pipeline["updated_at"] = _iso(utc_now())
            analysis_data[PIPELINE_KEY] = pipeline
            project.analysis_data = analysis_data
            await db.commit()
            run_id = project.analysis_run_id
        lock = self._locks.get(project_id)
        if lock is None or not lock.locked():
            # Only a sleeping retry is cancelled; an in-flight generation
            # is never interrupted (it would leave a stage "running").
            previous = self._scheduled.pop(project_id, None)
            if previous is not None and not previous.done():
                previous.cancel()
        self.start(project_id, run_id)
        return True

    async def resume_pending(self) -> int:
        """
        Called once at backend startup. Re-schedules unfinished stages:
        pending/running (interrupted by a restart), waiting_retry/degraded
        (at their planned time), and configuration failures (a restart is
        exactly what applies a corrected .env).
        """
        resumed = 0
        async with self._session_factory() as db:
            rows = (
                await db.execute(
                    select(Project.id, Project.analysis_run_id, Project.analysis_data).where(
                        Project.analysis_status == "completed",
                        Project.analysis_data[PIPELINE_KEY].isnot(None),
                    )
                )
            ).all()
        for project_id, run_id, analysis_data in rows:
            pipeline = _stored_pipeline(analysis_data)
            if pipeline is None:
                continue
            due_in: float | None = None
            changed = False
            for stage in STAGES:
                state = pipeline["stages"][stage]
                status = state.get("status")
                if status in (PENDING, RUNNING):
                    state["status"] = PENDING
                    changed = changed or status == RUNNING
                    due_in = 0.0
                elif status == FAILED and state.get("error_code") == LLM_CONFIGURATION_ERROR:
                    pipeline["stages"][stage] = new_stage_state()
                    changed, due_in = True, 0.0
                elif status in (WAITING_RETRY, DEGRADED):
                    nxt = _parse_iso(state.get("next_retry_at"))
                    if status == DEGRADED and (nxt is None or int(state.get("attempts") or 0) >= MAX_AUTOMATIC_ATTEMPTS):
                        continue
                    wait = max(0.0, (nxt - utc_now()).total_seconds()) if nxt else 0.0
                    due_in = wait if due_in is None else min(due_in, wait)
            if changed:
                async with self._session_factory() as db:
                    project = await self._load(db, project_id)
                    if project is not None:
                        data = dict(project.analysis_data or {})
                        data[PIPELINE_KEY] = pipeline
                        project.analysis_data = data
                        await db.commit()
            if due_in is not None:
                self.schedule(project_id, run_id, max(due_in, STARTUP_RESUME_DELAY_SECONDS))
                resumed += 1
        if resumed:
            logger.info("[Pipeline] resumed %s project pipeline(s) at startup", resumed)
        return resumed


post_analysis_pipeline = PostAnalysisPipeline()
