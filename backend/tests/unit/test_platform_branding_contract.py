"""
Platform branding contract.

Product decision (27 Sept 2026): the platform is "ForgeAI". Every customer
report printed "Généré par DotJcom ForgeAI", "Entreprise : DotJcom Ltd —
Soliman, Nabeul, Tunisie" on the cover and "DotJcom Ltd" in every footer,
although a SaaS report belongs to the customer. Emails, the browser title
and the login page also said "DotJcom ForgeAI".

Contract: no user-facing surface (exports, emails, frontend) names DotJcom;
the reports carry no company line.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import docx
from pptx import Presentation

from app.config import Settings
from app.services.export import labels as labels_module
from app.services.export.data_assembly import assemble_export_data
from app.services.export.docx_builder import build_docx
from app.services.export.pdf_builder import build_full_flow
from app.services.export.pdf_design import build_styles, make_page_callbacks
from app.services.export.pptx_builder import build_pptx
from tests.unit.test_export_word_contract import analysis_data

BACKEND = Path(__file__).resolve().parents[2]
FRONTEND = BACKEND.parent / "frontend"


def data():
    return assemble_export_data(analysis_data=analysis_data(), project_name="Atelier Partagé")


def test_word_report_names_only_forgeai():
    target = io.BytesIO()
    build_docx(data(), "27/09/2026", {}, target)
    target.seek(0)
    document = docx.Document(target)
    text = "\n".join(
        [p.text for p in document.paragraphs]
        + [c.text for t in document.tables for r in t.rows for c in r.cells]
        + [p.text for s in document.sections for p in s.footer.paragraphs]
    )
    assert "DotJcom" not in text
    assert "Généré par ForgeAI" in text
    assert labels_module.FR["company"] not in text  # no "Entreprise" row


def test_pdf_report_names_only_forgeai():
    flow = build_full_flow(data(), build_styles(), "27/09/2026", {})
    texts = []
    for flowable in flow:
        if hasattr(flowable, "getPlainText"):
            texts.append(flowable.getPlainText())
        for row in getattr(flowable, "_cellvalues", []) or []:
            for cell in row:
                texts.append(cell.getPlainText() if hasattr(cell, "getPlainText") else str(cell))
    text = "\n".join(texts)
    assert "DotJcom" not in text
    assert labels_module.FR["company"] not in text


def test_pdf_page_furniture_names_only_forgeai():
    drawn: list[str] = []

    class Canvas:
        def __getattr__(self, name):
            def record(*args, **kwargs):
                drawn.extend(str(a) for a in args if isinstance(a, str))
            return record

    doc = type("Doc", (), {"page": 3})()
    for callback in make_page_callbacks("Atelier Partagé"):
        callback(Canvas(), doc)
    assert not any("DotJcom" in line for line in drawn), drawn
    assert "Généré par ForgeAI" in drawn


def test_pitch_deck_names_only_forgeai():
    target = io.BytesIO()
    build_pptx(data(), "27/09/2026", {}, target)
    target.seek(0)
    text = "\n".join(
        shape.text_frame.text
        for slide in Presentation(target).slides
        for shape in slide.shapes
        if shape.has_text_frame
    )
    assert "DotJcom" not in text


def test_platform_name_defaults_to_forgeai():
    defaults = Settings.model_fields
    assert defaults["APP_NAME"].default == "ForgeAI"
    assert defaults["SMTP_FROM_NAME"].default == "ForgeAI"


def test_no_user_facing_source_names_dotjcom():
    surfaces = [
        BACKEND / "app/mailer.py",
        BACKEND / "app/services/export/pdf_design.py",
        BACKEND / "app/services/export/pdf_builder.py",
        BACKEND / "app/services/export/docx_builder.py",
        FRONTEND / "app/layout.tsx",
        FRONTEND / "app/page.tsx",
        FRONTEND / "app/login/page.tsx",
        FRONTEND / "app/admin/login/page.tsx",
    ]
    offenders = {
        str(path.relative_to(BACKEND.parent)): re.findall(r".{0,30}DotJcom.{0,30}", path.read_text(encoding="utf-8"))
        for path in surfaces
        if "DotJcom" in path.read_text(encoding="utf-8")
    }
    assert offenders == {}
