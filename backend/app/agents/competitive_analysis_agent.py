# ============================================================
# backend/app/agents/competitive_analysis_agent.py
# ============================================================
#
# CompetitiveAnalysisAgent V7.1 — Public Sources Preserved
#
# Objectifs :
# - garder ForgeCrawler V5 comme moteur strict ;
# - ne pas inventer de concurrents ;
# - garder uniquement les sources publiques déjà validées ;
# - aligner les clés backend avec le frontend :
#   sources, public_sources, local_competitor_sources,
#   regional_competitor_sources, international_benchmark_sources,
#   market_context_sources ;
# - garder les cards concurrentielles :
#   local_direct_competitors, regional_competitors,
#   international_benchmarks ;
# - exposer __extra_analysis_data.forgecrawler avec les mêmes clés ;
# - ne pas exposer rejected/internal/debug dans le rapport public.
# ============================================================

from __future__ import annotations

import logging
import re

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.services.domain_integrity_guard import normalize_output_language
from app.services.forgecrawler import ForgeCrawler
from app.services.canonical_source_ledger import canonical_source_ledger
from app.services.source_relevance_gate import source_relevance_gate

logger = logging.getLogger(__name__)


class CompetitiveAnalysisAgent:
    OFF_TOPIC_TITLE_TERMS = {
        "network cell info",
        "opera web browser",
        "chrome web store",
        "browser extension",
        "short video generator",
        "ai short video",
        "tiktok",
        "youtube",
        "instagram",
        "facebook",
        "minecraft",
        "casino",
        "gambling",
        "crypto",
        "stock trading",
        "forex",
        "medicine stock",
        "orange max it",
        "vpn",
        "antivirus",
        "weather app",
        "speed test",
        "cellular network",
        "mobile network analyzer",
    }

    GENERIC_WEAK_TERMS = {
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
        "software",
        "logiciel",
        "saas",
        "user",
        "users",
        "customer",
        "customers",
        "client",
        "clients",
        "data",
        "lite",
        "create",
        "help",
        "short",
        "system",
        "problem",
        "problème",
        "probleme",
        "market",
        "industry",
        "product",
    }

    GENERIC_WEAK_PHRASES = {
        "the problem",
        "main problem",
        "business problem",
        "saas platform",
        "software platform",
        "digital platform",
        "software solution",
        "digital solution",
        "platform for",
        "solution for",
        "business platform",
    }

    PUBLIC_MIN_SCORE = 0.70

    def __init__(self):
        self.crawler = ForgeCrawler(max_results_per_query=10, max_sources=8)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output_language = normalize_output_language(state.get("output_language", "fr"))

        title = str(state.get("title") or "").strip()
        description = str(state.get("description") or "").strip()
        industry = str(state.get("industry") or "").strip()
        region = str(state.get("region") or "").strip()

        analysis_data = dict(state.get("analysis_data") or {})
        project_context = dict(state.get("project_context") or {})

        project_intelligence = (
            state.get("project_intelligence")
            or analysis_data.get("project_intelligence")
            or project_context.get("project_intelligence")
            or {}
        )

        structured_project_context = (
            state.get("structured_project_context")
            or analysis_data.get("structured_project_context")
            or project_context.get("structured_project_context")
            or project_intelligence.get("structured_project_context")
            or {}
        )

        agent_context_packet = (
            state.get("agent_context_packet")
            or analysis_data.get("agent_context_packet")
            or project_context.get("agent_context_packet")
            or project_intelligence.get("agent_context_packet")
            or {}
        )

        query_planner = (
            state.get("query_planner")
            or analysis_data.get("query_planner")
            or project_context.get("query_planner")
            or project_intelligence.get("query_planner")
            or {}
        )

        merged_project_context = {
            **project_context,
            "project_intelligence": project_intelligence,
            "structured_project_context": structured_project_context,
            "agent_context_packet": agent_context_packet,
            "query_planner": query_planner,
            "output_language": output_language,
            "context_locked": True,
        }

        idea = self._build_idea(
            title=title,
            description=description,
            structured_project_context=structured_project_context,
        )

        manual_urls = self._extract_manual_urls(state)

        forgecrawler_result = await self.crawler.crawl_competitors(
            idea=idea,
            industry=industry,
            region=region,
            manual_urls=manual_urls,
            project_context=merged_project_context,
            agent_context_packet=agent_context_packet,
            query_planner=query_planner,
        )

        crawler_public_sources = list(forgecrawler_result.get("sources") or [])
        raw_local_candidates = self._collect_local_market_candidates(
            state=state,
            analysis_data=analysis_data,
        )
        local_market_sources = self._reclassify_local_market_candidates(
            candidates=raw_local_candidates,
            project_context=merged_project_context,
        )
        raw_public_sources = crawler_public_sources + local_market_sources

        logger.info(
            "[CompetitiveAnalysisAgent][CanonicalMerge] "
            "crawler=%s | local_candidates=%s | local_public=%s",
            len(crawler_public_sources),
            len(raw_local_candidates),
            len(local_market_sources),
        )

        safe_public_sources = self._safe_public_sources(
            sources=raw_public_sources,
            title=title,
            structured_project_context=structured_project_context,
            project_context=merged_project_context,
        )

        source_ledger = canonical_source_ledger.build(safe_public_sources)
        safe_public_sources = list(source_ledger.get("sources") or [])
        local_competitor_sources = list(
            source_ledger.get("local_direct_competitor_sources") or []
        )
        local_adjacent_source_items = list(
            source_ledger.get("adjacent_solution_sources") or []
        )
        regional_competitor_sources = list(
            source_ledger.get("regional_benchmark_sources") or []
        )
        international_benchmark_sources = list(
            source_ledger.get("international_benchmark_sources") or []
        )
        technology_provider_sources = list(
            source_ledger.get("technology_provider_sources") or []
        )
        technology_benchmark_sources = list(
            source_ledger.get("technology_benchmark_sources") or []
        )
        ecosystem_actor_sources = list(
            source_ledger.get("ecosystem_actor_sources") or []
        )
        market_context_sources = list(
            source_ledger.get("evidence_sources") or []
        )

        # CanonicalSourceLedger already owns the local-direct grouping.
        # CompetitiveAnalysisAgent only converts that canonical bucket into
        # presentation cards; it must not recalculate directness.
        local_direct_competitors = self._sources_to_competitor_cards(
            sources=local_competitor_sources,
            fallback_region=region or "Local",
            limit=None,
        )

        regional_competitors = self._regional_competitors(
            sources=safe_public_sources,
        )

        international_benchmarks = self._international_benchmarks(
            sources=safe_public_sources,
        )
        technology_providers = self._sources_to_competitor_cards(
            sources=technology_provider_sources,
            fallback_region="Technology benchmark",
        )
        technology_benchmarks = self._sources_to_competitor_cards(
            sources=technology_benchmark_sources,
            fallback_region="Technology benchmark",
        )
        ecosystem_actors = self._sources_to_competitor_cards(
            sources=ecosystem_actor_sources,
            fallback_region=region or "Local",
        )
        local_adjacent_solutions = self._sources_to_competitor_cards(
            sources=local_adjacent_source_items,
            fallback_region=region,
        )

        market_context_cards = self._market_context_sources(
            sources=safe_public_sources,
        )

        no_local_found = len(local_direct_competitors) == 0

        public_sources_count = len(safe_public_sources)
        raw_sources_count = len(raw_public_sources)
        region_counts = self._region_counts(safe_public_sources)

        source_quality = {
            "public_display_threshold": self.PUBLIC_MIN_SCORE,
            "public_threshold_policy": "role_aware",
            "sources_count": public_sources_count,
            "canonical_sources_count": public_sources_count,
            "local_sources_count": region_counts["local"],
            "regional_sources_count": region_counts["regional"],
            "international_sources_count": region_counts["international"],
            "unknown_region_sources_count": region_counts["unknown"],
            "raw_public_sources_count_before_safety_filter": raw_sources_count,
            "removed_from_public_after_safety_filter": max(
                0,
                raw_sources_count - public_sources_count,
            ),
            "internal_sources_count": int(
                forgecrawler_result.get("internal_sources_count") or 0
            ),
            "rejected_sources_count": int(
                forgecrawler_result.get("rejected_sources_count") or 0
            ),
            "no_verified_relevant_source_found": public_sources_count == 0,
            "strict_gate_active": True,
            "public_output_sanitized": True,
        }

        forgecrawler_public_summary = self._sanitized_forgecrawler_summary(
            forgecrawler_result=forgecrawler_result,
            safe_sources=safe_public_sources,
            local_competitor_sources=local_competitor_sources,
            regional_competitor_sources=regional_competitor_sources,
            international_benchmark_sources=international_benchmark_sources,
            market_context_sources=market_context_sources,
            source_ledger=source_ledger,
            technology_provider_sources=technology_provider_sources,
            source_quality=source_quality,
            language=output_language,
        )

        result = {
            "format": "competitive_analysis_v9_canonical_source_intelligence",
            "status": "completed",
            "source_based": public_sources_count > 0,
            "context_locked": True,
            "output_language": output_language,
            "confidence_level": self._public_confidence(
                safe_sources=safe_public_sources,
                local_direct_competitors=local_direct_competitors,
            ),
            "sources_count": public_sources_count,
            "canonical_sources_count": public_sources_count,
            "local_sources_count": region_counts["local"],
            "regional_sources_count": region_counts["regional"],
            "international_sources_count": region_counts["international"],
            "unknown_region_sources_count": region_counts["unknown"],
            "canonical_source_ledger": source_ledger,
            "local_competitors_count": len(local_direct_competitors),
            "local_adjacent_solutions_count": len(local_adjacent_solutions),
            "regional_competitors_count": len(regional_competitors),
            "international_benchmarks_count": len(international_benchmarks),
            "technology_providers_count": len(technology_providers),
            "technology_benchmarks_count": len(technology_benchmarks),
            "ecosystem_actors_count": len(ecosystem_actors),
            "market_sources_count": len(market_context_sources),
            "no_local_competitor_found": no_local_found,
            "no_verified_relevant_source_found": public_sources_count == 0,
            "no_source_message": (
                "No verified relevant source found."
                if output_language == "en"
                else "Aucune source pertinente vérifiée trouvée."
            ) if public_sources_count == 0 else "",

            # Canonical source arrays used by backend restore + frontend.
            "sources": safe_public_sources,
            "public_sources": safe_public_sources,
            "local_competitor_sources": local_competitor_sources,
            "regional_competitor_sources": regional_competitor_sources,
            "international_benchmark_sources": international_benchmark_sources,
            "technology_provider_sources": technology_provider_sources,
            "technology_benchmark_sources": technology_benchmark_sources,
            "ecosystem_actor_sources": ecosystem_actor_sources,
            "market_context_sources": market_context_sources,

            # Competitor card arrays used by frontend.
            "direct_competitors": [
                item.get("name")
                for item in local_direct_competitors
                if item.get("name")
            ],
            "local_direct_competitors": local_direct_competitors,
            "local_adjacent_solutions": local_adjacent_solutions,
            "regional_competitors": regional_competitors,
            "international_benchmarks": international_benchmarks,
            "technology_providers": technology_providers,
            "technology_benchmarks": technology_benchmarks,
            "ecosystem_actors": ecosystem_actors,
            "technology_provider_sources": technology_provider_sources,

            # Aliases for old/new frontend compatibility.
            "verified_competitors": local_direct_competitors,
            "local_competitors": local_direct_competitors,
            "market_sources": market_context_sources,
            "external_sources": {
                "sources_count": public_sources_count,
                "canonical_sources_count": public_sources_count,
                "local_sources_count": region_counts["local"],
                "regional_sources_count": region_counts["regional"],
                "international_sources_count": region_counts["international"],
                "unknown_region_sources_count": region_counts["unknown"],
                "local_competitors_count": len(local_direct_competitors),
                "local_adjacent_solutions_count": len(local_adjacent_solutions),
                "regional_competitors_count": len(regional_competitors),
                "international_benchmarks_count": len(international_benchmarks),
                "technology_providers_count": len(technology_providers),
                "technology_benchmarks_count": len(technology_benchmarks),
                "ecosystem_actors_count": len(ecosystem_actors),
                "market_sources_count": len(market_context_sources),
                "canonical_source_ledger": source_ledger,
                "sources": safe_public_sources,
                "public_sources": safe_public_sources,
                "local_competitor_sources": local_competitor_sources,
                "regional_competitor_sources": regional_competitor_sources,
                "international_benchmark_sources": international_benchmark_sources,
                "technology_provider_sources": technology_provider_sources,
                "technology_benchmark_sources": technology_benchmark_sources,
                "ecosystem_actor_sources": ecosystem_actor_sources,
                "adjacent_solution_sources": local_adjacent_source_items,
                "market_context_sources": market_context_sources,
                "verified_competitors": local_direct_competitors,
                "local_competitors": local_direct_competitors,
                "regional_competitors": regional_competitors,
                "international_benchmarks": international_benchmarks,
                "technology_providers": technology_providers,
                "technology_benchmarks": technology_benchmarks,
                "ecosystem_actors": ecosystem_actors,
                "market_sources": market_context_sources,
            },

            "indirect_competitors": self._build_indirect_competitors(
                market_context_sources=market_context_cards,
                adjacent_solutions=local_adjacent_solutions,
                regional_competitors=regional_competitors,
                international_benchmarks=international_benchmarks,
                structured_project_context=structured_project_context,
                language=output_language,
            ),
            "competitive_advantages": self._competitive_advantages(
                title=title,
                structured_project_context=structured_project_context,
                no_local_found=no_local_found,
                language=output_language,
            ),
            "market_gap": self._market_gap(
                title=title,
                region=region,
                no_local_found=no_local_found,
                local_direct_competitors=local_direct_competitors,
                language=output_language,
            ),
            "limitations": self._limitations(
                forgecrawler_result=forgecrawler_result,
                safe_sources=safe_public_sources,
                local_direct_competitors=local_direct_competitors,
                language=output_language,
            ),
            "source_quality": source_quality,
            "__extra_analysis_data": {
                "forgecrawler": forgecrawler_public_summary,
            },
        }

        return result

    # ========================================================
    # Public source safety
    # ========================================================

    def _collect_local_market_candidates(
        self,
        *,
        state: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Collect the local RAG hand-off from every supported state shape.

        The Business Analyst is executed before this graph in the current
        orchestration. Its result is therefore normally stored under
        ``analysis_data["business_analysis"]``. Older versions of this agent
        only inspected top-level keys and silently lost valid local pages.

        The collector intentionally accepts both the canonical candidate key
        and the legacy public-only key, then de-duplicates by canonical URL.
        It does not trust the previous classification: every item is evaluated
        again by ``_reclassify_local_market_candidates`` with the complete
        project-intelligence packet.
        """
        containers = [
            ("state", state),
            ("analysis_data", analysis_data),
            ("state.business_analysis", state.get("business_analysis")),
            (
                "analysis_data.business_analysis",
                analysis_data.get("business_analysis"),
            ),
            (
                "analysis_data.business_analyst",
                analysis_data.get("business_analyst"),
            ),
        ]

        collected: List[Dict[str, Any]] = []
        seen: set[str] = set()
        origin_counts: Dict[str, int] = {}

        for origin, container in containers:
            if not isinstance(container, dict):
                continue

            for key in ("local_market_candidates", "local_market_sources"):
                values = container.get(key) or []
                if not isinstance(values, list):
                    continue

                for item in values:
                    if not isinstance(item, dict) or not item.get("url"):
                        continue

                    normalized_url = self._normalized_source_url(
                        str(item.get("url") or "")
                    )
                    dedupe_key = normalized_url or self._normalize(
                        f"{item.get('title', '')}|{item.get('url', '')}"
                    )
                    if not dedupe_key or dedupe_key in seen:
                        continue

                    seen.add(dedupe_key)
                    collected.append(dict(item))
                    origin_counts[origin] = origin_counts.get(origin, 0) + 1

        logger.info(
            "[CompetitiveAnalysisAgent][LocalCandidateHandoff] "
            "total=%s | origins=%s",
            len(collected),
            origin_counts,
        )

        return collected

    def _reclassify_local_market_candidates(
        self,
        *,
        candidates: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Re-evaluate local RAG candidates with the complete project packet.

        LocalMarketSearch keeps useful internal candidates for semantic RAG.
        The business analyst previously discarded those candidates before the
        canonical ledger. This method performs one authoritative final gate
        using the preserved extracted-text preview and returns only sources
        that are now safe for public evidence.
        """
        public_sources: List[Dict[str, Any]] = []

        for candidate in candidates:
            gate_input = {
                **candidate,
                "extracted_text_preview": (
                    candidate.get("extracted_text_preview")
                    or candidate.get("body")
                    or candidate.get("snippet")
                    or ""
                ),
                "body": (
                    candidate.get("body")
                    or candidate.get("extracted_text_preview")
                    or candidate.get("snippet")
                    or ""
                ),
            }
            decision = source_relevance_gate.evaluate_source(
                source=gate_input,
                project_context=project_context,
            )
            enriched = {**candidate, **decision}

            logger.info(
                "[CompetitiveAnalysisAgent][LocalCandidate] "
                "title=%s | role=%s | region=%s | score=%s | "
                "public=%s | internal=%s | rejected=%s | forbidden=%s",
                enriched.get("title"),
                enriched.get("source_role"),
                enriched.get("region_match"),
                enriched.get("source_relevance_score"),
                enriched.get("public_display"),
                enriched.get("internal_only"),
                enriched.get("rejected"),
                enriched.get("matched_forbidden_terms") or [],
            )

            if (
                bool(enriched.get("public_display"))
                and not bool(enriched.get("internal_only"))
                and not bool(enriched.get("rejected"))
            ):
                public_sources.append(enriched)

        return public_sources

    def _safe_public_sources(
        self,
        *,
        sources: List[Dict[str, Any]],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Apply a final, lightweight public-safety check.

        ForgeCrawler and SourceRelevanceGate have already:
        - classified each candidate;
        - calculated relevance;
        - separated public, internal and rejected sources;
        - applied URL hygiene.

        This agent must not repeat the complete relevance gate. It only
        removes malformed sources and obvious generic false positives.
        """

        safe_sources: List[Dict[str, Any]] = []

        for source in sources:
            rejection_reason = self._public_source_rejection_reason(
                source=source,
                title=title,
                structured_project_context=structured_project_context,
                project_context=project_context,
            )

            if rejection_reason:
                logger.info(
                    "[CompetitiveAnalysisAgent][SourceRejected] "
                    "title=%s | type=%s | score=%s | reason=%s",
                    source.get("title") if isinstance(source, dict) else None,
                    source.get("source_type") if isinstance(source, dict) else None,
                    (
                        source.get("source_relevance_score")
                        if isinstance(source, dict)
                        else None
                    ),
                    rejection_reason,
                )
                continue

            compact_source = self._compact_public_source(source)

            if not compact_source:
                logger.info(
                    "[CompetitiveAnalysisAgent][SourceRejected] "
                    "title=%s | reason=invalid_public_shape",
                    source.get("title") if isinstance(source, dict) else None,
                )
                continue

            safe_sources.append(compact_source)

            logger.info(
                "[CompetitiveAnalysisAgent][SourceRetained] "
                "title=%s | type=%s | region=%s | score=%s",
                compact_source.get("title"),
                compact_source.get("source_type"),
                compact_source.get("region_match"),
                compact_source.get("source_relevance_score"),
            )

        safe_sources.sort(
            key=lambda item: float(item.get("source_relevance_score") or 0),
            reverse=True,
        )
        safe_sources = self._dedupe_vendor_sources(safe_sources)
        safe_sources = safe_sources[:8]

        logger.info(
            "[CompetitiveAnalysisAgent][AUDIT] "
            "raw_public=%s | safe_public=%s | titles=%s",
            len(sources),
            len(safe_sources),
            [item.get("title") for item in safe_sources],
        )

        return safe_sources

    def _is_public_safe_source(
        self,
        *,
        source: Dict[str, Any],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> bool:
        """
        Backward-compatible boolean wrapper.

        The detailed and auditable decision is centralized in
        `_public_source_rejection_reason`.
        """

        return not bool(
            self._public_source_rejection_reason(
                source=source,
                title=title,
                structured_project_context=structured_project_context,
                project_context=project_context,
            )
        )

    def _public_source_rejection_reason(
        self,
        *,
        source: Dict[str, Any],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> str:
        """Apply shape and contamination checks without redoing the gate.

        SourceRelevanceGate is authoritative. This final pass must never delete
        a valid technology benchmark, adjacent solution, market proof or
        ecosystem actor simply because it is not a direct competitor.
        """
        if not isinstance(source, dict):
            return "invalid_source_object"
        if bool(source.get("rejected")):
            return "already_rejected_by_source_gate"
        if bool(source.get("internal_only")):
            return "internal_only_source"
        if not bool(source.get("public_display")):
            return "not_marked_for_public_display"

        try:
            score = float(source.get("source_relevance_score") or 0)
        except (TypeError, ValueError):
            return "invalid_relevance_score"

        source_type = str(source.get("source_type") or "").strip().lower()
        source_role = str(source.get("source_role") or "").strip().lower()
        category = str(source.get("canonical_category") or "").strip().lower()
        region_match = str(source.get("region_match") or "unknown").strip().lower()

        # Backward-compatible canonicalization for already validated source
        # objects that predate Source Intelligence V8 fields. The final public
        # pass must not reject a valid adjacent solution merely because the
        # canonical_category alias was not copied by an older caller.
        if not category:
            category_aliases = {
                "competitor": "direct_competitor",
                "direct_competitor": "direct_competitor",
                "probable_direct_competitor": "probable_direct_competitor",
                "adjacent_solution": "adjacent_solution",
                "technology_benchmark": "technology_benchmark",
                "technology_provider": "technology_benchmark",
                "market_article": "market_evidence",
                "market_evidence": "market_evidence",
                "local_market_signal": "market_evidence",
                "regulation": "market_evidence",
                "directory": "ecosystem_actor",
            }
            category = category_aliases.get(source_type) or category_aliases.get(source_role, "")

        minimum_score = self.PUBLIC_MIN_SCORE
        if category == "direct_competitor" and region_match == "local":
            minimum_score = 0.58
        elif category == "adjacent_solution" and region_match == "local":
            minimum_score = 0.32
        elif category == "ecosystem_actor" and region_match == "local":
            minimum_score = 0.28
        elif category == "market_evidence" and region_match == "local":
            minimum_score = 0.36
        elif category == "market_evidence":
            minimum_score = 0.42
        elif category == "technology_benchmark":
            minimum_score = 0.40
        if score < minimum_score:
            return "score_below_role_aware_public_threshold"

        if source_type in {"", "irrelevant"} or category in {"", "irrelevant"}:
            return "irrelevant_source_type"
        if source_type == "directory" and score < 0.55:
            return "weak_directory_source"

        title_and_url = self._normalize(
            " ".join([str(source.get("title") or ""), str(source.get("url") or "")])
        )
        if self._contains_offtopic_title_terms(title_and_url):
            return "off_topic_title_or_url"
        if source.get("matched_forbidden_terms"):
            return "forbidden_context_detected"

        business_terms = self._business_matched_terms(
            source=source,
            title=title,
            structured_project_context=structured_project_context,
            project_context=project_context,
        )
        verified_direct = bool(
            category == "direct_competitor"
            and source_role == "direct_competitor"
            and bool(
                source.get(
                    "is_direct_competitor"
                )
            )
            and region_match == "local"
        )

        # SourceRelevanceGate may establish a direct competitor through
        # deterministic operational equivalence even when the public page
        # shares no literal project-domain token. Do not require a second
        # lexical business-term proof after canonical verification.
        if (
            not business_terms
            and not verified_direct
        ):
            return "no_business_specific_term"

        evidence_categories = {
            str(item).strip().lower()
            for item in (source.get("evidence_categories") or [])
            if str(item).strip()
        }
        if not evidence_categories:
            conservative_categories = {
                "direct_competitor": {"competitor_product"},
                "probable_direct_competitor": {"competitor_product"},
                "adjacent_solution": {"solution_benchmark"},
                "technology_benchmark": {"technology_benchmark", "solution_benchmark"},
                "market_evidence": {"sector_context"},
                "ecosystem_actor": {"regional_context"},
            }
            evidence_categories = conservative_categories.get(category, set())
        if not evidence_categories:
            return "missing_evidence_category"

        # SourceRelevanceGate is authoritative for direct-competitor
        # verification. This final public-safety pass must not recalculate
        # target, workflow or solution identity from lexical flags.
        if (
            category == "direct_competitor"
            and not bool(
                source.get(
                    "is_direct_competitor"
                )
            )
        ):
            return "direct_competitor_not_verified"

        return ""

    def _business_matched_terms(
        self,
        *,
        source: Dict[str, Any],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:
        """
        Keep only terms that provide real business-domain evidence.

        Generic product vocabulary, project-name tokens and phrases such as
        "SaaS platform" cannot justify publication by themselves.
        """

        matched = [
            self._normalize(item)
            for item in (source.get("matched_strong_terms") or [])
            if self._normalize(item)
        ]

        project_name_terms = set(self._project_name_terms(title))
        weak_terms = set(self.GENERIC_WEAK_TERMS)

        weak_terms.update(
            self._normalize(item)
            for item in (project_context.get("weak_terms_to_ignore") or [])
            if self._normalize(item)
        )

        context_terms = set(
            self._context_business_terms(structured_project_context)
        )

        business_terms: List[str] = []

        for term in matched:
            if not self._is_business_specific_term(
                term=term,
                weak_terms=weak_terms,
                project_name_terms=project_name_terms,
            ):
                continue

            # A term already accepted by SourceRelevanceGate remains valid.
            # Membership in context_terms is an additional positive signal,
            # not a requirement, because compact project contexts can omit
            # legitimate domain expressions found by the crawler.
            business_terms.append(term)

        # Preserve deterministic ordering and remove duplicates.
        return self._unique(business_terms)

    def _is_business_specific_term(
        self,
        *,
        term: str,
        weak_terms: set[str],
        project_name_terms: set[str],
    ) -> bool:
        normalized = self._normalize(term)

        if not normalized:
            return False

        if normalized in weak_terms:
            return False

        if normalized in self.GENERIC_WEAK_PHRASES:
            return False

        if normalized in project_name_terms:
            return False

        if len(normalized) < 4:
            return False

        tokens = {
            token.strip()
            for token in normalized.split()
            if token.strip()
        }

        if tokens and all(token in weak_terms for token in tokens):
            return False

        return True

    def _compact_public_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        title = self._clean_title(source.get("title"), source.get("url"))
        url = self._safe_url(source.get("url"))
        if not title or not url:
            return {}
        try:
            score = round(float(source.get("source_relevance_score") or 0), 2)
        except (TypeError, ValueError):
            return {}

        public_reason = str(source.get("public_reason") or "").strip()
        return {
            "title": title,
            "url": url,
            "source_relevance_score": score,
            "source_type": self._safe_label(source.get("source_type"), "source"),
            "source_role": self._safe_label(source.get("source_role"), "evidence"),
            "canonical_category": self._safe_label(
                source.get("canonical_category"),
                "market_evidence",
            ),
            "canonical_classification": self._safe_label(
                source.get("canonical_category"),
                "market_evidence",
            ),
            "comparison_scope": self._safe_label(source.get("comparison_scope"), "evidence"),
            "technology_supplier": bool(source.get("technology_supplier")),
            "canonical_source_id": str(source.get("canonical_source_id") or ""),
            "region_match": self._safe_label(source.get("region_match"), "unknown"),
            "confidence": self._safe_label(source.get("confidence"), "low"),
            "pricing_found": bool(source.get("pricing_found")),
            "why_relevant": public_reason or self._short_why_relevant(source),
            "public_reason": public_reason or self._short_why_relevant(source),
            "technical_reason": str(source.get("why_relevant") or "")[:500],
            "public_display": True,
            "is_direct_competitor": bool(source.get("is_direct_competitor")),
            "same_or_close_target_user": bool(source.get("same_or_close_target_user")),
            "same_or_close_sector": bool(source.get("same_or_close_sector")),
            "target_match_level": str(source.get("target_match_level") or "none"),
            "is_product_page": bool(source.get("is_product_page")),
            "same_or_close_use_case": bool(source.get("same_or_close_use_case")),
            "same_or_close_solution_category": bool(source.get("same_or_close_solution_category")),
            "clear_contextual_link": bool(source.get("clear_contextual_link")),
            "evidence_categories": [
                str(item).strip()
                for item in (source.get("evidence_categories") or [])
                if str(item).strip()
            ][:12],
            "matched_strong_terms": [
                str(item).strip()
                for item in (source.get("matched_strong_terms") or [])
                if str(item).strip()
            ][:12],
            "matched_domain_terms": list(source.get("matched_domain_terms") or [])[:12],
            "matched_sector_terms": list(source.get("matched_sector_terms") or [])[:10],
            "matched_target_terms": list(source.get("matched_target_terms") or [])[:10],
            "matched_use_case_terms": list(source.get("matched_use_case_terms") or [])[:10],
            "matched_solution_terms": list(source.get("matched_solution_terms") or [])[:10],
            "product_evidence_signals": list(source.get("product_evidence_signals") or [])[:10],
            "market_evidence_signals": list(source.get("market_evidence_signals") or [])[:10],
            "vendor_key": str(source.get("vendor_key") or ""),
            "vendor_name": str(source.get("vendor_name") or ""),
            "canonical_vendor_domain": str(source.get("canonical_vendor_domain") or ""),
            "sector_mismatch": bool(source.get("sector_mismatch")),
            "mismatch_terms": list(source.get("mismatch_terms") or [])[:8],
        }

    def _dedupe_vendor_sources(
        self,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for source in sources:
            canonical_id = str(source.get("canonical_source_id") or "").strip().lower()
            source_type = str(source.get("source_type") or "").lower()
            source_role = str(source.get("source_role") or "").lower()
            vendor_key = str(source.get("vendor_key") or "").strip().lower()
            normalized_url = self._normalized_source_url(str(source.get("url") or ""))
            vendor_scoped = source_type in {
                "competitor", "pricing_page", "adjacent_solution", "technology_benchmark"
            } or source_role in {
                "direct_competitor", "adjacent_solution", "regional_benchmark",
                "international_benchmark", "technology_provider",
            }
            if normalized_url:
                key = normalized_url
            elif vendor_scoped and vendor_key:
                key = vendor_key
            else:
                key = canonical_id or str(source.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(source)
        return result

    @staticmethod
    def _normalized_source_url(value: str) -> str:
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
        return f"https://{host}{path}"

    def _short_why_relevant(self, source: Dict[str, Any]) -> str:
        explicit = str(source.get("public_reason") or "").strip()
        if explicit:
            return explicit[:280]
        category = str(source.get("canonical_category") or "market_evidence").lower()
        region = str(source.get("region_match") or "unknown").lower()
        labels = {
            "direct_competitor": "Concurrent direct vérifié",
            "adjacent_solution": "Solution adjacente",
            "technology_benchmark": "Benchmark technologique",
            "market_evidence": "Preuve de marché",
            "ecosystem_actor": "Acteur de l’écosystème",
        }
        label = labels.get(category, "Source externe pertinente")
        location = "locale" if region == "local" else region
        return f"{label} retenu comme preuve {location}."[:280]

    # ========================================================
    # Canonical source groups
    # ========================================================



    def _regional_source_items(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []

        for source in sources:
            source_type = str(source.get("source_type") or "").lower()
            region_match = str(source.get("region_match") or "").lower()

            if region_match != "regional":
                continue

            if source_type not in {"competitor", "pricing_page", "adjacent_solution"}:
                continue

            result.append(source)

        return result[:6]

    def _international_source_items(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []

        for source in sources:
            source_type = str(source.get("source_type") or "").lower()
            region_match = str(source.get("region_match") or "").lower()

            if region_match not in {"international", "unknown"}:
                continue

            if source_type not in {"competitor", "pricing_page", "adjacent_solution"}:
                continue

            result.append(source)

        return result[:6]

    def _market_source_items(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []

        for source in sources:
            source_type = str(source.get("source_type") or "").lower()

            if source_type not in {
                "market_article",
                "regulation",
                "official_source",
                "local_ecosystem",
                "directory",
            }:
                continue

            result.append(source)

        return result[:8]

    # ========================================================
    # Competitor cards
    # ========================================================


    def _regional_competitors(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return self._sources_to_competitor_cards(
            sources=[
                source
                for source in sources
                if str(source.get("source_role") or "").lower() == "regional_benchmark"
            ],
            fallback_region="Regional",
        )

    def _international_benchmarks(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return self._sources_to_competitor_cards(
            sources=[
                source
                for source in sources
                if str(source.get("source_role") or "").lower()
                == "international_benchmark"
            ],
            fallback_region="International",
        )

    def _market_context_sources(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        market_sources: List[Dict[str, Any]] = []

        for source in sources:
            source_type = str(source.get("source_type") or "").lower()

            if source_type not in {
                "market_article",
                "regulation",
                "official_source",
                "local_ecosystem",
                "directory",
            }:
                continue

            market_sources.append(
                {
                    "title": source.get("title"),
                    "url": source.get("url"),
                    "source_type": source.get("source_type"),
                    "region_match": source.get("region_match"),
                    "confidence": source.get("confidence"),
                    "source_relevance_score": source.get("source_relevance_score"),
                    "why_relevant": source.get("why_relevant"),
                }
            )

        return market_sources[:6]

    def _sources_to_competitor_cards(
        self,
        *,
        sources: List[Dict[str, Any]],
        fallback_region: str,
        limit: Optional[int] = 6,
    ) -> List[Dict[str, Any]]:
        competitors: List[Dict[str, Any]] = []

        for source in sources:
            raw_region = str(source.get("region_match") or "").strip().lower()
            display_region = raw_region if raw_region in {"local", "regional", "international"} else fallback_region
            competitors.append(
                {
                    "name": source.get("vendor_name") or source.get("title"),
                    "title": source.get("title"),
                    "url": source.get("url"),
                    "source_url": source.get("url"),
                    "region": display_region,
                    "region_match": raw_region or display_region.lower(),
                    "source_type": source.get("source_type"),
                    "source_role": source.get("source_role"),
                    "comparison_scope": source.get("comparison_scope"),
                    "technology_supplier": bool(source.get("technology_supplier")),
                    "canonical_source_id": source.get("canonical_source_id"),
                    "confidence": source.get("confidence") or "low",
                    "source_relevance_score": source.get("source_relevance_score"),
                    "why_relevant": source.get("why_relevant") or "",
                    "evidence": source.get("why_relevant") or "",
                    "pricing_found": bool(source.get("pricing_found")),
                    "vendor_key": source.get("vendor_key"),
                    "canonical_vendor_domain": source.get("canonical_vendor_domain"),
                    "sector_mismatch": bool(source.get("sector_mismatch")),
                    "mismatch_terms": source.get("mismatch_terms") or [],
                }
            )

        if limit is None:
            return competitors

        return competitors[:limit]

    # ========================================================
    # Analysis text
    # ========================================================

    def _build_indirect_competitors(
        self,
        *,
        market_context_sources: List[Dict[str, Any]],
        regional_competitors: List[Dict[str, Any]],
        international_benchmarks: List[Dict[str, Any]],
        structured_project_context: Dict[str, Any],
        language: str,
        adjacent_solutions: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """Build indirect alternatives without vertical-specific knowledge.

        Canonical source buckets remain authoritative whenever real adjacent
        solutions or benchmarks exist. When no named alternative is available,
        the fallback describes structural substitutes derived only from the
        locked project context: workflow, actors and transaction/value unit.

        Editorial evidence is never converted into a competitor.
        """

        names: List[str] = []

        canonical_alternatives = (
            list(adjacent_solutions or [])
            + list(regional_competitors or [])
            + list(international_benchmarks or [])
        )

        for item in canonical_alternatives:
            name = str(
                item.get("name")
                or item.get("title")
                or ""
            ).strip()

            if name:
                names.append(
                    name
                )

        if names:
            return self._unique(
                names
            )[:8]

        # Market articles, reports, directories and regulations are evidence,
        # not competitors. The parameter is intentionally not used to create
        # alternative names.
        _ = market_context_sources

        def _values(
            value: Any,
        ) -> List[str]:
            if value is None:
                return []

            if isinstance(
                value,
                str,
            ):
                clean = value.strip()
                return [clean] if clean else []

            if isinstance(
                value,
                (
                    list,
                    tuple,
                    set,
                ),
            ):
                return self._unique(
                    [
                        str(item or "").strip()
                        for item in value
                        if str(item or "").strip()
                    ]
                )

            return []

        workflows = _values(
            structured_project_context.get(
                "priority_workflows"
            )
        )

        for key in (
            "priority_workflow",
            "main_use_case",
        ):
            value = str(
                structured_project_context.get(
                    key
                )
                or ""
            ).strip()

            if value:
                workflows.append(
                    value
                )

        workflows = self._unique(
            workflows
        )

        primary_workflow = (
            workflows[0]
            if workflows
            else ""
        )

        actor_names = _values(
            structured_project_context.get(
                "target_users"
            )
        )

        for actor in (
            structured_project_context.get(
                "actor_details"
            )
            or []
        ):
            if not isinstance(
                actor,
                dict,
            ):
                continue

            name = str(
                actor.get("name")
                or ""
            ).strip()

            if name:
                actor_names.append(
                    name
                )

        actor_names = self._unique(
            actor_names
        )

        transaction_text = str(
            structured_project_context.get(
                "transaction_unit_text"
            )
            or ""
        ).strip()

        if not transaction_text:
            transaction = (
                structured_project_context.get(
                    "transaction_unit"
                )
                or {}
            )

            if isinstance(
                transaction,
                dict,
            ):
                transaction_text = str(
                    transaction.get(
                        "sentence"
                    )
                    or ""
                ).strip()

        alternatives: List[str] = []

        if language == "en":
            if primary_workflow:
                alternatives.append(
                    "Manual or offline execution of the core workflow: "
                    + primary_workflow
                )
            else:
                alternatives.append(
                    "Manual or offline execution of the core workflow"
                )

            if len(actor_names) >= 2:
                alternatives.append(
                    "Direct coordination between "
                    + actor_names[0]
                    + " and "
                    + actor_names[1]
                    + " without the proposed product"
                )
            elif actor_names:
                alternatives.append(
                    "Direct coordination outside the proposed product for "
                    + actor_names[0]
                )
            else:
                alternatives.append(
                    "Direct coordination outside the proposed product"
                )

            if (
                transaction_text
                and transaction_text.casefold()
                != primary_workflow.casefold()
            ):
                alternatives.append(
                    "General-purpose tools as substitutes for the same "
                    "transaction or value unit: "
                    + transaction_text
                    + " (to validate in the target market)"
                )
            else:
                alternatives.append(
                    "General-purpose tools as substitutes for the same "
                    "workflow (to validate in the target market)"
                )

        else:
            if primary_workflow:
                alternatives.append(
                    "Exécution manuelle ou hors ligne du workflow principal : "
                    + primary_workflow
                )
            else:
                alternatives.append(
                    "Exécution manuelle ou hors ligne du workflow principal"
                )

            if len(actor_names) >= 2:
                alternatives.append(
                    "Coordination directe entre "
                    + actor_names[0]
                    + " et "
                    + actor_names[1]
                    + " sans le produit proposé"
                )
            elif actor_names:
                alternatives.append(
                    "Coordination directe hors du produit proposé pour "
                    + actor_names[0]
                )
            else:
                alternatives.append(
                    "Coordination directe hors du produit proposé"
                )

            if (
                transaction_text
                and transaction_text.casefold()
                != primary_workflow.casefold()
            ):
                alternatives.append(
                    "Outils généralistes comme substituts de la même "
                    "transaction ou unité de valeur : "
                    + transaction_text
                    + " (à valider sur le marché cible)"
                )
            else:
                alternatives.append(
                    "Outils généralistes comme substituts du même workflow "
                    "(à valider sur le marché cible)"
                )

        return self._unique(
            alternatives
        )[:8]

    def _competitive_advantages(
        self,
        *,
        title: str,
        structured_project_context: Dict[str, Any],
        no_local_found: bool,
        language: str,
    ) -> List[str]:
        target_users = structured_project_context.get("target_users") or []
        use_case = (
            structured_project_context.get("main_use_case")
            or structured_project_context.get("solution")
            or ""
        )

        target = ", ".join(target_users[:3]) if target_users else (
            "target users" if language == "en" else "utilisateurs cibles"
        )

        if language == "en":
            advantages = [
                f"Focused positioning for {target}.",
                f"Use-case specificity around: {use_case or 'the validated core workflow'}.",
                "Opportunity to start with a narrow MVP instead of a broad generic platform.",
            ]

            if no_local_found:
                advantages.append(
                    "No verified local direct competitor was retained in public sources, which may create an entry opportunity if field validation confirms the gap."
                )

            return advantages

        advantages = [
            f"Positionnement ciblé pour {target}.",
            f"Spécialisation sur le cas d’usage : {use_case or 'le flux métier principal validé'}.",
            "Possibilité de démarrer avec un MVP réduit au lieu d’une plateforme générique trop large.",
        ]

        if no_local_found:
            advantages.append(
                "Aucun concurrent local direct vérifié n’a été retenu dans les sources publiques, ce qui peut créer une opportunité si la validation terrain confirme le besoin."
            )

        return advantages

    def _market_gap(
        self,
        *,
        title: str,
        region: str,
        no_local_found: bool,
        local_direct_competitors: List[Dict[str, Any]],
        language: str,
    ) -> str:
        if language == "en":
            if no_local_found:
                return (
                    f"No verified local direct competitor was retained for {title} in {region}. "
                    "This does not prove the market is empty; the gap must be validated through interviews, field tests and manual competitor checks."
                )

            names = ", ".join(
                item.get("name", "")
                for item in local_direct_competitors[:3]
                if item.get("name")
            )

            return (
                f"Verified local competitors were retained: {names}. "
                "The gap should be searched in specialization, onboarding, pricing, local workflow fit and measurable customer value."
            )

        if no_local_found:
            return (
                f"Aucun concurrent local direct vérifié n’a été retenu pour {title} en {region}. "
                "Cela ne prouve pas que le marché est vide ; le gap doit être validé par entretiens, tests terrain et vérification manuelle des concurrents."
            )

        names = ", ".join(
            item.get("name", "")
            for item in local_direct_competitors[:3]
            if item.get("name")
        )

        return (
            f"Des concurrents locaux vérifiés ont été retenus : {names}. "
            "Le gap doit être recherché dans la spécialisation, l’onboarding, le prix, l’adaptation au workflow local et la valeur client mesurable."
        )

    def _limitations(
        self,
        *,
        forgecrawler_result: Dict[str, Any],
        safe_sources: List[Dict[str, Any]],
        local_direct_competitors: List[Dict[str, Any]],
        language: str,
    ) -> List[str]:
        limitations: List[str] = []

        rejected_count = int(forgecrawler_result.get("rejected_sources_count") or 0)
        raw_public_count = len(forgecrawler_result.get("sources") or [])
        safe_public_count = len(safe_sources)

        if language == "en":
            if safe_public_count == 0:
                limitations.append("No verified relevant source found.")

            if not local_direct_competitors:
                limitations.append(
                    "No verified local direct competitor was retained with enough relevance."
                )

            if rejected_count > 0:
                limitations.append(
                    f"{rejected_count} weak, generic or off-context source(s) were rejected."
                )

            if raw_public_count > safe_public_count:
                limitations.append(
                    f"{raw_public_count - safe_public_count} source(s) were removed from public output after final safety filtering."
                )

            limitations.append(
                "Public sources are compact and do not expose raw snippets, rejected-source content or weak-term matches."
            )

            return self._unique(limitations)

        if safe_public_count == 0:
            limitations.append("Aucune source pertinente vérifiée trouvée.")

        if not local_direct_competitors:
            limitations.append(
                "Aucun concurrent local direct vérifié n’a été retenu avec un niveau de pertinence suffisant."
            )

        if rejected_count > 0:
            limitations.append(
                f"{rejected_count} source(s) faibles, génériques ou hors contexte ont été rejetée(s)."
            )

        if raw_public_count > safe_public_count:
            limitations.append(
                f"{raw_public_count - safe_public_count} source(s) ont été retirée(s) de la sortie publique après filtrage final."
            )

        limitations.append(
            "Les sources publiques sont compactes et n’exposent pas les snippets bruts, le contenu rejeté ou les mots faibles."
        )

        return self._unique(limitations)

    def _public_confidence(
        self,
        *,
        safe_sources: List[Dict[str, Any]],
        local_direct_competitors: List[Dict[str, Any]],
    ) -> str:
        if len(local_direct_competitors) >= 2 and len(safe_sources) >= 4:
            return "high"

        if len(local_direct_competitors) >= 1:
            return "medium"

        if len(safe_sources) >= 3:
            return "medium"

        return "low"

    def _sanitized_forgecrawler_summary(
        self,
        *,
        forgecrawler_result: Dict[str, Any],
        safe_sources: List[Dict[str, Any]],
        local_competitor_sources: List[Dict[str, Any]],
        regional_competitor_sources: List[Dict[str, Any]],
        international_benchmark_sources: List[Dict[str, Any]],
        market_context_sources: List[Dict[str, Any]],
        source_ledger: Dict[str, Any],
        technology_provider_sources: List[Dict[str, Any]],
        source_quality: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        adjacent_sources = list(source_ledger.get("adjacent_solution_sources") or [])
        technology_sources = list(source_ledger.get("technology_benchmark_sources") or [])
        ecosystem_sources = list(source_ledger.get("ecosystem_actor_sources") or [])
        market_evidence_sources = list(source_ledger.get("market_evidence_sources") or [])
        region_counts = self._region_counts(safe_sources)
        return {
            "format": "forgecrawler_v8_public_canonical_summary",
            "status": forgecrawler_result.get("status") or "completed",
            "confidence_level": forgecrawler_result.get("confidence_level") or "low",
            "context_locked": True,
            "output_language": language,
            "public_display_threshold": self.PUBLIC_MIN_SCORE,
            "public_threshold_policy": "role_aware",
            "sources_count": len(safe_sources),
            "canonical_sources_count": len(safe_sources),
            "local_sources_count": region_counts["local"],
            "regional_sources_count": region_counts["regional"],
            "international_sources_count": region_counts["international"],
            "unknown_region_sources_count": region_counts["unknown"],
            "canonical_source_ledger": source_ledger,
            "local_competitors_count": len(local_competitor_sources),
            "adjacent_solutions_count": len(adjacent_sources),
            "regional_competitors_count": len(regional_competitor_sources),
            "international_benchmarks_count": len(international_benchmark_sources),
            "technology_benchmarks_count": len(technology_sources),
            "ecosystem_actors_count": len(ecosystem_sources),
            "market_sources_count": len(market_context_sources),
            "market_evidence_count": len(market_evidence_sources),
            "sources": safe_sources,
            "public_sources": safe_sources,
            "local_competitor_sources": local_competitor_sources,
            "adjacent_solution_sources": adjacent_sources,
            "regional_competitor_sources": regional_competitor_sources,
            "international_benchmark_sources": international_benchmark_sources,
            "technology_provider_sources": technology_provider_sources,
            "technology_benchmark_sources": technology_sources,
            "ecosystem_actor_sources": ecosystem_sources,
            "market_evidence_sources": market_evidence_sources,
            "market_context_sources": market_context_sources,
            "no_verified_relevant_source_found": len(safe_sources) == 0,
            "no_source_message": (
                "No verified relevant source found."
                if language == "en"
                else "Aucune source pertinente vérifiée trouvée."
            ) if len(safe_sources) == 0 else "",
            "source_quality": source_quality,
            "debug": {
                "strict_gate": True,
                "canonical_categories_enabled": True,
                "raw_debug_removed_from_public_payload": True,
                "rejected_sources_debug_hidden": True,
                "internal_sources_debug_hidden": True,
            },
        }

    # ========================================================
    # Context / idea helpers
    # ========================================================

    def _build_idea(
        self,
        *,
        title: str,
        description: str,
        structured_project_context: Dict[str, Any],
    ) -> str:
        parts = [
            title,
            description,
            str(structured_project_context.get("problem") or ""),
            str(structured_project_context.get("solution") or ""),
            str(structured_project_context.get("main_use_case") or ""),
            ", ".join(structured_project_context.get("target_users") or []),
        ]

        return " ".join(part.strip() for part in parts if str(part).strip())

    def _context_business_terms(
        self,
        structured_project_context: Dict[str, Any],
    ) -> List[str]:
        parts = []

        for key in [
            "sector",
            "industry",
            "problem",
            "solution",
            "main_use_case",
            "business_model",
            "mvp_scope",
        ]:
            value = structured_project_context.get(key)

            if value:
                parts.extend(self._important_phrases(str(value)))

        for user in structured_project_context.get("target_users") or []:
            parts.extend(self._important_phrases(str(user)))

        return self._unique(parts)

    def _project_name_terms(self, title: str) -> List[str]:
        normalized = self._normalize(title)

        if not normalized:
            return []

        parts = [
            part
            for part in re.split(r"[^a-zA-Z0-9À-ÿ]+", normalized)
            if len(part) >= 3
        ]

        return self._unique([normalized] + parts)

    def _region_counts(
        self,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        counts = {
            "local": 0,
            "regional": 0,
            "international": 0,
            "unknown": 0,
        }
        for source in sources:
            region = str(source.get("region_match") or "unknown").strip().lower()
            if region not in counts:
                region = "unknown"
            counts[region] += 1
        return counts

    # ========================================================
    # Generic helpers
    # ========================================================

    def _extract_manual_urls(self, state: Dict[str, Any]) -> Optional[List[str]]:
        candidates = (
            state.get("manual_urls")
            or state.get("urls")
            or (state.get("analysis_data") or {}).get("manual_urls")
        )

        if not candidates:
            return None

        if isinstance(candidates, list):
            return [str(item).strip() for item in candidates if str(item).strip()]

        if isinstance(candidates, str):
            urls = re.findall(r"https?://[^\s,;]+", candidates)
            return urls or None

        return None

    def _clean_title(self, title: Any, url: Any) -> str:
        clean = str(title or "").strip()

        if not clean:
            clean = self._domain(url)

        clean = re.sub(r"\s+", " ", clean)
        clean = clean.replace("\n", " ").strip()

        return clean[:140]

    def _safe_url(self, url: Any) -> str:
        clean = str(url or "").strip()

        if not clean:
            return ""

        parsed = urlparse(clean)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""

        return clean

    def _safe_label(self, value: Any, fallback: str) -> str:
        clean = str(value or "").strip().lower()
        clean = re.sub(r"[^a-zA-Z0-9_\- ]+", "", clean)
        clean = re.sub(r"\s+", "_", clean).strip("_")

        return clean or fallback

    def _contains_offtopic_title_terms(self, text: str) -> bool:
        return any(term in text for term in self.OFF_TOPIC_TITLE_TERMS)

    def _important_phrases(self, text: str) -> List[str]:
        normalized = self._normalize(text)

        if not normalized:
            return []

        words = [
            word
            for word in re.split(r"[^a-zA-Z0-9À-ÿ]+", normalized)
            if len(word) >= 4 and word not in self.GENERIC_WEAK_TERMS
        ]

        phrases: List[str] = []

        if len(words) >= 1:
            phrases.extend(words)

        for size in (2, 3, 4):
            for index in range(0, max(0, len(words) - size + 1)):
                phrases.append(" ".join(words[index : index + size]))

        return self._unique(phrases)[:30]

    def _domain(self, url: Any) -> str:
        try:
            parsed = urlparse(str(url or ""))
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""

    def _normalize(self, value: Any) -> str:
        text = str(value or "").lower()
        text = text.replace("’", "'")
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _unique(self, items: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for item in items:
            clean = str(item or "").strip()

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result