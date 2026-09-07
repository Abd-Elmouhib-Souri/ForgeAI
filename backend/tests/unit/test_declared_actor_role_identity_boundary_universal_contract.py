
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


def _clean(
    value: str,
) -> str:

    return comparison_key(
        _extractor()
        ._clean_actor(
            value
        )
    )


def _payer_names(
    description: str,
) -> list[str]:

    return [
        comparison_key(
            name
        )
        for name, role
        in (
            _extractor()
            ._declared_actor_roles(
                description
            )
        )
        if (
            role
            == ActorRole.PAYER
            and comparison_key(
                name
            )
        )
    ]


def test_atomic_actor_identity_remains_supported() -> None:

    assert (
        _clean(
            "client organization"
        )
        ==
        "client organization"
    )

    assert (
        _clean(
            "operations coordinators"
        )
        ==
        "operations coordinators"
    )


def test_existing_delegation_clause_rejection_remains_supported() -> None:
    """
    Historical C2 invariant:
    a product-capability proposition is not an actor identity.
    """

    assert (
        _clean(
            (
                "Platform must allow "
                "the operations manager "
                "to review requests"
            )
        )
        ==
        ""
    )


def test_modal_actor_capability_clause_is_not_actor_identity() -> None:
    """
    Universal actor identity invariant.

    Subject + capability is a proposition.
    It must not survive as one ActorContext identity.
    """

    assert (
        _clean(
            (
                "service recipients "
                "can submit support requests"
            )
        )
        ==
        ""
    )


def test_actor_access_policy_clause_is_not_actor_identity() -> None:
    """
    Authorization policy is not actor identity.
    """

    assert (
        _clean(
            (
                "account holders "
                "should only access "
                "their own records"
            )
        )
        ==
        ""
    )


def test_business_model_predicate_is_not_actor_identity() -> None:
    """
    A business-model proposition is not an actor entity.
    """

    assert (
        _clean(
            (
                "commercial model "
                "is a recurring subscription"
            )
        )
        ==
        ""
    )


def test_french_modal_capability_clause_is_not_actor_identity() -> None:

    assert (
        _clean(
            (
                "les usagers peuvent soumettre "
                "des demandes de support"
            )
        )
        ==
        ""
    )


def test_french_access_policy_clause_is_not_actor_identity() -> None:

    assert (
        _clean(
            (
                "les titulaires doivent seulement acceder "
                "a leurs propres dossiers"
            )
        )
        ==
        ""
    )


def test_direct_explicit_payer_relation_remains_supported() -> None:
    """
    Existing role-relation authority stays intact.
    """

    payers = _payer_names(
        (
            "The client organization is the economic payer "
            "and pays the recurring subscription directly."
        )
    )

    assert payers == [
        "client organization"
    ]


def test_business_model_followup_cannot_materialize_second_fake_payer() -> None:
    """
    Universal relation/identity integration invariant.

    A later business-model sentence may repeat payment semantics,
    but it must not create a second payer whose identity is the
    commercial-model clause itself.
    """

    payers = _payer_names(
        (
            "The client organization is the economic payer "
            "and pays the recurring subscription directly. "
            "The commercial model is a recurring subscription "
            "paid by the client organization."
        )
    )

    assert payers == [
        "client organization"
    ], payers


def test_structural_primary_users_are_owned_by_group_authority() -> None:
    """
    Architecture control.

    Label-first structural user declarations belong to
    _declared_actor_groups(), not _declared_actor_roles().
    """

    groups = [
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
                (
                    "The primary users are "
                    "operations coordinators "
                    "and service coordinators."
                )
            )
        )
    ]

    assert (
        "operations coordinators",
        ActorRole.USER,
    ) in groups

    assert (
        "service coordinators",
        ActorRole.USER,
    ) in groups
