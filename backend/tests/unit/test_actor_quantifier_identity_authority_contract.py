from __future__ import annotations

import pytest

from app.schemas.analysis_context import comparison_key
from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


@pytest.mark.parametrize(
    (
        "language",
        "candidate",
        "expected",
    ),
    (
        (
            "fr",
            "beaucoup de responsables de flotte",
            "responsables de flotte",
        ),
        (
            "fr",
            "de nombreux responsables de flotte",
            "responsables de flotte",
        ),
        (
            "fr",
            "plusieurs responsables de flotte",
            "responsables de flotte",
        ),
        (
            "en",
            "many operations managers",
            "operations managers",
        ),
        (
            "en",
            "several operations managers",
            "operations managers",
        ),
        (
            "en",
            "numerous operations managers",
            "operations managers",
        ),
    ),
)
def test_population_quantifier_is_not_part_of_actor_identity(
    language: str,
    candidate: str,
    expected: str,
) -> None:
    """
    Population quantity is metadata about prevalence or cardinality,
    not part of the canonical identity of the actor.

    The actor identity boundary must therefore remove a leading
    population quantifier while preserving the actor noun phrase.
    """

    extractor = ProjectContextExtractor()

    assert (
        comparison_key(
            extractor._clean_actor(
                candidate
            )
        )
        ==
        comparison_key(
            expected
        )
    ), (
        language,
        candidate,
        extractor._clean_actor(candidate),
    )


@pytest.mark.parametrize(
    (
        "language",
        "base_actor",
        "quantified_actor",
    ),
    (
        (
            "fr",
            "responsables de flotte",
            "beaucoup de responsables de flotte",
        ),
        (
            "en",
            "operations managers",
            "many operations managers",
        ),
    ),
)
def test_adding_population_quantifier_preserves_canonical_actor_identity(
    language: str,
    base_actor: str,
    quantified_actor: str,
) -> None:
    """
    Metamorphic actor identity invariant.

    Adding only population quantity to an actor phrase must not create
    a distinct actor identity.
    """

    extractor = ProjectContextExtractor()

    def extract_actor_keys(
        target_user: str,
    ) -> set[str]:
        packet = extractor.extract(
            title="TeamFlow",
            description=(
                "Un service logiciel interne."
                if language == "fr"
                else
                "An internal software service."
            ),
            industry="General operations",
            target_region="International",
            output_language=language,
            project_context={
                "target_users": [
                    target_user,
                ],
            },
            idea_readiness={},
            analysis_data={},
        )

        return {
            comparison_key(value)
            for value in packet.actor_names()
            if comparison_key(value)
        }

    baseline = extract_actor_keys(
        base_actor
    )

    transformed = extract_actor_keys(
        quantified_actor
    )

    assert transformed == baseline, (
        language,
        baseline,
        transformed,
    )


@pytest.mark.parametrize(
    (
        "candidate",
        "expected",
    ),
    (
        (
            "petites et moyennes entreprises locales",
            "petites et moyennes entreprises locales",
        ),
        (
            "small and medium local businesses",
            "small and medium local businesses",
        ),
    ),
)
def test_coordinated_size_modifiers_remain_part_of_organization_identity(
    candidate: str,
    expected: str,
) -> None:
    """
    Anti-overfit control.

    Organization size/type modifiers are semantic identity qualifiers,
    not population quantifiers and must remain intact.
    """

    extractor = ProjectContextExtractor()

    assert (
        comparison_key(
            extractor._clean_actor(
                candidate
            )
        )
        ==
        comparison_key(
            expected
        )
    )
