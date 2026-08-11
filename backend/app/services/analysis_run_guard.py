from __future__ import annotations

import asyncio
import uuid
from contextlib import nullcontext
from datetime import datetime, timezone
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable, ContextManager, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

if TYPE_CHECKING:
    from app.models import Project


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _project_model() -> type[Any]:
    """Import the ORM model lazily to avoid router/model import cycles."""
    from app.models import Project

    return Project


class AnalysisRunGuard:
    """Protect analysis runs from duplicates, stale writes and overload.

    The current Docker profile runs one Uvicorn process, so a bounded async
    semaphore is sufficient to cap concurrent background analyses. The
    ``analysis_run_id`` stored in PostgreSQL remains the source of truth for
    stale-write protection. A distributed queue can later replace this adapter
    without changing the public analysis contract.
    """

    def __init__(self, max_concurrent_runs: int | None = None) -> None:
        configured = (
            max_concurrent_runs
            if max_concurrent_runs is not None
            else getattr(settings, "ANALYSIS_MAX_CONCURRENT_RUNS", 2)
        )
        try:
            parsed = int(configured or 2)
        except (TypeError, ValueError):
            parsed = 2

        self.max_concurrent_runs = max(1, min(parsed, 8))
        self._semaphore = asyncio.Semaphore(self.max_concurrent_runs)

    @staticmethod
    def new_run_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def is_current(project: Any, run_id: str) -> bool:
        return bool(
            project is not None
            and str(getattr(project, "analysis_run_id", "") or "")
            == str(run_id or "")
        )

    def limit(self, function: F) -> F:
        """Queue an async analysis until one bounded execution slot is free."""

        @wraps(function)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            async with self._semaphore:
                return await function(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    async def ensure_current(
        self,
        db: AsyncSession,
        project_id: int,
        run_id: str,
    ) -> "Project | None":
        """Reload the project and reject an obsolete analysis run.

        ``populate_existing`` avoids trusting a stale identity-map value. The
        heartbeat is changed in memory only; the caller still owns the final
        transaction boundary.
        """
        model = _project_model()

        with self._no_autoflush(db):
            try:
                project = await db.get(
                    model,
                    project_id,
                    populate_existing=True,
                )
            except TypeError:
                # Compatibility with lightweight test doubles.
                project = await db.get(model, project_id)

        if not self.is_current(project, run_id):
            return None

        project.analysis_heartbeat_at = utc_now()
        return project

    async def commit_if_current(
        self,
        db: AsyncSession,
        project: "Project",
        run_id: str,
    ) -> bool:
        """Commit only while PostgreSQL still assigns the row to ``run_id``.

        The database run id is selected under ``FOR UPDATE`` and with autoflush
        disabled. This prevents pending results from being flushed before the
        stale-run decision and prevents another transaction from changing the
        run id between the check and this commit.
        """
        if not self.is_current(project, run_id):
            await db.rollback()
            return False

        project_id = getattr(project, "id", None)
        if project_id is not None:
            checked, stored_run_id = await self._read_database_run_id(
                db=db,
                project_id=int(project_id),
                lock_row=True,
            )
            if checked and str(stored_run_id or "") != str(run_id or ""):
                await db.rollback()
                return False

        project.analysis_heartbeat_at = utc_now()
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    async def _read_database_run_id(
        self,
        *,
        db: AsyncSession,
        project_id: int,
        lock_row: bool,
    ) -> tuple[bool, str | None]:
        """Read only the authoritative run id without overwriting pending data.

        ``checked`` is false only for lightweight test doubles that do not expose
        SQLAlchemy's ``execute`` method. Real ``AsyncSession`` instances always
        use the SELECT path.
        """
        execute = getattr(db, "execute", None)
        if not callable(execute):
            return False, None

        model = _project_model()
        statement = select(model.analysis_run_id).where(model.id == project_id)
        if lock_row:
            statement = statement.with_for_update()

        with self._no_autoflush(db):
            result = await execute(statement)

        scalar_one_or_none = getattr(result, "scalar_one_or_none", None)
        if callable(scalar_one_or_none):
            return True, scalar_one_or_none()

        scalar = getattr(result, "scalar", None)
        if callable(scalar):
            return True, scalar()

        return True, None

    @staticmethod
    def _no_autoflush(db: Any) -> ContextManager[Any]:
        manager = getattr(db, "no_autoflush", None)
        if manager is None:
            return nullcontext()
        return manager


analysis_run_guard = AnalysisRunGuard()
