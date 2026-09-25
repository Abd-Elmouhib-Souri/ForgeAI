from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.integrations.kroki_client import KrokiClient
from app.models import Export, ExportFormat, Project, User
from app.security import get_current_user
from app.services.export.data_assembly import assemble_export_data
from app.services.export.pdf_builder import build_full_flow
from app.services.export.pdf_design import build_document, build_styles
from app.services.solution_architecture_plan_service import (
    ANALYSIS_DATA_KEY as SOLUTION_ARCHITECTURE_KEY,
    deserialize_current,
)

router = APIRouter(prefix="/projects", tags=["Export"])

# WORKDIR du conteneur backend confirme par les traces d'erreur observees
# cette nuit ("/app/app/routers/..."). Les fichiers generes sont donc
# ecrits ici, et serves publiquement via le montage StaticFiles sur
# "/exports" ajoute dans main.py, exactement la convention documentee au
# CDC : file_path=f"/exports/{project.id}/business_plan.pdf".
EXPORTS_ROOT = Path("/app/exports")

_kroki_client: KrokiClient | None = None


def _get_kroki_client() -> KrokiClient:
    global _kroki_client
    if _kroki_client is None:
        _kroki_client = KrokiClient.from_environment()
    return _kroki_client


async def _get_project_or_404(
    project_id: int,
    db: AsyncSession,
    current_user: User,
) -> Project:
    # Meme garde de securite que solution_architect.py et
    # project_manager.py : filtrage user_id explicite dans la requete,
    # jamais un GET-by-id nu.
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable ou accès interdit.",
        )
    return project


async def _fetch_diagram_images(
    analysis_data: dict,
) -> dict[str, bytes]:
    """
    Rendu PNG des diagrammes UML pour l'export, uniquement si une
    architecture technique canonique existe deja pour ce projet. Kroki
    reste un moteur de rendu optionnel : un diagramme manquant produit
    un texte de repli dans pdf_builder.py, jamais une erreur bloquante
    pour le reste de l'export.
    """
    envelope = analysis_data.get(SOLUTION_ARCHITECTURE_KEY)
    if not isinstance(envelope, dict):
        return {}

    canonical = deserialize_current(envelope)
    if canonical is None:
        return {}

    client = _get_kroki_client()
    try:
        return await client.render_uml_bundle_png(canonical.uml)
    except Exception:
        # Echec total du rendu (Kroki indisponible) : l'export continue
        # sans images, jamais un blocage de tout le document pour une
        # amelioration visuelle optionnelle.
        return {}


@router.post("/{project_id}/export/pdf")
async def export_project_pdf(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    analysis_data = project.analysis_data if isinstance(project.analysis_data, dict) else {}

    data = assemble_export_data(
        analysis_data=analysis_data,
        project_name=project.title,
    )
    diagram_images = await _fetch_diagram_images(analysis_data)

    project_dir = EXPORTS_ROOT / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / "business_plan.pdf"

    styles = build_styles()
    generated_at = datetime.datetime.now().strftime("%d/%m/%Y")
    doc = build_document(str(file_path), project.title)
    flow = build_full_flow(data, styles, generated_at, diagram_images)
    doc.multiBuild(flow)

    public_path = f"/exports/{project_id}/business_plan.pdf"

    export_row = Export(
        project_id=project_id,
        format=ExportFormat.PDF,
        file_path=public_path,
        template_used="business",
    )
    db.add(export_row)
    await db.commit()
    await db.refresh(export_row)

    return {
        "export_id": export_row.id,
        "format": "pdf",
        "file_path": public_path,
        "created_at": export_row.created_at,
    }
