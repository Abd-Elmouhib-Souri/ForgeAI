from __future__ import annotations

import asyncio
import json
from copy import deepcopy
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


ALLOWED_TYPES = {
    "split",
    "sequencing",
    "risk",
    "overload",
    "parallelization",
    "critical_dependency",
}


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
    *,
    locked: bool = False,
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
        locked=locked,
        warnings=[],
    )


def make_backlog(
    *,
    source_hash: str = "src-generic",
    context_hash: str = "ctx-generic",
    locked_first: bool = False,
) -> CanonicalBacklogV1:
    return CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash=source_hash,
        context_hash=context_hash,
        epics=[],
        features=[],
        stories=[
            make_story(
                "S-001",
                locked=locked_first,
            ),
            make_story(
                "S-002",
            ),
            make_story(
                "S-003",
            ),
        ],
        warnings=[],
    )


def make_graph(
    *,
    source_hash: str = "src-generic",
    context_hash: str = "ctx-generic",
) -> DependencyGraphV1:
    return DependencyGraphV1(
        source_context_hash=source_hash,
        context_hash=context_hash,
        edges=[],
        hard_topological_order=[
            "S-001",
            "S-002",
            "S-003",
        ],
        warnings=[],
    )


def make_settings() -> PlanningSettingsV1:
    return PlanningSettingsV1(
        sprint_count=4,
        sprint_duration_days=14,
        planned_velocity=12.0,
        team_size=3,
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


def make_payload(
    *,
    source_hash: str = "src-generic",
    context_hash: str = "ctx-generic",
    recommendations: list[
        dict[str, Any]
    ] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version":
            "scrum_master_advice_v1",
        "source_context_hash":
            source_hash,
        "context_hash":
            context_hash,
        "recommendations": (
            recommendations
            if recommendations is not None
            else [
                {
                    "recommendation_type":
                        "risk",
                    "story_ids": [
                        "S-001",
                    ],
                    "rationale":
                        "Review delivery uncertainty.",
                }
            ]
        ),
        "warnings": [],
    }


def make_json(
    **changes: Any,
) -> str:
    return json.dumps(
        make_payload(
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
) -> ScrumMasterAdviceV1:
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


def test_00_recommendation_taxonomy_remains_closed():
    assert ALLOWED_TYPES == {
        "split",
        "sequencing",
        "risk",
        "overload",
        "parallelization",
        "critical_dependency",
    }


def test_01_all_allowed_advice_types_survive_strict_validation():
    recommendations = [
        {
            "recommendation_type": value,
            "story_ids": [
                "S-001",
                "S-002",
            ],
            "rationale":
                f"Generic advisory rationale for {value}.",
        }
        for value in sorted(
            ALLOWED_TYPES
        )
    ]

    result = invoke(
        FakeLLM(
            response=make_json(
                recommendations=recommendations
            )
        )
    )

    assert {
        item.recommendation_type
        for item in result.recommendations
    } == ALLOWED_TYPES


def test_02_success_never_mutates_canonical_inputs():
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

    invoke(
        FakeLLM(
            response=make_json()
        ),
        backlog=backlog,
        graph=graph,
        settings=settings,
    )

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


def test_03_one_unknown_reference_rejects_entire_advice():
    recommendations = [
        {
            "recommendation_type":
                "sequencing",
            "story_ids": [
                "S-001",
                "S-UNKNOWN",
            ],
            "rationale":
                "Generic sequencing observation.",
        },
        {
            "recommendation_type":
                "risk",
            "story_ids": [
                "S-002",
            ],
            "rationale":
                "Generic risk observation.",
        },
    ]

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=make_json(
                    recommendations=recommendations
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "advice_authority_rejected"
    )

    assert (
        exc_info.value.details
        ==
        [
            "unknown_story_reference",
        ]
    )


def test_04_both_output_hash_mismatches_are_reported_deterministically():
    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            FakeLLM(
                response=make_json(
                    source_hash="wrong-source",
                    context_hash="wrong-context",
                )
            )
        )

    assert (
        exc_info.value.code
        ==
        "advice_authority_rejected"
    )

    assert (
        exc_info.value.details
        ==
        [
            "source_context_hash_mismatch",
            "context_hash_mismatch",
        ]
    )


def test_05_input_context_mismatch_fails_before_provider():
    backlog = make_backlog(
        context_hash="ctx-A"
    )

    graph = make_graph(
        context_hash="ctx-B"
    )

    provider = FakeLLM(
        response=make_json(
            context_hash="ctx-A"
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


def test_06_input_source_mismatch_fails_before_provider():
    backlog = make_backlog(
        source_hash="src-A"
    )

    graph = make_graph(
        source_hash="src-B"
    )

    provider = FakeLLM(
        response=make_json(
            source_hash="src-A"
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


def test_07_timeout_failure_is_typed_and_never_fabricated():
    provider = FakeLLM(
        error=TimeoutError(
            "synthetic timeout"
        )
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider
        )

    assert (
        exc_info.value.code
        ==
        "generation_temporarily_unavailable"
    )

    assert len(
        provider.calls
    ) == 1


def test_08_arbitrary_provider_failure_is_typed():
    provider = FakeLLM(
        error=RuntimeError(
            "synthetic provider failure"
        )
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider
        )

    assert (
        exc_info.value.code
        ==
        "generation_temporarily_unavailable"
    )

    assert len(
        provider.calls
    ) == 1


def test_09_none_response_is_invalid_model_response():
    provider = FakeLLM(
        response=None
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )

    assert len(
        provider.calls
    ) == 1


def test_10_json_array_is_rejected():
    provider = FakeLLM(
        response='[{"value":"not-an-object"}]'
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


def test_11_json_scalar_is_rejected():
    provider = FakeLLM(
        response="42"
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


def test_12_final_sprint_assignment_cannot_enter_advice_envelope():
    payload = make_payload()

    payload[
        "sprint_assignments"
    ] = [
        {
            "story_id":
                "S-001",
            "sprint":
                1,
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


def test_13_story_points_cannot_enter_recommendation():
    payload = make_payload()

    payload[
        "recommendations"
    ][0][
        "story_points"
    ] = 13

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


def test_14_invalid_model_response_is_not_retried():
    provider = FakeLLM(
        response=(
            "This is prose, not strict JSON."
        )
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as exc_info:
        invoke(
            provider
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )

    assert len(
        provider.calls
    ) == 1


def test_15_locked_story_is_never_mutated_or_assigned():
    backlog = make_backlog(
        locked_first=True
    )

    before = deepcopy(
        backlog.model_dump(
            mode="python"
        )
    )

    result = invoke(
        FakeLLM(
            response=make_json(
                recommendations=[
                    {
                        "recommendation_type":
                            "risk",
                        "story_ids": [
                            "S-001",
                        ],
                        "rationale":
                            "Locked canonical Story remains advisory-only.",
                    }
                ]
            )
        ),
        backlog=backlog,
    )

    assert isinstance(
        result,
        ScrumMasterAdviceV1,
    )

    assert backlog.stories[0].locked is True

    assert (
        backlog.model_dump(
            mode="python"
        )
        ==
        before
    )

    assert (
        "sprint_assignments"
        not in result.model_fields
    )

    assert (
        "final_sprint_plan"
        not in result.model_fields
    )