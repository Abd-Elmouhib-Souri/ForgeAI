import asyncio
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
    embedding_stub = types.SimpleNamespace(
        DefaultEmbeddingFunction=lambda: (lambda values: values)
    )
    utils_stub.embedding_functions = embedding_stub

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

from app.agents.business_analyst_agent import AIBusinessAnalystAgent
from app.agents.fact_checker_agent import FactCheckerAgent
from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.agents.startup_evaluator_graph import StartupEvaluatorGraph
from app.agents.startup_evaluator_llm import extract_json_object, repair_object_encoding
from app.services.evidence_ledger import evidence_ledger
from app.services.public_analysis_sanitizer import sanitize_analysis_data_for_public


def _greenwatch_structured_context():
    description = (
        "GreenWatch est un robot autonome destiné aux propriétaires de serres, "
        "responsables de pépinières et coopératives agricoles. Il inspecte les "
        "cultures, détecte les maladies et le manque d’eau. Le modèle économique "
        "combine la location du robot, la maintenance et un abonnement mensuel. "
        "Contraintes : coût du matériel, autonomie de la batterie, précision de "
        "détection et connectivité dans les serres."
    )
    return {
        "project_name": "GreenWatch Robot",
        "description": description,
        "target_region": "Tunisie",
        "target_users": [
            "propriétaires de serres",
            "responsables de pépinières",
            "coopératives agricoles",
        ],
        "problem": "L’inspection manuelle des cultures est lente et irrégulière.",
        "solution": "Un robot autonome avec caméra, capteurs et tableau de bord.",
        "priority_workflows": [
            "inspecter régulièrement les cultures avec une caméra et des capteurs",
            "détecter les maladies et le manque d’eau",
            "transmettre les alertes au tableau de bord",
        ],
        "project_archetype": "hardware_iot",
        "success_metrics": [
            "détecter au moins 85 % des anomalies",
            "réduire le temps d’inspection",
        ],
        "constraints": [
            "coût du matériel",
            "autonomie de la batterie",
            "précision de détection",
            "connectivité dans les serres",
        ],
        "risk_dimensions": [
            "Le modèle économique combine la location du robot",
            "la maintenance",
            "un abonnement mensuel au tableau de bord",
            "charge de maintenance",
        ],
    }


def _sources():
    return [
        {
            "title": "Agriculture moderne en Tunisie",
            "url": "https://example.org/agriculture-tunisie",
            "source_type": "market_evidence",
            "source_role": "local_market_signal",
            "canonical_category": "market_evidence",
            "region_match": "local",
            "evidence_categories": [
                "local_market_signal",
                "market_demand_claim",
            ],
            "source_relevance_score": 0.72,
            "public_display": True,
            "snippet": (
                "Des exploitations tunisiennes testent des outils agricoles "
                "connectés et des solutions d’agriculture de précision."
            ),
        },
        {
            "title": "Robot agricole autonome avec IA",
            "url": "https://vendor.example/robot-agricole",
            "source_type": "technology_benchmark",
            "source_role": "technology_benchmark",
            "canonical_category": "technology_benchmark",
            "region_match": "international",
            "evidence_categories": ["technology_benchmark"],
            "source_relevance_score": 0.81,
            "public_display": True,
            "snippet": (
                "Robot autonome pour inspection agricole et détection de maladies."
            ),
        },
        {
            "title": "Agricultural Robot Market Report",
            "url": "https://www.marketsandmarkets.com/agricultural-robots-market",
            "source_type": "market_evidence",
            "source_role": "market_evidence",
            "canonical_category": "market_evidence",
            "region_match": "international",
            "evidence_categories": ["market_size_claim"],
            "source_relevance_score": 0.68,
            "public_display": True,
            "snippet": "Commercial market report landing page without visible methodology.",
        },
    ]


def _analysis_data():
    return {
        "output_language": "fr",
        "problem": "L’inspection manuelle des cultures est lente et irrégulière.",
        "proposed_solution": "Un robot autonome inspecte les cultures et détecte les anomalies.",
        "forgecrawler": {
            "status": "completed",
            "confidence_level": "medium",
            "sources": _sources(),
        },
        "competitive_analysis": {
            "status": "completed",
            "confidence_level": "low",
            "sources": _sources(),
        },
        "market_study": {
            "market_size": "Le marché atteindra 20 milliards USD en 2030.",
            "local_feasibility": (
                "Un pilote local peut être exploré auprès des serres tunisiennes."
            ),
            "market_trends": [
                "Les robots autonomes progressent dans l’agriculture de précision."
            ],
            "data_confidence": "low",
        },
        "financial_estimation": {
            "estimated_mvp_budget": "15 000 à 47 000 TND — estimation de planification",
            "roi_outlook": "Le retour dépend du nombre de pilotes payants.",
            "infrastructure_costs": "Robot, capteurs, intégration, tests et déploiement.",
            "financial_risk_level": "high",
        },
    }


def test_business_analyst_preserves_local_candidate_after_domain_guard(monkeypatch):
    from app.agents import business_analyst_agent as module

    monkeypatch.setattr(
        module.domain_integrity_guard,
        "validate_object",
        lambda **_: {"is_valid": False},
    )
    monkeypatch.setattr(
        module.domain_integrity_guard,
        "sanitize_object",
        lambda **kwargs: {
            key: value
            for key, value in kwargs["data"].items()
            if not key.startswith("local_market")
        },
    )

    agent = object.__new__(AIBusinessAnalystAgent)
    result = agent._post_process_result(
        result={
            "innovation_score": 7,
            "difficulty": "high",
            "recommended_technologies": ["Robot", "Caméra", "Capteurs"],
            "improvement_suggestions": ["Tester un pilote", "Mesurer", "Interviewer"],
            "sources_used": [],
        },
        input_data={
            "title": "GreenWatch Robot",
            "region": "Tunisie",
            "output_language": "fr",
        },
        project_context={"anchor_terms": ["robot agricole"]},
        local_rag_result={
            "candidates": [
                {
                    "title": "Smart Farm Tunisia",
                    "url": "https://example.tn/smart-farm",
                    "status": "reclassify",
                    "rejected": True,
                    "hard_rejected": False,
                    "public_display": False,
                }
            ]
        },
    )

    assert len(result["local_market_candidates"]) == 1
    assert result["local_market_candidates"][0]["retained_for_reclassification"] is True
    assert result["local_market_handoff_meta"]["candidate_count"] == 1


def test_hardware_personas_do_not_invent_buyer_or_maintainer_roles():
    structured = _greenwatch_structured_context()
    result = asyncio.run(
        PersonaBuilderAgent().run(
            {
                "title": structured["project_name"],
                "description": structured["description"],
                "industry": "Agriculture intelligente et robotique",
                "region": "Tunisie",
                "output_language": "fr",
                "structured_project_context": structured,
            }
        )
    )

    assert result["actor_role_map"]["economic_buyer_status"] == "to_validate"
    assert result["actor_role_map"]["technical_maintainer_status"] == "to_validate"
    assert [persona["name"] for persona in result["personas"]] == structured["target_users"]
    assert all(persona["buyer_status"] == "non_identifie" for persona in result["personas"])
    assert all(persona["maintenance_status"] == "non_identifie" for persona in result["personas"])
    assert all("Détenteur du budget" not in persona["role"] for persona in result["personas"])
    assert all("Responsable maintenance" not in persona["role"] for persona in result["personas"])


def test_persona_risks_exclude_business_model_fragments():
    structured = _greenwatch_structured_context()
    result = asyncio.run(
        PersonaBuilderAgent().run(
            {
                "title": structured["project_name"],
                "description": structured["description"],
                "region": "Tunisie",
                "output_language": "fr",
                "structured_project_context": structured,
            }
        )
    )
    normalized = " | ".join(result["persona_risks"]).lower()
    assert "abonnement mensuel" not in normalized
    assert "location du robot" not in normalized
    assert "le modèle économique" not in normalized
    assert "autonomie de la batterie" in normalized
    assert "précision de détection" in normalized


def test_evidence_ledger_recognizes_v8_categories_and_rejects_unsupported_number():
    ledger = evidence_ledger.build(_analysis_data())
    claims = {item["path"]: item for item in ledger["claims"]}

    assert ledger["confidence_by_category"]["local_market_confidence"] in {"medium", "high"}
    assert ledger["confidence_by_category"]["solution_benchmark"] in {"medium", "high"}
    assert claims["market_study.market_size"]["status"] == "not_confirmed"
    assert claims["market_study.market_trends[0]"]["status"] == "sourced"

    commercial = next(
        item
        for item in ledger["source_index"].values()
        if "marketsandmarkets" in item.get("url", "")
    )
    assert commercial["evidence_quality"] == "low"
    assert commercial["methodology_visible"] is False


def test_market_study_enrichment_uses_evidence_without_inventing_figures():
    graph = object.__new__(StartupEvaluatorGraph)
    analysis = _analysis_data()
    analysis["evidence_ledger"] = evidence_ledger.build(analysis)

    enriched = graph._enrich_market_study_from_evidence(
        market_study={"local_feasibility": "—", "market_trends": []},
        analysis_data=analysis,
        output_language="fr",
    )

    assert enriched["local_evidence_status"] == "signal_only"
    assert "ne prouvent pas encore" in enriched["local_feasibility"]
    assert enriched["market_trends"]
    assert not any("20 milliards" in trend for trend in enriched["market_trends"])


def test_fact_checker_contains_section_specific_claims_not_only_five_templates():
    analysis = _analysis_data()
    result = asyncio.run(
        FactCheckerAgent().run(
            {
                "title": "GreenWatch Robot",
                "description": _greenwatch_structured_context()["description"],
                "industry": "Agriculture intelligente et robotique",
                "region": "Tunisie",
                "output_language": "fr",
                "analysis_data": analysis,
                "project_context": {
                    "title": "GreenWatch Robot",
                    "description": _greenwatch_structured_context()["description"],
                    "industry": "Agriculture intelligente et robotique",
                    "market_region": "Tunisie",
                    "anchor_terms": ["robot agricole", "serre", "détection"],
                },
            }
        )
    )

    assert len(result["claims"]) > 5
    paths = {claim.get("path") for claim in result["claims"]}
    assert "market_study.local_feasibility" in paths
    assert "market_study.market_trends[0]" in paths
    assert result["claim_coverage"]["section_specific"] >= 2


def test_public_sanitizer_hides_handoff_and_repairs_text_tokens():
    sanitized = sanitize_analysis_data_for_public(
        {
            "output_language": "fr",
            "summary": "Lâ€™analyse Io T utilise Lo Ra WAN et 4 G/5 G.",
            "local_market_candidates": [{"url": "https://private.example"}],
            "local_market_handoff_meta": {"candidate_count": 1},
            "persona_builder": {
                "summary": "Lâ€™utilisateur consulte les alertes Io T via Lo Ra WAN."
            },
        },
        {"title": "GreenWatch", "output_language": "fr"},
    )

    assert "local_market_candidates" not in sanitized
    assert "local_market_handoff_meta" not in sanitized
    assert sanitized["summary"] == "L’analyse IoT utilise LoRaWAN et 4G/5G."
    assert sanitized["persona_builder"]["summary"] == (
        "L’utilisateur consulte les alertes IoT via LoRaWAN."
    )


def test_startup_evaluator_llm_repairs_encoding_and_trailing_comma():
    parsed = extract_json_object(
        '```json\n{"summary": "Lâ€™analyse est terminÃ©e", "score": 7,}\n```'
    )
    repaired = repair_object_encoding(parsed)
    assert repaired == {"summary": "L’analyse est terminée", "score": 7}