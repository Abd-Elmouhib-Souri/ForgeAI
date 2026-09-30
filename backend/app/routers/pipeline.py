"""
Post-analysis pipeline API.

GET  /projects/{id}/pipeline      -> reconciled state of Plan + Architecture
POST /projects/{id}/pipeline/run  -> manual "Relancer" (202, runs in background)

Both endpoints use the same ownership guard as every project router: the
project is filtered by user_id in the query, never fetched by bare id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import Project, User
from app.security import get_current_user
from app.services.post_analysis_pipeline import effective_state, post_analysis_pipeline

router = APIRouter(prefix="/projects", tags=["Pipeline"])


async def _get_project_or_404(project_id: int, db: AsyncSession, current_user: User) -> Project:
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


def _public_state(project: Project) -> dict:
    return effective_state(
        project_id=project.id,
        analysis_status=project.analysis_status,
        analysis_data=project.analysis_data if isinstance(project.analysis_data, dict) else None,
    )


@router.get("/{project_id}/pipeline")
async def get_pipeline(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    return _public_state(project)


@router.post("/{project_id}/pipeline/run", status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    if project.analysis_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "analysis_not_completed",
                "message": "Terminez l'analyse avant de générer le plan et l'architecture.",
            },
        )
    # Close this request's view before the background run writes new state.
    await db.rollback()
    await post_analysis_pipeline.reset_for_manual_run(project_id)
    await db.refresh(project)
    return _public_state(project)
