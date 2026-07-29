# ============================================================
# backend/app/services/source_relevance_gate.py
# ============================================================
#
# SourceRelevanceGate V1.3 — Strict Source Relevance Gate
#
# Objectifs :
# - empêcher les sources parachutées ;
# - calculer source_relevance_score ;
# - séparer source publique / source interne / source rejetée ;
# - exiger des mots-clés forts réellement utiles ;
# - ignorer les mots faibles ;
# - ajouter matched_strong_terms / matched_weak_terms ;
# - ajouter rejection_reason ;
# - ne jamais afficher publiquement une source faible.
#
# Lot 9A.3 fix :
# - ne jamais utiliser search_query comme preuve de pertinence ;
# - search_query reste un signal d'audit/debug côté crawler ;
# - seule la source réelle est évaluée :
#   title + url + snippet + extracted_text_preview.
#
# Lot 9A.4 fix :
# - nettoyer les faux strong terms : quick, cart, platform that, etc. ;
# - éviter le matching trop large par simple sous-chaîne ;
# - retirer dynamiquement des forbidden terms si le terme appartient au projet ;
# - mieux classer Statista / 6wresearch / AfterShip comme sources marché ;
# - ne pas forcer de concurrent ;
# - garder le seuil public strict.
#
# Lot 9A.5 fix :
# - les articles, blogs, guides, top lists, rankings, reports et forecasts
#   deviennent market_article ou directory ;
# - ces sources ne peuvent pas devenir direct=True ;
# - seules les vraies pages produit/service peuvent devenir competitor/pricing_page.
# ============================================================

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse


@dataclass
class SourceRelevanceDecision:
    source_relevance_score: float
    public_display: bool
    internal_only: bool
    rejected: bool

    source_type: str
    region_match: str
    is_direct_competitor: bool
    confidence: str

    matched_strong_terms: List[str]
    matched_weak_terms: List[str]
    matched_forbidden_terms: List[str]

    same_or_close_target_user: bool
    same_or_close_use_case: bool
    same_or_close_solution_category: bool
    clear_contextual_link: bool

    why_relevant: str
    rejection_reason: str


class SourceRelevanceGate:
    PUBLIC_DISPLAY_THRESHOLD = 0.70
    INTERNAL_USE_THRESHOLD = 0.50

    DEFAULT_WEAK_TERMS = {
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
        "create",
        "help",
        "short",
        "lite",
        "system",
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
    }

    DEFAULT_FORBIDDEN_DEMO_TERMS = {
        "pharmacy",
        "pharmacie",
        "medicine stock",
        "stock médicaments",
        "stock medicaments",
        "super app",
        "orange max it",
        "tiktok",
        "crypto",
        "stock trading",
        "robot agricole",
        "agrobot",
        "greenhouse robot",
        "doctor appointment",
        "medical appointment",
        "clinic booking",
        "patient scheduling",
    }

    DIRECTORY_HINTS = {
        "directory",
        "annuaire",
        "list of",
        "top companies",
        "best companies",
        "companies in",
        "capterra",
        "g2",
        "tracxn",
        "f6s",
        "crunchbase",
        "clutch",
        "product hunt",
    }

    MARKET_ARTICLE_HINTS = {
        "market",
        "report",
        "article",
        "blog",
        "news",
        "insight",
        "analysis",
        "study",
        "étude",
        "etude",
        "rapport",
        "tendance",
        "trend",
    }

    REGULATION_HINTS = {
        "law",
        "regulation",
        "government",
        "ministry",
        "official",
        "réglementation",
        "reglementation",
        "ministère",
        "ministere",
        "legislation",
    }

    COMPETITOR_HINTS = {
        "pricing",
        "features",
        "product",
        "demo",
        "book a demo",
        "sign up",
        "login",
        "subscription",
        "platform",
        "software",
        "solution",
        "application",
        "app",
        "outil",
        "logiciel",
        "tarifs",
        "fonctionnalités",
        "fonctionnalites",
    }

    LOW_SIGNAL_STRONG_TERMS = {
        "quick",
        "cart",
        "fast",
        "platform that",
        "that helps",
        "helps households",
        "mobile-first platform",
        "platform that helps",
        "that helps households",
        "mobile-first platform that",
        "mobile-first platform that helps",
        "platform that helps households",
    }

    LOW_SIGNAL_PHRASE_FRAGMENTS = {
        "that helps",
        "platform that",
        "helps households",
        "mobile-first platform",
    }

    MARKET_SOURCE_DOMAINS = {
        "statista.com",
        "6wresearch.com",
        "aftership.com",
        "datareportal.com",
        "mordorintelligence.com",
        "grandviewresearch.com",
        "fortunebusinessinsights.com",
        "researchandmarkets.com",
    }

    MARKET_CONTEXT_HINTS = {
        "market forecast",
        "market size",
        "market share",
        "market report",
        "industry report",
        "statistics",
        "consumer spending",
        "revenue forecast",
        "online food delivery",
        "grocery delivery market",
        "quick commerce market",
        "ecommerce statistics",
        "e-commerce statistics",
    }

    ARTICLE_OR_LIST_HINTS = {
        "top",
        "top 5",
        "top 10",
        "top 20",
        "best",
        "best apps",
        "best companies",
        "guide",
        "blog",
        "article",
        "list of",
        "ranking",
        "comparison",
        "comparatif",
        "classement",
        "meilleurs",
        "meilleures",
        "sites e-commerce",
        "food delivery apps",
        "delivery apps",
        "market forecast",
        "market report",
        "industry report",
        "statistics",
        "statistiques",
        "trends",
        "tendances",
    }

    ARTICLE_URL_HINTS = {
        "/blog/",
        "/article/",
        "/articles/",
        "/guide/",
        "/guides/",
        "/report/",
        "/reports/",
        "/outlook/",
        "/statistics/",
        "/statistiques/",
        "/market/",
        "/industry-report/",
    }

    def evaluate_source(
        self,
        *,
        source: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = self._build_context(project_context)
        source_text = self._source_text(source)
        normalized_text = self._normalize(source_text)

        matched_strong = self._matched_terms(
            normalized_text,
            context["strong_terms"],
            ignore_terms=context["weak_terms"],
        )
        matched_weak = self._matched_terms(
            normalized_text,
            context["weak_terms"],
            ignore_terms=set(),
        )
        matched_forbidden = self._matched_terms(
            normalized_text,
            context["forbidden_terms"],
            ignore_terms=set(),
        )

        source_type = self._classify_source_type(source, normalized_text)
        region_match = self._classify_region(source, normalized_text, context)

        same_target = self._has_target_match(normalized_text, context)
        same_use_case = self._has_use_case_match(normalized_text, context)
        same_solution = self._has_solution_match(normalized_text, context)

        clear_contextual_link = bool(
            len(matched_strong) >= 2
            or (same_target and same_use_case)
            or (same_use_case and same_solution)
        )

        score = self._score(
            source=source,
            source_type=source_type,
            region_match=region_match,
            matched_strong_terms=matched_strong,
            matched_weak_terms=matched_weak,
            matched_forbidden_terms=matched_forbidden,
            same_target=same_target,
            same_use_case=same_use_case,
            same_solution=same_solution,
            clear_contextual_link=clear_contextual_link,
        )

        rejection_reason = self._rejection_reason(
            score=score,
            source_type=source_type,
            matched_strong_terms=matched_strong,
            matched_forbidden_terms=matched_forbidden,
            clear_contextual_link=clear_contextual_link,
            same_use_case=same_use_case,
            same_solution=same_solution,
        )

        rejected = bool(rejection_reason)
        public_display = (
            not rejected
            and score >= self.PUBLIC_DISPLAY_THRESHOLD
            and clear_contextual_link
            and len(matched_strong) >= 2
        )
        internal_only = (
            not rejected
            and not public_display
            and score >= self.INTERNAL_USE_THRESHOLD
        )

        is_direct_competitor = bool(
            public_display
            and source_type in {"competitor", "pricing_page"}
            and region_match == "local"
            and same_use_case
            and same_solution
            and score >= 0.78
        )

        confidence = self._confidence(
            score=score,
            public_display=public_display,
            is_direct_competitor=is_direct_competitor,
            matched_strong_terms=matched_strong,
        )

        why_relevant = self._why_relevant(
            source=source,
            source_type=source_type,
            region_match=region_match,
            matched_strong_terms=matched_strong,
            same_target=same_target,
            same_use_case=same_use_case,
            same_solution=same_solution,
            public_display=public_display,
            internal_only=internal_only,
            rejection_reason=rejection_reason,
        )

        decision = SourceRelevanceDecision(
            source_relevance_score=round(score, 2),
            public_display=public_display,
            internal_only=internal_only,
            rejected=rejected,
            source_type=source_type,
            region_match=region_match,
            is_direct_competitor=is_direct_competitor,
            confidence=confidence,
            matched_strong_terms=matched_strong[:20],
            matched_weak_terms=matched_weak[:20],
            matched_forbidden_terms=matched_forbidden[:20],
            same_or_close_target_user=same_target,
            same_or_close_use_case=same_use_case,
            same_or_close_solution_category=same_solution,
            clear_contextual_link=clear_contextual_link,
            why_relevant=why_relevant,
            rejection_reason=rejection_reason,
        )

        return asdict(decision)

    def filter_sources(
        self,
        *,
        sources: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        public_sources: List[Dict[str, Any]] = []
        internal_sources: List[Dict[str, Any]] = []
        rejected_sources: List[Dict[str, Any]] = []

        for source in sources:
            decision = self.evaluate_source(
                source=source,
                project_context=project_context,
            )

            enriched = {
                **source,
                **decision,
            }

            if decision["public_display"]:
                public_sources.append(enriched)
            elif decision["internal_only"]:
                internal_sources.append(enriched)
            else:
                rejected_sources.append(enriched)

        public_sources.sort(
            key=lambda item: float(item.get("source_relevance_score") or 0),
            reverse=True,
        )
        internal_sources.sort(
            key=lambda item: float(item.get("source_relevance_score") or 0),
            reverse=True,
        )
        rejected_sources.sort(
            key=lambda item: float(item.get("source_relevance_score") or 0),
            reverse=True,
        )

        return {
            "public_sources": public_sources,
            "internal_sources": internal_sources,
            "rejected_sources": rejected_sources,
            "public_sources_count": len(public_sources),
            "internal_sources_count": len(internal_sources),
            "rejected_sources_count": len(rejected_sources),
        }

    # ========================================================
    # Context
    # ========================================================

    def _build_context(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        project_intelligence = project_context.get("project_intelligence") or {}
        structured = (
            project_context.get("structured_project_context")
            or project_intelligence.get("structured_project_context")
            or {}
        )

        packet = (
            project_context.get("agent_context_packet")
            or project_intelligence.get("agent_context_packet")
            or {}
        )

        strong_terms = self._safe_list(project_context.get("strong_keywords"))
        strong_terms += self._safe_list(project_context.get("must_match_terms"))
        strong_terms += self._safe_list(project_context.get("anchor_terms"))
        strong_terms += self._safe_list(packet.get("strong_keywords"))
        strong_terms += self._safe_list(packet.get("must_match_terms"))

        weak_terms = set(self.DEFAULT_WEAK_TERMS)
        weak_terms.update(
            self._normalize(term)
            for term in self._safe_list(project_context.get("weak_terms_to_ignore"))
        )
        weak_terms.update(
            self._normalize(term)
            for term in self._safe_list(packet.get("weak_terms_to_ignore"))
        )

        forbidden_terms = set(self.DEFAULT_FORBIDDEN_DEMO_TERMS)
        forbidden_terms.update(
            self._normalize(term)
            for term in self._safe_list(project_context.get("forbidden_offtopic_terms"))
        )
        forbidden_terms.update(
            self._normalize(term)
            for term in self._safe_list(packet.get("forbidden_offtopic_terms"))
        )

        title = self._safe_text(
            structured.get("project_name")
            or structured.get("title")
            or project_context.get("project_name")
            or project_context.get("title")
        )

        description = self._safe_text(
            structured.get("description")
            or project_context.get("description")
        )

        industry = self._safe_text(
            structured.get("sector")
            or structured.get("industry")
            or project_context.get("sector")
            or project_context.get("industry")
        )

        region = self._safe_text(
            structured.get("target_region")
            or structured.get("market_region")
            or project_context.get("target_region")
            or project_context.get("market_region")
            or "Tunisie"
        )

        target_users = self._safe_list(
            structured.get("target_users")
            or project_context.get("target_users")
            or project_context.get("target_market")
        )

        problem = self._safe_text(
            structured.get("problem")
            or structured.get("core_problem")
            or project_context.get("problem")
            or project_context.get("core_problem")
        )

        solution = self._safe_text(
            structured.get("solution")
            or structured.get("solution_type")
            or project_context.get("solution")
            or project_context.get("solution_type")
        )

        main_use_case = self._safe_text(
            structured.get("main_use_case")
            or project_context.get("main_use_case")
            or solution
        )

        current_project_text = self._normalize(
            " ".join(
                [
                    title,
                    description,
                    industry,
                    region,
                    " ".join(target_users),
                    problem,
                    solution,
                    main_use_case,
                ]
            )
        )

        normalized_forbidden_terms = set()

        for term in forbidden_terms:
            clean = self._normalize(term)

            if not clean:
                continue

            if self._term_matches(clean, current_project_text):
                continue

            normalized_forbidden_terms.add(clean)

        context_phrases = []
        context_phrases += self._important_phrases(title)
        context_phrases += self._important_phrases(industry)
        context_phrases += target_users
        context_phrases += self._important_phrases(problem)
        context_phrases += self._important_phrases(solution)
        context_phrases += self._important_phrases(main_use_case)

        strong_terms += context_phrases

        normalized_strong_terms = []

        for term in strong_terms:
            clean = self._normalize(term)

            if not clean:
                continue

            if not self._is_useful_strong_term(clean, weak_terms):
                continue

            normalized_strong_terms.append(clean)

        return {
            "title": title,
            "description": description,
            "industry": industry,
            "region": region,
            "target_users": [self._normalize(item) for item in target_users],
            "problem": self._normalize(problem),
            "solution": self._normalize(solution),
            "main_use_case": self._normalize(main_use_case),
            "strong_terms": self._unique(normalized_strong_terms)[:80],
            "weak_terms": weak_terms,
            "forbidden_terms": normalized_forbidden_terms,
        }

    # ========================================================
    # Scoring
    # ========================================================

    def _score(
        self,
        *,
        source: Dict[str, Any],
        source_type: str,
        region_match: str,
        matched_strong_terms: List[str],
        matched_weak_terms: List[str],
        matched_forbidden_terms: List[str],
        same_target: bool,
        same_use_case: bool,
        same_solution: bool,
        clear_contextual_link: bool,
    ) -> float:
        score = 0.0

        strong_count = len(matched_strong_terms)

        if strong_count >= 6:
            score += 0.48
        elif strong_count >= 4:
            score += 0.40
        elif strong_count >= 3:
            score += 0.32
        elif strong_count >= 2:
            score += 0.22
        elif strong_count == 1:
            score += 0.08

        if same_target:
            score += 0.12

        if same_use_case:
            score += 0.16

        if same_solution:
            score += 0.14

        if clear_contextual_link:
            score += 0.08

        if source_type == "competitor":
            score += 0.10
        elif source_type == "pricing_page":
            score += 0.12
        elif source_type == "adjacent_solution":
            score += 0.07
        elif source_type == "market_article":
            score += 0.03
        elif source_type == "directory":
            score -= 0.04
        elif source_type == "irrelevant":
            score -= 0.25

        if region_match == "local":
            score += 0.08
        elif region_match == "regional":
            score += 0.04
        elif region_match == "international":
            score += 0.01

        if source.get("text_extracted"):
            score += 0.04

        if source.get("pricing_found"):
            score += 0.03

        if matched_forbidden_terms:
            score -= 0.45

        if len(matched_weak_terms) > 0 and len(matched_strong_terms) == 0:
            score -= 0.35

        if len(matched_weak_terms) >= 5 and len(matched_strong_terms) < 2:
            score -= 0.20

        return max(0.0, min(1.0, score))

    def _rejection_reason(
        self,
        *,
        score: float,
        source_type: str,
        matched_strong_terms: List[str],
        matched_forbidden_terms: List[str],
        clear_contextual_link: bool,
        same_use_case: bool,
        same_solution: bool,
    ) -> str:
        if matched_forbidden_terms:
            return "Rejected because the source matches forbidden off-topic/demo terms."

        if source_type == "irrelevant":
            return "Rejected because the source type is irrelevant to the project."

        if not matched_strong_terms:
            return "Rejected because it only matches weak or generic terms."

        if len(matched_strong_terms) < 2:
            return "Rejected because fewer than two strong contextual terms were matched."

        if not clear_contextual_link:
            return "Rejected because the contextual link to the user's exact project is not clear."

        evidence_source_types = {
            "market_article",
            "directory",
            "regulation",
        }

        if source_type not in evidence_source_types:
            if not same_use_case and not same_solution:
                return "Rejected because the source does not match the use case or solution category."

        if score < self.INTERNAL_USE_THRESHOLD:
            return "Rejected because source_relevance_score is below the internal threshold."

        return ""

    def _confidence(
        self,
        *,
        score: float,
        public_display: bool,
        is_direct_competitor: bool,
        matched_strong_terms: List[str],
    ) -> str:
        if is_direct_competitor and score >= 0.82 and len(matched_strong_terms) >= 4:
            return "high"

        if public_display and score >= 0.70:
            return "medium"

        return "low"

    # ========================================================
    # Classification
    # ========================================================

    def _classify_source_type(self, source: Dict[str, Any], normalized_text: str) -> str:
        domain = self._domain(source.get("url") or "")

        if self._looks_like_article_or_list(source, normalized_text):
            if self._contains_any(normalized_text, self.DIRECTORY_HINTS):
                return "directory"

            return "market_article"

        if self._is_market_source_domain(domain):
            return "market_article"

        if self._contains_any(normalized_text, self.MARKET_CONTEXT_HINTS):
            return "market_article"

        if self._contains_any(normalized_text, self.REGULATION_HINTS):
            return "regulation"

        if self._contains_any(normalized_text, self.DIRECTORY_HINTS):
            return "directory"

        if self._contains_any(normalized_text, self.MARKET_ARTICLE_HINTS):
            if not self._contains_any(normalized_text, self.COMPETITOR_HINTS):
                return "market_article"

        if self._has_pricing_page_signal(source, normalized_text):
            return "pricing_page"

        if self._contains_any(normalized_text, self.COMPETITOR_HINTS):
            if domain and not self._is_search_or_social_domain(domain):
                return "competitor"

        if source.get("pricing_found") and not self._looks_like_article_or_list(source, normalized_text):
            return "pricing_page"

        if domain and not self._is_search_or_social_domain(domain):
            return "adjacent_solution"

        return "irrelevant"

    def _classify_region(
        self,
        source: Dict[str, Any],
        normalized_text: str,
        context: Dict[str, Any],
    ) -> str:
        region = self._normalize(context.get("region") or "")
        url = source.get("url") or ""
        domain = self._domain(url)

        local_markers = {region}

        if "tunisie" in region or "tunisia" in region:
            local_markers.update({"tunisia", "tunisie", ".tn"})

        if "france" in region:
            local_markers.update({"france", ".fr"})

        if any(marker and marker in normalized_text for marker in local_markers):
            return "local"

        if domain.endswith(".tn") and ("tunisie" in region or "tunisia" in region):
            return "local"

        regional_markers = {
            "africa",
            "afrique",
            "mena",
            "maghreb",
            "north africa",
            "afrique du nord",
            "middle east",
        }

        if any(marker in normalized_text for marker in regional_markers):
            return "regional"

        if domain:
            return "international"

        return "unknown"

    def _has_target_match(self, normalized_text: str, context: Dict[str, Any]) -> bool:
        for item in context.get("target_users") or []:
            if item and len(item) >= 3 and self._term_matches(item, normalized_text):
                return True

            for phrase in self._important_phrases(item):
                if self._term_matches(phrase, normalized_text):
                    return True

        return False

    def _has_use_case_match(self, normalized_text: str, context: Dict[str, Any]) -> bool:
        candidates = []
        candidates += self._important_phrases(context.get("problem") or "")
        candidates += self._important_phrases(context.get("main_use_case") or "")

        matches = [
            item
            for item in candidates
            if item and self._term_matches(item, normalized_text)
        ]

        return len(matches) >= 1

    def _has_solution_match(self, normalized_text: str, context: Dict[str, Any]) -> bool:
        candidates = self._important_phrases(context.get("solution") or "")

        matches = [
            item
            for item in candidates
            if item and self._term_matches(item, normalized_text)
        ]

        return len(matches) >= 1

    # ========================================================
    # Text helpers
    # ========================================================

    def _why_relevant(
        self,
        *,
        source: Dict[str, Any],
        source_type: str,
        region_match: str,
        matched_strong_terms: List[str],
        same_target: bool,
        same_use_case: bool,
        same_solution: bool,
        public_display: bool,
        internal_only: bool,
        rejection_reason: str,
    ) -> str:
        if rejection_reason:
            return rejection_reason

        parts = [
            f"type={source_type}",
            f"region={region_match}",
            f"strong_terms={', '.join(matched_strong_terms[:5])}",
        ]

        if same_target:
            parts.append("target_match=true")

        if same_use_case:
            parts.append("use_case_match=true")

        if same_solution:
            parts.append("solution_match=true")

        if public_display:
            parts.append("public_display=true")
        elif internal_only:
            parts.append("internal_only=true")

        return " | ".join(parts)

    def _source_text(self, source: Dict[str, Any]) -> str:
        """
        Build the evidence text used for relevance evaluation.

        Important:
        - search_query is intentionally excluded.
        - Search query is an acquisition/debug signal, not evidence.
        - Including it makes irrelevant pages look relevant because the query
          already contains project keywords by construction.
        """

        return " ".join(
            [
                self._safe_text(source.get("title")),
                self._safe_text(source.get("url")),
                self._safe_text(source.get("snippet")),
                self._safe_text(source.get("extracted_text_preview")),
            ]
        )

    def _matched_terms(
        self,
        normalized_text: str,
        terms: Any,
        ignore_terms: Any,
    ) -> List[str]:
        normalized_ignore = set(ignore_terms or set())
        result: List[str] = []

        for term in terms or []:
            clean = self._normalize(term)

            if not clean:
                continue

            if clean in normalized_ignore:
                continue

            if len(clean) < 3:
                continue

            if self._term_matches(clean, normalized_text):
                result.append(clean)

        return self._unique(result)

    def _important_phrases(self, text: Any) -> List[str]:
        normalized = self._normalize(text)

        if not normalized:
            return []

        words = [
            word
            for word in re.split(r"[^a-zA-Z0-9À-ÿ]+", normalized)
            if len(word) >= 4
        ]

        phrases = []

        if len(words) >= 2:
            for size in (2, 3, 4):
                for index in range(0, max(0, len(words) - size + 1)):
                    phrases.append(" ".join(words[index : index + size]))

        if len(normalized) >= 4:
            phrases.append(normalized)

        return self._unique(phrases)[:20]

    def _contains_any(self, text: str, terms: Any) -> bool:
        return any(self._term_matches(self._normalize(term), text) for term in terms)

    def _looks_like_article_or_list(
        self,
        source: Dict[str, Any],
        normalized_text: str,
    ) -> bool:
        title = self._normalize(source.get("title") or "")
        url = self._normalize(source.get("url") or "")

        title_url_text = f"{title} {url}"

        if self._contains_any(title_url_text, self.ARTICLE_OR_LIST_HINTS):
            return True

        if any(marker in url for marker in self.ARTICLE_URL_HINTS):
            return True

        article_domains = {
            "statista.com",
            "6wresearch.com",
            "aftership.com",
            "web2code.com",
            "mallatech.tn",
            "tunisie-innovation.tn",
            "codrocket.com",
            "sensortower.com",
            "mindthebridge.com",
            "menabytes.com",
            "enests.co",
        }

        domain = self._domain(source.get("url") or "")

        if any(domain == item or domain.endswith("." + item) for item in article_domains):
            if self._contains_any(normalized_text, self.MARKET_ARTICLE_HINTS):
                return True

            if self._contains_any(title_url_text, self.ARTICLE_OR_LIST_HINTS):
                return True

        return False

    def _has_pricing_page_signal(
        self,
        source: Dict[str, Any],
        normalized_text: str,
    ) -> bool:
        title = self._normalize(source.get("title") or "")
        url = self._normalize(source.get("url") or "")

        title_url_text = f"{title} {url}"

        if self._looks_like_article_or_list(source, normalized_text):
            return False

        strong_pricing_markers = {
            "pricing",
            "price",
            "prices",
            "plans",
            "subscription",
            "tarif",
            "tarifs",
            "abonnement",
        }

        if self._contains_any(title_url_text, strong_pricing_markers):
            return True

        pricing_url_markers = {
            "/pricing",
            "/price",
            "/prices",
            "/plans",
            "/tarif",
            "/tarifs",
            "/abonnement",
        }

        if any(marker in url for marker in pricing_url_markers):
            return True

        return False

    def _is_useful_strong_term(self, term: str, weak_terms: Any) -> bool:
        clean = self._normalize(term)

        if not clean:
            return False

        if clean in weak_terms:
            return False

        if clean in self.LOW_SIGNAL_STRONG_TERMS:
            return False

        for fragment in self.LOW_SIGNAL_PHRASE_FRAGMENTS:
            if fragment in clean:
                return False

        words = [
            word
            for word in re.split(r"[^a-zA-Z0-9À-ÿ]+", clean)
            if word
        ]

        if len(words) == 1:
            word = words[0]

            if word in self.LOW_SIGNAL_STRONG_TERMS:
                return False

            if len(word) <= 4 and word not in {"hive", "miel", "lms"}:
                return False

        return True

    def _term_matches(self, term: str, text: str) -> bool:
        clean = self._normalize(term)

        if not clean or not text:
            return False

        if " " in clean:
            return clean in text

        pattern = rf"(^|[^a-zA-Z0-9À-ÿ]){re.escape(clean)}([^a-zA-Z0-9À-ÿ]|$)"

        return re.search(pattern, text) is not None

    def _is_market_source_domain(self, domain: str) -> bool:
        clean_domain = self._normalize(domain)

        return any(
            clean_domain == item or clean_domain.endswith("." + item)
            for item in self.MARKET_SOURCE_DOMAINS
        )

    def _domain(self, url: str) -> str:
        try:
            parsed = urlparse(str(url))
            return parsed.netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def _is_search_or_social_domain(self, domain: str) -> bool:
        blocked = {
            "google.com",
            "bing.com",
            "duckduckgo.com",
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "x.com",
            "twitter.com",
            "tiktok.com",
            "pinterest.com",
            "reddit.com",
        }

        return any(domain == item or domain.endswith("." + item) for item in blocked)

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [self._safe_text(item) for item in value if self._safe_text(item)]

        if isinstance(value, str):
            if "," in value or ";" in value or "/" in value:
                return [
                    item.strip()
                    for item in re.split(r",|;|/", value)
                    if item.strip()
                ]

            return [value.strip()] if value.strip() else []

        return [str(value).strip()] if str(value).strip() else []

    def _normalize(self, value: Any) -> str:
        if value is None:
            return ""

        text = str(value).lower()
        text = text.replace("’", "'")
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = self._normalize(value)

            if not clean:
                continue

            if clean in seen:
                continue

            seen.add(clean)
            result.append(clean)

        return result


source_relevance_gate = SourceRelevanceGate()