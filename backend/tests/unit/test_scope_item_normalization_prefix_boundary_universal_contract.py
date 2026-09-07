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


def test_bare_scope_item_preserves_word_beginning_with_on() -> None:
    """
    Universal lexical-boundary invariant.

    A grammatical wrapper token such as "on" cannot consume the
    first characters of an ordinary lexical scope item.
    """

    assert (
        _normalize(
            "online payment processing"
        )
        ==
        "online payment processing"
    )


def test_other_on_prefixed_lexical_items_are_preserved() -> None:
    """
    Anti-overfit guard.

    The rule is not about payment and is not about the word online.
    """

    assert (
        _normalize(
            "onboarding workflow"
        )
        ==
        "onboarding workflow"
    )

    assert (
        _normalize(
            "on-demand reporting"
        )
        ==
        "on-demand reporting"
    )


def test_to_prefixed_lexical_item_is_not_partially_consumed() -> None:
    """
    The same boundary rule applies to every wrapper alternative.

    A grammatical "to" must not consume the beginning of "topic".
    """

    assert (
        _normalize(
            "topic management"
        )
        ==
        "topic management"
    )


def test_unrelated_bare_scope_items_remain_identity_preserving() -> None:
    """
    Ordinary items that contain no wrapper remain stable.
    """

    values = (
        "accounting",
        "inventory tracking",
        "quality control",
        "shipment preparation",
    )

    for value in values:

        assert (
            _normalize(
                value
            )
            ==
            value
        )


def test_real_structural_scope_wrappers_remain_supported() -> None:
    """
    Backward-compatibility guard.

    Fixing lexical boundaries must not disable the actual purpose
    of this normalizer: removing explicit structural MVP wrappers.
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
            "MVP: function beta"
        )
        ==
        "function beta"
    )


def test_real_runtime_shape_preserves_first_exclusion_item() -> None:
    """
    Regression for the observed carrier shape.

    The first explicit exclusion item must retain its lexical identity.
    """

    raw = (
        "online payment processing - "
        "accounting - payroll"
    )

    normalized = _normalize(
        raw
    )

    assert normalized.startswith(
        "online payment processing"
    )

    assert not normalized.startswith(
        "line payment processing"
    )