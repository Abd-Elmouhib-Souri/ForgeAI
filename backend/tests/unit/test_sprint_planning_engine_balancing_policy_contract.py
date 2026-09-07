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
    "_balance_assignments"
)


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "DETERMINISTIC_SPRINT_BALANCING_POLICY_NOT_IMPLEMENTED"
)


def _source() -> str:
    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:
    return ast.parse(
        _source()
    )


def _balance_method_present() -> bool:

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


BALANCING_IMPLEMENTED = (
    _balance_method_present()
)


balance_contract = pytest.mark.skipif(
    not BALANCING_IMPLEMENTED,
    reason=(
        "Deterministic Sprint balancing "
        "policy has not been implemented yet."
    ),
)


def _symbols() -> tuple[Any, ...]:

    from app.schemas.project_management import (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
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
        DependencyEdgeV1,
        DependencyGraphV1,
        SprintAssignmentV1,
        SprintPlanningEngine,
    )


def _story(
    story_id: str,
    story_points: int,
):

    (
        _CanonicalBacklogV1,
        CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return CanonicalUserStoryV1.model_construct(
        story_id=story_id,
        priority="Should",
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


def _assignments(
    specs: list[
        tuple[
            str,
            int,
        ]
    ],
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintAssignmentV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return [
        SprintAssignmentV1(
            story_id=story_id,
            sprint_number=sprint_number,
        )
        for story_id, sprint_number
        in specs
    ]


def _balance(
    backlog,
    graph,
    assignments,
    *,
    sprint_capacity: float = 10.0,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        SprintPlanningEngine,
    ) = _symbols()

    return SprintPlanningEngine()._balance_assignments(
        backlog=backlog,
        dependency_graph=graph,
        assignments=assignments,
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


def _loads(
    backlog,
    assignments,
) -> dict[int, float]:

    points = {
        story.story_id: float(
            story.story_points
        )
        for story in backlog.stories
    }

    result: dict[int, float] = {}

    for item in assignments:
        result.setdefault(
            item.sprint_number,
            0.0,
        )

        result[
            item.sprint_number
        ] += points[
            item.story_id
        ]

    return result


def _spread(
    backlog,
    assignments,
) -> float:

    loads = list(
        _loads(
            backlog,
            assignments,
        ).values()
    )

    if len(loads) <= 1:
        return 0.0

    return max(loads) - min(loads)


def test_00_real_red_anchor_balancing_policy_is_missing():

    assert TARGET.exists()

    if not _balance_method_present():
        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@balance_contract
def test_01_engine_exposes_private_deterministic_balancing_boundary():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        SprintPlanningEngine,
    ) = _symbols()

    method = (
        SprintPlanningEngine
        ._balance_assignments
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
        "assignments",
        "sprint_capacity",
    )


@balance_contract
def test_02_empty_assignments_remain_empty():

    backlog = _backlog(
        []
    )

    graph = _graph(
        []
    )

    assert _balance(
        backlog,
        graph,
        [],
    ) == []


@balance_contract
def test_03_single_used_sprint_is_not_spread_into_new_sprints():

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

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
    )

    assert _pairs(
        balanced
    ) == _pairs(
        original
    )


@balance_contract
def test_04_forward_boundary_shift_strictly_improves_load_spread():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
        sprint_capacity=10.0,
    )

    assert _pairs(
        balanced
    ) == [
        ("US-001", 1),
        ("US-002", 2),
        ("US-003", 2),
    ]

    assert _spread(
        backlog,
        balanced,
    ) < _spread(
        backlog,
        original,
    )


@balance_contract
def test_05_balancing_never_moves_story_to_an_earlier_sprint():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
            ("US-004", 2),
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

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
            ("US-004", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
        sprint_capacity=10.0,
    )

    original_sprint = {
        item.story_id: item.sprint_number
        for item in original
    }

    assert all(
        item.sprint_number
        >= original_sprint[
            item.story_id
        ]
        for item in balanced
    )


@balance_contract
def test_06_balancing_preserves_exact_story_set_and_certified_order():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
    )

    assert [
        item.story_id
        for item in balanced
    ] == [
        item.story_id
        for item in original
    ]

    assert len(
        balanced
    ) == len(
        {
            item.story_id
            for item in balanced
        }
    )


@balance_contract
def test_07_balancing_preserves_used_sprint_count_and_no_empty_used_sprint():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
    )

    original_used = sorted(
        {
            item.sprint_number
            for item in original
        }
    )

    balanced_used = sorted(
        {
            item.sprint_number
            for item in balanced
        }
    )

    assert balanced_used == original_used

    assert balanced_used == list(
        range(
            1,
            max(
                balanced_used
            )
            + 1,
        )
    )


@balance_contract
def test_08_balancing_never_exceeds_sprint_capacity():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
            ("US-004", 2),
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

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
            ("US-004", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
        sprint_capacity=10.0,
    )

    assert all(
        load <= 10.0
        for load in _loads(
            backlog,
            balanced,
        ).values()
    )


@balance_contract
def test_09_hard_dependency_remains_same_or_earlier_than_dependent():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
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
                "US-003",
                "US-002",
            )
        ],
    )

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
        sprint_capacity=10.0,
    )

    sprint_by_story = {
        item.story_id: item.sprint_number
        for item in balanced
    }

    assert (
        sprint_by_story[
            "US-002"
        ]
        <= sprint_by_story[
            "US-003"
        ]
    )


@balance_contract
def test_10_no_strict_balance_improvement_preserves_original_assignments():

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
        ]
    )

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
        sprint_capacity=10.0,
    )

    assert _pairs(
        balanced
    ) == _pairs(
        original
    )


@balance_contract
def test_11_balancing_never_increases_load_spread():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
            ("US-004", 2),
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

    original = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
            ("US-004", 2),
        ]
    )

    balanced = _balance(
        backlog,
        graph,
        original,
        sprint_capacity=10.0,
    )

    assert _spread(
        backlog,
        balanced,
    ) <= _spread(
        backlog,
        original,
    )


@balance_contract
def test_12_balancing_does_not_absorb_overflow_lock_priority_or_ai_authority():

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

    attributes = {
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

    signature = inspect.signature(
        _symbols()[-1]._balance_assignments
    )

    assert (
        "overflow_story_ids"
        not in signature.parameters
    )

    assert (
        "unplaced_story_ids"
        not in signature.parameters
    )

    assert (
        "advice"
        not in signature.parameters
    )

    for forbidden_attribute in (
        "priority",
        "split_recommended",
        "locked",
        "recommendations",
    ):
        assert forbidden_attribute not in attributes

    for forbidden_name in (
        "ScrumMasterAdviceV1",
        "SprintPlanningResultV1",
    ):
        assert forbidden_name not in referenced_names


@balance_contract
def test_13_balancing_is_deterministic_and_does_not_mutate_inputs():

    backlog = _backlog(
        [
            ("US-001", 6),
            ("US-002", 4),
            ("US-003", 4),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    assignments = _assignments(
        [
            ("US-001", 1),
            ("US-002", 1),
            ("US-003", 2),
        ]
    )

    before_backlog = deepcopy(
        backlog
    )

    before_graph = deepcopy(
        graph
    )

    before_assignments = deepcopy(
        assignments
    )

    engine = _symbols()[-1]()

    first = engine._balance_assignments(
        backlog=backlog,
        dependency_graph=graph,
        assignments=assignments,
        sprint_capacity=10.0,
    )

    second = engine._balance_assignments(
        backlog=backlog,
        dependency_graph=graph,
        assignments=assignments,
        sprint_capacity=10.0,
    )

    assert first == second

    assert backlog == before_backlog
    assert graph == before_graph
    assert assignments == before_assignments