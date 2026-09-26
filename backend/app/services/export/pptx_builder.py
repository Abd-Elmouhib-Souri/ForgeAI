"""
Sprint 6.3: 12-slide investor pitch deck (.pptx).

Built from the SAME assembled data and labels as the PDF / Word reports
(assemble_export_data + labels_for); nothing here reads analysis_data.

A slide never grows, so every text is bounded: at most MAX_BULLETS items of
MAX_CHARS characters, long prose is split into sentences and cut at a word
boundary with an ellipsis. Every slide still builds when its data is
missing, with an honest "no data" note instead of an empty frame.

Synchronous and network-free: the router runs it in asyncio.to_thread(),
UML images arrive as PNG bytes already rendered by Kroki.
"""

from __future__ import annotations

import io
import re
from typing import Any, BinaryIO

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Inches, Pt

from .labels import criteria_label, labels_for, layer_label

MAX_BULLETS = 5
MAX_CHARS = 160
# Narrow boxes (3 columns, SWOT quadrants) get a smaller text budget: the
# 27 Sept visual check showed 5 x 160 characters overflowing a 1/3 column.
NARROW_BULLETS = 3
NARROW_CHARS = 110
SLIDE_COUNT = 12

PRIMARY = RGBColor(0x7C, 0x3A, 0xED)
PRIMARY_LIGHT = RGBColor(0xF5, 0xF3, 0xFF)
TEXT_DARK = RGBColor(0x0F, 0x17, 0x2A)
TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SLIDE_W = Emu(12192000)  # 13.333 in, 16:9
SLIDE_H = Emu(6858000)   # 7.5 in
MARGIN = Inches(0.6)
BODY_TOP = Inches(1.55)
BODY_H = Inches(5.0)

_VERDICT_KEYS = {
    "STRONG_GO": "verdict_strong_go",
    "CONDITIONAL_GO": "verdict_conditional_go",
    "NO_GO": "verdict_no_go",
    "INSUFFICIENT_EVIDENCE": "verdict_insufficient_evidence",
}


# ---------------------------------------------------------------------------
# Text bounding
# ---------------------------------------------------------------------------

def clip(text: Any, limit: int = MAX_CHARS) -> str:
    """One line of at most ``limit`` characters, cut at a word boundary."""
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.")
    return f"{cut}…"


def sentences(text: Any, limit: int = MAX_BULLETS) -> list[str]:
    """Long prose -> at most ``limit`` clipped sentences."""
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", str(text or "")).strip())
    return [clip(p) for p in parts if p][:limit]


def items(values: Any, limit: int = MAX_BULLETS) -> list[str]:
    """List -> at most ``limit`` clipped, non-empty items."""
    if isinstance(values, str):
        values = [values]
    return [clip(v) for v in (values or []) if str(v or "").strip()][:limit]


# ---------------------------------------------------------------------------
# Slide primitives
# ---------------------------------------------------------------------------

class _Deck:
    def __init__(self, labels: dict[str, str], project_title: str) -> None:
        self.L = labels
        self.project = clip(project_title, 80)
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = SLIDE_W, SLIDE_H
        self._title_only = self.prs.slide_layouts[5]
        self._title_slide = self.prs.slide_layouts[0]

    # -- building blocks -----------------------------------------------------

    @staticmethod
    def _style_runs(paragraph, size: float, color: RGBColor, bold: bool = False) -> None:
        for run in paragraph.runs:
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.bold = bold

    def content_slide(self, title_key: str):
        """Title-only layout, repositioned for 16:9, violet accent bar."""
        slide = self.prs.slides.add_slide(self._title_only)
        title = slide.shapes.title
        title.left, title.top, title.width, title.height = MARGIN, Inches(0.45), SLIDE_W - 2 * MARGIN, Inches(0.9)
        title.text = clip(self.L[title_key], 80)
        frame = title.text_frame.paragraphs[0]
        frame.alignment = 1  # left
        self._style_runs(frame, 30, PRIMARY, bold=True)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), SLIDE_H)
        bar.fill.solid()
        bar.fill.fore_color.rgb = PRIMARY
        bar.line.fill.background()
        index = len(self.prs.slides)
        self.text(slide, f"ForgeAI · {self.project} · {index}/{SLIDE_COUNT}",
                  MARGIN, SLIDE_H - Inches(0.5), Inches(8), Inches(0.3), size=10, color=TEXT_MUTED)
        return slide

    def text(self, slide, value: str, left, top, width, height, *, size=18, color=TEXT_DARK, bold=False):
        box = slide.shapes.add_textbox(left, top, width, height)
        box.text_frame.word_wrap = True
        box.text_frame.text = clip(value)
        self._style_runs(box.text_frame.paragraphs[0], size, color, bold)
        return box

    def bullets(
        self,
        slide,
        values: list[str],
        left,
        top,
        width,
        height,
        *,
        heading: str | None = None,
        size=18,
        max_items: int = MAX_BULLETS,
        max_chars: int = MAX_CHARS,
    ):
        """Optional heading line + bounded bullets; honest note when empty."""
        box = slide.shapes.add_textbox(left, top, width, height)
        frame = box.text_frame
        frame.word_wrap = True
        lines: list[tuple[str, bool]] = []
        if heading:
            lines.append((clip(heading, 80), True))
        values = values[:max_items]
        lines.extend((f"• {v}" if not v.startswith("• ") else v, False) for v in values)
        if not values:
            lines.append((self.L["no_data"], False))
        for i, (line, is_heading) in enumerate(lines):
            paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            paragraph.text = clip(line, max_chars)
            paragraph.space_after = Pt(8)
            self._style_runs(paragraph, size + (2 if is_heading else 0),
                             PRIMARY if is_heading else TEXT_DARK, bold=is_heading)
        return box

    def panel(self, slide, left, top, width, height):
        """Light violet rounded background panel (no text)."""
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = PRIMARY_LIGHT
        shape.line.color.rgb = RGBColor(0xDD, 0xD6, 0xFE)
        return shape

    def columns(self, slide, blocks: list[tuple[str, list[str]]], size=16):
        """N equal columns, each a panel with heading + bullets.

        Three columns or more are narrow: smaller font and text budget.
        """
        narrow = len(blocks) >= 3
        gap = Inches(0.3)
        width = (SLIDE_W - 2 * MARGIN - gap * (len(blocks) - 1)) / len(blocks)
        for i, (heading, values) in enumerate(blocks):
            left = MARGIN + i * (width + gap)
            self.panel(slide, left, BODY_TOP, width, BODY_H)
            self.bullets(
                slide, values, left + Inches(0.2), BODY_TOP + Inches(0.2),
                width - Inches(0.4), BODY_H - Inches(0.4), heading=heading,
                size=14 if narrow else size,
                max_items=NARROW_BULLETS if narrow else MAX_BULLETS,
                max_chars=NARROW_CHARS if narrow else MAX_CHARS,
            )

    def verdict_label(self, code: str) -> str:
        upper = str(code or "").upper()
        key = _VERDICT_KEYS.get(upper)
        return self.L[key] if key else (upper or self.L["not_available"])


# ---------------------------------------------------------------------------
# The 12 slides
# ---------------------------------------------------------------------------

def _cover(d: _Deck, data: dict[str, Any], generated_at: str) -> None:
    slide = d.prs.slides.add_slide(d._title_slide)
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = PRIMARY
    title, subtitle = slide.shapes.title, slide.placeholders[1]
    title.left, title.top, title.width, title.height = MARGIN, Inches(2.2), SLIDE_W - 2 * MARGIN, Inches(1.5)
    title.text = d.project
    d._style_runs(title.text_frame.paragraphs[0], 48, WHITE, bold=True)
    cover = data["cover"]
    verdict = d.verdict_label(data["executive_summary"].get("verdict_code"))
    subtitle.left, subtitle.top, subtitle.width, subtitle.height = MARGIN, Inches(3.8), SLIDE_W - 2 * MARGIN, Inches(1.6)
    lines = [
        " · ".join(b for b in (cover.get("sector"), cover.get("region")) if b),
        f"{d.L['deck_tagline']} · {generated_at} · {verdict}",
    ]
    subtitle.text_frame.text = clip(lines[0]) or d.L["deck_tagline"]
    paragraph = subtitle.text_frame.add_paragraph()
    paragraph.text = clip(lines[1])
    for p in subtitle.text_frame.paragraphs:
        d._style_runs(p, 20, WHITE)


def _problem(d: _Deck, data: dict[str, Any]) -> None:
    slide = d.content_slide("deck_problem")
    pains = [p.get("main_pain") for p in data["personas"] if p.get("main_pain")]
    d.bullets(slide, sentences(data["description"].get("problem")), MARGIN, BODY_TOP,
              Inches(7.4), BODY_H, size=20)
    d.panel(slide, Inches(8.4), BODY_TOP, Inches(4.3), BODY_H)
    d.bullets(slide, items(pains, 3), Inches(8.6), BODY_TOP + Inches(0.2), Inches(3.9), BODY_H - Inches(0.4),
              heading=d.L["main_pain"], size=16)


def _solution(d: _Deck, data: dict[str, Any]) -> None:
    slide = d.content_slide("deck_solution")
    # Real project data only: the stated solution, else the committee's
    # improved idea, else the Business Model value proposition.
    solution = (
        sentences(data["description"].get("solution"))
        or sentences(data["debate_room"].get("improved_idea"))
        or items(data["business_model_canvas"].get("value_proposition"))
    )
    d.bullets(slide, solution, MARGIN, BODY_TOP, Inches(7.4), BODY_H, size=20)
    d.panel(slide, Inches(8.4), BODY_TOP, Inches(4.3), BODY_H)
    d.bullets(slide, items(data["competitive_analysis"].get("competitive_advantages"), 4),
              Inches(8.6), BODY_TOP + Inches(0.2), Inches(3.9), BODY_H - Inches(0.4),
              heading=d.L["deck_differentiation"], size=16)


def _market(d: _Deck, data: dict[str, Any]) -> None:
    market = data["market_study"]
    slide = d.content_slide("deck_market")
    headline = [v for v in (market.get("market_size"), market.get("target_market")) if v]
    d.columns(slide, [
        (d.L["market_size"], items(headline + sentences(market.get("summary"), 2), 4)),
        (d.L["customer_segments"], items(market.get("customer_segments"), 4)),
        (d.L["deck_why_now"], items(market.get("market_trends") or market.get("market_opportunities"), 4)),
    ])


def _customers(d: _Deck, data: dict[str, Any]) -> None:
    slide = d.content_slide("deck_customers")
    personas = data["personas"][:3]
    if not personas:
        d.bullets(slide, [], MARGIN, BODY_TOP, SLIDE_W - 2 * MARGIN, BODY_H)
        return
    d.columns(slide, [
        (
            p.get("name") or d.L["persona"],
            items(
                [p.get("role"), f"{d.L['main_pain']} : {p['main_pain']}" if p.get("main_pain") else None,
                 *(p.get("goals") or [])],
                4,
            ),
        )
        for p in personas
    ])


def _competition(d: _Deck, data: dict[str, Any]) -> None:
    comp = data["competitive_analysis"]
    slide = d.content_slide("deck_competition")
    competitors = [*(comp.get("local_competitors") or []), *(comp.get("local_adjacent_solutions") or []),
                   *(comp.get("international_benchmarks") or [])]
    d.columns(slide, [
        (d.L["local_competitors"], items(competitors, 5)),
        (d.L["competitive_advantages"], items(comp.get("competitive_advantages") or sentences(comp.get("market_gap"), 3), 5)),
    ])


def _business_model(d: _Deck, data: dict[str, Any]) -> None:
    bmc = data["business_model_canvas"]
    slide = d.content_slide("deck_business_model")
    d.columns(slide, [
        (d.L["value_proposition"], items(bmc.get("value_proposition"), 4)),
        (d.L["revenue_streams"], items(bmc.get("revenue_streams"), 4)),
        (d.L["channels"], items(bmc.get("channels"), 4)),
    ])


def _swot(d: _Deck, data: dict[str, Any]) -> None:
    swot = data["swot"]
    slide = d.content_slide("deck_swot")
    gap = Inches(0.25)
    width = (SLIDE_W - 2 * MARGIN - gap) / 2
    height = (BODY_H - gap) / 2
    for i, key in enumerate(("strengths", "weaknesses", "opportunities", "threats")):
        left = MARGIN + (i % 2) * (width + gap)
        top = BODY_TOP + (i // 2) * (height + gap)
        d.panel(slide, left, top, width, height)
        d.bullets(slide, items(swot.get(key), 3), left + Inches(0.2), top + Inches(0.1),
                  width - Inches(0.4), height - Inches(0.2), heading=d.L[key].upper(), size=13,
                  max_items=NARROW_BULLETS, max_chars=NARROW_CHARS)


def _score(d: _Deck, data: dict[str, Any]) -> None:
    score = data["startup_score"]
    slide = d.content_slide("deck_score")
    value = score.get("score_out_of_10")
    d.text(slide, f"{value:.1f}/10" if isinstance(value, (int, float)) else "—",
           MARGIN, BODY_TOP, Inches(4), Inches(1.3), size=60, color=PRIMARY, bold=True)
    verdict = d.verdict_label(data["debate_room"].get("verdict_code") or data["executive_summary"].get("verdict_code"))
    d.text(slide, verdict, MARGIN, BODY_TOP + Inches(1.4), Inches(4), Inches(0.6), size=22, bold=True)
    d.bullets(slide, sentences(score.get("score_explanation"), 3), MARGIN, BODY_TOP + Inches(2.1),
              Inches(4.2), Inches(2.8), size=14) if score.get("score_explanation") else None
    breakdown = {k: v for k, v in (score.get("breakdown") or {}).items() if isinstance(v, (int, float))}
    if breakdown:
        chart_data = CategoryChartData()
        chart_data.categories = [criteria_label(d.L, k).replace("\n", " ") for k in breakdown]
        chart_data.add_series(d.L["score_breakdown"], list(breakdown.values()))
        frame = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(5.2), BODY_TOP,
                                       Inches(7.5), BODY_H, chart_data)
        chart = frame.chart
        chart.has_legend = False
        chart.value_axis.minimum_scale = 0
        chart.value_axis.maximum_scale = 10
        chart.plots[0].series[0].format.fill.solid()
        chart.plots[0].series[0].format.fill.fore_color.rgb = PRIMARY
    else:
        d.bullets(slide, [], Inches(5.2), BODY_TOP, Inches(7.5), BODY_H)


def _roadmap(d: _Deck, data: dict[str, Any]) -> None:
    sprint = data["sprint_planning"]
    slide = d.content_slide("deck_roadmap")
    sprints = sprint.get("sprints") or []
    lines = [
        f"{d.L['sprint']} {s.get('sprint_number')} — {s.get('planned_story_points')} {d.L['story_points_short']} : "
        + ", ".join(str(x) for x in (s.get("stories") or []))
        for s in sprints
    ]
    if len(lines) > MAX_BULLETS:
        # Keep the first sprints and say how many follow.
        lines = lines[: MAX_BULLETS - 1] + [f"+ {len(sprints) - (MAX_BULLETS - 1)} {d.L['sprints']}"]
    meta = []
    if sprint.get("sprint_count"):
        meta.append(f"{sprint['sprint_count']} {d.L['sprints']}")
    if sprint.get("sprint_duration_days"):
        meta.append(f"{sprint['sprint_duration_days']} {d.L['days_per_sprint']}")
    if sprint.get("team_size"):
        meta.append(f"{d.L['team_of']} {sprint['team_size']}")
    d.bullets(slide, items(lines), MARGIN, BODY_TOP, SLIDE_W - 2 * MARGIN, BODY_H,
              heading=" · ".join(meta) or None, size=16)


def _architecture(d: _Deck, data: dict[str, Any], images: dict[str, bytes]) -> None:
    arch = data["solution_architecture"]
    slide = d.content_slide("deck_architecture")
    if not arch or not arch.get("available"):
        d.text(slide, d.L["architecture_not_generated"], MARGIN, BODY_TOP, SLIDE_W - 2 * MARGIN, Inches(1), size=20)
        return
    stack = [
        f"{layer_label(d.L, item['layer'])} : {item['technology']}"
        for item in arch.get("stack_layers") or []
        if item.get("technology")
    ]
    d.bullets(slide, items(stack), MARGIN, BODY_TOP, Inches(5.2), BODY_H,
              heading=f"{d.L['architecture_style']} : {arch.get('style') or '—'}", size=16)
    # Use-case diagram: the most business-readable UML view for investors.
    box_left, box_top, box_w, box_h = Inches(6.1), BODY_TOP, Inches(6.6), BODY_H
    png = images.get("use_case")
    if png:
        picture = slide.shapes.add_picture(io.BytesIO(png), box_left, box_top, width=box_w)
        if picture.height > box_h:
            ratio = box_h / picture.height
            picture.height = int(picture.height * ratio)
            picture.width = int(picture.width * ratio)
    else:
        d.text(slide, d.L["diagram_unavailable"], box_left, box_top, box_w, Inches(1), size=14, color=TEXT_MUTED)


def _verdict(d: _Deck, data: dict[str, Any]) -> None:
    summary = data["executive_summary"]
    debate = data["debate_room"]
    slide = d.content_slide("deck_verdict")
    d.text(slide, d.verdict_label(summary.get("verdict_code") or debate.get("verdict_code")),
           MARGIN, BODY_TOP, SLIDE_W - 2 * MARGIN, Inches(0.7), size=28, color=PRIMARY, bold=True)
    d.text(slide, summary.get("final_recommendation") or debate.get("final_recommendation") or "",
           MARGIN, BODY_TOP + Inches(0.8), SLIDE_W - 2 * MARGIN, Inches(0.8), size=18)
    top = BODY_TOP + Inches(1.7)
    height = BODY_H - Inches(1.7)
    width = (SLIDE_W - 2 * MARGIN - Inches(0.3)) / 2
    d.bullets(slide, items(summary.get("next_actions") or debate.get("next_actions"), 4), MARGIN, top,
              width, height, heading=d.L["next_actions"], size=15)
    d.bullets(slide, items(summary.get("go_conditions") or debate.get("go_conditions"), 4),
              MARGIN + width + Inches(0.3), top, width, height, heading=d.L["go_conditions"], size=15)


def build_pptx(
    data: dict[str, Any],
    generated_at: str,
    diagram_images: dict[str, bytes] | None,
    target: str | BinaryIO,
) -> None:
    """Write the 12-slide pitch deck to ``target`` (path or binary stream)."""
    deck = _Deck(labels_for(data.get("language")), data["cover"]["title"])
    _cover(deck, data, generated_at)
    for slide in (_problem, _solution, _market, _customers, _competition,
                  _business_model, _swot, _score, _roadmap):
        slide(deck, data)
    _architecture(deck, data, diagram_images or {})
    _verdict(deck, data)
    assert len(deck.prs.slides) == SLIDE_COUNT
    deck.prs.save(target)
