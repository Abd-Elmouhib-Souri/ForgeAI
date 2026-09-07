from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _decision_names(
    description: str,
):
    return [
        name
        for name, role
        in (
            ProjectContextExtractor()
            ._declared_actor_roles(
                description
            )
        )
        if role
        == ActorRole.DECISION_MAKER
    ]


def test_main_decision_makers_structured_heading_is_authoritative() -> None:
    description = (
        "Main decision makers:\n"
        "- organization owner\n"
        "- operations manager\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _decision_names(
        description
    ) == [
        "organization owner",
        "operations manager",
    ]


def test_primary_decision_makers_structured_heading_is_authoritative() -> None:
    description = (
        "Primary decision makers:\n"
        "- steering council\n"
        "- investment committee\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _decision_names(
        description
    ) == [
        "steering council",
        "investment committee",
    ]


def test_key_decision_makers_section_stops_at_other_heading() -> None:
    description = (
        "Key decision makers:\n"
        "- organization owner\n"
        "Paying customer:\n"
        "- operating organization\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _decision_names(
        description
    ) == [
        "organization owner",
    ]


def test_french_plural_modifier_structured_heading_is_authoritative() -> None:
    description = (
        "Principaux decideurs:\n"
        "- proprietaire de l organisation\n"
        "- responsable des operations\n"
        "Fonctionnalites MVP:\n"
        "- fonction alpha"
    )

    assert _decision_names(
        description
    ) == [
        "proprietaire de l organisation",
        "responsable des operations",
    ]


def test_main_decision_makers_inline_uses_existing_list_normalizer() -> None:
    description = (
        "Main decision makers: organization owner "
        "and operations manager."
    )

    assert _decision_names(
        description
    ) == [
        "organization owner",
        "operations manager",
    ]


def test_unrelated_structured_heading_does_not_create_decision_role() -> None:
    description = (
        "Project owners:\n"
        "- organization owner\n"
        "- operations manager\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _decision_names(
        description
    ) == []