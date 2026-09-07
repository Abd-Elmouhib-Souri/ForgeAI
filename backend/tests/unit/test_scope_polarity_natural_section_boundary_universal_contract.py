from __future__ import annotations

from app.services.scope_polarity import (
    partition_scope_sections,
)


def _fold(
    value: str,
) -> str:
    return str(
        value
        or ""
    ).casefold()


def test_natural_negative_mvp_heading_partitions_positive_and_excluded_scope() -> None:
    """
    Universal polarity invariant.

    A semantically negative MVP heading must establish the polarity
    boundary as a whole. The token "MVP" inside that heading must not
    cause the excluded section to remain positive.
    """

    positive, excluded = (
        partition_scope_sections(
            "MVP capabilities: "
            "function alpha; function beta. "
            "Explicitly out of scope for the MVP: "
            "excluded function gamma; excluded function delta."
        )
    )

    positive_folded = _fold(
        positive
    )

    excluded_folded = _fold(
        excluded
    )

    assert "function alpha" in positive_folded
    assert "function beta" in positive_folded

    assert "excluded function gamma" not in positive_folded
    assert "excluded function delta" not in positive_folded

    assert "excluded function gamma" in excluded_folded
    assert "excluded function delta" in excluded_folded


def test_negative_only_natural_heading_does_not_create_positive_scope() -> None:
    """
    A negative-only declaration cannot manufacture positive MVP scope.
    """

    positive, excluded = (
        partition_scope_sections(
            "Explicitly out of scope for the MVP: "
            "excluded function gamma; excluded function delta."
        )
    )

    positive_folded = _fold(
        positive
    )

    excluded_folded = _fold(
        excluded
    )

    assert "excluded function gamma" not in positive_folded
    assert "excluded function delta" not in positive_folded

    assert "excluded function gamma" in excluded_folded
    assert "excluded function delta" in excluded_folded


def test_following_business_section_does_not_bleed_into_excluded_scope() -> None:
    """
    Universal section-boundary invariant.

    Scope exclusion ends when another explicit semantic section starts.
    An unrelated following section cannot become a scope exclusion.
    """

    positive, excluded = (
        partition_scope_sections(
            "MVP capabilities: "
            "function alpha; function beta. "
            "Explicitly out of scope for the MVP: "
            "excluded function gamma; excluded function delta. "
            "Business objective: reduce processing delay."
        )
    )

    positive_folded = _fold(
        positive
    )

    excluded_folded = _fold(
        excluded
    )

    assert "function alpha" in positive_folded
    assert "function beta" in positive_folded

    assert "excluded function gamma" in excluded_folded
    assert "excluded function delta" in excluded_folded

    assert "reduce processing delay" not in positive_folded
    assert "reduce processing delay" not in excluded_folded


def test_french_following_semantic_section_respects_same_boundary() -> None:
    """
    The section-boundary invariant is semantic rather than English-only.
    """

    positive, excluded = (
        partition_scope_sections(
            "MVP : fonction alpha; fonction beta. "
            "Hors p\u00e9rim\u00e8tre du MVP : "
            "fonction gamma; fonction delta. "
            "Objectif m\u00e9tier : r\u00e9duire le d\u00e9lai."
        )
    )

    positive_folded = _fold(
        positive
    )

    excluded_folded = _fold(
        excluded
    )

    assert "fonction alpha" in positive_folded
    assert "fonction beta" in positive_folded

    assert "fonction gamma" not in positive_folded
    assert "fonction delta" not in positive_folded

    assert "fonction gamma" in excluded_folded
    assert "fonction delta" in excluded_folded

    assert "r\u00e9duire le d\u00e9lai" not in excluded_folded


def test_existing_historical_mvp_exclusions_form_remains_supported() -> None:
    """
    Anti-overfit / backward-compatibility guard.
    """

    positive, excluded = (
        partition_scope_sections(
            "MVP: function alpha; function beta. "
            "MVP exclusions: "
            "excluded function gamma; excluded function delta."
        )
    )

    positive_folded = _fold(
        positive
    )

    excluded_folded = _fold(
        excluded
    )

    assert "function alpha" in positive_folded
    assert "function beta" in positive_folded

    assert "excluded function gamma" in excluded_folded
    assert "excluded function delta" in excluded_folded