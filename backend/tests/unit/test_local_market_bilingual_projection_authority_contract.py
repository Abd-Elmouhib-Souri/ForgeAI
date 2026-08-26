from __future__ import annotations

import pytest

from app.web_search.local_market_search import (
    LocalMarketSearchService,
)


PLANNER_MARKERS = (
    "planneralpha",
    "plannerbeta",
    "plannergamma",
    "plannerdelta",
    "plannerepsilon",
)


def _context(
    domain: str,
    search_terms: list[str],
):
    planner = {
        "queries_by_intent": {
            "local_solutions": [
                (
                    "planneralpha tunisie "
                    f"{domain} application"
                ),
            ],

            "direct_competitors": [
                (
                    "plannerbeta "
                    f"{domain} software tunisie"
                ),
            ],

            "market_sources": [
                (
                    "plannergamma tunisie "
                    f"{domain} market report"
                ),
            ],

            "official_sources": [
                (
                    "plannerdelta tunisie "
                    f"{domain} official statistics"
                ),
            ],

            "field_validation": [
                (
                    "plannerepsilon tunisie "
                    f"{domain} workflow survey"
                ),
            ],
        },
    }

    archetype = {
        "project_archetype":
            "generic",

        "vertical":
            "generic",

        "search_terms":
            search_terms,

        # Deliberately dirty metadata.
        # It must never become executable.
        "search_queries": {
            "all": [
                "forbiddenraw Driftland",
            ],
        },
    }

    structured = {
        "context_locked":
            True,

        "project_archetype":
            "generic",

        "vertical":
            "generic",

        "priority_workflows":
            [],
    }

    return {
        "context_locked":
            True,

        "query_planner":
            planner,

        "structured_project_context":
            structured,

        "archetype_context":
            archetype,

        "project_intelligence": {
            "query_planner":
                planner,

            "structured_project_context":
                structured,

            "archetype_context":
                archetype,
        },

        "agent_context_packet": {
            "structured_project_context":
                structured,

            "archetype_context":
                archetype,
        },

        "domain_concepts":
            [],

        "search_concepts":
            [],

        "use_case_terms":
            [],

        "must_match_terms":
            [],
    }


@pytest.mark.parametrize(
    (
        "domain",
        "search_terms",
    ),
    (
        (
            "workforce scheduling",
            [
                "workforce scheduling",
                "employee scheduling",
            ],
        ),
        (
            "beekeeping hive management",
            [
                "beekeeping",
                "hive management",
            ],
        ),
        (
            "ride hailing",
            [
                "ride hailing",
                "taxi booking",
            ],
        ),
        (
            "internship platform",
            [
                "internship platform",
                "student recruitment",
            ],
        ),
    ),
)
def test_locked_bilingual_projection_preserves_planner_and_locale_diversity(
    domain: str,
    search_terms: list[str],
) -> None:

    service = (
        LocalMarketSearchService()
    )

    queries = service.build_queries(
        sector=domain,
        region="Tunisie",
        description=(
            f"{domain} local digital service"
        ),
        project_context=_context(
            domain,
            search_terms,
        ),
    )

    normalized = [
        str(query).casefold()
        for query in queries
    ]

    assert len(queries) <= 6

    # Five canonical planner intents retain authority
    # and occupy the first five projection slots.
    assert len(normalized) >= 5

    for index, marker in enumerate(
        PLANNER_MARKERS
    ):
        assert marker in normalized[index], (
            marker,
            index,
            queries,
        )

    # Both localized surfaces of the same canonical
    # market must survive the bounded projection.
    assert any(
        "tunisie"
        in query.split()
        for query in normalized
    ), queries

    assert any(
        "tunisia"
        in query.split()
        for query in normalized
    ), queries

    # Historical archetype query metadata remains
    # non-authoritative.
    assert not any(
        "forbiddenraw" in query
        or "driftland" in query
        for query in normalized
    ), queries
