from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.project_management import (
    CanonicalBacklogV1,
    CanonicalUserStoryV1,
    ProjectManagementContextV1,
)


MoSCoWPriority = Literal[
    "Must",
    "Should",
    "Could",
    "Won't",
]


class MoSCoWPriorityDecisionV1(BaseModel):
    """
    Explainable deterministic priority decision for one canonical
    User Story.

    This object records why the policy selected a priority. It does
    not own Story Points, dependencies, sprint assignment or
    architecture.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    story_id: str

    priority: MoSCoWPriority

    reason_codes: list[str] = Field(
        default_factory=list,
    )

    evidence_refs: list[str] = Field(
        default_factory=list,
    )


class MoSCoWPriorityResultV1(BaseModel):
    """
    Result of deterministic MoSCoW prioritization.

    `backlog` is a copied CanonicalBacklogV1 whose only policy-owned
    Story field changed by this service is `priority`.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "moscow_priority_result_v1"
    ] = "moscow_priority_result_v1"

    backlog: CanonicalBacklogV1

    decisions: list[
        MoSCoWPriorityDecisionV1
    ] = Field(
        default_factory=list,
    )

    must_ratio: float = 0.0

    warnings: list[str] = Field(
        default_factory=list,
    )


class MoSCoWPriorityPolicyError(ValueError):
    """
    Typed fail-closed error for priority-policy binding failures.
    """

    def __init__(
        self,
        *,
        code: str,
        story_id: str = "",
    ) -> None:

        self.code = str(
            code
            or ""
        ).strip()

        self.story_id = str(
            story_id
            or ""
        ).strip()

        message = self.code

        if self.story_id:

            message = (
                f"{message}: "
                f"{self.story_id}"
            )

        super().__init__(
            message
        )


class MoSCoWPriorityPolicy:
    """
    Deterministic MoSCoW authority for CanonicalBacklogV1.

    V1 authority is deliberately narrow.

    Story-level canonical provenance is authoritative:

      workflow + mvp_scope -> Must
      workflow OR mvp_scope -> Should
      other canonical in-scope support -> Could

    Won't is not fabricated because CanonicalUserStoryV1 currently
    represents admitted in-scope Stories only.

    Candidate priority remains advisory and is intentionally ignored
    by the final priority decision.

    No lexical scoring, LLM, RAG, web search or archetype inference is
    used here.
    """

    _MUST_SOFT_CAP = 0.50

    def apply(
        self,
        context: ProjectManagementContextV1,
        backlog: CanonicalBacklogV1,
    ) -> MoSCoWPriorityResultV1:

        self._validate_binding(
            context=context,
            backlog=backlog,
        )

        prioritized_stories: list[
            CanonicalUserStoryV1
        ] = []

        decisions: list[
            MoSCoWPriorityDecisionV1
        ] = []

        must_count = 0

        for story in backlog.stories:

            (
                priority,
                reason_codes,
                evidence_refs,
            ) = self._decide_story(
                story
            )

            if priority == "Must":
                must_count += 1

            prioritized_stories.append(
                story.model_copy(
                    update={
                        "priority":
                            priority,
                    },
                    deep=True,
                )
            )

            decisions.append(
                MoSCoWPriorityDecisionV1(
                    story_id=(
                        story.story_id
                    ),

                    priority=priority,

                    reason_codes=(
                        reason_codes
                    ),

                    evidence_refs=(
                        evidence_refs
                    ),
                )
            )

        story_count = len(
            prioritized_stories
        )

        must_ratio = (
            must_count
            /
            story_count
            if story_count
            else 0.0
        )

        policy_warnings: list[str] = []

        if (
            story_count
            and
            must_ratio
            >
            self._MUST_SOFT_CAP
        ):

            policy_warnings.append(
                "must_overload"
            )

        prioritized_backlog = (
            backlog.model_copy(
                update={
                    "stories":
                        prioritized_stories,
                },
                deep=True,
            )
        )

        return MoSCoWPriorityResultV1(
            backlog=(
                prioritized_backlog
            ),

            decisions=(
                decisions
            ),

            must_ratio=(
                must_ratio
            ),

            warnings=(
                policy_warnings
            ),
        )

    @staticmethod
    def _namespace(
        ref: str,
    ) -> str:

        text = str(
            ref
            or ""
        ).strip()

        if ":" not in text:
            return ""

        namespace, _ = text.split(
            ":",
            1,
        )

        return (
            namespace
            .strip()
            .casefold()
        )

    def _decide_story(
        self,
        story: CanonicalUserStoryV1,
    ) -> tuple[
        MoSCoWPriority,
        list[str],
        list[str],
    ]:

        refs = [
            str(ref).strip()
            for ref
            in story.provenance_refs
            if str(ref).strip()
        ]

        workflow_refs = [
            ref
            for ref
            in refs
            if self._namespace(ref)
            ==
            "workflow"
        ]

        mvp_refs = [
            ref
            for ref
            in refs
            if self._namespace(ref)
            ==
            "mvp_scope"
        ]

        if (
            workflow_refs
            and
            mvp_refs
        ):

            return (
                "Must",
                [
                    "priority_workflow",
                    "mvp_requirement",
                ],
                self._ordered_unique(
                    [
                        *workflow_refs,
                        *mvp_refs,
                    ]
                ),
            )

        if workflow_refs:

            return (
                "Should",
                [
                    "priority_workflow",
                ],
                self._ordered_unique(
                    workflow_refs
                ),
            )

        if mvp_refs:

            return (
                "Should",
                [
                    "mvp_requirement",
                ],
                self._ordered_unique(
                    mvp_refs
                ),
            )

        # Current CanonicalUserStoryV1 only admits in-scope Stories.
        #
        # Supporting canonical work remains Could. We intentionally
        # do not manufacture Won't from missing evidence.
        return (
            "Could",
            [
                "canonical_in_scope",
            ],
            self._ordered_unique(
                refs
            ),
        )

    @staticmethod
    def _ordered_unique(
        values: list[str],
    ) -> list[str]:

        seen: set[str] = set()

        result: list[str] = []

        for value in values:

            text = str(
                value
                or ""
            ).strip()

            if (
                not text
                or
                text in seen
            ):
                continue

            seen.add(
                text
            )

            result.append(
                text
            )

        return result

    @staticmethod
    def _validate_binding(
        *,
        context: ProjectManagementContextV1,
        backlog: CanonicalBacklogV1,
    ) -> None:

        if (
            backlog.context_hash
            !=
            context.context_hash
        ):

            raise MoSCoWPriorityPolicyError(
                code=(
                    "context_hash_mismatch"
                ),
            )

        if (
            backlog.source_context_hash
            !=
            context.source_context_hash
        ):

            raise MoSCoWPriorityPolicyError(
                code=(
                    "source_context_hash_mismatch"
                ),
            )

        for story in backlog.stories:

            if (
                story.source_context_hash
                !=
                context.source_context_hash
            ):

                raise MoSCoWPriorityPolicyError(
                    code=(
                        "source_context_hash_mismatch"
                    ),

                    story_id=(
                        story.story_id
                    ),
                )