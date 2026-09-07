from __future__ import annotations

import logging
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.agents.product_owner_agent import ProductOwnerGenerationError
from app.agents.scrum_master_agent import ScrumMasterGenerationError
from app.models import Project, User
from app.schemas.project_management import (
    BacklogLocksUpdateV1,
    PlanningSettingsUpdateV1,
)
from app.security import get_current_user
from app.services.project_management_plan_service import (
    ProjectManagementPlanError,
    project_management_plan_service,
)


router = APIRouter(prefix="/projects", tags=["Project Manager"])
logger = logging.getLogger(__name__)


async def _get_project_or_404(
    project_id: int,
    db: AsyncSession,
    current_user: User,
) -> Project:
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
    envelope = data.get("project_manager")
    return envelope if isinstance(envelope, Mapping) else None


def _plan_or_404(project: Project):
    plan = project_management_plan_service.deserialize_current(
        _stored_envelope(project)
    )
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun plan Agile n’a encore été généré pour ce projet.",
        )
    return plan


def _ensure_fresh(project: Project, plan) -> None:
    if project_management_plan_service.is_stale(
        plan=plan,
        project_id=project.id,
        analysis_data=project.analysis_data,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le plan est obsolète : générez un nouveau plan depuis le contexte actuel.",
        )


def _response(project: Project, plan) -> dict[str, Any]:
    stale = project_management_plan_service.is_stale(
        plan=plan,
        project_id=project.id,
        analysis_data=project.analysis_data,
    )
    return {"plan": plan.model_dump(mode="json"), "stale": stale}


async def _persist(project: Project, plan) -> None:
    analysis_data = dict(project.analysis_data or {})
    analysis_data["project_manager"] = (
        project_management_plan_service.serialize_with_history(
            current=plan,
            previous_envelope=_stored_envelope(project),
        )
    )
    project.analysis_data = analysis_data


def _raise_plan_error(exc: ProjectManagementPlanError) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


@router.post("/{project_id}/project-manager/generate", status_code=status.HTTP_201_CREATED)
async def generate_project_manager_plan(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    previous = project_management_plan_service.deserialize_current(
        _stored_envelope(project)
    )
    try:
        plan = await project_management_plan_service.generate(
            project_id=project.id,
            analysis_data=project.analysis_data,
            settings=previous.settings if previous else None,
            revision=(previous.revision + 1) if previous else 1,
        )
    except ProjectManagementPlanError as exc:
        _raise_plan_error(exc)
    except (ProductOwnerGenerationError, ScrumMasterGenerationError) as exc:
        unavailable = exc.code == "generation_temporarily_unavailable"
        logger.warning(
            "[ProjectManager] AI generation rejected | project_id=%s | code=%s | details=%s",
            project_id,
            exc.code,
            exc.details,
        )
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if unavailable
                else status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "code": exc.code,
                "message": str(exc),
                "details": exc.details,
            },
        ) from exc
    except Exception as exc:
        logger.exception(
            "[ProjectManager] Plan generation failed | project_id=%s",
            project_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="La génération Agile n’a pas pu aboutir. Vérifiez la configuration IA puis réessayez.",
        ) from exc

    await _persist(project, plan)
    await db.commit()
    await db.refresh(project)
    return _response(project, plan)


@router.get("/{project_id}/project-manager")
async def get_project_manager_plan(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    return _response(project, _plan_or_404(project))


@router.patch("/{project_id}/project-manager/settings")
async def update_project_manager_settings(
    project_id: int,
    update: PlanningSettingsUpdateV1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    plan = _plan_or_404(project)
    _ensure_fresh(project, plan)
    try:
        settings = project_management_plan_service.settings_from_update(plan.settings, update)
        next_plan = project_management_plan_service.replan(
            stored_plan=plan,
            settings=settings,
        )
    except ProjectManagementPlanError as exc:
        _raise_plan_error(exc)
    await _persist(project, next_plan)
    await db.commit()
    await db.refresh(project)
    return _response(project, next_plan)


@router.patch("/{project_id}/project-manager/backlog")
async def update_project_manager_backlog_locks(
    project_id: int,
    update: BacklogLocksUpdateV1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    plan = _plan_or_404(project)
    _ensure_fresh(project, plan)
    try:
        next_plan = project_management_plan_service.update_locks(
            stored_plan=plan,
            update=update,
        )
    except ProjectManagementPlanError as exc:
        _raise_plan_error(exc)
    await _persist(project, next_plan)
    await db.commit()
    await db.refresh(project)
    return _response(project, next_plan)


@router.post("/{project_id}/project-manager/replan")
async def replan_project_manager_plan(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    plan = _plan_or_404(project)
    _ensure_fresh(project, plan)
    try:
        next_plan = project_management_plan_service.replan(stored_plan=plan)
    except ProjectManagementPlanError as exc:
        _raise_plan_error(exc)
    await _persist(project, next_plan)
    await db.commit()
    await db.refresh(project)
    return _response(project, next_plan)


@router.get("/{project_id}/project-manager/sprints")
async def get_project_manager_sprints(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    plan = _plan_or_404(project)
    return {"sprints": plan.sprints, "overflow_story_ids": plan.overflow_story_ids, "stale": project_management_plan_service.is_stale(plan=plan, project_id=project.id, analysis_data=project.analysis_data)}


@router.get("/{project_id}/project-manager/metrics")
async def get_project_manager_metrics(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db, current_user)
    plan = _plan_or_404(project)
    return {"metrics": plan.metrics.model_dump(mode="json"), "stale": project_management_plan_service.is_stale(plan=plan, project_id=project.id, analysis_data=project.analysis_data)}
