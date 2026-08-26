from __future__ import annotations

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _packet(
    description: str,
):
    return project_context_extractor.extract(
        title="Transaction Workflow Fallback Authority",
        description=description,
        industry="Generic Operations",
        target_region="Europe",
        output_language="en",
    )


def test_pay_only_does_not_invent_transaction_start_en() -> None:
    transaction = _packet(
        (
            "The customer pays "
            "a monthly subscription."
        )
    ).transaction_unit

    assert transaction.initiation_action == ""

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


def test_pay_only_does_not_invent_transaction_start_fr() -> None:
    transaction = _packet(
        (
            "Le client paie "
            "un abonnement mensuel."
        )
    ).transaction_unit

    assert transaction.initiation_action == ""

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


def test_review_workflow_alone_does_not_create_transaction() -> None:
    transaction = _packet(
        (
            "The operator reviews "
            "inventory anomalies."
        )
    ).transaction_unit

    assert transaction.initiation_action == ""
    assert transaction.completion_action == ""
    assert transaction.object == ""
    assert transaction.name == ""
    assert transaction.is_explicit is False


def test_monitor_workflow_alone_does_not_create_transaction() -> None:
    transaction = _packet(
        (
            "The operator monitors "
            "greenhouse conditions."
        )
    ).transaction_unit

    assert transaction.initiation_action == ""
    assert transaction.completion_action == ""
    assert transaction.object == ""
    assert transaction.name == ""
    assert transaction.is_explicit is False


def test_record_workflow_alone_does_not_create_transaction() -> None:
    transaction = _packet(
        (
            "The operator records "
            "stock movements."
        )
    ).transaction_unit

    assert transaction.initiation_action == ""
    assert transaction.completion_action == ""
    assert transaction.object == ""
    assert transaction.name == ""
    assert transaction.is_explicit is False


def test_unrelated_review_does_not_become_start_of_payment_transaction() -> None:
    transaction = _packet(
        (
            "The operator reviews "
            "inventory anomalies. "
            "The company pays "
            "a monthly subscription."
        )
    ).transaction_unit

    assert transaction.initiation_action == ""

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
        != comparison_key(
            "inventory anomalies"
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_request_then_pay_remains_valid_transaction_en() -> None:
    transaction = _packet(
        (
            "The customer requests "
            "a maintenance visit "
            "and pays for the service."
        )
    ).transaction_unit

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key(
            "demander"
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
            "maintenance visit"
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_request_then_pay_remains_valid_transaction_fr() -> None:
    transaction = _packet(
        (
            "Le client demande "
            "une intervention de maintenance "
            "puis paie le service."
        )
    ).transaction_unit

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key(
            "demander"
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


def test_workflow_action_is_not_transaction_start_authority() -> None:
    import inspect

    from app.services.project_context_extractor import (
        ProjectContextExtractor,
    )

    source = inspect.getsource(
        ProjectContextExtractor
        ._extract_transaction_unit
    )

    assert (
        "workflows[0].action"
        not in source
    )
