"""
Output-language rules for agents that return STRICT structured JSON.

Why not reuse domain_integrity_guard.language_instruction()?
That lock says "every JSON string value must be in <language>", which is
right for free-text analysis agents but harmful here: planning payloads mix
human-readable text with machine values (enum values such as "must" or
"split", candidate keys, canonical IDs, hashes, references copied from an
ALLOWED list). Translating those makes the strict authorities reject the
answer, and the platform silently falls back to the deterministic backlog.

So this module localizes human-readable text ONLY and names what must stay
verbatim. The language itself is resolved by normalize_output_language(),
the single platform authority (unknown/empty -> "fr").
"""

from __future__ import annotations

from collections.abc import Iterable

from app.services.domain_integrity_guard import normalize_output_language

# Display name the model understands, keyed by the normalized code.
_LANGUAGE_NAMES = {
    "fr": "French",
    "en": "English",
}

# User-story sentence template per language (Connextra format).
_USER_STORY_TEMPLATES = {
    "fr": "En tant que ... je veux ... afin de ...",
    "en": "As a ... I want ... so that ...",
}


def resolve_output_language(language: str | None) -> str:
    """Return the normalized language code ("fr" or "en")."""
    return normalize_output_language(language)


def user_story_template(language: str | None) -> str:
    """Story example matching the project language, for prompt shapes."""
    return _USER_STORY_TEMPLATES[resolve_output_language(language)]


def structured_output_language_rules(
    language: str | None,
    *,
    translatable_fields: Iterable[str],
) -> str:
    """
    Build the OUTPUT LANGUAGE prompt block.

    ``translatable_fields`` lists the JSON fields holding human-readable
    text; everything else is declared untranslatable.
    """
    code = resolve_output_language(language)
    name = _LANGUAGE_NAMES[code]
    fields = ", ".join(str(field) for field in translatable_fields)

    return (
        "OUTPUT LANGUAGE\n"
        f"- Write every human-readable text value in {name} ({code}): {fields}.\n"
        "- Never translate or rephrase JSON keys, enum values, candidate keys, "
        "canonical identifiers, hashes, or any value copied from an ALLOWED list "
        "or from the canonical input; copy them exactly as given.\n"
        f"- Do not mix languages inside one text value; if a canonical fact is written "
        f"in another language, quote it verbatim and write the surrounding text in {name}.\n"
    )
