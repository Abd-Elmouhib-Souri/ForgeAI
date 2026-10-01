"""
"Clone and run" contracts (user's request, 30 Sept 2026: the supervisor must
be able to clone the complete, tested project and run it).

Observed REDs on a fresh clone:
  S1  .env.example listed the variable names with NO value (not even
      DATABASE_URL or the model names) and missed GROQ_API_BASE / KROKI_*:
      the stack could not start without guessing ~90 values;
  S2  the internal secrets (JWT, AES Fernet key, session, Postgres, Chroma)
      had to be invented by hand, with formats nobody documents;
  S3  no way to get the first admin: only an admin can create an admin;
  S4  without SMTP, sign-up sent nothing and the new user could never
      verify the address, so the user side could not be tested at all;
  S5  no root README explaining the steps.
"""

from __future__ import annotations

import base64
import importlib.util
import logging
import re
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.mailer as mailer
from app import admin_security
from app.admin_main import app as admin_app
from app.config import Settings
from app.database import Base, get_db
from app.models import AdminAuditLog, User, UserRole
from app.security import get_password_hash, verify_password
from app.scripts import create_admin

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
PASSWORD = "Bootstrap-Pass-2026!"


def env_keys(text: str) -> dict[str, str]:
    return dict(re.findall(r"^([A-Z][A-Z0-9_]*)=(.*)$", text, flags=re.M))


def load_init_env():
    spec = importlib.util.spec_from_file_location("init_env", ROOT / "scripts" / "init_env.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# S1: a complete template ------------------------------------------------------------

def test_the_template_has_a_value_or_an_explained_blank_for_every_setting():
    example = env_keys((ROOT / ".env.example").read_text(encoding="utf-8-sig"))
    required = {name for name, field in Settings.model_fields.items() if field.is_required()}
    assert required <= set(example), required - set(example)
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose_vars = set(re.findall(r"\$\{([A-Z_]+)", compose))
    assert compose_vars <= set(example), compose_vars - set(example)
    for name in ("GROQ_API_BASE", "KROKI_ENABLED", "KROKI_BASE_URL", "ADMIN_API_PORT"):
        assert name in example, name
    # Non-secret values are filled: the stack starts once the secrets exist.
    for name in ("POSTGRES_USER", "POSTGRES_DB", "REDIS_URL", "CHROMA_HOST", "FRONTEND_URL",
                 "GEMINI_MODEL", "GROQ_MODEL", "APP_NAME", "SMTP_FROM_NAME", "ENVIRONMENT"):
        assert example[name].strip(), name
    assert example["APP_NAME"] == example["SMTP_FROM_NAME"] == "ForgeAI"  # no DotJcom in the product
    # RED 1 Oct 2026 (clone test): gemini-2.5-flash answers 404 "no longer available
    # to new users" on a fresh account. The template must not configure it.
    assert example["GEMINI_FALLBACK_MODEL"] == ""
    assert example["KROKI_ENABLED"] == "true" and example["KROKI_BASE_URL"].startswith("http")


def test_the_template_never_carries_a_secret():
    for path in (ROOT / ".env.example", BACKEND / ".env.example", ROOT / "frontend" / ".env.example"):
        text = path.read_text(encoding="utf-8-sig")
        assert not re.search(r"AIza[0-9A-Za-z_-]{20,}|gsk_[0-9A-Za-z]{20,}|tvly-[0-9A-Za-z]{10,}|GOCSPX-", text), path
        values = env_keys(text)
        for name, value in values.items():
            if re.search(r"(KEY|SECRET|PASSWORD|TOKEN)$", name):  # not ACCESS_TOKEN_EXPIRE_MINUTES
                assert value == "", f"{path.name}: {name} must stay empty"


def test_backend_template_matches_the_root_one():
    assert env_keys((BACKEND / ".env.example").read_text(encoding="utf-8-sig")) == env_keys(
        (ROOT / ".env.example").read_text(encoding="utf-8-sig"))


def test_frontend_template_points_to_both_apis():
    front = env_keys((ROOT / "frontend" / ".env.example").read_text(encoding="utf-8-sig"))
    assert front["NEXT_PUBLIC_API_URL"] == "http://localhost:8000"
    assert front["NEXT_PUBLIC_ADMIN_API_URL"] == "http://localhost:8002"


# S2: generated internal secrets ---------------------------------------------------------

def make_repo(tmp_path: Path) -> Path:
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    for rel in (".env.example", "frontend/.env.example"):
        (tmp_path / rel).write_text((ROOT / rel).read_text(encoding="utf-8-sig"), encoding="utf-8")
    return tmp_path


def test_init_env_generates_every_internal_secret(tmp_path):
    repo = make_repo(tmp_path)
    to_fill = load_init_env().init_env(repo)
    values = env_keys((repo / ".env").read_text(encoding="utf-8"))
    for name in ("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY", "SESSION_SECRET_KEY", "POSTGRES_PASSWORD", "CHROMA_AUTH_TOKEN"):
        assert len(values[name]) >= 32, name
    assert values["JWT_SECRET_KEY"] != values["JWT_REFRESH_SECRET_KEY"]
    assert len(base64.urlsafe_b64decode(values["AES_SECRET_KEY"])) == 32  # a valid Fernet key
    assert values["DATABASE_URL"] == (
        f"postgresql+asyncpg://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}@postgres:5432/{values['POSTGRES_DB']}")
    # One file to fill (docker compose env_file feeds the backend); the frontend has its own.
    assert not (repo / "backend" / ".env").exists()
    assert "NEXT_PUBLIC_ADMIN_API_URL=http://localhost:8002" in (repo / "frontend" / ".env.local").read_text(encoding="utf-8")
    # Only the external keys are left to the person installing.
    assert {"GEMINI_API_KEY", "GROQ_API_KEY"} <= set(to_fill)
    assert "JWT_SECRET_KEY" not in to_fill


def test_init_env_never_overwrites_an_existing_env(tmp_path):
    repo = make_repo(tmp_path)
    (repo / ".env").write_text("JWT_SECRET_KEY=keep-me\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_init_env().init_env(repo)
    assert (repo / ".env").read_text(encoding="utf-8") == "JWT_SECRET_KEY=keep-me\n"


# S3: first admin from the server's command line -------------------------------------------

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
    yield maker
    admin_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_admin_makes_a_verified_admin_who_must_enroll_2fa(sessions):
    async with sessions() as db:
        user, created = await create_admin.bootstrap_admin(db, " Prof@Example.com ", "Encadrant", PASSWORD)
    assert created and user.email == "prof@example.com"
    assert (user.role, user.is_active, user.is_email_verified, user.is_two_factor_enabled) == (UserRole.ADMIN, True, True, False)
    async with sessions() as db:
        [entry] = (await db.execute(select(AdminAuditLog))).scalars().all()
    assert (entry.action, entry.result, entry.target_label) == ("admin.bootstrap", "success", "prof@example.com")
    assert PASSWORD not in str(entry.after)

    # First console login: password accepted, 2FA enrollment demanded.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=admin_app), base_url="http://t") as c:
        r = await c.post("/admin/login", json={"email": "prof@example.com", "password": PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json().get("enrollment_token") and not r.json().get("access_token")


@pytest.mark.asyncio
async def test_create_admin_promotes_an_existing_account(sessions):
    async with sessions() as db:
        db.add(User(email="bob@example.com", full_name="Bob", role=UserRole.ENTREPRENEUR, google_id="g-1",
                    hashed_password=get_password_hash("old-password-123"), is_active=False, is_email_verified=False))
        await db.commit()
    async with sessions() as db:
        user, created = await create_admin.bootstrap_admin(db, "BOB@example.com", "Bob", PASSWORD)
    assert not created
    assert (user.role, user.is_active, user.is_email_verified, user.google_id) == (UserRole.ADMIN, True, True, "g-1")
    assert verify_password(PASSWORD, user.hashed_password)


@pytest.mark.asyncio
async def test_create_admin_refuses_a_short_password(sessions):
    async with sessions() as db:
        with pytest.raises(ValueError, match="12 caractères"):
            await create_admin.bootstrap_admin(db, "a@example.com", "A", "short-pass")


# S4: e-mails in development without SMTP ------------------------------------------------

@pytest.fixture
def no_smtp(monkeypatch):
    monkeypatch.setattr(mailer.settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(mailer.settings, "SMTP_PASSWORD", "")


def test_without_smtp_in_development_the_link_goes_to_the_server_log(no_smtp, monkeypatch, caplog):
    monkeypatch.setattr(mailer.settings, "ENVIRONMENT", "development")
    caplog.set_level(logging.INFO, logger="app.mailer")
    mailer.deliver("vérification", mailer.send_verification_email, "prof@example.com",
                   "http://localhost:3000/verify-email?token=abc123")
    assert "http://localhost:3000/verify-email?token=abc123" in caplog.text
    assert "SMTP non configuré" in caplog.text
    assert "prof@example.com" not in caplog.text and "pr***@example.com" in caplog.text
    assert "envoyé à" not in caplog.text  # never claims it was sent


def test_without_smtp_in_production_nothing_is_logged_and_it_fails(no_smtp, monkeypatch, caplog):
    monkeypatch.setattr(mailer.settings, "ENVIRONMENT", "production")
    caplog.set_level(logging.INFO, logger="app.mailer")
    mailer.deliver("vérification", mailer.send_verification_email, "prof@example.com",
                   "http://localhost:3000/verify-email?token=abc123")
    assert "token=abc123" not in caplog.text
    assert "Échec de l'envoi" in caplog.text


@pytest.mark.asyncio
async def test_the_health_page_says_where_the_emails_go_without_smtp(no_smtp, monkeypatch):
    # Seen in the clone proof: the SMTP card still said "no e-mail will leave".
    from app.services import health_checks

    monkeypatch.setattr(mailer.settings, "ENVIRONMENT", "development")
    status, message, _ = await health_checks.check_smtp()
    assert status == "not_configured" and "docker compose logs backend" in message
    monkeypatch.setattr(mailer.settings, "ENVIRONMENT", "production")
    _, message, _ = await health_checks.check_smtp()
    assert "aucun e-mail" in message


# S5: the README tells the whole procedure ---------------------------------------------

def test_the_readme_gives_every_installation_step():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for step in ("git clone", "python scripts/init_env.py", "docker compose up -d --build",
                 "docker compose exec backend alembic upgrade head",
                 "docker compose exec backend python -m app.scripts.create_admin",
                 "npm ci", "npm run dev", "http://localhost:3000/admin/login",
                 "docker compose logs backend", "Santé du système"):
        assert step in readme, step
    assert "DotJcom" not in readme
    # Kroki needs no key, only a server address; the local option and the check are explained.
    for text in ("Kroki (aucune clé)", "KROKI_BASE_URL=http://host.docker.internal:8010",
                 "docker run -d --name kroki-local", "/health", "Rendu visuel indisponible",
                 "Limites des offres gratuites", "Request too large"):
        assert text in readme, text
