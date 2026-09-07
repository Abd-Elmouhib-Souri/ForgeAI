from __future__ import annotations

from typing import (
    Dict,
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.analysis_context import (
    ActorContext,
    ProblemContext,
    SolutionContext,
    TransactionUnitContext,
    WorkflowContext,
    clean_text,
    unique_texts,
)


class ProjectManagementContextV1(BaseModel):
    """
    Canonical planning input for ForgeAI Sprint 4.

    This model is deliberately narrower than ProjectContextPacketV3.

    It contains only facts and boundaries that are allowed to influence
    project-management planning.

    Archetype, search, RAG and query vocabulary are deliberately excluded
    from planning authority.

    Hashes are populated by the deterministic context builder.
    The schema itself never fabricates them.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "project_management_context_v1"
    ] = "project_management_context_v1"

    source_context_schema_version: Literal[
        "project_context_v3"
    ] = "project_context_v3"

    # --------------------------------------------------------
    # Project identity
    # --------------------------------------------------------

    project_id: str = ""
    project_name: str = ""
    language: str = ""
    target_region: str = ""
    industry: str = ""

    # --------------------------------------------------------
    # Canonical Sprint 3 project facts
    # --------------------------------------------------------

    problem: ProblemContext = Field(
        default_factory=ProblemContext,
    )

    solution: SolutionContext = Field(
        default_factory=SolutionContext,
    )

    actors: List[ActorContext] = Field(
        default_factory=list,
    )

    primary_user_actor_names: List[str] = Field(
        default_factory=list,
    )

    payer_actor_names: List[str] = Field(
        default_factory=list,
    )

    decision_maker_actor_names: List[str] = Field(
        default_factory=list,
    )

    partner_actor_names: List[str] = Field(
        default_factory=list,
    )

    blocker_actor_names: List[str] = Field(
        default_factory=list,
    )

    priority_workflows: List[WorkflowContext] = Field(
        default_factory=list,
    )

    transaction_unit: TransactionUnitContext = Field(
        default_factory=TransactionUnitContext,
    )

    # --------------------------------------------------------
    # Product / MVP semantic boundaries
    # --------------------------------------------------------

    mvp_scope: List[str] = Field(
        default_factory=list,
    )

    scope_exclusions: List[str] = Field(
        default_factory=list,
    )

    # --------------------------------------------------------
    # Operational requirements
    # --------------------------------------------------------

    input_data: List[str] = Field(
        default_factory=list,
    )

    output_decision: List[str] = Field(
        default_factory=list,
    )

    human_oversight: List[str] = Field(
        default_factory=list,
    )

    maintenance_model: List[str] = Field(
        default_factory=list,
    )

    deployment_environment: List[str] = Field(
        default_factory=list,
    )

    success_metrics: List[str] = Field(
        default_factory=list,
    )

    business_model_hypotheses: List[str] = Field(
        default_factory=list,
    )

    constraints: List[str] = Field(
        default_factory=list,
    )

    regulatory_flags: List[str] = Field(
        default_factory=list,
    )

    # --------------------------------------------------------
    # Clarification / uncertainty authority
    # --------------------------------------------------------

    clarification_facts: Dict[str, str] = Field(
        default_factory=dict,
    )

    assumptions: List[str] = Field(
        default_factory=list,
    )

    unknowns: List[str] = Field(
        default_factory=list,
    )

    warnings: List[str] = Field(
        default_factory=list,
    )

    # --------------------------------------------------------
    # Validated Sprint 3 outputs.
    #
    # Empty means unknown / not supplied by an explicitly certified
    # downstream authority.
    # --------------------------------------------------------

    decision_source: str = ""

    decision_status: Literal[
        "",
        "completed",
        "completed_with_fallback",
    ] = ""

    decision_source: str = ""

    decision_status: Literal[
        "",
        "completed",
        "completed_with_fallback",
    ] = ""

    validated_risks: List[str] = Field(
        default_factory=list,
    )

    validated_next_actions: List[str] = Field(
        default_factory=list,
    )

    go_no_go_conditions: List[str] = Field(
        default_factory=list,
    )

    canonical_verdict_code: str = ""

    final_recommendation: str = ""

    final_recommendation: str = ""

    # --------------------------------------------------------
    # Negative domain guardrail
    # --------------------------------------------------------

    forbidden_adjacent_domains: List[str] = Field(
        default_factory=list,
    )

    # --------------------------------------------------------
    # Deterministic provenance.
    #
    # Computed by the future builder, never by this schema.
    # --------------------------------------------------------

    source_context_hash: str = ""
    context_hash: str = ""

    @field_validator(
        "primary_user_actor_names",
        "payer_actor_names",
        "decision_maker_actor_names",
        "partner_actor_names",
        "blocker_actor_names",
        "mvp_scope",
        "scope_exclusions",
        "input_data",
        "output_decision",
        "human_oversight",
        "maintenance_model",
        "deployment_environment",
        "success_metrics",
        "business_model_hypotheses",
        "constraints",
        "regulatory_flags",
        "assumptions",
        "unknowns",
        "warnings",
        "validated_risks",
        "validated_next_actions",
        "go_no_go_conditions",
        "forbidden_adjacent_domains",
        mode="before",
    )
    @classmethod
    def normalize_string_lists(
        cls,
        value,
    ):
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            values = [
                value
            ]
        else:
            values = list(
                value
            )

        return unique_texts(
            clean_text(item)
            for item in values
            if clean_text(item)
        )

    @field_validator(
        "clarification_facts",
        mode="before",
    )
    @classmethod
    def normalize_clarification_facts(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            return {}

        output: Dict[str, str] = {}

        for raw_key, raw_value in value.items():

            key = clean_text(
                raw_key
            )

            item = clean_text(
                raw_value
            )

            if (
                not key
                or not item
            ):
                continue

            output[key] = item

        return output

class ProjectManagementDecisionProjectionV1(BaseModel):
    """
    Narrow deterministic projection of the canonical Sprint 3
    committee decision for Sprint 4 planning.

    Source authority:
        debate_room.judge only.

    This schema does not read Startup Score, Final Report,
    Evidence Ledger, RAG, search results or raw analysis_data.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "project_management_decision_projection_v1"
    ] = "project_management_decision_projection_v1"

    decision_source: str = ""

    decision_status: Literal[
        "",
        "completed",
        "completed_with_fallback",
    ] = ""

    canonical_verdict_code: str = ""

    validated_risks: List[str] = Field(
        default_factory=list,
    )

    validated_next_actions: List[str] = Field(
        default_factory=list,
    )

    go_no_go_conditions: List[str] = Field(
        default_factory=list,
    )

    final_recommendation: str = ""

    @field_validator(
        "validated_risks",
        "validated_next_actions",
        "go_no_go_conditions",
        mode="before",
    )
    @classmethod
    def normalize_decision_lists(
        cls,
        value,
    ):
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            values = [
                value
            ]
        else:
            values = list(
                value
            )

        return unique_texts(
            clean_text(item)
            for item in values
            if clean_text(item)
        )


# =====================================================================
# Sprint 4 ? Product Owner candidate backlog contracts
# =====================================================================
#
# These models describe advisory Product Owner proposals only.
#
# They deliberately do NOT own:
#   - canonical backlog IDs,
#   - final MoSCoW priority,
#   - Story Points,
#   - sprint assignment,
#   - lock state,
#   - architecture or technology decisions.
#
# Canonicalization belongs to the deterministic BacklogPolicyEngine
# and later planning policies.
# =====================================================================


def _candidate_required_text(
    value,
    *,
    field_name: str,
) -> str:
    text = clean_text(
        value
    )

    if not text:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    return text


def _candidate_optional_texts(
    value,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        values = [
            value
        ]

    elif isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        values = list(
            value
        )

    else:
        raise ValueError(
            "value must be a string or list of strings"
        )

    return unique_texts(
        clean_text(item)
        for item in values
        if clean_text(item)
    )


def _candidate_required_refs(
    value,
) -> list[str]:
    refs = _candidate_optional_texts(
        value
    )

    if not refs:
        raise ValueError(
            "provenance_refs must contain "
            "at least one canonical reference"
        )

    return refs


def _candidate_sha256_hex(
    value,
) -> str:
    text = clean_text(
        value
    )

    if (
        len(text) != 64
        or any(
            character
            not in
            "0123456789abcdefABCDEF"
            for character in text
        )
    ):
        raise ValueError(
            "value must be a 64-character "
            "SHA-256 hexadecimal digest"
        )

    return text.lower()


class CandidateAcceptanceCriterionV1(BaseModel):
    """
    Advisory acceptance criterion proposed by the Product Owner.

    It intentionally has no canonical AC identifier.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    statement: str

    candidate_testable: bool = True

    source_ref: str

    @field_validator(
        "statement",
        mode="before",
    )
    @classmethod
    def normalize_statement(
        cls,
        value,
    ):
        return _candidate_required_text(
            value,
            field_name="statement",
        )

    @field_validator(
        "source_ref",
        mode="before",
    )
    @classmethod
    def normalize_source_ref(
        cls,
        value,
    ):
        return _candidate_required_text(
            value,
            field_name="source_ref",
        )


class CandidateEpicV1(BaseModel):
    """
    Product Owner epic proposal.

    candidate_key is local to the candidate graph and is not a
    canonical EP-xxx identifier.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    candidate_key: str

    title: str

    description: str

    business_goal: str

    # Required intentionally.
    # Missing provenance must fail validation.
    provenance_refs: list[str]

    @field_validator(
        "candidate_key",
        "title",
        "description",
        "business_goal",
        mode="before",
    )
    @classmethod
    def normalize_required_strings(
        cls,
        value,
        info,
    ):
        return _candidate_required_text(
            value,
            field_name=info.field_name,
        )

    @field_validator(
        "provenance_refs",
        mode="before",
    )
    @classmethod
    def normalize_provenance_refs(
        cls,
        value,
    ):
        return _candidate_required_refs(
            value
        )


class CandidateFeatureV1(BaseModel):
    """
    Product Owner feature proposal.

    epic_key references a candidate epic, never a canonical epic ID.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    candidate_key: str

    epic_key: str

    title: str

    description: str

    business_value: str

    # Required intentionally.
    provenance_refs: list[str]

    @field_validator(
        "candidate_key",
        "epic_key",
        "title",
        "description",
        "business_value",
        mode="before",
    )
    @classmethod
    def normalize_required_strings(
        cls,
        value,
        info,
    ):
        return _candidate_required_text(
            value,
            field_name=info.field_name,
        )

    @field_validator(
        "provenance_refs",
        mode="before",
    )
    @classmethod
    def normalize_provenance_refs(
        cls,
        value,
    ):
        return _candidate_required_refs(
            value
        )


class CandidateComplexityFactorsV1(BaseModel):
    """
    Structured advisory complexity input proposed by the AI Product Owner.

    These factors describe candidate complexity only.

    They do NOT own:
    - final Story Points,
    - split decisions,
    - final priority,
    - sprint assignment,
    - dependencies,
    - architecture decisions.

    Final Fibonacci authority belongs to StoryPointPolicy.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    business_logic: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    integration_complexity: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    data_complexity: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    ui_complexity: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    security: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    external_dependency: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    uncertainty: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    testing_burden: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    regulatory_risk: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]

    hardware_dependency: Literal[
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ]


class CandidateUserStoryV1(BaseModel):
    """
    Advisory Product Owner story proposal.

    Priority, complexity and dependencies are candidate suggestions.

    Final priority, Story Points, dependency authority, canonical IDs
    and sprint assignment belong to deterministic Sprint 4 policies.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    candidate_key: str

    epic_key: str

    feature_key: str

    actor_ref: str

    title: str

    capability: str

    benefit: str

    story: str

    business_value: str

    # Required intentionally.
    # A story without acceptance criteria is not a valid candidate.
    acceptance_criteria: list[
        CandidateAcceptanceCriterionV1
    ]

    candidate_priority: str

    candidate_priority_rationale: str

    candidate_complexity: str

    candidate_complexity_rationale: str

    # Required structured advisory input for the future
    # deterministic StoryPointPolicy.
    candidate_complexity_factors: CandidateComplexityFactorsV1

    candidate_dependencies: list[str] = Field(
        default_factory=list,
    )

    # Required intentionally.
    provenance_refs: list[str]

    source_context_hash: str

    warnings: list[str] = Field(
        default_factory=list,
    )

    @field_validator(
        "candidate_key",
        "epic_key",
        "feature_key",
        "actor_ref",
        "title",
        "capability",
        "benefit",
        "story",
        "business_value",
        "candidate_priority_rationale",
        "candidate_complexity_rationale",
        mode="before",
    )
    @classmethod
    def normalize_required_strings(
        cls,
        value,
        info,
    ):
        return _candidate_required_text(
            value,
            field_name=info.field_name,
        )

    @field_validator(
        "candidate_priority",
        "candidate_complexity",
        mode="before",
    )
    @classmethod
    def normalize_candidate_labels(
        cls,
        value,
        info,
    ):
        text = _candidate_required_text(
            value,
            field_name=info.field_name,
        )

        return text.casefold()

    @field_validator(
        "acceptance_criteria",
        mode="before",
    )
    @classmethod
    def require_acceptance_criteria(
        cls,
        value,
    ):
        if value is None:
            raise ValueError(
                "acceptance_criteria must contain "
                "at least one criterion"
            )

        if isinstance(
            value,
            (
                str,
                bytes,
                dict,
            ),
        ):
            raise ValueError(
                "acceptance_criteria must be a list"
            )

        values = list(
            value
        )

        if not values:
            raise ValueError(
                "acceptance_criteria must contain "
                "at least one criterion"
            )

        return values

    @field_validator(
        "candidate_dependencies",
        "warnings",
        mode="before",
    )
    @classmethod
    def normalize_optional_lists(
        cls,
        value,
    ):
        return _candidate_optional_texts(
            value
        )

    @field_validator(
        "provenance_refs",
        mode="before",
    )
    @classmethod
    def normalize_provenance_refs(
        cls,
        value,
    ):
        return _candidate_required_refs(
            value
        )

    @field_validator(
        "source_context_hash",
        mode="before",
    )
    @classmethod
    def normalize_source_context_hash(
        cls,
        value,
    ):
        return _candidate_sha256_hex(
            value
        )


class CandidateBacklogV1(BaseModel):
    """
    Strict structured-output contract for the AI Product Owner.

    This object remains candidate-only until the deterministic
    BacklogPolicyEngine validates and canonicalizes it.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "candidate_backlog_v1"
    ] = "candidate_backlog_v1"

    source_context_hash: str

    context_hash: str

    epics: list[
        CandidateEpicV1
    ] = Field(
        default_factory=list,
    )

    features: list[
        CandidateFeatureV1
    ] = Field(
        default_factory=list,
    )

    stories: list[
        CandidateUserStoryV1
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )

    @field_validator(
        "source_context_hash",
        "context_hash",
        mode="before",
    )
    @classmethod
    def normalize_hashes(
        cls,
        value,
    ):
        return _candidate_sha256_hex(
            value
        )

    @field_validator(
        "warnings",
        mode="before",
    )
    @classmethod
    def normalize_warnings(
        cls,
        value,
    ):
        return _candidate_optional_texts(
            value
        )

# =====================================================================
# Sprint 4 ? Canonical Product Backlog
# =====================================================================
#
# BacklogPolicyEngine is the sole canonical backlog authority.
#
# Candidate Product Owner values remain advisory where explicitly
# represented below. Later deterministic policies own final priority,
# Story Points and dependency-graph decisions.
# =====================================================================


class CanonicalAcceptanceCriterionV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    acceptance_criterion_id: str
    story_id: str
    statement: str
    is_testable: bool
    source_ref: str


class CanonicalEpicV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    epic_id: str
    candidate_key: str

    title: str
    description: str
    business_goal: str

    provenance_refs: list[str]


class CanonicalFeatureV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    feature_id: str
    candidate_key: str

    epic_id: str

    title: str
    description: str
    business_value: str

    provenance_refs: list[str]


class CanonicalUserStoryV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    story_id: str
    candidate_key: str

    epic_id: str
    feature_id: str

    actor_ref: str

    title: str
    capability: str
    benefit: str
    story: str
    business_value: str

    acceptance_criteria: list[
        CanonicalAcceptanceCriterionV1
    ]

    # Product Owner advisory signal.
    candidate_priority: str
    candidate_priority_rationale: str

    # Final MoSCoW authority belongs to the later MoSCoWPolicy.
    priority: str | None = None

    # Product Owner advisory signal.
    candidate_complexity: str
    candidate_complexity_rationale: str

    # Required structured advisory input for the future
    # deterministic StoryPointPolicy.
    candidate_complexity_factors: CandidateComplexityFactorsV1

    # Final Fibonacci authority belongs to StoryPointPolicy.
    story_points: int | None = None

    # Final dependency graph remains empty until
    # DependencyGraphBuilder establishes canonical graph semantics.
    dependencies: list[str] = Field(
        default_factory=list,
    )

    # Candidate dependencies may be preserved only as canonical-ID
    # hints. They are NOT yet hard/soft canonical dependencies.
    dependency_hint_ids: list[str] = Field(
        default_factory=list,
    )

    scope_status: Literal[
        "in_scope"
    ] = "in_scope"

    locked: bool = False

    provenance_refs: list[str]
    source_context_hash: str

    warnings: list[str] = Field(
        default_factory=list,
    )


class CanonicalBacklogV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "canonical_backlog_v1"
    ] = "canonical_backlog_v1"

    source_context_hash: str
    context_hash: str

    epics: list[
        CanonicalEpicV1
    ] = Field(
        default_factory=list,
    )

    features: list[
        CanonicalFeatureV1
    ] = Field(
        default_factory=list,
    )

    stories: list[
        CanonicalUserStoryV1
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )
class PlanningSettingsV1(BaseModel):
    """
    Shared Sprint 4 planning configuration input.

    This model carries configuration only.

    It does not own:
    - final sprint assignments;
    - backlog priority;
    - Story Points;
    - dependency decisions;
    - Velocity calculation;
    - Burndown calculation;
    - planner output;
    - execution metrics.

    Detailed value-policy validation belongs to the dedicated
    PlanningSettings / SprintPlanningEngine authority layers.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    # Release sizing ownership.
    # auto   -> ForgeAI recalculates the required Sprint count.
    # manual -> the explicit user count is preserved.
    sprint_count_mode: Literal["auto", "manual"] = "auto"

    sprint_count: int

    # Release cadence ownership.
    # auto   -> SprintCadenceAdvisor resolves one release-level cadence.
    # manual -> the explicit user duration is preserved.
    sprint_duration_mode: Literal["auto", "manual"] = "auto"

    sprint_duration_days: int = 14

    planned_velocity: float

    team_size: int

    capacity_adjustment: float

    # ISO-compatible date representation.
    # Detailed date semantics are intentionally deferred to the
    # dedicated PlanningSettings validation layer.
    start_date: str

    # Configurable working-day identifiers.
    # Detailed allowed-value semantics are intentionally deferred.
    working_days: list[int]
class ScrumMasterRecommendationV1(BaseModel):
    """
    One structured AI Scrum Master recommendation.

    This object is advisory only.

    It may identify:
    - split opportunities;
    - sequencing concerns;
    - delivery risks;
    - overload risks;
    - parallelization opportunities;
    - critical dependencies.

    It does not own:
    - final priority;
    - Story Points;
    - dependency mutations;
    - sprint assignment;
    - backlog capabilities;
    - architecture;
    - Velocity;
    - Burndown.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    recommendation_type: Literal[
        "split",
        "sequencing",
        "risk",
        "overload",
        "parallelization",
        "critical_dependency",
    ]

    story_ids: list[str]

    rationale: str


class ScrumMasterAdviceV1(BaseModel):
    """
    Canonically-bound advisory output from the AI Scrum Master.

    This envelope contains recommendations only.

    SprintPlanningEngine remains the deterministic authority for
    final sprint placement and planning decisions.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: Literal[
        "scrum_master_advice_v1"
    ] = "scrum_master_advice_v1"

    source_context_hash: str

    context_hash: str

    recommendations: list[
        ScrumMasterRecommendationV1
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


# =====================================================================
# Sprint 4 - Durable plan, metrics and public API contracts
# =====================================================================


class SprintMetricV1(BaseModel):
    """Read-only planned metrics for one Sprint.

    ``actual_velocity`` deliberately remains unknown until delivery data is
    explicitly recorded by a future execution authority.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    sprint_number: int
    planned_story_points: int = 0
    planned_story_count: int = 0
    actual_velocity: Optional[float] = None


class ProjectManagementMetricsV1(BaseModel):
    """Deterministic planning metrics; no execution facts are inferred."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: Literal["project_management_metrics_v1"] = (
        "project_management_metrics_v1"
    )

    planned_velocity: float
    projected_velocity: float
    actual_velocity: Optional[float] = None
    total_story_points: int = 0
    assigned_story_points: int = 0
    overflow_story_points: int = 0
    sprint_metrics: list[SprintMetricV1] = Field(default_factory=list)
    ideal_burndown: list[float] = Field(default_factory=list)
    planned_burndown: list[float] = Field(default_factory=list)
    actual_burndown: Optional[list[float]] = None


class ReleasePlanningMetadataV1(BaseModel):
    """
    Durable projection of release-level planning decisions.

    This object does not own Story Point accounting.
    ProjectManagementMetricsV1 remains authoritative for total,
    assigned and overflow Story Points.

    Recommendation fields are optional because manual modes and
    deterministic replans must never fabricate recommendation
    provenance that was not actually produced by its authority.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: Literal[
        "release_planning_metadata_v1"
    ] = "release_planning_metadata_v1"

    sprint_count_mode: Literal[
        "auto",
        "manual",
    ]

    effective_sprint_count: int = Field(
        ge=1,
    )

    recommended_sprint_count: Optional[
        int
    ] = Field(
        default=None,
        ge=1,
    )

    sprint_count_reason: Optional[
        str
    ] = None

    evaluated_sprint_counts: list[
        int
    ] = Field(
        default_factory=list
    )

    sprint_duration_mode: Literal[
        "auto",
        "manual",
    ]

    effective_sprint_duration_days: int = Field(
        ge=1,
        le=31,
    )

    recommended_sprint_duration_days: Optional[
        int
    ] = Field(
        default=None,
        ge=1,
        le=31,
    )

    cadence_band: Optional[
        Literal[
            "short",
            "standard",
            "extended",
            "long",
        ]
    ] = None

    cadence_confidence: Optional[
        Literal[
            "low",
            "medium",
            "high",
        ]
    ] = None

    cadence_reason_codes: list[
        str
    ] = Field(
        default_factory=list
    )

    cadence_evaluated_story_count: Optional[
        int
    ] = Field(
        default=None,
        ge=0,
    )

    effective_sprint_capacity_story_points: float = Field(
        ge=0,
    )

    release_capacity_story_points: float = Field(
        ge=0,
    )

    capacity_utilization_ratio: float = Field(
        default=0.0,
        ge=0,
    )

    release_duration_days: int = Field(
        ge=1,
    )


class ProjectManagementPlanV1(BaseModel):
    """Versioned aggregate of certified Sprint 4 outputs.

    This envelope assembles outputs from their existing authorities.  It
    never recalculates priority, Story Points, dependencies or assignments.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: Literal["project_management_plan_v1"] = (
        "project_management_plan_v1"
    )
    generation_id: str
    revision: int = 1
    context_hash: str
    source_context_hash: str
    planner_version: str = "sprint4-v1"
    generated_at: str
    settings: PlanningSettingsV1
    release_planning: Optional[ReleasePlanningMetadataV1] = None
    epics: list[CanonicalEpicV1] = Field(default_factory=list)
    features: list[CanonicalFeatureV1] = Field(default_factory=list)
    stories: list[CanonicalUserStoryV1] = Field(default_factory=list)
    dependencies: list[dict] = Field(default_factory=list)
    sprints: list[dict] = Field(default_factory=list)
    overflow_story_ids: list[str] = Field(default_factory=list)
    metrics: ProjectManagementMetricsV1
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validation_status: Literal["valid"] = "valid"
    scrum_master_advice: list[ScrumMasterRecommendationV1] = Field(
        default_factory=list
    )


class PlanningSettingsUpdateV1(BaseModel):
    """Partial, user-owned planning configuration update."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    sprint_count_mode: Optional[
        Literal["auto", "manual"]
    ] = None

    sprint_count: Optional[int] = None
    sprint_duration_mode: Optional[
        Literal["auto", "manual"]
    ] = None

    sprint_duration_days: Optional[int] = None
    planned_velocity: Optional[float] = None
    team_size: Optional[int] = None
    capacity_adjustment: Optional[float] = None
    start_date: Optional[str] = None
    working_days: Optional[list[int]] = None


class BacklogLocksUpdateV1(BaseModel):
    """The UI may change only explicit lock state, never policy outputs."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    locked_story_ids: list[str] = Field(default_factory=list)
