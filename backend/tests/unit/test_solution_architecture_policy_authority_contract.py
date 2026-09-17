from __future__ import annotations

import importlib

import pytest

from app.schemas.solution_architecture import (
    CandidateArchitectureProposalV1,
    CandidateDatabaseDesignV1,
    CandidateSolutionArchitectureV1,
    CandidateTechnologyLayerV1,
    CandidateTechnologyStackV1,
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
)


MODULE = (
    "app.services.solution_architecture_policy"
)


def context(
    *,
    name: str = "Neutral Project",
    fingerprint: str = "a" * 64,
    signals: TechnicalSignalsV1 | None = None,
    constraints: list[str] | None = None,
    exclusions: list[str] | None = None,
):
    return SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name=name,
        sector=None,
        target_region=None,
        target_users=[],
        actors=[],
        priority_workflows=[],
        transaction_unit=None,
        positive_mvp_scope=[
            "Execute the core operational capability",
        ],
        explicit_exclusions=(
            exclusions
            or
            []
        ),
        input_data=[],
        output_decision=[],
        human_oversight=[],
        maintenance_model=[],
        assumptions=[],
        forbidden_adjacent_domains=[],
        constraints=(
            constraints
            or
            []
        ),
        technical_signals=(
            signals
            or
            TechnicalSignalsV1()
        ),
        upstream_context_fingerprint=(
            fingerprint
        ),
    )


def candidate(
    *,
    fingerprint: str = "a" * 64,
    style: str = "modular architecture",
    layers=None,
    database=None,
):
    return CandidateSolutionArchitectureV1(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            fingerprint
        ),
        architecture=(
            CandidateArchitectureProposalV1(
                style=style,
                rationale=[
                    "Proposed from supplied technical context."
                ],
                quality_attributes=[],
                constraints_addressed=[],
                alternatives=[],
                risks=[],
                conditions=[],
            )
        ),
        stack=(
            CandidateTechnologyStackV1(
                layers=(
                    layers
                    or
                    []
                )
            )
        ),
        uml_diagrams=[],
        database=database,
        assumptions=[],
        warnings=[],
        confidence=0.8,
    )


def module():
    return importlib.import_module(
        MODULE
    )


# ---------------------------------------------------------------------
# CONTROLS
# ---------------------------------------------------------------------

def test_control_candidate_schema_is_available():
    item = candidate()

    assert (
        item.source_context_fingerprint
        ==
        "a" * 64
    )


def test_control_not_applicable_database_candidate_is_representable():
    db = CandidateDatabaseDesignV1(
        status="not_applicable",
        rationale=(
            "No persistence requirement is established."
        ),
        entities=[],
        warnings=[],
    )

    assert (
        db.status
        ==
        "not_applicable"
    )


def test_control_unknown_technical_signals_are_representable():
    signals = TechnicalSignalsV1()

    assert (
        signals.expected_scale
        is None
    )

    assert (
        signals.realtime_required
        is None
    )


# ---------------------------------------------------------------------
# PRODUCT AUTHORITY
# ---------------------------------------------------------------------

def test_policy_public_api_exists():
    mod = module()

    assert hasattr(
        mod,
        "ArchitecturePolicyAuthority",
    )

    assert hasattr(
        mod,
        "ArchitecturePolicyResultV1",
    )

    assert hasattr(
        mod,
        "architecture_policy_authority",
    )


def test_policy_rejects_context_fingerprint_mismatch():
    authority = (
        module()
        .architecture_policy_authority
    )

    result = authority.evaluate(
        context=context(
            fingerprint="a" * 64
        ),
        candidate=candidate(
            fingerprint="b" * 64
        ),
    )

    assert not result.accepted

    assert (
        "context_fingerprint_mismatch"
        in {
            issue.code
            for issue
            in result.errors
        }
    )


def test_policy_rejects_duplicate_technical_layers():
    authority = (
        module()
        .architecture_policy_authority
    )

    layers = [
        CandidateTechnologyLayerV1(
            layer="runtime",
            status="recommended",
            technology="Runtime A",
            justification="Required.",
            alternatives=[],
            conditions=[],
        ),
        CandidateTechnologyLayerV1(
            layer=" Runtime ",
            status="recommended",
            technology="Runtime B",
            justification="Duplicate.",
            alternatives=[],
            conditions=[],
        ),
    ]

    result = authority.evaluate(
        context=context(),
        candidate=candidate(
            layers=layers
        ),
    )

    assert not result.accepted

    assert (
        "duplicate_technical_layer"
        in {
            issue.code
            for issue
            in result.errors
        }
    )


def test_policy_rejects_active_layer_without_technology():
    authority = (
        module()
        .architecture_policy_authority
    )

    layer = CandidateTechnologyLayerV1(
        layer="device_runtime",
        status="recommended",
        technology=None,
        justification=(
            "Provider omitted the actual technology."
        ),
        alternatives=[],
        conditions=[],
    )

    result = authority.evaluate(
        context=context(),
        candidate=candidate(
            layers=[
                layer
            ]
        ),
    )

    assert not result.accepted

    assert (
        "active_layer_missing_technology"
        in {
            issue.code
            for issue
            in result.errors
        }
    )


def test_policy_requires_evidence_for_advanced_distributed_complexity():
    authority = (
        module()
        .architecture_policy_authority
    )

    unsupported = authority.evaluate(
        context=context(
            signals=TechnicalSignalsV1(
                expected_scale=None,
                availability_requirement=None,
                integration_complexity=None,
                multi_tenant_requirement=None,
            )
        ),
        candidate=candidate(
            style=(
                "cloud-native microservices "
                "with Kubernetes"
            )
        ),
    )

    assert not unsupported.accepted

    assert (
        "advanced_complexity_without_support"
        in {
            issue.code
            for issue
            in unsupported.errors
        }
    )

    supported = authority.evaluate(
        context=context(
            signals=TechnicalSignalsV1(
                expected_scale="large scale",
                availability_requirement=(
                    "high availability"
                ),
                integration_complexity="high",
            )
        ),
        candidate=candidate(
            style=(
                "cloud-native microservices "
                "with Kubernetes"
            )
        ),
    )

    assert supported.accepted


def test_policy_rejects_database_when_persistence_is_explicitly_excluded():
    authority = (
        module()
        .architecture_policy_authority
    )

    db = CandidateDatabaseDesignV1(
        status="recommended",
        rationale=(
            "Persistent relational storage."
        ),
        entities=[],
        warnings=[],
    )

    result = authority.evaluate(
        context=context(
            constraints=[
                "The application must be stateless with no persistence."
            ]
        ),
        candidate=candidate(
            database=db
        ),
    )

    assert not result.accepted

    assert (
        "database_conflicts_with_no_persistence"
        in {
            issue.code
            for issue
            in result.errors
        }
    )


def test_policy_is_project_name_invariant_and_non_mutating():
    authority = (
        module()
        .architecture_policy_authority
    )

    source_candidate = candidate()

    context_a = context(
        name="Alpha"
    )

    context_b = context(
        name="Completely Different Name"
    )

    before_candidate = (
        source_candidate.model_dump(
            mode="json"
        )
    )

    before_a = context_a.model_dump(
        mode="json"
    )

    result_a = authority.evaluate(
        context=context_a,
        candidate=source_candidate,
    )

    result_b = authority.evaluate(
        context=context_b,
        candidate=source_candidate,
    )

    assert (
        result_a.model_dump(
            mode="json"
        )
        ==
        result_b.model_dump(
            mode="json"
        )
    )

    assert (
        source_candidate.model_dump(
            mode="json"
        )
        ==
        before_candidate
    )

    assert (
        context_a.model_dump(
            mode="json"
        )
        ==
        before_a
    )
