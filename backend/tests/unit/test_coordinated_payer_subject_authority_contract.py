from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _payers(
    sentence: str,
) -> list[str]:
    return [
        comparison_key(
            name
        )
        for name, role in (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )
        if role == ActorRole.PAYER
    ]


def _subject(
    prefix: str,
) -> str:
    return comparison_key(
        project_context_extractor
        ._workflow_subject_candidate(
            prefix
        )
    )


def test_then_pay_keeps_actor_subject() -> None:
    assert _payers(
        (
            "The customer then pays "
            "for the completed service."
        )
    ) == [
        "customer",
    ]


def test_book_and_pay_inherits_same_subject() -> None:
    assert _payers(
        (
            "The customer books a service "
            "and pays for the booking."
        )
    ) == [
        "customer",
    ]


def test_order_and_pay_inherits_same_subject() -> None:
    assert _payers(
        (
            "The customer orders an item "
            "and pays for the order."
        )
    ) == [
        "customer",
    ]


def test_request_and_pay_inherits_same_subject() -> None:
    assert _payers(
        (
            "The customer requests a service "
            "and pays after completion."
        )
    ) == [
        "customer",
    ]


def test_review_and_pay_inherits_same_subject() -> None:
    assert _payers(
        (
            "The manager reviews the proposal "
            "and pays the invoice."
        )
    ) == [
        "manager",
    ]


def test_new_subject_after_coordination_wins() -> None:
    assert _payers(
        (
            "The customer books a service "
            "and the company pays the fee."
        )
    ) == [
        "company",
    ]


def test_compound_subject_is_not_split() -> None:
    assert _payers(
        (
            "The sales and marketing team "
            "pays the subscription."
        )
    ) == [
        "sales and marketing team",
    ]


def test_modal_payment_remains_unchanged() -> None:
    assert _payers(
        (
            "The household user can choose to pay "
            "for the premium plan."
        )
    ) == [
        "household user",
    ]


def test_subject_candidate_removes_terminal_then() -> None:
    assert _subject(
        "The customer then "
    ) == "customer"


def test_subject_candidate_inherits_before_terminal_and() -> None:
    assert _subject(
        (
            "The customer books a service "
            "and "
        )
    ) == "customer"


def test_subject_candidate_inherits_before_terminal_then() -> None:
    assert _subject(
        (
            "The customer requests a service "
            "then "
        )
    ) == "customer"


def test_french_reserve_et_paie_inherits_subject() -> None:
    assert _payers(
        (
            "Le client reserve un service "
            "et paie la facture."
        )
    ) == [
        "client",
    ]


def test_french_demande_puis_paie_inherits_subject() -> None:
    assert _payers(
        (
            "Le client demande une intervention "
            "puis paie le service."
        )
    ) == [
        "client",
    ]


def test_french_new_subject_after_coordination_wins() -> None:
    assert _payers(
        (
            "Le client reserve un service "
            "et l'entreprise paie la facture."
        )
    ) == [
        "entreprise",
    ]


def test_authority_is_not_project_specific() -> None:
    import inspect

    source = (
        inspect.getsource(
            project_context_extractor
            ._workflow_subject_candidate
        )
        + inspect.getsource(
            project_context_extractor
            ._declared_actor_roles
        )
    ).lower()

    forbidden = (
        "mealmate",
        "greensense",
        "maintpro",
        "shiftflow",
        "stockops",
        "greenhouse",
    )

    assert all(
        token not in source
        for token in forbidden
    )
