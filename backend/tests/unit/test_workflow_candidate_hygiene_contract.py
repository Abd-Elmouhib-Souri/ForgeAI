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


def test_french_indefinite_article_does_not_corrupt_actor_head():
    subject = (
        project_context_extractor
        ._workflow_subject_candidate(
            "Une entreprise propri\u00e9taire "
        )
    )

    assert (
        subject
        == "entreprise propri\u00e9taire"
    )


def test_english_indefinite_article_does_not_corrupt_actor_head():
    subject = (
        project_context_extractor
        ._workflow_subject_candidate(
            "An operator "
        )
    )

    assert subject == "operator"


def test_booking_noun_inside_request_is_not_a_workflow_action():
    sentence = (
        "Une entreprise envoie "
        "une demande de r\u00e9servation."
    )

    result = actions(
        sentence
    )

    assert "reserver" not in result


def test_market_demand_noun_is_not_a_workflow_action():
    sentence = (
        "L'objectif est de v\u00e9rifier "
        "qu'il existe assez d'offre et "
        "de demande sur le march\u00e9."
    )

    result = actions(
        sentence
    )

    assert "demander" not in result


def test_mvp_nominal_request_list_does_not_create_actions():
    sentence = (
        "Le MVP doit permettre : "
        "les demandes de r\u00e9servation ; "
        "le paiement ; "
        "les \u00e9valuations."
    )

    result = actions(
        sentence
    )

    assert "demander" not in result
    assert "reserver" not in result


def test_french_infinitive_after_de_remains_actionable():
    sentence = (
        "La plateforme permet au client "
        "de r\u00e9server un service."
    )

    result = actions(
        sentence
    )

    assert "r\u00e9server" in result



def test_passive_result_receipt_does_not_get_result_bonus():
    initiating_score = (
        project_context_extractor
        ._workflow_score(
            "demande une course",
            "demander",
        )
    )

    receipt_score = (
        project_context_extractor
        ._workflow_score(
            "re\u00e7oit une confirmation",
            "recevoir",
        )
    )

    assert initiating_score == receipt_score


def test_productive_action_can_keep_result_bonus():
    base_score = (
        project_context_extractor
        ._workflow_score(
            "g\u00e9n\u00e8re un document",
            "generer",
        )
    )

    result_score = (
        project_context_extractor
        ._workflow_score(
            "g\u00e9n\u00e8re un rapport",
            "generer",
        )
    )

    assert result_score >= base_score
