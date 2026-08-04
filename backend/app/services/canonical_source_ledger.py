from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse, urlunparse


class CanonicalSourceLedger:
    """Build the single source ledger consumed by every report section.

    A source receives exactly one canonical category:
    - direct_competitor
    - adjacent_solution
    - technology_benchmark
    - market_evidence
    - ecosystem_actor
    - irrelevant

    ``source_role`` remains available for finer presentation buckets such as
    regional benchmark, technology provider or official evidence. This avoids
    the old contradiction where the same page appeared as a supplier in one
    section and as a market source in another.
    """

    ALLOWED_CATEGORIES = {
        "direct_competitor",
        "adjacent_solution",
        "technology_benchmark",
        "market_evidence",
        "ecosystem_actor",
        "irrelevant",
    }

    ROLE_TO_CATEGORY = {
        "direct_competitor": "direct_competitor",
        "adjacent_solution": "adjacent_solution",
        "regional_benchmark": "technology_benchmark",
        "international_benchmark": "technology_benchmark",
        "technology_provider": "technology_benchmark",
        "market_evidence": "market_evidence",
        "official_evidence": "market_evidence",
        "directory": "market_evidence",
        "local_ecosystem": "ecosystem_actor",
        "irrelevant": "irrelevant",
    }

    ROLE_BUCKETS = {
        "direct_competitor": "local_direct_competitor_sources",
        "adjacent_solution": "adjacent_solution_sources",
        "regional_benchmark": "regional_benchmark_sources",
        "international_benchmark": "international_benchmark_sources",
        "technology_provider": "technology_provider_sources",
        "market_evidence": "market_context_sources",
        "official_evidence": "official_source_items",
        "local_ecosystem": "local_ecosystem_sources",
        "directory": "directory_sources",
    }

    CATEGORY_BUCKETS = {
        "direct_competitor": "direct_competitor_sources",
        "adjacent_solution": "adjacent_solution_sources",
        "technology_benchmark": "technology_benchmark_sources",
        "market_evidence": "market_evidence_sources",
        "ecosystem_actor": "ecosystem_actor_sources",
        "irrelevant": "irrelevant_sources",
    }

    def build(self, sources: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        canonical: List[Dict[str, Any]] = []
        by_key: Dict[str, Dict[str, Any]] = {}

        for raw in sources or []:
            if not isinstance(raw, dict):
                continue
            item = self._normalize_item(raw)
            if item["canonical_category"] == "irrelevant":
                continue

            key = self._source_key(item)
            if not key:
                continue
            item.setdefault("canonical_source_id", self._source_id(key))

            existing = by_key.get(key)
            if existing is None:
                by_key[key] = item
                canonical.append(item)
                continue

            if self._quality(item) > self._quality(existing):
                index = canonical.index(existing)
                canonical[index] = item
                by_key[key] = item

        canonical.sort(key=self._quality, reverse=True)

        role_buckets: Dict[str, List[Dict[str, Any]]] = {
            name: [] for name in self.ROLE_BUCKETS.values()
        }
        category_buckets: Dict[str, List[Dict[str, Any]]] = {
            name: [] for name in self.CATEGORY_BUCKETS.values()
        }

        for item in canonical:
            role = str(item.get("source_role") or "irrelevant").lower()
            role_bucket = self.ROLE_BUCKETS.get(role)
            if role_bucket:
                role_buckets[role_bucket].append(item)

            category = str(item.get("canonical_category") or "irrelevant").lower()
            category_bucket = self.CATEGORY_BUCKETS.get(category)
            if category_bucket:
                category_buckets[category_bucket].append(item)

        # Compatibility aliases retain the existing API contract.
        role_buckets["adjacent_solution_sources"] = self._unique_by_id(
            category_buckets["adjacent_solution_sources"]
        )

        evidence_sources = self._unique_by_id(
            category_buckets["market_evidence_sources"]
            + category_buckets["ecosystem_actor_sources"]
        )
        benchmark_sources = self._unique_by_id(
            category_buckets["technology_benchmark_sources"]
        )

        roles = {
            role: role_buckets[bucket]
            for role, bucket in self.ROLE_BUCKETS.items()
        }
        categories = {
            category: category_buckets[bucket]
            for category, bucket in self.CATEGORY_BUCKETS.items()
        }

        return {
            "format": "canonical_source_ledger_v3_canonical_categories",
            "sources": canonical,
            "sources_count": len(canonical),
            "canonical_sources_count": len(canonical),
            "roles": roles,
            "categories": categories,
            **role_buckets,
            **category_buckets,
            "evidence_sources": evidence_sources,
            "benchmark_sources": benchmark_sources,
            "counts": {
                "all": len(canonical),
                "direct_competitors": len(category_buckets["direct_competitor_sources"]),
                "local_direct_competitors": len(role_buckets["local_direct_competitor_sources"]),
                "adjacent_solutions": len(category_buckets["adjacent_solution_sources"]),
                "technology_benchmarks": len(category_buckets["technology_benchmark_sources"]),
                "market_evidence": len(category_buckets["market_evidence_sources"]),
                "ecosystem_actors": len(category_buckets["ecosystem_actor_sources"]),
                "regional_benchmarks": len(role_buckets["regional_benchmark_sources"]),
                "international_benchmarks": len(role_buckets["international_benchmark_sources"]),
                "technology_providers": len(role_buckets["technology_provider_sources"]),
                "market_and_evidence": len(evidence_sources),
            },
        }

    def _normalize_item(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(raw)
        role = str(item.get("source_role") or self._legacy_role(item)).strip().lower()
        category = str(item.get("canonical_category") or "").strip().lower()
        if category not in self.ALLOWED_CATEGORIES:
            category = self.ROLE_TO_CATEGORY.get(role, "irrelevant")

        item["source_role"] = role
        item["canonical_category"] = category
        item["canonical_classification"] = category
        return item

    def _source_key(self, item: Dict[str, Any]) -> str:
        url = self._canonical_url(str(item.get("url") or item.get("source_url") or ""))
        if url:
            return url
        canonical_id = str(item.get("canonical_source_id") or "").strip().lower()
        if canonical_id:
            return canonical_id
        title = re.sub(r"\s+", " ", str(item.get("title") or "")).strip().lower()
        domain = str(item.get("canonical_vendor_domain") or "").strip().lower()
        return f"{domain}|{title}" if title or domain else ""

    @staticmethod
    def _canonical_url(value: str) -> str:
        try:
            parsed = urlparse(value.strip())
        except Exception:
            return ""
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        host = parsed.netloc.lower().split("@")[-1]
        if host.startswith("www."):
            host = host[4:]
        path = re.sub(r"/{2,}", "/", parsed.path or "/").rstrip("/")
        return urlunparse(("https", host, path, "", "", ""))

    @staticmethod
    def _source_id(key: str) -> str:
        return "src_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _quality(item: Dict[str, Any]) -> float:
        try:
            score = float(item.get("source_relevance_score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        score += 0.05 if item.get("text_extracted") else 0.0
        score += 0.03 if item.get("public_display") else 0.0
        role = str(item.get("source_role") or "").strip().lower()
        role_priority = {
            "direct_competitor": 0.20,
            "official_evidence": 0.14,
            "market_evidence": 0.10,
            "regional_benchmark": 0.08,
            "international_benchmark": 0.07,
            "technology_provider": 0.06,
            "adjacent_solution": 0.05,
            "local_ecosystem": 0.04,
            "directory": 0.01,
        }
        return score + role_priority.get(role, 0.0)

    @staticmethod
    def _unique_by_id(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()
        for item in items:
            key = str(item.get("canonical_source_id") or item.get("url") or item.get("title") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @staticmethod
    def _legacy_role(item: Dict[str, Any]) -> str:
        source_type = str(item.get("source_type") or "").lower()
        region = str(item.get("region_match") or "unknown").lower()
        if item.get("is_direct_competitor"):
            return "direct_competitor"
        if source_type == "technology_benchmark":
            return "technology_provider"
        if source_type in {"market_article", "market_evidence"}:
            return "market_evidence"
        if source_type in {"official_source", "regulation"}:
            return "official_evidence"
        if source_type == "local_ecosystem":
            return "local_ecosystem"
        if source_type == "directory":
            return "directory"
        if source_type == "adjacent_solution":
            return "adjacent_solution"
        if source_type in {"competitor", "pricing_page"}:
            if region == "local":
                return "direct_competitor"
            return "regional_benchmark" if region == "regional" else "international_benchmark"
        return "irrelevant"


canonical_source_ledger = CanonicalSourceLedger()