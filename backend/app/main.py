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
from app.routers.admin import router as admin_router

from app.config import settings
from app.database import engine
from app.routers.auth import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.project_manager import router as project_manager_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForgeAI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== DÉMARRAGE DE DOTJCOM FORGEAI ===")
    logger.info(f"Environnement détecté : {settings.ENVIRONMENT}")
    
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            logger.info("✅ Connexion asynchrone à PostgreSQL établie avec succès !")
    except Exception as e:
        logger.error(f"❌ Impossible de se connecter à PostgreSQL au démarrage : {e}")
        
    yield

    logger.info("=== FERMETURE DE DOTJCOM FORGEAI ===")
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
app.include_router(admin_router)

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
