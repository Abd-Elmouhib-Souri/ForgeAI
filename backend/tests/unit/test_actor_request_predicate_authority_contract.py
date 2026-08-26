from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _users(
    sentence: str,
) -> list[str]:
    return [
        comparison_key(
            name
        )
        for name, role in (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )
        if role == ActorRole.USER
    ]


def _packet_actor_names(
    sentence: str,
    *,
    language: str = "en",
) -> list[str]:
    packet = project_context_extractor.extract(
        title="Request Predicate Authority Probe",
        description=sentence,
        industry="Generic Operations",
        target_region="Europe",
        output_language=language,
    )

    return [
        comparison_key(
            actor.name
        )
        for actor in packet.actors
    ]


def test_direct_request_predicate_materializes_subject() -> None:
    users = _users(
        (
            "The facility manager requests "
            "a maintenance visit."
        )
    )

    assert users == [
        "facility manager",
    ], users


def test_approve_the_request_does_not_backtrack_subject() -> None:
    users = _users(
        (
            "The manager approves "
            "the request."
        )
    )

    assert users == [], users


def test_approve_a_request_does_not_backtrack_subject() -> None:
    users = _users(
        (
            "The manager approves "
            "a request."
        )
    )

    assert users == [], users


def test_decides_to_approve_request_does_not_create_false_actor() -> None:
    users = _users(
        (
            "The manager decides to approve "
            "the request."
        )
    )

    assert users == [], users


def test_chooses_to_approve_request_does_not_create_false_actor() -> None:
    users = _users(
        (
            "The manager chooses to approve "
            "the request."
        )
    )

    assert users == [], users


def test_send_service_request_keeps_only_real_subject() -> None:
    users = _users(
        (
            "The customer sends "
            "a service request."
        )
    )

    assert users == [
        "customer",
    ], users


def test_review_service_requests_keeps_review_subject_only() -> None:
    users = _users(
        (
            "The manager reviews "
            "service requests."
        )
    )

    assert users == [
        "manager",
    ], users


def test_packet_does_not_persist_control_clause_as_actor() -> None:
    actor_names = _packet_actor_names(
        (
            "The manager decides to approve "
            "the request."
        )
    )

    assert all(
        "approve" not in name
        and "decide" not in name
        for name in actor_names
    ), actor_names


def test_french_direct_demande_predicate_materializes_subject() -> None:
    users = _users(
        (
            "Le responsable demande "
            "une intervention."
        )
    )

    assert users == [
        "responsable",
    ], users


def test_french_approve_demande_noun_does_not_backtrack_subject() -> None:
    users = _users(
        (
            "Le responsable valide "
            "la demande."
        )
    )

    assert users == [
        "responsable",
    ], users


def test_french_send_demande_keeps_only_real_subject() -> None:
    users = _users(
        (
            "Le client envoie "
            "une demande de service."
        )
    )

    assert users == [
        "client",
    ], users


def test_request_authority_is_not_project_specific() -> None:
    import inspect

    source = inspect.getsource(
        project_context_extractor
        ._declared_actor_roles
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
        token not in source
        for token in forbidden
    ), source
