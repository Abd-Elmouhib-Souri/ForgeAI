"""
Sprint 7.7: real health checks of the platform (admin console "Santé du système").

Before: only PostgreSQL was tested; every other service was "configuré" as
soon as a setting existed. Now each check really talks to its service:

  postgres        SELECT 1
  migrations      database revision == code heads (a forgotten
                  "alembic upgrade head" is visible)
  analysis_queue  runs queued by an admin and not consumed (> 60 s), stuck runs
  redis           PING
  chromadb        heartbeat + an authenticated call (validates the token)
  public_api      GET /health of the public API (it runs the analyses)
  gemini, groq    list of models: no generation, no quota used; validates the
                  key AND that every configured model exists
  smtp            connect + STARTTLS + login
  disk            free space of the exports folder
  tavily,         configuration only (a Tavily test costs a credit, OAuth
  google_oauth    cannot be tested without a user) - said explicitly

Every check has a timeout and a latency; the network checks run
concurrently; no secret ever leaves this module (keys travel in headers,
messages are redacted). Results are cached CACHE_SECONDS unless refreshed.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import re
import shutil
import smtplib
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Project

CHECK_TIMEOUT_SECONDS = 5.0
CACHE_SECONDS = 30.0
QUEUE_WAIT_WARNING_SECONDS = 60
DISK_WARNING_BYTES = 1024**3  # 1 GiB

BACKEND_DIR = Path(__file__).resolve().parents[2]

# status: healthy | degraded (works, with a problem) | down | not_configured
Result = tuple[str, str, dict[str, Any]]


# ---------------------------------------------------------------------------
# Secrets never leave this module
# ---------------------------------------------------------------------------

_SECRET_SETTINGS = (
    "GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY", "SMTP_PASSWORD", "CHROMA_AUTH_TOKEN",
    "JWT_SECRET_KEY", "GOOGLE_CLIENT_SECRET", "GEMINI_SEARCH_CLASSIFIER_API_KEY",
)


def redact(message: str) -> str:
    """Remove every configured secret (and URL passwords) from a message."""
    text_value = str(message or "")
    for name in _SECRET_SETTINGS:
        secret = str(getattr(settings, name, "") or "")
        if len(secret) >= 6:
            text_value = text_value.replace(secret, "***")
    text_value = re.sub(r"(://[^:/@\s]+:)[^@\s]+@", r"\1***@", text_value)  # user:password@host
    text_value = re.sub(r"(key=)[^&\s]+", r"\1***", text_value)
    return text_value[:300]


# ---------------------------------------------------------------------------
# Hooks replaced by the tests (no real network there)
# ---------------------------------------------------------------------------

def make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=CHECK_TIMEOUT_SECONDS)


async def redis_ping() -> bool:
    import redis.asyncio as redis

    client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    try:
        return bool(await client.ping())
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Database checks (sequential: one AsyncSession is not concurrent-safe)
# ---------------------------------------------------------------------------

async def check_postgres(db: AsyncSession) -> Result:
    await db.execute(text("SELECT 1"))
    return "healthy", "Connexion à la base de données réussie.", {}


def code_migration_heads() -> list[str]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return sorted(ScriptDirectory.from_config(config).get_heads())


async def check_migrations(db: AsyncSession) -> Result:
    code = code_migration_heads()
    database = sorted(
        row[0] for row in (await db.execute(text("SELECT version_num FROM alembic_version"))).all()
    )
    details = {"database": database, "code": code}
    if database == code:
        return "healthy", "La base est à jour avec le code.", details
    return (
        "degraded",
        "La base n'est pas à jour avec le code : lancez « alembic upgrade head ».",
        details,
    )


async def check_analysis_queue(db: AsyncSession) -> Result:
    now = dt.datetime.now(dt.timezone.utc)
    waiting = await db.scalar(
        select(func.count(Project.id)).where(
            Project.analysis_enqueued_at.is_not(None),
            Project.analysis_enqueued_at < now - dt.timedelta(seconds=QUEUE_WAIT_WARNING_SECONDS),
        )
    )
    stalled = await db.scalar(
        select(func.count(Project.id)).where(
            Project.analysis_status.in_(("queued", "running")),
            or_(
                Project.analysis_heartbeat_at.is_(None),
                Project.analysis_heartbeat_at
                < now - dt.timedelta(seconds=settings.ANALYSIS_STALE_AFTER_SECONDS),
            ),
        )
    )
    details = {"waiting_over_60s": int(waiting or 0), "stalled": int(stalled or 0)}
    if details["waiting_over_60s"]:
        return "degraded", "Des relances attendent depuis plus d'une minute : l'API publique ne les prend pas en charge.", details
    if details["stalled"]:
        return "degraded", f"{details['stalled']} analyse(s) bloquée(s) : relancez-les depuis « Analyses IA ».", details
    return "healthy", "Aucune relance en attente, aucune analyse bloquée.", details


# ---------------------------------------------------------------------------
# Network checks (concurrent)
# ---------------------------------------------------------------------------

async def check_redis() -> Result:
    await redis_ping()
    return "healthy", "Redis répond.", {}


async def check_chromadb(http: httpx.AsyncClient) -> Result:
    address = f"{settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
    base = f"http://{address}/api/v1"
    beat = await http.get(f"{base}/heartbeat")
    if beat.status_code != 200:
        # Something answered, but not ChromaDB (wrong host/port) - say where we looked.
        return "down", f"Pas de ChromaDB à l'adresse {address} (HTTP {beat.status_code}) : vérifiez CHROMA_HOST / CHROMA_PORT.", {}
    auth = await http.get(
        f"{base}/collections", headers={"Authorization": f"Bearer {settings.CHROMA_AUTH_TOKEN}"}
    )
    if auth.status_code in (401, 403):
        return "down", "ChromaDB répond mais refuse le jeton d'accès (CHROMA_AUTH_TOKEN).", {}
    if auth.status_code != 200:
        return "degraded", f"ChromaDB répond, appel authentifié en erreur (HTTP {auth.status_code}).", {}
    return "healthy", "ChromaDB répond et accepte le jeton.", {}


async def check_public_api(http: httpx.AsyncClient) -> Result:
    response = await http.get(f"{settings.PUBLIC_API_INTERNAL_URL.rstrip('/')}/health")
    if response.status_code != 200:
        return "down", f"L'API publique répond HTTP {response.status_code} : les analyses ne peuvent pas tourner.", {}
    status = (response.json() or {}).get("status")
    if status != "healthy":
        return "degraded", f"L'API publique signale un état « {status} ».", {}
    return "healthy", "L'API publique (qui exécute les analyses) répond.", {}


def _models_result(provider: str, available: set[str], configured: list[str]) -> Result:
    wanted = sorted({model for model in configured if model})
    missing = [model for model in wanted if model not in available]
    details = {"configured_models": wanted, "missing_models": missing}
    if missing:
        return (
            "degraded",
            f"Clé {provider} valide, mais modèle(s) introuvable(s) : {', '.join(missing)}.",
            details,
        )
    return "healthy", f"Clé {provider} valide, tous les modèles configurés existent.", details


async def check_gemini(http: httpx.AsyncClient) -> Result:
    if not settings.GEMINI_API_KEY:
        return "not_configured", "Clé Gemini absente (GEMINI_API_KEY).", {}
    response = await http.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"pageSize": 1000},
        headers={"x-goog-api-key": settings.GEMINI_API_KEY},  # never in the URL
    )
    if response.status_code != 200:
        return "down", f"Gemini refuse la clé ou est indisponible (HTTP {response.status_code}).", {}
    available = {str(m.get("name", "")).removeprefix("models/") for m in response.json().get("models", [])}
    return _models_result(
        "Gemini", available,
        [settings.GEMINI_MODEL, settings.GEMINI_FALLBACK_MODEL, getattr(settings, "GEMINI_SEARCH_MODEL", "")],
    )


async def check_groq(http: httpx.AsyncClient) -> Result:
    if not settings.GROQ_API_KEY:
        return "not_configured", "Clé Groq absente (GROQ_API_KEY).", {}
    base = (settings.GROQ_API_BASE or "https://api.groq.com").rstrip("/")
    response = await http.get(
        f"{base}/openai/v1/models", headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    )
    if response.status_code != 200:
        return "down", f"Groq refuse la clé ou est indisponible (HTTP {response.status_code}).", {}
    available = {str(m.get("id", "")) for m in response.json().get("data", [])}
    return _models_result("Groq", available, [settings.GROQ_MODEL, settings.GROQ_FALLBACK_MODEL])


def _smtp_login() -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=CHECK_TIMEOUT_SECONDS) as server:
        server.ehlo()
        if settings.SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)


async def check_smtp() -> Result:
    if not (settings.SMTP_USERNAME and settings.SMTP_PASSWORD):
        return "not_configured", "SMTP non configuré : aucun e-mail (vérification, mot de passe) ne partira.", {}
    await asyncio.to_thread(_smtp_login)
    return "healthy", f"Connexion et authentification SMTP réussies ({settings.SMTP_HOST}).", {}


async def check_disk() -> Result:
    folder = Path(settings.EXPORTS_DIR)
    while not folder.exists() and folder != folder.parent:
        folder = folder.parent  # nearest existing parent (folder created on first export)
    usage = shutil.disk_usage(folder)
    free_gb = round(usage.free / 1024**3, 1)
    details = {"free_gb": free_gb, "total_gb": round(usage.total / 1024**3, 1)}
    if usage.free < DISK_WARNING_BYTES:
        return "degraded", f"Moins de 1 Go libre pour les exports ({free_gb} Go).", details
    return "healthy", f"{free_gb} Go libres pour les exports.", details


async def check_tavily() -> Result:
    if not settings.TAVILY_API_KEY:
        return "not_configured", "Clé Tavily absente : pas de recherche web.", {}
    return "healthy", "Clé présente (non testée : chaque test consommerait un crédit Tavily).", {"tested": False}


async def check_google_oauth() -> Result:
    if not (getattr(settings, "GOOGLE_CLIENT_ID", "") and getattr(settings, "GOOGLE_CLIENT_SECRET", "")):
        return "not_configured", "Connexion Google non configurée.", {}
    return "healthy", "Identifiants présents (non testables sans utilisateur).", {"tested": False}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def _timed(key: str, name: str, kind: str, check: Callable[[], Awaitable[Result]]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        status, message, details = await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        status, message, details = "down", f"Délai dépassé ({CHECK_TIMEOUT_SECONDS:g} s) : aucune réponse.", {}
    except httpx.TransportError as exc:
        # DNS, refused connection, proxy, TLS: the service cannot be reached from this server.
        status, message, details = "down", redact(f"Injoignable depuis le serveur ({type(exc).__name__}: {exc})"), {}
    except Exception as exc:  # the check itself failed: the service is down
        status, message, details = "down", redact(f"{type(exc).__name__}: {exc}") or type(exc).__name__, {}
    return {
        "key": key,
        "name": name,
        "type": kind,
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "message": redact(message),
        "details": details,
    }


def overall_status(services: list[dict[str, Any]]) -> str:
    statuses = {service["status"] for service in services}
    if "down" in statuses:
        return "down"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"  # "not_configured" optional services do not lower the grade


_cache: dict[str, Any] = {}


def clear_cache() -> None:
    _cache.clear()


async def run_all(db: AsyncSession, *, refresh: bool = False) -> dict[str, Any]:
    cached = _cache.get("body")
    if cached and not refresh and time.monotonic() - _cache["at"] < CACHE_SECONDS:
        return cached

    services = [
        await _timed("postgres", "PostgreSQL", "database", lambda: check_postgres(db)),
        await _timed("migrations", "Migrations de la base", "database", lambda: check_migrations(db)),
        await _timed("analysis_queue", "File des analyses", "queue", lambda: check_analysis_queue(db)),
    ]
    async with make_http_client() as http:
        services += await asyncio.gather(
            _timed("public_api", "API publique", "backend", lambda: check_public_api(http)),
            _timed("redis", "Redis", "cache", check_redis),
            _timed("chromadb", "ChromaDB", "vector_db", lambda: check_chromadb(http)),
            _timed("gemini", "Gemini", "llm", lambda: check_gemini(http)),
            _timed("groq", "Groq", "llm", lambda: check_groq(http)),
            _timed("smtp", "E-mail (SMTP)", "email", check_smtp),
            _timed("disk", "Espace disque (exports)", "disk", check_disk),
            _timed("tavily", "Recherche web (Tavily)", "search", check_tavily),
            _timed("google_oauth", "Connexion Google", "oauth", check_google_oauth),
        )
    body = {
        "overall_status": overall_status(services),
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cache_seconds": CACHE_SECONDS,
        "services": services,
    }
    _cache.update({"at": time.monotonic(), "body": body})
    return body
