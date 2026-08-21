import re

from app.services.project_context_extractor import (
    project_context_extractor,
)


def test_french_explicit_transaction_unit_has_priority():
    packet = (
        project_context_extractor
        .extract(
            title="TransactionAuthorityFR",
            description=(
                "Le probl\u00e8me est un processus fragment\u00e9. "
                "Les utilisateurs ne veulent pas acheter les actifs. "
                "Une entreprise envoie une demande de r\u00e9servation. "
                "L'unit\u00e9 de transaction principale est "
                "une r\u00e9servation temporaire d'un actif "
                "pour une p\u00e9riode d\u00e9termin\u00e9e."
            ),
            industry="plateforme B2B",
            target_region="Europe",
            output_language="fr",
        )
    )

    transaction = packet.transaction_unit

    assert transaction.is_explicit is True

    assert (
        transaction.name
        == (
            "une r\u00e9servation temporaire d'un actif "
            "pour une p\u00e9riode d\u00e9termin\u00e9e"
        )
    )

    assert "acheter" not in transaction.name

    assert (
        transaction.value_exchanged
        == transaction.name
    )


def test_english_explicit_transaction_unit_has_priority():
    packet = (
        project_context_extractor
        .extract(
            title="TransactionAuthorityEN",
            description=(
                "The current process is fragmented. "
                "Users do not buy the underlying asset. "
                "A company sends a booking request. "
                "The primary transaction unit is "
                "a temporary booking of one asset "
                "for a defined period."
            ),
            industry="B2B platform",
            target_region="Europe",
            output_language="en",
        )
    )

    transaction = packet.transaction_unit

    assert transaction.is_explicit is True

    assert (
        transaction.name
        == (
            "a temporary booking of one asset "
            "for a defined period"
        )
    )

    assert "buy" not in transaction.name


def test_negated_french_action_is_not_transaction_candidate():
    sentence = (
        "Les utilisateurs ne veulent pas acheter "
        "les actifs."
    )

    pattern = re.compile(
        r"\bachet(?:er|e|ent)?\b",
        re.IGNORECASE,
    )

    assert (
        project_context_extractor
        ._transaction_action_candidate(
            sentence,
            pattern,
        )
        is None
    )


def test_negated_english_action_is_not_transaction_candidate():
    sentence = (
        "Users do not buy the asset."
    )

    pattern = re.compile(
        r"\bbuy(?:s|ing)?\b",
        re.IGNORECASE,
    )

    assert (
        project_context_extractor
        ._transaction_action_candidate(
            sentence,
            pattern,
        )
        is None
    )


def test_positive_action_remains_eligible():
    sentence = (
        "The customer books the service."
    )

    pattern = re.compile(
        r"\bbook(?:s|ed|ing)?\b",
        re.IGNORECASE,
    )

    assert (
        project_context_extractor
        ._transaction_action_candidate(
            sentence,
            pattern,
        )
        is not None
    )


def test_scope_exclusion_action_is_not_transaction_candidate():
    sentence = (
        "Le MVP ne doit pas inclure "
        "l'achat des actifs."
    )

    pattern = re.compile(
        r"\bachat\b",
        re.IGNORECASE,
    )

    assert (
        project_context_extractor
        ._transaction_action_candidate(
            sentence,
            pattern,
        )
        is None
    )
