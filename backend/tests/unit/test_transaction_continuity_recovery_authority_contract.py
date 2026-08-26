from __future__ import annotations

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _bounds(
    description: str,
) -> tuple[str, str]:
    return (
        project_context_extractor
        ._explicit_transaction_flow_bounds(
            project_context_extractor
            ._sentences(
                description
            )
        )
    )


def _assert_bounds(
    description: str,
    expected_start: str,
    expected_completion: str,
) -> None:
    start, completion = _bounds(
        description
    )

    assert (
        comparison_key(start)
        == comparison_key(
            expected_start
        )
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key(
            expected_completion
        )
    ), (
        start,
        completion,
    )


def test_booking_delivery_then_definite_fee_keeps_payment_terminal() -> None:
    _assert_bounds(
        (
            "The buyer books a provider service. "
            "The provider delivers the service. "
            "The buyer pays the fee."
        ),
        "reserver",
        "payer",
    )


def test_explicit_conclusion_overrides_intermediate_reservation() -> None:
    _assert_bounds(
        (
            "Le vendeur publie un lot. "
            "L'acheteur reserve le lot "
            "et conclut la transaction."
        ),
        "publier",
        "conclure la transaction",
    )


def test_explicit_completed_object_state_remains_terminal() -> None:
    _assert_bounds(
        (
            "L'entreprise cliente initie "
            "une demande d'intervention. "
            "Le technicien realise l'intervention "
            "et l'entreprise confirme que "
            "l'intervention est terminee."
        ),
        "demander",
        "terminer",
    )


def test_booking_then_transaction_fee_keeps_payment_terminal() -> None:
    _assert_bounds(
        (
            "The client company books a provider service. "
            "The provider delivers the service. "
            "The client company pays the transaction fee."
        ),
        "reserver",
        "payer",
    )


def test_french_request_then_service_price_keeps_payment_terminal() -> None:
    _assert_bounds(
        (
            "L'entreprise cliente initie "
            "une demande d'intervention. "
            "Le prestataire realise ensuite "
            "l'intervention. "
            "L'entreprise cliente paie "
            "le prix du service."
        ),
        "demander",
        "payer",
    )


def test_send_request_then_service_fee_keeps_payment_terminal() -> None:
    _assert_bounds(
        (
            "The customer sends a request. "
            "The provider performs "
            "the requested service. "
            "The customer pays the service fee."
        ),
        "demander",
        "payer",
    )


def test_coordinated_french_service_reference_keeps_payment_terminal() -> None:
    _assert_bounds(
        (
            "Le client demande "
            "une intervention de maintenance "
            "puis paie le service."
        ),
        "demander",
        "payer",
    )


def test_same_actor_definite_subscription_is_not_enough() -> None:
    _assert_bounds(
        (
            "The customer books a meeting room. "
            "The customer pays "
            "the monthly analytics subscription."
        ),
        "reserver",
        "",
    )


def test_same_actor_unrelated_software_fee_is_not_enough() -> None:
    _assert_bounds(
        (
            "The customer books a meeting room. "
            "The customer pays the software fee."
        ),
        "reserver",
        "",
    )
