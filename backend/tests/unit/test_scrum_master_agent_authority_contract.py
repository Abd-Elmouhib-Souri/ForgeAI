from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest

import app.schemas.project_management as pm


BACKEND_ROOT = Path(__file__).resolve().parents[2]

AGENT_PATH = (
    BACKEND_ROOT
    / "app"
    / "agents"
    / "scrum_master_agent.py"
)


# ============================================================
# CANONICAL S4.9 AUTHORITY CONTRACT
# ============================================================

PLANNING_SETTINGS_REQUIRED_FIELDS = {
    "sprint_count",
    "sprint_duration_days",
    "planned_velocity",
    "team_size",
    "capacity_adjustment",
    "start_date",
    "working_days",
}


PLANNING_SETTINGS_FORBIDDEN_FIELDS = {
    "sprints",
    "sprint_assignments",
    "final_sprint_plan",
    "metrics",
    "burndown",
    "actual_velocity",
}


SCRUM_MASTER_ADVICE_REQUIRED_FIELDS = {
    "schema_version",
    "source_context_hash",
    "context_hash",
    "recommendations",
    "warnings",
}


SCRUM_MASTER_ADVICE_FORBIDDEN_FIELDS = {
    "backlog",
    "canonical_backlog",
    "priority",
    "story_points",
    "dependencies",
    "sprints",
    "sprint_assignments",
    "final_sprint_plan",
    "architecture",
    "stack",
}


FORBIDDEN_IMPORT_PREFIXES = (
    "langchain",
    "langgraph",
    "google",
    "groq",
    "openai",
    "requests",
    "httpx",
)


FORBIDDEN_AUTHORITY_IMPORTS = (
    "app.services.backlog_policy_engine",
    "app.services.moscow_priority_policy",
    "app.services.story_point_policy",
    "app.services.sprint_planning_engine",
    "app.services.agile_metrics_builder",
)


FORBIDDEN_AGENT_METHODS = {
    "assign_priority",
    "apply_priority",
    "assign_story_points",
    "estimate_story_points",
    "build_dependency_graph",
    "assign_dependencies",
    "assign_sprint",
    "assign_sprints",
    "plan_sprints",
    "build_sprint_plan",
    "replan",
    "calculate_velocity",
    "calculate_burndown",
    "build_architecture",
    "generate_backlog",
    "canonicalize_backlog",
}


def _planning_settings_class():
    cls = getattr(
        pm,
        "PlanningSettingsV1",
        None,
    )

    assert cls is not None, (
        "S4_9_FIRST_WRONG_LAYER="
        "MISSING_PLANNING_SETTINGS_INPUT_CONTRACT"
    )

    return cls


def _advice_class():
    cls = getattr(
        pm,
        "ScrumMasterAdviceV1",
        None,
    )

    assert cls is not None, (
        "S4_9_NEXT_WRONG_LAYER="
        "MISSING_SCRUM_MASTER_ADVICE_OUTPUT_CONTRACT"
    )

    return cls


def _agent_module():
    assert AGENT_PATH.exists(), (
        "S4_9_NEXT_WRONG_LAYER="
        "MISSING_AI_SCRUM_MASTER_AGENT"
    )

    return importlib.import_module(
        "app.agents.scrum_master_agent"
    )


# ============================================================
# 0. INPUT CONTRACT MUST EXIST BEFORE THE AGENT
# ============================================================

def test_00_planning_settings_v1_is_the_shared_input_contract():
    cls = _planning_settings_class()

    fields = set(
        cls.model_fields
    )

    missing = (
        PLANNING_SETTINGS_REQUIRED_FIELDS
        - fields
    )

    assert not missing, (
        "PlanningSettingsV1 is missing "
        f"required planning inputs: {sorted(missing)}"
    )

    leaked = (
        PLANNING_SETTINGS_FORBIDDEN_FIELDS
        & fields
    )

    assert not leaked, (
        "PlanningSettingsV1 owns planner "
        f"output authority: {sorted(leaked)}"
    )


# ============================================================
# 1. OUTPUT CONTRACT
# ============================================================

def test_01_scrum_master_advice_v1_is_advisory_only():
    _planning_settings_class()

    cls = _advice_class()

    fields = set(
        cls.model_fields
    )

    missing = (
        SCRUM_MASTER_ADVICE_REQUIRED_FIELDS
        - fields
    )

    assert not missing, (
        "ScrumMasterAdviceV1 is missing "
        f"required fields: {sorted(missing)}"
    )

    leaked = (
        SCRUM_MASTER_ADVICE_FORBIDDEN_FIELDS
        & fields
    )

    assert not leaked, (
        "ScrumMasterAdviceV1 leaks deterministic "
        f"authority: {sorted(leaked)}"
    )


# ============================================================
# 2. AGENT TARGET
# ============================================================

def test_02_scrum_master_agent_exists_only_after_shared_contracts():
    _planning_settings_class()
    _advice_class()

    assert AGENT_PATH.exists(), (
        "S4_9_NEXT_WRONG_LAYER="
        "MISSING_AI_SCRUM_MASTER_AGENT"
    )


# ============================================================
# 3. PUBLIC API
# ============================================================

def test_03_scrum_master_public_symbols_are_explicit():
    _planning_settings_class()
    _advice_class()

    module = _agent_module()

    agent = getattr(
        module,
        "AIScrumMasterAgent",
        None,
    )

    error = getattr(
        module,
        "ScrumMasterGenerationError",
        None,
    )

    assert agent is not None, (
        "AIScrumMasterAgent missing."
    )

    assert error is not None, (
        "ScrumMasterGenerationError missing."
    )

    assert issubclass(
        error,
        RuntimeError,
    )


# ============================================================
# 4. EXACT INPUT SIGNATURE
# ============================================================

def test_04_scrum_master_methods_have_one_canonical_input_shape():
    _planning_settings_class()
    _advice_class()

    module = _agent_module()

    cls = module.AIScrumMasterAgent

    build_prompt = inspect.signature(
        cls.build_prompt
    )

    generate_advice = inspect.signature(
        cls.generate_advice
    )

    expected = [
        "self",
        "backlog",
        "dependency_graph",
        "planning_settings",
    ]

    assert list(
        build_prompt.parameters
    ) == expected

    assert list(
        generate_advice.parameters
    ) == expected

    assert inspect.iscoroutinefunction(
        cls.generate_advice
    )


# ============================================================
# 5. CENTRAL LLM PROVIDER ONLY
# ============================================================

def test_05_scrum_master_uses_central_provider_without_direct_llm_stack():
    _planning_settings_class()
    _advice_class()
    _agent_module()

    tree = ast.parse(
        AGENT_PATH.read_text(
            encoding="utf-8"
        )
    )

    imports: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                imports.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module:
                imports.add(
                    node.module
                )

    assert (
        "app.llm.provider"
        in imports
    ), (
        "AIScrumMasterAgent must reuse "
        "the central LLMProvider."
    )

    assert (
        "app.llm.json_response"
        in imports
    ), (
        "AIScrumMasterAgent must reuse "
        "the shared strict JSON parser."
    )

    forbidden_external = sorted(
        module
        for module in imports
        if module.startswith(
            FORBIDDEN_IMPORT_PREFIXES
        )
    )

    assert not forbidden_external, (
        "Direct external intelligence authority "
        f"is forbidden: {forbidden_external}"
    )

    leaked_authorities = sorted(
        module
        for module in imports
        if module.startswith(
            FORBIDDEN_AUTHORITY_IMPORTS
        )
    )

    assert not leaked_authorities, (
        "Scrum Master imported deterministic "
        f"decision authorities: {leaked_authorities}"
    )


# ============================================================
# 6. NO HIDDEN PLANNER METHODS
# ============================================================

def test_06_scrum_master_exposes_no_deterministic_planner_authority():
    _planning_settings_class()
    _advice_class()
    _agent_module()

    tree = ast.parse(
        AGENT_PATH.read_text(
            encoding="utf-8"
        )
    )

    agent_nodes = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name
            ==
            "AIScrumMasterAgent"
        )
    ]

    assert len(agent_nodes) == 1

    methods = {
        node.name
        for node in agent_nodes[0].body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    leaked = sorted(
        methods
        & FORBIDDEN_AGENT_METHODS
    )

    assert not leaked, (
        "Scrum Master owns forbidden "
        f"planner methods: {leaked}"
    )


# ============================================================
# 7. COMPOSITION — NOT BASEAGENT AUTHORITY INHERITANCE
# ============================================================

def test_07_scrum_master_uses_provider_composition():
    _planning_settings_class()
    _advice_class()
    _agent_module()

    tree = ast.parse(
        AGENT_PATH.read_text(
            encoding="utf-8"
        )
    )

    agent_nodes = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name
            ==
            "AIScrumMasterAgent"
        )
    ]

    assert len(agent_nodes) == 1

    base_names = {
        (
            base.id
            if isinstance(
                base,
                ast.Name,
            )
            else ""
        )
        for base in agent_nodes[0].bases
    }

    assert "BaseAgent" not in base_names, (
        "AIScrumMasterAgent must follow "
        "the Product Owner composition pattern."
    )


# ============================================================
# 8. CANONICAL SOURCES ALREADY OWN FINAL DECISIONS
# ============================================================

def test_08_existing_canonical_story_surfaces_remain_the_decision_sources():
    story_fields = set(
        pm.CanonicalUserStoryV1.model_fields
    )

    required = {
        "priority",
        "story_points",
        "dependencies",
        "dependency_hint_ids",
        "locked",
    }

    assert required.issubset(
        story_fields
    ), (
        "CanonicalUserStoryV1 lost an "
        "existing planning authority surface."
    )


# ============================================================
# 9. CONTRACT CONSTANTS ARE DOMAIN / COUNTRY AGNOSTIC
# ============================================================

def test_09_authority_contract_is_fixture_free_and_structural():
    tree = ast.parse(
        Path(
            __file__
        ).read_text(
            encoding="utf-8"
        )
    )

    test_functions = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name.startswith(
                "test_"
            )
        )
    ]

    parameterized = []

    for function in test_functions:
        assert not function.args.args, (
            "Authority contracts must remain "
            "structural and fixture-free."
        )

        for decorator in function.decorator_list:
            text = ast.unparse(
                decorator
            )

            if "parametrize" in text:
                parameterized.append(
                    function.name
                )

    assert not parameterized, (
        "Authority contract must not depend "
        "on example-specific parametrization: "
        f"{parameterized}"
    )
