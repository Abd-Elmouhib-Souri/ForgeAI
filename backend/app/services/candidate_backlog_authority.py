from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.analysis_context import (
    clean_text,
    unique_texts,
)
from app.schemas.project_management import (
    CandidateBacklogV1,
    ProjectManagementContextV1,
)


class CandidateBacklogAuthorityResultV1(BaseModel):
    """
    Deterministic authority-validation result.

    This is NOT a canonical backlog and deliberately carries no:
    - canonical IDs,
    - final priority,
    - Story Points,
    - sprint assignment,
    - lock state.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal[
        "candidate_backlog_authority_result_v1"
    ] = "candidate_backlog_authority_result_v1"

    is_valid: bool = False

    error_codes: list[str] = Field(
        default_factory=list,
    )

    errors: list[str] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )

    resolved_provenance_refs: list[str] = Field(
        default_factory=list,
    )


class CandidateBacklogAuthorityValidator:
    """
    Validate that a Product Owner candidate backlog is genuinely bound
    to the canonical ProjectManagementContextV1 that produced it.

    This layer validates authority/provenance only.

    It does NOT:
    - assign canonical backlog IDs,
    - decide MoSCoW priority,
    - assign Story Points,
    - validate dependency graphs,
    - assign sprints,
    - lock stories,
    - consume RAG/search/query/archetype intelligence.
    """

    _POSITIVE_NAMESPACES = frozenset(
        {
            "actor",
            "problem",
            "solution",
            "workflow",
            "mvp_scope",
            "constraint",
            "validated_next_action",
            "go_no_go_condition",
            "validated_risk",
            "final_recommendation",
        }
    )

    _NEGATIVE_NAMESPACE = (
        "scope_exclusion"
    )

    def validate(
        self,
        *,
        context: ProjectManagementContextV1,
        candidate: CandidateBacklogV1,
    ) -> CandidateBacklogAuthorityResultV1:

        if not isinstance(
            context,
            ProjectManagementContextV1,
        ):
            raise TypeError(
                "context must be a "
                "ProjectManagementContextV1"
            )

        if not isinstance(
            candidate,
            CandidateBacklogV1,
        ):
            raise TypeError(
                "candidate must be a "
                "CandidateBacklogV1"
            )

        error_codes: list[str] = []
        errors: list[str] = []
        warnings: list[str] = []
        resolved_refs: list[str] = []

        self._validate_hash_binding(
            context=context,
            candidate=candidate,
            error_codes=error_codes,
            errors=errors,
        )

        positive_index = (
            self._build_positive_authority_index(
                context
            )
        )

        negative_scope = {
            self._normalize_value(
                value
            )
            for value in context.scope_exclusions
            if self._normalize_value(
                value
            )
        }

        canonical_actors = set(
            positive_index.get(
                "actor",
                set(),
            )
        )

        for story in candidate.stories:

            actor_key = self._normalize_value(
                story.actor_ref
            )

            if (
                not actor_key
                or actor_key
                not in canonical_actors
            ):
                self._add_error(
                    code="unknown_actor_ref",
                    message=(
                        "Story actor_ref does not resolve "
                        "to a canonical PM context actor: "
                        f"{story.actor_ref!r}"
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

            if (
                story.source_context_hash
                !=
                context.source_context_hash
            ):
                self._add_error(
                    code=(
                        "story_source_context_hash_mismatch"
                    ),
                    message=(
                        "Story source_context_hash does not "
                        "match the PM context source hash: "
                        f"{story.candidate_key!r}"
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

        for location, reference in (
            self._candidate_provenance_refs(
                candidate
            )
        ):

            outcome = self._resolve_reference(
                reference=reference,
                positive_index=positive_index,
                negative_scope=negative_scope,
            )

            if outcome == "resolved":

                cleaned = clean_text(
                    reference
                )

                if (
                    cleaned
                    and cleaned
                    not in resolved_refs
                ):
                    resolved_refs.append(
                        cleaned
                    )

                continue

            if outcome == "negative_scope":

                self._add_error(
                    code="negative_scope_provenance",
                    message=(
                        "Excluded scope cannot be used as "
                        "positive backlog provenance at "
                        f"{location}: {reference!r}"
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

                continue

            self._add_error(
                code="unresolved_provenance_ref",
                message=(
                    "Candidate provenance reference does "
                    "not resolve against canonical PM "
                    f"context at {location}: "
                    f"{reference!r}"
                ),
                error_codes=error_codes,
                errors=errors,
            )

        covered_mvp_scope: set[str] = set()

        for _, reference in (
            self._candidate_provenance_refs(
                candidate
            )
        ):

            cleaned = clean_text(
                reference
            )

            if (
                not cleaned
                or ":" not in cleaned
            ):
                continue

            raw_namespace, raw_value = (
                cleaned.split(
                    ":",
                    1,
                )
            )

            namespace = (
                clean_text(
                    raw_namespace
                )
                .casefold()
            )

            if namespace != "mvp_scope":
                continue

            value = self._normalize_value(
                raw_value
            )

            if (
                value
                and value
                in positive_index.get(
                    "mvp_scope",
                    set(),
                )
            ):
                covered_mvp_scope.add(
                    value
                )

        missing_mvp_scope = [
            clean_text(value)
            for value in context.mvp_scope
            if (
                self._normalize_value(value)
                and self._normalize_value(value)
                not in covered_mvp_scope
            )
        ]

        if missing_mvp_scope:

            self._add_error(
                code="canonical_scope_undercovered",
                message=(
                    "Candidate backlog does not preserve "
                    "all explicit positive MVP scope "
                    "commitments: "
                    + ", ".join(
                        missing_mvp_scope
                    )
                ),
                error_codes=error_codes,
                errors=errors,
            )

        return CandidateBacklogAuthorityResultV1(
            is_valid=(
                len(
                    error_codes
                )
                ==
                0
            ),
            error_codes=error_codes,
            errors=errors,
            warnings=warnings,
            resolved_provenance_refs=(
                resolved_refs
            ),
        )

    def _validate_hash_binding(
        self,
        *,
        context: ProjectManagementContextV1,
        candidate: CandidateBacklogV1,
        error_codes: list[str],
        errors: list[str],
    ) -> None:

        if (
            candidate.source_context_hash
            !=
            context.source_context_hash
        ):
            self._add_error(
                code="source_context_hash_mismatch",
                message=(
                    "CandidateBacklog source_context_hash "
                    "does not match ProjectManagementContext."
                ),
                error_codes=error_codes,
                errors=errors,
            )

        if (
            candidate.context_hash
            !=
            context.context_hash
        ):
            self._add_error(
                code="context_hash_mismatch",
                message=(
                    "CandidateBacklog context_hash does not "
                    "match ProjectManagementContext."
                ),
                error_codes=error_codes,
                errors=errors,
            )

    def _build_positive_authority_index(
        self,
        context: ProjectManagementContextV1,
    ) -> dict[str, set[str]]:

        index: dict[str, set[str]] = {
            namespace: set()
            for namespace
            in self._POSITIVE_NAMESPACES
        }

        for actor in context.actors:

            self._index_value(
                index,
                "actor",
                actor.name,
            )

        for value in (
            list(context.problem.actors_affected)
            + [context.problem.pain, context.problem.frequency, context.problem.severity]
            + list(context.problem.current_alternatives)
            + list(context.problem.consequences)
        ):
            self._index_value(index, "problem", value)

        for value in (
            [
                context.solution.mechanism,
                context.solution.core_value,
                context.solution.delivery_mode,
            ]
            + list(context.solution.required_capabilities)
            + list(context.solution.differentiators)
        ):
            self._index_value(index, "solution", value)

        for workflow in context.priority_workflows:

            self._index_value(
                index,
                "workflow",
                workflow.name,
            )

        for value in context.mvp_scope:

            self._index_value(
                index,
                "mvp_scope",
                value,
            )

        for value in context.constraints:

            self._index_value(
                index,
                "constraint",
                value,
            )

        for value in context.validated_next_actions:

            self._index_value(
                index,
                "validated_next_action",
                value,
            )

        for value in context.go_no_go_conditions:

            self._index_value(
                index,
                "go_no_go_condition",
                value,
            )

        for value in context.validated_risks:

            self._index_value(
                index,
                "validated_risk",
                value,
            )

        if context.final_recommendation:

            self._index_value(
                index,
                "final_recommendation",
                context.final_recommendation,
            )

        return index

    def _index_value(
        self,
        index: dict[str, set[str]],
        namespace: str,
        value,
    ) -> None:

        normalized = self._normalize_value(
            value
        )

        if normalized:
            index[
                namespace
            ].add(
                normalized
            )

    def _candidate_provenance_refs(
        self,
        candidate: CandidateBacklogV1,
    ):
        """
        Yield every candidate provenance reference with a stable location.

        Parent/child graph relationships are intentionally NOT validated
        here; that belongs to BacklogPolicyEngine / dependency policies.
        """
        for epic in candidate.epics:

            for reference in epic.provenance_refs:

                yield (
                    (
                        "epic:"
                        f"{epic.candidate_key}"
                    ),
                    reference,
                )

        for feature in candidate.features:

            for reference in feature.provenance_refs:

                yield (
                    (
                        "feature:"
                        f"{feature.candidate_key}"
                    ),
                    reference,
                )

        for story in candidate.stories:

            for reference in story.provenance_refs:

                yield (
                    (
                        "story:"
                        f"{story.candidate_key}"
                    ),
                    reference,
                )

            for index, criterion in enumerate(
                story.acceptance_criteria,
                start=1,
            ):

                yield (
                    (
                        "acceptance:"
                        f"{story.candidate_key}:"
                        f"{index}"
                    ),
                    criterion.source_ref,
                )

    def _resolve_reference(
        self,
        *,
        reference,
        positive_index: dict[str, set[str]],
        negative_scope: set[str],
    ) -> str:

        cleaned = clean_text(
            reference
        )

        if (
            not cleaned
            or ":"
            not in cleaned
        ):
            return "unresolved"

        raw_namespace, raw_value = (
            cleaned.split(
                ":",
                1,
            )
        )

        namespace = (
            clean_text(
                raw_namespace
            )
            .casefold()
        )

        value = self._normalize_value(
            raw_value
        )

        if (
            not namespace
            or not value
        ):
            return "unresolved"

        if (
            namespace
            ==
            self._NEGATIVE_NAMESPACE
        ):

            if value in negative_scope:
                return "negative_scope"

            return "unresolved"

        if (
            namespace
            not in
            self._POSITIVE_NAMESPACES
        ):
            return "unresolved"

        if (
            value
            in positive_index.get(
                namespace,
                set(),
            )
        ):
            return "resolved"

        return "unresolved"

    def _normalize_value(
        self,
        value,
    ) -> str:

        return (
            clean_text(
                value
            )
            .casefold()
        )

    def _add_error(
        self,
        *,
        code: str,
        message: str,
        error_codes: list[str],
        errors: list[str],
    ) -> None:

        if code not in error_codes:
            error_codes.append(
                code
            )

        cleaned_message = clean_text(
            message
        )

        if (
            cleaned_message
            and cleaned_message
            not in errors
        ):
            errors.append(
                cleaned_message
            )


candidate_backlog_authority_validator = (
    CandidateBacklogAuthorityValidator()
)
