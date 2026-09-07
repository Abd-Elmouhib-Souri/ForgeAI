from __future__ import annotations

from copy import deepcopy
import ast
import importlib
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


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "PRIORITY_AWARE_TOPOLOGICAL_ORDER_NOT_IMPLEMENTED"
)


EXPECTED_METHOD = (
    "_ordered_story_ids"
)


def _source() -> str:

    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:

    return ast.parse(
        _source()
    )


def _ordering_method_present() -> bool:

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


ORDERING_IMPLEMENTED = (
    _ordering_method_present()
)


ordering_contract = pytest.mark.skipif(
    not ORDERING_IMPLEMENTED,
    reason=(
        "Priority-aware deterministic ordering "
        "has not been implemented yet."
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
        SprintPlanningEngine,
    )

    return (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        DependencyEdgeV1,
        DependencyGraphV1,
        SprintPlanningEngine,
    )


def _story(
    story_id: str,
    priority: str,
):

    (
        _CanonicalBacklogV1,
        CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return CanonicalUserStoryV1.model_construct(
        story_id=story_id,
        priority=priority,
        story_points=3,
        dependencies=[],
        dependency_hint_ids=[],
        locked=False,
        warnings=[],
    )


def _backlog(
    specs: list[
        tuple[
            str,
            str,
        ]
    ],
):

    (
        CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
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
                priority,
            )
            for story_id, priority
            in specs
        ],
        warnings=[],
    )


def _edge(
    story_id: str,
    depends_on_story_id: str,
    *,
    dependency_type: str = "hard_dependency",
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
    ) = _symbols()

    return DependencyEdgeV1(
        story_id=story_id,
        depends_on_story_id=depends_on_story_id,
        dependency_type=dependency_type,
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


def _ordered(
    backlog,
    graph,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
    ) = _symbols()

    return SprintPlanningEngine()._ordered_story_ids(
        backlog=backlog,
        dependency_graph=graph,
    )


def test_00_real_red_anchor_priority_aware_ordering_is_missing():

    assert TARGET.exists()

    if not _ordering_method_present():

        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@ordering_contract
def test_01_engine_exposes_private_deterministic_ordering_boundary():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
    ) = _symbols()

    method = (
        SprintPlanningEngine
        ._ordered_story_ids
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
    )


@ordering_contract
def test_02_independent_ready_stories_follow_moscow_priority():

    backlog = _backlog(
        [
            ("US-001", "Could"),
            ("US-002", "Must"),
            ("US-003", "Won't"),
            ("US-004", "Should"),
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

    assert _ordered(
        backlog,
        graph,
    ) == [
        "US-002",
        "US-004",
        "US-001",
        "US-003",
    ]


@ordering_contract
def test_03_hard_dependency_always_beats_higher_priority_dependent():

    backlog = _backlog(
        [
            ("US-001", "Could"),
            ("US-002", "Must"),
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

    assert _ordered(
        backlog,
        graph,
    ) == [
        "US-001",
        "US-002",
    ]


@ordering_contract
def test_04_priority_is_applied_only_among_currently_ready_stories():

    backlog = _backlog(
        [
            ("US-001", "Could"),
            ("US-002", "Must"),
            ("US-003", "Should"),
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
            )
        ],
    )

    assert _ordered(
        backlog,
        graph,
    ) == [
        "US-003",
        "US-001",
        "US-002",
    ]


@ordering_contract
def test_05_equal_priority_uses_canonical_topological_order_as_tie_break():

    backlog = _backlog(
        [
            ("US-001", "Should"),
            ("US-002", "Should"),
            ("US-003", "Should"),
        ]
    )

    graph = _graph(
        [
            "US-003",
            "US-001",
            "US-002",
        ]
    )

    assert _ordered(
        backlog,
        graph,
    ) == [
        "US-003",
        "US-001",
        "US-002",
    ]


@ordering_contract
def test_06_soft_dependency_never_becomes_hard_ordering_constraint():

    backlog = _backlog(
        [
            ("US-001", "Must"),
            ("US-002", "Could"),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
        ],
        edges=[
            _edge(
                "US-001",
                "US-002",
                dependency_type="soft_dependency",
            )
        ],
    )

    assert _ordered(
        backlog,
        graph,
    ) == [
        "US-001",
        "US-002",
    ]


@ordering_contract
def test_07_wont_is_lowest_priority_but_remains_traceable_in_order():

    backlog = _backlog(
        [
            ("US-001", "Won't"),
            ("US-002", "Could"),
            ("US-003", "Should"),
            ("US-004", "Must"),
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

    result = _ordered(
        backlog,
        graph,
    )

    assert result == [
        "US-004",
        "US-003",
        "US-002",
        "US-001",
    ]

    assert set(
        result
    ) == {
        "US-001",
        "US-002",
        "US-003",
        "US-004",
    }


@ordering_contract
def test_08_ordering_is_deterministic_and_does_not_mutate_inputs():

    backlog = _backlog(
        [
            ("US-001", "Could"),
            ("US-002", "Must"),
            ("US-003", "Should"),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    before_backlog = deepcopy(
        backlog
    )

    before_graph = deepcopy(
        graph
    )

    first = _ordered(
        backlog,
        graph,
    )

    second = _ordered(
        backlog,
        graph,
    )

    assert first == second

    assert backlog == before_backlog
    assert graph == before_graph


@ordering_contract
def test_09_hard_dependency_remains_absolute_even_when_dependency_is_wont():

    backlog = _backlog(
        [
            ("US-001", "Won't"),
            ("US-002", "Must"),
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

    assert _ordered(
        backlog,
        graph,
    ) == [
        "US-001",
        "US-002",
    ]