from __future__ import annotations

import importlib

import pytest

from app.schemas.solution_architecture import (
    ArchitectureRecommendationV1,
    CandidateArchitectureProposalV1,
    CandidateDatabaseDesignV1,
    CandidateSolutionArchitectureV1,
    CandidateTechnologyLayerV1,
    CandidateTechnologyStackV1,
    DatabaseDesignV1,
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
    TechnologyLayerDecisionV1,
    TechnologyStackV1,
    UMLDiagramBundleV1,
    UMLDiagramV1,
)


FINGERPRINT = (
    "a" * 64
)


def context():
    return SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name=(
            "Neutral Canonical Architecture Project"
        ),
        sector=None,
        target_region=None,
        target_users=[],
        actors=[],
        priority_workflows=[],
        transaction_unit=None,
        positive_mvp_scope=[
            "Execute the canonical project capability",
        ],
        explicit_exclusions=[],
        input_data=[],
        output_decision=[],
        human_oversight=[],
        maintenance_model=[],
        assumptions=[
            "No additional operational assumption was supplied.",
        ],
        forbidden_adjacent_domains=[],
        constraints=[],
        technical_signals=(
            TechnicalSignalsV1()
        ),
        upstream_context_fingerprint=(
            FINGERPRINT
        ),
    )


def architecture():
    return CandidateArchitectureProposalV1(
        style="modular monolith",
        rationale=[
            (
                "A bounded architecture limits unnecessary "
                "distributed complexity."
            ),
        ],
        quality_attributes=[
            "maintainability",
        ],
        constraints_addressed=[],
        alternatives=[],
        risks=[],
        conditions=[],
    )


def layer(
    name,
    status,
    technology=None,
):
    return CandidateTechnologyLayerV1(
        layer=name,
        status=status,
        technology=technology,
        justification=(
            "This layer decision follows the supplied "
            "canonical technical context."
        ),
        alternatives=[],
        conditions=[],
    )


def no_database_candidate():
    return CandidateDatabaseDesignV1(
        status="not_applicable",
        rationale=(
            "Persistent storage is not required by "
            "this neutral contract fixture."
        ),
        dialect=None,
        entities=[],
        warnings=[],
    )


def basic_stack():
    return CandidateTechnologyStackV1(
        layers=[
            layer(
                "frontend",
                "recommended",
                "browser-ui",
            ),
            layer(
                "backend",
                "recommended",
                "application-service",
            ),
            layer(
                "database",
                "not_applicable",
                None,
            ),
            layer(
                "infrastructure",
                "not_applicable",
                None,
            ),
        ]
    )


def candidate(
    *,
    fingerprint=FINGERPRINT,
    architecture_value=None,
    stack_value=None,
    confidence=0.82,
):
    if architecture_value is None:
        architecture_value = architecture()

    if stack_value is None:
        stack_value = basic_stack()

    return CandidateSolutionArchitectureV1(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            fingerprint
        ),
        architecture=architecture_value,
        stack=stack_value,
        uml_diagrams=[],
        database=no_database_candidate(),
        assumptions=[
            "Candidate assumption.",
        ],
        warnings=[
            "Candidate warning.",
        ],
        confidence=confidence,
    )


def non_web_candidate():
    return CandidateSolutionArchitectureV1(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            FINGERPRINT
        ),
        architecture=(
            CandidateArchitectureProposalV1(
                style=(
                    "single-device modular architecture"
                ),
                rationale=[
                    (
                        "The technical context is represented "
                        "without forcing web or cloud layers."
                    ),
                ],
                quality_attributes=[
                    "reliability",
                ],
                constraints_addressed=[],
                alternatives=[],
                risks=[],
                conditions=[],
            )
        ),
        stack=(
            CandidateTechnologyStackV1(
                layers=[
                    layer(
                        "firmware",
                        "recommended",
                        "RTOS",
                    ),
                    layer(
                        "device communication",
                        "recommended",
                        "CAN",
                    ),
                ]
            )
        ),
        uml_diagrams=[],
        database=no_database_candidate(),
        assumptions=[],
        warnings=[],
        confidence=0.77,
    )


def uml_bundle():
    return UMLDiagramBundleV1(
        use_case=UMLDiagramV1(
            diagram_type="use_case",
            syntax="plantuml",
            source=(
                "@startuml\n"
                "actor User\n"
                "usecase Process\n"
                "@enduml"
            ),
            validation_status="valid",
        ),

        class_diagram=UMLDiagramV1(
            diagram_type="class",
            syntax="plantuml",
            source=(
                "@startuml\n"
                "class Record\n"
                "@enduml"
            ),
            validation_status="valid",
        ),

        sequence=UMLDiagramV1(
            diagram_type="sequence",
            syntax="plantuml",
            source=(
                "@startuml\n"
                "actor User\n"
                "participant Service\n"
                "User -> Service: process\n"
                "@enduml"
            ),
            validation_status="valid",
        ),

        activity=UMLDiagramV1(
            diagram_type="activity",
            syntax="plantuml",
            source=(
                "@startuml\n"
                "start\n"
                ":Process;\n"
                "stop\n"
                "@enduml"
            ),
            validation_status="valid",
        ),
    )


def no_database():
    return DatabaseDesignV1(
        status="not_applicable",
        dialect=None,
        sql=None,
        table_definitions=[],
        tables=[],
        relationships=[],
        validation_status=(
            "not_applicable"
        ),
        assumptions=[],
        warnings=[],
    )


def active_database():
    return DatabaseDesignV1(
        status="recommended",
        dialect="postgresql",
        sql=(
            'CREATE TABLE "records" (\n'
            '    "id" INTEGER NOT NULL PRIMARY KEY\n'
            ");"
        ),
        table_definitions=[],
        tables=[
            "records",
        ],
        relationships=[],
        validation_status="valid",
        assumptions=[],
        warnings=[],
    )


def module():
    return importlib.import_module(
        "app.services.solution_architecture_canonical_assembler"
    )


def assembler():
    return (
        module()
        .solution_architecture_canonical_assembler
    )


# =============================================================================
# CONTROL
# =============================================================================

def test_00_control_current_canonical_contract_is_green():
    not_applicable = TechnologyLayerDecisionV1(
        status="not_applicable",
        technology=None,
        justification="Not required.",
        alternatives=[],
        conditions=[],
    )

    stack = TechnologyStackV1(
        frontend=not_applicable,
        backend=not_applicable,
        database=not_applicable,
        infrastructure=not_applicable,
    )

    recommendation = ArchitectureRecommendationV1(
        style="modular monolith",
        rationale=[
            "Bounded architecture.",
        ],
        quality_attributes=[],
        constraints_addressed=[],
        alternatives=[],
        risks=[],
        conditions=[],
    )

    assert stack.frontend.status == "not_applicable"

    assert (
        recommendation.rationale
        ==
        [
            "Bounded architecture.",
        ]
    )


# =============================================================================
# F0
# =============================================================================

def test_01_canonical_stack_preserves_project_specific_layers():
    assert (
        "additional_layers"
        in
        TechnologyStackV1.model_fields
    )

    not_applicable = TechnologyLayerDecisionV1(
        status="not_applicable",
        technology=None,
        justification="Not represented.",
        alternatives=[],
        conditions=[],
    )

    firmware = TechnologyLayerDecisionV1(
        status="recommended",
        technology="RTOS",
        justification="Device runtime.",
        alternatives=[],
        conditions=[],
    )

    stack = TechnologyStackV1(
        frontend=not_applicable,
        backend=not_applicable,
        database=not_applicable,
        infrastructure=not_applicable,
        additional_layers={
            "firmware":
                firmware,
        },
    )

    assert (
        stack
        .additional_layers[
            "firmware"
        ]
        .technology
        ==
        "RTOS"
    )


# =============================================================================
# F1 API
# =============================================================================

def test_02_canonical_assembler_public_api_exists():
    value = module()

    assert hasattr(
        value,
        "SolutionArchitectureCanonicalAssembler",
    )

    assert hasattr(
        value,
        "SolutionArchitectureCanonicalAssemblyError",
    )

    assert hasattr(
        value,
        "solution_architecture_canonical_assembler",
    )


# =============================================================================
# F1/F2 FIXED SLOT PROJECTION
# =============================================================================

def test_03_fixed_stack_projection_preserves_candidate_technology():
    result = assembler().assemble(
        context=context(),
        candidate=candidate(),
        uml=uml_bundle(),
        database=no_database(),
    )

    assert (
        result.context_fingerprint
        ==
        FINGERPRINT
    )

    assert (
        result.stack.frontend.technology
        ==
        "browser-ui"
    )

    assert (
        result.stack.backend.technology
        ==
        "application-service"
    )

    assert (
        result.stack.database.status
        ==
        "not_applicable"
    )

    assert (
        result.stack.infrastructure.status
        ==
        "not_applicable"
    )

    assert (
        result.stack.additional_layers
        ==
        {}
    )


# =============================================================================
# F0/F2 NON-WEB LOSSLESS PROJECTION
# =============================================================================

def test_04_non_web_layers_are_not_dropped_or_forced_into_web_slots():
    result = assembler().assemble(
        context=context(),
        candidate=non_web_candidate(),
        uml=uml_bundle(),
        database=no_database(),
    )

    assert (
        result.stack.frontend.status
        ==
        "not_applicable"
    )

    assert (
        result.stack.backend.status
        ==
        "not_applicable"
    )

    assert (
        result.stack.database.status
        ==
        "not_applicable"
    )

    assert (
        result.stack.infrastructure.status
        ==
        "not_applicable"
    )

    assert set(
        result.stack.additional_layers
    ) == {
        "firmware",
        "device communication",
    }

    assert (
        result
        .stack
        .additional_layers[
            "firmware"
        ]
        .technology
        ==
        "RTOS"
    )

    assert (
        result
        .stack
        .additional_layers[
            "device communication"
        ]
        .technology
        ==
        "CAN"
    )


# =============================================================================
# F3/F4 POLICY GATE
# =============================================================================

def test_05_stale_candidate_is_rejected_by_policy_before_canonical_truth():
    stale = candidate(
        fingerprint=(
            "b" * 64
        )
    )

    with pytest.raises(
        module()
        .SolutionArchitectureCanonicalAssemblyError
    ) as caught:

        assembler().assemble(
            context=context(),
            candidate=stale,
            uml=uml_bundle(),
            database=no_database(),
        )

    assert (
        caught.value.code
        ==
        "policy_rejected"
    )


# =============================================================================
# F6 MISSING ARCHITECTURE
# =============================================================================

def test_06_missing_architecture_fails_closed():
    value = candidate().model_copy(
        update={
            "architecture":
                None,
        }
    )

    with pytest.raises(
        module()
        .SolutionArchitectureCanonicalAssemblyError
    ) as caught:

        assembler().assemble(
            context=context(),
            candidate=value,
            uml=uml_bundle(),
            database=no_database(),
        )

    assert (
        caught.value.code
        ==
        "candidate_architecture_missing"
    )


# =============================================================================
# F6 MISSING STACK
# =============================================================================

def test_07_missing_stack_fails_closed():
    value = candidate().model_copy(
        update={
            "stack":
                None,
        }
    )

    with pytest.raises(
        module()
        .SolutionArchitectureCanonicalAssemblyError
    ) as caught:

        assembler().assemble(
            context=context(),
            candidate=value,
            uml=uml_bundle(),
            database=no_database(),
        )

    assert (
        caught.value.code
        ==
        "candidate_stack_missing"
    )


# =============================================================================
# F6 CONFIDENCE
# =============================================================================

def test_08_missing_confidence_is_not_fabricated():
    value = candidate().model_copy(
        update={
            "confidence":
                None,
        }
    )

    with pytest.raises(
        module()
        .SolutionArchitectureCanonicalAssemblyError
    ) as caught:

        assembler().assemble(
            context=context(),
            candidate=value,
            uml=uml_bundle(),
            database=no_database(),
        )

    assert (
        caught.value.code
        ==
        "candidate_confidence_missing"
    )


# =============================================================================
# F5 DATABASE CONSISTENCY
# =============================================================================

def test_09_database_status_contradiction_fails_closed():
    with pytest.raises(
        module()
        .SolutionArchitectureCanonicalAssemblyError
    ) as caught:

        assembler().assemble(
            context=context(),
            candidate=candidate(),
            uml=uml_bundle(),
            database=active_database(),
        )

    assert (
        caught.value.code
        ==
        "database_candidate_consistency_error"
    )


# =============================================================================
# F5/F6 DETERMINISM + IMMUTABILITY
# =============================================================================

def test_10_assembly_is_deterministic_non_mutating_and_preserves_validated_truth():
    source_context = context()
    source_candidate = candidate()
    source_uml = uml_bundle()
    source_database = no_database()

    before_context = (
        source_context.model_dump(
            mode="json"
        )
    )

    before_candidate = (
        source_candidate.model_dump(
            mode="json"
        )
    )

    before_uml = (
        source_uml.model_dump(
            mode="json"
        )
    )

    before_database = (
        source_database.model_dump(
            mode="json"
        )
    )

    first = assembler().assemble(
        context=source_context,
        candidate=source_candidate,
        uml=source_uml,
        database=source_database,
    )

    second = assembler().assemble(
        context=source_context.model_copy(
            deep=True
        ),
        candidate=source_candidate.model_copy(
            deep=True
        ),
        uml=source_uml.model_copy(
            deep=True
        ),
        database=source_database.model_copy(
            deep=True
        ),
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

    assert (
        source_context.model_dump(
            mode="json"
        )
        ==
        before_context
    )

    assert (
        source_candidate.model_dump(
            mode="json"
        )
        ==
        before_candidate
    )

    assert (
        source_uml.model_dump(
            mode="json"
        )
        ==
        before_uml
    )

    assert (
        source_database.model_dump(
            mode="json"
        )
        ==
        before_database
    )

    assert (
        first.uml.model_dump(
            mode="json"
        )
        ==
        before_uml
    )

    assert (
        first.database.model_dump(
            mode="json"
        )
        ==
        before_database
    )

    assert (
        first.confidence
        ==
        source_candidate.confidence
    )

    assert (
        "Candidate assumption."
        in
        first.assumptions
    )

    assert (
        "No additional operational assumption was supplied."
        in
        first.assumptions
    )

    assert (
        first.warnings
        ==
        source_candidate.warnings
    )
