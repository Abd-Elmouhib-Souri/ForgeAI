from __future__ import annotations

import app.services.project_context_extractor as pce_module


def _pil():
    return (
        pce_module
        .project_intelligence_layer
    )


def _extract(
    description: str,
) -> str:

    return (
        _pil()
        ._extract_economic_buyer_from_description(
            description
        )
    )


def test_explicit_paying_customer_authority_does_not_depend_on_actor_lexicon(
    monkeypatch,
) -> None:
    """
    Explicit semantic authority outranks a generic lexical heuristic.
    """

    monkeypatch.setattr(
        _pil(),
        "_is_actor_phrase",
        lambda value: False,
    )

    assert (
        _extract(
            (
                "A generic workflow. "
                "Paying customer: operating organization. "
                "Business objective: reduce delay."
            )
        )
        ==
        "operating organization"
    )


def test_explicit_budget_owner_authority_does_not_depend_on_actor_lexicon(
    monkeypatch,
) -> None:
    """
    The invariant is about semantic role declarations,
    not one particular heading.
    """

    monkeypatch.setattr(
        _pil(),
        "_is_actor_phrase",
        lambda value: False,
    )

    assert (
        _extract(
            "Budget owner: finance organization."
        )
        ==
        "finance organization"
    )


def test_explicit_french_payer_authority_does_not_depend_on_actor_lexicon(
    monkeypatch,
) -> None:
    """
    The authority invariant is language-independent.
    """

    monkeypatch.setattr(
        _pil(),
        "_is_actor_phrase",
        lambda value: False,
    )

    assert (
        _extract(
            "Client payeur: organisation cliente."
        )
        ==
        "organisation cliente"
    )


def test_historical_heuristic_sentence_still_uses_generic_actor_validation(
    monkeypatch,
) -> None:
    """
    Unlabeled prose remains protected by the generic actor heuristic.
    """

    monkeypatch.setattr(
        _pil(),
        "_is_actor_phrase",
        lambda value: False,
    )

    assert (
        _extract(
            (
                "The economic buyer is "
                "the client organization."
            )
        )
        ==
        ""
    )


def test_empty_explicit_heading_cannot_consume_the_next_section() -> None:
    """
    Section-boundary safety.

    An empty payer declaration cannot capture the following heading.
    """

    description = (
        "Paying customer:\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert (
        _extract(
            description
        )
        ==
        ""
    )


def test_payment_capability_without_role_declaration_is_not_payer_identity() -> None:
    """
    Anti-invention invariant.
    """

    descriptions = (
        "The MVP includes online payment processing.",
        "Payment status is visible in the dashboard.",
        "The customer can pay online.",
    )

    for description in descriptions:

        assert (
            _extract(
                description
            )
            ==
            ""
        )