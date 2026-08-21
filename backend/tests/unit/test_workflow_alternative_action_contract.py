from app.services.project_context_extractor import (
    project_context_extractor,
)


def workflow_sentences(
    description: str,
    *,
    language: str,
):
    packet = (
        project_context_extractor
        .extract(
            title="AlternativeActionContract",
            description=description,
            industry="generic service",
            target_region="Europe",
            output_language=language,
        )
    )

    return [
        workflow.sentence
        for workflow
        in packet.priority_workflows
    ]


def test_english_or_actions_preserve_shared_object():
    workflows = workflow_sentences(
        (
            "An operator reviews a request, "
            "then approves or rejects each record."
        ),
        language="en",
    )

    assert (
        "approve or reject each record"
        in workflows
    )


def test_french_ou_actions_preserve_shared_object():
    workflows = workflow_sentences(
        (
            "Un op\u00e9rateur examine une demande, "
            "puis accepte ou refuse chaque dossier."
        ),
        language="fr",
    )

    assert (
        "accepter ou refuser chaque dossier"
        in workflows
    )


def test_sequential_and_actions_remain_separate():
    workflows = workflow_sentences(
        (
            "An operator reviews a record "
            "and exports the result."
        ),
        language="en",
    )

    joined = " | ".join(
        workflows
    )

    assert "review" in joined
    assert "export" in joined
