# ============================================================
# backend/app/rag/web_dynamic_rag.py
# ============================================================
#
# DynamicWebRAGService V2 — compatible ancien + nouveau LocalMarketSearchService
#
# Objectif :
# - fournir la classe DynamicWebRAGService attendue par business_analyst_agent.py ;
# - rester compatible avec ton ancien local_market_search.py ;
# - accepter project_context + output_language ;
# - construire un contexte local propre pour le Business Analyst ;
# - éviter que le backend crash au démarrage.
# ============================================================

import logging
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from app.services.domain_integrity_guard import normalize_output_language
from app.services.project_context_builder import project_context_builder
from app.web_search.local_market_search import LocalMarketSearchService

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_MIN_CHUNK_CHARS = 300
DEFAULT_TOP_K = 5


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    if not text:
        return []

    cleaned = str(text).strip()

    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: List[str] = []
    start = 0

    while start < len(cleaned):
        end = start + chunk_size
        chunk = cleaned[start:end].strip()

        if chunk:
            chunks.append(chunk)

        next_start = end - overlap

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def build_similarity_query(
    sector: str,
    region: str,
    description: str = "",
    project_context: Optional[Dict[str, Any]] = None,
) -> str:
    terms_text = ""

    if isinstance(project_context, dict):
        terms = project_context.get("anchor_terms") or []
        terms_text = " ".join(str(term) for term in terms[:12])

    return (
        f"Local market context for this exact project. "
        f"Sector: {sector}. "
        f"Region: {region}. "
        f"Project terms: {terms_text}. "
        f"Project description: {description}. "
        f"Find local actors, competitors, adoption, regulation, opportunities, constraints and market evidence."
    )


def format_local_context(
    passages: List[Dict[str, Any]],
    output_language: str = "fr",
) -> str:
    language = normalize_output_language(output_language)

    if not passages:
        if language == "en":
            return (
                "No reliable local web context was found. "
                "The local assessment must remain cautious and requires field validation."
            )

        return (
            "Aucun contexte web local fiable n'a été trouvé. "
            "L'analyse locale doit rester prudente et nécessite une validation terrain."
        )

    lines: List[str] = []

    for index, item in enumerate(passages, start=1):
        metadata = item.get("metadata") or {}
        document = item.get("document") or ""
        distance = item.get("distance")

        title = metadata.get("title") or "Source web"
        url = metadata.get("url") or ""
        domain = metadata.get("domain") or ""
        query = metadata.get("query") or ""

        if language == "en":
            lines.append(f"[LOCAL PASSAGE {index}]")
            lines.append(f"Source: {title}")
            lines.append(f"Domain: {domain}")
            lines.append(f"URL: {url}")
            lines.append(f"Search query: {query}")

            if distance is not None:
                lines.append(f"Vector distance: {distance}")

            lines.append("Content:")
            lines.append(str(document))
            lines.append("")
        else:
            lines.append(f"[PASSAGE LOCAL {index}]")
            lines.append(f"Source : {title}")
            lines.append(f"Domaine : {domain}")
            lines.append(f"URL : {url}")
            lines.append(f"Query utilisée : {query}")

            if distance is not None:
                lines.append(f"Distance vectorielle : {distance}")

            lines.append("Contenu :")
            lines.append(str(document))
            lines.append("")

    return "\n".join(lines).strip()


class DynamicWebRAGService:
    """
    Service RAG web dynamique.

    Important :
    Cette classe existe pour être importée par :
    from app.rag.web_dynamic_rag import DynamicWebRAGService
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            headers={
                "Authorization": f"Bearer {settings.CHROMA_AUTH_TOKEN}",
            },
        )

    def _create_temp_collection_name(self) -> str:
        return f"web_local_{uuid.uuid4().hex}"

    def _build_chunks_from_web_results(
        self,
        web_results: List[Dict[str, Any]],
    ) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for source_index, result in enumerate(web_results):
            text = str(result.get("text") or "").strip()

            chunks = chunk_text(
                text=text,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
            )

            for chunk_index, chunk in enumerate(chunks):
                if len(chunk) < DEFAULT_MIN_CHUNK_CHARS:
                    continue

                chunk_id = f"source_{source_index}_chunk_{chunk_index}"

                documents.append(chunk)

                metadatas.append(
                    {
                        "source_index": source_index,
                        "chunk_index": chunk_index,
                        "title": result.get("title") or "",
                        "url": result.get("url") or "",
                        "domain": result.get("domain") or "",
                        "query": result.get("query") or "",
                        "snippet": result.get("snippet") or "",
                    }
                )

                ids.append(chunk_id)

        return documents, metadatas, ids

    def _query_temp_collection(
        self,
        collection: Any,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        raw_results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]

        passages: List[Dict[str, Any]] = []

        for document, metadata, distance in zip(documents, metadatas, distances):
            passages.append(
                {
                    "document": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return passages

    async def _search_web_results(
        self,
        *,
        sector: str,
        region: str,
        description: str,
        project_context: Dict[str, Any],
        output_language: str,
    ) -> List[Dict[str, Any]]:
        search_service = LocalMarketSearchService(
            max_results_per_query=5,
            max_pages_to_fetch=4,
            max_text_chars=5000,
        )

        try:
            return await search_service.search_local_market(
                sector=sector,
                region=region,
                description=description,
                project_context=project_context,
                output_language=output_language,
            )
        except TypeError:
            return await search_service.search_local_market(
                sector=sector,
                region=region,
                description=description,
            )

    async def build_local_context(
        self,
        sector: str,
        region: str,
        description: str = "",
        project_context: Optional[Dict[str, Any]] = None,
        output_language: str = "fr",
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)

        context = project_context or project_context_builder.build(
            title=str(description or "")[:120],
            description=description,
            industry=sector,
            market_region=region,
            output_language=language,
            analysis_data={},
        )

        temp_collection_name = self._create_temp_collection_name()
        collection_created = False

        result: Dict[str, Any] = {
            "local_context": "",
            "passages": [],
            "sources": [],
            "web_results_count": 0,
            "chunks_count": 0,
            "temp_collection_name": temp_collection_name,
            "cleanup_done": False,
            "error": None,
        }

        try:
            web_results = await self._search_web_results(
                sector=sector,
                region=region,
                description=description,
                project_context=context,
                output_language=language,
            )

            result["web_results_count"] = len(web_results)
            result["sources"] = [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "domain": item.get("domain"),
                    "query": item.get("query"),
                    "snippet": item.get("snippet"),
                    "text_length": item.get("text_length"),
                }
                for item in web_results
            ]

            if not web_results:
                result["local_context"] = format_local_context([], language)
                result["temp_collection_name"] = None
                result["cleanup_done"] = True
                return result

            documents, metadatas, ids = self._build_chunks_from_web_results(web_results)

            result["chunks_count"] = len(documents)

            if not documents:
                result["local_context"] = format_local_context([], language)
                result["temp_collection_name"] = None
                result["cleanup_done"] = True
                return result

            collection = self.client.create_collection(
                name=temp_collection_name,
                embedding_function=self.embedding_function,
            )
            collection_created = True

            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

            similarity_query = build_similarity_query(
                sector=sector,
                region=region,
                description=description,
                project_context=context,
            )

            passages = self._query_temp_collection(
                collection=collection,
                query=similarity_query,
                top_k=min(self.top_k, len(documents)),
            )

            result["passages"] = passages
            result["local_context"] = format_local_context(
                passages=passages,
                output_language=language,
            )

            return result

        except Exception as exc:
            logger.exception("[DynamicWebRAGService] Failed")

            result["error"] = str(exc)

            if language == "en":
                result["local_context"] = (
                    "An error occurred while building the local web context. "
                    "The local analysis must remain cautious."
                )
            else:
                result["local_context"] = (
                    "Erreur lors de la construction du contexte web local. "
                    "L'analyse locale doit rester prudente."
                )

            return result

        finally:
            if collection_created:
                try:
                    self.client.delete_collection(name=temp_collection_name)
                    result["cleanup_done"] = True
                except Exception as exc:
                    result["cleanup_done"] = False
                    logger.error(
                        "[DynamicWebRAGService] Cleanup failed | collection=%s | error=%s",
                        temp_collection_name,
                        str(exc)[:300],
                    )


async def _manual_test() -> None:
    service = DynamicWebRAGService()

    result = await service.build_local_context(
        sector="EdTech",
        region="Tunisie",
        description="Plateforme IA pour aider les élèves tunisiens du baccalauréat à réviser.",
        output_language="fr",
    )

    print("WEB RESULTS:", result.get("web_results_count"))
    print("CHUNKS:", result.get("chunks_count"))
    print("ERROR:", result.get("error"))
    print((result.get("local_context") or "")[:1000])


if __name__ == "__main__":
    import asyncio

    asyncio.run(_manual_test())