"""
Sprint 7.2 admin audit log contracts.

Observed REDs (audit 27 Sept 2026):
  B1  No trace of admin actions: a role change, a deactivation or a deletion
      left no record of who did it, when, from where, or what changed.
  B2  No trace of failed admin logins, blocked attempts or wrong
      confirmation codes (brute force invisible after the fact).
  B3  Deleting a project (admin or owner) left its export files (PDF, Word,
      PowerPoint) on disk forever.

Contract:
  * one append-only table (admin_audit_logs): the ORM refuses UPDATE and
    DELETE, and PostgreSQL refuses them too (trigger in the migration);
  * failures are recorded even though the request answers 4xx;
  * no secret (password, TOTP code, token) ever lands in the log;
  * GET /admin/audit (filters + pagination) and GET /admin/audit/export.csv,
    admin-only, read-only; CSV cells cannot run as spreadsheet formulas.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import httpx
import pyotp
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import admin_security
from app.admin_main import app as admin_app
from app.config import settings
from app.database import Base, get_db
from app.main import app as public_app
from app.models import AdminAuditLog, Export, ExportFormat, Project, User, UserRole
from app.security import create_access_token, get_password_hash
from app.security_policy import protect_totp_secret

BACKEND = Path(__file__).resolve().parents[2]
PASSWORD = "Admin-Pass-2026!x"
SECRET = pyotp.random_base32()
UA = "Mozilla/5.0 (AuditTest)"
SENT: list[str] = []  # verification e-mails queued during the current test


@pytest_asyncio.fixture
async def env(tmp_path, monkeypatch):
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
    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path / "exports"))
    # Harness: no real SMTP from the tests (the background task blocked on
    # the network). Queued e-mails are kept for assertions.
    import app.routers.admin as admin_router_module

    SENT.clear()
    monkeypatch.setattr(admin_router_module, "send_verification_email",
                        lambda email, link, *args, **kwargs: SENT.append(email))

    async with sessions() as session:
        session.add_all([
            User(email="alice@example.com", full_name="Alice Admin", role=UserRole.ADMIN,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                 is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)),
            User(email="bob@example.com", full_name="Bob Admin", role=UserRole.ADMIN,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True,
                 is_two_factor_enabled=True, two_factor_secret=protect_totp_secret(SECRET)),
            User(email="nora@example.com", full_name="Nora New Admin", role=UserRole.ADMIN,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True),
            User(email="user@example.com", full_name="Uma User", role=UserRole.ENTREPRENEUR,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=True),
            User(email="pending@example.com", full_name="Paul Pending", role=UserRole.STUDENT,
                 hashed_password=get_password_hash(PASSWORD), is_active=True, is_email_verified=False),
        ])
        await session.commit()
    yield sessions
    admin_app.dependency_overrides.clear()
    public_app.dependency_overrides.clear()
    await engine.dispose()


def client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                             headers={"User-Agent": UA})


async def login(c, email="alice@example.com") -> str:
    r = await c.post("/admin/login", json={"email": email, "password": PASSWORD,
                                           "two_factor_code": pyotp.TOTP(SECRET).now()})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str, code: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if code is not None:
        headers["X-Admin-Confirmation"] = code
    return headers


async def uid(sessions, email: str) -> int:
    async with sessions() as s:
        return (await s.execute(select(User.id).where(User.email == email))).scalar_one()


async def entries(sessions, action: str | None = None) -> list[AdminAuditLog]:
    async with sessions() as s:
        query = select(AdminAuditLog).order_by(AdminAuditLog.id)
        if action:
            query = query.where(AdminAuditLog.action == action)
        return list((await s.execute(query)).scalars())


def no_secret(entry: AdminAuditLog) -> None:
    blob = repr((entry.before, entry.after, entry.detail, entry.target_label))
    assert PASSWORD not in blob
    assert "Bearer" not in blob and "eyJ" not in blob


# B1/B2: logins ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_login_is_recorded_with_ip_and_browser(env):
    async with client(admin_app) as c:
        await login(c)
    [entry] = await entries(env, "admin.login")
    assert entry.result == "success"
    assert entry.actor_email == "alice@example.com"
    assert entry.actor_id == await uid(env, "alice@example.com")
    assert entry.ip_address  # ASGI test client host
    assert entry.user_agent == UA
    assert entry.created_at is not None
    no_secret(entry)


@pytest.mark.asyncio
async def test_failed_logins_are_recorded_despite_the_error_response(env):
    async with client(admin_app) as c:
        r = await c.post("/admin/login", json={"email": "alice@example.com", "password": "wrong-password"})
        assert r.status_code == 401
        r = await c.post("/admin/login", json={"email": "ghost@example.com", "password": "wrong-password"})
        assert r.status_code == 401
        r = await c.post("/admin/login", json={"email": "user@example.com", "password": PASSWORD})
        assert r.status_code == 403
        r = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD,
                                               "two_factor_code": "000000"})
        assert r.status_code == 401
    rows = await entries(env, "admin.login")
    assert [(e.actor_email, e.result, e.detail) for e in rows] == [
        ("alice@example.com", "failure", "bad_credentials"),
        ("ghost@example.com", "failure", "bad_credentials"),
        ("user@example.com", "denied", "not_admin"),
        ("alice@example.com", "failure", "totp_invalid"),
    ]
    # Unknown account: no actor id, but the attempted e-mail is kept.
    assert rows[1].actor_id is None
    for e in rows:
        no_secret(e)
        assert "000000" not in repr((e.before, e.after, e.detail))


@pytest.mark.asyncio
async def test_blocked_login_is_recorded(env):
    async with client(admin_app) as c:
        for _ in range(settings.ADMIN_LOGIN_MAX_ATTEMPTS):
            await c.post("/admin/login", json={"email": "alice@example.com", "password": "wrong-password"})
        r = await c.post("/admin/login", json={"email": "alice@example.com", "password": PASSWORD})
        assert r.status_code == 429
    [blocked] = await entries(env, "admin.login.blocked")
    assert blocked.result == "denied"
    assert blocked.actor_email == "alice@example.com"


@pytest.mark.asyncio
async def test_two_factor_enrollment_is_recorded(env):
    async with client(admin_app) as c:
        r = await c.post("/admin/login", json={"email": "nora@example.com", "password": PASSWORD})
        enroll = r.json()["enrollment_token"]
        setup = (await c.post("/admin/2fa/setup", headers=auth(enroll))).json()
        r = await c.post("/admin/2fa/enable", headers=auth(enroll), json={"code": "000000"})
        assert r.status_code == 401
        r = await c.post("/admin/2fa/enable", headers=auth(enroll),
                         json={"code": pyotp.TOTP(setup["secret"]).now()})
        assert r.status_code == 200
    rows = await entries(env, "admin.2fa.enable")
    assert [e.result for e in rows] == ["failure", "success"]
    for e in rows:
        assert setup["secret"] not in repr((e.before, e.after, e.detail))


@pytest.mark.asyncio
async def test_wrong_confirmation_code_is_recorded(env):
    target = await uid(env, "user@example.com")
    async with client(admin_app) as c:
        token = await login(c)
        r = await c.patch(f"/admin/users/{target}/role", headers=auth(token, "000000"), json={"role": "student"})
        assert r.status_code == 428
    [entry] = await entries(env, "admin.confirmation")
    assert entry.result == "failure"
    assert entry.actor_email == "alice@example.com"
    assert entry.detail == "confirmation_invalid"
    # The refused change itself is not logged as done.
    assert await entries(env, "user.role.update") == []


# B1: sensitive actions --------------------------------------------------------------

@pytest.mark.asyncio
async def test_role_and_status_changes_record_before_and_after(env):
    target = await uid(env, "user@example.com")
    async with client(admin_app) as c:
        token = await login(c)
        code = pyotp.TOTP(SECRET).now()
        assert (await c.patch(f"/admin/users/{target}/role", headers=auth(token, code),
                              json={"role": "consultant"})).status_code == 200
        assert (await c.patch(f"/admin/users/{target}/status", headers=auth(token, code),
                              json={"is_active": False})).status_code == 200
    [role] = await entries(env, "user.role.update")
    assert (role.before, role.after) == ({"role": "entrepreneur"}, {"role": "consultant"})
    assert (role.target_type, role.target_id, role.target_label) == ("user", str(target), "user@example.com")
    assert role.result == "success" and role.actor_email == "alice@example.com"
    [state] = await entries(env, "user.status.update")
    assert (state.before, state.after) == ({"is_active": True}, {"is_active": False})


@pytest.mark.asyncio
async def test_refused_business_rule_is_recorded_as_denied(env):
    me = await uid(env, "alice@example.com")
    async with client(admin_app) as c:
        token = await login(c)
        r = await c.patch(f"/admin/users/{me}/status", headers=auth(token, pyotp.TOTP(SECRET).now()),
                          json={"is_active": False})
        assert r.status_code == 400
    [entry] = await entries(env, "user.status.update")
    assert entry.result == "denied"
    assert entry.detail


@pytest.mark.asyncio
async def test_admin_creation_is_recorded_without_the_password(env):
    async with client(admin_app) as c:
        token = await login(c)
        r = await c.post("/admin/users/create-admin", headers=auth(token, pyotp.TOTP(SECRET).now()),
                         json={"email": "new-admin@example.com", "full_name": "New Admin",
                               "password": "Very-Strong-Pass-2026"})
        assert r.status_code == 201, r.text
    assert SENT == ["new-admin@example.com"]
    [entry] = await entries(env, "admin.create")
    assert entry.target_label == "new-admin@example.com"
    assert "Very-Strong-Pass-2026" not in repr((entry.before, entry.after, entry.detail))


@pytest.mark.asyncio
async def test_resend_verification_and_user_deletion_are_recorded(env):
    pending = await uid(env, "pending@example.com")
    async with client(admin_app) as c:
        token = await login(c)
        assert (await c.post(f"/admin/users/{pending}/resend-verification",
                             headers=auth(token))).status_code == 200
        assert (await c.delete(f"/admin/users/{pending}",
                               headers=auth(token, pyotp.TOTP(SECRET).now()))).status_code == 204
    assert SENT == ["pending@example.com"]
    [resend] = await entries(env, "user.verification.resend")
    assert resend.target_label == "pending@example.com"
    [deleted] = await entries(env, "user.delete")
    # The deleted account is gone, its snapshot stays in the log.
    assert deleted.before["email"] == "pending@example.com"
    assert deleted.before["role"] == "student"
    assert deleted.after is None


# B3: project deletion ---------------------------------------------------------------

async def make_project_with_export(sessions, owner_email: str) -> tuple[int, Path]:
    owner = await uid(sessions, owner_email)
    async with sessions() as s:
        project = Project(title="Tawla Pro", description="Plateforme test", user_id=owner)
        s.add(project)
        await s.flush()
        folder = Path(settings.EXPORTS_DIR) / str(project.id)
        folder.mkdir(parents=True)
        (folder / "abc.pdf").write_bytes(b"%PDF-1.4 test")
        s.add(Export(project_id=project.id, format=ExportFormat.PDF, file_path=f"{project.id}/abc.pdf"))
        await s.commit()
        return project.id, folder


@pytest.mark.asyncio
async def test_admin_project_deletion_is_recorded_and_removes_export_files(env):
    project_id, folder = await make_project_with_export(env, "user@example.com")
    async with client(admin_app) as c:
        token = await login(c)
        r = await c.delete(f"/admin/projects/{project_id}", headers=auth(token, pyotp.TOTP(SECRET).now()))
        assert r.status_code == 204
    assert not folder.exists()
    [entry] = await entries(env, "project.delete")
    assert entry.before["title"] == "Tawla Pro"
    assert entry.before["owner_email"] == "user@example.com"
    assert entry.before["exports"] == 1


@pytest.mark.asyncio
async def test_owner_project_deletion_also_removes_export_files(env):
    project_id, folder = await make_project_with_export(env, "user@example.com")
    token = create_access_token({"sub": "user@example.com"})
    async with client(public_app) as c:
        r = await c.delete(f"/projects/{project_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204, r.text
    assert not folder.exists()


def test_export_cleanup_never_leaves_the_exports_folder(tmp_path, monkeypatch):
    from app.services.export.storage import delete_project_files

    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path / "exports"))
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    (tmp_path / "exports").mkdir()
    try:
        (tmp_path / "exports" / "7").symlink_to(outside, target_is_directory=True)
    except OSError:
        # Harness: Windows refuses symlinks without admin rights / developer
        # mode (WinError 1314). The guard is proven on Linux, where the
        # product runs (Docker image).
        pytest.skip("symlink creation not permitted on this machine")
    delete_project_files(7)
    assert (outside / "keep.txt").exists()


def test_export_cleanup_of_a_missing_folder_is_silent(tmp_path, monkeypatch):
    from app.services.export.storage import delete_project_files

    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path / "exports"))
    delete_project_files(999)  # never exported: no error, nothing created
    assert not (tmp_path / "exports" / "999").exists()


# Append-only ------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_entries_cannot_be_updated_or_deleted(env):
    async with client(admin_app) as c:
        await login(c)
    async with env() as s:
        entry = (await s.execute(select(AdminAuditLog))).scalars().first()
        entry.result = "failure"
        with pytest.raises(Exception, match="append-only"):
            await s.flush()
    async with env() as s:
        entry = (await s.execute(select(AdminAuditLog))).scalars().first()
        await s.delete(entry)
        with pytest.raises(Exception, match="append-only"):
            await s.flush()


def test_migration_creates_the_table_and_the_postgres_guard():
    [migration] = list((BACKEND / "migrations" / "versions").glob("*admin_audit_logs*.py"))
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision: Union[str, None] = "8b24c1a0f3e7"' in source
    assert "admin_audit_logs" in source
    assert "BEFORE UPDATE OR DELETE" in source
    assert "append-only" in source


# Reading the log ----------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_list_requires_an_admin_session(env):
    user_token = create_access_token({"sub": "user@example.com"})
    async with client(admin_app) as c:
        assert (await c.get("/admin/audit")).status_code == 401
        assert (await c.get("/admin/audit", headers={"Authorization": f"Bearer {user_token}"})).status_code == 401
        assert (await c.get("/admin/audit/export.csv")).status_code == 401


def test_audit_routes_are_read_only():
    methods = set()
    for route in admin_app.routes:
        if getattr(route, "path", "").startswith("/admin/audit"):
            methods |= set(route.methods or ())
    assert methods and methods <= {"GET", "HEAD"}, methods


@pytest.mark.asyncio
async def test_audit_list_filters_and_paginates(env):
    async with client(admin_app) as c:
        await c.post("/admin/login", json={"email": "alice@example.com", "password": "wrong-password"})
        token = await login(c)
        await login(c, "bob@example.com")

        page = (await c.get("/admin/audit", headers=auth(token))).json()
        assert page["total"] == 3 and page["page"] == 1
        # Newest first.
        assert page["items"][0]["actor_email"] == "bob@example.com"
        assert {"id", "created_at", "actor_email", "action", "target_type", "target_id", "target_label",
                "before", "after", "ip_address", "user_agent", "result", "detail"} <= set(page["items"][0])

        failures = (await c.get("/admin/audit?result=failure", headers=auth(token))).json()
        assert [i["detail"] for i in failures["items"]] == ["bad_credentials"]

        bob = (await c.get("/admin/audit?actor=bob", headers=auth(token))).json()
        assert bob["total"] == 1

        small = (await c.get("/admin/audit?page_size=2&page=2", headers=auth(token))).json()
        assert small["total"] == 3 and len(small["items"]) == 1

        assert (await c.get("/admin/audit?page_size=1000", headers=auth(token))).status_code == 422

        actions = (await c.get("/admin/audit/actions", headers=auth(token))).json()
        assert "admin.login" in actions and "project.delete" in actions


@pytest.mark.asyncio
async def test_audit_csv_export_is_safe_for_spreadsheets(env):
    async with client(admin_app) as c:
        # A hostile browser string starting with "=" must not become a formula.
        await c.post("/admin/login", headers={"User-Agent": "=HYPERLINK(\"http://evil\")"},
                     json={"email": "alice@example.com", "password": "x"})
        await c.post("/admin/login", json={"email": "alice@example.com", "password": "wrong-password"})
        token = await login(c)
        r = await c.get("/admin/audit/export.csv", headers=auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8-sig")
    assert text.startswith("Date;Auteur;Action;")  # French Excel separator
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    assert rows[0][:4] == ["Date", "Auteur", "Action", "Résultat"]
    assert len(rows) >= 3
    cells = [cell for row in rows[1:] for cell in row]
    assert not any(cell.startswith(("=", "+", "-", "@")) for cell in cells)
