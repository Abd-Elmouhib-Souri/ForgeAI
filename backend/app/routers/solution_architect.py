from __future__ import annotations

import logging
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.integrations.kroki_client import KrokiClient
from app.models import Project, User
from app.security import get_current_user
from app.services.solution_architecture_plan_service import (
    ANALYSIS_DATA_KEY,
    SolutionArchitecturePlanError,
    deserialize_current,
    generate,
    is_stale,
    serialize,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Solution Architect"])

# Client Kroki paresseux : une seule instance par process, construite au
# premier appel a partir des variables d'environnement (KROKI_ENABLED,
# KROKI_BASE_URL). Si Kroki n'est pas configure, chaque rendu individuel
# echoue proprement en status="unavailable" (gere par render_uml_bundle),
# jamais une exception non geree.
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
    # Filtrage user_id explicite dans la requête — jamais un GET-by-id nu.
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


def _stored_envelope(project: Project) -> Mapping[str, Any] | None:
    data = project.analysis_data
    if not isinstance(data, Mapping):
        return None
    envelope = data.get(ANALYSIS_DATA_KEY)
    return envelope if isinstance(envelope, Mapping) else None


async def _persist(project: Project, canonical: Any) -> None:
    # Réassignation complète du dict, jamais de mutation in-place : identique
    # au pattern _persist de project_manager.py, requis pour que SQLAlchemy
    # détecte le changement sur la colonne JSON.
    analysis_data = dict(project.analysis_data or {})
    analysis_data[ANALYSIS_DATA_KEY] = serialize(canonical)
    project.analysis_data = analysis_data


def _raise_plan_error(exc: SolutionArchitecturePlanError) -> None:
    status_code = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.code == "generation_temporarily_unavailable"
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    raise HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


@router.post("/{project_id}/solution-architecture/generate")
async def generate_solution_architecture(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    try:
        canonical = await generate(
            project_id=project.id,
            analysis_data=project.analysis_data,
        )
    except SolutionArchitecturePlanError as exc:
        _raise_plan_error(exc)
        return  # inatteignable : _raise_plan_error lève toujours

    await _persist(project, canonical)
    await db.commit()
    return {
        "solution_architecture": canonical.model_dump(mode="json"),
        "stale": False,
    }


@router.get("/{project_id}/solution-architecture")
async def get_solution_architecture(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    canonical = deserialize_current(_stored_envelope(project))
    if canonical is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune architecture technique générée pour ce projet.",
        )
    return {
        "solution_architecture": canonical.model_dump(mode="json"),
        "stale": is_stale(canonical=canonical, analysis_data=project.analysis_data),
    }


@router.get("/{project_id}/solution-architecture/render")
async def render_solution_architecture_uml(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rendu visuel des 4 diagrammes PlantUML deja canoniques en SVG, via
    # Kroki. Kroki est un simple moteur de rendu, jamais une autorite : si
    # indisponible, chaque diagramme individuel reste "unavailable" sans
    # jamais invalider le PlantUML canonique deja persiste.
    project = await _get_project_or_404(project_id, db, current_user)
    canonical = deserialize_current(_stored_envelope(project))
    if canonical is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune architecture technique générée pour ce projet.",
        )

    client = _get_kroki_client()
    results = await client.render_uml_bundle(canonical.uml)

    return {
        diagram_type: {
            "status": result.status,
            "svg": result.svg,
            "error_code": result.error_code,
            "error_message": result.error_message,
        }
        for diagram_type, result in results.items()
    }


@router.post("/{project_id}/solution-architecture/regenerate")
async def regenerate_solution_architecture(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Alias explicite de /generate — deux noms d'endpoint distincts pour le
    # contrat, même logique. Documenté dans FORGEAI_SPRINT5_PLAN_COMPLET (S5-K).
    return await generate_solution_architecture(project_id, current_user, db)
