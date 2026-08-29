from __future__ import annotations

from pathlib import Path

import pytest

import app.schemas.project_management as pm


# ============================================================
# S4.9 / S4.11 SHARED PLANNING INPUT SEMANTICS
# ============================================================

REQUIRED_INPUT_FIELDS = {
    "sprint_count",
    "sprint_duration_days",
    "planned_velocity",
    "team_size",
    "capacity_adjustment",
    "start_date",
    "working_days",
}


FORBIDDEN_OUTPUT_AUTHORITY_FIELDS = {
    "sprints",
    "sprint_assignments",
    "final_sprint_plan",
    "planned_sprints",
    "story_assignments",
    "overflow_stories",
    "blocked_stories",
    "metrics",
    "burndown",
    "ideal_burndown",
    "planned_burndown",
    "projected_velocity",
    "actual_velocity",
}


# The SprintPlanningEngine owns this deterministic constraint.
# PlanningSettings carries the user/configuration value.
SPRINT_COUNT_MIN = 4
SPRINT_COUNT_MAX = 8


# The official plan allows 14 days as a possible default,
# but explicitly requires the duration to remain configurable.
ALLOWED_SPRINT_DURATION_DEFAULT = 14


def _settings_class_or_skip():
    cls = getattr(
        pm,
        "PlanningSettingsV1",
        None,
    )

    if cls is None:
        pytest.skip(
            "PlanningSettingsV1 intentionally absent: "
            "S4.9-A1 owns the certified REAL_RED."
        )

    return cls


# ============================================================
# 0. CONTRACT SCOPE ITSELF
# ============================================================

def test_00_planning_settings_semantics_are_input_only():
    assert REQUIRED_INPUT_FIELDS == {
        "sprint_count",
        "sprint_duration_days",
        "planned_velocity",
        "team_size",
        "capacity_adjustment",
        "start_date",
        "working_days",
    }

    assert (
        REQUIRED_INPUT_FIELDS
        &
        FORBIDDEN_OUTPUT_AUTHORITY_FIELDS
    ) == set()

    assert SPRINT_COUNT_MIN == 4
    assert SPRINT_COUNT_MAX == 8

    assert (
        ALLOWED_SPRINT_DURATION_DEFAULT
        == 14
    )


# ============================================================
# 1. CANONICAL INPUT SURFACE
# ============================================================

def test_01_planning_settings_contains_all_shared_inputs():
    cls = _settings_class_or_skip()

    fields = set(
        cls.model_fields
    )

    missing = (
        REQUIRED_INPUT_FIELDS
        - fields
    )

    assert not missing, (
        "PlanningSettingsV1 is missing "
        f"shared planning inputs: {sorted(missing)}"
    )


# ============================================================
# 2. INPUT MODEL MUST NOT BECOME A PLANNER RESULT
# ============================================================

def test_02_planning_settings_contains_no_planner_output_authority():
    cls = _settings_class_or_skip()

    fields = set(
        cls.model_fields
    )

    leaked = (
        FORBIDDEN_OUTPUT_AUTHORITY_FIELDS
        &
        fields
    )

    assert not leaked, (
        "PlanningSettingsV1 leaks deterministic "
        f"planner/metrics authority: {sorted(leaked)}"
    )


# ============================================================
# 3. FAIL CLOSED ON UNKNOWN SETTINGS
# ============================================================

def test_03_planning_settings_forbids_unknown_fields():
    cls = _settings_class_or_skip()

    config = dict(
        cls.model_config
    )

    assert config.get(
        "extra"
    ) == "forbid", (
        "PlanningSettingsV1 must fail closed "
        "on unknown configuration fields."
    )


# ============================================================
# 4. SPRINT COUNT MUST NOT BE A HIDDEN FIXED SIX-SPRINT PLAN
# ============================================================

def test_04_sprint_count_has_no_silent_fixed_default():
    cls = _settings_class_or_skip()

    field = cls.model_fields[
        "sprint_count"
    ]

    assert field.is_required(), (
        "sprint_count must be supplied explicitly "
        "at this shared-input stage; ForgeAI must "
        "not silently hardcode a fixed sprint count."
    )


# ============================================================
# 5. 14-DAY DEFAULT IS ALLOWED, NEVER MANDATORY
# ============================================================

def test_05_sprint_duration_is_configurable_even_if_default_is_14():
    cls = _settings_class_or_skip()

    field = cls.model_fields[
        "sprint_duration_days"
    ]

    # Both forms are valid at this architectural stage:
    #
    # 1. explicit value required;
    # 2. configurable field with the plan's allowed 14-day default.
    #
    # What is forbidden is silently choosing another undocumented
    # fixed default before the dedicated PlanningSettings validation lot.

    if not field.is_required():
        assert field.default == (
            ALLOWED_SPRINT_DURATION_DEFAULT
        ), (
            "If sprint_duration_days has a default "
            "before S4.11 validation, the only "
            "plan-supported default is 14."
        )


# ============================================================
# 6. NO ACTUAL-METRIC AUTHORITY IN SETTINGS
# ============================================================

def test_06_planning_settings_never_claims_actual_execution_metrics():
    cls = _settings_class_or_skip()

    fields = set(
        cls.model_fields
    )

    actual_metric_fields = {
        "actual_velocity",
        "actual_burndown",
        "actual_capacity",
        "actual_completed_points",
    }

    leaked = (
        actual_metric_fields
        &
        fields
    )

    assert not leaked, (
        "PlanningSettingsV1 cannot contain "
        f"observed execution metrics: {sorted(leaked)}"
    )


# ============================================================
# 7. CONTRACT MUST REMAIN UNIVERSAL
# ============================================================

def test_07_planning_settings_contract_is_fixture_free_and_structural():
    import ast

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
            "PlanningSettings contract must "
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
        "PlanningSettings semantics must not "
        "depend on example-specific "
        f"parametrization: {parameterized}"
    )
