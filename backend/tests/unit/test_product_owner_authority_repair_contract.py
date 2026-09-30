"""
Product Owner authority-repair contracts.

Observed product RED (project 31 "TawlaPro", 26 Sept 2026, real Groq):
  [LLMProvider] success model=groq:openai/gpt-oss-120b task=product_owner
  [ProductOwner] Candidate authority rejected
      codes=['unresolved_provenance_ref', 'canonical_scope_undercovered']
      - invented reference 'mvp_scope:menu en français'
      - 2 of 11 MVP items not referenced by any provenance_refs
  -> the whole AI backlog was discarded for the deterministic fallback
     (11 identical 13-SP stories, one per sprint).

First Wrong Layer: contract. The validator's rule is mechanical (every
context.mvp_scope item must appear verbatim as "mvp_scope:<item>" in some
provenance_refs) but the prompt only said "preserve every MVP commitment",
and an authority rejection had no repair at all (only schema errors had one).

Universal fix:
  * the prompt lists the exact REQUIRED MVP COVERAGE references;
  * ONE bounded authority repair carrying the validator's exact errors,
    WITHOUT the previous output (keeps the request inside small TPM budgets);
  * still fail-closed: a second rejection raises candidate_authority_rejected,
    which the plan service already maps to the honest, flagged fallback.
"""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from app.agents.product_owner_agent import ProductOwnerAgent, ProductOwnerGenerationError
from tests.unit.test_product_owner_agent_universal_contract import make_context, make_payload

SCOPE = "reservation de postes"


def context():
    # Neutral fixture (not TawlaPro/SoukPilot): the rule is universal.
    return make_context(
        project_id="repair-1",
        project_name="Atelier Partage",
        language="fr",
        target_region="",
        industry="services",
        actor_name="Artisan",
        decision_maker_name="Gerant",
        workflow_name="Reserver un poste",
        action="reserve",
        object_name="poste de travail",
        result="poste reserve",
        mvp_scope=SCOPE,
        exclusion="paiement en ligne",
    )


def valid_payload(ctx):
    return make_payload(ctx, actor_name="Artisan", workflow_name="Reserver un poste",
                        mvp_scope=SCOPE, title="Reserver un poste")


def undercovered_payload(ctx):
    # Same backlog, but the only mvp_scope reference is replaced by an
    # invented one: both observed error codes at once.
    # Every occurrence is swapped, as in the real run, so both
    # unresolved_provenance_ref AND canonical_scope_undercovered fire.
    raw = json.dumps(deepcopy(valid_payload(ctx)), ensure_ascii=False)
    return json.loads(raw.replace(f"mvp_scope:{SCOPE}", "mvp_scope:menu en français"))


class ScriptedLLM:
    """Returns scripted outcomes in order and records every prompt."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.prompts: list[str] = []

    async def invoke(self, prompt: str, task_type: str = "general"):
        self.prompts.append(prompt)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return json.dumps(outcome, ensure_ascii=False)


# R1 ------------------------------------------------------------------------

def test_prompt_states_the_exact_mvp_coverage_rule():
    prompt = ProductOwnerAgent().build_prompt(context())
    assert "REQUIRED MVP COVERAGE" in prompt
    block = prompt.split("REQUIRED MVP COVERAGE", 1)[1]
    assert json.dumps([f"mvp_scope:{SCOPE}"], ensure_ascii=False) in block
    # The rule must sit before the long canonical payload.
    assert prompt.index("REQUIRED MVP COVERAGE") < prompt.index("CANONICAL PROJECT MANAGEMENT CONTEXT")


# R2 ------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authority_rejection_gets_one_repair_with_exact_errors():
    ctx = context()
    llm = ScriptedLLM(undercovered_payload(ctx), valid_payload(ctx))

    candidate = await ProductOwnerAgent(llm).generate_candidate_backlog(ctx)

    assert candidate.stories[0].candidate_key == "story_core"
    assert len(llm.prompts) == 2
    repair = llm.prompts[1]
    assert "AUTHORITY VALIDATION FAILED" in repair
    assert "unresolved_provenance_ref" in repair and "canonical_scope_undercovered" in repair
    assert "mvp_scope:menu en français" in repair  # the exact offending value
    assert "REQUIRED MVP COVERAGE" in repair


@pytest.mark.asyncio
async def test_repair_prompt_does_not_resend_the_previous_output():
    ctx = context()
    rejected = undercovered_payload(ctx)
    rejected["stories"][0]["business_value"] = "UNIQUE-PREVIOUS-OUTPUT-MARKER"
    llm = ScriptedLLM(rejected, valid_payload(ctx))

    await ProductOwnerAgent(llm).generate_candidate_backlog(ctx)

    assert "UNIQUE-PREVIOUS-OUTPUT-MARKER" not in llm.prompts[1]
    # Bounded growth: only the error report is added to the original prompt.
    assert len(llm.prompts[1]) - len(llm.prompts[0]) < 4000


# R3 ------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_second_rejection_stays_fail_closed_and_bounded():
    ctx = context()
    llm = ScriptedLLM(undercovered_payload(ctx), undercovered_payload(ctx))

    with pytest.raises(ProductOwnerGenerationError) as caught:
        await ProductOwnerAgent(llm).generate_candidate_backlog(ctx)

    assert caught.value.code == "candidate_authority_rejected"
    assert "canonical_scope_undercovered" in caught.value.details
    assert len(llm.prompts) == 2


@pytest.mark.asyncio
async def test_provider_failure_during_repair_keeps_the_original_rejection():
    ctx = context()
    llm = ScriptedLLM(undercovered_payload(ctx), RuntimeError("429 rate limit"))

    with pytest.raises(ProductOwnerGenerationError) as caught:
        await ProductOwnerAgent(llm).generate_candidate_backlog(ctx)

    # The plan service maps this code to the flagged deterministic fallback.
    assert caught.value.code == "candidate_authority_rejected"
    assert len(llm.prompts) == 2


@pytest.mark.asyncio
async def test_valid_first_answer_costs_a_single_call():
    ctx = context()
    llm = ScriptedLLM(valid_payload(ctx))
    await ProductOwnerAgent(llm).generate_candidate_backlog(ctx)
    assert len(llm.prompts) == 1
