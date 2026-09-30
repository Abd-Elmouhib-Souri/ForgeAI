from __future__ import annotations

import importlib
import json

import pytest

from app.agents.solution_architect_agent import (
    SolutionArchitectAgent,
)
from app.schemas.solution_architecture import (
    CandidateDatabaseDesignV1,
    CandidateDatabaseEntityV1,
    CandidateSolutionArchitectureV1,
    CandidateUMLDiagramV1,
    DatabaseDesignV1,
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
    UMLDiagramBundleV1,
    UMLDiagramV1,
)


FINGERPRINT = (
    "a" * 64
)


VALID_UML = {
    "use_case": (
        "@startuml\n"
        "actor User\n"
        "usecase Process\n"
        "@enduml"
    ),
    "class": (
        "@startuml\n"
        "class Record\n"
        "@enduml"
    ),
    "sequence": (
        "@startuml\n"
        "actor User\n"
        "participant Service\n"
        "User -> Service: process\n"
        "@enduml"
    ),
    "activity": (
        "@startuml\n"
        "start\n"
        ":Process;\n"
        "stop\n"
        "@enduml"
    ),
}


def context():
    return SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name="Neutral Architecture Project",
        sector=None,
        target_region=None,
        target_users=[],
        actors=[],
        priority_workflows=[],
        transaction_unit=None,
        positive_mvp_scope=[
            "Process one canonical business record",
        ],
        explicit_exclusions=[],
        input_data=[],
        output_decision=[],
        human_oversight=[],
        maintenance_model=[],
        assumptions=[],
        forbidden_adjacent_domains=[],
        constraints=[],
        technical_signals=(
            TechnicalSignalsV1()
        ),
        upstream_context_fingerprint=(
            FINGERPRINT
        ),
    )


def candidate_uml(
    diagram_type: str,
    source: str | None = None,
):
    return CandidateUMLDiagramV1(
        diagram_type=diagram_type,
        syntax="plantuml",
        source=(
            source
            if source is not None
            else VALID_UML[
                diagram_type
            ]
        ),
    )


def candidate(
    diagrams=None,
):
    return CandidateSolutionArchitectureV1(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            FINGERPRINT
        ),
        uml_diagrams=list(
            diagrams
            or []
        ),
        assumptions=[],
        warnings=[],
        confidence=0.8,
    )


class FakeLLM:
    def __init__(
        self,
        responses,
    ):
        self.responses = list(
            responses
        )
        self.calls = []

    async def invoke(
        self,
        prompt,
        task_type,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "task_type": task_type,
            }
        )

        if not self.responses:
            raise RuntimeError(
                "unexpected fake provider call"
            )

        value = self.responses.pop(
            0
        )

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value


def response(
    diagram_type: str,
    source: str,
) -> str:
    return json.dumps(
        {
            "diagram_type":
                diagram_type,
            "syntax":
                "plantuml",
            "source":
                source,
        }
    )


def core_module():
    return importlib.import_module(
        "app.services.solution_architecture_core"
    )


# -------------------------------------------------------------------------
# 0. GREEN CONTROL ? EXISTING FOUR-SLOT UML CANONICAL CONTRACT
# -------------------------------------------------------------------------

def test_00_control_existing_four_slot_uml_contract():
    use_case = UMLDiagramV1(
        diagram_type="use_case",
        syntax="plantuml",
        source=VALID_UML["use_case"],
        validation_status="valid",
    )

    class_diagram = UMLDiagramV1(
        diagram_type="class",
        syntax="plantuml",
        source=VALID_UML["class"],
        validation_status="valid",
    )

    sequence = UMLDiagramV1(
        diagram_type="sequence",
        syntax="plantuml",
        source=VALID_UML["sequence"],
        validation_status="valid",
    )

    activity = UMLDiagramV1(
        diagram_type="activity",
        syntax="plantuml",
        source=VALID_UML["activity"],
        validation_status="valid",
    )

    bundle = UMLDiagramBundleV1(
        use_case=use_case,
        class_diagram=class_diagram,
        sequence=sequence,
        activity=activity,
    )

    assert bundle.use_case.diagram_type == "use_case"
    assert bundle.class_diagram.diagram_type == "class"
    assert bundle.sequence.diagram_type == "sequence"
    assert bundle.activity.diagram_type == "activity"


# -------------------------------------------------------------------------
# H0 ? DATABASE NOT APPLICABLE MUST BE REPRESENTABLE
# -------------------------------------------------------------------------

def test_01_database_not_applicable_has_no_fake_sql():
    database = DatabaseDesignV1(
        status="not_applicable",
        dialect=None,
        sql=None,
        table_definitions=[],
        tables=[],
        relationships=[],
        validation_status="not_applicable",
        assumptions=[],
        warnings=[],
    )

    assert database.status == "not_applicable"
    assert database.dialect is None
    assert database.sql is None
    assert database.tables == []


# -------------------------------------------------------------------------
# H1 ? STRUCTURED CANDIDATE DATABASE INPUT
# -------------------------------------------------------------------------

def test_02_candidate_database_supports_columns_and_foreign_keys():
    schema = importlib.import_module(
        "app.schemas.solution_architecture"
    )

    Column = getattr(
        schema,
        "DatabaseColumnProposalV1",
    )

    ForeignKey = getattr(
        schema,
        "DatabaseForeignKeyProposalV1",
    )

    entity = CandidateDatabaseEntityV1(
        name="records",
        description="Canonical project records.",
        columns=[
            Column(
                name="id",
                data_type="INTEGER",
                nullable=False,
                primary_key=True,
            ),
            Column(
                name="owner_id",
                data_type="INTEGER",
                nullable=False,
            ),
        ],
        foreign_keys=[
            ForeignKey(
                column="owner_id",
                references_table="owners",
                references_column="id",
            ),
        ],
    )

    assert len(entity.columns) == 2
    assert len(entity.foreign_keys) == 1


# -------------------------------------------------------------------------
# G4 ? PLANTUML STRUCTURAL VALIDATOR
# -------------------------------------------------------------------------

def test_03_plantuml_validator_accepts_four_types_and_rejects_remote_include():
    module = core_module()

    validator = (
        module
        .PlantUMLStructuralValidator()
    )

    for diagram_type, source in VALID_UML.items():
        assert validator.validate(
            diagram_type=diagram_type,
            source=source,
        )

    assert not validator.validate(
        diagram_type="class",
        source=(
            "@startuml\n"
            "!includeurl https://example.invalid/a.puml\n"
            "class Record\n"
            "@enduml"
        ),
    )


# -------------------------------------------------------------------------
# G2/G3 ? MISSING TYPE ONLY MUST BE REPAIRED
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_04_missing_activity_only_triggers_one_activity_repair():
    module = core_module()

    fake = FakeLLM(
        [
            response(
                "activity",
                VALID_UML[
                    "activity"
                ],
            )
        ]
    )

    service = module.UMLCompletionService(
        agent=SolutionArchitectAgent(
            llm=fake
        )
    )

    source = candidate(
        [
            candidate_uml("use_case"),
            candidate_uml("class"),
            candidate_uml("sequence"),
        ]
    )

    bundle = await service.complete(
        context=context(),
        candidate=source,
    )

    assert bundle.activity.diagram_type == "activity"

    assert len(fake.calls) == 1

    assert (
        fake.calls[0]["task_type"]
        ==
        "solution_architect_uml_repair"
    )

    assert "activity" in (
        fake.calls[0]["prompt"]
        .casefold()
    )


# -------------------------------------------------------------------------
# G3 ? INVALID TYPE ONLY MUST BE REPAIRED
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_05_invalid_class_only_triggers_one_class_repair():
    module = core_module()

    fake = FakeLLM(
        [
            response(
                "class",
                VALID_UML[
                    "class"
                ],
            )
        ]
    )

    service = module.UMLCompletionService(
        agent=SolutionArchitectAgent(
            llm=fake
        )
    )

    source = candidate(
        [
            candidate_uml("use_case"),
            candidate_uml(
                "class",
                "@startuml\nnote invalid\n@enduml",
            ),
            candidate_uml("sequence"),
            candidate_uml("activity"),
        ]
    )

    bundle = await service.complete(
        context=context(),
        candidate=source,
    )

    assert (
        bundle.class_diagram.validation_status
        ==
        "valid"
    )

    assert len(fake.calls) == 1

    assert "class" in (
        fake.calls[0]["prompt"]
        .casefold()
    )


# -------------------------------------------------------------------------
# G3 ? REPAIR MUST FAIL CLOSED IF STILL INVALID
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_06_invalid_repair_fails_closed():
    module = core_module()

    fake = FakeLLM(
        [
            response(
                "class",
                "@startuml\nnote still invalid\n@enduml",
            )
        ]
    )

    service = module.UMLCompletionService(
        agent=SolutionArchitectAgent(
            llm=fake
        )
    )

    source = candidate(
        [
            candidate_uml("use_case"),
            candidate_uml("sequence"),
            candidate_uml("activity"),
        ]
    )

    with pytest.raises(
        module.SolutionArchitectureCoreError
    ) as caught:
        await service.complete(
            context=context(),
            candidate=source,
        )

    assert (
        caught.value.code
        ==
        "invalid_uml_after_repair"
    )


# -------------------------------------------------------------------------
# H0 ? BUILDER MUST PRESERVE TRUE N/A
# -------------------------------------------------------------------------

def test_07_database_builder_not_applicable_produces_no_sql():
    module = core_module()

    proposal = CandidateDatabaseDesignV1(
        status="not_applicable",
        rationale=(
            "The canonical project requires no persistent database."
        ),
        dialect=None,
        entities=[],
        warnings=[],
    )

    database = (
        module
        .DatabaseDesignBuilder()
        .build(
            candidate=proposal
        )
    )

    assert database.status == "not_applicable"
    assert database.sql is None
    assert database.tables == []
    assert database.relationships == []


# -------------------------------------------------------------------------
# H1/H2/H3 ? STRUCTURED MODEL -> DETERMINISTIC SQL WITH PK/FK
# -------------------------------------------------------------------------

def test_08_database_builder_generates_deterministic_create_table_pk_fk_sql():
    module = core_module()

    schema = importlib.import_module(
        "app.schemas.solution_architecture"
    )

    Column = getattr(
        schema,
        "DatabaseColumnProposalV1",
    )

    ForeignKey = getattr(
        schema,
        "DatabaseForeignKeyProposalV1",
    )

    proposal = CandidateDatabaseDesignV1(
        status="recommended",
        rationale=(
            "Persistent structured records are required."
        ),
        dialect="postgresql",
        entities=[
            CandidateDatabaseEntityV1(
                name="owners",
                description="Record owners.",
                columns=[
                    Column(
                        name="id",
                        data_type="INTEGER",
                        nullable=False,
                        primary_key=True,
                    ),
                ],
                foreign_keys=[],
            ),
            CandidateDatabaseEntityV1(
                name="records",
                description="Project records.",
                columns=[
                    Column(
                        name="id",
                        data_type="INTEGER",
                        nullable=False,
                        primary_key=True,
                    ),
                    Column(
                        name="owner_id",
                        data_type="INTEGER",
                        nullable=False,
                    ),
                    Column(
                        name="name",
                        data_type="VARCHAR(120)",
                        nullable=False,
                    ),
                ],
                foreign_keys=[
                    ForeignKey(
                        column="owner_id",
                        references_table="owners",
                        references_column="id",
                        on_delete="CASCADE",
                    ),
                ],
            ),
        ],
        warnings=[],
    )

    builder = (
        module
        .DatabaseDesignBuilder()
    )

    first = builder.build(
        candidate=proposal
    )

    second = builder.build(
        candidate=proposal
    )

    assert (
        first.model_dump(
            mode="json"
        )
        ==
        second.model_dump(
            mode="json"
        )
    )

    assert first.validation_status == "valid"

    assert (
        'CREATE TABLE "owners"'
        in first.sql
    )

    assert (
        'CREATE TABLE "records"'
        in first.sql
    )

    assert (
        "PRIMARY KEY"
        in first.sql
    )

    assert (
        "FOREIGN KEY"
        in first.sql
    )

    assert (
        'REFERENCES "owners" ("id")'
        in first.sql
    )

    assert first.tables == [
        "owners",
        "records",
    ]


# -------------------------------------------------------------------------
# H3 ? UNKNOWN FK TARGET MUST FAIL CLOSED
# -------------------------------------------------------------------------

def test_09_database_builder_rejects_unknown_foreign_key_target():
    module = core_module()

    schema = importlib.import_module(
        "app.schemas.solution_architecture"
    )

    Column = getattr(
        schema,
        "DatabaseColumnProposalV1",
    )

    ForeignKey = getattr(
        schema,
        "DatabaseForeignKeyProposalV1",
    )

    proposal = CandidateDatabaseDesignV1(
        status="recommended",
        rationale="Persistent records.",
        dialect="postgresql",
        entities=[
            CandidateDatabaseEntityV1(
                name="records",
                description="Records.",
                columns=[
                    Column(
                        name="id",
                        data_type="INTEGER",
                        nullable=False,
                        primary_key=True,
                    ),
                    Column(
                        name="owner_id",
                        data_type="INTEGER",
                        nullable=False,
                    ),
                ],
                foreign_keys=[
                    ForeignKey(
                        column="owner_id",
                        references_table="missing_table",
                        references_column="id",
                    ),
                ],
            ),
        ],
        warnings=[],
    )

    with pytest.raises(
        module.SolutionArchitectureCoreError
    ) as caught:
        (
            module
            .DatabaseDesignBuilder()
            .build(
                candidate=proposal
            )
        )

    assert (
        caught.value.code
        ==
        "unknown_foreign_key_target_table"
    )


# -------------------------------------------------------------------------
# G3 ? AGENT TARGETED REPAIR MUST BIND TYPE, CONTEXT, PROVIDER TASK
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_agent_targeted_uml_repair_uses_one_provider_call_and_host_type_binding():
    fake = FakeLLM(
        [
            response(
                "use_case",
                VALID_UML[
                    "class"
                ],
            )
        ]
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    diagram = (
        await agent.generate_uml_diagram(
            context=context(),
            diagram_type="class",
        )
    )

    assert diagram.diagram_type == "class"
    assert diagram.syntax == "plantuml"

    assert len(fake.calls) == 1

    assert (
        fake.calls[0]["task_type"]
        ==
        "solution_architect_uml_repair"
    )

    prompt = fake.calls[0][
        "prompt"
    ]

    assert FINGERPRINT in prompt
    assert "class" in prompt.casefold()
