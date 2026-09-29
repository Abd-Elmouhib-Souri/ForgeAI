"""
E-mail identity contracts (RED found by the user, 28 Sept 2026).

Observed RED: "mot de passe oublié" logged "aucun compte pour so***@gmail.com"
for an account that exists. Pydantic keeps the case of the local part
("Sourimouhib3@gmail.com" stays capitalised, browsers often capitalise the
first letter) and every lookup compared e-mails case-sensitively: the same
mailbox could fail to log in, fail to reset, or even register twice.

Contract: an e-mail typed by a person is matched case- and space-
insensitively everywhere (public + admin), and new accounts are stored in
lowercase. Lookups by token subject stay exact (the stored value itself).
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.routers.auth as auth_router
from app import admin_security
from app.admin_main import app as admin_app
from app.database import Base, get_db
from app.email_identity import normalize_email
from app.main import app as public_app
from app.models import User, UserRole
from app.security import get_password_hash
from app.security_policy import protect_totp_secret

BACKEND = Path(__file__).resolve().parents[2]
SECRET = pyotp.random_base32()
PASSWORD = "Pass-Word-2026!x"


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

    public_app.dependency_overrides[get_db] = _db
    admin_app.dependency_overrides[get_db] = _db
    admin_security.login_throttle.use_store(admin_security.MemoryStore())

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(auth_router, "send_password_reset_email", lambda to, link: sent.append(("reset", to)))
    monkeypatch.setattr(auth_router, "send_google_account_password_email", lambda to, link, login: sent.append(("google", to)))
    monkeypatch.setattr(auth_router, "send_verification_email", lambda to, link: sent.append(("verify", to)))

    async with sessions() as s:
        s.add_all([
            User(email="sourimouhib3@gmail.com", full_name="Google User", role=UserRole.ENTREPRENEUR,
                 hashed_password=None, google_id="g-1", is_active=True, is_email_verified=True),
            User(email="classic@example.com", full_name="Classic", role=UserRole.ENTREPRENEUR,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True),
            User(email="admin@example.com", full_name="Admin", role=UserRole.ADMIN,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                 is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)),
        ])
        await s.commit()
    yield sessions, sent
    public_app.dependency_overrides.clear()
    admin_app.dependency_overrides.clear()
    await engine.dispose()


def client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


def test_normalize_email():
    assert normalize_email("  Sourimouhib3@Gmail.COM ") == "sourimouhib3@gmail.com"


@pytest.mark.asyncio
async def test_forgot_password_with_a_capital_letter_finds_the_account(env):
    _, sent = env
    async with client(public_app) as c:
        r = await c.post("/auth/forgot-password", json={"email": "Sourimouhib3@gmail.com"})
    assert r.status_code == 200
    assert sent == [("google", "sourimouhib3@gmail.com")]  # the stored address


@pytest.mark.asyncio
async def test_login_ignores_case_and_spaces(env):
    async with client(public_app) as c:
        r = await c.post("/auth/login", json={"email": " Classic@Example.com ", "password": PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


@pytest.mark.asyncio
async def test_register_stores_lowercase_and_refuses_a_case_duplicate(env):
    sessions, _ = env
    async with client(public_app) as c:
        first = await c.post("/auth/register", json={"email": "New.User@Example.com", "password": PASSWORD,
                                                     "full_name": "New User", "role": "entrepreneur"})
        assert first.status_code in (200, 201), first.text
        again = await c.post("/auth/register", json={"email": "new.user@example.com", "password": PASSWORD,
                                                     "full_name": "Twin", "role": "entrepreneur"})
    assert again.status_code == 400, again.text
    async with sessions() as s:
        stored = (await s.execute(select(User.email).where(func.lower(User.email) == "new.user@example.com"))).scalars().all()
    assert stored == ["new.user@example.com"]


@pytest.mark.asyncio
async def test_admin_login_ignores_case(env):
    async with client(admin_app) as c:
        r = await c.post("/admin/login", json={"email": "Admin@Example.com", "password": PASSWORD,
                                               "two_factor_code": pyotp.TOTP(SECRET).now()})
    assert r.status_code == 200, r.text


def test_no_typed_email_is_compared_case_sensitively():
    # Lookups from what a person typed must go through same_email();
    # only token subjects (the stored value) may be compared exactly.
    for path in ("app/routers/auth.py", "app/routers/admin.py"):
        source = (BACKEND / path).read_text(encoding="utf-8")
        offenders = re.findall(r"User\.email == (user_in\.email|payload\.email)", source)
        assert offenders == [], (path, offenders)
    auth_source = (BACKEND / "app/routers/auth.py").read_text(encoding="utf-8")
    google_block = auth_source[auth_source.index("User.google_id == google_id"):]
    assert "same_email(User.email, email)" in google_block[:600]


def test_lower_email_lookups_are_indexed():
    [migration] = list((BACKEND / "migrations" / "versions").glob("*users_email_lower_index*.py"))
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision: Union[str, None] = "e3c1a7d5b902"' in source
    assert "lower(email)" in source
