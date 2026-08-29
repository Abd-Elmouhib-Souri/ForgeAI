from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.project_management import (
    CandidateBacklogV1,
    CanonicalAcceptanceCriterionV1,
    CanonicalBacklogV1,
    CanonicalEpicV1,
    CanonicalFeatureV1,
    CanonicalUserStoryV1,
    ProjectManagementContextV1,
)
from app.services.candidate_backlog_authority import (
    candidate_backlog_authority_validator,
)


class BacklogPolicyResultV1(BaseModel):
    """
    Deterministic validation result for CandidateBacklogV1.

    This object is deliberately validation-only.

    It does not own:
    - canonical IDs;
    - final MoSCoW priority;
    - Story Points;
    - sprint assignment;
    - velocity or burndown;
    - architecture decisions.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "backlog_policy_result_v1"
    ] = "backlog_policy_result_v1"

    is_valid: bool

    error_codes: list[str] = Field(
        default_factory=list,
    )

    errors: list[str] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


class BacklogPolicyCanonicalizationError(ValueError):
    """
    Typed failure emitted when a candidate backlog cannot cross the
    already-certified BacklogPolicyEngine gate.

    This exception does not create fallback work items.
    """

    def __init__(
        self,
        *,
        code: str,
        errors: list[str] | None = None,
    ) -> None:

        self.code = str(
            code
            or ""
        ).strip()

        self.errors = list(
            errors
            or []
        )

        message = self.code

        if self.errors:
            message = (
                f"{message}: "
                +
                "; ".join(
                    self.errors
                )
            )

        super().__init__(
            message
        )


class BacklogPolicyEngine:
    """
    Deterministic admissibility policy for Product Owner candidates.

    CandidateBacklogAuthorityValidator owns canonical context binding.

    BacklogPolicyEngine owns:
    - candidate-key uniqueness;
    - Epic -> Feature -> Story hierarchy;
    - parent consistency;
    - dependency target existence;
    - self-dependency rejection;
    - Acceptance Criteria testability;
    - exact normalized Story duplication.

    Later deterministic layers own:
    - stable canonical IDs;
    - MoSCoW;
    - Story Points;
    - dependency DAG/cycle authority;
    - sprint planning.
    """

    def evaluate(
        self,
        context: ProjectManagementContextV1,
        candidate: CandidateBacklogV1,
    ) -> BacklogPolicyResultV1:

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

        # --------------------------------------------------------
        # 1. Canonical candidate authority is mandatory.
        # --------------------------------------------------------

        authority = (
            candidate_backlog_authority_validator.validate(
                context=context,
                candidate=candidate,
            )
        )

        if not authority.is_valid:

            self._add_error(
                code="candidate_authority_rejected",
                message=(
                    "Candidate backlog failed canonical "
                    "context authority validation."
                ),
                error_codes=error_codes,
                errors=errors,
            )

            for code in authority.error_codes:

                clean = self._clean_text(
                    code
                )

                if clean:

                    detail = (
                        "Candidate authority detail: "
                        f"{clean}"
                    )

                    if detail not in errors:
                        errors.append(
                            detail
                        )

            for warning in authority.warnings:

                clean = self._clean_text(
                    warning
                )

                if (
                    clean
                    and
                    clean not in warnings
                ):
                    warnings.append(
                        clean
                    )

            return BacklogPolicyResultV1(
                is_valid=False,
                error_codes=error_codes,
                errors=errors,
                warnings=warnings,
            )

        # --------------------------------------------------------
        # 2. Candidate-key uniqueness.
        # --------------------------------------------------------

        epic_keys = [
            epic.candidate_key
            for epic in candidate.epics
        ]

        feature_keys = [
            feature.candidate_key
            for feature in candidate.features
        ]

        story_keys = [
            story.candidate_key
            for story in candidate.stories
        ]

        self._validate_unique_keys(
            values=epic_keys,
            code="duplicate_epic_key",
            entity_name="Epic",
            error_codes=error_codes,
            errors=errors,
        )

        self._validate_unique_keys(
            values=feature_keys,
            code="duplicate_feature_key",
            entity_name="Feature",
            error_codes=error_codes,
            errors=errors,
        )

        self._validate_unique_keys(
            values=story_keys,
            code="duplicate_story_key",
            entity_name="Story",
            error_codes=error_codes,
            errors=errors,
        )

        epic_key_set = set(
            epic_keys
        )

        feature_by_key = {
            feature.candidate_key:
                feature
            for feature in candidate.features
        }

        story_key_set = set(
            story_keys
        )

        # --------------------------------------------------------
        # 3. Feature -> Epic hierarchy.
        # --------------------------------------------------------

        for feature in candidate.features:

            if (
                feature.epic_key
                not in epic_key_set
            ):

                self._add_error(
                    code="missing_parent_epic",
                    message=(
                        "Feature "
                        f"'{feature.candidate_key}' "
                        "references missing Epic "
                        f"'{feature.epic_key}'."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

        # --------------------------------------------------------
        # 4. Story -> Epic / Feature hierarchy.
        # --------------------------------------------------------

        for story in candidate.stories:

            if (
                story.epic_key
                not in epic_key_set
            ):

                self._add_error(
                    code="missing_parent_epic",
                    message=(
                        "Story "
                        f"'{story.candidate_key}' "
                        "references missing Epic "
                        f"'{story.epic_key}'."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

            parent_feature = (
                feature_by_key.get(
                    story.feature_key
                )
            )

            if parent_feature is None:

                self._add_error(
                    code="missing_parent_feature",
                    message=(
                        "Story "
                        f"'{story.candidate_key}' "
                        "references missing Feature "
                        f"'{story.feature_key}'."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

            elif (
                parent_feature.epic_key
                !=
                story.epic_key
            ):

                self._add_error(
                    code=(
                        "story_epic_feature_mismatch"
                    ),
                    message=(
                        "Story "
                        f"'{story.candidate_key}' "
                        "declares Epic "
                        f"'{story.epic_key}' "
                        "but Feature "
                        f"'{story.feature_key}' "
                        "belongs to Epic "
                        f"'{parent_feature.epic_key}'."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

        # --------------------------------------------------------
        # 5. Candidate dependency target existence.
        #
        # Cycle/DAG authority is deliberately deferred to the
        # future DependencyGraphBuilder.
        # --------------------------------------------------------

        for story in candidate.stories:

            for dependency in (
                story.candidate_dependencies
            ):

                dependency_key = (
                    self._clean_text(
                        dependency
                    )
                )

                if (
                    dependency_key
                    ==
                    story.candidate_key
                ):

                    self._add_error(
                        code="self_dependency",
                        message=(
                            "Story "
                            f"'{story.candidate_key}' "
                            "cannot depend on itself."
                        ),
                        error_codes=error_codes,
                        errors=errors,
                    )

                    continue

                if (
                    dependency_key
                    not in story_key_set
                ):

                    self._add_error(
                        code=(
                            "unknown_dependency_target"
                        ),
                        message=(
                            "Story "
                            f"'{story.candidate_key}' "
                            "references unknown dependency "
                            f"'{dependency_key}'."
                        ),
                        error_codes=error_codes,
                        errors=errors,
                    )

        # --------------------------------------------------------
        # 6. Acceptance Criteria testability.
        # --------------------------------------------------------

        for story in candidate.stories:

            has_testable = any(
                bool(
                    criterion.candidate_testable
                )
                for criterion
                in story.acceptance_criteria
            )

            if not has_testable:

                self._add_error(
                    code=(
                        "untestable_acceptance_criteria"
                    ),
                    message=(
                        "Story "
                        f"'{story.candidate_key}' "
                        "must contain at least one "
                        "testable Acceptance Criterion."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

        # --------------------------------------------------------
        # 7. Exact normalized Story duplication.
        #
        # Only normalization-equivalent duplicates belong here.
        # Broader semantic merging needs a dedicated future
        # contract before implementation.
        # --------------------------------------------------------

        seen_story_semantics: dict[
            str,
            str,
        ] = {}

        for story in candidate.stories:

            normalized_story = (
                self._normalize_semantic_text(
                    story.story
                )
            )

            if not normalized_story:
                continue

            previous_key = (
                seen_story_semantics.get(
                    normalized_story
                )
            )

            if previous_key is not None:

                self._add_error(
                    code=(
                        "duplicate_story_semantics"
                    ),
                    message=(
                        "Stories "
                        f"'{previous_key}' and "
                        f"'{story.candidate_key}' "
                        "have duplicate normalized "
                        "Story semantics."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

                continue

            seen_story_semantics[
                normalized_story
            ] = story.candidate_key

        return BacklogPolicyResultV1(
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
        )


    def canonicalize(
        self,
        context: ProjectManagementContextV1,
        candidate: CandidateBacklogV1,
    ) -> CanonicalBacklogV1:
        """
        Project one already-admissible CandidateBacklogV1 into the
        sole canonical backlog representation.

        Identity rule for this Sprint 4 stage:
        - deterministic for the same admitted backlog and structural
          order;
        - backend-controlled;
        - independent from candidate_key text as canonical identity.

        Persistent identity across future backlog revisions belongs to
        persistence/versioning/replanning and is not claimed here.
        """

        policy_result = self.evaluate(
            context=context,
            candidate=candidate,
        )

        if not policy_result.is_valid:

            raise BacklogPolicyCanonicalizationError(
                code="backlog_policy_rejected",
                errors=list(
                    policy_result.errors
                ),
            )

        # --------------------------------------------------------
        # Canonical deterministic identities.
        #
        # The input order is meaningful candidate backlog structure.
        # candidate_key is used only to resolve relationships while
        # projecting; it is never published as canonical identity.
        # --------------------------------------------------------

        epic_id_by_candidate_key = {
            epic.candidate_key:
                f"EP-{index:03d}"
            for index, epic
            in enumerate(
                candidate.epics,
                start=1,
            )
        }

        feature_id_by_candidate_key = {
            feature.candidate_key:
                f"FE-{index:03d}"
            for index, feature
            in enumerate(
                candidate.features,
                start=1,
            )
        }

        story_id_by_candidate_key = {
            story.candidate_key:
                f"US-{index:03d}"
            for index, story
            in enumerate(
                candidate.stories,
                start=1,
            )
        }

        canonical_epics = [
            CanonicalEpicV1(
                epic_id=(
                    epic_id_by_candidate_key[
                        epic.candidate_key
                    ]
                ),

                candidate_key=(
                    epic.candidate_key
                ),

                title=(
                    epic.title
                ),

                description=(
                    epic.description
                ),

                business_goal=(
                    epic.business_goal
                ),

                provenance_refs=list(
                    epic.provenance_refs
                ),
            )
            for epic
            in candidate.epics
        ]

        canonical_features = [
            CanonicalFeatureV1(
                feature_id=(
                    feature_id_by_candidate_key[
                        feature.candidate_key
                    ]
                ),

                candidate_key=(
                    feature.candidate_key
                ),

                epic_id=(
                    epic_id_by_candidate_key[
                        feature.epic_key
                    ]
                ),

                title=(
                    feature.title
                ),

                description=(
                    feature.description
                ),

                business_value=(
                    feature.business_value
                ),

                provenance_refs=list(
                    feature.provenance_refs
                ),
            )
            for feature
            in candidate.features
        ]

        acceptance_index = 1

        canonical_stories: list[
            CanonicalUserStoryV1
        ] = []

        for story in candidate.stories:

            canonical_story_id = (
                story_id_by_candidate_key[
                    story.candidate_key
                ]
            )

            canonical_acceptance: list[
                CanonicalAcceptanceCriterionV1
            ] = []

            for criterion in (
                story.acceptance_criteria
            ):

                canonical_acceptance.append(
                    CanonicalAcceptanceCriterionV1(
                        acceptance_criterion_id=(
                            f"AC-{acceptance_index:03d}"
                        ),

                        story_id=(
                            canonical_story_id
                        ),

                        statement=(
                            criterion.statement
                        ),

                        is_testable=(
                            criterion.candidate_testable
                        ),

                        source_ref=(
                            criterion.source_ref
                        ),
                    )
                )

                acceptance_index += 1

            dependency_hint_ids = [
                story_id_by_candidate_key[
                    dependency_key
                ]
                for dependency_key
                in story.candidate_dependencies
            ]

            canonical_stories.append(
                CanonicalUserStoryV1(
                    story_id=(
                        canonical_story_id
                    ),

                    candidate_key=(
                        story.candidate_key
                    ),

                    epic_id=(
                        epic_id_by_candidate_key[
                            story.epic_key
                        ]
                    ),

                    feature_id=(
                        feature_id_by_candidate_key[
                            story.feature_key
                        ]
                    ),

                    actor_ref=(
                        story.actor_ref
                    ),

                    title=(
                        story.title
                    ),

                    capability=(
                        story.capability
                    ),

                    benefit=(
                        story.benefit
                    ),

                    story=(
                        story.story
                    ),

                    business_value=(
                        story.business_value
                    ),

                    acceptance_criteria=(
                        canonical_acceptance
                    ),

                    candidate_priority=(
                        story.candidate_priority
                    ),

                    candidate_priority_rationale=(
                        story.candidate_priority_rationale
                    ),

                    priority=None,

                    candidate_complexity=(
                        story.candidate_complexity
                    ),

                    candidate_complexity_rationale=(
                        story.candidate_complexity_rationale
                    ),

                    candidate_complexity_factors=(
                        story.candidate_complexity_factors
                    ),
                    story_points=None,

                    dependencies=[],

                    dependency_hint_ids=(
                        dependency_hint_ids
                    ),

                    scope_status="in_scope",

                    locked=False,

                    provenance_refs=list(
                        story.provenance_refs
                    ),

                    source_context_hash=(
                        story.source_context_hash
                    ),

                    warnings=list(
                        story.warnings
                    ),
                )
            )

        return CanonicalBacklogV1(
            source_context_hash=(
                candidate.source_context_hash
            ),

            context_hash=(
                candidate.context_hash
            ),

            epics=(
                canonical_epics
            ),

            features=(
                canonical_features
            ),

            stories=(
                canonical_stories
            ),

            warnings=list(
                candidate.warnings
            ),
        )

    def _validate_unique_keys(
        self,
        *,
        values: list[str],
        code: str,
        entity_name: str,
        error_codes: list[str],
        errors: list[str],
    ) -> None:

        seen: set[str] = set()

        for value in values:

            key = self._clean_text(
                value
            )

            if key in seen:

                self._add_error(
                    code=code,
                    message=(
                        f"{entity_name} candidate key "
                        f"'{key}' is duplicated."
                    ),
                    error_codes=error_codes,
                    errors=errors,
                )

                continue

            seen.add(
                key
            )

    def _normalize_semantic_text(
        self,
        value,
    ) -> str:

        text = unicodedata.normalize(
            "NFKC",
            self._clean_text(
                value
            ),
        )

        text = text.casefold()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _clean_text(
        self,
        value,
    ) -> str:

        return str(
            value
            or ""
        ).strip()

    def _add_error(
        self,
        *,
        code: str,
        message: str,
        error_codes: list[str],
        errors: list[str],
    ) -> None:

        clean_code = self._clean_text(
            code
        )

        clean_message = self._clean_text(
            message
        )

        if (
            clean_code
            and
            clean_code not in error_codes
        ):
            error_codes.append(
                clean_code
            )

        if (
            clean_message
            and
            clean_message not in errors
        ):
            errors.append(
                clean_message
            )


backlog_policy_engine = (
    BacklogPolicyEngine()
)