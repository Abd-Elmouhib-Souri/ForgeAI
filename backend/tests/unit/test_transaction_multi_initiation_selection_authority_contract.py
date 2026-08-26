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


def _transaction(
    description: str,
):
    return (
        project_context_extractor
        .extract(
            title="Multi Initiation Authority",
            description=description,
            industry="Generic Operations",
            target_region="Europe",
            output_language="en",
        )
        .transaction_unit
    )


def test_complete_later_publish_booking_lifecycle_outranks_orphan_publish() -> None:
    description = (
        "A manager publishes the weekly schedule. "
        "A provider publishes a service offer. "
        "A customer books the service offer."
    )

    start, completion = _bounds(
        description
    )

    assert (
        comparison_key(start)
        == "publier"
    )

    assert (
        comparison_key(completion)
        == "reserver"
    )


def test_selected_transaction_object_belongs_to_complete_lifecycle() -> None:
    description = (
        "A manager publishes the weekly schedule. "
        "A provider publishes a service offer. "
        "A customer books the service offer."
    )

    transaction = _transaction(
        description
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == "publier"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == "reserver"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == "service offer"
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.value_exchanged
        )
        == "service offer"
    ), transaction.model_dump(
        mode="json"
    )


def test_complete_later_lifecycle_can_use_different_initiation_family() -> None:
    description = (
        "A customer requests general information. "
        "A provider publishes an equipment offer. "
        "A buyer orders the equipment offer."
    )

    transaction = _transaction(
        description
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == "publier"
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == "commander"
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == "equipment offer"
    ), transaction.model_dump(
        mode="json"
    )


def test_existing_complete_earliest_lifecycle_is_preserved() -> None:
    description = (
        "A seller publishes an equipment offer. "
        "A buyer orders the equipment offer. "
        "A manager later publishes the weekly schedule."
    )

    transaction = _transaction(
        description
    )

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == "publier"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == "commander"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == "equipment offer"
    ), transaction.model_dump(
        mode="json"
    )


def test_orphan_initiation_is_preserved_when_no_complete_lifecycle_exists() -> None:
    description = (
        "A manager publishes the weekly schedule. "
        "A customer requests general information."
    )

    start, completion = _bounds(
        description
    )

    assert (
        comparison_key(start)
        == "publier"
    )

    assert completion == ""
