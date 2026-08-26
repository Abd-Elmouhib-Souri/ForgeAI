from __future__ import annotations

import inspect

import pytest

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)

from app.services.forgecrawler import (
    ForgeCrawler,
)


def synthetic_profile():
    """
    Sector profiles are semantic/domain hints.

    Driftland deliberately represents stale profile geography.
    It must never become execution geography.
    """
    return {
        "queries": {
            "direct_competitors": [
                (
                    "Driftland workforce "
                    "scheduling software"
                ),
                (
                    "Driftland employee "
                    "shift planning software"
                ),
            ],
            "adjacent_solutions": [
                (
                    "Driftland workforce "
                    "attendance platform"
                ),
            ],
            "market_sources": [
                (
                    "Driftland workforce "
                    "digital adoption study"
                ),
            ],
            "pricing": [
                (
                    "workforce scheduling "
                    "software pricing"
                ),
            ],
        },
    }


def planner(
    region: str,
):
    service = (
        project_intelligence_layer
    )

    kwargs = {
        "title":
            "UniversalRegionAuthority",

        "industry":
            "workforce scheduling",

        "target_region":
            region,

        "target_users":
            [
                "operations teams",
                "shift supervisors",
            ],

        "problem":
            (
                "manual workforce "
                "scheduling"
            ),

        "solution":
            (
                "workforce scheduling "
                "software"
            ),

        "main_use_case":
            (
                "publish schedules "
                "and manage attendance"
            ),

        "business_model":
            "subscription",

        "strong_keywords":
            [
                "workforce scheduling",
                "shift planning",
                "attendance",
            ],

        "sector_profile":
            synthetic_profile(),

        "language":
            "en",

        "search_concepts":
            [
                "workforce scheduling",
                "shift planning",
                "attendance",
            ],

        "domain_concepts":
            [
                "workforce scheduling",
                "shift planning",
            ],

        "use_case_terms":
            [
                "publish schedules",
                "manage attendance",
            ],

        "solution_terms":
            [
                (
                    "workforce scheduling "
                    "software"
                ),
            ],

        "target_terms":
            [
                "shift supervisors",
            ],

        "archetype_context":
            {},
    }

    signature = inspect.signature(
        service._query_planner
    )

    supported = {
        key: value
        for key, value
        in kwargs.items()
        if key
        in signature.parameters
    }

    return service._query_planner(
        **supported
    )


def all_intent_queries(
    value,
):
    result = []

    intents = (
        value.get(
            "queries_by_intent"
        )
        or {}
    )

    for queries in intents.values():

        if not isinstance(
            queries,
            list,
        ):
            continue

        result.extend(
            str(query)
            for query in queries
        )

    return result


def normalized(
    values,
):
    return [
        str(value).casefold()
        for value in values
    ]


@pytest.mark.parametrize(
    "canonical_region",
    [
        "Canonland",
        "Altland",
    ],
)
def test_profile_geography_cannot_override_canonical_region(
    canonical_region,
):
    value = planner(
        canonical_region
    )

    queries = normalized(
        all_intent_queries(
            value
        )
    )

    assert not any(
        "driftland" in query
        for query in queries
    ), value

    region = (
        canonical_region
        .casefold()
    )

    region_sensitive = (
        value.get(
            "queries_by_intent"
        )
        or {}
    )

    generated = []

    for intent in (
        "direct_competitors",
        "local_solutions",
        "official_sources",
        "market_sources",
        "field_validation",
    ):
        generated.extend(
            region_sensitive.get(
                intent
            )
            or []
        )

    assert any(
        region
        in str(query).casefold()
        for query in generated
    ), value


def test_profile_geography_cannot_invent_region_when_region_is_empty():
    value = planner(
        ""
    )

    queries = normalized(
        all_intent_queries(
            value
        )
    )

    assert not any(
        "driftland" in query
        for query in queries
    ), value


def test_balanced_query_projection_cannot_hide_dirty_intent_state():
    value = planner(
        "Canonland"
    )

    intent_queries = normalized(
        all_intent_queries(
            value
        )
    )

    top_level = normalized(
        value.get(
            "queries"
        )
        or []
    )

    # Both public planner surfaces must obey the same
    # geography authority. A clean balanced projection
    # may not hide contaminated intent state.
    assert not any(
        "driftland" in query
        for query in intent_queries
    ), {
        "queries_by_intent":
            value.get(
                "queries_by_intent"
            ),

        "queries":
            value.get(
                "queries"
            ),
    }

    assert not any(
        "driftland" in query
        for query in top_level
    ), value


def test_forgecrawler_cannot_reactivate_profile_geography():
    value = planner(
        "Canonland"
    )

    crawler = ForgeCrawler()

    structured = {
        "context_locked":
            True,

        "project_name":
            "UniversalRegionAuthority",

        "description":
            (
                "Workforce scheduling "
                "software for operations teams."
            ),

        "industry":
            "workforce scheduling",

        "target_region":
            "Canonland",

        "market_region":
            "Canonland",

        "target_users":
            [
                "operations teams",
                "shift supervisors",
            ],

        "solution_category":
            "workforce scheduling software",

        "priority_workflows":
            [
                "publish schedules",
                "manage attendance",
            ],

        "use_case_terms":
            [
                "publish schedules",
                "manage attendance",
            ],

        "solution_terms":
            [
                "workforce scheduling software",
            ],
    }

    context = {
        "context_locked":
            True,

        "project_name":
            "UniversalRegionAuthority",

        "title":
            "UniversalRegionAuthority",

        "description":
            structured[
                "description"
            ],

        "industry":
            structured[
                "industry"
            ],

        "target_region":
            "Canonland",

        "market_region":
            "Canonland",

        "structured_project_context":
            structured,

        "query_planner":
            value,

        "project_intelligence":
            {
                "context_locked":
                    True,

                "structured_project_context":
                    structured,

                "query_planner":
                    value,
            },

        "agent_context_packet":
            {
                "context_locked":
                    True,

                "structured_project_context":
                    structured,

                "query_planner":
                    value,
            },

        "strong_keywords":
            [
                "workforce scheduling",
                "shift planning",
                "attendance",
            ],

        "must_match_terms":
            [
                "workforce scheduling",
                "shift planning",
            ],
    }

    built = (
        crawler._build_project_context(
            idea=structured[
                "description"
            ],
            industry=structured[
                "industry"
            ],
            region="Canonland",
            project_context=context,
            agent_context_packet=(
                context[
                    "agent_context_packet"
                ]
            ),
            query_planner=value,
        )
    )

    queries = (
        crawler._build_queries(
            idea=structured[
                "description"
            ],
            industry=structured[
                "industry"
            ],
            region="Canonland",
            project_context=built,
        )
    )

    lowered = normalized(
        queries
    )

    assert built.get(
        "target_region"
    ) == "Canonland"

    assert built.get(
        "market_region"
    ) == "Canonland"

    assert not any(
        "driftland" in query
        for query in lowered
    ), queries

    assert any(
        "canonland" in query
        for query in lowered
    ), queries
