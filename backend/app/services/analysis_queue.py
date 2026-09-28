"""
Sprint 7.6: analysis runs queued in the database.

Decision (28 Sept 2026): the admin API never executes an analysis. It only
ENQUEUES a new run (``analysis_enqueued_at``); the public API is the only
process that runs analyses, through ``AnalysisQueueWorker``.

One place for:
  * ``is_stalled``: what "stuck" means (queued/running without any sign of
    life for ANALYSIS_STALE_AFTER_SECONDS, e.g. interrupted by a restart);
  * ``prepare_new_run``: the reset shared by the owner's start and the
    admin relaunch (same fields, same kept project-manager plan);
  * ``claim_and_start``: an atomic claim, so a queued run starts exactly
    once even with several public API processes polling.

Stale-write safety is still ``analysis_run_id``: an old task that wakes up
after a relaunch sees another run id and discards its results.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import select, update

from app.config import settings
from app.models import Project

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "running")
ADMIN_RELAUNCH_STEP = "Relance demandée par un administrateur"

Launcher = Callable[[int, str], Awaitable[None]]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes: they are stored in UTC.
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def is_stalled(status: str | None, heartbeat: datetime | None, now: datetime | None = None) -> bool:
    """True for a queued/running analysis that stopped giving signs of life."""
    if status not in ACTIVE_STATUSES:
        return False
    last = as_utc(heartbeat)
    if last is None:
        return True
    return (now or utc_now()) - last > timedelta(seconds=settings.ANALYSIS_STALE_AFTER_SECONDS)


def is_live(project: Project) -> bool:
    """An analysis is really in progress: a new run must not start."""
    return project.analysis_status in ACTIVE_STATUSES and not is_stalled(
        project.analysis_status, project.analysis_heartbeat_at
    )


def new_run_id() -> str:
    from app.services.analysis_run_guard import analysis_run_guard

    return analysis_run_guard.new_run_id()


def prepare_new_run(project: Project, *, step: str) -> str:
    """Reset the project for a new run and return its run id (caller commits)."""
    run_id = new_run_id()
    now = utc_now()
    project.analysis_run_id = run_id
    project.analysis_attempt = int(project.analysis_attempt or 0) + 1
    project.analysis_heartbeat_at = now
    project.analysis_status = "queued"
    project.analysis_step = step
    project.analysis_progress = 2
    # The project-manager plan survives a new run (it is the user's work).
    existing = project.analysis_data or {}
    project_manager = existing.get("project_manager") if isinstance(existing, dict) else None
    project.analysis_data = {"project_manager": project_manager} if isinstance(project_manager, dict) else None
    project.analysis_error = None
    project.analysis_started_at = now
    project.analysis_completed_at = None
    project.analysis_enqueued_at = None
    return run_id


def enqueue(project: Project) -> str:
    """Admin relaunch: new run, picked up by the public API worker."""
    run_id = prepare_new_run(project, step=ADMIN_RELAUNCH_STEP)
    project.analysis_enqueued_at = utc_now()
    return run_id


_running_tasks: set[asyncio.Task] = set()


def _spawn(coroutine: Awaitable[None]) -> None:
    task = asyncio.ensure_future(coroutine)
    _running_tasks.add(task)  # keep a reference until it finishes
    task.add_done_callback(_running_tasks.discard)


async def claim_and_start(session_factory, launch: Launcher, *, batch: int = 5) -> int:
    """
    Start the queued runs. Returns how many this call claimed.

    The claim is one UPDATE guarded by the run id and "still queued": when
    two workers race for the same row, exactly one UPDATE matches.
    """
    async with session_factory() as db:
        candidates = (
            await db.execute(
                select(Project.id, Project.analysis_run_id)
                .where(Project.analysis_enqueued_at.is_not(None))
                .order_by(Project.analysis_enqueued_at)
                .limit(batch)
            )
        ).all()
    claimed = 0
    for project_id, run_id in candidates:
        async with session_factory() as db:
            result = await db.execute(
                update(Project)
                .where(
                    Project.id == project_id,
                    Project.analysis_run_id == run_id,
                    Project.analysis_enqueued_at.is_not(None),
                )
                .values(analysis_enqueued_at=None)
            )
            await db.commit()
        if result.rowcount == 1:
            claimed += 1
            logger.info("[AnalysisQueue] run claimed | project_id=%s | run_id=%s", project_id, run_id)
            _spawn(launch(project_id, run_id))
    return claimed


def _default_launcher(project_id: int, run_id: str) -> Awaitable[None]:
    # Looked up at call time (import cycle + tests replace the function).
    from app.routers import projects as projects_router

    return projects_router.run_project_analysis_background(project_id, run_id)


class AnalysisQueueWorker:
    """Polling loop of the PUBLIC API process (never started by the admin API)."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        from app.database import AsyncSessionLocal

        while True:
            try:
                await claim_and_start(AsyncSessionLocal, _default_launcher)
            except asyncio.CancelledError:
                raise
            except Exception:  # database hiccup: log and keep polling
                logger.exception("[AnalysisQueue] polling failed")
            await asyncio.sleep(settings.ANALYSIS_QUEUE_POLL_SECONDS)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None


analysis_queue_worker = AnalysisQueueWorker()


def audit_snapshot(project: Project) -> dict[str, Any]:
    """Public state of a run, for the audit log (no analysis content)."""
    heartbeat = as_utc(project.analysis_heartbeat_at)
    return {
        "analysis_status": project.analysis_status,
        "analysis_step": project.analysis_step,
        "analysis_attempt": project.analysis_attempt,
        "analysis_heartbeat_at": heartbeat.isoformat() if heartbeat else None,
        "analysis_stalled": is_stalled(project.analysis_status, project.analysis_heartbeat_at),
    }
