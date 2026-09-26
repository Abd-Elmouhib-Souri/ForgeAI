"""
Sprint 6.3 pitch deck contracts.

CDC 6.3: a 12-slide investor pitch deck (.pptx) generated from the SAME
assembled data and labels as the PDF / Word reports, stored and downloaded
through the private Sprint 6.1 storage.

Every assertion re-reads the produced .pptx with python-pptx.
"""

from __future__ import annotations

import io
import re
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from pptx import Presentation
from pptx.util import Emu

from app.config import settings
from app.database import get_db
from app.models import ExportFormat
from app.routers import export as export_router_module
from app.security import get_current_user
from app.services.export import labels as labels_module
from app.services.export.data_assembly import assemble_export_data
from app.services.export.pptx_builder import (
    MAX_BULLETS,
    MAX_CHARS,
    NARROW_BULLETS,
    NARROW_CHARS,
    build_pptx,
)
from tests.unit.test_export_word_contract import OWNER, PNG, FakeDB, analysis_data

FR = labels_module.FR


def build(language="fr", images=None, data=None) -> Presentation:
    assembled = assemble_export_data(
        analysis_data=analysis_data() if data is None else data,
        project_name="Atelier Partagé",
        output_language=language,
    )
    target = io.BytesIO()
    build_pptx(assembled, "27/09/2026", images or {}, target)
    target.seek(0)
    return Presentation(target)


def slide_texts(slide) -> list[str]:
    return [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]


def title_of(slide) -> str:
    return slide.shapes.title.text if slide.shapes.title is not None else slide_texts(slide)[0]


def test_deck_has_exactly_twelve_slides_in_pitch_order():
    deck = build()
    titles = [title_of(s) for s in deck.slides]
    assert len(titles) == 12
    assert titles[0] == "Atelier Partagé"
    assert titles[1:] == [
        FR["deck_problem"], FR["deck_solution"], FR["deck_market"], FR["deck_customers"],
        FR["deck_competition"], FR["deck_business_model"], FR["deck_swot"], FR["deck_score"],
        FR["deck_roadmap"], FR["deck_architecture"], FR["deck_verdict"],
    ]


def test_deck_is_widescreen():
    deck = build()
    assert (deck.slide_width, deck.slide_height) == (Emu(12192000), Emu(6858000))


def test_deck_carries_the_real_project_content():
    text = "\n".join(t for s in build().slides for t in slide_texts(s))
    for expected in ("Les artisans perdent du temps", "Une application de réservation",
                     "1 200 ateliers", "Sami", "Tableur partagé", "abonnement",
                     "GO conditionnel", "Interroger dix artisans.", "modular_monolith",
                     "Next.js", "WebSocket", "Sprint 1"):
        assert expected in text, expected


def test_score_slide_uses_a_native_editable_chart():
    score_slide = build().slides[8]
    charts = [shape for shape in score_slide.shapes if shape.has_chart]
    assert len(charts) == 1
    categories = list(charts[0].chart.plots[0].categories)
    assert len(categories) == 2  # market, team in the fixture


def test_architecture_slide_embeds_the_use_case_diagram_when_rendered():
    with_image = build(images={"use_case": PNG}).slides[10]
    assert any(shape.shape_type == 13 for shape in with_image.shapes)  # PICTURE
    without = build(images={}).slides[10]
    assert not any(shape.shape_type == 13 for shape in without.shapes)


def test_no_text_can_overflow_a_slide():
    long = analysis_data()
    long["problem"] = "Très long problème. " * 80
    long["final_report"]["decision"]["next_actions"] = [f"Action {i} " + "x" * 400 for i in range(20)]
    for slide in build(data=long).slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            paragraphs = [p.text for p in shape.text_frame.paragraphs if p.text]
            assert len(paragraphs) <= MAX_BULLETS + 1  # + optional subtitle line
            assert all(len(p) <= MAX_CHARS for p in paragraphs), paragraphs


def test_english_project_gets_an_english_deck():
    titles = [title_of(s) for s in build(language="en").slides]
    assert titles[1] == "The problem" and titles[-1] == "Verdict and next steps"


def test_empty_project_still_builds_twelve_honest_slides():
    deck = build(data={})
    assert len(deck.slides) == 12
    text = "\n".join(t for s in deck.slides for t in slide_texts(s))
    assert FR["no_data"] in text
    assert FR["architecture_not_generated"] in text


@pytest.mark.asyncio
async def test_pitch_deck_endpoint_is_private_offloaded_and_named(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", str(tmp_path))
    offloaded = []
    real_to_thread = export_router_module.asyncio.to_thread

    async def spy(func, *args, **kwargs):
        offloaded.append(func)
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(export_router_module.asyncio, "to_thread", spy)
    project = SimpleNamespace(id=31, title="Atelier Partagé", user_id=5,
                              analysis_data=analysis_data(), output_language="fr")
    db = FakeDB(project)
    app = FastAPI()
    app.include_router(export_router_module.router)

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: OWNER
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
        response = await client.post("/projects/31/export/powerpoint")

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "powerpoint"
    assert body["file_name"] == "ForgeAI_Atelier_Partage_pitch_deck.pptx"
    row = db.added[0]
    assert row.format == ExportFormat.POWERPOINT
    assert re.fullmatch(r"31/[0-9a-f]{32}\.pptx", row.file_path)
    assert len(Presentation(str(tmp_path / row.file_path)).slides) == 12
    assert offloaded and "projects.user_id = 5" in db.sql[0]


def test_frontend_offers_the_pitch_deck_through_the_same_private_flow():
    from tests.unit.test_export_word_contract import FRONTEND

    section = (FRONTEND / "app/projects/[id]/_sections/ExportSection.tsx").read_text(encoding="utf-8")
    assert 'runExport("powerpoint")' in section
    assert "Exporter le pitch deck" in section


def test_three_column_slides_use_the_narrow_text_budget():
    # Visual RED 27 Sept: Market and Business model text overflowed 1/3 columns.
    long = analysis_data()
    long["business_model_canvas"]["value_propositions"] = ["y" * 300 for _ in range(8)]
    long["market_study"]["customer_segments"] = ["z" * 300 for _ in range(8)]
    deck = build(data=long)
    for index in (3, 6):  # Market, Business model
        for shape in deck.slides[index].shapes:
            if not shape.has_text_frame:
                continue
            bullets = [p.text for p in shape.text_frame.paragraphs if p.text.startswith("• ")]
            assert len(bullets) <= NARROW_BULLETS
            assert all(len(b) <= NARROW_CHARS for b in bullets)


def test_solution_slide_falls_back_on_real_project_data():
    data = analysis_data()
    data["solution"] = ""
    data["debate_room"]["judge"]["improved_idea"] = "Commencer par un seul atelier pilote."
    text = "\n".join(slide_texts(build(data=data).slides[2]))
    assert "Commencer par un seul atelier pilote." in text
    assert FR["no_data"] not in text.split("\n")[1]
