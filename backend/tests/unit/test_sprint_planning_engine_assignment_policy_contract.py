from __future__ import annotations

from copy import deepcopy
import ast
import inspect
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
    "_assign_story_ids"
)


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "DETERMINISTIC_SPRINT_ASSIGNMENT_POLICY_NOT_IMPLEMENTED"
)


def _source() -> str:
    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:
    return ast.parse(
        _source()
    )


def _assignment_method_present() -> bool:
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


ASSIGNMENT_IMPLEMENTED = (
    _assignment_method_present()
)


assignment_contract = pytest.mark.skipif(
    not ASSIGNMENT_IMPLEMENTED,
    reason=(
        "Deterministic Sprint assignment "
        "policy has not been implemented yet."
    ),
)


def _symbols() -> tuple[Any, ...]:

    from app.schemas.project_management import (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        PlanningSettingsV1,
    )

    from app.services.dependency_graph_builder import (
        DependencyEdgeV1,
        DependencyGraphV1,
    )

    from app.services.sprint_planning_engine import (
        SprintAssignmentV1,
        SprintPlanningEngine,
    )

    return (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        PlanningSettingsV1,
        DependencyEdgeV1,
        DependencyGraphV1,
        SprintAssignmentV1,
        SprintPlanningEngine,
    )


def _story(
    story_id: str,
    story_points: int,
    *,
    priority: str = "Should",
):

    (
        _CanonicalBacklogV1,
        CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return CanonicalUserStoryV1.model_construct(
        story_id=story_id,
        priority=priority,
        story_points=story_points,
        dependencies=[],
        dependency_hint_ids=[],
        locked=False,
        warnings=[],
    )


def _backlog(
    specs: list[
        tuple[
            str,
            int,
        ]
    ],
):

    (
        CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash="src-hash",
        context_hash="ctx-hash",
        epics=[],
        features=[],
        stories=[
            _story(
                story_id,
                story_points,
            )
            for story_id, story_points
            in specs
        ],
        warnings=[],
    )


def _edge(
    story_id: str,
    depends_on_story_id: str,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return DependencyEdgeV1(
        story_id=story_id,
        depends_on_story_id=depends_on_story_id,
        dependency_type="hard_dependency",
    )


def _graph(
    order: list[str],
    *,
    edges=None,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return DependencyGraphV1(
        source_context_hash="src-hash",
        context_hash="ctx-hash",
        edges=list(
            edges or []
        ),
        hard_topological_order=list(
            order
        ),
        warnings=[],
    )


def _settings(
    *,
    sprint_count: int = 4,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return PlanningSettingsV1.model_construct(
        sprint_count=sprint_count,
        sprint_duration_days=14,
        planned_velocity=10.0,
        team_size=2,
        capacity_adjustment=1.0,
        start_date="2026-09-01",
        working_days=[
            0,
            1,
            2,
            3,
            4,
        ],
    )


def _assign(
    backlog,
    graph,
    ordered_story_ids,
    *,
    sprint_count: int = 4,
    sprint_capacity: float = 10.0,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        SprintPlanningEngine,
    ) = _symbols()

    return SprintPlanningEngine()._assign_story_ids(
        backlog=backlog,
        dependency_graph=graph,
        ordered_story_ids=ordered_story_ids,
        planning_settings=_settings(
            sprint_count=sprint_count,
        ),
        sprint_capacity=sprint_capacity,
    )


def _pairs(
    assignments,
):
    return [
        (
            item.story_id,
            item.sprint_number,
        )
        for item in assignments
    ]


def test_00_real_red_anchor_assignment_policy_is_missing():

    assert TARGET.exists()

    if not _assignment_method_present():
        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@assignment_contract
def test_01_engine_exposes_private_deterministic_assignment_boundary():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        SprintPlanningEngine,
    ) = _symbols()

    method = (
        SprintPlanningEngine
        ._assign_story_ids
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
        "backlog",
        "dependency_graph",
        "ordered_story_ids",
        "planning_settings",
        "sprint_capacity",
    )


@assignment_contract
def test_02_sequential_next_fit_assignment_respects_capacity():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 5),
            ("US-003", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_capacity=10.0,
    )

    assert _pairs(
        assignments
    ) == [
        ("US-001", 1),
        ("US-002", 1),
        ("US-003", 2),
    ]

    assert unplaced == []


@assignment_contract
def test_03_assignment_does_not_backfill_earlier_sprint():

    backlog = _backlog(
        [
            ("US-001", 8),
            ("US-002", 5),
            ("US-003", 2),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_capacity=10.0,
    )

    assert _pairs(
        assignments
    ) == [
        ("US-001", 1),
        ("US-002", 2),
        ("US-003", 2),
    ]

    assert unplaced == []


@assignment_contract
def test_04_hard_dependency_may_share_sprint_but_must_appear_first():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
        ],
        edges=[
            _edge(
                "US-002",
                "US-001",
            )
        ],
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
        ],
        sprint_capacity=10.0,
    )

    assert _pairs(
        assignments
    ) == [
        ("US-001", 1),
        ("US-002", 1),
    ]

    assert unplaced == []


@assignment_contract
def test_05_unplaced_hard_dependency_blocks_its_dependents():

    backlog = _backlog(
        [
            ("US-001", 13),
            ("US-002", 5),
            ("US-003", 3),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        edges=[
            _edge(
                "US-002",
                "US-001",
            ),
            _edge(
                "US-003",
                "US-002",
            ),
        ],
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_capacity=10.0,
    )

    assert assignments == []

    assert unplaced == [
        "US-001",
        "US-002",
        "US-003",
    ]


@assignment_contract
def test_06_oversized_story_does_not_block_unrelated_feasible_story():

    backlog = _backlog(
        [
            ("US-001", 13),
            ("US-002", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
        ]
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
        ],
        sprint_capacity=10.0,
    )

    assert _pairs(
        assignments
    ) == [
        ("US-002", 1),
    ]

    assert unplaced == [
        "US-001",
    ]


@assignment_contract
def test_07_zero_capacity_leaves_all_stories_unplaced():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 3),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
        ]
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
        ],
        sprint_capacity=0.0,
    )

    assert assignments == []

    assert unplaced == [
        "US-001",
        "US-002",
    ]


@assignment_contract
def test_08_configured_sprint_count_is_a_hard_assignment_boundary():

    backlog = _backlog(
        [
            ("US-001", 8),
            ("US-002", 8),
            ("US-003", 8),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_count=2,
        sprint_capacity=10.0,
    )

    assert _pairs(
        assignments
    ) == [
        ("US-001", 1),
        ("US-002", 2),
    ]

    assert unplaced == [
        "US-003",
    ]


@assignment_contract
def test_09_assignment_sprint_numbers_are_monotonic_and_in_range():

    backlog = _backlog(
        [
            ("US-001", 8),
            ("US-002", 5),
            ("US-003", 2),
            ("US-004", 7),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
            "US-004",
        ]
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
            "US-004",
        ],
        sprint_count=4,
        sprint_capacity=10.0,
    )

    sprint_numbers = [
        item.sprint_number
        for item in assignments
    ]

    assert sprint_numbers == sorted(
        sprint_numbers
    )

    assert all(
        1 <= sprint_number <= 4
        for sprint_number in sprint_numbers
    )

    assert unplaced == []


@assignment_contract
def test_10_unplaced_ids_are_unique_and_follow_certified_order():

    backlog = _backlog(
        [
            ("US-001", 13),
            ("US-002", 5),
            ("US-003", 13),
            ("US-004", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
            "US-004",
        ],
        edges=[
            _edge(
                "US-002",
                "US-001",
            )
        ],
    )

    assignments, unplaced = _assign(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
            "US-004",
        ],
        sprint_capacity=10.0,
    )

    assert _pairs(
        assignments
    ) == [
        ("US-004", 1),
    ]

    assert unplaced == [
        "US-001",
        "US-002",
        "US-003",
    ]

    assert len(
        unplaced
    ) == len(
        set(unplaced)
    )


@assignment_contract
def test_11_assignment_is_deterministic_and_does_not_mutate_inputs():

    backlog = _backlog(
        [
            ("US-001", 8),
            ("US-002", 5),
            ("US-003", 2),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    settings = _settings(
        sprint_count=4,
    )

    ordered = [
        "US-001",
        "US-002",
        "US-003",
    ]

    before_backlog = deepcopy(
        backlog
    )

    before_graph = deepcopy(
        graph
    )

    before_settings = deepcopy(
        settings
    )

    before_ordered = list(
        ordered
    )

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        SprintPlanningEngine,
    ) = _symbols()

    engine = SprintPlanningEngine()

    first = engine._assign_story_ids(
        backlog=backlog,
        dependency_graph=graph,
        ordered_story_ids=ordered,
        planning_settings=settings,
        sprint_capacity=10.0,
    )

    second = engine._assign_story_ids(
        backlog=backlog,
        dependency_graph=graph,
        ordered_story_ids=ordered,
        planning_settings=settings,
        sprint_capacity=10.0,
    )

    assert first == second

    assert backlog == before_backlog
    assert graph == before_graph
    assert settings == before_settings
    assert ordered == before_ordered


@assignment_contract
def test_12_assignment_helper_does_not_absorb_split_lock_or_ai_authority():

    tree = _tree()

    engine = next(
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
    )

    method = next(
        node
        for node in engine.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == EXPECTED_METHOD
        )
    )

    attribute_names = {
        node.attr
        for node in ast.walk(
            method
        )
        if isinstance(
            node,
            ast.Attribute,
        )
    }

    referenced_names = {
        node.id
        for node in ast.walk(
            method
        )
        if isinstance(
            node,
            ast.Name,
        )
    }

    assert "split_recommended" not in attribute_names
    assert "locked" not in attribute_names

    assert "ScrumMasterAdviceV1" not in referenced_names

    signature = inspect.signature(
        _symbols()[-1]._assign_story_ids
    )

    assert "advice" not in signature.parameters