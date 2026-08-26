from __future__ import annotations

from app.services.project_context_extractor import (
    project_context_extractor,
)


def _workflows(
    sentence: str,
    *,
    output_language: str = "en",
):
    packet = project_context_extractor.extract(
        title="Validate Action Authority Probe",
        description=sentence,
        industry="Generic Operations",
        target_region="Europe",
        output_language=output_language,
    )

    return list(
        packet.priority_workflows
    )


def _actions(
    sentence: str,
    *,
    output_language: str = "en",
) -> list[str]:
    return [
        workflow.action.lower()
        for workflow in _workflows(
            sentence,
            output_language=output_language,
        )
    ]


def test_english_validates_is_workflow_action() -> None:
    actions = _actions(
        "The manager validates the request."
    )

    assert actions == [
        "validate",
    ], actions


def test_english_validate_infinitive_is_workflow_action() -> None:
    actions = _actions(
        "The manager must validate the request."
    )

    assert actions == [
        "validate",
    ], actions


def test_french_valide_is_workflow_action_in_english_output() -> None:
    actions = _actions(
        "Le responsable valide la demande.",
        output_language="en",
    )

    assert actions == [
        "validate",
    ], actions


def test_french_valider_infinitive_is_workflow_action() -> None:
    actions = _actions(
        "Le responsable doit valider la demande.",
        output_language="en",
    )

    assert actions == [
        "validate",
    ], actions


def test_french_valider_localizes_to_french() -> None:
    actions = _actions(
        "Le responsable valide la demande.",
        output_language="fr",
    )

    assert actions == [
        "valider",
    ], actions


def test_decide_de_valider_keeps_downstream_action() -> None:
    workflows = _workflows(
        (
            "Le responsable decide de valider "
            "la demande."
        )
    )

    assert len(
        workflows
    ) == 1, [
        item.model_dump(
            mode="json"
        )
        for item in workflows
    ]

    assert (
        workflows[0].action.lower()
        == "validate"
    )

    assert (
        workflows[0].actor.lower()
        == "responsable"
    )


def test_accented_decide_de_valider_keeps_downstream_action() -> None:
    workflows = _workflows(
        (
            "Le responsable d\u00e9cide de valider "
            "la demande."
        )
    )

    assert len(
        workflows
    ) == 1, [
        item.model_dump(
            mode="json"
        )
        for item in workflows
    ]

    assert (
        workflows[0].action.lower()
        == "validate"
    )

    assert (
        workflows[0].actor.lower()
        == "responsable"
    )


def test_choisit_de_valider_removes_control_wrapper() -> None:
    workflows = _workflows(
        (
            "Le responsable choisit de valider "
            "la demande."
        )
    )

    actions = [
        workflow.action.lower()
        for workflow in workflows
    ]

    assert actions == [
        "validate",
    ], actions

    assert (
        workflows[0].actor.lower()
        == "responsable"
    )


def test_peut_choisir_de_valider_removes_control_wrapper() -> None:
    workflows = _workflows(
        (
            "Le responsable peut choisir de valider "
            "la demande."
        )
    )

    actions = [
        workflow.action.lower()
        for workflow in workflows
    ]

    assert actions == [
        "validate",
    ], actions

    assert (
        workflows[0].actor.lower()
        == "responsable"
    )


def test_approve_semantics_remain_approve() -> None:
    actions = _actions(
        "The manager approves the request."
    )

    assert actions == [
        "approve",
    ], actions


def test_approuve_semantics_remain_approve_in_english() -> None:
    actions = _actions(
        "Le responsable approuve la demande.",
        output_language="en",
    )

    assert actions == [
        "approve",
    ], actions


def test_approuve_semantics_remain_approuver_in_french() -> None:
    actions = _actions(
        "Le responsable approuve la demande.",
        output_language="fr",
    )

    assert actions == [
        "approuver",
    ], actions


def test_validation_noun_is_not_action() -> None:
    occurrences = (
        project_context_extractor
        ._workflow_action_occurrences(
            (
                "The validation of the request "
                "is documented."
            )
        )
    )

    assert not any(
        str(
            item["surface"]
        ).lower().startswith(
            "valid"
        )
        for item in occurrences
    ), [
        (
            item["surface"],
            item["action"],
        )
        for item in occurrences
    ]


def test_validate_authority_is_not_project_specific() -> None:
    import inspect

    source = (
        inspect.getsource(
            project_context_extractor
            ._workflow_action_occurrences
        )
        + inspect.getsource(
            project_context_extractor
            ._localized_workflow_action
        )
    ).lower()

    forbidden = (
        "mealmate",
        "greensense",
        "maintpro",
        "shiftflow",
        "stockops",
        "greenhouse",
        "warehouse",
    )

    assert all(
        token not in source
        for token in forbidden
    ), source
