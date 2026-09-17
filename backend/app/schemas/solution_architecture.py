from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class SolutionArchitectureContractModel(BaseModel):
    """
    Shared strict base for Sprint 5 canonical architecture contracts.

    These models describe architecture truth and technical decision inputs.
    They intentionally do not contain renderer/provider state.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class TechnicalSignalsV1(
    SolutionArchitectureContractModel
):
    """
    Project-agnostic technical signals used by architecture policies.

    These are observations/constraints, not architecture decisions.
    """

    delivery_stage: str | None = None

    client_surfaces: list[str] = Field(
        default_factory=list
    )

    realtime_required: bool | None = None
    offline_required: bool | None = None

    availability_requirement: str | None = None
    expected_scale: str | None = None
    data_sensitivity: str | None = None

    regulatory_context: list[str] = Field(
        default_factory=list
    )

    integration_complexity: str | None = None

    team_size: int | None = Field(
        default=None,
        ge=1,
    )

    budget_constraint: str | None = None
    time_to_market: str | None = None
    ai_workload: str | None = None
    hardware_dependency: bool | None = None

    deployment_constraints: list[str] = Field(
        default_factory=list
    )

    latency_requirement: str | None = None
    multi_tenant_requirement: bool | None = None
    data_volume: str | None = None
    consistency_requirement: str | None = None


class ArchitectureActorV1(
    SolutionArchitectureContractModel
):
    """
    Canonical actor projection needed by technical architecture,
    UML and database reasoning.

    The model preserves upstream actor truth without imposing a
    domain-specific role taxonomy.
    """

    name: str = Field(
        min_length=1
    )

    role: str = Field(
        min_length=1
    )

    description: str = ""

    is_explicit: bool = False
    is_generic: bool = False


class ArchitectureWorkflowV1(
    SolutionArchitectureContractModel
):
    """
    Canonical operational workflow projection.

    It preserves actor/action/object/result semantics required by
    Use Case, Sequence and Activity diagrams without allowing those
    diagrams to invent project workflows later.
    """

    name: str = Field(
        min_length=1
    )

    actor: str = Field(
        min_length=1
    )

    action: str = Field(
        min_length=1
    )

    object: str = Field(
        min_length=1
    )

    result: str = ""
    output: str = ""
    frequency: str = ""

    is_explicit: bool = False

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class ArchitectureTransactionUnitV1(
    SolutionArchitectureContractModel
):
    """
    Canonical transaction/value-exchange projection.

    Supply and demand actors are optional because many legitimate
    projects are not two-sided marketplaces or transactional systems.
    """

    name: str = Field(
        min_length=1
    )

    description: str = ""

    supply_actor: str | None = None
    demand_actor: str | None = None


class SolutionArchitectureContextV1(
    SolutionArchitectureContractModel
):
    """
    Canonical technical input packet for the Solution Architect.

    This contract is deliberately independent from any sector,
    country, project name, architecture style, or technology stack.
    """

    schema_version: Literal[
        "solution_architecture_context_v1"
    ]

    language: str

    project_name: str

    sector: str | None = None
    target_region: str | None = None

    target_users: list[str] = Field(
        default_factory=list
    )

    actors: list[
        ArchitectureActorV1
    ] = Field(
        default_factory=list
    )

    priority_workflows: list[
        ArchitectureWorkflowV1
    ] = Field(
        default_factory=list
    )

    transaction_unit: (
        ArchitectureTransactionUnitV1
        | None
    ) = None

    positive_mvp_scope: list[str] = Field(
        default_factory=list
    )

    explicit_exclusions: list[str] = Field(
        default_factory=list
    )

    input_data: list[str] = Field(
        default_factory=list
    )

    output_decision: list[str] = Field(
        default_factory=list
    )

    human_oversight: list[str] = Field(
        default_factory=list
    )

    maintenance_model: list[str] = Field(
        default_factory=list
    )

    assumptions: list[str] = Field(
        default_factory=list
    )

    forbidden_adjacent_domains: list[str] = Field(
        default_factory=list
    )

    constraints: list[str] = Field(
        default_factory=list
    )

    technical_signals: TechnicalSignalsV1

    upstream_context_fingerprint: str


class CandidateArchitectureProposalV1(
    SolutionArchitectureContractModel
):
    """
    Structural architecture proposal emitted before policy validation.

    `style` remains open text. The candidate proposes; it does not decide.
    """

    style: str = Field(
        min_length=1
    )

    rationale: list[str] = Field(
        default_factory=list
    )

    quality_attributes: list[str] = Field(
        default_factory=list
    )

    constraints_addressed: list[str] = Field(
        default_factory=list
    )

    alternatives: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    conditions: list[str] = Field(
        default_factory=list
    )


class CandidateTechnologyLayerV1(
    SolutionArchitectureContractModel
):
    """
    One proposed technical layer.

    Layer identity remains open so ForgeAI can represent web, mobile,
    embedded, batch, data, device, integration or future project layers
    without imposing a fixed web application topology.
    """

    layer: str = Field(
        min_length=1
    )

    status: Literal[
        "recommended",
        "conditional",
        "not_applicable",
    ]

    technology: str | None = None

    justification: str = ""

    alternatives: list[str] = Field(
        default_factory=list
    )

    conditions: list[str] = Field(
        default_factory=list
    )


class CandidateTechnologyStackV1(
    SolutionArchitectureContractModel
):
    """
    Open collection of technical-layer proposals.

    Candidate form deliberately does not require frontend, backend,
    database or cloud layers.
    """

    layers: list[
        CandidateTechnologyLayerV1
    ] = Field(
        default_factory=list
    )


class CandidateUMLDiagramV1(
    SolutionArchitectureContractModel
):
    """
    One PlantUML proposal.

    The candidate bundle may be incomplete. Exact four-diagram coverage
    and syntax validity belong to the later UML validation authority.
    """

    diagram_type: Literal[
        "use_case",
        "class",
        "sequence",
        "activity",
    ]

    syntax: Literal[
        "plantuml"
    ] = "plantuml"

    source: str = Field(
        min_length=1
    )



class DatabaseColumnProposalV1(
    SolutionArchitectureContractModel
):
    name: str = Field(
        min_length=1
    )

    data_type: str = Field(
        min_length=1
    )

    nullable: bool = True
    primary_key: bool = False
    unique: bool = False

    default: str | None = None


class DatabaseForeignKeyProposalV1(
    SolutionArchitectureContractModel
):
    column: str = Field(
        min_length=1
    )

    references_table: str = Field(
        min_length=1
    )

    references_column: str = Field(
        min_length=1
    )

    on_delete: str | None = None


class CandidateDatabaseEntityV1(
    SolutionArchitectureContractModel
):
    name: str = Field(
        min_length=1
    )

    description: str = Field(
        min_length=1
    )

    columns: list[
        DatabaseColumnProposalV1
    ] = Field(
        default_factory=list
    )

    foreign_keys: list[
        DatabaseForeignKeyProposalV1
    ] = Field(
        default_factory=list
    )




class CandidateDatabaseDesignV1(
    SolutionArchitectureContractModel
):
    status: Literal[
        "recommended",
        "conditional",
        "not_applicable",
    ]

    rationale: str = Field(
        min_length=1
    )

    dialect: str | None = None

    entities: list[
        CandidateDatabaseEntityV1
    ] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )



class CandidateSolutionArchitectureV1(
    SolutionArchitectureContractModel
):
    """
    Typed structural output of the future Solution Architect LLM.

    This object is not canonical architecture truth. Partial proposals
    remain parseable so deterministic authorities can identify and repair
    missing or invalid portions without fabricating replacements.
    """

    schema_version: Literal[
        "candidate_solution_architecture_v1"
    ]

    source_context_fingerprint: str = Field(
        pattern=r"^[0-9a-fA-F]{64}$"
    )

    architecture: (
        CandidateArchitectureProposalV1
        | None
    ) = None

    stack: (
        CandidateTechnologyStackV1
        | None
    ) = None

    uml_diagrams: list[
        CandidateUMLDiagramV1
    ] = Field(
        default_factory=list
    )

    database: (
        CandidateDatabaseDesignV1
        | None
    ) = None

    assumptions: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class ArchitectureRecommendationV1(
    SolutionArchitectureContractModel
):
    """
    Architecture recommendation after canonical validation.

    `style` remains open text rather than a hard-coded project/domain
    taxonomy so future architecture families can be represented.
    """

    style: str

    rationale: list[str] = Field(
        default_factory=list
    )

    quality_attributes: list[str] = Field(
        default_factory=list
    )

    constraints_addressed: list[str] = Field(
        default_factory=list
    )

    alternatives: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    conditions: list[str] = Field(
        default_factory=list
    )


class TechnologyLayerDecisionV1(
    SolutionArchitectureContractModel
):
    """
    Decision for one technical layer.

    A layer can legitimately be not applicable. ForgeAI must not
    fabricate web/cloud/database layers for projects that do not need
    them.
    """

    status: Literal[
        "recommended",
        "conditional",
        "not_applicable",
    ]

    technology: str | None = None

    justification: str = Field(
        min_length=1
    )

    alternatives: list[str] = Field(
        default_factory=list
    )

    conditions: list[str] = Field(
        default_factory=list
    )

    @model_validator(
        mode="after"
    )
    def validate_layer_semantics(self):
        if (
            self.status
            in {
                "recommended",
                "conditional",
            }
            and
            not self.technology
        ):
            raise ValueError(
                "technology is required when "
                "the layer is recommended or conditional"
            )

        if (
            self.status
            ==
            "not_applicable"
            and
            self.technology is not None
        ):
            raise ValueError(
                "technology must be null when "
                "the layer is not applicable"
            )

        return self



class TechnologyStackV1(
    SolutionArchitectureContractModel
):
    """
    Canonical technology decisions.

    The four stable CDC reporting slots remain explicit.
    Project-specific technical layers are preserved separately so
    non-web, embedded, edge, device, desktop or future architectures
    are not silently reduced to a web-only model.
    """

    frontend: TechnologyLayerDecisionV1
    backend: TechnologyLayerDecisionV1
    database: TechnologyLayerDecisionV1
    infrastructure: TechnologyLayerDecisionV1

    additional_layers: dict[
        str,
        TechnologyLayerDecisionV1,
    ] = Field(
        default_factory=dict
    )



class UMLDiagramV1(
    SolutionArchitectureContractModel
):
    """
    Canonical UML source.

    Rendering is deliberately excluded from this truth contract.
    Kroki or another renderer can fail without destroying this object.
    """

    diagram_type: Literal[
        "use_case",
        "class",
        "sequence",
        "activity",
    ]

    syntax: Literal[
        "plantuml"
    ]

    source: str = Field(
        min_length=1
    )

    validation_status: Literal[
        "pending",
        "valid",
        "invalid",
    ]


class UMLDiagramBundleV1(
    SolutionArchitectureContractModel
):
    """
    The exact four UML types required by Sprint 5 CORE.
    """

    use_case: UMLDiagramV1
    class_diagram: UMLDiagramV1
    sequence: UMLDiagramV1
    activity: UMLDiagramV1

    @model_validator(
        mode="after"
    )
    def validate_slot_types(self):
        expected = {
            "use_case": "use_case",
            "class_diagram": "class",
            "sequence": "sequence",
            "activity": "activity",
        }

        for field_name, diagram_type in expected.items():
            diagram = getattr(
                self,
                field_name,
            )

            if (
                diagram.diagram_type
                !=
                diagram_type
            ):
                raise ValueError(
                    f"{field_name} must contain "
                    f"diagram_type={diagram_type!r}"
                )

        return self



class DatabaseColumnV1(
    SolutionArchitectureContractModel
):
    name: str = Field(
        min_length=1
    )

    data_type: str = Field(
        min_length=1
    )

    nullable: bool = True
    primary_key: bool = False
    unique: bool = False

    default: str | None = None


class DatabaseForeignKeyV1(
    SolutionArchitectureContractModel
):
    column: str = Field(
        min_length=1
    )

    references_table: str = Field(
        min_length=1
    )

    references_column: str = Field(
        min_length=1
    )

    on_delete: str | None = None


class DatabaseTableV1(
    SolutionArchitectureContractModel
):
    name: str = Field(
        min_length=1
    )

    description: str = Field(
        min_length=1
    )

    columns: list[
        DatabaseColumnV1
    ]

    foreign_keys: list[
        DatabaseForeignKeyV1
    ] = Field(
        default_factory=list
    )


class DatabaseDesignV1(
    SolutionArchitectureContractModel
):
    """
    Canonical database design for the user's project.

    SQL is a deterministic projection of the validated structured
    table model. Projects that genuinely need no persistent database
    can explicitly use status=not_applicable without fabricated SQL.
    """

    status: Literal[
        "recommended",
        "conditional",
        "not_applicable",
    ] = "recommended"

    dialect: str | None = None

    sql: str | None = None

    table_definitions: list[
        DatabaseTableV1
    ] = Field(
        default_factory=list
    )

    tables: list[str] = Field(
        default_factory=list
    )

    relationships: list[str] = Field(
        default_factory=list
    )

    validation_status: Literal[
        "pending",
        "valid",
        "invalid",
        "not_applicable",
    ]

    assumptions: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    @model_validator(
        mode="after"
    )
    def validate_database_semantics(self):
        if self.status == "not_applicable":
            if self.dialect is not None:
                raise ValueError(
                    "dialect must be null when database is not applicable"
                )

            if self.sql is not None:
                raise ValueError(
                    "sql must be null when database is not applicable"
                )

            if (
                self.table_definitions
                or self.tables
                or self.relationships
            ):
                raise ValueError(
                    "database structure must be empty when not applicable"
                )

            if (
                self.validation_status
                !=
                "not_applicable"
            ):
                raise ValueError(
                    "not-applicable database must have "
                    "validation_status=not_applicable"
                )

            return self

        if not self.dialect:
            raise ValueError(
                "dialect is required for an applicable database"
            )

        if not self.sql:
            raise ValueError(
                "sql is required for an applicable database"
            )

        if (
            self.validation_status
            ==
            "not_applicable"
        ):
            raise ValueError(
                "applicable database cannot use "
                "validation_status=not_applicable"
            )

        return self



class CanonicalSolutionArchitectureV1(
    SolutionArchitectureContractModel
):
    """
    Canonical Sprint 5 output.

    Renderer output is intentionally absent. PlantUML and SQL source
    remain authoritative even when a renderer/provider is unavailable.
    """

    schema_version: Literal[
        "canonical_solution_architecture_v1"
    ]

    context_fingerprint: str

    architecture: ArchitectureRecommendationV1
    stack: TechnologyStackV1
    uml: UMLDiagramBundleV1
    database: DatabaseDesignV1

    assumptions: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
