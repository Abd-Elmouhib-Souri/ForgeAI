from __future__ import annotations

import ast
from pathlib import Path
from typing import (
    Literal,
    get_args,
    get_origin,
)

import pytest

import app.schemas.project_management as pm


# ============================================================
# S4.9 SCRUM MASTER ADVISORY OUTPUT CONTRACT
# ============================================================

ALLOWED_RECOMMENDATION_TYPES = (
    "split",
    "sequencing",
    "risk",
    "overload",
    "parallelization",
    "critical_dependency",
)


REQUIRED_RECOMMENDATION_FIELDS = {
    "recommendation_type",
    "story_ids",
    "rationale",
}


FORBIDDEN_RECOMMENDATION_FIELDS = {
    "priority",
    "new_priority",
    "story_points",
    "new_story_points",
    "dependencies",
    "new_dependencies",
    "dependency_type",
    "sprint",
    "sprint_id",
    "sprint_number",
    "assigned_sprint",
    "capability",
    "new_capability",
    "architecture",
    "stack",
    "velocity",
    "burndown",
}


REQUIRED_ADVICE_FIELDS = {
    "schema_version",
    "source_context_hash",
    "context_hash",
    "recommendations",
    "warnings",
}


FORBIDDEN_ADVICE_FIELDS = {
    "backlog",
    "canonical_backlog",
    "priority",
    "story_points",
    "dependencies",
    "sprints",
    "sprint_assignments",
    "final_sprint_plan",
    "planned_sprints",
    "architecture",
    "stack",
    "metrics",
    "burndown",
    "actual_velocity",
}


EXPECTED_SCHEMA_VERSION = (
    "scrum_master_advice_v1"
)


def _recommendation_class_or_skip():
    cls = getattr(
        pm,
        "ScrumMasterRecommendationV1",
        None,
    )

    if cls is None:
        pytest.skip(
            "ScrumMasterRecommendationV1 intentionally "
            "absent while S4.9 contracts are being armed."
        )

    return cls


def _advice_class_or_skip():
    cls = getattr(
        pm,
        "ScrumMasterAdviceV1",
        None,
    )

    if cls is None:
        pytest.skip(
            "ScrumMasterAdviceV1 intentionally absent "
            "while S4.9-A1 owns the REAL_RED."
        )

    return cls


# ============================================================
# 0. CLOSED ADVISORY TAXONOMY
# ============================================================

def test_00_scrum_master_recommendation_taxonomy_is_closed():
    assert set(
        ALLOWED_RECOMMENDATION_TYPES
    ) == {
        "split",
        "sequencing",
        "risk",
        "overload",
        "parallelization",
        "critical_dependency",
    }

    assert len(
        ALLOWED_RECOMMENDATION_TYPES
    ) == len(
        set(
            ALLOWED_RECOMMENDATION_TYPES
        )
    )


# ============================================================
# 1. CONTRACT ITSELF MUST REMAIN STRUCTURAL
# ============================================================

def test_01_scrum_master_advice_contract_is_fixture_free_and_structural():
    tree = ast.parse(
        Path(
            __file__
        ).read_text(
            encoding="utf-8"
        )
    )

    test_functions = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name.startswith(
                "test_"
            )
        )
    ]

    parameterized = []

    for function in test_functions:

        assert not function.args.args, (
            "Scrum Master advice semantics must "
            "remain structural and fixture-free."
        )

        for decorator in function.decorator_list:

            text = ast.unparse(
                decorator
            )

            if "parametrize" in text:
                parameterized.append(
                    function.name
                )

    assert not parameterized, (
        "Scrum Master advice contract must not "
        "depend on example-specific parametrization: "
        f"{parameterized}"
    )


# ============================================================
# 2. STRUCTURED RECOMMENDATION MODEL
# ============================================================

def test_02_scrum_master_recommendation_has_minimal_advisory_surface():
    cls = _recommendation_class_or_skip()

    fields = set(
        cls.model_fields
    )

    missing = (
        REQUIRED_RECOMMENDATION_FIELDS
        - fields
    )

    assert not missing, (
        "ScrumMasterRecommendationV1 is missing "
        f"required advisory fields: {sorted(missing)}"
    )


# ============================================================
# 3. RECOMMENDATION TYPE MUST BE CLOSED
# ============================================================

def test_03_recommendation_type_is_closed_literal():
    cls = _recommendation_class_or_skip()

    field = cls.model_fields[
        "recommendation_type"
    ]

    annotation = field.annotation

    assert get_origin(
        annotation
    ) is Literal, (
        "recommendation_type must be a closed Literal."
    )

    values = set(
        get_args(
            annotation
        )
    )

    assert values == set(
        ALLOWED_RECOMMENDATION_TYPES
    ), (
        "Scrum Master recommendation taxonomy drifted: "
        f"{sorted(values)}"
    )


# ============================================================
# 4. RECOMMENDATION CANNOT OWN DETERMINISTIC DECISIONS
# ============================================================

def test_04_recommendation_contains_no_planner_or_policy_authority():
    cls = _recommendation_class_or_skip()

    fields = set(
        cls.model_fields
    )

    leaked = (
        FORBIDDEN_RECOMMENDATION_FIELDS
        &
        fields
    )

    assert not leaked, (
        "ScrumMasterRecommendationV1 leaks "
        "deterministic authority: "
        f"{sorted(leaked)}"
    )


# ============================================================
# 5. ADVICE ENVELOPE
# ============================================================

def test_05_scrum_master_advice_has_canonical_envelope():
    cls = _advice_class_or_skip()

    fields = set(
        cls.model_fields
    )

    missing = (
        REQUIRED_ADVICE_FIELDS
        - fields
    )

    assert not missing, (
        "ScrumMasterAdviceV1 is missing "
        f"canonical fields: {sorted(missing)}"
    )


# ============================================================
# 6. RECOMMENDATIONS MUST BE TYPED
# ============================================================

def test_06_advice_recommendations_use_structured_recommendation_model():
    recommendation_cls = (
        _recommendation_class_or_skip()
    )

    advice_cls = (
        _advice_class_or_skip()
    )

    annotation = (
        advice_cls
        .model_fields[
            "recommendations"
        ]
        .annotation
    )

    assert get_origin(
        annotation
    ) is list, (
        "recommendations must be a typed list."
    )

    args = get_args(
        annotation
    )

    assert args == (
        recommendation_cls,
    ), (
        "recommendations must contain only "
        "ScrumMasterRecommendationV1 objects."
    )


# ============================================================
# 7. ADVICE ENVELOPE MUST NOT BECOME THE PLAN
# ============================================================

def test_07_advice_contains_no_final_planning_authority():
    cls = _advice_class_or_skip()

    fields = set(
        cls.model_fields
    )

    leaked = (
        FORBIDDEN_ADVICE_FIELDS
        &
        fields
    )

    assert not leaked, (
        "ScrumMasterAdviceV1 leaks final "
        f"planning authority: {sorted(leaked)}"
    )


# ============================================================
# 8. STRICT MODELS
# ============================================================

def test_08_scrum_master_advice_models_fail_closed_on_extra_fields():
    recommendation_cls = (
        _recommendation_class_or_skip()
    )

    advice_cls = (
        _advice_class_or_skip()
    )

    assert dict(
        recommendation_cls.model_config
    ).get(
        "extra"
    ) == "forbid"

    assert dict(
        advice_cls.model_config
    ).get(
        "extra"
    ) == "forbid"


# ============================================================
# 9. SCHEMA VERSION IS EXPLICIT
# ============================================================

def test_09_scrum_master_advice_schema_version_is_explicit_v1():
    cls = _advice_class_or_skip()

    field = cls.model_fields[
        "schema_version"
    ]

    annotation = field.annotation

    assert get_origin(
        annotation
    ) is Literal

    assert set(
        get_args(
            annotation
        )
    ) == {
        EXPECTED_SCHEMA_VERSION
    }

    if not field.is_required():
        assert field.default == (
            EXPECTED_SCHEMA_VERSION
        )