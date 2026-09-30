"""
Sprint 7.8 readable analysis diagnostic contracts.

Observed REDs (audit 29 Sept 2026, real analysis of project 30):
  D1  steps were raw English keys ("idea_readiness_check",
      "business_model_canvas") in two flat lists; a step that silently used
      its fallback answer ("fallback_used") looked exactly like a success;
  D2  nothing said in one line whether the run was fine, degraded or failed;
  D3  sources and confidence were raw codes ("completed", "low");
  D4  the "queries" panel listed 40 lines for 9 distinct queries; errors
      were a blind recursive dump of every "error" key, not attributed to
      a step, and an exception text could carry a provider key;
  D5  the page suggested nothing about models or step durations, which the
      analysis does not record: the admin must be told, not left guessing.

Contract: the backend decides everything (order, status, wording); the
page only displays. The raw analysis_data stays available.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import admin_security
from app.admin_main import app as admin_app
from app.config import settings
from app.database import Base, get_db
from app.models import Project, User, UserRole
from app.security import get_password_hash
from app.security_policy import protect_totp_secret
from app.services import analysis_diagnostics

PASSWORD = "Admin-Pass-2026!x"
SECRET = pyotp.random_base32()
GEMINI_KEY = "AIza-TEST-GEMINI-SECRET-123"
STARTED = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)

ALL_STEPS = [
    "idea_readiness_check", "project_intelligence_layer", "competitive_analysis", "market_study",
    "swot", "business_model_canvas", "financial_estimation", "persona_builder", "fact_checker",
    "startup_score",
]


def realistic_data(**meta) -> dict:
    """Trimmed copy of the real structure (project 30), no business content."""
    ok = {"status": "completed", "fallback_used": False, "error_handled": False}
    return {
        "idea_readiness": {"status": "ready"},
        "project_intelligence": {"status": "completed"},
        "competitive_analysis": {"status": "completed"},
        "market_study": dict(ok),
        "swot": dict(ok),
        "business_model_canvas": dict(ok),
        "financial_estimation": dict(ok),
        "persona_builder": dict(ok),
        "startup_score": {**ok, "score": 7.0, "verdict_code": "CONDITIONAL_GO"},
        "fact_check_report": {"status": "completed", "error_handled": False,
                              "claim_coverage": {"total": 14, "sourced": 2, "estimated": 10}},
        "forgecrawler": {
            "status": "completed", "confidence_level": "low", "sources_count": 8,
            "local_sources_count": 5, "regional_sources_count": 0, "international_sources_count": 3,
            "local_competitors_count": 1, "market_sources_count": 2,
            "source_quality": {"rejected_sources_count": 4, "removed_from_public_after_safety_filter": 3},
            "no_verified_relevant_source_found": False,
        },
        "overall_evidence_confidence": "low",
        "verdict_code": "conditional_go",
        "query_planner": {"queries": ["artisan maroc", "Artisan Maroc ", "plombier casablanca"]},
        "local_market_candidates": [{"query": "artisan maroc"}, {"search_query": "réparation domicile"}],
        "debate_room": {"meta": {"completed": True, "progress": 100}},
        "startup_evaluator_meta": {
            "completed_steps": list(ALL_STEPS), "failed_steps": [], "current_step": "startup_score",
            "progress": 100, "error": None, "fact_checker_fallback_used": False,
            "fact_checker_error_handled": False, **meta,
        },
    }


def project(**fields) -> Project:
    values = {"id": 30, "title": "RepairLink", "description": "d", "user_id": 1,
              "analysis_status": "completed", "analysis_progress": 100,
              "analysis_started_at": STARTED, "analysis_completed_at": STARTED + timedelta(minutes=6, seconds=5),
              "analysis_data": realistic_data()}
    values.update(fields)
    return Project(**values)


def steps(diag: dict) -> dict:
    return {step["key"]: step for step in diag["steps"]}


# D1: steps -------------------------------------------------------------------------

def test_steps_follow_the_pipeline_order_with_french_labels():
    diag = analysis_diagnostics.build(project())
    assert [s["key"] for s in diag["steps"]] == [*ALL_STEPS, "debate_room"]
    labels = {s["key"]: s["label"] for s in diag["steps"]}
    assert labels["idea_readiness_check"] == "Vérification de la maturité de l'idée"
    assert labels["business_model_canvas"] == "Business Model Canvas"
    assert labels["fact_checker"] == "Vérification des faits"
    assert labels["debate_room"] == "Salle de débat"
    for step in diag["steps"]:
        assert (step["status"], step["status_label"]) == ("completed", "Réussie"), step


def test_a_step_that_used_its_fallback_is_not_shown_as_a_plain_success():
    data = realistic_data(fact_checker_fallback_used=True)
    data["swot"]["fallback_used"] = True
    data["financial_estimation"]["error_handled"] = True
    by_key = steps(analysis_diagnostics.build(project(analysis_data=data)))
    for key in ("swot", "financial_estimation", "fact_checker"):
        assert by_key[key]["status"] == "degraded", key
        assert by_key[key]["status_label"] == "Réussie avec repli"
    assert "Réponse de secours utilisée" in by_key["swot"]["notes"]
    assert "Erreur rattrapée pendant l'étape" in by_key["financial_estimation"]["notes"]


def test_failed_and_never_run_steps():
    data = realistic_data(
        completed_steps=ALL_STEPS[:3], failed_steps=["market_study"], current_step="market_study",
        error="market_study failed: 429 quota exceeded",
    )
    data["debate_room"] = {}
    by_key = steps(analysis_diagnostics.build(project(analysis_status="failed", analysis_data=data)))
    assert by_key["market_study"]["status"] == "failed"
    assert by_key["market_study"]["status_label"] == "Échouée"
    assert by_key["market_study"]["error"] == "429 quota exceeded"  # step prefix removed, attributed
    assert by_key["swot"]["status"] == "not_run" and by_key["swot"]["status_label"] == "Non exécutée"
    assert by_key["debate_room"]["status"] == "not_run"


def test_the_current_step_of_a_running_analysis():
    data = realistic_data(completed_steps=ALL_STEPS[:4], current_step="swot", progress=40)
    data["debate_room"] = {}
    diag = analysis_diagnostics.build(project(analysis_status="running", analysis_completed_at=None,
                                              analysis_data=data))
    assert steps(diag)["swot"]["status"] == "running"
    assert steps(diag)["swot"]["status_label"] == "En cours"
    assert steps(diag)["business_model_canvas"]["status"] == "not_run"
    assert diag["summary"]["level"] == "running"


# D2: one-line summary -------------------------------------------------------------

def test_summary_levels_and_duration():
    clean = analysis_diagnostics.build(project())["summary"]
    assert clean == {**clean, "level": "ok", "steps_done": 11, "steps_total": 11, "duration_seconds": 365}
    assert clean["headline"] == "Analyse terminée sans incident"

    data = realistic_data()
    data["swot"]["fallback_used"] = True
    degraded = analysis_diagnostics.build(project(analysis_data=data))["summary"]
    assert degraded["level"] == "warning"
    assert degraded["headline"] == "Analyse terminée avec 1 étape en repli"

    data = realistic_data(failed_steps=["market_study"], completed_steps=ALL_STEPS[:3], error="market_study failed: x")
    failed = analysis_diagnostics.build(project(analysis_status="failed", analysis_data=data))["summary"]
    assert failed["level"] == "error"
    assert failed["headline"] == "Analyse en échec à l'étape « Étude de marché »"


def test_a_project_that_was_never_analysed_does_not_crash():
    for data in (None, {}, "garbage", {"startup_evaluator_meta": "x", "forgecrawler": [1]}):
        diag = analysis_diagnostics.build(project(analysis_status="not_started", analysis_data=data,
                                                  analysis_started_at=None, analysis_completed_at=None))
        assert diag["summary"]["level"] == "not_started"
        assert diag["summary"]["headline"] == "Aucune analyse lancée"
        assert diag["summary"]["duration_seconds"] is None
        assert all(s["status"] == "not_run" for s in diag["steps"])


# D3: sources and evidence ------------------------------------------------------------

def test_sources_and_evidence_are_summarised_in_french():
    diag = analysis_diagnostics.build(project())
    assert diag["sources"] == {
        "status_label": "Terminée", "confidence_label": "Faible",
        "total": 8, "local": 5, "regional": 0, "international": 3,
        "local_competitors": 1, "market": 2, "rejected": 4, "removed_by_safety_filter": 3,
        "no_relevant_source": False,
    }
    assert diag["evidence"] == {
        "overall_label": "Faible", "verdict_label": "Go sous conditions", "score": 7.0,
        "claims_total": 14, "claims_sourced": 2, "claims_estimated": 10,
    }


# D4: errors and queries --------------------------------------------------------------

def test_errors_are_attributed_deduplicated_and_never_leak_a_secret(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", GEMINI_KEY)
    data = realistic_data(failed_steps=["swot"], completed_steps=ALL_STEPS[:5],
                          error=f"swot failed: 403 for key {GEMINI_KEY}")
    data["forgecrawler"]["errors"] = ["ddgs timeout", "ddgs timeout", "  "]
    diag = analysis_diagnostics.build(project(analysis_status="failed", analysis_data=data))
    assert {"where": "SWOT", "message": "403 for key ***"} in diag["errors"]
    assert diag["errors"].count({"where": "Recherche de sources", "message": "ddgs timeout"}) == 1
    assert GEMINI_KEY not in str(diag)


def test_queries_are_deduplicated_but_the_total_is_kept():
    queries = analysis_diagnostics.build(project())["queries"]
    assert queries["total"] == 5
    assert queries["unique"] == ["artisan maroc", "plombier casablanca", "réparation domicile"]


# D5: honest about what is not recorded ------------------------------------------------

def test_what_the_analysis_does_not_record_is_said():
    assert analysis_diagnostics.build(project())["not_recorded"] == [
        "Modèle d'IA utilisé à chaque étape",
        "Durée de chaque étape",
    ]


# HTTP: served by the detail route, raw data kept -------------------------------------

@pytest_asyncio.fixture
async def sessions():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _db():
        async with maker() as session:
            yield session

    admin_app.dependency_overrides[get_db] = _db
    admin_security.login_throttle.use_store(admin_security.MemoryStore())
    async with maker() as s:
        s.add(User(id=1, email="alice@example.com", full_name="Alice Admin", role=UserRole.ADMIN,
                   hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                   is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)))
        s.add(project())
        await s.commit()
    yield maker
    admin_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_the_detail_route_serves_the_readable_diagnostic_and_the_raw_data(sessions):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=admin_app), base_url="http://t") as c:
        r = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD,
                                               "two_factor_code": pyotp.TOTP(SECRET).now()})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        detail = await c.get("/admin/analyses/30", headers=h)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["diagnostics"]["summary"]["level"] == "ok"
    assert len(body["diagnostics"]["steps"]) == 11
    assert body["analysis_data"]["forgecrawler"]["sources_count"] == 8  # raw JSON still there
