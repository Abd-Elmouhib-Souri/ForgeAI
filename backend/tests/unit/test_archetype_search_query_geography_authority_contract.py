from __future__ import annotations

import inspect

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)

from app.web_search.local_market_search import (
    LocalMarketSearchService,
)


def archetype_context():
    """
    Archetype metadata deliberately contains stale geography.

    Search terms are valid semantic hints.
    Search-query strings are NOT execution geography authority.
    """
    return {
        "project_archetype":
            "operations_software",

        "vertical":
            "workforce",

        "search_terms":
            [
                "workforce scheduling",
                "shift planning",
                "attendance tracking",
            ],

        "search_queries": {
            "local_fr": [
                (
                    "logiciel workforce "
                    "Driftland"
                ),
            ],

            "local_en": [
                (
                    "workforce scheduling "
                    "software Driftland"
                ),
            ],

            "all": [
                (
                    "employee scheduling "
                    "Driftland"
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
            "ArchetypeRegionAuthority",

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
                "attendance tracking",
            ],

        # Keep sector profile neutral so this contract isolates
        # archetype_context.search_queries only.
        "sector_profile":
            {},

        "language":
            "en",

        "search_concepts":
            [
                "workforce scheduling",
                "shift planning",
                "attendance tracking",
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
            archetype_context(),
    }

    signature = inspect.signature(
        service._query_planner
    )

    return service._query_planner(
        **{
            key: value
            for key, value
            in kwargs.items()
            if key
            in signature.parameters
        }
    )


def planner_strings(value):
    result = []

    intents = (
        value.get(
            "queries_by_intent"
        )
        or {}
    )

    for values in intents.values():

        if isinstance(
            values,
            list,
        ):
            result.extend(
                str(item)
                for item in values
            )

    result.extend(
        str(item)
        for item in (
            value.get(
                "queries"
            )
            or []
        )
    )

    result.extend(
        str(item)
        for item in (
            value.get(
                "verification_queries"
            )
            or []
        )
    )

    return result


def test_pil_does_not_execute_archetype_search_query_geography():
    value = planner(
        "Canonland"
    )

    queries = [
        query.casefold()
        for query in planner_strings(
            value
        )
    ]

    assert not any(
        "driftland" in query
        for query in queries
    ), value

    assert any(
        "canonland" in query
        for query in queries
    ), value


def test_pil_does_not_invent_archetype_geography_when_region_empty():
    value = planner(
        ""
    )

    queries = [
        query.casefold()
        for query in planner_strings(
            value
        )
    ]

    assert not any(
        "driftland" in query
        for query in queries
    ), value


def test_local_market_search_does_not_execute_archetype_query_geography():
    service = (
        LocalMarketSearchService()
    )

    context = {
        "context_locked":
            True,

        "project_name":
            "ArchetypeRegionAuthority",

        "title":
            "ArchetypeRegionAuthority",

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

        "archetype_context":
            archetype_context(),

        "structured_project_context": {
            "context_locked":
                True,

            "target_region":
                "Canonland",

            "market_region":
                "Canonland",

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
                    (
                        "workforce scheduling "
                        "software"
                    ),
                ],
        },

        # Give LocalMarketSearch a clean planner.
        # Any Driftland result must therefore come from
        # archetype_context.search_queries itself.
        "query_planner": {
            "queries_by_intent": {
                "direct_competitors": [
                    (
                        "workforce scheduling "
                        "software Canonland"
                    ),
                ],

                "local_solutions": [
                    (
                        "workforce scheduling "
                        "platform Canonland"
                    ),
                ],
            },

            "queries": [
                (
                    "workforce scheduling "
                    "software Canonland"
                ),
            ],
        },

        "strong_keywords":
            [
                "workforce scheduling",
                "shift planning",
                "attendance tracking",
            ],

        "must_match_terms":
            [
                "workforce scheduling",
                "shift planning",
            ],
    }

    queries = (
        service.build_queries(
            sector="workforce scheduling",
            region="Canonland",
            description=(
                "Workforce scheduling "
                "software for operations teams."
            ),
            project_context=context,
        )
    )

    lowered = [
        str(query).casefold()
        for query in queries
    ]

    assert not any(
        "driftland" in query
        for query in lowered
    ), queries

    assert any(
        "canonland" in query
        for query in lowered
    ), queries
