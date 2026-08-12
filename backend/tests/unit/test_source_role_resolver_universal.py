from __future__ import annotations

from app.services.source_role_resolver import (
    source_role_resolver,
)


def _context(
    *,
    archetype: str,
    domain_concepts: list[str],
    use_case_terms: list[str],
    solution_terms: list[str],
    target_terms: list[str] | None = None,
) -> dict:
    structured = {
        "project_archetype": archetype,
        "domain_concepts": domain_concepts,
        "use_case_terms": use_case_terms,
        "solution_terms": solution_terms,
        "target_users": target_terms or [],
        "priority_workflows": [],
    }

    packet = {
        "domain_concepts": domain_concepts,
        "use_case_terms": use_case_terms,
        "solution_terms": solution_terms,
        "target_terms": target_terms or [],
    }

    return {
        "structured_project_context": structured,
        "agent_context_packet": packet,
    }


def _decision(
    *,
    source_type: str = "adjacent_solution",
    product_page: bool = False,
) -> dict:
    return {
        "source_type": source_type,
        "region_match": "local",
        "is_product_page": product_page,
        "same_or_close_target_user": False,
        "same_or_close_use_case": False,
        "same_or_close_solution_category": False,
        "sector_mismatch": False,
    }


def test_resolver_contains_no_mobility_authority() -> None:
    assert not hasattr(
        source_role_resolver,
        "MOBILITY_VERTICALS",
    )

    assert not hasattr(
        source_role_resolver,
        "MOBILITY_OPERATION_SIGNALS",
    )


def test_marketplace_operation_equivalence_is_domain_neutral() -> None:
    context = _context(
        archetype="two_sided_marketplace",
        domain_concepts=[
            "internship platform",
            "student company marketplace",
        ],
        use_case_terms=[
            "publish internship offers",
            "submit applications",
        ],
        solution_terms=[
            "internship matching platform",
        ],
        target_terms=[
            "students",
            "companies",
        ],
    )

    result = source_role_resolver.resolve(
        source={
            "title": "Internship Platform",
            "url": "https://example.tn/internships",
            "body": (
                "An internship platform for students and companies. "
                "Companies publish internship offers and students "
                "submit applications online."
            ),
        },
        decision=_decision(),
        project_context=context,
    )

    assert result["consumer_operation"] is True
    assert result["operation_equivalent"] is True
    assert result["source_role"] == "direct_competitor"


def test_b2b_workflow_equivalence_is_domain_neutral() -> None:
    context = _context(
        archetype="b2b_workflow_saas",
        domain_concepts=[
            "workforce management",
        ],
        use_case_terms=[
            "record attendance",
            "approve leave requests",
        ],
        solution_terms=[
            "workforce management platform",
        ],
        target_terms=[
            "supervisors",
            "hr managers",
        ],
    )

    result = source_role_resolver.resolve(
        source={
            "title": "Workforce Management Platform",
            "url": "https://example.tn/workforce",
            "body": (
                "A workforce management platform for SMEs. "
                "Managers record attendance and approve leave "
                "requests from one dashboard."
            ),
        },
        decision=_decision(),
        project_context=context,
    )

    assert result["consumer_operation"] is True
    assert result["operation_equivalent"] is True
    assert result["source_role"] == "direct_competitor"


def test_brand_or_domain_phrase_without_operation_is_not_direct() -> None:
    context = _context(
        archetype="two_sided_marketplace",
        domain_concepts=[
            "ride hailing",
            "taxi booking",
        ],
        use_case_terms=[
            "connect passengers and drivers",
        ],
        solution_terms=[
            "ride hailing platform",
        ],
    )

    result = source_role_resolver.resolve(
        source={
            "title": "Yassir Road Safety Initiative",
            "url": "https://yassir.com/news/road-safety",
            "body": (
                "Yassir supports a public road safety campaign "
                "in Tunisia focused on safer streets, awareness "
                "and driver education."
            ),
        },
        decision=_decision(),
        project_context=context,
    )

    assert result["consumer_operation"] is False
    assert result["operation_equivalent"] is False
    assert result["source_role"] != "direct_competitor"


def test_adjacent_iot_operation_does_not_become_direct() -> None:
    context = _context(
        archetype="hardware_iot_robotics",
        domain_concepts=[
            "smart agriculture",
            "agricultural robotics",
        ],
        use_case_terms=[
            "inspect crops",
            "detect anomalies",
        ],
        solution_terms=[
            "autonomous robot",
            "computer vision",
        ],
        target_terms=[
            "greenhouse owners",
        ],
    )

    result = source_role_resolver.resolve(
        source={
            "title": "Smart Agriculture Dashboard",
            "url": "https://example.tn/smart-agriculture",
            "body": (
                "A smart agriculture dashboard for farms. "
                "Monitor sensor data and view crop metrics."
            ),
        },
        decision=_decision(
            product_page=True,
        ),
        project_context=context,
    )

    assert result["operation_equivalent"] is False
    assert result["source_role"] == "adjacent_solution"


def test_generic_white_label_supplier_is_technology_provider() -> None:
    context = _context(
        archetype="b2b_workflow_saas",
        domain_concepts=[
            "workflow automation",
        ],
        use_case_terms=[
            "manage operational workflows",
        ],
        solution_terms=[
            "workflow platform",
        ],
    )

    result = source_role_resolver.resolve(
        source={
            "title": "White Label Workflow Platform",
            "url": "https://vendor.example.com/platform",
            "body": (
                "White label software for businesses with API "
                "integration, SDK, deployment support and request demo."
            ),
        },
        decision={
            **_decision(
                source_type="competitor",
                product_page=True,
            ),
            "same_or_close_solution_category": True,
        },
        project_context=context,
    )

    assert result["technology_supplier"] is True
    assert result["source_role"] == "technology_provider"
    assert (
        result["legacy_source_type"]
        == "technology_benchmark"
    )

def test_same_operation_outside_launch_market_is_benchmark_not_competitor_type() -> None:
    context = _context(
        archetype="b2b_workflow_saas",
        domain_concepts=[
            "workforce management",
        ],
        use_case_terms=[
            "record attendance",
            "approve leave requests",
        ],
        solution_terms=[
            "workforce management platform",
        ],
        target_terms=[
            "supervisors",
            "hr managers",
        ],
    )

    decision = _decision()

    decision["region_match"] = "international"

    result = source_role_resolver.resolve(
        source={
            "title": "Global Workforce Management Platform",
            "url": "https://example.com/workforce",
            "body": (
                "A workforce management platform where managers "
                "record attendance and approve leave requests."
            ),
        },
        decision=decision,
        project_context=context,
    )

    assert result["operation_equivalent"] is True

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
        result["canonical_category"]
        == "technology_benchmark"
    )


def test_source_gate_contains_no_closed_sector_taxonomy_authority() -> None:
    from app.services.source_relevance_gate import (
        source_relevance_gate,
    )

    assert not hasattr(
        source_relevance_gate,
        "VERTICAL_SECTOR_GROUPS",
    )
    assert not hasattr(
        source_relevance_gate,
        "CROSS_SECTOR_PRODUCT_HINTS",
    )
    assert not hasattr(
        source_relevance_gate,
        "_vertical_mismatch_terms",
    )

    assert hasattr(
        source_relevance_gate,
        "RECRUITMENT_CONTEXT_TERMS",
    )
