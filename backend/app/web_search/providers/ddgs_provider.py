from __future__ import annotations

import asyncio
from typing import Any

from app.config import settings

try:
    from ddgs import DDGS as _DDGS
except Exception as import_error:  # optional runtime dependency
    _DDGS = None
    _DDGS_IMPORT_ERROR: Exception | None = import_error
else:
    _DDGS_IMPORT_ERROR = None


class DDGSSearchError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds

    def __str__(self) -> str:
        return self.message


class DDGSSearchProvider:
    """Best-effort, no-key fallback provider for public URL discovery."""

    name = "ddgs"

    def __init__(self, max_results: int = 8) -> None:
        self.max_results = max(1, min(int(max_results or 8), 12))

    @property
    def enabled(self) -> bool:
        return bool(
            getattr(settings, "ENABLE_DDGS_FALLBACK", True)
            and _DDGS is not None
        )

    async def search(self, query: str) -> list[dict[str, Any]]:
        normalized_query = " ".join(str(query or "").split())[:300]
        if not normalized_query or not self.enabled:
            return []
        return await asyncio.to_thread(self._search_sync, normalized_query)

    def _search_sync(self, query: str) -> list[dict[str, Any]]:
        if _DDGS is None:
            detail = (
                type(_DDGS_IMPORT_ERROR).__name__
                if _DDGS_IMPORT_ERROR
                else "missing"
            )
            raise DDGSSearchError(f"DDGS dependency unavailable: {detail}")

        timeout = max(
            1,
            min(
                int(
                    getattr(settings, "SEARCH_PROVIDER_TIMEOUT_SECONDS", 35)
                    or 35
                ),
                120,
            ),
        )
        region = str(
            getattr(settings, "DDGS_REGION", "us-en") or "us-en"
        ).strip()
        safesearch = str(
            getattr(settings, "DDGS_SAFESEARCH", "moderate") or "moderate"
        ).strip().lower()
        if safesearch not in {"on", "moderate", "off"}:
            safesearch = "moderate"
        backend = str(
            getattr(settings, "DDGS_BACKEND", "auto") or "auto"
        ).strip()

        try:
            client = _DDGS(timeout=timeout)
            raw_rows = client.text(
                query,
                region=region,
                safesearch=safesearch,
                max_results=self.max_results,
                backend=backend,
            )
        except Exception as exc:
            raise DDGSSearchError(
                f"DDGS search failure: {type(exc).__name__}: {str(exc)[:300]}"
            ) from exc

        return self._normalize_rows(raw_rows, query)

    def _normalize_rows(
        self,
        raw_rows: Any,
        query: str,
    ) -> list[dict[str, Any]]:
        if not isinstance(raw_rows, (list, tuple)):
            try:
                raw_rows = list(raw_rows or [])
            except TypeError:
                return []

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_rows:
            if not isinstance(item, dict):
                continue

            url = str(item.get("href") or item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)

            title = str(item.get("title") or "").strip()
            snippet = str(item.get("body") or item.get("snippet") or "").strip()
            rows.append(
                {
                    "title": title or url,
                    "url": url,
                    "snippet": snippet,
                    "provider": self.name,
                    "provider_score": 0.0,
                    "search_query": query,
                    "grounded": False,
                }
            )
            if len(rows) >= self.max_results:
                break

        return rows
