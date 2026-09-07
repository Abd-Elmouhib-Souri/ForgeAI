from __future__ import annotations

import inspect
from pathlib import Path

from app.models import Project
from app.services.idea_readiness_checker import (
    IdeaReadinessChecker,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


ROOT = Path(__file__).resolve().parents[2]


def test_project_has_durable_clarification_context_authority():
    """
    Clarification answers outlive analysis runs.

    analysis_data is run-scoped and is intentionally reset by
    /analyze/start, therefore explicit user clarification facts need
    their own durable Project authority.
    """

    assert hasattr(
        Project,
        "clarification_context",
    )


def test_readiness_exposes_field_bound_clarification_items():
    """
    Every clarification question actually displayed to the user retains
    the canonical field it resolves.

    Diagnostic fields may be more numerous than the human-facing question
    surface because ContextConfidenceGate intentionally caps that surface.
    """
    checker = IdeaReadinessChecker()

    result = checker.evaluate(
        title="Universal Context Probe",
        description="A digital product.",
        industry="",
        target_region="",
        output_language="en",
    )

    requested_fields = list(
        dict.fromkeys(
            [
                *(
                    result.get(
                        "missing_fields"
                    )
                    or []
                ),
                *(
                    result.get(
                        "ambiguous_fields"
                    )
                    or []
                ),
                *(
                    result.get(
                        "blockers"
                    )
                    or []
                ),
            ]
        )
    )

    questions = (
        result.get(
            "clarification_questions"
        )
        or []
    )

    items = (
        result.get(
            "clarification_items"
        )
        or []
    )

    assert requested_fields
    assert questions
    assert items

    assert len(
        items
    ) == len(
        questions
    )

    assert [
        item.get(
            "question"
        )
        for item in items
    ] == questions

    assert [
        item.get(
            "field"
        )
        for item in items
    ] == requested_fields[
        :len(
            questions
        )
    ]

    missing = set(
        result.get(
            "missing_fields"
        )
        or []
    )

    ambiguous = set(
        result.get(
            "ambiguous_fields"
        )
        or []
    )

    for item in items:
        field = item.get(
            "field"
        )

        if field in missing:
            expected_kind = "missing"

        elif field in ambiguous:
            expected_kind = "ambiguous"

        else:
            expected_kind = "blocking"

        assert (
            item.get(
                "kind"
            )
            == expected_kind
        )


def test_field_bound_items_respect_gate_question_cap():
    """
    A very vague project can expose more diagnostic fields than questions.

    That must never crash IdeaReadinessChecker, and every displayed question
    must still retain its canonical field identity.
    """
    checker = IdeaReadinessChecker()

    result = checker.evaluate(
        title="Student App",
        description=(
            "Je veux creer une application "
            "pour les etudiants."
        ),
        industry="Education",
        target_region="",
        output_language="fr",
    )

    requested_fields = list(
        dict.fromkeys(
            [
                *(
                    result.get(
                        "missing_fields"
                    )
                    or []
                ),
                *(
                    result.get(
                        "ambiguous_fields"
                    )
                    or []
                ),
                *(
                    result.get(
                        "blockers"
                    )
                    or []
                ),
            ]
        )
    )

    questions = (
        result.get(
            "clarification_questions"
        )
        or []
    )

    items = (
        result.get(
            "clarification_items"
        )
        or []
    )

    assert len(
        questions
    ) <= 10

    assert len(
        items
    ) == len(
        questions
    )

    assert [
        item.get(
            "field"
        )
        for item in items
    ] == requested_fields[
        :len(
            questions
        )
    ]

    assert [
        item.get(
            "question"
        )
        for item in items
    ] == questions


def test_explicit_clarification_answers_invalidate_stale_packet():
    """
    An old packet with identical title/description must never override
    newer explicit user clarification answers.
    """

    checker = IdeaReadinessChecker()

    signature = inspect.signature(
        checker.evaluate
    )

    assert (
        "clarification_answers"
        in signature.parameters
    )

    original_packet = (
        project_context_extractor.extract(
            title="Region Probe",
            description=(
                "A scheduling product for "
                "small companies."
            ),
            industry=(
                "workforce scheduling"
            ),
            target_region="Tunisie",
            output_language="en",
        )
    )

    result = checker.evaluate(
        title="Region Probe",
        description=(
            "A scheduling product for "
            "small companies."
        ),
        industry=(
            "workforce scheduling"
        ),
        target_region="Tunisie",
        output_language="en",
        project_context={
            "project_context_packet":
                original_packet.model_dump(
                    mode="json"
                ),
        },
        clarification_answers={
            "target_region":
                "France",
        },
    )

    packet = (
        result[
            "project_context_packet"
        ]
    )

    assert (
        packet["target_region"]
        == "France"
    )


def test_explicit_problem_and_solution_answers_beat_old_inference():
    """
    Explicit user answers are higher authority than text inference.

    They enrich the canonical packet without rewriting the original
    project description.
    """

    checker = IdeaReadinessChecker()

    signature = inspect.signature(
        checker.evaluate
    )

    assert (
        "clarification_answers"
        in signature.parameters
    )

    description = (
        "The problem is an old inferred problem. "
        "The proposed solution is an old inferred solution."
    )

    result = checker.evaluate(
        title="Authority Probe",
        description=description,
        industry="digital services",
        target_region="France",
        output_language="en",
        clarification_answers={
            "problem": (
                "Teams lose time because "
                "handoffs are fragmented."
            ),
            "solution": (
                "A shared workflow that "
                "coordinates the handoff."
            ),
        },
    )

    packet = (
        result[
            "project_context_packet"
        ]
    )

    assert packet["description"] == description

    assert isinstance(
        packet["problem"],
        dict,
    )

    assert (
        packet["problem"]["pain"]
        == (
            "Teams lose time because "
            "handoffs are fragmented."
        )
    )

    assert isinstance(
        packet["solution"],
        dict,
    )

    assert (
        packet["solution"]["mechanism"]
        == (
            "A shared workflow that "
            "coordinates the handoff."
        )
    )


def test_background_preflight_consumes_durable_clarification_context():
    """
    The runtime preflight must project durable Project clarification
    facts into IdeaReadinessChecker before any agent or web search.
    """

    source = (
        ROOT
        / "app/routers/projects.py"
    ).read_text(
        encoding="utf-8",
    )

    assert (
        "clarification_context"
        in source
    )

    assert (
        "clarification_answers="
        in source
    )

    readiness_call = source.find(
        "idea_readiness_checker.evaluate("
    )

    assert readiness_call >= 0

    neighborhood = source[
        readiness_call:
        readiness_call + 2200
    ]

    assert (
        "clarification_answers="
        in neighborhood
    )


def test_dedicated_clarification_patch_route_exists():
    """
    Saving clarification answers is not the same operation as launching
    a new analysis run.
    """

    source = (
        ROOT
        / "app/routers/projects.py"
    ).read_text(
        encoding="utf-8",
    )

    assert (
        '/{project_id}/clarifications'
        in source
    )

    assert (
        '@router.patch('
        in source
    )


def test_start_analysis_does_not_erase_durable_clarifications():
    """
    Starting a new analysis must discard data owned by the previous analysis
    run while preserving durable user clarification authority.

    Sprint 4 Project Manager revisions are also durable state: when a valid
    project_manager envelope exists it may survive alone so downstream
    Product Manager authority can classify it as current or stale.

    This contract intentionally verifies runtime semantics rather than a
    specific assignment statement inside the router.
    """
    import asyncio
    import copy
    from types import SimpleNamespace

    import app.routers.projects as projects_module

    durable_clarifications = {
        "target_region": "New Zealand",
        "human_oversight": "A coordinator approves release.",
        "transaction_flow": (
            "A member requests equipment and a coordinator approves."
        ),
    }

    durable_project_manager = {
        "schema_version": "project_management_plan_v1",
        "revision": 4,
        "context_hash": "previous-context-hash",
        "sentinel": "DURABLE_PM_REVISION",
    }

    class FakeDB:
        def __init__(self, project):
            self.project = project
            self.commit_count = 0
            self.refresh_count = 0

        async def commit(self):
            self.commit_count += 1

        async def refresh(self, value):
            assert value is self.project
            self.refresh_count += 1

    class FakeBackgroundTasks:
        def __init__(self):
            self.tasks = []

        def add_task(self, func, *args, **kwargs):
            self.tasks.append(
                (
                    func,
                    args,
                    kwargs,
                )
            )

    async def execute_case(
        *,
        initial_analysis_data,
        expected_analysis_data,
    ):
        project = SimpleNamespace(
            id=987654321,
            analysis_status="completed",
            analysis_run_id="old-run",
            analysis_attempt=7,
            analysis_heartbeat_at=None,
            analysis_step="Previous completed analysis",
            analysis_progress=100,
            analysis_data=copy.deepcopy(
                initial_analysis_data
            ),
            analysis_error="old error",
            analysis_started_at=None,
            analysis_completed_at="old-completed",
            clarification_context=copy.deepcopy(
                durable_clarifications
            ),
        )

        db = FakeDB(project)
        background_tasks = FakeBackgroundTasks()

        original_get = (
            projects_module.get_project_or_404
        )
        original_public = (
            projects_module.analysis_to_public_response
        )

        async def fake_get_project_or_404(
            project_id,
            db_arg,
            current_user,
        ):
            assert project_id == project.id
            assert db_arg is db
            return project

        def fake_public_response(
            current_project,
        ):
            return {
                "analysis_status":
                    current_project.analysis_status,
                "analysis_data":
                    copy.deepcopy(
                        current_project.analysis_data
                    ),
                "clarification_context":
                    copy.deepcopy(
                        current_project.clarification_context
                    ),
            }

        projects_module.get_project_or_404 = (
            fake_get_project_or_404
        )
        projects_module.analysis_to_public_response = (
            fake_public_response
        )

        try:
            response = await (
                projects_module.start_project_analysis(
                    project_id=project.id,
                    background_tasks=background_tasks,
                    current_user=SimpleNamespace(
                        id=123
                    ),
                    db=db,
                )
            )
        finally:
            projects_module.get_project_or_404 = (
                original_get
            )
            projects_module.analysis_to_public_response = (
                original_public
            )

        assert project.analysis_data == expected_analysis_data

        assert (
            project.clarification_context
            == durable_clarifications
        )

        assert project.analysis_status == "queued"
        assert project.analysis_attempt == 8

        assert len(
            background_tasks.tasks
        ) == 1

        assert db.commit_count == 1
        assert db.refresh_count == 1

        assert (
            response["analysis_data"]
            == expected_analysis_data
        )

        assert (
            response["clarification_context"]
            == durable_clarifications
        )

    async def run_cases():
        # No durable Project Manager state:
        # all previous run-owned analysis must disappear.
        await execute_case(
            initial_analysis_data={
                "market_study": {
                    "sentinel": "STALE_RUN_DATA",
                },
                "startup_evaluator": {
                    "sentinel": "STALE_RUN_DATA",
                },
            },
            expected_analysis_data=None,
        )

        # A Project Manager revision is durable, but arbitrary
        # previous analysis data must still disappear.
        await execute_case(
            initial_analysis_data={
                "market_study": {
                    "sentinel": "STALE_RUN_DATA",
                },
                "startup_evaluator": {
                    "sentinel": "STALE_RUN_DATA",
                },
                "project_manager": copy.deepcopy(
                    durable_project_manager
                ),
            },
            expected_analysis_data={
                "project_manager": copy.deepcopy(
                    durable_project_manager
                ),
            },
        )

    asyncio.run(
        run_cases()
    )
