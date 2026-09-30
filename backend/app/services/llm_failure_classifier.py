"""
Classify why an AI generation step failed.

Why this module exists
----------------------
Before this, every Solution Architect failure surfaced as the same
"service temporarily unavailable" message: an exhausted free quota, a
decommissioned model (HTTP 404 ``model_not_found``) and an invalid LLM
answer were indistinguishable for the user and for the retry logic.

This module walks the exception chain (``__cause__`` / ``__context__``),
finds the typed ``LLMUnavailableError`` raised by ``LLMProvider`` and turns
it into one stable, user-facing classification.

The classification is deterministic and universal: it depends only on
error types and provider failure kinds, never on a project, sector,
country or model name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.llm.provider import LLMUnavailableError

# Stable codes shared by backend, API and frontend.
LLM_QUOTA_OR_UNAVAILABLE = "llm_quota_or_unavailable"
LLM_CONFIGURATION_ERROR = "llm_configuration_error"
INVALID_MODEL_OUTPUT = "invalid_model_output"
CONTEXT_INVALID = "context_invalid"
UNEXPECTED_ERROR = "unexpected_error"

# Upstream error codes meaning "the canonical project context is unusable":
# retrying cannot help until the analysis is re-run.
_CONTEXT_CODES = frozenset(
    {
        "analysis_required",
        "project_context_missing",
        "project_context_invalid",
        "project_context_required",
    }
)

# Plain-text markers kept as a fallback for errors raised outside
# LLMProvider (e.g. an SDK error that escaped without the typed wrapper).
_TEMPORARY_MARKERS = (
    "429",
    "quota",
    "resource_exhausted",
    "rate limit",
    "circuits llm",
    "temporarily unavailable",
    "timeout",
    "timed out",
)
_CONFIGURATION_MARKERS = (
    "model_not_found",
    "does not exist",
    "api key not valid",
    "invalid api key",
    "api_key_invalid",
)


@dataclass(frozen=True)
class FailureClassification:
    """Stable, serialisable description of a failed generation step."""

    code: str
    # True when an automatic delayed retry can reasonably succeed.
    retryable: bool
    # "provider:model" identifiers whose configuration is broken.
    misconfigured_models: tuple[str, ...] = field(default_factory=tuple)
    # Short technical detail for logs / admin, never shown raw to users.
    detail: str = ""


def _chain(exc: BaseException | None) -> list[BaseException]:
    """Return exc and its causes, without looping on cyclic chains."""
    seen: list[BaseException] = []
    current = exc
    while current is not None and all(current is not item for item in seen):
        seen.append(current)
        current = current.__cause__ or current.__context__
    return seen


def find_llm_unavailable(exc: BaseException | None) -> LLMUnavailableError | None:
    """First LLMUnavailableError in the exception chain, if any."""
    for item in _chain(exc):
        if isinstance(item, LLMUnavailableError):
            return item
    return None


def is_provider_unavailable(exc: BaseException | None) -> bool:
    """
    True when no model could answer at all (quota, outage, bad config).

    Immediate retries are pointless in that case: every circuit is open
    or every provider refused. Content errors (invalid JSON, policy
    rejection) are NOT provider unavailability and stay retryable.
    """
    if find_llm_unavailable(exc) is not None:
        return True
    text = " ".join(str(item).lower() for item in _chain(exc))
    return any(marker in text for marker in _TEMPORARY_MARKERS + _CONFIGURATION_MARKERS)


def _kind_base(kind: str) -> str:
    # "circuit_open:configuration" -> "configuration"
    return kind.split(":", 1)[1] if kind.startswith("circuit_open:") else kind


def classify(exc: BaseException | None) -> FailureClassification:
    """Map any generation failure to one stable classification."""
    chain = _chain(exc)
    detail = str(chain[-1] if chain else exc or "")[:500]

    unavailable = find_llm_unavailable(exc)
    if unavailable is not None:
        kinds = {key: _kind_base(kind) for key, kind in unavailable.failures.items()}
        misconfigured = tuple(sorted(k for k, v in kinds.items() if v == "configuration"))
        # At least one model is only temporarily blocked (quota / outage /
        # unknown): waiting can fix it, even if another model is broken.
        if not kinds or any(v != "configuration" for v in kinds.values()):
            return FailureClassification(
                code=LLM_QUOTA_OR_UNAVAILABLE,
                retryable=True,
                misconfigured_models=misconfigured,
                detail=detail,
            )
        # Every model is misconfigured: waiting cannot fix it.
        return FailureClassification(
            code=LLM_CONFIGURATION_ERROR,
            retryable=False,
            misconfigured_models=misconfigured,
            detail=detail,
        )

    # Typed business errors carry a ``code`` attribute.
    codes = {str(getattr(item, "code", "") or "") for item in chain}
    if codes & _CONTEXT_CODES:
        return FailureClassification(code=CONTEXT_INVALID, retryable=False, detail=detail)

    text = " ".join(str(item).lower() for item in chain)
    if any(marker in text for marker in _CONFIGURATION_MARKERS):
        return FailureClassification(code=LLM_CONFIGURATION_ERROR, retryable=False, detail=detail)
    if any(marker in text for marker in _TEMPORARY_MARKERS):
        return FailureClassification(code=LLM_QUOTA_OR_UNAVAILABLE, retryable=True, detail=detail)

    if codes & {"generation_retryable", "invalid_model_response", "policy_rejected"}:
        return FailureClassification(code=INVALID_MODEL_OUTPUT, retryable=True, detail=detail)

    return FailureClassification(code=UNEXPECTED_ERROR, retryable=True, detail=detail)
