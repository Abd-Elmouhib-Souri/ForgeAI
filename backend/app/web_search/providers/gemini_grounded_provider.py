from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiGroundedSearchError(RuntimeError):
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


class GeminiGroundedSearchProvider:
    """Optional Google Search grounding provider for URL discovery.

    The provider only emits cited public URLs and grounding metadata. Relevance,
    source roles and claim verification remain downstream responsibilities.
    """

    name = "gemini_grounded"

    def __init__(self, max_results: int = 8) -> None:
        self.max_results = max(1, min(int(max_results or 8), 12))

    @property
    def enabled(self) -> bool:
        return bool(
            str(getattr(settings, "GEMINI_API_KEY", "") or "").strip()
            and getattr(settings, "ENABLE_GEMINI_GROUNDED_SEARCH", False)
            and str(getattr(settings, "GEMINI_SEARCH_MODEL", "") or "").strip()
        )

    async def search(self, query: str) -> list[dict[str, Any]]:
        normalized_query = " ".join(str(query or "").split())[:300]
        if not normalized_query or not self.enabled:
            return []
        return await asyncio.to_thread(self._search_sync, normalized_query)

    def _search_sync(self, query: str) -> list[dict[str, Any]]:
        try:
            from google import genai
            from google.genai import types
        except Exception as exc:
            raise GeminiGroundedSearchError(
                f"google-genai dependency unavailable: {type(exc).__name__}"
            ) from exc

        timeout_ms = int(
            max(
                1.0,
                float(
                    getattr(settings, "SEARCH_PROVIDER_TIMEOUT_SECONDS", 35)
                    or 35
                ),
            )
            * 1000
        )
        api_key = str(getattr(settings, "GEMINI_API_KEY", "") or "").strip()
        model = str(
            getattr(settings, "GEMINI_SEARCH_MODEL", "") or ""
        ).strip()

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
        except TypeError:
            # Compatibility with older google-genai releases.
            client = genai.Client(api_key=api_key)

        prompt = f"""
You are the web-research discovery layer for ForgeAI.

Find public sources for this exact business-research query:
{query}

Priorities, in order:
1. official company product or pricing pages;
2. government, ministry, national statistics or recognised institutions;
3. peer-reviewed or reputable research;
4. credible sector reports and professional publications.

Rules:
- Search the live web.
- Never invent a URL, company, statistic or citation.
- Prefer pages whose title and content directly answer the query.
- Avoid generic homepages, social networks, scraped directories and unrelated pages.
- Return a concise grounded answer; ForgeAI will read the grounding citations.
""".strip()

        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
        except Exception as exc:
            raise self._structured_error(exc) from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    logger.debug(
                        "[GeminiGrounded] client close failed",
                        exc_info=True,
                    )

        return self._normalize_response(response=response, query=query)

    def _normalize_response(
        self,
        *,
        response: Any,
        query: str,
    ) -> list[dict[str, Any]]:
        candidates = getattr(response, "candidates", None) or []
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        search_entry_html = ""

        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            if metadata is None:
                continue

            search_queries = [
                str(item).strip()
                for item in (getattr(metadata, "web_search_queries", None) or [])
                if str(item).strip()
            ]
            entry_point = getattr(metadata, "search_entry_point", None)
            rendered_content = str(
                getattr(entry_point, "rendered_content", "") or ""
            ).strip()
            if rendered_content and not search_entry_html:
                search_entry_html = rendered_content[:20000]

            chunks = getattr(metadata, "grounding_chunks", None) or []
            supports = getattr(metadata, "grounding_supports", None) or []

            snippets_by_chunk: dict[int, list[str]] = {}
            for support in supports:
                segment = getattr(support, "segment", None)
                segment_text = str(getattr(segment, "text", "") or "").strip()
                indices = getattr(support, "grounding_chunk_indices", None) or []
                for index in indices:
                    try:
                        numeric_index = int(index)
                    except (TypeError, ValueError):
                        continue
                    if segment_text:
                        snippets_by_chunk.setdefault(numeric_index, []).append(
                            segment_text
                        )

            for index, chunk in enumerate(chunks):
                web = getattr(chunk, "web", None)
                url = str(getattr(web, "uri", "") or "").strip()
                title = str(getattr(web, "title", "") or "").strip()
                if not url or url in seen:
                    continue

                seen.add(url)
                snippet_parts: list[str] = []
                for item in snippets_by_chunk.get(index, []):
                    if item and item not in snippet_parts:
                        snippet_parts.append(item)
                snippet = " ".join(snippet_parts).strip()
                host = (urlparse(url).hostname or "").lower()

                rows.append(
                    {
                        "title": title or url,
                        "url": url,
                        "snippet": snippet
                        or "Cited by Gemini Grounding with Google Search.",
                        "provider": self.name,
                        "provider_score": 0.0,
                        "search_query": query,
                        "provider_search_queries": search_queries,
                        "grounded": True,
                        "grounding_redirect": (
                            "vertexaisearch.cloud.google.com" in host
                            or "grounding-api-redirect" in url
                        ),
                    }
                )
                if len(rows) >= self.max_results:
                    break

            if len(rows) >= self.max_results:
                break

        if rows and search_entry_html:
            rows[0]["google_search_suggestions_html"] = search_entry_html

        if not rows:
            logger.warning(
                "[GeminiGrounded] no grounding citations returned query=%r",
                query,
            )
        return rows

    @classmethod
    def _structured_error(cls, exc: Exception) -> GeminiGroundedSearchError:
        status_code = cls._extract_status_code(exc)
        response = getattr(exc, "response", None)
        retry_after = cls._retry_after_seconds(response)
        message = (
            "Gemini grounded search failure: "
            f"{type(exc).__name__}: {str(exc)[:500]}"
        )
        return GeminiGroundedSearchError(
            message,
            status_code=status_code,
            retry_after_seconds=retry_after,
        )

    @staticmethod
    def _extract_status_code(exc: Exception) -> int | None:
        symbolic = {
            "UNAUTHENTICATED": 401,
            "PERMISSION_DENIED": 403,
            "RESOURCE_EXHAUSTED": 429,
            "DEADLINE_EXCEEDED": 504,
            "UNAVAILABLE": 503,
        }
        for raw in (
            getattr(exc, "status_code", None),
            getattr(exc, "code", None),
            getattr(getattr(exc, "response", None), "status_code", None),
        ):
            if raw is None:
                continue
            try:
                return int(raw)
            except (TypeError, ValueError):
                name = str(getattr(raw, "name", raw) or "").upper()
                if name in symbolic:
                    return symbolic[name]
        return None

    @staticmethod
    def _retry_after_seconds(response: Any) -> float | None:
        headers = getattr(response, "headers", None)
        if not headers:
            return None
        raw = headers.get("retry-after") or headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            pass
        try:
            retry_at = parsedate_to_datetime(str(raw))
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(
                0.0,
                (retry_at - datetime.now(timezone.utc)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None
