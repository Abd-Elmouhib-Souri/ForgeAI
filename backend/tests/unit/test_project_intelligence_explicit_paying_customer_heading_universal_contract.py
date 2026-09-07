from __future__ import annotations

import app.services.project_context_extractor as pce_module


def _extract(
    description: str,
) -> str:

    return (
        pce_module
        .project_intelligence_layer
        ._extract_economic_buyer_from_description(
            description
        )
    )


def test_explicit_paying_customer_block_heading_is_canonical() -> None:
    """
    Explicit semantic-heading invariant.

    An explicit paying-customer section establishes the economic
    buyer without requiring a sentence-form predicate.
    """

    description = (
        "A generic product coordinates a workflow.\n"
        "Paying customer:\n"
        "- operating organization\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert (
        _extract(
            description
        )
        ==
        "operating organization"
    )


def test_explicit_paying_customer_inline_heading_is_canonical() -> None:
    """
    The authority is the semantic declaration, not the newline layout.
    """

    assert (
        _extract(
            (
                "A generic service coordinates a workflow. "
                "Paying customer: operating organization. "
                "Business objective: reduce processing delay."
            )
        )
        ==
        "operating organization"
    )


def test_existing_economic_buyer_sentence_grammar_remains_supported() -> None:
    """
    Historical grammar must remain GREEN.
    """

    assert (
        _extract(
            (
                "A generic service coordinates a workflow. "
                "The economic buyer is the client organization."
            )
        )
        ==
        "client organization"
    )


def test_payment_capability_never_creates_payer_identity() -> None:
    """
    Anti-overfit and anti-invention invariant.

    Payment capability is not payer identity.
    """

    descriptions = (
        (
            "The system allows customers "
            "to pay online."
        ),
        (
            "The MVP includes online "
            "payment processing."
        ),
        (
            "Payment status is displayed "
            "in the dashboard."
        ),
    )

    for description in descriptions:

        assert (
            _extract(
                description
            )
            ==
            ""
        )