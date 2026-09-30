from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import solution_architecture as sa


# =============================================================================
# CONTROLS ? EXISTING S5-B MUST REMAIN GREEN
# =============================================================================

def test_control_existing_context_contract_is_available():
    assert (
        sa.SolutionArchitectureContextV1
        is not None
    )


def test_control_existing_technical_signal_contract_is_available():
    assert (
        sa.TechnicalSignalsV1
        is not None
    )


# =============================================================================
# NEW UNIVERSAL CONTEXT COVERAGE CONTRACT
# =============================================================================

def test_context_has_structured_actor_contract():
    actor = sa.ArchitectureActorV1(
        name="Operational User",
        role="user",
        description="Uses the system operationally.",
        is_explicit=True,
        is_generic=False,
    )

    assert actor.name == "Operational User"
    assert actor.role == "user"
    assert actor.is_explicit is True
    assert actor.is_generic is False


def test_context_has_structured_workflow_contract():
    workflow = sa.ArchitectureWorkflowV1(
        name="Review request",
        actor="Operational User",
        action="review",
        object="request",
        result="approved request",
        output="decision",
        frequency="daily",
        is_explicit=True,
        confidence=0.91,
    )

    assert workflow.actor == "Operational User"
    assert workflow.action == "review"
    assert workflow.object == "request"
    assert workflow.confidence == 0.91

    with pytest.raises(
        ValidationError
    ):
        sa.ArchitectureWorkflowV1(
            name="Invalid",
            actor="",
            action="review",
            object="request",
            result="",
            output="",
            frequency="",
            is_explicit=False,
            confidence=1.5,
        )


def test_context_has_structured_transaction_contract():
    transaction = (
        sa.ArchitectureTransactionUnitV1(
            name="Service Request",
            description=(
                "A request exchanged between "
                "a requester and a provider."
            ),
            supply_actor="Provider",
            demand_actor="Requester",
        )
    )

    assert (
        transaction.supply_actor
        ==
        "Provider"
    )

    assert (
        transaction.demand_actor
        ==
        "Requester"
    )


def test_solution_architecture_context_preserves_operational_authorities():
    actor = sa.ArchitectureActorV1(
        name="Operator",
        role="user",
        description="Daily operational user.",
        is_explicit=True,
        is_generic=False,
    )

    workflow = sa.ArchitectureWorkflowV1(
        name="Review case",
        actor="Operator",
        action="review",
        object="case",
        result="reviewed case",
        output="decision",
        frequency="daily",
        is_explicit=True,
        confidence=0.95,
    )

    transaction = (
        sa.ArchitectureTransactionUnitV1(
            name="Case",
            description="Primary project transaction.",
            supply_actor="Service Provider",
            demand_actor="Customer",
        )
    )

    context = sa.SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name="Neutral Project",
        sector="Neutral Domain",
        target_region="International",
        target_users=[
            "Operator"
        ],
        actors=[
            actor
        ],
        priority_workflows=[
            workflow
        ],
        transaction_unit=transaction,
        positive_mvp_scope=[
            "Review cases"
        ],
        explicit_exclusions=[
            "Automatic final approval"
        ],
        input_data=[
            "case information"
        ],
        output_decision=[
            "review decision"
        ],
        human_oversight=[
            "A human validates final approval."
        ],
        maintenance_model=[
            "Internal operations team maintains the service."
        ],
        assumptions=[
            "Initial rollout serves one organization."
        ],
        forbidden_adjacent_domains=[
            "unrelated marketplace"
        ],
        constraints=[
            "Sensitive data must remain protected."
        ],
        technical_signals=(
            sa.TechnicalSignalsV1(
                regulatory_context=[
                    "applicable privacy requirements"
                ],
                deployment_constraints=[
                    "managed deployment environment"
                ],
            )
        ),
        upstream_context_fingerprint=(
            "context-fingerprint"
        ),
    )

    assert (
        context.actors[0].role
        ==
        "user"
    )

    assert (
        context.priority_workflows[0].action
        ==
        "review"
    )

    assert (
        context.transaction_unit.name
        ==
        "Case"
    )

    assert (
        context.input_data
        ==
        [
            "case information"
        ]
    )

    assert (
        context.output_decision
        ==
        [
            "review decision"
        ]
    )

    assert (
        context.human_oversight
        ==
        [
            "A human validates final approval."
        ]
    )

    assert (
        context.maintenance_model
        ==
        [
            "Internal operations team maintains the service."
        ]
    )

    assert (
        context.assumptions
        ==
        [
            "Initial rollout serves one organization."
        ]
    )

    assert (
        context.forbidden_adjacent_domains
        ==
        [
            "unrelated marketplace"
        ]
    )


def test_context_coverage_does_not_require_raw_analysis_or_runtime_metadata():
    forbidden = {
        "analysis_data",
        "project_intelligence",
        "query_plan",
        "search_terms",
        "rag_context",
        "startup_score",
        "created_at",
        "generated_at",
        "provider",
        "renderer_status",
        "svg",
    }

    fields = set(
        sa.SolutionArchitectureContextV1
        .model_fields
        .keys()
    )

    assert not (
        fields
        &
        forbidden
    )
