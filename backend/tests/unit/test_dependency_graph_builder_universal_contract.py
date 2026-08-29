from __future__ import annotations

import importlib.util
from typing import Any

import pytest


MODULE_NAME = (
    "app.services."
    "dependency_graph_builder"
)

UNIVERSAL_INVARIANTS = (
    "deterministic_graph",
    "input_order_invariant",
    "dependency_order_invariant",
    "duplicate_edge_invariant",
    "hard_dag_required",
    "soft_edges_never_create_hard_constraints",
    "business_text_irrelevant_to_graph_semantics",
    "disconnected_components_supported",
    "long_acyclic_chains_supported",
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
        "A1 authority REAL_RED remains the current "
        "First Wrong Layer."
    ),
)


def _symbols() -> tuple[Any, ...]:
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
    story_text: str | None = None,
    business_value: str | None = None,
    priority: str | None = None,
    story_points: int | None = None,
):
    (
        _CanonicalBacklogV1,
        CanonicalUserStoryV1,
        _DependencyGraphBuilder,
        _DependencyGraphBuilderError,
    ) = _symbols()

    return CanonicalUserStoryV1.model_construct(
        story_id=story_id,
        title=title or story_id,
        story=story_text or f"Story {story_id}",
        business_value=business_value or "",
        priority=priority,
        story_points=story_points,
        dependencies=list(
            dependencies or []
        ),
        dependency_hint_ids=list(
            hints or []
        ),
        warnings=[],
    )


def _backlog(stories):
    (
        CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _DependencyGraphBuilder,
        _DependencyGraphBuilderError,
    ) = _symbols()

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
    ) = _symbols()

    return DependencyGraphBuilder().build(
        backlog=backlog
    )


def _edge_signature(result):
    return [
        (
            edge.story_id,
            edge.depends_on_story_id,
            edge.dependency_type,
        )
        for edge in result.graph.edges
    ]


def _graph_signature(result):
    return (
        tuple(
            _edge_signature(result)
        ),
        tuple(
            result.graph.hard_topological_order
        ),
    )


def _assert_error(
    backlog,
    code: str,
) -> None:
    (
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        DependencyGraphBuilder,
        DependencyGraphBuilderError,
    ) = _symbols()

    with pytest.raises(
        DependencyGraphBuilderError
    ) as exc_info:
        DependencyGraphBuilder().build(
            backlog=backlog
        )

    assert exc_info.value.code == code


def test_universal_contract_is_explicit() -> None:
    assert UNIVERSAL_INVARIANTS == (
        "deterministic_graph",
        "input_order_invariant",
        "dependency_order_invariant",
        "duplicate_edge_invariant",
        "hard_dag_required",
        "soft_edges_never_create_hard_constraints",
        "business_text_irrelevant_to_graph_semantics",
        "disconnected_components_supported",
        "long_acyclic_chains_supported",
    )


@runtime_contract
def test_empty_backlog_produces_empty_graph() -> None:
    result = _build(
        _backlog([])
    )

    assert result.graph.edges == []

    assert (
        result.graph.hard_topological_order
        ==
        []
    )


@runtime_contract
def test_hints_alone_never_invent_hard_dependencies() -> None:
    """
    Critical authority invariant.

    Advisory Product Owner hints may become soft edges,
    but cannot silently become hard planning constraints.
    """
    backlog = _backlog(
        [
            _story("US-001"),
            _story(
                "US-002",
                hints=["US-001"],
            ),
            _story(
                "US-003",
                hints=[
                    "US-001",
                    "US-002",
                ],
            ),
        ]
    )

    result = _build(
        backlog
    )

    assert all(
        edge.dependency_type
        ==
        "soft_dependency"
        for edge in result.graph.edges
    )

    assert (
        result.graph.hard_topological_order
        ==
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )


@runtime_contract
def test_duplicate_references_do_not_change_graph_semantics() -> None:
    duplicated = _backlog(
        [
            _story("US-001"),
            _story("US-002"),
            _story(
                "US-003",
                dependencies=[
                    "US-001",
                    "US-001",
                    "US-001",
                ],
                hints=[
                    "US-001",
                    "US-002",
                    "US-002",
                ],
            ),
        ]
    )

    normalized = _backlog(
        [
            _story("US-001"),
            _story("US-002"),
            _story(
                "US-003",
                dependencies=[
                    "US-001",
                ],
                hints=[
                    "US-002",
                ],
            ),
        ]
    )

    assert (
        _graph_signature(
            _build(duplicated)
        )
        ==
        _graph_signature(
            _build(normalized)
        )
    )


@runtime_contract
def test_story_and_dependency_input_order_are_irrelevant() -> None:
    first = _backlog(
        [
            _story(
                "US-004",
                dependencies=[
                    "US-003",
                    "US-001",
                    "US-002",
                ],
                hints=[
                    "US-002",
                    "US-001",
                ],
            ),
            _story("US-002"),
            _story("US-001"),
            _story(
                "US-003",
                dependencies=["US-001"],
            ),
        ]
    )

    second = _backlog(
        [
            _story("US-001"),
            _story(
                "US-003",
                dependencies=["US-001"],
            ),
            _story("US-002"),
            _story(
                "US-004",
                dependencies=[
                    "US-002",
                    "US-001",
                    "US-003",
                ],
                hints=[
                    "US-001",
                    "US-002",
                ],
            ),
        ]
    )

    assert (
        _graph_signature(
            _build(first)
        )
        ==
        _graph_signature(
            _build(second)
        )
    )


@runtime_contract
def test_disconnected_dag_has_stable_topological_order() -> None:
    backlog = _backlog(
        [
            _story(
                "US-006",
                dependencies=["US-005"],
            ),
            _story("US-002"),
            _story(
                "US-004",
                dependencies=[
                    "US-001",
                    "US-003",
                ],
            ),
            _story("US-005"),
            _story("US-003"),
            _story("US-001"),
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
            "US-003",
            "US-004",
            "US-005",
            "US-006",
        ]
    )


@runtime_contract
def test_long_acyclic_chain_is_supported() -> None:
    stories = [
        _story("US-001")
    ]

    for index in range(2, 41):
        current = f"US-{index:03d}"
        previous = f"US-{index - 1:03d}"

        stories.append(
            _story(
                current,
                dependencies=[previous],
            )
        )

    result = _build(
        _backlog(
            list(reversed(stories))
        )
    )

    assert (
        result.graph.hard_topological_order
        ==
        [
            f"US-{index:03d}"
            for index in range(1, 41)
        ]
    )


@runtime_contract
def test_multi_node_hard_cycle_is_rejected() -> None:
    backlog = _backlog(
        [
            _story(
                "US-001",
                dependencies=["US-003"],
            ),
            _story(
                "US-002",
                dependencies=["US-001"],
            ),
            _story(
                "US-003",
                dependencies=["US-002"],
            ),
        ]
    )

    _assert_error(
        backlog,
        "hard_dependency_cycle",
    )


@runtime_contract
def test_soft_edges_do_not_change_hard_dag_semantics() -> None:
    without_soft = _backlog(
        [
            _story("US-001"),
            _story(
                "US-002",
                dependencies=["US-001"],
            ),
            _story(
                "US-003",
                dependencies=["US-002"],
            ),
        ]
    )

    with_soft = _backlog(
        [
            _story(
                "US-001",
                hints=["US-003"],
            ),
            _story(
                "US-002",
                dependencies=["US-001"],
                hints=["US-003"],
            ),
            _story(
                "US-003",
                dependencies=["US-002"],
                hints=["US-001"],
            ),
        ]
    )

    first = _build(
        without_soft
    )

    second = _build(
        with_soft
    )

    assert (
        first.graph.hard_topological_order
        ==
        second.graph.hard_topological_order
        ==
        [
            "US-001",
            "US-002",
            "US-003",
        ]
    )


@runtime_contract
def test_business_text_does_not_change_dependency_semantics() -> None:
    """
    Dependency authority is structural, not keyword-driven.

    Changing titles, prose, business value, priority or Story
    Points must not create or remove dependency edges.
    """
    first = _backlog(
        [
            _story(
                "US-001",
                title="Create account",
                story_text="As a user I create an account.",
                business_value="Access",
                priority="Must",
                story_points=3,
            ),
            _story(
                "US-002",
                dependencies=["US-001"],
                hints=["US-001"],
                title="Protected dashboard",
                story_text="As a user I view my dashboard.",
                business_value="Visibility",
                priority="Should",
                story_points=5,
            ),
        ]
    )

    second = _backlog(
        [
            _story(
                "US-001",
                title="Registro inicial",
                story_text="Texte métier totalement différent.",
                business_value="Different value",
                priority="Could",
                story_points=13,
            ),
            _story(
                "US-002",
                dependencies=["US-001"],
                hints=["US-001"],
                title="Inspection robotique",
                story_text="Unrelated business wording.",
                business_value="Another value",
                priority="Must",
                story_points=1,
            ),
        ]
    )

    assert (
        _graph_signature(
            _build(first)
        )
        ==
        _graph_signature(
            _build(second)
        )
    )