from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.project_management import (
    CanonicalBacklogV1,
    PlanningSettingsV1,
    ScrumMasterAdviceV1,
)

from app.services.dependency_graph_builder import (
    DependencyGraphV1,
)

from app.services.sprint_planning_engine import (
    SprintPlanningEngine,
)


class ReleaseSizingResultV1(
    BaseModel
):

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: Literal[
        "release_sizing_result_v1"
    ] = "release_sizing_result_v1"

    recommended_sprint_count: int

    evaluated_sprint_counts: list[
        int
    ] = Field(
        default_factory=list
    )

    reason: Literal[
        "minimum_zero_overflow"
    ] = "minimum_zero_overflow"


class ReleaseSizingEngineError(
    RuntimeError
):

    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:

        self.code = code
        super().__init__(
            message
        )


class ReleaseSizingEngine:
    """
    Deterministic release-sizing authority.

    It reuses SprintPlanningEngine rather than duplicating capacity,
    dependency, ordering, balancing or overflow policy.

    The recommendation is the minimum positive Sprint count whose
    certified planning result contains no overflow.
    """

    def __init__(
        self,
        planner: SprintPlanningEngine
        | None = None,
    ) -> None:

        self._planner = (
            planner
            or SprintPlanningEngine()
        )


    def size(
        self,
        *,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        base_settings: PlanningSettingsV1,
        advice: ScrumMasterAdviceV1,
    ) -> ReleaseSizingResultV1:

        stories = list(
            backlog.stories
        )

        if not stories:
            raise ReleaseSizingEngineError(
                "empty_release_backlog",
                (
                    "Release sizing requires at "
                    "least one canonical Story."
                ),
            )

        # When every Story is individually feasible, one Story per
        # Sprint is a finite natural upper bound. If overflow remains
        # there, arbitrary extra empty Sprints cannot fix the release.
        upper_bound = len(
            stories
        )

        evaluated: list[int] = []

        for sprint_count in range(
            1,
            upper_bound + 1,
        ):

            settings = (
                base_settings.model_copy(
                    update={
                        "sprint_count":
                            sprint_count,
                    },
                    deep=True,
                )
            )

            planning = (
                self._planner.plan(
                    backlog,
                    dependency_graph,
                    settings,
                    advice,
                )
            )

            evaluated.append(
                sprint_count
            )

            if not planning.overflow_story_ids:

                return ReleaseSizingResultV1(
                    recommended_sprint_count=(
                        sprint_count
                    ),
                    evaluated_sprint_counts=(
                        evaluated
                    ),
                )

        raise ReleaseSizingEngineError(
            "release_unsizeable_with_current_capacity",
            (
                "The canonical release cannot be fully "
                "planned with the current per-Sprint "
                "capacity without changing backlog truth."
            ),
        )
