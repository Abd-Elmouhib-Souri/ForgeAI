from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_management import (
    CanonicalBacklogV1,
    PlanningSettingsV1,
    ScrumMasterAdviceV1,
)
from app.services.dependency_graph_builder import (
    DependencyGraphV1,
)


MIN_SPRINTS = 1

# Sprint count is release-derived. There is no universal
# product maximum; optional organisational limits belong to
# an explicit policy layer, not this planner.
MAX_SPRINTS = None


_ALLOWED_PRIORITIES = frozenset(
    {
        "Must",
        "Should",
        "Could",
        "Won't",
    }
)


_PRIORITY_RANK = {
    "Must": 0,
    "Should": 1,
    "Could": 2,
    "Won't": 3,
}


_ALLOWED_STORY_POINTS = frozenset(
    {
        1,
        2,
        3,
        5,
        8,
        13,
        21,
    }
)


class SprintAssignmentV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    story_id: str
    sprint_number: int


class SprintPlanningResultV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: Literal[
        "sprint_planning_result_v1"
    ] = "sprint_planning_result_v1"

    source_context_hash: str
    context_hash: str
    sprint_count: int

    assignments: list[
        SprintAssignmentV1
    ] = Field(
        default_factory=list
    )

    overflow_story_ids: list[
        str
    ] = Field(
        default_factory=list
    )

    warnings: list[
        str
    ] = Field(
        default_factory=list
    )


class SprintPlanningEngineError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        details: list[str] | None = None,
    ) -> None:
        self.code = code
        self.details = list(
            details or []
        )

        super().__init__(
            message
        )


class SprintPlanningEngine:
    """
    Deterministic Sprint Planning authority.

    Current certified responsibilities:
    - canonical input binding;
    - planning-input validation;
    - hard-dependency-safe priority-aware ordering.

    Capacity, Sprint assignment, overflow and balancing
    remain intentionally outside the current certified layer.
    """

    def plan(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        planning_settings: PlanningSettingsV1,
        advice: ScrumMasterAdviceV1,
    ) -> SprintPlanningResultV1:
        self._validate_inputs(
            backlog=backlog,
            dependency_graph=dependency_graph,
            planning_settings=planning_settings,
            advice=advice,
        )

        ordered_story_ids = self._ordered_story_ids(
            backlog=backlog,
            dependency_graph=dependency_graph,
        )

        sprint_capacity = self._effective_sprint_capacity(
            planning_settings=planning_settings,
        )

        assignments, unplaced_story_ids = self._assign_story_ids(
            backlog=backlog,
            dependency_graph=dependency_graph,
            ordered_story_ids=ordered_story_ids,
            planning_settings=planning_settings,
            sprint_capacity=sprint_capacity,
        )

        overflow_story_ids, warnings = self._project_overflow(
            backlog=backlog,
            dependency_graph=dependency_graph,
            unplaced_story_ids=unplaced_story_ids,
            sprint_capacity=sprint_capacity,
        )

        balanced_assignments = self._balance_assignments(
            backlog=backlog,
            dependency_graph=dependency_graph,
            assignments=assignments,
            sprint_capacity=sprint_capacity,
        )

        result = SprintPlanningResultV1(
            source_context_hash=backlog.source_context_hash,
            context_hash=backlog.context_hash,
            sprint_count=planning_settings.sprint_count,
            assignments=balanced_assignments,
            overflow_story_ids=overflow_story_ids,
            warnings=warnings,
        )

        self._validate_final_plan(
            backlog=backlog,
            dependency_graph=dependency_graph,
            planning_settings=planning_settings,
            ordered_story_ids=ordered_story_ids,
            result=result,
            sprint_capacity=sprint_capacity,
        )

        return result

    def _ordered_story_ids(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
    ) -> list[str]:
        """
        Return a deterministic hard-dependency-safe Story order.

        Hard dependencies are absolute constraints.

        Among Stories that are currently ready, MoSCoW priority
        is used first. The canonical hard topological order is
        the deterministic tie-break for equal priority.

        Soft dependencies do not block readiness.
        """

        canonical_order = list(
            dependency_graph.hard_topological_order
        )

        canonical_index = {
            story_id: index
            for index, story_id
            in enumerate(
                canonical_order
            )
        }

        story_by_id = {
            story.story_id: story
            for story in backlog.stories
        }

        remaining_hard_dependencies = {
            story_id: 0
            for story_id
            in canonical_order
        }

        hard_dependents = {
            story_id: []
            for story_id
            in canonical_order
        }

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            remaining_hard_dependencies[
                edge.story_id
            ] += 1

            hard_dependents[
                edge.depends_on_story_id
            ].append(
                edge.story_id
            )

        ready = [
            story_id
            for story_id
            in canonical_order
            if (
                remaining_hard_dependencies[
                    story_id
                ]
                == 0
            )
        ]

        ordered: list[str] = []

        while ready:
            next_story_id = min(
                ready,
                key=lambda story_id: (
                    _PRIORITY_RANK[
                        story_by_id[
                            story_id
                        ].priority
                    ],
                    canonical_index[
                        story_id
                    ],
                ),
            )

            ready.remove(
                next_story_id
            )

            ordered.append(
                next_story_id
            )

            for dependent_story_id in (
                hard_dependents[
                    next_story_id
                ]
            ):
                remaining_hard_dependencies[
                    dependent_story_id
                ] -= 1

                if (
                    remaining_hard_dependencies[
                        dependent_story_id
                    ]
                    == 0
                ):
                    ready.append(
                        dependent_story_id
                    )

        if (
            len(ordered)
            != len(canonical_order)
        ):
            raise SprintPlanningEngineError(
                code="dependency_graph_mismatch",
                message=(
                    "Unable to produce a complete "
                    "hard-dependency-safe planning order."
                ),
                details=[
                    "priority_aware_topological_order_incomplete"
                ],
            )

        return ordered

    def _effective_sprint_capacity(
        self,
        planning_settings: PlanningSettingsV1,
    ) -> float:
        """
        Return deterministic Story Point capacity for one Sprint.

        planned_velocity already represents the planned velocity
        of the team for one configured Sprint.

        capacity_adjustment is the explicit multiplicative
        availability/capacity factor.

        team_size, sprint_count and sprint_duration_days are not
        silently converted into Story Point multipliers.
        """

        planned_velocity = (
            planning_settings.planned_velocity
        )

        capacity_adjustment = (
            planning_settings.capacity_adjustment
        )

        details: list[str] = []

        for field_name, value in (
            (
                "planned_velocity",
                planned_velocity,
            ),
            (
                "capacity_adjustment",
                capacity_adjustment,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    (
                        int,
                        float,
                    ),
                )
            ):
                details.append(
                    f"{field_name}:not_numeric"
                )
                continue

            numeric_value = float(
                value
            )

            if not math.isfinite(
                numeric_value
            ):
                details.append(
                    f"{field_name}:non_finite"
                )
                continue

            if numeric_value < 0:
                details.append(
                    f"{field_name}:negative"
                )

        if details:
            raise SprintPlanningEngineError(
                code="invalid_capacity_settings",
                message=(
                    "Sprint capacity settings must be "
                    "finite non-negative numeric values."
                ),
                details=details,
            )

        effective_capacity = (
            float(
                planned_velocity
            )
            * float(
                capacity_adjustment
            )
        )

        if (
            not math.isfinite(
                effective_capacity
            )
            or effective_capacity < 0
        ):
            raise SprintPlanningEngineError(
                code="invalid_capacity_settings",
                message=(
                    "Effective Sprint capacity must be "
                    "finite and non-negative."
                ),
                details=[
                    "effective_sprint_capacity"
                ],
            )

        return effective_capacity
    def _assign_story_ids(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        ordered_story_ids: list[str],
        planning_settings: PlanningSettingsV1,
        sprint_capacity: float,
    ) -> tuple[
        list[SprintAssignmentV1],
        list[str],
    ]:
        """
        Deterministically place Stories using sequential next-fit.

        The certified Story order is authoritative.

        Capacity is never exceeded and earlier Sprints are never
        backfilled after assignment has advanced to a later Sprint.

        Hard dependencies may share a Sprint with their dependent,
        provided the dependency has already been assigned.

        Stories that cannot currently be placed are returned through
        the internal unplaced list. This helper does not decide the
        public overflow semantics.

        No automatic split, lock interpretation, AI recommendation,
        balancing or replanning authority belongs to this helper.
        """

        story_by_id = {
            story.story_id: story
            for story in backlog.stories
        }

        hard_dependencies: dict[
            str,
            set[str],
        ] = {
            story_id: set()
            for story_id
            in ordered_story_ids
        }

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            hard_dependencies.setdefault(
                edge.story_id,
                set(),
            ).add(
                edge.depends_on_story_id
            )

        assignments: list[
            SprintAssignmentV1
        ] = []

        unplaced_story_ids: list[str] = []

        unplaced_story_id_set: set[str] = set()

        assigned_sprint_by_story_id: dict[
            str,
            int,
        ] = {}

        sprint_count = (
            planning_settings.sprint_count
        )

        current_sprint = 1
        used_capacity = 0.0

        for story_id in ordered_story_ids:
            dependencies = (
                hard_dependencies.get(
                    story_id,
                    set(),
                )
            )

            dependency_unplaced = any(
                (
                    dependency_story_id
                    in unplaced_story_id_set
                    or dependency_story_id
                    not in assigned_sprint_by_story_id
                )
                for dependency_story_id
                in dependencies
            )

            if dependency_unplaced:
                unplaced_story_ids.append(
                    story_id
                )

                unplaced_story_id_set.add(
                    story_id
                )

                continue

            story = story_by_id[
                story_id
            ]

            story_points = float(
                story.story_points
            )

            if (
                sprint_capacity <= 0
                or story_points
                > sprint_capacity
            ):
                unplaced_story_ids.append(
                    story_id
                )

                unplaced_story_id_set.add(
                    story_id
                )

                continue

            if current_sprint > sprint_count:
                unplaced_story_ids.append(
                    story_id
                )

                unplaced_story_id_set.add(
                    story_id
                )

                continue

            if (
                used_capacity
                + story_points
                > sprint_capacity
            ):
                current_sprint += 1
                used_capacity = 0.0

            if current_sprint > sprint_count:
                unplaced_story_ids.append(
                    story_id
                )

                unplaced_story_id_set.add(
                    story_id
                )

                continue

            assignments.append(
                SprintAssignmentV1(
                    story_id=story_id,
                    sprint_number=current_sprint,
                )
            )

            assigned_sprint_by_story_id[
                story_id
            ] = current_sprint

            used_capacity += (
                story_points
            )

        return (
            assignments,
            unplaced_story_ids,
        )
    def _project_overflow(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        unplaced_story_ids: list[str],
        sprint_capacity: float,
    ) -> tuple[
        list[str],
        list[str],
    ]:
        """
        Project internal unplaced Stories into public overflow output.

        Every unplaced Story remains publicly visible.

        Classification precedence:
        1. blocked by an unplaced hard dependency;
        2. zero/non-positive Sprint capacity;
        3. Story larger than one Sprint capacity;
        4. otherwise configured planning capacity is exhausted.

        This helper owns classification/projection only. It does not
        reorder Stories, recompute capacity, assign Stories, balance
        Sprints, split Stories, interpret locks or consume AI advice.
        """

        story_by_id = {
            story.story_id: story
            for story in backlog.stories
        }

        unplaced_story_id_set = set(
            unplaced_story_ids
        )

        hard_dependencies: dict[
            str,
            set[str],
        ] = {
            story_id: set()
            for story_id
            in unplaced_story_ids
        }

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            if (
                edge.story_id
                not in unplaced_story_id_set
            ):
                continue

            hard_dependencies.setdefault(
                edge.story_id,
                set(),
            ).add(
                edge.depends_on_story_id
            )

        overflow_story_ids = list(
            unplaced_story_ids
        )

        warnings: list[str] = []

        for story_id in unplaced_story_ids:
            dependencies = (
                hard_dependencies.get(
                    story_id,
                    set(),
                )
            )

            blocked_by_unplaced_dependency = any(
                dependency_story_id
                in unplaced_story_id_set
                for dependency_story_id
                in dependencies
            )

            if blocked_by_unplaced_dependency:
                reason = (
                    "blocked_by_unplaced_dependency"
                )

            elif sprint_capacity <= 0:
                reason = (
                    "zero_capacity"
                )

            else:
                story = story_by_id[
                    story_id
                ]

                story_points = float(
                    story.story_points
                )

                if story_points > sprint_capacity:
                    reason = (
                        "story_exceeds_sprint_capacity"
                    )
                else:
                    reason = (
                        "capacity_exhausted"
                    )

            warnings.append(
                "sprint_overflow:"
                f"{reason}:"
                f"{story_id}"
            )

        return (
            overflow_story_ids,
            warnings,
        )
    def _balance_assignments(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        assignments: list[SprintAssignmentV1],
        sprint_capacity: float,
    ) -> list[SprintAssignmentV1]:
        """
        Conservatively rebalance already-assigned Stories.

        The assigned Story set and its certified order are immutable.
        Existing used Sprint numbers are immutable as a set.

        A Story may stay in place or move to a later existing Sprint,
        but never to an earlier Sprint.

        Among every feasible contiguous partition, choose the
        deterministic minimum tuple:

        1. load spread;
        2. number of moved Stories;
        3. total Sprint delay;
        4. lexicographic Sprint-number vector.

        Capacity, hard-dependency precedence and non-empty used
        Sprints remain mandatory.

        This helper does not recover overflow Stories, recompute
        upstream authorities, interpret locks, consume AI advice,
        calculate Agile metrics or perform replanning.
        """

        if not assignments:
            return []

        def _copy_original() -> list[SprintAssignmentV1]:
            return [
                SprintAssignmentV1(
                    story_id=item.story_id,
                    sprint_number=item.sprint_number,
                )
                for item in assignments
            ]

        story_ids = [
            item.story_id
            for item in assignments
        ]

        if len(
            story_ids
        ) != len(
            set(
                story_ids
            )
        ):
            return _copy_original()

        story_by_id = {
            story.story_id: story
            for story in backlog.stories
        }

        if any(
            story_id not in story_by_id
            for story_id in story_ids
        ):
            return _copy_original()

        original_sprint_numbers = [
            item.sprint_number
            for item in assignments
        ]

        if original_sprint_numbers != sorted(
            original_sprint_numbers
        ):
            return _copy_original()

        used_sprints = sorted(
            set(
                original_sprint_numbers
            )
        )

        if len(
            used_sprints
        ) <= 1:
            return _copy_original()

        if sprint_capacity <= 0:
            return _copy_original()

        story_points = [
            float(
                story_by_id[
                    story_id
                ].story_points
            )
            for story_id in story_ids
        ]

        if any(
            points <= 0
            or points > sprint_capacity
            for points in story_points
        ):
            return _copy_original()

        story_index = {
            story_id: index
            for index, story_id
            in enumerate(
                story_ids
            )
        }

        assigned_story_id_set = set(
            story_ids
        )

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            if (
                edge.story_id
                not in assigned_story_id_set
            ):
                continue

            if (
                edge.depends_on_story_id
                not in assigned_story_id_set
            ):
                return _copy_original()

            dependency_index = story_index[
                edge.depends_on_story_id
            ]

            dependent_index = story_index[
                edge.story_id
            ]

            if dependency_index > dependent_index:
                return _copy_original()

        prefix_points: list[float] = [
            0.0
        ]

        for points in story_points:
            prefix_points.append(
                prefix_points[-1]
                + points
            )

        story_count = len(
            story_ids
        )

        sprint_count = len(
            used_sprints
        )

        if story_count < sprint_count:
            return _copy_original()

        Score = tuple[
            float,
            int,
            int,
            tuple[int, ...],
        ]

        memo: dict[
            tuple[
                int,
                int,
                float | None,
                float | None,
            ],
            Score | None,
        ] = {}

        def _best_partition(
            start_index: int,
            sprint_position: int,
            current_min_load: float | None,
            current_max_load: float | None,
        ) -> Score | None:

            key = (
                start_index,
                sprint_position,
                current_min_load,
                current_max_load,
            )

            if key in memo:
                return memo[
                    key
                ]

            sprint_number = (
                used_sprints[
                    sprint_position
                ]
            )

            remaining_sprints = (
                sprint_count
                - sprint_position
            )

            max_end = (
                story_count
                - (
                    remaining_sprints
                    - 1
                )
            )

            if (
                sprint_position
                == sprint_count - 1
            ):
                candidate_ends = (
                    story_count,
                )
            else:
                candidate_ends = range(
                    start_index + 1,
                    max_end + 1,
                )

            best: Score | None = None

            for end_index in candidate_ends:
                if end_index <= start_index:
                    continue

                segment_load = (
                    prefix_points[
                        end_index
                    ]
                    - prefix_points[
                        start_index
                    ]
                )

                if segment_load > sprint_capacity:
                    if (
                        sprint_position
                        != sprint_count - 1
                    ):
                        break

                    continue

                violates_forward_only = any(
                    sprint_number
                    < original_sprint_numbers[
                        index
                    ]
                    for index
                    in range(
                        start_index,
                        end_index,
                    )
                )

                if violates_forward_only:
                    continue

                next_min_load = (
                    segment_load
                    if current_min_load
                    is None
                    else min(
                        current_min_load,
                        segment_load,
                    )
                )

                next_max_load = (
                    segment_load
                    if current_max_load
                    is None
                    else max(
                        current_max_load,
                        segment_load,
                    )
                )

                segment_vector = (
                    sprint_number,
                ) * (
                    end_index
                    - start_index
                )

                segment_moved = sum(
                    1
                    for index
                    in range(
                        start_index,
                        end_index,
                    )
                    if sprint_number
                    != original_sprint_numbers[
                        index
                    ]
                )

                segment_delay = sum(
                    sprint_number
                    - original_sprint_numbers[
                        index
                    ]
                    for index
                    in range(
                        start_index,
                        end_index,
                    )
                )

                if (
                    sprint_position
                    == sprint_count - 1
                ):
                    if end_index != story_count:
                        continue

                    candidate: Score = (
                        float(
                            next_max_load
                            - next_min_load
                        ),
                        segment_moved,
                        segment_delay,
                        segment_vector,
                    )

                else:
                    suffix = _best_partition(
                        end_index,
                        sprint_position + 1,
                        next_min_load,
                        next_max_load,
                    )

                    if suffix is None:
                        continue

                    candidate = (
                        suffix[0],
                        segment_moved
                        + suffix[1],
                        segment_delay
                        + suffix[2],
                        segment_vector
                        + suffix[3],
                    )

                if (
                    best is None
                    or candidate < best
                ):
                    best = candidate

            memo[
                key
            ] = best

            return best

        best = _best_partition(
            0,
            0,
            None,
            None,
        )

        if best is None:
            return _copy_original()

        balanced_sprint_numbers = (
            best[3]
        )

        balanced = [
            SprintAssignmentV1(
                story_id=story_id,
                sprint_number=sprint_number,
            )
            for story_id, sprint_number
            in zip(
                story_ids,
                balanced_sprint_numbers,
                strict=True,
            )
        ]

        balanced_sprint_by_story_id = {
            item.story_id: item.sprint_number
            for item in balanced
        }

        balanced_used_sprints = sorted(
            {
                item.sprint_number
                for item in balanced
            }
        )

        if balanced_used_sprints != used_sprints:
            return _copy_original()

        loads = {
            sprint_number: 0.0
            for sprint_number
            in used_sprints
        }

        for item in balanced:
            loads[
                item.sprint_number
            ] += float(
                story_by_id[
                    item.story_id
                ].story_points
            )

        if any(
            load > sprint_capacity
            for load in loads.values()
        ):
            return _copy_original()

        if any(
            (
                balanced_sprint_by_story_id[
                    item.story_id
                ]
                < item.sprint_number
            )
            for item in assignments
        ):
            return _copy_original()

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            if (
                edge.story_id
                not in balanced_sprint_by_story_id
            ):
                continue

            if (
                edge.depends_on_story_id
                not in balanced_sprint_by_story_id
            ):
                return _copy_original()

            if (
                balanced_sprint_by_story_id[
                    edge.depends_on_story_id
                ]
                >
                balanced_sprint_by_story_id[
                    edge.story_id
                ]
            ):
                return _copy_original()

        return balanced
    def _validate_final_plan(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        planning_settings: PlanningSettingsV1,
        ordered_story_ids: list[str],
        result: SprintPlanningResultV1,
        sprint_capacity: float,
    ) -> None:
        """
        Validate the completed deterministic Sprint Planning result.

        This boundary validates already-produced planning decisions.
        It does not recalculate ordering, capacity, assignment,
        overflow, balancing, AI advice, metrics or validation status.
        """

        details: list[str] = []

        canonical_story_ids = [
            story.story_id
            for story in backlog.stories
        ]

        canonical_story_id_set = set(
            canonical_story_ids
        )

        certified_order = list(
            ordered_story_ids
        )

        certified_order_valid = (
            len(certified_order)
            == len(canonical_story_ids)
            and len(certified_order)
            == len(set(certified_order))
            and set(certified_order)
            == canonical_story_id_set
        )

        if not certified_order_valid:
            details.append(
                "certified_order_mismatch"
            )

        if (
            result.schema_version
            != "sprint_planning_result_v1"
        ):
            details.append(
                "schema_version_mismatch"
            )

        if (
            result.source_context_hash
            != backlog.source_context_hash
        ):
            details.append(
                "source_context_hash_mismatch"
            )

        if (
            result.context_hash
            != backlog.context_hash
        ):
            details.append(
                "context_hash_mismatch"
            )

        if (
            result.sprint_count
            != planning_settings.sprint_count
        ):
            details.append(
                "sprint_count_mismatch"
            )

        assignments = list(
            result.assignments
        )

        overflow_story_ids = list(
            result.overflow_story_ids
        )

        warnings = list(
            result.warnings
        )

        assignment_story_ids = [
            item.story_id
            for item in assignments
        ]

        referenced_story_ids = (
            assignment_story_ids
            + overflow_story_ids
        )

        unknown_story_ids = [
            story_id
            for story_id in referenced_story_ids
            if story_id
            not in canonical_story_id_set
        ]

        if unknown_story_ids:
            details.append(
                "unknown_story_reference:"
                + ",".join(
                    str(story_id)
                    for story_id
                    in unknown_story_ids
                )
            )

        if (
            len(assignment_story_ids)
            != len(set(assignment_story_ids))
        ):
            details.append(
                "duplicate_assignment_story"
            )

        if (
            len(overflow_story_ids)
            != len(set(overflow_story_ids))
        ):
            details.append(
                "duplicate_overflow_story"
            )

        assignment_story_id_set = set(
            assignment_story_ids
        )

        overflow_story_id_set = set(
            overflow_story_ids
        )

        if (
            assignment_story_id_set
            & overflow_story_id_set
        ):
            details.append(
                "story_partition_overlap"
            )

        if (
            assignment_story_id_set
            | overflow_story_id_set
        ) != canonical_story_id_set:
            details.append(
                "story_partition_mismatch"
            )

        valid_assignment_sprints = True

        for item in assignments:
            sprint_number = item.sprint_number

            if (
                type(sprint_number) is not int
                or sprint_number < 1
                or sprint_number
                > planning_settings.sprint_count
            ):
                valid_assignment_sprints = False

                details.append(
                    "invalid_assignment_sprint:"
                    f"{item.story_id}"
                )

        if valid_assignment_sprints:
            sprint_numbers = [
                item.sprint_number
                for item in assignments
            ]

            if sprint_numbers != sorted(
                sprint_numbers
            ):
                details.append(
                    "assignment_sprint_order_mismatch"
                )

        story_by_id = {
            story.story_id: story
            for story in backlog.stories
        }

        capacity_valid = (
            type(sprint_capacity)
            in (int, float)
            and not isinstance(
                sprint_capacity,
                bool,
            )
            and math.isfinite(
                float(sprint_capacity)
            )
            and float(sprint_capacity) >= 0
        )

        if not capacity_valid:
            details.append(
                "invalid_final_capacity"
            )

        if (
            capacity_valid
            and valid_assignment_sprints
        ):
            sprint_loads: dict[
                int,
                float,
            ] = {}

            for item in assignments:
                if item.story_id not in story_by_id:
                    continue

                sprint_loads.setdefault(
                    item.sprint_number,
                    0.0,
                )

                sprint_loads[
                    item.sprint_number
                ] += float(
                    story_by_id[
                        item.story_id
                    ].story_points
                )

            if any(
                load > float(sprint_capacity)
                for load
                in sprint_loads.values()
            ):
                details.append(
                    "sprint_capacity_exceeded"
                )

        if certified_order_valid:
            position = {
                story_id: index
                for index, story_id
                in enumerate(certified_order)
            }

            known_assignment_ids = [
                story_id
                for story_id
                in assignment_story_ids
                if story_id in position
            ]

            if known_assignment_ids != sorted(
                known_assignment_ids,
                key=position.__getitem__,
            ):
                details.append(
                    "assignment_order_mismatch"
                )

            known_overflow_ids = [
                story_id
                for story_id
                in overflow_story_ids
                if story_id in position
            ]

            if known_overflow_ids != sorted(
                known_overflow_ids,
                key=position.__getitem__,
            ):
                details.append(
                    "overflow_order_mismatch"
                )

        assignment_sprint_by_story_id: dict[
            str,
            int,
        ] = {}

        for item in assignments:
            if (
                item.story_id
                not in canonical_story_id_set
            ):
                continue

            if type(item.sprint_number) is not int:
                continue

            assignment_sprint_by_story_id.setdefault(
                item.story_id,
                item.sprint_number,
            )

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            dependent_story_id = edge.story_id
            dependency_story_id = (
                edge.depends_on_story_id
            )

            if (
                dependent_story_id
                not in assignment_sprint_by_story_id
            ):
                continue

            if (
                dependency_story_id
                in overflow_story_id_set
            ):
                details.append(
                    "assigned_story_blocked_by_"
                    "overflow_dependency:"
                    f"{dependent_story_id}->"
                    f"{dependency_story_id}"
                )
                continue

            if (
                dependency_story_id
                not in assignment_sprint_by_story_id
            ):
                continue

            if (
                assignment_sprint_by_story_id[
                    dependency_story_id
                ]
                >
                assignment_sprint_by_story_id[
                    dependent_story_id
                ]
            ):
                details.append(
                    "hard_dependency_sprint_violation:"
                    f"{dependent_story_id}->"
                    f"{dependency_story_id}"
                )

        overflow_warning_prefix = (
            "sprint_overflow:"
        )

        actual_overflow_warnings = [
            warning
            for warning in warnings
            if (
                isinstance(warning, str)
                and warning.startswith(
                    overflow_warning_prefix
                )
            )
        ]

        hard_dependencies: dict[
            str,
            set[str],
        ] = {
            story_id: set()
            for story_id
            in overflow_story_ids
        }

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            if (
                edge.story_id
                not in overflow_story_id_set
            ):
                continue

            hard_dependencies.setdefault(
                edge.story_id,
                set(),
            ).add(
                edge.depends_on_story_id
            )

        numeric_capacity = (
            float(sprint_capacity)
            if capacity_valid
            else 0.0
        )

        expected_overflow_warnings: list[
            str
        ] = []

        for story_id in overflow_story_ids:
            if story_id not in story_by_id:
                continue

            dependencies = hard_dependencies.get(
                story_id,
                set(),
            )

            blocked = any(
                dependency_story_id
                in overflow_story_id_set
                for dependency_story_id
                in dependencies
            )

            if blocked:
                reason = (
                    "blocked_by_unplaced_dependency"
                )

            elif numeric_capacity <= 0:
                reason = "zero_capacity"

            elif (
                float(
                    story_by_id[
                        story_id
                    ].story_points
                )
                > numeric_capacity
            ):
                reason = (
                    "story_exceeds_sprint_capacity"
                )

            else:
                reason = "capacity_exhausted"

            expected_overflow_warnings.append(
                overflow_warning_prefix
                + reason
                + ":"
                + story_id
            )

        if (
            actual_overflow_warnings
            != expected_overflow_warnings
        ):
            details.append(
                "overflow_warning_mismatch"
            )

        if details:
            raise SprintPlanningEngineError(
                code="planning_result_invalid",
                message=(
                    "Final Sprint planning result "
                    "violates certified invariants."
                ),
                details=details,
            )

    def _validate_inputs(
        self,
        *,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        planning_settings: PlanningSettingsV1,
        advice: ScrumMasterAdviceV1,
    ) -> None:
        self._validate_canonical_binding(
            backlog=backlog,
            dependency_graph=dependency_graph,
            advice=advice,
        )

        self._validate_sprint_count(
            planning_settings
        )

        story_ids = [
            story.story_id
            for story in backlog.stories
        ]

        story_id_set = set(
            story_ids
        )

        self._validate_story_readiness(
            backlog=backlog,
            story_ids=story_ids,
            story_id_set=story_id_set,
        )

        self._validate_dependency_graph(
            dependency_graph=dependency_graph,
            story_ids=story_ids,
            story_id_set=story_id_set,
        )

        self._validate_advice_references(
            advice=advice,
            story_id_set=story_id_set,
        )

    @staticmethod
    def _validate_canonical_binding(
        *,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        advice: ScrumMasterAdviceV1,
    ) -> None:
        details: list[str] = []

        if (
            dependency_graph.source_context_hash
            != backlog.source_context_hash
        ):
            details.append(
                "dependency_graph.source_context_hash"
            )

        if (
            dependency_graph.context_hash
            != backlog.context_hash
        ):
            details.append(
                "dependency_graph.context_hash"
            )

        if (
            advice.source_context_hash
            != backlog.source_context_hash
        ):
            details.append(
                "advice.source_context_hash"
            )

        if (
            advice.context_hash
            != backlog.context_hash
        ):
            details.append(
                "advice.context_hash"
            )

        if details:
            raise SprintPlanningEngineError(
                code="canonical_binding_mismatch",
                message=(
                    "Sprint planning inputs are not "
                    "bound to the same canonical context."
                ),
                details=details,
            )

    @staticmethod
    def _validate_sprint_count(
        planning_settings: PlanningSettingsV1,
    ) -> None:
        """
        Validate the resolved structural Sprint-count invariant.

        Sprint count is a release-sizing result, so a project may
        legitimately require fewer than four or more than eight Sprints.

        Parsing/coercion belongs to PlanningSettingsV1.
        """

        sprint_count = (
            planning_settings.sprint_count
        )

        if (
            type(sprint_count) is not int
            or sprint_count < MIN_SPRINTS
        ):
            raise SprintPlanningEngineError(
                code="invalid_sprint_count",
                message=(
                    "sprint_count must be "
                    "a positive integer."
                ),
                details=[
                    f"sprint_count={sprint_count!r}"
                ],
            )

    @staticmethod
    def _validate_story_readiness(
        *,
        backlog: CanonicalBacklogV1,
        story_ids: list[str],
        story_id_set: set[str],
    ) -> None:
        details: list[str] = []

        if (
            len(story_ids)
            != len(story_id_set)
        ):
            details.append(
                "duplicate_story_id"
            )

        for story in backlog.stories:
            priority = story.priority

            if (
                not isinstance(
                    priority,
                    str,
                )
                or priority
                not in _ALLOWED_PRIORITIES
            ):
                details.append(
                    "invalid_priority:"
                    f"{story.story_id}"
                )

            story_points = (
                story.story_points
            )

            if (
                type(story_points) is not int
                or story_points
                not in _ALLOWED_STORY_POINTS
            ):
                details.append(
                    "invalid_story_points:"
                    f"{story.story_id}"
                )

        if details:
            raise SprintPlanningEngineError(
                code="planning_input_not_ready",
                message=(
                    "Canonical backlog is not ready "
                    "for deterministic Sprint planning."
                ),
                details=details,
            )

    @staticmethod
    def _validate_dependency_graph(
        *,
        dependency_graph: DependencyGraphV1,
        story_ids: list[str],
        story_id_set: set[str],
    ) -> None:
        order = list(
            dependency_graph.hard_topological_order
        )

        details: list[str] = []

        if (
            len(order)
            != len(story_ids)
        ):
            details.append(
                "hard_topological_order_size_mismatch"
            )

        if (
            len(order)
            != len(set(order))
        ):
            details.append(
                "hard_topological_order_duplicate_story"
            )

        if (
            set(order)
            != story_id_set
        ):
            details.append(
                "hard_topological_order_story_set_mismatch"
            )

        if details:
            raise SprintPlanningEngineError(
                code="dependency_graph_mismatch",
                message=(
                    "Dependency graph does not match "
                    "the canonical backlog."
                ),
                details=details,
            )

        position = {
            story_id: index
            for index, story_id
            in enumerate(order)
        }

        edge_details: list[str] = []

        for edge in dependency_graph.edges:
            story_id = edge.story_id
            depends_on = (
                edge.depends_on_story_id
            )

            if (
                story_id
                not in story_id_set
            ):
                edge_details.append(
                    "unknown_story:"
                    f"{story_id}"
                )

            if (
                depends_on
                not in story_id_set
            ):
                edge_details.append(
                    "unknown_dependency:"
                    f"{depends_on}"
                )

        if edge_details:
            raise SprintPlanningEngineError(
                code="dependency_graph_mismatch",
                message=(
                    "Dependency graph references "
                    "unknown canonical stories."
                ),
                details=edge_details,
            )

        precedence_details: list[str] = []

        for edge in dependency_graph.edges:
            if (
                edge.dependency_type
                != "hard_dependency"
            ):
                continue

            story_position = position[
                edge.story_id
            ]

            dependency_position = position[
                edge.depends_on_story_id
            ]

            if (
                dependency_position
                >= story_position
            ):
                precedence_details.append(
                    "hard_dependency_precedence:"
                    f"{edge.story_id}->"
                    f"{edge.depends_on_story_id}"
                )

        if precedence_details:
            raise SprintPlanningEngineError(
                code="dependency_graph_mismatch",
                message=(
                    "Hard dependency precedence "
                    "contradicts topological order."
                ),
                details=precedence_details,
            )

    @staticmethod
    def _validate_advice_references(
        *,
        advice: ScrumMasterAdviceV1,
        story_id_set: set[str],
    ) -> None:
        details: list[str] = []

        for recommendation in (
            advice.recommendations
        ):
            for story_id in (
                recommendation.story_ids
            ):
                if (
                    story_id
                    not in story_id_set
                ):
                    details.append(
                        "unknown_advice_story:"
                        f"{story_id}"
                    )

        if details:
            raise SprintPlanningEngineError(
                code="advice_reference_mismatch",
                message=(
                    "Scrum Master advice references "
                    "unknown canonical stories."
                ),
                details=details,
            )
