
from __future__ import annotations

import pytest

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def extract(
    description: str,
    *,
    language: str = "fr",
):
    return project_context_extractor.extract(
        title="UniversalActorRelationContract",
        description=description,
        industry="B2B software",
        target_region=(
            "Tunisie"
            if language == "fr"
            else "United Kingdom"
        ),
        output_language=language,
    )


def actor_rows(packet):
    return {
        (
            comparison_key(
                actor.name
            ),
            actor.role.value,
        )
        for actor in packet.actors
    }


def assert_actor_role(
    packet,
    name: str,
    role: str,
):
    expected = (
        comparison_key(
            name
        ),
        role,
    )

    assert expected in actor_rows(
        packet
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in packet.actors
    ]


def test_french_plural_operational_users_are_explicit_users():
    packet = extract(
        (
            "Les operateurs de production sont "
            "les utilisateurs operationnels."
        )
    )

    assert_actor_role(
        packet,
        "operateurs de production",
        "user",
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected_name",
    ),
    [
        (
            "fr",
            (
                "Le decideur principal est "
                "le gerant du magasin."
            ),
            "gerant du magasin",
        ),
        (
            "en",
            (
                "The primary decision maker is "
                "the store manager."
            ),
            "store manager",
        ),
    ],
)
def test_label_first_decision_maker_relation_is_canonical(
    language: str,
    description: str,
    expected_name: str,
):
    packet = extract(
        description,
        language=language,
    )

    assert_actor_role(
        packet,
        expected_name,
        "decision_maker",
    )

    assert (
        comparison_key(
            expected_name
        )
        in {
            comparison_key(
                value
            )
            for value
            in packet.decision_maker_actor_names
        }
    )


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
                "L'entreprise cliente compare "
                "les propositions et choisit "
                "un prestataire."
            ),
            "entreprise cliente",
        ),
        (
            "en",
            (
                "The client company compares "
                "the proposals and chooses "
                "a provider."
            ),
            "client company",
        ),
    ],
)
def test_workflow_actor_is_identity_not_predicate_fragment(
    language: str,
    description: str,
    expected_actor: str,
):
    packet = extract(
        description,
        language=language,
    )

    choosing = [
        workflow
        for workflow
        in packet.priority_workflows
        if workflow.action
        in {
            "choisir",
            "choose",
        }
    ]

    assert choosing, [
        workflow.model_dump(
            mode="json"
        )
        for workflow
        in packet.priority_workflows
    ]

    actor = comparison_key(
        choosing[0].actor
    )

    assert actor == comparison_key(
        expected_actor
    ), choosing[0].model_dump(
        mode="json"
    )

    assert not any(
        marker in actor
        for marker in (
            "compare les propositions",
            "compare the proposals",
            "compares the proposals",
        )
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "payer",
        "decision_maker",
        "operational_user",
    ),
    [
        (
            "fr",
            (
                "L'utilisateur operationnel principal est "
                "le responsable stock. "
                "Le directeur des operations est "
                "le decideur principal. "
                "L'entreprise cliente est le payeur. "
                "L'entreprise cliente paie l'abonnement."
            ),
            "entreprise cliente",
            "directeur des operations",
            "responsable stock",
        ),
        (
            "en",
            (
                "The primary operational user is "
                "the inventory manager. "
                "The operations director is "
                "the primary decision maker. "
                "The client company is the payer. "
                "The client company pays the subscription."
            ),
            "client company",
            "operations director",
            "inventory manager",
        ),
    ],
)
def test_existing_explicit_role_authorities_remain_preserved(
    language: str,
    description: str,
    payer: str,
    decision_maker: str,
    operational_user: str,
):
    packet = extract(
        description,
        language=language,
    )

    assert_actor_role(
        packet,
        payer,
        "payer",
    )

    assert_actor_role(
        packet,
        decision_maker,
        "decision_maker",
    )

    assert_actor_role(
        packet,
        operational_user,
        "user",
    )


def test_market_segment_is_not_silently_used_as_operational_user():
    packet = extract(
        (
            "Le segment client principal est "
            "les PME tunisiennes de commerce de detail. "
            "L'utilisateur operationnel principal est "
            "le responsable stock. "
            "Le payeur est la PME cliente."
        )
    )

    users = {
        comparison_key(
            actor.name
        )
        for actor in packet.actors
        if actor.role.value == "user"
    }

    assert (
        comparison_key(
            "responsable stock"
        )
        in users
    )

    assert (
        comparison_key(
            "PME tunisiennes de commerce de detail"
        )
        not in users
    )
