from __future__ import annotations

import pytest

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _reservation_pattern():
    matches = [
        (pattern, action)
        for pattern, action
        in project_context_extractor
        ._transaction_initiation_patterns()
        if comparison_key(action) == "reserver"
    ]

    assert len(matches) == 1

    return matches[0]


def _grammar_state(
    sentence: str,
):
    pattern, action = _reservation_pattern()

    match = pattern.search(
        sentence
    )

    assert match is not None

    item = {
        "pattern": match.re,
        "action": action,
        "match": match,
        "surface": match.group(0),
    }

    return {
        "nominal":
            project_context_extractor
            ._workflow_match_is_nominal(
                sentence=sentence,
                item=item,
                accepted=[],
            ),

        "transaction_grammar":
            project_context_extractor
            ._transaction_match_is_grammatically_operational(
                sentence=sentence,
                action=action,
                action_match=match,
            ),

        "action_candidate":
            project_context_extractor
            ._transaction_action_candidate(
                sentence,
                pattern,
                action,
            ),

        "completion_gate":
            project_context_extractor
            ._transaction_completion_candidate_is_operational(
                sentence=sentence,
                action="reserver",
                action_match=match,
            ),
    }


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
def test_french_preverbal_object_clitic_does_not_make_predicate_nominal(
    sentence: str,
) -> None:
    state = _grammar_state(
        sentence
    )

    assert state["nominal"] is False
    assert state["transaction_grammar"] is True
    assert state["action_candidate"] is not None
    assert state["completion_gate"] is True


def test_workflow_occurrence_keeps_clitic_reservation_predicate() -> None:
    sentence = (
        "Le vendeur publie un lot et "
        "l'acheteur le r\u00e9serve "
        "apr\u00e8s comparaison."
    )

    occurrences = (
        project_context_extractor
        ._workflow_action_occurrences(
            sentence
        )
    )

    actions = {
        comparison_key(
            item["action"]
        )
        for item in occurrences
    }

    assert "publier" in actions
    assert "reserver" in actions


def test_direct_object_reservation_remains_predicate() -> None:
    sentence = (
        "L'acheteur r\u00e9serve "
        "un lot apr\u00e8s comparaison."
    )

    state = _grammar_state(
        sentence
    )

    assert state["nominal"] is False
    assert state["transaction_grammar"] is True
    assert state["action_candidate"] is not None
    assert state["completion_gate"] is True


def test_nominal_reserve_remains_nominal() -> None:
    sentence = (
        "La r\u00e9serve du lot "
        "est confirm\u00e9e."
    )

    state = _grammar_state(
        sentence
    )

    assert state["nominal"] is True
    assert state["transaction_grammar"] is False
    assert state["action_candidate"] is None
    assert state["completion_gate"] is False
