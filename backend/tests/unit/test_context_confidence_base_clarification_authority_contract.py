from __future__ import annotations

import pytest

from app.services.idea_readiness_checker import (
    IdeaReadinessChecker,
)


BASE_FIELD_ANSWERS = {
    "actors": (
        "Primary users operate the solution, "
        "the customer organization pays, and "
        "an authorized manager makes the decision."
    ),
    "priority_workflow": (
        "A user creates a request, it is assigned, "
        "processed, reviewed, and closed."
    ),
    "project_archetype": (
        "A software service."
    ),
    "business_model": (
        "Customer organizations pay a recurring subscription."
    ),
    "mvp_scope": (
        "The first testable version includes account access, "
        "request creation, processing, status tracking, and reporting."
    ),
    "constraints": (
        "The project has explicit technical, financial, "
        "operational, and regulatory constraints."
    ),
    "success_metrics": (
        "Success is measured through active use, completed workflows, "
        "processing time, and repeat usage."
    ),
}


@pytest.mark.parametrize(
    ("field", "answer"),
    sorted(
        BASE_FIELD_ANSWERS.items()
    ),
)
def test_resolved_explicit_base_field_is_not_reasked(
    field: str,
    answer: str,
) -> None:
    """
    A resolved field-bound user clarification must beat structural absence.

    The gate may continue using structural evidence when no clarification
    exists, but once the user explicitly answers the exact canonical field,
    evaluate() must consume the same resolution authority as
    _requirement_is_present().
    """
    result = IdeaReadinessChecker().evaluate(
        title="Universal Clarification Probe",
        description="A digital service.",
        industry="Digital services",
        target_region="France",
        output_language="en",
        analysis_data={},
        clarification_answers={
            field: answer,
        },
    )

    unresolved = {
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
    }

    assert field not in unresolved, (
        "BASE_GATE_IGNORED_RESOLVED_"
        "EXPLICIT_CLARIFICATION:"
        + field
    )


def test_round_bundle_removes_every_answered_base_field() -> None:
    checker = IdeaReadinessChecker()

    answers = {
        "problem": (
            "Business teams lose time because operational requests "
            "are fragmented across manual workflows."
        ),
        "solution": (
            "A software platform centralizes requests, "
            "tracks states, and records outcomes."
        ),
        **BASE_FIELD_ANSWERS,
    }

    result = checker.evaluate(
        title="Universal Clarification Probe",
        description="A digital service.",
        industry="Digital services",
        target_region="France",
        output_language="en",
        analysis_data={},
        clarification_answers=answers,
    )

    unresolved = {
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
    }

    intersection = (
        set(answers)
        & unresolved
    )

    assert not intersection, (
        "BASE_GATE_REASKED_EXPLICIT_FIELDS:"
        + ",".join(
            sorted(intersection)
        )
    )

    assert float(
        result.get(
            "score"
        )
        or 0.0
    ) > 0.38


def test_explicit_unresolved_base_answer_stays_unresolved() -> None:
    result = IdeaReadinessChecker().evaluate(
        title="Universal Clarification Probe",
        description="A digital service.",
        industry="Digital services",
        target_region="France",
        output_language="en",
        analysis_data={},
        clarification_answers={
            "actors":
                "Not defined yet.",
        },
    )

    unresolved = {
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
    }

    assert "actors" in unresolved
