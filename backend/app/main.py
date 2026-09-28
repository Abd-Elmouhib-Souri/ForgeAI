import warnings

warnings.filterwarnings(
    "ignore",
    message=r"The default value of `allowed_objects` will change in a future version.*",
    category=Warning,
)

warnings.filterwarnings(
    "ignore",
    category=PendingDeprecationWarning,
)
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.sql import text

from app.config import settings
from app.database import engine
from app.routers.auth import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.project_manager import router as project_manager_router
from app.routers.solution_architect import router as solution_architect_router
from app.routers.export import router as export_router
from app.routers.pipeline import router as pipeline_router
from app.services.post_analysis_pipeline import post_analysis_pipeline
from app.services.analysis_queue import analysis_queue_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForgeAI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== DÉMARRAGE DE FORGEAI ===")
    logger.info(f"Environnement détecté : {settings.ENVIRONMENT}")
    
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            logger.info("✅ Connexion asynchrone à PostgreSQL établie avec succès !")
    except Exception as e:
        logger.error(f"❌ Impossible de se connecter à PostgreSQL au démarrage : {e}")
        
    # Reprend les étapes Plan/Architecture interrompues par un redémarrage,
    # en attente de quota, ou bloquées par une configuration LLM corrigée
    # depuis (un redémarrage applique le nouveau .env).
    try:
        await post_analysis_pipeline.resume_pending()
    except Exception:
        logger.exception("Reprise du pipeline post-analyse impossible au démarrage")

    # Sprint 7.6: this process (the public API) runs the analyses queued by
    # an admin. The admin API never starts this worker.
    analysis_queue_worker.start()

    yield

    await analysis_queue_worker.stop()

    logger.info("=== FERMETURE DE FORGEAI ===")
    logger.info("Fermeture du pool de connexions de la base de données...")
    await engine.dispose()
    logger.info("👋 Base de données déconnectée proprement. À bientôt !")

app = FastAPI(
    title=settings.APP_NAME,
    description="Plateforme SaaS IA multi-agent pour l'idéation de projets et la génération agile",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nécessaire pour le flow OAuth Google (stockage temporaire du "state" anti-CSRF)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(project_manager_router)
app.include_router(solution_architect_router)
app.include_router(export_router)
app.include_router(pipeline_router)
# Sprint 7.1: the admin routes are NOT mounted here any more; they live in
# the separate admin API (app/admin_main.py, port 8002, private network).

# Sprint 6.1 hardening : les exports ne sont PLUS servis publiquement.
# Ils sont stockes dans settings.EXPORTS_DIR et telecharges uniquement via
# GET /projects/{id}/exports/{export_id}/download (authentifie, filtre
# sur le proprietaire). Voir app/services/export/storage.py.

@app.get("/", status_code=status.HTTP_200_OK, tags=["System"])
async def root():
    return {
        "status": "online",
        "application": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs"
    }

@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check():
    db_status = "healthy"
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status
    }