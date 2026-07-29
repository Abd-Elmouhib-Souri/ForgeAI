# ============================================================
# backend/app/services/forgecrawler.py
# ============================================================
#
# ForgeCrawler V5.2 — Strict Relevance Gate + Audit + Public Hygiene
#
# Objectifs :
# - utiliser Project Intelligence Layer si disponible ;
# - générer des requêtes orientées cas d’usage réel ;
# - scraper les sources disponibles ;
# - appliquer SourceRelevanceGate ;
# - afficher publiquement uniquement les sources solides ;
# - garder les sources internes / rejetées seulement en debug admin ;
# - ne jamais afficher une source parachutée ;
# - retourner "No verified relevant source found" si aucune source solide.
#
# Lot 8C cleanup :
# - réduit les logs trafilatura / urllib3 ;
# - utilise html.parser au lieu de lxml ;
# - garde le fallback snippet quand une source externe échoue.
#
# Lot 9A.2 audit :
# - ajoute des logs d'audit ForgeCrawler ;
# - ne change pas les seuils ;
# - ne change pas SourceRelevanceGate ;
# - ne force aucun concurrent.
#
# Lot 9A.4 hygiene :
# - retire les URLs stg/dev/test/preview/preprod/sandbox ;
# - déduplique les URLs publiques proches ;
# - évite d'afficher plusieurs variantes de la même source ;
# - conserve uniquement les sources publiques réellement affichables.
# ============================================================

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import trafilatura
from bs4 import BeautifulSoup
from ddgs import DDGS

from app.services.source_relevance_gate import source_relevance_gate


logging.getLogger("trafilatura").setLevel(logging.CRITICAL)
logging.getLogger("trafilatura.downloads").setLevel(logging.CRITICAL)
logging.getLogger("trafilatura.core").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


@dataclass
class ForgeCrawlerSource:
    title: str
    url: str
    snippet: str
    extracted_text_preview: str
    extraction_method: str
    text_extracted: bool
    pricing_found: bool
    confidence: str

    source_type: str
    region_match: str
    is_direct_competitor: bool
    why_relevant: str

    source_relevance_score: float
    public_display: bool
    internal_only: bool
    rejected: bool
    matched_strong_terms: List[str]
    matched_weak_terms: List[str]
    matched_forbidden_terms: List[str]
    rejection_reason: str

    search_query: Optional[str] = None
    error: Optional[str] = None


class ForgeCrawler:
    def __init__(
        self,
        max_results_per_query: int = 10,
        max_sources: int = 8,
        timeout_seconds: int = 12,
        max_text_chars: int = 2500,
    ):
        self.max_results_per_query = max_results_per_query
        self.max_sources = max_sources
        self.timeout_seconds = timeout_seconds
        self.max_text_chars = max_text_chars

    async def crawl_competitors(
        self,
        idea: str,
        industry: str = "",
        region: str = "",
        manual_urls: Optional[List[str]] = None,
        project_context: Optional[Dict[str, Any]] = None,
        agent_context_packet: Optional[Dict[str, Any]] = None,
        query_planner: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_region = region or "Tunisie"

        context = self._build_project_context(
            idea=idea,
            industry=industry,
            region=clean_region,
            project_context=project_context,
            agent_context_packet=agent_context_packet,
            query_planner=query_planner,
        )

        queries = self._build_queries(
            idea=idea,
            industry=industry,
            region=clean_region,
            project_context=context,
        )

        errors: List[str] = []
        search_results: List[Dict[str, Any]] = []

        logger.info(
            "[ForgeCrawler] Start strict gate | region=%s | queries=%s",
            clean_region,
            queries,
        )

        if manual_urls:
            for url in manual_urls:
                if self._is_valid_url(url) and self._is_public_source_url(url):
                    search_results.append(
                        {
                            "title": self._domain_from_url(url),
                            "href": url,
                            "body": "URL fournie manuellement par l'utilisateur.",
                            "search_query": "manual_url",
                        }
                    )

        for query in queries:
            try:
                ddgs_results = await self._search_ddgs(query)

                for result in ddgs_results:
                    result["search_query"] = query

                search_results.extend(ddgs_results)

            except Exception as exc:
                error_message = f"DDGS search failed for query='{query}': {str(exc)}"
                logger.exception("[ForgeCrawler] %s", error_message)
                errors.append(error_message)

        clean_results = self._deduplicate_results(search_results)

        logger.info(
            "[ForgeCrawler][AUDIT] Search summary | raw_results=%s | clean_results=%s | queries=%s",
            len(search_results),
            len(clean_results),
            len(queries),
        )

        for index, item in enumerate(clean_results[:20], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] Candidate %s | title=%s | url=%s | query=%s",
                index,
                str(item.get("title") or "")[:120],
                str(item.get("href") or item.get("url") or "")[:180],
                str(item.get("search_query") or "")[:160],
            )

        raw_sources: List[Dict[str, Any]] = []

        max_extract_candidates = max(self.max_sources * 8, 50)

        for result in clean_results[:max_extract_candidates]:
            url = result.get("href") or result.get("url") or ""
            title = result.get("title") or self._domain_from_url(str(url))
            snippet = result.get("body") or result.get("snippet") or ""
            search_query = result.get("search_query")

            if not self._is_valid_url(str(url)):
                continue

            if not self._is_public_source_url(str(url)):
                logger.info(
                    "[ForgeCrawler][AUDIT] Skip non-public URL | title=%s | url=%s",
                    str(title)[:100],
                    str(url)[:180],
                )
                continue

            raw_source = await self._extract_source(
                title=str(title),
                url=str(url),
                snippet=str(snippet),
                search_query=str(search_query) if search_query else None,
            )

            raw_sources.append(raw_source)

        logger.info(
            "[ForgeCrawler][AUDIT] Extraction summary | raw_sources=%s | max_extract_candidates=%s",
            len(raw_sources),
            max_extract_candidates,
        )

        for index, item in enumerate(raw_sources[:20], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] Extracted %s | title=%s | url=%s | method=%s | text_extracted=%s | pricing=%s | error=%s | query=%s",
                index,
                str(item.get("title") or "")[:120],
                str(item.get("url") or "")[:180],
                str(item.get("extraction_method") or ""),
                bool(item.get("text_extracted")),
                bool(item.get("pricing_found")),
                str(item.get("error") or "")[:120],
                str(item.get("search_query") or "")[:160],
            )

        gate_result = source_relevance_gate.filter_sources(
            sources=raw_sources,
            project_context=context,
        )

        raw_public_sources = gate_result["public_sources"]
        internal_sources = gate_result["internal_sources"]
        rejected_sources = gate_result["rejected_sources"]

        public_sources = self._deduplicate_sources_by_canonical_url(
            [
                source
                for source in raw_public_sources
                if self._is_public_source_url(str(source.get("url") or ""))
            ]
        )[: self.max_sources]

        logger.info(
            "[ForgeCrawler][AUDIT] Gate summary | public_raw=%s | public_after_hygiene=%s | internal=%s | rejected=%s",
            len(raw_public_sources),
            len(public_sources),
            len(internal_sources),
            len(rejected_sources),
        )

        for index, item in enumerate(public_sources[:10], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] PUBLIC %s | score=%s | type=%s | region=%s | direct=%s | title=%s | url=%s | strong=%s | weak=%s | forbidden=%s | reason=%s",
                index,
                item.get("source_relevance_score"),
                item.get("source_type"),
                item.get("region_match"),
                item.get("is_direct_competitor"),
                str(item.get("title") or "")[:100],
                str(item.get("url") or "")[:160],
                item.get("matched_strong_terms"),
                item.get("matched_weak_terms"),
                item.get("matched_forbidden_terms"),
                str(item.get("why_relevant") or "")[:240],
            )

        for index, item in enumerate(internal_sources[:10], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] INTERNAL %s | score=%s | type=%s | region=%s | title=%s | url=%s | strong=%s | weak=%s | forbidden=%s | reason=%s",
                index,
                item.get("source_relevance_score"),
                item.get("source_type"),
                item.get("region_match"),
                str(item.get("title") or "")[:100],
                str(item.get("url") or "")[:160],
                item.get("matched_strong_terms"),
                item.get("matched_weak_terms"),
                item.get("matched_forbidden_terms"),
                str(item.get("why_relevant") or "")[:240],
            )

        for index, item in enumerate(rejected_sources[:20], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] REJECTED %s | score=%s | type=%s | region=%s | title=%s | url=%s | strong=%s | weak=%s | forbidden=%s | rejection=%s",
                index,
                item.get("source_relevance_score"),
                item.get("source_type"),
                item.get("region_match"),
                str(item.get("title") or "")[:100],
                str(item.get("url") or "")[:160],
                item.get("matched_strong_terms"),
                item.get("matched_weak_terms"),
                item.get("matched_forbidden_terms"),
                str(item.get("rejection_reason") or "")[:240],
            )

        forge_sources = [
            self._to_forge_source(source)
            for source in public_sources
        ]

        local_competitors = [
            source
            for source in forge_sources
            if source.is_direct_competitor and source.region_match == "local"
        ]

        regional_competitors = [
            source
            for source in forge_sources
            if source.source_type in {"competitor", "pricing_page", "adjacent_solution"}
            and source.region_match == "regional"
        ]

        international_benchmarks = [
            source
            for source in forge_sources
            if source.source_type in {"competitor", "pricing_page", "adjacent_solution"}
            and source.region_match == "international"
        ]

        market_sources = [
            source
            for source in forge_sources
            if source.source_type in {
                "market_article",
                "directory",
                "regulation",
                "adjacent_solution",
            }
            and not source.is_direct_competitor
        ]

        status = self._build_status(
            public_sources=forge_sources,
            errors=errors,
        )

        confidence_level = self._global_confidence(
            public_sources=forge_sources,
            local_competitors=local_competitors,
        )

        no_source_message = self._no_source_message(context)

        limitations = self._build_limitations(
            public_sources=forge_sources,
            errors=errors,
            local_competitors=local_competitors,
            rejected_count=len(rejected_sources),
            no_source_message=no_source_message,
        )

        return {
            "format": "forgecrawler_v5_2_strict_relevance_gate_audit_hygiene",
            "query": queries[0] if queries else "",
            "queries": queries,
            "target_region": clean_region,
            "status": status,
            "confidence_level": confidence_level,
            "source_based": bool(forge_sources),
            "context_locked": True,

            "public_display_threshold": 0.70,
            "internal_use_threshold": 0.50,

            "sources_count": len(forge_sources),
            "raw_public_sources_count": len(raw_public_sources),
            "internal_sources_count": len(internal_sources),
            "rejected_sources_count": len(rejected_sources),

            "local_competitors_found": len(local_competitors) > 0,
            "local_competitors_count": len(local_competitors),
            "regional_competitors_count": len(regional_competitors),
            "international_benchmarks_count": len(international_benchmarks),
            "market_sources_count": len(market_sources),

            "sources": [asdict(source) for source in forge_sources],
            "local_competitor_sources": [asdict(source) for source in local_competitors],
            "regional_competitor_sources": [asdict(source) for source in regional_competitors],
            "international_benchmark_sources": [
                asdict(source) for source in international_benchmarks
            ],
            "market_context_sources": [asdict(source) for source in market_sources],

            "no_verified_relevant_source_found": len(forge_sources) == 0,
            "no_source_message": no_source_message if len(forge_sources) == 0 else "",

            "errors": errors,
            "limitations": self._unique_strings(limitations),

            "debug": {
                "strict_gate": True,
                "audit_enabled": True,
                "public_hygiene_enabled": True,
                "queries_count": len(queries),
                "raw_search_results_count": len(search_results),
                "clean_search_results_count": len(clean_results),
                "raw_sources_count": len(raw_sources),
                "raw_public_sources_count": len(raw_public_sources),
                "public_sources_count": len(forge_sources),
                "internal_sources_count": len(internal_sources),
                "rejected_sources_count": len(rejected_sources),
                "internal_sources_debug": internal_sources[:10],
                "raw_public_sources_debug": [
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source_relevance_score": item.get("source_relevance_score"),
                        "source_type": item.get("source_type"),
                        "region_match": item.get("region_match"),
                        "matched_strong_terms": item.get("matched_strong_terms"),
                    }
                    for item in raw_public_sources[:20]
                ],
                "rejected_sources_debug": [
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source_relevance_score": item.get("source_relevance_score"),
                        "source_type": item.get("source_type"),
                        "region_match": item.get("region_match"),
                        "matched_strong_terms": item.get("matched_strong_terms"),
                        "matched_weak_terms": item.get("matched_weak_terms"),
                        "matched_forbidden_terms": item.get("matched_forbidden_terms"),
                        "rejection_reason": item.get("rejection_reason"),
                    }
                    for item in rejected_sources[:20]
                ],
            },
        }

    # ========================================================
    # Search / extraction
    # ========================================================

    async def _search_ddgs(self, query: str) -> List[Dict[str, Any]]:
        def run_search() -> List[Dict[str, Any]]:
            with DDGS() as ddgs:
                results = ddgs.text(
                    query,
                    max_results=self.max_results_per_query,
                )
                return list(results)

        return await asyncio.to_thread(run_search)

    async def _extract_source(
        self,
        *,
        title: str,
        url: str,
        snippet: str,
        search_query: Optional[str],
    ) -> Dict[str, Any]:
        try:
            downloaded = await asyncio.wait_for(
                asyncio.to_thread(trafilatura.fetch_url, url),
                timeout=self.timeout_seconds,
            )

            extracted_text = ""

            if downloaded:
                extracted_text = trafilatura.extract(downloaded) or ""

            if extracted_text and len(extracted_text.strip()) >= 200:
                preview = self._clean_text(extracted_text)
                extraction_method = "trafilatura"
                text_extracted = True
                error = None

            elif downloaded:
                soup_text = self._extract_with_bs4(downloaded)

                if soup_text and len(soup_text.strip()) >= 100:
                    preview = self._clean_text(soup_text)
                    extraction_method = "beautifulsoup"
                    text_extracted = True
                    error = "Trafilatura extraction empty, used BeautifulSoup fallback."
                else:
                    preview = self._clean_text(snippet)
                    extraction_method = "snippet"
                    text_extracted = False
                    error = "Scraping empty, used search snippet fallback."
            else:
                preview = self._clean_text(snippet)
                extraction_method = "snippet"
                text_extracted = False
                error = "No HTML downloaded, used search snippet fallback."

        except asyncio.TimeoutError:
            preview = self._clean_text(snippet)
            extraction_method = "snippet"
            text_extracted = False
            error = f"Timeout after {self.timeout_seconds}s."

        except Exception as exc:
            preview = self._clean_text(snippet)
            extraction_method = "snippet"
            text_extracted = False
            error = f"Extraction failed: {str(exc)}"

        combined_text = " ".join([title, url, snippet, preview])
        pricing_found = self._detect_pricing(combined_text)

        return {
            "title": title,
            "url": url,
            "snippet": self._clean_text(snippet),
            "extracted_text_preview": preview[: self.max_text_chars],
            "extraction_method": extraction_method,
            "text_extracted": text_extracted,
            "pricing_found": pricing_found,
            "search_query": search_query,
            "error": error,
        }

    def _extract_with_bs4(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        parts: List[str] = []

        title = soup.find("title")
        if title and title.get_text(strip=True):
            parts.append(title.get_text(" ", strip=True))

        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description and meta_description.get("content"):
            parts.append(str(meta_description.get("content")))

        for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = tag.get_text(" ", strip=True)
            if text:
                parts.append(text)

        return "\n".join(parts)

    # ========================================================
    # Query builder
    # ========================================================

    def _build_queries(
        self,
        *,
        idea: str,
        industry: str,
        region: str,
        project_context: Dict[str, Any],
    ) -> List[str]:
        query_planner = (
            project_context.get("query_planner")
            or (project_context.get("project_intelligence") or {}).get("query_planner")
            or {}
        )

        queries_by_intent = query_planner.get("queries_by_intent") or {}

        queries: List[str] = []

        for key in [
            "direct_competitors",
            "adjacent_solutions",
            "market_sources",
            "pricing",
            "field_validation",
        ]:
            value = queries_by_intent.get(key) or []
            if isinstance(value, list):
                queries.extend(str(item) for item in value)

        strong_keywords = project_context.get("strong_keywords") or []
        must_match_terms = project_context.get("must_match_terms") or []

        region_short = self._clean_text(region or "Tunisie")
        industry_short = self._clean_text(industry)
        idea_short = self._shorten_for_search(idea, max_words=12)

        if strong_keywords:
            strong_base = " ".join(str(item) for item in strong_keywords[:5])
            queries.extend(
                [
                    f"{strong_base} {region_short}",
                    f"{strong_base} competitors {region_short}",
                    f"{strong_base} software {region_short}",
                ]
            )

        if must_match_terms:
            must_base = " ".join(str(item) for item in must_match_terms[:4])
            queries.extend(
                [
                    f"{must_base} {region_short}",
                    f"{must_base} alternatives {region_short}",
                ]
            )

        queries.extend(
            [
                f"{idea_short} competitors {region_short}",
                f"{idea_short} alternatives {region_short}",
                f"{industry_short} software {region_short}",
                f"{industry_short} market {region_short}",
            ]
        )

        clean_queries: List[str] = []
        seen = set()

        for query in queries:
            clean = self._clean_text(query)

            if len(clean) < 8:
                continue

            normalized = clean.lower()

            if normalized in seen:
                continue

            seen.add(normalized)
            clean_queries.append(clean)

        return clean_queries[:16]

    # ========================================================
    # Context builder
    # ========================================================

    def _build_project_context(
        self,
        *,
        idea: str,
        industry: str,
        region: str,
        project_context: Optional[Dict[str, Any]],
        agent_context_packet: Optional[Dict[str, Any]],
        query_planner: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        base = dict(project_context or {})

        if agent_context_packet:
            base["agent_context_packet"] = agent_context_packet

            if not base.get("strong_keywords"):
                base["strong_keywords"] = agent_context_packet.get("strong_keywords") or []

            if not base.get("must_match_terms"):
                base["must_match_terms"] = agent_context_packet.get("must_match_terms") or []

            if not base.get("weak_terms_to_ignore"):
                base["weak_terms_to_ignore"] = (
                    agent_context_packet.get("weak_terms_to_ignore") or []
                )

            if not base.get("forbidden_offtopic_terms"):
                base["forbidden_offtopic_terms"] = (
                    agent_context_packet.get("forbidden_offtopic_terms") or []
                )

        if query_planner:
            base["query_planner"] = query_planner

        base.setdefault("description", idea)
        base.setdefault("industry", industry)
        base.setdefault("market_region", region)
        base.setdefault("target_region", region)
        base.setdefault("context_locked", True)

        if not base.get("strong_keywords"):
            base["strong_keywords"] = self._fallback_strong_terms(
                idea=idea,
                industry=industry,
                region=region,
            )

        if not base.get("must_match_terms"):
            base["must_match_terms"] = base["strong_keywords"][:12]

        if not base.get("weak_terms_to_ignore"):
            base["weak_terms_to_ignore"] = [
                "app",
                "application",
                "platform",
                "digital",
                "mobile",
                "service",
                "solution",
                "tool",
                "business",
                "startup",
                "online",
                "dashboard",
                "management",
                "software",
                "saas",
            ]

        return base

    def _fallback_strong_terms(
        self,
        *,
        idea: str,
        industry: str,
        region: str,
    ) -> List[str]:
        text = f"{idea} {industry} {region}"
        words = [
            word.strip()
            for word in re.split(r"[^a-zA-Z0-9À-ÿ]+", text.lower())
            if len(word.strip()) >= 4
        ]

        weak = {
            "application",
            "platform",
            "digital",
            "mobile",
            "service",
            "solution",
            "business",
            "startup",
            "software",
            "saas",
        }

        terms = [word for word in words if word not in weak]

        phrases: List[str] = []

        for size in (2, 3):
            for index in range(0, max(0, len(terms) - size + 1)):
                phrases.append(" ".join(terms[index: index + size]))

        return self._unique_strings(terms + phrases)[:30]

    # ========================================================
    # Output helpers
    # ========================================================

    def _to_forge_source(self, source: Dict[str, Any]) -> ForgeCrawlerSource:
        return ForgeCrawlerSource(
            title=str(source.get("title") or ""),
            url=str(source.get("url") or ""),
            snippet=str(source.get("snippet") or ""),
            extracted_text_preview=str(source.get("extracted_text_preview") or ""),
            extraction_method=str(source.get("extraction_method") or "unknown"),
            text_extracted=bool(source.get("text_extracted")),
            pricing_found=bool(source.get("pricing_found")),
            confidence=str(source.get("confidence") or "low"),
            source_type=str(source.get("source_type") or "irrelevant"),
            region_match=str(source.get("region_match") or "unknown"),
            is_direct_competitor=bool(source.get("is_direct_competitor")),
            why_relevant=str(source.get("why_relevant") or ""),
            source_relevance_score=float(source.get("source_relevance_score") or 0.0),
            public_display=bool(source.get("public_display")),
            internal_only=bool(source.get("internal_only")),
            rejected=bool(source.get("rejected")),
            matched_strong_terms=list(source.get("matched_strong_terms") or []),
            matched_weak_terms=list(source.get("matched_weak_terms") or []),
            matched_forbidden_terms=list(source.get("matched_forbidden_terms") or []),
            rejection_reason=str(source.get("rejection_reason") or ""),
            search_query=source.get("search_query"),
            error=source.get("error"),
        )

    def _build_status(
        self,
        *,
        public_sources: List[ForgeCrawlerSource],
        errors: List[str],
    ) -> str:
        if public_sources:
            return "completed"

        if errors:
            return "limited"

        return "no_verified_sources"

    def _global_confidence(
        self,
        *,
        public_sources: List[ForgeCrawlerSource],
        local_competitors: List[ForgeCrawlerSource],
    ) -> str:
        if len(local_competitors) >= 2 and len(public_sources) >= 3:
            return "high"

        if len(local_competitors) >= 1:
            return "medium"

        if len(public_sources) >= 3:
            return "medium"

        return "low"

    def _build_limitations(
        self,
        *,
        public_sources: List[ForgeCrawlerSource],
        errors: List[str],
        local_competitors: List[ForgeCrawlerSource],
        rejected_count: int,
        no_source_message: str,
    ) -> List[str]:
        limitations: List[str] = []

        if not public_sources:
            limitations.append(no_source_message)

        if not local_competitors:
            limitations.append(
                "Aucun concurrent local direct vérifié n'a été trouvé avec un score de pertinence suffisant."
            )

        if rejected_count > 0:
            limitations.append(
                f"{rejected_count} source(s) ont été rejetée(s) car trop faibles, génériques ou hors contexte."
            )

        if errors:
            limitations.append(
                "Certaines recherches ou extractions web ont échoué, mais l'analyse continue avec les sources valides."
            )

        limitations.append(
            "Les sources faibles ne sont pas affichées publiquement ; elles restent uniquement en debug admin."
        )

        return limitations

    def _no_source_message(self, project_context: Dict[str, Any]) -> str:
        language = str(project_context.get("output_language") or "fr").lower()

        if language == "en":
            return "No verified relevant source found."

        return "Aucune source pertinente vérifiée trouvée."

    # ========================================================
    # Generic helpers
    # ========================================================

    def _detect_pricing(self, text: str) -> bool:
        normalized = text.lower()

        pricing_terms = [
            "pricing",
            "price",
            "plans",
            "subscription",
            "tarif",
            "tarifs",
            "abonnement",
            "mensuel",
            "monthly",
            "$",
            "€",
            "dt",
            "tnd",
        ]

        return any(term in normalized for term in pricing_terms)

    def _is_public_source_url(self, url: str) -> bool:
        if not self._is_valid_url(url):
            return False

        parsed = urlparse(str(url))
        domain = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()

        labels = domain.split(".")
        first_label = labels[0] if labels else ""

        non_public_prefixes = (
            "stg",
            "stg-",
            "stage",
            "stage-",
            "staging",
            "staging-",
            "dev",
            "dev-",
            "test",
            "test-",
            "preview",
            "preview-",
            "preprod",
            "preprod-",
            "uat",
            "uat-",
            "sandbox",
            "sandbox-",
        )

        if len(labels) >= 3 and first_label.startswith(non_public_prefixes):
            return False

        non_public_path_markers = {
            "/staging/",
            "/stage/",
            "/dev/",
            "/test/",
            "/preview/",
            "/preprod/",
            "/uat/",
            "/sandbox/",
        }

        if any(marker in path for marker in non_public_path_markers):
            return False

        return True

    def _canonical_source_key(self, source: Dict[str, Any]) -> str:
        url = str(source.get("url") or "")

        if not self._is_valid_url(url):
            return ""

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        language_segments = {
            "en",
            "fr",
            "ar",
            "de",
            "es",
            "it",
            "pt",
            "en-us",
            "en-gb",
            "fr-fr",
            "ar-tn",
        }

        path_segments = [
            segment.strip().lower()
            for segment in parsed.path.split("/")
            if segment.strip()
        ]

        clean_segments = [
            segment
            for segment in path_segments
            if segment not in language_segments
        ]

        canonical_path = "/".join(clean_segments)

        return f"{domain}/{canonical_path}".rstrip("/")

    def _deduplicate_sources_by_canonical_url(
        self,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()

        for source in sources:
            key = self._canonical_source_key(source)

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            result.append(source)

        return result

    def _deduplicate_results(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        clean_results: List[Dict[str, Any]] = []
        seen_urls = set()

        for result in results:
            url = str(result.get("href") or result.get("url") or "").strip()

            if not url:
                continue

            normalized_url = self._normalize_url(url)

            if normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)
            clean_results.append(result)

        return clean_results

    def _is_valid_url(self, url: str) -> bool:
        try:
            parsed = urlparse(str(url))
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:
            return False

    def _domain_from_url(self, url: str) -> str:
        try:
            return urlparse(str(url)).netloc.replace("www.", "")
        except Exception:
            return ""

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(str(url))
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()

    def _shorten_for_search(self, text: str, max_words: int = 12) -> str:
        words = [
            word
            for word in re.split(r"\s+", self._clean_text(text))
            if word.strip()
        ]

        return " ".join(words[:max_words])

    def _clean_text(self, text: Any) -> str:
        if text is None:
            return ""

        value = str(text)
        value = re.sub(r"\s+", " ", value).strip()

        return value

    def _unique_strings(self, items: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for item in items:
            clean = self._clean_text(item)

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result