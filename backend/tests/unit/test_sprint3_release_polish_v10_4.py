from __future__ import annotations

from copy import deepcopy

from app.agents.fact_checker_agent import FactCheckerAgent
from app.services.evidence_ledger import EvidenceLedger
from app.services.source_relevance_gate import SourceRelevanceGate


def _market_source() -> dict:
    return {
        "title": "Agricultural Robots Market Size, Share & Report 2031",
        "url": "https://mordorintelligence.com/industry-reports/agricultural-robots-market",
        "source_type": "market_article",
        "source_role": "market_evidence",
        "canonical_category": "market_evidence",
        "region_match": "international",
        "pricing_found": True,
        "public_display": True,
        "evidence_quality": "low",
        "methodology_visible": False,
        "evidence_categories": [
            "market_size_claim",
            "sector_context",
            "pricing",
        ],
    }


def _greenwatch_context() -> dict:
    structured = {
        "project_name": "GreenWatch Robot",
        "sector": "Agriculture intelligente et robotique",
        "target_region": "Tunisie",
        "target_users": [
            "propriétaires de serres",
            "responsables de pépinières",
            "coopératives agricoles",
        ],
        "problem": "Inspection manuelle tardive des cultures sous serre.",
        "solution": "Robot agricole autonome avec caméra et capteurs IoT.",
        "priority_workflows": [
            "inspecter les cultures",
            "détecter les anomalies",
        ],
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


def test_internal_financial_estimate_never_inherits_market_pricing_source() -> None:
    ledger = EvidenceLedger().build(
        {
            "financial_estimation": {
                "estimated_mvp_budget": (
                    "Fourchette interne de planification : "
                    "15 100 TND à 47 500 TND."
                )
            },
            "competitive_analysis": {"sources": [_market_source()]},
        }
    )
    claim = next(
        item
        for item in ledger["claims"]
        if item["path"] == "financial_estimation.estimated_mvp_budget"
    )

    assert claim["status"] == "estimated"
    assert claim["confidence"] == "low"
    assert claim["source_ids"] == []
    assert "pricing" not in next(iter(ledger["source_index"].values()))[
        "evidence_categories"
    ]


def test_non_confirmed_market_size_is_not_marked_sourced() -> None:
    ledger = EvidenceLedger().build(
        {
            "market_study": {
                "market_size": (
                    "Non confirmé. Les données statistiques officielles "
                    "sur les serres ne sont pas présentes."
                )
            },
            "competitive_analysis": {"sources": [_market_source()]},
        }
    )
    claim = next(
        item
        for item in ledger["claims"]
        if item["path"] == "market_study.market_size"
    )

    assert claim["status"] == "not_confirmed"
    assert claim["confidence"] == "low"


def test_registry_finance_card_has_no_external_evidence() -> None:
    agent = FactCheckerAgent()
    ledger = EvidenceLedger().build(
        {
            "financial_estimation": {
                "estimated_mvp_budget": (
                    "Fourchette interne de planification : "
                    "15 100 TND à 47 500 TND."
                )
            },
            "competitive_analysis": {"sources": [_market_source()]},
        }
    )
    cards = agent._claims_from_registry(
        registry=ledger,
        language="fr",
        fallback_sources=[_market_source()],
    )
    card = next(
        item
        for item in cards
        if item["path"] == "financial_estimation.estimated_mvp_budget"
    )

    assert card["status"] == "estimated"
    assert card["evidence"] == []
    assert card["consulted_sources"] == []


def test_non_confirmed_claim_uses_consulted_sources_not_supporting_evidence() -> None:
    agent = FactCheckerAgent()
    ledger = EvidenceLedger().build(
        {
            "market_study": {
                "market_size": (
                    "Non confirmé. Les données officielles sur les serres "
                    "ne sont pas présentes."
                )
            },
            "competitive_analysis": {"sources": [_market_source()]},
        }
    )
    cards = agent._claims_from_registry(
        registry=ledger,
        language="fr",
        fallback_sources=[_market_source()],
    )
    card = next(
        item for item in cards if item["path"] == "market_study.market_size"
    )

    assert card["status"] == "not_confirmed"
    assert len(card["evidence"]) == 1
    assert card["evidence_kind"] == "consulted_insufficient"
    assert len(card["consulted_sources"]) == 1
    assert card["consulted_sources"][0]["display_title"].startswith(
        "Agricultural Robots"
    )


def test_local_context_is_a_recommendation_not_a_sourced_fact() -> None:
    local_source = {
        **_market_source(),
        "title": "SMART AGRI Tunisie",
        "url": "https://example.org/smart-agri",
        "region_match": "local",
        "evidence_quality": "medium",
        "evidence_categories": [
            "regional_context",
            "sector_context",
            "local_market_signal",
        ],
    }
    ledger = EvidenceLedger().build(
        {
            "market_study": {
                "local_context": (
                    "En Tunisie, la première validation doit se concentrer "
                    "sur des entretiens et des petits pilotes."
                )
            },
            "competitive_analysis": {"sources": [local_source]},
        }
    )
    cards = FactCheckerAgent()._claims_from_registry(
        registry=ledger,
        language="fr",
        fallback_sources=[local_source],
    )
    card = next(
        item for item in cards if item["path"] == "market_study.local_context"
    )

    assert card["status"] == "recommendation"
    assert card["category"] == "recommendation"
    assert card["evidence"] == []
    assert card["public_status"] == "Recommandation"


def test_public_report_repair_drops_injected_unmatched_claims() -> None:
    agent = FactCheckerAgent()
    fallback = {
        "claims": [
            {
                "claim_id": "known",
                "path": "market_study.market_size",
                "claim": "La taille du marché n’est pas confirmée.",
                "category": "market_size",
                "status": "not_confirmed",
                "confidence": "low",
                "evidence": [],
                "consulted_sources": [],
            }
        ]
    }
    sanitized = deepcopy(fallback)
    sanitized["claims"].append(
        {
            "claim": (
                "Adoption croissante de l’intelligence artificielle "
                "dans l’agriculture tunisienne"
            ),
            "category": "general",
            "status": "estimated",
            "confidence": "low",
            "evidence": [],
        }
    )

    repaired = agent._repair_public_report(
        result=sanitized,
        fallback=fallback,
        language="fr",
    )

    assert len(repaired["claims"]) == 1
    assert repaired["claims"][0]["claim_id"] == "known"


def test_document_host_page_cannot_be_an_adjacent_solution() -> None:
    decision = SourceRelevanceGate().evaluate_source(
        source={
            "title": (
                "Agriculture moderne en Tunisie : enjeux et solutions | PDF"
            ),
            "url": "https://fr.scribd.com/document/939152656/actualite",
            "snippet": (
                "Document général sur l’agriculture, la robotique "
                "et les capteurs en Tunisie."
            ),
            "extracted_text_preview": (
                "PDF de contexte sectoriel sans produit, service, "
                "fonctionnalités ni page fournisseur."
            ),
            "ai_source_type": "adjacent_solution",
            "ai_classifier_confidence": 0.95,
            "ai_same_sector": True,
            "ai_same_workflow": True,
        },
        project_context=_greenwatch_context(),
    )

    assert decision["source_type"] != "adjacent_solution"
    assert decision["canonical_category"] != "adjacent_solution"
    assert "adjacent_solution" not in decision["evidence_categories"]


def test_cautious_market_signals_survive_public_sanitization() -> None:
    signal = (
        "Signal à valider : l’inspection agricole combine "
        "automatisation, vision artificielle et capteurs connectés."
    )
    sanitized = EvidenceLedger().sanitize_public_claims(
        {
            "market_study": {"market_trends": [signal]},
            "competitive_analysis": {"sources": []},
            "output_language": "fr",
        }
    )

    assert sanitized["market_study"]["market_trends"] == [signal]
    assert sanitized["market_study"]["trends"] == [signal]