from __future__ import annotations

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


ADVISORY_ARCHETYPE = {
    "project_archetype":
        "b2b_workflow_saas",

    "primary_archetype":
        "b2b_workflow_saas",

    "vertical":
        "general",

    "business_motion":
        "b2b",

    "interaction_model":
        "workflow",

    # Advisory discovery hint.
    #
    # It is useful when no project-specific domain is known, but it may
    # never replace an explicit current project domain.
    "search_terms": [
        "workflow management software",
        "operations workflow software",
    ],

    "search_queries":
        {},
}


DOMAIN_INTENTS = (
    "direct_competitors",
    "local_solutions",
    "official_sources",
    "market_sources",
    "adjacent_solutions",
    "pricing",
)


def _normalize(
    value,
) -> str:
    return " ".join(
        str(
            value
            or ""
        )
        .casefold()
        .split()
    )


def _planner(
    *,
    industry: str,
    domain: str,
    archetype_context=None,
):
    return (
        project_intelligence_layer
        ._query_planner(
            title="Neutral Domain Authority",
            industry=industry,
            target_region="Global",
            target_users=[
                "operations managers",
                "field operators",
            ],
            problem=(
                "Recurring operational work is coordinated manually."
            ),
            solution=(
                "Centralize domain-specific requests and completed work."
            ),
            main_use_case=(
                "manage field intervention"
            ),
            business_model=(
                "B2B subscription"
            ),
            strong_keywords=[
                domain,
                "field operations",
            ],
            sector_profile={},
            language="en",
            search_concepts=[
                domain,
                "field operations",
            ],
            domain_concepts=[
                domain,
            ],
            use_case_terms=[
                "manage field intervention",
                "review completed work",
            ],
            solution_terms=[
                domain,
            ],
            target_terms=[
                "operations managers",
            ],
            archetype_context=(
                archetype_context
                if archetype_context is not None
                else ADVISORY_ARCHETYPE
            ),
        )
    )


def _intent_queries(
    planner,
):
    by_intent = (
        planner.get(
            "queries_by_intent"
        )
        or {}
    )

    return {
        intent:
            [
                str(value)
                for value in (
                    by_intent.get(
                        intent
                    )
                    or []
                )
            ]
        for intent in DOMAIN_INTENTS
    }


def _all_queries(
    planner,
):
    result = []

    for values in (
        _intent_queries(
            planner
        )
        .values()
    ):
        result.extend(
            values
        )

    result.extend(
        str(value)
        for value in (
            planner.get(
                "queries"
            )
            or []
        )
    )

    result.extend(
        str(value)
        for value in (
            planner.get(
                "verification_queries"
            )
            or []
        )
    )

    return result


def _blob(
    values,
) -> str:
    return _normalize(
        " ".join(
            values
        )
    )


def _assert_domain_in_domain_intents(
    planner,
    marker: str,
) -> None:

    intents = _intent_queries(
        planner
    )

    missing = []

    for intent, queries in intents.items():

        if not queries:
            continue

        if marker not in _blob(
            queries
        ):
            missing.append(
                {
                    "intent":
                        intent,

                    "queries":
                        queries,
                }
            )

    assert missing == [], {
        "marker":
            marker,
        "missing":
            missing,
        "planner":
            planner,
    }


def test_explicit_specific_industry_outranks_advisory_archetype_domain() -> None:
    """
    Explicit current project domain is higher authority than an advisory
    archetype discovery hint.

    The advisory hint may enrich research, but it must not become the
    executable domain when a specific current industry is available.
    """

    planner = _planner(
        industry=(
            "Cryogenic Logistics Operations"
        ),
        domain=(
            "cryogenic logistics operations"
        ),
    )

    queries = _all_queries(
        planner
    )

    assert (
        "cryogenic"
        in
        _normalize(
            planner.get(
                "base_context"
            )
        )
    ), planner

    assert (
        "cryogenic"
        in
        _blob(
            queries
        )
    ), planner

    _assert_domain_in_domain_intents(
        planner,
        "cryogenic",
    )


def test_changing_only_explicit_domain_changes_executable_query_identity() -> None:
    """
    Metamorphic authority invariant.

    With the same generic advisory archetype and the same workflow, users,
    region and business model, changing the explicit project domain must
    change executable search identity.
    """

    first = _planner(
        industry=(
            "Cryogenic Logistics Operations"
        ),
        domain=(
            "cryogenic logistics operations"
        ),
    )

    second = _planner(
        industry=(
            "Ceramic Kiln Quality Control"
        ),
        domain=(
            "ceramic kiln quality control"
        ),
    )

    first_queries = {
        _normalize(value)
        for value in _all_queries(
            first
        )
    }

    second_queries = {
        _normalize(value)
        for value in _all_queries(
            second
        )
    }

    assert (
        "cryogenic"
        in
        _blob(
            first_queries
        )
    ), first

    assert (
        "ceramic"
        in
        _blob(
            second_queries
        )
    ), second

    assert (
        first_queries
        !=
        second_queries
    ), {
        "first":
            sorted(
                first_queries
            ),
        "second":
            sorted(
                second_queries
            ),
    }


def test_advisory_archetype_hint_cannot_replace_explicit_domain_across_intents() -> None:
    """
    Archetype search terms remain enrichment metadata.

    They may not replace the explicit project's domain in the research
    intents whose purpose is domain-level competitor and market discovery.
    """

    planner = _planner(
        industry=(
            "Marine Corrosion Inspection"
        ),
        domain=(
            "marine corrosion inspection"
        ),
    )

    _assert_domain_in_domain_intents(
        planner,
        "marine",
    )


def test_generic_industry_can_still_fall_back_to_archetype_domain() -> None:
    """
    Recall/fallback preservation.

    When the explicit industry is genuinely generic, an advisory archetype
    domain remains a legitimate fallback.
    """

    planner = _planner(
        industry="Software",
        domain="",
    )

    assert (
        "workflow management"
        in
        _blob(
            _all_queries(
                planner
            )
        )
    ), planner


def test_explicit_domain_works_when_archetype_has_no_search_hint() -> None:
    """
    Existing explicit-domain path remains valid without enrichment.
    """

    planner = _planner(
        industry=(
            "Precision Coating Inspection"
        ),
        domain=(
            "precision coating inspection"
        ),
        archetype_context={
            "project_archetype":
                "b2b_workflow_saas",

            "primary_archetype":
                "b2b_workflow_saas",

            "vertical":
                "general",

            "search_terms":
                [],

            "search_queries":
                {},
        },
    )

    assert (
        "precision"
        in
        _blob(
            _all_queries(
                planner
            )
        )
    ), planner


def test_canonical_domain_outranks_generic_fallback_when_explicit_industry_is_generic() -> None:
    """
    Canonical project-domain authority must survive when the raw industry
    label is generic and no advisory archetype search hint is available.

    A synthetic generic fallback such as "business sector" must never
    outrank a concrete canonical project-domain concept.
    """

    planner = _planner(
        industry="Software",
        domain=(
            "marine corrosion inspection"
        ),
        archetype_context={
            "project_archetype":
                "b2b_workflow_saas",

            "primary_archetype":
                "b2b_workflow_saas",

            "vertical":
                "general",

            "search_terms":
                [],

            "search_queries":
                {},
        },
    )

    assert (
        "marine"
        in
        _normalize(
            planner.get(
                "base_context"
            )
        )
    ), planner

    assert (
        "marine"
        in
        _blob(
            _all_queries(
                planner
            )
        )
    ), planner

    _assert_domain_in_domain_intents(
        planner,
        "marine",
    )


def test_canonical_domain_outranks_advisory_archetype_when_explicit_industry_is_generic() -> None:
    """
    Canonical structured project-domain evidence has higher authority than
    an advisory archetype discovery hint.

    The archetype hint remains useful only after explicit and canonical
    domain authorities are unavailable.
    """

    planner = _planner(
        industry="Software",
        domain=(
            "marine corrosion inspection"
        ),
    )

    assert (
        "marine"
        in
        _normalize(
            planner.get(
                "base_context"
            )
        )
    ), planner

    assert (
        "marine"
        in
        _blob(
            _all_queries(
                planner
            )
        )
    ), planner

    _assert_domain_in_domain_intents(
        planner,
        "marine",
    )
