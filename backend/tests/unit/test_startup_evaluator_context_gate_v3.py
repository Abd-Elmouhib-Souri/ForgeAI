from __future__ import annotations

import asyncio
from typing import Any, Dict

import app.agents.startup_evaluator_graph as graph_module
from app.agents.startup_evaluator_graph import StartupEvaluatorGraph


def _readiness_payload(
    *,
    ready: bool,
) -> Dict[str, Any]:
    status = (
        "ready_cautious"
        if ready
        else "needs_clarification"
    )

    score = 0.83 if ready else 0.42

    return {
        "format": (
            "idea_readiness_v1_context_confidence"
        ),
        "canonical_format": (
            "idea_readiness_v3_project_context"
        ),
        "schema_version": (
            "project_context_v3"
        ),
        "status": status,
        "score": score,
        "ready_for_agents": ready,
        "threshold": 0.75,
        "missing_fields": (
            []
            if ready
            else ["problem"]
        ),
        "ambiguous_fields": (
            ["business_model"]
            if ready
            else ["actors"]
        ),
        "blockers": (
            []
            if ready
            else ["problem"]
        ),
        "questions": (
            []
            if ready
            else [
                (
                    "Quel problème concret "
                    "souhaitez-vous résoudre ?"
                )
            ]
        ),
        "clarification_questions": (
            []
            if ready
            else [
                (
                    "Quel problème concret "
                    "souhaitez-vous résoudre ?"
                )
            ]
        ),
        "project_context_packet": {
            "schema_version": (
                "project_context_v3"
            ),
            "project_name": "Test Project",
            "description": (
                "Description de test."
            ),
            "target_region": "",
            "primary_archetype": (
                "b2b_workflow_saas"
            ),
        },
        "context_confidence": {
            "score": score,
            "status": status,
            "missing_fields": (
                []
                if ready
                else ["problem"]
            ),
            "ambiguous_fields": (
                ["business_model"]
                if ready
                else ["actors"]
            ),
            "blockers": (
                []
                if ready
                else ["problem"]
            ),
            "ready_for_agents": ready,
        },
        "legacy_project_context": {
            "project_name": (
                "Test Project"
            ),
            "target_region": "",
            "project_archetype": (
                "b2b_workflow_saas"
            ),
        },
    }


class _FailIfInvokedApp:
    async def ainvoke(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise AssertionError(
            "LangGraph agents must not start."
        )


class _CaptureApp:
    def __init__(self) -> None:
        self.state: Dict[str, Any] | None = None

    async def ainvoke(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.state = dict(state)

        return {
            **state,
            "current_step": "startup_score",
            "progress": 100,
        }


def _graph_without_agent_initialization(
    app: Any,
) -> StartupEvaluatorGraph:
    graph = StartupEvaluatorGraph.__new__(
        StartupEvaluatorGraph
    )

    graph.on_step_complete = None
    graph.app = app

    return graph


def test_gate_is_mandatory_and_stops_before_project_intelligence(
    monkeypatch: Any,
) -> None:
    readiness = _readiness_payload(
        ready=False
    )

    monkeypatch.setattr(
        graph_module.project_context_builder,
        "build",
        lambda **kwargs: {
            "title": kwargs.get(
                "title",
                "",
            ),
        },
    )

    monkeypatch.setattr(
        graph_module.idea_readiness_checker,
        "evaluate",
        lambda **kwargs: readiness,
    )

    def _project_intelligence_must_not_run(
        **kwargs: Any,
    ) -> Dict[str, Any]:
        raise AssertionError(
            "Project Intelligence Layer must "
            "not run before clarification."
        )

    monkeypatch.setattr(
        graph_module.project_intelligence_layer,
        "build",
        _project_intelligence_must_not_run,
    )

    graph = (
        _graph_without_agent_initialization(
            _FailIfInvokedApp()
        )
    )

    result = asyncio.run(
        graph.run(
            {
                "project_id": 12,
                "title": "Vague App",
                "description": (
                    "Une application utile."
                ),
                "industry": "",
                "target_region": "",
                # This old flag must no longer
                # disable the gate.
                "enforce_idea_readiness": False,
            }
        )
    )

    assert (
        result["current_step"]
        == "needs_clarification"
    )

    assert (
        result["completed_steps"]
        == ["idea_readiness_check"]
    )

    assert result["region"] == ""

    assert (
        result["analysis_data"][
            "needs_clarification"
        ]
        is True
    )

    assert (
        result["analysis_data"][
            "pipeline_stop"
        ][
            "external_search_started"
        ]
        is False
    )

    assert (
        result["analysis_data"][
            "pipeline_stop"
        ][
            "project_intelligence_started"
        ]
        is False
    )

    assert (
        result["analysis_data"][
            "pipeline_stop"
        ][
            "heavy_agents_started"
        ]
        is False
    )

    assert (
        graph.on_step_complete
        is None
    )


def test_ready_context_reaches_agents_with_one_canonical_packet(
    monkeypatch: Any,
) -> None:
    readiness = _readiness_payload(
        ready=True
    )

    monkeypatch.setattr(
        graph_module.project_context_builder,
        "build",
        lambda **kwargs: {
            "title": kwargs.get(
                "title",
                "",
            ),
            "target_region": (
                kwargs.get(
                    "market_region",
                    "",
                )
            ),
            "old_inference": (
                "must_not_override_v3"
            ),
        },
    )

    monkeypatch.setattr(
        graph_module.idea_readiness_checker,
        "evaluate",
        lambda **kwargs: readiness,
    )

    project_intelligence_calls = {
        "count": 0,
    }

    def _build_intelligence(
        **kwargs: Any,
    ) -> Dict[str, Any]:
        project_intelligence_calls[
            "count"
        ] += 1

        assert (
            kwargs["project_context"][
                "project_context_packet"
            ]
            == readiness[
                "project_context_packet"
            ]
        )

        return {
            "status": "ready",
            "structured_project_context": {
                "source": (
                    "project_intelligence"
                ),
            },
            "query_planner": {
                "queries": [
                    "test query",
                ],
            },
            "agent_context_packet": {
                "legacy_key": "preserved",
            },
        }

    monkeypatch.setattr(
        graph_module.project_intelligence_layer,
        "build",
        _build_intelligence,
    )

    monkeypatch.setattr(
        graph_module.project_intelligence_layer,
        "merge_into_project_context",
        lambda **kwargs: {
            **kwargs[
                "base_project_context"
            ],
            "project_archetype": (
                "wrong_old_archetype"
            ),
            "domain_label": "Test",
        },
    )

    capture_app = _CaptureApp()

    graph = (
        _graph_without_agent_initialization(
            capture_app
        )
    )

    result = asyncio.run(
        graph.run(
            {
                "project_id": 13,
                "title": "Test Project",
                "description": (
                    "Description de test."
                ),
                "industry": "SaaS B2B",
                "target_region": "",
            }
        )
    )

    assert (
        project_intelligence_calls[
            "count"
        ]
        == 1
    )

    assert capture_app.state is not None

    state = capture_app.state

    analysis_data = state[
        "analysis_data"
    ]

    assert state["region"] == ""

    assert (
        analysis_data[
            "project_context_packet"
        ]
        == readiness[
            "project_context_packet"
        ]
    )

    assert (
        analysis_data[
            "context_confidence"
        ]
        == readiness[
            "context_confidence"
        ]
    )

    assert (
        analysis_data[
            "legacy_project_context"
        ]
        == readiness[
            "legacy_project_context"
        ]
    )

    assert (
        analysis_data[
            "agent_context_packet"
        ][
            "legacy_key"
        ]
        == "preserved"
    )

    assert (
        analysis_data[
            "agent_context_packet"
        ][
            "project_context_packet"
        ]
        == readiness[
            "project_context_packet"
        ]
    )

    assert (
        state[
            "project_context"
        ][
            "project_archetype"
        ]
        == "b2b_workflow_saas"
    )

    assert (
        result["analysis_data"][
            "startup_evaluator_meta"
        ][
            "readiness_enforced"
        ]
        is True
    )


def test_agent_step_receives_canonical_context_fields() -> None:
    received: Dict[str, Any] = {}

    class _Agent:
        async def run(
            self,
            state: Dict[str, Any],
        ) -> Dict[str, Any]:
            received.update(
                state
            )

            return {
                "status": "ok",
            }

    graph = (
        _graph_without_agent_initialization(
            _CaptureApp()
        )
    )

    state = {
        "project_id": 1,
        "title": "Test",
        "description": (
            "Description de test."
        ),
        "industry": "SaaS",
        "region": "",
        "output_language": "fr",
        "project_context": {},
        "analysis_data": {
            "project_intelligence": {
                "status": "ready",
            },
            "structured_project_context": {
                "project_name": "Test",
            },
            "agent_context_packet": {
                "context_locked": True,
            },
            "project_context_packet": {
                "schema_version": (
                    "project_context_v3"
                ),
            },
            "context_confidence": {
                "score": 0.83,
            },
            "idea_readiness": {
                "ready_for_agents": True,
            },
            "legacy_project_context": {
                "project_name": "Test",
            },
            "query_planner": {
                "queries": [],
            },
        },
        "completed_steps": [],
        "failed_steps": [],
        "current_step": (
            "project_intelligence_layer"
        ),
        "progress": 7,
        "error": None,
        "partial_completion": False,
    }

    asyncio.run(
        graph._run_agent_step(
            state=state,
            step_name="market_study",
            result_key="market_study",
            progress=32,
            agent=_Agent(),
        )
    )

    assert (
        received[
            "project_context_packet"
        ][
            "schema_version"
        ]
        == "project_context_v3"
    )

    assert (
        received[
            "context_confidence"
        ][
            "score"
        ]
        == 0.83
    )

    assert (
        received[
            "idea_readiness"
        ][
            "ready_for_agents"
        ]
        is True
    )

    assert (
        received[
            "legacy_project_context"
        ][
            "project_name"
        ]
        == "Test"
    )