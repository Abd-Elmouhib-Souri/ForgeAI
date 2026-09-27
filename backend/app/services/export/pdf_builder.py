from __future__ import annotations

from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    Paragraph as _ReportLabParagraph,
    Spacer,
    Table,
    TableStyle,
)

from . import pdf_design as design
from contextvars import ContextVar

from .templates import sections_for
from .labels import (
    DIAGRAM_ORDER,
    FR,
    category_label,
    criteria_label,
    labels_for,
    layer_label,
    status_label,
)

# Labels of the report being built. Set by build_full_flow() for the whole
# (synchronous) flow construction; a ContextVar is isolated per thread and
# per task, so concurrent FR and EN exports never mix their labels.
_LABELS: ContextVar[dict[str, str]] = ContextVar("export_labels", default=FR)


# Built-in PDF fonts (Helvetica / Courier) only cover Windows-1252: any
# other character is drawn as a black box. LLM text often carries these
# typographic variants (observed on project 31: U+2011 non-breaking hyphen
# in "Wi-Fi", U+202F narrow no-break space in "< 2 s"). Map each one to a
# visually equivalent Windows-1252 character. Unknown scripts are kept as
# is: they need an embedded Unicode font, never a silent deletion.
_PDF_SAFE_MAP = str.maketrans(
    {
        "\u2010": "-",       # hyphen
        "\u2011": "-",       # non-breaking hyphen
        "\u2012": "-",       # figure dash
        "\u2212": "-",       # minus sign
        "\u202f": "\u00a0",  # narrow no-break space -> no-break space
        "\u2007": "\u00a0",  # figure space -> no-break space
        "\u2009": " ",       # thin space
        "\u200a": " ",       # hair space
        "\u2002": " ",       # en space
        "\u2003": " ",       # em space
        "\u200b": "",        # zero-width space
        "\u2060": "",        # word joiner
        "\u2192": "->",      # rightwards arrow
        "\u2190": "<-",      # leftwards arrow
        "\u2264": "<=",
        "\u2265": ">=",
        "\u2248": "~",
    }
)


def pdf_safe_text(text: Any) -> Any:
    """Printable version of ``text`` for the built-in PDF fonts."""
    if not isinstance(text, str):
        return text
    return text.translate(_PDF_SAFE_MAP)


class Paragraph(_ReportLabParagraph):
    """ReportLab Paragraph whose text is always made printable first."""

    def __init__(self, text, *args, **kwargs):
        super().__init__(pdf_safe_text(text), *args, **kwargs)


def _t(key: str) -> str:
    """Label of the current report language (see labels.py)."""
    return _LABELS.get()[key]


def _bullet_list(items: list[Any], styles: dict) -> list[Paragraph]:
    paragraphs = []
    for item in items:
        text = item if isinstance(item, str) else str(item)
        if not text.strip():
            continue
        paragraphs.append(Paragraph(f"•&nbsp;&nbsp;{text}", styles["Bullet"]))
    return paragraphs


def _section_heading(title: str, styles: dict) -> Paragraph:
    heading = Paragraph(title, styles["SectionTitle"])
    # Consomme par _ExportDocTemplate.afterFlowable (pdf_design.py) pour
    # remplir le sommaire dynamique avec le vrai numero de page.
    heading.toc_level = 0
    heading.toc_text = title
    return heading


def _empty_note(styles: dict) -> Paragraph:
    return Paragraph(_t("no_data"), styles["Caption"])


# ---------------------------------------------------------------------------
# 1. Page de couverture
# ---------------------------------------------------------------------------

def _identity_row(label: str, value: str, styles: dict) -> list[Any]:
    return [
        Paragraph(f"<b>{label}</b>", styles["BodyMuted"]),
        Paragraph(value or "—", styles["Body"]),
    ]


def _stat_block(value: str, label: str, styles: dict, width) -> Table:
    table = Table(
        [
            [Paragraph(value, styles["CoverTitle"])],
            [Paragraph(label, styles["Caption"])],
        ],
        colWidths=[width],
    )
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, 0), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
            ]
        )
    )
    return table


def _build_cover(data: dict[str, Any], styles: dict, generated_at: str) -> list[Any]:
    cover = data["cover"]
    flow: list[Any] = [
        Spacer(1, 1.8 * cm),
        Paragraph(_t("brand"), styles["CoverMeta"]),
        Spacer(1, 0.2 * cm),
        Paragraph(_t("report_kind"), styles["CoverMeta"]),
        Spacer(1, 1 * cm),
        Paragraph(cover["title"], styles["CoverTitle"]),
        Spacer(1, 0.2 * cm),
    ]
    meta_bits = [b for b in (cover.get("sector"), cover.get("region")) if b]
    if meta_bits:
        flow.append(Paragraph(" · ".join(meta_bits), styles["CoverSubtitle"]))

    flow.append(Spacer(1, 1 * cm))

    identity_rows = [
        _identity_row(_t("project"), cover["title"], styles),
        _identity_row(_t("type"), _t(f"template_{data.get('template') or 'business'}"), styles),
        _identity_row(_t("date"), generated_at, styles),
        _identity_row(_t("classification"), _t("confidential"), styles),
        _identity_row(_t("generated_by"), "ForgeAI", styles),
    ]
    identity_table = Table(
        identity_rows,
        colWidths=[4 * cm, design.CONTENT_WIDTH - 4 * cm],
    )
    identity_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, design.BORDER),
            ]
        )
    )
    flow.append(identity_table)
    flow.append(Spacer(1, 1.2 * cm))

    score = data["startup_score"].get("score_out_of_10")
    score_text = f"{score:.1f}/10" if isinstance(score, (int, float)) else "—"
    stats = [
        (score_text, _t("startup_score")),
        (str(len(data["personas"])), _t("personas")),
        (str(len(data["backlog"]["stories"])), _t("stat_user_stories")),
        (str(len(data["sources"])), _t("stat_verified_sources")),
    ]
    stat_w = design.CONTENT_WIDTH / 4
    stat_row = Table(
        [[_stat_block(v, l, styles, stat_w) for v, l in stats]],
        colWidths=[stat_w] * 4,
    )
    stat_row.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, design.BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    flow.append(stat_row)

    flow.append(NextPageTemplate("Content"))
    flow.append(PageBreak())

    # Sommaire dynamique : les vrais numeros de page ne sont connus
    # qu'apres le premier passage de mise en page ; doc.multiBuild()
    # (utilise par le routeur, pas doc.build()) refait la pagination
    # jusqu'a ce que le sommaire soit stable.
    flow.append(Paragraph(_t("table_of_contents"), styles["SectionTitle"]))
    flow.append(design.build_toc())
    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 2. Resume executif
# ---------------------------------------------------------------------------

_VERDICT_STYLES = {
    # code -> (label key, colour, background); "GO" keeps its own text.
    "STRONG_GO": ("verdict_strong_go", design.SUCCESS, design.SUCCESS_LIGHT),
    "GO": (None, design.SUCCESS, design.SUCCESS_LIGHT),
    "CONDITIONAL_GO": ("verdict_conditional_go", design.WARNING, design.WARNING_LIGHT),
    "NO_GO": ("verdict_no_go", design.DANGER, design.DANGER_LIGHT),
    "INSUFFICIENT_EVIDENCE": ("verdict_insufficient_evidence", design.WARNING, design.WARNING_LIGHT),
}


def _verdict_badge(verdict_code: str, styles: dict) -> Table:
    code = str(verdict_code or "").upper()
    if code in _VERDICT_STYLES:
        key, color, bg = _VERDICT_STYLES[code]
        label = _t(key) if key else code
    else:
        label, color, bg = (verdict_code or _t("not_available"), design.TEXT_MUTED, design.SURFACE)
    table = Table([[Paragraph(label, styles["TableHeader"])]], colWidths=[6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("TEXTCOLOR", (0, 0), (-1, -1), design.WHITE),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return table


def _build_executive_summary(data: dict[str, Any], styles: dict) -> list[Any]:
    summary = data["executive_summary"]
    flow: list[Any] = [_section_heading(_t("executive_summary"), styles)]

    flow.append(_verdict_badge(summary.get("verdict_code", ""), styles))
    flow.append(Spacer(1, 0.4 * cm))

    if summary.get("final_recommendation"):
        flow.append(Paragraph(summary["final_recommendation"], styles["Body"]))

    if summary.get("debate_synthesis"):
        flow.append(Paragraph(_t("committee_synthesis"), styles["SubsectionTitle"]))
        flow.append(Paragraph(summary["debate_synthesis"], styles["Body"]))

    if summary.get("critical_risks"):
        flow.append(Paragraph(_t("critical_risks"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(summary["critical_risks"], styles))

    if summary.get("next_actions"):
        flow.append(Paragraph(_t("next_actions"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(summary["next_actions"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 3. Description de l'idee + Innovation Score
# ---------------------------------------------------------------------------

def _build_description(data: dict[str, Any], styles: dict) -> list[Any]:
    desc = data["description"]
    flow: list[Any] = [_section_heading(_t("idea_description"), styles)]

    if desc.get("problem"):
        flow.append(Paragraph(_t("problem"), styles["SubsectionTitle"]))
        flow.append(Paragraph(desc["problem"], styles["Body"]))

    if desc.get("solution"):
        flow.append(Paragraph(_t("proposed_solution"), styles["SubsectionTitle"]))
        flow.append(Paragraph(desc["solution"], styles["Body"]))

    score = desc.get("innovation_breakdown_score") or desc.get("innovation_score")
    if score is not None:
        flow.append(Paragraph(_t("innovation_score"), styles["SubsectionTitle"]))
        flow.append(
            Paragraph(f"{score:.1f} / 10" if isinstance(score, float) else f"{score} / 10", styles["Body"])
        )

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 4. Etude de marche
# ---------------------------------------------------------------------------

def _build_market_study(data: dict[str, Any], styles: dict) -> list[Any]:
    market = data["market_study"]
    flow: list[Any] = [_section_heading(_t("market_study"), styles)]

    if market.get("summary"):
        flow.append(Paragraph(market["summary"], styles["Body"]))

    if market.get("market_size"):
        flow.append(Paragraph(_t("market_size"), styles["SubsectionTitle"]))
        flow.append(Paragraph(market["market_size"], styles["Body"]))

    if market.get("target_market"):
        flow.append(Paragraph(_t("target_market"), styles["SubsectionTitle"]))
        flow.append(Paragraph(market["target_market"], styles["Body"]))

    if market.get("customer_segments"):
        flow.append(Paragraph(_t("customer_segments"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["customer_segments"], styles))

    if market.get("market_trends"):
        flow.append(Paragraph(_t("market_trends"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["market_trends"], styles))

    if market.get("adoption_barriers"):
        flow.append(Paragraph(_t("adoption_barriers"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["adoption_barriers"], styles))

    if market.get("recommendations"):
        flow.append(Paragraph(_t("recommendations"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["recommendations"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 5. SWOT — grille 2x2 visuelle
# ---------------------------------------------------------------------------

def _swot_cell(title: str, items: list[str], color, bg, styles: dict, width) -> Table:
    heading = Table(
        [[Paragraph(title, styles["QuadrantHeading"])]],
        colWidths=[width],
    )
    heading.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    body_paragraphs = _bullet_list(items, styles) or [_empty_note(styles)]
    inner = Table(
        [[heading]] + [[p] for p in body_paragraphs],
        colWidths=[width],
    )
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 1), (-1, -1), bg),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LEFTPADDING", (0, 1), (-1, -1), 8),
                ("RIGHTPADDING", (0, 1), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
            ]
        )
    )
    return inner


def _build_swot(data: dict[str, Any], styles: dict) -> list[Any]:
    swot = data["swot"]
    flow: list[Any] = [_section_heading(_t("swot"), styles)]

    if swot.get("summary"):
        flow.append(Paragraph(swot["summary"], styles["Body"]))
        flow.append(Spacer(1, 0.3 * cm))

    col_w = 8.2 * cm
    col_w = 8.2 * cm
    inner_w = col_w - 0.3 * cm
    grid = Table(
        [
            [
                _swot_cell(
                    _t("strengths").upper(),
                    swot.get("strengths", []),
                    design.SUCCESS,
                    design.SUCCESS_LIGHT,
                    styles,
                    inner_w,
                ),
                _swot_cell(
                    _t("weaknesses").upper(),
                    swot.get("weaknesses", []),
                    design.DANGER,
                    design.DANGER_LIGHT,
                    styles,
                    inner_w,
                ),
            ],
            [
                _swot_cell(
                    _t("opportunities").upper(),
                    swot.get("opportunities", []),
                    design.PRIMARY,
                    design.PRIMARY_LIGHT,
                    styles,
                    inner_w,
                ),
                _swot_cell(
                    _t("threats").upper(),
                    swot.get("threats", []),
                    design.WARNING,
                    design.WARNING_LIGHT,
                    styles,
                    inner_w,
                ),
            ],
        ],
        colWidths=[col_w, col_w],
    )
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(grid)

    if swot.get("strategic_recommendations"):
        recap = [
            Spacer(1, 0.3 * cm),
            Paragraph(_t("strategic_recommendations"), styles["SubsectionTitle"]),
        ]
        recap.extend(_bullet_list(swot["strategic_recommendations"], styles))
        # KeepTogether : un bloc court qui ne tiendrait pas en bas de la
        # grille SWOT (deja volumineuse) ne doit jamais deborder seul
        # sur une page quasi vide ; il bascule en bloc sur la page
        # suivante plutot que de se scinder en un fragment orphelin.
        flow.append(KeepTogether(recap))

    return flow


# ---------------------------------------------------------------------------
# 6. Business Model Canvas — regroupement en 4 piliers (Osterwalder),
# tient nativement dans la largeur portrait standard : toutes les pages
# du rapport gardent la meme taille, aucun changement de format.
# ---------------------------------------------------------------------------

def _bmc_pillar(
    title: str,
    blocks: list[tuple[str, list[str]]],
    styles: dict,
    width,
) -> Table:
    rows = [[Paragraph(title, styles["QuadrantHeading"])]]
    for block_title, items in blocks:
        rows.append([Paragraph(block_title, styles["SubsectionTitle"])])
        rows.extend([[p] for p in (_bullet_list(items, styles) or [_empty_note(styles)])])

    heading = Table([rows[0]], colWidths=[width])
    heading.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), design.PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    body = Table([[heading]] + [[row[0]] for row in rows[1:]], colWidths=[width])
    body.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 1), (-1, -1), design.SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LEFTPADDING", (0, 1), (-1, -1), 8),
                ("RIGHTPADDING", (0, 1), (-1, -1), 8),
            ]
        )
    )
    return body


def _build_business_model_canvas(data: dict[str, Any], styles: dict) -> list[Any]:
    bmc = data["business_model_canvas"]
    flow: list[Any] = [_section_heading(_t("business_model_canvas"), styles)]
    flow.append(
        Paragraph(
            _t("bmc_intro"),
            styles["BodyMuted"],
        )
    )
    flow.append(Spacer(1, 0.25 * cm))

    col_w = (design.CONTENT_WIDTH - 0.3 * cm) / 2

    row1 = Table(
        [
            [
                _bmc_pillar(
                    _t("bmc_pillar_infrastructure"),
                    [
                        (_t("key_partnerships"), bmc.get("key_partnerships", [])),
                        (_t("key_activities"), bmc.get("key_activities", [])),
                        (_t("key_resources"), bmc.get("key_resources", [])),
                    ],
                    styles,
                    col_w,
                ),
                _bmc_pillar(
                    _t("bmc_pillar_offer"),
                    [(_t("value_proposition"), bmc.get("value_proposition", []))],
                    styles,
                    col_w,
                ),
            ]
        ],
        colWidths=[col_w, col_w],
    )
    row1.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(row1)

    row2 = Table(
        [
            [
                _bmc_pillar(
                    _t("bmc_pillar_customers"),
                    [
                        (_t("customer_relationships"), bmc.get("customer_relationships", [])),
                        (_t("channels"), bmc.get("channels", [])),
                        (_t("customer_segments"), bmc.get("customer_segments", [])),
                    ],
                    styles,
                    col_w,
                ),
                _bmc_pillar(
                    _t("bmc_pillar_finances"),
                    [
                        (_t("cost_structure"), bmc.get("cost_structure", [])),
                        (_t("revenue_streams"), bmc.get("revenue_streams", [])),
                    ],
                    styles,
                    col_w,
                ),
            ]
        ],
        colWidths=[col_w, col_w],
    )
    row2.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(row2)

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# Point d'entree partiel (passe 1) — utilise par le test de verification.
# pdf_builder_part2 complete la liste avant l'appel final a doc.build().
# ---------------------------------------------------------------------------

def build_part1_flow(data: dict[str, Any], styles: dict, generated_at: str) -> list[Any]:
    flow: list[Any] = []
    flow.extend(_build_cover(data, styles, generated_at))
    flow.extend(_build_executive_summary(data, styles))
    flow.extend(_build_description(data, styles))
    flow.extend(_build_market_study(data, styles))
    flow.extend(_build_swot(data, styles))
    flow.extend(_build_business_model_canvas(data, styles))
    return flow


# ---------------------------------------------------------------------------
# 7. Analyse concurrentielle
# ---------------------------------------------------------------------------

def _build_competitive_analysis(data: dict[str, Any], styles: dict) -> list[Any]:
    comp = data["competitive_analysis"]
    flow: list[Any] = [_section_heading(_t("competitive_analysis"), styles)]

    if comp.get("market_gap"):
        flow.append(Paragraph(comp["market_gap"], styles["Body"]))

    if comp.get("local_competitors"):
        flow.append(Paragraph(_t("local_competitors"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["local_competitors"], styles))

    if comp.get("local_adjacent_solutions"):
        flow.append(Paragraph(_t("local_adjacent_solutions"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["local_adjacent_solutions"], styles))

    if comp.get("international_benchmarks"):
        flow.append(Paragraph(_t("international_benchmarks"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["international_benchmarks"], styles))

    if comp.get("competitive_advantages"):
        flow.append(Paragraph(_t("competitive_advantages"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["competitive_advantages"], styles))

    if comp.get("limitations"):
        flow.append(Paragraph(_t("analysis_limitations"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["limitations"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# Sources et preuves (ForgeCrawler) — tracabilite des affirmations
# ---------------------------------------------------------------------------



def _build_sources(data: dict[str, Any], styles: dict) -> list[Any]:
    sources = data["sources"]
    flow: list[Any] = [_section_heading(_t("sources"), styles)]

    if not sources:
        flow.append(_empty_note(styles))
        flow.append(PageBreak())
        return flow

    flow.append(
        Paragraph(
            _t("sources_intro"),
            styles["BodyMuted"],
        )
    )
    flow.append(Spacer(1, 0.2 * cm))

    header = [
        Paragraph(_t("source"), styles["TableHeader"]),
        Paragraph(_t("category"), styles["TableHeader"]),
        Paragraph(_t("relevance"), styles["TableHeader"]),
    ]
    rows = [header]
    for source in sources:
        title_block = Paragraph(
            f"<b>{source['title']}</b><br/>"
            f"<font size=7.5 color='#7c3aed'>{source['url']}</font>",
            styles["TableCell"],
        )
        category = category_label(_LABELS.get(), source["category"])
        score = source.get("relevance_score")
        score_text = f"{score:.0%}" if isinstance(score, (int, float)) else "—"
        rows.append(
            [
                title_block,
                Paragraph(category, styles["TableCell"]),
                Paragraph(score_text, styles["TableCell"]),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            design.CONTENT_WIDTH - 4 * cm - 2.5 * cm,
            4 * cm,
            2.5 * cm,
        ],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), design.PRIMARY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [design.WHITE, design.SURFACE]),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, design.BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow.append(table)
    flow.append(PageBreak())
    return flow



def _score_bar_chart(breakdown: dict[str, float]) -> Drawing:
    labels = [
        criteria_label(_LABELS.get(), key) for key in breakdown if breakdown.get(key) is not None
    ]
    values = [v for v in breakdown.values() if v is not None]

    drawing = Drawing(design.CONTENT_WIDTH, 6.5 * cm)
    chart = VerticalBarChart()
    chart.x = 35
    chart.y = 40
    chart.height = 5 * cm
    chart.width = design.CONTENT_WIDTH - 50
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.dy = -8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 10
    chart.valueAxis.valueStep = 2
    chart.bars[0].fillColor = design.PRIMARY
    chart.barWidth = 8
    drawing.add(chart)
    return drawing


def _build_startup_score(data: dict[str, Any], styles: dict) -> list[Any]:
    score = data["startup_score"]
    flow: list[Any] = [_section_heading(_t("startup_score"), styles)]

    value = score.get("score_out_of_10")
    if value is not None:
        flow.append(
            Paragraph(
                f"{value:.1f} / 10" if isinstance(value, float) else f"{value} / 10",
                styles["CoverTitle"],
            )
        )

    if score.get("score_explanation"):
        flow.append(Paragraph(score["score_explanation"], styles["Body"]))

    breakdown = {k: v for k, v in score.get("breakdown", {}).items() if v is not None}
    if breakdown:
        flow.append(Paragraph(_t("score_breakdown"), styles["SubsectionTitle"]))
        flow.append(_score_bar_chart(breakdown))

    if score.get("strengths"):
        flow.append(Paragraph(_t("strengths"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(score["strengths"], styles))

    if score.get("weaknesses"):
        flow.append(Paragraph(_t("weaknesses"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(score["weaknesses"], styles))

    if score.get("recommendations"):
        recap = [Paragraph(_t("recommendations"), styles["SubsectionTitle"])]
        recap.extend(_bullet_list(score["recommendations"], styles))
        flow.append(KeepTogether(recap))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# Session strategique du comite (Debate Room)
# ---------------------------------------------------------------------------

_VOTE_COLORS = {
    "GO": design.SUCCESS,
    "STRONG_GO": design.SUCCESS,
    "CONDITIONAL_GO": design.WARNING,
    "NO_GO": design.DANGER,
    "INSUFFICIENT_EVIDENCE": design.WARNING,
}


def _metric_card(label: str, value: Any, styles: dict, width) -> Table:
    text = f"{value:.1f}" if isinstance(value, float) else str(value or "—")
    table = Table(
        [
            [Paragraph(label, styles["Caption"])],
            [Paragraph(text, styles["SubsectionTitle"])],
        ],
        colWidths=[width],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), design.SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]
        )
    )
    return table


def _build_debate_room(data: dict[str, Any], styles: dict) -> list[Any]:
    debate = data["debate_room"]
    flow: list[Any] = [_section_heading(_t("debate_room"), styles)]

    if not debate.get("votes") and not debate.get("committee"):
        flow.append(_empty_note(styles))
        flow.append(PageBreak())
        return flow

    flow.append(
        Paragraph(
            f"{debate.get('rounds_count', 0)} {_t('debate_rounds')} · "
            f"{len(debate.get('committee', []))} {_t('committee_members')}",
            styles["BodyMuted"],
        )
    )
    flow.append(Spacer(1, 0.2 * cm))
    flow.append(_verdict_badge(debate.get("verdict_code", ""), styles))
    flow.append(Spacer(1, 0.3 * cm))

    metric_w = (design.CONTENT_WIDTH - 3 * 0.3 * cm) / 4
    metrics = Table(
        [
            [
                _metric_card(_t("potential_score"), debate.get("potential_score"), styles, metric_w),
                _metric_card(_t("confidence_score"), debate.get("confidence_score"), styles, metric_w),
                _metric_card(_t("execution_readiness_score"), debate.get("execution_readiness_score"), styles, metric_w),
                _metric_card(_t("investment_attractiveness_score"), debate.get("investment_attractiveness_score"), styles, metric_w),
            ]
        ],
        colWidths=[metric_w] * 4,
    )
    metrics.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    flow.append(metrics)
    flow.append(Spacer(1, 0.3 * cm))

    if debate.get("debate_synthesis"):
        flow.append(Paragraph(debate["debate_synthesis"], styles["Body"]))

    if debate.get("committee"):
        flow.append(Paragraph(_t("committee_composition"), styles["SubsectionTitle"]))
        header = [
            Paragraph(_t("role"), styles["TableHeader"]),
            Paragraph(_t("mandate"), styles["TableHeader"]),
        ]
        rows = [header]
        for member in debate["committee"]:
            role_label = member["role"] + (
                "" if member["voting_member"] else f" ({_t('consultative')})"
            )
            rows.append(
                [
                    Paragraph(role_label, styles["TableCell"]),
                    Paragraph(member["mandate"], styles["TableCell"]),
                ]
            )
        table = Table(
            rows,
            colWidths=[5 * cm, design.CONTENT_WIDTH - 5 * cm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), design.PRIMARY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [design.WHITE, design.SURFACE]),
                    ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, design.BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flow.append(table)
        flow.append(Spacer(1, 0.3 * cm))

    if debate.get("votes"):
        flow.append(Paragraph(_t("committee_votes"), styles["SubsectionTitle"]))
        header = [
            Paragraph(_t("member"), styles["TableHeader"]),
            Paragraph(_t("vote"), styles["TableHeader"]),
            Paragraph(_t("confidence"), styles["TableHeader"]),
            Paragraph(_t("justification"), styles["TableHeader"]),
        ]
        rows = [header]
        for vote in debate["votes"]:
            confidence = vote.get("confidence")
            confidence_text = (
                f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "—"
            )
            rows.append(
                [
                    Paragraph(vote["member"], styles["TableCell"]),
                    Paragraph(vote["vote"], styles["TableCell"]),
                    Paragraph(confidence_text, styles["TableCell"]),
                    Paragraph(vote["reason"], styles["TableCell"]),
                ]
            )
        table = Table(
            rows,
            colWidths=[3.5 * cm, 3 * cm, 2 * cm, design.CONTENT_WIDTH - 8.5 * cm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), design.PRIMARY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [design.WHITE, design.SURFACE]),
                    ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, design.BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flow.append(table)

    flow.append(PageBreak())

    if debate.get("critical_risks") or debate.get("missing_evidence"):
        flow.append(_section_heading(_t("risks_and_missing_evidence"), styles))
        if debate.get("critical_risks"):
            flow.append(Paragraph(_t("critical_risks"), styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["critical_risks"], styles))
        if debate.get("missing_evidence"):
            flow.append(Paragraph(_t("missing_evidence"), styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["missing_evidence"], styles))

    if debate.get("go_conditions") or debate.get("no_go_conditions"):
        if debate.get("go_conditions"):
            flow.append(Paragraph(_t("go_conditions"), styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["go_conditions"], styles))
        if debate.get("no_go_conditions"):
            flow.append(Paragraph(_t("no_go_conditions"), styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["no_go_conditions"], styles))

    if debate.get("final_recommendation") or debate.get("improved_idea"):
        flow.append(Paragraph(_t("committee_final_recommendation"), styles["SubsectionTitle"]))
        recap_rows = []
        if debate.get("final_recommendation"):
            recap_rows.append([Paragraph(debate["final_recommendation"], styles["Body"])])
        if debate.get("improved_idea"):
            recap_rows.append(
                [Paragraph(f"<b>{_t('improved_idea')} :</b> {debate['improved_idea']}", styles["Body"])]
            )
        recap = Table(recap_rows, colWidths=[design.CONTENT_WIDTH])
        recap.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), design.PRIMARY_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.6, design.PRIMARY),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        flow.append(recap)

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 9. Personas
# ---------------------------------------------------------------------------

def _persona_card(persona: dict[str, Any], styles: dict) -> Table:
    rows = [
        [Paragraph(persona.get("name") or _t("persona"), styles["SubsectionTitle"])],
    ]
    if persona.get("role"):
        rows.append([Paragraph(persona["role"], styles["BodyMuted"])])
    if persona.get("profile"):
        rows.append([Paragraph(persona["profile"], styles["Body"])])
    if persona.get("main_pain"):
        rows.append([Paragraph(f"<b>{_t('main_pain')} :</b> {persona['main_pain']}", styles["Body"])])
    if persona.get("goals"):
        rows.append([Paragraph(f"<b>{_t('goals')}</b>", styles["Body"])])
        rows.extend([[p] for p in _bullet_list(persona["goals"], styles)])
    if persona.get("frustrations"):
        rows.append([Paragraph(f"<b>{_t('frustrations')}</b>", styles["Body"])])
        rows.extend([[p] for p in _bullet_list(persona["frustrations"], styles)])

    table = Table(rows, colWidths=[design.CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), design.SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _build_personas(data: dict[str, Any], styles: dict) -> list[Any]:
    personas = data["personas"]
    flow: list[Any] = [_section_heading(_t("personas"), styles)]

    if not personas:
        flow.append(_empty_note(styles))
    for persona in personas:
        flow.append(KeepTogether(_persona_card(persona, styles)))
        flow.append(Spacer(1, 0.35 * cm))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 10. Product Backlog
# ---------------------------------------------------------------------------

def _build_backlog(data: dict[str, Any], styles: dict) -> list[Any]:
    backlog = data["backlog"]
    flow: list[Any] = [_section_heading(_t("product_backlog"), styles)]

    stories = backlog.get("stories", [])
    if not stories:
        flow.append(_empty_note(styles))
        flow.append(PageBreak())
        return flow

    header = [
        Paragraph(_t("id"), styles["TableHeader"]),
        Paragraph(_t("user_story"), styles["TableHeader"]),
        Paragraph(_t("priority"), styles["TableHeader"]),
        Paragraph(_t("points"), styles["TableHeader"]),
    ]
    rows = [header]
    for story in stories:
        rows.append(
            [
                Paragraph(story.get("story_id", ""), styles["TableCell"]),
                Paragraph(story.get("story", ""), styles["TableCell"]),
                Paragraph(story.get("priority", ""), styles["TableCell"]),
                Paragraph(
                    str(story.get("story_points", "")), styles["TableCell"]
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            1.8 * cm,
            design.CONTENT_WIDTH - 1.8 * cm - 2.6 * cm - 2 * cm,
            2.6 * cm,
            2 * cm,
        ],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), design.PRIMARY),
                ("BACKGROUND", (0, 1), (-1, -1), design.SURFACE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [design.WHITE, design.SURFACE]),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, design.BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow.append(table)
    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 11. Sprint Planning — burndown en graphique en courbe
# ---------------------------------------------------------------------------

def _burndown_chart(ideal: list[float], planned: list[float]) -> Drawing:
    drawing = Drawing(design.CONTENT_WIDTH, 6 * cm)
    chart = HorizontalLineChart()
    chart.x = 35
    chart.y = 30
    chart.height = 4.5 * cm
    chart.width = design.CONTENT_WIDTH - 60
    # "planned" en premier (dessine en dessous), "ideal" en second
    # (dessine par-dessus, en pointilles) : quand les deux courbes sont
    # identiques (cas frequent avant l'execution d'un sprint reel), les
    # pointilles gris restent visibles par-dessus le trait violet plein
    # plutot que d'etre entierement masques par lui.
    chart.data = [planned, ideal]
    chart.categoryAxis.categoryNames = [""] * len(ideal)
    chart.categoryAxis.visibleTicks = 0
    chart.valueAxis.valueMin = 0
    chart.lines[0].strokeColor = design.PRIMARY
    chart.lines[0].strokeWidth = 2
    chart.lines[1].strokeColor = design.WARNING
    chart.lines[1].strokeDashArray = (6, 4)
    chart.lines[1].strokeWidth = 2

    legend = Legend()
    legend.x = design.CONTENT_WIDTH - 90
    legend.y = 5.6 * cm
    legend.colorNamePairs = [
        (design.PRIMARY, _t("planned")),
        (design.WARNING, _t("ideal")),
    ]
    legend.fontSize = 7
    legend.columnMaximum = 1
    drawing.add(chart)
    drawing.add(legend)
    return drawing


def _build_sprint_planning(data: dict[str, Any], styles: dict) -> list[Any]:
    sprint = data["sprint_planning"]
    flow: list[Any] = [_section_heading(_t("sprint_planning"), styles)]

    settings_bits = []
    if sprint.get("sprint_count"):
        settings_bits.append(f"{sprint['sprint_count']} {_t('sprints')}")
    if sprint.get("sprint_duration_days"):
        settings_bits.append(f"{sprint['sprint_duration_days']} {_t('days_per_sprint')}")
    if sprint.get("planned_velocity"):
        settings_bits.append(f"{_t('planned_velocity')} {sprint['planned_velocity']} {_t('story_points_short')}")
    if sprint.get("team_size"):
        settings_bits.append(f"{_t('team_of')} {sprint['team_size']}")
    if settings_bits:
        flow.append(Paragraph(" · ".join(settings_bits), styles["BodyMuted"]))

    for s in sprint.get("sprints", []):
        flow.append(
            Paragraph(
                f"{_t('sprint')} {s.get('sprint_number')} — {s.get('planned_story_points')} {_t('points_long')}",
                styles["SubsectionTitle"],
            )
        )
        flow.extend(_bullet_list(s.get("stories", []), styles))

    ideal = sprint.get("ideal_burndown") or []
    planned = sprint.get("planned_burndown") or []
    if ideal and planned:
        flow.append(Paragraph(_t("burndown"), styles["SubsectionTitle"]))
        flow.append(_burndown_chart(ideal, planned))

    if sprint.get("scrum_master_advice"):
        flow.append(Paragraph(_t("scrum_master_advice"), styles["SubsectionTitle"]))
        flow.extend(_bullet_list(sprint["scrum_master_advice"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 12-13. Architecture technique + Diagrammes UML
# ---------------------------------------------------------------------------

def _code_paragraph(code: str, styles: dict) -> Paragraph:
    """
    Code block that keeps line breaks and indentation but still wraps long
    lines inside the page (Preformatted would overflow the margin).
    Text is escaped: SQL may legitimately contain <, > or &.
    """
    from xml.sax.saxutils import escape

    lines = []
    for line in str(code).splitlines():
        stripped = line.lstrip(" ")
        indent = "&nbsp;" * (len(line) - len(stripped))
        lines.append(indent + escape(stripped))
    return Paragraph("<br/>".join(lines), styles["Code"])


def _labelled_bullets(key: str, items: list[str], styles: dict) -> list[Any]:
    """Subsection title + bullets, or nothing when the list is empty."""
    if not items:
        return []
    return [Paragraph(_t(key), styles["SubsectionTitle"]), *_bullet_list(items, styles)]


def _grid_table(rows: list[list[Any]], col_widths: list[float]) -> Table:
    """Same visual grammar as the backlog / sources tables."""
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), design.PRIMARY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [design.WHITE, design.SURFACE]),
                ("BOX", (0, 0), (-1, -1), 0.6, design.BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, design.BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_solution_architecture(
    data: dict[str, Any],
    styles: dict,
    diagram_images: dict[str, bytes] | None = None,
) -> list[Any]:
    """
    Every element of the "Architecture technique" page of the app:
    style + rationale, quality attributes, constraints, risks,
    alternatives, stack (technology, status, justification), database
    tables + SQL, the four UML diagrams, assumptions, warnings, confidence.

    diagram_images: PNG bytes per diagram type, rendered by Kroki upstream
    (never here: this module stays synchronous and network-free). A missing
    image prints an honest note, never a broken picture.
    """
    arch = data["solution_architecture"]
    flow: list[Any] = [_section_heading(_t("solution_architecture"), styles)]

    if not arch or not arch.get("available"):
        flow.append(Paragraph(_t("architecture_not_generated"), styles["BodyMuted"]))
        flow.append(PageBreak())
        return flow

    if isinstance(arch.get("confidence"), (int, float)):
        flow.append(
            Paragraph(f"{_t('architecture_confidence')} : {arch['confidence']:.0%}", styles["BodyMuted"])
        )

    if arch.get("style"):
        flow.append(Paragraph(_t("architecture_style"), styles["SubsectionTitle"]))
        flow.append(Paragraph(arch["style"], styles["CoverSubtitle"]))
    flow.extend(_bullet_list(arch.get("rationale") or [], styles))
    flow.extend(_labelled_bullets("quality_attributes", arch.get("quality_attributes") or [], styles))
    flow.extend(_labelled_bullets("constraints_addressed", arch.get("constraints_addressed") or [], styles))
    flow.extend(_labelled_bullets("architecture_risks", arch.get("risks") or [], styles))
    flow.extend(_labelled_bullets("architecture_alternatives", arch.get("alternatives") or [], styles))
    flow.extend(_labelled_bullets("architecture_conditions", arch.get("conditions") or [], styles))

    layers = arch.get("stack_layers") or []
    if layers:
        flow.append(Paragraph(_t("tech_stack"), styles["SubsectionTitle"]))
        rows = [[
            Paragraph(_t("layer"), styles["TableHeader"]),
            Paragraph(_t("technology"), styles["TableHeader"]),
            Paragraph(_t("status"), styles["TableHeader"]),
            Paragraph(_t("justification"), styles["TableHeader"]),
        ]]
        for item in layers:
            rows.append([
                Paragraph(layer_label(_LABELS.get(), item["layer"]), styles["TableCell"]),
                Paragraph(item.get("technology") or "—", styles["TableCell"]),
                Paragraph(status_label(_LABELS.get(), item.get("status") or ""), styles["TableCell"]),
                Paragraph(item.get("justification") or "", styles["TableCell"]),
            ])
        flow.append(_grid_table(rows, [3.2 * cm, 3.6 * cm, 2.6 * cm, design.CONTENT_WIDTH - 9.4 * cm]))

    tables = arch.get("database_tables") or []
    if tables or arch.get("database_sql"):
        flow.append(Paragraph(_t("database"), styles["SubsectionTitle"]))
    if tables:
        rows = [[
            Paragraph(_t("database_tables"), styles["TableHeader"]),
            Paragraph(_t("columns"), styles["TableHeader"]),
            Paragraph(_t("foreign_keys"), styles["TableHeader"]),
        ]]
        for table in tables:
            columns = ", ".join(
                f"{c['name']} ({c['data_type']}{', PK' if c.get('primary_key') else ''})"
                for c in table.get("columns") or []
            )
            name = f"<b>{table['name']}</b>"
            if table.get("description"):
                name += f"<br/><font size=7.5>{table['description']}</font>"
            rows.append([
                Paragraph(name, styles["TableCell"]),
                Paragraph(columns or "—", styles["TableCell"]),
                Paragraph("<br/>".join(table.get("foreign_keys") or []) or "—", styles["TableCell"]),
            ])
        flow.append(_grid_table(rows, [4 * cm, design.CONTENT_WIDTH - 9 * cm, 5 * cm]))
    if arch.get("database_sql"):
        flow.append(Paragraph(_t("sql_script"), styles["SubsectionTitle"]))
        flow.append(_code_paragraph(arch["database_sql"], styles))

    flow.extend(_labelled_bullets("assumptions", arch.get("assumptions") or [], styles))
    flow.extend(_labelled_bullets("warnings", arch.get("warnings") or [], styles))
    flow.append(PageBreak())

    uml = arch.get("uml_diagrams") or {}
    images = diagram_images or {}
    if uml:
        flow.append(_section_heading(_t("uml_diagrams"), styles))
        for diagram_type in DIAGRAM_ORDER:
            if not uml.get(diagram_type):
                continue
            flow.append(Paragraph(_t(f"diagram_{diagram_type}"), styles["SubsectionTitle"]))
            image_bytes = images.get(diagram_type)
            if image_bytes:
                from reportlab.platypus import Image
                import io

                img = Image(io.BytesIO(image_bytes))
                # Fit the page width AND height (tall sequence diagrams).
                max_width = design.CONTENT_WIDTH
                max_height = 18 * cm
                ratio = min(1.0, max_width / img.drawWidth, max_height / img.drawHeight)
                img.drawWidth *= ratio
                img.drawHeight *= ratio
                flow.append(img)
            else:
                flow.append(Paragraph(_t("diagram_unavailable"), styles["Caption"]))
            flow.append(Spacer(1, 0.3 * cm))
        flow.append(PageBreak())
    return flow


def build_part2_flow(
    data: dict[str, Any],
    styles: dict,
    diagram_images: dict[str, bytes] | None = None,
) -> list[Any]:
    flow: list[Any] = []
    flow.extend(_build_competitive_analysis(data, styles))
    flow.extend(_build_sources(data, styles))
    flow.extend(_build_startup_score(data, styles))
    flow.extend(_build_debate_room(data, styles))
    flow.extend(_build_personas(data, styles))
    flow.extend(_build_backlog(data, styles))
    flow.extend(_build_sprint_planning(data, styles))
    flow.extend(_build_solution_architecture(data, styles, diagram_images))
    return flow


# Section key (templates.SECTION_KEYS) -> builder. The architecture section
# also needs the rendered UML images, handled in build_full_flow.
_SECTION_BUILDERS = {
    "executive_summary": _build_executive_summary,
    "idea_description": _build_description,
    "market_study": _build_market_study,
    "swot": _build_swot,
    "business_model_canvas": _build_business_model_canvas,
    "competitive_analysis": _build_competitive_analysis,
    "sources": _build_sources,
    "startup_score": _build_startup_score,
    "debate_room": _build_debate_room,
    "personas": _build_personas,
    "product_backlog": _build_backlog,
    "sprint_planning": _build_sprint_planning,
}


def build_full_flow(
    data: dict[str, Any],
    styles: dict,
    generated_at: str,
    diagram_images: dict[str, bytes] | None = None,
) -> list[Any]:
    """
    Point d'entree unique utilise par le router d'export.

    Cover first, then the sections of the export template (templates.py),
    in the template's order. Each section ends with its own page break, so
    any order keeps a clean layout.
    """
    token = _LABELS.set(labels_for(data.get("language")))
    try:
        flow = _build_cover(data, styles, generated_at)
        for key in sections_for(data.get("template")):
            if key == "solution_architecture":
                flow.extend(_build_solution_architecture(data, styles, diagram_images))
            else:
                flow.extend(_SECTION_BUILDERS[key](data, styles))
            # Every section starts on its own page, whatever the template
            # order (the SWOT builder, for one, ends without a page break).
            if not flow or type(flow[-1]).__name__ != "PageBreak":
                flow.append(PageBreak())
    finally:
        _LABELS.reset(token)
    # Le dernier PageBreak laisse une page finale vide : on le retire,
    # jamais souhaitable en fin de document.
    if flow and type(flow[-1]).__name__ == "PageBreak":
        flow.pop()
    return flow
