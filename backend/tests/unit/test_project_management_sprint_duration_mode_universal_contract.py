from __future__ import annotations

import pytest

from app.schemas.project_management import (
    PlanningSettingsUpdateV1,
    PlanningSettingsV1,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)


def _settings(
    *,
    duration: int = 14,
    mode: str = "auto",
) -> PlanningSettingsV1:

    return PlanningSettingsV1(
        sprint_count_mode="auto",
        sprint_count=4,
        sprint_duration_mode=mode,
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


def test_duration_mode_defaults_to_auto() -> None:

    settings = PlanningSettingsV1(
        sprint_count_mode="auto",
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
        settings.sprint_duration_mode
        ==
        "auto"
    )


def test_legacy_settings_without_duration_mode_migrate_to_auto() -> None:

    payload = {
        "sprint_count_mode": "auto",
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
        settings.sprint_duration_mode
        ==
        "auto"
    )


def test_service_default_duration_mode_is_auto() -> None:

    settings = (
        ProjectManagementPlanService
        .default_settings()
    )

    assert (
        settings.sprint_duration_mode
        ==
        "auto"
    )


def test_explicit_duration_update_switches_only_duration_to_manual() -> None:

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
                sprint_duration_days=21,
            ),
        )
    )

    assert (
        updated.sprint_duration_days
        ==
        21
    )

    assert (
        updated.sprint_duration_mode
        ==
        "manual"
    )

    # Count ownership is independent.
    assert (
        updated.sprint_count_mode
        ==
        current.sprint_count_mode
    )


def test_explicit_auto_can_reclaim_duration_authority() -> None:

    service = (
        ProjectManagementPlanService()
    )

    current = _settings(
        duration=21,
        mode="manual",
    )

    updated = (
        service.settings_from_update(
            current,
            PlanningSettingsUpdateV1(
                sprint_duration_mode="auto",
            ),
        )
    )

    assert (
        updated.sprint_duration_mode
        ==
        "auto"
    )

    # Stored prior duration remains historical input until
    # the cadence authority resolves the next generation.
    assert (
        updated.sprint_duration_days
        ==
        21
    )


def test_count_and_duration_modes_are_independent() -> None:

    settings = PlanningSettingsV1(
        sprint_count_mode="manual",
        sprint_count=6,
        sprint_duration_mode="auto",
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
        "manual"
    )

    assert (
        settings.sprint_duration_mode
        ==
        "auto"
    )
