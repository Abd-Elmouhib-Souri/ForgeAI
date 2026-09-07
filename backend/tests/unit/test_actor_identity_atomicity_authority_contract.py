from __future__ import annotations

import pytest

from app.schemas.analysis_context import comparison_key
from app.services.project_context_extractor import ProjectContextExtractor


def extract(
    *,
    description: str,
    language: str,
):
    return ProjectContextExtractor().extract(
        title="Actor Identity Contract",
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def actor_keys(packet) -> list[str]:
    return [
        comparison_key(value)
        for value in packet.actor_names()
        if comparison_key(value)
    ]


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
        "forbidden_composite",
    ),
    (
        (
            "fr",
            (
                "Le produit est une application web pour une équipe "
                "opérationnelle. "
                "Les utilisateurs ciblés sont le gestionnaire "
                "et l'agent terrain."
            ),
            (
                "gestionnaire",
                "agent terrain",
            ),
            "gestionnaire et l'agent terrain",
        ),
        (
            "en",
            (
                "The product is a web application for an operations team. "
                "The target users are the operations manager "
                "and the field agent."
            ),
            (
                "operations manager",
                "field agent",
            ),
            "operations manager and the field agent",
        ),
    ),
)
def test_explicit_coordinated_actor_declarations_become_atomic_identities(
    language: str,
    description: str,
    expected: tuple[str, str],
    forbidden_composite: str,
) -> None:
    """
    Universal actor-identity invariant.

    Explicit coordinated actor declarations must preserve every actor
    as an independent canonical identity.

    No actor may disappear and the whole coordinated phrase must not
    survive as one composite actor.
    """

    packet = extract(
        description=description,
        language=language,
    )

    actual = set(
        actor_keys(packet)
    )

    expected_keys = {
        comparison_key(value)
        for value in expected
    }

    assert expected_keys.issubset(actual), (
        language,
        packet.actor_names(),
    )

    assert comparison_key(
        forbidden_composite
    ) not in actual, (
        language,
        packet.actor_names(),
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected_actor",
    ),
    (
        (
            "fr",
            (
                "Le produit est un outil web interne. "
                "L'utilisateur ciblé est le responsable des opérations."
            ),
            "responsable des opérations",
        ),
        (
            "en",
            (
                "The product is an internal web tool. "
                "The target user is the operations manager."
            ),
            "operations manager",
        ),
    ),
)
def test_single_multiword_actor_identity_is_not_split_into_words(
    language: str,
    description: str,
    expected_actor: str,
) -> None:
    """
    Anti-overfitting control.

    Atomicity means splitting coordinated actors, not splitting a valid
    multi-word role into individual tokens.
    """

    packet = extract(
        description=description,
        language=language,
    )

    actual = set(
        actor_keys(packet)
    )

    assert comparison_key(
        expected_actor
    ) in actual, (
        language,
        packet.actor_names(),
    )
