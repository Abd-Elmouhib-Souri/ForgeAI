from __future__ import annotations

import ast
import inspect
import textwrap

import app.schemas.project_management as project_management_schema

from app.schemas.project_management import (
    ProjectManagementMetricsV1,
    ProjectManagementPlanV1,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)

from app.services.release_sizing_engine import (
    ReleaseSizingResultV1,
)

from app.services.sprint_cadence_advisor import (
    SprintCadenceRecommendationV1,
)


# =============================================================================
# EXISTING AUTHORITY CONTROLS
#
# These controls prove B3 must PROJECT existing truth,
# not create duplicate point-accounting authorities.
# =============================================================================

def test_existing_metrics_remain_story_point_accounting_authority_control() -> None:

    fields = (
        ProjectManagementMetricsV1
        .model_fields
    )

    required = {
        "planned_velocity",
        "projected_velocity",
        "actual_velocity",
        "total_story_points",
        "assigned_story_points",
        "overflow_story_points",
        "sprint_metrics",
        "ideal_burndown",
        "planned_burndown",
        "actual_burndown",
    }

    assert required <= set(
        fields
    )


def test_release_sizing_result_already_exposes_recommendation_metadata_control() -> None:

    fields = (
        ReleaseSizingResultV1
        .model_fields
    )

    assert {
        "recommended_sprint_count",
        "evaluated_sprint_counts",
        "reason",
    } <= set(
        fields
    )


def test_cadence_result_already_exposes_recommendation_metadata_control() -> None:

    fields = (
        SprintCadenceRecommendationV1
        .model_fields
    )

    assert {
        "recommended_sprint_duration_days",
        "cadence_band",
        "confidence",
        "reason_codes",
        "evaluated_story_count",
    } <= set(
        fields
    )


# =============================================================================
# REAL RED 1 ? RELEASE METADATA SCHEMA AUTHORITY
# =============================================================================

def test_release_planning_metadata_schema_exists() -> None:

    metadata_type = getattr(
        project_management_schema,
        "ReleasePlanningMetadataV1",
        None,
    )

    assert metadata_type is not None, (
        "ReleasePlanningMetadataV1 is missing; "
        "release-level planning provenance currently has no durable schema."
    )


# =============================================================================
# REAL RED 2 ? PRIMARY PLAN MUST PROJECT IT
# =============================================================================

def test_primary_plan_projects_release_planning_metadata() -> None:

    assert (
        "release_planning"
        in
        ProjectManagementPlanV1
        .model_fields
    ), (
        "ProjectManagementPlanV1 currently discards "
        "release-sizing/cadence decision metadata."
    )


# =============================================================================
# REAL RED 3 ? ASSEMBLY BOUNDARY MUST RECEIVE THE AUTHORITY OUTPUT
# =============================================================================

def test_plan_assembly_accepts_release_planning_metadata() -> None:

    parameters = (
        inspect.signature(
            ProjectManagementPlanService
            ._assemble_plan
        )
        .parameters
    )

    assert (
        "release_planning"
        in parameters
    ), (
        "_assemble_plan has no explicit release_planning input, "
        "so recommendation provenance cannot reach the durable plan."
    )


# =============================================================================
# REAL RED 4 ? GENERATE MUST PROJECT THE RESOLVED METADATA
# =============================================================================

def test_generate_projects_release_planning_metadata_to_assembly() -> None:

    source = textwrap.dedent(
        inspect.getsource(
            ProjectManagementPlanService
            .generate
        )
    )

    tree = ast.parse(
        source
    )

    calls = [
        node
        for node in ast.walk(
            tree
        )
        if (
            isinstance(
                node,
                ast.Call,
            )
            and isinstance(
                node.func,
                ast.Attribute,
            )
            and node.func.attr
            ==
            "_assemble_plan"
        )
    ]

    assert len(
        calls
    ) == 1

    keyword_names = {
        keyword.arg
        for keyword
        in calls[0].keywords
        if keyword.arg
        is not None
    }

    assert (
        "release_planning"
        in keyword_names
    ), (
        "generate resolves sizing/cadence internally but "
        "does not project their metadata to _assemble_plan."
    )
