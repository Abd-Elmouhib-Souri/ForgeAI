from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.services.analysis_run_guard as guard_module
from app.services.analysis_run_guard import AnalysisRunGuard


def test_analysis_run_ids_are_unique() -> None:
    guard = AnalysisRunGuard(max_concurrent_runs=2)
    assert guard.new_run_id() != guard.new_run_id()


def test_analysis_guard_limits_parallel_runs() -> None:
    guard = AnalysisRunGuard(max_concurrent_runs=2)
    active = 0
    maximum_seen = 0
    lock = asyncio.Lock()

    @guard.limit
    async def work() -> None:
        nonlocal active, maximum_seen
        async with lock:
            active += 1
            maximum_seen = max(maximum_seen, active)
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1

    async def scenario() -> None:
        await asyncio.gather(*(work() for _ in range(6)))

    asyncio.run(scenario())
    assert maximum_seen == 2


def test_ensure_current_uses_fresh_database_value(monkeypatch) -> None:
    guard = AnalysisRunGuard(max_concurrent_runs=1)
    project = SimpleNamespace(
        id=7,
        analysis_run_id="run-current",
        analysis_heartbeat_at=None,
    )

    class FakeDB:
        no_autoflush = __import__("contextlib").nullcontext()

        async def get(self, _model, project_id, **kwargs):
            assert project_id == 7
            assert kwargs.get("populate_existing") is True
            return project

    monkeypatch.setattr(guard_module, "_project_model", lambda: object)
    current = asyncio.run(
        guard.ensure_current(FakeDB(), 7, "run-current")  # type: ignore[arg-type]
    )
    assert current is project
    assert project.analysis_heartbeat_at is not None


def test_commit_rejects_database_stale_run(monkeypatch) -> None:
    guard = AnalysisRunGuard(max_concurrent_runs=1)
    project = SimpleNamespace(
        id=10,
        analysis_run_id="run-old",
        analysis_heartbeat_at=None,
    )

    async def stored_run_id(**_kwargs):
        return True, "run-new"

    monkeypatch.setattr(guard, "_read_database_run_id", stored_run_id)

    class FakeDB:
        committed = False
        rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    db = FakeDB()
    accepted = asyncio.run(
        guard.commit_if_current(db, project, "run-old")  # type: ignore[arg-type]
    )
    assert accepted is False
    assert db.rolled_back is True
    assert db.committed is False


def test_commit_accepts_database_current_run(monkeypatch) -> None:
    guard = AnalysisRunGuard(max_concurrent_runs=1)
    project = SimpleNamespace(
        id=10,
        analysis_run_id="run-current",
        analysis_heartbeat_at=None,
    )

    async def stored_run_id(**_kwargs):
        return True, "run-current"

    monkeypatch.setattr(guard, "_read_database_run_id", stored_run_id)

    class FakeDB:
        committed = False
        rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    db = FakeDB()
    accepted = asyncio.run(
        guard.commit_if_current(db, project, "run-current")  # type: ignore[arg-type]
    )
    assert accepted is True
    assert db.committed is True
    assert db.rolled_back is False
    assert project.analysis_heartbeat_at is not None
