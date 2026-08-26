from __future__ import annotations

import copy
from unittest.mock import patch

import app.web_search.local_market_search as module


def _service():
    # The tested methods have no dependency on constructor-owned
    # network/search clients.
    return (
        module.LocalMarketSearchService
        .__new__(
            module.LocalMarketSearchService
        )
    )


def _canonical_structured():
    return {
        "context_locked":
            True,

        "project_archetype":
            "canonical operating model",

        "vertical":
            "canonical vertical",

        "actors": {
            "primary_user":
                "canonical operators",

            "payer":
                "canonical buyer",
        },

        "target_users": [
            "canonical operators",
        ],

        "priority_workflows": [
            "canonical approval workflow",
        ],

        "success_metrics": [
            "canonical metric",
        ],
    }


def _conflicting_archetype():
    return {
        "project_archetype":
            "inferred downstream archetype",

        "vertical":
            "inferred downstream vertical",

        "actors": {
            "primary_user":
                "inferred coordinators",

            "payer":
                "inferred purchasing team",
        },

        "target_users": [
            "inferred coordinators",
        ],

        "priority_workflows": [
            "inferred scheduling workflow",
        ],

        "success_metrics": [
            "inferred downstream metric",
        ],

        # Keep search enrichment neutral here.
        #
        # Actor-authority tests must fail ONLY because actor precedence
        # is wrong, not because an inferred actor was copied into
        # search_terms by the fixture itself.
        "search_terms": [
            "neutral archetype search enrichment",
        ],

        "search_queries": {
            "all": [
                "neutral archetype query",
            ],
        },
    }


def test_locked_structured_actors_precede_archetype_actors_for_search_terms() -> None:
    service = _service()

    canonical = (
        _canonical_structured()
    )

    conflicting = (
        _conflicting_archetype()
    )

    context = {
        "context_locked":
            True,

        "structured_project_context":
            copy.deepcopy(
                canonical
            ),

        "project_intelligence": {
            "structured_project_context":
                copy.deepcopy(
                    canonical
                ),
        },

        "agent_context_packet": {
            "structured_project_context":
                copy.deepcopy(
                    canonical
                ),
        },

        "must_match_terms": [],
        "domain_concepts": [],
        "search_concepts": [],
        "use_case_terms": [],
    }

    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        return_value=copy.deepcopy(
            conflicting
        ),
    ):
        ensured = (
            service._ensure_archetype_context(
                context,
                sector="Generic Operations",
                region="Canonical Region",
                description="Generic operational description.",
                output_language="en",
            )
        )

    terms = (
        service._specific_context_terms(
            ensured
        )
    )

    normalized = [
        module.normalize_text(
            str(
                item
            )
        )
        for item in terms
    ]

    assert any(
        "canonical operators"
        in item
        for item in normalized
    ), terms

    assert any(
        "canonical buyer"
        in item
        for item in normalized
    ), terms

    assert not any(
        "inferred coordinators"
        in item
        for item in normalized
    ), terms

    assert not any(
        "inferred purchasing team"
        in item
        for item in normalized
    ), terms


def test_locked_top_structured_context_replaces_stale_nested_surfaces() -> None:
    service = _service()

    canonical = (
        _canonical_structured()
    )

    stale = {
        "context_locked":
            True,

        "actors": {
            "primary_user":
                "stale downstream actors",
        },

        "target_users": [
            "stale downstream users",
        ],

        "priority_workflows": [
            "stale downstream workflow",
        ],
    }

    existing_archetype = {
        "project_archetype":
            "generic",

        "search_terms": [
            "neutral search term",
        ],

        "search_queries": {
            "all": [
                "neutral query",
            ],
        },
    }

    output = (
        service._ensure_archetype_context(
            {
                "context_locked":
                    True,

                "structured_project_context":
                    copy.deepcopy(
                        canonical
                    ),

                "archetype_context":
                    copy.deepcopy(
                        existing_archetype
                    ),

                "project_intelligence": {
                    "structured_project_context":
                        copy.deepcopy(
                            stale
                        ),
                },

                "agent_context_packet": {
                    "structured_project_context":
                        copy.deepcopy(
                            stale
                        ),
                },
            },
            sector="Generic Operations",
            region="Canonical Region",
            description="Generic description.",
            output_language="en",
        )
    )

    top = dict(
        output.get(
            "structured_project_context"
        )
        or {}
    )

    intelligence = dict(
        output.get(
            "project_intelligence"
        )
        or {}
    )

    packet = dict(
        output.get(
            "agent_context_packet"
        )
        or {}
    )

    intelligence_structured = dict(
        intelligence.get(
            "structured_project_context"
        )
        or {}
    )

    packet_structured = dict(
        packet.get(
            "structured_project_context"
        )
        or {}
    )

    # Local search may add non-authoritative search/archetype
    # enrichment fields that were absent from the incoming structured
    # context. What it may NOT do is alter any canonical field already
    # present upstream.
    for field, expected in canonical.items():
        assert (
            top.get(
                field
            )
            == expected
        ), (
            field,
            expected,
            top.get(
                field
            ),
        )

    # Once the top-level structured projection has been established,
    # parallel structured surfaces must not retain stale competing
    # copies.
    assert (
        intelligence_structured
        == top
    )

    assert (
        packet_structured
        == top
    )


def test_locked_non_empty_structured_values_survive_archetype_enrichment() -> None:
    service = _service()

    canonical = (
        _canonical_structured()
    )

    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        return_value=(
            _conflicting_archetype()
        ),
    ):
        output = (
            service._ensure_archetype_context(
                {
                    "context_locked":
                        True,

                    "structured_project_context":
                        copy.deepcopy(
                            canonical
                        ),
                },
                sector="Generic Operations",
                region="Canonical Region",
                description="Generic description.",
                output_language="en",
            )
        )

    structured = dict(
        output.get(
            "structured_project_context"
        )
        or {}
    )

    for field in (
        "project_archetype",
        "vertical",
        "actors",
        "target_users",
        "priority_workflows",
        "success_metrics",
    ):
        assert (
            structured.get(
                field
            )
            == canonical.get(
                field
            )
        ), field


def test_locked_explicit_empty_structured_values_remain_authoritative() -> None:
    service = _service()

    canonical = {
        "context_locked":
            True,

        "project_archetype":
            "",

        "vertical":
            "",

        "actors": {},

        "target_users": [],

        "priority_workflows": [],

        "success_metrics": [],
    }

    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        return_value=(
            _conflicting_archetype()
        ),
    ):
        output = (
            service._ensure_archetype_context(
                {
                    "context_locked":
                        True,

                    "structured_project_context":
                        copy.deepcopy(
                            canonical
                        ),
                },
                sector="Generic Operations",
                region="Canonical Region",
                description="Generic description.",
                output_language="en",
            )
        )

    structured = dict(
        output.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        structured.get(
            "project_archetype"
        )
        == ""
    )

    assert (
        structured.get(
            "vertical"
        )
        == ""
    )

    assert (
        structured.get(
            "actors"
        )
        == {}
    )

    assert (
        structured.get(
            "target_users"
        )
        == []
    )

    assert (
        structured.get(
            "priority_workflows"
        )
        == []
    )

    assert (
        structured.get(
            "success_metrics"
        )
        == []
    )


def test_unlocked_incomplete_search_context_can_still_receive_archetype_enrichment() -> None:
    service = _service()

    inferred = (
        _conflicting_archetype()
    )

    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        return_value=copy.deepcopy(
            inferred
        ),
    ):
        output = (
            service._ensure_archetype_context(
                {
                    "context_locked":
                        False,

                    "structured_project_context": {
                        "context_locked":
                            False,
                    },
                },
                sector="Generic Operations",
                region="Canonical Region",
                description="Generic description.",
                output_language="en",
            )
        )

    structured = dict(
        output.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        structured.get(
            "actors"
        )
        == inferred[
            "actors"
        ]
    )

    assert (
        structured.get(
            "target_users"
        )
        == inferred[
            "target_users"
        ]
    )

    assert (
        structured.get(
            "priority_workflows"
        )
        == inferred[
            "priority_workflows"
        ]
    )
