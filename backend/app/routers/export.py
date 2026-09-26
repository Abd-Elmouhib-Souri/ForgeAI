from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.integrations.kroki_client import KrokiClient
from app.models import Export, ExportFormat, Project, User
from app.security import get_current_user
from app.services.export.data_assembly import assemble_export_data
from app.services.export.pdf_builder import build_full_flow
from app.services.export.pdf_design import build_document, build_styles
from app.services.export import storage
from app.services.solution_architecture_plan_service import (
    ANALYSIS_DATA_KEY as SOLUTION_ARCHITECTURE_KEY,
    deserialize_current,
)

router = APIRouter(prefix="/projects", tags=["Export"])

# Les fichiers generes sont PRIVES (settings.EXPORTS_DIR, jamais monte en
# StaticFiles). Export.file_path contient une cle de stockage aleatoire
# "<project_id>/<uuid>.pdf" ; le seul acces est la route de telechargement
# authentifiee ci-dessous, filtree sur le proprietaire dans la requete SQL.
# (Avant Sprint 6.1 hardening : URL publique previsible /exports/<id>/...)

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


def _download_url(project_id: int, export_id: int) -> str:
    # Chemin relatif a l'API : le frontend l'appelle avec son client axios
    # (bearer en memoire), jamais comme un simple lien public.
    return f"/projects/{project_id}/exports/{export_id}/download"


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

    # Nouvelle cle a chaque export : l'historique ne pointe jamais vers un
    # fichier ecrase par un export plus recent.
    storage_key = storage.new_storage_key(project_id, "pdf")
    target = storage.path_for_key(storage_key)

    styles = build_styles()
    generated_at = datetime.datetime.now().strftime("%d/%m/%Y")
    flow = build_full_flow(data, styles, generated_at, diagram_images)

    def _render(temp_path: str) -> None:
        # ReportLab est synchrone et CPU-bound.
        build_document(temp_path, project.title).multiBuild(flow)

    # Hors event loop : l'API reste reactive pendant la generation.
    # Ecriture atomique : jamais de PDF partiel sur disque.
    await asyncio.to_thread(storage.write_atomically, target, _render)

    # La ligne Export n'est creee qu'apres un fichier complet.
    export_row = Export(
        project_id=project_id,
        format=ExportFormat.PDF,
        file_path=storage_key,
        template_used="business",
    )
    db.add(export_row)
    try:
        await db.commit()
    except Exception:
        # Pas de fichier orphelin si la base refuse la ligne.
        target.unlink(missing_ok=True)
        raise
    await db.refresh(export_row)

    return {
        "export_id": export_row.id,
        "format": "pdf",
        "download_url": _download_url(project_id, export_row.id),
        "file_name": storage.download_filename(project.title, "business_plan", "pdf"),
        "created_at": export_row.created_at,
    }


# Nom lisible du document selon le format (Word / pitch deck en 6.2 / 6.3).
_DOCUMENT_NAMES = {
    ExportFormat.PDF: "business_plan",
    ExportFormat.WORD: "business_plan",
    ExportFormat.POWERPOINT: "pitch_deck",
}


@router.get("/{project_id}/exports/{export_id}/download")
async def download_export(
    project_id: int,
    export_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Propriete verifiee DANS la requete (jointure projects.user_id) : un
    # export d'un autre utilisateur est indiscernable d'un export inexistant.
    result = await db.execute(
        select(Export)
        .join(Project, Project.id == Export.project_id)
        .where(
            Export.id == export_id,
            Export.project_id == project_id,
            Project.user_id == current_user.id,
        )
        .options(selectinload(Export.project))
    )
    export_row = result.scalar_one_or_none()
    if export_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export introuvable ou accès interdit.",
        )

    path = storage.resolve_storage_path(export_row.file_path, project_id=project_id)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier d'export introuvable sur le serveur ; relancez l'export.",
        )

    extension = storage.extension_of(path)
    return FileResponse(
        path,
        media_type=storage.MEDIA_TYPES.get(extension, "application/octet-stream"),
        filename=storage.download_filename(
            export_row.project.title,
            _DOCUMENT_NAMES.get(export_row.format, "export"),
            extension,
        ),
        # Document prive : aucun cache partage (proxy, CDN).
        headers={"Cache-Control": "private, no-store"},
    )
