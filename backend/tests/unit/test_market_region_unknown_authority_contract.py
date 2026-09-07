from pathlib import Path

from app.schemas.project import ProjectCreate
from app.services.project_context_builder import project_context_builder


def test_missing_market_region_remains_unknown_at_project_admission() -> None:
    project = ProjectCreate(
        title="Universal project",
        description="A project with no declared geography.",
    )

    assert project.market_region == ""


def test_project_payload_does_not_invent_a_country_for_unknown_region() -> None:
    payload = project_context_builder.project_payload(
        project_id=1,
        title="Universal project",
        description="A project with no declared geography.",
        industry=None,
        market_region=None,
        output_language="en",
    )

    assert payload["market_region"] == ""


def test_runtime_agents_do_not_restore_the_legacy_tunisia_fallback() -> None:
    root = Path(__file__).resolve().parents[2]
    agent_files = (
        root / "app" / "agents" / "defender_agent.py",
        root / "app" / "agents" / "critic_agent.py",
        root / "app" / "agents" / "judge_agent.py",
    )

    for path in agent_files:
        assert 'or "Tunisie"' not in path.read_text(encoding="utf-8")
