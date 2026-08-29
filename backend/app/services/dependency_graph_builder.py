from __future__ import annotations

import heapq
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_management import (
    CanonicalBacklogV1,
)


DependencyType = Literal[
    "hard_dependency",
    "soft_dependency",
]


class DependencyEdgeV1(BaseModel):
    """
    One canonical directed dependency edge.

    Direction semantics:

        story_id
            depends on
        depends_on_story_id
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    story_id: str
    depends_on_story_id: str
    dependency_type: DependencyType


class DependencyGraphV1(BaseModel):
    """
    Deterministic dependency graph suitable for downstream
    Sprint planning.

    Only hard dependencies constrain the topological order.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: Literal[
        "dependency_graph_v1"
    ] = "dependency_graph_v1"

    source_context_hash: str
    context_hash: str

    edges: list[
        DependencyEdgeV1
    ] = Field(
        default_factory=list
    )

    hard_topological_order: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )


class DependencyGraphResultV1(BaseModel):
    """
    Canonical backlog projection plus deterministic graph.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    backlog: CanonicalBacklogV1
    graph: DependencyGraphV1


class DependencyGraphBuilderError(ValueError):
    """
    Typed fail-closed dependency authority error.
    """

    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        self.code = code

        super().__init__(
            message
        )


class DependencyGraphBuilder:
    """
    Canonical Sprint 4 dependency authority.

    V1 authority:

    - story.dependencies
        -> hard_dependency

    - story.dependency_hint_ids
        -> soft_dependency only

    Hard dependencies always win when the same relation appears
    on both surfaces.

    The builder is deliberately local and deterministic.
    It does not use LLMs, RAG, Web search, country rules,
    domain rules, priority logic, Story Point logic or
    sprint-assignment logic.
    """

    def build(
        self,
        backlog: CanonicalBacklogV1,
    ) -> DependencyGraphResultV1:
        story_ids = {
            story.story_id
            for story in backlog.stories
        }

        hard_pairs: set[
            tuple[str, str]
        ] = set()

        soft_pairs: set[
            tuple[str, str]
        ] = set()

        stories = sorted(
            backlog.stories,
            key=lambda story: story.story_id,
        )

        for story in stories:
            story_id = story.story_id

            hard_targets = sorted(
                set(
                    story.dependencies
                    or []
                )
            )

            soft_targets = sorted(
                set(
                    story.dependency_hint_ids
                    or []
                )
            )

            for target_id in hard_targets:
                self._validate_reference(
                    story_id=story_id,
                    target_id=target_id,
                    story_ids=story_ids,
                )

                hard_pairs.add(
                    (
                        story_id,
                        target_id,
                    )
                )

            for target_id in soft_targets:
                self._validate_reference(
                    story_id=story_id,
                    target_id=target_id,
                    story_ids=story_ids,
                )

                pair = (
                    story_id,
                    target_id,
                )

                if pair in hard_pairs:
                    continue

                soft_pairs.add(
                    pair
                )

        # Hard authority dominates an equivalent soft hint,
        # regardless of the original story/input ordering.
        soft_pairs.difference_update(
            hard_pairs
        )

        hard_order = (
            self._hard_topological_order(
                story_ids=story_ids,
                hard_pairs=hard_pairs,
            )
        )

        edges: list[
            DependencyEdgeV1
        ] = []

        for (
            story_id,
            target_id,
        ) in hard_pairs:
            edges.append(
                DependencyEdgeV1(
                    story_id=story_id,
                    depends_on_story_id=target_id,
                    dependency_type=(
                        "hard_dependency"
                    ),
                )
            )

        for (
            story_id,
            target_id,
        ) in soft_pairs:
            edges.append(
                DependencyEdgeV1(
                    story_id=story_id,
                    depends_on_story_id=target_id,
                    dependency_type=(
                        "soft_dependency"
                    ),
                )
            )

        edges.sort(
            key=lambda edge: (
                edge.story_id,
                edge.depends_on_story_id,
                0
                if edge.dependency_type
                == "hard_dependency"
                else 1,
            )
        )

        graph = DependencyGraphV1(
            source_context_hash=(
                backlog.source_context_hash
            ),
            context_hash=(
                backlog.context_hash
            ),
            edges=edges,
            hard_topological_order=(
                hard_order
            ),
            warnings=[],
        )

        return DependencyGraphResultV1(
            backlog=backlog.model_copy(
                deep=True
            ),
            graph=graph,
        )

    @staticmethod
    def _validate_reference(
        *,
        story_id: str,
        target_id: str,
        story_ids: set[str],
    ) -> None:
        if target_id == story_id:
            raise DependencyGraphBuilderError(
                "self_dependency",
                (
                    f"Story '{story_id}' cannot "
                    "depend on itself."
                ),
            )

        if target_id not in story_ids:
            raise DependencyGraphBuilderError(
                "unknown_dependency_target",
                (
                    f"Story '{story_id}' references "
                    "unknown dependency target "
                    f"'{target_id}'."
                ),
            )

    @staticmethod
    def _hard_topological_order(
        *,
        story_ids: set[str],
        hard_pairs: set[
            tuple[str, str]
        ],
    ) -> list[str]:
        """
        Deterministic Kahn topological sort.

        A pair:

            (story_id, depends_on_story_id)

        means:

            depends_on_story_id
                must precede
            story_id

        Lexical story_id ordering is the deterministic tie-break.
        """

        indegree = {
            story_id: 0
            for story_id in story_ids
        }

        dependents = {
            story_id: set()
            for story_id in story_ids
        }

        for (
            story_id,
            target_id,
        ) in hard_pairs:
            if (
                story_id
                not in dependents[target_id]
            ):
                dependents[
                    target_id
                ].add(
                    story_id
                )

                indegree[
                    story_id
                ] += 1

        ready = [
            story_id
            for story_id, degree
            in indegree.items()
            if degree == 0
        ]

        heapq.heapify(
            ready
        )

        order: list[str] = []

        while ready:
            current = heapq.heappop(
                ready
            )

            order.append(
                current
            )

            for dependent in sorted(
                dependents[current]
            ):
                indegree[
                    dependent
                ] -= 1

                if (
                    indegree[
                        dependent
                    ]
                    == 0
                ):
                    heapq.heappush(
                        ready,
                        dependent,
                    )

        if len(order) != len(story_ids):
            raise DependencyGraphBuilderError(
                "hard_dependency_cycle",
                (
                    "Hard dependency graph contains "
                    "at least one cycle."
                ),
            )

        return order