from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.agents.bmc_agent import BMCAgent
from app.agents.debate_room_graph import DebateRoomGraph
from app.agents.financial_estimation_agent import FinancialEstimationAgent
from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.agents.swot_agent import SWOTAgent
from app.services.project_intelligence_layer import project_intelligence_layer
from app.services.source_relevance_gate import source_relevance_gate


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
FRONTEND_CONTRACT_SKIP_REASON = (
    "Frontend source is not mounted in the backend container; "
    "validate.ps1 enforces the same contract on the host before lint/build."
)


TAXI_DESCRIPTION = (
    "une application qui permet aux clients de réserver un taxi selon leur région "
    "et leur destination et qui aide à trouver un taxi disponible"
)

NAWBA_DESCRIPTION = """Nawba Tunisia is a simple workforce management platform for small Tunisian
factories, workshops, restaurants and retail businesses that organize employees
in rotating shifts. Many small companies still prepare weekly schedules using
paper, Excel sheets or WhatsApp groups. The idea is to give managers one simple
place to create weekly shifts, record attendance, approve leave requests and
notify employees when a schedule changes. The first version would focus only on
shift planning, attendance, leave requests and a monthly export for payroll
preparation. The main operational user would be the supervisor or HR assistant
responsible for schedules. The economic buyer would probably be the company
owner or HR manager. The business model could be a monthly subscription based
on the number of employees."""


def _intelligence(title: str, description: str, industry: str, language: str = "fr"):
    return project_intelligence_layer.build(
        title=title,
        description=description,
        industry=industry,
        target_region="Tunisie",
        output_language=language,
    )


def _state(title: str, description: str, industry: str, intelligence: dict, language: str = "fr"):
    context = project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )
    return {
        "title": title,
        "description": description,
        "industry": industry,
        "region": "Tunisie",
        "output_language": language,
        "project_context": context,
        "structured_project_context": intelligence["structured_project_context"],
        "analysis_data": {
            "project_intelligence": intelligence,
            "structured_project_context": intelligence["structured_project_context"],
        },
    }


def test_taxi_idea_resolves_marketplace_without_inventing_actors_or_workflows():
    intelligence = _intelligence(
        "TaxiSmart",
        TAXI_DESCRIPTION,
        "transport",
    )
    structured = intelligence[
        "structured_project_context"
    ]

    assert (
        structured["project_archetype"]
        == "two_sided_marketplace"
    )
    assert structured["vertical"] == "mobility_taxi"

    # ProjectIntelligenceLayer receives no canonical actor/workflow
    # packet in this helper. It must not invent those fields.
    assert structured["target_users"] == []
    assert structured["priority_workflows"] == []

    actors = structured["actors"]
    assert actors["demand_side"] == ""
    assert actors["supply_side"] == ""
    assert actors["operator_or_partner"] == ""
    assert actors["payer"] == ""

    # No revenue model was explicitly supplied by the user.
    # PIL must therefore preserve an unknown business model rather
    # than inventing a marketplace commission.
    assert structured["business_model"] == ""

def test_taxi_query_plan_is_ride_hailing_specific_and_not_logistics_tms():
    planner = _intelligence("TaxiSmart", TAXI_DESCRIPTION, "transport")["query_planner"]
    joined = " | ".join(planner["queries"]).lower()

    assert "application réservation taxi tunisie" in joined
    assert "ride hailing" in joined
    assert "transport management software" not in joined
    assert "tms software" not in joined
    assert "region destination platform" not in joined


def test_taxi_personas_bmc_finance_and_swot_use_marketplace_language():
    intelligence = _intelligence(
        "TaxiSmart",
        TAXI_DESCRIPTION,
        "transport",
    )
    state = _state(
        "TaxiSmart",
        TAXI_DESCRIPTION,
        "transport",
        intelligence,
    )

    structured = intelligence[
        "structured_project_context"
    ]
    assert structured["target_users"] == []

    personas = asyncio.run(
        PersonaBuilderAgent().run(state)
    )

    names = [
        item["name"]
        for item in personas["personas"]
    ]

    assert len(names) == 3
    assert all(
        str(name).strip()
        for name in names
    )

    # Without canonical actor input the agent must not recreate
    # the old domain-specific taxi fallback.
    legacy_actor_names = {
        "Passager cherchant un taxi",
        "Chauffeur de taxi",
        "Exploitant de flotte ou op\u00e9rateur de plateforme",
    }
    assert not legacy_actor_names.intersection(
        set(names)
    )

    persona_text = str(personas).lower()
    assert "target user" not in persona_text
    assert "persona 2" not in persona_text
    assert (
        "g\u00e9rer destination resolu trouver"
        not in persona_text
    )
    assert "double saisie" not in persona_text

    bmc = asyncio.run(
        BMCAgent().run(state)
    )
    finance = asyncio.run(
        FinancialEstimationAgent().run(state)
    )
    swot = asyncio.run(
        SWOTAgent().run(state)
    )

    assert bmc["format"] == (
        "bmc_v6_archetype_aware"
    )
    assert "marketplace" in bmc["summary"].lower()
    assert any(
        "commission" in item.lower()
        for item in bmc["revenue_streams"]
    )

    assert finance["format"] == (
        "financial_estimation_v6_archetype_aware"
    )
    assert any(
        "transaction" in item.lower()
        for item in finance["recommended_kpis"]
    )
    assert (
        "abonnement mensuel pour les organisations actives"
        not in str(finance).lower()
    )

    assert swot["format"] == (
        "swot_v6_archetype_aware"
    )
    assert "liquidit\u00e9" in str(swot).lower()
    assert "tableurs" not in str(swot).lower()

def test_taxi_debate_has_five_adaptive_rounds_and_four_questions_each():
    intelligence = _intelligence("TaxiSmart", TAXI_DESCRIPTION, "transport")
    context = project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )
    analysis = {
        "project_intelligence": intelligence,
        "structured_project_context": intelligence["structured_project_context"],
        "startup_score": {
            "potential_score": 7.0,
            "evidence_confidence_score": 3.0,
            "execution_readiness_score": 6.0,
        },
        "fact_check_report": {"claims": [], "recommended_next_checks": []},
        "competitive_analysis": {},
    }

    room = asyncio.run(
        DebateRoomGraph().run(
            project_id=100,
            title="TaxiSmart",
            description=TAXI_DESCRIPTION,
            industry="transport",
            region="Tunisie",
            output_language="fr",
            project_context=context,
            analysis_data=analysis,
            max_rounds=5,
        )
    )["debate_room"]

    assert len(room["rounds"]) == 5
    assert all(len(item["committee_questions"]) == 4 for item in room["rounds"])
    assert room["rounds"][4]["topic"] == "Décision du comité d’investissement"
    joined = str(room).lower()
    assert "gérer destination resolu trouver" not in joined
    assert "double saisie" not in joined
    assert "économie unitaire" in joined


def test_mobility_source_gate_keeps_ride_hailing_and_rejects_logistics_tms():
    intelligence = _intelligence("TaxiSmart", TAXI_DESCRIPTION, "transport")
    context = project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )

    ride_hailing = source_relevance_gate.evaluate_source(
        source={
            "title": "Taxi booking and ride-hailing app for passengers and drivers",
            "url": "https://taxifast.tn/taxi-booking",
            "snippet": "Passengers book a taxi, drivers accept ride requests and complete trips.",
            "extracted_text_preview": "Taxi booking app with pickup, destination, driver matching, trip status, cancellation and payment. Product features, download app, driver signup.",
            "text_extracted": True,
        },
        project_context=context,
    )
    logistics = source_relevance_gate.evaluate_source(
        source={
            "title": "Transportation Management System for freight logistics",
            "url": "https://example.org/logistics-tms",
            "snippet": "Freight shipping, warehouse, cargo and fleet logistics software.",
            "extracted_text_preview": "TMS for maritime freight, warehouse operations, shipping and cargo management.",
            "text_extracted": True,
        },
        project_context=context,
    )

    assert ride_hailing["source_type"] in {"competitor", "adjacent_solution"}
    assert ride_hailing["public_display"] is True
    assert ride_hailing["rejected"] is False
    assert logistics["source_type"] == "irrelevant"
    assert logistics["rejected"] is True


def test_simple_internship_idea_resolves_marketplace_without_inventing_actors():
    intelligence = _intelligence(
        "StageFacile Tunisie",
        (
            "Je veux cr\u00e9er une application pour aider les \u00e9tudiants "
            "\u00e0 trouver des stages. Les entreprises peuvent publier "
            "leurs offres et les \u00e9tudiants peuvent envoyer leur CV."
        ),
        "\u00e9ducation et recrutement",
    )

    structured = intelligence[
        "structured_project_context"
    ]

    assert (
        structured["project_archetype"]
        == "two_sided_marketplace"
    )
    assert structured["vertical"] == "internship_jobs"

    # This helper intentionally bypasses canonical context extraction.
    # PIL therefore classifies but does not invent actors/workflows.
    assert structured["target_users"] == []
    assert structured["priority_workflows"] == []

    assert any(
        "plateforme stages \u00e9tudiants tunisie"
        in item.lower()
        for item in intelligence[
            "query_planner"
        ]["queries"]
    )

def test_hardware_idea_uses_field_operation_lens():
    intelligence = _intelligence(
        "AgroBot",
        "Un robot avec caméra et capteurs inspecte les plantes dans une petite serre et signale les plantes malades.",
        "robotique agricole",
    )
    structured = intelligence["structured_project_context"]
    state = _state("AgroBot", "robot serre caméra capteurs", "robotique agricole", intelligence)

    assert structured["project_archetype"] == "hardware_iot"
    personas = asyncio.run(PersonaBuilderAgent().run(state))
    finance = asyncio.run(FinancialEstimationAgent().run(state))
    assert any("terrain" in item["role"].lower() for item in personas["personas"])
    assert any("composant" in item.lower() for item in finance["initial_costs"])
    assert "abonnement mensuel pour les organisations actives" not in str(finance).lower()


def test_nawba_b2b_regression_is_preserved():
    intelligence = _intelligence(
        "Nawba Tunisia",
        NAWBA_DESCRIPTION,
        "Human Resources / Workforce Scheduling / SME SaaS",
        "en",
    )
    structured = intelligence["structured_project_context"]
    state = _state(
        "Nawba Tunisia",
        NAWBA_DESCRIPTION,
        "Human Resources / Workforce Scheduling / SME SaaS",
        intelligence,
        "en",
    )

    assert structured["project_archetype"] == "b2b_workflow_saas"
    personas = asyncio.run(PersonaBuilderAgent().run(state))
    assert [item["name"] for item in personas["personas"]] == [
        "Shift supervisor or HR assistant",
        "SME owner or HR manager",
        "Employee or team lead",
    ]


@pytest.mark.skipif(
    not FRONTEND_ROOT.is_dir(),
    reason=FRONTEND_CONTRACT_SKIP_REASON,
)
def test_frontend_sync_contract_reconciles_initial_focus_and_active_queue():
    client = (
        FRONTEND_ROOT
        / "app"
        / "projects"
        / "[id]"
        / "_components"
        / "ProjectDetailClient.tsx"
    ).read_text(encoding="utf-8")

    assert '["queued", "pending", "running"]' in client
    assert "await fetchProject();\n      await fetchAnalysis();" in client
    assert 'window.addEventListener("focus", reconcile)' in client
    assert 'document.addEventListener("visibilitychange", onVisibilityChange)' in client
    assert 'window.addEventListener("online", reconcile)' in client
    assert 'headers: { "Cache-Control": "no-cache" }' in client
    assert "analysisRequestInFlight.current" in client
    assert "activeAnalysisRunId" in client


def test_ambiguous_generic_idea_uses_neutral_lens_not_b2b_records_template():
    description = "Je veux créer une application simple pour aider les gens à organiser une activité locale plus facilement."
    intelligence = _intelligence("LocalEasy", description, "application numérique")
    structured = intelligence["structured_project_context"]
    state = _state("LocalEasy", description, "application numérique", intelligence)

    assert structured["project_archetype"] == "generic_digital_product"
    personas = asyncio.run(PersonaBuilderAgent().run(state))
    bmc = asyncio.run(BMCAgent().run(state))
    finance = asyncio.run(FinancialEstimationAgent().run(state))
    swot = asyncio.run(SWOTAgent().run(state))

    combined = " ".join(map(str, [personas, bmc, finance, swot])).lower()
    assert "dossiers gérés" not in combined
    assert "tableurs" not in combined
    assert "double saisie" not in combined
    assert "abonnement mensuel pour les organisations actives" not in combined
    assert bmc["format"] == "bmc_v6_archetype_aware"
    assert finance["format"] == "financial_estimation_v6_archetype_aware"
    assert swot["format"] == "swot_v6_archetype_aware"


def test_competitive_public_filter_accepts_verified_taxi_product():
    from app.agents.competitive_analysis_agent import CompetitiveAnalysisAgent

    intelligence = _intelligence("TaxiSmart", TAXI_DESCRIPTION, "transport")
    context = project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )
    source = source_relevance_gate.evaluate_source(
        source={
            "title": "Taxi booking app for passengers and drivers",
            "url": "https://taxifast.tn/taxi-booking",
            "snippet": "Passengers book taxis and drivers accept ride requests in Tunisia.",
            "extracted_text_preview": "Product features include pickup, destination, driver signup, trip status, cancellation and payment.",
            "text_extracted": True,
        },
        project_context=context,
    )

    rejection = CompetitiveAnalysisAgent()._public_source_rejection_reason(
        source=source
        | {
            "title": "Taxi booking app for passengers and drivers",
            "url": "https://taxifast.tn/taxi-booking",
        },
        title="TaxiSmart",
        structured_project_context=intelligence["structured_project_context"],
        project_context=context,
    )

    assert source["public_display"] is True
    assert source["source_type"] == "competitor"
    assert rejection == ""


@pytest.mark.skipif(
    not FRONTEND_ROOT.is_dir(),
    reason=FRONTEND_CONTRACT_SKIP_REASON,
)
def test_frontend_source_journey_distinguishes_completion_from_evidence():
    journey = (
        FRONTEND_ROOT
        / "app"
        / "projects"
        / "[id]"
        / "_sections"
        / "AnalysisJourneySection.tsx"
    ).read_text(encoding="utf-8")

    assert "retainedSourceCount" in journey
    assert "Recherche de sources terminée" in journey
    assert "Terminée — preuves insuffisantes" in journey
    assert "No compatible external evidence was retained" in journey


@pytest.mark.parametrize(
    ("description", "industry", "expected"),
    [
        ("Une plateforme met en relation des clients et des prestataires avec commission.", "services", "two_sided_marketplace"),
        ("Une application permet de réserver un rendez-vous et payer en ligne.", "services", "consumer_transactional_app"),
        ("Un SaaS dashboard pour managers gère les dossiers, le reporting et les exports.", "business software", "b2b_workflow_saas"),
        ("Une boutique en ligne avec catalogue, panier, paiement et livraison.", "commerce", "ecommerce"),
        ("Un robot IoT avec caméra, capteur et moteur inspecte le terrain.", "robotique", "hardware_iot"),
        ("Un outil d’intelligence artificielle analyse et prédit les ventes.", "analytics", "analytics_ai_tool"),
        ("Un réseau social et forum pour une communauté de créateurs de contenu.", "media", "content_community"),
        ("Une application médicale permet aux patients de réserver avec un médecin.", "santé", "regulated_service"),
        ("Une application pour aider les gens dans une activité locale.", "digital", "generic_digital_product"),
    ],
)
def test_archetype_matrix_covers_major_project_families(description, industry, expected):
    intelligence = _intelligence("Archetype test", description, industry)
    assert intelligence["structured_project_context"]["project_archetype"] == expected
