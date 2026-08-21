from __future__ import annotations

from app.services.source_role_resolver import (
    source_role_resolver,
)


def _context() -> dict:
    domain = [
        "workforce management",
    ]

    use_cases = [
        "record attendance",
        "approve leave requests",
    ]

    solutions = [
        "workforce management platform",
    ]

    targets = [
        "supervisors",
        "hr managers",
    ]

    return {
        "structured_project_context": {
            "project_archetype": (
                "b2b_workflow_saas"
            ),
            "domain_concepts": domain,
            "use_case_terms": use_cases,
            "solution_terms": solutions,
            "target_users": targets,
            "priority_workflows": [],
        },
        "agent_context_packet": {
            "domain_concepts": domain,
            "use_case_terms": use_cases,
            "solution_terms": solutions,
            "target_terms": targets,
        },
    }


def _decision() -> dict:
    return {
        "source_type": "adjacent_solution",
        "region_match": "local",
        "is_product_page": False,
        "same_or_close_target_user": False,
        "same_or_close_use_case": False,
        "same_or_close_solution_category": False,
        "sector_mismatch": False,
    }


def _resolve(
    body: str,
) -> dict:
    return source_role_resolver.resolve(
        source={
            "title": "Candidate",
            "url": "https://example.test/product",
            "body": body,
        },
        decision=_decision(),
        project_context=_context(),
    )


def test_close_role_head_preserves_direct_business_match() -> None:
    result = _resolve(
        (
            "A workforce management platform for SMEs. "
            "Managers record attendance and approve leave "
            "requests from one dashboard."
        )
    )

    assert result["consumer_operation"] is True
    assert result["operation_equivalent"] is True
    assert result["source_role"] == "direct_competitor"


def test_same_workflow_for_different_actor_is_not_direct() -> None:
    result = _resolve(
        (
            "A workforce management platform for individual "
            "consumers. Parents record attendance and approve "
            "leave requests for family activities."
        )
    )

    assert result["consumer_operation"] is True
    assert result["operation_equivalent"] is True
    assert result["source_role"] != "direct_competitor"
    assert result["canonical_category"] != "direct_competitor"


def test_explicit_actor_mismatch_is_never_direct() -> None:
    result = _resolve(
        (
            "A workforce management platform designed exclusively "
            "for individual household consumers, not employers "
            "or HR teams. Parents record attendance and approve "
            "leave requests for family activities."
        )
    )

    assert result["consumer_operation"] is True
    assert result["operation_equivalent"] is True
    assert result["source_role"] != "direct_competitor"
    assert result["canonical_category"] != "direct_competitor"


def test_classifier_confirmed_same_target_remains_authoritative() -> None:
    decision = _decision()

    decision[
        "same_or_close_target_user"
    ] = True

    result = source_role_resolver.resolve(
        source={
            "title": "Validated target product",
            "url": "https://example.test/validated",
            "body": (
                "A workforce management platform. "
                "Record attendance and approve leave requests."
            ),
        },
        decision=decision,
        project_context=_context(),
    )

    assert result["source_role"] == "direct_competitor"

def test_missing_target_authority_is_unknown_not_mismatch() -> None:
    context = {
        "structured_project_context": {
            "project_archetype": (
                "b2b_workflow_saas"
            ),
            "domain_concepts": [
                "workforce management",
            ],
            "target_users": [],
            "priority_workflows": [],
        },
        "domain_concepts": [
            "workforce management",
        ],
        "use_case_terms": [
            "record attendance",
            "approve leave requests",
        ],
        "solution_terms": [
            "workforce management platform",
        ],
        "target_users": [],
    }

    result = source_role_resolver.resolve(
        source={
            "title": "Operational product",
            "url": "https://example.test/operation",
            "body": (
                "A workforce management platform. "
                "Managers record attendance and approve leave "
                "requests from one dashboard."
            ),
        },
        decision={
            "source_type": "adjacent_solution",
            "region_match": "local",
            "is_product_page": False,
            "same_or_close_target_user": False,
            "same_or_close_use_case": False,
            "same_or_close_solution_category": False,
            "sector_mismatch": False,
        },
        project_context=context,
    )

    assert result["consumer_operation"] is True
    assert result["operation_equivalent"] is True
    assert result["source_role"] == "direct_competitor"


def test_root_level_compatibility_terms_are_preserved() -> None:
    context = source_role_resolver._context(
        {
            "structured_project_context": {
                "project_archetype": (
                    "generic_digital_product"
                ),
            },
            "domain_concepts": [
                "service booking",
            ],
            "use_case_terms": [
                "book appointments",
            ],
            "solution_terms": [
                "booking platform",
            ],
            "target_users": [
                "service operators",
            ],
        }
    )

    assert (
        "service booking"
        in context["domain_concepts"]
    )

    assert (
        "book appointments"
        in context["use_case_terms"]
    )

    assert (
        "booking platform"
        in context["solution_terms"]
    )

    assert (
        "service operators"
        in context["target_terms"]
    )


def test_nonlocal_operational_match_with_different_actor_remains_benchmark() -> None:
    context = {
        "structured_project_context": {
            "project_archetype": (
                "b2b_workflow_saas"
            ),
            "domain_concepts": [
                "workforce management",
            ],
            "use_case_terms": [
                "record attendance",
                "approve leave requests",
            ],
            "solution_terms": [
                "workforce management platform",
            ],
            "target_users": [
                "supervisors",
                "hr managers",
            ],
            "priority_workflows": [],
        },
        "agent_context_packet": {
            "domain_concepts": [
                "workforce management",
            ],
            "use_case_terms": [
                "record attendance",
                "approve leave requests",
            ],
            "solution_terms": [
                "workforce management platform",
            ],
            "target_terms": [
                "supervisors",
                "hr managers",
            ],
        },
    }

    result = source_role_resolver.resolve(
        source={
            "title": (
                "International Workforce "
                "Management Platform"
            ),
            "url": (
                "https://example.org/"
                "workforce-platform"
            ),
            "body": (
                "A workforce management platform "
                "for operational coordinators. "
                "Coordinators record attendance "
                "and approve leave requests."
            ),
        },
        decision={
            "source_type": (
                "adjacent_solution"
            ),
            "region_match": (
                "international"
            ),
            "is_product_page": True,
            "same_or_close_target_user": False,
            "same_or_close_use_case": True,
            "same_or_close_solution_category": True,
            "sector_mismatch": False,
        },
        project_context=context,
    )

    assert (
        result["source_role"]
        == "international_benchmark"
    )

    assert (
        result["comparison_scope"]
        == "international_benchmark"
    )

    assert (
        result["legacy_source_type"]
        == "adjacent_solution"
    )

    assert (
        result["source_role"]
        != "direct_competitor"
    )


def test_local_product_same_solution_with_unknown_target_can_remain_direct() -> None:
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

    result = source_role_resolver.resolve(
        source={
            "title": (
                "Local Service Booking Platform"
            ),
            "url": (
                "https://example.test/"
                "booking"
            ),
            "body": (
                "A local service booking platform "
                "with online booking."
            ),
        },
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

    assert (
        result["source_role"]
        == "direct_competitor"
    )


def test_local_product_same_solution_with_known_actor_mismatch_is_not_direct() -> None:
    context = {
        "structured_project_context": {
            "project_archetype": (
                "b2b_workflow_saas"
            ),
            "domain_concepts": [
                "workforce management",
            ],
            "solution_terms": [
                "workforce management platform",
            ],
            "target_users": [
                "hr managers",
            ],
            "priority_workflows": [],
        },
        "agent_context_packet": {
            "domain_concepts": [
                "workforce management",
            ],
            "solution_terms": [
                "workforce management platform",
            ],
            "target_terms": [
                "hr managers",
            ],
        },
    }

    result = source_role_resolver.resolve(
        source={
            "title": (
                "Consumer Workforce Platform"
            ),
            "url": (
                "https://example.test/"
                "consumer-workforce"
            ),
            "body": (
                "A workforce management platform "
                "for parents and individual "
                "household consumers."
            ),
        },
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

    assert (
        result["source_role"]
        != "direct_competitor"
    )

    assert (
        result["canonical_category"]
        != "direct_competitor"
    )
