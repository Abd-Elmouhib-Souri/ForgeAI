# ============================================================
# backend/app/services/forgecrawler.py
# ============================================================
#
# ForgeCrawler V7 — Professional Query Planner + Evidence Prefilter + Strict Gate
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
# - limiter la recherche à 8 requêtes courtes et intentionnelles ;
# - préfiltrer et classer les candidats avant téléchargement ;
# - limiter l'extraction à 16 pages avec concurrence bornée ;
# - préserver les preuves métier du SourceRelevanceGate jusqu'au frontend.
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
from app.web_search.search_gateway import search_gateway

from app.services.source_relevance_gate import source_relevance_gate
from app.services.source_classifier import source_classifier


logging.getLogger("trafilatura").setLevel(logging.CRITICAL)
logging.getLogger("trafilatura.downloads").setLevel(logging.CRITICAL)
logging.getLogger("trafilatura.core").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


@dataclass
class ForgeCrawlerSource:
    """
    Public-safe source contract returned by ForgeCrawler.

    The four contextual-match booleans are deliberately preserved. They are
    produced by SourceRelevanceGate and are required by the deterministic
    competitor classifier. Older versions dropped them while converting the
    gate result to a dataclass, which made every strict direct competitor look
    unverified downstream.
    """

    title: str
    url: str
    snippet: str
    extracted_text_preview: str
    extraction_method: str
    text_extracted: bool
    pricing_found: bool
    confidence: str

    source_type: str
    source_role: str
    canonical_category: str
    comparison_scope: str
    region_match: str
    is_direct_competitor: bool
    technology_supplier: bool
    canonical_source_id: str
    why_relevant: str
    public_reason: str

    source_relevance_score: float
    public_display: bool
    internal_only: bool
    rejected: bool

    matched_strong_terms: List[str]
    matched_weak_terms: List[str]
    matched_forbidden_terms: List[str]

    matched_domain_terms: List[str]
    matched_sector_terms: List[str]
    matched_target_terms: List[str]
    matched_use_case_terms: List[str]
    matched_solution_terms: List[str]
    product_evidence_signals: List[str]
    market_evidence_signals: List[str]
    evidence_categories: List[str]

    same_or_close_target_user: bool
    same_or_close_sector: bool
    target_match_level: str
    is_product_page: bool
    same_or_close_use_case: bool
    same_or_close_solution_category: bool
    clear_contextual_link: bool

    rejection_reason: str
    vendor_key: str = ""
    vendor_name: str = ""
    canonical_vendor_domain: str = ""
    sector_mismatch: bool = False
    mismatch_terms: Optional[List[str]] = None
    search_provider: str = ""
    provider_score: float = 0.0
    search_query: Optional[str] = None
    error: Optional[str] = None


class ForgeCrawler:
    # Query Planner V3 constraints.
    MAX_QUERY_WORDS = 9
    DEFAULT_MAX_QUERIES = 8
    DEFAULT_MAX_EXTRACT_CANDIDATES = 16
    DEFAULT_MAX_PARALLEL_EXTRACTIONS = 4

    # Generic words are never enough to make a query or a candidate specific.
    QUERY_WEAK_TERMS = {
        "app",
        "application",
        "platform",
        "plateforme",
        "digital",
        "mobile",
        "service",
        "solution",
        "tool",
        "outil",
        "business",
        "startup",
        "online",
        "website",
        "dashboard",
        "management",
        "manage",
        "software",
        "logiciel",
        "saas",
        "system",
        "product",
        "market",
        "industry",
        "company",
        "companies",
        "competitor",
        "competitors",
        "alternative",
        "alternatives",
        "pricing",
        "price",
    }

    QUERY_STOP_WORDS = {
        "a",
        "an",
        "and",
        "the",
        "is",
        "are",
        "for",
        "from",
        "with",
        "who",
        "that",
        "this",
        "these",
        "those",
        "to",
        "of",
        "in",
        "on",
        "by",
        "need",
        "needs",
        "small",
        "lightweight",
        "simple",
        "basic",
        "first",
        "main",
        "new",
        "using",
        "used",
        "pour",
        "avec",
        "dans",
        "des",
        "les",
        "une",
        "un",
        "qui",
        "sur",
        "par",
        "aux",
        "du",
        "de",
        "la",
        "le",
    }

    # Terms removed from fallback concept extraction. They describe prose or
    # commercial framing, not the user's business domain.
    FALLBACK_CONCEPT_STOP_WORDS = QUERY_STOP_WORDS | QUERY_WEAK_TERMS | {
        "problem", "problems", "many", "still", "model", "monthly", "low",
        "high", "first", "main", "possible", "real", "existing", "current",
        "problème", "probleme", "problèmes", "problemes", "modèle", "modele",
        "mensuel", "faible", "premier", "première", "premiere",
    }

    CANDIDATE_EVIDENCE_MARKERS = {
        "software", "platform", "application", "app", "product", "features",
        "pricing", "plans", "subscription", "market", "report", "study",
        "statistics", "survey", "regulation", "traceability", "workflow",
        "system", "tool", "dashboard", "solution", "research", "analysis",
        "logiciel", "plateforme", "fonctionnalités", "fonctionnalites",
        "tarifs", "marché", "marche", "rapport", "étude", "etude",
        "statistiques", "enquête", "enquete", "réglementation", "reglementation",
    }

    OFF_TOPIC_CANDIDATE_TERMS = {
        "football",
        "soccer",
        "squad",
        "transfermarkt",
        "weather",
        "météo",
        "meteo",
        "tourism",
        "tourisme",
        "hotel",
        "flight",
        "casino",
        "gambling",
        "forex",
        "crypto",
        "music",
        "song",
        "movie",
        "minecraft",
        "phone lookup",
        "mobile operators",
        "telecom",
        "speed test",
        "youtube",
        "tiktok",
        "instagram",
        "facebook",
        "google translate",
        "translator",
    }

    LOW_VALUE_DOMAINS = {
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "dzen.ru",
        "pinterest.com",
        "instagram.com",
        "facebook.com",
        "translate.google.com",
        "translate.google.com.tn",
    }

    def __init__(
        self,
        max_results_per_query: int = 10,
        max_sources: int = 8,
        timeout_seconds: int = 12,
        max_text_chars: int = 2500,
        max_queries: int = DEFAULT_MAX_QUERIES,
        max_extract_candidates: int = DEFAULT_MAX_EXTRACT_CANDIDATES,
        max_parallel_extractions: int = DEFAULT_MAX_PARALLEL_EXTRACTIONS,
    ):
        # DDGS can internally query several engines for one request. Limiting
        # each query to eight results reduces rate limiting and duplicate noise.
        self.max_results_per_query = max(
            3,
            min(int(max_results_per_query or 8), 8),
        )
        self.max_sources = max(1, int(max_sources or 8))
        self.timeout_seconds = max(4, int(timeout_seconds or 12))
        self.max_text_chars = max(500, int(max_text_chars or 2500))
        self.max_queries = max(1, min(int(max_queries or 8), 8))
        self.max_extract_candidates = max(
            self.max_sources,
            min(int(max_extract_candidates or 16), 16),
        )
        self.max_parallel_extractions = max(
            1,
            min(int(max_parallel_extractions or 4), 6),
        )

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
        clean_region = str(region or "").strip()

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
                provider_results = await self._search_web(query)

                for result in provider_results:
                    result["search_query"] = query

                search_results.extend(provider_results)

            except Exception as exc:
                error_message = f"Web search failed for query='{query}': {str(exc)}"
                logger.exception("[ForgeCrawler] %s", error_message)
                errors.append(error_message)

        clean_results = self._deduplicate_results(search_results)

        prefiltered_results = self._prefilter_and_rank_results(
            results=clean_results,
            project_context=context,
            manual_urls=manual_urls or [],
        )

        logger.info(
            "[ForgeCrawler][AUDIT] Search summary | "
            "raw_results=%s | clean_results=%s | prefiltered=%s | queries=%s",
            len(search_results),
            len(clean_results),
            len(prefiltered_results),
            len(queries),
        )

        for index, item in enumerate(prefiltered_results[:20], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] Candidate %s | "
                "prefilter_score=%s | matched=%s | title=%s | url=%s | query=%s",
                index,
                item.get("_prefilter_score"),
                item.get("_prefilter_matched_terms"),
                str(item.get("title") or "")[:120],
                str(item.get("href") or item.get("url") or "")[:180],
                str(item.get("search_query") or "")[:160],
            )

        # Download only the best candidates. The old implementation extracted
        # up to 64 pages sequentially. V3 caps this at 16 and uses a bounded
        # semaphore, which is substantially faster without creating an
        # uncontrolled burst of outgoing requests.
        extraction_candidates = prefiltered_results[
            : self.max_extract_candidates
        ]

        semaphore = asyncio.Semaphore(self.max_parallel_extractions)

        async def extract_candidate(
            result: Dict[str, Any],
        ) -> Optional[Dict[str, Any]]:
            url = result.get("href") or result.get("url") or ""
            title = result.get("title") or self._domain_from_url(str(url))
            snippet = result.get("body") or result.get("snippet") or ""
            search_query = result.get("search_query")

            if not self._is_valid_url(str(url)):
                return None

            if not self._is_public_source_url(str(url)):
                logger.info(
                    "[ForgeCrawler][AUDIT] Skip non-public URL | "
                    "title=%s | url=%s",
                    str(title)[:100],
                    str(url)[:180],
                )
                return None

            async with semaphore:
                source = await self._extract_source(
                    title=str(title),
                    url=str(url),
                    snippet=str(snippet),
                    search_query=(
                        str(search_query)
                        if search_query
                        else None
                    ),
                )

            source["prefilter_score"] = result.get("_prefilter_score")
            source["prefilter_matched_terms"] = result.get("_prefilter_matched_terms") or []
            source["search_provider"] = str(result.get("provider") or "")
            source["provider_score"] = self._safe_float(result.get("provider_score"), 0.0)
            return source

        extracted_items = await asyncio.gather(
            *[
                extract_candidate(result)
                for result in extraction_candidates
            ],
            return_exceptions=True,
        )

        raw_sources: List[Dict[str, Any]] = []

        for item in extracted_items:
            if isinstance(item, Exception):
                errors.append(
                    f"Candidate extraction failed: {str(item)}"
                )
                logger.warning(
                    "[ForgeCrawler] Candidate extraction failed: %s",
                    item,
                )
                continue

            if isinstance(item, dict):
                raw_sources.append(item)

        logger.info(
            "[ForgeCrawler][AUDIT] Extraction summary | "
            "raw_sources=%s | max_extract_candidates=%s | parallelism=%s",
            len(raw_sources),
            self.max_extract_candidates,
            self.max_parallel_extractions,
        )

        for index, item in enumerate(raw_sources[:20], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] Extracted %s | "
                "title=%s | url=%s | method=%s | "
                "text_extracted=%s | pricing=%s | error=%s | query=%s",
                index,
                str(item.get("title") or "")[:120],
                str(item.get("url") or "")[:180],
                str(item.get("extraction_method") or ""),
                bool(item.get("text_extracted")),
                bool(item.get("pricing_found")),
                str(item.get("error") or "")[:120],
                str(item.get("search_query") or "")[:160],
            )

        classified_sources = await source_classifier.classify_sources(
            raw_sources,
            context,
        )

        gate_result = source_relevance_gate.filter_sources(
            sources=classified_sources,
            project_context=context,
        )

        raw_public_sources = [
            self._enrich_vendor_identity(item)
            for item in gate_result["public_sources"]
        ]
        internal_sources = gate_result["internal_sources"]
        rejected_sources = gate_result["rejected_sources"]

        public_sources, hygiene_rejected = self._select_public_sources(
            raw_public_sources
        )

        logger.info(
            "[ForgeCrawler][AUDIT] Gate summary | public_raw=%s | public_after_hygiene=%s | internal=%s | rejected=%s | hygiene_rejected=%s",
            len(raw_public_sources),
            len(public_sources),
            len(internal_sources),
            len(rejected_sources),
            len(hygiene_rejected),
        )

        for item in hygiene_rejected:
            logger.info(
                "[ForgeCrawler][HygieneRejected] title=%s | url=%s | canonical_key=%s | reason=%s | rank=%s",
                str(item.get("title") or "")[:120],
                str(item.get("url") or "")[:180],
                str(item.get("canonical_key") or "")[:180],
                str(item.get("hygiene_reason") or "unknown"),
                item.get("public_rank"),
            )

        for index, item in enumerate(public_sources[:10], start=1):
            logger.info(
                "[ForgeCrawler][AUDIT] PUBLIC %s | score=%s | type=%s | role=%s | region=%s | direct=%s | title=%s | url=%s | strong=%s | weak=%s | forbidden=%s | evidence=%s | reason=%s",
                index,
                item.get("source_relevance_score"),
                item.get("source_type"),
                item.get("source_role"),
                item.get("region_match"),
                item.get("is_direct_competitor"),
                str(item.get("title") or "")[:100],
                str(item.get("url") or "")[:160],
                item.get("matched_strong_terms"),
                item.get("matched_weak_terms"),
                item.get("matched_forbidden_terms"),
                item.get("evidence_categories"),
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

        local_adjacent_sources = [
            source
            for source in forge_sources
            if source.canonical_category == "adjacent_solution"
            and source.region_match == "local"
        ]

        regional_competitors = [
            source
            for source in forge_sources
            if source.source_role == "regional_benchmark"
        ]

        international_benchmarks = [
            source
            for source in forge_sources
            if source.source_role in {
                "international_benchmark",
                "technology_provider",
            }
        ]

        technology_benchmarks = [
            source
            for source in forge_sources
            if source.canonical_category == "technology_benchmark"
        ]

        ecosystem_sources = [
            source
            for source in forge_sources
            if source.canonical_category == "ecosystem_actor"
        ]

        market_sources = [
            source
            for source in forge_sources
            if source.canonical_category == "market_evidence"
        ]

        status = self._build_status(
            public_sources=forge_sources,
            errors=errors,
        )

        evidence_confidence = self._evidence_confidence(
            public_sources=forge_sources,
            local_competitors=local_competitors,
        )
        confidence_level = evidence_confidence["overall_evidence_confidence"]

        no_source_message = self._no_source_message(context)

        limitations = self._build_limitations(
            public_sources=forge_sources,
            errors=errors,
            local_competitors=local_competitors,
            rejected_count=len(rejected_sources),
            no_source_message=no_source_message,
        )

        return {
            "format": "forgecrawler_v8_canonical_source_intelligence",
            "query": queries[0] if queries else "",
            "queries": queries,
            "target_region": clean_region,
            "status": status,
            "confidence_level": confidence_level,
            "evidence_confidence": evidence_confidence,
            "source_based": bool(forge_sources),
            "context_locked": True,

            "public_display_threshold": 0.70,
            "public_threshold_policy": "role_aware",
            "public_selection_policy": "role_aware_diversity_v10",
            "public_selection_quotas": {
                "local_direct_competitor": 1,
                "local_adjacent_solution": 2,
                "local_market_evidence": 2,
                "local_ecosystem_actor": 1,
                "technology_benchmark": 1,
                "external_market_evidence": 1,
            },
            "role_thresholds": {
                "direct_competitor_local": 0.58,
                "adjacent_solution_local": 0.32,
                "ecosystem_actor_local": 0.28,
                "market_evidence_local": 0.36,
                "market_evidence_external": 0.42,
                "technology_benchmark": 0.40,
            },
            "internal_use_threshold": 0.50,

            "sources_count": len(forge_sources),
            "raw_public_sources_count": len(raw_public_sources),
            "internal_sources_count": len(internal_sources),
            "rejected_sources_count": len(rejected_sources),

            "local_competitors_found": len(local_competitors) > 0,
            "local_competitors_count": len(local_competitors),
            "local_adjacent_solutions_count": len(local_adjacent_sources),
            "regional_competitors_count": len(regional_competitors),
            "international_benchmarks_count": len(international_benchmarks),
            "technology_benchmarks_count": len(technology_benchmarks),
            "ecosystem_sources_count": len(ecosystem_sources),
            "market_sources_count": len(market_sources),

            "sources": [asdict(source) for source in forge_sources],
            "local_competitor_sources": [asdict(source) for source in local_competitors],
            "local_adjacent_solution_sources": [
                asdict(source) for source in local_adjacent_sources
            ],
            "regional_competitor_sources": [asdict(source) for source in regional_competitors],
            "international_benchmark_sources": [
                asdict(source) for source in international_benchmarks
            ],
            "technology_benchmark_sources": [
                asdict(source) for source in technology_benchmarks
            ],
            "ecosystem_actor_sources": [
                asdict(source) for source in ecosystem_sources
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
                "query_planner_version": "v3",
                "candidate_prefilter_enabled": True,
                "queries_count": len(queries),
                "raw_search_results_count": len(search_results),
                "clean_search_results_count": len(clean_results),
                "prefiltered_search_results_count": len(prefiltered_results),
                "max_extract_candidates": self.max_extract_candidates,
                "max_parallel_extractions": self.max_parallel_extractions,
                "raw_sources_count": len(raw_sources),
                "classified_sources_count": len(classified_sources),
                "raw_public_sources_count": len(raw_public_sources),
                "public_sources_count": len(forge_sources),
                "public_selection_buckets": {
                    bucket: sum(
                        1
                        for item in public_sources
                        if self._source_diversity_bucket(item) == bucket
                    )
                    for bucket in {
                        self._source_diversity_bucket(item)
                        for item in public_sources
                    }
                },
                "hygiene_rejected_count": len(hygiene_rejected),
                "hygiene_rejected_debug": hygiene_rejected[:20],
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
                        "evidence_categories": item.get("evidence_categories"),
                        "is_direct_competitor": item.get("is_direct_competitor"),
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

    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        rows = await search_gateway.search(
            query, min_results=5, allow_gemini_fallback=True
        )
        return [
            {
                "title": row.get("title") or "",
                "href": row.get("url") or "",
                "body": row.get("snippet") or "",
                "provider": row.get("provider"),
                "provider_score": row.get("provider_score"),
                "raw_content": row.get("raw_content") or "",
                "search_query": query,
            }
            for row in rows
        ]

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
    # Candidate prefilter / ranking
    # ========================================================

    def _prefilter_and_rank_results(
        self,
        *,
        results: List[Dict[str, Any]],
        project_context: Dict[str, Any],
        manual_urls: List[str],
    ) -> List[Dict[str, Any]]:
        """Reject off-topic candidates before any page download.

        Only title, snippet and URL are used. The search query is deliberately
        excluded because it already contains project terms by construction.
        """
        business_terms = self._business_search_terms(
            idea=str(project_context.get("description") or ""),
            industry=str(project_context.get("industry") or ""),
            region=str(
                project_context.get("market_region")
                or project_context.get("target_region")
                or ""
            ),
            project_context=project_context,
        )
        region_terms = self._tokenize_search_text(
            project_context.get("market_region")
            or project_context.get("target_region")
            or ""
        )
        manual_keys = {
            self._normalize_url(url)
            for url in manual_urls
            if self._is_valid_url(url)
        }

        ranked: List[Dict[str, Any]] = []
        for result in results:
            url = str(result.get("href") or result.get("url") or "").strip()
            if not self._is_valid_url(url) or not self._is_public_source_url(url):
                continue

            normalized_url = self._normalize_url(url)
            is_manual = normalized_url in manual_keys
            title = self._clean_text(result.get("title") or "")
            snippet = self._clean_text(
                result.get("body") or result.get("snippet") or ""
            )
            score, hard_reject, matched_terms = self._candidate_prefilter_score(
                title=title,
                snippet=snippet,
                url=url,
                business_terms=business_terms,
                region_terms=region_terms,
                is_manual=is_manual,
            )
            if hard_reject and not is_manual:
                continue
            if score < 1.35 and not is_manual:
                continue

            enriched = dict(result)
            enriched["_prefilter_score"] = round(score, 3)
            enriched["_prefilter_matched_terms"] = matched_terms[:12]
            enriched["_manual_url"] = is_manual
            ranked.append(enriched)

        ranked.sort(
            key=lambda item: (
                bool(item.get("_manual_url")),
                float(item.get("_prefilter_score") or 0),
                len(item.get("_prefilter_matched_terms") or []),
            ),
            reverse=True,
        )

        # Domain diversity prevents a single publisher or directory from taking
        # every extraction slot.
        diverse: List[Dict[str, Any]] = []
        domain_counts: Dict[str, int] = {}
        for item in ranked:
            url = str(item.get("href") or item.get("url") or "")
            domain = self._domain_from_url(url).lower()
            per_domain_limit = 3 if bool(item.get("_manual_url")) else 2
            if domain_counts.get(domain, 0) >= per_domain_limit:
                continue
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            diverse.append(item)
        return diverse

    def _candidate_prefilter_score(
        self,
        *,
        title: str,
        snippet: str,
        url: str,
        business_terms: List[str],
        region_terms: List[str],
        is_manual: bool,
    ) -> tuple[float, bool, List[str]]:
        normalized_text = self._normalize_search_phrase(
            " ".join([title, snippet, url])
        )
        normalized_title_url = self._normalize_search_phrase(
            " ".join([title, url])
        )
        if not normalized_text:
            return (10.0, False, ["manual_url"]) if is_manual else (0.0, True, [])

        domain = self._domain_from_url(url).lower().replace("www.", "")
        if domain in self.LOW_VALUE_DOMAINS:
            return (10.0, False, ["manual_url"]) if is_manual else (-5.0, True, [])

        matched_terms: List[str] = []
        score = 0.0
        for term in business_terms:
            clean_term = self._normalize_search_phrase(term)
            if not clean_term or clean_term in self.QUERY_WEAK_TERMS:
                continue
            if self._phrase_in_text(clean_term, normalized_text):
                matched_terms.append(clean_term)
                word_count = len(clean_term.split())
                score += 2.2 if word_count >= 2 else 1.0

        matched_terms = self._unique_strings(matched_terms)
        multiword_match = any(len(item.split()) >= 2 for item in matched_terms)
        specific_single_matches = {
            item for item in matched_terms
            if " " not in item and len(item) >= 5
        }

        evidence_markers = {
            marker
            for marker in self.CANDIDATE_EVIDENCE_MARKERS
            if self._phrase_in_text(marker, normalized_text)
        }
        off_topic = any(
            self._phrase_in_text(term, normalized_title_url)
            for term in self.OFF_TOPIC_CANDIDATE_TERMS
        )

        # One generic-looking isolated word is insufficient. A niche one-word
        # concept is accepted only together with an evidence marker, while two
        # different concepts or one multiword concept are sufficient.
        has_business_evidence = bool(
            multiword_match
            or len(specific_single_matches) >= 2
            or (len(specific_single_matches) == 1 and evidence_markers)
        )
        if not has_business_evidence and not is_manual:
            return (score, True, matched_terms)
        if off_topic and len(matched_terms) < 2 and not is_manual:
            return (-4.0, True, matched_terms)

        score += min(1.2, 0.20 * len(evidence_markers))
        source_tokens = set(self._tokenize_search_text(normalized_text))
        if set(region_terms) & source_tokens:
            score += 0.25
        if is_manual:
            score += 10.0

        if any(marker in domain for marker in (
            "rocketreach", "info-clipper", "techbehemoths", "yandex"
        )):
            score -= 1.2
        return score, False, matched_terms

    def _normalize_search_phrase(self, value: Any) -> str:
        text = self._clean_text(value).lower()
        text = text.replace("’", "'")
        text = re.sub(
            r"[^a-z0-9à-ÿ'\- ]+",
            " ",
            text,
        )
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _tokenize_search_text(self, value: Any) -> List[str]:
        normalized = self._normalize_search_phrase(value)

        return [
            token
            for token in re.split(r"[\s\-]+", normalized)
            if token
        ]

    def _phrase_in_text(
        self,
        phrase: str,
        text: str,
    ) -> bool:
        clean_phrase = self._normalize_search_phrase(phrase)
        clean_text = self._normalize_search_phrase(text)

        if not clean_phrase or not clean_text:
            return False

        pattern = (
            r"(?<![a-z0-9à-ÿ])"
            + re.escape(clean_phrase)
            + r"(?![a-z0-9à-ÿ])"
        )

        return bool(
            re.search(pattern, clean_text)
        )

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
        """
        Build at most eight short, intent-specific queries.

        Priority order:
        1. concise queries already produced by Project Intelligence Layer;
        2. direct/adjacent solution discovery;
        3. regional and international benchmarks;
        4. market evidence.

        Long fragments copied from the project description are discarded.
        A query must contain at least one business-specific term that is not
        merely the project name, region, or a generic product word.
        """

        query_planner = (
            project_context.get("query_planner")
            or (
                project_context.get("project_intelligence")
                or {}
            ).get("query_planner")
            or {}
        )

        project_name = self._clean_text(
            project_context.get("project_name")
            or project_context.get("title")
            or ""
        )
        region_token_set = set(
            self._tokenize_search_text(region)
        )
        project_name_terms = set(
            self._tokenize_search_text(project_name)
        ) - region_token_set

        business_terms = self._business_search_terms(
            idea=idea,
            industry=industry,
            region=region,
            project_context=project_context,
        )

        explicit_candidates: List[str] = []
        queries_by_intent = (
            query_planner.get("queries_by_intent")
            or {}
        )

        for key in [
            "direct_competitors",
            "adjacent_solutions",
            "regional_benchmarks",
            "international_benchmarks",
            "market_sources",
            "pricing",
            "field_validation",
        ]:
            value = queries_by_intent.get(key) or []

            if isinstance(value, list):
                explicit_candidates.extend(
                    str(item)
                    for item in value
                    if str(item).strip()
                )

        top_level_queries = query_planner.get("queries") or []

        if isinstance(top_level_queries, list):
            explicit_candidates.extend(
                str(item)
                for item in top_level_queries
                if str(item).strip()
            )

        prepared_explicit: List[tuple[float, str]] = []

        for raw_query in explicit_candidates:
            prepared = self._prepare_query(
                raw_query=raw_query,
                project_name_terms=project_name_terms,
                business_terms=business_terms,
                region=region,
            )

            if not prepared:
                continue

            quality = self._query_quality_score(
                query=prepared,
                business_terms=business_terms,
                project_name_terms=project_name_terms,
                region=region,
            )

            if quality <= 0:
                continue

            prepared_explicit.append((quality, prepared))

        prepared_explicit.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        queries: List[str] = []

        # Keep a maximum of six planner queries so that generated fallback
        # intents still get at least two slots.
        for _, query in prepared_explicit:
            self._append_diverse_query(queries, query)

            if len(queries) >= min(6, self.max_queries):
                break

        generated_queries = self._generated_query_candidates(
            business_terms=business_terms,
            industry=industry,
            region=region,
        )

        for query in generated_queries:
            prepared = self._prepare_query(
                raw_query=query,
                project_name_terms=project_name_terms,
                business_terms=business_terms,
                region=region,
            )

            if not prepared:
                continue

            self._append_diverse_query(queries, prepared)

            if len(queries) >= self.max_queries:
                break

        # Absolute fallback for projects with very little structured context.
        if not queries:
            industry_short = self._shorten_for_search(
                industry,
                max_words=3,
            )
            region_short = self._shorten_for_search(
                region or "",
                max_words=2,
            )

            fallback = self._clean_text(
                " ".join(part for part in [industry_short, "software", region_short] if part)
            )

            if len(fallback.split()) >= 3:
                queries.append(fallback)

        logger.info(
            "[ForgeCrawler][QueryPlannerV3] "
            "queries=%s | business_terms=%s",
            queries,
            business_terms[:12],
        )

        return queries[: self.max_queries]

    def _business_search_terms(
        self,
        *,
        idea: str,
        industry: str,
        region: str,
        project_context: Dict[str, Any],
    ) -> List[str]:
        intelligence = project_context.get("project_intelligence") or {}
        structured = (
            project_context.get("structured_project_context")
            or intelligence.get("structured_project_context")
            or {}
        )
        packet = project_context.get("agent_context_packet") or {}
        planner = project_context.get("query_planner") or {}

        raw_values: List[Any] = [
            project_context.get("search_concepts"),
            project_context.get("domain_concepts"),
            project_context.get("use_case_terms"),
            project_context.get("solution_terms"),
            packet.get("search_concepts"),
            packet.get("domain_concepts"),
            packet.get("use_case_terms"),
            packet.get("solution_terms"),
            structured.get("search_concepts"),
            structured.get("domain_concepts"),
            structured.get("use_case_terms"),
            structured.get("solution_terms"),
            structured.get("use_cases"),
            structured.get("solution_category"),
            planner.get("primary_search_terms"),
            planner.get("domain_concepts"),
            planner.get("use_case_terms"),
            planner.get("solution_terms"),
        ]

        region_tokens = set(self._tokenize_search_text(region))
        project_name_tokens = set(self._tokenize_search_text(
            project_context.get("project_name") or project_context.get("title") or ""
        )) - region_tokens
        cleaned: List[str] = []

        for value in raw_values:
            values = value if isinstance(value, list) else [value]
            for item in values:
                if not item:
                    continue
                for fragment in re.split(r"[/,;|]+", str(item)):
                    tokens = [
                        token for token in self._tokenize_search_text(fragment)
                        if token not in self.FALLBACK_CONCEPT_STOP_WORDS
                        and token not in region_tokens
                        and token not in project_name_tokens
                        and len(token) >= 3
                    ]
                    if not tokens:
                        continue
                    phrase = " ".join(tokens[:4])
                    if phrase and phrase not in self.QUERY_WEAK_TERMS:
                        cleaned.append(phrase)
                    if len(tokens) == 1 and len(tokens[0]) >= 5:
                        cleaned.append(tokens[0])

        # Compatibility fallback for old projects without Project Intelligence
        # V3. The extractor removes prose glue and business-model wording.
        if not cleaned:
            cleaned.extend(self._fallback_strong_terms(
                idea=idea,
                industry=industry,
                region=region,
            ))

        # Preserve Project Intelligence ordering: domain concepts and explicit
        # workflows must not be displaced by long target-user phrases.
        target_tokens = {
            token
            for value in (
                project_context.get("target_terms")
                or packet.get("target_terms")
                or structured.get("target_terms")
                or []
            )
            for token in self._tokenize_search_text(value)
        }
        unique = []
        for item in self._unique_strings(cleaned):
            item_tokens = set(self._tokenize_search_text(item))
            if item_tokens and target_tokens and item_tokens.issubset(target_tokens):
                continue
            unique.append(item)
        return unique[:32]

    def _prepare_query(
        self,
        *,
        raw_query: str,
        project_name_terms: set[str],
        business_terms: List[str],
        region: str,
    ) -> str:
        original = self._clean_text(raw_query)

        if not original:
            return ""

        # Project-description fragments are the main source of query pollution.
        # Queries longer than fourteen words are discarded before compaction.
        if len(original.split()) > 14:
            return ""

        tokens = self._tokenize_search_text(original)

        if not tokens:
            return ""

        region_tokens = set(
            self._tokenize_search_text(region)
        )
        intent_tokens = {
            "competitor",
            "competitors",
            "alternative",
            "alternatives",
            "software",
            "logiciel",
            "platform",
            "plateforme",
            "market",
            "marché",
            "marche",
            "report",
            "rapport",
            "pricing",
            "price",
            "tarif",
            "benchmark",
        }

        business_token_set = {
            token
            for term in business_terms
            for token in self._tokenize_search_text(term)
        }

        compact_tokens: List[str] = []
        seen = set()

        for token in tokens:
            if token in self.QUERY_STOP_WORDS:
                continue

            # Project names are not evidence. They are allowed only when a
            # query already contains at least one true business term.
            if token in project_name_terms:
                continue

            if token in seen:
                continue

            if len(token) < 2:
                continue

            seen.add(token)
            compact_tokens.append(token)

        has_business_term = any(
            token in business_token_set
            for token in compact_tokens
        )

        if not has_business_term:
            return ""

        # Keep region and intent words, but remove generic filler product words
        # when the query would otherwise exceed the limit.
        if len(compact_tokens) > self.MAX_QUERY_WORDS:
            prioritized = [
                token
                for token in compact_tokens
                if token in business_token_set
                or token in region_tokens
                or token in intent_tokens
            ]

            remaining = [
                token
                for token in compact_tokens
                if token not in prioritized
            ]

            compact_tokens = (
                prioritized + remaining
            )[: self.MAX_QUERY_WORDS]

        query = " ".join(
            compact_tokens[: self.MAX_QUERY_WORDS]
        )

        if len(query.split()) < 3:
            return ""

        return self._clean_text(query)

    def _query_quality_score(
        self,
        *,
        query: str,
        business_terms: List[str],
        project_name_terms: set[str],
        region: str,
    ) -> float:
        normalized = self._normalize_search_phrase(query)
        tokens = set(self._tokenize_search_text(normalized))

        if not tokens:
            return -1.0

        business_matches = 0.0

        for term in business_terms:
            clean_term = self._normalize_search_phrase(term)

            if not clean_term:
                continue

            if self._phrase_in_text(clean_term, normalized):
                business_matches += (
                    2.0
                    if len(clean_term.split()) >= 2
                    else 1.0
                )

        non_project_business_tokens = [
            token
            for token in tokens
            if token not in project_name_terms
            and token not in self.QUERY_WEAK_TERMS
            and token not in self.QUERY_STOP_WORDS
            and len(token) >= 3
        ]

        if business_matches <= 0 or not non_project_business_tokens:
            return -1.0

        score = business_matches * 3.0

        intent_markers = {
            "competitor",
            "competitors",
            "alternative",
            "alternatives",
            "software",
            "logiciel",
            "market",
            "marché",
            "marche",
            "pricing",
            "tarif",
            "benchmark",
        }

        score += sum(
            0.75
            for marker in intent_markers
            if marker in tokens
        )

        region_tokens = set(
            self._tokenize_search_text(region)
        )

        if tokens & region_tokens:
            score += 1.0

        word_count = len(tokens)

        if 4 <= word_count <= 8:
            score += 1.0
        elif word_count > self.MAX_QUERY_WORDS:
            score -= 2.0

        return score

    def _generated_query_candidates(
        self,
        *,
        business_terms: List[str],
        industry: str,
        region: str,
    ) -> List[str]:
        region_short = self._shorten_for_search(region or "", max_words=2)
        region_normalized = self._normalize_search_phrase(region_short)
        local_fr = "Tunisie" if region_normalized in {"tunisie", "tunisia"} else region_short
        local_en = "Tunisia" if region_normalized in {"tunisie", "tunisia"} else region_short

        specific_terms = [term for term in business_terms if term]
        primary = specific_terms[0] if specific_terms else ""
        secondary = specific_terms[1] if len(specific_terms) > 1 else ""
        tertiary = specific_terms[2] if len(specific_terms) > 2 else ""

        industry_terms = [
            token
            for token in self._tokenize_search_text(industry)
            if token not in self.QUERY_WEAK_TERMS
            and token not in self.QUERY_STOP_WORDS
        ]
        industry_specific = " ".join(industry_terms[:2])

        generated = [
            f"{primary} logiciel {local_fr}",
            f"{primary} software {local_en}",
            f"{secondary} logiciel {local_fr}",
            f"{secondary} software {local_en}",
            f"{primary} concurrents {local_fr}",
            f"{primary} competitors {local_en}",
            f"{tertiary} software {local_en}",
            f"{primary} market report {local_en}",
            f"{industry_specific} benchmark {local_en}",
        ]

        return self._unique_strings([
            self._clean_text(query)
            for query in generated
            if self._clean_text(query)
        ])

    def _append_diverse_query(
        self,
        queries: List[str],
        candidate: str,
    ) -> None:
        normalized = self._normalize_search_phrase(candidate)

        if not normalized:
            return

        candidate_tokens = set(
            self._tokenize_search_text(normalized)
        )

        for existing in queries:
            existing_tokens = set(
                self._tokenize_search_text(existing)
            )

            union = candidate_tokens | existing_tokens

            if not union:
                continue

            similarity = len(
                candidate_tokens & existing_tokens
            ) / len(union)

            if similarity >= 0.78:
                return

        queries.append(candidate)

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
        region_tokens = set(self._tokenize_search_text(region))
        text = self._normalize_search_phrase(f"{industry} {idea}")
        clauses = re.split(r"[,;:|/]|\b(?:and|or|et|ou|for|pour|who|that)\b", text)
        result: List[str] = []
        for clause in clauses:
            tokens = [
                token for token in self._tokenize_search_text(clause)
                if token not in self.FALLBACK_CONCEPT_STOP_WORDS
                and token not in region_tokens
                and len(token) >= 3
            ]
            for size in (3, 2):
                for index in range(0, len(tokens) - size + 1):
                    result.append(" ".join(tokens[index:index + size]))
            for token in tokens:
                if len(token) >= 5:
                    result.append(token)
        return self._unique_strings(result)[:24]

    def _to_forge_source(
        self,
        source: Dict[str, Any],
    ) -> ForgeCrawlerSource:
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
            source_role=str(source.get("source_role") or "irrelevant"),
            canonical_category=str(source.get("canonical_category") or "irrelevant"),
            comparison_scope=str(source.get("comparison_scope") or "irrelevant"),
            region_match=str(source.get("region_match") or "unknown"),
            is_direct_competitor=bool(source.get("is_direct_competitor")),
            technology_supplier=bool(source.get("technology_supplier")),
            canonical_source_id=str(source.get("canonical_source_id") or ""),
            why_relevant=str(source.get("why_relevant") or ""),
            public_reason=str(source.get("public_reason") or ""),
            source_relevance_score=self._safe_float(source.get("source_relevance_score")),
            public_display=bool(source.get("public_display")),
            internal_only=bool(source.get("internal_only")),
            rejected=bool(source.get("rejected")),
            matched_strong_terms=list(source.get("matched_strong_terms") or []),
            matched_weak_terms=list(source.get("matched_weak_terms") or []),
            matched_forbidden_terms=list(source.get("matched_forbidden_terms") or []),
            matched_domain_terms=list(source.get("matched_domain_terms") or []),
            matched_sector_terms=list(source.get("matched_sector_terms") or []),
            matched_target_terms=list(source.get("matched_target_terms") or []),
            matched_use_case_terms=list(source.get("matched_use_case_terms") or []),
            matched_solution_terms=list(source.get("matched_solution_terms") or []),
            product_evidence_signals=list(source.get("product_evidence_signals") or []),
            market_evidence_signals=list(source.get("market_evidence_signals") or []),
            evidence_categories=list(source.get("evidence_categories") or []),
            same_or_close_target_user=bool(source.get("same_or_close_target_user")),
            same_or_close_sector=bool(source.get("same_or_close_sector")),
            target_match_level=str(source.get("target_match_level") or "none"),
            is_product_page=bool(source.get("is_product_page")),
            same_or_close_use_case=bool(source.get("same_or_close_use_case")),
            same_or_close_solution_category=bool(source.get("same_or_close_solution_category")),
            clear_contextual_link=bool(source.get("clear_contextual_link")),
            rejection_reason=str(source.get("rejection_reason") or ""),
            vendor_key=str(source.get("vendor_key") or ""),
            vendor_name=str(source.get("vendor_name") or ""),
            canonical_vendor_domain=str(source.get("canonical_vendor_domain") or ""),
            sector_mismatch=bool(source.get("sector_mismatch")),
            mismatch_terms=list(source.get("mismatch_terms") or []),
            search_provider=str(source.get("search_provider") or ""),
            provider_score=self._safe_float(source.get("provider_score"), 0.0),
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
        # Backward-compatible wrapper. The public confidence now represents
        # evidence coverage, not simply the number of discovered URLs.
        return self._evidence_confidence(
            public_sources=public_sources,
            local_competitors=local_competitors,
        )["overall_evidence_confidence"]

    def _evidence_confidence(
        self,
        *,
        public_sources: List[ForgeCrawlerSource],
        local_competitors: List[ForgeCrawlerSource],
    ) -> Dict[str, str]:
        product_benchmarks = [
            source for source in public_sources
            if source.canonical_category in {
                "direct_competitor",
                "adjacent_solution",
                "technology_benchmark",
            }
            and (
                "solution_benchmark" in set(source.evidence_categories or [])
                or "technology_benchmark" in set(source.evidence_categories or [])
                or "adjacent_solution" in set(source.evidence_categories or [])
            )
        ]
        market_size_sources = [
            source for source in public_sources
            if "market_size" in set(source.evidence_categories or [])
        ]
        demand_sources = [
            source for source in public_sources
            if "market_demand" in set(source.evidence_categories or [])
        ]

        discovery = "high" if len(public_sources) >= 6 else (
            "medium" if len(public_sources) >= 2 else "low"
        )
        solution = "high" if len(product_benchmarks) >= 3 else (
            "medium" if product_benchmarks else "low"
        )
        local = "high" if len(local_competitors) >= 2 else (
            "medium" if len(local_competitors) == 1 else "low"
        )
        market_size = "high" if len(market_size_sources) >= 2 else (
            "medium" if len(market_size_sources) == 1 else "low"
        )
        market_demand = "high" if len(demand_sources) >= 2 else (
            "medium" if len(demand_sources) == 1 else "low"
        )

        # High overall confidence requires multiple independent evidence
        # categories. Many international products alone cannot produce High.
        if (
            market_size in {"medium", "high"}
            and market_demand in {"medium", "high"}
            and (local in {"medium", "high"} or solution == "high")
        ):
            overall = "high"
        elif len(public_sources) >= 2 and solution in {"medium", "high"}:
            overall = "medium"
        elif len(public_sources) >= 2 and (market_size != "low" or market_demand != "low"):
            overall = "medium"
        else:
            overall = "low"

        return {
            "discovery_confidence": discovery,
            "solution_benchmark_confidence": solution,
            "local_competition_confidence": local,
            "market_size_confidence": market_size,
            "market_demand_confidence": market_demand,
            "overall_evidence_confidence": overall,
        }

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

    def _safe_float(
        self,
        value: Any,
        fallback: float = 0.0,
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _detect_pricing(self, text: str) -> bool:
        normalized = self._normalize_search_phrase(text)

        if not normalized:
            return False

        pricing_words = {
            "pricing",
            "price",
            "prices",
            "plans",
            "subscription",
            "subscriptions",
            "tarif",
            "tarifs",
            "abonnement",
            "mensuel",
            "monthly",
        }

        tokens = set(
            self._tokenize_search_text(normalized)
        )

        if tokens & pricing_words:
            return True

        currency_pattern = (
            r"(?:\$|€|\b(?:tnd|usd|eur|dt)\b)"
            r"\s*\d"
            r"|\d\s*(?:\$|€|\b(?:tnd|usd|eur|dt)\b)"
        )

        return bool(
            re.search(currency_pattern, normalized)
        )

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

    PRODUCT_SOURCE_TYPES = {"competitor", "pricing_page", "adjacent_solution", "technology_benchmark"}

    VENDOR_NAME_OVERRIDES = {
        "workday": "Workday",
        "workforcesoftware": "WorkForce Software",
        "qgenda": "QGenda",
        "dayforce": "Dayforce",
        "paycor": "Paycor",
        "isolvedhcm": "isolved HCM",
        "joinhomebase": "Homebase",
        "combohr": "Combo",
        "talenteo": "Talenteo",
    }

    def _enrich_vendor_identity(self, source: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(source)
        url = str(source.get("url") or "")
        domain = self._registrable_domain(self._domain_from_url(url))
        source_type = str(source.get("source_type") or "").lower()
        if source_type not in self.PRODUCT_SOURCE_TYPES or not domain:
            enriched.setdefault("vendor_key", "")
            enriched.setdefault("vendor_name", "")
            enriched.setdefault("canonical_vendor_domain", domain)
            return enriched

        stem = domain.split(".")[0].replace("-", "").replace("_", "")
        vendor_name = self.VENDOR_NAME_OVERRIDES.get(stem)
        if not vendor_name:
            raw_stem = domain.split(".")[0].replace("-", " ").replace("_", " ")
            vendor_name = " ".join(part.capitalize() for part in raw_stem.split())

        enriched["canonical_vendor_domain"] = domain
        enriched["vendor_key"] = f"vendor:{domain}"
        enriched["vendor_name"] = vendor_name or str(source.get("title") or domain)
        return enriched

    def _registrable_domain(self, domain: str) -> str:
        clean = str(domain or "").lower().strip(".").replace("www.", "")
        labels = [label for label in clean.split(".") if label]
        if len(labels) <= 2:
            return clean
        two_level_suffixes = {
            "co.uk", "org.uk", "com.au", "com.br", "co.za",
            "com.tn", "org.tn", "net.tn", "gov.tn", "edu.tn",
            "co.in", "co.jp", "com.sg", "com.sa", "com.ae",
        }
        suffix = ".".join(labels[-2:])
        if suffix in two_level_suffixes and len(labels) >= 3:
            return ".".join(labels[-3:])
        return ".".join(labels[-2:])

    def _canonical_source_key(self, source: Dict[str, Any]) -> str:
        url = str(source.get("url") or "")

        if not self._is_valid_url(url):
            return ""

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        source_type = str(source.get("source_type") or "").lower()
        vendor_key = str(source.get("vendor_key") or "").strip().lower()
        if source_type in self.PRODUCT_SOURCE_TYPES:
            if vendor_key:
                return vendor_key

            # `_select_public_sources()` is also exercised directly by unit
            # tests and legacy callers, before `_enrich_vendor_identity()` has
            # necessarily created a vendor key. In that case, use the exact
            # normalized host rather than the registrable domain. Collapsing
            # every `*.example.com` or shared-hosting subdomain into one vendor
            # incorrectly removes distinct products before diversity selection.
            if domain:
                return f"vendor:{domain}"

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
        kept, _ = self._select_public_sources(sources, enforce_limit=False)
        return kept

    def _public_source_rank(self, source: Dict[str, Any]) -> float:
        source_type = str(source.get("source_type") or "").lower()
        categories = set(source.get("evidence_categories") or [])
        score = self._safe_float(source.get("source_relevance_score"), 0.0)

        type_weight = {
            "competitor": 3.0,
            "pricing_page": 2.9,
            "adjacent_solution": 2.4,
            "technology_benchmark": 2.1,
            "regulation": 1.8,
            "market_article": 1.3,
            "directory": 0.7,
        }.get(source_type, 0.0)

        evidence_weight = 0.0
        if source.get("is_direct_competitor"):
            evidence_weight += 3.0
        if "competitor_product" in categories:
            evidence_weight += 1.2
        if "solution_benchmark" in categories:
            evidence_weight += 0.8
        if "market_size" in categories:
            evidence_weight += 1.0
        if "market_demand" in categories:
            evidence_weight += 0.8
        if "problem_context" in categories:
            evidence_weight += 0.4
        if "regulation" in categories:
            evidence_weight += 0.5

        specificity = min(1.0, 0.08 * len(source.get("matched_domain_terms") or []))
        specificity += min(0.6, 0.06 * len(source.get("matched_use_case_terms") or []))
        specificity += min(0.6, 0.06 * len(source.get("matched_solution_terms") or []))

        extraction_weight = 0.15 if source.get("text_extracted") else 0.0
        return round(type_weight + evidence_weight + specificity + extraction_weight + score, 4)

    def _source_diversity_bucket(
        self,
        source: Dict[str, Any],
    ) -> str:
        category = str(
            source.get("canonical_category")
            or source.get("source_role")
            or source.get("source_type")
            or ""
        ).strip().lower()
        role = str(source.get("source_role") or "").strip().lower()
        region_match = str(source.get("region_match") or "").strip().lower()

        if bool(source.get("is_direct_competitor")) and region_match == "local":
            return "local_direct_competitor"

        if category == "adjacent_solution" and region_match == "local":
            return "local_adjacent_solution"

        if category == "ecosystem_actor" and region_match == "local":
            return "local_ecosystem_actor"

        if category == "market_evidence" and region_match == "local":
            return "local_market_evidence"

        if category == "technology_benchmark" or role in {
            "technology_provider",
            "international_benchmark",
            "regional_benchmark",
        }:
            return "technology_benchmark"

        if category == "market_evidence":
            return "external_market_evidence"

        return "other"

    def _select_diverse_ranked_sources(
        self,
        ranked: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Select a role-diverse evidence set before filling by global rank.

        The previous global top-N selection frequently kept several commercial
        international reports while dropping all local adjacent solutions and
        ecosystem signals. The quotas below are minimum opportunities, not
        unconditional passes: every source has already passed the relevance
        gate, URL hygiene and canonical deduplication.
        """

        if limit <= 0 or len(ranked) <= limit:
            return list(ranked)

        quota_plan = (
            ("local_direct_competitor", 1),
            ("local_adjacent_solution", 2),
            ("local_market_evidence", 2),
            ("local_ecosystem_actor", 1),
            ("technology_benchmark", 1),
            ("external_market_evidence", 1),
        )

        selected_ids: set[int] = set()

        for bucket, quota in quota_plan:
            taken = 0
            for source in ranked:
                source_id = id(source)
                if source_id in selected_ids:
                    continue
                if self._source_diversity_bucket(source) != bucket:
                    continue
                selected_ids.add(source_id)
                taken += 1
                if taken >= quota or len(selected_ids) >= limit:
                    break
            if len(selected_ids) >= limit:
                break

        if len(selected_ids) < limit:
            for source in ranked:
                source_id = id(source)
                if source_id in selected_ids:
                    continue
                selected_ids.add(source_id)
                if len(selected_ids) >= limit:
                    break

        return [
            source
            for source in ranked
            if id(source) in selected_ids
        ][:limit]

    def _select_public_sources(
        self,
        sources: List[Dict[str, Any]],
        *,
        enforce_limit: bool = True,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Deduplicate and rank public sources with explicit rejection reasons."""
        best_by_key: Dict[str, Dict[str, Any]] = {}
        removed: List[Dict[str, Any]] = []

        for source in sources:
            url = str(source.get("url") or "")
            key = self._canonical_source_key(source)
            rank = self._public_source_rank(source)

            if not self._is_public_source_url(url):
                removed.append({
                    **source,
                    "canonical_key": key,
                    "public_rank": rank,
                    "hygiene_reason": "non_public_or_invalid_url",
                })
                continue

            if not key:
                removed.append({
                    **source,
                    "canonical_key": "",
                    "public_rank": rank,
                    "hygiene_reason": "missing_canonical_key",
                })
                continue

            candidate = {**source, "_public_rank": rank}
            existing = best_by_key.get(key)
            if existing is None:
                best_by_key[key] = candidate
                continue

            existing_rank = self._safe_float(existing.get("_public_rank"), 0.0)
            if rank > existing_rank:
                removed.append({
                    **existing,
                    "canonical_key": key,
                    "public_rank": existing_rank,
                    "hygiene_reason": "duplicate_replaced_by_higher_quality_variant",
                })
                best_by_key[key] = candidate
            else:
                removed.append({
                    **source,
                    "canonical_key": key,
                    "public_rank": rank,
                    "hygiene_reason": "duplicate_lower_quality_variant",
                })

        ranked = sorted(
            best_by_key.values(),
            key=lambda item: (
                self._safe_float(item.get("_public_rank"), 0.0),
                self._safe_float(item.get("source_relevance_score"), 0.0),
            ),
            reverse=True,
        )

        if enforce_limit and len(ranked) > self.max_sources:
            # Very small result sets should preserve pure evidence quality.
            # Applying six category quotas to a capacity of one or two can
            # force a weak article into the result while excluding a second
            # official product page. Production uses eight sources, where the
            # diversity plan is meaningful and prevents international reports
            # from crowding out local evidence.
            diversity_applied = self.max_sources >= 4

            if diversity_applied:
                selected = self._select_diverse_ranked_sources(
                    ranked=ranked,
                    limit=self.max_sources,
                )
            else:
                selected = ranked[: self.max_sources]

            selected_ids = {id(source) for source in selected}
            plain_top_ids = {
                id(source) for source in ranked[: self.max_sources]
            }
            diversity_changed_selection = (
                diversity_applied and selected_ids != plain_top_ids
            )
            capacity_reason = (
                "capacity_lower_priority_after_diversity"
                if diversity_changed_selection
                else "capacity_lower_priority"
            )

            for source in ranked:
                if id(source) in selected_ids:
                    continue
                removed.append({
                    **source,
                    "canonical_key": self._canonical_source_key(source),
                    "public_rank": source.get("_public_rank"),
                    "diversity_bucket": self._source_diversity_bucket(source),
                    "hygiene_reason": capacity_reason,
                })

            ranked = selected

        cleaned = []
        for source in ranked:
            item = dict(source)
            item.pop("_public_rank", None)
            cleaned.append(item)

        return cleaned, removed

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