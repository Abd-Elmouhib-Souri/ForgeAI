from __future__ import annotations

from typing import Any, Dict

from app.agents.competitive_analysis_agent import CompetitiveAnalysisAgent
from app.services.canonical_source_ledger import canonical_source_ledger
from app.services.forgecrawler import ForgeCrawler
from app.services.source_relevance_gate import source_relevance_gate


def greenwatch_context() -> Dict[str, Any]:
    structured = {
        "project_name": "GreenWatch Robot",
        "market_region": "Tunisie",
        "target_region": "Tunisie",
        "sector": "Agriculture intelligente et robotique",
        "industry": "Agriculture intelligente et robotique",
        "project_archetype": "hardware_iot_robotics",
        "vertical": "agriculture",
        "target_users": [
            "propriétaires de serres",
            "responsables de pépinières",
            "coopératives agricoles",
        ],
        "priority_workflows": [
            "inspecter régulièrement les cultures avec une caméra et des capteurs",
            "détecter les anomalies",
            "transmettre les résultats à un tableau de bord avec des alertes",
        ],
        "solution_category": (
            "robot autonome inspection cultures vision capteurs tableau de bord"
        ),
        "domain_concepts": [
            "agriculture intelligente",
            "robotique agricole",
            "serres",
            "cultures",
            "vision",
            "capteurs",
        ],
        "use_case_terms": [
            "inspection cultures",
            "détection anomalies",
            "monitoring serre",
        ],
        "solution_terms": [
            "robot autonome",
            "caméra",
            "capteurs",
            "tableau de bord",
        ],
    }
    packet = {
        "domain_concepts": structured["domain_concepts"],
        "target_terms": structured["target_users"],
        "use_case_terms": structured["use_case_terms"],
        "solution_terms": structured["solution_terms"],
    }
    return {
        "output_language": "fr",
        "market_region": "Tunisie",
        "industry": structured["industry"],
        "structured_project_context": structured,
        "agent_context_packet": packet,
    }


def test_local_adjacent_solution_is_public_but_never_direct() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Smart Farm – La technologie au service de l’agriculture",
            "url": "https://smartfarm.com.tn/en",
            "snippet": "Smart agriculture monitoring platform in Tunisia.",
            "extracted_text_preview": (
                "Our smart agriculture platform uses sensors, monitoring, "
                "dashboard and crop data for farms and greenhouses. Features, "
                "customers, sign up and contact sales."
            ),
            "text_extracted": True,
            "ai_source_type": "adjacent_solution",
            "ai_classifier_confidence": 0.84,
            "ai_same_sector": True,
            "ai_same_workflow": False,
            "ai_product_page": True,
        },
        project_context=greenwatch_context(),
    )

    assert decision["public_display"] is True
    assert decision["rejected"] is False
    assert decision["canonical_category"] == "adjacent_solution"
    assert decision["source_role"] == "adjacent_solution"
    assert decision["is_direct_competitor"] is False
    assert "adjacent_solution" in decision["evidence_categories"]


def test_local_ecosystem_actor_survives_ai_irrelevant_label() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": (
                "Agriculture intelligente : 20 startups et 200 investisseurs "
                "réunis à Tunis"
            ),
            "url": (
                "https://webmanagercenter.com/2026/06/11/"
                "agriculture-intelligente-startups-tunis"
            ),
            "snippet": (
                "Un événement de l’écosystème AgriTech tunisien réunit "
                "startups, investisseurs et agriculteurs."
            ),
            "extracted_text_preview": (
                "Programme d’innovation en agriculture intelligente en Tunisie. "
                "Startups, investisseurs, incubateurs et acteurs agricoles "
                "présentent des solutions pour les cultures et les serres."
            ),
            "text_extracted": True,
            "ai_source_type": "irrelevant",
            "ai_classifier_confidence": 0.95,
            "ai_same_sector": True,
            "ai_product_page": False,
        },
        project_context=greenwatch_context(),
    )

    assert decision["public_display"] is True
    assert decision["source_type"] == "local_ecosystem"
    assert decision["source_role"] == "local_ecosystem"
    assert decision["canonical_category"] == "ecosystem_actor"
    assert decision["is_direct_competitor"] is False


def test_technology_benchmark_is_retained_without_exact_target_match() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Dilepix – Intelligence artificielle en agriculture de précision",
            "url": "https://dilepix.com/",
            "snippet": "Computer vision for crop disease and precision agriculture.",
            "extracted_text_preview": (
                "Our product uses computer vision, cameras and artificial "
                "intelligence to detect crop diseases. Features, customers and "
                "request demo."
            ),
            "text_extracted": True,
            "ai_source_type": "technology_benchmark",
            "ai_classifier_confidence": 0.90,
            "ai_same_sector": True,
            "ai_same_workflow": True,
            "ai_product_page": True,
        },
        project_context=greenwatch_context(),
    )

    assert decision["public_display"] is True
    assert decision["canonical_category"] == "technology_benchmark"
    assert decision["source_role"] == "technology_provider"
    assert decision["is_direct_competitor"] is False


def test_market_report_is_retained_as_claim_not_verified_market_size() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Agricultural Robots Market Size and Report",
            "url": (
                "https://mordorintelligence.com/industry-reports/"
                "agricultural-robots-market"
            ),
            "snippet": "Agricultural robots market size, growth and forecast.",
            "extracted_text_preview": (
                "The agricultural robots market size, market share and CAGR "
                "forecast covers autonomous robots, computer vision, cameras "
                "and sensors for farms."
            ),
            "text_extracted": True,
            "ai_source_type": "market_article",
            "ai_classifier_confidence": 0.90,
            "ai_same_sector": True,
            "ai_product_page": False,
        },
        project_context=greenwatch_context(),
    )

    assert decision["public_display"] is True
    assert decision["canonical_category"] == "market_evidence"
    assert "market_size_claim" in decision["evidence_categories"]
    assert "market_size" not in decision["evidence_categories"]
    assert decision["is_direct_competitor"] is False


def test_unrelated_healthcare_product_is_rejected() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Hospital patient scheduling software",
            "url": "https://example-health.com/",
            "snippet": "Medical scheduling platform for hospitals and clinics.",
            "extracted_text_preview": (
                "Features, pricing, customers, patient scheduling and clinic booking."
            ),
            "text_extracted": True,
            "ai_source_type": "adjacent_solution",
            "ai_classifier_confidence": 0.90,
            "ai_same_sector": False,
            "ai_same_workflow": False,
            "ai_product_page": True,
        },
        project_context=greenwatch_context(),
    )

    assert decision["public_display"] is False
    assert decision["rejected"] is True

    # Without a closed sector taxonomy the resolver may retain an
    # adjacent-solution candidate role from weak structural overlap.
    # The relevance gate remains authoritative for publication safety:
    # unrelated evidence must be rejected and can never become direct.
    assert decision["canonical_category"] != "direct_competitor"
    assert decision["source_role"] != "direct_competitor"
    assert decision["is_direct_competitor"] is False


def test_canonical_ledger_keeps_one_primary_category_per_source() -> None:
    sources = [
        {
            "title": "Smart Farm",
            "url": "https://smartfarm.com.tn/en",
            "source_role": "adjacent_solution",
            "canonical_category": "adjacent_solution",
            "source_relevance_score": 0.45,
            "public_display": True,
        },
        {
            "title": "AgriTech event",
            "url": "https://example.tn/agritech-event",
            "source_role": "local_ecosystem",
            "canonical_category": "ecosystem_actor",
            "source_relevance_score": 0.60,
            "public_display": True,
        },
        {
            "title": "Dilepix",
            "url": "https://dilepix.com/",
            "source_role": "technology_provider",
            "canonical_category": "technology_benchmark",
            "source_relevance_score": 0.55,
            "public_display": True,
        },
    ]

    ledger = canonical_source_ledger.build(sources)

    assert ledger["sources_count"] == 3
    assert ledger["counts"]["adjacent_solutions"] == 1
    assert ledger["counts"]["ecosystem_actors"] == 1
    assert ledger["counts"]["technology_benchmarks"] == 1
    assert not ledger["direct_competitor_sources"]

    category_memberships = sum(
        len(ledger["categories"][category])
        for category in (
            "direct_competitor",
            "adjacent_solution",
            "technology_benchmark",
            "market_evidence",
            "ecosystem_actor",
        )
    )
    assert category_memberships == ledger["sources_count"]


def test_final_public_filter_does_not_delete_non_direct_evidence() -> None:
    agent = CompetitiveAnalysisAgent()
    context = greenwatch_context()
    structured = context["structured_project_context"]

    for source in (
        {
            "title": "Dilepix",
            "url": "https://dilepix.com/",
            "source_type": "technology_benchmark",
            "source_role": "technology_provider",
            "canonical_category": "technology_benchmark",
            "source_relevance_score": 0.56,
            "public_display": True,
            "internal_only": False,
            "rejected": False,
            "matched_strong_terms": ["agriculture", "vision", "capteurs"],
            "matched_forbidden_terms": [],
            "evidence_categories": ["technology_benchmark"],
            "same_or_close_target_user": False,
            "same_or_close_use_case": False,
            "same_or_close_solution_category": False,
            "is_direct_competitor": False,
        },
        {
            "title": "AgriTech Tunisia event",
            "url": "https://example.tn/agritech-event",
            "source_type": "local_ecosystem",
            "source_role": "local_ecosystem",
            "canonical_category": "ecosystem_actor",
            "region_match": "local",
            "source_relevance_score": 0.40,
            "public_display": True,
            "internal_only": False,
            "rejected": False,
            "matched_strong_terms": ["agriculture intelligente"],
            "matched_forbidden_terms": [],
            "evidence_categories": ["local_ecosystem", "ecosystem_signal"],
            "is_direct_competitor": False,
        },
    ):
        reason = agent._public_source_rejection_reason(
            source=source,
            title="GreenWatch Robot",
            structured_project_context=structured,
            project_context=context,
        )
        assert reason == ""


def test_query_planner_does_not_invent_tunisia_when_region_is_empty() -> None:
    crawler = ForgeCrawler()
    context = crawler._build_project_context(
        idea="Application de gestion de réservations pour salons de coiffure.",
        industry="BeautyTech",
        region="",
        project_context={
            "title": "SalonFlow",
            "domain_concepts": ["salon booking", "hair salon"],
            "use_case_terms": ["book appointment"],
            "solution_terms": ["booking software"],
        },
        agent_context_packet=None,
        query_planner=None,
    )
    queries = crawler._build_queries(
        idea="Application de gestion de réservations pour salons de coiffure.",
        industry="BeautyTech",
        region="",
        project_context=context,
    )

    assert context.get("target_region") == ""
    assert all("tunisie" not in query.lower() for query in queries)
    assert all("tunisia" not in query.lower() for query in queries)

def test_locality_target_and_one_sector_word_are_not_public_evidence() -> None:
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Application agriculture Tunisie",
            "url": "https://generic-agri-app.example/",
            "snippet": "Application pour propriétaires de serres tunisiens",
            "extracted_text_preview": (
                "Une application pour les propriétaires de serres afin de "
                "communiquer avec leurs clients. Sign up and login."
            ),
            "text_extracted": True,
        },
        project_context=greenwatch_context(),
    )

    assert decision["is_direct_competitor"] is False
    assert decision["public_display"] is False