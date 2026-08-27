from __future__ import annotations

import importlib
import importlib.util
import inspect
import re

import pytest

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProblemContext,
    ProjectContextPacketV3,
    SolutionContext,
    TransactionUnitContext,
    WorkflowContext,
)
from app.schemas.project_management import (
    ProjectManagementContextV1,
)


MODULE_NAME = (
    "app.services."
    "project_management_context_builder"
)


def module_exists() -> bool:
    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def skip_until_builder_exists() -> None:
    if not module_exists():
        pytest.skip(
            "Blocked by builder existence contract."
        )


def load_module():
    return importlib.import_module(
        MODULE_NAME
    )


def load_builder():
    module = load_module()

    builder = getattr(
        module,
        "project_management_context_builder",
        None,
    )

    if builder is not None:
        return builder

    builder_class = getattr(
        module,
        "ProjectManagementContextBuilder",
    )

    return builder_class()


def workflow(
    *,
    name: str,
    actor: str,
    action: str,
    object_: str,
) -> WorkflowContext:
    return WorkflowContext(
        name=name,
        actor=actor,
        action=action,
        object=object_,
        result="",
        output="",
        frequency="",
        is_explicit=True,
        confidence=0.95,
    )


def base_packet() -> ProjectContextPacketV3:

    return ProjectContextPacketV3(
        project_name="FlowPilot",
        description=(
            "A workflow product for operational teams."
        ),
        language="en",
        target_region="North Africa",
        industry_user_input=(
            "B2B operations software"
        ),

        sector_labels=[
            "Operations",
        ],

        # These are intentionally present in the source
        # packet but MUST NOT become planning authority.
        primary_archetype="b2b_workflow_saas",
        archetype_confidence=0.91,
        secondary_archetypes=[
            "workflow_tool",
        ],

        problem=ProblemContext(
            actors_affected=[
                "case coordinators",
            ],
            pain=(
                "Requests are coordinated manually "
                "and conflict."
            ),
            frequency="daily",
            severity="high",
            current_alternatives=[
                "email",
                "spreadsheets",
            ],
            consequences=[
                "delays",
                "coordination errors",
            ],
        ),

        solution=SolutionContext(
            mechanism=(
                "Coordinate requests in a shared "
                "workflow."
            ),
            core_value=(
                "Reduce operational conflicts."
            ),
            delivery_mode="web application",
            required_capabilities=[
                "request intake",
                "review",
            ],
            differentiators=[],
        ),

        actors=[
            ActorContext(
                name="Case coordinator",
                role=ActorRole.USER,
                description="",
                is_explicit=True,
                decision_power="low",
                buying_power="low",
            ),
            ActorContext(
                name="Team supervisor",
                role=ActorRole.OPERATOR,
                description="",
                is_explicit=True,
                decision_power="medium",
                buying_power="low",
            ),
            ActorContext(
                name="Operating company",
                role=ActorRole.PAYER,
                description="",
                is_explicit=True,
                decision_power="medium",
                buying_power="high",
            ),
            ActorContext(
                name="Operations manager",
                role=ActorRole.DECISION_MAKER,
                description="",
                is_explicit=True,
                decision_power="high",
                buying_power="high",
            ),
        ],

        payer_actor_names=[
            "Operating company",
        ],

        decision_maker_actor_names=[
            "Operations manager",
        ],

        partner_actor_names=[],
        blocker_actor_names=[],

        priority_workflows=[
            workflow(
                name="Submit request",
                actor="Case coordinator",
                action="submit",
                object_="operational request",
            ),
            workflow(
                name="Review request",
                actor="Team supervisor",
                action="review",
                object_="operational request",
            ),
        ],

        transaction_unit=TransactionUnitContext(
            name="operational request",
            description="",
            object="request",
            supply_actor="",
            demand_actor="Case coordinator",
            initiation_action="submit",
            completion_action="approve",
            value_exchanged="",
            payment_responsibility="Operating company",
            fulfillment_responsibility="Team supervisor",
            fulfillment_mode="internal workflow",
            trust_mechanism="human review",
            dispute_responsibility="",
            is_explicit=True,
            confidence=0.9,
        ),

        mvp_scope=[
            "Request intake",
            "Supervisor review",
        ],

        scope_exclusions=[
            "Automatic payment execution is excluded.",
        ],

        input_data=[
            "requested time",
            "request identifier",
        ],

        output_decision=[
            "approved request",
        ],

        human_oversight=[
            (
                "A supervisor must approve "
                "the final request."
            ),
        ],

        maintenance_model=[],

        deployment_environment=[
            "web application",
        ],

        success_metrics=[
            "reduced coordination conflicts",
        ],

        business_model_hypotheses=[
            "subscription",
        ],

        constraints=[
            (
                "The system must not expose "
                "confidential request data."
            ),
        ],

        regulatory_flags=[],

        # Unsafe positive planning hints.
        domain_terms=[
            "operations",
            "workflow",
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

        assumptions=[
            (
                "Initial rollout assumes one "
                "operating organization."
            ),
        ],

        clarification_facts={
            "payer": "Operating company",
            "decision_maker": "Operations manager",
        },

        blocking_missing_fields=[
            "validated pricing",
        ],

        validation_warnings=[
            (
                "Pricing remains an unvalidated "
                "assumption."
            ),
        ],
    )


def build(
    packet: ProjectContextPacketV3,
    *,
    project_id: str = "project-42",
) -> ProjectManagementContextV1:

    builder = load_builder()

    result = builder.build(
        packet=packet,
        project_id=project_id,
    )

    assert isinstance(
        result,
        ProjectManagementContextV1,
    )

    return result


def assert_sha256(value: str) -> None:
    assert re.fullmatch(
        r"[0-9a-f]{64}",
        value,
    ), value


def without_hashes(
    context: ProjectManagementContextV1,
):
    return context.model_dump(
        mode="json",
        exclude={
            "source_context_hash",
            "context_hash",
        },
    )


# ------------------------------------------------------------
# Existence / API
# ------------------------------------------------------------


def test_project_management_context_builder_module_exists() -> None:

    assert module_exists(), (
        "Missing deterministic Sprint 4 builder module: "
        "app.services.project_management_context_builder"
    )


def test_builder_exposes_canonical_build_api() -> None:

    skip_until_builder_exists()

    module = load_module()

    assert hasattr(
        module,
        "ProjectManagementContextBuilder",
    )

    assert hasattr(
        module,
        "project_management_context_builder",
    )

    builder = load_builder()

    signature = inspect.signature(
        builder.build
    )

    assert "packet" in signature.parameters
    assert "project_id" in signature.parameters


# ------------------------------------------------------------
# Canonical projection
# ------------------------------------------------------------


def test_builder_preserves_authoritative_project_facts() -> None:

    skip_until_builder_exists()

    packet = base_packet()

    context = build(
        packet
    )

    assert context.project_id == "project-42"
    assert context.project_name == packet.project_name
    assert context.language == packet.language
    assert context.target_region == packet.target_region

    assert (
        context.industry
        ==
        packet.industry_user_input
    )

    assert context.problem == packet.problem
    assert context.solution == packet.solution
    assert context.actors == packet.actors

    assert (
        context.payer_actor_names
        ==
        packet.payer_actor_names
    )

    assert (
        context.decision_maker_actor_names
        ==
        packet.decision_maker_actor_names
    )

    assert (
        context.priority_workflows
        ==
        packet.priority_workflows
    )

    assert (
        context.transaction_unit
        ==
        packet.transaction_unit
    )

    assert context.mvp_scope == packet.mvp_scope

    assert (
        context.scope_exclusions
        ==
        packet.scope_exclusions
    )

    assert context.input_data == packet.input_data

    assert (
        context.output_decision
        ==
        packet.output_decision
    )

    assert (
        context.human_oversight
        ==
        packet.human_oversight
    )

    assert (
        context.constraints
        ==
        packet.constraints
    )

    assert (
        context.forbidden_adjacent_domains
        ==
        packet.forbidden_adjacent_domains
    )


def test_builder_derives_primary_operational_users_from_canonical_actor_roles() -> None:

    skip_until_builder_exists()

    context = build(
        base_packet()
    )

    assert (
        context.primary_user_actor_names
        ==
        [
            "Case coordinator",
            "Team supervisor",
        ]
    )


def test_builder_maps_uncertainty_without_inventing_certainty() -> None:

    skip_until_builder_exists()

    packet = base_packet()

    context = build(
        packet
    )

    assert (
        context.assumptions
        ==
        packet.assumptions
    )

    assert (
        context.unknowns
        ==
        packet.blocking_missing_fields
    )

    assert (
        context.warnings
        ==
        packet.validation_warnings
    )

    assert (
        context.clarification_facts
        ==
        packet.clarification_facts
    )


def test_builder_does_not_fabricate_downstream_validated_outputs() -> None:

    skip_until_builder_exists()

    context = build(
        base_packet()
    )

    assert context.validated_risks == []
    assert context.validated_next_actions == []
    assert context.go_no_go_conditions == []
    assert context.canonical_verdict_code == ""


# ------------------------------------------------------------
# Deterministic provenance
# ------------------------------------------------------------


def test_builder_generates_full_sha256_hashes() -> None:

    skip_until_builder_exists()

    context = build(
        base_packet()
    )

    assert_sha256(
        context.source_context_hash
    )

    assert_sha256(
        context.context_hash
    )


def test_same_canonical_packet_produces_same_context_and_hashes() -> None:

    skip_until_builder_exists()

    packet = base_packet()

    first = build(
        packet
    )

    second = build(
        packet.model_copy(
            deep=True
        )
    )

    assert first == second

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


def test_archetype_and_query_hints_cannot_mutate_planning_context_or_hashes() -> None:

    skip_until_builder_exists()

    clean_packet = base_packet()

    noisy_packet = clean_packet.model_copy(
        deep=True,
        update={
            "primary_archetype": (
                "two_sided_marketplace"
            ),
            "archetype_confidence": 1.0,
            "secondary_archetypes": [
                "workforce_platform",
            ],
            "domain_terms": [
                "workforce",
                "recruiting",
                "marketplace",
            ],
            "use_case_terms": [
                "candidate matching",
            ],
            "solution_terms": [
                "talent marketplace",
            ],
            "target_terms": [
                "job seekers",
            ],
        },
    )

    clean_context = build(
        clean_packet
    )

    noisy_context = build(
        noisy_packet
    )

    assert (
        without_hashes(
            clean_context
        )
        ==
        without_hashes(
            noisy_context
        )
    )

    assert (
        clean_context.source_context_hash
        ==
        noisy_context.source_context_hash
    )

    assert (
        clean_context.context_hash
        ==
        noisy_context.context_hash
    )


def test_authoritative_canonical_change_changes_hashes() -> None:

    skip_until_builder_exists()

    first_packet = base_packet()

    second_packet = first_packet.model_copy(
        deep=True,
        update={
            "mvp_scope": [
                *first_packet.mvp_scope,
                "Audit history",
            ],
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
        !=
        second.source_context_hash
    )

    assert (
        first.context_hash
        !=
        second.context_hash
    )


def test_clarification_dict_insertion_order_does_not_change_hashes() -> None:

    skip_until_builder_exists()

    first_packet = base_packet()

    second_packet = first_packet.model_copy(
        deep=True,
        update={
            "clarification_facts": {
                "decision_maker": (
                    "Operations manager"
                ),
                "payer": (
                    "Operating company"
                ),
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


# ------------------------------------------------------------
# Authority boundaries
# ------------------------------------------------------------


def test_builder_api_does_not_accept_raw_analysis_or_search_authorities() -> None:

    skip_until_builder_exists()

    builder = load_builder()

    signature = inspect.signature(
        builder.build
    )

    forbidden_parameters = {
        "analysis_data",
        "project_intelligence",
        "archetype_context",
        "search_terms",
        "queries",
        "query_plan",
        "rag_context",
    }

    leaked = (
        forbidden_parameters
        &
        set(
            signature.parameters
        )
    )

    assert not leaked, (
        "Unsafe authority entered builder API: "
        + ", ".join(
            sorted(
                leaked
            )
        )
    )


def test_builder_does_not_mutate_source_packet() -> None:

    skip_until_builder_exists()

    packet = base_packet()

    before = packet.model_dump(
        mode="json"
    )

    build(
        packet
    )

    after = packet.model_dump(
        mode="json"
    )

    assert after == before


def test_meaningful_workflow_order_is_preserved() -> None:

    skip_until_builder_exists()

    packet = base_packet()

    context = build(
        packet
    )

    assert [
        item.name
        for item
        in context.priority_workflows
    ] == [
        "Submit request",
        "Review request",
    ]