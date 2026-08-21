from __future__ import annotations

import re
from typing import Any

from app.schemas.analysis_context import (
    clean_text,
    comparison_key,
)


_SCOPE_REFERENCE_PATTERN = re.compile(
    r"\b(?:"
    r"mvp"
    r"|minimum viable product"
    r"|first version"
    r"|initial version"
    r"|premiere version"
    r"|version initiale"
    r"|first pilot"
    r"|premier pilote"
    r"|premiere pilote"
    r"|pilot"
    r"|pilote"
    r"|prototype"
    r")\b",
    re.IGNORECASE,
)


def is_scope_exclusion_statement(
    value: Any,
) -> bool:
    """
    Return True only when text explicitly describes exclusion from
    product/MVP scope.

    The rule is grammatical and domain-independent. It must not depend
    on a feature name, sector, archetype, project or geography.

    Strong continuation forms such as:

        "It will not initially include ..."
        "Elle n'inclut pas initialement ..."

    are accepted even when the MVP antecedent is located in the previous
    sentence.

    Positive constructions such as:

        "The MVP includes ..."
        "Le MVP inclut ..."

    must remain false.

    "not only / pas seulement" is deliberately protected because it is
    additive rather than exclusive.
    """
    text = clean_text(
        value
    )

    if not text:
        return False

    key = comparison_key(
        text
    )

    if not key:
        return False

    # --------------------------------------------------------
    # Strong FR continuation / direct exclusion:
    #
    # "elle n inclut pas initialement ..."
    # "le mvp ne comprend pas ..."
    #
    # Protect "ne ... pas seulement", which is additive.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:n|ne)\s+"
        r"(?:"
        r"inclu(?:t|ent|ra|ront)"
        r"|comprend(?:s|ent|ra|ront)?"
        r"|contien(?:t|nent|dra|dront)"
        r")\s+"
        r"pas\b"
        r"(?!\s+seulement\b)",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Strong EN continuation / direct exclusion:
    #
    # "it will not initially include ..."
    # "the MVP does not include ..."
    #
    # Protect "does not only include ...".
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"do|does|did|"
        r"will|would|shall|should|"
        r"can|could"
        r")\s+not\b"
        r"(?!\s+only\b)"
        r"(?:\s+(?:"
        r"initially|currently|yet"
        r")){0,2}\s+"
        r"include\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    has_scope_reference = bool(
        _SCOPE_REFERENCE_PATTERN.search(
            key
        )
    )

    if not has_scope_reference:
        return False

    # --------------------------------------------------------
    # Scope-linked French exclusions.
    #
    # Modal negative scope declarations:
    #
    #   "Le MVP ne doit pas inclure ..."
    #   "La premi?re version ne devra pas comprendre ..."
    #   "Le prototype ne devrait pas contenir ..."
    #   "Le pilote ne peut pas inclure ..."
    #
    # These are grammatical scope exclusions, not feature-specific
    # heuristics. "pas seulement" remains additive and therefore
    # must not be classified as an exclusion.
    # --------------------------------------------------------

    french_modal_scope_exclusion = re.search(
        r"\b(?:n|ne)\s+"
        r"(?:"
        r"doit|doivent|"
        r"devra|devront|"
        r"devrait|devraient|"
        r"peut|peuvent|"
        r"pourra|pourront|"
        r"pourrait|pourraient"
        r")\s+"
        r"pas\b"
        r"(?!\s+seulement\b)"
        r"(?:\s+(?:"
        r"initialement|encore|actuellement"
        r")){0,2}\s+"
        r"(?:inclure|comprendre|contenir)\b",
        key,
        flags=re.IGNORECASE,
    )

    if french_modal_scope_exclusion is not None:
        return True

    french_scope_exclusions = (
        r"\b(?:n|ne)\s+"
        r"(?:fait|font|fera|feront)\s+"
        r"pas\b"
        r"(?:\s+(?:"
        r"initialement|encore|actuellement"
        r")){0,2}\s+"
        r"partie\b",

        r"\b(?:n|ne)\s+"
        r"(?:est|sont|sera|seront)\s+"
        r"pas\b"
        r"(?:\s+(?:"
        r"initialement|encore|actuellement"
        r")){0,2}\s+"
        r"inclu(?:e|es|s)?\b",

        r"\b(?:est|sont|sera|seront)\s+"
        r"exclu(?:e|es|s)?\b",

        r"\bhors\s+(?:du\s+|de\s+la\s+)?"
        r"perimetre\b",

        r"\bpas\s+dans\s+(?:le|la|les)?\s*"
        r"(?:"
        r"mvp|premiere version|version initiale|"
        r"prototype|pilote"
        r")\b",

        r"\b(?:"
        r"mvp|premiere version|version initiale|"
        r"prototype|pilote"
        r")\b"
        r".{0,80}\b"
        r"exclu(?:t|ent|ra|ront)\b",
    )

    if any(
        re.search(
            pattern,
            key,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern in french_scope_exclusions
    ):
        return True

    # --------------------------------------------------------
    # Scope-linked English exclusions.
    # --------------------------------------------------------

    english_scope_exclusions = (
        r"\b(?:is|are|was|were|will\s+be)\s+"
        r"not\s+part\s+of\b",

        r"\b(?:is|are|was|were|will\s+be)\s+"
        r"not\s+included\s+in\b",

        r"\b(?:is|are|was|were|will\s+be)\s+"
        r"excluded\s+from\b",

        r"\bout\s+of\s+scope\b",

        r"\bnot\s+(?:in|within)\s+(?:the\s+)?"
        r"(?:"
        r"mvp|first version|initial version|"
        r"prototype|pilot"
        r")\b",

        r"\b(?:"
        r"mvp|first version|initial version|"
        r"prototype|pilot"
        r")\b"
        r".{0,80}\b"
        r"exclud(?:e|es|ed|ing)\b",
    )

    return any(
        re.search(
            pattern,
            key,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern in english_scope_exclusions
    )
