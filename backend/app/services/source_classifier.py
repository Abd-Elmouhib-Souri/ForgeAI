from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, Iterable, List

from app.config import settings

logger = logging.getLogger(__name__)


_ALLOWED_TYPES = {
    "direct_competitor",
    "adjacent_solution",
    "technology_benchmark",
    "market_evidence",
    "market_article",
    "official_source",
    "directory",
    "local_ecosystem",
    "irrelevant",
}


class SourceClassifier:
    """Optional AI classification layer with deterministic final fallback.

    Search remains DDGS/Gemini Grounded. This service only classifies already
    discovered pages. The AI output is advisory: SourceRelevanceGate still
    applies deterministic target, workflow, sector and evidence checks before a
    source can become public.
    """

    async def classify_sources(
        self,
        sources: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not sources:
            return []

        limit = max(1, min(int(settings.SEARCH_CLASSIFIER_MAX_SOURCES), 20))
        selected = [dict(item) for item in sources[:limit]]
        remainder = [dict(item) for item in sources[limit:]]

        if not settings.ENABLE_AI_SOURCE_CLASSIFIER:
            return [self._with_deterministic(item) for item in selected] + remainder

        providers = self._provider_order()
        last_error = ""
        for provider in providers:
            try:
                if provider == "gemini":
                    result = await self._classify_gemini(selected, project_context)
                elif provider == "groq":
                    result = await self._classify_groq(selected, project_context)
                else:
                    continue
                merged = self._merge(selected, result, provider)
                logger.info(
                    "[SourceClassifier] provider=%s classified=%s",
                    provider,
                    len(merged),
                )
                return merged + remainder
            except Exception as exc:  # pragma: no cover - provider/network path
                last_error = str(exc)
                logger.warning(
                    "[SourceClassifier] provider=%s failed error=%s",
                    provider,
                    last_error[:500],
                )

        rows = [self._with_deterministic(item) for item in selected]
        if last_error:
            for row in rows:
                row["classifier_error"] = last_error[:300]
        return rows + remainder

    def _provider_order(self) -> List[str]:
        requested = [
            str(settings.SEARCH_CLASSIFIER_PRIMARY or "gemini").strip().lower(),
            str(settings.SEARCH_CLASSIFIER_FALLBACK or "groq").strip().lower(),
        ]
        order: List[str] = []
        for provider in requested:
            if provider not in {"gemini", "groq"} or provider in order:
                continue
            if provider == "gemini" and not settings.GEMINI_SEARCH_CLASSIFIER_API_KEY:
                continue
            if provider == "groq" and not settings.GROQ_API_KEY:
                continue
            order.append(provider)
        return order

    async def _classify_gemini(
        self,
        sources: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        from google import genai  # lazy import

        client = genai.Client(api_key=settings.GEMINI_SEARCH_CLASSIFIER_API_KEY)
        prompt = self._prompt(sources, context)

        def call() -> Any:
            return client.models.generate_content(
                model=settings.GEMINI_SEARCH_CLASSIFIER_MODEL,
                contents=prompt,
            )

        response = await asyncio.wait_for(
            asyncio.to_thread(call),
            timeout=float(settings.SEARCH_CLASSIFIER_TIMEOUT_SECONDS),
        )
        text = str(getattr(response, "text", "") or "")
        return self._parse(text)

    async def _classify_groq(
        self,
        sources: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        from groq import AsyncGroq  # lazy import

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        completion = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.GROQ_MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": "Return only valid JSON. Never invent facts or companies.",
                    },
                    {"role": "user", "content": self._prompt(sources, context)},
                ],
            ),
            timeout=float(settings.SEARCH_CLASSIFIER_TIMEOUT_SECONDS),
        )
        text = completion.choices[0].message.content or ""
        return self._parse(text)

    def _prompt(
        self,
        sources: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        structured = (
            context.get("structured_project_context")
            or (context.get("project_intelligence") or {}).get("structured_project_context")
            or context
        )
        compact_sources = []
        for index, source in enumerate(sources):
            compact_sources.append(
                {
                    "index": index,
                    "title": str(source.get("title") or "")[:180],
                    "url": str(source.get("url") or source.get("href") or "")[:300],
                    "snippet": str(source.get("snippet") or source.get("body") or "")[:500],
                    "preview": str(source.get("extracted_text_preview") or "")[:900],
                }
            )
        packet = {
            "project": {
                "sector": structured.get("sector") or structured.get("industry"),
                "region": structured.get("target_region") or structured.get("market_region"),
                "target_users": structured.get("target_users"),
                "problem": structured.get("problem"),
                "solution": structured.get("solution"),
                "priority_workflows": structured.get("priority_workflows")
                or structured.get("use_cases"),
            },
            "sources": compact_sources,
        }
        return (
            "Classify each source for this exact project. A shared keyword alone "
            "does not create a competitor. Editorial pages are never products. "
            "Do not mark a source irrelevant merely because it is not a direct "
            "competitor: a local sector page may be market_evidence or "
            "local_ecosystem, and a product serving a nearby workflow may be an "
            "adjacent_solution. A technology page may be a technology_benchmark. "
            "Use direct_competitor only for a real product serving the same target "
            "and workflow in the launch market. Use one type from: "
            "direct_competitor, adjacent_solution, technology_benchmark, "
            "market_evidence, market_article, official_source, directory, "
            "local_ecosystem, irrelevant. Return a JSON array with index, "
            "source_type, confidence (0..1), same_target, same_workflow, "
            "same_sector, product_page, reason.\n"
            + json.dumps(packet, ensure_ascii=False)
        )

    def _parse(self, text: str) -> List[Dict[str, Any]]:
        cleaned = str(text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start < 0 or end < start:
            raise ValueError("Classifier response does not contain a JSON array")
        value = json.loads(cleaned[start : end + 1])
        if not isinstance(value, list):
            raise ValueError("Classifier response must be a JSON array")
        return [item for item in value if isinstance(item, dict)]

    def _merge(
        self,
        sources: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]],
        provider: str,
    ) -> List[Dict[str, Any]]:
        by_index: Dict[int, Dict[str, Any]] = {}
        for item in decisions:
            try:
                index = int(item.get("index"))
            except (TypeError, ValueError):
                continue
            by_index[index] = item

        result: List[Dict[str, Any]] = []
        for index, source in enumerate(sources):
            row = dict(source)
            decision = by_index.get(index)
            if not decision:
                result.append(self._with_deterministic(row))
                continue
            source_type = str(decision.get("source_type") or "irrelevant").strip().lower()
            if source_type not in _ALLOWED_TYPES:
                source_type = "irrelevant"
            row.update(
                {
                    "ai_source_type": source_type,
                    "ai_classifier_confidence": self._number(
                        decision.get("confidence"), 0.0
                    ),
                    "ai_same_target": bool(decision.get("same_target")),
                    "ai_same_workflow": bool(decision.get("same_workflow")),
                    "ai_same_sector": bool(decision.get("same_sector")),
                    "ai_product_page": bool(decision.get("product_page")),
                    "ai_classifier_reason": str(decision.get("reason") or "")[:500],
                    "classifier_provider": provider,
                }
            )
            result.append(row)
        return result

    def _with_deterministic(self, source: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(source)
        url = str(row.get("url") or row.get("href") or "").lower()
        text = " ".join(
            str(row.get(key) or "").lower()
            for key in ("title", "snippet", "body", "extracted_text_preview")
        )
        article = any(
            marker in url
            for marker in (
                "/blog/",
                "/article/",
                "/news/",
                "/journal/",
                "/guide/",
                "/resources/",
                "/report/",
            )
        )
        product_signals = sum(
            signal in text
            for signal in (
                "pricing",
                "free trial",
                "sign up",
                "book a demo",
                "dashboard",
                "features",
                "customers",
            )
        )
        ecosystem_signals = sum(
            signal in text
            for signal in (
                "ecosystem",
                "startup program",
                "innovation program",
                "incubator",
                "accelerator",
                "investors",
                "startups",
                "appel à projets",
            )
        )
        if article and ecosystem_signals >= 2:
            source_type = "local_ecosystem"
        elif article:
            source_type = "market_article"
        elif product_signals >= 2:
            source_type = "adjacent_solution"
        else:
            source_type = "market_evidence"
        row.update(
            {
                "ai_source_type": source_type,
                "ai_classifier_confidence": 0.45,
                "ai_classifier_reason": "Deterministic classifier fallback.",
                "classifier_provider": "deterministic",
            }
        )
        return row

    @staticmethod
    def _number(value: Any, default: float) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default


source_classifier = SourceClassifier()