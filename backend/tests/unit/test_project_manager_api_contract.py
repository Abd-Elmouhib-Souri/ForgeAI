from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "app" / "routers" / "project_manager.py"
SERVICE = ROOT / "app" / "services" / "project_management_plan_service.py"
MAIN = ROOT / "app" / "main.py"


def test_project_manager_router_exposes_the_owner_scoped_sprint4_endpoints():
    source = ROUTER.read_text(encoding="utf-8")
    for route in (
        '"/{project_id}/project-manager/generate"',
        '"/{project_id}/project-manager"',
        '"/{project_id}/project-manager/settings"',
        '"/{project_id}/project-manager/backlog"',
        '"/{project_id}/project-manager/replan"',
        '"/{project_id}/project-manager/sprints"',
        '"/{project_id}/project-manager/metrics"',
    ):
        assert route in source
    assert "Project.id == project_id" in source
    assert "Project.user_id == current_user.id" in source


def test_plan_service_persists_versioned_snapshots_and_never_fabricates_actual_metrics():
    source = SERVICE.read_text(encoding="utf-8")
    assert '"schema_version": "project_manager_persistence_v1"' in source
    assert '"history"' in source
    assert "actual_velocity: Optional[float] = None" in (ROOT / "app" / "schemas" / "project_management.py").read_text(encoding="utf-8")
    assert "locked_story_would_move" in source
    assert "ProductOwnerAgent().generate_candidate_backlog" in source
    # Scrum Master advice follows the project output language.
    assert "AIScrumMasterAgent(\n                output_language=context.language,\n            ).generate_advice" in source


def test_project_manager_router_is_registered_in_the_application():
    source = MAIN.read_text(encoding="utf-8")
    assert "project_manager_router" in source
    assert "app.include_router(project_manager_router)" in source
