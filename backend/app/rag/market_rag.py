# ============================================================
# backend/app/rag/market_rag.py
# ============================================================
#
# MarketRAGService V3 — Dynamic Context Locked
#
# Objectif :
# - supprimer les alias sectoriels fixes ;
# - ne pas router par FinTech / HealthTech / AgriTech hardcodé ;
# - utiliser project_context si disponible ;
# - rester compatible avec les anciens appels ;
# - fournir un contexte global prudent, jamais forcé.
# ============================================================

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 3
DEFAULT_COLLECTION_NAME = "market_rag"


class MarketRAGService:
    def __init__(self) -> None:
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.client = None

        try:
            token = getattr(settings, "CHROMA_AUTH_TOKEN", "")
            headers = {"Authorization": f"Bearer {token}"} if token else {}

            self.client = chromadb.HttpClient(
                host=getattr(settings, "CHROMA_HOST", "chroma"),
                port=int(getattr(settings, "CHROMA_PORT", 8000)),
                headers=headers,
            )
        except Exception as exc:
            logger.warning("[MarketRAGService] Chroma connection unavailable: %s", exc)
            self.client = None

    def search_market_context(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        sector_hint: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
        output_language: str = "fr",
    ) -> str:
        language = normalize_output_language(output_language)

        if not self.client:
            return self._fallback_context(
                query=query,
                sector_hint=sector_hint,
                project_context=project_context,
                output_language=language,
            )

        search_query = self._build_dynamic_query(
            query=query,
            sector_hint=sector_hint,
            project_context=project_context,
        )

        try:
            collection_name = getattr(
                settings,
                "MARKET_RAG_COLLECTION",
                DEFAULT_COLLECTION_NAME,
            )

            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
            )

            try:
                if collection.count() <= 0:
                    return self._fallback_context(
                        query=query,
                        sector_hint=sector_hint,
                        project_context=project_context,
                        output_language=language,
                    )
            except Exception:
                pass

            raw_results = collection.query(
                query_texts=[search_query],
                n_results=max(1, int(top_k)),
                include=["documents", "metadatas", "distances"],
            )

            passages = self._parse_results(
                raw_results=raw_results,
                project_context=project_context,
            )

            if not passages:
                return self._fallback_context(
                    query=query,
                    sector_hint=sector_hint,
                    project_context=project_context,
                    output_language=language,
                )

            return self._format_context(
                passages=passages,
                output_language=language,
            )

        except Exception as exc:
            logger.warning("[MarketRAGService] Search failed: %s", exc)

            return self._fallback_context(
                query=query,
                sector_hint=sector_hint,
                project_context=project_context,
                output_language=language,
            )

    def _build_dynamic_query(
        self,
        query: str,
        sector_hint: Optional[str],
        project_context: Optional[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []

        if query:
            parts.append(str(query))

        if sector_hint:
            parts.append(f"Sector provided by user: {sector_hint}")

        if isinstance(project_context, dict):
            anchor_terms = project_context.get("anchor_terms") or []
            core_terms = project_context.get("core_terms") or []
            domain_label = project_context.get("domain_label") or ""

            if domain_label:
                parts.append(f"Project domain: {domain_label}")

            if anchor_terms:
                parts.append(
                    "High-signal project terms: "
                    + ", ".join(str(term) for term in anchor_terms[:15])
                )

            if core_terms:
                parts.append(
                    "Core project terms: "
                    + ", ".join(str(term) for term in core_terms[:15])
                )

        parts.append(
            "Find global market signals, comparable business models, adoption risks, "
            "customer validation patterns and constraints for this exact project."
        )

        return "\n".join(parts).strip()

    def _parse_results(
        self,
        raw_results: Dict[str, Any],
        project_context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]

        passages: List[Dict[str, Any]] = []

        for document, metadata, distance in zip(documents, metadatas, distances):
            text = str(document or "").strip()

            if not text:
                continue

            if project_context and not self._is_relevant(text, project_context):
                continue

            passages.append(
                {
                    "document": text,
                    "metadata": metadata or {},
                    "distance": distance,
                    "matched_terms": self._matched_project_terms(
                        text=text,
                        project_context=project_context or {},
                    ),
                }
            )

        return passages

    def _is_relevant(
        self,
        text: str,
        project_context: Dict[str, Any],
    ) -> bool:
        matched = self._matched_project_terms(text, project_context)

        if matched:
            return True

        validation = domain_integrity_guard.validate_text(
            text=text,
            project_context=project_context,
        )

        return bool(validation.get("is_valid"))

    def _matched_project_terms(
        self,
        text: str,
        project_context: Dict[str, Any],
    ) -> List[str]:
        normalized_text = self._normalize(text)

        terms = list(project_context.get("anchor_terms") or []) + list(
            project_context.get("core_terms") or []
        )

        matches: List[str] = []

        for term in terms:
            clean = self._normalize(str(term))

            if len(clean) < 3:
                continue

            if clean in normalized_text:
                matches.append(str(term))

        return self._unique(matches)[:20]

    def _format_context(
        self,
        passages: List[Dict[str, Any]],
        output_language: str,
    ) -> str:
        language = normalize_output_language(output_language)
        lines: List[str] = []

        if language == "en":
            lines.append("STATIC GLOBAL MARKET CONTEXT")
            lines.append(
                "These passages are only general benchmarks. They must not be treated as local proof."
            )
        else:
            lines.append("CONTEXTE MARCHÉ GLOBAL STATIQUE")
            lines.append(
                "Ces passages sont seulement des benchmarks généraux. Ils ne doivent pas être traités comme preuve locale."
            )

        for index, item in enumerate(passages, start=1):
            metadata = item.get("metadata") or {}
            document = item.get("document") or ""
            distance = item.get("distance")
            matched_terms = item.get("matched_terms") or []

            title = metadata.get("title") or metadata.get("source") or "Source RAG"
            url = metadata.get("url") or ""

            if language == "en":
                lines.append("")
                lines.append(f"[GLOBAL PASSAGE {index}]")
                lines.append(f"Source: {title}")
                if url:
                    lines.append(f"URL: {url}")
                if distance is not None:
                    lines.append(f"Vector distance: {distance}")
                if matched_terms:
                    lines.append("Matched project terms: " + ", ".join(matched_terms[:8]))
                lines.append("Content:")
                lines.append(str(document)[:1200])
            else:
                lines.append("")
                lines.append(f"[PASSAGE GLOBAL {index}]")
                lines.append(f"Source : {title}")
                if url:
                    lines.append(f"URL : {url}")
                if distance is not None:
                    lines.append(f"Distance vectorielle : {distance}")
                if matched_terms:
                    lines.append("Termes projet retrouvés : " + ", ".join(matched_terms[:8]))
                lines.append("Contenu :")
                lines.append(str(document)[:1200])

        return "\n".join(lines).strip()

    def _fallback_context(
        self,
        query: str,
        sector_hint: Optional[str],
        project_context: Optional[Dict[str, Any]],
        output_language: str,
    ) -> str:
        language = normalize_output_language(output_language)

        domain_label = ""

        if isinstance(project_context, dict):
            domain_label = str(project_context.get("domain_label") or "")

        if language == "en":
            return (
                "No reliable static global market context was found in the local RAG database. "
                f"The analysis must remain cautious and rely mainly on the project input"
                f"{' and its context: ' + domain_label if domain_label else ''}. "
                "Any market size, competitor or adoption claim should be validated with external sources "
                "and field interviews."
            )

        return (
            "Aucun contexte marché global statique fiable n'a été trouvé dans la base RAG locale. "
            f"L’analyse doit rester prudente et s’appuyer principalement sur l’input du projet"
            f"{' et son contexte : ' + domain_label if domain_label else ''}. "
            "Toute affirmation sur la taille du marché, les concurrents ou l’adoption doit être validée "
            "par des sources externes et des entretiens terrain."
        )

    def _normalize(self, text: str) -> str:
        text = str(text or "")
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\.\-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = str(value or "").strip()

            if not clean:
                continue

            key = self._normalize(clean)

            if key not in seen:
                seen.add(key)
                result.append(clean)

        return result