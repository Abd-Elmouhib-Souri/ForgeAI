
from __future__ import annotations

import pytest

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


TECHNICAL_ACTORS = {
    "system",
    "systeme",
    "platform",
    "plateforme",
    "application",
    "software",
    "logiciel",
}


def extract(
    description: str,
    *,
    language: str = "fr",
):
    return project_context_extractor.extract(
        title="UniversalActorMembershipContract",
        description=description,
        industry="Marketplace B2B",
        target_region=(
            "Tunisie"
            if language == "fr"
            else "United Kingdom"
        ),
        output_language=language,
    )


def actor_roles(packet):
    return {
        (
            comparison_key(
                actor.name
            ),
            actor.role.value,
        )
        for actor in packet.actors
    }


def canonical_actor_keys(packet):
    return {
        comparison_key(
            actor.name
        )
        for actor in packet.actors
    }


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected_actor",
    ),
    [
        (
            "fr",
            (
                "Le responsable maintenance "
                "publie une demande d'intervention."
            ),
            "responsable maintenance",
        ),
        (
            "en",
            (
                "The maintenance manager "
                "submits a service request."
            ),
            "maintenance manager",
        ),
    ],
)
def test_explicit_request_initiator_is_canonical_operational_user(
    language: str,
    description: str,
    expected_actor: str,
) -> None:
    packet = extract(
        description,
        language=language,
    )

    assert (
        comparison_key(
            expected_actor
        ),
        "user",
    ) in actor_roles(
        packet
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in packet.actors
    ]


def test_nontechnical_workflow_owners_are_canonical_actors() -> None:
    packet = extract(
        (
            "Le responsable maintenance publie une demande. "
            "Les techniciens qualifies sont les prestataires. "
            "Les prestataires proposent une intervention. "
            "L'entreprise cliente compare les propositions "
            "et choisit un prestataire. "
            "La PME cliente paie l'intervention."
        )
    )

    canonical = canonical_actor_keys(
        packet
    )

    unresolved = [
        workflow.actor
        for workflow
        in packet.priority_workflows
        if (
            workflow.actor
            and comparison_key(
                workflow.actor
            )
            not in canonical
            and comparison_key(
                workflow.actor
            )
            not in TECHNICAL_ACTORS
        )
    ]

    assert unresolved == [], {
        "actors": [
            actor.model_dump(
                mode="json"
            )
            for actor in packet.actors
        ],
        "workflows": [
            workflow.model_dump(
                mode="json"
            )
            for workflow
            in packet.priority_workflows
        ],
        "unresolved":
            unresolved,
    }


def test_marketplace_transaction_projects_explicit_demand_side() -> None:
    packet = extract(
        (
            "Le responsable maintenance publie "
            "une demande d'intervention. "
            "Les prestataires proposent une intervention. "
            "Le prestataire realise l'intervention. "
            "La PME cliente paie l'intervention."
        )
    )

    transaction = packet.transaction_unit

    assert transaction.supply_actor, (
        transaction.model_dump(
            mode="json"
        )
    )

    assert transaction.demand_actor, (
        transaction.model_dump(
            mode="json"
        )
    )

    assert transaction.has_two_sides is True, (
        transaction.model_dump(
            mode="json"
        )
    )


def test_actor_membership_does_not_destroy_explicit_payer_authority() -> None:
    packet = extract(
        (
            "Le responsable maintenance publie "
            "une demande d'intervention. "
            "L'entreprise cliente est le payeur. "
            "L'entreprise cliente paie l'intervention."
        )
    )

    payer_keys = {
        comparison_key(
            name
        )
        for name
        in packet.payer_actor_names
    }

    assert (
        "entreprise cliente"
        in payer_keys
    )

    assert (
        "responsable maintenance"
        not in payer_keys
    )
