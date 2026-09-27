"""
Sprint 7.1: admin authentication and authorization.

Why a module of its own: before 7.1 an admin token was a plain user token
({"sub": email}). An admin could log in through /auth/login and renew the
token with /auth/refresh, skipping 2FA entirely, and the admin routes were
served by the public API. Now:

  * admin tokens carry a dedicated audience (ADMIN_AUDIENCE), last 15
    minutes and have no refresh; PyJWT refuses them in the public API
    (a token with an "aud" claim fails a decode that expects none), and the
    admin API refuses user tokens (missing "aud");
  * 2FA is mandatory: an admin without it only gets an ENROLLMENT token,
    good for nothing but /admin/2fa/setup and /admin/2fa/enable;
  * sensitive actions need a fresh TOTP code in X-Admin-Confirmation
    (HTTP 428 when missing or wrong: the console asks for the code instead
    of logging the admin out, which 401/403 would do);
  * failed password / TOTP attempts are limited per account and per IP.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Protocol

import jwt
import pyotp
import segno
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.security_policy import reveal_totp_secret

logger = logging.getLogger(__name__)

ADMIN_AUDIENCE = "forgeai-admin"
ENROLL_AUDIENCE = "forgeai-admin-enroll"
CONFIRMATION_HEADER = "X-Admin-Confirmation"

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def create_admin_token(email: str, *, audience: str, minutes: int) -> str:
    """Short-lived admin token bound to one audience."""
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": email,
            "aud": audience,
            "scope": "admin",
            "iat": now,
            "exp": now + timedelta(minutes=minutes),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def issue_admin_access_token(email: str) -> str:
    return create_admin_token(email, audience=ADMIN_AUDIENCE, minutes=settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)


def issue_enrollment_token(email: str) -> str:
    return create_admin_token(email, audience=ENROLL_AUDIENCE, minutes=settings.ADMIN_ENROLL_TOKEN_EXPIRE_MINUTES)


def _unauthorized(message: str = "Session admin invalide ou expirée.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
    audience: str,
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        # audience= makes PyJWT require the claim: user tokens (no "aud")
        # and enrollment tokens (other audience) are both rejected here.
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=audience,
        )
    except jwt.PyJWTError:
        raise _unauthorized()
    email = payload.get("sub")
    if not email:
        raise _unauthorized()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or user.role != UserRole.ADMIN:
        raise _unauthorized()
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte administrateur désactivé.")
    return user


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Guard of every admin route: admin audience + active admin with 2FA."""
    user = await _user_from_token(credentials, db, ADMIN_AUDIENCE)
    if not user.is_two_factor_enabled:
        # Cannot happen with a token issued by /admin/login, but a 2FA reset
        # must invalidate existing sessions immediately.
        raise _unauthorized("La double authentification doit être activée.")
    return user


async def get_enrolling_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Guard of the 2FA enrollment routes only."""
    user = await _user_from_token(credentials, db, ENROLL_AUDIENCE)
    if user.is_two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La double authentification est déjà activée.")
    return user


# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------

def verify_totp(user: User, code: str | None) -> bool:
    """True when ``code`` is the user's current TOTP (±1 step of clock drift)."""
    if not code or not user.two_factor_secret:
        return False
    try:
        return pyotp.TOTP(reveal_totp_secret(user.two_factor_secret)).verify(str(code).strip(), valid_window=1)
    except Exception:  # corrupted / undecryptable secret
        logger.warning("TOTP verification failed for admin id=%s (secret unreadable)", user.id)
        return False


def qr_svg(provisioning_uri: str) -> str:
    """Inline SVG QR code for authenticator apps (no image file, no network)."""
    # omitsize: viewBox only, no fixed width/height, so the QR scales to its
    # container instead of being clipped (a clipped QR may not scan).
    return segno.make(provisioning_uri, error="m").svg_inline(scale=5, border=2, omitsize=True)


async def require_confirmation(
    request: Request,
    admin: User = Depends(get_current_admin),
    confirmation: str | None = Header(default=None, alias=CONFIRMATION_HEADER),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Step-up for sensitive actions: a fresh TOTP code in X-Admin-Confirmation.

    428 (not 401/403) so the console asks for the code instead of ending
    the session.
    """
    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"reason": "confirmation_required", "message": "Confirmez l'action avec votre code 2FA."},
        )
    if not verify_totp(admin, confirmation):
        # Sprint 7.2: a wrong code on a sensitive action is worth a trace
        # (stolen session trying to act). Never the code itself.
        from app.services import admin_audit  # local import: no cycle at load time

        await admin_audit.add_and_commit(
            db, request, action="admin.confirmation", result="failure", actor=admin,
            detail="confirmation_invalid", after={"method": request.method, "path": request.url.path},
        )
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"reason": "confirmation_invalid", "message": "Code de confirmation invalide ou expiré."},
        )
    return admin


# ---------------------------------------------------------------------------
# Attempt limiting
# ---------------------------------------------------------------------------

class ThrottleStore(Protocol):
    async def count(self, key: str) -> tuple[int, int]: ...  # (failures, seconds left)
    async def hit(self, key: str, window: int) -> None: ...
    async def clear(self, key: str) -> None: ...


class MemoryStore:
    """Per-process counters. Fallback when Redis is unreachable, and tests."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[int, float]] = {}

    async def count(self, key: str) -> tuple[int, int]:
        failures, expires = self._items.get(key, (0, 0.0))
        left = expires - time.monotonic()
        if left <= 0:
            self._items.pop(key, None)
            return 0, 0
        return failures, int(left) + 1

    async def hit(self, key: str, window: int) -> None:
        failures, _ = await self.count(key)
        _, expires = self._items.get(key, (0, time.monotonic() + window))
        self._items[key] = (failures + 1, expires)

    async def clear(self, key: str) -> None:
        self._items.pop(key, None)


class RedisStore:
    """Shared counters: correct across workers, containers and restarts."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)

    @staticmethod
    def _key(key: str) -> str:
        return f"forgeai:admin-login:{key}"

    async def count(self, key: str) -> tuple[int, int]:
        value, ttl = await self._redis.get(self._key(key)), await self._redis.ttl(self._key(key))
        return (int(value) if value else 0), max(int(ttl), 0)

    async def hit(self, key: str, window: int) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(self._key(key))
            pipe.expire(self._key(key), window, nx=True)  # window starts at the first failure
            await pipe.execute()

    async def clear(self, key: str) -> None:
        await self._redis.delete(self._key(key))


class LoginThrottle:
    """At most ADMIN_LOGIN_MAX_ATTEMPTS failures per key within the window."""

    def __init__(self, store: ThrottleStore | None = None) -> None:
        self._store = store
        self._fallback = MemoryStore()

    def use_store(self, store: ThrottleStore) -> None:
        self._store = store

    def _primary(self) -> ThrottleStore:
        if self._store is None:
            self._store = RedisStore(settings.REDIS_URL)
        return self._store

    async def _call(self, method: str, *args):
        try:
            return await getattr(self._primary(), method)(*args)
        except Exception as exc:  # Redis down: never lock admins out, never fail open silently
            logger.warning("Admin login throttle: Redis unavailable (%s), using in-memory counters", exc)
            return await getattr(self._fallback, method)(*args)

    async def retry_after(self, keys: list[str]) -> int:
        """Seconds until the block ends (0 = not blocked)."""
        waits = []
        for key in keys:
            failures, left = await self._call("count", key)
            if failures >= settings.ADMIN_LOGIN_MAX_ATTEMPTS:
                waits.append(max(left, 1))
        return max(waits, default=0)

    async def record_failure(self, keys: list[str]) -> None:
        for key in keys:
            await self._call("hit", key, settings.ADMIN_LOGIN_WINDOW_SECONDS)

    async def reset(self, keys: list[str]) -> None:
        for key in keys:
            await self._call("clear", key)


login_throttle = LoginThrottle()


def throttle_keys(email: str, client_ip: str | None) -> list[str]:
    """One counter per account and one per source IP."""
    keys = [f"email:{email.strip().lower()}"]
    if client_ip:
        keys.append(f"ip:{client_ip}")
    return keys
