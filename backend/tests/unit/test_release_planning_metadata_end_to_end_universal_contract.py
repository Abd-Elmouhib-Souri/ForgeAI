from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import app.services.project_management_plan_service as plan_service_module

from app.agents.product_owner_agent import (
    ProductOwnerAgent,
)

from app.agents.scrum_master_agent import (
    AIScrumMasterAgent,
)

from app.schemas.project_management import (
    PlanningSettingsV1,
    ProjectManagementMetricsV1,
    ProjectManagementPlanV1,
    ScrumMasterAdviceV1,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)

from app.services.release_sizing_engine import (
    ReleaseSizingResultV1,
)

from app.services.sprint_cadence_advisor import (
    SprintCadenceRecommendationV1,
)


def _settings(
    *,
    count_mode: str = "auto",
    count: int = 4,
    duration_mode: str = "auto",
    duration: int = 14,
    velocity: float = 20,
) -> PlanningSettingsV1:

    return PlanningSettingsV1(
        sprint_count_mode=count_mode,
        sprint_count=count,
        sprint_duration_mode=duration_mode,
        sprint_duration_days=duration,
        planned_velocity=velocity,
        team_size=3,
        capacity_adjustment=1.0,
        start_date="2026-09-07",
        working_days=[
            0,
            1,
            2,
            3,
            4,
        ],
    )


def _metrics(
    *,
    total: int = 30,
    assigned: int = 30,
) -> ProjectManagementMetricsV1:

    return ProjectManagementMetricsV1(
        planned_velocity=20,
        projected_velocity=10,
        total_story_points=total,
        assigned_story_points=assigned,
        overflow_story_points=(
            total
            -
            assigned
        ),
        sprint_metrics=[],
        ideal_burndown=[],
        planned_burndown=[],
    )


def _wire_generate(
    monkeypatch: pytest.MonkeyPatch,
    service: ProjectManagementPlanService,
    *,
    cadence_days: int = 21,
    sized_count: int = 3,
    metrics: ProjectManagementMetricsV1 | None = None,
):
    """
    Keep orchestration real while replacing only expensive/upstream
    authorities with deterministic fixtures.

    _build_release_planning_metadata and _assemble_plan remain REAL.
    """

    context = SimpleNamespace(
        project_id="b3-b2",
        language="fr",
        assumptions=[],
        warnings=[],
        regulatory_flags=[],
        human_oversight=[],
        unknowns=[],
    )

    candidate = object()
    canonical = object()
    prioritized = object()

    estimated = SimpleNamespace(
        source_context_hash="src-b3-b2",
        context_hash="ctx-b3-b2",
        epics=[],
        features=[],
        stories=[],
        warnings=[],
    )

    graph = SimpleNamespace(
        source_context_hash="src-b3-b2",
        context_hash="ctx-b3-b2",
        edges=[],
        warnings=[],
        hard_topological_order=[],
    )

    observed = {
        "cadence_calls": 0,
        "sizing_calls": 0,
        "planner_settings": None,
    }


    monkeypatch.setattr(
        service,
        "_build_context",
        lambda **kwargs: context,
    )


    async def fake_candidate(
        self,
        supplied_context,
    ):

        assert supplied_context is context
        return candidate


    monkeypatch.setattr(
        ProductOwnerAgent,
        "generate_candidate_backlog",
        fake_candidate,
    )


    def fake_canonicalize(
        supplied_context,
        supplied_candidate,
    ):

        assert supplied_context is context
        assert supplied_candidate is candidate

        return canonical


    monkeypatch.setattr(
        plan_service_module.backlog_policy_engine,
        "canonicalize",
        fake_canonicalize,
    )


    def fake_priority(
        supplied_context,
        supplied_backlog,
    ):

        assert supplied_context is context
        assert supplied_backlog is canonical

        return SimpleNamespace(
            backlog=prioritized,
            warnings=[],
        )


    monkeypatch.setattr(
        service._priority_policy,
        "apply",
        fake_priority,
    )


    def fake_points(
        supplied_context,
        supplied_backlog,
    ):

        assert supplied_context is context
        assert supplied_backlog is prioritized

        return SimpleNamespace(
            backlog=estimated,
        )


    monkeypatch.setattr(
        service._story_point_policy,
        "apply",
        fake_points,
    )


    def fake_graph(
        supplied_backlog,
    ):

        assert supplied_backlog is estimated

        return SimpleNamespace(
            graph=graph
        )


    monkeypatch.setattr(
        service._dependency_builder,
        "build",
        fake_graph,
    )


    def fake_cadence(
        *,
        context,
        backlog,
    ):

        observed[
            "cadence_calls"
        ] += 1

        assert backlog is estimated

        return SprintCadenceRecommendationV1(
            recommended_sprint_duration_days=(
                cadence_days
            ),
            cadence_band=(
                "short"
                if cadence_days <= 7
                else (
                    "standard"
                    if cadence_days <= 14
                    else (
                        "extended"
                        if cadence_days <= 21
                        else "long"
                    )
                )
            ),
            confidence="high",
            reason_codes=[
                "b3_b2_e2e"
            ],
            evaluated_story_count=0,
        )


    monkeypatch.setattr(
        service._cadence_advisor,
        "recommend",
        fake_cadence,
    )


    def fake_size(
        **kwargs,
    ):

        observed[
            "sizing_calls"
        ] += 1

        assert (
            kwargs[
                "backlog"
            ]
            is estimated
        )

        return ReleaseSizingResultV1(
            recommended_sprint_count=(
                sized_count
            ),
            evaluated_sprint_counts=list(
                range(
                    1,
                    sized_count + 1,
                )
            ),
            reason="minimum_zero_overflow",
        )


    monkeypatch.setattr(
        service._release_sizing,
        "size",
        fake_size,
    )


    async def fake_scrum(
        self,
        backlog,
        dependency_graph,
        planning_settings,
    ):

        assert backlog is estimated
        assert dependency_graph is graph

        return ScrumMasterAdviceV1(
            source_context_hash=(
                estimated
                .source_context_hash
            ),
            context_hash=(
                estimated
                .context_hash
            ),
            recommendations=[],
            warnings=[],
        )


    monkeypatch.setattr(
        AIScrumMasterAgent,
        "generate_advice",
        fake_scrum,
    )


    def fake_plan(
        backlog,
        dependency_graph,
        planning_settings,
        advice,
    ):

        assert backlog is estimated
        assert dependency_graph is graph

        observed[
            "planner_settings"
        ] = planning_settings

        return SimpleNamespace(
            sprint_count=(
                planning_settings
                .sprint_count
            ),
            assignments=[],
            overflow_story_ids=[],
            warnings=[],
        )


    monkeypatch.setattr(
        service._planner,
        "plan",
        fake_plan,
    )


    monkeypatch.setattr(
        service,
        "_build_metrics",
        lambda **kwargs: (
            metrics
            or _metrics()
        ),
    )


    monkeypatch.setattr(
        service,
        "_sprints",
        lambda backlog, planning: [],
    )


    return (
        estimated,
        graph,
        observed,
    )


@pytest.mark.asyncio
async def test_auto_generate_projects_authority_provenance_into_final_durable_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    _, _, observed = _wire_generate(
        monkeypatch,
        service,
        cadence_days=21,
        sized_count=3,
        metrics=_metrics(
            total=30,
            assigned=30,
        ),
    )


    plan = await service.generate(
        project_id=800,
        analysis_data={},
        settings=None,
        revision=7,
    )


    assert isinstance(
        plan,
        ProjectManagementPlanV1,
    )

    assert plan.revision == 7

    assert (
        observed[
            "cadence_calls"
        ]
        ==
        1
    )

    assert (
        observed[
            "sizing_calls"
        ]
        ==
        1
    )


    assert (
        plan.settings
        .sprint_count_mode
        ==
        "auto"
    )

    assert (
        plan.settings
        .sprint_count
        ==
        3
    )

    assert (
        plan.settings
        .sprint_duration_mode
        ==
        "auto"
    )

    assert (
        plan.settings
        .sprint_duration_days
        ==
        21
    )


    metadata = (
        plan.release_planning
    )

    assert metadata is not None

    assert (
        metadata
        .effective_sprint_count
        ==
        3
    )

    assert (
        metadata
        .recommended_sprint_count
        ==
        3
    )

    assert (
        metadata
        .evaluated_sprint_counts
        ==
        [
            1,
            2,
            3,
        ]
    )

    assert (
        metadata
        .sprint_count_reason
        ==
        "minimum_zero_overflow"
    )

    assert (
        metadata
        .effective_sprint_duration_days
        ==
        21
    )

    assert (
        metadata
        .recommended_sprint_duration_days
        ==
        21
    )

    assert (
        metadata
        .cadence_band
        ==
        "extended"
    )

    assert (
        metadata
        .cadence_confidence
        ==
        "high"
    )

    assert (
        metadata
        .cadence_reason_codes
        ==
        [
            "b3_b2_e2e"
        ]
    )


    # Certified capacity authority:
    # planned_velocity 20 * adjustment 1.0 = 20 SP / Sprint.
    assert (
        metadata
        .effective_sprint_capacity_story_points
        ==
        pytest.approx(
            20.0
        )
    )

    assert (
        metadata
        .release_capacity_story_points
        ==
        pytest.approx(
            60.0
        )
    )

    assert (
        metadata
        .capacity_utilization_ratio
        ==
        pytest.approx(
            0.5
        )
    )

    assert (
        metadata
        .release_duration_days
        ==
        63
    )


    # Durable JSON-compatible round-trip.
    payload = plan.model_dump(
        mode="json"
    )

    restored = (
        ProjectManagementPlanV1
        .model_validate(
            payload
        )
    )

    assert (
        restored.release_planning
        ==
        plan.release_planning
    )

    assert (
        restored.settings
        ==
        plan.settings
    )

    assert (
        restored.metrics
        ==
        plan.metrics
    )


@pytest.mark.asyncio
async def test_manual_generate_keeps_effective_values_without_fake_auto_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    _, _, observed = _wire_generate(
        monkeypatch,
        service,
        cadence_days=7,
        sized_count=2,
        metrics=_metrics(
            total=42,
            assigned=42,
        ),
    )


    settings = _settings(
        count_mode="manual",
        count=6,
        duration_mode="manual",
        duration=21,
    )


    plan = await service.generate(
        project_id=801,
        analysis_data={},
        settings=settings,
    )


    assert (
        observed[
            "cadence_calls"
        ]
        ==
        0
    )

    assert (
        observed[
            "sizing_calls"
        ]
        ==
        0
    )


    metadata = (
        plan.release_planning
    )

    assert metadata is not None

    assert (
        metadata.sprint_count_mode
        ==
        "manual"
    )

    assert (
        metadata.effective_sprint_count
        ==
        6
    )

    assert (
        metadata.recommended_sprint_count
        is None
    )

    assert (
        metadata.evaluated_sprint_counts
        ==
        []
    )

    assert (
        metadata.sprint_count_reason
        is None
    )


    assert (
        metadata.sprint_duration_mode
        ==
        "manual"
    )

    assert (
        metadata
        .effective_sprint_duration_days
        ==
        21
    )

    assert (
        metadata
        .recommended_sprint_duration_days
        is None
    )

    assert metadata.cadence_band is None
    assert metadata.cadence_confidence is None

    assert (
        metadata.cadence_reason_codes
        ==
        []
    )


    assert (
        metadata
        .release_capacity_story_points
        ==
        pytest.approx(
            120.0
        )
    )

    assert (
        metadata
        .capacity_utilization_ratio
        ==
        pytest.approx(
            42.0
            /
            120.0
        )
    )

    assert (
        metadata.release_duration_days
        ==
        126
    )


@pytest.mark.asyncio
async def test_replan_preserves_provenance_only_for_unchanged_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    _, _, _ = _wire_generate(
        monkeypatch,
        service,
        cadence_days=14,
        sized_count=4,
        metrics=_metrics(
            total=40,
            assigned=40,
        ),
    )


    original = await service.generate(
        project_id=802,
        analysis_data={},
    )

    original_metadata = (
        original.release_planning
    )

    assert original_metadata is not None

    assert (
        original_metadata
        .recommended_sprint_count
        ==
        4
    )

    assert (
        original_metadata
        .recommended_sprint_duration_days
        ==
        14
    )


    # Replan uses reconstructed deterministic backlog/graph.
    graph = SimpleNamespace(
        source_context_hash=(
            original
            .source_context_hash
        ),
        context_hash=(
            original
            .context_hash
        ),
        edges=[],
        warnings=[],
        hard_topological_order=[],
    )


    monkeypatch.setattr(
        service._dependency_builder,
        "build",
        lambda backlog: SimpleNamespace(
            graph=graph
        ),
    )


    def fake_replan_planner(
        backlog,
        dependency_graph,
        planning_settings,
        advice,
    ):

        return SimpleNamespace(
            sprint_count=(
                planning_settings
                .sprint_count
            ),
            assignments=[],
            overflow_story_ids=[],
            warnings=[],
        )


    monkeypatch.setattr(
        service._planner,
        "plan",
        fake_replan_planner,
    )


    monkeypatch.setattr(
        service,
        "_assert_locks_preserved",
        lambda *args, **kwargs: None,
    )


    monkeypatch.setattr(
        service,
        "_build_metrics",
        lambda **kwargs: _metrics(
            total=40,
            assigned=40,
        ),
    )


    monkeypatch.setattr(
        service,
        "_sprints",
        lambda backlog, planning: [],
    )


    same = service.replan(
        stored_plan=original,
    )


    assert same.revision == (
        original.revision
        +
        1
    )

    assert same.release_planning is not None

    assert (
        same.release_planning
        .recommended_sprint_count
        ==
        original_metadata
        .recommended_sprint_count
    )

    assert (
        same.release_planning
        .recommended_sprint_duration_days
        ==
        original_metadata
        .recommended_sprint_duration_days
    )

    assert (
        same.release_planning
        .cadence_reason_codes
        ==
        original_metadata
        .cadence_reason_codes
    )


    # A settings change invalidates old recommendation provenance.
    changed_settings = (
        original.settings.model_copy(
            update={
                "planned_velocity":
                    10.0,
            },
            deep=True,
        )
    )


    changed = service.replan(
        stored_plan=original,
        settings=changed_settings,
    )


    assert changed.release_planning is not None

    assert (
        changed.release_planning
        .recommended_sprint_count
        is None
    )

    assert (
        changed.release_planning
        .evaluated_sprint_counts
        ==
        []
    )

    assert (
        changed.release_planning
        .sprint_count_reason
        is None
    )

    assert (
        changed.release_planning
        .recommended_sprint_duration_days
        is None
    )

    assert (
        changed.release_planning
        .cadence_band
        is None
    )

    assert (
        changed.release_planning
        .cadence_confidence
        is None
    )

    assert (
        changed.release_planning
        .cadence_reason_codes
        ==
        []
    )


    # Effective deterministic projections still reflect current settings.
    assert (
        changed.release_planning
        .effective_sprint_count
        ==
        changed_settings
        .sprint_count
    )

    assert (
        changed.release_planning
        .effective_sprint_duration_days
        ==
        changed_settings
        .sprint_duration_days
    )

    assert (
        changed.release_planning
        .effective_sprint_capacity_story_points
        ==
        pytest.approx(
            10.0
        )
    )


@pytest.mark.asyncio
async def test_legacy_plan_without_release_metadata_remains_readable_and_replan_does_not_invent_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    _, _, _ = _wire_generate(
        monkeypatch,
        service,
        cadence_days=14,
        sized_count=3,
    )


    current = await service.generate(
        project_id=803,
        analysis_data={},
    )


    payload = current.model_dump(
        mode="json"
    )

    payload.pop(
        "release_planning",
        None,
    )


    legacy = (
        ProjectManagementPlanV1
        .model_validate(
            payload
        )
    )


    assert legacy.release_planning is None


    graph = SimpleNamespace(
        source_context_hash=(
            legacy
            .source_context_hash
        ),
        context_hash=(
            legacy
            .context_hash
        ),
        edges=[],
        warnings=[],
        hard_topological_order=[],
    )


    monkeypatch.setattr(
        service._dependency_builder,
        "build",
        lambda backlog: SimpleNamespace(
            graph=graph
        ),
    )


    monkeypatch.setattr(
        service._planner,
        "plan",
        lambda backlog, dependency_graph, planning_settings, advice:
            SimpleNamespace(
                sprint_count=(
                    planning_settings
                    .sprint_count
                ),
                assignments=[],
                overflow_story_ids=[],
                warnings=[],
            ),
    )


    monkeypatch.setattr(
        service,
        "_assert_locks_preserved",
        lambda *args, **kwargs: None,
    )


    monkeypatch.setattr(
        service,
        "_build_metrics",
        lambda **kwargs: _metrics(
            total=0,
            assigned=0,
        ),
    )


    monkeypatch.setattr(
        service,
        "_sprints",
        lambda backlog, planning: [],
    )


    replanned = service.replan(
        stored_plan=legacy,
    )


    assert (
        replanned.release_planning
        is None
    )

    assert (
        replanned.revision
        ==
        legacy.revision + 1
    )
