from __future__ import annotations

from copy import deepcopy

from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


DESCRIPTION = (
    "The procurement organization is the economic payer "
    "and pays the subscription directly. "
    "Operational staff use the application daily."
)


FRESH_PAYER = (
    "procurement organization"
)


STALE_ALIAS = (
    "procurement organization is the economic payer and"
)


STALE_CONTEXT = {
    "context_locked":
        True,

    "target_users": [
        STALE_ALIAS,
    ],

    "actors": {
        "payer":
            STALE_ALIAS,
    },

    "payer_actor_names": [
        STALE_ALIAS,
    ],
}


def _packet(
    *,
    project_context,
):

    return (
        ProjectContextExtractor()
        .extract(
            title="NeutralFreshRoleAuthority",
            description=DESCRIPTION,
            industry="B2B operations",
            target_region="Global",
            output_language="en",
            project_context=deepcopy(
                project_context
            ),
            idea_readiness={},
            analysis_data={},
        )
    )


def _payer_keys(
    packet,
):

    return [
        comparison_key(
            value
        )
        for value in (
            packet.payer_actor_names
            or []
        )
    ]


def _payer_actor_keys(
    actors,
):

    return [
        comparison_key(
            actor.name
        )
        for actor in actors
        if actor.role
        ==
        ActorRole.PAYER
    ]


def _contains_stale_role_grammar(
    values,
) -> bool:

    return any(
        "economic payer and"
        in comparison_key(
            value
        )
        for value in values
    )


def test_fresh_reconciliation_boundary_preserves_current_explicit_authority() -> None:
    """
    Universal freshness/reconciliation invariant.

    Fresh explicit current-project actor authority must survive the
    reconciliation boundary and malformed stale role-grammar identities
    must not survive AFTER that boundary.

    The malformed stale identity is deliberately not required to exist
    before reconciliation.

    A stronger upstream canonical actor-identity validator may reject the
    invalid proposition earlier. Reconciliation must remain correct and
    idempotent in either topology.
    """

    extractor = (
        ProjectContextExtractor()
    )

    raw = (
        extractor
        ._extract_explicit_actors(
            description=DESCRIPTION,
            project_context=deepcopy(
                STALE_CONTEXT
            ),
            analysis_data={},
        )
    )

    raw_payers = (
        _payer_actor_keys(
            raw
        )
    )

    assert (
        comparison_key(
            FRESH_PAYER
        )
        in raw_payers
    )

    reconciled = (
        extractor
        ._reconcile_fresh_declared_actor_authority(
            actors=raw,
            description=DESCRIPTION,
        )
    )

    reconciled_payers = (
        _payer_actor_keys(
            reconciled
        )
    )

    assert (
        comparison_key(
            FRESH_PAYER
        )
        in reconciled_payers
    )

    assert not any(
        "economic payer and"
        in value
        for value in reconciled_payers
    ), reconciled_payers




def test_lower_authority_structured_population_cannot_reintroduce_actor_identity_superseded_by_fresh_role_authority() -> None:
    """
    Universal authority invariant.

    Once fresh explicit current-project evidence has superseded a stale
    role-grammar identity, a later lower-authority structured-population
    merge may not reintroduce that stale identity into the canonical actor
    registry or its role projections.
    """

    packet = _packet(
        project_context=STALE_CONTEXT,
    )


    payer_keys = (
        _payer_keys(
            packet
        )
    )


    assert (
        comparison_key(
            FRESH_PAYER
        )
        in payer_keys
    )


    assert not any(
        "economic payer and"
        in value
        for value in payer_keys
    ), payer_keys


    canonical_payer_actors = [
        actor.name
        for actor in packet.actors
        if actor.role
        ==
        ActorRole.PAYER
    ]


    assert not (
        _contains_stale_role_grammar(
            canonical_payer_actors
        )
    ), canonical_payer_actors


def test_stale_lower_authority_context_is_observationally_irrelevant_to_fresh_explicit_role_projection() -> None:
    """
    Metamorphic freshness invariant.

    With the exact same fresh current description, adding stale lower-authority
    persisted role aliases must not change the final canonical payer identity.
    """

    fresh_packet = _packet(
        project_context={},
    )


    stale_packet = _packet(
        project_context=STALE_CONTEXT,
    )


    fresh_payers = {
        comparison_key(
            value
        )
        for value in (
            fresh_packet.payer_actor_names
            or []
        )
    }


    stale_payers = {
        comparison_key(
            value
        )
        for value in (
            stale_packet.payer_actor_names
            or []
        )
    }


    assert fresh_payers == {
        comparison_key(
            FRESH_PAYER
        )
    }


    assert (
        stale_payers
        ==
        fresh_payers
    )
