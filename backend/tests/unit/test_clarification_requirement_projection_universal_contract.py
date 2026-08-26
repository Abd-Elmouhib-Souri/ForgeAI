from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from app.schemas.analysis_context import (
    ProjectContextPacketV3,
)
from app.services.context_confidence_gate import (
    ContextConfidenceGate,
)


EXPECTED_REQUIREMENTS = {
    "audience_side",
    "beneficiary",
    "business_model",
    "creator_side",
    "decision_maker",
    "deliverable",
    "demand_side",
    "deployment_environment",
    "dispute_responsibility",
    "fulfillment_logistics",
    "human_oversight",
    "input_data",
    "maintenance_model",
    "moderation_model",
    "operational_safety",
    "operational_user",
    "output_decision",
    "payer",
    "payment_responsibility",
    "priority_workflow",
    "professional_responsibility",
    "regulated_provider",
    "regulatory_scope",
    "return_refund_policy",
    "service_client",
    "service_provider",
    "supply_side",
    "target_region",
    "transaction_flow",
    "transaction_unit",
    "trust_mechanism",
}


PROJECTOR_PATH = (
    Path("/app")
    / "app/services/"
    "clarification_answer_projector.py"
)


def _requirement_union() -> set[str]:
    gate = ContextConfidenceGate()

    return {
        str(field)
        for mapping in (
            gate.ARCHETYPE_BLOCKING_REQUIREMENTS,
            gate.ARCHETYPE_AMBIGUOUS_REQUIREMENTS,
        )
        for fields in mapping.values()
        for field in fields
    }


def _projector():
    assert PROJECTOR_PATH.exists(), (
        "A dedicated universal clarification projector "
        "must own answer -> canonical packet projection."
    )

    module = importlib.import_module(
        "app.services."
        "clarification_answer_projector"
    )

    projector = getattr(
        module,
        "clarification_answer_projector",
        None,
    )

    assert projector is not None

    assert callable(
        getattr(
            projector,
            "apply",
            None,
        )
    )

    return projector


def _empty_packet() -> ProjectContextPacketV3:
    return ProjectContextPacketV3(
        project_name="Universal clarification probe",
        description=(
            "The original project description."
        ),
        language="en",
    )


def test_contract_covers_complete_current_gate_vocabulary():
    """
    If the gate gains a new archetype requirement, this contract must
    consciously evolve with it.
    """
    current = _requirement_union()

    assert current == EXPECTED_REQUIREMENTS

    assert len(current) == 31


def test_packet_has_dedicated_explicit_clarification_fact_channel():
    """
    Explicit answers are facts supplied by the user.

    They must not be hidden in description, assumptions or constraints.
    """
    assert (
        "clarification_facts"
        in ProjectContextPacketV3.model_fields
    )


def test_dedicated_universal_projector_exists():
    _projector()


@pytest.mark.parametrize(
    "requirement",
    sorted(EXPECTED_REQUIREMENTS),
)
def test_every_archetype_requirement_preserves_field_bound_explicit_fact(
    requirement: str,
):
    """
    Every requirement supported by ContextConfidenceGate has a generic
    field-bound explicit-fact channel.

    No sector-specific parser is required merely to preserve an answer.
    """
    projector = _projector()

    value = (
        "Explicit user clarification for "
        f"{requirement}."
    )

    packet = projector.apply(
        _empty_packet(),
        {
            requirement: value,
        },
    )

    assert (
        packet.clarification_facts[
            requirement
        ]
        == value
    )


@pytest.mark.parametrize(
    "requirement",
    sorted(EXPECTED_REQUIREMENTS),
)
def test_every_gate_requirement_can_be_resolved_by_its_explicit_user_fact(
    requirement: str,
):
    """
    A non-empty, resolved answer attached to the exact canonical field
    is higher authority than lexical inference.

    The gate must not require the user to repeat one of its internal
    marker words.
    """
    projector = _projector()

    value = (
        "The user explicitly supplied "
        f"the required {requirement} information."
    )

    packet = projector.apply(
        _empty_packet(),
        {
            requirement: value,
        },
    )

    gate = ContextConfidenceGate()

    assert gate._requirement_is_present(
        packet,
        requirement,
    )


@pytest.mark.parametrize(
    (
        "requirement",
        "answer",
    ),
    [
        (
            "human_oversight",
            "Not defined yet.",
        ),
        (
            "transaction_flow",
            "\u00c0 d\u00e9finir.",
        ),
        (
            "target_region",
            "Unknown.",
        ),
        (
            "payment_responsibility",
            "To be decided.",
        ),
    ],
)
def test_unresolved_explicit_answer_never_satisfies_gate(
    requirement: str,
    answer: str,
):
    """
    Field identity does not turn an unresolved statement into knowledge.
    """
    projector = _projector()

    packet = projector.apply(
        _empty_packet(),
        {
            requirement: answer,
        },
    )

    gate = ContextConfidenceGate()

    assert not gate._requirement_is_present(
        packet,
        requirement,
    )


def test_core_answers_project_to_real_canonical_structures():
    """
    Where ProjectContextPacketV3 already owns a precise structural field,
    clarification must update that structure as well as preserve the fact.
    """
    projector = _projector()

    packet = projector.apply(
        _empty_packet(),
        {
            "target_region":
                "France",

            "problem":
                (
                    "Teams lose time because "
                    "handoffs are fragmented."
                ),

            "solution":
                (
                    "A shared workflow coordinates "
                    "the handoff."
                ),

            "business_model":
                "Subscription per operational team",

            "deployment_environment":
                "Factory floor",

            "regulatory_scope":
                "French workplace regulation",

            "transaction_unit":
                "One completed equipment rental",

            "payment_responsibility":
                "The purchasing company pays",

            "trust_mechanism":
                "Verified provider identity",

            "dispute_responsibility":
                "Platform support handles disputes",

            "fulfillment_logistics":
                "Provider delivers and retrieves equipment",
        },
    )

    assert packet.target_region == "France"

    assert (
        packet.problem.pain
        == (
            "Teams lose time because "
            "handoffs are fragmented."
        )
    )

    assert (
        packet.solution.mechanism
        == (
            "A shared workflow coordinates "
            "the handoff."
        )
    )

    assert (
        "Subscription per operational team"
        in packet.business_model_hypotheses
    )

    assert (
        "Factory floor"
        in packet.deployment_environment
    )

    assert (
        "French workplace regulation"
        in packet.regulatory_flags
    )

    assert (
        packet.transaction_unit.payment_responsibility
        == "The purchasing company pays"
    )

    assert (
        packet.transaction_unit.trust_mechanism
        == "Verified provider identity"
    )

    assert (
        packet.transaction_unit.dispute_responsibility
        == "Platform support handles disputes"
    )

    assert (
        "Provider delivers and retrieves equipment"
        in {
            packet.transaction_unit.fulfillment_mode,
            packet.transaction_unit.fulfillment_responsibility,
            packet.transaction_unit.description,
        }
    )

    assert (
        "One completed equipment rental"
        in {
            packet.transaction_unit.name,
            packet.transaction_unit.object,
            packet.transaction_unit.description,
        }
    )


def test_actor_requirement_answers_materialize_canonical_actor_authority():
    """
    Actor clarifications must not remain generic text only when a canonical
    actor surface already exists.
    """
    projector = _projector()

    packet = projector.apply(
        _empty_packet(),
        {
            "supply_side":
                "equipment owners",

            "demand_side":
                "industrial SMEs",

            "operational_user":
                "shift supervisors",

            "decision_maker":
                "operations director",

            "payer":
                "purchasing department",

            "service_provider":
                "certified technicians",

            "service_client":
                "factory managers",

            "beneficiary":
                "production teams",
        },
    )

    actor_names = {
        actor.name
        for actor in packet.actors
    }

    for expected in {
        "equipment owners",
        "industrial SMEs",
        "shift supervisors",
        "operations director",
        "purchasing department",
        "certified technicians",
        "factory managers",
        "production teams",
    }:
        assert expected in actor_names

    assert (
        packet.transaction_unit.supply_actor
        == "equipment owners"
    )

    assert (
        packet.transaction_unit.demand_actor
        == "industrial SMEs"
    )

    assert (
        "operations director"
        in packet.decision_maker_actor_names
    )

    assert (
        "purchasing department"
        in packet.payer_actor_names
    )


def test_original_project_description_is_never_rewritten():
    projector = _projector()

    packet = _empty_packet()

    original = packet.description

    projected = projector.apply(
        packet,
        {
            "problem":
                "Explicit clarified problem.",

            "solution":
                "Explicit clarified solution.",

            "human_oversight":
                "A qualified reviewer validates every output.",
        },
    )

    assert projected.description == original


def test_clarification_facts_survive_packet_serialization_and_legacy_projection():
    """
    Generic facts must remain available to downstream consumers even when
    there is no dedicated structural field for that requirement.
    """
    projector = _projector()

    packet = projector.apply(
        _empty_packet(),
        {
            "human_oversight":
                (
                    "A qualified reviewer validates "
                    "every recommendation."
                ),

            "moderation_model":
                (
                    "Community reports are reviewed "
                    "by trained moderators."
                ),
        },
    )

    dumped = packet.model_dump(
        mode="json"
    )

    assert (
        dumped["clarification_facts"][
            "human_oversight"
        ]
        == (
            "A qualified reviewer validates "
            "every recommendation."
        )
    )

    legacy = packet.to_legacy_dict()

    assert (
        legacy["clarification_facts"][
            "moderation_model"
        ]
        == (
            "Community reports are reviewed "
            "by trained moderators."
        )
    )

def test_real_unicode_french_unresolved_answer_remains_unresolved():
    projector = _projector()

    answer = "\u00c0 d\u00e9finir."

    packet = projector.apply(
        _empty_packet(),
        {
            "human_oversight":
                answer,
        },
    )

    assert (
        packet.clarification_facts[
            "human_oversight"
        ]
        == answer
    )

    gate = ContextConfidenceGate()

    assert not gate._requirement_is_present(
        packet,
        "human_oversight",
    )
