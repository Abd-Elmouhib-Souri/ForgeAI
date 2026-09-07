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
    r"|first release"
    r"|initial release"
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


_SCOPE_EXCLUSION_SECTION_HEADING_PATTERN = re.compile(
    r"\b(?:"
    r"(?:explicitly\s+)?out\s+of\s+scope\s+for\s+(?:the\s+)?mvp"
    r"|outside\s+(?:the\s+)?mvp\s+scope"
    r"|mvp\s+exclusions?"
    r"|scope\s+exclusions?"
    r"|(?:the\s+)?exclusions?\s+(?:of|from)\s+(?:the\s+)?mvp"
    r"|(?:les?\s+)?exclusions?\s+du\s+mvp"
    r"|hors\s+(?:du\s+|de\s+la\s+)?"
    r"p(?:e|\u00e9)rim(?:e|\u00e8)tre"
    r"(?:\s+du\s+mvp)?"
    r"|(?:the\s+)?mvp\s+"
    r"(?:do|does|did|will|would|shall|should|can|could)\s+"
    r"not\b"
    r"(?!\s+only\b)"
    r"(?:\s+(?:initially|currently|yet)){0,2}\s+"
    r"include"
    r"|(?:le\s+)?mvp\s+"
    r"(?:"
    r"n['\u2019]\s*"
    r"|ne\s+"
    r")"
    r"(?:"
    r"inclu(?:t|ent|ra|ront)"
    r"|comprend(?:s|ent|ra|ront)?"
    r"|contien(?:t|nent|dra|dront)"
    r")\s+"
    r"pas\b"
    r"(?!\s+seulement\b)"
    r"(?:\s+(?:initialement|encore|actuellement)){0,2}"
    r")\b"
    r"(?:\s+(?:are|is|sont))?"
    r"\s*:?",
    re.IGNORECASE,
)


_SCOPE_FOLLOWING_SECTION_HEADING_PATTERN = re.compile(
    r"\b(?:"
    r"business\s+objective"
    r"|business\s+goal"
    r"|objectif\s+m(?:e|\u00e9)tier"
    r"|objectif\s+commercial"
    r")"
    r"\s*:",
    re.IGNORECASE,
)


def partition_scope_sections(
    value: Any,
) -> tuple[str, str]:
    """
    Split a mixed positive/negative MVP-scope carrier using explicit
    semantic section boundaries.

    This is a grammatical, domain-independent authority.

    Invariants:

    - a negative scope heading establishes negative polarity as a whole;
    - a token such as "MVP" inside a negative heading cannot make that
      section positive;
    - a following explicit planning section terminates the negative
      scope carrier;
    - feature vocabulary, sector, geography and project identity never
      participate in the decision.

    Historical heading grammar remains supported.
    """
    text = clean_text(
        value
    )

    if not text:
        return "", ""

    match = (
        _SCOPE_EXCLUSION_SECTION_HEADING_PATTERN.search(
            text
        )
    )

    if match is None:
        return text, ""

    positive = clean_text(
        text[
            :match.start()
        ].strip(
            " .,:;-"
        )
    )

    excluded_carrier = text[
        match.end():
    ]

    following_section = (
        _SCOPE_FOLLOWING_SECTION_HEADING_PATTERN.search(
            excluded_carrier
        )
    )

    if following_section is not None:
        excluded_carrier = excluded_carrier[
            :following_section.start()
        ]

    excluded = clean_text(
        excluded_carrier.strip(
            " .,:;-"
        )
    )

    return positive, excluded


def reconcile_scope_polarity(
    positive_values: list[Any],
    excluded_values: list[Any],
) -> list[str]:
    """
    Reconcile canonical scope polarity.

    An item explicitly established as excluded must never remain
    simultaneously in positive MVP scope.

    Matching uses exact canonical comparison only. It deliberately
    avoids substring, vocabulary, sector, archetype, project and
    geography heuristics.

    Positive ordering is preserved.
    """
    excluded_keys: set[str] = set()

    for value in excluded_values:
        text = clean_text(
            value
        )

        if not text:
            continue

        key = comparison_key(
            text
        )

        if key:
            excluded_keys.add(
                key
            )

    reconciled: list[str] = []
    seen_positive: set[str] = set()

    for value in positive_values:
        text = clean_text(
            value
        )

        if not text:
            continue

        key = comparison_key(
            text
        )

        if not key:
            continue

        if key in excluded_keys:
            continue

        if key in seen_positive:
            continue

        seen_positive.add(
            key
        )

        reconciled.append(
            text
        )

    return reconciled


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

    section_match = (
        _SCOPE_EXCLUSION_SECTION_HEADING_PATTERN.search(
            text
        )
    )

    if (
        section_match is not None
        and not clean_text(
            text[:section_match.start()]
        )
    ):
        return True

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


    # --------------------------------------------------------
    # QA8.7B3B direct passive exclusions.
    #
    # These formulations already express exclusion directly
    # and therefore do not need an additional MVP/scope noun:
    #
    #   "Marketplace features are not included."
    #   "The marketplace is not included."
    #
    # Positive declarations remain unaffected.
    # --------------------------------------------------------

    direct_passive_exclusions = (
        r"\b(?:is|are|was|were|will\s+be)\s+"
        r"not\s+included\b",

        r"\b(?:isnt|arent|wasnt|werent)\s+"
        r"included\b",

        r"\b(?:n|ne)\s+"
        r"(?:est|sont|sera|seront)\s+"
        r"pas\s+"
        r"inclu(?:e|es|s)?\b",
    )

    if any(
        re.search(
            pattern,
            key,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern in direct_passive_exclusions
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
    # F5 scope-qualified active capability negation.
    #
    # A current-release scope reference plus an explicit statement that
    # the product/service does not provide, collect, perform, etc. a
    # capability establishes negative product scope.
    #
    # The release-scope requirement above is essential: generic security,
    # resilience and behavioral negative controls remain outside this
    # classifier unless the user explicitly places them in release scope.
    #
    # No capability, sector, project, geography or archetype noun is
    # hard-coded here.
    # --------------------------------------------------------

    english_scoped_active_exclusion = re.search(
        r"\b(?:"
        r"do|does|did|"
        r"will|would|shall|should|"
        r"can|could"
        r")\s+not\b"
        r"(?!\s+only\b)"
        r"(?:\s+(?:"
        r"initially|currently|yet"
        r")){0,2}\s+"
        r"(?:"
        r"include|provide|offer|support|"
        r"perform|collect|process|handle|deliver|"
        r"replace"
        r")\b",
        key,
        flags=re.IGNORECASE,
    )

    if (
        english_scoped_active_exclusion
        is not None
    ):
        return True

    french_scoped_active_exclusion = re.search(
        r"\b(?:n|ne)\s+"
        r"(?:"
        r"fournit|fournissent|fournira|fourniront|"
        r"propose|proposent|proposera|proposeront|"
        r"offre|offrent|offrira|offriront|"
        r"collecte|collectent|collectera|collecteront|"
        r"traite|traitent|traitera|traiteront|"
        r"effectue|effectuent|effectuera|effectueront|"
        r"realise|realisent|realisera|realiseront|"
        r"inclut|incluent|inclura|incluront|"
        r"comprend|comprennent|comprendra|comprendront|"
        r"remplace|remplacent|remplacera|remplaceront"
        r")\s+"
        r"pas\b"
        r"(?!\s+seulement\b)",
        key,
        flags=re.IGNORECASE,
    )

    if (
        french_scoped_active_exclusion
        is not None
    ):
        return True

    french_scoped_modal_active_exclusion = re.search(
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
        r"(?:"
        r"fournir|proposer|offrir|"
        r"collecter|traiter|effectuer|realiser|"
        r"inclure|comprendre|contenir"
        r")\b",
        key,
        flags=re.IGNORECASE,
    )

    if (
        french_scoped_modal_active_exclusion
        is not None
    ):
        return True


    # --------------------------------------------------------
    # Scope-qualified delivery without a capability.
    #
    #   "The first release is delivered without X."
    #   "La premiere version est livree sans X."
    #
    # A plain operational "works without X" is deliberately
    # not classified as an exclusion.
    # --------------------------------------------------------

    scoped_without_exclusions = (
        r"\b(?:"
        r"mvp|first version|initial version|"
        r"first release|initial release|"
        r"prototype|pilot"
        r")\b"
        r".{0,60}\b"
        r"(?:"
        r"is|will\s+be|"
        r"is\s+delivered|will\s+be\s+delivered|"
        r"ships?|launch(?:es|ed)?"
        r")\b"
        r".{0,30}\bwithout\b",

        r"\b(?:"
        r"mvp|premiere version|version initiale|"
        r"prototype|pilote"
        r")\b"
        r".{0,60}\b"
        r"(?:"
        r"est|sera|"
        r"est\s+livree|sera\s+livree|"
        r"livree|lancee"
        r")\b"
        r".{0,30}\bsans\b",
    )

    if any(
        re.search(
            pattern,
            key,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern in scoped_without_exclusions
    ):
        return True

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
