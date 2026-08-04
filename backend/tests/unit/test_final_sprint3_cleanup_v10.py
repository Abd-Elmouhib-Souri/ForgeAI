from __future__ import annotations

import asyncio

from app.agents.bmc_agent import BMCAgent
from app.agents.business_analyst_agent import AIBusinessAnalystAgent
from app.agents.debate_room_graph import DebateRoomGraph
from app.rag.web_dynamic_rag import copy_local_source_contract
from app.services.domain_integrity_guard import domain_integrity_guard
from app.services.forgecrawler import ForgeCrawler
from app.services.public_analysis_sanitizer import (
    sanitize_analysis_data_for_public,
)


def _structured_hardware_context() -> dict:
    return {
        "project_name": "GreenWatch Robot",
        "sector": "Agriculture intelligente et robotique",
        "target_region": "Tunisie",
        "target_users": [
            "propriétaires de serres",
            "responsables de pépinières",
            "coopératives agricoles",
        ],
        "problem": "L’inspection manuelle est irrégulière et coûteuse.",
        "solution": "Un robot inspecte les cultures et envoie des alertes.",
        "project_archetype": "hardware_iot",
        "priority_workflows": [
            "inspecter régulièrement les cultures avec une caméra et des capteurs",
            "détecter les anomalies",
            "transmettre les résultats à un tableau de bord avec des alertes",
        ],
        "validation_unit": "inspection complète d’une serre",
        "business_model": "location du robot et abonnement au tableau de bord",
        "actors": {
            "payer": "coopératives agricoles",
            "technical_maintainer": "responsables de pépinières",
        },
        # No provenance is supplied: the two assignments above are hypotheses,
        # not facts that may be shown as confirmed roles.
        "success_metrics": ["détecter au moins 85 % des anomalies"],
        "constraints": ["coût du matériel", "fiabilité terrain"],
    }


def test_local_rag_contract_preserves_reclassification_flags() -> None:
    source = copy_local_source_contract(
        {
            "title": "SMART AGRI",
            "url": "https://smart-agri.example.tn/project",
            "candidate_status": "internal_candidate",
            "requires_canonical_recheck": True,
            "rejected": True,
            "hard_rejected": False,
            "canonical_category": "adjacent_solution",
            "region_match": "local",
            "text": "Projet agricole tunisien utilisant des capteurs et une plateforme.",
        }
    )

    assert source["candidate_status"] == "internal_candidate"
    assert source["requires_canonical_recheck"] is True
    assert source["retained_for_reclassification"] is True
    assert source["hard_rejected"] is False
    assert source["origin"] == "local_market_search"
    assert source["canonical_category"] == "adjacent_solution"
    assert source["body"]


def test_business_analyst_handoff_keeps_internal_candidate(monkeypatch) -> None:
    monkeypatch.setattr(
        domain_integrity_guard,
        "validate_object",
        lambda **_: {"is_valid": True},
    )

    agent = AIBusinessAnalystAgent.__new__(AIBusinessAnalystAgent)
    result = agent._post_process_result(
        result={
            "innovation_score": 7,
            "difficulty": "high",
            "recommended_technologies": ["ROS", "IoT", "LoRaWAN"],
            "improvement_suggestions": ["Tester le pilote"] * 3,
            "sources_used": [],
        },
        input_data={
            "title": "GreenWatch Robot",
            "description": "Robot de surveillance de serre",
            "industry": "Agriculture intelligente",
            "region": "Tunisie",
            "output_language": "fr",
            "structured_project_context": _structured_hardware_context(),
        },
        project_context={
            "title": "GreenWatch Robot",
            "industry": "Agriculture intelligente",
            "market_region": "Tunisie",
            "anchor_terms": ["robot", "serre", "inspection"],
            "structured_project_context": _structured_hardware_context(),
        },
        local_rag_result={
            "sources": [
                {
                    "title": "SMART AGRI",
                    "url": "https://smart-agri.example.tn/project",
                    "candidate_status": "internal_candidate",
                    "requires_canonical_recheck": True,
                    "retained_for_reclassification": True,
                    "rejected": True,
                    "hard_rejected": False,
                }
            ]
        },
    )

    assert len(result["local_market_candidates"]) == 1
    assert result["local_market_candidates"][0]["origin"] == "local_market_search"
    assert result["local_market_handoff_meta"]["candidate_count"] == 1


def test_bmc_does_not_promote_targets_to_payer_or_maintainer() -> None:
    result = asyncio.run(
        BMCAgent().run(
            {
                "output_language": "fr",
                "structured_project_context": _structured_hardware_context(),
            }
        )
    )

    segments = " ".join(result["customer_segments"])
    assert "Acheteur économique : Non identifié" in segments
    assert "Maintenance ou déploiement : Non identifié" in segments
    assert "Acheteur économique : coopératives agricoles" not in segments
    assert result["actor_role_provenance"]["payer"]["status"] == "to_confirm"
    assert (
        result["actor_role_provenance"]["technical_maintainer"]["status"]
        == "to_confirm"
    )


def test_bmc_accepts_only_explicit_role_provenance() -> None:
    structured = _structured_hardware_context()
    structured["actor_provenance"] = {
        "payer": "explicit",
        "technical_maintainer": "user_provided",
    }

    result = asyncio.run(
        BMCAgent().run(
            {
                "output_language": "fr",
                "structured_project_context": structured,
            }
        )
    )

    segments = " ".join(result["customer_segments"])
    assert "Acheteur économique : coopératives agricoles" in segments
    assert "Maintenance ou déploiement : responsables de pépinières" in segments


def test_debate_uses_explicit_users_without_inventing_marketplace_roles() -> None:
    graph = DebateRoomGraph()
    structured = _structured_hardware_context()

    context = graph._context(
        title="GreenWatch Robot",
        description="Robot de surveillance de serre",
        industry="Agriculture intelligente",
        region="Tunisie",
        project_context={
            "output_language": "fr",
            "structured_project_context": structured,
        },
        analysis={"structured_project_context": structured},
    )

    assert context["economic_buyer_status"] == "to_confirm"
    assert context["economic_buyer"] == "non identifié — à valider"
    assert context["demand_actor"] == ""
    assert context["supply_actor"] == ""
    assert context["operator_actor"] == ""

    evidence = {"level": "low", "score": 3.0, "sources": []}
    round_one = graph._round_adaptive_problem(
        1,
        context,
        {"competitive_analysis": {}},
        evidence,
        "fr",
    )

    first_question = round_one["committee_questions"][0]["question"]
    actor_answer = round_one["committee_questions"][1]["answer"]["direct_answer"]

    assert "À quelle fréquence l’action suivante est-elle" in first_question
    assert "inspecter régulièrement les cultures" in first_question
    assert "segments utilisateurs explicitement ciblés" in actor_answer
    assert "offre/partenaire=" not in actor_answer

    economics = graph._round_adaptive_economics(
        4,
        context,
        {},
        evidence,
        "fr",
    )
    assert (
        "Le payeur économique n’est pas encore identifié"
        in economics["committee_questions"][0]["answer"]["direct_answer"]
    )


def test_debate_vote_confidences_are_role_specific_and_explainable() -> None:
    votes = DebateRoomGraph()._votes(
        evidence_score=3.0,
        readiness=6.0,
        language="fr",
    )

    confidences = {vote["confidence"] for vote in votes}
    assert len(confidences) >= 4
    assert all("confidence_basis" in vote for vote in votes)
    assert all(
        vote["confidence_basis"]["formula"].startswith("0.30")
        for vote in votes
    )


def _source(
    index: int,
    *,
    category: str,
    region: str,
    source_type: str,
    role: str = "",
    direct: bool = False,
    score: float = 0.60,
) -> dict:
    return {
        "title": f"Source {index}",
        "url": f"https://source-{index}.example.com/page",
        "source_type": source_type,
        "source_role": role or category,
        "canonical_category": category,
        "region_match": region,
        "is_direct_competitor": direct,
        "source_relevance_score": score,
        "evidence_categories": ["market_demand"]
        if category == "market_evidence"
        else ["solution_benchmark"],
        "matched_domain_terms": ["agriculture", "robot"],
        "matched_use_case_terms": ["inspection"],
        "matched_solution_terms": ["robot"],
        "text_extracted": True,
    }


def test_forgecrawler_capacity_selection_preserves_source_diversity() -> None:
    crawler = ForgeCrawler(max_sources=8)
    sources = [
        _source(1, category="adjacent_solution", region="local", source_type="adjacent_solution", score=0.51),
        _source(2, category="adjacent_solution", region="local", source_type="adjacent_solution", score=0.50),
        _source(3, category="market_evidence", region="local", source_type="market_article", score=0.49),
        _source(4, category="market_evidence", region="local", source_type="market_article", score=0.48),
        _source(5, category="ecosystem_actor", region="local", source_type="market_article", score=0.47),
        _source(6, category="technology_benchmark", region="international", source_type="technology_benchmark", role="technology_provider", score=0.75),
        _source(7, category="technology_benchmark", region="international", source_type="technology_benchmark", role="technology_provider", score=0.74),
        _source(8, category="market_evidence", region="international", source_type="market_article", score=0.73),
        _source(9, category="market_evidence", region="international", source_type="market_article", score=0.72),
        _source(10, category="market_evidence", region="international", source_type="market_article", score=0.71),
        _source(11, category="market_evidence", region="international", source_type="market_article", score=0.70),
    ]

    selected, removed = crawler._select_public_sources(sources)
    buckets = [crawler._source_diversity_bucket(item) for item in selected]

    assert len(selected) == 8
    assert buckets.count("local_adjacent_solution") == 2
    assert buckets.count("local_market_evidence") == 2
    assert buckets.count("local_ecosystem_actor") == 1
    assert buckets.count("technology_benchmark") >= 1
    assert buckets.count("external_market_evidence") >= 1
    assert any(
        item.get("hygiene_reason")
        == "capacity_lower_priority_after_diversity"
        for item in removed
    )


def test_public_sanitizer_preserves_new_source_groups_and_cleans_text() -> None:
    sanitized = sanitize_analysis_data_for_public(
        {
            "output_language": "fr",
            "summary": "Capteurs Io T, Lo Ra WAN, Wi Fi et 4 G/5 G.",
            "persona_builder": {
                "limitations": [
                    "Les contraintes principales sont le coût du matériel",
                    "fiabilité terrain",
                ]
            },
            "forgecrawler": {
                "format": "forgecrawler_v10",
                "status": "completed",
                "confidence_level": "low",
                "sources_count": 1,
                "local_adjacent_solutions_count": 1,
                "technology_benchmarks_count": 0,
                "ecosystem_sources_count": 0,
                "market_sources_count": 0,
                "sources": [],
                "local_adjacent_solution_sources": [
                    {
                        "title": "Smart Farm",
                        "url": "https://smart-farm.example.tn",
                        "canonical_category": "adjacent_solution",
                        "region_match": "local",
                    }
                ],
            },
        },
        {"title": "GreenWatch Robot", "output_language": "fr"},
    )

    assert sanitized is not None
    assert sanitized["summary"] == "Capteurs IoT, LoRaWAN, Wi-Fi et 4G/5G."
    assert sanitized["persona_builder"]["limitations"] == ["fiabilité terrain"]
    assert (
        sanitized["forgecrawler"]["local_adjacent_solutions_count"] == 1
    )
    assert len(
        sanitized["forgecrawler"]["local_adjacent_solution_sources"]
    ) == 1