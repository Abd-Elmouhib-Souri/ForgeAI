# ============================================================
# backend/app/web_search/local_market_search.py
# ============================================================
#
# LocalMarketSearchService V2 — Dynamic Context-Locked Web Search
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
from ddgs import DDGS

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder

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
)

BLOCKED_EXTENSIONS = (
    ".pdf",
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
        max_pages_to_fetch: int = 5,
        max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
    ) -> None:
        self.max_results_per_query = max_results_per_query
        self.max_pages_to_fetch = max_pages_to_fetch
        self.max_text_chars = max_text_chars

    def build_queries(
        self,
        sector: str,
        region: str,
        description: str = "",
        project_context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        sector = str(sector or "").strip() or "startup"
        region = str(region or "").strip() or "Tunisie"
        description = str(description or "").strip()

        anchor_terms = []
        core_terms = []

        if isinstance(project_context, dict):
            anchor_terms = project_context.get("anchor_terms") or []
            core_terms = project_context.get("core_terms") or []

        project_terms = self._unique_strings(
            [
                str(term)
                for term in list(anchor_terms) + list(core_terms)
                if self._is_searchable_term(str(term))
            ]
        )

        short_context = " ".join(project_terms[:8])
        long_context = " ".join(project_terms[:12])
        description_short = " ".join(description.split()[:14])

        queries: List[str] = []

        if short_context:
            queries.extend(
                [
                    f"{short_context} {region}",
                    f"{short_context} marché {region}",
                    f"{short_context} startup {region}",
                    f"{short_context} logiciel SaaS {region}",
                    f"{short_context} concurrents {region}",
                    f"{short_context} competitors {region}",
                    f"site:.tn {short_context}",
                ]
            )

        if long_context:
            queries.extend(
                [
                    f"{long_context} solution",
                    f"{long_context} pricing",
                    f"{long_context} market",
                    f"{long_context} case study",
                ]
            )

        queries.extend(
            [
                f"{sector} {region} marché startup",
                f"{sector} {region} innovation transformation digitale",
                f"{sector} {region} software SaaS",
                f"{sector} {region} competitors",
            ]
        )

        if description_short:
            queries.append(f"{description_short} {region} marché")
            queries.append(f"{description_short} {region} competitors")

        cleaned_queries = []

        for query in queries:
            query = clean_text(query)

            if not query:
                continue

            query = re.sub(
                r"\b(None|non spécifié|not specified|null)\b",
                " ",
                query,
                flags=re.IGNORECASE,
            )
            query = clean_text(query)

            if query:
                cleaned_queries.append(query)

        return self._unique_strings(cleaned_queries)[:12]

    def search_urls(self, queries: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        logger.info("[LocalMarketSearchService] Début recherche web dynamique")

        with DDGS() as ddgs:
            for query in queries:
                logger.info("[LocalMarketSearchService] Query web : %s", query)

                try:
                    search_results = ddgs.text(
                        query,
                        max_results=self.max_results_per_query,
                    )

                    for item in search_results:
                        url = item.get("href") or item.get("url") or ""
                        title = item.get("title") or ""
                        snippet = item.get("body") or item.get("snippet") or ""

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
                            }
                        )

                except Exception as exc:
                    logger.error(
                        "[LocalMarketSearchService] Erreur query='%s' : %s",
                        query,
                        str(exc)[:300],
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

            soup = BeautifulSoup(response.text, "lxml")

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
        language = normalize_output_language(output_language)

        context = project_context or project_context_builder.build(
            title=self._title_from_description(description),
            description=description,
            industry=sector,
            market_region=region,
            output_language=language,
            analysis_data={},
        )

        queries = self.build_queries(
            sector=sector,
            region=region,
            description=description,
            project_context=context,
        )

        url_results = self.search_urls(queries)

        enriched_results: List[Dict[str, Any]] = []

        for result in url_results:
            if len(enriched_results) >= self.max_pages_to_fetch:
                break

            url = result["url"]

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

            if len(text) < 120:
                continue

            matched_project_terms = self._matched_project_terms(
                text=" ".join(
                    [
                        str(result.get("title") or ""),
                        str(result.get("snippet") or ""),
                        text,
                        str(result.get("url") or ""),
                    ]
                ),
                project_context=context,
            )

            enriched_result = {
                **result,
                "text": text[: self.max_text_chars],
                "text_length": len(text),
                "matched_project_terms": matched_project_terms,
            }

            if not self._is_relevant_to_project(enriched_result, context):
                logger.info(
                    "[LocalMarketSearchService] Source rejetée hors contexte : %s",
                    url,
                )
                continue

            enriched_results.append(enriched_result)

        logger.info(
            "[LocalMarketSearchService] Pages enrichies valides : %s",
            len(enriched_results),
        )

        return enriched_results

    def _is_relevant_to_project(
        self,
        source: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> bool:
        matched_terms = source.get("matched_project_terms") or []

        if len(matched_terms) >= 1:
            return True

        validation = domain_integrity_guard.validate_text(
            text=" ".join(
                [
                    str(source.get("title") or ""),
                    str(source.get("snippet") or ""),
                    str(source.get("text") or ""),
                ]
            ),
            project_context=project_context,
        )

        return bool(validation.get("is_valid"))

    def _matched_project_terms(
        self,
        text: str,
        project_context: Dict[str, Any],
    ) -> List[str]:
        normalized_text = normalize_text(text)

        terms = list(project_context.get("anchor_terms") or []) + list(
            project_context.get("core_terms") or []
        )

        matches: List[str] = []

        for term in terms:
            clean = normalize_text(str(term))

            if len(clean) < 3:
                continue

            if clean in normalized_text:
                matches.append(str(term))

        return self._unique_strings(matches)[:20]

    def _is_searchable_term(self, term: str) -> bool:
        clean = normalize_text(term)

        if len(clean) < 3:
            return False

        blocked = {
            "project",
            "startup",
            "business",
            "model",
            "solution",
            "platform",
            "application",
            "software",
            "market",
            "marche",
            "marché",
            "local",
            "global",
            "tunisie",
            "tunisia",
            "simple",
            "small",
            "users",
            "clients",
            "user",
            "client",
            "management",
            "digital",
        }

        return clean not in blocked

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