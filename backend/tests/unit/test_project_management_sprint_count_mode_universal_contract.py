from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.services.project_management_plan_service as plan_service_module

from app.agents.product_owner_agent import (
    ProductOwnerAgent,
)

from app.agents.scrum_master_agent import (
    AIScrumMasterAgent,
)

from app.schemas.project_management import (
    PlanningSettingsUpdateV1,
    PlanningSettingsV1,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)


class _StopAfterResolvedSettings(
    RuntimeError
):
    pass


def _settings(
    *,
    sprint_count: int = 4,
    mode: str = "auto",
) -> PlanningSettingsV1:

    return PlanningSettingsV1(
        sprint_count_mode=mode,
        sprint_count=sprint_count,
        sprint_duration_days=14,
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


async def _exercise_generation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    settings,
    recommended_count: int,
    expected_scrum_count: int,
    expect_sizing: bool,
) -> None:

    service = (
        ProjectManagementPlanService()
    )

    context = object()
    candidate = object()
    canonical = object()
    prioritized = object()

    estimated = SimpleNamespace(
        source_context_hash="src-mode",
        context_hash="ctx-mode",
        stories=[
            SimpleNamespace(
                story_id="US-001",
                story_points=5,
            ),
        ],
    )

    graph = object()

    monkeypatch.setattr(
        service,
        "_build_context",
        lambda **kwargs: context,
    )


    async def candidate_backlog(
        self,
        supplied_context,
    ):

        assert supplied_context is context

        return candidate


    monkeypatch.setattr(
        ProductOwnerAgent,
        "generate_candidate_backlog",
        candidate_backlog,
    )


    monkeypatch.setattr(
        plan_service_module.backlog_policy_engine,
        "canonicalize",
        lambda supplied_context, supplied_candidate: canonical,
    )


    monkeypatch.setattr(
        service._priority_policy,
        "apply",
        lambda supplied_context, supplied_backlog: (
            SimpleNamespace(
                backlog=prioritized,
                warnings=[],
            )
        ),
    )


    monkeypatch.setattr(
        service._story_point_policy,
        "apply",
        lambda supplied_context, supplied_backlog: (
            SimpleNamespace(
                backlog=estimated,
            )
        ),
    )


    monkeypatch.setattr(
        service._dependency_builder,
        "build",
        lambda supplied_backlog: (
            SimpleNamespace(
                graph=graph,
            )
        ),
    )


    sizing_calls = []


    def fake_size(
        **kwargs,
    ):

        sizing_calls.append(
            kwargs
        )

        assert (
            kwargs["backlog"]
            is estimated
        )

        assert (
            kwargs["dependency_graph"]
            is graph
        )

        return SimpleNamespace(
            recommended_sprint_count=(
                recommended_count
            ),
        )


    monkeypatch.setattr(
        service._release_sizing,
        "size",
        fake_size,
    )


    async def stop_at_scrum(
        self,
        backlog,
        dependency_graph,
        planning_settings,
    ):

        assert backlog is estimated
        assert dependency_graph is graph

        assert (
            planning_settings.sprint_count
            ==
            expected_scrum_count
        )

        raise _StopAfterResolvedSettings()


    monkeypatch.setattr(
        AIScrumMasterAgent,
        "generate_advice",
        stop_at_scrum,
    )


    with pytest.raises(
        _StopAfterResolvedSettings
    ):

        await service.generate(
            project_id=700,
            analysis_data={},
            settings=settings,
        )


    assert (
        bool(sizing_calls)
        is expect_sizing
    )


def test_schema_default_is_auto_not_implicit_manual() -> None:

    settings = PlanningSettingsV1(
        sprint_count=4,
        sprint_duration_days=14,
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

    assert (
        settings.sprint_count_mode
        ==
        "auto"
    )


def test_legacy_payload_without_mode_migrates_deterministically_to_auto() -> None:

    payload = {
        "sprint_count": 4,
        "sprint_duration_days": 14,
        "planned_velocity": 20,
        "team_size": 3,
        "capacity_adjustment": 1.0,
        "start_date": "2026-09-07",
        "working_days": [
            0,
            1,
            2,
            3,
            4,
        ],
    }

    settings = (
        PlanningSettingsV1
        .model_validate(
            payload
        )
    )

    assert (
        settings.sprint_count_mode
        ==
        "auto"
    )


def test_service_default_settings_are_auto() -> None:

    settings = (
        ProjectManagementPlanService
        .default_settings()
    )

    assert (
        settings.sprint_count_mode
        ==
        "auto"
    )


def test_user_sprint_count_update_implicitly_switches_to_manual() -> None:

    service = (
        ProjectManagementPlanService()
    )

    current = (
        service.default_settings()
    )

    updated = (
        service.settings_from_update(
            current,
            PlanningSettingsUpdateV1(
                sprint_count=6,
            ),
        )
    )

    assert (
        updated.sprint_count
        ==
        6
    )

    assert (
        updated.sprint_count_mode
        ==
        "manual"
    )


def test_explicit_auto_mode_wins_when_user_switches_back_to_auto() -> None:

    service = (
        ProjectManagementPlanService()
    )

    current = _settings(
        sprint_count=7,
        mode="manual",
    )

    updated = (
        service.settings_from_update(
            current,
            PlanningSettingsUpdateV1(
                sprint_count_mode="auto",
            ),
        )
    )

    assert (
        updated.sprint_count_mode
        ==
        "auto"
    )

    # Existing count remains only a stored prior value.
    # Auto generation must recalculate it before final planning.
    assert (
        updated.sprint_count
        ==
        7
    )


@pytest.mark.asyncio
async def test_first_generation_without_settings_uses_auto_sizing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    await _exercise_generation(
        monkeypatch,
        settings=None,
        recommended_count=3,
        expected_scrum_count=3,
        expect_sizing=True,
    )


@pytest.mark.asyncio
async def test_regeneration_with_previous_auto_settings_recalculates_sprint_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    previous_settings = _settings(
        sprint_count=9,
        mode="auto",
    )

    await _exercise_generation(
        monkeypatch,
        settings=previous_settings,
        recommended_count=3,
        expected_scrum_count=3,
        expect_sizing=True,
    )


@pytest.mark.asyncio
async def test_manual_mode_preserves_explicit_user_sprint_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    manual_settings = _settings(
        sprint_count=6,
        mode="manual",
    )

    await _exercise_generation(
        monkeypatch,
        settings=manual_settings,
        recommended_count=2,
        expected_scrum_count=6,
        expect_sizing=False,
    )
