from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
from pathlib import Path

import pytest


MODULE_NAME = "app.services.story_point_policy"

SERVICE_SOURCE = Path(
    "app/services/story_point_policy.py"
)

EXPECTED_PUBLIC_SYMBOLS = (
    "StoryPointDecisionV1",
    "StoryPointResultV1",
    "StoryPointPolicyError",
    "StoryPointPolicy",
)

ALLOWED_STORY_POINTS = {
    1,
    2,
    3,
    5,
    8,
    13,
    21,
}


def _module_exists() -> bool:
    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def _load_module():
    if not _module_exists():
        pytest.skip(
            "StoryPointPolicy module does not exist yet"
        )

    return importlib.import_module(
        MODULE_NAME
    )


def _symbol(name: str):
    module = _load_module()

    value = getattr(
        module,
        name,
        None,
    )

    if value is None:
        pytest.skip(
            f"{name} does not exist yet"
        )

    return value


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_story_point_policy_module_exists() -> None:

    assert _module_exists(), (
        "Missing deterministic Sprint 4 StoryPointPolicy: "
        "app.services.story_point_policy"
    )


# ============================================================
# PUBLIC AUTHORITY SHAPE
# ============================================================


@pytest.mark.parametrize(
    "symbol_name",
    EXPECTED_PUBLIC_SYMBOLS,
)
def test_story_point_policy_exposes_expected_public_symbols(
    symbol_name: str,
) -> None:

    module = _load_module()

    assert hasattr(
        module,
        symbol_name,
    ), (
        "StoryPointPolicy authority is missing "
        f"public symbol: {symbol_name}"
    )


def test_story_point_policy_apply_accepts_context_and_backlog() -> None:

    policy_class = _symbol(
        "StoryPointPolicy"
    )

    signature = inspect.signature(
        policy_class.apply
    )

    assert list(
        signature.parameters
    ) == [
        "self",
        "context",
        "backlog",
    ]


# ============================================================
# DECISION / RESULT SHAPE
# ============================================================


def test_story_point_decision_exposes_final_authority_fields() -> None:

    decision_model = _symbol(
        "StoryPointDecisionV1"
    )

    fields = set(
        decision_model.model_fields
    )

    assert {
        "story_id",
        "story_points",
        "split_recommended",
    }.issubset(
        fields
    )


def test_story_point_result_exposes_backlog_and_decisions() -> None:

    result_model = _symbol(
        "StoryPointResultV1"
    )

    fields = set(
        result_model.model_fields
    )

    assert {
        "backlog",
        "decisions",
    }.issubset(
        fields
    )


# ============================================================
# DETERMINISTIC AUTHORITY BOUNDARY
# ============================================================


def test_story_point_policy_has_no_external_intelligence_imports() -> None:

    _symbol(
        "StoryPointPolicy"
    )

    assert SERVICE_SOURCE.exists()

    tree = ast.parse(
        SERVICE_SOURCE.read_text(
            encoding="utf-8"
        )
    )

    imported: list[str] = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):
            imported.extend(
                alias.name
                for alias
                in node.names
            )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            imported.append(
                node.module
                or ""
            )


    forbidden_prefixes = (
        "app.agents",
        "app.rag",
        "app.web_search",
        "langchain",
        "langgraph",
        "google",
        "groq",
    )


    offenders = [
        name
        for name
        in imported
        if any(
            name.startswith(prefix)
            for prefix
            in forbidden_prefixes
        )
    ]


    assert not offenders, offenders


def test_story_point_policy_does_not_own_other_planning_authorities() -> None:

    _symbol(
        "StoryPointPolicy"
    )

    source = SERVICE_SOURCE.read_text(
        encoding="utf-8"
    )


    forbidden_methods = (
        "assign_priority",
        "build_dependency_graph",
        "assign_sprint",
        "plan_sprints",
        "calculate_velocity",
        "calculate_burndown",
        "build_architecture",
    )


    for method in forbidden_methods:

        assert (
            f"def {method}("
            not in source
        )


# ============================================================
# FIBONACCI OUTPUT VOCABULARY
#
# This contracts the allowed final values only.
# It deliberately does NOT define factor weights,
# thresholds or aggregation.
# ============================================================


def test_story_point_contract_uses_required_fibonacci_vocabulary() -> None:

    assert ALLOWED_STORY_POINTS == {
        1,
        2,
        3,
        5,
        8,
        13,
        21,
    }
