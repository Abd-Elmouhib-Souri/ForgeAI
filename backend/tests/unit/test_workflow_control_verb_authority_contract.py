from __future__ import annotations

from app.services.project_context_extractor import (
    project_context_extractor,
)


def _workflows(
    sentence: str,
):
    packet = project_context_extractor.extract(
        title="Control Verb Workflow Probe",
        description=sentence,
        industry="Generic Product / Service",
        target_region="Europe",
        output_language="en",
    )

    return list(
        packet.priority_workflows
    )


def _actions(
    sentence: str,
) -> list[str]:
    return [
        workflow.action.lower()
        for workflow in _workflows(
            sentence
        )
    ]


def _objects(
    sentence: str,
) -> list[str]:
    return [
        workflow.object.lower()
        for workflow in _workflows(
            sentence
        )
    ]


def test_can_choose_to_pay_does_not_create_choose_workflow() -> None:
    sentence = (
        "The household user can choose to pay "
        "for a premium subscription."
    )

    actions = _actions(
        sentence
    )

    assert "choose" not in actions, actions
    assert "pay" in actions, actions


def test_choose_to_pay_does_not_create_choose_workflow() -> None:
    sentence = (
        "The household user chooses to pay "
        "for a premium subscription."
    )

    actions = _actions(
        sentence
    )

    assert "choose" not in actions, actions
    assert "pay" in actions, actions


def test_may_decide_to_pay_does_not_create_decide_workflow() -> None:
    sentence = (
        "The household user may decide to pay "
        "for the premium plan."
    )

    actions = _actions(
        sentence
    )

    assert "decide" not in actions, actions
    assert "pay" in actions, actions


def test_decides_to_approve_keeps_only_business_action() -> None:
    sentence = (
        "The manager decides to approve "
        "the request."
    )

    actions = _actions(
        sentence
    )

    assert "decide" not in actions, actions
    assert "approve" in actions, actions


def test_choose_direct_object_remains_real_workflow() -> None:
    sentence = (
        "The user chooses meals "
        "for the weekly plan."
    )

    actions = _actions(
        sentence
    )

    assert "choose" in actions, actions


def test_modal_choose_direct_object_remains_real_workflow() -> None:
    sentence = (
        "The user can choose a meal "
        "from the weekly plan."
    )

    actions = _actions(
        sentence
    )

    assert "choose" in actions, actions


def test_choose_between_options_remains_real_workflow() -> None:
    sentence = (
        "The user chooses between "
        "the available plans."
    )

    actions = _actions(
        sentence
    )

    assert "choose" in actions, actions


def test_control_verb_never_produces_object_to() -> None:
    sentence = (
        "The household user can choose to pay "
        "for a premium subscription."
    )

    objects = _objects(
        sentence
    )

    assert "to" not in objects, objects


def test_decides_to_approve_preserves_actor_subject() -> None:
    sentence = (
        "The manager decides to approve "
        "the request."
    )

    workflows = _workflows(
        sentence
    )

    approve = [
        workflow
        for workflow in workflows
        if workflow.action.lower()
        == "approve"
    ]

    assert len(
        approve
    ) == 1, [
        workflow.model_dump(
            mode="json"
        )
        for workflow in workflows
    ]

    assert (
        approve[0].actor.lower()
        == "manager"
    ), approve[0].model_dump(
        mode="json"
    )


def test_can_choose_to_pay_preserves_actor_on_pay() -> None:
    sentence = (
        "The household user can choose to pay "
        "for a premium subscription."
    )

    workflows = _workflows(
        sentence
    )

    pay = [
        workflow
        for workflow in workflows
        if workflow.action.lower()
        == "pay"
    ]

    assert len(
        pay
    ) == 1, [
        workflow.model_dump(
            mode="json"
        )
        for workflow in workflows
    ]

    assert (
        pay[0].actor.lower()
        == "household user"
    ), pay[0].model_dump(
        mode="json"
    )


def test_chooses_to_approve_preserves_actor_subject() -> None:
    sentence = (
        "The manager chooses to approve "
        "the request."
    )

    workflows = _workflows(
        sentence
    )

    approve = [
        workflow
        for workflow in workflows
        if workflow.action.lower()
        == "approve"
    ]

    assert len(
        approve
    ) == 1, [
        workflow.model_dump(
            mode="json"
        )
        for workflow in workflows
    ]

    assert (
        approve[0].actor.lower()
        == "manager"
    ), approve[0].model_dump(
        mode="json"
    )



def test_control_filter_is_not_project_specific() -> None:
    import inspect

    source = inspect.getsource(
        project_context_extractor
        ._extract_workflows
    ).lower()

    forbidden = (
        "mealmate",
        "greensense",
        "maintpro",
        "shiftflow",
        "stockops",
        "household user",
    )

    assert all(
        value not in source
        for value in forbidden
    ), source
