from __future__ import annotations

import asyncio
from typing import Any

from app.agents.debate_room_graph import DebateRoomGraph
from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.services.evidence_ledger import evidence_ledger
from app.services.project_intelligence_layer import project_intelligence_layer
from app.services.source_classifier import SourceClassifier
from app.services.source_relevance_gate import source_relevance_gate


DESCRIPTION = (
    "BeeTrace Tunisia is a lightweight SaaS platform for small Tunisian "
    "beekeepers and honey cooperatives who need to track hive inspections, "
    "honey harvest batches, disease treatments, feeding actions, hive movements "
    "and product traceability. Many small beekeepers still use notebooks, "
    "WhatsApp and spreadsheets. The platform lets users register hives, record "
    "inspections, track treatments and harvest batches, attach photos and export "
    "traceability sheets. The business model is a monthly beekeeper subscription "
    "or a cooperative plan."
)


def _intelligence() -> dict[str, Any]:
    return project_intelligence_layer.build(
        title="BeeTrace Tunisia",
        description=DESCRIPTION,
        industry="AgriTech / Beekeeping / Traceability",
        target_region="Tunisie",
        output_language="en",
    )


def _context() -> dict[str, Any]:
    intelligence = _intelligence()
    return project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )


def test_query_planner_balances_domain_local_official_and_pricing_intents() -> None:
    planner = _intelligence()["query_planner"]
    selected = planner["queries"]
    intents = planner["queries_by_intent"]

    assert planner["format"] == "query_planner_v5_archetype_aware"
    assert len(selected) <= 8
    assert intents["direct_competitors"]
    assert intents["local_solutions"]
    assert intents["official_sources"]
    assert intents["market_sources"]
    assert intents["pricing"]
    assert any("beekeeping" in query.lower() for query in selected)
    assert not any(query.lower().startswith("generate traceability sheets") for query in selected)


def test_local_beekeeper_tech_is_public_but_unrelated_traksys_is_rejected() -> None:
    context = _context()
    beekeeper = source_relevance_gate.evaluate_source(
        source={
            "title": "Beekeeper Tech, application 100% tunisienne",
            "url": "https://tunisie-direct.com/beekeeper-tech-application",
            "snippet": (
                "Application mobile tunisienne pour apiculteurs, suivi des ruches, "
                "inspections, features et login."
            ),
            "extracted_text_preview": (
                "Application pour apiculteurs permettant de surveiller les ruches "
                "et suivre les inspections."
            ),
            "text_extracted": True,
        },
        project_context=context,
    )
    traksys = source_relevance_gate.evaluate_source(
        source={
            "title": "Manufacturing Traceability Software | TrakSYS MES",
            "url": "https://parsec-corp.com/solutions/by-function/traceability",
            "snippet": "Industrial MES for factories, production lines and batches. Features and demo.",
            "extracted_text_preview": "Manufacturing plants, shop floor and industrial inventory.",
            "text_extracted": True,
        },
        project_context=context,
    )

    assert beekeeper["region_match"] == "local"
    assert beekeeper["public_display"] is True
    assert beekeeper["source_type"] in {
        "competitor",
        "adjacent_solution",
        "market_article",
    }

    # TrakSYS shares only weak traceability/product vocabulary with
    # the project. Without any closed sector taxonomy it must still
    # remain non-direct and must not reach the public report.
    assert traksys["source_type"] == "adjacent_solution"
    assert traksys["source_role"] == "adjacent_solution"
    assert traksys["is_direct_competitor"] is False
    assert traksys["public_display"] is False
    assert traksys["rejected"] is True
    assert traksys["canonical_category"] != "direct_competitor"
    assert traksys["source_role"] != "direct_competitor"


def test_local_ecosystem_is_visible_but_never_a_competitor() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "AgriTech4Tunisia innovation program",
            "url": "https://agritechchallenge.org/fr/projects/agritech4tunisia",
            "snippet": "Programme tunisien d'innovation agricole et accélérateur agritech.",
            "extracted_text_preview": "Tunisia agritech ecosystem for agricultural startups and innovation.",
            "text_extracted": True,
        },
        project_context=_context(),
    )
    assert decision["source_type"] == "local_ecosystem"
    assert decision["public_display"] is True
    assert decision["is_direct_competitor"] is False
    assert "local_ecosystem" in decision["evidence_categories"]


def test_commercial_market_report_remains_claim_only() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Tunisia Food Traceability Market 2025-2031",
            "url": "https://6wresearch.com/industry-report/tunisia-food-traceability-market",
            "snippet": "Commercial report landing page with market size, forecast and CAGR.",
            "extracted_text_preview": "Market revenue, demand, adoption outlook and forecast.",
            "text_extracted": True,
        },
        project_context=_context(),
    )
    categories = set(decision["evidence_categories"])
    assert "market_size_claim" in categories
    assert "market_demand_claim" in categories
    assert "market_size" not in categories
    assert "market_demand" not in categories


def test_canonical_confidence_separates_search_coverage_from_evidence() -> None:
    sources = [
        {
            "title": f"Relevant source {index}",
            "url": f"https://example.com/{index}",
            "public_display": True,
            "source_relevance_score": 0.75,
            "source_type": "market_article",
            "region_match": "international",
            "evidence_categories": ["sector_context"],
        }
        for index in range(5)
    ]
    sanitized = evidence_ledger.sanitize_public_claims(
        {
            "output_language": "en",
            "forgecrawler": {"sources": sources},
            "competitive_analysis": {},
            "market_study": {},
            "startup_score": {"verdict_code": "CONDITIONAL_GO"},
        }
    )
    confidence = sanitized["evidence_confidence"]
    assert confidence["search_coverage"] == "high"
    assert confidence["overall_evidence_confidence"] == "low"
    assert sanitized["forgecrawler"]["confidence_level"] == "low"
    assert sanitized["forgecrawler"]["search_coverage"] == "high"
    assert sanitized["verdict_code"] == "conditional_go"


def test_personas_have_distinct_workflows_and_language() -> None:
    state = {
        "title": "BeeTrace Tunisia",
        "description": DESCRIPTION,
        "industry": "AgriTech / Beekeeping / Traceability",
        "region": "Tunisie",
        "output_language": "en",
        "project_context": _context(),
        "analysis_data": {"project_intelligence": _intelligence()},
    }
    result = asyncio.run(PersonaBuilderAgent().run(state))
    personas = result["personas"]

    assert len(personas) == 3
    assert len({persona["id"] for persona in personas}) == 3
    assert len({persona["use_case"] for persona in personas}) == 3
    assert len({tuple(persona["goals"]) for persona in personas}) == 3
    assert all("small beekeepers" not in persona["profile"].lower() or "a hands-on small beekeepers" not in persona["profile"].lower() for persona in personas)
    assert all("complete generate" not in persona["use_case"].lower() for persona in personas)


def test_debate_room_has_five_complete_rounds_questions_answers_and_votes() -> None:
    intelligence = _intelligence()
    analysis = {
        "project_intelligence": intelligence,
        "structured_project_context": intelligence["structured_project_context"],
        "overall_evidence_confidence": "low",
        "evidence_confidence": {"overall_evidence_confidence": "low"},
        "competitive_analysis": {"market_gap": "No verified local direct competitor."},
        "financial_estimation": {"roi_outlook": "Requires price validation."},
        "startup_score": {
            "potential_score": 7.0,
            "evidence_confidence_score": 3.0,
            "execution_readiness_score": 6.5,
            "evidence_confidence_level": "low",
        },
        "fact_check_report": {
            "global_confidence": "low",
            "claims": [
                {"category": "problem", "status": "not_confirmed"},
                {"category": "market", "status": "not_confirmed"},
                {"category": "finance", "status": "not_confirmed"},
            ],
            "recommended_next_checks": ["Interview target users."],
        },
    }
    room = asyncio.run(
        DebateRoomGraph().run(
            project_id=1,
            title="BeeTrace Tunisia",
            description=DESCRIPTION,
            industry="AgriTech / Beekeeping / Traceability",
            region="Tunisie",
            output_language="en",
            project_context=_context(),
            analysis_data=analysis,
            max_rounds=5,
        )
    )["debate_room"]

    assert room["format"] == "debate_room_pro_v9_investment_committee"
    assert len(room["committee"]) == 8
    assert len(room["rounds"]) == 5
    assert room["judge"]["verdict_code"] == "conditional_go"
    assert len(room["judge"]["committee_votes"]) == 6
    assert room["meeting_preparation"]["top_questions"]

    forbidden = {
        "problem to validate",
        "solution to validate",
        "reduced core workflow",
        "business model to validate",
    }
    for round_data in room["rounds"]:
        assert round_data["topic"]
        assert round_data["objective"]
        assert round_data["main_question"]
        assert len(round_data["committee_questions"]) == 4
        assert round_data["round_summary"]["go_conditions"]
        assert round_data["round_summary"]["no_go_conditions"]
        for qa in round_data["committee_questions"]:
            assert qa["asked_by"]
            assert qa["addressed_to"]
            assert qa["question"]
            assert qa["answer"]["direct_answer"]
            assert qa["answer"]["evidence_status"]
            assert qa["answer"]["unresolved_point"]
            assert qa["meeting_preparation"]["likely_real_question"]
            assert qa["meeting_preparation"]["recommended_answer"]
            assert qa["meeting_preparation"]["proofs_to_prepare"]
            assert qa["meeting_preparation"]["answer_to_avoid"]
        flattened = str(round_data).lower()
        assert all(token not in flattened for token in forbidden)


def test_source_classifier_has_deterministic_final_fallback() -> None:
    classifier = SourceClassifier()
    article = classifier._with_deterministic(  # noqa: SLF001
        {
            "title": "Guide to honey traceability",
            "url": "https://example.com/blog/honey-traceability",
            "snippet": "Editorial guide",
        }
    )
    product = classifier._with_deterministic(  # noqa: SLF001
        {
            "title": "Apiary platform",
            "url": "https://example.com/product",
            "snippet": "Features, pricing, customers and book a demo",
        }
    )
    assert article["classifier_provider"] == "deterministic"
    assert article["ai_source_type"] == "market_article"
    assert product["ai_source_type"] == "adjacent_solution"


def test_source_classifier_falls_back_from_gemini_to_groq(monkeypatch) -> None:
    from app.config import settings

    classifier = SourceClassifier()
    monkeypatch.setattr(settings, "ENABLE_AI_SOURCE_CLASSIFIER", True)
    monkeypatch.setattr(settings, "GEMINI_SEARCH_CLASSIFIER_API_KEY", "test-gemini")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-groq")
    monkeypatch.setattr(settings, "SEARCH_CLASSIFIER_PRIMARY", "gemini")
    monkeypatch.setattr(settings, "SEARCH_CLASSIFIER_FALLBACK", "groq")

    async def failing_gemini(*_args, **_kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    async def working_groq(*_args, **_kwargs):
        return [
            {
                "index": 0,
                "source_type": "adjacent_solution",
                "confidence": 0.82,
                "same_target": True,
                "same_workflow": True,
                "same_sector": True,
                "product_page": True,
                "reason": "Product matches the locked project context.",
            }
        ]

    monkeypatch.setattr(classifier, "_classify_gemini", failing_gemini)
    monkeypatch.setattr(classifier, "_classify_groq", working_groq)

    result = asyncio.run(
        classifier.classify_sources(
            [{"title": "Apiary app", "url": "https://example.com"}],
            _context(),
        )
    )
    assert result[0]["classifier_provider"] == "groq"
    assert result[0]["ai_source_type"] == "adjacent_solution"


def test_source_classifier_uses_rules_when_gemini_and_groq_fail(monkeypatch) -> None:
    from app.config import settings

    classifier = SourceClassifier()
    monkeypatch.setattr(settings, "ENABLE_AI_SOURCE_CLASSIFIER", True)
    monkeypatch.setattr(settings, "GEMINI_SEARCH_CLASSIFIER_API_KEY", "test-gemini")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-groq")
    monkeypatch.setattr(settings, "SEARCH_CLASSIFIER_PRIMARY", "gemini")
    monkeypatch.setattr(settings, "SEARCH_CLASSIFIER_FALLBACK", "groq")

    async def fail(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(classifier, "_classify_gemini", fail)
    monkeypatch.setattr(classifier, "_classify_groq", fail)

    result = asyncio.run(
        classifier.classify_sources(
            [
                {
                    "title": "Honey guide",
                    "url": "https://example.com/blog/honey-guide",
                    "snippet": "Editorial article",
                }
            ],
            _context(),
        )
    )
    assert result[0]["classifier_provider"] == "deterministic"
    assert result[0]["ai_source_type"] == "market_article"
    assert "classifier_error" in result[0]


def test_main_llm_falls_back_from_gemini_to_groq(monkeypatch) -> None:
    from types import SimpleNamespace

    from app.config import settings
    from app.llm.provider import LLMProvider

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-groq")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODEL", "")
    monkeypatch.setattr(settings, "GROQ_FALLBACK_MODEL", "")
    monkeypatch.setattr(settings, "LLM_PRIMARY_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 5)

    LLMProvider._shared_models.clear()  # noqa: SLF001
    LLMProvider._shared_health.clear()  # noqa: SLF001
    LLMProvider._shared_limiters.clear()  # noqa: SLF001
    provider = LLMProvider()

    class DummyModel:
        def __init__(self, provider_name: str):
            self.provider_name = provider_name

        async def ainvoke(self, _prompt: str):
            if self.provider_name == "gemini":
                raise RuntimeError("429 RESOURCE_EXHAUSTED")
            return SimpleNamespace(content='{"status":"ok","provider":"groq"}')

    async def model_factory(config):
        return DummyModel(config.provider)

    monkeypatch.setattr(provider, "_get_or_create_model", model_factory)
    result = asyncio.run(provider.invoke("Return JSON", task_type="fallback_test"))
    assert '"provider":"groq"' in result
