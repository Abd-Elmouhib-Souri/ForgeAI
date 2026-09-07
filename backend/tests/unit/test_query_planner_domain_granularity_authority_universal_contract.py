from __future__ import annotations

import inspect

import pytest

from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


service = project_intelligence_layer


def _normalize(value) -> str:
    return service._normalize_concept(value)


def _planner(
    *,
    industry: str,
    canonical_domain: str,
    advisory_domain: str = "workflow management software",
):
    """
    Invoke the real Query Planner authority directly.

    Explicit industry is a current user fact.

    canonical_domain is a more discriminative current-project domain already
    admitted into canonical research context.

    advisory_domain is lower-authority archetype metadata.
    """

    kwargs = {
        "title":
            "Neutral Research Boundary",

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
                "Centralize the specialized workflow "
                "and its operational evidence."
            ),

        "main_use_case":
            "manage specialized operational workflow",

        "business_model":
            "B2B subscription",

        "strong_keywords":
            [
                canonical_domain,
            ],

        "sector_profile":
            {},

        "language":
            "en",

        "search_concepts":
            [
                canonical_domain,
                industry,
            ],

        "domain_concepts":
            [
                canonical_domain,
                industry,
            ],

        "use_case_terms":
            [
                "manage specialized workflow",
                "review operational evidence",
            ],

        "solution_terms":
            [
                canonical_domain,
            ],

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


    call_kwargs = {
        key:
            value

        for key, value
        in kwargs.items()

        if key in signature.parameters
    }


    missing_required = [
        name
        for name, parameter
        in signature.parameters.items()
        if (
            name != "self"
            and parameter.default
            is inspect.Parameter.empty
            and parameter.kind
            in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
            and name not in call_kwargs
        )
    ]


    if missing_required:
        raise RuntimeError(
            "QUERY_PLANNER_REQUIRED_ARGUMENTS_NOT_COVERED:"
            + repr(
                missing_required
            )
        )


    return service._query_planner(
        **call_kwargs
    )


def _effective_domain(planner) -> str:

    base_context = str(
        planner.get(
            "base_context"
        )
        or ""
    )


    return _normalize(
        base_context
        .split(
            " | ",
            1,
        )[0]
    )


def _all_queries(planner):

    result = []


    queries_by_intent = (
        planner.get(
            "queries_by_intent"
        )
        or {}
    )


    if isinstance(
        queries_by_intent,
        dict,
    ):

        for values in (
            queries_by_intent.values()
        ):

            if isinstance(
                values,
                list,
            ):

                result.extend(
                    str(value)
                    for value in values
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


def _blob(values) -> str:

    return _normalize(
        " ".join(
            values
        )
    )


@pytest.mark.parametrize(
    (
        "broad_industry",
        "canonical_domain",
        "required_marker",
    ),
    [
        (
            "Transport Operations",
            "cold chain shipment monitoring",
            "cold chain",
        ),
        (
            "Education Services",
            "apprenticeship placement platform",
            "apprenticeship",
        ),
        (
            "Industrial Services",
            "marine corrosion inspection",
            "marine corrosion",
        ),
    ],
)
def test_broad_explicit_category_cannot_erase_more_discriminative_canonical_domain(
    broad_industry: str,
    canonical_domain: str,
    required_marker: str,
) -> None:
    """
    Universal invariant:

    An explicit broad category remains true project context, but it cannot
    erase a more discriminative current canonical search identity.
    """

    planner = _planner(
        industry=broad_industry,
        canonical_domain=canonical_domain,
    )


    assert (
        required_marker
        in _effective_domain(
            planner
        )
    ), planner


    assert (
        required_marker
        in _blob(
            _all_queries(
                planner
            )
        )
    ), planner


def test_canonical_domain_granularity_changes_executable_identity_when_broad_category_is_constant() -> None:
    """
    Metamorphic invariant:

    Holding the explicit broad category constant while changing only the
    specialized current canonical domain must change executable identity.
    """

    first = _planner(
        industry="Industrial Services",
        canonical_domain="marine corrosion inspection",
    )


    second = _planner(
        industry="Industrial Services",
        canonical_domain="ceramic kiln quality control",
    )


    first_domain = _effective_domain(
        first
    )


    second_domain = _effective_domain(
        second
    )


    assert (
        "marine corrosion"
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


    assert (
        {
            _normalize(value)
            for value in _all_queries(
                first
            )
        }
        !=
        {
            _normalize(value)
            for value in _all_queries(
                second
            )
        }
    )


def test_genuinely_specific_explicit_domain_remains_authoritative() -> None:
    """
    Recall preservation:

    This contract does not authorize canonical inference to overwrite an
    explicit domain when that explicit fact is already the specialized domain.
    """

    explicit_domain = (
        "Cryogenic Logistics Operations"
    )


    planner = _planner(
        industry=explicit_domain,
        canonical_domain=explicit_domain,
        advisory_domain="workflow management software",
    )


    assert (
        "cryogenic"
        in _effective_domain(
            planner
        )
    ), planner


    assert (
        "cryogenic"
        in _blob(
            _all_queries(
                planner
            )
        )
    ), planner


def test_generic_technology_label_can_use_current_canonical_domain() -> None:

    planner = _planner(
        industry="Software",
        canonical_domain="precision coating inspection",
        advisory_domain="workflow management software",
    )


    assert (
        "precision coating"
        in _effective_domain(
            planner
        )
    ), planner


def test_advisory_archetype_hint_remains_lower_authority_than_current_canonical_domain() -> None:
    """
    Preserve F4-N hierarchy:
    advisory archetype metadata stays below current canonical project domain.
    """

    planner = _planner(
        industry="Software",
        canonical_domain="ceramic kiln quality control",
        advisory_domain="workforce scheduling software",
    )


    query_blob = _blob(
        _all_queries(
            planner
        )
    )


    assert (
        "ceramic kiln"
        in query_blob
    ), planner


    assert (
        "workforce scheduling"
        not in _effective_domain(
            planner
        )
    ), planner
