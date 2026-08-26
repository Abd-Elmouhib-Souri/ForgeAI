from __future__ import annotations

import pytest

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _raw_pair(
    sentence: str,
):
    publish = None
    reserve = None

    for pattern, action in (
        project_context_extractor
        ._transaction_initiation_patterns()
    ):
        for match in pattern.finditer(
            sentence
        ):
            action_key = comparison_key(
                action
            )

            if (
                action_key == "publier"
                and publish is None
            ):
                publish = (
                    action,
                    match,
                )

            if (
                action_key == "reserver"
                and reserve is None
            ):
                reserve = (
                    action,
                    match,
                )

    assert publish is not None
    assert reserve is not None

    return (
        publish,
        reserve,
    )


def _continuous(
    sentence: str,
) -> bool:
    (
        (
            publish_action,
            publish_match,
        ),
        (
            reserve_action,
            reserve_match,
        ),
    ) = _raw_pair(
        sentence
    )

    return (
        project_context_extractor
        ._transaction_events_are_continuous(
            initiation_sentence=sentence,
            initiation_action=publish_action,
            initiation_match=publish_match,
            completion_sentence=sentence,
            completion_action=reserve_action,
            completion_match=reserve_match,
        )
    )


@pytest.mark.parametrize(
    "sentence",
    (
        (
            "Le vendeur publie un lot et "
            "l'acheteur le r\u00e9serve "
            "apr\u00e8s comparaison."
        ),
        (
            "Le vendeur publie une offre et "
            "l'acheteur la r\u00e9serve "
            "apr\u00e8s comparaison."
        ),
        (
            "Le vendeur publie des lots et "
            "l'acheteur les r\u00e9serve "
            "apr\u00e8s comparaison."
        ),
    ),
)
def test_preverbal_object_clitic_is_strong_transaction_reference(
    sentence: str,
) -> None:
    assert _continuous(
        sentence
    ) is True


def test_direct_object_control_remains_continuous() -> None:
    assert (
        _continuous(
            (
                "Le vendeur publie un lot et "
                "l'acheteur r\u00e9serve "
                "le lot apr\u00e8s comparaison."
            )
        )
        is True
    )



def test_clitic_does_not_bridge_an_intervening_unrelated_object_action() -> None:
    sentence = (
        "Le vendeur publie un lot et "
        "l'acheteur examine une salle "
        "puis la r\u00e9serve."
    )

    assert (
        _continuous(
            sentence
        )
        is False
    )


def test_plural_clitic_does_not_bridge_an_intervening_unrelated_object_action() -> None:
    sentence = (
        "Le vendeur publie des lots et "
        "l'acheteur examine des machines "
        "puis les r\u00e9serve."
    )

    assert (
        _continuous(
            sentence
        )
        is False
    )
