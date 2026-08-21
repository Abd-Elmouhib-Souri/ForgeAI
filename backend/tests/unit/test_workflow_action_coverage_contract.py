import pytest

from app.services.project_context_extractor import (
    project_context_extractor,
)


def actions(sentence: str):
    return [
        item["action"]
        for item
        in (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )
    ]


@pytest.mark.parametrize(
    ("sentence", "expected"),
    (
        (
            "The customer searches an item.",
            "rechercher",
        ),
        (
            "The user consults the available offers.",
            "consulter",
        ),
        (
            "The provider accepts the request.",
            "accepter",
        ),
        (
            "The provider rejects the request.",
            "refuser",
        ),
        (
            "The customer pays the order.",
            "payer",
        ),
        (
            "The item is handed over to the customer.",
            "remettre",
        ),
        (
            "The customer returns the item.",
            "retourner",
        ),
        (
            "The transaction is closed.",
            "cloturer",
        ),
        (
            "The users leave a review.",
            "evaluer",
        ),
        (
            "Le client recherche un \u00e9quipement.",
            "rechercher",
        ),
        (
            "Le client consulte les offres.",
            "consulter",
        ),
        (
            "Le fournisseur accepte la demande.",
            "accepter",
        ),
        (
            "Le fournisseur refuse la demande.",
            "refuser",
        ),
        (
            "Le client paie la commande.",
            "payer",
        ),
        (
            "L'\u00e9quipement est remis au client.",
            "remettre",
        ),
        (
            "Le client retourne l'\u00e9quipement.",
            "retourner",
        ),
        (
            "La transaction est cl\u00f4tur\u00e9e.",
            "cloturer",
        ),
        (
            "Les utilisateurs laissent une "
            "\u00e9valuation.",
            "evaluer",
        ),
    ),
)
def test_generic_workflow_actions_are_detected(
    sentence,
    expected,
):
    assert expected in actions(
        sentence
    )


def test_french_search_noun_is_not_an_action():
    assert (
        "rechercher"
        not in actions(
            "La recherche utilisateur "
            "est termin\u00e9e."
        )
    )


def test_english_search_noun_is_not_an_action():
    assert (
        "rechercher"
        not in actions(
            "The search result is available."
        )
    )
