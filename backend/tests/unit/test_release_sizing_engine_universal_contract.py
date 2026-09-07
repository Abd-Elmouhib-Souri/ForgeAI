from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.project_management import (
    PlanningSettingsV1,
)

from app.services.release_sizing_engine import (
    ReleaseSizingEngine,
    ReleaseSizingEngineError,
)


class _FakePlanner:

    def __init__(
        self,
        clears_at: int | None,
    ) -> None:

        self.clears_at = clears_at
        self.calls: list[int] = []

    def plan(
        self,
        backlog,
        dependency_graph,
        planning_settings,
        advice,
    ):

        count = (
            planning_settings
            .sprint_count
        )

        self.calls.append(
            count
        )

        overflow = (
            []
            if (
                self.clears_at is not None
                and count >= self.clears_at
            )
            else ["US-OVERFLOW"]
        )

        return SimpleNamespace(
            sprint_count=count,
            overflow_story_ids=overflow,
        )


def _settings():

    return PlanningSettingsV1(
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


def _backlog(
    story_count: int,
):

    return SimpleNamespace(
        source_context_hash="source",
        context_hash="context",
        stories=[
            SimpleNamespace(
                story_id=(
                    f"US-{index:03d}"
                ),
                story_points=5,
            )
            for index
            in range(
                1,
                story_count + 1,
            )
        ],
    )


def _bound():

    return (
        SimpleNamespace(),
        SimpleNamespace(
            source_context_hash="source",
            context_hash="context",
            recommendations=[],
            warnings=[],
        ),
    )


@pytest.mark.parametrize(
    (
        "story_count",
        "clears_at",
    ),
    [
        (1, 1),
        (5, 3),
        (12, 9),
    ],
)
def test_release_sizing_returns_minimum_zero_overflow_count(
    story_count,
    clears_at,
) -> None:

    planner = _FakePlanner(
        clears_at
    )

    engine = ReleaseSizingEngine(
        planner=planner
    )

    graph, advice = _bound()

    result = engine.size(
        backlog=_backlog(
            story_count
        ),
        dependency_graph=graph,
        base_settings=_settings(),
        advice=advice,
    )

    assert (
        result.recommended_sprint_count
        ==
        clears_at
    )

    assert planner.calls == list(
        range(
            1,
            clears_at + 1,
        )
    )


def test_release_sizing_starts_from_one_not_four() -> None:

    planner = _FakePlanner(
        2
    )

    engine = ReleaseSizingEngine(
        planner=planner
    )

    graph, advice = _bound()

    result = engine.size(
        backlog=_backlog(6),
        dependency_graph=graph,
        base_settings=_settings(),
        advice=advice,
    )

    assert (
        result.recommended_sprint_count
        ==
        2
    )

    assert planner.calls == [
        1,
        2,
    ]


def test_unsizeable_release_fails_explicitly() -> None:

    planner = _FakePlanner(
        None
    )

    engine = ReleaseSizingEngine(
        planner=planner
    )

    graph, advice = _bound()

    with pytest.raises(
        ReleaseSizingEngineError
    ) as captured:

        engine.size(
            backlog=_backlog(4),
            dependency_graph=graph,
            base_settings=_settings(),
            advice=advice,
        )

    assert (
        captured.value.code
        ==
        "release_unsizeable_with_current_capacity"
    )

    assert planner.calls == [
        1,
        2,
        3,
        4,
    ]
