"""Shared LLM JSON helpers for the Sprint 3 startup evaluator."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class StartupEvaluatorLLMError(Exception):
    """Raised when a provider response cannot be converted to a JSON object."""


def repair_text_encoding(value: Any) -> str:
    """Repair common UTF-8-as-Windows-1252 mojibake without changing clean text."""
    text = str(value or "")

    mojibake_markers = ("Ã", "Â", "â€", "â€™", "â€œ", "â€”", "ï¿½")
    if not any(marker in text for marker in mojibake_markers):
        return text

    candidate = text
    for _ in range(2):
        try:
            repaired = candidate.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

        old_score = sum(candidate.count(marker) for marker in mojibake_markers)
        new_score = sum(repaired.count(marker) for marker in mojibake_markers)

        if new_score >= old_score:
            break

        candidate = repaired

    return candidate


def repair_object_encoding(value: Any) -> Any:
    """Recursively repair text values and dictionary keys returned by an LLM."""
    if isinstance(value, dict):
        return {
            repair_text_encoding(key): repair_object_encoding(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [repair_object_encoding(item) for item in value]

    if isinstance(value, tuple):
        return tuple(repair_object_encoding(item) for item in value)

    if isinstance(value, str):
        return repair_text_encoding(value)

    return value


def _content_to_text(raw_response: Any) -> str:
    """Convert supported provider response shapes to text."""
    if isinstance(raw_response, dict):
        return json.dumps(raw_response, ensure_ascii=False)

    content = getattr(raw_response, "content", raw_response)

    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)

    return repair_text_encoding(content).strip()


def _strip_markdown_fence(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _remove_trailing_commas(text: str) -> str:
    """Remove trailing commas before a closing JSON delimiter."""
    return re.sub(r",\s*([}\]])", r"\1", text)


def _loads_object(candidate: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        parsed = json.loads(_remove_trailing_commas(candidate))

    if not isinstance(parsed, dict):
        raise StartupEvaluatorLLMError("Le JSON retourné n'est pas un objet.")

    return repair_object_encoding(parsed)


def extract_json_object(raw_response: Any) -> Dict[str, Any]:
    """Extract one JSON object from plain JSON, fenced JSON or surrounding text."""
    text = _strip_markdown_fence(_content_to_text(raw_response))

    if not text:
        raise StartupEvaluatorLLMError("Réponse LLM vide.")

    try:
        return _loads_object(text)
    except (json.JSONDecodeError, StartupEvaluatorLLMError):
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise StartupEvaluatorLLMError(
            "Impossible de trouver un objet JSON dans la réponse LLM : "
            f"{text[:500]}"
        )

    candidate = text[start : end + 1]

    try:
        return _loads_object(candidate)
    except (json.JSONDecodeError, StartupEvaluatorLLMError) as exc:
        raise StartupEvaluatorLLMError(
            f"JSON invalide retourné par le LLM : {exc}"
        ) from exc


async def invoke_llm_json(
    llm: LLMProvider,
    prompt: str,
    task_type: str,
) -> Dict[str, Any]:
    """Invoke the configured provider and return a repaired JSON dictionary."""
    logger.info("[StartupEvaluatorLLM] Appel LLM | task_type=%s", task_type)

    raw_response = await llm.invoke(prompt, task_type)
    parsed = extract_json_object(raw_response)

    logger.info(
        "[StartupEvaluatorLLM] JSON parsé avec succès | task_type=%s",
        task_type,
    )

    return parsed