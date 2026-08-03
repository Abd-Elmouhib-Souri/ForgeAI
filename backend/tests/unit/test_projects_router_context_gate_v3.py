from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from app.routers import projects


class FakeDB:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


def test_market_region_is_never_invented() -> None:
    assert projects.normalize_market_region(None) == ""
    assert projects.normalize_market_region("") == ""
    assert projects.normalize_market_region("   ") == ""
    assert projects.normalize_market_region("  France  ") == "France"


def test_readiness_payload_preserves_canonical_contract() -> None:
    readiness = {
        "score": 0.61,
        "status": "needs_clarification",
        "ready_for_agents": False,
        "missing_fields": ["problem"],
        "ambiguous_fields": ["business_model"],
        "blockers": ["problem"],
        "project_context_packet": {
            "schema_version": "project_context_v3",
            "project_name": "Student App",
        },
        "context_confidence": {
            "score": 0.61,
            "status": "needs_clarification",
        },
        "legacy_project_context": {
            "project_name": "Student App",
        },
    }

    data = projects._build_readiness_analysis_data(
        readiness
    )

    assert data["idea_readiness"] == readiness
    assert data["needs_clarification"] is True
    assert data["partial_completion"] is False
    assert (
        data["project_context_packet"]["schema_version"]
        == "project_context_v3"
    )
    assert (
        data["context_extraction_quality"]["ready_for_agents"]
        is False
    )
    assert data["context_extraction_quality"]["blockers"] == [
        "problem"
    ]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            {
                "current_step": "needs_clarification",
                "analysis_data": {},
            },
            True,
        ),
        (
            {
                "analysis_data": {
                    "needs_clarification": True,
                }
            },
            True,
        ),
        (
            {
                "analysis_data": {
                    "idea_readiness": {
                        "ready_for_agents": False,
                    }
                }
            },
            True,
        ),
        (
            {
                "analysis_data": {
                    "idea_readiness": {
                        "ready_for_agents": True,
                    }
                }
            },
            False,
        ),
    ],
)
def test_clarification_detection(
    payload: dict[str, Any],
    expected: bool,
) -> None:
    assert (
        projects._analysis_requires_clarification(
            payload
        )
        is expected
    )


def test_clarification_state_is_not_completed_or_failed() -> None:
    async def scenario() -> None:
        db = FakeDB()
        project = SimpleNamespace(
            analysis_data=None,
            analysis_status="running",
            analysis_step="",
            analysis_progress=25,
            analysis_error="old error",
            analysis_completed_at="old completion",
            analysis_heartbeat_at=None,
        )

        analysis_data = {
            "idea_readiness": {
                "ready_for_agents": False,
                "questions": [
                    "Quel problème concret souhaitez-vous résoudre ?"
                ],
            },
            "project_context_packet": {
                "schema_version": "project_context_v3",
            },
        }

        await projects._persist_needs_clarification(
            db=db,
            project=project,
            analysis_data=analysis_data,
            output_language="fr",
        )

        assert db.commit_count == 1
        assert project.analysis_status == "needs_clarification"
        assert project.analysis_step == "Clarification du projet requise"
        assert project.analysis_progress == 10
        assert project.analysis_error is None
        assert project.analysis_completed_at is None
        assert project.analysis_heartbeat_at is not None
        assert project.analysis_data["needs_clarification"] is True
        assert project.analysis_data["partial_completion"] is False

    asyncio.run(scenario())


def test_preflight_is_before_every_analysis_agent() -> None:
    module_source = inspect.getsource(
        projects
    )

    readiness_position = module_source.index(
        "idea_readiness_checker.evaluate("
    )
    business_agent_position = module_source.index(
        "AIBusinessAnalystAgent()"
    )
    startup_graph_position = module_source.index(
        "StartupEvaluatorGraph()"
    )
    debate_graph_position = module_source.index(
        "DebateRoomGraph("
    )

    assert readiness_position < business_agent_position
    assert readiness_position < startup_graph_position
    assert readiness_position < debate_graph_position


def test_background_pipeline_has_defensive_clarification_stop() -> None:
    module_source = inspect.getsource(
        projects
    )

    start = module_source.index(
        "@analysis_run_guard.limit"
    )
    end = module_source.index(
        '@router.post(\n    "",',
        start,
    )
    function_source = module_source[
        start:end
    ]

    # One stop happens before Sprint 2 and another after the graph result.
    assert (
        function_source.count(
            "_persist_needs_clarification("
        )
        >= 2
    )

    assert (
        function_source.index(
            "_analysis_requires_clarification(graph_result)"
        )
        < function_source.index(
            "DebateRoomGraph("
        )
    )


def test_public_step_supports_clarification_status() -> None:
    assert (
        projects.public_analysis_step(
            "Clarification du projet requise",
            "fr",
        )
        == "Clarification du projet requise"
    )

    assert (
        projects.public_analysis_step(
            "Clarification du projet requise",
            "en",
        )
        == "Project clarification required"
    )