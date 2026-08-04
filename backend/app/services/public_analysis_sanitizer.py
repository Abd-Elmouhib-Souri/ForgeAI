from app.services.evidence_ledger import evidence_ledger
from copy import deepcopy
from typing import Any, Dict, List, Optional

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)


TECHNICAL_KEYS_TO_HIDE = {
    "errors",
    "error",
    "raw_errors",
    "ddgs_errors",
    "scraping_errors",
    "provider_errors",
    "llm_errors",
    "model_errors",
    "fallback_errors",
    "traceback",
    "stacktrace",
    "exception",
    "raw_response",
    "raw_output",
    "raw_outputs",
    "raw_sources",
    "debug",
    "debug_info",
    "queries",
    "search_query",
    "extraction_method",
    "text_extracted",
    "partial_completion",
    "local_market_sources",
    "local_market_candidates",

    # Internal context / guard packets - never public
    "startup_evaluator_meta",
    "project_intelligence",
    "agent_context_packet",
    "structured_project_context",
    "guard_context",
    "internal_context",
    "project_context_used",

    # Internal contamination-control lists - never public
    "forbidden_offtopic_terms",
    "forbidden_terms",
    "offtopic_terms",
    "demo_terms",
    "contamination_terms",
    "rejected_terms",
    "blocked_terms",
    "forbidden_entities",
    "rejected_entities",
}


SAFE_META_KEYS = {
    "completed_steps",
    "failed_steps",
    "progress",
    "current_step",
    "completed",
    "output_language",
    "context_locked",
    "llm_used",
    "format",
    "status",
}


# Public source sections are already validated by ForgeCrawler,
# SourceRelevanceGate and CompetitiveAnalysisAgent. The global public
# sanitizer may clean their shape, but must not delete or reclassify them.
PUBLIC_SOURCE_SECTION_FIELDS = {
    "forgecrawler": {
        "format",
        "status",
        "confidence_level",
        "context_locked",
        "output_language",
        "public_display_threshold",
        "sources_count",
        "local_competitors_count",
        "regional_competitors_count",
        "international_benchmarks_count",
        "market_sources_count",
        "sources",
        "public_sources",
        "local_competitor_sources",
        "regional_competitor_sources",
        "international_benchmark_sources",
        "market_context_sources",
        "source_quality",
        "no_verified_relevant_source_found",
        "no_source_message",
        "limitations",
    },
    "competitive_analysis": {
        "format",
        "status",
        "source_based",
        "context_locked",
        "output_language",
        "confidence_level",
        "sources_count",
        "local_competitors_count",
        "regional_competitors_count",
        "international_benchmarks_count",
        "market_sources_count",
        "sources",
        "public_sources",
        "local_competitor_sources",
        "regional_competitor_sources",
        "international_benchmark_sources",
        "market_context_sources",
        "local_direct_competitors",
        "local_adjacent_solutions",
        "regional_competitors",
        "international_benchmarks",
        "verified_competitors",
        "local_competitors",
        "market_sources",
        "external_sources",
        "no_verified_relevant_source_found",
        "no_source_message",
        "source_quality",
        "limitations",
    },
}


PUBLIC_CONTEXT_GATE_SECTION_FIELDS = {
    "idea_readiness": {
        "format",
        "canonical_format",
        "schema_version",
        "status",
        "score",
        "ready_for_agents",
        "threshold",
        "missing_fields",
        "ambiguous_fields",
        "blockers",
        "questions",
        "clarification_questions",
        "recommendation",
        "reasons",
        "output_language",
        "checklist",
    },
    "context_confidence": {
        "score",
        "status",
        "missing_fields",
        "ambiguous_fields",
        "blockers",
        "clarification_questions",
        "reasons",
        "ready_for_agents",
    },
}


MOJIBAKE_TEXT_REPLACEMENTS = {
    "â€™": "’",
    "â€˜": "‘",
    "â€œ": "“",
    "â€": "”",
    "â€”": "—",
    "â€“": "–",
    "â€¦": "…",
    "Ã€": "À",
    "Ã‚": "Â",
    "Ã‡": "Ç",
    "Ãˆ": "È",
    "Ã‰": "É",
    "ÃŠ": "Ê",
    "Ã‹": "Ë",
    "ÃŽ": "Î",
    "ÃÏ": "Ï",
    "Ã”": "Ô",
    "Ã™": "Ù",
    "Ã›": "Û",
    "Ãœ": "Ü",
    "Ã ": "à",
    "Ã¢": "â",
    "Ã¤": "ä",
    "Ã§": "ç",
    "Ã¨": "è",
    "Ã©": "é",
    "Ãª": "ê",
    "Ã«": "ë",
    "Ã®": "î",
    "Ã¯": "ï",
    "Ã´": "ô",
    "Ã¶": "ö",
    "Ã¹": "ù",
    "Ã»": "û",
    "Ã¼": "ü",
    "Å“": "œ",
    "Å’": "Œ",
    "Â ": " ",
}


TECHNICAL_WORD_REPLACEMENTS_FR = {
    "RAG global": "sources générales disponibles",
    "RAG local": "sources locales disponibles",
    "RAG": "sources disponibles",
    "LLM": "moteur d’analyse",
    "LangGraph": "workflow d’analyse",
    "ForgeCrawler": "sources externes",
    "DDGS": "moteur de recherche externe",
    "Gemini": "moteur d’analyse",
    "Groq": "moteur d’analyse",
    "trafilatura": "extraction web",
    "BeautifulSoup": "extraction web",
    "beautifulsoup": "extraction web",
}


TECHNICAL_WORD_REPLACEMENTS_EN = {
    "RAG global": "available general sources",
    "RAG local": "available local sources",
    "RAG": "available sources",
    "LLM": "analysis engine",
    "LangGraph": "analysis workflow",
    "ForgeCrawler": "external sources",
    "DDGS": "external search engine",
    "Gemini": "analysis engine",
    "Groq": "analysis engine",
    "trafilatura": "web extraction",
    "BeautifulSoup": "web extraction",
    "beautifulsoup": "web extraction",
}


LANGUAGE_WORD_REPLACEMENTS_EN = {
    "PIVOTER": "PIVOT",
    "POURSUIVRE": "CONTINUE",
    "ABANDONNER": "STOP",
    "GO_CONDITIONNEL_POUR_MVP": "CONDITIONAL_GO_FOR_MVP",
    "PIVOTER_AVANT_MVP": "PIVOT_BEFORE_MVP",
    "NO_GO_AVANT_REPOSITIONNEMENT": "NO_GO_BEFORE_REPOSITIONING",
    "PIVOT_NÉCESSAIRE": "PIVOT_REQUIRED",
    "PIVOT_NECESSAIRE": "PIVOT_REQUIRED",
    "Moyenne": "Medium",
    "Moyen": "Medium",
    "moyenne": "medium",
    "moyen": "medium",
    "Élevé": "High",
    "Elevé": "High",
    "élevé": "high",
    "eleve": "high",
    "Faible": "Low",
    "faible": "low",
    "À vérifier": "To verify",
    "A vérifier": "To verify",
    "à vérifier": "to verify",
    "a vérifier": "to verify",
    "Concurrents locaux": "Local competitors",
    "Concurrent local": "Local competitor",
    "Aucun concurrent local direct vérifié": "No verified direct local competitor",
    "Aucune source externe pertinente vérifiée": "No verified relevant external source",
    "Source externe": "External source",
    "Sources externes": "External sources",
    "Analyse terminée": "Analysis completed",
    "Analyse complète": "Complete analysis",
    "Analyse stratégique": "Strategic analysis",
    "Vérification des affirmations": "Claim verification",
    "Personas clients": "Customer personas",
    "Débat stratégique": "Strategic debate",
}


LANGUAGE_WORD_REPLACEMENTS_FR = {
    "CONDITIONAL_GO_FOR_MVP": "GO_CONDITIONNEL_POUR_MVP",
    "PIVOT_BEFORE_MVP": "PIVOTER_AVANT_MVP",
    "NO_GO_BEFORE_REPOSITIONING": "NO_GO_AVANT_REPOSITIONNEMENT",
    "PIVOT_REQUIRED": "PIVOT_NÉCESSAIRE",
    "CONTINUE_WITH_FOCUSED_MVP": "POURSUIVRE_AVEC_MVP_CIBLÉ",
    "PIVOT_BEFORE_SCALING": "PIVOTER_AVANT_SCALE",
}


def sanitize_analysis_data_for_public(
    analysis_data: Optional[Dict[str, Any]],
    project_context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Nettoie analysis_data pour les routes utilisateur.
    Ne modifie jamais la base de données.

    Phase 3K / Lot 8B :
    - nettoyage public context-locked ;
    - language lock FR/EN ;
    - pas de fallback métier hardcodé ;
    - sources hors contexte filtrées ;
    - Debate Room meta publique conservée proprement ;
    - paquets internes et listes de contamination masqués ;
    - formats publics restaurés après DomainIntegrityGuard.
    """

    if not analysis_data:
        return analysis_data

    raw_data = deepcopy(analysis_data)
    data = deepcopy(analysis_data)
    context = project_context or {}
    language = _language(data, context)

    data = _ensure_proposed_solution(data, context)
    data = _sanitize_recursive(data, context)
    data = _sanitize_external_sources(data, raw_data, context)
    data = _sanitize_competitive_analysis(data, context)

    # Preserve validated public source structures before the global
    # DomainIntegrityGuard pass. This prevents an unrelated text
    # contamination rule from silently turning retained sources into zero.
    public_source_snapshot = _snapshot_public_source_sections(data)
    public_context_gate_snapshot = _snapshot_public_context_gate_sections(data)

    data = _sanitize_debate_room(data, context)
    # DebateRoomGraph emits a deterministic, typed public contract. Preserve it
    # across the broad DomainIntegrityGuard pass so role IDs, fixed questions,
    # round titles and evidence-status labels are not rewritten as generic text.
    debate_room_snapshot = deepcopy(data.get("debate_room")) if isinstance(data.get("debate_room"), dict) else None
    # PersonaBuilderAgent emits a deterministic typed contract. Preserve the
    # already-clean public persona object across the global DomainIntegrityGuard;
    # otherwise generic but required fields such as buying power, adoption
    # triggers and interview questions can be blanked independently.
    persona_builder_snapshot = deepcopy(data.get("persona_builder")) if isinstance(data.get("persona_builder"), dict) else None
    data = _sanitize_public_limitations(data, context)
    data = _final_language_pass(data, language)

    guard_context = _build_guard_context_from_public_context(data, context)

    validation = domain_integrity_guard.validate_object(
        data=data,
        project_context=guard_context,
    )

    if not validation["is_valid"]:
        data = domain_integrity_guard.sanitize_object(
            data=data,
            project_context=guard_context,
        )
        data = _restore_safe_public_formats(data, raw_data)
        data = _sanitize_recursive(data, context)
        data = _final_language_pass(data, language)

    data = _restore_safe_public_formats(data, raw_data)
    data = _sanitize_recursive(data, context)
    data = _final_language_pass(data, language)
    data = _restore_public_source_sections(
        data,
        public_source_snapshot,
    )
    data = evidence_ledger.sanitize_public_claims(data)
    data = _restore_public_context_gate_sections(
        data,
        public_context_gate_snapshot,
        context,
    )
    if isinstance(debate_room_snapshot, dict):
        data["debate_room"] = debate_room_snapshot
    if isinstance(persona_builder_snapshot, dict):
        data["persona_builder"] = persona_builder_snapshot

    return data


def _language(
    data: Optional[Dict[str, Any]] = None,
    project_context: Optional[Dict[str, Any]] = None,
) -> str:
    data = data or {}
    project_context = project_context or {}

    return normalize_output_language(
        project_context.get("output_language")
        or data.get("output_language")
        or data.get("project_context_meta", {}).get("output_language")
        or "fr"
    )


def _build_guard_context_from_public_context(
    data: Dict[str, Any],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    if "core_terms" in project_context and "anchor_terms" in project_context:
        return project_context

    return domain_integrity_guard.build_project_context(
        title=str(project_context.get("title") or data.get("title") or ""),
        description=str(
            project_context.get("description")
            or data.get("summary")
            or data.get("problem")
            or ""
        ),
        industry=str(
            project_context.get("industry")
            or data.get("detected_sector")
            or ""
        ),
        market_region=str(
            project_context.get("market_region")
            or project_context.get("region")
            or data.get("target_region")
            or ""
        ),
        output_language=_language(data, project_context),
        analysis_data=data,
    )


def _sanitize_recursive(value: Any, project_context: Dict[str, Any]) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}

        for key, item in value.items():
            if key in TECHNICAL_KEYS_TO_HIDE:
                continue

            cleaned[key] = _sanitize_recursive(item, project_context)

        return cleaned

    if isinstance(value, list):
        return [_sanitize_recursive(item, project_context) for item in value]

    if isinstance(value, str):
        return _clean_public_text(value, project_context)

    return value


def _clean_public_text(text: str, project_context: Dict[str, Any]) -> str:
    language = _language(project_context=project_context)
    cleaned = _repair_mojibake_text(str(text or ""))

    technical_replacements = (
        TECHNICAL_WORD_REPLACEMENTS_EN
        if language == "en"
        else TECHNICAL_WORD_REPLACEMENTS_FR
    )

    language_replacements = (
        LANGUAGE_WORD_REPLACEMENTS_EN
        if language == "en"
        else LANGUAGE_WORD_REPLACEMENTS_FR
    )

    for old, new in technical_replacements.items():
        cleaned = cleaned.replace(old, new)

    for old, new in language_replacements.items():
        cleaned = cleaned.replace(old, new)

    technical_error_markers = [
        "search failed",
        "DDGS search failed",
        "operation timed out",
        "error sending request",
        "No results found",
        "provider failed",
        "model failed",
        "fallback",
        "traceback",
        "stacktrace",
        "download error",
        "certificate verify failed",
        "read timed out",
    ]

    lowered = cleaned.lower()

    if any(marker.lower() in lowered for marker in technical_error_markers):
        if language == "en":
            return (
                "Some external sources could not be fully accessed. "
                "The analysis is based on the available sources and should be "
                "completed with field validation."
            )

        return (
            "Certaines sources externes n’ont pas pu être consultées entièrement. "
            "L’analyse reste basée sur les sources disponibles et doit être "
            "complétée par une validation terrain."
        )

    return cleaned


def _ensure_proposed_solution(
    data: Dict[str, Any],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    language = _language(data, project_context)

    intelligence = data.get("project_intelligence") or {}
    structured = (
        data.get("structured_project_context")
        or intelligence.get("structured_project_context")
        or project_context.get("structured_project_context")
        or project_context.get("project_intelligence", {}).get("structured_project_context")
        or {}
    )

    explicit_solution = str(
        structured.get("solution")
        or project_context.get("solution")
        or project_context.get("solution_type")
        or ""
    ).strip()
    mvp_scope = str(
        structured.get("mvp_scope")
        or project_context.get("mvp_scope")
        or ""
    ).strip()

    # The structured solution is authoritative. It prevents the original long
    # description (problem + solution + business model) from leaking into the
    # public solution section.
    if explicit_solution:
        solution = explicit_solution
        if mvp_scope and mvp_scope.lower() not in solution.lower():
            if language == "en":
                solution = f"{solution} The first MVP is limited to: {mvp_scope}."
            else:
                solution = f"{solution} Le premier MVP est limité à : {mvp_scope}."
        data["proposed_solution"] = solution
        return data

    current = str(data.get("proposed_solution") or "").strip()
    if current:
        # Keep a short existing solution only when it is not obviously the full
        # project description containing both labelled problem and solution.
        lowered = current.lower()
        contaminated = (
            len(current) > 700
            or ("the problem is" in lowered and "the solution is" in lowered)
            or ("le problème" in lowered and "la solution" in lowered)
        )
        if not contaminated:
            return data

    title = str(project_context.get("title") or data.get("title") or "Project").strip()
    if language == "en":
        data["proposed_solution"] = (
            f"{title} must be defined as a focused MVP based only on the explicit solution and core use cases supplied by the project owner."
        )
    else:
        data["proposed_solution"] = (
            f"{title} doit être défini comme un MVP ciblé fondé uniquement sur la solution et les cas d’usage explicitement fournis par le porteur du projet."
        )
    return data

def _sanitize_external_sources(
    data: Dict[str, Any],
    raw_data: Dict[str, Any],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    forgecrawler = data.get("forgecrawler")
    raw_forgecrawler = raw_data.get("forgecrawler") or {}

    if not isinstance(forgecrawler, dict):
        return data

    raw_status = raw_forgecrawler.get("status") or forgecrawler.get("status")
    raw_errors_count = _count_hidden_errors(raw_forgecrawler)
    for group_key in [
        "sources",
        "public_sources",
        "local_competitor_sources",
        "regional_competitor_sources",
        "international_benchmark_sources",
        "market_context_sources",
    ]:
        group = forgecrawler.get(group_key)

        if not isinstance(group, list):
            continue

        cleaned_group = [
            _sanitize_public_source(item, project_context)
            for item in group
        ]

        cleaned_group = [
            item
            for item in cleaned_group
            if isinstance(item, dict)
            and (
                str(item.get("title") or "").strip()
                or str(item.get("url") or "").strip()
            )
        ]

        forgecrawler[group_key] = _deduplicate_public_sources(cleaned_group)

    sources = forgecrawler.get("sources") or []
    local_sources = forgecrawler.get("local_competitor_sources") or []
    market_sources = forgecrawler.get("market_context_sources") or []

    forgecrawler["confidence_level"] = _public_confidence_level(
        raw_status=raw_status,
        sources_count=len(sources),
        local_sources_count=len(local_sources),
        market_sources_count=len(market_sources),
        raw_errors_count=raw_errors_count,
        current_confidence=forgecrawler.get("confidence_level"),
    )

    language = _language(data, project_context)

    if raw_status == "completed":
        forgecrawler["status"] = "completed"
        forgecrawler["limitations"] = forgecrawler.get("limitations") or [
            (
                "Available external sources were used, but field validation is still recommended."
                if language == "en"
                else "Les sources externes disponibles ont été exploitées, mais une validation terrain reste recommandée."
            )
        ]

    elif raw_status == "partial":
        forgecrawler["status"] = "partial"
        forgecrawler["limitations"] = [
            (
                "Some external sources could not be fully accessed."
                if language == "en"
                else "Certaines sources externes n’ont pas pu être consultées entièrement."
            ),
            (
                "Results should be completed with field validation."
                if language == "en"
                else "Les résultats doivent être complétés par une validation terrain."
            ),
        ]

    else:
        forgecrawler["status"] = "limited"
        forgecrawler["limitations"] = [
            (
                "External source coverage is limited."
                if language == "en"
                else "La couverture des sources externes est limitée."
            ),
            (
                "Field validation is recommended before any final decision."
                if language == "en"
                else "Une validation terrain est recommandée avant toute décision finale."
            ),
        ]

    for key in [
        "errors",
        "raw_errors",
        "ddgs_errors",
        "scraping_errors",
        "queries",
    ]:
        forgecrawler.pop(key, None)

    data["forgecrawler"] = forgecrawler

    return data


def _deduplicate_public_sources(
    sources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen = set()

    for source in sources:
        source_type = str(source.get("source_type") or "").strip().lower()
        vendor_key = str(source.get("vendor_key") or "").strip().lower()
        if source_type in {"competitor", "pricing_page", "adjacent_solution"} and vendor_key:
            key = vendor_key
        else:
            key = (
                str(source.get("url") or "").strip().lower()
                or str(source.get("title") or "").strip().lower()
            )

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(source)

    return result


def _sanitize_public_source(
    source: Any,
    project_context: Dict[str, Any],
) -> Any:
    if not isinstance(source, dict):
        return source

    language = _language(project_context=project_context)

    allowed = {
        "title",
        "url",
        "snippet",
        "extracted_text_preview",
        "source_type",
        "region_match",
        "is_direct_competitor",
        "why_relevant",
        "confidence",
        "pricing_found",
        "source_relevance_score",
        "public_display",
        "same_or_close_target_user",
        "same_or_close_use_case",
        "same_or_close_solution_category",
        "matched_strong_terms",
        "vendor_key",
        "vendor_name",
        "canonical_vendor_domain",
        "sector_mismatch",
        "mismatch_terms",
        "search_provider",
        "provider_score",
    }

    cleaned = {
        key: _sanitize_recursive(value, project_context)
        for key, value in source.items()
        if key in allowed
    }

    fallback_title = "External source" if language == "en" else "Source externe"

    cleaned["title"] = _clean_source_title(
        str(cleaned.get("title") or fallback_title),
        language=language,
    )

    return cleaned


def _clean_source_title(title: str, language: str = "fr") -> str:
    fallback = "External source" if language == "en" else "Source externe"

    text = str(title or "").strip()

    if not text:
        return fallback

    separators = [" — ", " - ", " : ", "|"]

    for separator in separators:
        if separator in text:
            text = text.split(separator)[0].strip()

    words = text.split()

    if len(words) > 10:
        text = " ".join(words[:10]) + "..."

    return text or fallback


def _sanitize_competitive_analysis(
    data: Dict[str, Any],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    competitive = data.get("competitive_analysis")

    if not isinstance(competitive, dict):
        return data

    for group_key in [
        "local_direct_competitors",
        "local_adjacent_solutions",
        "regional_competitors",
        "international_benchmarks",
        "market_context_sources",
    ]:
        group = competitive.get(group_key)

        if isinstance(group, list):
            cleaned_group = [
                _sanitize_competitive_item(item, project_context) for item in group
            ]

            cleaned_group = [
                item for item in cleaned_group if isinstance(item, dict)
            ]

            # Business relevance has already been decided upstream.
            # The public sanitizer only cleans the payload shape and text.
            competitive[group_key] = _deduplicate_competitive_items(cleaned_group)

    if competitive.get("confidence_level") == "high":
        sources_count = competitive.get("sources_count") or 0
        local_count = competitive.get("local_competitors_count") or 0

        try:
            sources_count_int = int(sources_count)
            local_count_int = int(local_count)
        except Exception:
            sources_count_int = 0
            local_count_int = 0

        if sources_count_int < 5 or local_count_int <= 1:
            competitive["confidence_level"] = "medium"

    data["competitive_analysis"] = competitive

    return data


def _deduplicate_competitive_items(
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        vendor_key = str(item.get("vendor_key") or "").strip().lower()
        key = vendor_key or str(
            item.get("source_url")
            or item.get("url")
            or item.get("name")
            or item.get("title")
            or ""
        ).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _competitor_to_source_like(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": item.get("name") or item.get("title") or "",
        "snippet": item.get("evidence") or item.get("description") or "",
        "extracted_text_preview": item.get("evidence") or item.get("description") or "",
        "why_relevant": item.get("why_relevant") or item.get("evidence") or "",
        "url": item.get("source_url") or item.get("url") or "",
        **item,
    }


def _sanitize_competitive_item(
    item: Any,
    project_context: Dict[str, Any],
) -> Any:
    if not isinstance(item, dict):
        return item

    language = _language(project_context=project_context)
    cleaned = deepcopy(item)

    if "name" in cleaned:
        cleaned["name"] = _clean_source_title(
            str(cleaned["name"]),
            language=language,
        )

    if "title" in cleaned:
        cleaned["title"] = _clean_source_title(
            str(cleaned["title"]),
            language=language,
        )

    cleaned.pop("error", None)
    cleaned.pop("raw_error", None)
    cleaned.pop("search_query", None)

    return _sanitize_recursive(cleaned, project_context)


def _sanitize_debate_room(
    data: Dict[str, Any],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    debate_room = data.get("debate_room")

    if not isinstance(debate_room, dict):
        return data

    language = _language(data, project_context)

    if "title" not in debate_room:
        debate_room["title"] = (
            "Debate Room Pro+ — Project Review Committee"
            if language == "en"
            else "Salle de débat stratégique — Comité de validation projet"
        )

    rounds = debate_room.get("rounds")

    if isinstance(rounds, list):
        debate_room["rounds"] = [
            _sanitize_debate_round(round_item, project_context)
            for round_item in rounds
        ]

    meta = debate_room.get("meta")

    if isinstance(meta, dict):
        debate_room["meta"] = {
            key: _sanitize_recursive(value, project_context)
            for key, value in meta.items()
            if key in SAFE_META_KEYS
        }

    judge = debate_room.get("judge")

    if isinstance(judge, dict):
        debate_room["judge"] = _sanitize_recursive(judge, project_context)

    debate_room["output_language"] = language
    debate_room["context_locked"] = True

    data["debate_room"] = debate_room

    return data


def _sanitize_debate_round(
    round_item: Any,
    project_context: Dict[str, Any],
) -> Any:
    if not isinstance(round_item, dict):
        return round_item

    cleaned = deepcopy(round_item)

    for role_key in ["moderator", "defender", "critic", "judge", "round_summary"]:
        role_data = cleaned.get(role_key)

        if isinstance(role_data, dict):
            cleaned[role_key] = _sanitize_recursive(role_data, project_context)

    cleaned["context_locked"] = True
    cleaned["output_language"] = _language(project_context=project_context)

    return _sanitize_recursive(cleaned, project_context)


def _sanitize_public_limitations(
    data: Dict[str, Any],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    public_limitations = data.get("public_limitations")
    language = _language(data, project_context)

    if isinstance(public_limitations, list) and public_limitations:
        data["public_limitations"] = [
            _clean_public_text(str(item), project_context)
            for item in public_limitations
        ]
        return data

    limitations: List[str] = []

    forgecrawler = data.get("forgecrawler")

    if isinstance(forgecrawler, dict):
        if forgecrawler.get("status") == "partial":
            limitations.append(
                "Some external sources could not be fully accessed."
                if language == "en"
                else "Certaines sources externes n’ont pas pu être consultées entièrement."
            )

        if forgecrawler.get("confidence_level") in {"low", "medium"}:
            limitations.append(
                "The confidence level should be strengthened with field validation."
                if language == "en"
                else "Le niveau de confiance doit être renforcé par des validations terrain."
            )

    market_study = data.get("market_study")

    if isinstance(market_study, dict):
        if market_study.get("data_confidence") in {"low", "medium"}:
            limitations.append(
                "Market estimates should be confirmed with reliable regional or sector data."
                if language == "en"
                else "Les estimations de marché doivent être confirmées par des données régionales ou sectorielles fiables."
            )

    if not limitations:
        limitations.append(
            "Results should be used as decision support and validated through field research."
            if language == "en"
            else "Les résultats doivent être utilisés comme aide à la décision et validés par une étude terrain."
        )

    data["public_limitations"] = _unique_strings(limitations)

    return data


def _final_language_pass(value: Any, language: str) -> Any:
    context = {"output_language": language}

    if isinstance(value, dict):
        return {
            key: _final_language_pass(item, language)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _final_language_pass(item, language)
            for item in value
        ]

    if isinstance(value, str):
        return _clean_public_text(value, context)

    return value


def _repair_mojibake_text(value: str) -> str:
    """
    Répare les séquences UTF-8 courantes affichées comme du texte mojibake.

    Cette fonction est volontairement déterministe et limitée à des séquences
    connues. Elle ne transforme pas arbitrairement le contenu métier.
    """
    repaired = str(value or "")

    for broken, correct in MOJIBAKE_TEXT_REPLACEMENTS.items():
        repaired = repaired.replace(broken, correct)

    return repaired


def _snapshot_public_context_gate_sections(
    data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Capture uniquement les champs publics du gate de contexte.

    Le DomainIntegrityGuard reste libre de nettoyer le reste du rapport,
    mais ne doit jamais supprimer les questions nécessaires à l'utilisateur
    pour compléter son projet.
    """
    snapshot: Dict[str, Dict[str, Any]] = {}

    for section_name, allowed_fields in (
        PUBLIC_CONTEXT_GATE_SECTION_FIELDS.items()
    ):
        section = data.get(section_name)

        if not isinstance(section, dict):
            continue

        snapshot[section_name] = {
            key: deepcopy(section[key])
            for key in allowed_fields
            if key in section
        }

    return snapshot


def _restore_public_context_gate_sections(
    data: Dict[str, Any],
    snapshot: Dict[str, Dict[str, Any]],
    project_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Restaure le contrat public du gate après les sanitizers génériques.

    Les textes restent nettoyés, mais les listes de questions, champs manquants,
    ambiguïtés et blocages conservent leur contenu et leur ordre.
    """
    restored = dict(data)

    for section_name, fields in snapshot.items():
        current_section = dict(restored.get(section_name) or {})
        safe_fields = _sanitize_recursive(
            deepcopy(fields),
            project_context,
        )

        if isinstance(safe_fields, dict):
            current_section.update(safe_fields)

        restored[section_name] = current_section

    return restored


def _snapshot_public_source_sections(
    data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    snapshot: Dict[str, Dict[str, Any]] = {}

    for section_name, allowed_fields in PUBLIC_SOURCE_SECTION_FIELDS.items():
        section = data.get(section_name)

        if not isinstance(section, dict):
            continue

        snapshot[section_name] = {
            key: deepcopy(section[key])
            for key in allowed_fields
            if key in section
        }

    return snapshot


def _restore_public_source_sections(
    data: Dict[str, Any],
    snapshot: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    restored = dict(data)

    for section_name, fields in snapshot.items():
        current_section = dict(restored.get(section_name) or {})
        current_section.update(deepcopy(fields))
        restored[section_name] = current_section

    return restored


def _restore_safe_public_formats(
    data: Dict[str, Any],
    raw_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Restaure les champs format publics après DomainIntegrityGuard.

    Ces formats sont techniques mais utiles pour le frontend et la validation.
    On restaure uniquement les formats des sections publiques validées.
    """

    if not isinstance(data, dict) or not isinstance(raw_data, dict):
        return data

    public_sections = [
        "startup_score",
        "financial_estimation",
        "market_study",
        "swot",
        "business_model_canvas",
        "persona_builder",
        "debate_room",
    ]

    for section_key in public_sections:
        section = data.get(section_key)
        raw_section = raw_data.get(section_key)

        if not isinstance(section, dict) or not isinstance(raw_section, dict):
            continue

        raw_format = raw_section.get("format")

        if isinstance(raw_format, str) and raw_format.strip():
            section["format"] = raw_format.strip()

    debate_room = data.get("debate_room")
    raw_debate_room = raw_data.get("debate_room")

    if isinstance(debate_room, dict) and isinstance(raw_debate_room, dict):
        judge = debate_room.get("judge")
        raw_judge = raw_debate_room.get("judge")

        if isinstance(judge, dict) and isinstance(raw_judge, dict):
            raw_judge_format = raw_judge.get("format")

            if isinstance(raw_judge_format, str) and raw_judge_format.strip():
                judge["format"] = raw_judge_format.strip()

    return data


def _public_confidence_level(
    raw_status: Any,
    sources_count: int,
    local_sources_count: int,
    market_sources_count: int,
    raw_errors_count: int,
    current_confidence: Any,
) -> str:
    if sources_count <= 2:
        return "low"

    if raw_status == "partial" or raw_errors_count > 0:
        if sources_count >= 5 and (
            local_sources_count >= 1 or market_sources_count >= 3
        ):
            return "medium"

        return "low"

    if current_confidence in {"low", "medium", "high"}:
        return str(current_confidence)

    return "medium"


def _count_hidden_errors(value: Any) -> int:
    if isinstance(value, dict):
        count = 0

        for key, item in value.items():
            if key in {
                "errors",
                "raw_errors",
                "ddgs_errors",
                "scraping_errors",
                "provider_errors",
                "llm_errors",
            }:
                if isinstance(item, list):
                    count += len(item)
                elif item:
                    count += 1

            count += _count_hidden_errors(item)

        return count

    if isinstance(value, list):
        return sum(_count_hidden_errors(item) for item in value)

    return 0


def _unique_strings(items: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()

    for item in items:
        clean = str(item).strip()

        if not clean:
            continue

        key = clean.lower()

        if key not in seen:
            seen.add(key)
            result.append(clean)

    return result