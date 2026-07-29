import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# ─── INCLUSION DE NOTRE ARCHITECTURE (CORE) ─────────────────────────────────
# On importe notre configuration globale et notre Base SQLAlchemy pour le suivi
from app.config import settings
from app.database import Base
import app.models  # Force l'enregistrement de User et Project dans Base.metadata

# Objet de configuration Alembic qui donne accès aux valeurs du fichier alembic.ini en cours d'utilisation.
config = context.config

# Configuration du logging en lisant le fichier alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# On surcharge dynamiquement l'URL de connexion SQL d'Alembic avec celle de notre .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Définition de la cible des métadonnées pour l'auto-génération des tables
target_metadata = Base.metadata


def do_run_migrations(connection):
    """
    Exécute les migrations dans un contexte synchrone requis par Alembic.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Détecte les changements de types de colonnes (ex: Int -> String)
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """
    Exécute les migrations en mode 'Offline'.
    Génère le script SQL brut directement sans se connecter physiquement à la base.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Exécute les migrations en mode 'Online' (Asynchrone).
    Crée un moteur de connexion asynchrone et applique les changements en base de données.
    """
    # Récupération de la configuration sous forme de dictionnaire Python
    configuration = config.get_section(config.config_ini_section, {})
    
    # Création du moteur asynchrone SQLAlchemy compatible avec Alembic
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # On utilise run_sync pour encapsuler l'exécution synchrone d'Alembic dans notre flux asynchrone
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# Point d'entrée pour aiguiller l'exécution selon le mode choisi (online vs offline)
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())