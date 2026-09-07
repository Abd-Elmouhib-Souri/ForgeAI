from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _sections(description: str) -> dict[str, list[str]]:
    return (
        ProjectContextExtractor()
        ._explicit_semantic_sections(
            description
        )
    )


def _joined_mvp_scope(
    sections: dict[str, list[str]],
) -> str:
    return " ".join(
        sections.get(
            "mvp_scope",
            [],
        )
    ).casefold()


def test_negative_scope_heading_never_becomes_positive_mvp_scope() -> None:
    """
    Universal polarity invariant:

    Merely containing the token "MVP" inside a negative section heading
    must never cause that heading to be interpreted as positive MVP scope.

    Section classification depends on the semantic heading as a whole,
    not on a positive-label token appearing inside another heading.
    """

    sections = _sections(
        "Explicitly out of scope for the MVP: "
        "excluded capability gamma; excluded capability delta."
    )

    positive = _joined_mvp_scope(
        sections
    )

    assert "excluded capability gamma" not in positive, (
        "NEGATIVE_SCOPE_HEADING_WAS_PROJECTED_AS_POSITIVE_MVP_SCOPE"
    )

    assert "excluded capability delta" not in positive, (
        "NEGATIVE_SCOPE_HEADING_WAS_PROJECTED_AS_POSITIVE_MVP_SCOPE"
    )


def test_explicit_mvp_capabilities_section_is_positive_scope_without_negative_bleed() -> None:
    """
    Universal section-boundary invariant:

    A user may express explicit positive MVP commitments under a natural
    capability-oriented MVP heading.

    A following explicit negative-scope heading must terminate that
    positive section. Negative values must never bleed into positive scope.
    """

    sections = _sections(
        "MVP capabilities: "
        "capability alpha; capability beta. "
        "Explicitly out of scope for the MVP: "
        "excluded capability gamma; excluded capability delta. "
        "Business objective: reduce processing delay."
    )

    positive = _joined_mvp_scope(
        sections
    )

    assert "capability alpha" in positive, (
        "EXPLICIT_POSITIVE_MVP_CAPABILITY_WAS_LOST"
    )

    assert "capability beta" in positive, (
        "EXPLICIT_POSITIVE_MVP_CAPABILITY_WAS_LOST"
    )

    assert "excluded capability gamma" not in positive, (
        "NEGATIVE_SCOPE_BLED_INTO_POSITIVE_MVP_SCOPE"
    )

    assert "excluded capability delta" not in positive, (
        "NEGATIVE_SCOPE_BLED_INTO_POSITIVE_MVP_SCOPE"
    )

    assert "reduce processing delay" not in positive, (
        "FOLLOWING_SEMANTIC_SECTION_BLED_INTO_POSITIVE_MVP_SCOPE"
    )


def test_existing_explicit_mvp_scope_heading_remains_supported() -> None:
    """
    Anti-overfit / backward-compatibility guard.

    Fixing natural section boundaries must not remove the already-supported
    explicit "MVP scope:" form.
    """

    sections = _sections(
        "MVP scope: capability alpha; capability beta."
    )

    positive = _joined_mvp_scope(
        sections
    )

    assert "capability alpha" in positive
    assert "capability beta" in positive