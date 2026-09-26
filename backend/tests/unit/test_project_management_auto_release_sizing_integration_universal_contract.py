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
    ScrumMasterAdviceV1,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)


def _settings(
    *,
    sprint_count: int,
    mode: str,
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


async def _run_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    incoming_settings: PlanningSettingsV1 | None,
    recommended_count: int,
    expected_final_count: int,
    expect_release_sizing: bool,
) -> tuple[
    Any,
    dict[str, Any],
]:

    service = (
        ProjectManagementPlanService()
    )

    context = SimpleNamespace(
        project_id="700",
        language="fr",
    )

    candidate = object()
    canonical = object()
    prioritized = object()

    estimated = SimpleNamespace(
        source_context_hash="src-b1-6",
        context_hash="ctx-b1-6",
        stories=[
            SimpleNamespace(
                story_id="US-001",
                story_points=8,
            ),
            SimpleNamespace(
                story_id="US-002",
                story_points=5,
            ),
            SimpleNamespace(
                story_id="US-003",
                story_points=3,
            ),
        ],
    )

    graph = SimpleNamespace(
        source_context_hash="src-b1-6",
        context_hash="ctx-b1-6",
        edges=[],
    )

    priority_result = (
        SimpleNamespace(
            backlog=prioritized,
            warnings=[],
        )
    )

    estimation_result = (
        SimpleNamespace(
            backlog=estimated,
        )
    )

    observed: dict[
        str,
        Any,
    ] = {
        "sizing_calls": 0,
        "scrum_count": None,
        "planner_count": None,
        "assembly_count": None,
        "assembly_mode": None,
        "revision": None,
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

        return priority_result


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

        return estimation_result


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


    def fake_size(
        **kwargs,
    ):

        observed[
            "sizing_calls"
        ] += 1

        assert (
            kwargs["backlog"]
            is estimated
        )

        assert (
            kwargs[
                "dependency_graph"
            ]
            is graph
        )

        base_settings = (
            kwargs[
                "base_settings"
            ]
        )

        assert (
            base_settings
            .sprint_count_mode
            ==
            "auto"
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


    async def fake_scrum(
        self,
        backlog,
        dependency_graph,
        planning_settings,
    ):

        assert backlog is estimated
        assert dependency_graph is graph

        observed[
            "scrum_count"
        ] = (
            planning_settings
            .sprint_count
        )

        assert (
            planning_settings
            .sprint_count
            ==
            expected_final_count
        )

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

        assert isinstance(
            advice,
            ScrumMasterAdviceV1,
        )

        observed[
            "planner_count"
        ] = (
            planning_settings
            .sprint_count
        )

        assert (
            planning_settings
            .sprint_count
            ==
            expected_final_count
        )

        return SimpleNamespace(
            sprint_count=(
                expected_final_count
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


    sentinel_plan = (
        SimpleNamespace(
            marker="assembled-plan",
            settings=None,
        )
    )


    def fake_assemble(
        *,
        context,
        backlog,
        graph,
        advice,
        planning,
        settings,
        revision,
        release_planning,
        extra_warnings,
    ):

        assert backlog is estimated

        observed[
            "assembly_count"
        ] = (
            settings.sprint_count
        )

        observed[
            "assembly_mode"
        ] = (
            settings.sprint_count_mode
        )

        observed[
            "revision"
        ] = revision

        assert (
            settings.sprint_count
            ==
            expected_final_count
        )

        sentinel_plan.settings = (
            settings
        )

        return sentinel_plan


    monkeypatch.setattr(
        service,
        "_assemble_plan",
        fake_assemble,
    )


    result = await service.generate(
        project_id=700,
        analysis_data={},
        settings=incoming_settings,
        revision=4,
    )


    assert result is sentinel_plan

    assert (
        observed["scrum_count"]
        ==
        expected_final_count
    )

    assert (
        observed["planner_count"]
        ==
        expected_final_count
    )

    assert (
        observed["assembly_count"]
        ==
        expected_final_count
    )

    assert (
        observed["revision"]
        ==
        4
    )

    assert (
        bool(
            observed[
                "sizing_calls"
            ]
        )
        is expect_release_sizing
    )


    return (
        result,
        observed,
    )


@pytest.mark.asyncio
async def test_first_generation_auto_count_reaches_scrum_planner_and_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=None,
            recommended_count=3,
            expected_final_count=3,
            expect_release_sizing=True,
        )
    )

    assert (
        result.settings
        .sprint_count_mode
        ==
        "auto"
    )

    assert (
        result.settings
        .sprint_count
        ==
        3
    )

    assert (
        observed[
            "sizing_calls"
        ]
        ==
        1
    )


@pytest.mark.asyncio
async def test_regeneration_auto_recalculates_and_does_not_mutate_previous_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    previous = _settings(
        sprint_count=9,
        mode="auto",
    )

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=previous,
            recommended_count=3,
            expected_final_count=3,
            expect_release_sizing=True,
        )
    )

    # Previous persisted settings remain historical truth.
    # The newly generated revision owns the new recommendation.
    assert (
        previous.sprint_count
        ==
        9
    )

    assert (
        previous.sprint_count_mode
        ==
        "auto"
    )

    assert (
        result.settings
        .sprint_count
        ==
        3
    )

    assert (
        result.settings
        .sprint_count_mode
        ==
        "auto"
    )

    assert (
        observed[
            "sizing_calls"
        ]
        ==
        1
    )


@pytest.mark.asyncio
async def test_manual_count_bypasses_sizing_and_reaches_scrum_planner_and_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    manual = _settings(
        sprint_count=6,
        mode="manual",
    )

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=manual,
            recommended_count=2,
            expected_final_count=6,
            expect_release_sizing=False,
        )
    )

    assert (
        manual.sprint_count
        ==
        6
    )

    assert (
        result.settings
        .sprint_count
        ==
        6
    )

    assert (
        result.settings
        .sprint_count_mode
        ==
        "manual"
    )

    assert (
        observed[
            "sizing_calls"
        ]
        ==
        0
    )
