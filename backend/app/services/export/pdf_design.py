from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageTemplate

# ---------------------------------------------------------------------------
# Palette — reprend exactement les couleurs Tailwind deja utilisees dans le
# frontend (violet-700 pour l'accent principal, slate pour le texte, et les
# memes couleurs semantiques que les badges de statut du frontend). Aucune
# couleur improvisee ici : un lecteur qui a vu le produit web doit
# reconnaitre la meme identite dans le document exporte.
# ---------------------------------------------------------------------------

PRIMARY = colors.HexColor("#7c3aed")  # violet-700
PRIMARY_LIGHT = colors.HexColor("#f5f3ff")  # violet-50
PRIMARY_DARK = colors.HexColor("#5b21b6")  # violet-800

TEXT_DARK = colors.HexColor("#0f172a")  # slate-900
TEXT_MUTED = colors.HexColor("#475569")  # slate-600
TEXT_FAINT = colors.HexColor("#94a3b8")  # slate-400

BORDER = colors.HexColor("#e2e8f0")  # slate-200
SURFACE = colors.HexColor("#f8fafc")  # slate-50

SUCCESS = colors.HexColor("#059669")  # emerald-600
SUCCESS_LIGHT = colors.HexColor("#ecfdf5")  # emerald-50
WARNING = colors.HexColor("#d97706")  # amber-600
WARNING_LIGHT = colors.HexColor("#fffbeb")  # amber-50
DANGER = colors.HexColor("#dc2626")  # red-600
DANGER_LIGHT = colors.HexColor("#fef2f2")  # red-50

WHITE = colors.white

# ---------------------------------------------------------------------------
# Mise en page
# ---------------------------------------------------------------------------

PAGE_SIZE = A4
LANDSCAPE_PAGE_SIZE = landscape(A4)
MARGIN_LEFT = 2.2 * cm
MARGIN_RIGHT = 2.2 * cm
MARGIN_TOP = 2.6 * cm
MARGIN_BOTTOM = 2.4 * cm

CONTENT_WIDTH = PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT
LANDSCAPE_CONTENT_WIDTH = LANDSCAPE_PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT

# Page furniture text now comes from labels.py (accented, per language).


# ---------------------------------------------------------------------------
# Styles de texte
# ---------------------------------------------------------------------------

def build_styles() -> dict[str, ParagraphStyle]:
    """
    Un dictionnaire de styles nommes, construit a la demande (jamais un
    singleton module-level partage) pour eviter toute mutation croisee
    entre deux exports generes en parallele par des requetes concurrentes.
    """
    return {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=TEXT_DARK,
            spaceAfter=6,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=TEXT_MUTED,
            spaceAfter=4,
        ),
        "CoverMeta": ParagraphStyle(
            "CoverMeta",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=TEXT_FAINT,
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=PRIMARY_DARK,
            spaceBefore=4,
            spaceAfter=12,
        ),
        "SubsectionTitle": ParagraphStyle(
            "SubsectionTitle",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=TEXT_DARK,
            spaceBefore=10,
            spaceAfter=6,
            # Never leave a subsection title alone at the bottom of a page
            # (observed: "Base de donnees" orphaned from its table).
            keepWithNext=1,
        ),
        "Body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=TEXT_DARK,
            spaceAfter=6,
        ),
        "BodyMuted": ParagraphStyle(
            "BodyMuted",
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=TEXT_MUTED,
            spaceAfter=6,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=TEXT_DARK,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=3,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=WHITE,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=TEXT_DARK,
        ),
        "Caption": ParagraphStyle(
            "Caption",
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=TEXT_FAINT,
        ),
        "QuadrantHeading": ParagraphStyle(
            "QuadrantHeading",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=WHITE,
        ),
        "Code": ParagraphStyle(
            "Code",
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=SUCCESS,
        ),
    }


# ---------------------------------------------------------------------------
# En-tete / pied de page — dessines sur chaque page via un callback canvas.
# La page de couverture (premiere page) n'a ni en-tete ni pied de page ;
# toutes les pages suivantes reprennent le titre du projet et la
# numerotation. Deux gabarits de page distincts geres par BaseDocTemplate.
# ---------------------------------------------------------------------------

def make_page_callbacks(project_title: str, labels: dict[str, str] | None = None):
    from .labels import FR

    labels = labels or FR
    footer_text = f"{labels['generated_by']} DotJcom ForgeAI"

    def _on_cover_page(canvas: Canvas, doc: BaseDocTemplate) -> None:
        # Bandeau violet en pied de la couverture, sans numero de page.
        canvas.saveState()
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, 0, PAGE_SIZE[0], 0.9 * cm, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(PAGE_SIZE[0] / 2, 0.32 * cm, footer_text)
        canvas.restoreState()

    def _on_content_page(canvas: Canvas, doc: BaseDocTemplate) -> None:
        canvas.saveState()

        # En-tete a deux niveaux, a l'image du CDC : marque a gauche,
        # classification a droite, separateur fin.
        canvas.setFillColor(PRIMARY)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(MARGIN_LEFT, PAGE_SIZE[1] - 1.3 * cm, "ForgeAI")
        canvas.setFillColor(TEXT_FAINT)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            PAGE_SIZE[0] - MARGIN_RIGHT,
            PAGE_SIZE[1] - 1.3 * cm,
            labels["confidential_document"],
        )
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(MARGIN_LEFT, PAGE_SIZE[1] - 1.7 * cm, project_title)
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.6)
        canvas.line(
            MARGIN_LEFT,
            PAGE_SIZE[1] - 1.85 * cm,
            PAGE_SIZE[0] - MARGIN_RIGHT,
            PAGE_SIZE[1] - 1.85 * cm,
        )

        # Pied de page en trois parties, a l'image du CDC : entreprise,
        # nom du document, numero de page.
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TEXT_FAINT)
        canvas.drawString(MARGIN_LEFT, 1.2 * cm, "DotJcom Ltd")
        canvas.drawCentredString(
            PAGE_SIZE[0] / 2,
            1.2 * cm,
            f"{labels['report_footer']} — {project_title}",
        )
        canvas.drawRightString(
            PAGE_SIZE[0] - MARGIN_RIGHT, 1.2 * cm, f"{labels['page']} {doc.page}"
        )
        canvas.restoreState()

    def _on_content_landscape_page(canvas: Canvas, doc: BaseDocTemplate) -> None:
        # Page paysage dediee au contenu trop large pour le format
        # portrait (ex. Business Model Canvas a 5 colonnes) : la taille
        # de page est basculee explicitement sur ce canvas avant de
        # dessiner, independamment du gabarit portrait par defaut du
        # document.
        canvas.setPageSize(LANDSCAPE_PAGE_SIZE)
        canvas.saveState()

        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(
            MARGIN_LEFT, LANDSCAPE_PAGE_SIZE[1] - 1.4 * cm, project_title
        )
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.6)
        canvas.line(
            MARGIN_LEFT,
            LANDSCAPE_PAGE_SIZE[1] - 1.6 * cm,
            LANDSCAPE_PAGE_SIZE[0] - MARGIN_RIGHT,
            LANDSCAPE_PAGE_SIZE[1] - 1.6 * cm,
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_FAINT)
        canvas.drawString(MARGIN_LEFT, 1.2 * cm, footer_text)
        canvas.drawRightString(
            LANDSCAPE_PAGE_SIZE[0] - MARGIN_RIGHT, 1.2 * cm, f"{labels['page']} {doc.page}"
        )
        canvas.restoreState()

    return _on_cover_page, _on_content_page, _on_content_landscape_page


class _ExportDocTemplate(BaseDocTemplate):
    """
    BaseDocTemplate standard, avec le seul ajout necessaire pour un vrai
    sommaire dynamique : chaque flowable de titre de section (marque
    d'un attribut toc_level) notifie sa page reelle apres mise en page.
    Necessite doc.multiBuild(story) au lieu de doc.build(story) pour que
    reportlab refasse la pagination jusqu'a stabilisation du sommaire.
    """

    def afterFlowable(self, flowable):
        level = getattr(flowable, "toc_level", None)
        if level is None:
            return
        text = getattr(flowable, "toc_text", None)
        if text is None and hasattr(flowable, "getPlainText"):
            text = flowable.getPlainText()
        if text:
            self.notify("TOCEntry", (level, text, self.page))


def build_document(
    file_path: str,
    project_title: str,
    labels: dict[str, str] | None = None,
) -> BaseDocTemplate:
    """
    Construit un BaseDocTemplate a trois gabarits : "Cover" (une page,
    sans en-tete/pied), "Content" (portrait, la majorite des pages) et
    "ContentLandscape" (paysage, reserve au contenu trop large pour le
    portrait comme le Business Model Canvas). pdf_builder.py bascule
    entre eux via NextPageTemplate(...).
    """
    on_cover_page, on_content_page, on_content_landscape_page = (
        make_page_callbacks(project_title, labels)
    )

    frame_cover = Frame(
        MARGIN_LEFT,
        MARGIN_BOTTOM,
        PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT,
        PAGE_SIZE[1] - MARGIN_BOTTOM - MARGIN_TOP,
        id="cover",
    )
    frame_content = Frame(
        MARGIN_LEFT,
        MARGIN_BOTTOM,
        PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT,
        PAGE_SIZE[1] - MARGIN_BOTTOM - MARGIN_TOP,
        id="content",
    )
    frame_content_landscape = Frame(
        MARGIN_LEFT,
        MARGIN_BOTTOM,
        LANDSCAPE_PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT,
        LANDSCAPE_PAGE_SIZE[1] - MARGIN_BOTTOM - MARGIN_TOP,
        id="content_landscape",
    )

    doc = _ExportDocTemplate(
        file_path,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title=project_title,
        author="DotJcom ForgeAI",
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="Cover", frames=[frame_cover], onPage=on_cover_page),
            PageTemplate(
                id="Content", frames=[frame_content], onPage=on_content_page
            ),
            PageTemplate(
                id="ContentLandscape",
                frames=[frame_content_landscape],
                onPage=on_content_landscape_page,
            ),
        ]
    )
    return doc


def build_toc():
    """
    Sommaire dynamique : une seule entree de niveau (les 15 titres de
    section, aucune sous-section imbriquee necessaire pour ce rapport),
    stylee pour rester coherente avec le reste du document. Les numeros
    de page affiches sont reels, remplis par reportlab lors du second
    passage de doc.multiBuild().
    """
    from reportlab.platypus.tableofcontents import TableOfContents

    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCEntry",
            fontName="Helvetica",
            fontSize=11,
            leading=18,
            textColor=TEXT_DARK,
            leftIndent=0,
        ),
    ]
    toc.dotsMinLevel = 0
    return toc


# Reexporte pour que pdf_builder.py puisse basculer de gabarit sans
# importer platypus directement.
__all__ = [
    "PRIMARY",
    "PRIMARY_LIGHT",
    "PRIMARY_DARK",
    "TEXT_DARK",
    "TEXT_MUTED",
    "TEXT_FAINT",
    "BORDER",
    "SURFACE",
    "SUCCESS",
    "SUCCESS_LIGHT",
    "WARNING",
    "WARNING_LIGHT",
    "DANGER",
    "DANGER_LIGHT",
    "WHITE",
    "build_styles",
    "build_document",
    "NextPageTemplate",
]
