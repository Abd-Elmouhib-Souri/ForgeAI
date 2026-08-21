import pytest

from app.services.source_role_resolver import (
    source_role_resolver,
)


def _rich_marketplace_context():
    structured = {
        "project_archetype": (
            "two_sided_marketplace"
        ),
        "domain_concepts": [
            "professional equipment rental marketplace",
            "temporary equipment rental",
            "b2b rental",
        ],
        "target_users": [
            "business renters",
            "equipment owners",
        ],
        "priority_workflows": [
            "submit a rental reservation request",
            "publish available equipment",
        ],
        "use_case_terms": [
            "submit rental reservation request",
            "temporary equipment rental",
        ],
        "solution_terms": [
            "connect equipment owners and business renters",
        ],
    }

    return {
        "structured_project_context": structured,
        "agent_context_packet": {
            "domain_concepts": (
                structured[
                    "domain_concepts"
                ]
            ),
            "target_terms": (
                structured[
                    "target_users"
                ]
            ),
            "use_case_terms": (
                structured[
                    "use_case_terms"
                ]
            ),
            "solution_terms": (
                structured[
                    "solution_terms"
                ]
            ),
        },
    }


@pytest.mark.parametrize(
    "source",
    [
        {
            "title": (
                "Create Your B2B Marketplace Platform"
            ),
            "url": (
                "https://vendor.example/"
                "marketplace-platform"
            ),
        },
        {
            "title": (
                "B2B Wholesale Marketplace"
            ),
            "url": (
                "https://wholesale.example/"
                "b2b-marketplace"
            ),
        },
    ],
)
def test_generic_category_overlap_is_not_enough_for_direct_competition(
    source,
):
    result = (
        source_role_resolver.resolve(
            source=source,
            decision={
                "source_type": "competitor",
                "region_match": "local",
                "is_product_page": True,
                "same_or_close_target_user": True,
                "same_or_close_use_case": True,
                "same_or_close_solution_category": True,
                "sector_mismatch": False,
            },
            project_context=(
                _rich_marketplace_context()
            ),
        )
    )

    assert (
        result[
            "consumer_operation"
        ]
        is False
    )

    assert (
        result[
            "operation_equivalent"
        ]
        is False
    )

    assert (
        result[
            "source_role"
        ]
        != "direct_competitor"
    )

    assert (
        result[
            "canonical_category"
        ]
        != "direct_competitor"
    )


def test_same_solution_fallback_survives_with_real_multi_axis_source_evidence():
    context = {
        "structured_project_context": {
            "project_archetype": (
                "transactional_platform"
            ),
            "domain_concepts": [
                "service booking",
            ],
            "target_users": [],
            "priority_workflows": [],
        },
        "solution_terms": [
            "service booking platform",
        ],
        "target_users": [],
    }

    source = {
        "title": (
            "Local Service Booking Platform"
        ),
        "url": (
            "https://booking.example/"
            "booking"
        ),
        "body": (
            "A local service booking platform "
            "with online booking."
        ),
    }

    result = (
        source_role_resolver.resolve(
            source=source,
            decision={
                "source_type": (
                    "adjacent_solution"
                ),
                "region_match": "local",
                "is_product_page": True,
                "same_or_close_target_user": False,
                "same_or_close_use_case": False,
                "same_or_close_solution_category": True,
                "sector_mismatch": False,
            },
            project_context=context,
        )
    )

    assert (
        result["source_role"]
        == "direct_competitor"
    )
