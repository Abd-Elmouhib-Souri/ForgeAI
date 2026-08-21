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
    "sentence",
    (
        "Le client renseigne ses informations.",
        "Le client renseignera ses informations.",
        "Le client remplit le formulaire.",
        "Les utilisateurs remplissent le formulaire.",
        "The user enters the information.",
        "The user entered the information.",
        "The user fills in the form.",
        "The users filled in the form.",
    ),
)
def test_generic_data_entry_actions_are_detected(
    sentence,
):
    assert "renseigner" in actions(
        sentence
    )


def test_french_coordinated_data_entry_is_separate_workflow():
    packet = (
        project_context_extractor
        .extract(
            title="DataEntryContract",
            description=(
                "Un op\u00e9rateur cr\u00e9e un dossier, "
                "renseigne les informations requises."
            ),
            industry="Service professionnel",
            target_region="France",
            output_language="fr",
        )
    )

    workflows = {
        workflow.action:
            workflow
        for workflow
        in packet.priority_workflows
    }

    assert "cr\u00e9er" in workflows
    assert "renseigner" in workflows

    assert (
        workflows[
            "cr\u00e9er"
        ].object
        == "un dossier"
    )

    assert (
        workflows[
            "renseigner"
        ].object
        == "les informations requises"
    )


def test_english_coordinated_data_entry_is_separate_workflow():
    packet = (
        project_context_extractor
        .extract(
            title="DataEntryContract",
            description=(
                "An operator creates a record, "
                "then enters the required information."
            ),
            industry="Professional service",
            target_region="Europe",
            output_language="en",
        )
    )

    workflows = {
        workflow.action:
            workflow
        for workflow
        in packet.priority_workflows
    }

    assert "create" in workflows
    assert "enter" in workflows

    assert (
        workflows[
            "create"
        ].object
        == "a record"
    )

    assert (
        workflows[
            "enter"
        ].object
        == "the required information"
    )


def test_bare_pour_before_known_action_can_be_purpose():
    sentence = (
        "Le syst\u00e8me cr\u00e9e un formulaire "
        "pour renseigner les donn\u00e9es."
    )

    occurrence = next(
        item
        for item
        in (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )
        if item["action"] == "creer"
    )

    match = occurrence[
        "match"
    ]

    assert (
        project_context_extractor
        ._action_object(
            sentence,
            match,
        )
        == "un formulaire"
    )

    assert (
        project_context_extractor
        ._result_after_action(
            sentence,
            match,
            occurrence["action"],
        )
        == "renseigner les donn\u00e9es"
    )
