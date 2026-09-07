from __future__ import annotations

import runpy
from pathlib import Path

from app.services.candidate_backlog_authority import (
    candidate_backlog_authority_validator,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)


_MODULE = runpy.run_path(
    str(
        Path(__file__).with_name(
            "test_candidate_backlog_scope_coverage_authority_contract.py"
        )
    )
)

_context = _MODULE["_context"]


def _fallback(
    scope_items: list[str],
    *,
    language: str = "en",
    preserve_workflow: bool = False,
):

    context = _context()

    update = {
        "mvp_scope":
            list(scope_items),

        "language":
            language,
    }

    if not preserve_workflow:

        update[
            "priority_workflows"
        ] = []

    context = context.model_copy(
        update=update,
        deep=True,
    )

    candidate = (
        ProjectManagementPlanService
        ._build_deterministic_candidate(
            context
        )
    )

    return (
        context,
        candidate,
    )


def _scope_refs(story):

    return [
        ref
        for ref
        in story.provenance_refs
        if str(ref).startswith(
            "mvp_scope:"
        )
    ]


def test_unbound_atomic_scope_commitments_do_not_collapse_into_one_god_story() -> None:

    scope = [
        "Create workspace access",
        "Export decision audit history",
        "Send status notifications",
    ]

    context, candidate = _fallback(
        scope
    )

    result = (
        candidate_backlog_authority_validator
        .validate(
            context=context,
            candidate=candidate,
        )
    )

    assert result.is_valid

    refs = [
        _scope_refs(story)
        for story
        in candidate.stories
    ]

    assert refs

    assert all(
        len(item) == 1
        for item
        in refs
    ), refs

    assert {
        ref
        for item
        in refs
        for ref
        in item
    } == {
        f"mvp_scope:{value}"
        for value
        in scope
    }


def test_single_atomic_scope_commitment_remains_one_delivery_unit() -> None:

    context, candidate = _fallback(
        [
            "Create workspace access",
        ]
    )

    result = (
        candidate_backlog_authority_validator
        .validate(
            context=context,
            candidate=candidate,
        )
    )

    assert result.is_valid

    assert len(
        candidate.stories
    ) == 1

    assert _scope_refs(
        candidate.stories[0]
    ) == [
        "mvp_scope:Create workspace access"
    ]


def test_each_delivery_unit_is_bound_to_exactly_one_explicit_scope_commitment() -> None:

    scope = [
        "Create service request",
        "Record completion evidence",
        "Export audit history",
    ]

    context, candidate = _fallback(
        scope
    )

    result = (
        candidate_backlog_authority_validator
        .validate(
            context=context,
            candidate=candidate,
        )
    )

    assert result.is_valid

    seen = set()

    for story in candidate.stories:

        refs = _scope_refs(
            story
        )

        assert len(
            refs
        ) == 1

        value = refs[0].split(
            ":",
            1,
        )[1]

        surface = " ".join(
            [
                str(story.title),
                str(story.capability),
                str(story.story),
            ]
        ).casefold()

        assert value.casefold() in surface

        seen.add(
            refs[0]
        )

    assert seen == {
        f"mvp_scope:{value}"
        for value
        in scope
    }


def test_empty_scope_does_not_manufacture_filler_stories() -> None:

    context, candidate = _fallback(
        [],
        preserve_workflow=True,
    )

    result = (
        candidate_backlog_authority_validator
        .validate(
            context=context,
            candidate=candidate,
        )
    )

    assert result.is_valid

    assert len(
        candidate.stories
    ) == 1

    assert not _scope_refs(
        candidate.stories[0]
    )
