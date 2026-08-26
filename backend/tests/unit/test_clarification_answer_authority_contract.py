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


ROOT = Path("/app")


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
    analysis_data may be reset for a new run; clarification_context may
    not.
    """

    assert hasattr(
        Project,
        "clarification_context",
    )

    source = (
        ROOT
        / "app/routers/projects.py"
    ).read_text(
        encoding="utf-8",
    )

    start = source.find(
        "async def start_project_analysis"
    )

    assert start >= 0

    end = source.find(
        "\n@router.",
        start + 1,
    )

    if end < 0:
        end = len(source)

    function_source = source[
        start:end
    ]

    assert (
        "project.analysis_data = None"
        in function_source
    )

    assert (
        "project.clarification_context = None"
        not in function_source
    )
