"""
Sprint 5 hardening contracts (session 21-22 Sept 2026).

These contracts guard behaviour introduced AFTER the 2382/2382 GREEN
baseline and not covered by it:

  H1  The JSON example embedded in the candidate prompt must itself be a
      valid CandidateSolutionArchitectureV1 (an example that violates the
      strict schema teaches the LLM to fail validation).
  H2  ForgeAI imposes schema_version, exactly like the context fingerprint:
      a model omitting / mistyping the literal no longer rejects the whole
      candidate.
  H3  UML repair is deterministic-first, but an empty deterministic
      projection (no actors/workflows, no DB entities) falls back to ONE
      bounded LLM repair instead of failing the architecture closed.
  H4  LLMProvider structured-mode health is isolated from normal invoke()
      health, and providers without tool calling are never contacted.

Universal: no project name, sector, country or fixture-specific value.
"""

from __future__ import annotations

import json

import pytest

from app.agents.solution_architect_agent import SolutionArchitectAgent
from app.llm.provider import LLMModelConfig, LLMProvider, ProviderHealth
from app.schemas.solution_architecture import (
    CandidateSolutionArchitectureV1,
    CandidateUMLDiagramV1,
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
)
from app.services import solution_architecture_core as core


# -------------------------------------------------------------------------
# Neutral fixtures (no domain, no country, no project name semantics)
# -------------------------------------------------------------------------

FINGERPRINT = "a" * 64

VALID_UML = {
    "use_case": "@startuml\nactor User\nusecase Process\n@enduml",
    "class": "@startuml\nclass Record\n@enduml",
    "sequence": "@startuml\nactor User\nparticipant Service\nUser -> Service: process\n@enduml",
    "activity": "@startuml\nstart\n:Process;\nstop\n@enduml",
}


def neutral_context() -> SolutionArchitectureContextV1:
    # Empty actors/workflows on purpose: deterministic use_case/class
    # builders have nothing to project from.
    return SolutionArchitectureContextV1(
        schema_version="solution_architecture_context_v1",
        language="en",
        project_name="Neutral Architecture Project",
        technical_signals=TechnicalSignalsV1(),
        upstream_context_fingerprint=FINGERPRINT,
    )


class FakeLLM:
    """Records every call; returns queued responses in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def invoke(self, prompt, task_type):
        self.calls.append({"prompt": prompt, "task_type": task_type})
        if not self.responses:
            raise RuntimeError("unexpected fake provider call")
        return self.responses.pop(0)


def _prompt_example(prompt: str) -> dict:
    # The example is the single line right after the "never nested inside
    # architecture):" marker in the candidate prompt.
    marker = "never nested inside architecture):\n"
    assert marker in prompt, "candidate prompt lost its JSON example"
    line = prompt.split(marker, 1)[1].split("\n", 1)[0]
    return json.loads(line)


# -------------------------------------------------------------------------
# H1 — prompt example must satisfy the strict schema
# -------------------------------------------------------------------------

def test_h1_prompt_example_is_a_valid_candidate():
    prompt = SolutionArchitectAgent(llm=FakeLLM([])).build_prompt(
        context=neutral_context()
    )
    example = _prompt_example(prompt)

    # "<sha256>" is a placeholder by design; ForgeAI imposes the real value.
    example["source_context_fingerprint"] = FINGERPRINT

    # Must not raise: every field name/type shown to the model is legal.
    CandidateSolutionArchitectureV1.model_validate(example)


def test_h1_prompt_names_the_schema_version_literal():
    prompt = SolutionArchitectAgent(llm=FakeLLM([])).build_prompt(
        context=neutral_context()
    )
    assert "candidate_solution_architecture_v1" in prompt


# -------------------------------------------------------------------------
# H2 — schema_version imposed by ForgeAI
# -------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("schema_version", [None, "candidate_v1", "V1"])
async def test_h2_schema_version_is_imposed_not_trusted(schema_version):
    payload = {
        "source_context_fingerprint": "b" * 64,  # wrong on purpose
        "architecture": {"style": "modular_monolith", "rationale": ["r"]},
    }
    if schema_version is not None:
        payload["schema_version"] = schema_version

    fake = FakeLLM([json.dumps(payload)])
    candidate = await SolutionArchitectAgent(
        llm=fake
    ).generate_candidate_architecture(context=neutral_context())

    assert candidate.schema_version == "candidate_solution_architecture_v1"
    # Existing invariant kept: fingerprint always comes from ForgeAI.
    assert candidate.source_context_fingerprint == FINGERPRINT
    assert len(fake.calls) == 1


# -------------------------------------------------------------------------
# H3 — deterministic-first UML repair with bounded LLM fallback
# -------------------------------------------------------------------------

def _candidate(diagrams: dict[str, str]) -> CandidateSolutionArchitectureV1:
    return CandidateSolutionArchitectureV1(
        schema_version="candidate_solution_architecture_v1",
        source_context_fingerprint=FINGERPRINT,
        uml_diagrams=[
            CandidateUMLDiagramV1(
                diagram_type=t, syntax="plantuml", source=s
            )
            for t, s in diagrams.items()
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("broken_type", ["use_case", "class"])
async def test_h3_empty_deterministic_projection_falls_back_to_one_llm_repair(
    broken_type,
):
    diagrams = dict(VALID_UML)
    diagrams[broken_type] = "@startuml\nnote invalid\n@enduml"

    fake = FakeLLM([
        json.dumps({
            "diagram_type": broken_type,
            "syntax": "plantuml",
            "source": VALID_UML[broken_type],
        })
    ])
    service = core.UMLCompletionService(agent=SolutionArchitectAgent(llm=fake))

    bundle = await service.complete(
        context=neutral_context(), candidate=_candidate(diagrams)
    )

    attr = "class_diagram" if broken_type == "class" else broken_type
    assert getattr(bundle, attr).validation_status == "valid"
    assert len(fake.calls) == 1  # bounded: exactly one repair call


@pytest.mark.asyncio
async def test_h3_still_fails_closed_when_llm_repair_is_invalid_too():
    diagrams = dict(VALID_UML)
    diagrams["class"] = "@startuml\nnote invalid\n@enduml"

    fake = FakeLLM([
        json.dumps({
            "diagram_type": "class",
            "syntax": "plantuml",
            "source": "@startuml\nnote still invalid\n@enduml",
        })
    ])
    service = core.UMLCompletionService(agent=SolutionArchitectAgent(llm=fake))

    with pytest.raises(core.SolutionArchitectureCoreError):
        await service.complete(
            context=neutral_context(), candidate=_candidate(diagrams)
        )
    assert len(fake.calls) == 1


# -------------------------------------------------------------------------
# H4 — structured-mode circuit isolation & capability skip
# -------------------------------------------------------------------------

def _bare_provider(configs: list[LLMModelConfig]) -> LLMProvider:
    # Bypass __init__ (no real API keys needed); reset shared class state
    # so tests never leak circuit health into each other.
    provider = object.__new__(LLMProvider)
    provider.model_configs = configs
    LLMProvider._shared_health.clear()
    LLMProvider._shared_models.clear()
    return provider


def _config(provider: str, structured: bool) -> LLMModelConfig:
    return LLMModelConfig(
        provider=provider,
        model_name=f"{provider}-model",
        rpm=600,
        api_key="test-key",
        priority=1,
        supports_structured=structured,
    )


def test_h4_structured_failures_never_open_the_normal_circuit():
    config = _config("groq", structured=False)
    provider = _bare_provider([config])

    # A proven configuration failure in structured mode opens only the
    # ":structured" circuit.
    provider._record_failure(config, "configuration", structured=True)

    assert provider._circuit_is_open(config, structured=True) is True
    assert provider._circuit_is_open(config, structured=False) is False


def test_h4_normal_failures_never_open_the_structured_circuit():
    config = _config("gemini", structured=True)
    provider = _bare_provider([config])

    provider._record_failure(config, "configuration", structured=False)

    assert provider._circuit_is_open(config, structured=False) is True
    assert provider._circuit_is_open(config, structured=True) is False


@pytest.mark.asyncio
async def test_h4_invoke_structured_skips_models_without_tool_calling(monkeypatch):
    no_tools = _config("groq", structured=False)
    with_tools = _config("gemini", structured=True)
    provider = _bare_provider([no_tools, with_tools])

    requested: list[str] = []

    class _StructuredModel:
        async def ainvoke(self, prompt):
            return {"ok": True}

    class _Model:
        def with_structured_output(self, schema):
            return _StructuredModel()

    async def fake_get_or_create_model(config, *, structured=False):
        requested.append(config.provider)
        return _Model()

    monkeypatch.setattr(provider, "_get_or_create_model", fake_get_or_create_model)

    result = await provider.invoke_structured("prompt", dict, "test")

    assert result == {"ok": True}
    assert requested == ["gemini"]  # groq never contacted


def test_h4_health_entries_are_distinct_objects():
    config = _config("gemini", structured=True)
    provider = _bare_provider([config])
    provider._circuit_is_open(config, structured=False)
    provider._circuit_is_open(config, structured=True)

    normal = LLMProvider._shared_health[provider._health_key(config)]
    structured = LLMProvider._shared_health[
        provider._health_key(config, structured=True)
    ]
    assert isinstance(normal, ProviderHealth)
    assert normal is not structured


# -------------------------------------------------------------------------
# H5 — database field-name synonyms (real gpt-oss answer, 25 Sept 2026)
#
# The model wrote "type" and "source_column"/"referenced_table"/
# "referenced_column" (87 validation errors). Renaming KEYS is a
# deterministic repair; values are never invented.
# -------------------------------------------------------------------------

def _answer_with_synonyms(with_description: bool = True) -> dict:
    entity_extra = {"description": "Restaurant enregistre."} if with_description else {}
    return {
        "architecture": {"style": "modular_monolith", "rationale": ["r"]},
        "database": {
            "status": "recommended",
            "rationale": "Donnees relationnelles.",
            "dialect": "postgresql",
            "entities": [
                {"name": "restaurant", **entity_extra,
                 "columns": [{"name": "id", "type": "SERIAL", "primary_key": True},
                             {"name": "name", "type": "VARCHAR(255)"}]},
                {"name": "table", **entity_extra,
                 "columns": [{"name": "id", "type": "SERIAL", "primary_key": True},
                             {"name": "restaurant_id", "type": "INTEGER"}],
                 "foreign_keys": [{"source_column": "restaurant_id",
                                   "referenced_table": "restaurant",
                                   "referenced_column": "id"}]},
            ],
        },
    }


@pytest.mark.asyncio
async def test_h5_key_synonyms_are_renamed_before_validation():
    fake = FakeLLM([json.dumps(_answer_with_synonyms())])
    candidate = await SolutionArchitectAgent(llm=fake).generate_candidate_architecture(
        context=neutral_context()
    )
    table = candidate.database.entities[1]
    assert table.columns[1].data_type == "INTEGER"
    fk = table.foreign_keys[0]
    assert (fk.column, fk.references_table, fk.references_column) == ("restaurant_id", "restaurant", "id")


def test_h5_canonical_key_wins_over_its_synonym():
    from app.agents.solution_architect_agent import normalize_candidate_field_aliases

    payload = {"database": {"entities": [{"columns": [{"name": "c", "data_type": "TEXT", "type": "INTEGER"}]}]}}
    column = normalize_candidate_field_aliases(payload)["database"]["entities"][0]["columns"][0]
    assert column["data_type"] == "TEXT"  # never overwritten
    assert column["type"] == "INTEGER"    # left for strict validation to reject


@pytest.mark.asyncio
async def test_h5_missing_content_is_never_invented():
    from app.agents.solution_architect_agent import SolutionArchitectGenerationError

    fake = FakeLLM([json.dumps(_answer_with_synonyms(with_description=False))])
    with pytest.raises(SolutionArchitectGenerationError):
        await SolutionArchitectAgent(llm=fake).generate_candidate_architecture(context=neutral_context())


def test_h5_prompt_example_shows_every_database_field_name():
    prompt = SolutionArchitectAgent(llm=FakeLLM([])).build_prompt(context=neutral_context())
    example = _prompt_example(prompt)
    entity = example["database"]["entities"][0]
    assert {"name", "description", "columns", "foreign_keys"} <= set(entity)
    assert "data_type" in entity["columns"][0]
    assert set(entity["foreign_keys"][0]) == {"column", "references_table", "references_column"}


# -------------------------------------------------------------------------
# H6 — core stack slots use their exact names (real run, 25 Sept 2026)
#
# Frontend and infrastructure showed "not applicable" for a product with a
# smartphone app and a kitchen tablet: the model named those layers
# differently, so the assembler filed them as additional layers (which the
# UI never displayed).
# -------------------------------------------------------------------------

def test_h6_prompt_names_the_four_core_layers_exactly():
    prompt = SolutionArchitectAgent(llm=FakeLLM([])).build_prompt(context=neutral_context())
    layers = [layer["layer"] for layer in _prompt_example(prompt)["stack"]["layers"]]
    assert layers == ["frontend", "backend", "database", "infrastructure"]
    assert "Use EXACTLY these layer names" in prompt
