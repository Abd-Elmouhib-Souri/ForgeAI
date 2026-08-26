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
    return (
        project_context_extractor
        ._explicit_transaction_flow_bounds(
            project_context_extractor
            ._sentences(
                description
            )
        )
    )


def _transaction(
    description: str,
):
    return (
        project_context_extractor
        .extract(
            title="Transaction Continuity Authority",
            description=description,
            industry="Generic Operations",
            target_region="Europe",
            output_language="en",
        )
        .transaction_unit
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


# ==================================================================
# Cross-sentence positive controls.
# ==================================================================


def test_related_publish_payment_remains_continuous() -> None:
    _assert_bounds(
        (
            "The provider publishes a service offer. "
            "The customer pays the service fee."
        ),
        "publier",
        "payer",
    )


def test_related_request_payment_remains_continuous() -> None:
    _assert_bounds(
        (
            "The customer requests a maintenance visit. "
            "The customer pays the maintenance service fee."
        ),
        "demander",
        "payer",
    )


def test_related_booking_payment_remains_continuous() -> None:
    _assert_bounds(
        (
            "The customer books a meeting room. "
            "The customer pays the room fee."
        ),
        "reserver",
        "payer",
    )


def test_related_order_payment_remains_continuous() -> None:
    _assert_bounds(
        (
            "The customer orders office equipment. "
            "The customer pays the equipment price."
        ),
        "commander",
        "payer",
    )


# ==================================================================
# Cross-sentence negative controls.
#
# Later unrelated payment must not be fused into the earlier
# transaction lifecycle.
# ==================================================================


def test_unrelated_payment_does_not_close_publish_transaction() -> None:
    _assert_bounds(
        (
            "The manager publishes the weekly schedule. "
            "The company pays a monthly software subscription."
        ),
        "publier",
        "",
    )


def test_unrelated_payment_does_not_close_request_transaction() -> None:
    _assert_bounds(
        (
            "The customer requests a maintenance visit. "
            "The company pays a monthly accounting subscription."
        ),
        "demander",
        "",
    )


def test_unrelated_payment_does_not_close_booking_transaction() -> None:
    _assert_bounds(
        (
            "The customer books a meeting room. "
            "The company pays a monthly analytics subscription."
        ),
        "reserver",
        "",
    )


def test_unrelated_payment_does_not_close_order_transaction() -> None:
    _assert_bounds(
        (
            "The customer orders office equipment. "
            "The company pays a monthly cloud subscription."
        ),
        "commander",
        "",
    )


# ==================================================================
# Sentence coordination / discourse continuity.
# ==================================================================


def test_same_sentence_generic_reference_remains_continuous() -> None:
    _assert_bounds(
        (
            "The customer requests a maintenance visit "
            "and pays for the service."
        ),
        "demander",
        "payer",
    )


def test_pronominal_reference_remains_continuous() -> None:
    _assert_bounds(
        (
            "The customer orders office equipment "
            "and pays for it."
        ),
        "commander",
        "payer",
    )


def test_same_subject_and_same_sentence_are_not_enough() -> None:
    _assert_bounds(
        (
            "The customer books a meeting room "
            "and pays a monthly analytics subscription."
        ),
        "reserver",
        "",
    )


def test_new_subject_same_sentence_does_not_create_continuity() -> None:
    _assert_bounds(
        (
            "The manager publishes the weekly schedule "
            "and the company pays "
            "a monthly software subscription."
        ),
        "publier",
        "",
    )


# ==================================================================
# Existing lifecycle controls that continuity filtering must preserve.
# ==================================================================


def test_explicit_transaction_close_remains_valid() -> None:
    _assert_bounds(
        (
            "The provider publishes an offer. "
            "The transaction is closed."
        ),
        "publier",
        "cloturer",
    )


def test_publish_then_booking_remains_valid() -> None:
    _assert_bounds(
        (
            "The seller publishes an item. "
            "The buyer books the item."
        ),
        "publier",
        "reserver",
    )


def test_publish_then_order_remains_valid() -> None:
    _assert_bounds(
        (
            "The seller publishes an item. "
            "The buyer orders the item."
        ),
        "publier",
        "commander",
    )


# ==================================================================
# Full-packet authority projection.
# ==================================================================


def test_unrelated_payment_does_not_change_transaction_object() -> None:
    transaction = _transaction(
        (
            "The customer books a meeting room. "
            "The company pays "
            "a monthly analytics subscription."
        )
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key(
            "reserver"
        )
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        transaction.completion_action
        == ""
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == comparison_key(
            "meeting room"
        )
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.value_exchanged
        )
        == comparison_key(
            "meeting room"
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_related_payment_keeps_original_transaction_object() -> None:
    transaction = _transaction(
        (
            "The customer orders office equipment. "
            "The customer pays "
            "the equipment price."
        )
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key(
            "commander"
        )
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key(
            "payer"
        )
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == comparison_key(
            "office equipment"
        )
    ), transaction.model_dump(
        mode="json"
    )


# ==================================================================
# Authority topology.
#
# Continuity belongs inside canonical lifecycle selection, not in:
#
# - Workflow
# - Actor
# - _extract_transaction_unit projection
# ==================================================================


def test_canonical_continuity_authority_exists() -> None:
    assert hasattr(
        ProjectContextExtractor,
        "_transaction_events_are_continuous",
    )


def test_lifecycle_selection_consumes_continuity_authority() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._explicit_transaction_lifecycle_selection
    )

    assert (
        "_transaction_events_are_continuous"
        in source
    )


def test_flow_bounds_projects_canonical_lifecycle_selection_only() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._explicit_transaction_flow_bounds
    )

    assert (
        "_explicit_transaction_lifecycle_selection"
        in source
    )

    assert (
        "_transaction_events_are_continuous"
        not in source
    )

    assert (
        "completion_patterns"
        not in source
    )


def test_projection_layer_does_not_own_continuity_policy() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._extract_transaction_unit
    )

    assert (
        "_transaction_events_are_continuous"
        not in source
    )


def test_workflow_fallback_authority_remains_closed() -> None:
    source = inspect.getsource(
        ProjectContextExtractor
        ._extract_transaction_unit
    )

    assert (
        "workflows[0].action"
        not in source
    )
