from __future__ import annotations

import pytest

from app.schemas.analysis_context import comparison_key
from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def extract(
    *,
    title: str,
    description: str,
    language: str,
):
    return ProjectContextExtractor().extract(
        title=title,
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def actor_keys(packet) -> set[str]:
    return {
        comparison_key(value)
        for value in packet.actor_names()
        if comparison_key(value)
    }


@pytest.mark.parametrize(
    (
        "language",
        "title",
        "baseline",
        "transformed",
        "expected_actor",
    ),
    (
        (
            "fr",
            "FlowDesk",
            (
                "Le produit est une application web. "
                "L'utilisateur cibl\u00e9 est le gestionnaire."
            ),
            (
                "Le produit est une application web. "
                "L'utilisateur cibl\u00e9 est le gestionnaire. "
                "FlowDesk doit permettre au gestionnaire "
                "d'enregistrer et de suivre les demandes."
            ),
            "gestionnaire",
        ),
        (
            "en",
            "FlowDesk",
            (
                "The product is a web application. "
                "The target user is the operations manager."
            ),
            (
                "The product is a web application. "
                "The target user is the operations manager. "
                "FlowDesk must allow the operations manager "
                "to register and track requests."
            ),
            "operations manager",
        ),
    ),
)
def test_operational_product_clause_cannot_materialize_as_actor_identity(
    language: str,
    title: str,
    baseline: str,
    transformed: str,
    expected_actor: str,
) -> None:
    """
    Universal metamorphic actor-identity invariant.

    Adding an operational sentence describing what the product enables
    must not create a new actor identity.

    Product name + modal/action clause is workflow/solution evidence,
    never an actor identity.
    """

    before = extract(
        title=title,
        description=baseline,
        language=language,
    )

    after = extract(
        title=title,
        description=transformed,
        language=language,
    )

    before_keys = actor_keys(
        before
    )

    after_keys = actor_keys(
        after
    )

    assert comparison_key(
        expected_actor
    ) in before_keys

    assert comparison_key(
        expected_actor
    ) in after_keys

    assert after_keys == before_keys, (
        language,
        before.actor_names(),
        after.actor_names(),
    )


@pytest.mark.parametrize(
    (
        "language",
        "title",
        "description",
    ),
    (
        (
            "fr",
            "FlowDesk",
            (
                "Le produit est une application web. "
                "L'utilisateur cibl\u00e9 est le gestionnaire. "
                "FlowDesk doit permettre au gestionnaire "
                "de suivre les demandes."
            ),
        ),
        (
            "en",
            "FlowDesk",
            (
                "The product is a web application. "
                "The target user is the operations manager. "
                "FlowDesk must allow the operations manager "
                "to track requests."
            ),
        ),
    ),
)
def test_actor_identity_cannot_be_a_product_modal_clause(
    language: str,
    title: str,
    description: str,
) -> None:
    """
    Actor identities are noun/entity identities.

    They cannot be complete propositions owned by the product.
    """

    packet = extract(
        title=title,
        description=description,
        language=language,
    )

    title_key = comparison_key(
        title
    )

    forbidden_relation_tokens = {
        "doit permettre",
        "must allow",
        "permettre au",
        "allow the",
    }

    for actor_name in packet.actor_names():

        key = comparison_key(
            actor_name
        )

        assert not (
            title_key
            and key.startswith(
                title_key
            )
            and any(
                comparison_key(token)
                in key
                for token
                in forbidden_relation_tokens
            )
        ), (
            language,
            packet.actor_names(),
        )


@pytest.mark.parametrize(
    (
        "language",
        "candidate",
    ),
    (
        (
            "fr",
            (
                "PlanBoard doit permettre au responsable "
                "des operations de suivre les demandes"
            ),
        ),
        (
            "en",
            (
                "PlanBoard must allow the operations manager "
                "to track requests"
            ),
        ),
    ),
)
def test_actor_identity_cleaner_rejects_complete_predicative_clause(
    language: str,
    candidate: str,
) -> None:
    """
    Canonical actor identity invariant.

    A structured actor candidate is not trusted merely because an
    upstream layer labeled it as an actor.

    A complete subject + predicate + operation proposition is not an
    actor identity and must be rejected at the canonical actor boundary.
    """

    extractor = ProjectContextExtractor()

    assert extractor._clean_actor(
        candidate
    ) == "", (
        language,
        extractor._clean_actor(candidate),
    )


@pytest.mark.parametrize(
    (
        "language",
        "candidate",
    ),
    (
        (
            "fr",
            (
                "PlanBoard doit permettre au responsable "
                "des operations d'"
            ),
        ),
        (
            "en",
            (
                "PlanBoard must allow the operations manager to"
            ),
        ),
    ),
)
def test_actor_identity_cleaner_rejects_truncated_predicative_clause(
    language: str,
    candidate: str,
) -> None:
    """
    Historical/projection compatibility invariant.

    A proposition already truncated before its operational verb
    is still not a noun/entity identity.
    """

    extractor = ProjectContextExtractor()

    assert extractor._clean_actor(
        candidate
    ) == "", (
        language,
        extractor._clean_actor(candidate),
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "structured_source",
        "expected_actor",
    ),
    (
        (
            "fr",
            (
                "Le produit est une application web. "
                "L'utilisateur cible est le responsable "
                "des operations."
            ),
            {
                "target_users": [
                    (
                        "PlanBoard doit permettre au responsable "
                        "des operations de suivre les demandes"
                    ),
                ],
            },
            "responsable des operations",
        ),
        (
            "en",
            (
                "The product is a web application. "
                "The target user is the operations manager."
            ),
            {
                "target_users": [
                    (
                        "PlanBoard must allow the operations manager "
                        "to track requests"
                    ),
                ],
            },
            "operations manager",
        ),
    ),
)
def test_structured_target_user_carrier_cannot_bypass_actor_identity_semantics(
    language: str,
    description: str,
    structured_source: dict,
    expected_actor: str,
) -> None:
    """
    Structured carriers provide evidence, not semantic immunity.

    project_context.target_users must pass through the same canonical
    actor-identity validity boundary as natural-language extraction.
    """

    packet = ProjectContextExtractor().extract(
        title="PlanBoard",
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context=structured_source,
        idea_readiness={},
        analysis_data={},
    )

    actual = {
        comparison_key(value)
        for value in packet.actor_names()
        if comparison_key(value)
    }

    assert comparison_key(
        expected_actor
    ) in actual

    assert actual == {
        comparison_key(
            expected_actor
        )
    }, (
        language,
        packet.actor_names(),
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "structured_source",
        "expected_actor",
    ),
    (
        (
            "fr",
            (
                "Le produit est une application web. "
                "L'utilisateur cible est le responsable "
                "des operations."
            ),
            {
                "target_users": [
                    (
                        "PlanBoard doit permettre au responsable "
                        "des operations d'"
                    ),
                ],
            },
            "responsable des operations",
        ),
        (
            "en",
            (
                "The product is a web application. "
                "The target user is the operations manager."
            ),
            {
                "target_users": [
                    (
                        "PlanBoard must allow the operations manager to"
                    ),
                ],
            },
            "operations manager",
        ),
    ),
)
def test_historical_truncated_actor_carrier_cannot_override_valid_identity(
    language: str,
    description: str,
    structured_source: dict,
    expected_actor: str,
) -> None:
    """
    Historical malformed projections cannot re-enter the canonical
    packet as actor identities.
    """

    packet = ProjectContextExtractor().extract(
        title="PlanBoard",
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data=structured_source,
    )

    actual = {
        comparison_key(value)
        for value in packet.actor_names()
        if comparison_key(value)
    }

    assert actual == {
        comparison_key(
            expected_actor
        )
    }, (
        language,
        packet.actor_names(),
    )
