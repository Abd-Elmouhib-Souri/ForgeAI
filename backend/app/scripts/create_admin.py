"""
Create (or promote) an admin from the server's command line.

Only an admin can create an admin in the console, so a fresh installation
needs a first one. Whoever can run this command already controls the
server, which is why the account is created verified. 2FA is NOT set up
here: the console demands it at the first login (QR code).

    docker compose exec backend python -m app.scripts.create_admin
    docker compose exec backend python -m app.scripts.create_admin --email prof@example.com --name "Prénom Nom"

The password is typed twice (hidden), or read from FORGEAI_ADMIN_PASSWORD
for a non-interactive install. It never appears in the audit log.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.email_identity import normalize_email, same_email
from app.models import User, UserRole
from app.security import get_password_hash
from app.services import admin_audit as audit


async def bootstrap_admin(db: AsyncSession, email: str, full_name: str, password: str) -> tuple[User, bool]:
    """Create the admin, or promote the existing account. Returns (user, created)."""
    if len(password) < settings.ADMIN_MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Mot de passe trop court : au moins {settings.ADMIN_MIN_PASSWORD_LENGTH} caractères pour un admin."
        )
    email = normalize_email(email)
    if "@" not in email:
        raise ValueError("Adresse e-mail invalide.")

    user = (await db.execute(select(User).where(same_email(User.email, email)))).scalar_one_or_none()
    before = audit.user_snapshot(user) if user is not None else None
    created = user is None
    if created:
        user = User(email=email, full_name=full_name.strip() or email)
        db.add(user)
    # Existing account (e.g. created with Google): keep its identity and
    # google_id, only give it the admin role and a password.
    user.role = UserRole.ADMIN
    user.is_active = True
    user.is_email_verified = True
    user.hashed_password = get_password_hash(password)
    await db.flush()  # user.id for the audit entry, same transaction

    audit.add(db, None, action="admin.bootstrap", result="success", actor_email="cli",
              target_type="user", target_id=user.id, target_label=user.email,
              before=before, after=audit.user_snapshot(user))  # never the password
    await db.commit()
    await db.refresh(user)
    return user, created


def _ask(prompt: str, value: str | None) -> str:
    return value if value else input(prompt).strip()


def _password() -> str:
    from_env = os.environ.get("FORGEAI_ADMIN_PASSWORD")
    if from_env:
        return from_env
    first = getpass.getpass(f"Mot de passe (au moins {settings.ADMIN_MIN_PASSWORD_LENGTH} caractères) : ")
    if first != getpass.getpass("Confirmez le mot de passe : "):
        raise ValueError("Les deux mots de passe ne correspondent pas.")
    return first


async def _main(email: str, name: str, password: str) -> None:
    from app.database import AsyncSessionLocal  # the real database only here, never in tests

    async with AsyncSessionLocal() as db:
        user, created = await bootstrap_admin(db, email, name, password)
    verb = "créé" if created else "promu administrateur"
    print(f"Compte {user.email} {verb}.")
    print("Connectez-vous sur /admin/login : la double authentification (QR code) sera demandée à la première connexion.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Créer ou promouvoir un administrateur ForgeAI.")
    parser.add_argument("--email")
    parser.add_argument("--name")
    args = parser.parse_args(argv)
    try:
        email = _ask("E-mail de l'administrateur : ", args.email)
        name = _ask("Nom complet : ", args.name)
        asyncio.run(_main(email, name, _password()))
    except (ValueError, KeyboardInterrupt) as exc:
        print(f"Erreur : {exc}" if str(exc) else "Annulé.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
