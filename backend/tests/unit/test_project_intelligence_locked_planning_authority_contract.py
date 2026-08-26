from __future__ import annotations

import copy
from typing import Any, Dict
from unittest.mock import patch

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


def _canonical(
    *,
    target_users: list[str] | None = None,
    priority_workflows: list[str] | None = None,
) -> Dict[str, Any]:
    return {
        "title":
            "Authority Probe",

        "project_name":
            "Authority Probe",

        "description":
            "Canonical project description.",

        "industry":
            "Canonical Sector",

        "sector":
            "Canonical Sector",

        "target_region":
            "Canonical Region",

        "market_region":
            "Canonical Region",

        "target_users":
            (
                ["canonical operators"]
                if target_users is None
                else list(
                    target_users
                )
            ),

        "problem":
            "canonical coordination problem",

        "core_problem":
            "canonical coordination problem",

        "solution":
            "canonical coordination solution",

        "business_model":
            "canonical commercial model",

        "mvp_scope":
            "canonical minimum scope",

        "priority_workflow":
            (
                "canonical workflow"
                if priority_workflows is None
                else (
                    priority_workflows[0]
                    if priority_workflows
                    else ""
                )
            ),

        "priority_workflows":
            (
                ["canonical workflow"]
                if priority_workflows is None
                else list(
                    priority_workflows
                )
            ),

        "context_locked":
            True,
    }


def _readiness() -> Dict[str, Any]:
    return {
        "schema_version":
            "project_context_v3",

        "status":
            "ready",

        "score":
            0.93,

        "ready_for_agents":
            True,

        "missing_fields": [],

        "ambiguous_fields": [],

        "blockers": [],
    }


def _safe_copy(
    value: Any,
) -> Any:
    try:
        return copy.deepcopy(
            value
        )
    except Exception:
        return repr(
            value
        )


def _capture_build(
    *,
    canonical: Dict[str, Any],
    description: str,
) -> tuple[
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
]:
    pil = (
        project_intelligence_layer
    )

    captures: Dict[
        str,
        Dict[str, Any],
    ] = {}


    def wrapper(
        name: str,
        original,
    ):
        def call(
            *args,
            **kwargs,
        ):
            captures[
                name
            ] = {
                key:
                    _safe_copy(
                        value
                    )
                for key, value
                in kwargs.items()
            }

            return original(
                *args,
                **kwargs,
            )

        return call


    original_strong = (
        pil._strong_keywords
    )

    original_domain = (
        pil._domain_concepts
    )

    original_query = (
        pil._query_planner
    )

    original_confidence = (
        pil._context_confidence
    )


    with (
        patch.object(
            pil,
            "_strong_keywords",
            side_effect=wrapper(
                "strong_keywords",
                original_strong,
            ),
        ),
        patch.object(
            pil,
            "_domain_concepts",
            side_effect=wrapper(
                "domain_concepts",
                original_domain,
            ),
        ),
        patch.object(
            pil,
            "_query_planner",
            side_effect=wrapper(
                "query_planner",
                original_query,
            ),
        ),
        patch.object(
            pil,
            "_context_confidence",
            side_effect=wrapper(
                "context_confidence",
                original_confidence,
            ),
        ),
    ):
        intelligence = (
            pil.build(
                title="Authority Probe",
                description=description,
                industry="Canonical Sector",
                target_region="Canonical Region",
                output_language="en",
                project_context=canonical,
                idea_readiness=_readiness(),
                analysis_data={
                    "idea_readiness":
                        _readiness(),
                },
            )
        )


    for stage in (
        "strong_keywords",
        "domain_concepts",
        "query_planner",
        "context_confidence",
    ):
        assert (
            stage
            in captures
        ), stage


    return (
        captures,
        intelligence,
    )


def test_locked_target_users_feed_all_internal_planning_stages() -> None:
    canonical = (
        _canonical()
    )

    captures, _ = (
        _capture_build(
            canonical=canonical,
            description=(
                "Target users are field coordinators. "
                "They monitor daily requests."
            ),
        )
    )

    for stage in (
        "strong_keywords",
        "query_planner",
        "context_confidence",
    ):
        assert (
            captures[
                stage
            ].get(
                "target_users"
            )
            == canonical[
                "target_users"
            ]
        ), (
            stage,
            captures[
                stage
            ].get(
                "target_users"
            ),
        )


def test_locked_core_facts_override_conflicting_description_for_planning() -> None:
    canonical = (
        _canonical()
    )

    captures, _ = (
        _capture_build(
            canonical=canonical,
            description=(
                "Problem: downstream raw problem. "
                "Solution: downstream raw solution. "
                "Target users are downstream coordinators. "
                "Business model: downstream subscription model. "
                "The MVP should focus on downstream workflow."
            ),
        )
    )

    expected = {
        "target_users":
            canonical[
                "target_users"
            ],

        "problem":
            canonical[
                "problem"
            ],

        "solution":
            canonical[
                "solution"
            ],

        "business_model":
            canonical[
                "business_model"
            ],

        "mvp_scope":
            canonical[
                "mvp_scope"
            ],
    }


    for stage in (
        "strong_keywords",
        "context_confidence",
    ):
        kwargs = (
            captures[
                stage
            ]
        )

        for field, value in (
            expected.items()
        ):
            if field not in kwargs:
                continue

            assert (
                kwargs[
                    field
                ]
                == value
            ), (
                stage,
                field,
                value,
                kwargs[
                    field
                ],
            )


    query = (
        captures[
            "query_planner"
        ]
    )

    for field in (
        "target_users",
        "problem",
        "solution",
        "business_model",
    ):
        assert (
            query.get(
                field
            )
            == expected[
                field
            ]
        ), (
            field,
            expected[
                field
            ],
            query.get(
                field
            ),
        )


def test_locked_priority_workflow_is_primary_query_workflow() -> None:
    canonical = (
        _canonical()
    )

    captures, _ = (
        _capture_build(
            canonical=canonical,
            description=(
                "The proposed tool centralizes operational updates "
                "and generates dashboards."
            ),
        )
    )

    query = (
        captures[
            "query_planner"
        ]
    )

    canonical_workflows = (
        canonical[
            "priority_workflows"
        ]
    )

    assert (
        query.get(
            "main_use_case"
        )
        == canonical_workflows[
            0
        ]
    ), (
        canonical_workflows,
        query.get(
            "main_use_case"
        ),
    )

    query_use_case_terms = list(
        query.get(
            "use_case_terms"
        )
        or []
    )

    for workflow in (
        canonical_workflows
    ):
        assert (
            workflow
            in query_use_case_terms
        ), (
            workflow,
            query_use_case_terms,
        )


def test_locked_target_users_produce_canonical_target_terms() -> None:
    canonical = (
        _canonical()
    )

    captures, _ = (
        _capture_build(
            canonical=canonical,
            description=(
                "Target users are downstream coordinators. "
                "The tool centralizes operational updates."
            ),
        )
    )

    domain = (
        captures[
            "domain_concepts"
        ]
    )

    query = (
        captures[
            "query_planner"
        ]
    )

    expected_target_terms = (
        project_intelligence_layer
        ._extract_concepts(
            values=(
                canonical[
                    "target_users"
                ]
            ),
            max_items=20,
            prefer_short=True,
        )
    )

    region_noise = (
        project_intelligence_layer
        ._extract_concepts(
            values=(
                project_intelligence_layer
                ._region_noise_values(
                    canonical[
                        "target_region"
                    ]
                )
            ),
            max_items=16,
            prefer_short=True,
        )
    )

    title_noise = (
        project_intelligence_layer
        ._extract_concepts(
            values=[
                canonical[
                    "title"
                ],
            ],
            max_items=8,
            prefer_short=True,
        )
    )

    expected_target_terms = (
        project_intelligence_layer
        ._remove_context_noise(
            expected_target_terms,
            region_noise
            + title_noise,
        )
    )

    assert (
        domain.get(
            "target_terms"
        )
        == expected_target_terms
    ), (
        expected_target_terms,
        domain.get(
            "target_terms"
        ),
    )

    assert (
        query.get(
            "target_terms"
        )
        == expected_target_terms
    ), (
        expected_target_terms,
        query.get(
            "target_terms"
        ),
    )


def test_locked_empty_target_users_are_not_reauthored_for_planning() -> None:
    canonical = (
        _canonical(
            target_users=[],
        )
    )

    captures, intelligence = (
        _capture_build(
            canonical=canonical,
            description=(
                "Target users are downstream coordinators. "
                "They approve daily requests."
            ),
        )
    )

    for stage in (
        "strong_keywords",
        "query_planner",
        "context_confidence",
    ):
        assert (
            captures[
                stage
            ].get(
                "target_users"
            )
            == []
        ), stage


    structured = (
        intelligence.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        structured.get(
            "target_users"
        )
        == []
    )


def test_locked_published_projection_remains_canonical() -> None:
    canonical = (
        _canonical()
    )

    _, intelligence = (
        _capture_build(
            canonical=canonical,
            description=(
                "Target users are downstream coordinators. "
                "Problem: downstream problem. "
                "Solution: downstream solution."
            ),
        )
    )

    structured = (
        intelligence.get(
            "structured_project_context"
        )
        or {}
    )

    for field in (
        "target_users",
        "problem",
        "solution",
        "business_model",
        "mvp_scope",
        "priority_workflows",
    ):
        assert (
            structured.get(
                field
            )
            == canonical.get(
                field
            )
        ), field
