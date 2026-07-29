"""
Helper LLM pour Sprint 3 — Startup Evaluator.

Rôle :
- appeler LLMProvider
- récupérer le contenu texte
- extraire un JSON valide
- éviter que les agents répètent le même code de parsing
"""

import json
import logging
import re
from typing import Any, Dict

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class StartupEvaluatorLLMError(Exception):
    """Erreur spécifique au parsing ou à l'appel LLM du Sprint 3."""


def _content_to_text(raw_response: Any) -> str:
    """
    Convertit différents formats possibles de réponse LLM en texte.

    Le LLMProvider peut retourner :
    - string JSON
    - dict
    - objet avec .content
    """
    if isinstance(raw_response, dict):
        return json.dumps(raw_response, ensure_ascii=False)

    content = getattr(raw_response, "content", raw_response)

    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)

    return str(content or "").strip()


def extract_json_object(raw_response: Any) -> Dict[str, Any]:
    """
    Extrait un objet JSON depuis la réponse LLM.

    Accepte :
    - JSON pur
    - ```json ... ```
    - texte contenant un JSON
    """
    text = _content_to_text(raw_response)

    if not text:
        raise StartupEvaluatorLLMError("Réponse LLM vide.")

    # Supprimer les blocs markdown éventuels.
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Essai direct.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed

        raise StartupEvaluatorLLMError("Le JSON retourné n'est pas un objet.")
    except json.JSONDecodeError:
        pass

    # Essai en extrayant de la première accolade à la dernière.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise StartupEvaluatorLLMError(
            f"Impossible de trouver un objet JSON dans la réponse LLM : {text[:500]}"
        )

    candidate = text[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise StartupEvaluatorLLMError(
            f"JSON invalide retourné par le LLM : {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise StartupEvaluatorLLMError("Le JSON extrait n'est pas un objet.")

    return parsed


async def invoke_llm_json(
    llm: LLMProvider,
    prompt: str,
    task_type: str,
) -> Dict[str, Any]:
    """
    Appelle le LLMProvider et retourne un dict JSON.

    Important :
    - task_type permet au LLMProvider de choisir le bon modèle / fallback.
    - On garde un log clair pour debug.
    """
    logger.info(f"[StartupEvaluatorLLM] Appel LLM | task_type={task_type}")

    raw_response = await llm.invoke(prompt, task_type)

    parsed = extract_json_object(raw_response)

    logger.info(f"[StartupEvaluatorLLM] JSON parsé avec succès | task_type={task_type}")

    return parsed