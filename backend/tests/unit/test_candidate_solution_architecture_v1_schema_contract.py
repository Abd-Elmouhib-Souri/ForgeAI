from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

import app.schemas.solution_architecture as sa


CANDIDATE_MODEL_NAMES = {
    "CandidateArchitectureProposalV1",
    "CandidateTechnologyLayerV1",
    "CandidateTechnologyStackV1",
    "CandidateUMLDiagramV1",
    "CandidateDatabaseEntityV1",
    "CandidateDatabaseDesignV1",
    "CandidateSolutionArchitectureV1",
}


def candidate_class():
    return getattr(
        sa,
        "CandidateSolutionArchitectureV1",
    )


def annotation_mentions(
    model,
    field_name: str,
    expected_name: str,
) -> bool:
    annotation = (
        model
        .model_fields[
            field_name
        ]
        .annotation
    )

    if (
        getattr(
            annotation,
            "__name__",
            None,
        )
        ==
        expected_name
    ):
        return True

    for arg in get_args(
        annotation
    ):
        if (
            getattr(
                arg,
                "__name__",
                None,
            )
            ==
            expected_name
        ):
            return True

        for nested in get_args(
            arg
        ):
            if (
                getattr(
                    nested,
                    "__name__",
                    None,
                )
                ==
                expected_name
            ):
                return True

    return (
        expected_name
        in str(annotation)
    )


# =============================================================================
# GREEN CONTROLS
# =============================================================================

def test_control_existing_solution_architecture_authorities_are_green():
    required = {
        "TechnicalSignalsV1",
        "ArchitectureActorV1",
        "ArchitectureWorkflowV1",
        "ArchitectureTransactionUnitV1",
        "SolutionArchitectureContextV1",
        "ArchitectureRecommendationV1",
        "TechnologyLayerDecisionV1",
        "TechnologyStackV1",
        "UMLDiagramV1",
        "UMLDiagramBundleV1",
        "DatabaseDesignV1",
        "CanonicalSolutionArchitectureV1",
    }

    assert all(
        hasattr(
            sa,
            name,
        )
        for name in required
    )


def test_control_context_is_distinct_from_canonical_output():
    assert (
        sa.SolutionArchitectureContextV1
        is not
        sa.CanonicalSolutionArchitectureV1
    )

    assert (
        "upstream_context_fingerprint"
        in
        sa.SolutionArchitectureContextV1
        .model_fields
    )


def test_control_canonical_schema_does_not_own_runtime_renderer_state():
    forbidden = {
        "provider",
        "model",
        "renderer",
        "renderer_status",
        "svg",
        "latency_ms",
        "generated_at",
    }

    fields = set(
        sa.CanonicalSolutionArchitectureV1
        .model_fields
    )

    assert not (
        fields
        &
        forbidden
    )


# =============================================================================
# PRODUCT CONTRACTS
# =============================================================================

def test_candidate_solution_architecture_model_family_exists():
    for name in CANDIDATE_MODEL_NAMES:
        assert hasattr(
            sa,
            name,
        ), (
            f"Missing candidate model: {name}"
        )


def test_candidate_architecture_proposal_is_structural_and_open():
    model = getattr(
        sa,
        "CandidateArchitectureProposalV1",
    )

    required = {
        "style",
        "rationale",
        "quality_attributes",
        "constraints_addressed",
        "alternatives",
        "risks",
        "conditions",
    }

    assert (
        required
        <=
        set(
            model.model_fields
        )
    )

    # Architecture style must remain open text.
    style_annotation = (
        model
        .model_fields[
            "style"
        ]
        .annotation
    )

    assert (
        style_annotation
        is str
        or
        str
        in get_args(
            style_annotation
        )
    )


def test_candidate_stack_uses_open_layers_not_fixed_web_assumptions():
    layer_model = getattr(
        sa,
        "CandidateTechnologyLayerV1",
    )

    stack_model = getattr(
        sa,
        "CandidateTechnologyStackV1",
    )

    required_layer_fields = {
        "layer",
        "status",
        "technology",
        "justification",
        "alternatives",
        "conditions",
    }

    assert (
        required_layer_fields
        <=
        set(
            layer_model.model_fields
        )
    )

    assert (
        "layers"
        in
        stack_model.model_fields
    )

    assert annotation_mentions(
        stack_model,
        "layers",
        "CandidateTechnologyLayerV1",
    )

    # Do not structurally force every project into a web stack.
    forbidden_fixed_required = {
        "frontend",
        "backend",
        "database",
        "cloud",
        "infrastructure",
    }

    required_fields = {
        name
        for name, field
        in stack_model.model_fields.items()
        if field.is_required()
    }

    assert not (
        required_fields
        &
        forbidden_fixed_required
    )


def test_candidate_uml_is_partial_parseable_plantuml_proposal():
    diagram_model = getattr(
        sa,
        "CandidateUMLDiagramV1",
    )

    required = {
        "diagram_type",
        "syntax",
        "source",
    }

    assert (
        required
        <=
        set(
            diagram_model.model_fields
        )
    )

    candidate = candidate_class()(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            "a" * 64
        ),
        uml_diagrams=[],
    )

    # Missing diagrams must remain structurally parseable here.
    # Completeness belongs to the later UML authority layer.
    assert (
        candidate.uml_diagrams
        ==
        []
    )


def test_candidate_database_does_not_force_persistence_when_not_applicable():
    entity_model = getattr(
        sa,
        "CandidateDatabaseEntityV1",
    )

    database_model = getattr(
        sa,
        "CandidateDatabaseDesignV1",
    )

    assert (
        {
            "name",
            "description",
        }
        <=
        set(
            entity_model.model_fields
        )
    )

    assert (
        {
            "status",
            "rationale",
            "entities",
            "warnings",
        }
        <=
        set(
            database_model.model_fields
        )
    )

    assert annotation_mentions(
        database_model,
        "entities",
        "CandidateDatabaseEntityV1",
    )

    candidate = candidate_class()(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            "b" * 64
        ),
    )

    # The top-level candidate must remain parseable before
    # the database policy determines applicability.
    assert candidate.database is None


def test_candidate_top_level_is_bound_to_context_and_typed():
    model = candidate_class()

    required = {
        "schema_version",
        "source_context_fingerprint",
        "architecture",
        "stack",
        "uml_diagrams",
        "database",
        "assumptions",
        "warnings",
        "confidence",
    }

    assert (
        required
        <=
        set(
            model.model_fields
        )
    )

    assert annotation_mentions(
        model,
        "architecture",
        "CandidateArchitectureProposalV1",
    )

    assert annotation_mentions(
        model,
        "stack",
        "CandidateTechnologyStackV1",
    )

    assert annotation_mentions(
        model,
        "uml_diagrams",
        "CandidateUMLDiagramV1",
    )

    assert annotation_mentions(
        model,
        "database",
        "CandidateDatabaseDesignV1",
    )


def test_candidate_is_partial_candidate_only_and_excludes_runtime_authority():
    model = candidate_class()

    candidate = model(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            "c" * 64
        ),
    )

    assert candidate.architecture is None
    assert candidate.stack is None
    assert candidate.uml_diagrams == []
    assert candidate.database is None
    assert candidate.assumptions == []
    assert candidate.warnings == []
    assert candidate.confidence is None

    forbidden_fields = {
        "canonical",
        "is_valid",
        "provider",
        "model",
        "latency_ms",
        "renderer",
        "renderer_status",
        "svg",
        "created_at",
        "generated_at",
        "analysis_data",
        "rag_context",
        "search_terms",
        "query_plan",
    }

    assert not (
        set(
            model.model_fields
        )
        &
        forbidden_fields
    )

    with pytest.raises(
        ValidationError
    ):
        model(
            schema_version=(
                "candidate_solution_architecture_v1"
            ),
            source_context_fingerprint=(
                "d" * 64
            ),
            confidence=1.01,
        )

    valid = model(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            "e" * 64
        ),
        confidence=0.73,
    )

    assert valid.confidence == 0.73
