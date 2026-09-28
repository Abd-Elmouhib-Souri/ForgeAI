"""
Sprint 7.4 admin lists contracts (server-side pagination, light queries).

Observed REDs (measured 28 Sept 2026, real PostgreSQL, 300 accounts /
600 projects with ~45 KB of analysis each):
  D1  /admin/users, /admin/projects, /admin/analyses and /admin/errors
      returned EVERY row (305 / 601 / 532 / 65) and the console filtered,
      searched and counted in the browser;
  D2  the project-based lists read the heavy JSON columns (analysis_data,
      clarification_context) for every row: /admin/projects = 489 KB and
      247 ms, ~18 MB transferred from the database for a table that shows
      none of it;
  D3  /admin/stats ran 13 SQL queries (+1 for the session);
  D4  no export of the users / projects lists.

Contract: every list answers {items, total, page, page_size} with
search / filters / whitelisted sort done in SQL, never selects the heavy
columns, runs a constant number of queries, and has a CSV twin.
"""

from __future__ import annotations

import csv
import io

import httpx
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import admin_security
from app.admin_main import app as admin_app
from app.database import Base, get_db
from app.models import Project, User, UserRole
from app.security import get_password_hash
from app.security_policy import protect_totp_secret

PASSWORD = "Admin-Pass-2026!x"
SECRET = pyotp.random_base32()
BIG = {"sections": [{"text": "x" * 400} for _ in range(50)]}
HEAVY_COLUMNS = ("analysis_data", "clarification_context")
STATUSES = ["completed", "completed", "failed", "running", "not_started", "needs_clarification"]


@pytest_asyncio.fixture
async def env():
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
    admin_security.login_throttle.use_store(admin_security.MemoryStore())

    async with sessions() as s:
        s.add(User(email="alice@example.com", full_name="Alice Admin", role=UserRole.ADMIN,
                   hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                   is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)))
        clients = []
        for i in range(30):
            clients.append(User(
                email=f"client{i:02d}@perf.example.com", full_name=f"Client {i:02d}",
                role=[UserRole.ENTREPRENEUR, UserRole.STUDENT, UserRole.CONSULTANT][i % 3],
                hashed_password="x", is_active=i % 10 != 0, is_email_verified=i % 4 != 0,
            ))
        # A literal "%" in a name: search must not treat it as a wildcard.
        clients.append(User(email="percent@perf.example.com", full_name="Cent % Pour", role=UserRole.STUDENT,
                            hashed_password="x", is_active=True, is_email_verified=True))
        s.add_all(clients)
        await s.flush()
        for i in range(60):
            status = STATUSES[i % len(STATUSES)]
            s.add(Project(
                title=f"Projet {i:02d}", description="Longue description " * 50,
                user_id=clients[i % 30].id,
                industry=["retail", "fintech", "santé"][i % 3], market_region=["Tunisie", "France"][i % 2],
                analysis_status=status, startup_score=40 + i if status == "completed" else None,
                analysis_error="Timeout fournisseur" if status == "failed" else None,
                analysis_data=BIG if status in ("completed", "failed") else None,
                clarification_context={"answers": ["y" * 500]},
            ))
        await s.commit()

    statements: list[str] = []

    def _record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _record)
    yield statements
    event.remove(engine.sync_engine, "before_cursor_execute", _record)
    admin_app.dependency_overrides.clear()
    await engine.dispose()


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=admin_app), base_url="http://test")


async def headers(c) -> dict:
    r = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD,
                                           "two_factor_code": pyotp.TOTP(SECRET).now()})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def measured(c, statements, path, h):
    """GET path; return (json, number of SQL statements of the route itself)."""
    statements.clear()
    r = await c.get(path, headers=h)
    assert r.status_code == 200, (path, r.text)
    # The first statement is the session check (admin lookup) of every route.
    return r.json(), statements[1:]


def assert_page(body, *, total=None, size=None):
    assert set(body) >= {"items", "total", "page", "page_size"}, body.keys()
    if total is not None:
        assert body["total"] == total
    if size is not None:
        assert len(body["items"]) == size


# D1 users ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_users_list_is_paginated_filtered_and_sorted_by_the_server(env):
    async with client() as c:
        h = await headers(c)
        body, sql = await measured(c, env, "/admin/users", h)
        assert_page(body, total=32, size=25)  # 31 clients + alice, default page of 25
        assert body["page"] == 1 and body["page_size"] == 25
        assert "project_count" in body["items"][0]
        assert len(sql) <= 2  # count + page, whatever the number of rows

        body = (await c.get("/admin/users?page=2&page_size=25", headers=h)).json()
        assert_page(body, total=32, size=7)

        body = (await c.get("/admin/users?search=CLIENT0&sort=email&order=asc", headers=h)).json()
        assert [u["email"] for u in body["items"]][:2] == ["client00@perf.example.com", "client01@perf.example.com"]
        assert body["total"] == 10

        assert (await c.get("/admin/users?status=inactive", headers=h)).json()["total"] == 3
        assert (await c.get("/admin/users?verified=false", headers=h)).json()["total"] == 8
        assert (await c.get("/admin/users?role=admin", headers=h)).json()["total"] == 1

        # "%" is a character, not a wildcard.
        assert (await c.get("/admin/users?search=%25", headers=h)).json()["total"] == 1

        top = (await c.get("/admin/users?sort=project_count&order=desc&page_size=1", headers=h)).json()
        assert top["items"][0]["project_count"] == 2

        assert (await c.get("/admin/users?page_size=101", headers=h)).status_code == 422
        assert (await c.get("/admin/users?sort=hashed_password", headers=h)).status_code == 422


# D1 + D2 projects / analyses / errors --------------------------------------------

@pytest.mark.asyncio
async def test_projects_list_is_paginated_and_never_reads_heavy_columns(env):
    async with client() as c:
        h = await headers(c)
        body, sql = await measured(c, env, "/admin/projects", h)
        assert_page(body, total=60, size=25)
        assert len(sql) <= 2
        assert not any(col in s for s in sql for col in HEAVY_COLUMNS), sql
        item = body["items"][0]
        assert {"id", "title", "owner_email", "analysis_status", "startup_score", "created_at"} <= set(item)
        assert not set(item) & {"analysis_data", "clarification_context", "description"}
        assert 0 < len(item["description_excerpt"]) <= 160  # cut in SQL, not the full text

        found = (await c.get("/admin/projects?search=client03@perf", headers=h)).json()
        assert found["total"] == 2  # owner e-mail is searchable

        failed = (await c.get("/admin/projects?status=failed", headers=h)).json()
        assert failed["total"] == 10 and {p["analysis_status"] for p in failed["items"]} == {"failed"}

        best = (await c.get("/admin/projects?sort=startup_score&order=desc&page_size=1", headers=h)).json()
        assert best["items"][0]["startup_score"] == 40 + 55  # project 55, last "completed"


@pytest.mark.asyncio
async def test_analyses_and_errors_lists_are_paginated_and_light(env):
    async with client() as c:
        h = await headers(c)
        body, sql = await measured(c, env, "/admin/analyses", h)
        assert_page(body, total=50)  # every project except the 10 "not_started"
        assert not any(col in s for s in sql for col in HEAVY_COLUMNS), sql
        assert len(sql) <= 2
        running = (await c.get("/admin/analyses?status=running", headers=h)).json()
        assert running["total"] == 10

        body, sql = await measured(c, env, "/admin/errors", h)
        assert_page(body, total=10)
        assert not any(col in s for s in sql for col in HEAVY_COLUMNS), sql
        assert len(sql) <= 2


# D3 stats -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_use_a_constant_small_number_of_queries(env):
    async with client() as c:
        h = await headers(c)
        body, sql = await measured(c, env, "/admin/stats", h)
    assert len(sql) <= 3, f"{len(sql)} queries"  # counters + top sectors + top regions
    assert body["users"] == {"total": 32, "active": 29, "inactive": 3, "verified": 24,
                             "unverified": 8, "admins": 1}
    assert body["projects"]["total"] == 60
    assert body["analyses"]["total"] == 50  # started at least once
    assert body["analyses"]["completed"] == 20 and body["analyses"]["failed"] == 10
    assert body["analyses"]["running"] == 10 and body["analyses"]["with_errors"] == 10


# D4 CSV exports -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_users_and_projects_csv_follow_the_screen_filters(env):
    async with client() as c:
        h = await headers(c)
        users = await c.get("/admin/users/export.csv?status=inactive", headers=h)
        projects = await c.get("/admin/projects/export.csv?status=failed", headers=h)
    for response in (users, projects):
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]
    user_rows = list(csv.reader(io.StringIO(users.content.decode("utf-8-sig")), delimiter=";"))
    assert user_rows[0][:4] == ["E-mail", "Nom", "Rôle", "Statut"]
    assert len(user_rows) == 1 + 3
    assert {row[3] for row in user_rows[1:]} == {"Désactivé"}
    project_rows = list(csv.reader(io.StringIO(projects.content.decode("utf-8-sig")), delimiter=";"))
    assert project_rows[0][:3] == ["Projet", "Propriétaire", "Statut de l'analyse"]
    assert len(project_rows) == 1 + 10
    assert {row[2] for row in project_rows[1:]} == {"Échouée"}


def test_list_routes_stay_read_only():
    for route in admin_app.routes:
        path = getattr(route, "path", "")
        if path.endswith("/export.csv"):
            assert route.methods <= {"GET", "HEAD"}, path
