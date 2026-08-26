from __future__ import annotations

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)
from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


def _extract(
    description: str,
    *,
    language: str = "fr",
):
    return (
        project_context_extractor
        .extract(
            title="ScopeBridge",
            description=description,
            industry="Generic Services",
            target_region=(
                "France"
                if language == "fr"
                else "United Kingdom"
            ),
            output_language=language,
        )
    )


def _actor_names(
    packet,
):
    result = []

    for actor in (
        packet.actors
        or []
    ):
        if isinstance(
            actor,
            dict,
        ):
            name = actor.get(
                "name"
            )
        else:
            name = getattr(
                actor,
                "name",
                None,
            )

        if name:
            result.append(
                str(name)
            )

    return result


def _keys(
    values,
):
    return {
        comparison_key(
            value
        )
        for value in (
            values
            or []
        )
        if comparison_key(
            value
        )
    }


def test_scope_polarity_recognizes_direct_french_mvp_exclusion() -> None:
    assert (
        is_scope_exclusion_statement(
            (
                "Le MVP ne comprend pas "
                "les services destinés aux particuliers."
            )
        )
        is True
    )


def test_scope_polarity_recognizes_direct_english_mvp_exclusion() -> None:
    assert (
        is_scope_exclusion_statement(
            (
                "The MVP does not include "
                "services for individual consumers."
            )
        )
        is True
    )


def test_negative_only_french_scope_actor_is_not_materialized() -> None:
    packet = (
        _extract(
            (
                "ScopeBridge est une plateforme B2B. "
                "Les utilisateurs principaux sont "
                "les entreprises clientes. "
                "Le MVP ne comprend pas "
                "les services destinés aux particuliers. "
                "Le problème actuel est que les demandes "
                "sont lentes à traiter. "
                "La solution centralise les demandes "
                "et leur traitement."
            )
        )
    )

    actor_keys = _keys(
        _actor_names(
            packet
        )
    )

    target_keys = _keys(
        packet.target_terms
    )

    assert (
        comparison_key(
            "particuliers"
        )
        not in actor_keys
    ), _actor_names(packet)

    assert (
        comparison_key(
            "particuliers"
        )
        not in target_keys
    ), packet.target_terms


def test_negative_only_english_scope_actor_is_not_materialized() -> None:
    packet = (
        _extract(
            (
                "ScopeBridge is a B2B platform. "
                "The primary users are client companies. "
                "The MVP does not include services "
                "for individual consumers. "
                "The current problem is that requests "
                "are slow to process. "
                "The solution centralizes requests "
                "and their processing."
            ),
            language="en",
        )
    )

    actor_keys = _keys(
        _actor_names(
            packet
        )
    )

    target_keys = _keys(
        packet.target_terms
    )

    excluded = comparison_key(
        "individual consumers"
    )

    assert (
        excluded
        not in actor_keys
    ), _actor_names(packet)

    assert (
        excluded
        not in target_keys
    ), packet.target_terms


def test_positive_actor_declaration_remains_authoritative() -> None:
    packet = (
        _extract(
            (
                "ScopeBridge est une plateforme numérique. "
                "Les utilisateurs principaux sont "
                "les entreprises clientes et les particuliers. "
                "Le problème actuel est que les demandes "
                "sont lentes à traiter. "
                "La solution centralise les demandes "
                "et leur traitement."
            )
        )
    )

    actor_keys = _keys(
        _actor_names(
            packet
        )
    )

    assert (
        comparison_key(
            "particuliers"
        )
        in actor_keys
    ), _actor_names(packet)


def test_positive_actor_is_not_erased_by_excluded_feature_for_same_actor() -> None:
    packet = (
        _extract(
            (
                "ScopeBridge est une plateforme numérique. "
                "Les utilisateurs principaux sont "
                "les entreprises clientes et les particuliers. "
                "Le MVP ne comprend pas "
                "un abonnement premium obligatoire "
                "pour les particuliers. "
                "Le problème actuel est que les demandes "
                "sont lentes à traiter. "
                "La solution centralise les demandes "
                "et leur traitement."
            )
        )
    )

    actor_keys = _keys(
        _actor_names(
            packet
        )
    )

    target_keys = _keys(
        packet.target_terms
    )

    actor = comparison_key(
        "particuliers"
    )

    assert (
        actor
        in actor_keys
    ), _actor_names(packet)

    assert (
        actor
        in target_keys
    ), packet.target_terms
