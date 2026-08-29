from __future__ import annotations

import asyncio
import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from app.agents.scrum_master_agent import (
    AIScrumMasterAgent,
    ScrumMasterGenerationError,
)
from app.schemas.project_management import (
    CanonicalBacklogV1,
    CanonicalUserStoryV1,
    PlanningSettingsV1,
    ScrumMasterAdviceV1,
)
from app.services.dependency_graph_builder import (
    DependencyGraphV1,
)


AGENT_PATH = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "agents"
    / "scrum_master_agent.py"
)

AGENT_SOURCE = AGENT_PATH.read_text(
    encoding="utf-8"
)

RUNTIME_BLOCKED = (
    '"runtime_not_certified"'
    in AGENT_SOURCE
)


EXPECTED_TASK_TYPE = (
    "scrum_master_advice"
)


EXPECTED_GENERATION_ERROR_CODES = {
    "generation_temporarily_unavailable",
    "invalid_model_response",
    "advice_authority_rejected",
    "canonical_binding_mismatch",
}


EXPECTED_AUTHORITY_DETAILS = {
    "source_context_hash_mismatch",
    "context_hash_mismatch",
    "unknown_story_reference",
}


runtime_contract = pytest.mark.skipif(
    RUNTIME_BLOCKED,
    reason=(
        "AI Scrum Master runtime remains intentionally "
        "blocked; runtime-enabled tests are armed."
    ),
)


class FakeLLM:
    def __init__(
        self,
        *,
        response: Any = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[
            dict[str, str]
        ] = []

    async def invoke(
        self,
        prompt: str,
        task_type: str,
    ) -> Any:
        self.calls.append(
            {
                "prompt": prompt,
                "task_type": task_type,
            }
        )

        if self.error is not None:
            raise self.error

        return self.response


def _run(coro):
    return asyncio.run(
        coro
    )


def make_story(
    story_id: str,
) -> CanonicalUserStoryV1:
    return CanonicalUserStoryV1.model_construct(
        story_id=story_id,
        title=f"Story {story_id}",
        story=f"Canonical story {story_id}",
        business_value="canonical",
        priority="Must",
        story_points=3,
        dependencies=[],
        dependency_hint_ids=[],
        locked=False,
        warnings=[],
    )


def make_backlog(
    *,
    source_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
) -> CanonicalBacklogV1:
    return CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash=source_hash,
        context_hash=context_hash,
        epics=[],
        features=[],
        stories=[
            make_story(
                "US-001"
            ),
            make_story(
                "US-002"
            ),
        ],
        warnings=[],
    )


def make_graph(
    *,
    source_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
) -> DependencyGraphV1:
    return DependencyGraphV1(
        source_context_hash=source_hash,
        context_hash=context_hash,
        edges=[],
        hard_topological_order=[
            "US-001",
            "US-002",
        ],
        warnings=[],
    )


def make_settings() -> PlanningSettingsV1:
    return PlanningSettingsV1(
        sprint_count=4,
        sprint_duration_days=14,
        planned_velocity=8.0,
        team_size=2,
        capacity_adjustment=1.0,
        start_date="2030-01-01",
        working_days=[
            1,
            2,
            3,
            4,
            5,
        ],
    )


def valid_payload(
    *,
    source_hash: str = "src-hash",
    context_hash: str = "ctx-hash",
    story_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version":
            "scrum_master_advice_v1",
        "source_context_hash":
            source_hash,
        "context_hash":
            context_hash,
        "recommendations": [
            {
                "recommendation_type":
                    "risk",
                "story_ids": (
                    list(
                        story_ids
                        if story_ids is not None
                        else [
                            "US-001",
                        ]
                    )
                ),
                "rationale":
                    "Review delivery risk before planning.",
            }
        ],
        "warnings": [],
    }


def valid_json(
    **changes: Any,
) -> str:
    return json.dumps(
        valid_payload(
            **changes
        ),
        ensure_ascii=False,
        sort_keys=True,
    )


def invoke(
    provider: FakeLLM,
    *,
    backlog: CanonicalBacklogV1 | None = None,
    graph: DependencyGraphV1 | None = None,
    settings: PlanningSettingsV1 | None = None,
):
    return _run(
        AIScrumMasterAgent(
            llm=provider
        ).generate_advice(
            backlog=(
                backlog
                if backlog is not None
                else make_backlog()
            ),
            dependency_graph=(
                graph
                if graph is not None
                else make_graph()
            ),
            planning_settings=(
                settings
                if settings is not None
                else make_settings()
            ),
        )
    )


def test_00_runtime_contract_defines_closed_failure_semantics():
    assert EXPECTED_TASK_TYPE == (
        "scrum_master_advice"
    )

    assert EXPECTED_GENERATION_ERROR_CODES == {
        "generation_temporarily_unavailable",
        "invalid_model_response",
        "advice_authority_rejected",
        "canonical_binding_mismatch",
    }

    assert EXPECTED_AUTHORITY_DETAILS == {
        "source_context_hash_mismatch",
        "context_hash_mismatch",
        "unknown_story_reference",
    }


def test_01_runtime_contract_has_no_direct_external_llm_imports():
    tree = ast.parse(
        Path(
            __file__
        ).read_text(
            encoding="utf-8"
        )
    )

    imports = {
        node.module
        for node in ast.walk(
            tree
        )
        if (
            isinstance(
                node,
                ast.ImportFrom,
            )
            and node.module
        )
    }

    forbidden_external = (
        "langchain",
        "langgraph",
        "google",
        "groq",
        "openai",
        "requests",
        "httpx",
    )

    hits = [
        module
        for module in imports
        if module.startswith(
            forbidden_external
        )
    ]

    assert not hits


def test_02_scrum_master_runtime_generation_is_enabled():
    provider = FakeLLM(
        response=valid_json()
    )

    try:
        result = invoke(
            provider
        )

    except ScrumMasterGenerationError as exc:
        pytest.fail(
            "S4_9_RUNTIME_FIRST_WRONG_LAYER="
            f"{exc.code}"
        )

    assert isinstance(
        result,
        ScrumMasterAdviceV1,
    )


@runtime_contract
def test_03_runtime_uses_injected_provider_once():
    provider = FakeLLM(
        response=valid_json()
    )

    invoke(
        provider
    )

    assert len(
        provider.calls
    ) == 1


@runtime_contract
def test_04_runtime_uses_scrum_master_task_type():
    provider = FakeLLM(
        response=valid_json()
    )

    invoke(
        provider
    )

    assert (
        provider.calls[0][
            "task_type"
        ]
        ==
        EXPECTED_TASK_TYPE
    )


@runtime_contract
def test_05_runtime_prompt_is_deterministic_and_inputs_are_immutable():
    backlog = make_backlog()
    graph = make_graph()
    settings = make_settings()

    backlog_before = deepcopy(
        backlog.model_dump(
            mode="python"
        )
    )

    graph_before = deepcopy(
        graph.model_dump(
            mode="python"
        )
    )

    settings_before = deepcopy(
        settings.model_dump(
            mode="python"
        )
    )

    agent = AIScrumMasterAgent()

    first = agent.build_prompt(
        backlog,
        graph,
        settings,
    )

    second = agent.build_prompt(
        backlog,
        graph,
        settings,
    )

    assert first == second

    assert (
        backlog.model_dump(
            mode="python"
        )
        ==
        backlog_before
    )

    assert (
        graph.model_dump(
            mode="python"
        )
        ==
        graph_before
    )

    assert (
        settings.model_dump(
            mode="python"
        )
        ==
        settings_before
    )


@runtime_contract
def test_06_runtime_returns_strict_scrum_master_advice():
    result = invoke(
        FakeLLM(
            response=valid_json()
        )
    )

    assert isinstance(
        result,
        ScrumMasterAdviceV1,
    )

    assert (
        result.schema_version
        ==
        "scrum_master_advice_v1"
    )


@runtime_contract
def test_07_runtime_accepts_markdown_fenced_json_only():
    fenced = (
        "```json\n"
        + valid_json()
        + "\n```"
    )

    result = invoke(
        FakeLLM(
            response=fenced
        )
    )

    assert isinstance(
        result,
        ScrumMasterAdviceV1,
    )


@runtime_contract
def test_08_empty_response_is_not_replaced_with_fake_advice():
    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=""
            )
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


@runtime_contract
def test_09_invalid_json_is_not_repaired_or_fabricated():
    response = (
        'Here is your advice: '
        '{"schema_version":"scrum_master_advice_v1"}'
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=response
            )
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


@runtime_contract
def test_10_provider_failure_produces_no_fake_valid_advice():
    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                error=RuntimeError(
                    "provider unavailable"
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "generation_temporarily_unavailable"
    )


@runtime_contract
def test_11_forbidden_final_planning_field_is_rejected():
    payload = valid_payload()

    payload[
        "sprint_assignments"
    ] = [
        {
            "story_id": "US-001",
            "sprint": 1,
        }
    ]

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=json.dumps(
                    payload
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


@runtime_contract
def test_12_wrong_source_context_hash_is_rejected_by_authority():
    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=valid_json(
                    source_hash="wrong-src-hash"
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "advice_authority_rejected"
    )

    assert (
        "source_context_hash_mismatch"
        in exc_info.value.details
    )


@runtime_contract
def test_13_wrong_context_hash_is_rejected_by_authority():
    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=valid_json(
                    context_hash="wrong-ctx-hash"
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "advice_authority_rejected"
    )

    assert (
        "context_hash_mismatch"
        in exc_info.value.details
    )


@runtime_contract
def test_14_unknown_story_reference_is_rejected():
    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=valid_json(
                    story_ids=[
                        "US-NOT-CANONICAL",
                    ]
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "advice_authority_rejected"
    )

    assert (
        "unknown_story_reference"
        in exc_info.value.details
    )


@runtime_contract
def test_15_input_binding_mismatch_fails_before_provider_execution():
    backlog = make_backlog(
        source_hash="src-A",
        context_hash="ctx-A",
    )

    graph = make_graph(
        source_hash="src-B",
        context_hash="ctx-A",
    )

    provider = FakeLLM(
        response=valid_json(
            source_hash="src-A",
            context_hash="ctx-A",
        )
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider,
            backlog=backlog,
            graph=graph,
        )

    assert (
        exc_info.value.code
        ==
        "canonical_binding_mismatch"
    )

    assert provider.calls == []