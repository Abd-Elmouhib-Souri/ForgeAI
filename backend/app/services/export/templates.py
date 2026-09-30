"""
Sprint 6.4: export templates per user role.

A template SELECTS and ORDERS the report sections for the PDF and Word
exports. It never generates or rewrites text (no LLM call): every word in
the dossier still comes from the validated analysis.

Section keys are also the label keys of their titles (labels.py), so a
template, its builders and its headings can never drift apart.
"""

from __future__ import annotations

# Complete report, in the historical (CDC) order.
SECTION_KEYS: tuple[str, ...] = (
    "executive_summary",
    "idea_description",
    "market_study",
    "swot",
    "business_model_canvas",
    "competitive_analysis",
    "sources",
    "startup_score",
    "debate_room",
    "personas",
    "product_backlog",
    "sprint_planning",
    "solution_architecture",
)

DEFAULT_TEMPLATE = "business"

TEMPLATES: dict[str, tuple[str, ...]] = {
    # Everything: the complete ForgeAI analysis report.
    "business": SECTION_KEYS,
    # Founder / investor dossier: market and money first, delivery plan,
    # committee verdict; implementation details (backlog, UML) left out.
    "entrepreneur": (
        "executive_summary",
        "idea_description",
        "market_study",
        "personas",
        "business_model_canvas",
        "competitive_analysis",
        "swot",
        "startup_score",
        "sprint_planning",
        "debate_room",
        "sources",
    ),
    # Academic project (PFE / internship report): design and engineering
    # first (users, backlog, sprints, architecture, UML), then the context.
    "student": (
        "executive_summary",
        "idea_description",
        "personas",
        "product_backlog",
        "sprint_planning",
        "solution_architecture",
        "market_study",
        "swot",
        "business_model_canvas",
        "sources",
    ),
    # Advisory report: diagnosis, risks and recommendations first.
    "consultant": (
        "executive_summary",
        "debate_room",
        "swot",
        "market_study",
        "competitive_analysis",
        "business_model_canvas",
        "startup_score",
        "personas",
        "sprint_planning",
        "sources",
    ),
}


def normalize_template(value: str | None) -> str:
    """Canonical template name; empty -> the complete report."""
    return str(value or DEFAULT_TEMPLATE).strip().lower() or DEFAULT_TEMPLATE


def sections_for(template: str | None) -> tuple[str, ...]:
    """Ordered section keys of a template (ValueError when unknown)."""
    name = normalize_template(template)
    if name not in TEMPLATES:
        raise ValueError(f"Unknown export template: {template!r}")
    return TEMPLATES[name]


def document_name(template: str | None) -> str:
    """Download file stem: business_plan, student_report, ..."""
    name = normalize_template(template)
    return "business_plan" if name == DEFAULT_TEMPLATE else f"{name}_report"
