from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
from pathlib import Path

import pytest


MODULE_NAME = "app.services.dependency_graph_builder"

SERVICE_PATH = Path(
    "app/services/dependency_graph_builder.py"
)


REQUIRED_PUBLIC_SYMBOLS = {
    "DependencyEdgeV1",
    "DependencyGraphV1",
    "DependencyGraphResultV1",
    "DependencyGraphBuilderError",
    "DependencyGraphBuilder",
}


FORBIDDEN_IMPORT_PREFIXES = (
    "app.agents",
    "app.rag",
    "app.web_search",
    "langchain",
    "langgraph",
    "google",
    "groq",
    "openai",
    "requests",
    "httpx",
)


FORBIDDEN_BUILDER_METHODS = {
    "assign_priority",
    "apply_priority",
    "assign_story_points",
    "estimate_story_points",
    "assign_sprint",
    "plan_sprints",
    "calculate_velocity",
    "calculate_burndown",
    "build_architecture",
    "generate_backlog",
    "canonicalize_backlog",
}


def _module():
    spec = importlib.util.find_spec(
        MODULE_NAME
    )

    if spec is None:
        pytest.skip(
            "DependencyGraphBuilder is intentionally "
            "not implemented yet."
        )

    return importlib.import_module(
        MODULE_NAME
    )


def _defined_class_names() -> set[str]:
    tree = ast.parse(
        SERVICE_PATH.read_text(
            encoding="utf-8"
        )
    )

    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def _imported_modules() -> set[str]:
    tree = ast.parse(
        SERVICE_PATH.read_text(
            encoding="utf-8"
        )
    )

    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module:
                imported.add(
                    node.module
                )

    return imported


def test_dependency_graph_builder_service_exists() -> None:
    """
    REAL RED gate.

    Dependency hints already exist, but no deterministic
    canonical dependency graph authority exists yet.
    """
    assert (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    ), (
        "DependencyGraphBuilder canonical authority "
        "is not implemented."
    )


def test_public_authority_surface_is_explicit() -> None:
    module = _module()

    missing = {
        name
        for name in REQUIRED_PUBLIC_SYMBOLS
        if not hasattr(
            module,
            name,
        )
    }

    assert not missing, (
        "Missing dependency authority symbols: "
        f"{sorted(missing)}"
    )


def test_builder_has_one_narrow_canonical_input() -> None:
    module = _module()

    signature = inspect.signature(
        module.DependencyGraphBuilder.build
    )

    assert list(
        signature.parameters
    ) == [
        "self",
        "backlog",
    ], (
        "DependencyGraphBuilder.build must consume "
        "only the canonical backlog."
    )


def test_existing_dependency_surfaces_remain_authoritative() -> None:
    """
    Existing schema authority must be reused.

    candidate_dependencies = Product Owner advisory proposals

    dependency_hint_ids = canonical-ID advisory hints

    dependencies = final dependency decisions surface
    """
    from app.schemas.project_management import (
        CandidateUserStoryV1,
        CanonicalUserStoryV1,
    )

    candidate_fields = set(
        CandidateUserStoryV1.model_fields
    )

    canonical_fields = set(
        CanonicalUserStoryV1.model_fields
    )

    assert (
        "candidate_dependencies"
        in candidate_fields
    )

    assert {
        "dependencies",
        "dependency_hint_ids",
    }.issubset(
        canonical_fields
    )


def test_edge_contract_has_explicit_direction_and_type() -> None:
    module = _module()

    fields = set(
        module.DependencyEdgeV1.model_fields
    )

    assert {
        "story_id",
        "depends_on_story_id",
        "dependency_type",
    }.issubset(
        fields
    )


def test_dependency_type_is_closed_to_hard_or_soft() -> None:
    module = _module()

    edge_model = (
        module.DependencyEdgeV1
    )

    hard = edge_model(
        story_id="US-002",
        depends_on_story_id="US-001",
        dependency_type="hard_dependency",
    )

    soft = edge_model(
        story_id="US-003",
        depends_on_story_id="US-001",
        dependency_type="soft_dependency",
    )

    assert (
        hard.dependency_type
        == "hard_dependency"
    )

    assert (
        soft.dependency_type
        == "soft_dependency"
    )

    with pytest.raises(Exception):
        edge_model(
            story_id="US-004",
            depends_on_story_id="US-001",
            dependency_type="maybe_dependency",
        )


def test_graph_contract_exposes_planning_safe_outputs() -> None:
    module = _module()

    graph_fields = set(
        module.DependencyGraphV1.model_fields
    )

    result_fields = set(
        module.DependencyGraphResultV1.model_fields
    )

    assert {
        "schema_version",
        "source_context_hash",
        "context_hash",
        "edges",
        "hard_topological_order",
        "warnings",
    }.issubset(
        graph_fields
    )

    assert {
        "backlog",
        "graph",
    }.issubset(
        result_fields
    )


def test_dependency_graph_error_is_typed() -> None:
    module = _module()

    error_type = (
        module.DependencyGraphBuilderError
    )

    assert issubclass(
        error_type,
        ValueError,
    )

    assert (
        hasattr(
            error_type,
            "code",
        )
        or
        (
            "code"
            in inspect.signature(
                error_type.__init__
            ).parameters
        )
    )


def test_dependency_authority_has_no_external_intelligence() -> None:
    _module()

    imported = _imported_modules()

    forbidden = sorted(
        module_name
        for module_name in imported
        if module_name.startswith(
            FORBIDDEN_IMPORT_PREFIXES
        )
    )

    assert not forbidden, (
        "Dependency graph authority must be "
        "deterministic and local. "
        f"Forbidden imports: {forbidden}"
    )


def test_dependency_builder_does_not_own_other_planning_decisions() -> None:
    module = _module()

    builder = (
        module.DependencyGraphBuilder
    )

    leaked = sorted(
        method
        for method in FORBIDDEN_BUILDER_METHODS
        if hasattr(
            builder,
            method,
        )
    )

    assert not leaked, (
        "DependencyGraphBuilder authority leaked "
        f"into unrelated decisions: {leaked}"
    )


def test_service_does_not_redefine_backlog_authority() -> None:
    _module()

    defined = _defined_class_names()

    forbidden_parallel_models = {
        "CandidateBacklogV1",
        "CandidateUserStoryV1",
        "CanonicalBacklogV1",
        "CanonicalUserStoryV1",
    }

    leaked = sorted(
        defined
        & forbidden_parallel_models
    )

    assert not leaked, (
        "DependencyGraphBuilder must reuse canonical "
        "backlog schemas, not define a parallel "
        f"backlog authority: {leaked}"
    )