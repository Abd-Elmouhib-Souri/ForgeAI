from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.project_management import (
    CanonicalBacklogV1,
    CanonicalUserStoryV1,
    ProjectManagementContextV1,
)


StoryPointValue = Literal[
    1,
    2,
    3,
    5,
    8,
    13,
    21,
]


class StoryPointDecisionV1(BaseModel):
    """
    Final deterministic Story Point decision for one canonical Story.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    story_id: str
    story_points: StoryPointValue
    split_recommended: bool


class StoryPointResultV1(BaseModel):
    """
    Canonical backlog projection plus auditable Story Point decisions.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    backlog: CanonicalBacklogV1
    decisions: list[StoryPointDecisionV1]


class StoryPointPolicyError(ValueError):
    """
    Typed fail-closed error raised by StoryPointPolicy.
    """

    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        self.code = code
        super().__init__(message)


class StoryPointPolicy:
    """
    Deterministic Sprint 4 Story Point authority.

    V1 calibration:

      none    -> 0
      low     -> 1
      medium  -> 2
      high    -> 3

    All ten complexity dimensions have equal influence.

    Partial unknown values use their conservative upper bound of 3
    for estimation only. The canonical structured factor remains
    unchanged and is never rewritten.

    Aggregate load:

      0       -> 1
      1..5    -> 2
      6..10   -> 3
      11..15  -> 5
      16..20  -> 8
      21..25  -> 13
      26..30  -> 21

    21 Story Points always recommends splitting.

    The policy does not own priority, dependencies, sprint assignment,
    velocity, burndown, architecture or any external intelligence.
    """

    _FACTOR_NAMES = (
        "business_logic",
        "integration_complexity",
        "data_complexity",
        "ui_complexity",
        "security",
        "external_dependency",
        "uncertainty",
        "testing_burden",
        "regulatory_risk",
        "hardware_dependency",
    )

    _SEVERITY_RANK = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }

    _UNKNOWN = "unknown"

    _TIER_BANDS = (
        (0, 0, 1),
        (1, 5, 2),
        (6, 10, 3),
        (11, 15, 5),
        (16, 20, 8),
        (21, 25, 13),
        (26, 30, 21),
    )

    def apply(
        self,
        context: ProjectManagementContextV1,
        backlog: CanonicalBacklogV1,
    ) -> StoryPointResultV1:
        self._validate_binding(
            context=context,
            backlog=backlog,
        )

        estimated_stories: list[
            CanonicalUserStoryV1
        ] = []

        decisions: list[
            StoryPointDecisionV1
        ] = []

        for story in backlog.stories:
            story_points = (
                self._estimate_story(
                    story
                )
            )

            split_recommended = (
                story_points == 21
            )

            estimated_stories.append(
                story.model_copy(
                    update={
                        "story_points":
                            story_points,
                    },
                    deep=True,
                )
            )

            decisions.append(
                StoryPointDecisionV1(
                    story_id=story.story_id,
                    story_points=story_points,
                    split_recommended=(
                        split_recommended
                    ),
                )
            )

        estimated_backlog = (
            backlog.model_copy(
                update={
                    "stories":
                        estimated_stories,
                },
                deep=True,
            )
        )

        return StoryPointResultV1(
            backlog=estimated_backlog,
            decisions=decisions,
        )

    @staticmethod
    def _validate_binding(
        *,
        context: ProjectManagementContextV1,
        backlog: CanonicalBacklogV1,
    ) -> None:
        if (
            backlog.source_context_hash
            !=
            context.source_context_hash
        ):
            raise StoryPointPolicyError(
                "source_context_hash_mismatch",
                (
                    "Canonical backlog source_context_hash "
                    "does not match ProjectManagementContextV1."
                ),
            )

        if (
            backlog.context_hash
            !=
            context.context_hash
        ):
            raise StoryPointPolicyError(
                "context_hash_mismatch",
                (
                    "Canonical backlog context_hash "
                    "does not match ProjectManagementContextV1."
                ),
            )

    def _estimate_story(
        self,
        story: CanonicalUserStoryV1,
    ) -> StoryPointValue:
        factors = (
            story.candidate_complexity_factors
        )

        values = [
            getattr(
                factors,
                factor_name,
            )
            for factor_name
            in self._FACTOR_NAMES
        ]

        if all(
            value == self._UNKNOWN
            for value in values
        ):
            raise StoryPointPolicyError(
                "complexity_factors_all_unknown",
                (
                    "Story Point estimation cannot be "
                    "fabricated when all ten complexity "
                    "factors are unknown."
                ),
            )

        load = 0

        for value in values:
            if value == self._UNKNOWN:
                # Conservative upper-bound contribution only.
                # The canonical factor itself remains "unknown".
                load += 3
                continue

            rank = self._SEVERITY_RANK.get(
                value
            )

            if rank is None:
                raise StoryPointPolicyError(
                    "unsupported_complexity_signal",
                    (
                        "Unsupported structured complexity "
                        f"signal: {value!r}"
                    ),
                )

            load += rank

        return self._story_points_for_load(
            load
        )

    def _story_points_for_load(
        self,
        load: int,
    ) -> StoryPointValue:
        for (
            minimum,
            maximum,
            story_points,
        ) in self._TIER_BANDS:
            if minimum <= load <= maximum:
                return story_points

        raise StoryPointPolicyError(
            "complexity_load_out_of_range",
            (
                "Structured complexity load is outside "
                f"the V1 range 0..30: {load}"
            ),
        )
