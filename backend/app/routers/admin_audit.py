"""
Sprint 7.2: reading the admin audit log (read-only: GET routes only).

  GET /admin/audit             filtered, paginated list (newest first)
  GET /admin/audit/actions     action codes and their French labels
  GET /admin/audit/export.csv  same filters, CSV for Excel / LibreOffice
"""

import csv
import datetime
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.admin_security import get_current_admin
from app.database import get_db
from app.models import AdminAuditLog, User
from app.services.admin_audit import ACTIONS, RESULTS

router = APIRouter(prefix="/admin/audit", tags=["Admin audit"])

CSV_MAX_ROWS = 10_000
RESULT_LABELS = {"success": "Succès", "failure": "Échec", "denied": "Refusé"}


class AuditFilters:
    """Query-string filters shared by the list and the CSV export."""

    def __init__(
        self,
        action: str | None = Query(default=None, max_length=64),
        result: str | None = Query(default=None, pattern="^(success|failure|denied)$"),
        actor: str | None = Query(default=None, max_length=255, description="Partie de l'e-mail de l'auteur"),
        target_type: str | None = Query(default=None, max_length=32),
        date_from: datetime.datetime | None = Query(default=None),
        date_to: datetime.datetime | None = Query(default=None),
    ) -> None:
        self.action, self.result, self.actor = action, result, actor
        self.target_type, self.date_from, self.date_to = target_type, date_from, date_to

    def apply(self, query):
        if self.action:
            query = query.where(AdminAuditLog.action == self.action)
        if self.result:
            query = query.where(AdminAuditLog.result == self.result)
        if self.actor:
            # Bound parameter: no SQL injection; % and _ lose their wildcard role.
            needle = self.actor.strip().lower().replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
            query = query.where(AdminAuditLog.actor_email.like(f"%{needle}%", escape="\\"))
        if self.target_type:
            query = query.where(AdminAuditLog.target_type == self.target_type)
        if self.date_from:
            query = query.where(AdminAuditLog.created_at >= self.date_from)
        if self.date_to:
            query = query.where(AdminAuditLog.created_at <= self.date_to)
        return query


def _iso(value: datetime.datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def serialize_entry(entry: AdminAuditLog) -> dict[str, Any]:
    return {
        "id": entry.id,
        "created_at": _iso(entry.created_at),
        "actor_id": entry.actor_id,
        "actor_email": entry.actor_email,
        "action": entry.action,
        "action_label": ACTIONS.get(entry.action, entry.action),
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "target_label": entry.target_label,
        "before": entry.before,
        "after": entry.after,
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "result": entry.result,
        "detail": entry.detail,
    }


@router.get("")
async def list_audit_entries(
    filters: AuditFilters = Depends(),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(filters.apply(select(func.count(AdminAuditLog.id))))
    rows = await db.execute(
        filters.apply(select(AdminAuditLog))
        .order_by(AdminAuditLog.id.desc())  # id is monotonic: stable newest-first order
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [serialize_entry(entry) for entry in rows.scalars()],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/actions")
async def list_audit_actions(admin: User = Depends(get_current_admin)):
    return ACTIONS


def _csv_cell(value: Any) -> str:
    """
    Text for one CSV cell. A cell starting with = + - @ (or tab / CR) is
    run as a formula by spreadsheets (CSV injection): prefix it with '.
    """
    if value is None:
        text = ""
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    if text[:1] in {"=", "+", "-", "@", "\t", "\r"}:
        text = "'" + text
    return text


@router.get("/export.csv")
async def export_audit_csv(
    filters: AuditFilters = Depends(),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        filters.apply(select(AdminAuditLog)).order_by(AdminAuditLog.id.desc()).limit(CSV_MAX_ROWS)
    )
    buffer = io.StringIO()
    # ";": the separator Excel expects in French locales ("," puts everything in one column).
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Date", "Auteur", "Action", "Résultat", "Motif", "Type de cible", "Cible",
                     "Avant", "Après", "Adresse IP", "Navigateur"])
    for entry in rows.scalars():
        writer.writerow([_csv_cell(v) for v in (
            _iso(entry.created_at),
            entry.actor_email,
            ACTIONS.get(entry.action, entry.action),
            RESULT_LABELS.get(entry.result, entry.result),
            entry.detail,
            entry.target_type,
            entry.target_label or entry.target_id,
            entry.before,
            entry.after,
            entry.ip_address,
            entry.user_agent,
        )])
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        # BOM: Excel then reads the accents as UTF-8.
        content=("﻿" + buffer.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="forgeai-audit-{stamp}.csv"'},
    )
