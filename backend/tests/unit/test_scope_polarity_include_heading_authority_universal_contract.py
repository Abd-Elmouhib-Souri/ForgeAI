from __future__ import annotations

import unicodedata

from app.services.scope_polarity import (
    is_scope_exclusion_statement,
    partition_scope_sections,
)


def _fold(
    value,
) -> str:
    text = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(
            char
        )
    )

    return " ".join(
        text
        .casefold()
        .replace("-", " ")
        .split()
    )


def _assert_partition(
    *,
    value: str,
    positive_terms: tuple[str, ...],
    negative_terms: tuple[str, ...],
) -> None:

    positive, excluded = (
        partition_scope_sections(
            value
        )
    )

    positive_folded = _fold(
        positive
    )

    excluded_folded = _fold(
        excluded
    )

    for term in positive_terms:

        assert (
            _fold(term)
            in positive_folded
        ), {
            "positive":
                positive,
            "missing":
                term,
        }

    for term in negative_terms:

        assert (
            _fold(term)
            not in positive_folded
        ), {
            "positive":
                positive,
            "negative_leak":
                term,
        }

        assert (
            _fold(term)
            in excluded_folded
        ), {
            "excluded":
                excluded,
            "missing_exclusion":
                term,
        }


def test_english_does_not_include_heading_is_partition_authority() -> None:
    """
    The section partition authority must agree with the statement
    classifier for a semantically explicit negative MVP declaration.
    """

    value = (
        "MVP capabilities: "
        "function alpha; function beta. "
        "The MVP does NOT include: "
        "function gamma; function delta. "
        "Business objective: reduce processing delay."
    )

    assert is_scope_exclusion_statement(
        "The MVP does NOT include function gamma."
    )

    _assert_partition(
        value=value,
        positive_terms=(
            "function alpha",
            "function beta",
        ),
        negative_terms=(
            "function gamma",
            "function delta",
        ),
    )

    _, excluded = (
        partition_scope_sections(
            value
        )
    )

    assert (
        "business objective"
        not in _fold(
            excluded
        )
    )


def test_english_does_not_initially_include_heading_has_same_polarity() -> None:
    """
    Temporal modifiers do not change explicit negative polarity.
    """

    _assert_partition(
        value=(
            "MVP capabilities: "
            "function alpha. "
            "The MVP does not initially include: "
            "function gamma; function delta."
        ),
        positive_terms=(
            "function alpha",
        ),
        negative_terms=(
            "function gamma",
            "function delta",
        ),
    )


def test_french_ninclut_pas_heading_is_partition_authority() -> None:
    """
    The invariant is language-independent.
    """

    value = (
        "MVP : fonction alpha; fonction beta. "
        "Le MVP n'inclut pas : "
        "fonction gamma; fonction delta. "
        "Objectif m\u00e9tier : r\u00e9duire le d\u00e9lai."
    )

    assert is_scope_exclusion_statement(
        "Le MVP n'inclut pas la fonction gamma."
    )

    _assert_partition(
        value=value,
        positive_terms=(
            "fonction alpha",
            "fonction beta",
        ),
        negative_terms=(
            "fonction gamma",
            "fonction delta",
        ),
    )

    _, excluded = (
        partition_scope_sections(
            value
        )
    )

    assert (
        "objectif metier"
        not in _fold(
            excluded
        )
    )


def test_french_ne_comprend_pas_heading_is_partition_authority() -> None:
    """
    Equivalent explicit exclusion grammar must establish equivalent
    section polarity.
    """

    assert is_scope_exclusion_statement(
        "Le MVP ne comprend pas la fonction gamma."
    )

    _assert_partition(
        value=(
            "MVP : fonction alpha. "
            "Le MVP ne comprend pas : "
            "fonction gamma; fonction delta."
        ),
        positive_terms=(
            "fonction alpha",
        ),
        negative_terms=(
            "fonction gamma",
            "fonction delta",
        ),
    )


def test_natural_and_established_negative_headings_are_semantically_equivalent() -> None:
    """
    Wording is syntax, not business truth.

    Existing historical heading support and natural-language heading
    support must produce the same canonical partition.
    """

    natural = (
        "MVP capabilities: "
        "function alpha; function beta. "
        "The MVP does not include: "
        "function gamma; function delta."
    )

    established = (
        "MVP capabilities: "
        "function alpha; function beta. "
        "Explicitly out of scope for the MVP: "
        "function gamma; function delta."
    )

    natural_positive, natural_excluded = (
        partition_scope_sections(
            natural
        )
    )

    established_positive, established_excluded = (
        partition_scope_sections(
            established
        )
    )

    assert (
        _fold(
            natural_positive
        )
        ==
        _fold(
            established_positive
        )
    )

    assert (
        _fold(
            natural_excluded
        )
        ==
        _fold(
            established_excluded
        )
    )


def test_positive_include_heading_must_not_be_partitioned_as_negative() -> None:
    """
    Positive syntax remains positive.
    """

    value = (
        "The MVP includes: "
        "function alpha; function beta."
    )

    positive, excluded = (
        partition_scope_sections(
            value
        )
    )

    assert (
        "function alpha"
        in _fold(
            positive
        )
    )

    assert (
        excluded
        ==
        ""
    )

    assert not is_scope_exclusion_statement(
        "The MVP includes function alpha."
    )


def test_not_only_is_additive_not_negative_scope() -> None:
    """
    Anti-overclassification control.

    'not only' / 'pas seulement' are additive constructions.
    """

    english = (
        "The MVP does not only include "
        "function alpha; it also includes function beta."
    )

    french = (
        "Le MVP n'inclut pas seulement "
        "la fonction alpha; il inclut aussi la fonction beta."
    )

    for value in (
        english,
        french,
    ):

        positive, excluded = (
            partition_scope_sections(
                value
            )
        )

        assert excluded == ""
        assert positive

        assert not is_scope_exclusion_statement(
            value
        )