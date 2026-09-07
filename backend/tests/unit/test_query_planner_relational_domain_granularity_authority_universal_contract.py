from __future__ import annotations

import inspect

import pytest

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


service = project_intelligence_layer


def _normalize(
    value,
) -> str:

    return (
        service
        ._normalize_concept(
            value
        )
    )


def _run(
    *,
    industry: str,
    domain_concepts: list[str],
    advisory_domain: str = "workflow management software",
):
    """
    Exercise the actual Query Planner authority.

    This contract deliberately separates:

    - explicit contextual truth;
    - broad category context;
    - substantive explicit domain facets;
    - canonical specialized domain identity;
    - lower-authority archetype advice.
    """

    values = {
        "title":
            "Neutral Relational Domain Boundary",

        "industry":
            industry,

        "target_region":
            "Global",

        "target_users":
            [
                "operations manager",
            ],

        "problem":
            (
                "The current process is fragmented "
                "and difficult to monitor."
            ),

        "solution":
            (
                "Centralize the specialized operational "
                "workflow and its evidence."
            ),

        "main_use_case":
            "manage specialized operational workflow",

        "business_model":
            "B2B subscription",

        "strong_keywords":
            list(
                domain_concepts
            ),

        "sector_profile":
            {},

        "language":
            "en",

        "search_concepts":
            list(
                domain_concepts
            ),

        "domain_concepts":
            list(
                domain_concepts
            ),

        "use_case_terms":
            [
                "manage specialized operational workflow",
            ],

        "solution_terms":
            list(
                domain_concepts
            ),

        "target_terms":
            [
                "operations manager",
            ],

        "archetype_context":
            {
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

                "search_terms":
                    [
                        advisory_domain,
                    ],

                "search_queries":
                    {},
            },
    }


    signature = inspect.signature(
        service._query_planner
    )


    kwargs = {
        key:
            value

        for key, value
        in values.items()

        if key in signature.parameters
    }


    return service._query_planner(
        **kwargs
    )


def _effective_domain(
    planner,
) -> str:

    return _normalize(
        str(
            planner.get(
                "base_context"
            )
            or ""
        )
        .split(
            " | ",
            1,
        )[0]
    )


def _query_blob(
    planner,
) -> str:

    values = []


    values.extend(
        str(value)
        for value in (
            planner.get(
                "queries"
            )
            or []
        )
    )


    values.extend(
        str(value)
        for value in (
            planner.get(
                "verification_queries"
            )
            or []
        )
    )


    for intent_values in (
        planner.get(
            "queries_by_intent"
        )
        or {}
    ).values():

        if isinstance(
            intent_values,
            list,
        ):

            values.extend(
                str(value)
                for value in intent_values
            )


    return _normalize(
        " ".join(
            values
        )
    )


# ====================================================================
# A. BROAD CATEGORY MUST YIELD
# ====================================================================

@pytest.mark.parametrize(
    (
        "industry",
        "canonical_domain",
        "marker",
    ),
    [
        (
            "Industrial Services",
            "coating integrity inspection",
            "coating integrity",
        ),
        (
            "Transport Operations",
            "route network optimization",
            "route network",
        ),
        (
            "Education and Recruitment",
            "apprenticeship placement platform",
            "apprenticeship",
        ),
    ],
)
def test_broad_explicit_context_yields_to_more_discriminative_current_domain(
    industry: str,
    canonical_domain: str,
    marker: str,
) -> None:

    planner = _run(
        industry=industry,
        domain_concepts=[
            canonical_domain,
            industry,
        ],
    )


    assert (
        marker
        in _effective_domain(
            planner
        )
    ), planner


# ====================================================================
# B. SUBSTANTIVE SINGLE-FACET MUST NOT BE ERASED
# ====================================================================

@pytest.mark.parametrize(
    (
        "industry",
        "domain_concepts",
        "marker",
    ),
    [
        (
            "Technology / Metrology / Software",
            [
                "metrology calibration software",
                "dimensional inspection",
                "metrology",
                "technology",
                "software",
            ],
            "metrology",
        ),
        (
            "Digital / Forestry / Technology",
            [
                "forestry inventory platform",
                "forest asset records",
                "forestry",
                "digital",
                "technology",
            ],
            "forestry",
        ),
        (
            "Software / Aquaculture / Technology",
            [
                "aquaculture farm management",
                "water quality monitoring",
                "aquaculture",
                "software",
                "technology",
            ],
            "aquaculture",
        ),
    ],
)
def test_substantive_explicit_domain_facet_survives_generic_wrappers(
    industry: str,
    domain_concepts: list[str],
    marker: str,
) -> None:

    planner = _run(
        industry=industry,
        domain_concepts=domain_concepts,
    )


    assert (
        marker
        in _effective_domain(
            planner
        )
    ), planner


    assert (
        marker
        in _query_blob(
            planner
        )
    ), planner


# ====================================================================
# C. QUALIFIED EXPLICIT DOMAIN KEEPS AUTHORITY
# ====================================================================

def test_qualified_explicit_domain_remains_above_unrelated_canonical_candidate() -> None:

    planner = _run(
        industry="Cryogenic Logistics Operations",
        domain_concepts=[
            "marine equipment inspection",
            "Cryogenic Logistics Operations",
        ],
    )


    assert (
        "cryogenic logistics"
        in _effective_domain(
            planner
        )
    ), planner


# ====================================================================
# D. GENERIC EXPLICIT LABEL CAN YIELD
# ====================================================================

def test_generic_technology_wrapper_does_not_own_executable_identity() -> None:

    planner = _run(
        industry="Software",
        domain_concepts=[
            "precision coating inspection",
            "Software",
        ],
    )


    assert (
        "precision coating"
        in _effective_domain(
            planner
        )
    ), planner


# ====================================================================
# E. GRANULARITY MUST FOLLOW CURRENT CANONICAL SPECIALIZATION
# ====================================================================

def test_broad_context_does_not_freeze_executable_domain_identity() -> None:

    first = _run(
        industry="Industrial Services",
        domain_concepts=[
            "coating integrity inspection",
            "Industrial Services",
        ],
    )


    second = _run(
        industry="Industrial Services",
        domain_concepts=[
            "ceramic kiln quality control",
            "Industrial Services",
        ],
    )


    first_domain = _effective_domain(
        first
    )


    second_domain = _effective_domain(
        second
    )


    assert (
        "coating integrity"
        in first_domain
    ), first


    assert (
        "ceramic kiln"
        in second_domain
    ), second


    assert (
        first_domain
        != second_domain
    )


# ====================================================================
# F. IMPORTANT ANTI-OVERFIT INVARIANT
#
# Explicit-domain preservation must NOT require lexical overlap with
# the specialized canonical phrase.
# ====================================================================

def test_specialized_canonical_domain_does_not_require_lexical_overlap_with_broad_category() -> None:

    planner = _run(
        industry="Transport Operations",
        domain_concepts=[
            "fleet dispatch optimization",
            "Transport Operations",
        ],
    )


    assert (
        "fleet dispatch"
        in _effective_domain(
            planner
        )
    ), planner
