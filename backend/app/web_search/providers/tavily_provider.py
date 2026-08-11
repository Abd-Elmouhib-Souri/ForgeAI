from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.config import settings


class TavilySearchError(RuntimeError):
    """Structured Tavily failure used by SearchGateway circuit breaking."""

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
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.retry_after_seconds is not None:
            parts.append(f"retry_after={self.retry_after_seconds}")
        return " | ".join(parts)


class TavilySearchProvider:
    """Primary search provider using Tavily's REST Search API."""

    name = "tavily"

    def __init__(self, max_results: int = 8) -> None:
        configured = int(
            getattr(settings, "TAVILY_MAX_RESULTS", max_results) or max_results
        )
        self.max_results = max(1, min(configured, 20))
        self.endpoint = str(
            getattr(settings, "TAVILY_SEARCH_URL", "https://api.tavily.com/search")
            or "https://api.tavily.com/search"
        ).strip()

    @property
    def enabled(self) -> bool:
        return bool(
            getattr(settings, "ENABLE_TAVILY_SEARCH", True)
            and str(getattr(settings, "TAVILY_API_KEY", "") or "").strip()
        )

    async def search(self, query: str) -> list[dict[str, Any]]:
        normalized_query = " ".join(str(query or "").split())[:300]
        if not normalized_query or not self.enabled:
            return []

        depth = str(
            getattr(settings, "TAVILY_SEARCH_DEPTH", "basic") or "basic"
        ).strip().lower()
        if depth not in {"basic", "advanced", "fast", "ultra-fast"}:
            depth = "basic"

        payload: dict[str, Any] = {
            "query": normalized_query,
            "search_depth": depth,
            "max_results": self.max_results,
            "topic": "general",
            "include_answer": False,
            "include_raw_content": bool(
                getattr(settings, "TAVILY_INCLUDE_RAW_CONTENT", False)
            ),
            "include_images": False,
            "include_favicon": False,
            "include_usage": True,
        }

        # Tavily's Search contract accepts chunks_per_source for fast and
        # advanced depth. Basic and ultra-fast return generic content instead.
        if depth in {"advanced", "fast"}:
            payload["chunks_per_source"] = max(
                1,
                min(
                    int(
                        getattr(settings, "TAVILY_CHUNKS_PER_SOURCE", 2)
                        or 2
                    ),
                    3,
                ),
            )

        if bool(getattr(settings, "TAVILY_SAFE_SEARCH", False)):
            payload["safe_search"] = True

        api_key = str(getattr(settings, "TAVILY_API_KEY", "") or "").strip()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ForgeAI/1.0 TavilySearchProvider",
        }
        timeout_seconds = max(
            1.0,
            float(
                getattr(settings, "SEARCH_PROVIDER_TIMEOUT_SECONDS", 35)
                or 35
            ),
        )
        timeout = httpx.Timeout(
            timeout_seconds,
            connect=min(10.0, timeout_seconds),
        )

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise TavilySearchError(
                f"Tavily network failure: {type(exc).__name__}"
            ) from exc

        if response.status_code >= 400:
            raise TavilySearchError(
                self._error_detail(response) or "Tavily search request failed",
                status_code=response.status_code,
                retry_after_seconds=self._retry_after_seconds(response),
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise TavilySearchError(
                "Tavily returned invalid JSON",
                status_code=response.status_code,
            ) from exc

        return self._normalize_response(body=body, query=normalized_query)

    def _normalize_response(
        self,
        *,
        body: Any,
        query: str,
    ) -> list[dict[str, Any]]:
        if not isinstance(body, dict):
            return []

        min_score = max(
            0.0,
            min(
                float(getattr(settings, "TAVILY_MIN_SCORE", 0.35) or 0.35),
                1.0,
            ),
        )
        request_id = str(body.get("request_id") or "").strip()
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        rows: list[dict[str, Any]] = []

        for item in body.get("results") or []:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            content = str(item.get("content") or "").strip()
            raw_content = str(item.get("raw_content") or "").strip()
            published_date = str(item.get("published_date") or "").strip()
            try:
                provider_score = float(item.get("score") or 0.0)
            except (TypeError, ValueError):
                provider_score = 0.0

            if not url or provider_score < min_score:
                continue

            row = {
                "title": title or url,
                "url": url,
                "snippet": content or raw_content[:1200],
                "raw_content": raw_content[:6000] if raw_content else "",
                "provider": self.name,
                "provider_score": round(provider_score, 6),
                "search_query": query,
                "grounded": False,
                "tavily_request_id": request_id,
                "tavily_credits": usage.get("credits"),
            }
            if published_date:
                row["published_date"] = published_date
            rows.append(row)

        rows.sort(
            key=lambda row: float(row.get("provider_score") or 0.0),
            reverse=True,
        )
        return rows[: self.max_results]

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        raw = response.headers.get("retry-after")
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            pass

        try:
            retry_at = parsedate_to_datetime(raw)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(
                0.0,
                (retry_at - datetime.now(timezone.utc)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return str(response.text or "")[:500]

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, dict):
                return str(detail.get("error") or detail)[:500]
            return str(payload.get("error") or detail or payload)[:500]
        return str(payload)[:500]
