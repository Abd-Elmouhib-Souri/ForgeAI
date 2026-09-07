from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _normalize(
    value: str,
) -> str:

    return (
        ProjectContextExtractor()
        ._normalize_scope_item(
            value
        )
    )


def test_feminine_limited_wrapper_requires_complete_token_boundary() -> None:
    """
    Universal lexical-boundary invariant.

    A shorter grammatical alternative such as "limite" / "limite-accent"
    cannot consume only the prefix of a longer inflected form.
    """

    assert (
        _normalize(
            (
                "La premi\u00e8re version "
                "sera limit\u00e9e \u00e0 "
                "fonction delta"
            )
        )
        ==
        "fonction delta"
    )


def test_longer_auxiliary_cannot_be_partially_consumed() -> None:
    """
    An auxiliary alternative must also end on a token boundary.

    "sera" cannot consume the beginning of "serait".
    """

    assert (
        _normalize(
            (
                "Le MVP serait limit\u00e9 \u00e0 "
                "fonction epsilon"
            )
        )
        ==
        "fonction epsilon"
    )


def test_feminine_focused_wrapper_requires_complete_token_boundary() -> None:
    """
    The invariant is grammatical and does not depend on one adjective.
    """

    assert (
        _normalize(
            (
                "La premi\u00e8re version "
                "sera concentr\u00e9e sur "
                "fonction zeta"
            )
        )
        ==
        "fonction zeta"
    )


def test_existing_english_structural_wrappers_remain_supported() -> None:
    """
    Backward compatibility.
    """

    assert (
        _normalize(
            "The MVP will be limited to function alpha"
        )
        ==
        "function alpha"
    )

    assert (
        _normalize(
            "The first version: function beta"
        )
        ==
        "function beta"
    )


def test_bare_lexical_items_remain_identity_preserving() -> None:
    """
    Anti-overfit guard from the already-closed 2P invariant.
    """

    values = (
        "online payment processing",
        "onboarding workflow",
        "on-demand reporting",
        "topic management",
        "prototype testing",
        "version control",
    )

    for value in values:

        assert (
            _normalize(
                value
            )
            ==
            value
        )