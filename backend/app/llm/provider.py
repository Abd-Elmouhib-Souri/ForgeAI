from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar, Optional

from aiolimiter import AsyncLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.config import settings

logger = logging.getLogger(__name__)

# Groq limit errors, e.g.:
#   413 "Request too large ... on tokens per minute (TPM): Limit 8000, Requested 12738"
#   429 "Rate limit reached ... (TPM): Limit 8000, Used 7888, Requested 6120.
#        Please try again in 7.66s"
#   429 "Request too large ... output tokens per minute (OTPM): Limit 1000, Requested 2305"
_TOKEN_LIMIT_RE = re.compile(
    r"\((I|O)?TPM\):\s*Limit\s+(\d+)(?:,\s*Used\s+(\d+))?,\s*Requested\s+(\d+)",
    re.IGNORECASE,
)
_RETRY_AFTER_RE = re.compile(
    r"try again in\s+(?:(\d+)m)?(\d+(?:\.\d+)?)(ms|s)", re.IGNORECASE
)
# Kept free between the estimated prompt and the answer budget.
_TOKEN_SAFETY_MARGIN = 256


def _estimate_tokens(text: str) -> int:
    # Conservative: ~3.2 characters per token for French prose + JSON.
    return int(len(text or "") / 3.2) + 32


@dataclass(frozen=True)
class LLMModelConfig:
    provider: str
    model_name: str
    rpm: int
    api_key: str
    priority: int
    base_url: str | None = None
    supports_structured: bool = False


@dataclass
class ProviderHealth:
    failures: int = 0
    open_until: float = 0.0
    # Last proven failure kind ("temporary" | "configuration") that fed this
    # circuit. Lets a later "circuit_open" skip explain its real cause.
    last_kind: str = ""


class LLMUnavailableError(RuntimeError):
    """
    Every configured model failed or was skipped for one invocation.

    Subclass of RuntimeError: every existing ``except RuntimeError`` /
    ``except Exception`` caller keeps working unchanged.

    ``failures`` maps "provider:model" -> kind, where kind is one of
    "temporary", "configuration", "unknown" or "circuit_open:<last_kind>".
    Callers (e.g. the post-analysis pipeline) use it to distinguish an
    exhausted quota (retry later) from a broken configuration (fix .env).
    """

    def __init__(self, message: str, failures: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.failures: dict[str, str] = dict(failures or {})


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
    # "provider:model" -> ("TPM" | "OTPM" | "ITPM", limit) learned from errors.
    _learned_token_limits: ClassVar[dict[str, tuple[str, int]]] = {}
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
                        supports_structured=True,
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
                            supports_structured=True,
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
                        base_url=settings.GROQ_API_BASE or None,
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
                            # Same endpoint as the primary Groq model: without
                            # it the fallback silently bypassed GROQ_API_BASE.
                            base_url=settings.GROQ_API_BASE or None,
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

    async def _get_or_create_model(
        self,
        config: LLMModelConfig,
        *,
        structured: bool = False,
    ) -> Any:
        key = self._model_key(config)
        if structured:
            # Le mode structure (tool calling / with_structured_output) est
            # incompatible, cote API, avec le mode JSON force utilise par
            # invoke() (Groq : "json mode cannot be combined with tool/
            # function calling"). Instance separee, jamais partagee avec
            # celle d'invoke(), pour eviter ce conflit.
            key = f"{key}:structured"
        cached = self._shared_models.get(key)
        if cached is not None:
            return cached

        async with self._model_lock:
            cached = self._shared_models.get(key)
            if cached is not None:
                return cached

            timeout = float(settings.LLM_REQUEST_TIMEOUT_SECONDS)
            if config.provider == "gemini":
                if structured:
                    model = ChatGoogleGenerativeAI(
                        model=config.model_name,
                        google_api_key=config.api_key,
                        temperature=0.2,
                        timeout=timeout,
                        max_tokens=6000,
                        # Pas de response_mime_type ici : with_structured_output
                        # pilote lui-meme le format via l'appel de fonction natif.
                        max_retries=0,
                    )
                else:
                    model = ChatGoogleGenerativeAI(
                        model=config.model_name,
                        google_api_key=config.api_key,
                        temperature=0.2,
                        timeout=timeout,
                        max_tokens=6000,
                        # Both Sprint 4 agents have a strict JSON contract.  Ask
                        # Gemini to enforce it at the provider boundary rather
                        # than spending a second free request repairing prose.
                        response_mime_type="application/json",
                        max_retries=0,
                    )
            elif config.provider == "groq":
                if structured:
                    model = ChatGroq(
                        model=config.model_name,
                        groq_api_key=config.api_key,
                        groq_api_base=config.base_url,
                        temperature=0.2,
                        timeout=timeout,
                        max_tokens=6000,
                        # Pas de model_kwargs response_format ici : Groq
                        # refuse explicitement de combiner json_object mode
                        # avec le tool calling qu'utilise with_structured_output.
                        max_retries=0,
                    )
                else:
                    model = ChatGroq(
                        model=config.model_name,
                        groq_api_key=config.api_key,
                        groq_api_base=config.base_url,
                        temperature=0.2,
                        timeout=timeout,
                        max_tokens=8000,
                        **self._groq_reasoning_kwargs(config),
                    # Groq's JSON object mode is supported by the selected
                        # free models and avoids Markdown/prose wrappers.
                        model_kwargs={
                            "response_format": {"type": "json_object"},
                        },
                        max_retries=0,
                    )
            else:
                raise RuntimeError(f"Provider LLM non supporté : {config.provider}")

            self._shared_models[key] = model
            return model

    @staticmethod
    def _groq_reasoning_kwargs(config: LLMModelConfig) -> dict[str, Any]:
        effort = str(settings.GROQ_REASONING_EFFORT or "").strip()
        if effort and "gpt-oss" in config.model_name.lower():
            return {"reasoning_effort": effort}
        return {}

    @staticmethod
    def _default_max_tokens(model: Any) -> int | None:
        value = getattr(model, "max_tokens", None) or getattr(model, "max_output_tokens", None)
        return int(value) if isinstance(value, int) and value > 0 else None

    def _output_budget(self, key: str, prompt: str, default_max: int | None) -> int | None:
        """
        Answer budget that fits the model's learned per-minute limit.

        None  -> no known limit: use the model default.
        0     -> the prompt alone cannot fit: skip this model.
        """
        learned = self._learned_token_limits.get(key)
        if not learned or not default_max:
            return None
        scope, limit = learned
        if scope == "OTPM":
            budget = limit - _TOKEN_SAFETY_MARGIN
        elif scope == "ITPM":
            budget = default_max if _estimate_tokens(prompt) + _TOKEN_SAFETY_MARGIN <= limit else 0
        else:  # TPM counts prompt + requested max_tokens
            budget = limit - _estimate_tokens(prompt) - _TOKEN_SAFETY_MARGIN
        budget = min(default_max, budget)
        return budget if budget >= settings.LLM_MIN_OUTPUT_TOKENS else 0

    def _learn_from_limit_error(self, key: str, exc: Exception, sent_max: int | None) -> tuple[int | None, float | None]:
        """
        Parse a per-minute limit error.

        Returns (new_max_tokens, wait_seconds):
        * new_max_tokens: smaller answer budget that fits the limit (413 case);
        * wait_seconds: provider-advised wait before the budget refills (429).
        """
        message = str(exc)
        match = _TOKEN_LIMIT_RE.search(message)
        new_max: int | None = None
        if match:
            prefix, limit_raw, _used, requested_raw = match.groups()
            scope = f"{(prefix or '').upper()}TPM"
            limit, requested = int(limit_raw), int(requested_raw)
            self._learned_token_limits[key] = (scope, limit)
            if requested > limit and sent_max:
                if scope == "OTPM":
                    candidate = limit - _TOKEN_SAFETY_MARGIN
                elif scope == "ITPM":
                    candidate = 0  # the prompt itself is too big for this model
                else:
                    prompt_tokens = max(0, requested - sent_max)
                    candidate = limit - prompt_tokens - _TOKEN_SAFETY_MARGIN
                if settings.LLM_MIN_OUTPUT_TOKENS <= candidate < sent_max:
                    new_max = candidate
        wait: float | None = None
        retry = _RETRY_AFTER_RE.search(message)
        if retry and new_max is None:
            minutes, amount, unit = retry.groups()
            seconds = float(amount) / (1000.0 if unit.lower() == "ms" else 1.0)
            wait = seconds + 60.0 * int(minutes or 0)
        return new_max, wait

    async def _ainvoke_within_limits(self, model: Any, config: LLMModelConfig, prompt: str, task_type: str) -> Any:
        """
        One model call that adapts to per-minute token limits:
        shrink the answer budget when the request is too large, or wait the
        provider-advised delay when the minute budget is momentarily spent.
        Bounded to 2 adaptations; anything else propagates unchanged.
        """
        key = self._model_key(config)
        default_max = self._default_max_tokens(model)
        budget = self._output_budget(key, prompt, default_max)
        if budget == 0:
            raise RuntimeError(
                f"Request too large for {key} per-minute token limit (413): skipped before sending."
            )
        limiter = self._get_limiter(config)
        for adaptation in range(3):
            runnable = model.bind(max_tokens=budget) if budget else model
            try:
                async with limiter:
                    return await asyncio.wait_for(
                        runnable.ainvoke(prompt),
                        timeout=float(settings.LLM_REQUEST_TIMEOUT_SECONDS),
                    )
            except Exception as exc:
                if adaptation == 2:
                    raise
                new_max, wait = self._learn_from_limit_error(key, exc, budget or default_max)
                if new_max:
                    logger.info(
                        "[LLMProvider] shrinking max_tokens model=%s task_type=%s max_tokens=%s",
                        key, task_type, new_max,
                    )
                    budget = new_max
                    continue
                if wait is not None and 0 < wait <= float(settings.LLM_RATE_LIMIT_MAX_WAIT_SECONDS):
                    logger.info(
                        "[LLMProvider] rate limited, waiting model=%s task_type=%s seconds=%.1f",
                        key, task_type, wait,
                    )
                    await asyncio.sleep(wait + 0.25)
                    continue
                raise
        raise RuntimeError("unreachable")  # pragma: no cover

    @staticmethod
    def _error_kind(exc: Exception) -> str:
        message = str(exc).lower()
        # Request-scoped size problem: another (larger-limit) model may still
        # answer, but it must never open this model's shared circuit.
        if "request too large" in message or "413" in message:
            return "too_large"
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

    def _health_key(self, config: LLMModelConfig, *, structured: bool = False) -> str:
        # Meme logique de suffixe que _get_or_create_model : une sante
        # separee pour le mode structure, pour qu'un echec structurel
        # (ex. Groq refusant le tool calling) n'ouvre jamais le circuit
        # partage utilise par invoke() sur ce meme modele.
        key = self._model_key(config)
        return f"{key}:structured" if structured else key

    def _circuit_is_open(self, config: LLMModelConfig, *, structured: bool = False) -> bool:
        health = self._shared_health.setdefault(
            self._health_key(config, structured=structured), ProviderHealth()
        )
        return health.open_until > time.time()

    def _circuit_cause(self, config: LLMModelConfig, *, structured: bool = False) -> str:
        # "circuit_open:<kind>" keeps the original reason visible to callers.
        health = self._shared_health.get(self._health_key(config, structured=structured))
        return f"circuit_open:{(health.last_kind if health else '') or 'unknown'}"

    def _record_success(self, config: LLMModelConfig, *, structured: bool = False) -> None:
        health = self._shared_health.setdefault(
            self._health_key(config, structured=structured), ProviderHealth()
        )
        health.failures = 0
        health.open_until = 0.0

    def _record_failure(self, config: LLMModelConfig, kind: str, *, structured: bool = False) -> None:
        # "unknown" means ForgeAI has not established that the model or
        # provider itself is unhealthy.  The failure may be scoped only to
        # the current request, prompt, structured-output mode or task.
        #
        # Never promote an unscoped failure into shared model-global health.
        # The current invocation still fails normally and may continue
        # through the fallback chain; only proven provider/model-scoped
        # failures are eligible to poison the shared circuit.
        if kind in ("unknown", "too_large"):
            return

        health = self._shared_health.setdefault(
            self._health_key(config, structured=structured), ProviderHealth()
        )
        health.last_kind = kind
        health.failures += 1
        if kind == "configuration" or health.failures >= settings.LLM_CIRCUIT_FAILURES:
            health.open_until = time.time() + settings.LLM_CIRCUIT_COOLDOWN_SECONDS

    async def invoke(self, prompt: str, task_type: str = "general") -> str:
        if not str(prompt or "").strip():
            raise ValueError("Le prompt LLM ne peut pas être vide.")

        last_error: Optional[Exception] = None
        attempted = 0
        # model key -> failure kind, reported through LLMUnavailableError
        failures: dict[str, str] = {}

        for config in self.model_configs:
            key = self._model_key(config)
            if self._circuit_is_open(config):
                failures[key] = self._circuit_cause(config)
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
                response = await self._ainvoke_within_limits(model, config, prompt, task_type)

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
                failures[key] = kind
                self._record_failure(config, kind)
                logger.warning(
                    "[LLMProvider] failed model=%s task_type=%s kind=%s error_type=%s error=%s",
                    key,
                    task_type,
                    kind,
                    type(exc).__name__,
                    str(exc)[:1000],
                )
                # Always continue to the next configured provider. A configuration
                # error is visible in logs and opens the provider circuit, but does
                # not prevent Groq from keeping the analysis available.
                continue

        if attempted == 0:
            raise LLMUnavailableError(
                "Tous les circuits LLM configurés sont temporairement ouverts.",
                failures,
            )

        raise LLMUnavailableError(
            f"Tous les modèles LLM ont échoué. Dernière erreur : {last_error}",
            failures,
        ) from last_error

    async def invoke_structured(
        self,
        prompt: str,
        schema: type,
        task_type: str = "general",
    ) -> Any:
        """
        Comme ``invoke``, mais force la sortie a etre structurellement
        conforme au schema Pydantic donne, via l'appel de fonction natif
        du fournisseur (tool calling), pas une simple instruction textuelle
        esperant que le modele obeisse.

        Contrairement a ``invoke``, le contrat public existant reste
        totalement inchange : cette methode est purement additive, utilisee
        uniquement la ou un agent choisit explicitement de l'appeler.

        Leve la meme famille d'exceptions que ``invoke`` en cas d'echec sur
        tous les fournisseurs configures ; la boucle de circuit-breaker et
        de fallback est partagee et inchangee.
        """
        if not str(prompt or "").strip():
            raise ValueError("Le prompt LLM ne peut pas être vide.")

        last_error: Optional[Exception] = None
        attempted = 0
        failures: dict[str, str] = {}

        for config in self.model_configs:
            if not config.supports_structured:
                # Connu et permanent (ex. Groq compound-mini : "tool calling
                # is not supported with this model") - inutile de gaspiller
                # un aller-retour reseau garanti perdu d'avance.
                continue

            key = self._model_key(config)
            if self._circuit_is_open(config, structured=True):
                failures[key] = self._circuit_cause(config, structured=True)
                logger.warning(
                    "[LLMProvider] circuit_open model=%s task_type=%s", key, task_type
                )
                continue

            attempted += 1
            try:
                logger.info(
                    "[LLMProvider] trying model=%s task_type=%s mode=structured",
                    key,
                    task_type,
            )
                model = await self._get_or_create_model(config, structured=True)
                structured_model = model.with_structured_output(schema)
                limiter = self._get_limiter(config)
                async with limiter:
                    result = await asyncio.wait_for(
                        structured_model.ainvoke(prompt),
                        timeout=float(settings.LLM_REQUEST_TIMEOUT_SECONDS),
                    )

                if result is None:
                    raise RuntimeError(f"Réponse structurée vide depuis {key}")

                self._record_success(config, structured=True)
                logger.info(
                    "[LLMProvider] success model=%s task_type=%s mode=structured",
                    key,
                    task_type,
                )
                return result

            except Exception as exc:
                last_error = exc
                kind = self._error_kind(exc)
                failures[key] = kind
                self._record_failure(config, kind, structured=True)
                logger.warning(
                    "[LLMProvider] failed model=%s task_type=%s mode=structured kind=%s error_type=%s error=%s",
                    key,
                    task_type,
                    kind,
                    type(exc).__name__,
                    str(exc)[:1000],
                )
                continue

        if attempted == 0:
            raise LLMUnavailableError(
                "Tous les circuits LLM configurés sont temporairement ouverts.",
                failures,
            )

        raise LLMUnavailableError(
            f"Tous les modèles LLM (mode structuré) ont échoué. Dernière erreur : {last_error}",
            failures,
        ) from last_error






