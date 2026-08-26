from __future__ import annotations

import copy
from unittest.mock import patch

import app.web_search.local_market_search as module


def _service():
    return (
        module.LocalMarketSearchService
        .__new__(
            module.LocalMarketSearchService
        )
    )


def _canonical_structured(
    *,
    target_region_marker=True,
    target_region="Canonland",
    market_region_marker=True,
    market_region="Canonland",
):
    result = {
        "context_locked":
            True,

        "project_archetype":
            "generic",

        "vertical":
            "generic operations",

        "actors": {
            "primary_user":
                "operations users",
        },

        "target_users": [
            "operations users",
        ],

        "priority_workflows": [
            "approve requests",
        ],
    }

    if target_region_marker:
        result[
            "target_region"
        ] = target_region

    if market_region_marker:
        result[
            "market_region"
        ] = market_region

    return result


def _neutral_archetype():
    return {
        "project_archetype":
            "generic",

        "vertical":
            "generic operations",

        "actors": {},

        "target_users": [],

        "priority_workflows": [],

        "search_terms": [],

        "search_queries": {
            "all": [],
        },
    }


def _planner():
    return {
        "queries_by_intent": {
            "local_solutions": [
                "planneralpha canonland local solutions",
            ],

            "direct_competitors": [
                "plannerbeta canonland competitors",
            ],

            "market_sources": [
                "plannergamma canonland market evidence",
            ],

            "official_sources": [
                "plannerdelta canonland official evidence",
            ],

            "field_validation": [
                "plannerepsilon canonland field validation",
            ],
        }
    }


def _context(
    structured,
    *,
    planner=None,
):
    result = {
        "context_locked":
            True,

        "structured_project_context":
            copy.deepcopy(
                structured
            ),

        "project_intelligence": {
            "structured_project_context":
                copy.deepcopy(
                    structured
                ),
        },

        "agent_context_packet": {
            "structured_project_context":
                copy.deepcopy(
                    structured
                ),
        },

        "domain_concepts": [],
        "search_concepts": [],
        "use_case_terms": [],
        "must_match_terms": [],
    }

    # Mirror canonical region aliases at the outer packet when present.
    for field in (
        "target_region",
        "market_region",
    ):
        if field in structured:
            result[
                field
            ] = structured[
                field
            ]

    if planner is not None:
        result[
            "query_planner"
        ] = copy.deepcopy(
            planner
        )

        result[
            "project_intelligence"
        ][
            "query_planner"
        ] = copy.deepcopy(
            planner
        )

    return result


def _normalized(
    queries,
):
    return [
        module.normalize_text(
            str(
                query
            )
        )
        for query in queries
    ]


def test_locked_target_region_overrides_conflicting_downstream_region_for_fallback_queries() -> None:
    service = _service()

    structured = (
        _canonical_structured()
    )

    context = (
        _context(
            structured
        )
    )

    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        return_value=(
            _neutral_archetype()
        ),
    ):
        queries = (
            service.build_queries(
                sector="Generic Operations",
                region="Driftland",
                description="Generic operational service.",
                project_context=context,
            )
        )

    normalized = (
        _normalized(
            queries
        )
    )

    assert any(
        "canonland"
        in query
        for query in normalized
    ), queries

    assert not any(
        "driftland"
        in query
        for query in normalized
    ), queries


def test_locked_planner_and_enrichment_use_one_canonical_region() -> None:
    service = _service()

    structured = (
        _canonical_structured()
    )

    context = (
        _context(
            structured,
            planner=_planner(),
        )
    )

    # Existing archetype prevents unrelated resolver variability.
    archetype = {
        "project_archetype":
            "generic",

        "vertical":
            "generic",

        "search_terms": [],

        "search_queries": {
            "all": [],
        },
    }

    context[
        "archetype_context"
    ] = copy.deepcopy(
        archetype
    )

    context[
        "project_intelligence"
    ][
        "archetype_context"
    ] = copy.deepcopy(
        archetype
    )

    context[
        "agent_context_packet"
    ][
        "archetype_context"
    ] = copy.deepcopy(
        archetype
    )

    queries = (
        service.build_queries(
            sector="Generic Operations",
            region="Driftland",
            description="Generic operational service.",
            project_context=context,
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    planner_markers = (
        "planneralpha",
        "plannerbeta",
        "plannergamma",
        "plannerdelta",
        "plannerepsilon",
    )

    for marker in planner_markers:
        assert any(
            marker
            in query
            for query in normalized
        ), (
            marker,
            queries,
        )

    # No secondary LocalMarket candidate may reintroduce the caller's
    # conflicting geography.
    assert not any(
        "driftland"
        in query
        for query in normalized
    ), queries

    assert any(
        "canonland"
        in query
        for query in normalized
    ), queries


def test_locked_canonical_region_is_passed_to_archetype_resolver() -> None:
    service = _service()

    structured = (
        _canonical_structured()
    )

    context = (
        _context(
            structured
        )
    )

    captured = {}


    def fake_resolve(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return (
            _neutral_archetype()
        )


    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        side_effect=fake_resolve,
    ):
        service.build_queries(
            sector="Generic Operations",
            region="Driftland",
            description="Generic operational service.",
            project_context=context,
        )

    assert (
        captured.get(
            "target_region"
        )
        == "Canonland"
    ), captured


def test_locked_explicit_empty_target_region_does_not_fall_back_to_downstream_region() -> None:
    service = _service()

    structured = (
        _canonical_structured(
            target_region_marker=True,
            target_region="",
            market_region_marker=True,
            market_region="",
        )
    )

    context = (
        _context(
            structured
        )
    )

    captured = {}


    def fake_resolve(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return (
            _neutral_archetype()
        )


    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        side_effect=fake_resolve,
    ):
        queries = (
            service.build_queries(
                sector="Generic Operations",
                region="Driftland",
                description="Generic operational service.",
                project_context=context,
            )
        )

    normalized = (
        _normalized(
            queries
        )
    )

    assert not any(
        "driftland"
        in query
        for query in normalized
    ), queries

    assert (
        captured.get(
            "target_region"
        )
        == ""
    ), captured


def test_locked_market_region_alias_is_authoritative_when_target_region_key_is_absent() -> None:
    service = _service()

    structured = (
        _canonical_structured(
            target_region_marker=False,
            market_region_marker=True,
            market_region="Canonland",
        )
    )

    context = (
        _context(
            structured
        )
    )

    captured = {}


    def fake_resolve(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return (
            _neutral_archetype()
        )


    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        side_effect=fake_resolve,
    ):
        queries = (
            service.build_queries(
                sector="Generic Operations",
                region="Driftland",
                description="Generic operational service.",
                project_context=context,
            )
        )

    normalized = (
        _normalized(
            queries
        )
    )

    assert any(
        "canonland"
        in query
        for query in normalized
    ), queries

    assert not any(
        "driftland"
        in query
        for query in normalized
    ), queries

    assert (
        captured.get(
            "target_region"
        )
        == "Canonland"
    ), captured


def test_unlocked_context_preserves_downstream_region_fallback_behavior() -> None:
    service = _service()

    structured = {
        "context_locked":
            False,

        "project_archetype":
            "generic",

        "vertical":
            "generic operations",

        "actors": {
            "primary_user":
                "operations users",
        },

        "target_users": [
            "operations users",
        ],

        "priority_workflows": [
            "approve requests",
        ],
    }

    context = {
        "context_locked":
            False,

        "structured_project_context":
            copy.deepcopy(
                structured
            ),

        "project_intelligence": {
            "structured_project_context":
                copy.deepcopy(
                    structured
                ),
        },

        "agent_context_packet": {
            "structured_project_context":
                copy.deepcopy(
                    structured
                ),
        },
    }

    with patch.object(
        module.project_archetype_resolver,
        "resolve",
        return_value=(
            _neutral_archetype()
        ),
    ):
        queries = (
            service.build_queries(
                sector="Generic Operations",
                region="Driftland",
                description="Generic operational service.",
                project_context=context,
            )
        )

    normalized = (
        _normalized(
            queries
        )
    )

    assert any(
        "driftland"
        in query
        for query in normalized
    ), queries
