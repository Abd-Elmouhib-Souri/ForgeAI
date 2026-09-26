"""
Sprint 6.2 Word export contracts (+ shared accented labels).

CDC 6.2: export the complete project report as an editable .docx built
from the SAME assembled data as the PDF (data_assembly.py), stored and
downloaded through the private Sprint 6.1 storage.

Observed REDs carried into this slice:
  L1  PDF labels printed without accents ("Resume executif", "Genere par")
      and always in French, even for English projects.
  L2  Project-specific stack layers (e.g. real-time messaging) vanished from
      the export: only the four core layers were assembled.

Every document assertion re-reads the produced .docx with python-docx:
behaviour, not source text.
"""

from __future__ import annotations

import datetime
import io
import re
from pathlib import Path
from types import SimpleNamespace

import docx
import httpx
import pytest
from fastapi import FastAPI

from app.config import settings
from app.database import get_db
from app.models import ExportFormat
from app.routers import export as export_router_module
from app.security import get_current_user
from app.services.export import labels as labels_module
from app.services.export.data_assembly import assemble_export_data
from app.services.export.docx_builder import build_docx

BACKEND = Path(__file__).resolve().parents[2]
FRONTEND = BACKEND.parent / "frontend"
OWNER = SimpleNamespace(id=5)

def _png(width: int = 400, height: int = 300) -> bytes:
    """Real PNG standing in for a Kroki-rendered UML diagram."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


PNG = _png()


def real_architecture_envelope() -> dict:
    """Architecture exactly as solution_architecture_plan_service persists it."""
    from app.schemas import solution_architecture as sa
    from app.services.solution_architecture_plan_service import serialize

    def layer(tech):
        return sa.TechnologyLayerDecisionV1(status="recommended", technology=tech,
                                            justification=f"{tech} convient au MVP.", alternatives=[], conditions=[])

    def diagram(kind):
        return sa.UMLDiagramV1(diagram_type=kind, syntax="plantuml",
                               source="@startuml\nactor Artisan\n@enduml", validation_status="pending")

    canonical = sa.CanonicalSolutionArchitectureV1(
        schema_version="canonical_solution_architecture_v1",
        context_fingerprint="ctx-word-001",
        architecture=sa.ArchitectureRecommendationV1(
            style="modular_monolith", rationale=["Petite équipe."],
            quality_attributes=["maintenabilité"], constraints_addressed=["équipe de deux"],
            alternatives=["microservices écartés"], risks=["couplage entre modules"],
        ),
        stack=sa.TechnologyStackV1(
            frontend=layer("Next.js"), backend=layer("FastAPI"), database=layer("PostgreSQL"),
            infrastructure=layer("Docker"), additional_layers={"realtime_messaging": layer("WebSocket")},
        ),
        uml=sa.UMLDiagramBundleV1(use_case=diagram("use_case"), class_diagram=diagram("class"),
                                  sequence=diagram("sequence"), activity=diagram("activity")),
        database=sa.DatabaseDesignV1(
            dialect="postgresql", sql="CREATE TABLE postes (id INTEGER PRIMARY KEY);",
            tables=["postes"], relationships=[], validation_status="pending",
            table_definitions=[sa.DatabaseTableV1(
                name="postes", description="Postes de travail réservables.",
                columns=[sa.DatabaseColumnV1(name="id", data_type="INTEGER", primary_key=True, nullable=False)],
                foreign_keys=[])],
        ),
        assumptions=["Un atelier possède plusieurs postes."], warnings=[], confidence=0.78,
    )
    return serialize(canonical)


def analysis_data() -> dict:
    """Neutral, complete fixture (a shared-workshop booking idea)."""
    return {
        "problem": "Les artisans perdent du temps à réserver des postes de travail.",
        "solution": "Une application de réservation de postes partagés.",
        "final_report": {
            "context": {"industry_user_input": "Services", "target_region": "Tunisie"},
            "decision": {
                "verdict_code": "conditional_go",
                "final_recommendation": "Lancer un pilote limité.",
                "debate_synthesis": "Le besoin est réel mais le paiement reste à prouver.",
                "critical_risks": ["adoption lente"],
                "next_actions": ["Interroger dix artisans."],
            },
        },
        "market_study": {"summary": "Marché de niche en croissance.", "market_size": "1 200 ateliers"},
        "swot": {"swot_matrix": {"strengths": ["simplicité"], "weaknesses": ["notoriété"],
                                 "opportunities": ["tiers-lieux"], "threats": ["tableurs"]}},
        "business_model_canvas": {"value_propositions": ["réserver en 30 s"], "revenue_streams": ["abonnement"]},
        "competitive_analysis": {"local_competitors": [{"name": "Tableur partagé"}]},
        "forgecrawler": {"canonical_source_ledger": {"sources": [
            {"title": "Étude tiers-lieux", "url": "https://example.org/tiers-lieux",
             "canonical_category": "market_evidence", "source_relevance_score": 0.8},
        ]}},
        "startup_score": {"score_out_of_10": 7.2, "breakdown": {"market": 7, "team": 6}},
        "debate_room": {"committee": [{"id": "cfo", "role": "Directeur financier", "mandate": "coûts"}],
                        "judge": {"verdict_code": "conditional_go", "critical_risks": ["adoption lente"],
                                  "committee_votes": [
                            {"member": "cfo", "vote": "go", "confidence": 0.6, "reason": "coûts maîtrisés"}]}},
        "persona_builder": {"personas": [{"persona_name": "Sami", "role": "Artisan",
                                          "main_pain": "files d'attente", "goals": ["gagner du temps"]}]},
        "project_manager": {"current": {
            "settings": {"sprint_count": 2, "sprint_duration_days": 14, "planned_velocity": 20, "team_size": 2},
            "metrics": {"total_story_points": 8, "assigned_story_points": 8},
            "epics": [{"epic_id": "EP-001", "title": "Réservation"}],
            "stories": [
                {"story_id": "US-001", "title": "Réserver un poste", "priority": "must", "story_points": 5,
                 "story": "En tant qu'artisan, je veux réserver un poste afin de travailler.",
                 "acceptance_criteria": ["Le poste réservé n'est plus disponible."]},
                {"story_id": "US-002", "title": "Annuler", "priority": "should", "story_points": 3,
                 "story": "En tant qu'artisan, je veux annuler afin de libérer le poste.",
                 "acceptance_criteria": []},
            ],
            "sprints": [{"sprint_number": 1, "planned_story_points": 8, "story_ids": ["US-001", "US-002"]}],
            "scrum_master_advice": [{"rationale": "Valider US-001 avant US-002."}],
        }},
        # REAL persisted shape, produced by the service itself (a hand-written
        # dict hid the 27 Sept RED: the export read the wrong level).
        "solution_architecture": real_architecture_envelope(),
    }


def build(language="fr", images=None, data=None) -> docx.Document:
    assembled = assemble_export_data(
        analysis_data=analysis_data() if data is None else data,
        project_name="Atelier Partagé",
        output_language=language,
    )
    target = io.BytesIO()
    build_docx(assembled, "27/09/2026", images or {}, target)
    target.seek(0)
    return docx.Document(target)


def headings(document, level=1):
    return [p.text for p in document.paragraphs if p.style.name == f"Heading {level}"]


def all_text(document) -> str:
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


# L1: shared labels -------------------------------------------------------------

def test_labels_are_accented_and_bilingual_with_identical_keys():
    assert set(labels_module.FR) == set(labels_module.EN)
    fr = labels_module.labels_for("fr")
    assert fr["executive_summary"] == "Résumé exécutif"
    assert fr["market_study"] == "Étude de marché"
    assert fr["generated_by"] == "Généré par"
    assert labels_module.labels_for("en")["executive_summary"] == "Executive summary"
    assert labels_module.labels_for("klingon") is labels_module.FR  # platform default


def test_pdf_builder_prints_no_hard_coded_unaccented_label():
    import ast

    # Printed strings only (string constants), not section comments.
    tree = ast.parse((BACKEND / "app/services/export/pdf_builder.py").read_text(encoding="utf-8"))
    source = "\n".join(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    for legacy in ("Resume executif", "Genere par", "Etude de marche", "Description de l'idee",
                   "Base de donnees", "Sources verifiees", "Priorite", "Synthese du comite"):
        assert legacy not in source, legacy


# L2: assembly ---------------------------------------------------------------------

def test_additional_stack_layers_are_exported():
    data = assemble_export_data(analysis_data=analysis_data(), project_name="x")
    assert data["solution_architecture"]["stack"]["realtime_messaging"] == "WebSocket"
    assert data["language"] == "fr"


def test_architecture_is_read_from_the_persisted_canonical_payload():
    # RED 27 Sept 2026: empty "Architecture technique" page in the PDF.
    arch = assemble_export_data(analysis_data=analysis_data(), project_name="x")["solution_architecture"]
    assert arch["style"] == "modular_monolith"
    assert arch["quality_attributes"] == ["maintenabilité"]
    assert arch["constraints_addressed"] == ["équipe de deux"]
    assert arch["risks"] == ["couplage entre modules"]
    assert arch["alternatives"] == ["microservices écartés"]
    assert [l["layer"] for l in arch["stack_layers"]] == [
        "frontend", "backend", "database", "infrastructure", "realtime_messaging"]
    assert arch["stack_layers"][0]["justification"] == "Next.js convient au MVP."
    assert set(arch["uml_diagrams"]) == {"use_case", "class_diagram", "sequence", "activity"}
    assert arch["database_tables"][0]["name"] == "postes"
    assert arch["database_sql"].startswith("CREATE TABLE postes")
    assert arch["assumptions"] == ["Un atelier possède plusieurs postes."]
    assert arch["confidence"] == 0.78


# 6.2: document content ------------------------------------------------------------

def test_word_report_has_every_section_in_pdf_order():
    fr = labels_module.FR
    assert headings(build()) == [
        fr["executive_summary"], fr["idea_description"], fr["market_study"], fr["swot"],
        fr["business_model_canvas"], fr["competitive_analysis"], fr["sources"],
        fr["startup_score"], fr["debate_room"], fr["risks_and_missing_evidence"],
        fr["personas"], fr["product_backlog"], fr["sprint_planning"],
        fr["solution_architecture"], fr["uml_diagrams"],
    ]


def test_word_report_carries_the_real_project_content():
    text = all_text(build())
    for expected in ("Atelier Partagé", "Généré par", "GO conditionnel", "Lancer un pilote limité.",
                     "En tant qu'artisan, je veux réserver un poste", "Le poste réservé n'est plus disponible.",
                     "Valider US-001 avant US-002.", "WebSocket", "CREATE TABLE postes",
                     "https://example.org/tiers-lieux", "Preuve de marché", "Directeur financier"):
        assert expected in text, expected
    assert "Resume executif" not in text


def test_backlog_is_a_real_table_with_one_row_per_story():
    document = build()
    backlog = next(t for t in document.tables if t.rows[0].cells[0].text == "ID")
    assert [c.text for c in backlog.rows[0].cells] == ["ID", "User story", "Priorité", "Points"]
    assert [r.cells[0].text for r in backlog.rows[1:]] == ["US-001", "US-002"]


def test_rendered_uml_diagrams_are_embedded_as_images():
    document = build(images={"use_case": PNG, "class_diagram": PNG})
    assert len(document.inline_shapes) == 2
    # Without Kroki images the document still builds, with an honest note.
    assert "Rendu visuel indisponible" in all_text(build(images={}))


def test_english_project_gets_an_english_report():
    document = build(language="en")
    assert headings(document)[0] == "Executive summary"
    assert "Généré par" not in all_text(document)


def test_empty_project_still_builds_an_honest_document():
    document = build(data={})
    text = all_text(document)
    assert labels_module.FR["architecture_not_generated"] in text
    assert labels_module.FR["no_data"] in text


# 6.2: endpoint ---------------------------------------------------------------------

class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    def __init__(self, *rows):
        self.rows = list(rows)
        self.sql: list[str] = []
        self.added: list = []

    async def execute(self, statement):
        self.sql.append(str(statement.compile(compile_kwargs={"literal_binds": True})))
        return _Result(self.rows.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        obj.id = 9
        obj.created_at = datetime.datetime(2026, 9, 27, tzinfo=datetime.timezone.utc)


@pytest.mark.asyncio
async def test_word_export_endpoint_is_private_offloaded_and_downloadable(tmp_path, monkeypatch):
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
        response = await client.post("/projects/31/export/word")

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "word"
    assert body["download_url"] == "/projects/31/exports/9/download"
    assert body["file_name"] == "ForgeAI_Atelier_Partage_business_plan.docx"
    row = db.added[0]
    assert row.format == ExportFormat.WORD
    assert re.fullmatch(r"31/[0-9a-f]{32}\.docx", row.file_path)
    produced = docx.Document(str(tmp_path / row.file_path))
    assert headings(produced)[0] == "Résumé exécutif"
    assert offloaded, "python-docx must run in a worker thread"
    assert "projects.user_id = 5" in db.sql[0]


def test_frontend_offers_word_export_through_the_same_private_flow():
    section = (FRONTEND / "app/projects/[id]/_sections/ExportSection.tsx").read_text(encoding="utf-8")
    assert "/export/${format}" in section
    assert "Exporter en Word" in section
    assert 'runExport("word")' in section and 'runExport("pdf")' in section
