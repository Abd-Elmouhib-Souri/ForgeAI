# ============================================================
# backend/app/web_search/local_market_search.py
# ============================================================
#
# LocalMarketSearchService V3 — Secondary Market Context Search
#
# Objectif :
# - garder ton Bloc 3 existant ;
# - ajouter project_context ;
# - ajouter output_language ;
# - construire les requêtes depuis l'input utilisateur ;
# - filtrer les sources hors contexte ;
# - rester compatible avec l'ancien appel :
#   search_local_market(sector, region, description)
# - rester compatible avec le nouveau DynamicWebRAGService :
#   search_local_market(..., project_context=..., output_language=...)
# ============================================================

import asyncio
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from app.web_search.search_gateway import search_gateway

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder
from app.services.project_archetype_resolver import project_archetype_resolver
from app.services.source_relevance_gate import source_relevance_gate
from app.services.source_classifier import source_classifier

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_MAX_TEXT_CHARS = 6000
MIN_TEXT_CHARS = 300

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

BLOCKED_DOMAINS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "ebay.com",
    "amazon.com",
    "yandex.com",
    "kaggle.com",
    "translate.google.com",
)

BLOCKED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".zip",
    ".rar",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
)

BOT_PROTECTION_KEYWORDS = (
    "checking your browser",
    "you might be a bot",
    "making sure you're not a bot",
    "make sure you're not a bot",
    "enable cookies",
    "enable javascript",
    "access denied",
    "captcha",
    "verify you are human",
    "just a moment",
    "cloudflare",
    "anubis",
    "proof-of-work",
)


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(text: str) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\.\-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def get_url_path(url: str) -> str:
    try:
        return urlparse(url).path.lower()
    except Exception:
        return ""


def is_blocked_domain(domain: str) -> bool:
    domain = domain.lower()

    for blocked_domain in BLOCKED_DOMAINS:
        if domain == blocked_domain:
            return True

        if domain.endswith("." + blocked_domain):
            return True

    return False


def is_probably_valid_url(url: str) -> bool:
    if not url:
        return False

    if not url.startswith(("http://", "https://")):
        return False

    domain = get_domain(url)

    if is_blocked_domain(domain):
        return False

    path = get_url_path(url)

    for extension in BLOCKED_EXTENSIONS:
        if path.endswith(extension):
            return False

    return True


def looks_like_bot_protection(text: str) -> bool:
    if not text:
        return False

    lower_text = text.lower()

    return any(keyword in lower_text for keyword in BOT_PROTECTION_KEYWORDS)


class LocalMarketSearchService:
    """
    Service de recherche web locale dynamique.

    Entrée :
    - sector
    - region
    - description
    - project_context optionnel
    - output_language optionnel

    Sortie :
    [
      {
        "query": "...",
        "title": "...",
        "url": "...",
        "domain": "...",
        "snippet": "...",
        "text": "...",
        "text_length": 2500,
        "matched_project_terms": [...]
      }
    ]
    """

    def __init__(
        self,
        max_results_per_query: int = 5,
        max_pages_to_fetch: int = 6,
        max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
    ) -> None:
        self.max_results_per_query = max(2, min(int(max_results_per_query or 5), 5))
        self.max_pages_to_fetch = max(1, min(int(max_pages_to_fetch or 6), 8))
        self.max_text_chars = max(1000, int(max_text_chars or DEFAULT_MAX_TEXT_CHARS))

    def build_queries(
        self,
        sector: str,
        region: str,
        description: str = "",
        project_context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build concise bilingual local-market queries.

        French and English discovery are both required for Tunisia because local
        vendors frequently publish in one language only. Project Intelligence
        remains the source of truth; domain profiles only add narrow synonyms.
        """
        sector = clean_text(sector or "")
        region = clean_text(region or "")
        region_normalized = normalize_text(region)
        region_fr = "Tunisie" if region_normalized in {"tunisie", "tunisia"} else region
        region_en = "Tunisia" if region_normalized in {"tunisie", "tunisia"} else region
        context = self._ensure_archetype_context(
            project_context or {},
            sector=sector,
            region=region,
            description=description,
        )
        intelligence = context.get("project_intelligence") or {}
        planner = context.get("query_planner") or intelligence.get("query_planner") or {}
        queries_by_intent = planner.get("queries_by_intent") or {}

        concepts = self._specific_context_terms(context)
        primary = concepts[0] if concepts else self._compact_sector(sector)
        secondary = concepts[1] if len(concepts) > 1 else ""
        structured = (
            context.get("structured_project_context")
            or intelligence.get("structured_project_context")
            or {}
        )
        packet = context.get("agent_context_packet") or intelligence.get("agent_context_packet") or {}
        archetype_context = (
            context.get("archetype_context")
            or packet.get("archetype_context")
            or intelligence.get("archetype_context")
            or {}
        )
        workflows = self._safe_term_list(
            structured.get("priority_workflows")
            or structured.get("use_cases")
            or structured.get("use_case_terms")
        )
        workflow = workflows[0] if workflows else secondary

        archetype_terms = self._safe_term_list(archetype_context.get("search_terms"))
        semantic_text = normalize_text(
            " ".join(
                [sector, description, primary, secondary, workflow]
                + concepts[:12]
                + archetype_terms[:12]
                + self._safe_term_list(archetype_context.get("priority_workflows"))[:4]
            )
        )
        candidates: List[str] = []

        archetype_queries = archetype_context.get("search_queries") or {}
        for key in ("local_fr", "local_en", "all"):
            candidates.extend(self._safe_term_list(archetype_queries.get(key))[:6])

        # Narrow bilingual profiles fix low recall without weakening relevance.
        if any(term in semantic_text for term in (
            "workforce scheduling", "employee scheduling", "shift planning",
            "attendance tracking", "human resources", "planning equipes",
        )):
            candidates.extend([
                f"logiciel planning personnel {region_fr}",
                f"logiciel gestion horaires employes {region_fr}",
                f"application pointage presence {region_fr}",
                f"SIRH planning conges {region_fr}",
                f"workforce scheduling software {region_en}",
                f"shift planning employee attendance {region_en}",
            ])
        elif any(term in semantic_text for term in (
            "beekeeping", "beekeeper", "apiculture", "apiculteur",
            "hive management", "gestion ruches", "honey traceability",
        )):
            candidates.extend([
                f"logiciel apiculture gestion ruches {region_fr}",
                f"application apiculteur suivi ruches {region_fr}",
                f"tracabilite miel logiciel {region_fr}",
                f"beekeeping hive management software {region_en}",
                f"honey traceability software {region_en}",
            ])
        elif any(term in semantic_text for term in (
            "taxi booking", "ride hailing", "e hailing", "taxi dispatch",
            "reservation taxi", "réservation taxi", "commande taxi",
            "mise en relation taxi chauffeur",
        )):
            candidates.extend([
                f"application réservation taxi {region_fr}",
                f"commander taxi application {region_fr}",
                f"plateforme mise en relation taxi chauffeur {region_fr}",
                f"taxi booking app {region_en}",
                f"ride hailing {region_en}",
                f"taxi dispatch platform {region_en}",
            ])
        elif any(term in semantic_text for term in (
            "internship platform", "internship job board", "plateforme stages",
            "offres de stage etudiants", "offres de stage étudiants",
            "student recruitment",
        )):
            candidates.extend([
                f"plateforme stages étudiants {region_fr}",
                f"offres de stage entreprises {region_fr}",
                f"site recrutement stages {region_fr}",
                f"internship platform {region_en}",
                f"student internship job board {region_en}",
            ])

        # Generic fallback is used only when the archetype resolver could not
        # provide exact domain queries. This prevents broad sector terms such as
        # "transport software" from displacing a precise ride-hailing query.
        has_archetype_queries = any(
            self._safe_term_list(archetype_queries.get(key))
            for key in ("local_fr", "local_en", "all")
        )
        if not has_archetype_queries and primary:
            candidates.extend([
                f"{primary} logiciel {region}",
                f"{primary} software {region}",
                f"site:.tn {primary} logiciel" if normalize_text(region) in {"tunisie", "tunisia"} else f"{primary} local software {region}",
                f"{primary} statistiques officielles {region}",
                f"{primary} official statistics {region}",
            ])
        if not has_archetype_queries and workflow:
            candidates.extend([
                f"{workflow} logiciel {region}",
                f"{workflow} software {region}",
            ])

        # Keep only the strongest short planner queries after the bilingual core.
        for intent in (
            "local_solutions",
            "direct_competitors",
            "market_sources",
            "official_sources",
            "field_validation",
        ):
            values = queries_by_intent.get(intent) or []
            if isinstance(values, list):
                candidates.extend(str(item) for item in values[:1])

        cleaned: List[str] = []
        for query in candidates:
            value = self._normalize_query(query)
            if 3 <= len(value.split()) <= 9:
                cleaned.append(value)
        return self._unique_strings(cleaned)[:6]

    async def search_urls(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Search through the shared gateway and return unique URL candidates.

        LocalMarketSearch stays a secondary market-context consumer. The gateway
        owns provider selection, cache, circuit breaking and optional Gemini
        fallback, which prevents this service from launching an independent DDGS
        search path.
        """
        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        logger.info("[LocalMarketSearchService] Début recherche web dynamique")

        for query in queries:
            logger.info("[LocalMarketSearchService] Query web : %s", query)

            try:
                search_results = await search_gateway.search(
                    query,
                    min_results=min(4, self.max_results_per_query),
                    allow_gemini_fallback=True,
                )
            except Exception as exc:
                logger.error(
                    "[LocalMarketSearchService] Erreur query='%s' : %s",
                    query,
                    str(exc)[:300],
                )
                continue

            for item in search_results[: self.max_results_per_query]:
                url = item.get("url") or item.get("href") or ""
                title = item.get("title") or ""
                snippet = item.get("snippet") or item.get("body") or ""

                if not is_probably_valid_url(url):
                    continue

                normalized_url = self._normalize_url(url)
                if normalized_url in seen_urls:
                    continue

                seen_urls.add(normalized_url)
                results.append(
                    {
                        "query": query,
                        "title": title,
                        "url": url,
                        "domain": get_domain(url),
                        "snippet": snippet,
                        "provider": item.get("provider"),
                    }
                )

        logger.info(
            "[LocalMarketSearchService] URLs trouvées après filtrage : %s",
            len(results),
        )
        return results

    async def fetch_page_text(self, url: str) -> str:
        headers = {
            "User-Agent": USER_AGENT,
        }

        try:
            async with httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = await client.get(url)

            content_type = response.headers.get("content-type", "").lower()

            if "text/html" not in content_type:
                return ""

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(
                [
                    "script",
                    "style",
                    "noscript",
                    "svg",
                    "nav",
                    "header",
                    "footer",
                    "form",
                    "aside",
                    "iframe",
                ]
            ):
                tag.decompose()

            parts: List[str] = []

            title = soup.find("title")
            if title:
                parts.append(title.get_text(" ", strip=True))

            meta_description = soup.find("meta", attrs={"name": "description"})
            if meta_description and meta_description.get("content"):
                parts.append(str(meta_description.get("content")))

            for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                text = tag.get_text(" ", strip=True)
                if text:
                    parts.append(text)

            text = clean_text(" ".join(parts))

            if looks_like_bot_protection(text):
                return ""

            return text[: self.max_text_chars]

        except Exception as exc:
            logger.error(
                "[LocalMarketSearchService] Erreur téléchargement URL=%s : %s",
                url,
                str(exc)[:300],
            )
            return ""

    async def search_local_market(
        self,
        sector: str,
        region: str,
        description: str = "",
        project_context: Optional[Dict[str, Any]] = None,
        output_language: str = "fr",
    ) -> List[Dict[str, Any]]:
        """Return canonical local candidates, not only direct competitors.

        The previous implementation discarded a page as soon as the first
        deterministic gate did not prove the exact workflow. That removed useful
        local market evidence, ecosystem actors and adjacent solutions before the
        canonical source ledger could classify them. V4 performs extraction and
        optional AI classification first, then keeps every context-compatible
        local candidate with an explicit public/internal/candidate status.
        """
        language = normalize_output_language(output_language)
        clean_region = clean_text(region or "")

        context = project_context or project_context_builder.build(
            title=self._title_from_description(description),
            description=description,
            industry=sector,
            market_region=clean_region,
            output_language=language,
            analysis_data={},
        )
        context = self._ensure_archetype_context(
            context,
            sector=sector,
            region=clean_region,
            description=description,
            output_language=language,
        )

        queries = self.build_queries(
            sector=sector,
            region=clean_region,
            description=description,
            project_context=context,
        )
        url_results = await self.search_urls(queries)

        raw_candidates: List[Dict[str, Any]] = []
        for result in url_results[: self.max_pages_to_fetch]:
            url = str(result.get("url") or "")
            logger.info("[LocalMarketSearchService] Extraction texte : %s", url)

            page_text = await self.fetch_page_text(url)
            fallback_text = clean_text(
                " ".join(
                    [
                        str(result.get("title") or ""),
                        str(result.get("snippet") or ""),
                    ]
                )
            )
            text = page_text if len(page_text) >= MIN_TEXT_CHARS else fallback_text
            if len(text) < 80:
                continue

            matched_project_terms = self._matched_project_terms(
                text=" ".join(
                    [
                        str(result.get("title") or ""),
                        str(result.get("snippet") or ""),
                        text,
                        url,
                    ]
                ),
                project_context=context,
            )
            raw_candidates.append(
                {
                    **result,
                    "extracted_text_preview": text[: self.max_text_chars],
                    "text": text[: self.max_text_chars],
                    "text_length": len(text),
                    "text_extracted": len(page_text) >= MIN_TEXT_CHARS,
                    "search_query": result.get("query"),
                    "matched_project_terms": matched_project_terms,
                    "candidate_origin": "local_market_search",
                }
            )

        classified_candidates = await source_classifier.classify_sources(
            raw_candidates,
            context,
        )

        enriched_results: List[Dict[str, Any]] = []
        for candidate in classified_candidates:
            gate_decision = source_relevance_gate.evaluate_source(
                source=candidate,
                project_context=context,
            )
            enriched_result = {
                **candidate,
                **gate_decision,
                "local_source_type": gate_decision.get("source_type"),
            }

            if not self._is_relevant_to_project(enriched_result, context):
                logger.info(
                    "[LocalMarketSearchService][CandidateRejected] "
                    "title=%s | ai_type=%s | role=%s | type=%s | region=%s "
                    "| score=%s | reason=%s",
                    enriched_result.get("title"),
                    enriched_result.get("ai_source_type"),
                    enriched_result.get("source_role"),
                    enriched_result.get("source_type"),
                    enriched_result.get("region_match"),
                    enriched_result.get("source_relevance_score"),
                    enriched_result.get("rejection_reason"),
                )
                continue

            if enriched_result.get("public_display"):
                candidate_status = "public"
            elif enriched_result.get("internal_only"):
                candidate_status = "internal"
            else:
                candidate_status = "candidate"

            enriched_result["candidate_status"] = candidate_status
            enriched_result["public_candidate"] = candidate_status == "public"
            enriched_result["requires_canonical_recheck"] = candidate_status != "public"

            logger.info(
                "[LocalMarketSearchService][CandidateRetained] "
                "title=%s | category=%s | role=%s | type=%s | region=%s "
                "| score=%s | status=%s",
                enriched_result.get("title"),
                enriched_result.get("canonical_category"),
                enriched_result.get("source_role"),
                enriched_result.get("source_type"),
                enriched_result.get("region_match"),
                enriched_result.get("source_relevance_score"),
                candidate_status,
            )
            enriched_results.append(enriched_result)

        logger.info(
            "[LocalMarketSearchService] Candidats locaux conservés : %s",
            len(enriched_results),
        )
        return enriched_results

    def _is_relevant_to_project(
        self,
        source: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> bool:
        if source.get("matched_forbidden_terms"):
            return False

        source_type = str(source.get("source_type") or "").lower()
        ai_type = str(source.get("ai_source_type") or "").lower()
        ai_confidence = float(source.get("ai_classifier_confidence") or 0)
        region_match = str(source.get("region_match") or "").lower()

        matched_terms = self._safe_term_list(source.get("matched_project_terms"))
        domain_terms = self._safe_term_list(source.get("matched_domain_terms"))
        sector_terms = self._safe_term_list(source.get("matched_sector_terms"))
        target_terms = self._safe_term_list(source.get("matched_target_terms"))
        use_case_terms = self._safe_term_list(source.get("matched_use_case_terms"))
        solution_terms = self._safe_term_list(source.get("matched_solution_terms"))
        all_matches = self._unique_strings(
            matched_terms
            + domain_terms
            + sector_terms
            + target_terms
            + use_case_terms
            + solution_terms
        )

        if not all_matches:
            return False

        # Preserve local evidence and adjacent actors even when they cannot be
        # presented as direct competitors. The canonical gate will decide the
        # final public role later.
        if region_match == "local":
            if source_type != "irrelevant":
                return True
            return bool(
                ai_confidence >= 0.60
                and ai_type in {
                    "adjacent_solution",
                    "technology_benchmark",
                    "market_evidence",
                    "market_article",
                    "official_source",
                    "directory",
                    "local_ecosystem",
                }
            )

        if source_type == "technology_benchmark":
            return bool(domain_terms or use_case_terms or solution_terms)

        if source.get("public_display") or source.get("internal_only"):
            return True

        multiword = any(len(normalize_text(item).split()) >= 2 for item in all_matches)
        return multiword or len(all_matches) >= 2

    def _matched_project_terms(
        self,
        text: str,
        project_context: Dict[str, Any],
    ) -> List[str]:
        normalized_text = normalize_text(text)
        matches: List[str] = []
        for term in self._specific_context_terms(project_context):
            clean = normalize_text(term)
            if len(clean) < 4:
                continue
            pattern = rf"(?<![a-z0-9]){re.escape(clean)}(?![a-z0-9])"
            if re.search(pattern, normalized_text):
                matches.append(term)
        return self._unique_strings(matches)[:20]

    def _is_searchable_term(self, term: str) -> bool:
        clean = normalize_text(term)
        if len(clean) < 4:
            return False
        blocked = {
            "project", "startup", "business", "model", "solution", "platform",
            "application", "software", "market", "marche", "local", "global",
            "tunisie", "tunisia", "simple", "small", "users", "clients",
            "user", "client", "management", "digital", "problem", "service",
            "tool", "system", "saas", "pricing", "price", "monthly",
        }
        tokens = [token for token in clean.split() if token not in blocked]
        return bool(tokens)

    def _specific_context_terms(self, project_context: Dict[str, Any]) -> List[str]:
        intelligence = project_context.get("project_intelligence") or {}
        packet = project_context.get("agent_context_packet") or {}
        structured = (
            project_context.get("structured_project_context")
            or intelligence.get("structured_project_context")
            or {}
        )
        packet = project_context.get("agent_context_packet") or intelligence.get("agent_context_packet") or {}
        archetype_context = (
            project_context.get("archetype_context")
            or packet.get("archetype_context")
            or intelligence.get("archetype_context")
            or {}
        )
        actors = archetype_context.get("actors") or structured.get("actors") or {}
        raw_values = [
            project_context.get("domain_concepts"),
            project_context.get("search_concepts"),
            project_context.get("use_case_terms"),
            packet.get("domain_concepts"),
            packet.get("search_concepts"),
            packet.get("use_case_terms"),
            structured.get("domain_concepts"),
            structured.get("search_concepts"),
            structured.get("use_case_terms"),
            structured.get("priority_workflows"),
            structured.get("vertical"),
            structured.get("project_archetype"),
            archetype_context.get("search_terms"),
            archetype_context.get("priority_workflows"),
            archetype_context.get("vertical"),
            archetype_context.get("validation_unit"),
            list(actors.values()) if isinstance(actors, dict) else actors,
            project_context.get("must_match_terms"),
        ]
        result: List[str] = []
        for value in raw_values:
            values = value if isinstance(value, list) else [value]
            for item in values:
                if item and self._is_searchable_term(str(item)):
                    result.append(clean_text(str(item)))
        return self._unique_strings(result)[:24]

    def _ensure_archetype_context(
        self,
        context: Dict[str, Any],
        *,
        sector: str,
        region: str,
        description: str,
        output_language: str = "fr",
    ) -> Dict[str, Any]:
        merged = dict(context or {})
        intelligence = dict(merged.get("project_intelligence") or {})
        packet = dict(
            merged.get("agent_context_packet")
            or intelligence.get("agent_context_packet")
            or {}
        )
        existing = (
            merged.get("archetype_context")
            or packet.get("archetype_context")
            or intelligence.get("archetype_context")
            or {}
        )
        if not existing or not (existing.get("search_queries") or {}).get("all"):
            existing = project_archetype_resolver.resolve(
                title=self._title_from_description(description),
                description=description,
                industry=sector,
                target_region=region,
                output_language=output_language,
            )

        structured = dict(
            merged.get("structured_project_context")
            or intelligence.get("structured_project_context")
            or {}
        )
        structured.setdefault("project_archetype", existing.get("project_archetype"))
        structured.setdefault("vertical", existing.get("vertical"))
        structured.setdefault("actors", existing.get("actors") or {})
        structured.setdefault("target_users", existing.get("target_users") or [])
        structured.setdefault("priority_workflows", existing.get("priority_workflows") or [])
        structured.setdefault("success_metrics", existing.get("success_metrics") or [])
        structured.setdefault("risk_dimensions", existing.get("risk_dimensions") or [])

        packet["archetype_context"] = existing
        packet.setdefault("structured_project_context", structured)
        intelligence["archetype_context"] = existing
        intelligence.setdefault("structured_project_context", structured)
        intelligence["agent_context_packet"] = packet

        merged["archetype_context"] = existing
        merged["structured_project_context"] = structured
        merged["agent_context_packet"] = packet
        merged["project_intelligence"] = intelligence
        return merged

    def _compact_sector(self, sector: str) -> str:
        tokens = [
            token for token in normalize_text(sector).split()
            if self._is_searchable_term(token)
        ]
        return " ".join(tokens[:3])

    def _normalize_query(self, query: str) -> str:
        value = clean_text(query)
        value = re.sub(
            r"\b(None|non spécifié|not specified|null)\b",
            " ",
            value,
            flags=re.IGNORECASE,
        )
        tokens: List[str] = []
        seen = set()
        for token in value.split():
            key = normalize_text(token)
            if not key or key in seen:
                continue
            seen.add(key)
            tokens.append(token)
        return clean_text(" ".join(tokens[:9]))

    def _safe_term_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if value:
            return [str(value)]
        return []

    def _title_from_description(self, description: str) -> str:
        text = str(description or "").strip()

        if "." in text:
            return text.split(".", 1)[0][:120]

        return text[:120]

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()

    def _unique_strings(self, values: List[Any]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = str(value or "").strip()

            if not clean:
                continue

            key = normalize_text(clean)

            if key not in seen:
                seen.add(key)
                result.append(clean)

        return result


async def _manual_test() -> None:
    service = LocalMarketSearchService(
        max_results_per_query=5,
        max_pages_to_fetch=4,
        max_text_chars=2500,
    )

    results = await service.search_local_market(
        sector="EdTech",
        region="Tunisie",
        description=(
            "Plateforme IA pour aider les élèves tunisiens du baccalauréat "
            "à réviser avec des parcours personnalisés."
        ),
    )

    print("\n==============================")
    print("LOCAL MARKET WEB SEARCH TEST")
    print("==============================")
    print(f"Nombre de résultats enrichis valides : {len(results)}")

    for index, item in enumerate(results, start=1):
        print("\n------------------------------")
        print(f"Résultat {index}")
        print("------------------------------")
        print("Query   :", item.get("query"))
        print("Title   :", item.get("title"))
        print("URL     :", item.get("url"))
        print("Domain  :", item.get("domain"))
        print("Matched :", item.get("matched_project_terms"))
        print("Text len:", item.get("text_length"))
        print("Text preview:")
        print((item.get("text") or "")[:600])


if __name__ == "__main__":
    asyncio.run(_manual_test())