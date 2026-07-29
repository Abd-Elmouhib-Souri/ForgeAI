"""add market region and analysis progress

Revision ID: 11ebdd303c5d
Revises: 494f8a2baf87
Create Date: 2026-07-14 21:53:21.312809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "11ebdd303c5d"
down_revision: Union[str, None] = "494f8a2baf87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pays / région cible du projet.
    # server_default est nécessaire parce que la table projects contient déjà
    # des projets existants. PostgreSQL doit savoir quelle valeur mettre
    # pour les anciennes lignes.
    op.add_column(
        "projects",
        sa.Column(
            "market_region",
            sa.String(length=100),
            nullable=False,
            server_default="Tunisie",
        ),
    )

    # Étape actuelle de l'analyse IA.
    # Exemple :
    # - idle
    # - Préparation de l’analyse
    # - RAG global
    # - Recherche locale
    # - Analyse LLM
    # - Analyse terminée
    op.add_column(
        "projects",
        sa.Column(
            "analysis_step",
            sa.String(length=100),
            nullable=False,
            server_default="idle",
        ),
    )

    # Progression numérique affichable côté frontend.
    # Exemple : 0, 10, 35, 70, 90, 100.
    op.add_column(
        "projects",
        sa.Column(
            "analysis_progress",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # On enlève les server_default après création.
    # Comme ça, les futures valeurs seront contrôlées par SQLAlchemy/backend,
    # pas directement par PostgreSQL.
    op.alter_column(
        "projects",
        "market_region",
        server_default=None,
    )

    op.alter_column(
        "projects",
        "analysis_step",
        server_default=None,
    )

    op.alter_column(
        "projects",
        "analysis_progress",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("projects", "analysis_progress")
    op.drop_column("projects", "analysis_step")
    op.drop_column("projects", "market_region")