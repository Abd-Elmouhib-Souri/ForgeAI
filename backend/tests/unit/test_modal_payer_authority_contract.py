from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _payers(
    description: str,
) -> list[str]:
    packet = project_context_extractor.extract(
        title="Modal Payer Contract",
        description=description,
        industry="Generic Subscription / Service",
        target_region="Europe",
        output_language="en",
    )

    return [
        comparison_key(
            actor.name
        )
        for actor in packet.actors
        if actor.role == ActorRole.PAYER
    ]


def _assert_only_payer(
    description: str,
    expected: str,
) -> None:
    payers = _payers(
        description
    )

    assert payers == [
        comparison_key(
            expected
        )
    ], (
        description,
        payers,
    )


def test_direct_present_payment_keeps_subject() -> None:
    _assert_only_payer(
        (
            "The household user pays "
            "the monthly subscription."
        ),
        "household user",
    )


def test_direct_future_payment_keeps_subject() -> None:
    _assert_only_payer(
        (
            "The household user will pay "
            "the monthly subscription."
        ),
        "household user",
    )


def test_can_pay_keeps_only_actor_subject() -> None:
    _assert_only_payer(
        (
            "The household user can pay "
            "for the premium plan."
        ),
        "household user",
    )


def test_may_pay_keeps_only_actor_subject() -> None:
    _assert_only_payer(
        (
            "The household user may pay "
            "for the premium plan."
        ),
        "household user",
    )


def test_can_choose_to_pay_keeps_only_actor_subject() -> None:
    _assert_only_payer(
        (
            "The household user can choose to pay "
            "for a monthly premium subscription."
        ),
        "household user",
    )


def test_chooses_to_pay_keeps_only_actor_subject() -> None:
    _assert_only_payer(
        (
            "The household user chooses to pay "
            "for the premium plan."
        ),
        "household user",
    )


def test_decides_to_pay_keeps_only_actor_subject() -> None:
    _assert_only_payer(
        (
            "The household user decides to pay "
            "for the premium plan."
        ),
        "household user",
    )


def test_may_decide_to_pay_keeps_only_actor_subject() -> None:
    _assert_only_payer(
        (
            "The household user may decide to pay "
            "for the premium plan."
        ),
        "household user",
    )


def test_platform_allowing_users_to_pay_is_not_payer() -> None:
    assert not _payers(
        (
            "The platform allows users to pay "
            "for the service."
        )
    )


def test_system_enabling_customers_to_pay_is_not_payer() -> None:
    assert not _payers(
        (
            "The system enables customers to pay online."
        )
    )


def test_platform_letting_customers_pay_is_not_payer() -> None:
    assert not _payers(
        (
            "The platform lets customers pay online."
        )
    )


def test_direct_negative_payment_is_not_payer() -> None:
    assert not _payers(
        (
            "The household user does not pay "
            "for the free plan."
        )
    )


def test_modal_negative_choice_is_not_payer() -> None:
    assert not _payers(
        (
            "The household user can choose not to pay "
            "for the free plan."
        )
    )


def test_modal_negative_may_not_pay_is_not_payer() -> None:
    assert not _payers(
        (
            "The household user may not pay "
            "for the free plan."
        )
    )
