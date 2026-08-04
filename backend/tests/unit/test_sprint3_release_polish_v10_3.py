from __future__ import annotations

from copy import deepcopy

from app.agents.fact_checker_agent import FactCheckerAgent
from app.services.evidence_ledger import EvidenceLedger


def _source(
    *,
    title: str,
    url: str,
    snippet: str,
    source_type: str = "technology_benchmark",
    source_role: str = "technology_provider",
    canonical_category: str = "technology_benchmark",
    region_match: str = "international",
) -> dict:
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source_type": source_type,
        "source_role": source_role,
        "canonical_category": canonical_category,
        "region_match": region_match,
        "public_display": True,
        "evidence_categories": [
            "technology_benchmark",
            "solution_benchmark",
        ],
    }


def _claim_for_suggestion(suggestion: str, sources: list[dict]) -> dict:
    ledger = EvidenceLedger().build(
        {
            "improvement_suggestions": [suggestion],
            "competitive_analysis": {"sources": sources},
        }
    )
    return next(
        claim
        for claim in ledger["claims"]
        if claim["path"] == "improvement_suggestions[0]"
    )


def test_unrelated_technology_benchmark_does_not_support_solar_recharge() -> None:
    claim = _claim_for_suggestion(
        (
            "Intégrer un système de recharge automatique par induction "
            "ou via des stations solaires installées dans la serre."
        ),
        [
            _source(
                title="Agriculture intelligente connectée à l’IoT avec ESP32",
                url="https://robotique.site/iot",
                snippet="Capteurs IoT pour mesurer température et humidité.",
            )
        ],
    )

    assert claim["status"] == "estimated"
    assert claim["confidence"] == "low"
    assert claim["source_ids"] == []


def test_unrelated_technology_benchmark_does_not_support_crda_partnership() -> None:
    claim = _claim_for_suggestion(
        (
            "Développer des partenariats avec les Commissariats Régionaux "
            "au Développement Agricole (CRDA)."
        ),
        [
            _source(
                title="Robot de surveillance agricole",
                url="https://example.com/robot",
                snippet="Vision artificielle et capteurs embarqués.",
            )
        ],
    )

    assert claim["status"] == "estimated"
    assert claim["source_ids"] == []


def test_unrelated_technology_benchmark_does_not_support_spot_spraying() -> None:
    claim = _claim_for_suggestion(
        (
            "Ajouter une fonctionnalité de pulvérisation ciblée "
            "(spot spraying) pour traiter les plantes malades."
        ),
        [
            _source(
                title="Robot de surveillance agricole",
                url="https://example.com/inspection",
                snippet="Inspection des cultures avec caméra et alertes.",
            )
        ],
    )

    assert claim["source_ids"] == []


def test_matching_spot_spraying_benchmark_is_retained() -> None:
    claim = _claim_for_suggestion(
        (
            "Ajouter une fonctionnalité de pulvérisation ciblée "
            "(spot spraying) pour traiter les plantes malades."
        ),
        [
            _source(
                title="Robot agricole avec pulvérisation ciblée",
                url="https://example.com/spot-spraying",
                snippet=(
                    "Spot spraying et traitement pesticide ciblé "
                    "des cultures détectées comme malades."
                ),
            )
        ],
    )

    assert claim["status"] == "estimated"
    assert claim["confidence"] == "medium"
    assert len(claim["source_ids"]) == 1


def test_market_trend_requires_semantic_compatibility() -> None:
    ledger = EvidenceLedger().build(
        {
            "market_study": {
                "market_trends": [
                    "Utilisation de drones pour la surveillance des champs",
                    "Modernisation agricole face au stress hydrique",
                ]
            },
            "competitive_analysis": {
                "sources": [
                    {
                        "title": "DronIA pour la surveillance agricole en Tunisie",
                        "url": "https://example.com/dronia",
                        "snippet": (
                            "Drones et vision artificielle pour surveiller "
                            "les champs agricoles."
                        ),
                        "source_type": "market_article",
                        "source_role": "market_evidence",
                        "canonical_category": "market_evidence",
                        "region_match": "local",
                        "public_display": True,
                        "evidence_categories": [
                            "market_demand_claim",
                            "local_market_signal",
                        ],
                    }
                ]
            },
        }
    )

    claims = {
        claim["path"]: claim
        for claim in ledger["claims"]
        if claim["path"].startswith("market_study.market_trends[")
    }

    assert claims["market_study.market_trends[0]"]["status"] == "sourced"
    assert claims["market_study.market_trends[0]"]["source_ids"]
    assert claims["market_study.market_trends[1]"]["status"] == "estimated"
    assert claims["market_study.market_trends[1]"]["source_ids"] == []


def test_compact_evidence_preserves_human_readable_title_aliases() -> None:
    agent = FactCheckerAgent()
    compact = agent._compact_evidence(
        {
            "title": (
                "Agriculture intelligente connectée à l’IoT "
                "et contrôlée par ESP32"
            ),
            "url": "https://robotique.site/iot",
            "source_type": "technology_benchmark",
            "region_match": "international",
            "evidence_quality": "medium",
        }
    )

    assert compact["title"].startswith("Agriculture intelligente")
    assert compact["source_title"] == compact["title"]
    assert compact["name"] == compact["title"]


def test_public_report_repair_restores_fallback_evidence_title() -> None:
    agent = FactCheckerAgent()
    full_title = (
        "Agriculture intelligente connectée à l’IoT "
        "et contrôlée par ESP32"
    )
    fallback = {
        "claims": [
            {
                "claim_id": "solution_feasibility",
                "path": "proposed_solution",
                "claim": "La solution peut être testée par un MVP réduit.",
                "category": "solution",
                "status": "estimated",
                "confidence": "medium",
                "evidence": [
                    {
                        "title": full_title,
                        "url": "https://robotique.site/iot",
                        "source_type": "technology_benchmark",
                        "region_match": "international",
                        "evidence_quality": "medium",
                    }
                ],
            }
        ]
    }
    sanitized = deepcopy(fallback)
    sanitized["claims"][0]["evidence"] = [
        {
            "title": "robotique.site",
            "url": "https://robotique.site/iot",
            "source_type": "technology_benchmark",
            "region_match": "international",
        }
    ]

    repaired = agent._repair_public_report(
        result=sanitized,
        fallback=fallback,
        language="fr",
    )

    evidence = repaired["claims"][0]["evidence"][0]
    assert evidence["title"] == full_title
    assert evidence["source_title"] == full_title


def test_french_neutral_messages_are_valid_utf8() -> None:
    text = EvidenceLedger._neutral_text("fr", "market_size")
    assert "marché" in text
    assert "vérifiée" in text
    assert "Ã" not in text
    assert "â€" not in text