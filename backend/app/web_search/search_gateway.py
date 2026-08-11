from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import settings
from app.web_search.providers.ddgs_provider import DDGSSearchProvider
from app.web_search.providers.gemini_grounded_provider import (
    GeminiGroundedSearchProvider,
)
from app.web_search.providers.tavily_provider import TavilySearchProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderState:
    failures: int = 0
    open_until: float = 0.0
    last_error: str = ""


@dataclass
class KeyLockEntry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


class SearchGateway:
    """Single resilient search entry point for ForgeAI.

    Provider order is configuration-driven. The gateway handles bounded
    concurrency, fallback, circuit breaking, cache de-duplication and URL
    canonicalization; source relevance and evidence truth remain downstream.
    """

    CACHE_SCHEMA_VERSION = "search_gateway_v3"
    MAX_MEMORY_CACHE_ENTRIES = 512

    # Provider health and cached results are shared by gateway instances in the
    # single-worker Docker profile. Event-loop-bound locks remain instance-local.
    _memory_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
    _states: dict[str, ProviderState] = {}

    def __init__(self) -> None:
        self.max_results_per_query = self._setting_int(
            "SEARCH_MAX_RESULTS_PER_QUERY",
            8,
            minimum=1,
            maximum=20,
        )
        self.providers = {
            "tavily": TavilySearchProvider(self.max_results_per_query),
            "ddgs": DDGSSearchProvider(self.max_results_per_query),
            "gemini_grounded": GeminiGroundedSearchProvider(
                self.max_results_per_query
            ),
        }
        self._provider_semaphores: dict[str, asyncio.Semaphore] = {}
        self._locks: dict[str, KeyLockEntry] = {}

    @classmethod
    def clear_runtime_state(cls) -> None:
        cls._memory_cache.clear()
        cls._states.clear()

    def provider_order(self) -> list[str]:
        requested = [
            str(
                getattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
                or "tavily"
            ).strip().lower(),
            str(
                getattr(settings, "SEARCH_FALLBACK_PROVIDER", "ddgs")
                or "ddgs"
            ).strip().lower(),
        ]
        order: list[str] = []
        for name in requested + ["tavily", "ddgs", "gemini_grounded"]:
            if name not in self.providers or name in order:
                continue
            if name == "ddgs" and not bool(
                getattr(settings, "ENABLE_DDGS_FALLBACK", True)
            ):
                continue
            provider = self.providers[name]
            if bool(getattr(provider, "enabled", True)):
                order.append(name)
        return order

    async def search(
        self,
        query: str,
        *,
        min_results: int | None = None,
        allow_gemini_fallback: bool = True,
        allow_fallback: bool = True,
        force_provider: str | None = None,
        bypass_cache: bool = False,
    ) -> list[dict[str, Any]]:
        normalized_query = " ".join(str(query or "").split())[:300]
        if not normalized_query:
            return []

        required = self._required_results(min_results)
        forced = str(force_provider or "").strip().lower()
        if forced:
            provider = self.providers.get(forced)
            if provider is None or not bool(getattr(provider, "enabled", True)):
                return []
            order = [forced]
        else:
            order = self.provider_order()
            if not allow_gemini_fallback:
                order = [name for name in order if name != "gemini_grounded"]

        if not allow_fallback and order:
            order = order[:1]
        if not order:
            return []

        key = self._cache_key(
            query=normalized_query,
            order=order,
            required=required,
            allow_fallback=allow_fallback,
            allow_gemini_fallback=allow_gemini_fallback,
            forced=forced,
        )

        async with self._locked_key(key):
            if not bypass_cache:
                cached = await self._cache_get(key)
                if cached is not None:
                    return cached[: self.max_results_per_query]

            results: list[dict[str, Any]] = []
            used: list[str] = []
            for name in order:
                provider = self.providers[name]
                if not bool(getattr(provider, "enabled", True)):
                    continue

                rows = await self._safe_provider_search(
                    provider,
                    normalized_query,
                )
                if rows:
                    used.append(name)
                    results.extend(rows)
                    results = self._dedupe(results)
                if len(results) >= required:
                    break

            results = results[: self.max_results_per_query]
            # A partial result can be caused by a temporary provider outage. Do
            # not let it suppress fallback/retry for the whole cache TTL.
            if len(results) >= required and not bypass_cache:
                await self._cache_set(key, results)

            logger.info(
                "[SearchGateway] query=%r results=%s providers=%s order=%s",
                normalized_query,
                len(results),
                used,
                order,
            )
            return results

    async def search_many(
        self,
        queries: list[str],
        *,
        min_results_per_query: int | None = None,
        concurrency: int = 3,
    ) -> list[dict[str, Any]]:
        bounded_concurrency = max(1, min(int(concurrency or 3), 6))
        semaphore = asyncio.Semaphore(bounded_concurrency)
        max_queries = self._setting_int(
            "SEARCH_MAX_QUERIES_PER_ANALYSIS",
            10,
            minimum=1,
            maximum=50,
        )

        normalized_queries: list[str] = []
        seen_queries: set[str] = set()
        for query in queries:
            clean = " ".join(str(query or "").split())[:300]
            key = clean.casefold()
            if not clean or key in seen_queries:
                continue
            seen_queries.add(key)
            normalized_queries.append(clean)
            if len(normalized_queries) >= max_queries:
                break

        async def one(query: str) -> list[dict[str, Any]]:
            async with semaphore:
                return await self.search(
                    query,
                    min_results=min_results_per_query,
                )

        groups = await asyncio.gather(
            *(one(query) for query in normalized_queries),
            return_exceptions=True,
        )
        rows: list[dict[str, Any]] = []
        for group in groups:
            if isinstance(group, Exception):
                logger.warning("[SearchGateway] search_many item failed: %s", group)
                continue
            rows.extend(group)
        return self._dedupe(rows)

    async def _safe_provider_search(
        self,
        provider: Any,
        query: str,
    ) -> list[dict[str, Any]]:
        name = str(getattr(provider, "name", "unknown"))
        state = self._states.setdefault(name, ProviderState())
        now = time.time()
        if state.open_until > now:
            logger.warning(
                "[SearchGateway] circuit_open provider=%s remaining_seconds=%s last_error=%s",
                name,
                round(state.open_until - now, 1),
                state.last_error[:240],
            )
            return []

        limit = 3
        if name == "tavily":
            limit = self._setting_int(
                "TAVILY_MAX_CONCURRENT_REQUESTS",
                3,
                minimum=1,
                maximum=10,
            )
        semaphore = self._provider_semaphores.setdefault(
            name,
            asyncio.Semaphore(limit),
        )
        timeout = max(
            1.0,
            self._setting_float("SEARCH_PROVIDER_TIMEOUT_SECONDS", 35.0) + 2.0,
        )

        try:
            async with semaphore:
                raw_rows = await asyncio.wait_for(
                    provider.search(query),
                    timeout=timeout,
                )

            rows = raw_rows if isinstance(raw_rows, list) else []
            state.failures = 0
            state.open_until = 0.0
            state.last_error = ""
            return [row for row in rows if isinstance(row, dict)]
        except Exception as exc:
            state.failures += 1
            message = str(exc)
            lower_message = message.lower()
            retry_after = getattr(exc, "retry_after_seconds", None)
            status_code = self._status_code(exc)
            failure_limit = self._setting_int(
                "SEARCH_CIRCUIT_FAILURES",
                2,
                minimum=1,
                maximum=20,
            )
            should_open = (
                state.failures >= failure_limit
                or status_code in {401, 403, 429, 432, 433}
                or any(
                    marker in lower_message
                    for marker in (
                        "429",
                        "403",
                        "432",
                        "433",
                        "rate limit",
                        "quota",
                        "usage limit",
                        "resource exhausted",
                        "permission",
                        "invalid api key",
                        "unauthorized",
                    )
                )
            )
            if should_open:
                cooldown = self._setting_float(
                    "SEARCH_CIRCUIT_COOLDOWN_SECONDS",
                    900.0,
                )
                if retry_after is not None:
                    try:
                        cooldown = max(cooldown, float(retry_after))
                    except (TypeError, ValueError):
                        pass
                state.open_until = time.time() + max(1.0, cooldown)

            state.last_error = message
            logger.warning(
                "[SearchGateway] provider=%s failed status=%s error=%s",
                name,
                status_code,
                message[:800],
            )
            return []

    @asynccontextmanager
    async def _locked_key(self, key: str) -> AsyncIterator[None]:
        entry = self._locks.get(key)
        if entry is None:
            entry = KeyLockEntry()
            self._locks[key] = entry
        entry.users += 1

        try:
            async with entry.lock:
                yield
        finally:
            entry.users -= 1
            if entry.users <= 0:
                self._locks.pop(key, None)

    async def _cache_get(self, key: str) -> list[dict[str, Any]] | None:
        now = time.time()
        self._prune_memory_cache(now)
        local = self._memory_cache.get(key)
        if local and local[0] > now:
            return [dict(item) for item in local[1]]

        redis_url = str(getattr(settings, "REDIS_URL", "") or "").strip()
        if not redis_url:
            return None

        try:
            import redis.asyncio as redis

            client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            try:
                value = await asyncio.wait_for(
                    client.get(f"forgeai:search:{key}"),
                    timeout=2.0,
                )
            finally:
                await client.aclose()
            if value:
                decoded = json.loads(value)
                rows = self._validated_cached_rows(decoded)
                if rows:
                    ttl = self._cache_ttl()
                    self._memory_cache[key] = (now + ttl, rows)
                    return [dict(item) for item in rows]
        except Exception:
            logger.debug("[SearchGateway] Redis cache unavailable", exc_info=True)
        return None

    async def _cache_set(self, key: str, rows: list[dict[str, Any]]) -> None:
        safe_rows = self._validated_cached_rows(rows)
        if not safe_rows:
            return

        ttl = self._cache_ttl()
        now = time.time()
        self._prune_memory_cache(now)
        self._memory_cache[key] = (now + ttl, safe_rows)
        redis_url = str(getattr(settings, "REDIS_URL", "") or "").strip()
        if not redis_url:
            return

        try:
            import redis.asyncio as redis

            client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            try:
                await asyncio.wait_for(
                    client.setex(
                        f"forgeai:search:{key}",
                        ttl,
                        json.dumps(safe_rows, ensure_ascii=False, default=str),
                    ),
                    timeout=2.0,
                )
            finally:
                await client.aclose()
        except Exception:
            logger.debug(
                "[SearchGateway] Redis cache write unavailable",
                exc_info=True,
            )

    def _cache_key(
        self,
        *,
        query: str,
        order: list[str],
        required: int,
        allow_fallback: bool,
        allow_gemini_fallback: bool,
        forced: str,
    ) -> str:
        material = json.dumps(
            {
                "schema": self.CACHE_SCHEMA_VERSION,
                "query": query.lower(),
                "providers": order,
                "required": required,
                "max_results": self.max_results_per_query,
                "allow_fallback": allow_fallback,
                "allow_gemini_fallback": allow_gemini_fallback,
                "forced": forced,
                "tavily_depth": str(
                    getattr(settings, "TAVILY_SEARCH_DEPTH", "basic")
                ),
                "tavily_raw": bool(
                    getattr(settings, "TAVILY_INCLUDE_RAW_CONTENT", False)
                ),
                "tavily_safe": bool(
                    getattr(settings, "TAVILY_SAFE_SEARCH", False)
                ),
                "tavily_min_score": self._setting_float(
                    "TAVILY_MIN_SCORE",
                    0.35,
                ),
            },
            sort_keys=True,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @classmethod
    def _dedupe(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        best: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            canonical = cls._canonical_url(str(row.get("url") or ""))
            if not canonical:
                continue

            normalized = dict(row)
            normalized["url"] = canonical
            previous = best.get(canonical)
            if previous is None or cls._row_rank(normalized) > cls._row_rank(previous):
                best[canonical] = normalized

        return sorted(
            best.values(),
            key=cls._row_rank,
            reverse=True,
        )

    @classmethod
    def _row_rank(cls, row: dict[str, Any]) -> tuple[int, float, int]:
        return (
            1 if bool(row.get("grounded")) else 0,
            cls._safe_float(row.get("provider_score"), 0.0),
            len(str(row.get("snippet") or "")),
        )

    @staticmethod
    def _safe_float(value: Any, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        for value in (
            getattr(exc, "status_code", None),
            getattr(exc, "code", None),
            getattr(getattr(exc, "response", None), "status_code", None),
        ):
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _canonical_url(url: str) -> str:
        try:
            parsed = urlparse(url.strip())
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
                return ""
            if parsed.username or parsed.password:
                return ""

            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]

            filtered_query = sorted(
                (
                    (key, value)
                    for key, value in parse_qsl(
                        parsed.query,
                        keep_blank_values=False,
                    )
                    if key.lower()
                    not in {
                        "utm_source",
                        "utm_medium",
                        "utm_campaign",
                        "utm_term",
                        "utm_content",
                        "utm_id",
                        "gclid",
                        "fbclid",
                        "mc_cid",
                        "mc_eid",
                    }
                ),
                key=lambda pair: (pair[0].lower(), pair[1]),
            )
            path = parsed.path.rstrip("/") or "/"
            return urlunparse(
                (
                    parsed.scheme.lower(),
                    netloc,
                    path,
                    "",
                    urlencode(filtered_query),
                    "",
                )
            )
        except Exception:
            return ""

    @classmethod
    def _validated_cached_rows(cls, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return cls._dedupe(
            [dict(item) for item in value if isinstance(item, dict)]
        )

    @classmethod
    def _prune_memory_cache(cls, now: float) -> None:
        expired = [key for key, value in cls._memory_cache.items() if value[0] <= now]
        for key in expired:
            cls._memory_cache.pop(key, None)

        overflow = len(cls._memory_cache) - cls.MAX_MEMORY_CACHE_ENTRIES
        if overflow > 0:
            oldest = sorted(
                cls._memory_cache.items(),
                key=lambda item: item[1][0],
            )[:overflow]
            for key, _value in oldest:
                cls._memory_cache.pop(key, None)

    def _required_results(self, value: int | None) -> int:
        raw = value
        if raw is None:
            raw = getattr(settings, "SEARCH_MIN_RESULTS", 4)
        try:
            parsed = int(raw or 4)
        except (TypeError, ValueError):
            parsed = 4
        return max(1, min(parsed, self.max_results_per_query))

    @staticmethod
    def _setting_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            value = int(getattr(settings, name, default) or default)
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(value, maximum))

    @staticmethod
    def _setting_float(name: str, default: float) -> float:
        try:
            return float(getattr(settings, name, default) or default)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _cache_ttl() -> int:
        try:
            ttl = int(getattr(settings, "SEARCH_CACHE_TTL_SECONDS", 21600) or 21600)
        except (TypeError, ValueError):
            ttl = 21600
        return max(1, min(ttl, 86400))


search_gateway = SearchGateway()
