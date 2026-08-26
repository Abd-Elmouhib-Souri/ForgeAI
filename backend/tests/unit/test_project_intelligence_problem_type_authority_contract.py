from __future__ import annotations

from app.services.project_intelligence_layer import (
    ProjectIntelligenceLayer,
)


def build(
    problem,
    *,
    description=(
        "Teams rely on several manual handoffs. "
        "This creates recurring delays, conflicting updates "
        "and incomplete information."
    ),
):
    return ProjectIntelligenceLayer().build(
        title="ProblemTypeAuthorityProbe",
        description=description,
        industry="B2B operations",
        target_region="Europe",
        output_language="en",
        project_context={
            "context_locked": True,
            "problem": problem,
        },
        idea_readiness={},
        analysis_data={},
    )


def keyword_blob(result) -> str:
    return " ".join(
        str(value)
        for value
        in (
            result.get(
                "problem_keywords"
            )
            or []
        )
    ).casefold()


def assert_no_problem_schema_leak(
    value,
):
    text = str(
        value or ""
    ).casefold()

    for forbidden in (
        "actors_affected",
        "actors affected",
        "current_alternatives",
        "current alternatives",
        "consequences",
        "frequency",
        "severity",
    ):
        assert forbidden not in text


# ============================================================
# Empty canonical object:
# preserve the canonical dict, but NEVER stringify its schema
# into planning/search text.
# ============================================================

def test_locked_empty_problem_mapping_never_becomes_textual_schema():
    problem = {
        "actors_affected": [],
        "pain": "",
        "frequency": "",
        "severity": "",
        "current_alternatives": [],
        "consequences": [],
    }

    result = build(
        problem
    )

    structured = result[
        "structured_project_context"
    ]

    assert structured[
        "problem"
    ] == problem

    assert isinstance(
        structured["problem"],
        dict,
    )

    assert_no_problem_schema_leak(
        structured.get(
            "core_problem"
        )
    )

    assert_no_problem_schema_leak(
        keyword_blob(
            result
        )
    )


# ============================================================
# Populated canonical object:
# planning/search may consume semantic pain, never dict repr.
# ============================================================

def test_locked_populated_problem_mapping_projects_only_semantic_pain_to_text():
    pain = (
        "Manual reconciliation causes "
        "recurring processing delays."
    )

    problem = {
        "actors_affected": [
            "operations teams",
        ],
        "pain": pain,
        "frequency": "weekly",
        "severity": "medium",
        "current_alternatives": [],
        "consequences": [
            "late processing",
        ],
    }

    result = build(
        problem,
        description=(
            "The service supports a routine "
            "business workflow."
        ),
    )

    structured = result[
        "structured_project_context"
    ]

    assert structured[
        "problem"
    ] == problem

    assert isinstance(
        structured["problem"],
        dict,
    )

    core_problem = str(
        structured.get(
            "core_problem"
        )
        or ""
    ).casefold()

    assert (
        "manual reconciliation"
        in core_problem
    )

    assert_no_problem_schema_leak(
        core_problem
    )

    keywords = keyword_blob(
        result
    )

    assert_no_problem_schema_leak(
        keywords
    )


# ============================================================
# Existing string compatibility must remain unchanged.
# ============================================================

def test_plain_problem_string_remains_supported():
    pain = (
        "Manual reconciliation causes "
        "recurring processing delays."
    )

    result = build(
        pain,
        description=(
            "The service supports a routine "
            "business workflow."
        ),
    )

    structured = result[
        "structured_project_context"
    ]

    assert (
        structured.get(
            "problem"
        )
        == pain
    )

    assert (
        structured.get(
            "core_problem"
        )
        == pain
    )


# Blind-B2.8 locked problem alias authority.
#
# `problem` is the modern canonical authority.
#
# When a locked upstream context explicitly contains `problem`,
# downstream PIL must not manufacture a stronger-looking
# `core_problem` from a lower-authority heuristic merely because
# the canonical pain is empty.
#
# `core_problem` remains a compatibility text projection:
#
#     problem string       -> same text
#     problem mapping      -> mapping["pain"]
#     empty mapping pain   -> ""
#
# If upstream explicitly supplied `core_problem`, normal locked
# key-preservation remains authoritative.


def test_locked_problem_presence_blocks_inferred_core_problem_alias():
    pil = ProjectIntelligenceLayer()

    canonical_problem = {
        "actors_affected": [],
        "pain": "",
        "frequency": "",
        "severity": "",
        "current_alternatives": [],
        "consequences": [],
    }

    projected = (
        pil._preserve_locked_canonical_projection(
            structured_project_context={
                "problem": (
                    "Lower authority generated problem."
                ),
                "core_problem": (
                    "Lower authority generated problem."
                ),
            },
            base_project_context={
                "context_locked": True,
                "problem": canonical_problem,
            },
        )
    )

    assert (
        projected["problem"]
        == canonical_problem
    )

    assert (
        projected.get(
            "core_problem"
        )
        == ""
    )


def test_build_does_not_invent_core_problem_when_locked_problem_pain_is_empty():
    canonical_problem = {
        "actors_affected": [],
        "pain": "",
        "frequency": "",
        "severity": "",
        "current_alternatives": [],
        "consequences": [],
    }

    result = build(
        canonical_problem
    )

    structured = result[
        "structured_project_context"
    ]

    assert (
        structured["problem"]
        == canonical_problem
    )

    assert (
        structured.get(
            "core_problem"
        )
        == ""
    )
