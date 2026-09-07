from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _packet(
    description: str,
):
    return (
        ProjectContextExtractor()
        .extract(
            title="Neutral Actor Coexistence",
            description=description,
            industry="software",
            target_region="Global",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )


def _actor_names(
    packet,
):
    return [
        actor.name
        for actor
        in packet.actors
    ]


def _actor_pairs(
    packet,
):
    return [
        (
            actor.name,
            actor.role,
        )
        for actor
        in packet.actors
    ]


BASE_DESCRIPTION = (
    "Primary operational users:\n"
    "- operations coordinator\n"
    "- inventory manager\n"
    "External users:\n"
    "- business buyer\n"
    "- delivery partner\n"
    "Paying customer:\n"
    "- operating organization\n"
    "MVP capabilities:\n"
    "- function alpha"
)


ONE_DECISION_DESCRIPTION = (
    "Primary operational users:\n"
    "- operations coordinator\n"
    "- inventory manager\n"
    "External users:\n"
    "- business buyer\n"
    "- delivery partner\n"
    "Paying customer:\n"
    "- operating organization\n"
    "Decision makers:\n"
    "- organization owner\n"
    "MVP capabilities:\n"
    "- function alpha"
)


TWO_DECISION_DESCRIPTION = (
    "Primary operational users:\n"
    "- operations coordinator\n"
    "- inventory manager\n"
    "External users:\n"
    "- business buyer\n"
    "- delivery partner\n"
    "Paying customer:\n"
    "- operating organization\n"
    "Decision makers:\n"
    "- organization owner\n"
    "- operations manager\n"
    "MVP capabilities:\n"
    "- function alpha"
)


def test_adding_decision_relation_preserves_unrelated_partner() -> None:
    base = _packet(
        BASE_DESCRIPTION
    )

    variant = _packet(
        ONE_DECISION_DESCRIPTION
    )

    assert base.partner_actor_names == [
        "delivery partner",
    ]

    assert variant.partner_actor_names == [
        "delivery partner",
    ]


def test_adding_multiple_decision_relations_preserves_unrelated_partner() -> None:
    packet = _packet(
        TWO_DECISION_DESCRIPTION
    )

    assert packet.partner_actor_names == [
        "delivery partner",
    ]


def test_decision_authority_coexists_with_structured_actor_population() -> None:
    packet = _packet(
        TWO_DECISION_DESCRIPTION
    )

    actor_names = set(
        _actor_names(
            packet
        )
    )

    assert {
        "operations coordinator",
        "inventory manager",
        "business buyer",
        "delivery partner",
        "organization owner",
        "operations manager",
    }.issubset(
        actor_names
    )


def test_decision_relations_remain_authoritative_after_actor_coexistence() -> None:
    packet = _packet(
        TWO_DECISION_DESCRIPTION
    )

    assert packet.decision_maker_actor_names == [
        "organization owner",
        "operations manager",
    ]

    assert (
        (
            "organization owner",
            ActorRole.DECISION_MAKER,
        )
        in _actor_pairs(
            packet
        )
    )

    assert (
        (
            "operations manager",
            ActorRole.DECISION_MAKER,
        )
        in _actor_pairs(
            packet
        )
    )


def test_structured_partner_surface_does_not_leak_bullet_marker() -> None:
    packet = _packet(
        ONE_DECISION_DESCRIPTION
    )

    assert "- delivery partner" not in _actor_names(
        packet
    )

    assert "delivery partner" in _actor_names(
        packet
    )


def test_payer_authority_is_independent_of_actor_population_merge() -> None:
    packet = _packet(
        TWO_DECISION_DESCRIPTION
    )

    assert "operating organization" in (
        packet.payer_actor_names
    )