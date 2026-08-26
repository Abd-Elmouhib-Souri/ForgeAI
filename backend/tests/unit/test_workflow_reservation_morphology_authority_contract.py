from __future__ import annotations

from app.services.project_context_extractor import (
    project_context_extractor,
)


def _occurrences(
    sentence: str,
):
    return (
        project_context_extractor
        ._workflow_action_occurrences(
            sentence
        )
    )


def _actions(
    sentence: str,
) -> list[str]:
    return [
        str(
            item["action"]
        )
        for item in _occurrences(
            sentence
        )
    ]


def _workflow_actions(
    sentence: str,
) -> list[str]:
    packet = project_context_extractor.extract(
        title="Reservation Morphology Probe",
        description=sentence,
        industry="Generic Service",
        target_region="Europe",
        output_language="en",
    )

    return [
        workflow.action.lower()
        for workflow
        in packet.priority_workflows
    ]


def test_ascii_present_reserve_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client reserve un service."
    ) == [
        "book",
    ]


def test_accented_present_reserve_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client r\u00e9serve un service."
    ) == [
        "book",
    ]


def test_ascii_infinitive_reserver_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client doit reserver un service."
    ) == [
        "book",
    ]


def test_accented_infinitive_reserver_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client doit r\u00e9server un service."
    ) == [
        "book",
    ]


def test_ascii_plural_reservent_is_booking_action() -> None:
    assert _workflow_actions(
        "Les clients reservent un service."
    ) == [
        "book",
    ]


def test_accented_plural_reservent_is_booking_action() -> None:
    assert _workflow_actions(
        "Les clients r\u00e9servent un service."
    ) == [
        "book",
    ]


def test_ascii_future_reservera_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client reservera un service."
    ) == [
        "book",
    ]


def test_accented_future_reservera_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client r\u00e9servera un service."
    ) == [
        "book",
    ]


def test_ascii_imperfect_reservait_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client reservait un service."
    ) == [
        "book",
    ]


def test_accented_imperfect_reservait_is_booking_action() -> None:
    assert _workflow_actions(
        "Le client r\u00e9servait un service."
    ) == [
        "book",
    ]


def test_ascii_reserve_noun_with_determiner_is_not_action() -> None:
    assert _actions(
        "Une reserve de stock est disponible."
    ) == []


def test_accented_reserve_noun_with_determiner_is_not_action() -> None:
    assert _actions(
        "Une r\u00e9serve de stock est disponible."
    ) == []


def test_ascii_reserve_object_is_not_second_action() -> None:
    actions = _workflow_actions(
        (
            "Le responsable examine "
            "la reserve disponible."
        )
    )

    assert actions == [
        "review",
    ], actions


def test_accented_reserve_object_is_not_second_action() -> None:
    actions = _workflow_actions(
        (
            "Le responsable examine "
            "la r\u00e9serve disponible."
        )
    )

    assert actions == [
        "review",
    ], actions


def test_reservation_noun_remains_nominal() -> None:
    assert _actions(
        (
            "La r\u00e9servation du service "
            "est obligatoire."
        )
    ) == []


def test_ascii_reservation_noun_remains_nominal() -> None:
    assert _actions(
        (
            "La reservation du service "
            "est obligatoire."
        )
    ) == []


def test_english_booking_noun_remains_nominal() -> None:
    assert _actions(
        (
            "The booking of the service "
            "is documented."
        )
    ) == []


def test_english_book_action_remains_supported() -> None:
    assert _workflow_actions(
        "The customer books a service."
    ) == [
        "book",
    ]


def test_authority_is_not_project_specific() -> None:
    import inspect

    from app.services.project_context_extractor import (
        ProjectContextExtractor,
    )

    source = inspect.getsource(
        ProjectContextExtractor
    ).lower()

    forbidden = (
        "mealmate",
        "greensense",
        "maintpro",
        "shiftflow",
        "stockops",
        "greenhouse",
    )

    assert all(
        token not in source[
            source.find(
                "action_patterns"
            ):
            source.find(
                "action_priority"
            )
        ]
        for token in forbidden
    )
