from __future__ import annotations

import copy

import app.web_search.local_market_search as module


def _service():
    return (
        module.LocalMarketSearchService
        .__new__(
            module.LocalMarketSearchService
        )
    )


def _structured(
    *,
    locked: bool,
):
    return {
        "context_locked":
            locked,

        "project_archetype":
            "generic operating model",

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
            "approve operational request",
        ],
    }


def _planner():
    # These are the EXACT intent keys consumed by build_queries().
    return {
        "queries_by_intent": {
            "local_solutions": [
                "planneralpha local solution evidence",
            ],

            "direct_competitors": [
                "plannerbeta direct competitor evidence",
            ],

            "market_sources": [
                "plannergamma market source evidence",
            ],

            "official_sources": [
                "plannerdelta official source evidence",
            ],

            "field_validation": [
                "plannerepsilon field validation evidence",
            ],
        }
    }


def _archetype_with_many_queries():
    # More than enough candidates to fill the final [:6] capacity
    # before planner candidates under the current implementation.
    return {
        "project_archetype":
            "generic",

        "vertical":
            "generic operations",

        "actors": {
            "primary_user":
                "inferred users",
        },

        "priority_workflows": [
            "inferred workflow",
        ],

        "search_terms": [
            "neutral discovery enrichment",
        ],

        "search_queries": {
            "local_fr": [
                "archealpha local discovery one",
                "archebeta local discovery two",
                "archegamma local discovery three",
            ],

            "local_en": [
                "archedelta local discovery four",
                "archeepsilon local discovery five",
                "archezeta local discovery six",
            ],

            "all": [
                "archeeta generic discovery seven",
                "archetheta generic discovery eight",
            ],
        },
    }


def _context(
    *,
    locked: bool,
    planner=None,
    archetype=None,
):
    structured = (
        _structured(
            locked=locked,
        )
    )

    result = {
        "context_locked":
            locked,

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

    if archetype is not None:
        result[
            "archetype_context"
        ] = copy.deepcopy(
            archetype
        )

        result[
            "project_intelligence"
        ][
            "archetype_context"
        ] = copy.deepcopy(
            archetype
        )

        result[
            "agent_context_packet"
        ][
            "archetype_context"
        ] = copy.deepcopy(
            archetype
        )

    return result


def _queries(
    context,
):
    service = _service()

    return (
        service.build_queries(
            sector="Generic Operations",
            region="Test Region",
            description="Generic operational description.",
            project_context=context,
        )
    )


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


def _planner_markers():
    return [
        "planneralpha",
        "plannerbeta",
        "plannergamma",
        "plannerdelta",
        "plannerepsilon",
    ]


def test_locked_canonical_planner_queries_cannot_be_crowded_out_by_archetype_queries() -> None:
    queries = (
        _queries(
            _context(
                locked=True,
                planner=_planner(),
                archetype=(
                    _archetype_with_many_queries()
                ),
            )
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    # Every canonical planner intent supplied to the local-search
    # consumer must survive the final six-query projection.
    for marker in (
        _planner_markers()
    ):
        assert any(
            marker
            in query
            for query in normalized
        ), (
            marker,
            queries,
        )


def test_locked_canonical_planner_is_primary_before_archetype_enrichment() -> None:
    queries = (
        _queries(
            _context(
                locked=True,
                planner=_planner(),
                archetype=(
                    _archetype_with_many_queries()
                ),
            )
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    assert len(
        normalized
    ) <= 6

    # Five planner intents exist. They must occupy the first five
    # positions; the remaining capacity may be used by enrichment.
    expected = (
        _planner_markers()
    )

    actual = []

    for query in normalized[:5]:
        matched = next(
            (
                marker
                for marker in expected
                if marker in query
            ),
            None,
        )

        actual.append(
            matched
        )

    assert (
        actual
        == expected
    ), (
        expected,
        actual,
        queries,
    )


def test_locked_planner_queries_cannot_be_crowded_out_by_generic_fallback() -> None:
    # No archetype query candidates.
    #
    # Current production also builds generic primary/workflow fallback
    # candidates BEFORE planner candidates. This test freezes the same
    # authority rule for that path.
    archetype = {
        "project_archetype":
            "generic",

        "vertical":
            "generic operations",

        "search_terms": [],

        "search_queries": {
            "all": [],
        },
    }

    queries = (
        _queries(
            _context(
                locked=True,
                planner=_planner(),
                archetype=archetype,
            )
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    for marker in (
        _planner_markers()
    ):
        assert any(
            marker
            in query
            for query in normalized
        ), (
            marker,
            queries,
        )


def test_unlocked_context_without_planner_keeps_archetype_fallback() -> None:
    queries = (
        _queries(
            _context(
                locked=False,
                planner=None,
                archetype=(
                    _archetype_with_many_queries()
                ),
            )
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    # Archetype enrichment must survive without a usable
    # canonical planner, but raw archetype search_queries are
    # non-authoritative metadata and must never be executed.
    assert any(
        "neutral discovery enrichment"
        in query
        and "test region"
        in query
        for query in normalized
    ), queries

    assert not any(
        "archealpha" in query
        or "archebeta" in query
        or "archegamma" in query
        or "archedelta" in query
        or "archeepsilon" in query
        or "archezeta" in query
        or "archeeta" in query
        or "archetheta" in query
        for query in normalized
    ), queries


def test_locked_context_with_empty_planner_can_still_use_archetype_enrichment() -> None:
    empty_planner = {
        "queries_by_intent": {},
    }

    queries = (
        _queries(
            _context(
                locked=True,
                planner=empty_planner,
                archetype=(
                    _archetype_with_many_queries()
                ),
            )
        )
    )

    normalized = (
        _normalized(
            queries
        )
    )

    # Archetype enrichment must survive without a usable
    # canonical planner, but raw archetype search_queries are
    # non-authoritative metadata and must never be executed.
    assert any(
        "neutral discovery enrichment"
        in query
        and "test region"
        in query
        for query in normalized
    ), queries

    assert not any(
        "archealpha" in query
        or "archebeta" in query
        or "archegamma" in query
        or "archedelta" in query
        or "archeepsilon" in query
        or "archezeta" in query
        or "archeeta" in query
        or "archetheta" in query
        for query in normalized
    ), queries
