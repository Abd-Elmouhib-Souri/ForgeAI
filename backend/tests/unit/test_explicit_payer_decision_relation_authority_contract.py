from __future__ import annotations

import pytest

from app.schemas.analysis_context import comparison_key
from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def extract(
    *,
    description: str,
    language: str,
):
    return ProjectContextExtractor().extract(
        title="RelationFlow",
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def keys(
    values: list[str],
) -> set[str]:
    return {
        comparison_key(value)
        for value in values
        if comparison_key(value)
    }


# ============================================================
# D1 ? PAYER RELATION
#
# Matrix:
#   simple declaration
#   relation scoped to product/service
#
# This lets us distinguish:
#   relation semantics GREEN
# from
#   grammatical carrier RED
# ============================================================

@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    (
        (
            "fr",
            (
                "Le payeur principal est "
                "l'entreprise cliente."
            ),
            "entreprise cliente",
        ),
        (
            "en",
            (
                "The primary payer is "
                "the client company."
            ),
            "client company",
        ),
    ),
)
def test_explicit_simple_payer_relation_is_canonical(
    language: str,
    description: str,
    expected: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    assert comparison_key(
        expected
    ) in keys(
        packet.payer_actor_names
    ), (
        language,
        packet.payer_actor_names,
        packet.actor_names(),
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    (
        (
            "fr",
            (
                "Le payeur principal de la plateforme "
                "est l'entreprise cliente."
            ),
            "entreprise cliente",
        ),
        (
            "en",
            (
                "The primary payer for the platform "
                "is the client company."
            ),
            "client company",
        ),
    ),
)
def test_product_scoped_payer_relation_is_canonical(
    language: str,
    description: str,
    expected: str,
) -> None:
    """
    Product/service qualification must not destroy the payer relation.

    The semantic relation is:
        payer -> actor

    The phrase describing what is being paid for is not part of the
    actor identity and must not block role materialization.
    """

    packet = extract(
        description=description,
        language=language,
    )

    assert comparison_key(
        expected
    ) in keys(
        packet.payer_actor_names
    ), (
        language,
        packet.payer_actor_names,
        packet.actor_names(),
    )


# ============================================================
# D2 ? DECISION MAKER RELATION
#
# Matrix:
#   singular declaration
#   plural coordinated declaration
# ============================================================

@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    (
        (
            "fr",
            (
                "Le d\u00e9cideur principal est "
                "le directeur des op\u00e9rations."
            ),
            "directeur des op\u00e9rations",
        ),
        (
            "en",
            (
                "The primary decision maker is "
                "the operations director."
            ),
            "operations director",
        ),
    ),
)
def test_explicit_single_decision_maker_is_canonical(
    language: str,
    description: str,
    expected: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    assert comparison_key(
        expected
    ) in keys(
        packet.decision_maker_actor_names
    ), (
        language,
        packet.decision_maker_actor_names,
        packet.actor_names(),
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    (
        (
            "fr",
            (
                "Les principaux d\u00e9cideurs sont "
                "le responsable des op\u00e9rations, "
                "le directeur administratif et "
                "le directeur g\u00e9n\u00e9ral."
            ),
            (
                "responsable des op\u00e9rations",
                "directeur administratif",
                "directeur g\u00e9n\u00e9ral",
            ),
        ),
        (
            "en",
            (
                "The primary decision makers are "
                "the operations manager, "
                "the administrative director, and "
                "the general manager."
            ),
            (
                "operations manager",
                "administrative director",
                "general manager",
            ),
        ),
    ),
)
def test_explicit_multiple_decision_makers_are_atomic_and_canonical(
    language: str,
    description: str,
    expected: tuple[str, ...],
) -> None:
    """
    Explicit coordinated decision makers must materialize as atomic
    actor identities carrying the decision-maker relation.
    """

    packet = extract(
        description=description,
        language=language,
    )

    actual = keys(
        packet.decision_maker_actor_names
    )

    expected_keys = {
        comparison_key(value)
        for value in expected
    }

    assert expected_keys.issubset(
        actual
    ), (
        language,
        expected_keys,
        actual,
        packet.actor_names(),
    )


# ============================================================
# NEGATIVE AUTHORITY CONTROL
#
# Mere target-user identity cannot invent economic/decision roles.
# ============================================================

@pytest.mark.parametrize(
    (
        "language",
        "description",
    ),
    (
        (
            "fr",
            (
                "L'utilisateur cibl\u00e9 est "
                "le responsable des op\u00e9rations."
            ),
        ),
        (
            "en",
            (
                "The target user is "
                "the operations manager."
            ),
        ),
    ),
)
def test_target_user_identity_does_not_invent_payer_or_decision_relation(
    language: str,
    description: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    assert packet.payer_actor_names == []
    assert packet.decision_maker_actor_names == []
