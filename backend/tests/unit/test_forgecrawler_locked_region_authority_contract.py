from __future__ import annotations

import copy
import inspect

from app.services.forgecrawler import (
    ForgeCrawler,
)


def _service() -> ForgeCrawler:
    service = (
        ForgeCrawler.__new__(
            ForgeCrawler
        )
    )

    service.max_queries = 8

    return service


def _structured(
    *,
    target_region_marker: bool = True,
    target_region: str = "Canonland",
    market_region_marker: bool = True,
    market_region: str = "Canonland",
    locked: bool = True,
):
    result = {
        "context_locked":
            locked,

        "project_name":
            "GenericOps",

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

        "domain_concepts": [
            "generic operations",
        ],

        "use_case_terms": [
            "approve requests",
        ],

        "strong_keywords": [
            "generic operations",
            "approve requests",
        ],

        "must_match_terms": [
            "generic operations",
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


def _packet(
    structured,
):
    return {
        "structured_project_context":
            copy.deepcopy(
                structured
            ),

        "strong_keywords":
            copy.deepcopy(
                structured.get(
                    "strong_keywords"
                )
                or []
            ),

        "must_match_terms":
            copy.deepcopy(
                structured.get(
                    "must_match_terms"
                )
                or []
            ),
    }


def _planner():
    # Business-specific queries known from QA10.2A.1 to survive
    # ForgeCrawler query-quality filtering.
    return {
        "queries_by_intent": {
            "direct_competitors": [
                (
                    "planneralpha generic operations "
                    "direct competitors Canonland"
                ),
            ],

            "adjacent_solutions": [
                (
                    "plannerbeta approve requests "
                    "adjacent solutions Canonland"
                ),
            ],

            "regional_benchmarks": [
                (
                    "plannergamma generic operations "
                    "regional benchmark Canonland"
                ),
            ],

            "market_sources": [
                (
                    "plannerdelta generic operations "
                    "market evidence Canonland"
                ),
            ],

            "field_validation": [
                (
                    "plannerepsilon approve requests "
                    "field validation Canonland"
                ),
            ],
        }
    }


def _base_context(
    structured,
    *,
    include_outer_regions: bool,
    planner=None,
):
    result = {
        "context_locked":
            bool(
                structured.get(
                    "context_locked"
                )
            ),

        "project_name":
            "GenericOps",

        "description":
            (
                "Generic operational service "
                "for operations users."
            ),

        "industry":
            "Generic Operations",

        "structured_project_context":
            copy.deepcopy(
                structured
            ),

        "agent_context_packet":
            _packet(
                structured
            ),

        "strong_keywords":
            copy.deepcopy(
                structured.get(
                    "strong_keywords"
                )
                or []
            ),

        "must_match_terms":
            copy.deepcopy(
                structured.get(
                    "must_match_terms"
                )
                or []
            ),
    }

    if include_outer_regions:
        if "target_region" in structured:
            result[
                "target_region"
            ] = structured[
                "target_region"
            ]

        if "market_region" in structured:
            result[
                "market_region"
            ] = structured[
                "market_region"
            ]

    if planner is not None:
        result[
            "query_planner"
        ] = copy.deepcopy(
            planner
        )

    return result


def _build_context(
    service,
    *,
    structured,
    include_outer_regions,
    caller_region,
    planner=None,
):
    packet = (
        _packet(
            structured
        )
    )

    return (
        service._build_project_context(
            idea=(
                "Generic operational service "
                "for operations users."
            ),
            industry="Generic Operations",
            region=caller_region,
            project_context=(
                _base_context(
                    structured,
                    include_outer_regions=(
                        include_outer_regions
                    ),
                    planner=planner,
                )
            ),
            agent_context_packet=packet,
            query_planner=(
                copy.deepcopy(
                    planner
                )
                if planner is not None
                else {}
            ),
        )
    )


def _normalized(
    queries,
):
    return [
        str(
            query
        ).lower()
        for query in queries
    ]


def test_locked_structured_region_projects_to_top_level_when_outer_aliases_are_missing() -> None:
    service = _service()

    structured = (
        _structured()
    )

    built = (
        _build_context(
            service,
            structured=structured,
            include_outer_regions=False,
            caller_region="Driftland",
        )
    )

    assert (
        built.get(
            "target_region"
        )
        == "Canonland"
    ), built

    assert (
        built.get(
            "market_region"
        )
        == "Canonland"
    ), built


def test_locked_structured_explicit_empty_region_remains_empty_across_surfaces() -> None:
    service = _service()

    structured = (
        _structured(
            target_region="",
            market_region="",
        )
    )

    built = (
        _build_context(
            service,
            structured=structured,
            include_outer_regions=False,
            caller_region="Driftland",
        )
    )

    assert (
        built.get(
            "target_region"
        )
        == ""
    ), built

    assert (
        built.get(
            "market_region"
        )
        == ""
    ), built

    structured_out = dict(
        built.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        structured_out.get(
            "target_region"
        )
        == ""
    )

    assert (
        structured_out.get(
            "market_region"
        )
        == ""
    )


def test_locked_query_generation_uses_canonical_region_not_conflicting_caller_region() -> None:
    service = _service()

    structured = (
        _structured()
    )

    planner = (
        _planner()
    )

    built = (
        _build_context(
            service,
            structured=structured,
            include_outer_regions=True,
            caller_region="Driftland",
            planner=planner,
        )
    )

    queries = (
        service._build_queries(
            idea=(
                "Generic operational service "
                "for operations users."
            ),
            industry="Generic Operations",
            region="Driftland",
            project_context=built,
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    # Planner queries are already canonical and must survive.
    for marker in (
        "planneralpha",
        "plannerbeta",
        "plannergamma",
        "plannerdelta",
        "plannerepsilon",
    ):
        assert any(
            marker
            in query
            for query in normalized
        ), (
            marker,
            queries,
        )

    # Generated ForgeCrawler queries must use the SAME canonical
    # geography instead of reintroducing the caller's conflicting value.
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


def test_crawl_competitors_public_target_region_must_not_project_clean_caller_region() -> None:
    # Public projection is frozen here as a topology contract.
    #
    # QA10.2A.1 already proved that clean_region is the raw method
    # argument while the canonical context may contain another region.
    source = inspect.getsource(
        ForgeCrawler.crawl_competitors
    )

    assert (
        '"target_region": clean_region'
        not in source
    ), source


def test_locked_existing_top_level_region_remains_preserved() -> None:
    # GREEN preservation control.
    service = _service()

    structured = (
        _structured()
    )

    built = (
        _build_context(
            service,
            structured=structured,
            include_outer_regions=True,
            caller_region="Driftland",
        )
    )

    assert (
        built.get(
            "target_region"
        )
        == "Canonland"
    )

    assert (
        built.get(
            "market_region"
        )
        == "Canonland"
    )


def test_unlocked_context_preserves_caller_region_compatibility() -> None:
    # GREEN legacy compatibility control.
    service = _service()

    structured = (
        _structured(
            target_region_marker=False,
            market_region_marker=False,
            locked=False,
        )
    )

    built = (
        _build_context(
            service,
            structured=structured,
            include_outer_regions=False,
            caller_region="Driftland",
        )
    )

    assert (
        built.get(
            "target_region"
        )
        == "Driftland"
    )

    assert (
        built.get(
            "market_region"
        )
        == "Driftland"
    )

    queries = (
        service._build_queries(
            idea=(
                "Generic operational service "
                "for operations users."
            ),
            industry="Generic Operations",
            region="Driftland",
            project_context=built,
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
