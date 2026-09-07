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
    "_project_overflow"
)


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "DETERMINISTIC_OVERFLOW_PROJECTION_NOT_IMPLEMENTED"
)


WARNING_PREFIX = (
    "sprint_overflow:"
)


def _source() -> str:

    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:

    return ast.parse(
        _source()
    )


def _overflow_method_present() -> bool:

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


OVERFLOW_IMPLEMENTED = (
    _overflow_method_present()
)


overflow_contract = pytest.mark.skipif(
    not OVERFLOW_IMPLEMENTED,
    reason=(
        "Deterministic overflow projection "
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
    story_points: int,
    *,
    priority: str = "Should",
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


def _project(
    backlog,
    graph,
    unplaced_story_ids,
    *,
    sprint_capacity: float,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
    ) = _symbols()

    return SprintPlanningEngine()._project_overflow(
        backlog=backlog,
        dependency_graph=graph,
        unplaced_story_ids=unplaced_story_ids,
        sprint_capacity=sprint_capacity,
    )


def test_00_real_red_anchor_overflow_projection_is_missing():

    assert TARGET.exists()

    if not _overflow_method_present():
        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@overflow_contract
def test_01_engine_exposes_private_deterministic_overflow_boundary():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
    ) = _symbols()

    method = (
        SprintPlanningEngine
        ._project_overflow
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
        "unplaced_story_ids",
        "sprint_capacity",
    )


@overflow_contract
def test_02_no_unplaced_story_produces_no_public_overflow():

    backlog = _backlog(
        [
            ("US-001", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
        ]
    )

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [],
        sprint_capacity=10.0,
    )

    assert overflow_ids == []
    assert warnings == []


@overflow_contract
def test_03_every_unplaced_story_remains_visible_in_public_overflow():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 3),
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

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_capacity=10.0,
    )

    assert overflow_ids == [
        "US-001",
        "US-002",
        "US-003",
    ]

    assert len(warnings) == 3


@overflow_contract
def test_04_oversized_story_has_explicit_reason():

    backlog = _backlog(
        [
            ("US-001", 13),
        ]
    )

    graph = _graph(
        [
            "US-001",
        ]
    )

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
        ],
        sprint_capacity=10.0,
    )

    assert overflow_ids == [
        "US-001",
    ]

    assert warnings == [
        (
            "sprint_overflow:"
            "story_exceeds_sprint_capacity:"
            "US-001"
        )
    ]


@overflow_contract
def test_05_zero_capacity_has_explicit_reason_before_oversized_classification():

    backlog = _backlog(
        [
            ("US-001", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
        ]
    )

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
        ],
        sprint_capacity=0.0,
    )

    assert overflow_ids == [
        "US-001",
    ]

    assert warnings == [
        "sprint_overflow:zero_capacity:US-001"
    ]


@overflow_contract
def test_06_blocked_dependency_reason_has_precedence_for_dependent_story():

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
        ],
        edges=[
            _edge(
                "US-002",
                "US-001",
            )
        ],
    )

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
        ],
        sprint_capacity=10.0,
    )

    assert overflow_ids == [
        "US-001",
        "US-002",
    ]

    assert warnings == [
        (
            "sprint_overflow:"
            "story_exceeds_sprint_capacity:"
            "US-001"
        ),
        (
            "sprint_overflow:"
            "blocked_by_unplaced_dependency:"
            "US-002"
        ),
    ]


@overflow_contract
def test_07_individually_feasible_unplaced_story_is_capacity_exhausted():

    backlog = _backlog(
        [
            ("US-001", 8),
        ]
    )

    graph = _graph(
        [
            "US-001",
        ]
    )

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
        ],
        sprint_capacity=10.0,
    )

    assert overflow_ids == [
        "US-001",
    ]

    assert warnings == [
        "sprint_overflow:capacity_exhausted:US-001"
    ]


@overflow_contract
def test_08_dependency_blocking_propagates_causally_through_chain():

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

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_capacity=10.0,
    )

    assert overflow_ids == [
        "US-001",
        "US-002",
        "US-003",
    ]

    assert warnings == [
        (
            "sprint_overflow:"
            "story_exceeds_sprint_capacity:"
            "US-001"
        ),
        (
            "sprint_overflow:"
            "blocked_by_unplaced_dependency:"
            "US-002"
        ),
        (
            "sprint_overflow:"
            "blocked_by_unplaced_dependency:"
            "US-003"
        ),
    ]


@overflow_contract
def test_09_every_public_overflow_has_one_machine_readable_warning():

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
            )
        ],
    )

    overflow_ids, warnings = _project(
        backlog,
        graph,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        sprint_capacity=10.0,
    )

    assert len(warnings) == len(
        overflow_ids
    )

    assert all(
        warning.startswith(
            WARNING_PREFIX
        )
        for warning in warnings
    )

    assert all(
        warning.endswith(
            story_id
        )
        for story_id, warning
        in zip(
            overflow_ids,
            warnings,
            strict=True,
        )
    )


@overflow_contract
def test_10_public_overflow_preserves_certified_unplaced_order():

    backlog = _backlog(
        [
            ("US-001", 13),
            ("US-002", 5),
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

    input_order = [
        "US-003",
        "US-001",
    ]

    overflow_ids, _warnings = _project(
        backlog,
        graph,
        input_order,
        sprint_capacity=10.0,
    )

    assert overflow_ids == input_order


@overflow_contract
def test_11_overflow_projection_is_deterministic_and_does_not_mutate_inputs():

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
        ],
        edges=[
            _edge(
                "US-002",
                "US-001",
            )
        ],
    )

    unplaced = [
        "US-001",
        "US-002",
    ]

    before_backlog = deepcopy(
        backlog
    )

    before_graph = deepcopy(
        graph
    )

    before_unplaced = list(
        unplaced
    )

    first = _project(
        backlog,
        graph,
        unplaced,
        sprint_capacity=10.0,
    )

    second = _project(
        backlog,
        graph,
        unplaced,
        sprint_capacity=10.0,
    )

    assert first == second

    assert backlog == before_backlog
    assert graph == before_graph
    assert unplaced == before_unplaced


@overflow_contract
def test_12_overflow_projection_does_not_absorb_other_planning_authorities():

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

    method_source = ast.unparse(
        method
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

    for forbidden_call in (
        "_ordered_story_ids",
        "_effective_sprint_capacity",
        "_assign_story_ids",
    ):
        assert forbidden_call not in method_source

    plan_method = next(
        node
        for node in engine.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == "plan"
        )
    )

    assert plan_method is not None
