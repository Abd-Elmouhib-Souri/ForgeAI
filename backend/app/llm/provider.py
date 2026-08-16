from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, ClassVar, Optional

from aiolimiter import AsyncLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMModelConfig:
    provider: str
    model_name: str
    rpm: int
    api_key: str
    priority: int


@dataclass
class ProviderHealth:
    failures: int = 0
    open_until: float = 0.0


class LLMProvider:
    BLOCKED_MODEL_NAMES: ClassVar[set[str]] = {
        "gemini-2.5-flash-lite",
        "models/gemini-2.5-flash-lite",
    }
    """Central LLM gateway.

    Generation order is Gemini -> Groq. Search is intentionally handled by
    ``SearchGateway`` because Groq is an LLM provider, not a web-search engine.
    The public ``invoke`` contract remains compatible with every existing agent.
    """

    _shared_models: ClassVar[dict[str, Any]] = {}
    _shared_limiters: ClassVar[dict[str, AsyncLimiter]] = {}
    _shared_health: ClassVar[dict[str, ProviderHealth]] = {}
    _model_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _fallback_chain_logged: ClassVar[bool] = False
    _blocked_model_config_logged: ClassVar[bool] = False

    def __init__(self) -> None:
        self.model_configs = self._build_model_configs()
        if not self.model_configs:
            raise RuntimeError(
                "Aucun modèle LLM disponible. Configure GEMINI_API_KEY ou GROQ_API_KEY."
            )

        if not LLMProvider._fallback_chain_logged:
            logger.info(
                "[LLMProvider] fallback_chain=%s",
                " -> ".join(self._model_key(item) for item in self.model_configs),
            )
            LLMProvider._fallback_chain_logged = True

    def _build_model_configs(self) -> list[LLMModelConfig]:
        configs: list[LLMModelConfig] = []
        priority = 1

        requested_order = [
            str(settings.LLM_PRIMARY_PROVIDER or "gemini").strip().lower(),
            str(settings.LLM_FALLBACK_PROVIDER or "groq").strip().lower(),
        ]
        provider_order: list[str] = []
        for provider in requested_order + ["gemini", "groq"]:
            if provider in {"gemini", "groq"} and provider not in provider_order:
                provider_order.append(provider)

        for provider in provider_order:
            if provider == "gemini" and settings.GEMINI_API_KEY:
                configs.append(
                    LLMModelConfig(
                        provider="gemini",
                        model_name=settings.GEMINI_MODEL,
                        rpm=8,
                        api_key=settings.GEMINI_API_KEY,
                        priority=priority,
                    )
                )
                priority += 1
                fallback_model = str(settings.GEMINI_FALLBACK_MODEL or "").strip()
                if fallback_model and fallback_model.lower() not in self.BLOCKED_MODEL_NAMES:
                    configs.append(
                        LLMModelConfig(
                            provider="gemini",
                            model_name=fallback_model,
                            rpm=8,
                            api_key=settings.GEMINI_API_KEY,
                            priority=priority,
                        )
                    )
                    priority += 1
                elif fallback_model and not LLMProvider._blocked_model_config_logged:
                    # The obsolete fallback is ignored safely. Log once at INFO
                    # rather than emitting one warning for every agent instance.
                    logger.info(
                        "[LLMProvider] obsolete Gemini fallback ignored; clear GEMINI_FALLBACK_MODEL in .env",
                    )
                    LLMProvider._blocked_model_config_logged = True

            if provider == "groq" and settings.GROQ_API_KEY:
                configs.append(
                    LLMModelConfig(
                        provider="groq",
                        model_name=settings.GROQ_MODEL,
                        rpm=20,
                        api_key=settings.GROQ_API_KEY,
                        priority=priority,
                    )
                )
                priority += 1
                if settings.GROQ_FALLBACK_MODEL:
                    configs.append(
                        LLMModelConfig(
                            provider="groq",
                            model_name=settings.GROQ_FALLBACK_MODEL,
                            rpm=20,
                            api_key=settings.GROQ_API_KEY,
                            priority=priority,
                        )
                    )
                    priority += 1

        return sorted(configs, key=lambda item: item.priority)

    @staticmethod
    def _model_key(config: LLMModelConfig) -> str:
        return f"{config.provider}:{config.model_name}"

    def _get_limiter(self, config: LLMModelConfig) -> AsyncLimiter:
        key = self._model_key(config)
        limiter = self._shared_limiters.get(key)
        if limiter is None:
            limiter = AsyncLimiter(config.rpm, 60)
            self._shared_limiters[key] = limiter
        return limiter

    async def _get_or_create_model(self, config: LLMModelConfig) -> Any:
        key = self._model_key(config)
        cached = self._shared_models.get(key)
        if cached is not None:
            return cached

        async with self._model_lock:
            cached = self._shared_models.get(key)
            if cached is not None:
                return cached

            timeout = float(settings.LLM_REQUEST_TIMEOUT_SECONDS)
            if config.provider == "gemini":
                model = ChatGoogleGenerativeAI(
                    model=config.model_name,
                    google_api_key=config.api_key,
                    temperature=0.2,
                    timeout=timeout,
                    max_retries=0,
                )
            elif config.provider == "groq":
                model = ChatGroq(
                    model=config.model_name,
                    groq_api_key=config.api_key,
                    temperature=0.2,
                    timeout=timeout,
                    max_retries=0,
                )
            else:
                raise RuntimeError(f"Provider LLM non supporté : {config.provider}")

            self._shared_models[key] = model
            return model

    @staticmethod
    def _error_kind(exc: Exception) -> str:
        message = str(exc).lower()
        if any(token in message for token in (
            "429", "rate limit", "quota", "resource_exhausted", "500", "502",
            "503", "504", "timeout", "timed out", "temporarily unavailable",
            "service unavailable", "connection reset", "connection error",
        )):
            return "temporary"
        if any(token in message for token in (
            "api_key_invalid", "api key not valid", "invalid api key", "unauthorized",
            "permission denied", "401", "403", "invalid argument", "model not found", "404",
        )):
            return "configuration"
        return "unknown"

    def _circuit_is_open(self, config: LLMModelConfig) -> bool:
        health = self._shared_health.setdefault(
            self._model_key(config), ProviderHealth()
        )
        return health.open_until > time.time()

    def _record_success(self, config: LLMModelConfig) -> None:
        health = self._shared_health.setdefault(
            self._model_key(config), ProviderHealth()
        )
        health.failures = 0
        health.open_until = 0.0

    def _record_failure(self, config: LLMModelConfig, kind: str) -> None:
        health = self._shared_health.setdefault(
            self._model_key(config), ProviderHealth()
        )
        health.failures += 1
        if kind == "configuration" or health.failures >= settings.LLM_CIRCUIT_FAILURES:
            health.open_until = time.time() + settings.LLM_CIRCUIT_COOLDOWN_SECONDS

    async def invoke(self, prompt: str, task_type: str = "general") -> str:
        if not str(prompt or "").strip():
            raise ValueError("Le prompt LLM ne peut pas être vide.")

        last_error: Optional[Exception] = None
        attempted = 0

        for config in self.model_configs:
            key = self._model_key(config)
            if self._circuit_is_open(config):
                logger.warning(
                    "[LLMProvider] circuit_open model=%s task_type=%s", key, task_type
                )
                continue

            attempted += 1
            try:
                logger.info(
                    "[LLMProvider] trying model=%s task_type=%s", key, task_type
                )
                model = await self._get_or_create_model(config)
                limiter = self._get_limiter(config)
                async with limiter:
                    response = await asyncio.wait_for(
                        model.ainvoke(prompt),
                        timeout=float(settings.LLM_REQUEST_TIMEOUT_SECONDS),
                    )

                content = getattr(response, "content", None)
                if isinstance(content, list):
                    content = "\n".join(
                        str(item.get("text") if isinstance(item, dict) else item)
                        for item in content
                    )
                content = str(content or "").strip()
                if not content:
                    raise RuntimeError(f"Réponse vide depuis {key}")

                self._record_success(config)
                logger.info(
                    "[LLMProvider] success model=%s task_type=%s", key, task_type
                )
                return content

            except Exception as exc:
                last_error = exc
                kind = self._error_kind(exc)
                self._record_failure(config, kind)
                logger.warning(
                    "[LLMProvider] failed model=%s task_type=%s kind=%s error=%s",
                    key,
                    task_type,
                    kind,
                    str(exc)[:1000],
                )
                # Always continue to the next configured provider. A configuration
                # error is visible in logs and opens the provider circuit, but does
                # not prevent Groq from keeping the analysis available.
                continue

        if attempted == 0:
            raise RuntimeError("Tous les circuits LLM configurés sont temporairement ouverts.")

        raise RuntimeError(
            f"Tous les modèles LLM ont échoué. Dernière erreur : {last_error}"
        )
