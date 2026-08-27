from __future__ import annotations

import importlib
import importlib.util
from typing import (
    get_args,
    get_origin,
)

import pytest
from pydantic import ValidationError

from app.schemas.analysis_context import (
    ActorContext,
    ProblemContext,
    SolutionContext,
    TransactionUnitContext,
    WorkflowContext,
)


MODULE_NAME = (
    "app.schemas.project_management"
)


def module_exists() -> bool:
    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def load_model():
    module = importlib.import_module(
        MODULE_NAME
    )

    return getattr(
        module,
        "ProjectManagementContextV1",
    )


def skip_until_schema_exists() -> None:
    if not module_exists():
        pytest.skip(
            "Blocked by schema existence contract."
        )


def list_item_type(annotation):
    origin = get_origin(
        annotation
    )

    assert origin is list

    args = get_args(
        annotation
    )

    assert len(args) == 1

    return args[0]


def test_project_management_schema_module_exists() -> None:

    assert module_exists(), (
        "Missing canonical Sprint 4 schema module: "
        "app.schemas.project_management"
    )


def test_project_management_context_v1_exists_with_exact_version() -> None:

    skip_until_schema_exists()

    model = load_model()

    assert (
        model.model_fields[
            "schema_version"
        ].default
        ==
        "project_management_context_v1"
    )


def test_required_planning_authority_fields_exist() -> None:

    skip_until_schema_exists()

    model = load_model()

    required = {
        "schema_version",
        "source_context_schema_version",

        "project_id",
        "project_name",
        "language",
        "target_region",
        "industry",

        "problem",
        "solution",

        "actors",
        "primary_user_actor_names",
        "payer_actor_names",
        "decision_maker_actor_names",
        "partner_actor_names",
        "blocker_actor_names",

        "priority_workflows",
        "transaction_unit",

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

        "clarification_facts",

        "assumptions",
        "unknowns",
        "warnings",

        "validated_risks",
        "validated_next_actions",
        "go_no_go_conditions",
        "canonical_verdict_code",

        "forbidden_adjacent_domains",

        "source_context_hash",
        "context_hash",
    }

    actual = set(
        model.model_fields
    )

    missing = (
        required - actual
    )

    assert not missing, (
        "Missing PM planning fields: "
        + ", ".join(
            sorted(
                missing
            )
        )
    )


def test_unsafe_archetype_and_query_fields_are_not_planning_authority() -> None:

    skip_until_schema_exists()

    model = load_model()

    forbidden = {
        "primary_archetype",
        "archetype_confidence",
        "secondary_archetypes",

        "domain_terms",
        "use_case_terms",
        "solution_terms",
        "target_terms",

        "search_terms",
        "queries",
        "query_plan",
        "rag_terms",
    }

    actual = set(
        model.model_fields
    )

    leaked = (
        forbidden & actual
    )

    assert not leaked, (
        "Unsafe archetype/query planning authority leaked "
        "into ProjectManagementContextV1: "
        + ", ".join(
            sorted(
                leaked
            )
        )
    )


def test_nested_project_facts_reuse_canonical_sprint3_types() -> None:

    skip_until_schema_exists()

    model = load_model()

    assert (
        model.model_fields[
            "problem"
        ].annotation
        is ProblemContext
    )

    assert (
        model.model_fields[
            "solution"
        ].annotation
        is SolutionContext
    )

    assert (
        list_item_type(
            model.model_fields[
                "actors"
            ].annotation
        )
        is ActorContext
    )

    assert (
        list_item_type(
            model.model_fields[
                "priority_workflows"
            ].annotation
        )
        is WorkflowContext
    )

    assert (
        model.model_fields[
            "transaction_unit"
        ].annotation
        is TransactionUnitContext
    )


def test_semantically_distinct_planning_boundaries_are_independent() -> None:

    skip_until_schema_exists()

    model = load_model()

    context = model(
        mvp_scope=[
            "Allow operators to approve requests."
        ],
        scope_exclusions=[
            "Automatic payment execution is excluded."
        ],
        constraints=[
            "The system must not store passwords "
            "in plaintext."
        ],
        human_oversight=[
            "A qualified professional must review "
            "the final recommendation."
        ],
    )

    assert context.mvp_scope == [
        "Allow operators to approve requests."
    ]

    assert context.scope_exclusions == [
        "Automatic payment execution is excluded."
    ]

    assert context.constraints == [
        "The system must not store passwords "
        "in plaintext."
    ]

    assert context.human_oversight == [
        "A qualified professional must review "
        "the final recommendation."
    ]


def test_mutable_defaults_are_isolated_between_context_instances() -> None:

    skip_until_schema_exists()

    model = load_model()

    first = model()
    second = model()

    first.mvp_scope.append(
        "Capability A"
    )

    first.constraints.append(
        "Constraint A"
    )

    first.clarification_facts[
        "key"
    ] = "value"

    assert second.mvp_scope == []
    assert second.constraints == []
    assert second.clarification_facts == {}


def test_validated_sprint3_outputs_default_to_unknown_not_fabricated() -> None:

    skip_until_schema_exists()

    model = load_model()

    context = model()

    assert (
        context.validated_risks
        == []
    )

    assert (
        context.validated_next_actions
        == []
    )

    assert (
        context.go_no_go_conditions
        == []
    )

    assert (
        context.canonical_verdict_code
        == ""
    )


def test_hash_fields_exist_but_do_not_fabricate_hashes_in_schema_layer() -> None:

    skip_until_schema_exists()

    model = load_model()

    context = model()

    assert (
        context.source_context_hash
        == ""
    )

    assert (
        context.context_hash
        == ""
    )


def test_unknown_fields_are_rejected() -> None:

    skip_until_schema_exists()

    model = load_model()

    with pytest.raises(
        ValidationError
    ):
        model(
            invented_planning_authority=(
                "This field must never "
                "be silently accepted."
            )
        )


def test_source_context_version_defaults_to_project_context_v3() -> None:

    skip_until_schema_exists()

    model = load_model()

    context = model()

    assert (
        context.source_context_schema_version
        ==
        "project_context_v3"
    )
