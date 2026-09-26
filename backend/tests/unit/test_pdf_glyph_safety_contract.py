"""
PDF glyph-safety contract.

Observed RED (project 31 "TawlaPro", real export, 27 Sept 2026): black
squares in "Wi■Fi", "multi■restaurant", "code■base". The LLM writes
U+2011 NON-BREAKING HYPHEN (6x) and U+202F NARROW NO-BREAK SPACE (3x);
the PDF's built-in Helvetica/Courier only cover Windows-1252, so every
other character is drawn as a black box. Word is unaffected (full fonts).

Universal fix: every Paragraph built by pdf_builder maps known typographic
characters to a visually equivalent Windows-1252 character. Unknown
characters (e.g. Arabic script) are kept untouched: rendering them needs an
embedded Unicode font, a separate enhancement.
"""

from __future__ import annotations

import pytest

from app.services.export import pdf_builder
from app.services.export.pdf_design import build_styles


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Wi‑Fi", "Wi-Fi"),                     # observed
        ("mise à jour en < 2 s", "mise à jour en < 2 s"),  # observed
        ("multi‐tenant", "multi-tenant"),
        ("− 5 %", "- 5 %"),
        ("10 000", "10 000"),
        ("A → B", "A -> B"),
        ("x ≤ 3 et y ≥ 4", "x <= 3 et y >= 4"),
        ("zéro​largeur", "zérolargeur"),
    ],
)
def test_typographic_characters_become_printable(raw, expected):
    assert pdf_builder.pdf_safe_text(raw) == expected


def test_windows_1252_text_is_left_untouched():
    text = "Résumé exécutif — « Étude » … l’équipe – 3 € ™"
    assert pdf_builder.pdf_safe_text(text) == text


def test_unknown_scripts_are_not_destroyed():
    # Arabic needs an embedded Unicode font (separate enhancement): never
    # silently delete or replace a user's words.
    assert pdf_builder.pdf_safe_text("مطعم") == "مطعم"


def test_every_pdf_paragraph_is_sanitized():
    styles = build_styles()
    paragraph = pdf_builder.Paragraph("isolation multi‑restaurant", styles["Body"])
    assert paragraph.text == "isolation multi-restaurant"
    # The SQL block goes through the same Paragraph.
    code = pdf_builder._code_paragraph("-- Wi‑Fi\nSELECT 1;", styles)
    assert "‑" not in code.text
