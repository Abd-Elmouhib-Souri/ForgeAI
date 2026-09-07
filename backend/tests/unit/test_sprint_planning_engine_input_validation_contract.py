from __future__ import annotations

from copy import deepcopy
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
    "sprint_planning_runtime_not_certified"
)


FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "INPUT_BINDING_VALIDATION_NOT_IMPLEMENTED"
)


ALLOWED_PRIORITIES = {
    "Must",
    "Should",
    "Could",
    "Won't",
}

ALLOWED_STORY_POINTS = {
    1,
    2,
    3,
    5,
    8,
    13,
    21,
}


EXPECTED_ERROR_CODES = {
    "canonical_binding_mismatch",
    "invalid_sprint_count",
    "planning_input_not_ready",
    "dependency_graph_mismatch",
    "advice_reference_mismatch",
}


def _source() -> str:
    return TARGET.read_text(
        encoding="utf-8"
    )


def _old_runtime_gate_present() -> bool:
    return (
        OLD_RUNTIME_GATE
        in _source()
    )


RUNTIME_VALIDATION_IMPLEMENTED = (
    not _old_runtime_gate_present()
)


runtime_contract = pytest.mark.skipif(
    not RUNTIME_VALIDATION_IMPLEMENTED,
    reason=(
        "Input binding / validation has not "
        "been implemented yet; the B0 runtime "
        "gate remains the current FWL."
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
        SprintPlanningEngineError,
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
        SprintPlanningEngineError,
    )


def _story(
    story_id: str,
    *,
    priority: str | None = "Must",
    story_points: int | None = 3,
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
        _SprintPlanningEngineError,
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
    stories=None,
    *,
    source_context_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
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
        _SprintPlanningEngineError,
    ) = _symbols()

    if stories is None:
        stories = [
            _story("US-001"),
            _story("US-002"),
        ]

    return CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash=source_context_hash,
        context_hash=context_hash,
        epics=[],
        features=[],
        stories=list(stories),
        warnings=[],
    )


def _graph(
    *,
    source_context_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
    edges=None,
    order=None,
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
        _SprintPlanningEngineError,
    ) = _symbols()

    return DependencyGraphV1(
        source_context_hash=source_context_hash,
        context_hash=context_hash,
        edges=list(
            edges or []
        ),
        hard_topological_order=list(
            order
            if order is not None
            else [
                "US-001",
                "US-002",
            ]
        ),
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
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        _SprintPlanningEngineError,
    ) = _symbols()

    return DependencyEdgeV1(
        story_id=story_id,
        depends_on_story_id=depends_on_story_id,
        dependency_type=dependency_type,
    )


def _settings(
    *,
    sprint_count: int = 4,
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
        _SprintPlanningEngineError,
    ) = _symbols()

    return PlanningSettingsV1(
        sprint_count=sprint_count,
        sprint_duration_days=14,
        planned_velocity=8.0,
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


def _advice(
    *,
    source_context_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
    story_ids=None,
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
        _SprintPlanningEngineError,
    ) = _symbols()

    recommendations = []

    if story_ids is not None:
        recommendations.append(
            ScrumMasterRecommendationV1(
                recommendation_type="risk",
                story_ids=list(
                    story_ids
                ),
                rationale="Planning risk.",
            )
        )

    return ScrumMasterAdviceV1(
        source_context_hash=source_context_hash,
        context_hash=context_hash,
        recommendations=recommendations,
        warnings=[],
    )


def _plan(
    *,
    backlog=None,
    graph=None,
    settings=None,
    advice=None,
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
        _SprintPlanningEngineError,
    ) = _symbols()

    backlog = (
        backlog
        if backlog is not None
        else _backlog()
    )

    graph = (
        graph
        if graph is not None
        else _graph()
    )

    settings = (
        settings
        if settings is not None
        else _settings()
    )

    advice = (
        advice
        if advice is not None
        else _advice()
    )

    return SprintPlanningEngine().plan(
        backlog=backlog,
        dependency_graph=graph,
        planning_settings=settings,
        advice=advice,
    )


def _assert_error(
    expected_code: str,
    *,
    backlog=None,
    graph=None,
    settings=None,
    advice=None,
):

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        SprintPlanningEngineError,
    ) = _symbols()

    with pytest.raises(
        SprintPlanningEngineError
    ) as exc_info:

        _plan(
            backlog=backlog,
            graph=graph,
            settings=settings,
            advice=advice,
        )

    assert (
        exc_info.value.code
        ==
        expected_code
    )

    return exc_info.value


def test_00_real_red_anchor_input_binding_validation_is_missing():

    assert TARGET.exists()

    if _old_runtime_gate_present():

        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


@runtime_contract
def test_01_planner_exposes_typed_validation_error_contract():

    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _PlanningSettingsV1,
        _ScrumMasterAdviceV1,
        _ScrumMasterRecommendationV1,
        _DependencyEdgeV1,
        _DependencyGraphV1,
        _SprintPlanningEngine,
        SprintPlanningEngineError,
    ) = _symbols()

    assert issubclass(
        SprintPlanningEngineError,
        ValueError,
    )

    assert EXPECTED_ERROR_CODES == {
        "canonical_binding_mismatch",
        "invalid_sprint_count",
        "planning_input_not_ready",
        "dependency_graph_mismatch",
        "advice_reference_mismatch",
    }


@runtime_contract
@pytest.mark.parametrize(
    (
        "graph_source",
        "graph_context",
        "advice_source",
        "advice_context",
    ),
    [
        (
            "wrong-source",
            "ctx-hash",
            "src-hash",
            "ctx-hash",
        ),
        (
            "src-hash",
            "wrong-context",
            "src-hash",
            "ctx-hash",
        ),
        (
            "src-hash",
            "ctx-hash",
            "wrong-source",
            "ctx-hash",
        ),
        (
            "src-hash",
            "ctx-hash",
            "src-hash",
            "wrong-context",
        ),
    ],
)
def test_02_all_canonical_hash_surfaces_must_bind(
    graph_source,
    graph_context,
    advice_source,
    advice_context,
):

    error = _assert_error(
        "canonical_binding_mismatch",
        graph=_graph(
            source_context_hash=(
                graph_source
            ),
            context_hash=(
                graph_context
            ),
        ),
        advice=_advice(
            source_context_hash=(
                advice_source
            ),
            context_hash=(
                advice_context
            ),
        ),
    )

    assert getattr(
        error,
        "details",
        None,
    )


@runtime_contract
@pytest.mark.parametrize(
    "sprint_count",
    [
        0,
        -1,
    ],
)
def test_03_sprint_count_must_be_positive_after_settings_resolution(
    sprint_count,
):

    _assert_error(
        "invalid_sprint_count",
        settings=_settings(
            sprint_count=sprint_count
        ),
    )


@runtime_contract
@pytest.mark.parametrize(
    "priority",
    [
        None,
        "",
        "P1",
        "Critical",
    ],
)
def test_04_final_priority_authority_must_be_ready(
    priority,
):

    backlog = _backlog(
        [
            _story(
                "US-001",
                priority=priority,
            ),
            _story(
                "US-002",
            ),
        ]
    )

    _assert_error(
        "planning_input_not_ready",
        backlog=backlog,
    )


@runtime_contract
@pytest.mark.parametrize(
    "story_points",
    [
        None,
        0,
        4,
        34,
    ],
)
def test_05_final_story_point_authority_must_be_ready(
    story_points,
):

    backlog = _backlog(
        [
            _story(
                "US-001",
                story_points=story_points,
            ),
            _story(
                "US-002",
            ),
        ]
    )

    _assert_error(
        "planning_input_not_ready",
        backlog=backlog,
    )


@runtime_contract
def test_06_hard_topological_order_must_cover_story_set_exactly():

    graph = _graph(
        order=[
            "US-001",
        ]
    )

    _assert_error(
        "dependency_graph_mismatch",
        graph=graph,
    )


@runtime_contract
def test_07_hard_topological_order_rejects_duplicate_story_ids():

    graph = _graph(
        order=[
            "US-001",
            "US-001",
        ]
    )

    _assert_error(
        "dependency_graph_mismatch",
        graph=graph,
    )


@runtime_contract
def test_08_dependency_edges_cannot_reference_unknown_stories():

    graph = _graph(
        edges=[
            _edge(
                "US-002",
                "US-999",
            )
        ],
        order=[
            "US-001",
            "US-002",
        ],
    )

    _assert_error(
        "dependency_graph_mismatch",
        graph=graph,
    )


@runtime_contract
def test_09_hard_dependency_precedence_must_match_topological_order():

    graph = _graph(
        edges=[
            _edge(
                "US-002",
                "US-001",
                dependency_type=(
                    "hard_dependency"
                ),
            )
        ],
        order=[
            "US-002",
            "US-001",
        ],
    )

    _assert_error(
        "dependency_graph_mismatch",
        graph=graph,
    )


@runtime_contract
def test_10_soft_dependency_does_not_impose_hard_precedence():

    graph = _graph(
        edges=[
            _edge(
                "US-001",
                "US-002",
                dependency_type=(
                    "soft_dependency"
                ),
            )
        ],
        order=[
            "US-001",
            "US-002",
        ],
    )

    backlog = _backlog()
    settings = _settings()
    advice = _advice()

    before = (
        deepcopy(backlog),
        deepcopy(graph),
        deepcopy(settings),
        deepcopy(advice),
    )

    from app.services.sprint_planning_engine import (
        SprintPlanningEngine,
    )

    result = (
        SprintPlanningEngine()
        ._validate_inputs(
            backlog=backlog,
            dependency_graph=graph,
            planning_settings=settings,
            advice=advice,
        )
    )

    assert result is None

    assert backlog == before[0]
    assert graph == before[1]
    assert settings == before[2]
    assert advice == before[3]


@runtime_contract
def test_11_advice_cannot_reference_unknown_story():

    advice = _advice(
        story_ids=[
            "US-999",
        ]
    )

    _assert_error(
        "advice_reference_mismatch",
        advice=advice,
    )


@runtime_contract
def test_12_validated_inputs_pass_without_mutation():

    backlog = _backlog()

    graph = _graph(
        edges=[
            _edge(
                "US-002",
                "US-001",
            )
        ],
        order=[
            "US-001",
            "US-002",
        ],
    )

    settings = _settings()

    advice = _advice(
        story_ids=[
            "US-001",
            "US-002",
        ]
    )

    before = (
        deepcopy(backlog),
        deepcopy(graph),
        deepcopy(settings),
        deepcopy(advice),
    )

    from app.services.sprint_planning_engine import (
        SprintPlanningEngine,
    )

    result = (
        SprintPlanningEngine()
        ._validate_inputs(
            backlog=backlog,
            dependency_graph=graph,
            planning_settings=settings,
            advice=advice,
        )
    )

    assert result is None

    assert backlog == before[0]
    assert graph == before[1]
    assert settings == before[2]
    assert advice == before[3]
