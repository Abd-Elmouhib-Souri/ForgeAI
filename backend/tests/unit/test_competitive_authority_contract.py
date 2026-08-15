import inspect

from app.agents.competitive_analysis_agent import (
    CompetitiveAnalysisAgent,
)
from app.services.canonical_source_ledger import (
    canonical_source_ledger,
)


def _canonical_direct_source(
    *,
    title: str,
    url: str,
    score: float,
    source_type: str,
):
    return {
        "title": title,
        "vendor_name": title,
        "url": url,
        "source_type": source_type,
        "source_role": "direct_competitor",
        "canonical_category": "direct_competitor",
        "comparison_scope": "local_direct",
        "region_match": "local",
        "source_relevance_score": score,
        "is_direct_competitor": True,
        "public_display": True,
        "internal_only": False,
        "rejected": False,
    }


def test_competitive_agent_has_no_post_ledger_directness_authority() -> None:
    source = inspect.getsource(
        CompetitiveAnalysisAgent
    )

    assert "LOCAL_DIRECT_MIN_SCORE" not in source
    assert "self._is_strict_direct_source(" not in source
    assert "self._local_direct_source_items(" not in source
    assert "self._local_direct_competitors(" not in source


def test_run_consumes_canonical_local_direct_bucket() -> None:
    source = inspect.getsource(
        CompetitiveAnalysisAgent.run
    )

    assert (
        "sources=local_competitor_sources"
        in source
    )

    assert (
        "sources=safe_public_sources,\n"
        "            fallback_region=region"
        not in source
    )


def test_canonical_direct_bucket_maps_one_to_one_to_cards() -> None:
    sources = [
        _canonical_direct_source(
            title="Direct A",
            url="https://direct-a.example/",
            score=0.59,
            source_type="competitor",
        ),
        _canonical_direct_source(
            title="Direct B",
            url="https://direct-b.example/",
            score=0.60,
            source_type="pricing_page",
        ),
    ]

    ledger = canonical_source_ledger.build(
        sources
    )

    canonical = list(
        ledger.get(
            "local_direct_competitor_sources"
        )
        or []
    )

    cards = (
        CompetitiveAnalysisAgent()
        ._sources_to_competitor_cards(
            sources=canonical,
            fallback_region="Local",
            limit=None,
        )
    )

    assert len(canonical) == 2
    assert len(cards) == len(canonical)

    assert {
        item["name"]
        for item in cards
    } == {
        "Direct A",
        "Direct B",
    }


def test_card_conversion_does_not_reclassify_business_role() -> None:
    source = _canonical_direct_source(
        title="Canonical Direct",
        url="https://canonical-direct.example/",
        score=0.59,
        source_type="legacy_custom_type",
    )

    cards = (
        CompetitiveAnalysisAgent()
        ._sources_to_competitor_cards(
            sources=[source],
            fallback_region="Local",
            limit=None,
        )
    )

    assert len(cards) == 1

    card = cards[0]

    assert (
        card["source_role"]
        == "direct_competitor"
    )

    assert (
        card["comparison_scope"]
        == "local_direct"
    )

    assert (
        card["source_type"]
        == "legacy_custom_type"
    )


def test_indirect_alternatives_have_no_vertical_specific_fallback() -> None:
    source = inspect.getsource(
        CompetitiveAnalysisAgent._build_indirect_competitors
    )

    forbidden = (
        "mobility_taxi",
        "Street hailing",
        "taxi ranks",
        "Maraude",
        "stations de taxis",
        "ride-hailing",
    )

    for token in forbidden:
        assert token not in source

    assert (
        'structured_project_context.get("vertical")'
        not in source
    )


def test_indirect_alternatives_prefer_canonical_adjacent_solution_names() -> None:
    values = (
        CompetitiveAnalysisAgent()
        ._build_indirect_competitors(
            market_context_sources=[
                {
                    "name": "Editorial Market Report",
                },
            ],
            adjacent_solutions=[
                {
                    "name": "Adjacent Workflow Product",
                },
            ],
            regional_competitors=[],
            international_benchmarks=[],
            structured_project_context={},
            language="en",
        )
    )

    assert values == [
        "Adjacent Workflow Product",
    ]

    assert (
        "Editorial Market Report"
        not in values
    )


def test_marketplace_indirect_fallback_uses_canonical_context_not_vertical() -> None:
    values = (
        CompetitiveAnalysisAgent()
        ._build_indirect_competitors(
            market_context_sources=[],
            adjacent_solutions=[],
            regional_competitors=[],
            international_benchmarks=[],
            structured_project_context={
                "project_archetype": "two_sided_marketplace",
                "vertical": "mobility_taxi",
                "priority_workflows": [
                    (
                        "Publish an offer, match demand "
                        "and confirm a transaction"
                    ),
                ],
                "target_users": [
                    "Supply-side company",
                    "Demand-side company",
                ],
                "transaction_unit_text": (
                    "One completed transaction"
                ),
            },
            language="en",
        )
    )

    joined = " ".join(
        values
    )

    assert (
        "Publish an offer, match demand "
        "and confirm a transaction"
        in joined
    )

    assert "Supply-side company" in joined
    assert "Demand-side company" in joined

    lowered = joined.lower()

    assert "taxi" not in lowered
    assert "ride-hailing" not in lowered
    assert "street hailing" not in lowered


def test_saas_indirect_fallback_uses_same_generic_contract() -> None:
    values = (
        CompetitiveAnalysisAgent()
        ._build_indirect_competitors(
            market_context_sources=[],
            adjacent_solutions=[],
            regional_competitors=[],
            international_benchmarks=[],
            structured_project_context={
                "project_archetype": "b2b_workflow_saas",
                "priority_workflows": [
                    "Approve employee leave requests",
                ],
                "target_users": [
                    "HR manager",
                ],
            },
            language="en",
        )
    )

    joined = " ".join(
        values
    )

    assert (
        "Approve employee leave requests"
        in joined
    )

    assert "HR manager" in joined

    lowered = joined.lower()

    assert "taxi" not in lowered
    assert "agriculture" not in lowered
    assert "healthcare" not in lowered
