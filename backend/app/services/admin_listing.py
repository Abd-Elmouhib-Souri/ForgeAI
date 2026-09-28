"""
Sprint 7.4: shared tools of the admin lists (users, projects, analyses,
errors, audit).

  * pagination: {items, total, page, page_size}, done in SQL (OFFSET/LIMIT)
    with one COUNT, whatever the size of the table;
  * search: case-insensitive LIKE with % and _ escaped (a "%" typed by the
    admin is a character, never a wildcard; bound parameters, no injection);
  * French labels for the codes shown in exports;
  * CSV: ";" separator + BOM (French Excel), cells that would run as a
    spreadsheet formula are neutralized.
"""

from __future__ import annotations

import csv
import datetime
import io
import json
from typing import Any, Iterable, Sequence

from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
CSV_MAX_ROWS = 10_000

ROLE_LABELS = {
    "admin": "Administrateur",
    "entrepreneur": "Entrepreneur",
    "student": "Étudiant",
    "consultant": "Consultant",
}

ANALYSIS_STATUS_LABELS = {
    "not_started": "Non lancée",
    "queued": "En file d'attente",
    "running": "En cours",
    "needs_clarification": "Précisions requises",
    "completed": "Terminée",
    "failed": "Échouée",
}


def like_pattern(search: str) -> str:
    """'%' and '_' typed by the admin match themselves (escape char: backslash)."""
    needle = search.strip().lower().replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{needle}%"


def contains(column, search: str):
    """Case-insensitive 'column contains search' condition."""
    return func.lower(column).like(like_pattern(search), escape="\\")


async def paginate(db: AsyncSession, query, count_query, *, page: int, page_size: int) -> tuple[list, int]:
    """Rows of one page + total matching rows (2 SQL statements)."""
    total = await db.scalar(count_query)
    rows = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).all()
    return rows, int(total or 0)


def page_body(items: list[dict], total: int, page: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def iso(value: Any) -> str | None:
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def csv_cell(value: Any) -> str:
    """
    Text of one CSV cell. A cell starting with = + - @ (or tab / CR) is run
    as a formula by spreadsheets (CSV injection): prefix it with '.
    """
    if value is None:
        text = ""
    elif isinstance(value, bool):
        text = "Oui" if value else "Non"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif isinstance(value, (datetime.datetime, datetime.date)):
        text = value.isoformat()
    else:
        text = str(value)
    if text[:1] in {"=", "+", "-", "@", "\t", "\r"}:
        text = "'" + text
    return text


def csv_response(name: str, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> Response:
    """UTF-8 CSV download (BOM + ';' so that French Excel opens it in columns)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(header)
    for row in rows:
        writer.writerow([csv_cell(value) for value in row])
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        content=("﻿" + buffer.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="forgeai-{name}-{stamp}.csv"'},
    )
