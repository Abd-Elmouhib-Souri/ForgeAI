from __future__ import annotations

import importlib
import inspect
import re

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
    TransactionUnitContext,
    WorkflowContext,
)

from app.schemas.solution_architecture import (
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
)


MODULE_NAME = (
    "app.services."
    "solution_architecture_context_builder"
)


# =============================================================================
# CANONICAL FIXTURE
# =============================================================================

def packet() -> ProjectContextPacketV3:
    """
    Neutral cross-domain packet.

    The values intentionally describe operational relationships rather than
    a specific country, sector or ForgeAI fixture.
    """

    base = ProjectContextPacketV3(
        project_name=(
            "Universal Architecture Context"
        ),
        description=(
            "A neutral operational system coordinates "
            "requests between participants."
        ),
        language="en",
        target_region="International",
        industry_user_input=(
            "Operational information system"
        ),
    )

    operator = ActorContext(
        name="Operational User",
        role=ActorRole.USER,
        description=(
            "Uses the system during the "
            "core operational workflow."
        ),
        is_explicit=True,
        is_generic=False,
    )

    provider = ActorContext(
        name="Service Provider",
        role=ActorRole.PROVIDER,
        description=(
            "Performs the operational service."
        ),
        is_explicit=True,
        is_generic=False,
    )

    workflow = WorkflowContext(
        name="Review request",
        actor="Operational User",
        action="review",
        object="request",
        result="reviewed request",
        output="review decision",
        frequency="daily",
        is_explicit=True,
        confidence=0.95,
    )

    transaction = TransactionUnitContext(
        name="Service Request",
        description=(
            "Primary operational unit exchanged "
            "between project participants."
        ),
        supply_actor="Service Provider",
        demand_actor="Operational User",
    )

    return base.model_copy(
        deep=True,
        update={
            "actors": [
                operator,
                provider,
            ],
            "priority_workflows": [
                workflow,
            ],
            "transaction_unit":
                transaction,
            "mvp_scope": [
                "Capture service requests",
                "Review service requests",
            ],
            "scope_exclusions": [
                (
                    "Automatic legally binding "
                    "final approval is excluded."
                ),
            ],
            "input_data": [
                "request information",
            ],
            "output_decision": [
                "review decision",
            ],
            "human_oversight": [
                (
                    "A human validates the "
                    "final decision."
                ),
            ],
            "maintenance_model": [
                (
                    "The operating organization "
                    "maintains the service."
                ),
            ],
            "deployment_environment": [
                "managed deployment environment",
            ],
            "constraints": [
                (
                    "Sensitive project information "
                    "must remain protected."
                ),
            ],
            "regulatory_flags": [
                "applicable privacy requirements",
            ],
            "assumptions": [
                (
                    "The initial rollout serves "
                    "one organization."
                ),
            ],
            "forbidden_adjacent_domains": [
                "unrelated marketplace",
            ],

            # Advisory/non-authoritative hints deliberately
            # present so contracts can prove they do not
            # silently become architecture truth.
            "primary_archetype":
                "generic_advisory_archetype",

            "secondary_archetypes": [
                "secondary_hint",
            ],

            "domain_terms": [
                "advisory domain term",
            ],

            "use_case_terms": [
                "advisory use case term",
            ],

            "solution_terms": [
                "advisory solution term",
            ],

            "target_terms": [
                "advisory target term",
            ],
        },
    )


def load_module():
    return importlib.import_module(
        MODULE_NAME
    )


def load_builder():
    module = load_module()

    return (
        module
        .solution_architecture_context_builder
    )


def build(
    source: ProjectContextPacketV3,
) -> SolutionArchitectureContextV1:
    return load_builder().build(
        packet=source
    )


def without_fingerprint(
    value: SolutionArchitectureContextV1,
) -> dict:
    return value.model_dump(
        mode="json",
        exclude={
            "upstream_context_fingerprint",
        },
    )


# =============================================================================
# GREEN CONTROLS
# =============================================================================

def test_control_project_context_packet_exposes_architecture_authorities():
    required = {
        "project_name",
        "language",
        "target_region",
        "industry_user_input",
        "actors",
        "priority_workflows",
        "transaction_unit",
        "mvp_scope",
        "scope_exclusions",
        "input_data",
        "output_decision",
        "human_oversight",
        "maintenance_model",
        "deployment_environment",
        "constraints",
        "regulatory_flags",
        "assumptions",
        "forbidden_adjacent_domains",
    }

    fields = set(
        ProjectContextPacketV3
        .model_fields
        .keys()
    )

    assert required <= fields


def test_control_solution_architecture_context_schema_is_builder_ready():
    required = {
        "project_name",
        "language",
        "sector",
        "target_region",
        "target_users",
        "actors",
        "priority_workflows",
        "transaction_unit",
        "positive_mvp_scope",
        "explicit_exclusions",
        "input_data",
        "output_decision",
        "human_oversight",
        "maintenance_model",
        "assumptions",
        "forbidden_adjacent_domains",
        "constraints",
        "technical_signals",
        "upstream_context_fingerprint",
    }

    fields = set(
        SolutionArchitectureContextV1
        .model_fields
        .keys()
    )

    assert required <= fields


def test_control_contract_fixture_is_valid_and_structured():
    source = packet()

    assert isinstance(
        source,
        ProjectContextPacketV3,
    )

    assert len(
        source.actors
    ) == 2

    assert (
        source.actors[0].role
        ==
        ActorRole.USER
    )

    assert len(
        source.priority_workflows
    ) == 1

    assert (
        source.priority_workflows[0].action
        ==
        "review"
    )

    assert (
        source.transaction_unit.name
        ==
        "Service Request"
    )


# =============================================================================
# PRODUCT CONTRACTS
# =============================================================================

def test_solution_architecture_context_builder_module_and_api_exist():
    builder = load_builder()

    assert builder is not None

    signature = inspect.signature(
        builder.build
    )

    parameters = set(
        signature.parameters
    )

    assert "packet" in parameters

    forbidden_parameters = {
        "analysis_data",
        "project_intelligence",
        "archetype_context",
        "search_terms",
        "queries",
        "query_plan",
        "rag_context",
        "startup_score",
        "renderer",
        "kroki",
        "svg",
    }

    assert not (
        parameters
        &
        forbidden_parameters
    )


def test_builder_preserves_canonical_scalar_facts_and_type():
    source = packet()

    context = build(
        source
    )

    assert isinstance(
        context,
        SolutionArchitectureContextV1,
    )

    assert (
        context.schema_version
        ==
        "solution_architecture_context_v1"
    )

    assert (
        context.project_name
        ==
        source.project_name
    )

    assert (
        context.language
        ==
        source.language
    )

    assert (
        context.target_region
        ==
        source.target_region
    )

    assert (
        context.sector
        ==
        source.industry_user_input
    )

    assert (
        context.target_users
        ==
        [
            "Operational User"
        ]
    )


def test_builder_preserves_structured_actor_workflow_transaction_relations():
    source = packet()

    context = build(
        source
    )

    assert [
        (
            actor.name,
            actor.role,
            actor.is_explicit,
            actor.is_generic,
        )
        for actor in context.actors
    ] == [
        (
            actor.name,
            actor.role.value,
            actor.is_explicit,
            actor.is_generic,
        )
        for actor in source.actors
    ]

    assert len(
        context.priority_workflows
    ) == 1

    projected = (
        context
        .priority_workflows[0]
    )

    canonical = (
        source
        .priority_workflows[0]
    )

    assert projected.name == canonical.name
    assert projected.actor == canonical.actor
    assert projected.action == canonical.action
    assert projected.object == canonical.object
    assert projected.result == canonical.result
    assert projected.output == canonical.output
    assert projected.frequency == canonical.frequency
    assert projected.is_explicit == canonical.is_explicit
    assert projected.confidence == canonical.confidence

    assert context.transaction_unit is not None

    assert (
        context.transaction_unit.name
        ==
        source.transaction_unit.name
    )

    assert (
        context.transaction_unit.supply_actor
        ==
        source.transaction_unit.supply_actor
    )

    assert (
        context.transaction_unit.demand_actor
        ==
        source.transaction_unit.demand_actor
    )


def test_builder_preserves_scope_and_operational_authorities():
    source = packet()

    context = build(
        source
    )

    assert (
        context.positive_mvp_scope
        ==
        source.mvp_scope
    )

    assert (
        context.explicit_exclusions
        ==
        source.scope_exclusions
    )

    assert (
        context.input_data
        ==
        source.input_data
    )

    assert (
        context.output_decision
        ==
        source.output_decision
    )

    assert (
        context.human_oversight
        ==
        source.human_oversight
    )

    assert (
        context.maintenance_model
        ==
        source.maintenance_model
    )

    assert (
        context.assumptions
        ==
        source.assumptions
    )

    assert (
        context.forbidden_adjacent_domains
        ==
        source.forbidden_adjacent_domains
    )

    assert (
        context.constraints
        ==
        source.constraints
    )


def test_builder_projects_direct_signals_without_fabricating_unknowns():
    source = packet()

    context = build(
        source
    )

    signals = (
        context
        .technical_signals
    )

    assert isinstance(
        signals,
        TechnicalSignalsV1,
    )

    assert (
        signals.regulatory_context
        ==
        source.regulatory_flags
    )

    assert (
        signals.deployment_constraints
        ==
        source.deployment_environment
    )

    # No canonical evidence currently exists for these values
    # in the neutral fixture, therefore unknown must remain unknown.
    assert signals.realtime_required is None
    assert signals.offline_required is None
    assert signals.hardware_dependency is None
    assert signals.team_size is None
    assert signals.expected_scale is None
    assert signals.availability_requirement is None
    assert signals.budget_constraint is None
    assert signals.time_to_market is None
    assert signals.ai_workload is None

    assert (
        signals.client_surfaces
        ==
        []
    )


def test_builder_is_deterministic_and_emits_sha256_fingerprint():
    source = packet()

    first = build(
        source
    )

    second = build(
        source
    )

    assert (
        first
        ==
        second
    )

    assert re.fullmatch(
        r"[0-9a-f]{64}",
        first
        .upstream_context_fingerprint
        .lower(),
    )


def test_authoritative_change_changes_architecture_context_fingerprint():
    first_source = packet()

    second_source = (
        first_source
        .model_copy(
            deep=True,
            update={
                "mvp_scope": [
                    *first_source.mvp_scope,
                    "Maintain audit history",
                ],
            },
        )
    )

    first = build(
        first_source
    )

    second = build(
        second_source
    )

    assert (
        first.positive_mvp_scope
        !=
        second.positive_mvp_scope
    )

    assert (
        first.upstream_context_fingerprint
        !=
        second.upstream_context_fingerprint
    )


def test_non_authoritative_hints_do_not_mutate_context_or_source_packet():
    source = packet()

    source_before = source.model_dump(
        mode="json"
    )

    noisy = source.model_copy(
        deep=True,
        update={
            "primary_archetype":
                "completely_different_hint",

            "secondary_archetypes": [
                "another_hint",
            ],

            "domain_terms": [
                "different advisory domain term",
            ],

            "use_case_terms": [
                "different advisory use case term",
            ],

            "solution_terms": [
                "different advisory solution term",
            ],

            "target_terms": [
                "different advisory target term",
            ],
        },
    )

    clean_context = build(
        source
    )

    noisy_context = build(
        noisy
    )

    assert (
        without_fingerprint(
            clean_context
        )
        ==
        without_fingerprint(
            noisy_context
        )
    )

    assert (
        clean_context
        .upstream_context_fingerprint
        ==
        noisy_context
        .upstream_context_fingerprint
    )

    assert (
        source.model_dump(
            mode="json"
        )
        ==
        source_before
    )
