from __future__ import annotations

import importlib.util
from typing import Any

import pytest


MODULE_NAME = (
    "app.services."
    "dependency_graph_builder"
)

DEPENDENCY_TYPES = (
    "hard_dependency",
    "soft_dependency",
)

HARD_SOURCE_FIELD = "dependencies"
SOFT_SOURCE_FIELD = "dependency_hint_ids"

ERROR_CODES = {
    "unknown_dependency_target",
    "self_dependency",
    "hard_dependency_cycle",
}

TOPOLOGICAL_TIE_BREAK = (
    "story_id_ascending"
)


def _module_exists() -> bool:
    try:
        return (
            importlib.util.find_spec(
                MODULE_NAME
            )
            is not None
        )
    except ModuleNotFoundError:
        return False


BUILDER_EXISTS = _module_exists()

runtime_contract = pytest.mark.skipif(
    not BUILDER_EXISTS,
    reason=(
        "DependencyGraphBuilder does not exist yet; "
        "the A1 authority REAL_RED remains the "
        "current First Wrong Layer."
    ),
)


def _runtime_symbols() -> tuple[Any, ...]:
    from app.schemas.project_management import (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
    )

    from app.services.dependency_graph_builder import (
        DependencyGraphBuilder,
        DependencyGraphBuilderError,
    )

    return (
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        DependencyGraphBuilder,
        DependencyGraphBuilderError,
    )


def _story(
    story_id: str,
    *,
    dependencies: list[str] | None = None,
    hints: list[str] | None = None,
    title: str | None = None,
):
    (
        _CanonicalBacklogV1,
        CanonicalUserStoryV1,
        _DependencyGraphBuilder,
        _DependencyGraphBuilderError,
    ) = _runtime_symbols()

    return CanonicalUserStoryV1.model_construct(
        story_id=story_id,
        title=title or story_id,
        dependencies=list(
            dependencies or []
        ),
        dependency_hint_ids=list(
            hints or []
        ),
        warnings=[],
    )


def _backlog(
    stories,
):
    (
        CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyGraphBuilder,
        _DependencyGraphBuilderError,
    ) = _runtime_symbols()

    return CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash="src-hash",
        context_hash="ctx-hash",
        epics=[],
        features=[],
        stories=list(stories),
        warnings=[],
    )


def _build(backlog):
    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        DependencyGraphBuilder,
        _DependencyGraphBuilderError,
    ) = _runtime_symbols()

    return DependencyGraphBuilder().build(
        backlog=backlog
    )


def _edge_triplets(result) -> set[
    tuple[str, str, str]
]:
    return {
        (
            edge.story_id,
            edge.depends_on_story_id,
            edge.dependency_type,
        )
        for edge in result.graph.edges
    }


def _assert_error(
    backlog,
    expected_code: str,
) -> None:
    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        DependencyGraphBuilder,
        DependencyGraphBuilderError,
    ) = _runtime_symbols()

    with pytest.raises(
        DependencyGraphBuilderError
    ) as exc_info:
        DependencyGraphBuilder().build(
            backlog=backlog
        )

    assert (
        exc_info.value.code
        ==
        expected_code
    )


def test_v1_semantic_contract_is_explicit() -> None:
    """
    Static V1 contract.

    No runtime implementation is required for this test.
    """
    assert DEPENDENCY_TYPES == (
        "hard_dependency",
        "soft_dependency",
    )

    assert (
        HARD_SOURCE_FIELD
        ==
        "dependencies"
    )

    assert (
        SOFT_SOURCE_FIELD
        ==
        "dependency_hint_ids"
    )

    assert ERROR_CODES == {
        "unknown_dependency_target",
        "self_dependency",
        "hard_dependency_cycle",
    }

    assert (
        TOPOLOGICAL_TIE_BREAK
        ==
        "story_id_ascending"
    )


@runtime_contract
def test_dependency_hints_are_soft_only() -> None:
    """
    Product Owner hints must never silently become hard
    planning constraints.
    """
    backlog = _backlog(
        [
            _story("US-001"),
            _story(
                "US-002",
                hints=["US-001"],
            ),
        ]
    )

    result = _build(
        backlog
    )

    assert _edge_triplets(result) == {
        (
            "US-002",
            "US-001",
            "soft_dependency",
        )
    }

    output = {
        story.story_id: story
        for story in result.backlog.stories
    }

    assert (
        output["US-002"].dependencies
        ==
        []
    )

    assert (
        output["US-002"].dependency_hint_ids
        ==
        ["US-001"]
    )


@runtime_contract
def test_explicit_canonical_dependencies_are_hard() -> None:
    backlog = _backlog(
        [
            _story("US-001"),
            _story(
                "US-002",
                dependencies=["US-001"],
            ),
        ]
    )

    result = _build(
        backlog
    )

    assert _edge_triplets(result) == {
        (
            "US-002",
            "US-001",
            "hard_dependency",
        )
    }


@runtime_contract
def test_hard_dependency_wins_over_same_soft_hint() -> None:
    backlog = _backlog(
        [
            _story("US-001"),
            _story(
                "US-002",
                dependencies=[
                    "US-001",
                    "US-001",
                ],
                hints=[
                    "US-001",
                    "US-001",
                ],
            ),
        ]
    )

    result = _build(
        backlog
    )

    assert _edge_triplets(result) == {
        (
            "US-002",
            "US-001",
            "hard_dependency",
        )
    }


@pytest.mark.parametrize(
    "surface",
    [
        "hard",
        "soft",
    ],
)
@runtime_contract
def test_unknown_dependency_target_fails_closed(
    surface: str,
) -> None:
    kwargs = (
        {
            "dependencies": [
                "US-999"
            ]
        }
        if surface == "hard"
        else {
            "hints": [
                "US-999"
            ]
        }
    )

    backlog = _backlog(
        [
            _story(
                "US-001",
                **kwargs,
            ),
        ]
    )

    _assert_error(
        backlog,
        "unknown_dependency_target",
    )


@pytest.mark.parametrize(
    "surface",
    [
        "hard",
        "soft",
    ],
)
@runtime_contract
def test_self_dependency_fails_closed(
    surface: str,
) -> None:
    kwargs = (
        {
            "dependencies": [
                "US-001"
            ]
        }
        if surface == "hard"
        else {
            "hints": [
                "US-001"
            ]
        }
    )

    backlog = _backlog(
        [
            _story(
                "US-001",
                **kwargs,
            ),
        ]
    )

    _assert_error(
        backlog,
        "self_dependency",
    )


@runtime_contract
def test_hard_cycle_is_explicit_red() -> None:
    backlog = _backlog(
        [
            _story(
                "US-001",
                dependencies=["US-002"],
            ),
            _story(
                "US-002",
                dependencies=["US-001"],
            ),
        ]
    )

    _assert_error(
        backlog,
        "hard_dependency_cycle",
    )


@runtime_contract
def test_soft_cycle_does_not_violate_hard_dag() -> None:
    backlog = _backlog(
        [
            _story(
                "US-001",
                hints=["US-002"],
            ),
            _story(
                "US-002",
                hints=["US-001"],
            ),
        ]
    )

    result = _build(
        backlog
    )

    assert _edge_triplets(result) == {
        (
            "US-001",
            "US-002",
            "soft_dependency",
        ),
        (
            "US-002",
            "US-001",
            "soft_dependency",
        ),
    }

    assert (
        result.graph.hard_topological_order
        ==
        [
            "US-001",
            "US-002",
        ]
    )


@runtime_contract
def test_soft_back_edge_does_not_create_false_hard_cycle() -> None:
    """
    US-002 hard-depends on US-001.

    US-001 may have a soft preference pointing back to US-002.
    Only the hard graph owns DAG validity.
    """
    backlog = _backlog(
        [
            _story(
                "US-001",
                hints=["US-002"],
            ),
            _story(
                "US-002",
                dependencies=["US-001"],
            ),
        ]
    )

    result = _build(
        backlog
    )

    assert (
        result.graph.hard_topological_order
        ==
        [
            "US-001",
            "US-002",
        ]
    )


@runtime_contract
def test_topological_order_is_input_order_invariant() -> None:
    first = _backlog(
        [
            _story(
                "US-003",
                dependencies=[
                    "US-002",
                    "US-001",
                ],
            ),
            _story("US-004"),
            _story("US-002"),
            _story("US-001"),
        ]
    )

    second = _backlog(
        [
            _story("US-001"),
            _story("US-002"),
            _story("US-004"),
            _story(
                "US-003",
                dependencies=[
                    "US-001",
                    "US-002",
                ],
            ),
        ]
    )

    first_result = _build(
        first
    )

    second_result = _build(
        second
    )

    assert (
        first_result.graph.hard_topological_order
        ==
        second_result.graph.hard_topological_order
    )

    assert (
        first_result.graph.hard_topological_order
        ==
        [
            "US-001",
            "US-002",
            "US-003",
            "US-004",
        ]
    )


@runtime_contract
def test_builder_does_not_mutate_canonical_backlog() -> None:
    backlog = _backlog(
        [
            _story("US-001"),
            _story(
                "US-002",
                dependencies=["US-001"],
                hints=["US-001"],
            ),
        ]
    )

    before = backlog.model_dump(
        mode="python"
    )

    result = _build(
        backlog
    )

    after = backlog.model_dump(
        mode="python"
    )

    assert after == before

    assert (
        result.backlog.model_dump(
            mode="python"
        )
        ==
        before
    )

    assert (
        result.backlog
        is not backlog
    )

    assert (
        result.graph.source_context_hash
        ==
        backlog.source_context_hash
    )

    assert (
        result.graph.context_hash
        ==
        backlog.context_hash
    )