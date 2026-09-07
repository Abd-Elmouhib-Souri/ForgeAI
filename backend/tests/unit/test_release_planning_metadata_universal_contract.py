from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.project_management import (
    PlanningSettingsV1,
    ProjectManagementMetricsV1,
    ProjectManagementPlanV1,
    ReleasePlanningMetadataV1,
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
) -> PlanningSettingsV1:

    return PlanningSettingsV1(
        sprint_count_mode=count_mode,
        sprint_count=count,
        sprint_duration_mode=duration_mode,
        sprint_duration_days=duration,
        planned_velocity=20,
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
    assigned: int = 0,
) -> ProjectManagementMetricsV1:

    return ProjectManagementMetricsV1(
        planned_velocity=20,
        projected_velocity=0,
        total_story_points=assigned,
        assigned_story_points=assigned,
        overflow_story_points=0,
        sprint_metrics=[],
        ideal_burndown=[],
        planned_burndown=[],
    )


def test_legacy_plan_field_is_optional_and_defaults_to_none() -> None:

    field = (
        ProjectManagementPlanV1
        .model_fields[
            "release_planning"
        ]
    )

    assert (
        field.is_required()
        is False
    )

    assert field.default is None


def test_auto_authorities_are_projected_with_their_original_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    monkeypatch.setattr(
        service._planner,
        "_effective_sprint_capacity",
        lambda settings: 18.0,
    )

    sizing = ReleaseSizingResultV1(
        recommended_sprint_count=5,
        evaluated_sprint_counts=[
            1,
            2,
            3,
            4,
            5,
        ],
        reason="minimum_zero_overflow",
    )

    cadence = (
        SprintCadenceRecommendationV1(
            recommended_sprint_duration_days=14,
            cadence_band="standard",
            confidence="high",
            reason_codes=[
                "standard_release_feedback_cycle",
            ],
            evaluated_story_count=12,
        )
    )

    metadata = (
        service
        ._build_release_planning_metadata(
            settings=_settings(
                count=5,
                duration=14,
            ),
            sizing=sizing,
            cadence=cadence,
        )
    )

    assert metadata.sprint_count_mode == "auto"
    assert metadata.effective_sprint_count == 5
    assert metadata.recommended_sprint_count == 5

    assert (
        metadata.evaluated_sprint_counts
        ==
        [
            1,
            2,
            3,
            4,
            5,
        ]
    )

    assert (
        metadata.sprint_count_reason
        ==
        "minimum_zero_overflow"
    )

    assert (
        metadata.sprint_duration_mode
        ==
        "auto"
    )

    assert (
        metadata.effective_sprint_duration_days
        ==
        14
    )

    assert (
        metadata.recommended_sprint_duration_days
        ==
        14
    )

    assert metadata.cadence_band == "standard"
    assert metadata.cadence_confidence == "high"

    assert (
        metadata.cadence_reason_codes
        ==
        [
            "standard_release_feedback_cycle",
        ]
    )

    assert (
        metadata.cadence_evaluated_story_count
        ==
        12
    )

    assert (
        metadata.effective_sprint_capacity_story_points
        ==
        18.0
    )

    assert (
        metadata.release_capacity_story_points
        ==
        90.0
    )

    assert (
        metadata.release_duration_days
        ==
        70
    )


def test_manual_modes_never_fake_auto_recommendation_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    monkeypatch.setattr(
        service._planner,
        "_effective_sprint_capacity",
        lambda settings: 20.0,
    )

    sizing = ReleaseSizingResultV1(
        recommended_sprint_count=2,
        evaluated_sprint_counts=[
            1,
            2,
        ],
    )

    cadence = (
        SprintCadenceRecommendationV1(
            recommended_sprint_duration_days=7,
            cadence_band="short",
            confidence="high",
            reason_codes=[
                "short_feedback_learning_cycle",
            ],
            evaluated_story_count=4,
        )
    )

    metadata = (
        service
        ._build_release_planning_metadata(
            settings=_settings(
                count_mode="manual",
                count=6,
                duration_mode="manual",
                duration=21,
            ),
            sizing=sizing,
            cadence=cadence,
        )
    )

    assert metadata.effective_sprint_count == 6
    assert metadata.recommended_sprint_count is None
    assert metadata.evaluated_sprint_counts == []
    assert metadata.sprint_count_reason is None

    assert (
        metadata.effective_sprint_duration_days
        ==
        21
    )

    assert (
        metadata.recommended_sprint_duration_days
        is None
    )

    assert metadata.cadence_band is None
    assert metadata.cadence_confidence is None
    assert metadata.cadence_reason_codes == []


def test_release_capacity_reuses_certified_planner_capacity_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    calls = []


    def capacity_authority(
        settings,
    ):

        calls.append(
            settings
        )

        return 13.5


    monkeypatch.setattr(
        service._planner,
        "_effective_sprint_capacity",
        capacity_authority,
    )

    settings = _settings(
        count=4,
    )

    metadata = (
        service
        ._build_release_planning_metadata(
            settings=settings,
        )
    )

    assert calls == [
        settings
    ]

    assert (
        metadata.effective_sprint_capacity_story_points
        ==
        13.5
    )

    assert (
        metadata.release_capacity_story_points
        ==
        54.0
    )


def test_release_duration_is_count_times_the_single_release_cadence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    monkeypatch.setattr(
        service._planner,
        "_effective_sprint_capacity",
        lambda settings: 20.0,
    )

    metadata = (
        service
        ._build_release_planning_metadata(
            settings=_settings(
                count=4,
                duration=21,
            ),
        )
    )

    assert (
        metadata.release_duration_days
        ==
        84
    )


def test_assemble_uses_existing_metrics_authority_for_capacity_utilization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    metadata = ReleasePlanningMetadataV1(
        sprint_count_mode="auto",
        effective_sprint_count=4,
        recommended_sprint_count=4,
        sprint_count_reason="minimum_zero_overflow",
        evaluated_sprint_counts=[
            1,
            2,
            3,
            4,
        ],
        sprint_duration_mode="auto",
        effective_sprint_duration_days=14,
        recommended_sprint_duration_days=14,
        cadence_band="standard",
        cadence_confidence="high",
        cadence_reason_codes=[
            "standard_release_feedback_cycle",
        ],
        cadence_evaluated_story_count=3,
        effective_sprint_capacity_story_points=10,
        release_capacity_story_points=40,
        capacity_utilization_ratio=0,
        release_duration_days=56,
    )

    metrics = _metrics(
        assigned=30,
    )

    monkeypatch.setattr(
        service,
        "_build_metrics",
        lambda **kwargs: metrics,
    )

    monkeypatch.setattr(
        service,
        "_sprints",
        lambda backlog, planning: [],
    )

    backlog = SimpleNamespace(
        context_hash="ctx",
        source_context_hash="src",
        epics=[],
        features=[],
        stories=[],
        warnings=[],
    )

    graph = SimpleNamespace(
        edges=[],
        warnings=[],
    )

    advice = SimpleNamespace(
        recommendations=[],
        warnings=[],
    )

    planning = SimpleNamespace(
        assignments=[],
        overflow_story_ids=[],
        warnings=[],
    )

    context = SimpleNamespace(
        assumptions=[],
        warnings=[],
    )

    plan = service._assemble_plan(
        context=context,
        backlog=backlog,
        graph=graph,
        advice=advice,
        planning=planning,
        settings=_settings(),
        revision=1,
        release_planning=metadata,
    )

    assert plan.release_planning is not None

    assert (
        plan.release_planning
        .capacity_utilization_ratio
        ==
        pytest.approx(
            0.75
        )
    )

    assert plan.metrics is metrics


def test_previous_provenance_is_preserved_only_when_explicitly_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    monkeypatch.setattr(
        service._planner,
        "_effective_sprint_capacity",
        lambda settings: 20.0,
    )

    previous = ReleasePlanningMetadataV1(
        sprint_count_mode="auto",
        effective_sprint_count=5,
        recommended_sprint_count=5,
        sprint_count_reason="minimum_zero_overflow",
        evaluated_sprint_counts=[
            1,
            2,
            3,
            4,
            5,
        ],
        sprint_duration_mode="auto",
        effective_sprint_duration_days=14,
        recommended_sprint_duration_days=14,
        cadence_band="standard",
        cadence_confidence="high",
        cadence_reason_codes=[
            "standard_release_feedback_cycle",
        ],
        cadence_evaluated_story_count=10,
        effective_sprint_capacity_story_points=20,
        release_capacity_story_points=100,
        capacity_utilization_ratio=0.8,
        release_duration_days=70,
    )

    refreshed = (
        service
        ._build_release_planning_metadata(
            settings=_settings(
                count=5,
            ),
            previous=previous,
        )
    )

    assert (
        refreshed.recommended_sprint_count
        ==
        5
    )

    assert (
        refreshed.recommended_sprint_duration_days
        ==
        14
    )

    assert (
        refreshed.cadence_band
        ==
        "standard"
    )


def test_auto_mode_without_current_or_preserved_authority_does_not_invent_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    monkeypatch.setattr(
        service._planner,
        "_effective_sprint_capacity",
        lambda settings: 20.0,
    )

    metadata = (
        service
        ._build_release_planning_metadata(
            settings=_settings(),
        )
    )

    assert metadata.sprint_count_mode == "auto"

    assert (
        metadata.recommended_sprint_count
        is None
    )

    assert (
        metadata.sprint_duration_mode
        ==
        "auto"
    )

    assert (
        metadata.recommended_sprint_duration_days
        is None
    )


def test_story_point_accounting_is_not_duplicated_at_plan_root() -> None:

    fields = set(
        ProjectManagementPlanV1
        .model_fields
    )

    assert (
        "total_story_points"
        not in fields
    )

    assert (
        "assigned_story_points"
        not in fields
    )

    assert (
        "overflow_story_points"
        not in fields
    )

    assert "metrics" in fields
    assert "release_planning" in fields
