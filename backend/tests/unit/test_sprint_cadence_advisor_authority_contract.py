from __future__ import annotations

import importlib.util


def test_sprint_cadence_advisor_authority_exists() -> None:
    """
    Sprint duration must have a dedicated deterministic release-level
    authority. It must not be invented by the frontend, Scrum Master,
    Product Owner or SprintPlanningEngine.
    """

    spec = importlib.util.find_spec(
        "app.services.sprint_cadence_advisor"
    )

    assert spec is not None, (
        "SprintCadenceAdvisor authority is missing."
    )
