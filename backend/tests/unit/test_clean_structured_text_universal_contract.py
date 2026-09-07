from __future__ import annotations

import unicodedata

import app.schemas.analysis_context as context_schema


def structured_clean(value):
    function = getattr(
        context_schema,
        "clean_structured_text",
        None,
    )

    assert callable(function)

    return function(value)


def test_structured_cleaner_preserves_line_boundaries() -> None:
    assert structured_clean(
        "alpha\nbeta"
    ) == "alpha\nbeta"


def test_structured_cleaner_canonicalizes_newline_encoding() -> None:
    assert structured_clean(
        "alpha\r\nbeta\rgamma"
    ) == (
        "alpha\nbeta\ngamma"
    )


def test_structured_cleaner_normalizes_whitespace_per_line() -> None:
    assert structured_clean(
        "  heading   value  \n  -   item   alpha  "
    ) == (
        "heading value\n- item alpha"
    )


def test_structured_cleaner_preserves_internal_blank_section_boundary() -> None:
    assert structured_clean(
        "\n\nalpha\n\nbeta\n\n"
    ) == (
        "alpha\n\nbeta"
    )


def test_structured_cleaner_preserves_unicode_nfc() -> None:
    source = (
        "Cafe\u0301\n"
        "- e\u0301le\u0301ment"
    )

    result = structured_clean(
        source
    )

    assert result == unicodedata.normalize(
        "NFC",
        result,
    )

    assert result == (
        "Caf\u00e9\n"
        "- \u00e9l\u00e9ment"
    )


def test_structured_cleaner_repairs_nul_without_merging_lines() -> None:
    assert structured_clean(
        "alpha\x00beta\n- gamma"
    ) == (
        "alpha beta\n- gamma"
    )


def test_atomic_clean_text_contract_remains_flat() -> None:
    assert context_schema.clean_text(
        "alpha\nbeta"
    ) == (
        "alpha beta"
    )