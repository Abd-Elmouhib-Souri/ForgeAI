"""
Prepare the configuration of a fresh ForgeAI clone.

    python scripts/init_env.py

Creates, from the committed templates:
  .env                 read by docker compose (backend, admin API, Postgres, Chroma)
  frontend/.env.local  URLs of the public and admin APIs

Every INTERNAL secret is generated at random (JWT, refresh JWT, session,
Fernet key for the admins' 2FA secrets, Postgres password + DATABASE_URL,
ChromaDB token). Only the EXTERNAL API keys are left for you to paste into
.env (Gemini and/or Groq, Tavily; Google OAuth and SMTP are optional).

Standard library only: no dependency to install. Never overwrites an
existing file (your keys are safe); delete the files yourself to restart.
"""

from __future__ import annotations

import base64
import os
import re
import secrets
import sys
from pathlib import Path

GENERATED = ("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY", "SESSION_SECRET_KEY", "CHROMA_AUTH_TOKEN")
# External keys the person installing provides (the first two: at least one is needed).
TO_FILL = ("GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY",
           "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SMTP_USERNAME", "SMTP_PASSWORD")


def _set(text: str, name: str, value: str) -> str:
    """Replace the value of NAME= (the line must exist in the template)."""
    pattern = re.compile(rf"^{name}=.*$", flags=re.M)
    if not pattern.search(text):
        raise SystemExit(f"Modèle incomplet : {name} manque dans .env.example")
    return pattern.sub(lambda _: f"{name}={value}", text, count=1)


def _get(text: str, name: str) -> str:
    match = re.search(rf"^{name}=(.*)$", text, flags=re.M)
    return match.group(1).strip() if match else ""


def init_env(root: Path) -> list[str]:
    """Write .env and frontend/.env.local; return the external keys still empty."""
    targets = [root / ".env", root / "frontend" / ".env.local"]
    existing = [str(path.relative_to(root)) for path in targets if path.exists()]
    if existing:
        raise SystemExit(
            "Déjà configuré (" + ", ".join(existing) + ") : rien n'a été modifié. "
            "Supprimez ces fichiers vous-même pour tout régénérer."
        )

    text = (root / ".env.example").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    for name in GENERATED:
        text = _set(text, name, secrets.token_urlsafe(48))
    # Fernet key: 32 random bytes, URL-safe base64 (what cryptography.Fernet expects).
    text = _set(text, "AES_SECRET_KEY", base64.urlsafe_b64encode(os.urandom(32)).decode("ascii"))
    password = secrets.token_urlsafe(32)  # URL-safe: no escaping needed in DATABASE_URL
    text = _set(text, "POSTGRES_PASSWORD", password)
    text = _set(text, "DATABASE_URL", "postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}".format(
        user=_get(text, "POSTGRES_USER"), pw=password, host=_get(text, "POSTGRES_SERVER"),
        port=_get(text, "POSTGRES_PORT"), db=_get(text, "POSTGRES_DB")))

    targets[0].write_text(text, encoding="utf-8", newline="\n")
    front = (root / "frontend" / ".env.example").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    targets[1].write_text(front, encoding="utf-8", newline="\n")
    return [name for name in TO_FILL if not _get(text, name)]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    to_fill = init_env(root)
    print("Configuration créée : .env et frontend/.env.local")
    print("Secrets internes générés (JWT, session, clé 2FA, Postgres, ChromaDB).")
    print("\nIl reste à coller vos clés d'API dans .env :")
    for name in to_fill:
        print(f"  - {name}")
    print("Au moins GEMINI_API_KEY ou GROQ_API_KEY est nécessaire pour lancer une analyse.")
    print("Les autres sont facultatives : voir les commentaires de .env et le README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
