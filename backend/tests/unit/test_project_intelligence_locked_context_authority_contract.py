from __future__ import annotations

from typing import Any, Dict

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


def _locked_context() -> Dict[str, Any]:
    return {
        "title":
            "Authority Probe",

        "project_name":
            "Authority Probe",

        "description":
            "Canonical project description.",

        "sector":
            "Canonical Sector",

        "industry":
            "Canonical Sector",

        "target_region":
            "Canonical Region",

        "market_region":
            "Canonical Region",

        "target_users": [
            "canonical operators",
        ],

        "problem":
            "canonical coordination problem",

        "core_problem":
            "canonical coordination problem",

        "solution":
            "canonical coordination solution",

        "priority_workflow":
            "canonical workflow",

        "priority_workflows": [
            "canonical workflow",
        ],

        "business_model":
            "canonical commercial model",

        "mvp_scope":
            "canonical minimum scope",

        "payer":
            "canonical buyer",

        "economic_buyer":
            "canonical buyer",

        "actors": {
            "primary_user":
                "canonical operators",

            "payer":
                "canonical buyer",
        },

        "constraints": [
            "canonical constraint",
        ],

        "success_metrics": [
            "canonical metric",
        ],

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


def _build() -> Dict[str, Any]:
    return (
        project_intelligence_layer
        .build(
            title="Authority Probe",
            description=(
                "Target users are field coordinators. "
                "They monitor daily requests and approve service changes. "
                "The proposed tool centralizes operational updates."
            ),
            industry="Canonical Sector",
            target_region="Canonical Region",
            output_language="en",
            project_context=_locked_context(),
            idea_readiness=_readiness(),
            analysis_data={
                "idea_readiness":
                    _readiness(),
            },
        )
    )


def test_locked_canonical_fields_survive_pil_structured_projection() -> None:
    canonical = _locked_context()

    intelligence = _build()

    structured = (
        intelligence.get(
            "structured_project_context"
        )
        or {}
    )

    for field in (
        "project_name",
        "title",
        "description",
        "sector",
        "industry",
        "target_region",
        "market_region",
        "target_users",
        "problem",
        "core_problem",
        "solution",
        "priority_workflow",
        "priority_workflows",
        "business_model",
        "mvp_scope",
        "actors",
        "constraints",
        "success_metrics",
    ):
        assert (
            structured.get(
                field
            )
            == canonical.get(
                field
            )
        ), (
            field,
            canonical.get(
                field
            ),
            structured.get(
                field
            ),
        )


def test_agent_packet_uses_same_locked_canonical_projection() -> None:
    canonical = _locked_context()

    intelligence = _build()

    packet = dict(
        intelligence.get(
            "agent_context_packet"
        )
        or {}
    )

    structured = dict(
        packet.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        structured.get(
            "target_users"
        )
        == canonical[
            "target_users"
        ]
    )

    assert (
        structured.get(
            "priority_workflows"
        )
        == canonical[
            "priority_workflows"
        ]
    )

    assert (
        structured.get(
            "problem"
        )
        == canonical[
            "problem"
        ]
    )

    assert (
        structured.get(
            "solution"
        )
        == canonical[
            "solution"
        ]
    )


def test_merge_cannot_override_locked_canonical_fields() -> None:
    canonical = _locked_context()

    intelligence = {
        "structured_project_context": {
            "target_region":
                "DOWNSTREAM_REGION",

            "target_users": [
                "DOWNSTREAM_USER",
            ],

            "problem":
                "DOWNSTREAM_PROBLEM",

            "solution":
                "DOWNSTREAM_SOLUTION",

            "priority_workflows": [
                "DOWNSTREAM_WORKFLOW",
            ],

            "business_model":
                "DOWNSTREAM_MODEL",

            "mvp_scope":
                "DOWNSTREAM_SCOPE",

            "payer":
                "DOWNSTREAM_PAYER",

            "actors": {
                "primary_user":
                    "DOWNSTREAM_ACTOR",
            },
        },

        "agent_context_packet": {
            "structured_project_context": {
                "target_users": [
                    "DOWNSTREAM_PACKET_USER",
                ],

                "priority_workflows": [
                    "DOWNSTREAM_PACKET_WORKFLOW",
                ],
            },
        },

        "strong_keywords": [],
        "must_match_terms": [],
        "domain_concepts": [],
        "search_concepts": [],
        "target_terms": [],
        "use_case_terms": [],
        "solution_terms": [],
        "problem_keywords": [],
        "weak_terms_to_ignore": [],
        "forbidden_offtopic_terms": [],
        "source_acceptance_rules": {},
        "query_planner": {},
        "context_confidence": {},
    }

    merged = (
        project_intelligence_layer
        .merge_into_project_context(
            base_project_context=canonical,
            intelligence=intelligence,
        )
    )

    for field in (
        "target_region",
        "target_users",
        "problem",
        "solution",
        "priority_workflows",
        "business_model",
        "mvp_scope",
        "payer",
        "actors",
    ):
        assert (
            merged.get(
                field
            )
            == canonical.get(
                field
            )
        ), field

    nested_intelligence = dict(
        merged.get(
            "project_intelligence"
        )
        or {}
    )

    nested_structured = dict(
        nested_intelligence.get(
            "structured_project_context"
        )
        or {}
    )

    nested_packet = dict(
        merged.get(
            "agent_context_packet"
        )
        or {}
    )

    packet_structured = dict(
        nested_packet.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        nested_structured.get(
            "target_users"
        )
        == canonical[
            "target_users"
        ]
    )

    assert (
        nested_structured.get(
            "priority_workflows"
        )
        == canonical[
            "priority_workflows"
        ]
    )

    assert (
        packet_structured.get(
            "target_users"
        )
        == canonical[
            "target_users"
        ]
    )

    assert (
        packet_structured.get(
            "priority_workflows"
        )
        == canonical[
            "priority_workflows"
        ]
    )


def test_locked_empty_canonical_values_cannot_be_invented_downstream() -> None:
    canonical = {
        **_locked_context(),
        "target_users": [],
        "priority_workflow": "",
        "priority_workflows": [],
        "payer": "",
        "economic_buyer": "",
    }

    intelligence = {
        "structured_project_context": {
            "target_users": [
                "invented downstream user",
            ],

            "priority_workflow":
                "invented downstream workflow",

            "priority_workflows": [
                "invented downstream workflow",
            ],

            "payer":
                "invented downstream payer",

            "economic_buyer":
                "invented downstream payer",
        },

        "agent_context_packet": {
            "structured_project_context": {
                "target_users": [
                    "invented packet user",
                ],
            },
        },
    }

    merged = (
        project_intelligence_layer
        .merge_into_project_context(
            base_project_context=canonical,
            intelligence=intelligence,
        )
    )

    assert (
        merged.get(
            "target_users"
        )
        == []
    )

    assert (
        merged.get(
            "priority_workflows"
        )
        == []
    )

    assert (
        merged.get(
            "priority_workflow"
        )
        == ""
    )

    assert (
        merged.get(
            "payer"
        )
        == ""
    )

    assert (
        merged.get(
            "economic_buyer"
        )
        == ""
    )

    nested_structured = (
        (
            merged.get(
                "project_intelligence"
            )
            or {}
        ).get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        nested_structured.get(
            "target_users"
        )
        == []
    )


def test_unlocked_context_keeps_legacy_enrichment_precedence() -> None:
    base = {
        "target_region":
            "BASE_REGION",

        "target_users": [
            "BASE_USER",
        ],

        "context_locked":
            False,
    }

    intelligence = {
        "structured_project_context": {
            "target_region":
                "ENRICHED_REGION",

            "target_users": [
                "ENRICHED_USER",
            ],
        },
    }

    merged = (
        project_intelligence_layer
        .merge_into_project_context(
            base_project_context=base,
            intelligence=intelligence,
        )
    )

    assert (
        merged.get(
            "target_region"
        )
        == "ENRICHED_REGION"
    )

    assert (
        merged.get(
            "target_users"
        )
        == [
            "ENRICHED_USER",
        ]
    )
