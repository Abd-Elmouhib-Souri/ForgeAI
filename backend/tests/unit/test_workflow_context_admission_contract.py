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


def test_french_objective_is_non_action_context():
    sentence = (
        "L'objectif initial est de valider "
        "que les clients acceptent de payer."
    )

    assert (
        project_context_extractor
        ._workflow_sentence_is_non_action_context(
            sentence
        )
    )


def test_english_goal_is_non_action_context():
    sentence = (
        "The initial goal is to validate "
        "that customers accept paying."
    )

    assert (
        project_context_extractor
        ._workflow_sentence_is_non_action_context(
            sentence
        )
    )


def test_french_passive_condition_does_not_create_action():
    sentence = (
        "Lorsque la demande est accept\u00e9e, "
        "le client paie la facture."
    )

    assert actions(
        sentence
    ) == [
        "payer",
    ]


def test_english_passive_condition_does_not_create_action():
    sentence = (
        "When the request is accepted, "
        "the customer pays the invoice."
    )

    assert actions(
        sentence
    ) == [
        "payer",
    ]


def test_active_conditional_action_remains_workflow_action():
    sentence = (
        "When the provider accepts the request, "
        "the system sends a confirmation."
    )

    detected = actions(
        sentence
    )

    assert "accepter" in detected
    assert "transmettre" in detected


def test_standalone_passive_business_step_remains_action():
    sentence = (
        "The transaction is closed."
    )

    assert actions(
        sentence
    ) == [
        "cloturer",
    ]



def test_french_compound_passive_condition_does_not_create_action():
    sentence = (
        "Lorsque la demande a \u00e9t\u00e9 accept\u00e9e, "
        "le client paie la facture."
    )

    assert actions(
        sentence
    ) == [
        "payer",
    ]


def test_english_compound_passive_condition_does_not_create_action():
    sentence = (
        "When the request has been accepted, "
        "the customer pays the invoice."
    )

    assert actions(
        sentence
    ) == [
        "payer",
    ]
