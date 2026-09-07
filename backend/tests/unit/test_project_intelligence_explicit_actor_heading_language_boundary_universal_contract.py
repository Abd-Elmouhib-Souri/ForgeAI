from __future__ import annotations

from app.services.project_intelligence_layer import (
    ProjectIntelligenceLayer,
)


def _roles(description: str):
    return (
        ProjectIntelligenceLayer()
        ._extract_actor_roles_from_description(
            description
        )
    )


def _targets(description: str):
    return (
        ProjectIntelligenceLayer()
        ._extract_target_users(
            description=description,
            project_context={},
            detected={},
        )
    )


def test_inline_target_users_heading_is_explicit_actor_authority() -> None:
    description = (
        "Target users: operations coordinator "
        "and inventory manager."
    )

    assert _roles(
        description
    ) == [
        "operations coordinator",
        "inventory manager",
    ]

    assert _targets(
        description
    ) == [
        "operations coordinator",
        "inventory manager",
    ]


def test_french_primary_operational_users_heading_is_supported() -> None:
    description = (
        "Utilisateurs operationnels principaux:\n"
        "- coordinateur des operations\n"
        "- gestionnaire des stocks\n"
        "Fonctionnalites MVP:\n"
        "- fonction alpha"
    )

    assert _roles(
        description
    ) == [
        "coordinateur des operations",
        "gestionnaire des stocks",
    ]


def test_french_external_users_heading_is_supported() -> None:
    description = (
        "Utilisateurs externes:\n"
        "- acheteur professionnel\n"
        "- partenaire logistique\n"
        "Fonctionnalites MVP:\n"
        "- fonction alpha"
    )

    assert _roles(
        description
    ) == [
        "acheteur professionnel",
        "partenaire logistique",
    ]


def test_decision_makers_are_not_promoted_to_target_users() -> None:
    description = (
        "Decision makers:\n"
        "- organization owner\n"
        "- operations manager\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _roles(
        description
    ) == []

    assert _targets(
        description
    ) == []


def test_decision_maker_section_stops_actor_collection() -> None:
    description = (
        "Primary operational users:\n"
        "- operations coordinator\n"
        "Decision makers:\n"
        "- organization owner\n"
        "- operations manager\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _roles(
        description
    ) == [
        "operations coordinator",
    ]