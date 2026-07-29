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
    "pricing_found",
    "confidence",
    "partial_completion",

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

    data = _sanitize_recursive(data, context)
    data = _ensure_proposed_solution(data, context)
    data = _sanitize_external_sources(data, raw_data, context)
    data = _sanitize_competitive_analysis(data, context)
    data = _sanitize_debate_room(data, context)
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
    cleaned = str(text or "")

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
    proposed_solution = data.get("proposed_solution")

    if isinstance(proposed_solution, str) and proposed_solution.strip():
        return data

    language = _language(data, project_context)

    title_fallback = "The project" if language == "en" else "Le projet"

    title = str(project_context.get("title") or data.get("title") or title_fallback)
    description = str(
        project_context.get("description")
        or data.get("summary")
        or data.get("problem")
        or ""
    )
    industry = str(
        project_context.get("industry")
        or data.get("detected_sector")
        or ""
    )
    region = str(
        project_context.get("market_region")
        or project_context.get("region")
        or data.get("target_region")
        or ""
    )

    if language == "en":
        data["proposed_solution"] = (
            f"{title} should be reduced to a clear MVP directly based on the user's "
            f"project description: {description[:300]}. "
            f"The first version must match the target sector"
            f"{' (' + industry + ')' if industry else ''}"
            f"{' and target region ' + region if region else ''}. "
            "No sector-specific feature should be added unless it is explicitly present "
            "in the project input or verified sources."
        )
        return data

    data["proposed_solution"] = (
        f"{title} doit être réduit à un MVP clair directement basé sur la description "
        f"du projet utilisateur : {description[:300]}. "
        f"La première version doit rester alignée avec le secteur ciblé"
        f"{' (' + industry + ')' if industry else ''}"
        f"{' et la région ' + region if region else ''}. "
        "Aucune fonctionnalité métier spécifique ne doit être ajoutée si elle n’apparaît "
        "pas dans l’input du projet ou dans des sources vérifiées."
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
    guard_context = _build_guard_context_from_public_context(data, project_context)

    for group_key in [
        "sources",
        "local_competitor_sources",
        "regional_competitor_sources",
        "international_benchmark_sources",
        "market_context_sources",
    ]:
        group = forgecrawler.get(group_key)

        if isinstance(group, list):
            cleaned_group = [
                _sanitize_public_source(item, project_context) for item in group
            ]

            cleaned_group = [
                item for item in cleaned_group if isinstance(item, dict)
            ]

            forgecrawler[group_key] = domain_integrity_guard.filter_sources(
                sources=cleaned_group,
                project_context=guard_context,
                min_overlap=1,
            )

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

    guard_context = _build_guard_context_from_public_context(data, project_context)

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

            if group_key != "market_context_sources":
                source_like_items = [
                    _competitor_to_source_like(item)
                    for item in cleaned_group
                ]

                filtered_items = domain_integrity_guard.filter_sources(
                    sources=source_like_items,
                    project_context=guard_context,
                    min_overlap=1,
                )

                competitive[group_key] = filtered_items
            else:
                competitive[group_key] = cleaned_group

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