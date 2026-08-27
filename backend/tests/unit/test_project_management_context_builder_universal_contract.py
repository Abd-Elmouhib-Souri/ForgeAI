from __future__ import annotations

import hashlib
import json
import re

import pytest

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProblemContext,
    ProjectContextPacketV3,
    SolutionContext,
    WorkflowContext,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


def workflow(
    name: str,
    action: str,
) -> WorkflowContext:
    return WorkflowContext(
        name=name,
        actor="Operator",
        action=action,
        object="request",
        result="",
        output="",
        frequency="daily",
        is_explicit=True,
        confidence=0.95,
    )


def packet() -> ProjectContextPacketV3:
    return ProjectContextPacketV3(
        project_name="Universal Planning Context",
        description=(
            "Narrative text that is not itself "
            "planning authority."
        ),
        language="en",
        target_region="International",
        industry_user_input="B2B operations",

        sector_labels=[
            "Operations",
        ],

        primary_archetype="b2b_workflow_saas",
        archetype_confidence=0.85,

        secondary_archetypes=[
            "workflow_tool",
        ],

        risk_domains=[
            "operational",
        ],

        problem=ProblemContext(
            actors_affected=[
                "Operator",
            ],
            pain="Manual coordination causes conflicts.",
            frequency="daily",
            severity="high",
            current_alternatives=[
                "spreadsheets",
            ],
            consequences=[
                "delays",
            ],
        ),

        solution=SolutionContext(
            mechanism="Coordinate requests.",
            core_value="Reduce conflicts.",
            delivery_mode="web application",
            required_capabilities=[
                "request intake",
                "review",
            ],
            differentiators=[],
        ),

        actors=[
            ActorContext(
                name="Operator",
                role=ActorRole.USER,
                is_explicit=True,
            ),
            ActorContext(
                name="Supervisor",
                role=ActorRole.OPERATOR,
                is_explicit=True,
            ),
            ActorContext(
                name="Company",
                role=ActorRole.PAYER,
                is_explicit=True,
            ),
        ],

        payer_actor_names=[
            "Company",
        ],

        decision_maker_actor_names=[],
        partner_actor_names=[],
        blocker_actor_names=[],

        priority_workflows=[
            workflow(
                "Submit",
                "submit",
            ),
            workflow(
                "Review",
                "review",
            ),
        ],

        mvp_scope=[
            "Request intake",
            "Supervisor review",
        ],

        scope_exclusions=[
            "Automatic payment execution is excluded.",
        ],

        human_oversight=[
            "A supervisor must approve final requests.",
        ],

        constraints=[
            "The system must not expose confidential data.",
        ],

        assumptions=[
            "Initial rollout assumes one organization.",
        ],

        clarification_facts={
            "payer": "Company",
            "user": "Operator",
        },

        blocking_missing_fields=[
            "validated pricing",
        ],

        validation_warnings=[
            "Pricing remains unvalidated.",
        ],

        domain_terms=[
            "operations",
        ],

        use_case_terms=[
            "coordination",
        ],

        solution_terms=[
            "workflow automation",
        ],

        target_terms=[
            "operations teams",
        ],

        forbidden_adjacent_domains=[
            "consumer marketplace",
        ],
    )


def build(
    value: ProjectContextPacketV3,
    *,
    project_id: str = "p-1",
):
    return (
        project_management_context_builder.build(
            packet=value,
            project_id=project_id,
        )
    )


def without_hashes(context):
    return context.model_dump(
        mode="json",
        exclude={
            "source_context_hash",
            "context_hash",
        },
    )


def assert_sha256(value: str) -> None:
    assert re.fullmatch(
        r"[0-9a-f]{64}",
        value,
    )


@pytest.mark.parametrize(
    (
        "field_name",
        "replacement",
    ),
    (
        (
            "description",
            (
                "Completely different irrelevant "
                "narrative prose."
            ),
        ),
        (
            "sector_labels",
            [
                "Completely Different Label",
            ],
        ),
        (
            "primary_archetype",
            "two_sided_marketplace",
        ),
        (
            "archetype_confidence",
            1.0,
        ),
        (
            "secondary_archetypes",
            [
                "workforce_platform",
            ],
        ),
        (
            "risk_domains",
            [
                "unrelated-risk-hint",
            ],
        ),
        (
            "domain_terms",
            [
                "recruiting",
                "marketplace",
            ],
        ),
        (
            "use_case_terms",
            [
                "candidate matching",
            ],
        ),
        (
            "solution_terms",
            [
                "talent platform",
            ],
        ),
        (
            "target_terms",
            [
                "job seekers",
            ],
        ),
    ),
)
def test_non_authoritative_source_hints_do_not_mutate_pm_context_or_hashes(
    field_name,
    replacement,
) -> None:

    original = packet()

    changed = original.model_copy(
        deep=True,
        update={
            field_name: replacement,
        },
    )

    first = build(
        original
    )

    second = build(
        changed
    )

    assert (
        without_hashes(first)
        ==
        without_hashes(second)
    )

    assert (
        first.source_context_hash
        ==
        second.source_context_hash
    )

    assert (
        first.context_hash
        ==
        second.context_hash
    )


@pytest.mark.parametrize(
    (
        "field_name",
        "replacement",
    ),
    (
        (
            "project_name",
            "Changed Project",
        ),
        (
            "target_region",
            "Tunisia",
        ),
        (
            "industry_user_input",
            "B2B logistics",
        ),
        (
            "mvp_scope",
            [
                "Request intake",
                "Supervisor review",
                "Audit history",
            ],
        ),
        (
            "scope_exclusions",
            [
                "Automatic payment execution is excluded.",
                "Autonomous approval is excluded.",
            ],
        ),
        (
            "constraints",
            [
                "The system must not expose confidential data.",
                "The system must operate offline.",
            ],
        ),
        (
            "human_oversight",
            [
                "A reviewer must validate every final output.",
            ],
        ),
        (
            "assumptions",
            [
                "The first rollout assumes two organizations.",
            ],
        ),
        (
            "blocking_missing_fields",
            [
                "validated pricing",
                "retention policy",
            ],
        ),
        (
            "validation_warnings",
            [
                "Pricing remains unvalidated.",
                "Retention policy remains unknown.",
            ],
        ),
        (
            "forbidden_adjacent_domains",
            [
                "consumer marketplace",
                "recruitment platform",
            ],
        ),
    ),
)
def test_authoritative_change_mutates_source_and_context_hashes(
    field_name,
    replacement,
) -> None:

    original = packet()

    changed = original.model_copy(
        deep=True,
        update={
            field_name: replacement,
        },
    )

    first = build(
        original
    )

    second = build(
        changed
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


def test_project_id_changes_context_identity_but_not_source_hash() -> None:

    source = packet()

    first = build(
        source,
        project_id="project-a",
    )

    second = build(
        source,
        project_id="project-b",
    )

    assert (
        first.source_context_hash
        ==
        second.source_context_hash
    )

    assert (
        first.context_hash
        !=
        second.context_hash
    )


def test_clarification_dict_order_is_not_hash_semantics() -> None:

    first_packet = packet()

    second_packet = first_packet.model_copy(
        deep=True,
        update={
            "clarification_facts": {
                "user": "Operator",
                "payer": "Company",
            },
        },
    )

    first = build(
        first_packet
    )

    second = build(
        second_packet
    )

    assert (
        first.source_context_hash
        ==
        second.source_context_hash
    )

    assert (
        first.context_hash
        ==
        second.context_hash
    )


def test_meaningful_workflow_order_is_preserved_by_hashing() -> None:

    first_packet = packet()

    second_packet = first_packet.model_copy(
        deep=True,
        update={
            "priority_workflows": list(
                reversed(
                    first_packet.priority_workflows
                )
            ),
        },
    )

    first = build(
        first_packet
    )

    second = build(
        second_packet
    )

    assert [
        value.name
        for value in first.priority_workflows
    ] == [
        "Submit",
        "Review",
    ]

    assert [
        value.name
        for value in second.priority_workflows
    ] == [
        "Review",
        "Submit",
    ]

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


def test_utf8_semantics_are_deterministic() -> None:

    first_packet = packet().model_copy(
        deep=True,
        update={
            "language": "fr",
            "target_region": "Tunisie",
            "mvp_scope": [
                (
                    "Validation des demandes "
                    "par l'opérateur"
                ),
            ],
        },
    )

    second_packet = first_packet.model_copy(
        deep=True
    )

    first = build(
        first_packet
    )

    second = build(
        second_packet
    )

    assert_sha256(
        first.source_context_hash
    )

    assert_sha256(
        first.context_hash
    )

    assert (
        first.source_context_hash
        ==
        second.source_context_hash
    )

    assert (
        first.context_hash
        ==
        second.context_hash
    )


def test_context_hash_matches_documented_canonical_json_algorithm() -> None:

    context = build(
        packet()
    )

    projection = context.model_dump(
        mode="json",
        exclude={
            "source_context_hash",
            "context_hash",
        },
    )

    material = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
    )

    expected = hashlib.sha256(
        material.encode(
            "utf-8"
        )
    ).hexdigest()

    assert (
        context.context_hash
        ==
        expected
    )


def test_no_time_or_runtime_metadata_enters_pm_context_schema() -> None:

    context = build(
        packet()
    )

    forbidden_fields = {
        "created_at",
        "updated_at",
        "generated_at",
        "timestamp",
        "run_id",
        "request_id",
    }

    assert not (
        forbidden_fields
        &
        set(
            context.model_fields
        )
    )


def test_downstream_sprint3_outputs_remain_unknown_until_certified() -> None:

    context = build(
        packet()
    )

    assert context.validated_risks == []
    assert context.validated_next_actions == []
    assert context.go_no_go_conditions == []
    assert context.canonical_verdict_code == ""