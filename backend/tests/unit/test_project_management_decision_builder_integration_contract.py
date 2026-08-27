from __future__ import annotations

import inspect

import pytest

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
)
from app.schemas.project_management import (
    ProjectManagementContextV1,
    ProjectManagementDecisionProjectionV1,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)
from app.services.project_management_decision_projector import (
    project_management_decision_projector,
)


def builder_has_decision_api() -> bool:

    signature = inspect.signature(
        project_management_context_builder.build
    )

    return (
        "decision"
        in signature.parameters
    )


def skip_until_decision_api_exists() -> None:

    if not builder_has_decision_api():
        pytest.skip(
            "Blocked by PM builder decision API."
        )


def packet() -> ProjectContextPacketV3:

    return ProjectContextPacketV3(
        project_name="Decision Integration Probe",
        language="en",
        target_region="International",
        industry_user_input="B2B workflow software",

        actors=[
            ActorContext(
                name="Operator",
                role=ActorRole.USER,
                is_explicit=True,
            ),
        ],

        mvp_scope=[
            "Request intake",
        ],

        scope_exclusions=[
            "Automatic payments are excluded.",
        ],

        constraints=[
            "The system must not expose confidential data.",
        ],

        primary_archetype="b2b_workflow_saas",

        domain_terms=[
            "operations",
        ],
    )


def normal_decision():
    return (
        project_management_decision_projector.project(
            debate_judge={
                "status": "completed",
                "verdict_code": "conditional_go",

                "critical_risks": [
                    "Retention remains unvalidated.",
                ],

                "next_actions": [
                    "Run pilot",
                    "Measure repeated use",
                ],

                "go_no_go_conditions": [
                    "GO if repeated use is observed.",
                ],

                "final_recommendation": (
                    "Run a bounded pilot."
                ),
            }
        )
    )


def fallback_decision():
    return (
        project_management_decision_projector.project(
            debate_judge={
                "status": "completed_with_fallback",
                "verdict_code": "insufficient_evidence",

                "critical_risks": [
                    "Committee review is incomplete.",
                ],

                "next_actions": [
                    "Review manually",
                ],

                "go_no_go_conditions": [
                    "NO-GO until review is complete.",
                ],

                "final_recommendation": (
                    "Do not scale."
                ),
            }
        )
    )


def build(
    source,
    *,
    project_id="p-1",
    decision=None,
):
    return (
        project_management_context_builder.build(
            packet=source,
            project_id=project_id,
            decision=decision,
        )
    )


# ------------------------------------------------------------
# First Wrong Layer
# ------------------------------------------------------------


def test_pm_builder_accepts_only_certified_decision_projection() -> None:

    signature = inspect.signature(
        project_management_context_builder.build
    )

    parameters = set(
        signature.parameters
    )

    assert "decision" in parameters, (
        "ProjectManagementContextBuilder.build "
        "does not yet accept the certified "
        "ProjectManagementDecisionProjectionV1."
    )

    forbidden = {
        "analysis_data",
        "debate_room",
        "debate_judge",
        "startup_score",
        "final_report",
        "evidence_ledger",
        "public_analysis",
        "project_intelligence",
        "search_results",
        "queries",
        "rag_context",
    }

    assert not (
        forbidden
        &
        parameters
    )


# ------------------------------------------------------------
# PM Context schema must preserve decision provenance
# ------------------------------------------------------------


def test_pm_context_preserves_decision_provenance_fields() -> None:

    skip_until_decision_api_exists()

    fields = set(
        ProjectManagementContextV1.model_fields
    )

    required = {
        "decision_source",
        "decision_status",
        "canonical_verdict_code",
        "validated_risks",
        "validated_next_actions",
        "go_no_go_conditions",
        "final_recommendation",
    }

    assert not (
        required
        -
        fields
    )


# ------------------------------------------------------------
# Normal authority projection
# ------------------------------------------------------------


def test_completed_decision_projects_into_pm_context() -> None:

    skip_until_decision_api_exists()

    decision = normal_decision()

    context = build(
        packet(),
        decision=decision,
    )

    assert (
        context.decision_source
        ==
        "debate_room.judge"
    )

    assert (
        context.decision_status
        ==
        "completed"
    )

    assert (
        context.canonical_verdict_code
        ==
        "conditional_go"
    )

    assert context.validated_risks == [
        "Retention remains unvalidated."
    ]

    assert context.validated_next_actions == [
        "Run pilot",
        "Measure repeated use",
    ]

    assert context.go_no_go_conditions == [
        "GO if repeated use is observed."
    ]

    assert (
        context.final_recommendation
        ==
        "Run a bounded pilot."
    )


# ------------------------------------------------------------
# Safe fallback authority
# ------------------------------------------------------------


def test_safe_fallback_projects_into_pm_context() -> None:

    skip_until_decision_api_exists()

    context = build(
        packet(),
        decision=fallback_decision(),
    )

    assert (
        context.decision_source
        ==
        "debate_room.judge"
    )

    assert (
        context.decision_status
        ==
        "completed_with_fallback"
    )

    assert (
        context.canonical_verdict_code
        ==
        "insufficient_evidence"
    )

    assert (
        context.final_recommendation
        ==
        "Do not scale."
    )


# ------------------------------------------------------------
# Unknown stays unknown
# ------------------------------------------------------------


def test_missing_decision_remains_unknown() -> None:

    skip_until_decision_api_exists()

    context = build(
        packet(),
        decision=None,
    )

    assert context.decision_source == ""
    assert context.decision_status == ""
    assert context.canonical_verdict_code == ""
    assert context.validated_risks == []
    assert context.validated_next_actions == []
    assert context.go_no_go_conditions == []
    assert context.final_recommendation == ""


def test_non_authoritative_manual_projection_is_not_promoted() -> None:

    skip_until_decision_api_exists()

    forged = (
        ProjectManagementDecisionProjectionV1(
            decision_source="",
            decision_status="completed",
            canonical_verdict_code="go",
            validated_risks=[
                "Forged risk",
            ],
            validated_next_actions=[
                "Scale immediately",
            ],
            go_no_go_conditions=[
                "GO",
            ],
            final_recommendation=(
                "Scale immediately."
            ),
        )
    )

    context = build(
        packet(),
        decision=forged,
    )

    assert context.decision_source == ""
    assert context.decision_status == ""
    assert context.canonical_verdict_code == ""
    assert context.validated_risks == []
    assert context.validated_next_actions == []
    assert context.go_no_go_conditions == []
    assert context.final_recommendation == ""


# ------------------------------------------------------------
# Hash authority separation
# ------------------------------------------------------------


def test_decision_changes_context_hash_but_not_source_context_hash() -> None:

    skip_until_decision_api_exists()

    source = packet()

    without_decision = build(
        source,
        decision=None,
    )

    with_decision = build(
        source,
        decision=normal_decision(),
    )

    assert (
        without_decision.source_context_hash
        ==
        with_decision.source_context_hash
    )

    assert (
        without_decision.context_hash
        !=
        with_decision.context_hash
    )


def test_different_canonical_decisions_share_source_hash_but_not_context_hash() -> None:

    skip_until_decision_api_exists()

    source = packet()

    normal = build(
        source,
        decision=normal_decision(),
    )

    fallback = build(
        source,
        decision=fallback_decision(),
    )

    assert (
        normal.source_context_hash
        ==
        fallback.source_context_hash
    )

    assert (
        normal.context_hash
        !=
        fallback.context_hash
    )


def test_same_packet_and_same_decision_are_fully_deterministic() -> None:

    skip_until_decision_api_exists()

    source = packet()
    decision = normal_decision()

    first = build(
        source,
        decision=decision,
    )

    second = build(
        source.model_copy(
            deep=True
        ),
        decision=decision.model_copy(
            deep=True
        ),
    )

    assert first == second


def test_canonical_project_change_still_changes_both_hashes() -> None:

    skip_until_decision_api_exists()

    first_packet = packet()

    second_packet = first_packet.model_copy(
        deep=True,
        update={
            "mvp_scope": [
                "Request intake",
                "Audit history",
            ],
        },
    )

    decision = normal_decision()

    first = build(
        first_packet,
        decision=decision,
    )

    second = build(
        second_packet,
        decision=decision,
    )

    assert (
        first.source_context_hash
        !=
        second.source_context_hash
    )

    assert (
        first.context_hash
        !=
        second.context_hash
    )


def test_archetype_noise_remains_isolated_even_with_decision_present() -> None:

    skip_until_decision_api_exists()

    clean_packet = packet()

    noisy_packet = clean_packet.model_copy(
        deep=True,
        update={
            "primary_archetype": (
                "two_sided_marketplace"
            ),
            "archetype_confidence": 1.0,
            "domain_terms": [
                "recruiting",
                "marketplace",
            ],
            "use_case_terms": [
                "candidate matching",
            ],
            "solution_terms": [
                "talent platform",
            ],
            "target_terms": [
                "job seekers",
            ],
        },
    )

    decision = normal_decision()

    clean = build(
        clean_packet,
        decision=decision,
    )

    noisy = build(
        noisy_packet,
        decision=decision,
    )

    assert (
        clean.source_context_hash
        ==
        noisy.source_context_hash
    )

    assert (
        clean.context_hash
        ==
        noisy.context_hash
    )


# ------------------------------------------------------------
# Immutability
# ------------------------------------------------------------


def test_builder_does_not_mutate_decision_projection() -> None:

    skip_until_decision_api_exists()

    decision = normal_decision()

    before = decision.model_dump(
        mode="json"
    )

    build(
        packet(),
        decision=decision,
    )

    after = decision.model_dump(
        mode="json"
    )

    assert after == before