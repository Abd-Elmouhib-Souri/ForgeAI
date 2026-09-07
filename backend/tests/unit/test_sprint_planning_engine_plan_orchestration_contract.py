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


OLD_RUNTIME_GATE = (
    "sprint_assignment_runtime_not_certified"
)


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "PLAN_ORCHESTRATION_NOT_IMPLEMENTED"
)


EXPECTED_PIPELINE_TOKENS = (
    "_validate_inputs",
    "_ordered_story_ids",
    "_effective_sprint_capacity",
    "_assign_story_ids",
    "_project_overflow",
    "_balance_assignments",
    "SprintPlanningResultV1",
    "_validate_final_plan",
)


def _source() -> str:

    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:

    return ast.parse(
        _source()
    )


def _engine_node() -> ast.ClassDef:

    return next(
        node
        for node in _tree().body
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name
            == "SprintPlanningEngine"
        )
    )


def _plan_node() -> ast.FunctionDef:

    return next(
        node
        for node
        in _engine_node().body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == "plan"
        )
    )


def _plan_body_source() -> str:

    plan = _plan_node()

    return "\n".join(
        ast.unparse(
            statement
        )
        for statement
        in plan.body
    )


def _orchestration_implemented() -> bool:

    source = _source()

    if OLD_RUNTIME_GATE in source:
        return False

    plan_source = (
        _plan_body_source()
    )

    return all(
        token in plan_source
        for token
        in EXPECTED_PIPELINE_TOKENS
    )


ORCHESTRATION_IMPLEMENTED = (
    _orchestration_implemented()
)


runtime_contract = pytest.mark.skipif(
    not ORCHESTRATION_IMPLEMENTED,
    reason=(
        "Final SprintPlanningEngine "
        "plan() orchestration is not "
        "implemented yet."
    ),
)


def _symbols() -> tuple[Any, ...]:

    from app.schemas.project_management import (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        PlanningSettingsV1,
        ScrumMasterAdviceV1,
        ScrumMasterRecommendationV1,
    )

    from app.services.dependency_graph_builder import (
        DependencyEdgeV1,
        DependencyGraphV1,
    )

    from app.services.sprint_planning_engine import (
        SprintPlanningEngine,
        SprintPlanningResultV1,
    )

    return (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        PlanningSettingsV1,
        ScrumMasterAdviceV1,
        ScrumMasterRecommendationV1,
        DependencyEdgeV1,
        DependencyGraphV1,
        SprintPlanningEngine,
        SprintPlanningResultV1,
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
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    return (
        CanonicalUserStoryV1
        .model_construct(
            story_id=story_id,
            priority=priority,
            story_points=story_points,
            dependencies=[],
            dependency_hint_ids=[],
            locked=False,
            warnings=[],
        )
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
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    return CanonicalBacklogV1.model_construct(
        schema_version=(
            "canonical_backlog_v1"
        ),
        source_context_hash=(
            "src-hash"
        ),
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
    *,
    dependency_type: str = (
        "hard_dependency"
    ),
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    return DependencyEdgeV1(
        story_id=story_id,
        depends_on_story_id=(
            depends_on_story_id
        ),
        dependency_type=(
            dependency_type
        ),
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
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    return DependencyGraphV1(
        source_context_hash=(
            "src-hash"
        ),
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
    planned_velocity: float = 10.0,
    capacity_adjustment: float = 1.0,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    return PlanningSettingsV1.model_construct(
        sprint_count=sprint_count,
        sprint_duration_days=14,
        planned_velocity=(
            planned_velocity
        ),
        team_size=2,
        capacity_adjustment=(
            capacity_adjustment
        ),
        start_date="2026-09-01",
        working_days=[
            0,
            1,
            2,
            3,
            4,
        ],
    )


def _advice(
    story_ids: list[str] | None = None,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        ScrumMasterAdviceV1,
        ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    recommendations = []

    if story_ids:

        recommendations.append(
            ScrumMasterRecommendationV1
            .model_construct(
                recommendation_type=(
                    "sequencing"
                ),
                story_ids=list(
                    story_ids
                ),
                rationale=(
                    "Advisory sequencing only."
                ),
            )
        )

    return ScrumMasterAdviceV1.model_construct(
        schema_version=(
            "scrum_master_advice_v1"
        ),
        source_context_hash=(
            "src-hash"
        ),
        context_hash="ctx-hash",
        recommendations=(
            recommendations
        ),
        warnings=[],
    )


def _plan(
    *,
    backlog,
    graph,
    settings=None,
    advice=None,
    engine=None,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    planner = (
        engine
        or SprintPlanningEngine()
    )

    return planner.plan(
        backlog=backlog,
        dependency_graph=graph,
        planning_settings=(
            settings
            or _settings()
        ),
        advice=(
            advice
            or _advice()
        ),
    )


def _pairs(
    result,
):

    return [
        (
            item.story_id,
            item.sprint_number,
        )
        for item
        in result.assignments
    ]


def test_00_real_red_anchor_plan_orchestration_is_missing():

    assert TARGET.exists()

    if not _orchestration_implemented():
        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@runtime_contract
def test_01_plan_signature_remains_canonical_and_synchronous():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    method = (
        SprintPlanningEngine.plan
    )

    assert not inspect.iscoroutinefunction(
        method
    )

    assert tuple(
        inspect.signature(
            method
        ).parameters
    ) == (
        "self",
        "backlog",
        "dependency_graph",
        "planning_settings",
        "advice",
    )


@runtime_contract
def test_02_plan_executes_certified_pipeline_in_exact_layer_order():

    body = _plan_body_source()

    positions = [
        body.index(
            token
        )
        for token
        in EXPECTED_PIPELINE_TOKENS
    ]

    assert positions == sorted(
        positions
    )

    for helper in (
        "_validate_inputs",
        "_ordered_story_ids",
        "_effective_sprint_capacity",
        "_assign_story_ids",
        "_project_overflow",
        "_balance_assignments",
        "_validate_final_plan",
    ):
        assert body.count(
            helper
        ) == 1


@runtime_contract
def test_03_valid_plan_returns_bound_minimal_result():

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

    settings = _settings()

    result = _plan(
        backlog=backlog,
        graph=graph,
        settings=settings,
    )

    assert result.schema_version == (
        "sprint_planning_result_v1"
    )

    assert (
        result.source_context_hash
        == backlog.source_context_hash
    )

    assert (
        result.context_hash
        == backlog.context_hash
    )

    assert (
        result.sprint_count
        == settings.sprint_count
    )

    assert _pairs(
        result
    ) == [
        ("US-001", 1),
        ("US-002", 1),
    ]

    assert (
        result.overflow_story_ids
        == []
    )

    assert result.warnings == []


@runtime_contract
def test_04_plan_uses_balanced_assignments_not_raw_assignment_output():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 5),
            ("US-003", 3),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    result = _plan(
        backlog=backlog,
        graph=graph,
    )

    assert _pairs(
        result
    ) == [
        ("US-001", 1),
        ("US-002", 2),
        ("US-003", 2),
    ]


@runtime_contract
def test_05_plan_publishes_explicit_oversized_story_overflow():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 13),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
        ]
    )

    result = _plan(
        backlog=backlog,
        graph=graph,
    )

    assert _pairs(
        result
    ) == [
        ("US-001", 1),
    ]

    assert (
        result.overflow_story_ids
        == [
            "US-002",
        ]
    )

    assert result.warnings == [
        (
            "sprint_overflow:"
            "story_exceeds_sprint_capacity:"
            "US-002"
        )
    ]


@runtime_contract
def test_06_zero_capacity_is_explicit_and_never_silent():

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

    result = _plan(
        backlog=backlog,
        graph=graph,
        settings=_settings(
            planned_velocity=0.0,
        ),
    )

    assert result.assignments == []

    assert (
        result.overflow_story_ids
        == [
            "US-001",
            "US-002",
        ]
    )

    assert result.warnings == [
        (
            "sprint_overflow:"
            "zero_capacity:"
            "US-001"
        ),
        (
            "sprint_overflow:"
            "zero_capacity:"
            "US-002"
        ),
    ]


@runtime_contract
def test_07_hard_dependency_blocking_survives_full_orchestration():

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

    result = _plan(
        backlog=backlog,
        graph=graph,
    )

    assert result.assignments == []

    assert (
        result.overflow_story_ids
        == [
            "US-001",
            "US-002",
        ]
    )

    assert result.warnings == [
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


@runtime_contract
def test_08_scrum_master_advice_remains_advisory_only():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 5),
            ("US-003", 3),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    without_advice = _plan(
        backlog=backlog,
        graph=graph,
        advice=_advice(),
    )

    with_advice = _plan(
        backlog=backlog,
        graph=graph,
        advice=_advice(
            story_ids=[
                "US-003",
            ]
        ),
    )

    assert (
        with_advice
        == without_advice
    )


@runtime_contract
def test_09_final_validator_is_called_on_constructed_result_before_return():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        SprintPlanningEngine,
        _SprintPlanningResultV1,
    ) = _symbols()

    class ProbeEngine(
        SprintPlanningEngine
    ):
        def __init__(self):
            self.validated_result = (
                None
            )

        def _validate_final_plan(
            self,
            **kwargs,
        ):
            self.validated_result = (
                kwargs["result"]
            )

            return (
                super()
                ._validate_final_plan(
                    **kwargs
                )
            )

    engine = ProbeEngine()

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

    result = _plan(
        backlog=backlog,
        graph=graph,
        engine=engine,
    )

    assert (
        engine.validated_result
        is result
    )


@runtime_contract
def test_10_plan_is_deterministic_and_does_not_mutate_inputs():

    backlog = _backlog(
        [
            ("US-001", 5),
            ("US-002", 5),
            ("US-003", 3),
        ]
    )

    graph = _graph(
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )

    settings = _settings()

    advice = _advice(
        story_ids=[
            "US-001",
            "US-003",
        ]
    )

    before = deepcopy(
        (
            backlog,
            graph,
            settings,
            advice,
        )
    )

    first = _plan(
        backlog=backlog,
        graph=graph,
        settings=settings,
        advice=advice,
    )

    second = _plan(
        backlog=backlog,
        graph=graph,
        settings=settings,
        advice=advice,
    )

    assert first == second

    assert (
        backlog,
        graph,
        settings,
        advice,
    ) == before


@runtime_contract
def test_11_plan_removes_temporary_gate_without_absorbing_later_authorities():

    source = _source()

    assert (
        OLD_RUNTIME_GATE
        not in source
    )

    plan = _plan_node()

    attributes = {
        node.attr
        for node in ast.walk(
            plan
        )
        if isinstance(
            node,
            ast.Attribute,
        )
    }

    referenced_names = {
        node.id
        for node in ast.walk(
            plan
        )
        if isinstance(
            node,
            ast.Name,
        )
    }

    for forbidden_attribute in (
        "locked",
        "validation_status",
        "metrics",
        "actual_velocity",
        "projected_velocity",
        "burndown",
    ):
        assert (
            forbidden_attribute
            not in attributes
        )

    for forbidden_name in (
        "AgileMetricsBuilder",
        "ProjectManagementPlanV1",
        "VelocityResultV1",
        "BurndownResultV1",
    ):
        assert (
            forbidden_name
            not in referenced_names
        )
