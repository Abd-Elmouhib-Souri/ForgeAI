"""
Sprint 7.6 analysis relaunch contracts (admin -> database queue -> public API).

Observed REDs (audit 28 Sept 2026):
  F1  no admin action could relaunch an analysis (failed or stuck);
  F2  an analysis interrupted by a restart stayed "running"/"queued" forever:
      analysis_heartbeat_at was written but never read, and the owner's own
      /analyze/start answered 409 for good;
  F3  set_analysis_progress wrote progress without refreshing the heartbeat.

Decision (user, 28 Sept 2026): the admin API only ENQUEUES (in the database,
audited); the public API is the only process that runs analyses. A worker
of the public API claims each queued run exactly once.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.routers.projects as projects_router
from app import admin_security
from app.admin_main import app as admin_app
from app.config import settings
from app.database import Base, get_db
from app.main import app as public_app
from app.models import AdminAuditLog, Project, User, UserRole
from app.security import create_access_token, get_password_hash
from app.security_policy import protect_totp_secret
from app.services import analysis_queue

BACKEND = Path(__file__).resolve().parents[2]
PASSWORD = "Admin-Pass-2026!x"
SECRET = pyotp.random_base32()
NOW = datetime.now(timezone.utc)
OLD = NOW - timedelta(hours=2)
PM = {"project_manager": {"plan": "kept"}}


@pytest_asyncio.fixture
async def env(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def _db():
        async with sessions() as session:
            yield session

    admin_app.dependency_overrides[get_db] = _db
    public_app.dependency_overrides[get_db] = _db
    admin_security.login_throttle.use_store(admin_security.MemoryStore())

    # No real analysis in tests: record who tries to run one, and where.
    runs: list[tuple[int, str]] = []

    async def fake_run(project_id: int, run_id: str) -> None:
        runs.append((project_id, run_id))

    monkeypatch.setattr(projects_router, "run_project_analysis_background", fake_run)

    async with sessions() as s:
        s.add(User(email="alice@example.com", full_name="Alice Admin", role=UserRole.ADMIN,
                   hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                   is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)))
        owner = User(email="owner@example.com", full_name="Olivia Owner", role=UserRole.ENTREPRENEUR,
                     hashed_password="x", is_active=True, is_email_verified=True)
        s.add(owner)
        await s.flush()

        def project(title, status, heartbeat, **extra):
            return Project(title=title, description="d", user_id=owner.id, analysis_status=status,
                           analysis_run_id=f"old-{title}", analysis_heartbeat_at=heartbeat,
                           analysis_attempt=1, analysis_data=dict(PM), **extra)

        s.add_all([
            project("failed", "failed", OLD, analysis_error="Timeout fournisseur"),
            project("fresh", "running", NOW),
            project("stuck", "running", OLD),
            project("stuck-queue", "queued", None),
            project("never", "not_started", None),
            # Finished runs carry their end date, like on a real database.
            project("done", "completed", OLD, startup_score=80, analysis_completed_at=OLD),
            project("recent", "completed", NOW, startup_score=70, analysis_completed_at=NOW),
        ])
        await s.commit()

    yield sessions, runs
    admin_app.dependency_overrides.clear()
    public_app.dependency_overrides.clear()
    await engine.dispose()


def client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def admin_headers(c, code: bool = True) -> dict:
    r = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD,
                                           "two_factor_code": pyotp.TOTP(SECRET).now()})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if code:
        h["X-Admin-Confirmation"] = pyotp.TOTP(SECRET).now()
    return h


async def project(sessions, title) -> Project:
    async with sessions() as s:
        return (await s.execute(select(Project).where(Project.title == title))).scalar_one()


async def audit(sessions) -> list[AdminAuditLog]:
    async with sessions() as s:
        return list((await s.execute(
            select(AdminAuditLog).where(AdminAuditLog.action == "analysis.relaunch").order_by(AdminAuditLog.id)
        )).scalars())


# F1: admin relaunch = enqueue only -------------------------------------------------

@pytest.mark.asyncio
async def test_relaunch_is_a_confirmed_admin_action(env):
    sessions, _ = env
    failed = await project(sessions, "failed")
    async with client(admin_app) as c:
        assert (await c.post(f"/admin/analyses/{failed.id}/relaunch")).status_code == 401
        h = await admin_headers(c, code=False)
        assert (await c.post(f"/admin/analyses/{failed.id}/relaunch", headers=h)).status_code == 428


@pytest.mark.asyncio
async def test_relaunch_enqueues_a_new_run_and_never_runs_it_in_the_admin_process(env):
    sessions, runs = env
    before = await project(sessions, "failed")
    async with client(admin_app) as c:
        r = await c.post(f"/admin/analyses/{before.id}/relaunch", headers=await admin_headers(c))
    assert r.status_code == 202, r.text
    after = await project(sessions, "failed")
    assert after.analysis_status == "queued"
    assert after.analysis_run_id and after.analysis_run_id != before.analysis_run_id
    assert after.analysis_attempt == before.analysis_attempt + 1
    assert after.analysis_enqueued_at is not None
    assert after.analysis_error is None
    assert "administrateur" in after.analysis_step
    assert after.analysis_data == PM  # same reset as the owner's start: the plan is kept
    assert runs == []  # the admin process never executes an analysis

    [entry] = await audit(sessions)
    assert entry.result == "success" and entry.actor_email == "alice@example.com"
    assert (entry.target_type, entry.target_id, entry.target_label) == ("project", str(before.id), "failed")
    assert entry.before["analysis_status"] == "failed" and entry.after["analysis_status"] == "queued"


@pytest.mark.asyncio
async def test_a_live_analysis_or_a_never_started_one_cannot_be_relaunched(env):
    sessions, _ = env
    fresh = await project(sessions, "fresh")
    never = await project(sessions, "never")
    async with client(admin_app) as c:
        h = await admin_headers(c)
        live = await c.post(f"/admin/analyses/{fresh.id}/relaunch", headers=h)
        first = await c.post(f"/admin/analyses/{never.id}/relaunch", headers={**h, "X-Admin-Confirmation": pyotp.TOTP(SECRET).now()})
    assert live.status_code == 409 and first.status_code == 409
    assert (await project(sessions, "fresh")).analysis_run_id == "old-fresh"  # untouched
    assert [(e.result, e.detail) for e in await audit(sessions)] == [
        ("denied", "analysis_active"), ("denied", "never_started")]


# F2: stuck runs are detected and can be restarted -----------------------------------

@pytest.mark.asyncio
async def test_stuck_runs_are_flagged_and_can_be_relaunched(env):
    sessions, _ = env
    async with client(admin_app) as c:
        h = await admin_headers(c)
        listing = (await c.get("/admin/analyses?page_size=100", headers=h)).json()
        stalled = {row["title"]: row["analysis_stalled"] for row in listing["items"]}
        assert stalled["stuck"] is True and stalled["stuck-queue"] is True
        assert stalled["fresh"] is False and stalled["failed"] is False

        stuck = await project(sessions, "stuck")
        detail = (await c.get(f"/admin/analyses/{stuck.id}", headers=h)).json()
        assert detail["analysis_stalled"] is True
        assert set(detail["pipeline"]["stages"]) == {"project_manager", "solution_architecture"}

        r = await c.post(f"/admin/analyses/{stuck.id}/relaunch", headers=h)
    assert r.status_code == 202
    assert (await project(sessions, "stuck")).analysis_run_id != "old-stuck"


@pytest.mark.asyncio
async def test_owner_can_restart_a_stuck_analysis_but_not_a_live_one(env):
    sessions, runs = env
    token = create_access_token({"sub": "owner@example.com"})
    h = {"Authorization": f"Bearer {token}"}
    stuck = await project(sessions, "stuck-queue")
    fresh = await project(sessions, "fresh")
    async with client(public_app) as c:
        assert (await c.post(f"/projects/{fresh.id}/analyze/start", headers=h)).status_code == 409
        r = await c.post(f"/projects/{stuck.id}/analyze/start", headers=h)
    assert r.status_code == 202, r.text
    restarted = await project(sessions, "stuck-queue")
    assert restarted.analysis_run_id != "old-stuck-queue"
    assert restarted.analysis_enqueued_at is None  # the owner's start runs directly, not via the queue
    assert runs == [(stuck.id, restarted.analysis_run_id)]


# The worker of the public API ------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_claims_each_queued_run_exactly_once(env):
    sessions, _ = env
    failed = await project(sessions, "failed")
    async with client(admin_app) as c:
        await c.post(f"/admin/analyses/{failed.id}/relaunch", headers=await admin_headers(c))
    queued = await project(sessions, "failed")

    started: list[tuple[int, str]] = []

    async def launch(project_id: int, run_id: str) -> None:
        started.append((project_id, run_id))

    # Two workers polling at the same time (two public API processes).
    counts = await asyncio.gather(
        analysis_queue.claim_and_start(sessions, launch),
        analysis_queue.claim_and_start(sessions, launch),
    )
    await asyncio.sleep(0)
    assert sum(counts) == 1
    assert started == [(queued.id, queued.analysis_run_id)]
    assert (await project(sessions, "failed")).analysis_enqueued_at is None
    assert await analysis_queue.claim_and_start(sessions, launch) == 0  # nothing left


def test_worker_runs_in_the_public_api_only():
    main = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    admin_main = (BACKEND / "app" / "admin_main.py").read_text(encoding="utf-8")
    assert "analysis_queue_worker.start()" in main and "analysis_queue_worker.stop()" in main
    assert "analysis_queue" not in admin_main
    assert settings.ANALYSIS_STALE_AFTER_SECONDS >= 600
    assert 1 <= settings.ANALYSIS_QUEUE_POLL_SECONDS <= 30


def test_migration_adds_the_queue_column():
    [migration] = list((BACKEND / "migrations" / "versions").glob("*analysis_enqueued_at*.py"))
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision: Union[str, None] = "d7a3c9e1f2b4"' in source
    assert "analysis_enqueued_at" in source


# F3: progress is a sign of life ---------------------------------------------------

@pytest.mark.asyncio
async def test_progress_writes_refresh_the_heartbeat():
    class FakeDb:
        async def commit(self):
            return None

    p = Project(title="t", description="d", user_id=1, analysis_heartbeat_at=OLD)
    await projects_router.set_analysis_progress(db=FakeDb(), project=p, step="Étape", progress=40)
    assert p.analysis_heartbeat_at > OLD


# RED 28 Sept 2026 (user's screenshot): the relaunched analysis vanished at the
# END of the list (default sort = end date, NULLs last, and a relaunch clears it).

@pytest.mark.asyncio
async def test_a_relaunched_analysis_comes_first_in_the_default_list(env):
    sessions, _ = env
    done = await project(sessions, "done")
    async with client(admin_app) as c:
        h = await admin_headers(c)
        assert (await c.post(f"/admin/analyses/{done.id}/relaunch", headers=h)).status_code == 202
        first = (await c.get("/admin/analyses", headers=h)).json()["items"][0]
    # Default order = last activity (end of a finished run, start of a live one).
    assert first["title"] == "done" and first["analysis_status"] == "queued"
