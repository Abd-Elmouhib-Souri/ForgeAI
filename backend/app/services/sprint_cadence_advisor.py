from __future__ import annotations

from typing import (
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas.project_management import (
    CanonicalBacklogV1,
    ProjectManagementContextV1,
)


CadenceBand = Literal[
    "short",
    "standard",
    "extended",
    "long",
]

CadenceConfidence = Literal[
    "low",
    "medium",
    "high",
]


class SprintCadencePolicyV1(
    BaseModel
):
    """
    Organisation-level cadence policy.

    The defaults are policy defaults, not universal project truths.
    Callers may inject another policy without changing the advisor's
    semantic algorithm.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    short_days: int = 7
    standard_days: int = 14
    extended_days: int = 21
    long_days: int = 28

    @model_validator(
        mode="after"
    )
    def validate_policy(
        self,
    ) -> "SprintCadencePolicyV1":

        values = (
            self.short_days,
            self.standard_days,
            self.extended_days,
            self.long_days,
        )

        if not all(
            (
                type(value) is int
                and 1 <= value <= 31
            )
            for value
            in values
        ):
            raise ValueError(
                "Cadence durations must be integer days in 1..31."
            )

        if not (
            self.short_days
            <
            self.standard_days
            <
            self.extended_days
            <
            self.long_days
        ):
            raise ValueError(
                "Cadence policy durations must be strictly increasing."
            )

        return self


class SprintCadenceRecommendationV1(
    BaseModel
):

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: Literal[
        "sprint_cadence_recommendation_v1"
    ] = (
        "sprint_cadence_recommendation_v1"
    )

    recommended_sprint_duration_days: int

    cadence_band: CadenceBand

    confidence: CadenceConfidence

    reason_codes: list[
        str
    ] = Field(
        default_factory=list
    )

    evaluated_story_count: int = 0


class SprintCadenceAdvisor:
    """
    Deterministic release-level Sprint cadence authority.

    Important semantic boundaries:

    - Story Points are never converted into calendar days.
    - sprint_duration_days never multiplies Story Point capacity.
    - project name, country, industry and language do not determine cadence.
    - one recommendation applies to the release, not separately per Sprint.
    - generic business/UI/data difficulty does not lengthen cadence.
    - only delivery-cycle signals influence cadence:
      integration, external dependencies, testing burden,
      regulatory validation, hardware validation and uncertainty.
    """

    _VALIDATION_DIMENSIONS = (
        "integration_complexity",
        "external_dependency",
        "testing_burden",
        "regulatory_risk",
        "hardware_dependency",
    )

    _IGNORED_DIFFICULTY_DIMENSIONS = (
        "business_logic",
        "data_complexity",
        "ui_complexity",
        "security",
    )

    _LEVEL_SCORE = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,

        # Unknown is not silently treated as "high".
        # It contributes limited validation pressure while remaining
        # explicitly represented in confidence/reasoning.
        "unknown": 1,
    }

    _UNCERTAINTY_SCORE = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,

        # Unknown uncertainty increases feedback pressure.
        "unknown": 2,
    }


    def __init__(
        self,
        policy: SprintCadencePolicyV1
        | None = None,
    ) -> None:

        self._policy = (
            policy
            or SprintCadencePolicyV1()
        )


    @property
    def policy(
        self,
    ) -> SprintCadencePolicyV1:

        return self._policy


    @staticmethod
    def _normalized_level(
        value,
    ) -> str:

        raw = getattr(
            value,
            "value",
            value,
        )

        text = str(
            raw or "unknown"
        ).strip().lower()

        if text not in {
            "none",
            "low",
            "medium",
            "high",
            "unknown",
        }:
            return "unknown"

        return text


    def recommend(
        self,
        *,
        context: ProjectManagementContextV1,
        backlog: CanonicalBacklogV1,
    ) -> SprintCadenceRecommendationV1:

        stories = list(
            getattr(
                backlog,
                "stories",
                [],
            )
            or []
        )

        max_validation_scores = {
            dimension: 0
            for dimension
            in self._VALIDATION_DIMENSIONS
        }

        max_validation_levels = {
            dimension: "none"
            for dimension
            in self._VALIDATION_DIMENSIONS
        }

        max_uncertainty_score = 0
        max_uncertainty_level = "none"

        factor_profiles_seen = 0
        unknown_signals_seen = 0


        for story in stories:

            factors = getattr(
                story,
                "candidate_complexity_factors",
                None,
            )

            if factors is None:
                continue

            factor_profiles_seen += 1


            for dimension in (
                self._VALIDATION_DIMENSIONS
            ):

                level = self._normalized_level(
                    getattr(
                        factors,
                        dimension,
                        "unknown",
                    )
                )

                score = self._LEVEL_SCORE[
                    level
                ]

                if level == "unknown":
                    unknown_signals_seen += 1

                if (
                    score
                    >
                    max_validation_scores[
                        dimension
                    ]
                ):
                    max_validation_scores[
                        dimension
                    ] = score

                    max_validation_levels[
                        dimension
                    ] = level


            uncertainty_level = (
                self._normalized_level(
                    getattr(
                        factors,
                        "uncertainty",
                        "unknown",
                    )
                )
            )

            uncertainty_score = (
                self._UNCERTAINTY_SCORE[
                    uncertainty_level
                ]
            )

            if uncertainty_level == "unknown":
                unknown_signals_seen += 1

            if (
                uncertainty_score
                >
                max_uncertainty_score
            ):
                max_uncertainty_score = (
                    uncertainty_score
                )

                max_uncertainty_level = (
                    uncertainty_level
                )


        regulatory_flags = list(
            getattr(
                context,
                "regulatory_flags",
                [],
            )
            or []
        )

        human_oversight = list(
            getattr(
                context,
                "human_oversight",
                [],
            )
            or []
        )

        unknowns = list(
            getattr(
                context,
                "unknowns",
                [],
            )
            or []
        )


        validation_load = sum(
            max_validation_scores.values()
        )

        if regulatory_flags:
            validation_load += 2

        if human_oversight:
            validation_load += 1


        high_validation_dimensions = sum(
            1
            for level
            in max_validation_levels.values()
            if level == "high"
        )

        medium_or_high_dimensions = sum(
            1
            for score
            in max_validation_scores.values()
            if score >= 2
        )


        feedback_pressure = (
            max_uncertainty_score
            +
            (
                1
                if unknowns
                else 0
            )
        )


        critical_high = any(
            max_validation_levels[
                dimension
            ]
            ==
            "high"
            for dimension
            in (
                "testing_burden",
                "regulatory_risk",
                "hardware_dependency",
            )
        )


        reason_codes: list[
            str
        ] = []


        if (
            high_validation_dimensions >= 4
            or (
                high_validation_dimensions >= 3
                and (
                    regulatory_flags
                    or human_oversight
                )
            )
        ):

            band: CadenceBand = "long"

            duration = (
                self._policy.long_days
            )

            reason_codes.append(
                "dense_cross_boundary_validation_cycle"
            )


        elif (
            high_validation_dimensions >= 2
            or validation_load >= 8
            or (
                critical_high
                and validation_load >= 5
            )
            or (
                medium_or_high_dimensions >= 3
                and validation_load >= 6
            )
        ):

            band = "extended"

            duration = (
                self._policy.extended_days
            )

            reason_codes.append(
                "extended_validation_coordination_cycle"
            )


        elif (
            feedback_pressure >= 3
            and validation_load <= 4
            and high_validation_dimensions == 0
        ):

            band = "short"

            duration = (
                self._policy.short_days
            )

            reason_codes.append(
                "short_feedback_learning_cycle"
            )


        else:

            band = "standard"

            duration = (
                self._policy.standard_days
            )

            reason_codes.append(
                "standard_release_feedback_cycle"
            )


        if regulatory_flags:
            reason_codes.append(
                "explicit_regulatory_validation"
            )

        if human_oversight:
            reason_codes.append(
                "explicit_human_validation"
            )

        if unknowns:
            reason_codes.append(
                "canonical_unknowns_present"
            )

        if (
            max_uncertainty_level
            in {
                "high",
                "unknown",
            }
        ):
            reason_codes.append(
                "elevated_uncertainty"
            )

        if critical_high:
            reason_codes.append(
                "high_validation_latency_signal"
            )


        if factor_profiles_seen == 0:

            confidence: CadenceConfidence = (
                "low"
            )

            reason_codes.append(
                "no_structured_story_cycle_signals"
            )


        elif (
            unknown_signals_seen > 0
            or unknowns
        ):

            confidence = "medium"

            reason_codes.append(
                "partial_signal_uncertainty"
            )


        else:

            confidence = "high"


        unique_reason_codes = list(
            dict.fromkeys(
                reason_codes
            )
        )


        return SprintCadenceRecommendationV1(
            recommended_sprint_duration_days=(
                duration
            ),
            cadence_band=band,
            confidence=confidence,
            reason_codes=unique_reason_codes,
            evaluated_story_count=len(
                stories
            ),
        )
