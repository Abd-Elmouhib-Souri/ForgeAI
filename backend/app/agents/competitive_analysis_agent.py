# ============================================================
# backend/app/agents/competitive_analysis_agent.py
# ============================================================
#
# CompetitiveAnalysisAgent V7 — Public Sources Aligned
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

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.services.domain_integrity_guard import normalize_output_language
from app.services.forgecrawler import ForgeCrawler


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
        "super app",
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
    }

    PUBLIC_MIN_SCORE = 0.70
    LOCAL_DIRECT_MIN_SCORE = 0.78

    def __init__(self):
        self.crawler = ForgeCrawler(max_results_per_query=10, max_sources=8)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output_language = normalize_output_language(state.get("output_language", "fr"))

        title = str(state.get("title") or "").strip()
        description = str(state.get("description") or "").strip()
        industry = str(state.get("industry") or "").strip()
        region = str(state.get("region") or "Tunisie").strip()

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

        raw_public_sources = forgecrawler_result.get("sources") or []

        safe_public_sources = self._safe_public_sources(
            sources=raw_public_sources,
            title=title,
            structured_project_context=structured_project_context,
            project_context=merged_project_context,
        )

        local_competitor_sources = self._local_direct_source_items(
            sources=safe_public_sources,
        )
        regional_competitor_sources = self._regional_source_items(
            sources=safe_public_sources,
        )
        international_benchmark_sources = self._international_source_items(
            sources=safe_public_sources,
        )
        market_context_sources = self._market_source_items(
            sources=safe_public_sources,
        )

        local_direct_competitors = self._local_direct_competitors(
            sources=safe_public_sources,
            fallback_region=region,
        )

        regional_competitors = self._regional_competitors(
            sources=safe_public_sources,
        )

        international_benchmarks = self._international_benchmarks(
            sources=safe_public_sources,
        )

        market_context_cards = self._market_context_sources(
            sources=safe_public_sources,
        )

        no_local_found = len(local_direct_competitors) == 0

        public_sources_count = len(safe_public_sources)
        raw_sources_count = len(raw_public_sources)

        source_quality = {
            "public_display_threshold": self.PUBLIC_MIN_SCORE,
            "sources_count": public_sources_count,
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
            source_quality=source_quality,
            language=output_language,
        )

        result = {
            "format": "competitive_analysis_v7_public_sources_aligned",
            "status": "completed",
            "source_based": public_sources_count > 0,
            "context_locked": True,
            "output_language": output_language,
            "confidence_level": self._public_confidence(
                safe_sources=safe_public_sources,
                local_direct_competitors=local_direct_competitors,
            ),
            "sources_count": public_sources_count,
            "local_competitors_count": len(local_direct_competitors),
            "regional_competitors_count": len(regional_competitors),
            "international_benchmarks_count": len(international_benchmarks),
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
            "market_context_sources": market_context_sources,

            # Competitor card arrays used by frontend.
            "direct_competitors": [
                item.get("name")
                for item in local_direct_competitors
                if item.get("name")
            ],
            "local_direct_competitors": local_direct_competitors,
            "local_adjacent_solutions": [],
            "regional_competitors": regional_competitors,
            "international_benchmarks": international_benchmarks,

            # Aliases for old/new frontend compatibility.
            "verified_competitors": local_direct_competitors,
            "local_competitors": local_direct_competitors,
            "market_sources": market_context_sources,
            "external_sources": {
                "sources": safe_public_sources,
                "public_sources": safe_public_sources,
                "local_competitor_sources": local_competitor_sources,
                "regional_competitor_sources": regional_competitor_sources,
                "international_benchmark_sources": international_benchmark_sources,
                "market_context_sources": market_context_sources,
                "verified_competitors": local_direct_competitors,
                "local_competitors": local_direct_competitors,
                "regional_competitors": regional_competitors,
                "international_benchmarks": international_benchmarks,
                "market_sources": market_context_sources,
            },

            "indirect_competitors": self._build_indirect_competitors(
                market_context_sources=market_context_cards,
                regional_competitors=regional_competitors,
                international_benchmarks=international_benchmarks,
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

    def _safe_public_sources(
        self,
        *,
        sources: List[Dict[str, Any]],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        safe_sources: List[Dict[str, Any]] = []

        for source in sources:
            if not self._is_public_safe_source(
                source=source,
                title=title,
                structured_project_context=structured_project_context,
                project_context=project_context,
            ):
                continue

            compact_source = self._compact_public_source(source)

            if compact_source:
                safe_sources.append(compact_source)

        safe_sources.sort(
            key=lambda item: float(item.get("source_relevance_score") or 0),
            reverse=True,
        )

        return safe_sources[:8]

    def _is_public_safe_source(
        self,
        *,
        source: Dict[str, Any],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> bool:
        if bool(source.get("rejected")):
            return False

        if not bool(source.get("public_display")):
            return False

        score = float(source.get("source_relevance_score") or 0)

        if score < self.PUBLIC_MIN_SCORE:
            return False

        source_type = str(source.get("source_type") or "").lower()

        if source_type == "irrelevant":
            return False

        if source_type == "directory" and score < 0.82:
            return False

        title_text = self._normalize(
            " ".join(
                [
                    str(source.get("title") or ""),
                    str(source.get("url") or ""),
                ]
            )
        )

        if self._contains_offtopic_title_terms(title_text):
            return False

        forbidden_terms = source.get("matched_forbidden_terms") or []

        if forbidden_terms:
            return False

        strong_terms = self._business_matched_terms(
            source=source,
            title=title,
            structured_project_context=structured_project_context,
            project_context=project_context,
        )

        if len(strong_terms) < 1:
            return False

        if not bool(source.get("clear_contextual_link")):
            return False

        if not bool(source.get("same_or_close_use_case")) and not bool(
            source.get("same_or_close_solution_category")
        ):
            if source_type not in {"market_article", "regulation"}:
                return False

        return True

    def _business_matched_terms(
        self,
        *,
        source: Dict[str, Any],
        title: str,
        structured_project_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:
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

        business_terms: List[str] = []

        for term in matched:
            if term in weak_terms:
                continue

            if term in project_name_terms:
                continue

            if len(term) < 4:
                continue

            business_terms.append(term)

        context_terms = self._context_business_terms(structured_project_context)

        for term in matched:
            if term in context_terms and term not in business_terms:
                business_terms.append(term)

        return self._unique(business_terms)

    def _compact_public_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        title = self._clean_title(source.get("title"), source.get("url"))
        url = self._safe_url(source.get("url"))

        if not title or not url:
            return {}

        score = round(float(source.get("source_relevance_score") or 0), 2)

        return {
            "title": title,
            "url": url,
            "source_relevance_score": score,
            "source_type": self._safe_label(source.get("source_type"), "source"),
            "region_match": self._safe_label(source.get("region_match"), "unknown"),
            "confidence": self._safe_label(source.get("confidence"), "low"),
            "pricing_found": bool(source.get("pricing_found")),
            "why_relevant": self._short_why_relevant(source),
            "public_display": True,
            "is_direct_competitor": bool(source.get("is_direct_competitor")),
        }

    def _short_why_relevant(self, source: Dict[str, Any]) -> str:
        source_type = self._safe_label(source.get("source_type"), "source")
        region = self._safe_label(source.get("region_match"), "unknown")
        score = round(float(source.get("source_relevance_score") or 0), 2)

        parts = [
            f"Retained as {source_type}",
            f"region={region}",
            f"relevance_score={score}",
        ]

        if bool(source.get("same_or_close_target_user")):
            parts.append("target_match=true")

        if bool(source.get("same_or_close_use_case")):
            parts.append("use_case_match=true")

        if bool(source.get("same_or_close_solution_category")):
            parts.append("solution_match=true")

        return " | ".join(parts)[:280]

    # ========================================================
    # Canonical source groups
    # ========================================================

    def _local_direct_source_items(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []

        for source in sources:
            source_type = str(source.get("source_type") or "").lower()
            region_match = str(source.get("region_match") or "").lower()
            score = float(source.get("source_relevance_score") or 0)

            if region_match != "local":
                continue

            if source_type not in {"competitor", "pricing_page"}:
                continue

            if score < self.LOCAL_DIRECT_MIN_SCORE:
                continue

            result.append(source)

        return result[:6]

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
                "directory",
                "adjacent_solution",
            }:
                continue

            result.append(source)

        return result[:8]

    # ========================================================
    # Competitor cards
    # ========================================================

    def _local_direct_competitors(
        self,
        *,
        sources: List[Dict[str, Any]],
        fallback_region: str,
    ) -> List[Dict[str, Any]]:
        competitors: List[Dict[str, Any]] = []

        for source in sources:
            source_type = str(source.get("source_type") or "").lower()
            region_match = str(source.get("region_match") or "").lower()
            score = float(source.get("source_relevance_score") or 0)

            if region_match != "local":
                continue

            if source_type not in {"competitor", "pricing_page"}:
                continue

            if score < self.LOCAL_DIRECT_MIN_SCORE:
                continue

            competitors.append(
                {
                    "name": source.get("title"),
                    "title": source.get("title"),
                    "url": source.get("url"),
                    "source_url": source.get("url"),
                    "region": fallback_region,
                    "source_type": source_type,
                    "confidence": source.get("confidence") or "medium",
                    "source_relevance_score": score,
                    "why_relevant": source.get("why_relevant") or "",
                    "evidence": source.get("why_relevant") or "",
                    "pricing_found": bool(source.get("pricing_found")),
                }
            )

        return competitors[:5]

    def _regional_competitors(
        self,
        *,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return self._sources_to_competitor_cards(
            sources=[
                source
                for source in sources
                if str(source.get("region_match") or "").lower() == "regional"
                and str(source.get("source_type") or "").lower()
                in {"competitor", "pricing_page", "adjacent_solution"}
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
                if str(source.get("region_match") or "").lower()
                in {"international", "unknown"}
                and str(source.get("source_type") or "").lower()
                in {"competitor", "pricing_page", "adjacent_solution"}
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
                "directory",
                "adjacent_solution",
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
    ) -> List[Dict[str, Any]]:
        competitors: List[Dict[str, Any]] = []

        for source in sources:
            competitors.append(
                {
                    "name": source.get("title"),
                    "title": source.get("title"),
                    "url": source.get("url"),
                    "source_url": source.get("url"),
                    "region": source.get("region_match") or fallback_region,
                    "source_type": source.get("source_type"),
                    "confidence": source.get("confidence") or "low",
                    "source_relevance_score": source.get("source_relevance_score"),
                    "why_relevant": source.get("why_relevant") or "",
                    "evidence": source.get("why_relevant") or "",
                    "pricing_found": bool(source.get("pricing_found")),
                }
            )

        return competitors[:6]

    # ========================================================
    # Analysis text
    # ========================================================

    def _build_indirect_competitors(
        self,
        *,
        market_context_sources: List[Dict[str, Any]],
        regional_competitors: List[Dict[str, Any]],
        international_benchmarks: List[Dict[str, Any]],
        language: str,
    ) -> List[str]:
        names: List[str] = []

        for item in regional_competitors + international_benchmarks:
            name = item.get("name")
            if name:
                names.append(str(name))

        for item in market_context_sources:
            title = item.get("title")
            if title:
                names.append(str(title))

        if names:
            return self._unique(names)[:8]

        if language == "en":
            return [
                "Manual tools currently used by the target users",
                "Generic spreadsheets, messaging apps and existing workflow habits",
            ]

        return [
            "Outils manuels actuellement utilisés par la cible",
            "Tableurs, messageries et habitudes de travail existantes",
        ]

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
        source_quality: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        return {
            "format": "forgecrawler_v5_public_sanitized_summary",
            "status": forgecrawler_result.get("status") or "completed",
            "confidence_level": forgecrawler_result.get("confidence_level") or "low",
            "context_locked": True,
            "output_language": language,
            "public_display_threshold": self.PUBLIC_MIN_SCORE,
            "sources_count": len(safe_sources),
            "local_competitors_count": len(local_competitor_sources),
            "regional_competitors_count": len(regional_competitor_sources),
            "international_benchmarks_count": len(international_benchmark_sources),
            "market_sources_count": len(market_context_sources),
            "sources": safe_sources,
            "public_sources": safe_sources,
            "local_competitor_sources": local_competitor_sources,
            "regional_competitor_sources": regional_competitor_sources,
            "international_benchmark_sources": international_benchmark_sources,
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