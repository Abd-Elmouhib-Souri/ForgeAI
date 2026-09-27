"""
Sprint 7.1 admin security contracts.

Observed REDs (audit 27 Sept 2026):
  A1  /admin/* routes were served by the PUBLIC API (port 8000).
  A2  2FA bypass: an admin logged in through /auth/login and renewed the
      token with /auth/refresh, without any TOTP code; admin and user tokens
      were identical ({"sub": email}).
  A3  2FA was optional for admins; with 2FA on and no code, /admin/login
      returned 200 with an empty token.
  A4  No attempt limit on the admin password / TOTP.
  A5  Role change, (de)activation, deletion and admin creation needed no
      confirmation; created admins only needed an 8-character password.
  A6  Broken strings: "Compte d?sactiv?.", "Adresse email non v?rifi?e.".

The admin API is exercised for real (httpx -> ASGI app) on an in-memory
SQLite database with the real models, real bcrypt hashes and real TOTP.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import jwt
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import admin_security
from app.admin_main import app as admin_app
from app.config import settings
from app.database import Base, get_db
from app.main import app as public_app
from app.models import User, UserRole
from app.security import create_access_token, get_password_hash
from app.security_policy import protect_totp_secret

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
PASSWORD = "Admin-Pass-2026!x"
SECRET = pyotp.random_base32()


@pytest_asyncio.fixture
async def db_env():
    """Real models on in-memory SQLite, shared by both apps."""
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

    async with sessions() as session:
        session.add_all([
            User(email="alice@example.com", full_name="Alice Admin", role=UserRole.ADMIN,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                 is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)),
            User(email="nora@example.com", full_name="Nora New Admin", role=UserRole.ADMIN,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True),
            User(email="user@example.com", full_name="Uma User", role=UserRole.ENTREPRENEUR,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True),
        ])
        await session.commit()
    yield sessions
    admin_app.dependency_overrides.clear()
    public_app.dependency_overrides.clear()
    await engine.dispose()


def client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def admin_token(c: httpx.AsyncClient) -> str:
    response = await c.post("/admin/login", json={
        "email": "alice@example.com", "password": PASSWORD, "two_factor_code": pyotp.TOTP(SECRET).now()})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str, code: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if code is not None:
        headers["X-Admin-Confirmation"] = code
    return headers


async def user_id(sessions, email: str) -> int:
    from sqlalchemy import select

    async with sessions() as session:
        return (await session.execute(select(User.id).where(User.email == email))).scalar_one()


# A1: separation -----------------------------------------------------------------

def test_public_api_exposes_no_admin_route():
    paths = {getattr(route, "path", "") for route in public_app.routes}
    assert not any(p.startswith("/admin") for p in paths), sorted(p for p in paths if "admin" in p)


def test_admin_api_exposes_only_admin_routes():
    paths = {getattr(route, "path", "") for route in admin_app.routes}
    business = {p for p in paths if not p.startswith(("/admin", "/health", "/docs", "/openapi", "/redoc"))}
    assert business == set(), business
    assert "/admin/stats" in paths


def test_admin_service_is_published_on_localhost_only():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "backend-admin:" in compose
    assert "app.admin_main:app" in compose
    assert '"127.0.0.1:${ADMIN_API_PORT:-8002}:8002"' in compose
    assert "--port 8002" in compose


def test_no_two_services_publish_the_same_host_port():
    # RED 27 Sept 2026: the admin API was put on host port 8001, already
    # published by ChromaDB ("8001:8000"): Docker refused to start it.
    import re

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    host_ports = []
    for mapping in re.findall(r'^\s*-\s*"([^"]+:\d+)"\s*$', compose, flags=re.M):
        parts = mapping.split(":")
        host = parts[-2]
        # Resolve ${VAR:-default} to its default for the comparison.
        default = re.search(r"\$\{[A-Z_]+:-(\d+)\}", mapping)
        host_ports.append(default.group(1) if default else host)
    assert len(host_ports) == len(set(host_ports)), host_ports


# A2: distinct tokens --------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_token_is_refused_by_the_admin_api(db_env):
    token = create_access_token({"sub": "alice@example.com"})  # what /auth/login issues
    async with client(admin_app) as c:
        assert (await c.get("/admin/stats", headers=auth(token))).status_code == 401


@pytest.mark.asyncio
async def test_admin_token_is_refused_by_the_public_api(db_env):
    async with client(admin_app) as c:
        token = await admin_token(c)
    async with client(public_app) as c:
        assert (await c.get("/projects", headers=auth(token))).status_code == 401


@pytest.mark.asyncio
async def test_admin_token_is_short_lived_scoped_and_sets_no_refresh_cookie(db_env):
    async with client(admin_app) as c:
        response = await c.post("/admin/login", json={
            "email": "alice@example.com", "password": PASSWORD, "two_factor_code": pyotp.TOTP(SECRET).now()})
    claims = jwt.decode(response.json()["access_token"], options={"verify_signature": False})
    assert claims["aud"] == admin_security.ADMIN_AUDIENCE
    assert claims["exp"] - claims["iat"] <= 15 * 60
    assert "set-cookie" not in response.headers


# A3: mandatory 2FA -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_or_wrong_totp_gets_no_token(db_env):
    async with client(admin_app) as c:
        missing = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD})
        wrong = await c.post("/admin/login", json={
            "email": "alice@example.com", "password": PASSWORD, "two_factor_code": "000000"})
    assert missing.status_code == 401 and missing.json()["detail"]["reason"] == "totp_required"
    assert wrong.status_code == 401 and wrong.json()["detail"]["reason"] == "totp_invalid"
    assert "access_token" not in missing.text and "access_token" not in wrong.text


@pytest.mark.asyncio
async def test_admin_without_2fa_must_enrol_before_any_access(db_env):
    async with client(admin_app) as c:
        first = await c.post("/admin/login", json={"email": "nora@example.com", "password": PASSWORD})
        assert first.status_code == 200
        body = first.json()
        assert body["requires_2fa_setup"] is True and not body.get("access_token")
        enrolment = body["enrollment_token"]
        # The enrolment token opens nothing but the 2FA setup.
        assert (await c.get("/admin/stats", headers=auth(enrolment))).status_code == 401

        setup = await c.post("/admin/2fa/setup", headers=auth(enrolment))
        assert setup.status_code == 200
        svg = setup.json()["qr_svg"]
        # viewBox only: the QR must scale to its box, never be clipped.
        assert svg.startswith("<svg") and "viewBox" in svg and ' width="' not in svg.split(">")[0]
        secret = setup.json()["secret"]

        bad = await c.post("/admin/2fa/enable", headers=auth(enrolment), json={"code": "000000"})
        assert bad.status_code == 401
        done = await c.post("/admin/2fa/enable", headers=auth(enrolment), json={"code": pyotp.TOTP(secret).now()})
        assert done.status_code == 200
        assert (await c.get("/admin/stats", headers=auth(done.json()["access_token"]))).status_code == 200


# A4: attempt limit ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sixth_attempt_is_blocked_even_with_the_right_password(db_env):
    async with client(admin_app) as c:
        for _ in range(settings.ADMIN_LOGIN_MAX_ATTEMPTS):
            wrong = await c.post("/admin/login", json={"email": "alice@example.com", "password": "nope-nope"})
            assert wrong.status_code == 401
        blocked = await c.post("/admin/login", json={
            "email": "alice@example.com", "password": PASSWORD, "two_factor_code": pyotp.TOTP(SECRET).now()})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


@pytest.mark.asyncio
async def test_wrong_totp_codes_count_as_failures(db_env):
    async with client(admin_app) as c:
        for _ in range(settings.ADMIN_LOGIN_MAX_ATTEMPTS):
            await c.post("/admin/login", json={
                "email": "alice@example.com", "password": PASSWORD, "two_factor_code": "111111"})
        blocked = await c.post("/admin/login", json={
            "email": "alice@example.com", "password": PASSWORD, "two_factor_code": pyotp.TOTP(SECRET).now()})
    assert blocked.status_code == 429


# A5: confirmation, last admin, strong passwords ------------------------------------

@pytest.mark.asyncio
async def test_role_change_requires_a_fresh_totp_confirmation(db_env):
    target = await user_id(db_env, "user@example.com")
    async with client(admin_app) as c:
        token = await admin_token(c)
        url, body = f"/admin/users/{target}/role", {"role": "student"}
        missing = await c.patch(url, headers=auth(token), json=body)
        wrong = await c.patch(url, headers=auth(token, "000000"), json=body)
        ok = await c.patch(url, headers=auth(token, pyotp.TOTP(SECRET).now()), json=body)
    # 428, never 401/403: the console must ask for the code, not log out.
    assert missing.status_code == 428 and missing.json()["detail"]["reason"] == "confirmation_required"
    assert wrong.status_code == 428 and wrong.json()["detail"]["reason"] == "confirmation_invalid"
    assert ok.status_code == 200 and ok.json()["role"] == "student"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("patch", "/admin/users/{uid}/status", {"is_active": False}),
        ("delete", "/admin/users/{uid}", None),
        ("post", "/admin/users/create-admin", {"email": "x@example.com", "full_name": "X Y", "password": "Very-Long-Pass-2026"}),
    ],
)
async def test_every_sensitive_action_requires_confirmation(db_env, method, path, body):
    uid = await user_id(db_env, "user@example.com")
    async with client(admin_app) as c:
        token = await admin_token(c)
        kwargs = {"headers": auth(token)}
        if body is not None:
            kwargs["json"] = body
        response = await getattr(c, method)(path.format(uid=uid), **kwargs)
    assert response.status_code == 428


@pytest.mark.asyncio
async def test_last_active_admin_cannot_be_demoted_or_deactivated(db_env):
    alice = await user_id(db_env, "alice@example.com")
    nora = await user_id(db_env, "nora@example.com")
    async with client(admin_app) as c:
        token = await admin_token(c)
        code = lambda: pyotp.TOTP(SECRET).now()  # noqa: E731
        # Nora deactivated: Alice becomes the only active admin.
        assert (await c.patch(f"/admin/users/{nora}/status", headers=auth(token, code()), json={"is_active": False})).status_code == 200
        for method, path, body in (
            ("patch", f"/admin/users/{alice}/role", {"role": "student"}),
            ("patch", f"/admin/users/{alice}/status", {"is_active": False}),
            ("delete", f"/admin/users/{alice}", None),
        ):
            kwargs = {"headers": auth(token, code())}
            if body:
                kwargs["json"] = body
            response = await getattr(c, method)(path, **kwargs)
            assert response.status_code == 400, (path, response.text)


@pytest.mark.asyncio
async def test_new_admins_need_a_twelve_character_password(db_env):
    async with client(admin_app) as c:
        token = await admin_token(c)
        response = await c.post("/admin/users/create-admin", headers=auth(token, pyotp.TOTP(SECRET).now()),
                                json={"email": "short@example.com", "full_name": "Short Pwd", "password": "Short-2026"})
    assert response.status_code == 422


# A6: messages ------------------------------------------------------------------------

def test_security_messages_are_properly_encoded():
    source = (BACKEND / "app/security.py").read_text(encoding="utf-8")
    assert "d?sactiv?" not in source and "v?rifi?e" not in source
    assert "Compte désactivé." in source and "Adresse e-mail non vérifiée." in source


# Frontend -------------------------------------------------------------------------------

def test_frontend_console_talks_to_the_admin_api_and_asks_for_confirmation():
    api = (ROOT / "frontend/lib/admin-api.ts").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_ADMIN_API_URL" in api and "http://localhost:8002" in api
    assert "X-Admin-Confirmation" in api and "428" in api
    login = (ROOT / "frontend/app/admin/login/page.tsx").read_text(encoding="utf-8")
    assert "requires_2fa_setup" in login and "/admin/2fa/setup" in login and "qr_svg" in login


@pytest.mark.asyncio
async def test_console_reads_the_signed_in_admin_from_the_admin_api(db_env):
    async with client(admin_app) as c:
        token = await admin_token(c)
        me = await c.get("/admin/me", headers=auth(token))
    assert me.status_code == 200 and me.json()["email"] == "alice@example.com"
    users_page = (ROOT / "frontend/app/admin/users/page.tsx").read_text(encoding="utf-8")
    assert 'adminFetch("/admin/me")' in users_page and "/auth/me" not in users_page
    assert "minLength={12}" in users_page
