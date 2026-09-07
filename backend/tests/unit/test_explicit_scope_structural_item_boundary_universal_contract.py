from __future__ import annotations

from app.schemas.analysis_context import (
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _packet(
    description: str,
):
    return (
        ProjectContextExtractor()
        .extract(
            title="Neutral Structural Scope",
            description=description,
            industry="software",
            target_region="Global",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )


def _keys(
    values,
) -> list[str]:
    return [
        comparison_key(
            value
        )
        for value in values
    ]


def _expected(
    *values: str,
) -> list[str]:
    return [
        comparison_key(
            value
        )
        for value in values
    ]


def test_newline_bullet_mvp_items_remain_distinct_canonical_scope_items() -> None:
    """
    Universal structural-boundary invariant.

    Each explicit bullet row is an independent user-declared scope
    commitment unless the row itself contains one compound capability.

    No arbitrary minimum or maximum cardinality is introduced.
    """

    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "- record management\n"
        "- status tracking\n"
        "Explicitly out of scope for the MVP:\n"
        "- automatic billing\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "account access",
        "record management",
        "status tracking",
    ), packet.mvp_scope


def test_newline_bullet_exclusions_remain_distinct_canonical_scope_items() -> None:
    """
    Negative explicit bullet rows obey the same structural identity
    invariant as positive MVP scope.
    """

    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "Explicitly out of scope for the MVP:\n"
        "- automatic billing\n"
        "- payroll processing\n"
        "- autonomous purchasing\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "automatic billing",
        "payroll processing",
        "autonomous purchasing",
    ), packet.scope_exclusions


def test_hyphenated_feature_tokens_are_not_mistaken_for_list_boundaries() -> None:
    """
    Structural bullets split items.

    Lexical hyphens inside one feature remain part of that same item.
    """

    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- role-based access control\n"
        "- real-time status tracking\n"
        "- user-facing notifications\n"
        "Explicitly out of scope for the MVP:\n"
        "- third-party payment processing\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "role-based access control",
        "real-time status tracking",
        "user-facing notifications",
    ), packet.mvp_scope

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "third-party payment processing",
    ), packet.scope_exclusions


def test_conjunctions_inside_one_bullet_do_not_create_fake_scope_items() -> None:
    """
    A conjunction inside one structural row belongs to that capability.

    The bullet boundary, not the words and/or, owns item identity.
    """

    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- create and review service requests\n"
        "- approve or reject requests\n"
        "Explicitly out of scope for the MVP:\n"
        "- automatic billing\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "create and review service requests",
        "approve or reject requests",
    ), packet.mvp_scope


def test_semicolon_scope_lists_remain_supported() -> None:
    """
    Historical supported semicolon syntax remains a preservation control.
    """

    packet = _packet(
        "A generic workflow platform. "
        "MVP capabilities: "
        "account access; "
        "record management; "
        "status tracking. "
        "Explicitly out of scope for the MVP: "
        "automatic billing; "
        "payroll processing. "
        "Business objective: "
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "account access",
        "record management",
        "status tracking",
    ), packet.mvp_scope

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "automatic billing",
        "payroll processing",
    ), packet.scope_exclusions
