from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.agents.startup_score_agent import StartupScoreAgent
from app.services.canonical_source_ledger import canonical_source_ledger
from app.services.project_archetype_resolver import project_archetype_resolver
from app.services.source_relevance_gate import source_relevance_gate
from app.services.source_role_resolver import source_role_resolver


TAXI_DESCRIPTION = (
    "Je veux créer une application qui permet aux clients de réserver un taxi "
    "selon leur position et leur destination. Les chauffeurs disponibles peuvent "
    "accepter la course et venir chercher le client."
)


def _taxi_archetype():
    return project_archetype_resolver.resolve(
        title="TaxiSmart",
        description=TAXI_DESCRIPTION,
        industry="Transport",
        target_region="Tunisie",
        output_language="fr",
    )


def _taxi_project_context():
    archetype = _taxi_archetype()
    structured = {
        **archetype,
        "project_name": "TaxiSmart",
        "sector": "Transport",
        "target_region": "Tunisie",
        "problem": "Difficulté à trouver un taxi disponible rapidement.",
        "solution": "Application de réservation et de mise en relation passager-chauffeur.",
        "domain_concepts": ["taxi booking", "ride hailing", "taxi", "mobility"],
        "target_users": archetype["target_users"],
        "priority_workflows": archetype["priority_workflows"],
    }
    return {
        "project_name": "TaxiSmart",
        "description": TAXI_DESCRIPTION,
        "sector": "Transport",
        "target_region": "Tunisie",
        "archetype_context": archetype,
        "structured_project_context": structured,
        "strong_keywords": ["taxi booking", "ride hailing", "taxi", "passenger", "driver"],
        "must_match_terms": ["taxi booking", "ride hailing"],
        "domain_concepts": ["taxi booking", "ride hailing", "taxi", "mobility"],
        "target_users": archetype["target_users"],
        "use_case_terms": archetype["priority_workflows"],
        "solution_terms": ["taxi booking app", "ride hailing platform", "reservation taxi"],
        "forbidden_terms": ["super app", "pharmacy", "hospital"],
    }


def test_taxi_archetype_exposes_queries_without_inventing_actor_roles():
    archetype = _taxi_archetype()

    assert (
        archetype["project_archetype"]
        == "two_sided_marketplace"
    )
    assert archetype["vertical"] == "mobility_taxi"

    assert (
        "application r\u00e9servation taxi Tunisie"
        in archetype["search_queries"]["local_fr"]
    )

    # Resolver authority is classification only.
    assert archetype["target_users"] == []
    assert archetype["priority_workflows"] == []

    actors = archetype["actors"]
    assert actors["demand_side"] == ""
    assert actors["supply_side"] == ""
    assert actors["operator_or_partner"] == ""
    assert actors["payer"] == ""
    assert actors["explicit_targets"] == []

    assert (
        archetype["authority"][
            "resolves_actor_roles"
        ]
        is False
    )
    assert (
        archetype["authority"][
            "invents_workflows"
        ]
        is False
    )

def test_local_market_search_uses_archetype_queries_not_generic_transport(monkeypatch):
    gateway_module = types.ModuleType("app.web_search.search_gateway")
    gateway_module.search_gateway = object()
    monkeypatch.setitem(sys.modules, "app.web_search.search_gateway", gateway_module)
    sys.modules.pop("app.web_search.local_market_search", None)
    local_module = importlib.import_module("app.web_search.local_market_search")
    service = local_module.LocalMarketSearchService()
    queries = service.build_queries(
        sector="Transport",
        region="Tunisie",
        description=TAXI_DESCRIPTION,
        project_context={
            "project_name": "TaxiSmart",
            "description": TAXI_DESCRIPTION,
            "sector": "Transport",
            "target_region": "Tunisie",
            "output_language": "fr",
        },
    )
    normalized = " | ".join(queries).lower()
    assert "réservation taxi" in normalized or "taxi booking" in normalized
    assert "ride hailing" in normalized or "mise en relation taxi chauffeur" in normalized
    assert "transport logiciel tunisie" not in normalized
    assert "transport software tunisia" not in normalized


def test_source_roles_separate_local_competitor_and_technology_provider():
    context = _taxi_project_context()
    common = {
        "source_type": "competitor",
        "is_product_page": True,
        "same_or_close_target_user": True,
        "same_or_close_use_case": True,
        "same_or_close_solution_category": True,
        "sector_mismatch": False,
    }
    technology = source_role_resolver.resolve(
        source={
            "title": "Ride Hailing Software & White Label Platform",
            "url": "https://yelowsoft.com/ride-hailing-software",
            "body": "White label ride hailing and taxi dispatch software for taxi companies.",
        },
        decision={**common, "region_match": "international"},
        project_context=context,
    )
    local = source_role_resolver.resolve(
        source={
            "title": "Ride with Yassir - Available in Tunisia",
            "url": "https://yassir.com/en/tunisia/ride-hailing",
            "body": "Book a ride in Tunisia with a passenger app and driver app.",
        },
        decision={**common, "region_match": "local"},
        project_context=context,
    )
    assert technology["source_role"] == "technology_provider"
    assert technology["legacy_source_type"] == "technology_benchmark"
    assert technology["technology_supplier"] is True
    assert local["source_role"] == "direct_competitor"
    assert local["legacy_source_type"] == "competitor"
    assert local["technology_supplier"] is False


def test_super_app_body_mention_does_not_reject_exact_local_ride_hailing_product():
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Ride with Yassir - Available in Tunisia",
            "url": "https://yassir.com/en/tunisia/ride-hailing",
            "snippet": (
                "Book a taxi by pickup area and destination in Tunisia. Ride hailing "
                "passenger app and driver app. Download app, available on mobile, get "
                "started and sign up. Yassir is a super app. Chauffeur accepts the ride."
            ),
            "body": (
                "Book a taxi by pickup area and destination in Tunisia. Ride hailing "
                "passenger app and driver app. Download app, available on mobile, get "
                "started and sign up. Yassir is a super app. Chauffeur accepts the ride. "
                "Features, pricing, customers, app and platform."
            ),
        },
        project_context=_taxi_project_context(),
    )
    assert decision["matched_forbidden_terms"] == []
    assert decision["rejected"] is False
    assert decision["public_display"] is True
    assert decision["source_role"] == "direct_competitor"
    assert decision["is_direct_competitor"] is True
    assert decision["region_match"] == "local"


def test_white_label_product_is_public_technology_provider_not_competitor():
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Ride Hailing Software & White Label Platform",
            "url": "https://yelowsoft.com/ride-hailing-software",
            "snippet": (
                "White label taxi booking and dispatch software for taxi businesses. "
                "Book a taxi by pickup area and destination. Passenger and driver apps, "
                "features, pricing, integrations and request demo."
            ),
            "body": (
                "White label taxi booking and dispatch software for taxi businesses. "
                "Start your ride hailing company. Passenger and driver apps, features, "
                "pricing, integrations, request demo, our software and our platform."
            ),
        },
        project_context=_taxi_project_context(),
    )
    assert decision["rejected"] is False
    assert decision["public_display"] is True
    assert decision["source_role"] == "technology_provider"
    assert decision["source_type"] == "technology_benchmark"
    assert decision["is_direct_competitor"] is False


def test_canonical_source_ledger_deduplicates_once_and_derives_all_counts():
    ledger = canonical_source_ledger.build(
        [
            {
                "title": "Yelowsoft",
                "url": "https://yelowsoft.com/ride-hailing-software",
                "source_role": "technology_provider",
                "source_relevance_score": 0.78,
            },
            {
                "title": "Yelowsoft duplicate",
                "url": "https://www.yelowsoft.com/ride-hailing-software/",
                "source_role": "technology_provider",
                "source_relevance_score": 0.95,
            },
            {
                "title": "Yassir Tunisia",
                "url": "https://yassir.com/en/tunisia/ride-hailing",
                "source_role": "direct_competitor",
                "source_relevance_score": 0.91,
            },
            {
                "title": "Ride Hailing Market Report",
                "url": "https://research.example.com/ride-hailing",
                "source_role": "market_evidence",
                "source_relevance_score": 0.74,
            },
        ]
    )
    assert ledger["sources_count"] == 3
    assert ledger["canonical_sources_count"] == 3
    assert ledger["counts"]["all"] == 3
    assert ledger["counts"]["local_direct_competitors"] == 1
    assert ledger["counts"]["technology_providers"] == 1
    assert ledger["counts"]["market_and_evidence"] == 1
    assert len(ledger["roles"]["technology_provider"]) == 1


def test_marketplace_personas_are_complete_without_invented_actor_roles():
    archetype = _taxi_archetype()

    assert archetype["target_users"] == []
    assert archetype["priority_workflows"] == []

    state = {
        "title": "TaxiSmart",
        "description": TAXI_DESCRIPTION,
        "industry": "Transport",
        "region": "Tunisie",
        "output_language": "fr",
        "project_context": {
            "archetype_context": archetype
        },
        "analysis_data": {
            "archetype_context": archetype
        },
    }

    agent = PersonaBuilderAgent()
    context = agent._context(state)
    result = agent._build(
        context,
        "fr",
    )

    assert (
        result["persona_schema_valid"]
        is True
    )
    assert (
        result["missing_fields_by_persona"]
        == []
    )
    assert len(result["personas"]) == 3

    names = [
        persona["name"]
        for persona in result["personas"]
    ]

    assert all(
        str(name).strip()
        for name in names
    )

    legacy_actor_names = {
        "Passager cherchant un taxi",
        "Chauffeur de taxi",
        "Exploitant de flotte ou op\u00e9rateur de plateforme",
    }

    assert not legacy_actor_names.intersection(
        set(names)
    )

    for persona in result["personas"]:
        assert not (
            persona["name"]
            .lower()
            .startswith("persona ")
        )
        assert persona["segment"]
        assert persona["interview_questions"]
        assert persona["current_alternatives"]
        assert persona["adoption_trigger"]

def test_marketplace_startup_actions_use_transaction_economics_not_saas_template():
    archetype = _taxi_archetype()
    state = {
        "title": "TaxiSmart",
        "description": TAXI_DESCRIPTION,
        "industry": "Transport",
        "region": "Tunisie",
        "output_language": "fr",
        "project_context": {"archetype_context": archetype},
        "analysis_data": {"archetype_context": archetype},
    }
    agent = StartupScoreAgent()
    context = agent._context(state)
    assert context["project_archetype"] == "two_sided_marketplace"
    actions = agent._recommendations(
        context=context,
        breakdown={"business_model_strength": 7.2},
        output_language="fr",
    ) + agent._next_actions(context=context, score=7.0, output_language="fr")
    joined = " ".join(actions).lower()
    assert "marge contributive" in joined
    assert "transaction" in joined
    assert "deux côtés" in joined
    assert "abonnement" not in joined
    assert "onboarding" not in joined


def test_frontend_contract_prefers_canonical_ledger_and_separates_technology():
    root = Path(__file__).resolve().parents[3]
    source_section = root / "frontend" / "app" / "projects" / "[id]" / "_sections" / "SourcesAndCompetitorsSection.tsx"
    types_file = root / "frontend" / "app" / "projects" / "[id]" / "_types" / "project-detail.types.ts"
    if not source_section.exists() or not types_file.exists():
        import pytest
        pytest.skip("Frontend is not mounted in the backend-only test image.")
    section_text = source_section.read_text(encoding="utf-8")
    types_text = types_file.read_text(encoding="utf-8")
    assert "canonical_source_ledger" in section_text
    assert "retainedCount" in section_text
    assert "technologyProviders" in section_text
    assert "Fournisseurs technologiques" in section_text
    assert "source_role?: string;" in types_text
    assert "canonical_source_ledger?: CanonicalSourceLedger;" in types_text
