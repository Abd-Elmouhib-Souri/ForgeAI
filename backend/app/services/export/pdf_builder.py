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
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from . import pdf_design as design


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
    return Paragraph("Aucune donnee disponible pour cette section.", styles["Caption"])


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
        Paragraph("FORGEAI", styles["CoverMeta"]),
        Spacer(1, 0.2 * cm),
        Paragraph("RAPPORT DE PROJET", styles["CoverMeta"]),
        Spacer(1, 1 * cm),
        Paragraph(cover["title"], styles["CoverTitle"]),
        Spacer(1, 0.2 * cm),
    ]
    meta_bits = [b for b in (cover.get("sector"), cover.get("region")) if b]
    if meta_bits:
        flow.append(Paragraph(" · ".join(meta_bits), styles["CoverSubtitle"]))

    flow.append(Spacer(1, 1 * cm))

    identity_rows = [
        _identity_row("Projet", cover["title"], styles),
        _identity_row("Type", "Rapport d'analyse strategique et technique", styles),
        _identity_row("Entreprise", "DotJcom Ltd — Soliman, Nabeul, Tunisie", styles),
        _identity_row("Date", generated_at, styles),
        _identity_row("Classification", "Confidentiel", styles),
        _identity_row("Genere par", "DotJcom ForgeAI", styles),
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
        (score_text, "Startup Score"),
        (str(len(data["personas"])), "Personas"),
        (str(len(data["backlog"]["stories"])), "User stories"),
        (str(len(data["sources"])), "Sources verifiees"),
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
    flow.append(Paragraph("Sommaire", styles["SectionTitle"]))
    flow.append(design.build_toc())
    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 2. Resume executif
# ---------------------------------------------------------------------------

_VERDICT_LABELS = {
    "STRONG_GO": ("Fort GO", design.SUCCESS, design.SUCCESS_LIGHT),
    "GO": ("GO", design.SUCCESS, design.SUCCESS_LIGHT),
    "CONDITIONAL_GO": ("GO conditionnel", design.WARNING, design.WARNING_LIGHT),
    "NO_GO": ("NO-GO", design.DANGER, design.DANGER_LIGHT),
    "INSUFFICIENT_EVIDENCE": (
        "Preuves insuffisantes",
        design.WARNING,
        design.WARNING_LIGHT,
    ),
}


def _verdict_badge(verdict_code: str, styles: dict) -> Table:
    label, color, bg = _VERDICT_LABELS.get(
        str(verdict_code or "").upper(),
        (verdict_code or "Non disponible", design.TEXT_MUTED, design.SURFACE),
    )
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
    flow: list[Any] = [_section_heading("Resume executif", styles)]

    flow.append(_verdict_badge(summary.get("verdict_code", ""), styles))
    flow.append(Spacer(1, 0.4 * cm))

    if summary.get("final_recommendation"):
        flow.append(Paragraph(summary["final_recommendation"], styles["Body"]))

    if summary.get("debate_synthesis"):
        flow.append(Paragraph("Synthese du comite strategique", styles["SubsectionTitle"]))
        flow.append(Paragraph(summary["debate_synthesis"], styles["Body"]))

    if summary.get("critical_risks"):
        flow.append(Paragraph("Risques critiques", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(summary["critical_risks"], styles))

    if summary.get("next_actions"):
        flow.append(Paragraph("Prochaines actions", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(summary["next_actions"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 3. Description de l'idee + Innovation Score
# ---------------------------------------------------------------------------

def _build_description(data: dict[str, Any], styles: dict) -> list[Any]:
    desc = data["description"]
    flow: list[Any] = [_section_heading("Description de l'idee", styles)]

    if desc.get("problem"):
        flow.append(Paragraph("Probleme", styles["SubsectionTitle"]))
        flow.append(Paragraph(desc["problem"], styles["Body"]))

    if desc.get("solution"):
        flow.append(Paragraph("Solution proposee", styles["SubsectionTitle"]))
        flow.append(Paragraph(desc["solution"], styles["Body"]))

    score = desc.get("innovation_breakdown_score") or desc.get("innovation_score")
    if score is not None:
        flow.append(Paragraph("Score d'innovation", styles["SubsectionTitle"]))
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
    flow: list[Any] = [_section_heading("Etude de marche", styles)]

    if market.get("summary"):
        flow.append(Paragraph(market["summary"], styles["Body"]))

    if market.get("market_size"):
        flow.append(Paragraph("Taille du marche", styles["SubsectionTitle"]))
        flow.append(Paragraph(market["market_size"], styles["Body"]))

    if market.get("target_market"):
        flow.append(Paragraph("Marche cible", styles["SubsectionTitle"]))
        flow.append(Paragraph(market["target_market"], styles["Body"]))

    if market.get("customer_segments"):
        flow.append(Paragraph("Segments clients", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["customer_segments"], styles))

    if market.get("market_trends"):
        flow.append(Paragraph("Tendances du marche", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["market_trends"], styles))

    if market.get("adoption_barriers"):
        flow.append(Paragraph("Freins a l'adoption", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(market["adoption_barriers"], styles))

    if market.get("recommendations"):
        flow.append(Paragraph("Recommandations", styles["SubsectionTitle"]))
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
    flow: list[Any] = [_section_heading("Analyse SWOT", styles)]

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
                    "FORCES",
                    swot.get("strengths", []),
                    design.SUCCESS,
                    design.SUCCESS_LIGHT,
                    styles,
                    inner_w,
                ),
                _swot_cell(
                    "FAIBLESSES",
                    swot.get("weaknesses", []),
                    design.DANGER,
                    design.DANGER_LIGHT,
                    styles,
                    inner_w,
                ),
            ],
            [
                _swot_cell(
                    "OPPORTUNITES",
                    swot.get("opportunities", []),
                    design.PRIMARY,
                    design.PRIMARY_LIGHT,
                    styles,
                    inner_w,
                ),
                _swot_cell(
                    "MENACES",
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
            Paragraph("Recommandations strategiques", styles["SubsectionTitle"]),
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
    flow: list[Any] = [_section_heading("Business Model Canvas", styles)]
    flow.append(
        Paragraph(
            "Les 9 blocs du canevas, regroupes selon les 4 piliers "
            "classiques du Business Model Canvas (Osterwalder).",
            styles["BodyMuted"],
        )
    )
    flow.append(Spacer(1, 0.25 * cm))

    col_w = (design.CONTENT_WIDTH - 0.3 * cm) / 2

    row1 = Table(
        [
            [
                _bmc_pillar(
                    "INFRASTRUCTURE",
                    [
                        ("Partenaires cles", bmc.get("key_partnerships", [])),
                        ("Activites cles", bmc.get("key_activities", [])),
                        ("Ressources cles", bmc.get("key_resources", [])),
                    ],
                    styles,
                    col_w,
                ),
                _bmc_pillar(
                    "OFFRE",
                    [("Proposition de valeur", bmc.get("value_proposition", []))],
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
                    "CLIENTS",
                    [
                        ("Relation client", bmc.get("customer_relationships", [])),
                        ("Canaux", bmc.get("channels", [])),
                        ("Segments clients", bmc.get("customer_segments", [])),
                    ],
                    styles,
                    col_w,
                ),
                _bmc_pillar(
                    "FINANCES",
                    [
                        ("Structure de couts", bmc.get("cost_structure", [])),
                        ("Sources de revenus", bmc.get("revenue_streams", [])),
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
    flow: list[Any] = [_section_heading("Analyse concurrentielle", styles)]

    if comp.get("market_gap"):
        flow.append(Paragraph(comp["market_gap"], styles["Body"]))

    if comp.get("local_competitors"):
        flow.append(Paragraph("Concurrents locaux", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["local_competitors"], styles))

    if comp.get("local_adjacent_solutions"):
        flow.append(Paragraph("Solutions adjacentes locales", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["local_adjacent_solutions"], styles))

    if comp.get("international_benchmarks"):
        flow.append(Paragraph("Benchmarks internationaux", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["international_benchmarks"], styles))

    if comp.get("competitive_advantages"):
        flow.append(Paragraph("Avantages concurrentiels", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["competitive_advantages"], styles))

    if comp.get("limitations"):
        flow.append(Paragraph("Limites de l'analyse", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(comp["limitations"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# Sources et preuves (ForgeCrawler) — tracabilite des affirmations
# ---------------------------------------------------------------------------

_CATEGORY_LABELS = {
    "direct_competitor": "Concurrent direct",
    "adjacent_solution": "Solution adjacente",
    "technology_benchmark": "Benchmark technologique",
    "market_evidence": "Preuve de marche",
    "ecosystem_actor": "Acteur ecosysteme",
}


def _build_sources(data: dict[str, Any], styles: dict) -> list[Any]:
    sources = data["sources"]
    flow: list[Any] = [_section_heading("Sources et preuves", styles)]

    if not sources:
        flow.append(_empty_note(styles))
        flow.append(PageBreak())
        return flow

    flow.append(
        Paragraph(
            "Sources verifiees ayant contribue aux affirmations de ce rapport, "
            "retenues par ForgeCrawler apres filtrage de pertinence et de fiabilite.",
            styles["BodyMuted"],
        )
    )
    flow.append(Spacer(1, 0.2 * cm))

    header = [
        Paragraph("Source", styles["TableHeader"]),
        Paragraph("Categorie", styles["TableHeader"]),
        Paragraph("Pertinence", styles["TableHeader"]),
    ]
    rows = [header]
    for source in sources:
        title_block = Paragraph(
            f"<b>{source['title']}</b><br/>"
            f"<font size=7.5 color='#7c3aed'>{source['url']}</font>",
            styles["TableCell"],
        )
        category = _CATEGORY_LABELS.get(source["category"], source["category"])
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

_CRITERIA_LABELS = {
    "problem_solution_fit": "Adequation\nprobleme",
    "market_potential": "Potentiel\nmarche",
    "execution_feasibility": "Faisabilite",
    "business_model_strength": "Modele\neconomique",
    "competitive_advantage": "Avantage\nconcurrentiel",
    "innovation": "Innovation",
    "scalability": "Scalabilite",
    "financial_viability": "Viabilite\nfinanciere",
    "risk_management": "Gestion\ndes risques",
}


def _score_bar_chart(breakdown: dict[str, float]) -> Drawing:
    labels = [
        _CRITERIA_LABELS.get(key, key) for key in breakdown if breakdown.get(key) is not None
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
    flow: list[Any] = [_section_heading("Startup Score", styles)]

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
        flow.append(Paragraph("Repartition par critere", styles["SubsectionTitle"]))
        flow.append(_score_bar_chart(breakdown))

    if score.get("strengths"):
        flow.append(Paragraph("Forces", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(score["strengths"], styles))

    if score.get("weaknesses"):
        flow.append(Paragraph("Faiblesses", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(score["weaknesses"], styles))

    if score.get("recommendations"):
        recap = [Paragraph("Recommandations", styles["SubsectionTitle"])]
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
    flow: list[Any] = [_section_heading("Session strategique du comite", styles)]

    if not debate.get("votes") and not debate.get("committee"):
        flow.append(_empty_note(styles))
        flow.append(PageBreak())
        return flow

    flow.append(
        Paragraph(
            f"{debate.get('rounds_count', 0)} tours de debat · "
            f"{len(debate.get('committee', []))} membres du comite",
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
                _metric_card("Potentiel strategique", debate.get("potential_score"), styles, metric_w),
                _metric_card("Confiance preuves", debate.get("confidence_score"), styles, metric_w),
                _metric_card("Preparation execution", debate.get("execution_readiness_score"), styles, metric_w),
                _metric_card("Attractivite investissement", debate.get("investment_attractiveness_score"), styles, metric_w),
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
        flow.append(Paragraph("Composition du comite", styles["SubsectionTitle"]))
        header = [
            Paragraph("Role", styles["TableHeader"]),
            Paragraph("Mandat", styles["TableHeader"]),
        ]
        rows = [header]
        for member in debate["committee"]:
            role_label = member["role"] + (
                "" if member["voting_member"] else " (consultatif)"
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
        flow.append(Paragraph("Votes individuels du comite", styles["SubsectionTitle"]))
        header = [
            Paragraph("Membre", styles["TableHeader"]),
            Paragraph("Vote", styles["TableHeader"]),
            Paragraph("Confiance", styles["TableHeader"]),
            Paragraph("Justification", styles["TableHeader"]),
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
        flow.append(_section_heading("Risques et preuves manquantes", styles))
        if debate.get("critical_risks"):
            flow.append(Paragraph("Risques critiques", styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["critical_risks"], styles))
        if debate.get("missing_evidence"):
            flow.append(Paragraph("Preuves manquantes", styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["missing_evidence"], styles))

    if debate.get("go_conditions") or debate.get("no_go_conditions"):
        if debate.get("go_conditions"):
            flow.append(Paragraph("Conditions GO", styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["go_conditions"], styles))
        if debate.get("no_go_conditions"):
            flow.append(Paragraph("Conditions NO-GO", styles["SubsectionTitle"]))
            flow.extend(_bullet_list(debate["no_go_conditions"], styles))

    if debate.get("final_recommendation") or debate.get("improved_idea"):
        flow.append(Paragraph("Recommandation finale du comite", styles["SubsectionTitle"]))
        recap_rows = []
        if debate.get("final_recommendation"):
            recap_rows.append([Paragraph(debate["final_recommendation"], styles["Body"])])
        if debate.get("improved_idea"):
            recap_rows.append(
                [Paragraph(f"<b>Idee amelioree :</b> {debate['improved_idea']}", styles["Body"])]
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
        [Paragraph(persona.get("name") or "Persona", styles["SubsectionTitle"])],
    ]
    if persona.get("role"):
        rows.append([Paragraph(persona["role"], styles["BodyMuted"])])
    if persona.get("profile"):
        rows.append([Paragraph(persona["profile"], styles["Body"])])
    if persona.get("main_pain"):
        rows.append([Paragraph(f"<b>Douleur principale :</b> {persona['main_pain']}", styles["Body"])])
    if persona.get("goals"):
        rows.append([Paragraph("<b>Objectifs</b>", styles["Body"])])
        rows.extend([[p] for p in _bullet_list(persona["goals"], styles)])
    if persona.get("frustrations"):
        rows.append([Paragraph("<b>Frustrations</b>", styles["Body"])])
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
    flow: list[Any] = [_section_heading("Personas", styles)]

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
    flow: list[Any] = [_section_heading("Product Backlog", styles)]

    stories = backlog.get("stories", [])
    if not stories:
        flow.append(_empty_note(styles))
        flow.append(PageBreak())
        return flow

    header = [
        Paragraph("ID", styles["TableHeader"]),
        Paragraph("User story", styles["TableHeader"]),
        Paragraph("Priorite", styles["TableHeader"]),
        Paragraph("Points", styles["TableHeader"]),
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
        (design.PRIMARY, "Planifie"),
        (design.WARNING, "Ideal"),
    ]
    legend.fontSize = 7
    legend.columnMaximum = 1
    drawing.add(chart)
    drawing.add(legend)
    return drawing


def _build_sprint_planning(data: dict[str, Any], styles: dict) -> list[Any]:
    sprint = data["sprint_planning"]
    flow: list[Any] = [_section_heading("Sprint Planning", styles)]

    settings_bits = []
    if sprint.get("sprint_count"):
        settings_bits.append(f"{sprint['sprint_count']} sprints")
    if sprint.get("sprint_duration_days"):
        settings_bits.append(f"{sprint['sprint_duration_days']} jours/sprint")
    if sprint.get("planned_velocity"):
        settings_bits.append(f"velocite prevue {sprint['planned_velocity']} pts")
    if sprint.get("team_size"):
        settings_bits.append(f"equipe de {sprint['team_size']}")
    if settings_bits:
        flow.append(Paragraph(" · ".join(settings_bits), styles["BodyMuted"]))

    for s in sprint.get("sprints", []):
        flow.append(
            Paragraph(
                f"Sprint {s.get('sprint_number')} — {s.get('planned_story_points')} points",
                styles["SubsectionTitle"],
            )
        )
        flow.extend(_bullet_list(s.get("stories", []), styles))

    ideal = sprint.get("ideal_burndown") or []
    planned = sprint.get("planned_burndown") or []
    if ideal and planned:
        flow.append(Paragraph("Diagramme Burndown", styles["SubsectionTitle"]))
        flow.append(_burndown_chart(ideal, planned))

    if sprint.get("scrum_master_advice"):
        flow.append(Paragraph("Conseils Scrum Master", styles["SubsectionTitle"]))
        flow.extend(_bullet_list(sprint["scrum_master_advice"], styles))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# 12-13. Architecture technique + Diagrammes UML
# ---------------------------------------------------------------------------

_DIAGRAM_LABELS = {
    "use_case": "Cas d'usage",
    "class_diagram": "Classes",
    "sequence": "Sequence",
    "activity": "Activite",
}


def _build_solution_architecture(
    data: dict[str, Any],
    styles: dict,
    diagram_images: dict[str, bytes] | None = None,
) -> list[Any]:
    """
    diagram_images : PNG bytes par type de diagramme, deja rendus via
    Kroki en amont (le rendu reseau ne se fait jamais dans ce module,
    purement synchrone et sans acces au client Kroki). Absent ou vide
    pour un diagramme => son image est omise, jamais une image cassee.
    """
    arch = data["solution_architecture"]
    flow: list[Any] = [_section_heading("Architecture technique", styles)]

    if not arch or not arch.get("available"):
        flow.append(
            Paragraph(
                "L'architecture technique n'a pas encore ete generee pour ce projet.",
                styles["BodyMuted"],
            )
        )
        flow.append(PageBreak())
        return flow

    if arch.get("style"):
        flow.append(Paragraph("Style d'architecture", styles["SubsectionTitle"]))
        flow.append(Paragraph(arch["style"], styles["CoverSubtitle"]))

    if arch.get("rationale"):
        flow.extend(_bullet_list(arch["rationale"], styles))

    stack = arch.get("stack") or {}
    if stack:
        flow.append(Paragraph("Stack technique", styles["SubsectionTitle"]))
        for layer, technology in stack.items():
            flow.append(Paragraph(f"• <b>{layer}</b> : {technology}", styles["Body"]))

    if arch.get("database_sql"):
        flow.append(Paragraph("Base de donnees", styles["SubsectionTitle"]))
        flow.append(Paragraph(arch["database_sql"], styles["Code"]))

    flow.append(PageBreak())

    uml = arch.get("uml_diagrams") or {}
    images = diagram_images or {}
    if uml:
        flow.append(_section_heading("Diagrammes UML", styles))
        for diagram_type, label in _DIAGRAM_LABELS.items():
            source = uml.get(diagram_type)
            if not source:
                continue
            flow.append(Paragraph(label, styles["SubsectionTitle"]))
            image_bytes = images.get(diagram_type)
            if image_bytes:
                from reportlab.platypus import Image
                import io

                img = Image(io.BytesIO(image_bytes))
                max_width = design.CONTENT_WIDTH
                if img.drawWidth > max_width:
                    ratio = max_width / img.drawWidth
                    img.drawWidth = max_width
                    img.drawHeight *= ratio
                flow.append(img)
            else:
                flow.append(
                    Paragraph(
                        "Rendu visuel indisponible ; code source omis de l'export.",
                        styles["Caption"],
                    )
                )
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


def build_full_flow(
    data: dict[str, Any],
    styles: dict,
    generated_at: str,
    diagram_images: dict[str, bytes] | None = None,
) -> list[Any]:
    """Point d'entree unique utilise par le router d'export."""
    flow = build_part1_flow(data, styles, generated_at)
    flow.extend(build_part2_flow(data, styles, diagram_images))
    # Le dernier PageBreak de build_part2_flow laisse une page finale
    # vide : on le retire, jamais souhaitable en fin de document.
    if flow and type(flow[-1]).__name__ == "PageBreak":
        flow.pop()
    return flow
