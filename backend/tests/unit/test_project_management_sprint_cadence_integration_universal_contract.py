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

from app.services.sprint_cadence_advisor import (
    SprintCadenceRecommendationV1,
)


def _settings(
    *,
    sprint_count: int,
    sprint_count_mode: str,
    sprint_duration_days: int,
    sprint_duration_mode: str,
) -> PlanningSettingsV1:

    return PlanningSettingsV1(
        sprint_count_mode=sprint_count_mode,
        sprint_count=sprint_count,
        sprint_duration_mode=sprint_duration_mode,
        sprint_duration_days=sprint_duration_days,
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
    cadence_days: int,
    recommended_count: int,
    expected_duration: int,
    expected_count: int,
    expect_cadence: bool,
    expect_sizing: bool,
) -> tuple[
    Any,
    dict[str, Any],
]:

    service = (
        ProjectManagementPlanService()
    )

    context = SimpleNamespace(
        project_id="800",
        regulatory_flags=[],
        human_oversight=[],
        unknowns=[],
    )

    candidate = object()
    canonical = object()
    prioritized = object()

    estimated = SimpleNamespace(
        source_context_hash="src-b2-b2",
        context_hash="ctx-b2-b2",
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
        source_context_hash="src-b2-b2",
        context_hash="ctx-b2-b2",
        edges=[],
    )

    observed: dict[
        str,
        Any,
    ] = {
        "cadence_calls": 0,
        "sizing_calls": 0,

        "sizing_duration": None,
        "sizing_count": None,

        "scrum_duration": None,
        "scrum_count": None,

        "planner_duration": None,
        "planner_count": None,

        "assembly_duration": None,
        "assembly_count": None,

        "assembly_duration_mode": None,
        "assembly_count_mode": None,

        "revision": None,
    }


    # -------------------------------------------------------------------------
    # Context
    # -------------------------------------------------------------------------

    monkeypatch.setattr(
        service,
        "_build_context",
        lambda **kwargs: context,
    )


    # -------------------------------------------------------------------------
    # Product Owner
    # -------------------------------------------------------------------------

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


    # -------------------------------------------------------------------------
    # Canonical backlog
    # -------------------------------------------------------------------------

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


    # -------------------------------------------------------------------------
    # MoSCoW
    # -------------------------------------------------------------------------

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


    # -------------------------------------------------------------------------
    # Story Points
    # -------------------------------------------------------------------------

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


    # -------------------------------------------------------------------------
    # Dependency graph
    # -------------------------------------------------------------------------

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


    # -------------------------------------------------------------------------
    # Cadence
    # -------------------------------------------------------------------------

    def fake_cadence(
        *,
        context: Any,
        backlog: Any,
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
                "integration-test"
            ],
            evaluated_story_count=3,
        )


    monkeypatch.setattr(
        service._cadence_advisor,
        "recommend",
        fake_cadence,
    )


    # -------------------------------------------------------------------------
    # Release sizing
    # -------------------------------------------------------------------------

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

        settings = (
            kwargs[
                "base_settings"
            ]
        )

        observed[
            "sizing_duration"
        ] = (
            settings
            .sprint_duration_days
        )

        observed[
            "sizing_count"
        ] = (
            settings
            .sprint_count
        )

        assert (
            settings
            .sprint_duration_days
            ==
            expected_duration
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


    # -------------------------------------------------------------------------
    # Scrum Master
    # -------------------------------------------------------------------------

    async def fake_scrum(
        self,
        backlog,
        dependency_graph,
        planning_settings,
    ):

        assert backlog is estimated
        assert dependency_graph is graph

        observed[
            "scrum_duration"
        ] = (
            planning_settings
            .sprint_duration_days
        )

        observed[
            "scrum_count"
        ] = (
            planning_settings
            .sprint_count
        )

        assert (
            planning_settings
            .sprint_duration_days
            ==
            expected_duration
        )

        assert (
            planning_settings
            .sprint_count
            ==
            expected_count
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


    # -------------------------------------------------------------------------
    # Final planner
    # -------------------------------------------------------------------------

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
            "planner_duration"
        ] = (
            planning_settings
            .sprint_duration_days
        )

        observed[
            "planner_count"
        ] = (
            planning_settings
            .sprint_count
        )

        assert (
            planning_settings
            .sprint_duration_days
            ==
            expected_duration
        )

        assert (
            planning_settings
            .sprint_count
            ==
            expected_count
        )

        return SimpleNamespace(
            sprint_count=(
                expected_count
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


    # -------------------------------------------------------------------------
    # Assembly
    # -------------------------------------------------------------------------

    sentinel_plan = SimpleNamespace(
        marker="assembled-b2-b2",
        settings=None,
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
            "assembly_duration"
        ] = (
            settings
            .sprint_duration_days
        )

        observed[
            "assembly_count"
        ] = (
            settings
            .sprint_count
        )

        observed[
            "assembly_duration_mode"
        ] = (
            settings
            .sprint_duration_mode
        )

        observed[
            "assembly_count_mode"
        ] = (
            settings
            .sprint_count_mode
        )

        observed[
            "revision"
        ] = revision

        assert (
            settings
            .sprint_duration_days
            ==
            expected_duration
        )

        assert (
            settings
            .sprint_count
            ==
            expected_count
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


    # -------------------------------------------------------------------------
    # Execute
    # -------------------------------------------------------------------------

    result = await service.generate(
        project_id=800,
        analysis_data={},
        settings=incoming_settings,
        revision=5,
    )


    assert result is sentinel_plan

    assert (
        bool(
            observed[
                "cadence_calls"
            ]
        )
        is expect_cadence
    )

    assert (
        bool(
            observed[
                "sizing_calls"
            ]
        )
        is expect_sizing
    )

    assert (
        observed[
            "scrum_duration"
        ]
        ==
        expected_duration
    )

    assert (
        observed[
            "planner_duration"
        ]
        ==
        expected_duration
    )

    assert (
        observed[
            "assembly_duration"
        ]
        ==
        expected_duration
    )

    assert (
        observed[
            "scrum_count"
        ]
        ==
        expected_count
    )

    assert (
        observed[
            "planner_count"
        ]
        ==
        expected_count
    )

    assert (
        observed[
            "assembly_count"
        ]
        ==
        expected_count
    )

    assert (
        observed[
            "revision"
        ]
        ==
        5
    )


    return (
        result,
        observed,
    )


@pytest.mark.asyncio
async def test_first_generation_auto_cadence_reaches_every_downstream_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=None,
            cadence_days=7,
            recommended_count=3,
            expected_duration=7,
            expected_count=3,
            expect_cadence=True,
            expect_sizing=True,
        )
    )

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
        observed[
            "sizing_duration"
        ]
        ==
        7
    )

    assert (
        result.settings
        .sprint_duration_days
        ==
        7
    )

    assert (
        result.settings
        .sprint_duration_mode
        ==
        "auto"
    )

    assert (
        result.settings
        .sprint_count
        ==
        3
    )


@pytest.mark.asyncio
async def test_auto_regeneration_recalculates_cadence_without_mutating_previous_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    previous = _settings(
        sprint_count=9,
        sprint_count_mode="auto",
        sprint_duration_days=28,
        sprint_duration_mode="auto",
    )

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=previous,
            cadence_days=14,
            recommended_count=4,
            expected_duration=14,
            expected_count=4,
            expect_cadence=True,
            expect_sizing=True,
        )
    )

    # Historical settings remain immutable.
    assert (
        previous.sprint_duration_days
        ==
        28
    )

    assert (
        previous.sprint_duration_mode
        ==
        "auto"
    )

    assert (
        previous.sprint_count
        ==
        9
    )

    # New revision owns the new recommendations.
    assert (
        result.settings
        .sprint_duration_days
        ==
        14
    )

    assert (
        result.settings
        .sprint_count
        ==
        4
    )

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


@pytest.mark.asyncio
async def test_manual_duration_bypasses_cadence_but_auto_count_still_sizes_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    settings = _settings(
        sprint_count=9,
        sprint_count_mode="auto",
        sprint_duration_days=21,
        sprint_duration_mode="manual",
    )

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=settings,
            cadence_days=7,
            recommended_count=3,
            expected_duration=21,
            expected_count=3,
            expect_cadence=False,
            expect_sizing=True,
        )
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
        1
    )

    assert (
        observed[
            "sizing_duration"
        ]
        ==
        21
    )

    assert (
        result.settings
        .sprint_duration_days
        ==
        21
    )

    assert (
        result.settings
        .sprint_duration_mode
        ==
        "manual"
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


@pytest.mark.asyncio
async def test_auto_duration_and_manual_count_are_independent_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    settings = _settings(
        sprint_count=6,
        sprint_count_mode="manual",
        sprint_duration_days=28,
        sprint_duration_mode="auto",
    )

    result, observed = (
        await _run_pipeline(
            monkeypatch,
            incoming_settings=settings,
            cadence_days=21,
            recommended_count=2,
            expected_duration=21,
            expected_count=6,
            expect_cadence=True,
            expect_sizing=False,
        )
    )

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
        0
    )

    assert (
        result.settings
        .sprint_duration_days
        ==
        21
    )

    assert (
        result.settings
        .sprint_duration_mode
        ==
        "auto"
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
