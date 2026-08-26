from __future__ import annotations

import asyncio

from app.agents.debate_room_graph import DebateRoomGraph
from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.llm.provider import LLMProvider
from app.services.project_intelligence_layer import project_intelligence_layer
from app.services.public_analysis_sanitizer import sanitize_analysis_data_for_public
from app.services.source_relevance_gate import source_relevance_gate

from app.services.project_context_extractor import (
    project_context_extractor,
)


DESCRIPTION = """Nawba Tunisia is a simple workforce management platform for small Tunisian
factories, workshops, restaurants and retail businesses that organize employees
in rotating shifts. Many small companies still prepare weekly schedules using
paper, Excel sheets or WhatsApp groups. The idea is to give managers one simple
place to create weekly shifts, record attendance, approve leave requests and
notify employees when a schedule changes. The first version would focus only on
shift planning, attendance, leave requests and a monthly export for payroll
preparation. The main operational user would be the supervisor or HR assistant
responsible for schedules. The economic buyer would probably be the company
owner or HR manager, but this still needs to be validated. The business model
could be a monthly subscription based on the number of employees."""


def _intelligence():
    return project_intelligence_layer.build(
        title="Nawba Tunisia",
        description=DESCRIPTION,
        industry="Human Resources / Workforce Scheduling / SME SaaS",
        target_region="Tunisie",
        output_language="en",
    )


def _context():
    intelligence = _intelligence()
    return project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )


def test_nawba_context_extracts_roles_and_real_workflows():
    # PIL classifies and plans searches, but it is not the
    # canonical actor/workflow authority.
    intelligence = _intelligence()

    structured = intelligence[
        "structured_project_context"
    ]

    assert (
        structured["project_archetype"]
        == "b2b_workflow_saas"
    )

    assert (
        structured["priority_workflows"]
        == []
    )

    packet = project_context_extractor.extract(
        title="Nawba Tunisia",
        description=DESCRIPTION,
        industry=(
            "Human Resources / "
            "Workforce Scheduling / SME SaaS"
        ),
        target_region="Tunisie",
        output_language="en",
    )

    canonical = packet.model_dump(
        mode="json"
    )

    actors = canonical["actors"]

    supervisor = next(
        actor
        for actor in actors
        if "supervisor"
        in actor["name"].lower()
    )

    hr_assistant = next(
        actor
        for actor in actors
        if "hr assistant"
        in actor["name"].lower()
    )

    # The explicit supervisor-or-HR-assistant relation declares
    # alternative operational identities. Preserve both identities
    # instead of requiring one merged actor label.
    for operational_user in (
        supervisor,
        hr_assistant,
    ):
        assert (
            operational_user["role"]
            == "user"
        )

        assert (
            operational_user["is_explicit"]
            is True
        )

    payer = next(
        actor
        for actor in actors
        if "company owner"
        in actor["name"].lower()
    )

    assert payer["role"] == "payer"
    assert payer["is_explicit"] is True

    assert any(
        "company owner"
        in name.lower()
        for name
        in canonical["payer_actor_names"]
    )

    workflows = canonical[
        "priority_workflows"
    ]

    assert any(
        workflow["action"] == "create"
        and "weekly shift"
        in workflow["object"].lower()
        for workflow in workflows
    )

    assert any(
        workflow["action"] == "record"
        and "attendance"
        in workflow["object"].lower()
        for workflow in workflows
    )

    assert any(
        workflow["action"] == "approve"
        and "leave request"
        in workflow["object"].lower()
        for workflow in workflows
    )

    assert any(
        workflow["action"] == "notify"
        and "schedule change"
        in workflow["object"].lower()
        for workflow in workflows
    )

    assert all(
        workflow["is_explicit"] is True
        for workflow in workflows
    )

    joined_workflows = " | ".join(
        workflow["name"]
        for workflow in workflows
    ).lower()

    assert (
        "excel sheets"
        not in joined_workflows
    )

    assert (
        "whatsapp groups"
        not in joined_workflows
    )

    assert (
        "first version"
        not in joined_workflows
    )

    # MVP scope remains distinct from operational workflows.
    assert any(
        "payroll"
        in item.lower()
        for item
        in canonical["mvp_scope"]
    )

    assert any(
        "monthly subscription"
        in item.lower()
        for item
        in canonical[
            "business_model_hypotheses"
        ]
    )

    # Search planning remains a PIL responsibility.
    selected_queries = intelligence[
        "query_planner"
    ]["queries"]

    assert any(
        "workforce scheduling"
        in query.lower()
        for query in selected_queries
    )

    assert not any(
        query.lower().startswith(
            "human resources management"
        )
        for query in selected_queries
    )



def test_nawba_personas_are_professional_roles():
    intelligence = _intelligence()
    result = asyncio.run(PersonaBuilderAgent().run({
        "title": "Nawba Tunisia",
        "description": DESCRIPTION,
        "industry": "Human Resources / Workforce Scheduling / SME SaaS",
        "region": "Tunisie",
        "output_language": "en",
        "project_context": _context(),
        "analysis_data": {"project_intelligence": intelligence},
    }))
    names = [item["name"] for item in result["personas"]]
    assert names == [
        "Shift supervisor or HR assistant",
        "SME owner or HR manager",
        "Employee or team lead",
    ]
    assert all("many small companies still prepare" not in item["name"].lower() for item in result["personas"])
    assert all("excel sheets or whatsapp groups" not in item["segment"].lower() for item in result["personas"])
    assert all("manage the first version" not in item["use_case"].lower() for item in result["personas"])
    assert all("complete create" not in " ".join(item["goals"]).lower() for item in result["personas"])


def test_public_sanitizer_preserves_committee_roles_and_round_five():
    intelligence = _intelligence()
    analysis = {
        "output_language": "en",
        "project_intelligence": intelligence,
        "structured_project_context": intelligence["structured_project_context"],
        "startup_score": {
            "potential_score": 7.0,
            "evidence_confidence_score": 3.0,
            "execution_readiness_score": 6.5,
        },
        "fact_check_report": {"claims": [], "recommended_next_checks": []},
        "competitive_analysis": {},
        "financial_estimation": {},
    }
    room = asyncio.run(DebateRoomGraph().run(
        project_id=9,
        title="Nawba Tunisia",
        description=DESCRIPTION,
        industry="Human Resources / Workforce Scheduling / SME SaaS",
        region="Tunisie",
        output_language="en",
        project_context=_context(),
        analysis_data=analysis,
        max_rounds=5,
    ))["debate_room"]
    analysis["debate_room"] = room
    public = sanitize_analysis_data_for_public(analysis, _context())
    committee_ids = [item["id"] for item in public["debate_room"]["committee"]]
    assert "product_technology_architect" in committee_ids
    assert "risk_execution_officer" in committee_ids
    assert "evidence_auditor" in committee_ids
    assert "red_team_challenger" in committee_ids
    assert public["debate_room"]["rounds"][4]["topic"] == "Investment committee decision"
    for round_data in public["debate_room"]["rounds"]:
        assert round_data["main_question"]
        assert all(item["question"] for item in round_data["committee_questions"])


def test_local_adjacent_workforce_product_can_be_public():
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Payroll and HR Management Software in Tunisia - Talenteo",
            "url": "https://talenteo.com/logiciel-sirh-gestion-ressources-humaines-paie-temps-conges-absences-tunisie/",
            "snippet": "Tunisian HR software for payroll, time, attendance, leave and absences. Features and platform.",
            "extracted_text_preview": "Manage employee attendance, leave requests, working time and payroll preparation in Tunisia. Product features and login.",
            "text_extracted": True,
        },
        project_context=_context(),
    )
    assert decision["region_match"] == "local"
    assert decision["source_type"] in {"adjacent_solution", "competitor"}
    assert decision["public_display"] is True


def test_obsolete_gemini_fallback_is_blocked():
    assert "gemini-2.5-flash-lite" in LLMProvider.BLOCKED_MODEL_NAMES


def test_ai_irrelevant_cannot_override_strong_workforce_product_evidence():
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Employee Scheduling Software | WorkForce Software",
            "url": "https://workforcesoftware.com/workforce-suite/scheduling",
            "snippet": (
                "Employee scheduling software for shift planning, rotating shifts, "
                "schedule changes, managers and workforce."
            ),
            "extracted_text_preview": (
                "Our workforce scheduling software helps managers create employee "
                "schedules, manage shift changes, attendance and leave. Features, "
                "customers, book a demo, login."
            ),
            "ai_source_type": "irrelevant",
            "ai_classifier_confidence": 0.95,
            "ai_same_workflow": True,
            "ai_same_sector": True,
            "ai_product_page": True,
        },
        project_context=_context(),
    )
    assert decision["source_type"] == "adjacent_solution"
    assert decision["public_display"] is True
    assert decision["rejected"] is False
    assert "solution_benchmark" in decision["evidence_categories"]


def test_competitive_public_filter_initializes_source_type_before_thresholds():
    from app.agents.competitive_analysis_agent import CompetitiveAnalysisAgent

    agent = CompetitiveAnalysisAgent()
    rejection = agent._public_source_rejection_reason(
        source={
            "title": "Employee Scheduling Software | WorkForce Software",
            "url": "https://workforcesoftware.com/workforce-suite/scheduling",
            "source_type": "adjacent_solution",
            "region_match": "international",
            "source_relevance_score": 0.79,
            "public_display": True,
            "internal_only": False,
            "rejected": False,
            "matched_strong_terms": [
                "workforce scheduling",
                "shift planning",
                "schedule changes",
            ],
            "same_or_close_use_case": True,
            "same_or_close_solution_category": True,
        },
        title="Nawba Tunisia",
        structured_project_context=_intelligence()["structured_project_context"],
        project_context=_context(),
    )
    assert rejection == ""
