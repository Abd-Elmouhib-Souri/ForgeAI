from __future__ import annotations

import re
from typing import Any

from app.schemas.analysis_context import (
    clean_text,
    comparison_key,
)


_EXPLICIT_CONSTRAINT_LABEL = re.compile(
    r"^(?:"
    r"(?:the\s+)?(?:main\s+)?constraints?"
    r"|(?:les\s+)?contraintes?"
    r"(?:\s+principales?)?"
    r")\b",
    re.IGNORECASE,
)


_SCOPE_INCLUSION = re.compile(
    r"^\s*"
    r"(?:(?:the|le|la)\s+)?"
    r"(?:"
    r"mvp"
    r"|minimum viable product"
    r"|first version"
    r"|initial version"
    r"|premiere version"
    r"|version initiale"
    r"|prototype"
    r"|pilot"
    r"|pilote"
    r")\b"
    r".{0,40}\b"
    r"(?:"
    r"includ(?:e|es|ed|ing)"
    r"|contain(?:s|ed|ing)?"
    r"|compris(?:e|es)?"
    r"|comprend(?:s|ent|ra|ront)?"
    r"|inclu(?:t|ent|ra|ront)"
    r")\b",
    re.IGNORECASE,
)


def is_negative_control_statement(
    value: Any,
) -> bool:
    """
    Detect an explicit strong prohibition/control requirement.

    This authority is intentionally domain-independent.

    It classifies grammatical prohibitions such as:

        "The system must not ..."
        "The service shall not ..."
        "Le systeme ne doit pas ..."
        "Le MVP ne devra jamais ..."

    It does not classify positive obligations and deliberately protects
    additive formulations such as "must not only" / "ne doit pas
    seulement".

    Scope exclusion remains a separate authority owned by
    scope_polarity.py.
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

    english_negative_control = re.search(
        r"\b(?:must|shall)\s+"
        r"(?:"
        r"not\b(?!\s+(?:only|necessarily)\b)"
        r"|never\b"
        r")",
        key,
        flags=re.IGNORECASE,
    )

    if english_negative_control is not None:
        return True

    french_negative_control = re.search(
        r"\b(?:ne|n)\s+"
        r"(?:"
        r"doit|doivent|"
        r"devra|devront|"
        r"devrait|devraient"
        r")\s+"
        r"(?:"
        r"pas\b(?!\s+(?:seulement|necessairement)\b)"
        r"|jamais\b"
        r")",
        key,
        flags=re.IGNORECASE,
    )

    return (
        french_negative_control
        is not None
    )


def is_constraint_statement(
    value: Any,
) -> bool:
    """
    Detect an actual restriction, obligation or operating boundary.

    The rule is intentionally domain-independent. A domain word such
    as "maintenance", "alert", "battery", "report" or "tracking" is
    never sufficient on its own to classify a sentence as a constraint.
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

    # Explicitly labelled constraint sections remain authoritative.
    if _EXPLICIT_CONSTRAINT_LABEL.match(
        key
    ):
        return True

    # A strong negative modal requirement is a control/constraint.
    #
    # It is deliberately not treated as a scope exclusion here.
    # Scope exclusion remains owned by scope_polarity.py.
    if is_negative_control_statement(
        text
    ):
        return True

    # A positive MVP inclusion is product scope, not a constraint.
    if _SCOPE_INCLUSION.search(
        key
    ):
        return False

    # --------------------------------------------------------
    # Budget / cost ceilings or explicit financial boundaries.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"budget|costs?|cost|cout|couts|prix"
        r")\b"
        r".{0,80}\b(?:"
        r"limited|limit|maximum|max|cap|capped|ceiling|"
        r"not exceed|must not exceed|"
        r"limite|limitee|limites|limitees|maximum|maximal|"
        r"plafond|ne doit pas depasser|ne peuvent pas depasser"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Time / deadline boundaries.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"deployment|delivery|implementation|completion|"
        r"deploiement|livraison|implementation|realisation"
        r")\b"
        r".{0,80}\b(?:"
        r"within|before|by|no later than|"
        r"dans|avant|au plus tard"
        r")\b"
        r".{0,40}\b"
        r"(?:"
        r"hours?|days?|weeks?|months?|years?|"
        r"heures?|jours?|semaines?|mois|ans?"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    if re.search(
        r"\b(?:"
        r"must|shall|required to|has to|have to|"
        r"doit|doivent|devra|devront"
        r")\b"
        r".{0,80}\b(?:"
        r"be completed|be delivered|be deployed|"
        r"etre termine|etre terminee|etre livre|etre livree|"
        r"etre deploye|etre deployee"
        r")\b"
        r".{0,80}\b(?:"
        r"within|before|by|"
        r"dans|avant"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Offline / connectivity operating boundary.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"must|shall|required to|has to|have to|"
        r"doit|doivent|devra|devront"
        r")\b"
        r".{0,80}\b(?:"
        r"work|operate|function|fonctionner|operer"
        r")\b"
        r".{0,40}\b(?:"
        r"offline|hors ligne|without internet|sans internet|"
        r"without connectivity|sans connexion"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Mandatory hosting / residency / deployment location.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"data|information|donnees"
        r")\b"
        r".{0,80}\b(?:"
        r"must|shall|required|"
        r"doit|doivent|devra|devront"
        r")\b"
        r".{0,80}\b(?:"
        r"hosted|stored|remain hosted|remain stored|"
        r"heberge|hebergees|stocke|stockees"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    if re.search(
        r"\b(?:"
        r"must|shall|required to|"
        r"doit|doivent|devra|devront"
        r")\b"
        r".{0,80}\b(?:"
        r"remain hosted|remain stored|be hosted|be stored|"
        r"rester heberge|rester hebergees|"
        r"etre heberge|etre hebergees|"
        r"etre stocke|etre stockees"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Mandatory compatibility / existing infrastructure.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"must|shall|required to|has to|have to|"
        r"doit|doivent|devra|devront"
        r")\b"
        r".{0,80}\b(?:"
        r"compatible with|integrate with|work with|"
        r"compatible avec|s integrer a|fonctionner avec"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Regulatory / security / privacy compliance.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"must|shall|required to|has to|have to|"
        r"doit|doivent|devra|devront"
        r")\b"
        r".{0,80}\b(?:"
        r"comply with|comply|respect|respecter|conform|"
        r"conforme|conformite"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    if re.search(
        r"\b(?:"
        r"regulatory requirement|regulatory requirements|"
        r"regulatory constraint|regulatory constraints|"
        r"exigence reglementaire|exigences reglementaires|"
        r"contrainte reglementaire|contraintes reglementaires"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    # --------------------------------------------------------
    # Quantified technical ceilings / floors.
    # --------------------------------------------------------

    if re.search(
        r"\b(?:"
        r"latency|response time|memory|storage|power consumption|"
        r"latence|temps de reponse|memoire|stockage|"
        r"consommation"
        r")\b"
        r".{0,60}\b(?:"
        r"less than|under|below|at most|maximum|max|"
        r"greater than|above|at least|minimum|min|"
        r"inferieur|inferieure|moins de|au plus|maximum|"
        r"superieur|superieure|au moins|minimum"
        r")\b",
        key,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def has_explicit_scope_reference(
    value: Any,
) -> bool:
    """
    Return True when text explicitly names a product-scope artifact.

    Used to prevent generic phrases such as "budget is limited to..."
    from being mistaken for MVP declarations.
    """
    text = clean_text(
        value
    )

    if not text:
        return False

    key = comparison_key(
        text
    )

    return bool(
        re.search(
            r"\b(?:"
            r"mvp"
            r"|minimum viable product"
            r"|first version"
            r"|initial version"
            r"|premiere version"
            r"|version initiale"
            r"|prototype"
            r"|first pilot"
            r"|premier pilote"
            r"|premiere pilote"
            r")\b",
            key,
            flags=re.IGNORECASE,
        )
    )
