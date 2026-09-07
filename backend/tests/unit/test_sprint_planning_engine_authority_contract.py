from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from typing import get_type_hints

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2]

TARGET = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "sprint_planning_engine.py"
)

FIRST_WRONG_LAYER_MARKER = (
    "S4_10_FIRST_WRONG_LAYER="
    "MISSING_SPRINT_PLANNING_OUTPUT_CONTRACT"
)


EXPECTED_ASSIGNMENT_FIELDS = (
    "story_id",
    "sprint_number",
)


EXPECTED_RESULT_FIELDS = (
    "schema_version",
    "source_context_hash",
    "context_hash",
    "sprint_count",
    "assignments",
    "overflow_story_ids",
    "warnings",
)


EXPECTED_PLAN_PARAMETERS = (
    "self",
    "backlog",
    "dependency_graph",
    "planning_settings",
    "advice",
)


FORBIDDEN_IMPORT_PREFIXES = (
    "app.agents",
    "app.llm",
    "langchain",
    "langgraph",
    "google.genai",
    "google.generativeai",
    "groq",
    "openai",
)


FORBIDDEN_UPSTREAM_AUTHORITY_SYMBOLS = {
    "MoSCoWPriorityPolicy",
    "StoryPointPolicy",
    "DependencyGraphBuilder",
    "AIScrumMasterAgent",
    "LLMProvider",
}


FORBIDDEN_LATER_ENGINE_METHODS = {
    "replan",
    "calculate_velocity",
    "calculate_burndown",
    "build_metrics",
    "build_agile_metrics",
    "persist",
    "save_plan",
}


FORBIDDEN_LATER_CLASSES = {
    "ProjectManagementPlanV1",
    "AgileMetricsV1",
    "VelocityResultV1",
    "BurndownResultV1",
}


FORBIDDEN_OUTPUT_AUTHORITY_FIELDS = {
    "priority",
    "story_points",
    "dependencies",
    "locked",
    "planned_velocity",
    "projected_velocity",
    "actual_velocity",
    "burndown",
    "metrics",
}


def _require_target() -> None:

    if not TARGET.exists():
        pytest.skip(
            "SprintPlanningEngine target "
            "does not exist yet."
        )


def _source() -> str:

    _require_target()

    return TARGET.read_text(
        encoding="utf-8"
    )


def _tree() -> ast.Module:

    return ast.parse(
        _source()
    )


def _module():

    _require_target()

    importlib.invalidate_caches()

    return importlib.import_module(
        "app.services.sprint_planning_engine"
    )


def _class_names(
    tree: ast.Module,
) -> set[str]:

    return {
        node.name
        for node in tree.body
        if isinstance(
            node,
            ast.ClassDef,
        )
    }


def _imported_modules(
    tree: ast.Module,
) -> set[str]:

    result: set[str] = set()

    for node in tree.body:

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:
                result.add(
                    node.module
                )

        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:
                result.add(
                    alias.name
                )

    return result


def _imported_symbols(
    tree: ast.Module,
) -> set[str]:

    result: set[str] = set()

    for node in tree.body:

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            for alias in node.names:
                result.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:
                result.add(
                    alias.asname
                    or alias.name.split(".")[-1]
                )

    return result


def test_00_real_red_anchor_output_contract_is_missing():

    if not TARGET.exists():

        pytest.fail(
            FIRST_WRONG_LAYER_MARKER
        )


def test_01_planner_declares_minimal_output_and_engine_classes():

    tree = _tree()

    names = _class_names(
        tree
    )

    assert "SprintAssignmentV1" in names
    assert "SprintPlanningResultV1" in names
    assert "SprintPlanningEngine" in names


def test_02_output_models_have_exact_minimal_authority_fields():

    module = _module()

    assignment = (
        module.SprintAssignmentV1
    )

    result = (
        module.SprintPlanningResultV1
    )

    assert tuple(
        assignment.model_fields
    ) == EXPECTED_ASSIGNMENT_FIELDS

    assert tuple(
        result.model_fields
    ) == EXPECTED_RESULT_FIELDS


def test_03_output_models_are_strict_and_result_is_versioned():

    module = _module()

    assignment = (
        module.SprintAssignmentV1
    )

    result = (
        module.SprintPlanningResultV1
    )

    assert (
        assignment.model_config.get(
            "extra"
        )
        ==
        "forbid"
    )

    assert (
        result.model_config.get(
            "extra"
        )
        ==
        "forbid"
    )

    schema_field = (
        result.model_fields[
            "schema_version"
        ]
    )

    assert (
        schema_field.default
        ==
        "sprint_planning_result_v1"
    )

    assert (
        "sprint_planning_result_v1"
        in str(
            schema_field.annotation
        )
    )


def test_04_plan_signature_consumes_canonical_inputs_only():

    module = _module()

    engine = (
        module.SprintPlanningEngine
    )

    method = engine.plan

    assert not inspect.iscoroutinefunction(
        method
    )

    signature = inspect.signature(
        method
    )

    assert tuple(
        signature.parameters
    ) == EXPECTED_PLAN_PARAMETERS

    hints = get_type_hints(
        method
    )

    from app.schemas.project_management import (
        CanonicalBacklogV1,
        PlanningSettingsV1,
        ScrumMasterAdviceV1,
    )

    from app.services.dependency_graph_builder import (
        DependencyGraphV1,
    )

    assert (
        hints["backlog"]
        is CanonicalBacklogV1
    )

    assert (
        hints["dependency_graph"]
        is DependencyGraphV1
    )

    assert (
        hints["planning_settings"]
        is PlanningSettingsV1
    )

    assert (
        hints["advice"]
        is ScrumMasterAdviceV1
    )

    assert (
        hints["return"]
        is module.SprintPlanningResultV1
    )


def test_05_planner_imports_only_canonical_planning_inputs():

    tree = _tree()

    imported = {}

    for node in tree.body:

        if not isinstance(
            node,
            ast.ImportFrom,
        ):
            continue

        if not node.module:
            continue

        imported.setdefault(
            node.module,
            set(),
        ).update(
            alias.name
            for alias in node.names
        )

    pm_imports = imported.get(
        "app.schemas.project_management",
        set(),
    )

    dependency_imports = imported.get(
        "app.services.dependency_graph_builder",
        set(),
    )

    assert {
        "CanonicalBacklogV1",
        "PlanningSettingsV1",
        "ScrumMasterAdviceV1",
    }.issubset(
        pm_imports
    )

    assert (
        "DependencyGraphV1"
        in dependency_imports
    )


def test_06_deterministic_planner_has_no_ai_provider_import():

    tree = _tree()

    modules = _imported_modules(
        tree
    )

    for module_name in modules:

        assert not any(
            (
                module_name
                == prefix
                or module_name.startswith(
                    prefix + "."
                )
            )
            for prefix
            in FORBIDDEN_IMPORT_PREFIXES
        )


def test_07_planner_does_not_recompute_upstream_authorities():

    tree = _tree()

    imported_symbols = (
        _imported_symbols(
            tree
        )
    )

    assert (
        imported_symbols
        &
        FORBIDDEN_UPSTREAM_AUTHORITY_SYMBOLS
    ) == set()


def test_08_sprint_count_boundary_is_release_derived():

    module = _module()

    # Structural planner truth only:
    # resolved Sprint counts begin at one.
    assert (
        module.MIN_SPRINTS
        == 1
    )

    # There is no universal product maximum.
    assert (
        module.MAX_SPRINTS
        is None
    )

    # The planner still must not own a fixed default count.
    assert not hasattr(
        module,
        "DEFAULT_SPRINT_COUNT",
    )


def test_09_planner_does_not_absorb_replanning_or_metrics_authority():

    tree = _tree()

    class_names = _class_names(
        tree
    )

    assert (
        class_names
        &
        FORBIDDEN_LATER_CLASSES
    ) == set()

    engine = next(
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name
            == "SprintPlanningEngine"
        )
    )

    method_names = {
        node.name
        for node in engine.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    assert (
        method_names
        &
        FORBIDDEN_LATER_ENGINE_METHODS
    ) == set()


def test_10_output_does_not_duplicate_upstream_or_metrics_authority():

    module = _module()

    assignment_fields = set(
        module.SprintAssignmentV1.model_fields
    )

    result_fields = set(
        module.SprintPlanningResultV1.model_fields
    )

    assert (
        assignment_fields
        &
        FORBIDDEN_OUTPUT_AUTHORITY_FIELDS
    ) == set()

    assert (
        result_fields
        &
        FORBIDDEN_OUTPUT_AUTHORITY_FIELDS
    ) == set()