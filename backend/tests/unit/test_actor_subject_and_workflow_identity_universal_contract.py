
from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _extractor() -> ProjectContextExtractor:

    return ProjectContextExtractor()


def _role_pairs(
    description: str,
):

    return [
        (
            comparison_key(
                name
            ),
            role,
        )
        for name, role
        in (
            _extractor()
            ._declared_actor_roles(
                description
            )
        )
    ]


def _group_pairs(
    description: str,
):

    return [
        (
            comparison_key(
                name
            ),
            role,
        )
        for name, role
        in (
            _extractor()
            ._declared_actor_groups(
                description
            )
        )
    ]


def _packet(
    description: str,
):

    return (
        _extractor()
        .extract(
            title="Neutral Workflow Product",
            description=description,
            industry="Business software",
            target_region="International",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )


def _actor_keys(
    packet,
):

    return [
        comparison_key(
            actor.name
        )
        for actor in (
            packet.actors
            or []
        )
        if comparison_key(
            actor.name
        )
    ]


# ============================================================================
# GREEN CONTROLS
# ============================================================================

def test_atomic_actor_identity_remains_valid_control() -> None:

    assert (
        _extractor()
        ._clean_actor(
            "service coordinators"
        )
        ==
        "service coordinators"
    )


def test_existing_actor_first_primary_user_grammar_remains_green_control() -> None:

    pairs = _group_pairs(
        (
            "Operations managers are "
            "the primary users."
        )
    )

    assert (
        "operations managers",
        ActorRole.USER,
    ) in pairs


def test_existing_direct_request_actor_authority_remains_green_control() -> None:

    pairs = _role_pairs(
        (
            "The customer sends "
            "a service request."
        )
    )

    assert (
        "customer",
        ActorRole.USER,
    ) in pairs


# ============================================================================
# RED 1 ? MODAL OPERATIONAL SUBJECT
# ============================================================================

def test_modal_request_relation_materializes_atomic_actor_subject() -> None:

    pairs = _role_pairs(
        (
            "Service recipients can submit maintenance requests "
            "and follow their status."
        )
    )

    assert (
        "service recipients",
        ActorRole.USER,
    ) in pairs

    assert not any(
        "can submit"
        in name
        for name, _
        in pairs
    )


def test_modal_request_subject_survives_full_packet() -> None:

    packet = _packet(
        (
            "A workflow product supports service organizations. "
            "Service recipients can submit maintenance requests "
            "and follow their status."
        )
    )

    actors = _actor_keys(
        packet
    )

    assert (
        "service recipients"
        in actors
    )

    assert not any(
        "can submit"
        in value
        for value in actors
    )


# ============================================================================
# RED 2 ? ACTOR-FIRST COORDINATED MAIN DAILY USERS
# ============================================================================

def test_coordinated_main_daily_user_subject_materializes_every_member() -> None:

    pairs = _group_pairs(
        (
            "Operations managers and service coordinators "
            "are the main daily users of the platform."
        )
    )

    assert (
        "operations managers",
        ActorRole.USER,
    ) in pairs

    assert (
        "service coordinators",
        ActorRole.USER,
    ) in pairs


def test_coordinated_main_daily_users_survive_full_packet() -> None:

    packet = _packet(
        (
            "A workflow product supports service organizations. "
            "Operations managers and service coordinators "
            "are the main daily users of the platform."
        )
    )

    actors = _actor_keys(
        packet
    )

    assert (
        "operations managers"
        in actors
    )

    assert (
        "service coordinators"
        in actors
    )


# ============================================================================
# RED 3 ? LEADING COORDINATION MARKER
# ============================================================================

def test_leading_coordination_marker_is_not_part_of_actor_identity() -> None:

    cleaned = (
        _extractor()
        ._clean_actor(
            "and other service providers"
        )
    )

    assert (
        comparison_key(
            cleaned
        )
        ==
        "other service providers"
    )


def test_provider_actor_cannot_survive_with_leading_coordination_marker() -> None:

    packet = _packet(
        (
            "Operations managers are the primary users. "
            "External consultants, inspectors, translators, "
            "and other service providers may receive assigned tasks "
            "and update their work status."
        )
    )

    actors = _actor_keys(
        packet
    )

    assert not any(
        value.startswith(
            "and "
        )
        for value in actors
    ), actors
