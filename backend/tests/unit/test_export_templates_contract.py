"""
Sprint 6.4 role-template contracts.

CDC 6.4: role templates (entrepreneur / student / consultant) on top of the
complete "business" report. A template SELECTS and ORDERS existing sections
for the PDF and the Word exports; it never generates new text (no LLM call,
nothing invented). The cover states which dossier it is, the template is
recorded in Export.template_used, and an unknown template is refused.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import docx
import httpx
import pytest
from fastapi import FastAPI

from app.config import settings
from app.database import get_db
from app.routers import export as export_router_module
from app.security import get_current_user
from app.services.export import labels as labels_module
from app.services.export import templates
from app.services.export.data_assembly import assemble_export_data
from app.services.export.docx_builder import build_docx
from app.services.export.pdf_builder import build_full_flow
from app.services.export.pdf_design import build_styles
from tests.unit.test_export_word_contract import FRONTEND, OWNER, FakeDB, analysis_data, headings

FR = labels_module.FR
ALL = templates.SECTION_KEYS


def assembled(template: str, language: str = "fr") -> dict:
    return assemble_export_data(
        analysis_data=analysis_data(), project_name="Atelier Partagé",
        output_language=language, template=template,
    )


def expected_headings(template: str) -> list[str]:
    """Section titles + the extra top-level pages two sections always add
    with the shared fixture (risks page after the committee, UML after the
    architecture)."""
    out: list[str] = []
    for key in templates.sections_for(template):
        out.append(FR[key])
        if key == "debate_room":
            out.append(FR["risks_and_missing_evidence"])
        if key == "solution_architecture":
            out.append(FR["uml_diagrams"])
    return out


# Template catalogue ---------------------------------------------------------------

def test_catalogue_has_the_three_cdc_roles_plus_the_complete_report():
    assert set(templates.TEMPLATES) == {"business", "entrepreneur", "student", "consultant"}
    assert templates.sections_for("business") == ALL
    for name, sections in templates.TEMPLATES.items():
        assert sections[0] == "executive_summary", name
        assert len(set(sections)) == len(sections), name
        assert set(sections) <= set(ALL), name


def test_each_role_emphasises_what_it_needs():
    student = templates.sections_for("student")
    assert {"product_backlog", "sprint_planning", "solution_architecture"} <= set(student)
    # Technical design comes before the market for an academic dossier.
    assert student.index("solution_architecture") < student.index("market_study")
    entrepreneur = templates.sections_for("entrepreneur")
    assert entrepreneur.index("market_study") < entrepreneur.index("swot")
    assert "business_model_canvas" in entrepreneur and "product_backlog" not in entrepreneur
    consultant = templates.sections_for("consultant")
    assert consultant[1] == "debate_room" and "swot" in consultant


def test_unknown_template_is_refused_and_default_is_the_complete_report():
    with pytest.raises(ValueError):
        templates.sections_for("hacker")
    assert templates.normalize_template(None) == "business"
    assert templates.normalize_template(" Student ") == "student"


def test_every_template_has_a_cover_label_in_both_languages():
    for name in templates.TEMPLATES:
        assert labels_module.FR[f"template_{name}"] and labels_module.EN[f"template_{name}"]


# Word ---------------------------------------------------------------------------

def word(template: str) -> docx.Document:
    target = io.BytesIO()
    build_docx(assembled(template), "27/09/2026", {}, target)
    target.seek(0)
    return docx.Document(target)


@pytest.mark.parametrize("template", ["business", "entrepreneur", "student", "consultant"])
def test_word_report_follows_the_template(template):
    document = word(template)
    assert headings(document) == expected_headings(template)
    cover_text = "\n".join(c.text for t in document.tables[:1] for r in t.rows for c in r.cells)
    assert FR[f"template_{template}"] in cover_text


# PDF ----------------------------------------------------------------------------

@pytest.mark.parametrize("template", ["business", "student", "consultant"])
def test_pdf_report_follows_the_template(template):
    flow = build_full_flow(assembled(template), build_styles(), "27/09/2026", {})
    toc = [getattr(f, "toc_text", None) for f in flow if getattr(f, "toc_level", None) == 0]
    assert toc == expected_headings(template)


@pytest.mark.parametrize("template", ["business", "entrepreneur", "student", "consultant"])
def test_every_pdf_section_starts_on_a_new_page(template):
    # Visual RED 27 Sept: in the consultant order, "Etude de marche" started
    # on the SWOT page (the SWOT builder ends without a page break).
    flow = build_full_flow(assembled(template), build_styles(), "27/09/2026", {})
    for index, flowable in enumerate(flow):
        if getattr(flowable, "toc_level", None) == 0:
            assert type(flow[index - 1]).__name__ == "PageBreak", flowable.toc_text


# Endpoint -------------------------------------------------------------------------

def client(db: FakeDB) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(export_router_module.router)

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: OWNER
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


def project():
    return SimpleNamespace(id=31, title="Atelier Partagé", user_id=5,
                           analysis_data=analysis_data(), output_language="fr")


@pytest.mark.asyncio
async def test_endpoint_applies_and_records_the_template(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path))
    db = FakeDB(project())
    async with client(db) as c:
        response = await c.post("/projects/31/export/word?template=student")
    assert response.status_code == 200
    assert response.json()["file_name"] == "ForgeAI_Atelier_Partage_student_report.docx"
    row = db.added[0]
    assert row.template_used == "student"
    produced = docx.Document(str(tmp_path / row.file_path))
    assert headings(produced) == expected_headings("student")


@pytest.mark.asyncio
async def test_endpoint_without_template_keeps_the_complete_report(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path))
    db = FakeDB(project())
    async with client(db) as c:
        response = await c.post("/projects/31/export/pdf")
    assert response.json()["file_name"] == "ForgeAI_Atelier_Partage_business_plan.pdf"
    assert db.added[0].template_used == "business"


@pytest.mark.asyncio
async def test_unknown_template_is_rejected_before_any_work(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path))
    db = FakeDB(project())
    async with client(db) as c:
        response = await c.post("/projects/31/export/pdf?template=hacker")
    assert response.status_code == 422
    assert db.added == [] and db.sql == []
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


def test_frontend_lets_the_user_choose_the_profile():
    section = (FRONTEND / "app/projects/[id]/_sections/ExportSection.tsx").read_text(encoding="utf-8")
    for value in ("business", "entrepreneur", "student", "consultant"):
        assert f'value: "{value}"' in section, value
    assert "?template=${template}" in section
    assert "Profil du dossier" in section
