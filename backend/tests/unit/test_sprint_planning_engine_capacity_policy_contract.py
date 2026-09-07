from __future__ import annotations

from copy import deepcopy
import ast
import inspect
import math
from pathlib import Path
from typing import Any

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2]

TARGET = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "sprint_planning_engine.py"
)


EXPECTED_METHOD = (
    "_effective_sprint_capacity"
)


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "EFFECTIVE_SPRINT_CAPACITY_POLICY_NOT_IMPLEMENTED"
)


def _source() -> str:
    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:
    return ast.parse(
        _source()
    )


def _capacity_method_present() -> bool:
    tree = _tree()

    engine = next(
        (
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name
                == "SprintPlanningEngine"
            )
        ),
        None,
    )

    if engine is None:
        return False

    return any(
        (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name
            == EXPECTED_METHOD
        )
        for node in engine.body
    )


CAPACITY_IMPLEMENTED = (
    _capacity_method_present()
)


capacity_contract = pytest.mark.skipif(
    not CAPACITY_IMPLEMENTED,
    reason=(
        "Effective Sprint capacity policy "
        "has not been implemented yet."
    ),
)


def _symbols() -> tuple[Any, ...]:
    from app.schemas.project_management import (
        PlanningSettingsV1,
    )

    from app.services.sprint_planning_engine import (
        SprintPlanningEngine,
        SprintPlanningEngineError,
    )

    return (
        PlanningSettingsV1,
        SprintPlanningEngine,
        SprintPlanningEngineError,
    )


def _settings(
    *,
    sprint_count: int = 4,
    sprint_duration_days: int = 14,
    planned_velocity: float = 8.0,
    team_size: int = 2,
    capacity_adjustment: float = 1.0,
):

    (
        PlanningSettingsV1,
        _SprintPlanningEngine,
        _SprintPlanningEngineError,
    ) = _symbols()

    return PlanningSettingsV1.model_construct(
        sprint_count=sprint_count,
        sprint_duration_days=sprint_duration_days,
        planned_velocity=planned_velocity,
        team_size=team_size,
        capacity_adjustment=capacity_adjustment,
        start_date="2026-09-01",
        working_days=[
            0,
            1,
            2,
            3,
            4,
        ],
    )


def _capacity(
    settings,
) -> float:

    (
        _PlanningSettingsV1,
        SprintPlanningEngine,
        _SprintPlanningEngineError,
    ) = _symbols()

    return (
        SprintPlanningEngine()
        ._effective_sprint_capacity(
            planning_settings=settings,
        )
    )


def _assert_capacity_error(
    settings,
):

    (
        _PlanningSettingsV1,
        _SprintPlanningEngine,
        SprintPlanningEngineError,
    ) = _symbols()

    with pytest.raises(
        SprintPlanningEngineError
    ) as exc_info:

        _capacity(
            settings
        )

    assert (
        exc_info.value.code
        ==
        "invalid_capacity_settings"
    )

    assert getattr(
        exc_info.value,
        "details",
        None,
    )

    return exc_info.value


def test_00_real_red_anchor_effective_capacity_policy_is_missing():

    assert TARGET.exists()

    if not _capacity_method_present():
        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@capacity_contract
def test_01_engine_exposes_private_deterministic_capacity_boundary():

    (
        _PlanningSettingsV1,
        SprintPlanningEngine,
        _SprintPlanningEngineError,
    ) = _symbols()

    method = (
        SprintPlanningEngine
        ._effective_sprint_capacity
    )

    assert not inspect.iscoroutinefunction(
        method
    )

    signature = inspect.signature(
        method
    )

    assert tuple(
        signature.parameters
    ) == (
        "self",
        "planning_settings",
    )

    assert (
        signature.return_annotation
        in (
            float,
            "float",
        )
    )


@capacity_contract
def test_02_neutral_adjustment_preserves_team_planned_velocity():

    settings = _settings(
        planned_velocity=8.0,
        capacity_adjustment=1.0,
    )

    assert _capacity(
        settings
    ) == pytest.approx(
        8.0
    )


@capacity_contract
@pytest.mark.parametrize(
    (
        "velocity",
        "adjustment",
        "expected",
    ),
    [
        (
            10.0,
            0.5,
            5.0,
        ),
        (
            10.0,
            1.25,
            12.5,
        ),
        (
            13.0,
            0.75,
            9.75,
        ),
    ],
)
def test_03_capacity_adjustment_is_a_multiplicative_factor(
    velocity,
    adjustment,
    expected,
):

    settings = _settings(
        planned_velocity=velocity,
        capacity_adjustment=adjustment,
    )

    assert _capacity(
        settings
    ) == pytest.approx(
        expected
    )


@capacity_contract
def test_04_team_size_does_not_multiply_story_point_capacity():

    small_team = _settings(
        planned_velocity=10.0,
        team_size=1,
        capacity_adjustment=1.0,
    )

    larger_team = _settings(
        planned_velocity=10.0,
        team_size=8,
        capacity_adjustment=1.0,
    )

    assert _capacity(
        small_team
    ) == pytest.approx(
        10.0
    )

    assert _capacity(
        larger_team
    ) == pytest.approx(
        10.0
    )


@capacity_contract
def test_05_sprint_count_does_not_change_per_sprint_capacity():

    four_sprints = _settings(
        sprint_count=4,
        planned_velocity=8.0,
        capacity_adjustment=1.0,
    )

    eight_sprints = _settings(
        sprint_count=8,
        planned_velocity=8.0,
        capacity_adjustment=1.0,
    )

    assert _capacity(
        four_sprints
    ) == pytest.approx(
        8.0
    )

    assert _capacity(
        eight_sprints
    ) == pytest.approx(
        8.0
    )


@capacity_contract
def test_06_sprint_duration_is_not_silently_applied_as_capacity_multiplier():

    one_week = _settings(
        sprint_duration_days=7,
        planned_velocity=8.0,
        capacity_adjustment=1.0,
    )

    two_weeks = _settings(
        sprint_duration_days=14,
        planned_velocity=8.0,
        capacity_adjustment=1.0,
    )

    assert _capacity(
        one_week
    ) == pytest.approx(
        8.0
    )

    assert _capacity(
        two_weeks
    ) == pytest.approx(
        8.0
    )


@capacity_contract
@pytest.mark.parametrize(
    (
        "velocity",
        "adjustment",
    ),
    [
        (
            0.0,
            1.0,
        ),
        (
            8.0,
            0.0,
        ),
        (
            0.0,
            0.0,
        ),
    ],
)
def test_07_zero_capacity_is_valid_and_explicit(
    velocity,
    adjustment,
):

    result = _capacity(
        _settings(
            planned_velocity=velocity,
            capacity_adjustment=adjustment,
        )
    )

    assert result == pytest.approx(
        0.0
    )


@capacity_contract
@pytest.mark.parametrize(
    (
        "velocity",
        "adjustment",
    ),
    [
        (
            -1.0,
            1.0,
        ),
        (
            8.0,
            -0.1,
        ),
        (
            float("nan"),
            1.0,
        ),
        (
            float("inf"),
            1.0,
        ),
        (
            8.0,
            float("nan"),
        ),
        (
            8.0,
            float("inf"),
        ),
    ],
)
def test_08_negative_or_non_finite_capacity_inputs_fail_closed(
    velocity,
    adjustment,
):

    _assert_capacity_error(
        _settings(
            planned_velocity=velocity,
            capacity_adjustment=adjustment,
        )
    )


@capacity_contract
def test_09_capacity_policy_is_deterministic_and_does_not_mutate_settings():

    settings = _settings(
        sprint_count=6,
        sprint_duration_days=21,
        planned_velocity=11.0,
        team_size=4,
        capacity_adjustment=0.8,
    )

    before = deepcopy(
        settings
    )

    first = _capacity(
        settings
    )

    second = _capacity(
        settings
    )

    assert first == pytest.approx(
        8.8
    )

    assert second == pytest.approx(
        8.8
    )

    assert first == second

    assert math.isfinite(
        first
    )

    assert settings == before