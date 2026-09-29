"""
One definition of "the same e-mail address" (RED 28 Sept 2026).

Pydantic's EmailStr keeps the case of the local part ("Sourimouhib3@gmail.com"),
and browsers often capitalise the first letter of a field. Every lookup made
from what a person TYPED must therefore ignore case and surrounding spaces,
and new accounts are stored in lowercase.

Lookups by a token subject (the stored value itself) stay exact.
"""

from sqlalchemy import func


def normalize_email(email: str | None) -> str:
    """Canonical form: trimmed and lowercase."""
    return str(email or "").strip().lower()


def same_email(column, email: str | None):
    """SQL condition: the column holds this address, whatever its case.

    Works for accounts stored before the normalisation (mixed case) too.
    """
    return func.lower(column) == normalize_email(email)
