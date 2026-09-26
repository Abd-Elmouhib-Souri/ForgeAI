"""
Sprint 6.1 export hardening contracts (pre-hosting security).

Observed REDs in the Sprint 6.1 PDF export (commit 96cdee8):
  S1  Files were served by a PUBLIC StaticFiles mount at a predictable URL
      (/exports/<project_id>/business_plan.pdf): anyone could enumerate
      project ids and download another user's business dossier.
  S2  ReportLab's synchronous doc.multiBuild() ran inside the event loop:
      the whole API froze while a PDF was generated.
  S3  Every export overwrote the same file, so older Export rows pointed to
      a document they did not describe.

Contracts:
  * a random (UUID) storage key per export, never a public URL;
  * download only through an authenticated, owner-filtered endpoint;
  * generation off the event loop, written atomically;
  * legacy rows keep working, path traversal is impossible.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from app.config import settings
from app.database import get_db
from app.models import ExportFormat
from app.routers import export as export_router_module
from app.security import get_current_user
from app.services.export import storage

BACKEND = Path(__file__).resolve().parents[2]
OWNER = SimpleNamespace(id=5)


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    """Records every compiled SQL statement and returns scripted rows."""

    def __init__(self, *rows):
        self.rows = list(rows)
        self.sql: list[str] = []
        self.added: list = []
        self.committed = False

    async def execute(self, statement):
        self.sql.append(str(statement.compile(compile_kwargs={"literal_binds": True})))
        return _Result(self.rows.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        obj.id = 7
        obj.created_at = datetime.datetime(2026, 9, 26, tzinfo=datetime.timezone.utc)


@pytest.fixture(autouse=True)
def exports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path))
    return tmp_path


def client_for(db: FakeDB) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(export_router_module.router)

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: OWNER
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def project(**overrides):
    base = dict(id=31, title="Tawla Pro été!", user_id=OWNER.id, analysis_data={})
    base.update(overrides)
    return SimpleNamespace(**base)


# S1 / S3: storage keys --------------------------------------------------------

def test_storage_keys_are_random_per_export_and_typed():
    first = storage.new_storage_key(31, "pdf")
    second = storage.new_storage_key(31, "pdf")
    assert first != second
    assert re.fullmatch(r"31/[0-9a-f]{32}\.pdf", first)
    assert storage.new_storage_key(31, "docx").endswith(".docx")
    with pytest.raises(ValueError):
        storage.new_storage_key(31, "html")


@pytest.mark.parametrize(
    "stored",
    ["../32/x.pdf", "32/abc.pdf", "/etc/passwd", "31/../../x.pdf", "31\\..\\x.pdf", "", "31/"],
)
def test_resolution_never_leaves_the_project_folder(exports_dir, stored):
    (exports_dir / "32").mkdir()
    (exports_dir / "32" / "abc.pdf").write_bytes(b"%PDF other user")
    assert storage.resolve_storage_path(stored, project_id=31) is None


def test_legacy_public_paths_still_resolve(exports_dir):
    (exports_dir / "31").mkdir()
    legacy = exports_dir / "31" / "business_plan.pdf"
    legacy.write_bytes(b"%PDF legacy")
    assert storage.resolve_storage_path("/exports/31/business_plan.pdf", project_id=31) == legacy.resolve()


def test_download_filename_is_readable_and_header_safe():
    assert storage.download_filename("Tawla Pro été!", "business_plan", "pdf") == "ForgeAI_Tawla_Pro_ete_business_plan.pdf"
    assert storage.download_filename("", "business_plan", "pdf") == "ForgeAI_projet_business_plan.pdf"
    assert storage.download_filename('a"\r\nb', "pitch_deck", "pptx") == "ForgeAI_a_b_pitch_deck.pptx"


def test_atomic_write_leaves_nothing_on_failure(exports_dir):
    target = exports_dir / "31" / "x.pdf"

    def broken_build(path: str) -> None:
        Path(path).write_bytes(b"partial")
        raise RuntimeError("renderer crashed")

    with pytest.raises(RuntimeError):
        storage.write_atomically(target, broken_build)
    assert list(exports_dir.rglob("*")) == [exports_dir / "31"]


# S1 / S2 / S3: generation endpoint ---------------------------------------------

@pytest.mark.asyncio
async def test_pdf_export_is_private_offloaded_and_unique(exports_dir, monkeypatch):
    offloaded = []
    real_to_thread = export_router_module.asyncio.to_thread

    async def spy_to_thread(func, *args, **kwargs):
        offloaded.append(func)
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(export_router_module.asyncio, "to_thread", spy_to_thread)
    db = FakeDB(project())

    async with client_for(db) as client:
        response = await client.post("/projects/31/export/pdf")

    assert response.status_code == 200
    body = response.json()
    assert body["download_url"] == "/projects/31/exports/7/download"
    assert body["file_name"] == "ForgeAI_Tawla_Pro_ete_business_plan.pdf"
    assert "/exports/31/" not in response.text  # no public URL anywhere

    row = db.added[0]
    assert re.fullmatch(r"31/[0-9a-f]{32}\.pdf", row.file_path)
    written = exports_dir / row.file_path
    assert written.read_bytes().startswith(b"%PDF")
    assert offloaded, "ReportLab must run in a worker thread"
    assert "projects.user_id = 5" in db.sql[0]


@pytest.mark.asyncio
async def test_failed_generation_leaves_no_file_and_no_row(exports_dir, monkeypatch):
    def crash(*args, **kwargs):
        raise RuntimeError("layout overflow")

    monkeypatch.setattr(export_router_module, "build_full_flow", crash)
    db = FakeDB(project())
    async with client_for(db) as client:
        with pytest.raises(RuntimeError):
            await client.post("/projects/31/export/pdf")
    assert db.added == [] and db.committed is False
    assert [p for p in exports_dir.rglob("*") if p.is_file()] == []


# S1: download endpoint ----------------------------------------------------------

def export_row(file_path: str):
    return SimpleNamespace(id=7, project_id=31, format=ExportFormat.PDF, file_path=file_path,
                           project=project())


@pytest.mark.asyncio
async def test_owner_downloads_with_attachment_headers(exports_dir):
    key = storage.new_storage_key(31, "pdf")
    (exports_dir / key).parent.mkdir(parents=True)
    (exports_dir / key).write_bytes(b"%PDF-1.4 owner")
    db = FakeDB(export_row(key))

    async with client_for(db) as client:
        response = await client.get("/projects/31/exports/7/download")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 owner"
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="ForgeAI_Tawla_Pro_ete_business_plan.pdf"' in response.headers["content-disposition"]
    assert "no-store" in response.headers["cache-control"]
    sql = db.sql[0]
    # Ownership is enforced in the query itself, never after loading.
    assert "projects.user_id = 5" in sql
    assert "exports.project_id = 31" in sql and "exports.id = 7" in sql


@pytest.mark.asyncio
async def test_foreign_or_unknown_export_is_404():
    db = FakeDB(None)
    async with client_for(db) as client:
        response = await client.get("/projects/31/exports/7/download")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_missing_file_on_disk_is_a_clear_404():
    db = FakeDB(export_row("31/" + "a" * 32 + ".pdf"))
    async with client_for(db) as client:
        response = await client.get("/projects/31/exports/7/download")
    assert response.status_code == 404
    assert "relancez l'export" in response.json()["detail"]


def test_public_exports_mount_is_gone():
    main = (BACKEND / "app/main.py").read_text(encoding="utf-8")
    assert 'app.mount("/exports"' not in main
    assert "StaticFiles" not in main
