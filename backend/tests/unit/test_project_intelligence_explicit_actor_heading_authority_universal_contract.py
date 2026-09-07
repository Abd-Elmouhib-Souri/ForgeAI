from __future__ import annotations

from app.services.project_intelligence_layer import (
    ProjectIntelligenceLayer,
)


def _roles(
    description: str,
):
    return (
        ProjectIntelligenceLayer()
        ._extract_actor_roles_from_description(
            description
        )
    )


def _targets(
    description: str,
):
    return (
        ProjectIntelligenceLayer()
        ._extract_target_users(
            description=description,
            project_context={},
            detected={},
        )
    )


def test_primary_operational_users_block_is_explicit_actor_authority() -> None:
    description = (
        "Primary operational users:\n"
        "- operations coordinator\n"
        "- inventory manager\n"
        "MVP capabilities:\n"
        "- function alpha"
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


def test_external_users_block_is_explicit_actor_authority() -> None:
    description = (
        "External users:\n"
        "- business buyer\n"
        "- delivery partner\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _roles(
        description
    ) == [
        "business buyer",
        "delivery partner",
    ]

    assert _targets(
        description
    ) == [
        "business buyer",
        "delivery partner",
    ]


def test_multiple_explicit_actor_sections_preserve_order_and_boundaries() -> None:
    description = (
        "Primary operational users:\n"
        "- operations coordinator\n"
        "- inventory manager\n"
        "External users:\n"
        "- business buyer\n"
        "- delivery partner\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _roles(
        description
    ) == [
        "operations coordinator",
        "inventory manager",
        "business buyer",
        "delivery partner",
    ]


def test_explicit_actor_heading_is_independent_of_generic_actor_lexicon(
    monkeypatch,
) -> None:
    """
    An explicit semantic heading establishes actor identity.

    Generic vocabulary may validate heuristic prose, but cannot veto an
    identity explicitly declared under an actor heading.
    """

    pil = ProjectIntelligenceLayer()

    monkeypatch.setattr(
        pil,
        "_is_actor_phrase",
        lambda value: False,
    )

    description = (
        "Primary operational users:\n"
        "- operations coordinator\n"
        "- inventory manager\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert (
        pil
        ._extract_actor_roles_from_description(
            description
        )
        ==
        [
            "operations coordinator",
            "inventory manager",
        ]
    )


def test_empty_actor_heading_does_not_consume_next_semantic_section() -> None:
    description = (
        "Primary operational users:\n"
        "MVP capabilities:\n"
        "- function alpha\n"
        "- function beta"
    )

    assert _roles(
        description
    ) == []


def test_explicit_actor_section_does_not_consume_following_non_actor_items() -> None:
    description = (
        "Primary operational users:\n"
        "- operations coordinator\n"
        "MVP capabilities:\n"
        "- function alpha\n"
        "- function beta"
    )

    result = _roles(
        description
    )

    assert result == [
        "operations coordinator",
    ]

    assert (
        "function alpha"
        not in result
    )

    assert (
        "function beta"
        not in result
    )


def test_historical_natural_user_prose_remains_supported() -> None:
    """
    Existing heuristic prose support is a separate fallback and must remain
    available after explicit-heading support is introduced.
    """

    assert _targets(
        "The main users are operations managers."
    ) == [
        "operations managers",
    ]