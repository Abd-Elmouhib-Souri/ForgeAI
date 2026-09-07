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

EXPECTED_METHOD = "_validate_final_plan"

FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "FINAL_SPRINT_PLANNING_RESULT_VALIDATION_NOT_IMPLEMENTED"
)

EXPECTED_ERROR_CODE = "planning_result_invalid"


def _source() -> str:
    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:
    return ast.parse(
        _source()
    )


def _method_present() -> bool:

    tree = _tree()

    engine = next(
        (
            node
            for node in tree.body
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "SprintPlanningEngine"
            )
        ),
        None,
    )

    if engine is None:
        return False

    return any(
        isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == EXPECTED_METHOD
        for node in engine.body
    )


FINAL_VALIDATION_IMPLEMENTED = (
    _method_present()
)


validation_contract = pytest.mark.skipif(
    not FINAL_VALIDATION_IMPLEMENTED,
    reason=(
        "Final Sprint Planning result validator "
        "has not been implemented yet."
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
        SprintPlanningEngineError,
        SprintPlanningResultV1,
    )

    return (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        PlanningSettingsV1,
        DependencyEdgeV1,
        DependencyGraphV1,
        SprintAssignmentV1,
        SprintPlanningEngine,
        SprintPlanningEngineError,
        SprintPlanningResultV1,
    )


def _story(
    story_id: str,
    story_points: int,
):

    (
        _CanonicalBacklogV1,
        CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
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
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
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
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
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
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
    ) = _symbols()

    return DependencyGraphV1(
        source_context_hash="src-hash",
        context_hash="ctx-hash",
        edges=list(edges or []),
        hard_topological_order=list(order),
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
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
    ) = _symbols()

    return PlanningSettingsV1.model_construct(
        sprint_count=sprint_count,
        sprint_duration_days=14,
        planned_velocity=10.0,
        team_size=2,
        capacity_adjustment=1.0,
        start_date="2026-09-01",
        working_days=[0, 1, 2, 3, 4],
    )


def _assignment(
    story_id: str,
    sprint_number: int,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintAssignmentV1,
        _SprintPlanningEngine,
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
    ) = _symbols()

    return SprintAssignmentV1.model_construct(
        story_id=story_id,
        sprint_number=sprint_number,
    )


def _result(
    *,
    assignments,
    overflow_story_ids,
    warnings,
    source_context_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
    sprint_count: int = 4,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
        _SprintPlanningEngineError,
        SprintPlanningResultV1,
    ) = _symbols()

    return SprintPlanningResultV1.model_construct(
        schema_version="sprint_planning_result_v1",
        source_context_hash=source_context_hash,
        context_hash=context_hash,
        sprint_count=sprint_count,
        assignments=list(assignments),
        overflow_story_ids=list(
            overflow_story_ids
        ),
        warnings=list(warnings),
    )


def _valid_case():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 5),
            ("US-003", 13),
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

    settings = _settings(
        sprint_count=4
    )

    ordered = [
        "US-001",
        "US-002",
        "US-003",
    ]

    result = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            )
        ],
    )

    return (
        backlog,
        graph,
        settings,
        ordered,
        result,
    )


def _validate(
    backlog,
    graph,
    settings,
    ordered_story_ids,
    result,
    *,
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
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
    ) = _symbols()

    return SprintPlanningEngine()._validate_final_plan(
        backlog=backlog,
        dependency_graph=graph,
        planning_settings=settings,
        ordered_story_ids=ordered_story_ids,
        result=result,
        sprint_capacity=sprint_capacity,
    )


def _assert_invalid(
    backlog,
    graph,
    settings,
    ordered_story_ids,
    result,
    *,
    detail_token: str,
    sprint_capacity: float = 10.0,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        _SprintPlanningEngine,
        SprintPlanningEngineError,
        _SprintPlanningResultV1,
    ) = _symbols()

    with pytest.raises(
        SprintPlanningEngineError
    ) as exc_info:

        _validate(
            backlog,
            graph,
            settings,
            ordered_story_ids,
            result,
            sprint_capacity=sprint_capacity,
        )

    assert exc_info.value.code == (
        EXPECTED_ERROR_CODE
    )

    assert exc_info.value.details

    assert any(
        detail_token in detail
        for detail
        in exc_info.value.details
    )


def test_00_real_red_anchor_final_validation_is_missing():

    assert TARGET.exists()

    if not _method_present():
        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@validation_contract
def test_01_engine_exposes_private_final_validation_boundary():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintAssignmentV1,
        SprintPlanningEngine,
        _SprintPlanningEngineError,
        _SprintPlanningResultV1,
    ) = _symbols()

    method = (
        SprintPlanningEngine
        ._validate_final_plan
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
        "planning_settings",
        "ordered_story_ids",
        "result",
        "sprint_capacity",
    )


@validation_contract
def test_02_valid_complete_result_passes_without_mutation():

    (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) = _valid_case()

    before = deepcopy(
        (
            backlog,
            graph,
            settings,
            ordered,
            result,
        )
    )

    assert (
        _validate(
            backlog,
            graph,
            settings,
            ordered,
            result,
        )
        is None
    )

    assert (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) == before


@validation_contract
def test_03_certified_order_must_cover_canonical_story_set_exactly():

    (
        backlog,
        graph,
        settings,
        _ordered,
        result,
    ) = _valid_case()

    for corrupted in (
        [
            "US-001",
            "US-002",
        ],
        [
            "US-001",
            "US-002",
            "US-003",
            "US-003",
        ],
        [
            "US-001",
            "US-002",
            "US-999",
        ],
    ):

        _assert_invalid(
            backlog,
            graph,
            settings,
            corrupted,
            result,
            detail_token=(
                "certified_order_mismatch"
            ),
        )


@validation_contract
def test_04_result_binding_must_match_canonical_authorities():

    (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) = _valid_case()

    source_bad = deepcopy(result)
    source_bad.source_context_hash = (
        "wrong-source"
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        source_bad,
        detail_token=(
            "source_context_hash_mismatch"
        ),
    )

    context_bad = deepcopy(result)
    context_bad.context_hash = (
        "wrong-context"
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        context_bad,
        detail_token=(
            "context_hash_mismatch"
        ),
    )

    sprint_bad = deepcopy(result)
    sprint_bad.sprint_count = 8

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        sprint_bad,
        detail_token=(
            "sprint_count_mismatch"
        ),
    )


@validation_contract
def test_05_result_rejects_unknown_story_reference():

    (
        backlog,
        graph,
        settings,
        ordered,
        _result_value,
    ) = _valid_case()

    corrupted = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-999",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-002",
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "capacity_exhausted:"
                "US-002"
            ),
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            ),
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        corrupted,
        detail_token=(
            "unknown_story_reference"
        ),
    )


@validation_contract
def test_06_every_canonical_story_must_be_in_exactly_one_public_partition():

    (
        backlog,
        graph,
        settings,
        ordered,
        _result_value,
    ) = _valid_case()

    missing = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            ),
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        missing,
        detail_token=(
            "story_partition_mismatch"
        ),
    )


@validation_contract
def test_07_assignments_and_overflow_must_be_disjoint():

    (
        backlog,
        graph,
        settings,
        ordered,
        _result_value,
    ) = _valid_case()

    overlap = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-002",
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "capacity_exhausted:"
                "US-002"
            ),
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            ),
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        overlap,
        detail_token=(
            "story_partition_overlap"
        ),
    )


@validation_contract
def test_08_assignment_story_ids_must_be_unique():

    (
        backlog,
        graph,
        settings,
        ordered,
        _result_value,
    ) = _valid_case()

    duplicate = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            ),
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        duplicate,
        detail_token=(
            "duplicate_assignment_story"
        ),
    )


@validation_contract
def test_09_overflow_story_ids_must_be_unique():

    (
        backlog,
        graph,
        settings,
        ordered,
        _result_value,
    ) = _valid_case()

    duplicate = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-003",
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            ),
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            ),
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        duplicate,
        detail_token=(
            "duplicate_overflow_story"
        ),
    )


@validation_contract
def test_10_assignment_sprint_numbers_must_be_real_ints_and_in_range():

    (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) = _valid_case()

    for invalid_number in (
        True,
        0,
        5,
    ):

        corrupted = deepcopy(result)

        corrupted.assignments[0] = (
            _assignment(
                "US-001",
                invalid_number,
            )
        )

        _assert_invalid(
            backlog,
            graph,
            settings,
            ordered,
            corrupted,
            detail_token=(
                "invalid_assignment_sprint"
            ),
        )


@validation_contract
def test_11_final_balanced_sprint_load_must_not_exceed_capacity():

    backlog = _backlog(
        [
            ("US-001", 8),
            ("US-002", 5),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
        ]
    )

    settings = _settings()

    result = _result(
        assignments=[
            _assignment(
                "US-001",
                1,
            ),
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[],
        warnings=[],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        [
            "US-001",
            "US-002",
        ],
        result,
        detail_token=(
            "sprint_capacity_exceeded"
        ),
        sprint_capacity=10.0,
    )


@validation_contract
def test_12_hard_dependency_must_not_be_in_later_sprint_than_dependent():

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

    settings = _settings()

    result = _result(
        assignments=[
            _assignment(
                "US-001",
                2,
            ),
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[],
        warnings=[],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        [
            "US-001",
            "US-002",
        ],
        result,
        detail_token=(
            "hard_dependency_sprint_violation"
        ),
    )


@validation_contract
def test_13_assigned_story_cannot_depend_on_public_overflow_story():

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

    settings = _settings()

    result = _result(
        assignments=[
            _assignment(
                "US-002",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-001",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-001"
            )
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        [
            "US-001",
            "US-002",
        ],
        result,
        detail_token=(
            "assigned_story_blocked_by_overflow_dependency"
        ),
    )


@validation_contract
def test_14_assignment_and_overflow_order_preserve_certified_story_order():

    (
        backlog,
        graph,
        settings,
        ordered,
        _result_value,
    ) = _valid_case()

    reversed_assignments = _result(
        assignments=[
            _assignment(
                "US-002",
                1,
            ),
            _assignment(
                "US-001",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-003",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-003"
            )
        ],
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        reversed_assignments,
        detail_token=(
            "assignment_order_mismatch"
        ),
    )

    backlog_two = _backlog(
        [
            ("US-001", 13),
            ("US-002", 13),
            ("US-003", 5),
        ]
    )

    graph_two = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    reversed_overflow = _result(
        assignments=[
            _assignment(
                "US-003",
                1,
            ),
        ],
        overflow_story_ids=[
            "US-002",
            "US-001",
        ],
        warnings=[
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-002"
            ),
            (
                "sprint_overflow:"
                "story_exceeds_sprint_capacity:"
                "US-001"
            ),
        ],
    )

    _assert_invalid(
        backlog_two,
        graph_two,
        settings,
        [
            "US-001",
            "US-002",
            "US-003",
        ],
        reversed_overflow,
        detail_token=(
            "overflow_order_mismatch"
        ),
    )


@validation_contract
def test_15_overflow_warnings_must_match_public_overflow_semantics():

    (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) = _valid_case()

    wrong_reason = deepcopy(result)

    wrong_reason.warnings = [
        (
            "sprint_overflow:"
            "capacity_exhausted:"
            "US-003"
        )
    ]

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        wrong_reason,
        detail_token=(
            "overflow_warning_mismatch"
        ),
    )

    missing_warning = deepcopy(result)
    missing_warning.warnings = []

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        missing_warning,
        detail_token=(
            "overflow_warning_mismatch"
        ),
    )

    stray_warning = deepcopy(result)

    stray_warning.warnings.append(
        (
            "sprint_overflow:"
            "capacity_exhausted:"
            "US-001"
        )
    )

    _assert_invalid(
        backlog,
        graph,
        settings,
        ordered,
        stray_warning,
        detail_token=(
            "overflow_warning_mismatch"
        ),
    )

    informational_warning = deepcopy(
        result
    )

    informational_warning.warnings.append(
        "planner_note:informational"
    )

    assert (
        _validate(
            backlog,
            graph,
            settings,
            ordered,
            informational_warning,
        )
        is None
    )


@validation_contract
def test_16_final_validator_is_deterministic_and_does_not_absorb_other_authorities():

    (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) = _valid_case()

    before = deepcopy(
        (
            backlog,
            graph,
            settings,
            ordered,
            result,
        )
    )

    engine = _symbols()[6]

    first_engine = engine()
    second_engine = engine()

    assert (
        first_engine._validate_final_plan(
            backlog=backlog,
            dependency_graph=graph,
            planning_settings=settings,
            ordered_story_ids=ordered,
            result=result,
            sprint_capacity=10.0,
        )
        is None
    )

    assert (
        second_engine._validate_final_plan(
            backlog=backlog,
            dependency_graph=graph,
            planning_settings=settings,
            ordered_story_ids=ordered,
            result=result,
            sprint_capacity=10.0,
        )
        is None
    )

    assert (
        backlog,
        graph,
        settings,
        ordered,
        result,
    ) == before

    tree = _tree()

    engine_node = next(
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
        for node in engine_node.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == EXPECTED_METHOD
        )
    )

    method_source = ast.unparse(
        method
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

    for forbidden_attribute in (
        "priority",
        "locked",
        "split_recommended",
        "recommendations",
        "validation_status",
        "metrics",
    ):
        assert forbidden_attribute not in attributes

    for forbidden_name in (
        "ScrumMasterAdviceV1",
        "AgileMetricsBuilder",
    ):
        assert forbidden_name not in referenced_names

    for forbidden_call in (
        "_ordered_story_ids",
        "_effective_sprint_capacity",
        "_assign_story_ids",
        "_project_overflow",
        "_balance_assignments",
    ):
        assert forbidden_call not in method_source

    plan_method = next(
        node
        for node in engine_node.body
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
