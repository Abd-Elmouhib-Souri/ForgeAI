from __future__ import annotations

from app.services.project_context_extractor import (
    project_context_extractor,
)


def _surfaces(
    sentence: str,
) -> list[str]:
    return [
        str(
            item.get("surface")
            or ""
        ).strip().lower()
        for item
        in (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )
    ]


def _actions(
    sentence: str,
) -> list[str]:
    return [
        str(
            item.get("action")
            or ""
        ).strip().lower()
        for item
        in (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )
    ]


def _packet(
    sentence: str,
):
    return (
        project_context_extractor.extract(
            title="Workflow Grammar Probe",
            description=sentence,
            industry="Generic Operations",
            target_region="Europe",
            output_language="en",
        )
    )


def test_copular_monitoring_modifier_is_not_action() -> None:
    sentence = (
        "The product is an IoT monitoring device "
        "for industrial facilities."
    )

    surfaces = _surfaces(
        sentence
    )

    assert not any(
        surface.startswith(
            "monitor"
        )
        for surface in surfaces
    ), surfaces


def test_progressive_monitoring_predicate_remains_action() -> None:
    sentence = (
        "The application is monitoring "
        "operational conditions."
    )

    surfaces = _surfaces(
        sentence
    )

    assert any(
        surface.startswith(
            "monitor"
        )
        for surface in surfaces
    ), surfaces


def test_alert_noun_after_review_is_not_second_action() -> None:
    sentence = (
        "The operations manager reviews "
        "sensor alerts."
    )

    surfaces = _surfaces(
        sentence
    )

    assert any(
        surface.startswith(
            "review"
        )
        for surface in surfaces
    ), surfaces

    assert not any(
        surface.startswith(
            "alert"
        )
        for surface in surfaces
    ), surfaces


def test_coordinated_alert_predicate_remains_action() -> None:
    sentence = (
        "The operations manager reviews "
        "and alerts the supervisor."
    )

    surfaces = _surfaces(
        sentence
    )

    assert any(
        surface.startswith(
            "review"
        )
        for surface in surfaces
    ), surfaces

    assert any(
        surface.startswith(
            "alert"
        )
        for surface in surfaces
    ), surfaces


def test_request_noun_after_review_is_not_second_action() -> None:
    sentence = (
        "The operations manager reviews "
        "service requests."
    )

    surfaces = _surfaces(
        sentence
    )

    assert any(
        surface.startswith(
            "review"
        )
        for surface in surfaces
    ), surfaces

    assert not any(
        surface.startswith(
            "request"
        )
        for surface in surfaces
    ), surfaces


def test_direct_request_predicate_remains_action() -> None:
    sentence = (
        "The customer requests a service."
    )

    surfaces = _surfaces(
        sentence
    )

    assert any(
        surface.startswith(
            "request"
        )
        for surface in surfaces
    ), surfaces


def test_packet_rejects_nominal_monitoring_workflow() -> None:
    packet = _packet(
        (
            "The product is an IoT monitoring "
            "device for industrial facilities."
        )
    )

    workflows = list(
        packet.priority_workflows
    )

    assert not any(
        workflow.action.lower()
        == "monitor"
        for workflow in workflows
    ), [
        workflow.model_dump(
            mode="json"
        )
        for workflow in workflows
    ]


def test_packet_rejects_alert_noun_but_keeps_review() -> None:
    packet = _packet(
        (
            "The operations manager reviews "
            "sensor alerts and checks "
            "operational conditions."
        )
    )

    workflows = list(
        packet.priority_workflows
    )

    actions = [
        workflow.action.lower()
        for workflow in workflows
    ]

    assert "review" in actions, [
        workflow.model_dump(
            mode="json"
        )
        for workflow in workflows
    ]

    assert "alert" not in actions, [
        workflow.model_dump(
            mode="json"
        )
        for workflow in workflows
    ]


def test_nominal_filter_is_not_sector_specific() -> None:
    source = (
        __import__(
            "inspect"
        )
        .getsource(
            project_context_extractor
            ._workflow_match_is_nominal
        )
        .lower()
    )

    forbidden = (
        "greenhouse",
        "farm manager",
        "greensense",
        "warehouse",
        "maintpro",
        "mealmate",
        "shiftflow",
    )

    assert all(
        value not in source
        for value in forbidden
    ), source
