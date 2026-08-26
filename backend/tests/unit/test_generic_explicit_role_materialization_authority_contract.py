from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    project_context_extractor,
)


def _packet(
    description: str,
):
    return project_context_extractor.extract(
        title="Generic Explicit Role Authority Probe",
        description=description,
        industry="Generic Operations",
        target_region="Europe",
        output_language="en",
    )


def _actors_for_role(
    description: str,
    role: ActorRole,
):
    return [
        actor
        for actor in _packet(
            description
        ).actors
        if actor.role == role
    ]


def test_generic_customer_explicit_payer_is_materialized() -> None:
    actors = _actors_for_role(
        "The customer pays the fee.",
        ActorRole.PAYER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "customer",
    ]

    assert actors[0].is_explicit is True
    assert actors[0].is_generic is True


def test_generic_customer_then_explicit_payer_is_materialized() -> None:
    actors = _actors_for_role(
        (
            "The customer then pays "
            "for the completed service."
        ),
        ActorRole.PAYER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "customer",
    ]


def test_generic_user_explicit_payer_is_materialized() -> None:
    actors = _actors_for_role(
        "The user pays a monthly subscription.",
        ActorRole.PAYER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "user",
    ]

    assert actors[0].is_generic is True


def test_generic_french_client_explicit_payer_is_materialized() -> None:
    actors = _actors_for_role(
        "Le client paie les frais.",
        ActorRole.PAYER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "client",
    ]

    assert actors[0].is_generic is True


def test_generic_customer_explicit_decision_maker_is_materialized() -> None:
    actors = _actors_for_role(
        (
            "The customer is the primary "
            "decision maker."
        ),
        ActorRole.DECISION_MAKER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "customer",
    ]

    assert actors[0].is_explicit is True
    assert actors[0].is_generic is True


def test_qualified_explicit_payer_remains_unchanged() -> None:
    actors = _actors_for_role(
        (
            "The client company pays "
            "for the completed service."
        ),
        ActorRole.PAYER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "client company",
    ]

    assert actors[0].is_generic is False


def test_qualified_french_explicit_payer_remains_unchanged() -> None:
    actors = _actors_for_role(
        (
            "L'entreprise cliente paie "
            "le service."
        ),
        ActorRole.PAYER,
    )

    assert [
        actor.name.lower()
        for actor in actors
    ] == [
        "entreprise cliente",
    ]

    assert actors[0].is_generic is False


def test_generic_coordinated_client_payer_reaches_final_packet() -> None:
    packet = _packet(
        (
            "Le client reserve un service "
            "et paie la facture."
        )
    )

    payers = [
        actor.name.lower()
        for actor in packet.actors
        if actor.role == ActorRole.PAYER
    ]

    assert payers == [
        "client",
    ]

    assert [
        workflow.actor.lower()
        for workflow in packet.priority_workflows
    ] == [
        "client",
        "client",
    ]


def test_generic_identity_does_not_override_pronoun_safety() -> None:
    actors = _actors_for_role(
        "It pays the fee.",
        ActorRole.PAYER,
    )

    assert actors == []


def test_same_generic_actor_can_preserve_two_explicit_roles() -> None:
    packet = _packet(
        (
            "The customer pays the fee. "
            "The customer is the primary "
            "decision maker."
        )
    )

    customer_roles = {
        actor.role
        for actor in packet.actors
        if actor.name.lower() == "customer"
    }

    assert ActorRole.PAYER in customer_roles
    assert ActorRole.DECISION_MAKER in customer_roles
