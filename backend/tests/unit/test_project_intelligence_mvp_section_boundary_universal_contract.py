from __future__ import annotations

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


def _structured(
    description: str,
) -> dict:
    result = project_intelligence_layer.build(
        title="Neutral Project",
        description=description,
        industry="software",
        target_region="Global",
        output_language="en",
        project_context={},
        idea_readiness={},
        analysis_data={},
    )

    return dict(
        result.get(
            "structured_project_context"
        )
        or {}
    )


def _mvp_scope(
    description: str,
) -> str:
    return str(
        _structured(
            description
        ).get(
            "mvp_scope"
        )
        or ""
    ).casefold()


def test_negative_heading_containing_mvp_never_becomes_positive_scope() -> None:
    """
    Universal semantic-heading invariant.

    A positive token appearing inside a negative heading must never cause
    the negative section to be interpreted as positive MVP scope.
    """

    scope = _mvp_scope(
        "A software product coordinates an operational process. "
        "Explicitly out of scope for the MVP: "
        "excluded function gamma; excluded function delta."
    )

    assert "excluded function gamma" not in scope, (
        "NEGATIVE_MVP_HEADING_BECAME_POSITIVE_SCOPE"
    )

    assert "excluded function delta" not in scope, (
        "NEGATIVE_MVP_HEADING_BECAME_POSITIVE_SCOPE"
    )


def test_natural_positive_mvp_heading_preserves_positive_commitments() -> None:
    """
    Universal positive-scope authority.

    Explicit positive MVP commitments remain positive regardless of
    sector, country, archetype or feature vocabulary.
    """

    scope = _mvp_scope(
        "A software product coordinates an operational process. "
        "MVP capabilities: "
        "function alpha; function beta."
    )

    assert "function alpha" in scope, (
        "EXPLICIT_POSITIVE_MVP_COMMITMENT_LOST"
    )

    assert "function beta" in scope, (
        "EXPLICIT_POSITIVE_MVP_COMMITMENT_LOST"
    )


def test_negative_and_following_sections_do_not_bleed_into_positive_mvp_scope() -> None:
    """
    Universal section-boundary invariant.

    An explicit negative section terminates positive MVP scope.
    A subsequent unrelated semantic section must also remain outside
    positive scope.
    """

    scope = _mvp_scope(
        "A software product coordinates an operational process. "
        "MVP capabilities: "
        "function alpha; function beta. "
        "Explicitly out of scope for the MVP: "
        "excluded function gamma; excluded function delta. "
        "Business objective: reduce processing delay."
    )

    assert "function alpha" in scope
    assert "function beta" in scope

    assert "excluded function gamma" not in scope, (
        "NEGATIVE_SCOPE_BLED_INTO_POSITIVE_MVP_SCOPE"
    )

    assert "excluded function delta" not in scope, (
        "NEGATIVE_SCOPE_BLED_INTO_POSITIVE_MVP_SCOPE"
    )

    assert "reduce processing delay" not in scope, (
        "FOLLOWING_SECTION_BLED_INTO_POSITIVE_MVP_SCOPE"
    )


def test_existing_supported_mvp_scope_form_remains_valid() -> None:
    """
    Backward-compatibility guard.
    """

    scope = _mvp_scope(
        "A software product coordinates an operational process. "
        "MVP: function alpha; function beta."
    )

    assert "function alpha" in scope
    assert "function beta" in scope