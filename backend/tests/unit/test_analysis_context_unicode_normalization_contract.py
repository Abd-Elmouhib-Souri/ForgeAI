from __future__ import annotations

import unicodedata

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    clean_text,
    unique_texts,
)


def test_clean_text_normalizes_canonical_unicode_to_nfc():
    nfc = "op\u00e9rateur"

    nfd = unicodedata.normalize(
        "NFD",
        nfc,
    )

    assert nfd != nfc

    cleaned = clean_text(
        nfd
    )

    assert cleaned == nfc

    assert unicodedata.is_normalized(
        "NFC",
        cleaned,
    )


def test_clean_text_remains_idempotent():
    source = (
        "Coordinateur "
        "r\u00e9gional"
    )

    once = clean_text(
        source
    )

    twice = clean_text(
        once
    )

    assert twice == once


def test_clean_text_preserves_existing_nul_and_whitespace_contract():
    value = (
        "  Caf\u0065\u0301"
        "\x00"
        "   service\t "
    )

    assert clean_text(value) == (
        "Caf\u00e9 service"
    )


def test_clean_text_uses_nfc_not_compatibility_folding():
    circled_digit = "\u2460"

    assert clean_text(
        circled_digit
    ) == circled_digit


def test_unique_texts_emits_one_nfc_canonical_value():
    nfc = (
        "coordinateur r\u00e9gional"
    )

    nfd = unicodedata.normalize(
        "NFD",
        nfc,
    )

    assert unique_texts(
        [
            nfd,
            nfc,
        ]
    ) == [
        nfc,
    ]


def test_actor_context_persists_nfc_identity():
    nfc = (
        "superviseur "
        "d\u2019\u00e9quipe"
    )

    nfd = unicodedata.normalize(
        "NFD",
        nfc,
    )

    actor = ActorContext(
        name=nfd,
        role=ActorRole.USER,
        is_explicit=True,
    )

    assert actor.name == nfc

    assert unicodedata.is_normalized(
        "NFC",
        actor.name,
    )
