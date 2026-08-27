from __future__ import annotations

import importlib
import importlib.util
import inspect

import pytest


MODULE_NAME = (
    "app.services."
    "project_management_decision_projector"
)


def module_exists() -> bool:
    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def skip_until_projector_exists() -> None:
    if not module_exists():
        pytest.skip(
            "Blocked by canonical decision projector."
        )


def module():
    return importlib.import_module(
        MODULE_NAME
    )


def projector():
    loaded = module()

    singleton = getattr(
        loaded,
        "project_management_decision_projector",
        None,
    )

    if singleton is not None:
        return singleton

    cls = getattr(
        loaded,
        "ProjectManagementDecisionProjector",
    )

    return cls()


def judge():
    return {
        "format": "debate_judge_v1",
        "status": "completed",

        "verdict": "CONDITIONAL_GO",
        "verdict_code": "conditional_go",

        "critical_risks": [
            "Payment willingness remains unvalidated.",
            "Pilot retention has not yet been measured.",
        ],

        "final_recommendation": (
            "Run a bounded pilot before scaling."
        ),

        "next_actions": [
            "Run pilot",
            "Validate payer",
        ],

        "go_no_go_conditions": [
            "GO if repeated use is observed.",
            "NO-GO if buyers reject the tested value.",
        ],
    }


# ------------------------------------------------------------
# Existence / API
# ------------------------------------------------------------


def test_decision_projector_module_exists() -> None:

    assert module_exists(), (
        "Missing canonical Sprint 4 decision projector: "
        "app.services.project_management_decision_projector"
    )


def test_decision_projector_has_one_narrow_authority_api() -> None:

    skip_until_projector_exists()

    value = projector()

    signature = inspect.signature(
        value.project
    )

    parameters = set(
        signature.parameters
    )

    assert "debate_judge" in parameters

    forbidden = {
        "analysis_data",
        "startup_score",
        "evidence_ledger",
        "final_report",
        "public_analysis",
        "project_intelligence",
        "archetype_context",
        "search_results",
        "queries",
    }

    assert not (
        forbidden
        &
        parameters
    )


# ------------------------------------------------------------
# Canonical authority
# ------------------------------------------------------------


def test_debate_judge_is_the_only_decision_authority() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge=judge(),
    )

    assert (
        result.decision_source
        ==
        "debate_room.judge"
    )

    assert (
        result.canonical_verdict_code
        ==
        "conditional_go"
    )


def test_next_actions_project_only_from_debate_judge() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge=judge(),
    )

    assert (
        result.validated_next_actions
        ==
        [
            "Run pilot",
            "Validate payer",
        ]
    )


def test_go_no_go_conditions_project_only_from_debate_judge() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge=judge(),
    )

    assert (
        result.go_no_go_conditions
        ==
        [
            "GO if repeated use is observed.",
            "NO-GO if buyers reject the tested value.",
        ]
    )


def test_critical_risks_project_as_decision_validated_risks() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge=judge(),
    )

    assert (
        result.validated_risks
        ==
        [
            "Payment willingness remains unvalidated.",
            "Pilot retention has not yet been measured.",
        ]
    )


def test_final_recommendation_is_preserved() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge=judge(),
    )

    assert (
        result.final_recommendation
        ==
        "Run a bounded pilot before scaling."
    )


# ------------------------------------------------------------
# Unknown stays unknown
# ------------------------------------------------------------


def test_missing_debate_judge_does_not_fabricate_decision() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge=None,
    )

    assert result.decision_source == ""
    assert result.decision_status == ""
    assert result.canonical_verdict_code == ""
    assert result.validated_risks == []
    assert result.validated_next_actions == []
    assert result.go_no_go_conditions == []
    assert result.final_recommendation == ""


def test_empty_debate_judge_does_not_fabricate_decision() -> None:

    skip_until_projector_exists()

    result = projector().project(
        debate_judge={},
    )

    assert result.decision_source == ""
    assert result.decision_status == ""
    assert result.canonical_verdict_code == ""
    assert result.validated_risks == []
    assert result.validated_next_actions == []
    assert result.go_no_go_conditions == []


def test_completed_judge_is_a_final_decision_authority() -> None:

    skip_until_projector_exists()

    source = judge()

    result = projector().project(
        debate_judge=source,
    )

    assert result.decision_source == "debate_room.judge"
    assert result.decision_status == "completed"

    assert (
        result.canonical_verdict_code
        ==
        "conditional_go"
    )


def test_completed_with_fallback_is_a_canonical_safe_fallback() -> None:

    skip_until_projector_exists()

    source = {
        "format": "investment_committee_memo_v9_fallback",
        "status": "completed_with_fallback",
        "verdict": "INSUFFICIENT_EVIDENCE",
        "verdict_code": "insufficient_evidence",

        "critical_risks": [
            (
                "The committee could not complete "
                "its structured review."
            ),
        ],

        "final_recommendation": (
            "Do not scale. Review the analysis "
            "and rerun the committee."
        ),

        "next_actions": [
            (
                "Review the error and validate "
                "the project manually."
            ),
        ],

        "go_no_go_conditions": [
            (
                "NO-GO for scaling until "
                "the review is complete."
            ),
        ],
    }

    result = projector().project(
        debate_judge=source,
    )

    assert (
        result.decision_source
        ==
        "debate_room.judge"
    )

    assert (
        result.decision_status
        ==
        "completed_with_fallback"
    )

    assert (
        result.canonical_verdict_code
        ==
        "insufficient_evidence"
    )

    assert result.validated_risks == [
        (
            "The committee could not complete "
            "its structured review."
        )
    ]

    assert result.validated_next_actions == [
        (
            "Review the error and validate "
            "the project manually."
        )
    ]

    assert result.go_no_go_conditions == [
        (
            "NO-GO for scaling until "
            "the review is complete."
        )
    ]

    assert (
        result.final_recommendation
        ==
        (
            "Do not scale. Review the analysis "
            "and rerun the committee."
        )
    )


@pytest.mark.parametrize(
    "status",
    (
        "running",
        "pending",
        "failed",
        "error",
    ),
)
def test_non_final_judge_status_does_not_enter_planning_authority(
    status,
) -> None:

    skip_until_projector_exists()

    source = judge()

    source[
        "status"
    ] = status

    result = projector().project(
        debate_judge=source,
    )

    assert result.decision_source == ""
    assert result.decision_status == ""
    assert result.canonical_verdict_code == ""
    assert result.validated_risks == []
    assert result.validated_next_actions == []
    assert result.go_no_go_conditions == []
    assert result.final_recommendation == ""


def test_missing_status_is_not_assumed_final() -> None:

    skip_until_projector_exists()

    source = judge()

    source.pop(
        "status",
        None,
    )

    result = projector().project(
        debate_judge=source,
    )

    assert result.decision_source == ""
    assert result.decision_status == ""
    assert result.canonical_verdict_code == ""
    assert result.validated_risks == []
    assert result.validated_next_actions == []
    assert result.go_no_go_conditions == []


# ------------------------------------------------------------
# Normalization / determinism
# ------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "raw",
        "expected",
    ),
    (
        (
            "conditional_go",
            "conditional_go",
        ),
        (
            "CONDITIONAL_GO",
            "conditional_go",
        ),
        (
            "Conditional Go",
            "conditional_go",
        ),
        (
            "proceed_with_validation",
            "proceed_with_validation",
        ),
    ),
)
def test_verdict_code_is_normalized_deterministically(
    raw,
    expected,
) -> None:

    skip_until_projector_exists()

    source = judge()
    source["verdict_code"] = raw

    result = projector().project(
        debate_judge=source,
    )

    assert (
        result.canonical_verdict_code
        ==
        expected
    )


def test_projector_does_not_mutate_debate_judge() -> None:

    skip_until_projector_exists()

    source = judge()

    before = repr(
        source
    )

    projector().project(
        debate_judge=source,
    )

    after = repr(
        source
    )

    assert after == before


def test_duplicate_decision_items_are_normalized_without_reordering() -> None:

    skip_until_projector_exists()

    source = judge()

    source[
        "next_actions"
    ] = [
        "Run pilot",
        "Run pilot",
        "Validate payer",
    ]

    result = projector().project(
        debate_judge=source,
    )

    assert (
        result.validated_next_actions
        ==
        [
            "Run pilot",
            "Validate payer",
        ]
    )


# ------------------------------------------------------------
# Semantic safety
# ------------------------------------------------------------


def test_projector_does_not_convert_missing_evidence_into_validated_risks() -> None:

    skip_until_projector_exists()

    source = judge()

    source[
        "missing_evidence"
    ] = [
        "No pricing interview yet.",
    ]

    result = projector().project(
        debate_judge=source,
    )

    assert (
        "No pricing interview yet."
        not in
        result.validated_risks
    )


def test_projector_does_not_convert_weak_assumptions_into_validated_risks() -> None:

    skip_until_projector_exists()

    source = judge()

    source[
        "weak_assumptions"
    ] = [
        "Users may pay monthly.",
    ]

    result = projector().project(
        debate_judge=source,
    )

    assert (
        "Users may pay monthly."
        not in
        result.validated_risks
    )