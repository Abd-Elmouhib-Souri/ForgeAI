"""
Sprint 7.2: writing the admin audit log (app.models.AdminAuditLog).

Two ways to record:
  * ``add(...)``: the entry joins the current transaction, so it is saved
    together with the change it describes (or not at all);
  * ``add_and_commit(...)``: for refusals (wrong password, wrong code,
    business rule), where the request is about to answer 4xx and nothing
    else is pending: the entry is committed right away.

Never pass a secret (password, TOTP code or secret, token) to these
functions: only identifiers, snapshots of public fields and reason codes.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, User

logger = logging.getLogger(__name__)

# Action code -> French label shown in the console (and the filter list).
ACTIONS: dict[str, str] = {
    "admin.login": "Connexion admin",
    "admin.login.blocked": "Connexion bloquée (trop de tentatives)",
    "admin.2fa.enable": "Activation de la double authentification",
    "admin.confirmation": "Code de confirmation refusé",
    "admin.create": "Création d'un administrateur",
    "user.role.update": "Changement de rôle",
    "user.status.update": "Activation / désactivation de compte",
    "user.verification.resend": "Renvoi de l'e-mail de vérification",
    "user.delete": "Suppression d'utilisateur",
    "project.delete": "Suppression de projet",
}

RESULTS = ("success", "failure", "denied")


def _cut(value: Any, size: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:size] if text else None


def client_ip(request: Request | None) -> str | None:
    # Direct peer address. Behind the production reverse proxy, uvicorn's
    # --proxy-headers (trusted proxy only) makes this the real client IP.
    return request.client.host if request is not None and request.client else None


def add(
    db: AsyncSession,
    request: Request | None,
    *,
    action: str,
    result: str,
    actor: User | None = None,
    actor_email: str | None = None,
    target_type: str | None = None,
    target_id: Any = None,
    target_label: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    detail: Any = None,
) -> AdminAuditLog:
    """Stage one audit entry in the current transaction."""
    if action not in ACTIONS:
        raise ValueError(f"Unknown audit action: {action!r}")
    if result not in RESULTS:
        raise ValueError(f"Unknown audit result: {result!r}")
    if isinstance(detail, dict):  # structured HTTPException detail
        detail = detail.get("reason") or detail.get("message")
    entry = AdminAuditLog(
        actor_id=actor.id if actor is not None else None,
        actor_email=_cut((actor.email if actor is not None else actor_email or "").strip().lower(), 255),
        action=action,
        target_type=target_type,
        target_id=_cut(target_id, 64),
        target_label=_cut(target_label, 255),
        before=before,
        after=after,
        ip_address=_cut(client_ip(request), 64),
        user_agent=_cut(request.headers.get("user-agent") if request is not None else None, 255),
        result=result,
        detail=_cut(detail, 255),
    )
    db.add(entry)
    return entry


async def add_and_commit(db: AsyncSession, request: Request | None, **fields: Any) -> None:
    """Record a refusal right away. Never breaks the request it describes."""
    try:
        add(db, request, **fields)
        await db.commit()
    except Exception:
        logger.exception("Admin audit: could not record %s", fields.get("action"))
        await db.rollback()


def user_snapshot(user: User) -> dict:
    """Public fields kept when an account is deleted (never the hash / 2FA secret)."""
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {
        "email": user.email,
        "full_name": user.full_name,
        "role": role,
        "is_active": bool(user.is_active),
        "is_email_verified": bool(user.is_email_verified),
    }
