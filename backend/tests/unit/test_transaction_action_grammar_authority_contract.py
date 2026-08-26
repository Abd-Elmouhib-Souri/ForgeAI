from __future__ import annotations

import inspect

from app.services.project_context_extractor import (
    ProjectContextExtractor,
    comparison_key,
    project_context_extractor,
)


def _bounds(
    description: str,
) -> tuple[str, str]:
    sentences = (
        project_context_extractor
        ._sentences(
            description
        )
    )

    return (
        project_context_extractor
        ._explicit_transaction_flow_bounds(
            sentences
        )
    )


def _transaction(
    description: str,
):
    return (
        project_context_extractor
        .extract(
            title="Transaction Grammar Authority",
            description=description,
            industry="Generic Operations",
            target_region="Europe",
            output_language="en",
        )
        .transaction_unit
    )


def test_booking_predicate_remains_transaction_start() -> None:
    start, completion = _bounds(
        "The customer books a service."
    )

    assert (
        comparison_key(start)
        == comparison_key("r\u00e9server")
    ), (
        start,
        completion,
    )

    assert completion == ""


def test_booking_progressive_remains_transaction_start() -> None:
    start, completion = _bounds(
        "The customer is booking a service."
    )

    assert (
        comparison_key(start)
        == comparison_key("r\u00e9server")
    ), (
        start,
        completion,
    )

    assert completion == ""


def test_booking_noun_after_payment_does_not_override_payment() -> None:
    start, completion = _bounds(
        (
            "The customer books a service "
            "and pays for the booking."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("r\u00e9server")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("payer")
    ), (
        start,
        completion,
    )


def test_booking_determiner_noun_is_not_transaction_event() -> None:
    assert _bounds(
        "The booking includes a service fee."
    ) == (
        "",
        "",
    )


def test_booking_metadata_is_not_transaction_event() -> None:
    assert _bounds(
        (
            "The booking of the service "
            "is documented."
        )
    ) == (
        "",
        "",
    )


def test_order_finite_predicate_is_transaction_start() -> None:
    start, completion = _bounds(
        "The customer orders an item."
    )

    assert (
        comparison_key(start)
        == comparison_key("commander")
    ), (
        start,
        completion,
    )

    assert completion == ""


def test_order_base_predicate_is_transaction_start() -> None:
    start, completion = _bounds(
        "Customers order items online."
    )

    assert (
        comparison_key(start)
        == comparison_key("commander")
    ), (
        start,
        completion,
    )

    assert completion == ""


def test_order_progressive_predicate_is_transaction_start() -> None:
    start, completion = _bounds(
        "The customer is ordering an item."
    )

    assert (
        comparison_key(start)
        == comparison_key("commander")
    ), (
        start,
        completion,
    )

    assert completion == ""


def test_order_noun_after_payment_does_not_override_payment() -> None:
    start, completion = _bounds(
        (
            "The customer orders an item "
            "and pays for the order."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("commander")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("payer")
    ), (
        start,
        completion,
    )


def test_order_then_item_payment_keeps_payment_completion() -> None:
    start, completion = _bounds(
        (
            "The customer orders an item "
            "and pays the item price."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("commander")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("payer")
    ), (
        start,
        completion,
    )


def test_order_determiner_noun_is_not_transaction_event() -> None:
    assert _bounds(
        "The order contains three items."
    ) == (
        "",
        "",
    )


def test_plural_orders_noun_is_not_transaction_event() -> None:
    assert _bounds(
        "The orders are processed daily."
    ) == (
        "",
        "",
    )


def test_order_metadata_is_not_transaction_event() -> None:
    assert _bounds(
        "The order of operations is documented."
    ) == (
        "",
        "",
    )


def test_publish_then_order_preserves_contextual_completion() -> None:
    start, completion = _bounds(
        (
            "The seller publishes an item. "
            "The buyer orders the item."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("commander")
    ), (
        start,
        completion,
    )


def test_publish_then_booking_preserves_contextual_completion() -> None:
    start, completion = _bounds(
        (
            "The seller publishes an item. "
            "The buyer books the item."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("reserver")
    ), (
        start,
        completion,
    )


def test_full_packet_book_then_pay_keeps_payment_completion() -> None:
    transaction = _transaction(
        (
            "The customer books a service "
            "and pays for the booking."
        )
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key("r\u00e9server")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == comparison_key("service")
    ), transaction.model_dump(
        mode="json"
    )


def test_full_packet_order_then_pay_has_order_start_and_payment_completion() -> None:
    transaction = _transaction(
        (
            "The customer orders an item "
            "and pays for the order."
        )
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key("commander")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == comparison_key("item")
    ), transaction.model_dump(
        mode="json"
    )


def test_transaction_grammar_reuses_workflow_nominal_authority() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._transaction_match_is_grammatically_operational
    )

    assert (
        "_workflow_match_is_nominal"
        in source
    )

    assert (
        "_workflow_match_is_conditional_passive_context"
        in source
    )


def test_transaction_completion_consumes_shared_grammar_authority() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._transaction_completion_candidate_is_operational
    )

    assert (
        "_transaction_match_is_grammatically_operational"
        in source
    )


def test_transaction_action_candidate_consumes_shared_grammar_authority() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._transaction_action_candidate
    )

    assert (
        "_transaction_match_is_grammatically_operational"
        in source
    )


def test_transaction_grammar_contains_no_project_specific_rule() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._transaction_match_is_grammatically_operational
    ).lower()

    forbidden = (
        "shiftflow",
        "mealmate",
        "stockops",
        "greensense",
        "maintpro",
        "repairlink",
        "greenhouse",
    )

    assert all(
        token not in source
        for token in forbidden
    )
