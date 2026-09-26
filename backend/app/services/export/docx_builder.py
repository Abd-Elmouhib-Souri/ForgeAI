"""
Sprint 6.2: editable Word (.docx) project report.

Same content, same order and same labels as the PDF (pdf_builder.py): both
consume assemble_export_data() and labels.labels_for(); nothing here reads
analysis_data directly. The document uses real Word heading styles, so the
navigation pane and an auto table of contents work in Word / LibreOffice.

Synchronous and network-free on purpose: the router runs it inside
asyncio.to_thread(), and UML diagrams arrive as PNG bytes already rendered
by Kroki (a missing image prints an honest note, never a broken picture).
"""

from __future__ import annotations

import io
from typing import Any, BinaryIO

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .labels import (
    DIAGRAM_ORDER,
    category_label,
    criteria_label,
    labels_for,
    layer_label,
    status_label,
)

# Same palette as pdf_design.py (violet brand, slate text).
PRIMARY = RGBColor(0x7C, 0x3A, 0xED)
PRIMARY_HEX = "7C3AED"
SURFACE_HEX = "F8FAFC"
TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)
CONTENT_WIDTH = Cm(16)
MAX_DIAGRAM_HEIGHT = Cm(20)

_VERDICT_KEYS = {
    "STRONG_GO": "verdict_strong_go",
    "CONDITIONAL_GO": "verdict_conditional_go",
    "NO_GO": "verdict_no_go",
    "INSUFFICIENT_EVIDENCE": "verdict_insufficient_evidence",
}


class _Report:
    """Small writer around python-docx keeping the labels at hand."""

    def __init__(self, labels: dict[str, str]) -> None:
        self.L = labels
        self.doc = Document()
        self._setup_styles()

    # -- styles & primitives -------------------------------------------------

    def _setup_styles(self) -> None:
        normal = self.doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        for name, size in (("Heading 1", 18), ("Heading 2", 13), ("Title", 28)):
            style = self.doc.styles[name]
            style.font.color.rgb = PRIMARY
            style.font.size = Pt(size)
        for section in self.doc.sections:
            section.left_margin = section.right_margin = Cm(2.5)

    def heading(self, text: str, level: int = 1) -> None:
        self.doc.add_heading(text, level=level)

    def para(self, text: Any, *, muted: bool = False, bold: bool = False, size: float | None = None) -> None:
        value = str(text or "").strip()
        if not value:
            return
        run = self.doc.add_paragraph().add_run(value)
        run.bold = bold
        if muted:
            run.font.color.rgb = TEXT_MUTED
        if size:
            run.font.size = Pt(size)

    def bullets(self, items: Any) -> None:
        for item in items or []:
            text = str(item or "").strip()
            if text:
                self.doc.add_paragraph(text, style="List Bullet")

    def titled_bullets(self, key: str, items: Any) -> None:
        if items:
            self.heading(self.L[key], 2)
            self.bullets(items)

    def titled_text(self, key: str, text: Any) -> None:
        if str(text or "").strip():
            self.heading(self.L[key], 2)
            self.para(text)

    def empty_note(self) -> None:
        self.para(self.L["no_data"], muted=True)

    def page_break(self) -> None:
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    @staticmethod
    def _shade(cell, hex_color: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:color"), "auto")
        shading.set(qn("w:fill"), hex_color)
        tc_pr.append(shading)

    def table(self, header: list[str], rows: list[list[Any]], widths: list[float] | None = None):
        """Grid table, violet header row, zebra body, header repeated per page."""
        table = self.doc.add_table(rows=1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for cell, text in zip(table.rows[0].cells, header):
            cell.text = ""
            run = cell.paragraphs[0].add_run(text)
            run.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            self._shade(cell, PRIMARY_HEX)
        # Repeat the header row on every page.
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        tr_pr.append(repeat)
        for index, values in enumerate(rows):
            cells = table.add_row().cells
            for cell, value in zip(cells, values):
                self._fill_cell(cell, value)
                if index % 2:
                    self._shade(cell, SURFACE_HEX)
        if widths:
            for row in table.rows:
                for cell, width in zip(row.cells, widths):
                    cell.width = Cm(width)
        self.doc.add_paragraph()
        return table

    @staticmethod
    def _fill_cell(cell, value: Any) -> None:
        """A cell value is text, or a list: first item = text, rest = bullets."""
        cell.text = ""
        if isinstance(value, list):
            head, *items = value or [""]
            cell.paragraphs[0].add_run(str(head or ""))
            for item in items:
                if str(item or "").strip():
                    cell.add_paragraph(f"• {item}")
        else:
            cell.paragraphs[0].add_run("" if value is None else str(value))

    def picture(self, png: bytes) -> None:
        shape = self.doc.add_picture(io.BytesIO(png), width=CONTENT_WIDTH)
        # Tall diagrams (sequence) must fit the page height too.
        if shape.height > MAX_DIAGRAM_HEIGHT:
            ratio = MAX_DIAGRAM_HEIGHT / shape.height
            shape.height = int(shape.height * ratio)
            shape.width = int(shape.width * ratio)

    def footer(self) -> None:
        """'Généré par DotJcom ForgeAI · Page N' on every page."""
        paragraph = self.doc.sections[0].footer.paragraphs[0]
        run = paragraph.add_run(f"{self.L['generated_by']} DotJcom ForgeAI · {self.L['page']} ")
        run.font.size = Pt(8)
        run.font.color.rgb = TEXT_MUTED
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), "PAGE")
        paragraph._p.append(field)

    def verdict_label(self, code: str) -> str:
        upper = str(code or "").upper()
        key = _VERDICT_KEYS.get(upper)
        return self.L[key] if key else (upper or self.L["not_available"])


# ---------------------------------------------------------------------------
# Sections (same order as pdf_builder.build_full_flow)
# ---------------------------------------------------------------------------

def _cover(r: _Report, data: dict[str, Any], generated_at: str) -> None:
    L, cover = r.L, data["cover"]
    r.para(L["brand"], muted=True, bold=True)
    r.para(L["report_kind"], muted=True)
    r.doc.add_paragraph(cover["title"], style="Title")
    r.para(" · ".join(b for b in (cover.get("sector"), cover.get("region")) if b), muted=True, size=13)

    score = data["startup_score"].get("score_out_of_10")
    score_text = f"{score:.1f}/10" if isinstance(score, (int, float)) else "—"
    identity = [
        (L["project"], cover["title"]),
        (L["type"], L["report_type"]),
        (L["company"], "DotJcom Ltd — Soliman, Nabeul, Tunisie"),
        (L["date"], generated_at),
        (L["classification"], L["confidential"]),
        (L["generated_by"], "DotJcom ForgeAI"),
        (L["stat_startup_score"], score_text),
        (L["stat_personas"], str(len(data["personas"]))),
        (L["stat_user_stories"], str(len(data["backlog"]["stories"]))),
        (L["stat_verified_sources"], str(len(data["sources"]))),
    ]
    table = r.doc.add_table(rows=0, cols=2)
    for label, value in identity:
        cells = table.add_row().cells
        cells[0].text = ""
        cells[0].paragraphs[0].add_run(label).bold = True
        cells[1].text = value or "—"
    r.page_break()


def _executive_summary(r: _Report, data: dict[str, Any]) -> None:
    summary = data["executive_summary"]
    r.heading(r.L["executive_summary"])
    r.para(r.verdict_label(summary.get("verdict_code")), bold=True, size=13)
    r.para(summary.get("final_recommendation"))
    r.titled_text("committee_synthesis", summary.get("debate_synthesis"))
    r.titled_bullets("critical_risks", summary.get("critical_risks"))
    r.titled_bullets("next_actions", summary.get("next_actions"))


def _description(r: _Report, data: dict[str, Any]) -> None:
    desc = data["description"]
    r.heading(r.L["idea_description"])
    r.titled_text("problem", desc.get("problem"))
    r.titled_text("proposed_solution", desc.get("solution"))
    score = desc.get("innovation_breakdown_score") or desc.get("innovation_score")
    if score is not None:
        r.titled_text("innovation_score", f"{score:.1f} / 10" if isinstance(score, float) else f"{score} / 10")


def _market_study(r: _Report, data: dict[str, Any]) -> None:
    market = data["market_study"]
    r.heading(r.L["market_study"])
    r.para(market.get("summary"))
    r.titled_text("market_size", market.get("market_size"))
    r.titled_text("target_market", market.get("target_market"))
    r.titled_bullets("customer_segments", market.get("customer_segments"))
    r.titled_bullets("market_trends", market.get("market_trends"))
    r.titled_bullets("adoption_barriers", market.get("adoption_barriers"))
    r.titled_bullets("recommendations", market.get("recommendations"))


def _swot(r: _Report, data: dict[str, Any]) -> None:
    L, swot = r.L, data["swot"]
    r.heading(L["swot"])
    r.para(swot.get("summary"))
    quadrant = lambda key: [L[key].upper(), *(swot.get(key) or [])]  # noqa: E731
    table = r.doc.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    for cell, key in zip(
        (table.cell(0, 0), table.cell(0, 1), table.cell(1, 0), table.cell(1, 1)),
        ("strengths", "weaknesses", "opportunities", "threats"),
    ):
        r._fill_cell(cell, quadrant(key))
        cell.paragraphs[0].runs[0].bold = True
    r.doc.add_paragraph()
    r.titled_bullets("strategic_recommendations", swot.get("strategic_recommendations"))


def _business_model_canvas(r: _Report, data: dict[str, Any]) -> None:
    L, bmc = r.L, data["business_model_canvas"]
    r.heading(L["business_model_canvas"])
    r.para(L["bmc_intro"], muted=True)
    pillars = (
        ("bmc_pillar_infrastructure", ("key_partnerships", "key_activities", "key_resources")),
        ("bmc_pillar_offer", ("value_proposition",)),
        ("bmc_pillar_customers", ("customer_relationships", "channels", "customer_segments")),
        ("bmc_pillar_finances", ("cost_structure", "revenue_streams")),
    )
    rows = [
        [L[pillar], [L[block], *(bmc.get(block) or [])]]
        for pillar, blocks in pillars
        for block in blocks
    ]
    r.table([L["business_model_canvas"], ""], rows, widths=[4, 12])


def _competitive_analysis(r: _Report, data: dict[str, Any]) -> None:
    comp = data["competitive_analysis"]
    r.heading(r.L["competitive_analysis"])
    r.para(comp.get("market_gap"))
    r.titled_bullets("local_competitors", comp.get("local_competitors"))
    r.titled_bullets("local_adjacent_solutions", comp.get("local_adjacent_solutions"))
    r.titled_bullets("international_benchmarks", comp.get("international_benchmarks"))
    r.titled_bullets("competitive_advantages", comp.get("competitive_advantages"))
    r.titled_bullets("analysis_limitations", comp.get("limitations"))


def _sources(r: _Report, data: dict[str, Any]) -> None:
    L, sources = r.L, data["sources"]
    r.heading(L["sources"])
    if not sources:
        r.empty_note()
        return
    r.para(L["sources_intro"], muted=True)
    rows = []
    for source in sources:
        score = source.get("relevance_score")
        rows.append([
            "\n".join(v for v in (source.get("title"), source.get("url")) if v),
            category_label(L, source.get("category") or ""),
            f"{score:.0%}" if isinstance(score, (int, float)) else "—",
        ])
    r.table([L["source"], L["category"], L["relevance"]], rows, widths=[10, 4, 2])


def _startup_score(r: _Report, data: dict[str, Any]) -> None:
    L, score = r.L, data["startup_score"]
    r.heading(L["startup_score"])
    value = score.get("score_out_of_10")
    if value is not None:
        r.para(f"{value:.1f} / 10" if isinstance(value, float) else f"{value} / 10", bold=True, size=20)
    r.para(score.get("score_explanation"))
    breakdown = {k: v for k, v in (score.get("breakdown") or {}).items() if v is not None}
    if breakdown:
        r.heading(L["score_breakdown"], 2)
        r.table(
            [L["score_breakdown"], "/ 10"],
            [[criteria_label(L, key).replace("\n", " "), value] for key, value in breakdown.items()],
            widths=[12, 4],
        )
    r.titled_bullets("strengths", score.get("strengths"))
    r.titled_bullets("weaknesses", score.get("weaknesses"))
    r.titled_bullets("recommendations", score.get("recommendations"))


def _debate_room(r: _Report, data: dict[str, Any]) -> None:
    L, debate = r.L, data["debate_room"]
    r.heading(L["debate_room"])
    if not debate.get("votes") and not debate.get("committee"):
        r.empty_note()
    else:
        r.para(
            f"{debate.get('rounds_count', 0)} {L['debate_rounds']} · "
            f"{len(debate.get('committee', []))} {L['committee_members']}",
            muted=True,
        )
        r.para(r.verdict_label(debate.get("verdict_code")), bold=True, size=13)
        metrics = [
            (L["potential_score"], debate.get("potential_score")),
            (L["confidence_score"], debate.get("confidence_score")),
            (L["execution_readiness_score"], debate.get("execution_readiness_score")),
            (L["investment_attractiveness_score"], debate.get("investment_attractiveness_score")),
        ]
        r.table(
            [label for label, _ in metrics],
            [[f"{v:.1f}" if isinstance(v, float) else (v if v is not None else "—") for _, v in metrics]],
        )
        r.para(debate.get("debate_synthesis"))
        if debate.get("committee"):
            r.heading(L["committee_composition"], 2)
            r.table(
                [L["role"], L["mandate"]],
                [
                    [m["role"] + ("" if m["voting_member"] else f" ({L['consultative']})"), m["mandate"]]
                    for m in debate["committee"]
                ],
                widths=[5, 11],
            )
        if debate.get("votes"):
            r.heading(L["committee_votes"], 2)
            r.table(
                [L["member"], L["vote"], L["confidence"], L["justification"]],
                [
                    [
                        v["member"],
                        v["vote"],
                        f"{v['confidence']:.0%}" if isinstance(v.get("confidence"), (int, float)) else "—",
                        v["reason"],
                    ]
                    for v in debate["votes"]
                ],
                widths=[3.5, 2.5, 2, 8],
            )

    # Same conditional page as the PDF.
    if debate.get("critical_risks") or debate.get("missing_evidence"):
        r.heading(L["risks_and_missing_evidence"])
        r.titled_bullets("critical_risks", debate.get("critical_risks"))
        r.titled_bullets("missing_evidence", debate.get("missing_evidence"))
    r.titled_bullets("go_conditions", debate.get("go_conditions"))
    r.titled_bullets("no_go_conditions", debate.get("no_go_conditions"))
    if debate.get("final_recommendation") or debate.get("improved_idea"):
        r.heading(L["committee_final_recommendation"], 2)
        r.para(debate.get("final_recommendation"))
        if debate.get("improved_idea"):
            r.para(f"{L['improved_idea']} : {debate['improved_idea']}")


def _personas(r: _Report, data: dict[str, Any]) -> None:
    L, personas = r.L, data["personas"]
    r.heading(L["personas"])
    if not personas:
        r.empty_note()
    for persona in personas:
        r.heading(persona.get("name") or L["persona"], 2)
        r.para(persona.get("role"), muted=True)
        r.para(persona.get("profile"))
        if persona.get("main_pain"):
            r.para(f"{L['main_pain']} : {persona['main_pain']}")
        if persona.get("goals"):
            r.para(L["goals"], bold=True)
            r.bullets(persona["goals"])
        if persona.get("frustrations"):
            r.para(L["frustrations"], bold=True)
            r.bullets(persona["frustrations"])
        if persona.get("expected_value"):
            r.para(f"{L['expected_value']} : {persona['expected_value']}")


def _backlog(r: _Report, data: dict[str, Any]) -> None:
    L, stories = r.L, data["backlog"].get("stories", [])
    r.heading(L["product_backlog"])
    if not stories:
        r.empty_note()
        return
    rows = []
    for story in stories:
        criteria = [
            c.get("statement") if isinstance(c, dict) else c
            for c in story.get("acceptance_criteria") or []
        ]
        rows.append([
            story.get("story_id", ""),
            [story.get("story", ""), *criteria],
            story.get("priority", ""),
            story.get("story_points", ""),
        ])
    r.table([L["id"], L["user_story"], L["priority"], L["points"]], rows, widths=[2, 10.5, 2, 1.5])


def _sprint_planning(r: _Report, data: dict[str, Any]) -> None:
    L, sprint = r.L, data["sprint_planning"]
    r.heading(L["sprint_planning"])
    bits = []
    if sprint.get("sprint_count"):
        bits.append(f"{sprint['sprint_count']} {L['sprints']}")
    if sprint.get("sprint_duration_days"):
        bits.append(f"{sprint['sprint_duration_days']} {L['days_per_sprint']}")
    if sprint.get("planned_velocity"):
        bits.append(f"{L['planned_velocity']} {sprint['planned_velocity']} {L['story_points_short']}")
    if sprint.get("team_size"):
        bits.append(f"{L['team_of']} {sprint['team_size']}")
    r.para(" · ".join(bits), muted=True)
    if not sprint.get("sprints"):
        r.empty_note()
    for s in sprint.get("sprints", []):
        r.heading(f"{L['sprint']} {s.get('sprint_number')} — {s.get('planned_story_points')} {L['points_long']}", 2)
        r.bullets(s.get("stories"))
    r.titled_bullets("scrum_master_advice", sprint.get("scrum_master_advice"))


def _solution_architecture(r: _Report, data: dict[str, Any], images: dict[str, bytes]) -> None:
    """Every element of the app's "Architecture technique" page."""
    L, arch = r.L, data["solution_architecture"]
    r.heading(L["solution_architecture"])
    if not arch or not arch.get("available"):
        r.para(L["architecture_not_generated"], muted=True)
        return
    if isinstance(arch.get("confidence"), (int, float)):
        r.para(f"{L['architecture_confidence']} : {arch['confidence']:.0%}", muted=True)
    if arch.get("style"):
        r.heading(L["architecture_style"], 2)
        r.para(arch["style"], bold=True, size=13)
    r.bullets(arch.get("rationale"))
    r.titled_bullets("quality_attributes", arch.get("quality_attributes"))
    r.titled_bullets("constraints_addressed", arch.get("constraints_addressed"))
    r.titled_bullets("architecture_risks", arch.get("risks"))
    r.titled_bullets("architecture_alternatives", arch.get("alternatives"))
    r.titled_bullets("architecture_conditions", arch.get("conditions"))

    if arch.get("stack_layers"):
        r.heading(L["tech_stack"], 2)
        r.table(
            [L["layer"], L["technology"], L["status"], L["justification"]],
            [
                [
                    layer_label(L, item["layer"]),
                    item.get("technology") or "—",
                    status_label(L, item.get("status") or ""),
                    item.get("justification") or "",
                ]
                for item in arch["stack_layers"]
            ],
            widths=[3, 3.5, 2.5, 7],
        )

    tables = arch.get("database_tables") or []
    if tables or arch.get("database_sql"):
        r.heading(L["database"], 2)
    if tables:
        r.table(
            [L["database_tables"], L["columns"], L["foreign_keys"]],
            [
                [
                    "\n".join(v for v in (t["name"], t.get("description")) if v),
                    ", ".join(
                        f"{c['name']} ({c['data_type']}{', PK' if c.get('primary_key') else ''})"
                        for c in t.get("columns") or []
                    ) or "—",
                    "\n".join(t.get("foreign_keys") or []) or "—",
                ]
                for t in tables
            ],
            widths=[4, 8, 4],
        )
    if arch.get("database_sql"):
        r.heading(L["sql_script"], 3)
        code = r.doc.add_paragraph()
        run = code.add_run(arch["database_sql"])
        run.font.name = "Consolas"
        run.font.size = Pt(8)
    r.titled_bullets("assumptions", arch.get("assumptions"))
    r.titled_bullets("warnings", arch.get("warnings"))

    uml = arch.get("uml_diagrams") or {}
    if uml:
        r.heading(L["uml_diagrams"])
        for diagram_type in DIAGRAM_ORDER:
            if not uml.get(diagram_type):
                continue
            r.heading(L[f"diagram_{diagram_type}"], 2)
            if images.get(diagram_type):
                r.picture(images[diagram_type])
            else:
                r.para(L["diagram_unavailable"], muted=True)


def build_docx(
    data: dict[str, Any],
    generated_at: str,
    diagram_images: dict[str, bytes] | None,
    target: str | BinaryIO,
) -> None:
    """Write the complete report to ``target`` (path or binary stream)."""
    report = _Report(labels_for(data.get("language")))
    _cover(report, data, generated_at)
    for section in (
        _executive_summary, _description, _market_study, _swot, _business_model_canvas,
        _competitive_analysis, _sources, _startup_score, _debate_room, _personas,
        _backlog, _sprint_planning,
    ):
        section(report, data)
    _solution_architecture(report, data, diagram_images or {})
    report.footer()
    report.doc.save(target)
