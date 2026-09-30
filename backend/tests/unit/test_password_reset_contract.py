"""
Password reset contracts (RED found by the user, 28 Sept 2026).

Observed REDs:
  R1  "mot de passe oublié" on an account created with Google (no password)
      silently did nothing: no e-mail, no log, and the page still said
      "un lien a été envoyé" - the user stayed locked out without knowing why;
  R2  the reasons for not sending (unknown e-mail, disabled, Google) were
      never logged, so nobody could diagnose it;
  R3  SMTP had no timeout (a mute server blocked the background task forever)
      and background send failures were not logged in a readable way.

Decision (user, 28 Sept 2026): a Google account receives an e-mail that
explains the Google sign-in AND offers a link to set a password (same proof
as a normal reset: access to the mailbox).

The HTTP answer stays identical in every case (no account enumeration).
"""

from __future__ import annotations

import logging

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.mailer as mailer
import app.routers.auth as auth_router
from app.database import Base, get_db
from app.main import app as public_app
from app.models import User, UserRole
from app.security import get_password_hash

GENERIC = "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."


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

    sent: list[tuple[str, str, str]] = []  # (kind, to, link)
    monkeypatch.setattr(auth_router, "send_password_reset_email",
                        lambda to, link: sent.append(("reset", to, link)))
    monkeypatch.setattr(auth_router, "send_google_account_password_email",
                        lambda to, link, login: sent.append(("google", to, link)))

    async with sessions() as s:
        s.add_all([
            User(email="google@example.com", full_name="Gina Google", role=UserRole.ENTREPRENEUR,
                 hashed_password=None, google_id="google-sub-123", is_active=True, is_email_verified=True),
            User(email="classic@example.com", full_name="Carl Classic", role=UserRole.ENTREPRENEUR,
                 hashed_password=get_password_hash("Old-Pass-2026!"), is_active=True, is_email_verified=True),
            User(email="disabled@example.com", full_name="Dan Disabled", role=UserRole.ENTREPRENEUR,
                 hashed_password=get_password_hash("Old-Pass-2026!"), is_active=False, is_email_verified=True),
        ])
        await s.commit()
    yield sessions, sent
    public_app.dependency_overrides.clear()
    await engine.dispose()


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=public_app), base_url="http://t")


async def forgot(c, email):
    r = await c.post("/auth/forgot-password", json={"email": email})
    assert r.status_code == 200, r.text
    return r.json()["message"]


# R1 ---------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_google_account_receives_an_email_to_set_a_password(env):
    sessions, sent = env
    async with client() as c:
        assert await forgot(c, "google@example.com") == GENERIC
    [(kind, to, link)] = sent
    assert (kind, to) == ("google", "google@example.com")
    assert "/reset-password?token=" in link


@pytest.mark.asyncio
async def test_the_google_account_can_then_log_in_with_email_and_password(env):
    sessions, sent = env
    async with client() as c:
        await forgot(c, "google@example.com")
        token = sent[0][2].split("token=", 1)[1]
        r = await c.post("/auth/reset-password", json={"token": token, "new_password": "New-Pass-2026!"})
        assert r.status_code == 200, r.text
        login = await c.post("/auth/login", json={"email": "google@example.com", "password": "New-Pass-2026!"})
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]
    async with sessions() as s:
        user = (await s.execute(select(User).where(User.email == "google@example.com"))).scalar_one()
    assert user.google_id == "google-sub-123"  # "Continuer avec Google" keeps working


@pytest.mark.asyncio
async def test_a_classic_account_still_receives_the_reset_email(env):
    _, sent = env
    async with client() as c:
        assert await forgot(c, "classic@example.com") == GENERIC
    assert [(k, to) for k, to, _ in sent] == [("reset", "classic@example.com")]


# R2 ---------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_email_cases_answer_the_same_and_are_logged_with_a_masked_address(env, caplog):
    _, sent = env
    caplog.set_level(logging.INFO, logger="app.routers.auth")
    async with client() as c:
        assert await forgot(c, "nobody@example.com") == GENERIC
        assert await forgot(c, "disabled@example.com") == GENERIC
    assert sent == []
    logs = caplog.text
    assert "no***@example.com" in logs and "aucun compte" in logs
    assert "di***@example.com" in logs and "désactivé" in logs
    assert "nobody@example.com" not in logs and "disabled@example.com" not in logs


def test_email_masking():
    assert mailer.mask_email("sourimouhib3@gmail.com") == "so***@gmail.com"
    assert mailer.mask_email("a@b.co") == "a***@b.co"
    assert mailer.mask_email("not-an-email") == "***"


# R3 ---------------------------------------------------------------------------------

class FakeSMTP:
    sent: list = []
    calls: list[dict] = []
    fail_with: Exception | None = None

    def __init__(self, host, port, timeout=None, **kwargs):
        FakeSMTP.calls.append({"host": host, "port": port, "timeout": timeout})
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, **kwargs):
        pass

    def login(self, *args):
        pass

    def send_message(self, message):
        FakeSMTP.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.calls, FakeSMTP.sent, FakeSMTP.fail_with = [], [], None
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(mailer.settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(mailer.settings, "SMTP_PORT", 587)
    return FakeSMTP


def test_every_smtp_connection_has_a_timeout(fake_smtp):
    mailer.send_email("to@example.com", "Sujet", "Corps")
    assert fake_smtp.calls[0]["timeout"] == mailer.settings.SMTP_TIMEOUT_SECONDS > 0


def test_background_delivery_logs_success_and_failure_without_crashing(fake_smtp, caplog):
    caplog.set_level(logging.INFO, logger="app.mailer")
    mailer.deliver("réinitialisation", mailer.send_email, "user@example.com", "Sujet", "Corps")
    assert "E-mail « réinitialisation » envoyé à us***@example.com" in caplog.text

    fake_smtp.fail_with = TimeoutError("timed out")
    mailer.deliver("réinitialisation", mailer.send_email, "user@example.com", "Sujet", "Corps")  # no raise
    assert "Échec de l'envoi de l'e-mail « réinitialisation » à us***@example.com" in caplog.text
    assert "TimeoutError" in caplog.text
    assert "user@example.com" not in caplog.text


def test_all_background_emails_go_through_the_logged_delivery():
    import inspect

    for module in (auth_router, __import__("app.routers.admin", fromlist=["x"])):
        source = inspect.getsource(module)
        assert "background_tasks.add_task(\n        deliver," in source or "add_task(deliver," in source, module.__name__


# RED 28 Sept 2026 (user's screenshot): the test mail landed in Gmail's spam.
# Missing Date / Message-ID headers are classic spam signals.

def test_every_email_carries_date_and_message_id_headers(fake_smtp, monkeypatch):
    monkeypatch.setattr(mailer.settings, "SMTP_FROM_EMAIL", "noreply@forgeai.example")
    monkeypatch.setattr(mailer.settings, "SMTP_FROM_NAME", "ForgeAI")
    mailer.send_email("to@example.com", "Sujet", "Corps", "<p>Corps</p>")
    [message] = fake_smtp.sent
    assert message["Date"]
    assert message["Message-ID"].endswith("@forgeai.example>")
    assert message["From"] == "ForgeAI <noreply@forgeai.example>"
    assert message.get_body(("plain",)) is not None and message.get_body(("html",)) is not None
