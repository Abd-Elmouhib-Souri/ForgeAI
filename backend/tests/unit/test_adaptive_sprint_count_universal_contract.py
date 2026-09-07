from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.sprint_planning_engine import (
    SprintPlanningEngine,
    SprintPlanningEngineError,
)


@pytest.mark.parametrize(
    "sprint_count",
    [
        1,
        3,
        9,
    ],
)
def test_positive_sprint_count_is_not_rejected_by_historical_4_to_8_rule(
    sprint_count,
) -> None:

    SprintPlanningEngine._validate_sprint_count(
        SimpleNamespace(
            sprint_count=sprint_count
        )
    )


@pytest.mark.parametrize(
    "sprint_count",
    [
        0,
        -1,
        True,
        1.5,
    ],
)
def test_resolved_sprint_count_requires_positive_integer(
    sprint_count,
) -> None:

    with pytest.raises(
        SprintPlanningEngineError
    ) as captured:

        SprintPlanningEngine._validate_sprint_count(
            SimpleNamespace(
                sprint_count=sprint_count
            )
        )

    assert (
        captured.value.code
        ==
        "invalid_sprint_count"
    )
