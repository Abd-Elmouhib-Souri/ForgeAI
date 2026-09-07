from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)

from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


def test_french_scope_qualified_replacement_negation_is_exclusion() -> None:

    assert is_scope_exclusion_statement(
        "La plateforme ne remplace pas "
        "un logiciel de gestion complet dans le MVP."
    )


def test_french_future_replacement_negation_is_exclusion() -> None:

    assert is_scope_exclusion_statement(
        "Le service ne remplacera pas "
        "le systeme historique dans la premiere version."
    )


def test_english_scope_qualified_replacement_negation_is_exclusion() -> None:

    assert is_scope_exclusion_statement(
        "The platform does not replace "
        "a complete management system in the MVP."
    )


def test_positive_replacement_statement_is_not_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        "La plateforme remplace le suivi manuel "
        "dans le MVP."
    )

    assert not is_scope_exclusion_statement(
        "The platform replaces manual tracking "
        "in the MVP."
    )


def test_negative_security_control_is_not_reclassified_as_scope_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        "Le MVP ne doit pas stocker "
        "les mots de passe en clair."
    )

    assert not is_scope_exclusion_statement(
        "The MVP must not store "
        "passwords in plaintext."
    )


def test_replacement_negation_without_release_scope_is_not_automatically_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        "Le systeme ne remplace pas "
        "une validation humaine."
    )

    assert not is_scope_exclusion_statement(
        "The system does not replace "
        "human validation."
    )


def test_replacement_negation_is_partitioned_out_of_positive_canonical_mvp() -> None:

    extractor = ProjectContextExtractor()

    packet = extractor.extract(
        title="Neutral Operations Platform",
        description=(
            "Le MVP doit permettre aux equipes "
            "de creer et suivre des dossiers. "
            "La plateforme ne remplace pas "
            "un logiciel de gestion complet dans le MVP."
        ),
        industry="Business software",
        target_region="International",
        output_language="fr",
        project_context={},
        idea_readiness={},
        analysis_data={},
    )

    positive = [
        value.casefold()
        for value in (
            packet.mvp_scope
            or []
        )
    ]

    excluded = [
        value.casefold()
        for value in (
            packet.scope_exclusions
            or []
        )
    ]

    assert not any(
        "ne remplace pas" in value
        for value in positive
    ), positive

    assert any(
        "ne remplace pas" in value
        for value in excluded
    ), excluded
