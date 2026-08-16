from __future__ import annotations

import importlib.util
import sys
import types
from importlib.machinery import ModuleSpec

if importlib.util.find_spec("chromadb") is None:
    chromadb_stub = types.ModuleType("chromadb")
    chromadb_stub.__spec__ = ModuleSpec("chromadb", loader=None)
    chromadb_stub.HttpClient = lambda *args, **kwargs: None

    config_stub = types.ModuleType("chromadb.config")
    config_stub.__spec__ = ModuleSpec("chromadb.config", loader=None)

    class _Settings:
        def __init__(self, *args, **kwargs):
            pass

    config_stub.Settings = _Settings
    utils_stub = types.ModuleType("chromadb.utils")
    utils_stub.__spec__ = ModuleSpec("chromadb.utils", loader=None)
    utils_stub.embedding_functions = types.SimpleNamespace(
        DefaultEmbeddingFunction=lambda: (lambda values: values)
    )
    sys.modules["chromadb"] = chromadb_stub
    sys.modules["chromadb.config"] = config_stub
    sys.modules["chromadb.utils"] = utils_stub

if importlib.util.find_spec("langgraph") is None:
    langgraph_stub = types.ModuleType("langgraph")
    langgraph_stub.__spec__ = ModuleSpec("langgraph", loader=None)
    graph_stub = types.ModuleType("langgraph.graph")
    graph_stub.__spec__ = ModuleSpec("langgraph.graph", loader=None)
    graph_stub.END = "END"

    class _StateGraph:
        def __init__(self, *args, **kwargs):
            pass

        def add_node(self, *args, **kwargs):
            return None

        def set_entry_point(self, *args, **kwargs):
            return None

        def add_edge(self, *args, **kwargs):
            return None

        def compile(self):
            return types.SimpleNamespace(ainvoke=None)

    graph_stub.StateGraph = _StateGraph
    sys.modules["langgraph"] = langgraph_stub
    sys.modules["langgraph.graph"] = graph_stub

from app.agents.competitive_analysis_agent import CompetitiveAnalysisAgent
from app.agents.debate_room_graph import DebateRoomGraph
from app.agents.fact_checker_agent import FactCheckerAgent
from app.agents.startup_evaluator_graph import StartupEvaluatorGraph
from app.services.source_relevance_gate import SourceRelevanceGate


def _greenwatch_context() -> dict:
    structured = {
        "project_name": "GreenWatch Robot",
        "sector": "Agriculture intelligente et robotique",
        "industry": "Agriculture intelligente et robotique",
        "target_region": "Tunisie",
        "target_users": [
            "propriétaires de serres",
            "responsables de pépinières",
            "coopératives agricoles",
        ],
        "problem": (
            "L’inspection manuelle des cultures demande du temps et détecte "
            "parfois trop tard les maladies et le manque d’eau."
        ),
        "solution": (
            "Un robot autonome inspecte les cultures avec une caméra, des "
            "capteurs et de la vision artificielle."
        ),
        "priority_workflows": [
            "inspecter régulièrement les cultures avec une caméra et des capteurs",
            "détecter les anomalies",
        ],
        "solution_category": "robot agricole autonome avec vision artificielle",
        "project_archetype": "hardware_iot",
    }
    return {
        "output_language": "fr",
        "structured_project_context": structured,
        "project_intelligence": {
            "structured_project_context": structured,
        },
        "agent_context_packet": {
            "domain_concepts": [
                "agriculture intelligente",
                "robotique agricole",
                "inspection des cultures",
                "vision artificielle",
                "capteurs IoT",
            ],
            "target_terms": structured["target_users"],
            "use_case_terms": structured["priority_workflows"],
            "solution_terms": [
                "robot agricole autonome",
                "vision artificielle",
                "capteurs IoT",
            ],
        },
    }


def test_generic_job_listing_is_not_local_ecosystem_evidence() -> None:
    gate = SourceRelevanceGate()
    decision = gate.evaluate_source(
        source={
            "title": "Emploi Responsable Intelligence Artificielle en Tunisie",
            "url": (
                "https://keejob.com/offres-emploi/243481/"
                "responsable-intelligence-artificielle"
            ),
            "snippet": (
                "Poste à pourvoir. Candidature pour un responsable IA. "
                "Agriculture intelligente, robotique et pépinières."
            ),
            "extracted_text_preview": (
                "Job description, apply now, carrière et recrutement."
            ),
            "ai_source_type": "local_ecosystem",
            "ai_classifier_confidence": 0.98,
            "ai_same_sector": True,
        },
        project_context=_greenwatch_context(),
    )

    assert decision["source_type"] == "irrelevant"
    assert decision["source_role"] == "irrelevant"
    assert decision["canonical_category"] == "irrelevant"
    assert decision["public_display"] is False
    assert decision["rejected"] is True



def test_unverified_provider_blog_is_not_exposed_as_verified_direct_competitor() -> None:
    gate = SourceRelevanceGate()

    decision = gate.evaluate_source(
        source={
            "title": (
                "DronIA - AI Agricultural Automation "
                "Solution Tunisia | Galylio"
            ),
            "url": "https://galylio.com/blog/dronia",
            "snippet": (
                "DronIA is an agricultural automation solution "
                "in Tunisia using AI, drones and computer vision "
                "to inspect crops."
            ),
            "extracted_text_preview": (
                "The DronIA solution supports agricultural "
                "inspection, crop monitoring, computer vision "
                "and automated alerts."
            ),
            "ai_source_type": "market_evidence",
            "ai_classifier_confidence": 0.82,
            "ai_same_sector": True,
            "ai_same_workflow": True,
        },
        project_context=_greenwatch_context(),
    )

    assert decision["region_match"] == "local"

    # Universal safety invariant:
    # a candidate that did not pass final direct-competitor
    # verification must never be exposed publicly as one.
    assert decision["is_direct_competitor"] is False
    assert decision["public_display"] is False



def test_competitive_region_counts_use_all_canonical_sources() -> None:
    counts = CompetitiveAnalysisAgent()._region_counts(
        [
            {"region_match": "local"},
            {"region_match": "local"},
            {"region_match": "regional"},
            {"region_match": "international"},
            {"region_match": "international"},
            {"region_match": "unknown"},
        ]
    )
    assert counts == {
        "local": 2,
        "regional": 1,
        "international": 2,
        "unknown": 1,
    }


def test_adjacent_solution_is_not_duplicated_as_market_context() -> None:
    agent = CompetitiveAnalysisAgent()
    rows = [
        {
            "title": "DronIA",
            "url": "https://galylio.com/blog/dronia",
            "source_type": "adjacent_solution",
            "canonical_category": "adjacent_solution",
            "region_match": "local",
        },
        {
            "title": "SMART AGRI",
            "url": "https://example.org/smart-agri",
            "source_type": "market_article",
            "canonical_category": "market_evidence",
            "region_match": "local",
        },
    ]

    cards = agent._market_context_sources(sources=rows)
    assert [item["title"] for item in cards] == ["SMART AGRI"]



def test_market_trends_replace_dash_with_cautious_evidence_signals() -> None:
    graph = StartupEvaluatorGraph.__new__(
        StartupEvaluatorGraph
    )

    result = graph._enrich_market_study_from_evidence(
        market_study={
            "market_trends": "\u2014"
        },
        analysis_data={
            "evidence_ledger": {
                "source_index": {
                    "local": {
                        "source_id": "local",
                        "title": "Initiative AgriTech Tunisie",
                        "region_match": "local",
                        "source_type": "market_article",
                        "evidence_quality": "medium",
                        "evidence_categories": [
                            "regional_context",
                            "local_market_signal",
                        ],
                    },
                    "tech": {
                        "source_id": "tech",
                        "title": "Agricultural inspection robot",
                        "region_match": "international",
                        "source_type": "technology_benchmark",
                        "evidence_quality": "medium",
                        "evidence_categories": [
                            "technology_benchmark",
                            "solution_benchmark",
                        ],
                    },
                }
            }
        },
        output_language="fr",
    )

    trends = result["market_trends"]

    assert isinstance(trends, list)
    assert trends

    assert all(
        isinstance(item, str)
        and item.strip()
        and item.strip() != "\u2014"
        for item in trends
    )

    # Presentation wording is not an authority contract.
    # The invariant is that evidence produces cautious,
    # non-empty signals without inventing a domain phrase.
    assert result["trends"] == trends
    assert result["local_evidence_status"] == "signal_only"

    assert any(
        item.get("source_type")
        == "technology_benchmark"
        for item in result["evidence_basis"]
    )




def test_fact_checker_filters_generic_demand_drivers_without_reclassifying_status() -> None:
    agent = FactCheckerAgent()

    registry = {
        "source_index": {
            "src-1": {
                "title": "Source",
                "url": "https://robotique.site/benchmark",
                "source_type": "technology_benchmark",
                "region_match": "international",
                "evidence_categories": [
                    "solution_benchmark"
                ],
            }
        },
        "claims": [
            {
                "claim_id": "market-size",
                "path": "market_study.market_size",
                "category": "market_size",
                "claim": (
                    "Non confirm\u00e9. Les donn\u00e9es fournies "
                    "ne permettent pas de quantifier "
                    "le march\u00e9 tunisien."
                ),
                "status": "sourced",
                "confidence": "medium",
                "source_ids": ["src-1"],
            },
            {
                "claim_id": "generic-driver",
                "path": "market_study.demand_drivers[0]",
                "category": "general",
                "claim": (
                    "Pression pour para\u00eetre plus "
                    "professionnel aupr\u00e8s des clients."
                ),
                "status": "sourced",
                "confidence": "medium",
                "source_ids": ["src-1"],
            },
        ],
    }

    claims = agent._claims_from_registry(
        registry=registry,
        language="fr",
        fallback_sources=[
            {
                "title": (
                    "Agriculture intelligente "
                    "connect\u00e9e \u00e0 IoT"
                ),
                "url": "https://robotique.site/benchmark",
                "source_type": "technology_benchmark",
                "region_match": "international",
                "evidence_categories": [
                    "solution_benchmark"
                ],
            }
        ],
    )

    # FactChecker is a presentation consumer.
    # It may filter a non-public card, but it must not
    # replace the upstream evidence classification.
    assert len(claims) == 1
    assert claims[0]["status"] == "sourced"
    assert claims[0]["public_status"] == "Sourc\u00e9"

    assert claims[0]["evidence"][0]["title"] == (
        "Agriculture intelligente connect\u00e9e \u00e0 IoT"
    )




def test_debate_frequency_question_has_article_and_dynamic_confidence() -> None:
    graph = DebateRoomGraph()

    question = graph._frequency_question(
        {
            "primary_target": "propri\u00e9taires de serres",
            "priority_workflow": (
                "inspecter r\u00e9guli\u00e8rement les cultures"
            ),
        },
        "fr",
    )

    assert (
        "par les propri\u00e9taires de serres"
        in question
    )
    assert (
        "par propri\u00e9taires de serres"
        not in question
    )

    values = {
        graph._adaptive_question_confidence(
            asked_by=role,
            support_status="field_validation_required",
            round_number=1,
        )
        for role in (
            "customer_problem_analyst",
            "market_competition_analyst",
            "risk_execution_officer",
            "evidence_auditor",
            "red_team_challenger",
        )
    }

    assert len(values) >= 4



def test_public_python_files_do_not_contain_mojibake_markers() -> None:
    outputs = [
        SourceRelevanceGate()._public_reason(
            source_type="market_article",
            source_role="market_evidence",
            canonical_category="market_evidence",
            region_match="local",
            evidence_categories=["local_market_signal"],
            output_language="fr",
        ),
        CompetitiveAnalysisAgent()._short_why_relevant(
            {
                "canonical_category": "ecosystem_actor",
                "region_match": "local",
            }
        ),
    ]
    assert all("Ã" not in value and "â€" not in value for value in outputs)
    assert "marché" in outputs[0]
    assert "écosystème" in outputs[1]
