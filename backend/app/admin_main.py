"""
Sprint 7.1: the ADMIN API, a separate ASGI application.

Run: uvicorn app.admin_main:app --port 8002 (docker-compose service
"backend-admin", published on 127.0.0.1 only; in production reachable
only through the private network / VPN, never from the Internet).

The public API (app.main, port 8000) no longer mounts any /admin route:
probing it reveals nothing to attack. Both apps share the image, the
database and the models; they refuse each other's tokens (audiences).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers.admin import router as admin_router

logger = logging.getLogger("ForgeAI.admin")

_production = settings.ENVIRONMENT.strip().lower() in {"production", "prod"}

app = FastAPI(
    title=f"{settings.APP_NAME} Admin",
    description="API d'administration ForgeAI (réseau privé uniquement).",
    version="1.0.0",
    # No interactive docs in production: nothing to browse for an intruder.
    docs_url=None if _production else "/docs",
    redoc_url=None,
    openapi_url=None if _production else "/openapi.json",
)

# Only the admin console may call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ADMIN_ALLOWED_ORIGINS,
    allow_credentials=False,  # bearer token in a header, no cookie
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Confirmation"],
)

app.include_router(admin_router)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health() -> dict:
    """Liveness for docker / monitoring (no data, no auth)."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database = "healthy"
    except Exception:
        logger.exception("Admin API: database unreachable")
        database = "unhealthy"
    return {"status": "healthy" if database == "healthy" else "degraded", "database": database}
