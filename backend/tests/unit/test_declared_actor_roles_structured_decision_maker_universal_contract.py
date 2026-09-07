from __future__ import annotations

from app.schemas.analysis_context import ActorRole

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _declared(
    description: str,
):
    return (
        ProjectContextExtractor()
        ._declared_actor_roles(
            description
        )
    )


def _decision_names(
    description: str,
):
    return [
        name
        for name, role
        in _declared(
            description
        )
        if role
        == ActorRole.DECISION_MAKER
    ]


def test_structured_plural_decision_maker_heading_is_explicit_authority() -> None:
    description = (
        "Decision makers:\n"
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


def test_structured_decision_maker_section_stops_at_next_heading() -> None:
    description = (
        "Decision makers:\n"
        "- organization owner\n"
        "MVP capabilities:\n"
        "- function alpha\n"
        "- function beta"
    )

    assert _decision_names(
        description
    ) == [
        "organization owner",
    ]


def test_structured_decision_maker_authority_does_not_depend_on_name_lexicon() -> None:
    description = (
        "Decision makers:\n"
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


def test_inline_singular_decision_maker_contract_remains_supported() -> None:
    description = (
        "Decision maker: procurement manager."
    )

    assert _decision_names(
        description
    ) == [
        "procurement manager",
    ]


def test_inline_plural_decision_makers_are_supported() -> None:
    description = (
        "Decision makers: organization owner "
        "and operations manager."
    )

    assert _decision_names(
        description
    ) == [
        "organization owner",
        "operations manager",
    ]


def test_french_structured_decision_maker_heading_is_supported() -> None:
    description = (
        "Decideurs:\n"
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


def test_unlabeled_actor_list_does_not_create_decision_authority() -> None:
    description = (
        "- organization owner\n"
        "- operations manager\n"
        "MVP capabilities:\n"
        "- function alpha"
    )

    assert _decision_names(
        description
    ) == []