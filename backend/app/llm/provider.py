import asyncio
import logging
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
    api_key: Optional[str]
    priority: int


class LLMProvider:
    """
    Provider LLM centralisé pour ForgeAI.

    Corrections importantes :
    - Les modèles sont partagés entre toutes les instances.
    - Les rate limiters sont partagés entre tous les agents.
    - Chaque agent garde le même point d'entrée : invoke(prompt, task_type).
    - Le fallback Gemini -> Gemini fallback -> Groq -> Groq fallback reste actif.
    """

    _shared_models: ClassVar[dict[str, Any]] = {}
    _shared_limiters: ClassVar[dict[str, AsyncLimiter]] = {}
    _shared_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _fallback_chain_logged: ClassVar[bool] = False

    def __init__(self) -> None:
        self.model_configs = self._build_model_configs()

        if not self.model_configs:
            raise RuntimeError(
                "Aucun modèle LLM disponible. Vérifie GEMINI_API_KEY ou GROQ_API_KEY dans .env."
            )

        if not LLMProvider._fallback_chain_logged:
            print(
                "[LLMProvider] Fallback chain = "
                + " -> ".join(self._model_key(config) for config in self.model_configs),
                flush=True,
            )
            LLMProvider._fallback_chain_logged = True

    def _build_model_configs(self) -> list[LLMModelConfig]:
        configs: list[LLMModelConfig] = []

        if settings.GEMINI_API_KEY:
            configs.append(
                LLMModelConfig(
                    provider="gemini",
                    model_name=settings.GEMINI_MODEL,
                    rpm=8,
                    api_key=settings.GEMINI_API_KEY,
                    priority=1,
                )
            )

            configs.append(
                LLMModelConfig(
                    provider="gemini",
                    model_name=settings.GEMINI_FALLBACK_MODEL,
                    rpm=10,
                    api_key=settings.GEMINI_API_KEY,
                    priority=2,
                )
            )

        if settings.GROQ_API_KEY:
            configs.append(
                LLMModelConfig(
                    provider="groq",
                    model_name=settings.GROQ_MODEL,
                    rpm=20,
                    api_key=settings.GROQ_API_KEY,
                    priority=3,
                )
            )

            configs.append(
                LLMModelConfig(
                    provider="groq",
                    model_name=settings.GROQ_FALLBACK_MODEL,
                    rpm=20,
                    api_key=settings.GROQ_API_KEY,
                    priority=4,
                )
            )

        return sorted(configs, key=lambda config: config.priority)

    def _model_key(self, config: LLMModelConfig) -> str:
        return f"{config.provider}:{config.model_name}"

    def _get_limiter(self, config: LLMModelConfig) -> AsyncLimiter:
        key = self._model_key(config)

        if key not in LLMProvider._shared_limiters:
            LLMProvider._shared_limiters[key] = AsyncLimiter(config.rpm, 60)

        return LLMProvider._shared_limiters[key]

    def _get_or_create_model(self, config: LLMModelConfig) -> Any:
        key = self._model_key(config)

        if key in LLMProvider._shared_models:
            return LLMProvider._shared_models[key]

        if config.provider == "gemini":
            model = ChatGoogleGenerativeAI(
                model=config.model_name,
                google_api_key=config.api_key,
                temperature=0.2,
            )

        elif config.provider == "groq":
            model = ChatGroq(
                model=config.model_name,
                groq_api_key=config.api_key,
                temperature=0.2,
            )

        else:
            raise RuntimeError(f"Provider LLM non supporté : {config.provider}")

        LLMProvider._shared_models[key] = model
        return model

    def _is_fallback_error(self, exc: Exception) -> bool:
        message = str(exc).lower()

        fallback_keywords = [
            "429",
            "too many requests",
            "rate limit",
            "quota",
            "resource_exhausted",
            "500",
            "502",
            "503",
            "504",
            "timeout",
            "timed out",
            "temporarily unavailable",
            "service unavailable",
            "unavailable",
            "connection",
            "connection error",
            "apierror",
            "model not found",
            "not found",
            "404",
            "400",
            "api_key_invalid",
            "api key not valid",
            "invalid api key",
            "invalid argument provided to gemini",
            "permission denied",
            "unauthorized",
            "401",
            "403",
        ]

        return any(keyword in message for keyword in fallback_keywords)

    async def invoke(self, prompt: str, task_type: str = "general") -> str:
        last_error: Optional[Exception] = None

        for index, config in enumerate(self.model_configs):
            key = self._model_key(config)
            has_next_model = index < len(self.model_configs) - 1

            try:
                print(
                    f"[LLMProvider] Trying model={key} | task_type={task_type}",
                    flush=True,
                )

                limiter = self._get_limiter(config)

                async with limiter:
                    async with LLMProvider._shared_lock:
                        model = self._get_or_create_model(config)

                    response = await model.ainvoke(prompt)

                content = getattr(response, "content", None)

                if not content:
                    raise RuntimeError(f"Réponse vide depuis {key}")

                print(
                    f"[LLMProvider] Success model={key} | task_type={task_type}",
                    flush=True,
                )

                return str(content)

            except Exception as exc:
                last_error = exc
                can_fallback = self._is_fallback_error(exc)

                print(
                    f"[LLMProvider] Failed model={key} | "
                    f"task_type={task_type} | "
                    f"fallback={can_fallback and has_next_model} | "
                    f"error={str(exc)[:300]}",
                    flush=True,
                )

                logger.warning(
                    "[LLMProvider] Model failed | model=%s | task_type=%s | fallback=%s | error=%s",
                    key,
                    task_type,
                    can_fallback and has_next_model,
                    str(exc)[:1000],
                )

                if can_fallback and has_next_model:
                    next_config = self.model_configs[index + 1]
                    next_key = self._model_key(next_config)

                    print(
                        f"[LLMProvider] fallback -> {next_key}",
                        flush=True,
                    )

                    continue

                break

        raise RuntimeError(
            f"Tous les modèles LLM ont échoué. Dernière erreur : {last_error}"
        )