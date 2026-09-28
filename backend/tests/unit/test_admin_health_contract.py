"""
Sprint 7.7 real health checks contracts.

Observed REDs (audit 28 Sept 2026):
  H1  only PostgreSQL was really tested; Redis, ChromaDB, Gemini, Groq,
      SMTP answered "configuré" as soon as a setting existed (a revoked
      key or a stopped container still looked fine);
  H2  a wrong model name (the cause of the "misconfigured_models"
      pipeline failures) was invisible;
  H3  nothing said that the database migrations were behind the code
      (the "alembic upgrade head" forgotten after a patch), nor that the
      public API (which runs the analyses, 7.6) was down.

Contract: each service is checked for real, concurrently, with a timeout
and a latency; LLM checks list the models (no quota used) and verify every
configured model; results are cached briefly unless a refresh is asked;
no secret ever appears in the answer.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import admin_security
from app.admin_main import app as admin_app
from app.config import settings
from app.database import Base, get_db
from app.models import Project, User, UserRole
from app.security import get_password_hash
from app.security_policy import protect_totp_secret
from app.services import health_checks

PASSWORD = "Admin-Pass-2026!x"
SECRET = pyotp.random_base32()
GEMINI_KEY = "AIza-TEST-GEMINI-SECRET-123"
GROQ_KEY = "gsk_TEST_GROQ_SECRET_456"
CHROMA_TOKEN = "chroma-TEST-TOKEN-789"


def provider_transport(*, gemini_status=200, groq_error=None, public_status=200):
    """Fake network: Gemini, Groq, ChromaDB and the public API."""

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "generativelanguage.googleapis.com":
            # The key must travel in a header, never in the URL (URLs leak in errors/logs).
            assert GEMINI_KEY not in str(request.url)
            assert request.headers.get("x-goog-api-key") == GEMINI_KEY
            if gemini_status != 200:
                return httpx.Response(gemini_status, json={"error": {"message": "API key not valid"}})
            return httpx.Response(200, json={"models": [
                {"name": "models/gemini-3-flash-preview"}, {"name": "models/gemini-2.5-pro"}]})
        if host == "api.groq.com":
            if groq_error:
                raise httpx.ConnectError(f"connection refused for key {GROQ_KEY}")
            assert request.headers["authorization"] == f"Bearer {GROQ_KEY}"
            return httpx.Response(200, json={"data": [{"id": "openai/gpt-oss-120b"}]})
        if host == "chroma.test":
            if request.url.path.endswith("/heartbeat"):
                return httpx.Response(200, json={"nanosecond heartbeat": 1})
            ok = request.headers.get("authorization") == f"Bearer {CHROMA_TOKEN}"
            return httpx.Response(200 if ok else 403, json=[])
        if host == "public.test":
            return httpx.Response(public_status, json={"status": "healthy"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest_asyncio.fixture
async def env(monkeypatch, tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        await conn.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": health_checks.code_migration_heads()[0]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def _db():
        async with sessions() as session:
            yield session

    admin_app.dependency_overrides[get_db] = _db
    admin_security.login_throttle.use_store(admin_security.MemoryStore())

    for name, value in {
        "GEMINI_API_KEY": GEMINI_KEY, "GEMINI_MODEL": "gemini-3-flash-preview",
        "GEMINI_FALLBACK_MODEL": "gemini-2.5-pro", "GEMINI_SEARCH_MODEL": "gemini-3-flash-preview",
        "GROQ_API_KEY": GROQ_KEY, "GROQ_API_BASE": "", "GROQ_MODEL": "openai/gpt-oss-120b",
        "GROQ_FALLBACK_MODEL": "openai/gpt-oss-120b",
        "CHROMA_HOST": "chroma.test", "CHROMA_PORT": 8000, "CHROMA_AUTH_TOKEN": CHROMA_TOKEN,
        "PUBLIC_API_INTERNAL_URL": "http://public.test", "EXPORTS_DIR": str(tmp_path),
        "SMTP_USERNAME": "", "SMTP_PASSWORD": "", "TAVILY_API_KEY": "tvly-TEST-SECRET",
    }.items():
        monkeypatch.setattr(settings, name, value)

    network = {"transport": provider_transport()}
    monkeypatch.setattr(health_checks, "make_http_client",
                        lambda: httpx.AsyncClient(transport=network["transport"], timeout=2))

    async def fake_ping():
        return True

    monkeypatch.setattr(health_checks, "redis_ping", fake_ping)
    health_checks.clear_cache()

    async with sessions() as s:
        s.add(User(email="alice@example.com", full_name="Alice Admin", role=UserRole.ADMIN,
                   hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                   is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)))
        await s.commit()
    yield sessions, network, engine
    admin_app.dependency_overrides.clear()
    health_checks.clear_cache()
    await engine.dispose()


async def health(refresh: bool = True) -> dict:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=admin_app), base_url="http://t") as c:
        r = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD,
                                               "two_factor_code": pyotp.TOTP(SECRET).now()})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        response = await c.get(f"/admin/health{'?refresh=true' if refresh else ''}", headers=h)
    assert response.status_code == 200, response.text
    return response.json()


def by_key(body: dict) -> dict:
    return {service["key"]: service for service in body["services"]}


# H1: real checks ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_every_service_is_really_checked_with_a_latency(env):
    body = await health()
    services = by_key(body)
    assert {"postgres", "migrations", "redis", "chromadb", "public_api", "analysis_queue",
            "gemini", "groq", "smtp", "disk", "tavily", "google_oauth"} <= set(services)
    for key in ("postgres", "redis", "chromadb", "public_api", "gemini", "groq"):
        assert services[key]["status"] == "healthy", services[key]
        assert isinstance(services[key]["latency_ms"], (int, float)), key
    assert services["smtp"]["status"] == "not_configured"
    assert body["overall_status"] == "healthy"
    assert body["checked_at"]


@pytest.mark.asyncio
async def test_a_revoked_key_or_a_stopped_service_is_down(env, monkeypatch):
    _, network, _ = env
    network["transport"] = provider_transport(gemini_status=400, groq_error=True, public_status=503)

    async def dead_ping():
        raise ConnectionError("redis down")

    monkeypatch.setattr(health_checks, "redis_ping", dead_ping)
    services = by_key(await health())
    for key in ("gemini", "groq", "public_api", "redis"):
        assert services[key]["status"] == "down", services[key]
        assert services[key]["message"]
    assert services["groq"]["message"].startswith("Injoignable depuis le serveur")  # plain words, not a class name


@pytest.mark.asyncio
async def test_chromadb_token_is_really_verified(env, monkeypatch):
    monkeypatch.setattr(settings, "CHROMA_AUTH_TOKEN", "wrong-token")
    chroma = by_key(await health())["chromadb"]
    assert chroma["status"] == "down" and "jeton" in chroma["message"].lower()


@pytest.mark.asyncio
async def test_a_check_that_hangs_is_cut_by_the_timeout(env, monkeypatch):
    async def slow_ping():
        await asyncio.sleep(30)

    monkeypatch.setattr(health_checks, "redis_ping", slow_ping)
    monkeypatch.setattr(health_checks, "CHECK_TIMEOUT_SECONDS", 0.2)
    started = asyncio.get_running_loop().time()
    redis = by_key(await health())["redis"]
    assert asyncio.get_running_loop().time() - started < 5
    assert redis["status"] == "down" and "délai" in redis["message"].lower()


# H2: configured models exist --------------------------------------------------------

@pytest.mark.asyncio
async def test_a_configured_model_that_does_not_exist_is_reported(env, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_FALLBACK_MODEL", "qwen/qwen3.8-27b")
    groq = by_key(await health())["groq"]
    assert groq["status"] == "degraded"
    assert groq["details"]["missing_models"] == ["qwen/qwen3.8-27b"]


# H3: migrations and the analysis queue --------------------------------------------

@pytest.mark.asyncio
async def test_migrations_behind_the_code_are_reported(env):
    _, _, engine = env
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE alembic_version SET version_num = '8b24c1a0f3e7'"))
    migrations = by_key(await health())["migrations"]
    assert migrations["status"] == "degraded"
    assert "alembic upgrade head" in migrations["message"]
    assert migrations["details"]["database"] == ["8b24c1a0f3e7"]


@pytest.mark.asyncio
async def test_a_queue_nobody_consumes_and_stuck_runs_are_reported(env):
    sessions, _, _ = env
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    async with sessions() as s:
        s.add_all([
            Project(title="waiting", description="d", user_id=1, analysis_status="queued",
                    analysis_heartbeat_at=old, analysis_enqueued_at=old),
            Project(title="stuck", description="d", user_id=1, analysis_status="running",
                    analysis_heartbeat_at=old),
        ])
        await s.commit()
    queue = by_key(await health())["analysis_queue"]
    assert queue["status"] == "degraded"
    assert queue["details"] == {"waiting_over_60s": 1, "stalled": 2}


# Safety and cost ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_secret_ever_appears_in_the_answer(env):
    _, network, _ = env
    network["transport"] = provider_transport(gemini_status=401, groq_error=True)
    raw = json.dumps(await health())
    for secret in (GEMINI_KEY, GROQ_KEY, CHROMA_TOKEN, "tvly-TEST-SECRET"):
        assert secret not in raw


@pytest.mark.asyncio
async def test_results_are_cached_unless_a_refresh_is_asked(env, monkeypatch):
    calls = []

    async def counting_ping():
        calls.append(1)
        return True

    monkeypatch.setattr(health_checks, "redis_ping", counting_ping)
    first = await health(refresh=False)
    second = await health(refresh=False)
    assert len(calls) == 1 and first["checked_at"] == second["checked_at"]
    await health(refresh=True)
    assert len(calls) == 2
