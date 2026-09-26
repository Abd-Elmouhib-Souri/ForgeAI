"""
Sprint 4 output-language contracts.

Observed product RED (project 31 "TawlaPro", output_language = fr,
25 Sept 2026): every AI Product Owner story ("Create Restaurant Account",
"As a restaurant owner I want ...") and every AI Scrum Master rationale
came back in English, while the analysis, the deterministic fallback and
the Solution Architect were in French.

First Wrong Layer: prompt construction. ProjectManagementContextV1 already
carries ``language`` (from the project's output_language) but neither
agent prompt ever told the model which language to write in, and the only
story example was English.

Universal fix, no project/sector specifics:
  * one shared rule builder (app.llm.output_language) that localizes
    human-readable text ONLY -- JSON keys, enum values, candidate keys,
    canonical IDs, hashes and copied ALLOWED references stay verbatim
    (translating them would make the strict authorities reject the
    answer and silently fall back to the deterministic backlog);
  * the Product Owner story example follows the language;
  * the Scrum Master receives the language through its constructor so
    its canonical build_prompt/generate_advice signatures are unchanged
    (test_04 of the authority contract).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.agents.product_owner_agent import ProductOwnerAgent
from app.agents.scrum_master_agent import AIScrumMasterAgent
from tests.unit.test_product_owner_agent_universal_contract import make_context
from tests.unit.test_scrum_master_agent_runtime_contract import (
    make_backlog,
    make_graph,
    make_settings,
)

BACKEND = Path(__file__).resolve().parents[2]


def po_context(language: str):
    # Neutral, non-SoukPilot/non-TawlaPro fixture: the rule must not depend
    # on any project, sector or country.
    return make_context(
        project_id="lang-1",
        project_name="Atelier Partage",
        language=language,
        target_region="",
        industry="services",
        actor_name="Artisan",
        decision_maker_name="Gerant",
        workflow_name="Reserver un poste",
        action="reserve",
        object_name="poste de travail",
        result="poste reserve",
        mvp_scope="reservation de postes",
        exclusion="paiement en ligne",
    )


# L1 ------------------------------------------------------------------------

def test_shared_rule_localizes_text_but_never_identifiers():
    from app.llm.output_language import structured_output_language_rules

    rules = structured_output_language_rules("French", translatable_fields=["title", "rationale"])
    assert "OUTPUT LANGUAGE" in rules
    assert "French (fr)" in rules
    assert "title, rationale" in rules
    # Identifiers and enums are explicitly protected from translation.
    for protected in ("JSON keys", "enum values", "identifiers", "hashes", "ALLOWED"):
        assert protected in rules

    english = structured_output_language_rules("en", translatable_fields=["title"])
    assert "English (en)" in english


def test_unknown_language_follows_the_platform_default():
    from app.llm.output_language import structured_output_language_rules

    # normalize_output_language() is the single authority: unknown -> fr.
    assert "French (fr)" in structured_output_language_rules("", translatable_fields=["x"])
    assert "French (fr)" in structured_output_language_rules("klingon", translatable_fields=["x"])


# L2 ------------------------------------------------------------------------

def test_product_owner_prompt_carries_the_project_language():
    prompt = ProductOwnerAgent().build_prompt(po_context("fr"))
    assert "OUTPUT LANGUAGE" in prompt
    assert "French (fr)" in prompt
    # The story example must not pull the model back to English.
    assert "En tant que" in prompt
    assert "As a ... I want" not in prompt
    for field in ("story", "acceptance_criteria[].statement", "candidate_priority_rationale"):
        assert field in prompt


def test_product_owner_prompt_stays_english_for_english_projects():
    prompt = ProductOwnerAgent().build_prompt(po_context("en"))
    assert "English (en)" in prompt
    assert "As a ... I want ... so that ..." in prompt
    assert "En tant que" not in prompt


# L3 ------------------------------------------------------------------------

def test_scrum_master_prompt_carries_the_project_language():
    backlog, graph, settings = make_backlog(), make_graph(), make_settings()
    prompt = AIScrumMasterAgent(output_language="fr").build_prompt(backlog, graph, settings)
    assert "OUTPUT LANGUAGE" in prompt
    assert "French (fr)" in prompt
    assert "rationale" in prompt.split("OUTPUT LANGUAGE", 1)[1]


def test_scrum_master_without_language_keeps_the_legacy_prompt():
    backlog, graph, settings = make_backlog(), make_graph(), make_settings()
    prompt = AIScrumMasterAgent().build_prompt(backlog, graph, settings)
    assert "OUTPUT LANGUAGE" not in prompt


def test_scrum_master_canonical_signatures_are_unchanged():
    expected = ["self", "backlog", "dependency_graph", "planning_settings"]
    assert list(inspect.signature(AIScrumMasterAgent.build_prompt).parameters) == expected
    assert list(inspect.signature(AIScrumMasterAgent.generate_advice).parameters) == expected


# L4 ------------------------------------------------------------------------

def test_plan_service_forwards_the_context_language_to_the_scrum_master():
    source = (BACKEND / "app/services/project_management_plan_service.py").read_text(encoding="utf-8")
    assert "AIScrumMasterAgent(\n                output_language=context.language,\n            )" in source
    assert "AIScrumMasterAgent().generate_advice" not in source


@pytest.mark.parametrize("language", ["fr", "en"])
def test_language_rule_is_placed_before_the_canonical_payload(language):
    # Instructions after a long JSON payload are easily ignored by small
    # models: the rule must sit with the other OUTPUT FORMAT rules.
    prompt = ProductOwnerAgent().build_prompt(po_context(language))
    assert prompt.index("OUTPUT LANGUAGE") < prompt.index("CANONICAL PROJECT MANAGEMENT CONTEXT")
