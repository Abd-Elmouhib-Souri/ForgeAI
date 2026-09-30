from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError


MODULE_NAME = "app.schemas.solution_architecture"


def module():
    return importlib.import_module(
        MODULE_NAME
    )


def technology_choice(
    *,
    status="recommended",
    technology="ExampleTech",
    justification=(
        "Chosen because it matches the canonical project constraints."
    ),
):
    mod = module()

    return mod.TechnologyLayerDecisionV1(
        status=status,
        technology=technology,
        justification=justification,
        alternatives=[],
        conditions=[],
    )


def uml(
    diagram_type: str,
):
    mod = module()

    return mod.UMLDiagramV1(
        diagram_type=diagram_type,
        syntax="plantuml",
        source=(
            "@startuml\n"
            "Alice -> Bob: test\n"
            "@enduml"
        ),
        validation_status="pending",
    )


def database():
    mod = module()

    return mod.DatabaseDesignV1(
        dialect="postgresql",
        sql=(
            "CREATE TABLE example ("
            "id INTEGER PRIMARY KEY"
            ");"
        ),
        tables=["example"],
        relationships=[],
        validation_status="pending",
    )


# =============================================================================
# CONTROLS
# =============================================================================

def test_control_existing_project_management_schema_still_imports():
    existing = importlib.import_module(
        "app.schemas.project_management"
    )

    assert existing is not None


def test_control_pydantic_validation_is_available():
    from pydantic import BaseModel

    assert BaseModel is not None


# =============================================================================
# PRODUCT CONTRACTS
# =============================================================================

def test_solution_architecture_context_is_universal_and_structured():
    mod = module()

    signals = mod.TechnicalSignalsV1(
        delivery_stage="mvp",
        client_surfaces=["mobile"],
        realtime_required=True,
        offline_required=None,
        availability_requirement="standard",
        expected_scale="moderate",
        data_sensitivity="high",
        regulatory_context=[
            "regional privacy requirements"
        ],
        integration_complexity="moderate",
        team_size=4,
        budget_constraint="limited",
        time_to_market="fast",
        ai_workload="none",
        hardware_dependency=False,
    )

    context = mod.SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name="Arbitrary Project",
        sector="Arbitrary Domain",
        target_region="Arbitrary Region",
        target_users=[
            "operator",
            "customer",
        ],
        positive_mvp_scope=[
            "capability one",
            "capability two",
        ],
        explicit_exclusions=[
            "future capability"
        ],
        constraints=[
            "limited connectivity"
        ],
        technical_signals=signals,
        upstream_context_fingerprint=(
            "ctx-test-001"
        ),
    )

    assert (
        context.schema_version
        ==
        "solution_architecture_context_v1"
    )

    assert (
        context.project_name
        ==
        "Arbitrary Project"
    )

    assert (
        context.technical_signals.realtime_required
        is True
    )

    assert (
        context.positive_mvp_scope
        ==
        [
            "capability one",
            "capability two",
        ]
    )


def test_stack_contract_supports_recommended_and_not_applicable_layers():
    mod = module()

    stack = mod.TechnologyStackV1(
        frontend=technology_choice(
            status="not_applicable",
            technology=None,
            justification=(
                "This project has no user-facing frontend surface."
            ),
        ),
        backend=technology_choice(),
        database=technology_choice(),
        infrastructure=technology_choice(),
    )

    assert (
        stack.frontend.status
        ==
        "not_applicable"
    )

    assert (
        stack.frontend.technology
        is None
    )

    assert (
        stack.backend.status
        ==
        "recommended"
    )


def test_uml_bundle_requires_the_four_core_types():
    mod = module()

    bundle = mod.UMLDiagramBundleV1(
        use_case=uml(
            "use_case"
        ),
        class_diagram=uml(
            "class"
        ),
        sequence=uml(
            "sequence"
        ),
        activity=uml(
            "activity"
        ),
    )

    assert (
        bundle.use_case.diagram_type
        ==
        "use_case"
    )

    assert (
        bundle.class_diagram.diagram_type
        ==
        "class"
    )

    assert (
        bundle.sequence.diagram_type
        ==
        "sequence"
    )

    assert (
        bundle.activity.diagram_type
        ==
        "activity"
    )


def test_canonical_output_does_not_require_renderer_success():
    mod = module()

    architecture = (
        mod.ArchitectureRecommendationV1(
            style="modular_monolith",
            rationale=[
                (
                    "The recommendation follows "
                    "the canonical technical constraints."
                )
            ],
            quality_attributes=[
                "maintainability"
            ],
            constraints_addressed=[
                "small delivery team"
            ],
            alternatives=[],
        )
    )

    stack = mod.TechnologyStackV1(
        frontend=technology_choice(),
        backend=technology_choice(),
        database=technology_choice(),
        infrastructure=technology_choice(),
    )

    bundle = mod.UMLDiagramBundleV1(
        use_case=uml(
            "use_case"
        ),
        class_diagram=uml(
            "class"
        ),
        sequence=uml(
            "sequence"
        ),
        activity=uml(
            "activity"
        ),
    )

    canonical = (
        mod.CanonicalSolutionArchitectureV1(
            schema_version=(
                "canonical_solution_architecture_v1"
            ),
            context_fingerprint=(
                "ctx-test-001"
            ),
            architecture=architecture,
            stack=stack,
            uml=bundle,
            database=database(),
            assumptions=[],
            warnings=[],
            confidence=0.82,
        )
    )

    assert (
        canonical.schema_version
        ==
        "canonical_solution_architecture_v1"
    )

    assert (
        canonical.confidence
        ==
        0.82
    )

    # Renderer independence:
    # canonical truth must exist before Kroki.
    assert canonical.uml.use_case.source

    assert canonical.database.sql


def test_canonical_confidence_is_bounded():
    mod = module()

    architecture = (
        mod.ArchitectureRecommendationV1(
            style="generic",
            rationale=[
                "reason"
            ],
            quality_attributes=[],
            constraints_addressed=[],
            alternatives=[],
        )
    )

    stack = mod.TechnologyStackV1(
        frontend=technology_choice(),
        backend=technology_choice(),
        database=technology_choice(),
        infrastructure=technology_choice(),
    )

    bundle = mod.UMLDiagramBundleV1(
        use_case=uml(
            "use_case"
        ),
        class_diagram=uml(
            "class"
        ),
        sequence=uml(
            "sequence"
        ),
        activity=uml(
            "activity"
        ),
    )

    with pytest.raises(
        ValidationError
    ):
        mod.CanonicalSolutionArchitectureV1(
            schema_version=(
                "canonical_solution_architecture_v1"
            ),
            context_fingerprint="ctx",
            architecture=architecture,
            stack=stack,
            uml=bundle,
            database=database(),
            assumptions=[],
            warnings=[],
            confidence=1.5,
        )
