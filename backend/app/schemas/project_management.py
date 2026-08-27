from __future__ import annotations

from typing import (
    Dict,
    List,
    Literal,
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
