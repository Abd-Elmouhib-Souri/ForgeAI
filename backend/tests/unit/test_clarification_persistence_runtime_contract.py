from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SCHEMA_PATH = (
    ROOT
    / "app/schemas/project.py"
)

ROUTER_PATH = (
    ROOT
    / "app/routers/projects.py"
)

MODEL_PATH = (
    ROOT
    / "app/models.py"
)


def _source(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8",
    )


def _class_source(
    path: Path,
    name: str,
) -> str:
    source = _source(
        path
    )

    tree = ast.parse(
        source
    )

    node = next(
        (
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name
                == name
            )
        ),
        None,
    )

    assert node is not None, (
        f"{name} is missing"
    )

    return (
        ast.get_source_segment(
            source,
            node,
        )
        or ""
    )


def _function_source(
    name: str,
) -> str:
    source = _source(
        ROUTER_PATH
    )

    tree = ast.parse(
        source
    )

    node = next(
        (
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
                and node.name
                == name
            )
        ),
        None,
    )

    assert node is not None, (
        f"{name} is missing"
    )

    return (
        ast.get_source_segment(
            source,
            node,
        )
        or ""
    )


def _clarification_route_source() -> str:
    source = _source(
        ROUTER_PATH
    )

    tree = ast.parse(
        source
    )

    for node in tree.body:

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        decorators = "\n".join(
            (
                ast.get_source_segment(
                    source,
                    decorator,
                )
                or ""
            )
            for decorator
            in node.decorator_list
        )

        if (
            "/{project_id}/clarifications"
            in decorators
        ):
            return (
                ast.get_source_segment(
                    source,
                    node,
                )
                or ""
            )

    return ""


def _project_update_route_source() -> str:
    source = _source(
        ROUTER_PATH
    )

    tree = ast.parse(
        source
    )

    for node in tree.body:

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        segment = (
            ast.get_source_segment(
                source,
                node,
            )
            or ""
        )

        decorators = "\n".join(
            (
                ast.get_source_segment(
                    source,
                    decorator,
                )
                or ""
            )
            for decorator
            in node.decorator_list
        )

        if (
            "ProjectUpdate"
            in segment
            and "/{project_id}"
            in decorators
            and "clarifications"
            not in decorators
        ):
            return segment

    return ""


def test_project_model_has_durable_clarification_context():
    source = _class_source(
        MODEL_PATH,
        "Project",
    )

    assert (
        "clarification_context"
        in source
    )


def test_project_schema_defines_bounded_clarification_update():
    source = _class_source(
        SCHEMA_PATH,
        "ProjectClarificationUpdate",
    )

    assert "answers" in source

    # API must bound both aggregate count and text sizes.
    assert (
        "64"
        in source
    )

    assert (
        "4000"
        in source
    )


def test_both_public_response_models_expose_durable_context():
    project_response = _class_source(
        SCHEMA_PATH,
        "ProjectResponse",
    )

    analysis_response = _class_source(
        SCHEMA_PATH,
        "ProjectAnalysisResponse",
    )

    assert (
        "clarification_context"
        in project_response
    )

    assert (
        "clarification_context"
        in analysis_response
    )


def test_public_response_functions_expose_durable_context():
    project_response = _function_source(
        "project_to_public_response"
    )

    analysis_response = _function_source(
        "analysis_to_public_response"
    )

    assert (
        "clarification_context"
        in project_response
    )

    assert (
        "clarification_context"
        in analysis_response
    )


def test_background_preflight_consumes_durable_answers():
    source = _source(
        ROUTER_PATH
    )

    index = source.find(
        "idea_readiness_checker.evaluate("
    )

    assert index >= 0

    prefix = source[
        max(
            0,
            index - 3000,
        ):
        index
    ]

    call_tail = source[
        index:
        index + 3000
    ]

    assert (
        "clarification_context"
        in prefix
    )

    assert (
        "clarification_answers"
        in call_tail
    )


def test_dedicated_patch_route_has_required_runtime_guards():
    source = _clarification_route_source()

    assert source

    assert (
        "ProjectClarificationUpdate"
        in source
    )

    assert (
        "clarification_context"
        in source
    )

    assert (
        "schema_version"
        in source
    )

    assert (
        "clarification_context_v1"
        in source
    )

    assert (
        "queued"
        in source
    )

    assert (
        "running"
        in source
    )

    assert (
        "HTTP_409_CONFLICT"
        in source
    )

    assert (
        "idea_readiness_checker"
        in source
    )

    assert (
        "clarification_answers"
        in source
    )

    assert (
        "await db.commit"
        in source
    )


def test_clarification_save_does_not_start_agents_or_increment_attempt():
    source = _clarification_route_source()

    assert source

    forbidden = (
        "BackgroundTasks",
        "run_project_analysis_background",
        "AIBusinessAnalystAgent",
        "StartupEvaluatorGraph",
        "DebateRoomGraph",
        "analysis_attempt +=",
        "analysis_attempt = "
        "project.analysis_attempt +",
    )

    for token in forbidden:
        assert token not in source


def test_start_analysis_preserves_durable_clarifications():
    source = _function_source(
        "start_project_analysis"
    )

    forbidden = (
        "project.clarification_context = None",
        "project.clarification_context = {}",
    )

    for token in forbidden:
        assert token not in source


def test_core_project_edit_invalidates_stale_clarifications():
    """
    Clarifications are answers to a particular project context.

    If title, description, industry or market region changes, old answers
    must not silently remain authoritative.

    Output-language-only changes do not invalidate business facts.
    """
    source = (
        _project_update_route_source()
    )

    assert source

    assert (
        "clarification_context"
        in source
    )

    context_fields = (
        "title",
        "description",
        "industry",
        "market_region",
    )

    for field in context_fields:
        assert field in source


def test_clarification_route_keeps_original_description_authority():
    source = _clarification_route_source()

    assert source

    # Saving answers must not concatenate/rewrite project.description.
    assert (
        "project.description +="
        not in source
    )

    assert (
        "project.description = "
        "project.description +"
        not in source
    )
