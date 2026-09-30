"""
Readable analysis diagnostic for the admin console (Sprint 7.8).

Pure function over a Project: it reads what the pipeline stored in
analysis_data and decides everything the page shows (step order, status,
French wording, one-line summary). The page only displays it.

What the analysis does NOT record (model used, per-step durations) is
listed in `not_recorded` instead of being guessed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.health_checks import redact

# Pipeline order (startup_evaluator_graph) + the debate room that follows it.
# key -> (French label, analysis_data block holding status/fallback flags)
STEPS: list[tuple[str, str, str | None]] = [
    ("idea_readiness_check", "Vérification de la maturité de l'idée", "idea_readiness"),
    ("project_intelligence_layer", "Compréhension du projet", "project_intelligence"),
    ("competitive_analysis", "Analyse concurrentielle", "competitive_analysis"),
    ("market_study", "Étude de marché", "market_study"),
    ("swot", "SWOT", "swot"),
    ("business_model_canvas", "Business Model Canvas", "business_model_canvas"),
    ("financial_estimation", "Estimation financière", "financial_estimation"),
    ("persona_builder", "Personas", "persona_builder"),
    ("fact_checker", "Vérification des faits", "fact_check_report"),
    ("startup_score", "Score de la startup", "startup_score"),
    ("debate_room", "Salle de débat", None),
]
STEP_LABELS = {key: label for key, label, _ in STEPS}

STATUS_LABELS = {
    "completed": "Réussie",
    "degraded": "Réussie avec repli",
    "failed": "Échouée",
    "running": "En cours",
    "not_run": "Non exécutée",
}

CONFIDENCE_LABELS = {"high": "Élevée", "medium": "Moyenne", "low": "Faible", "very_low": "Très faible"}
PROCESS_STATUS_LABELS = {
    "completed": "Terminée", "running": "En cours", "failed": "Échouée", "skipped": "Ignorée",
    "partial": "Partielle", "pending": "En attente",
}
VERDICT_LABELS = {
    "strong_go": "Go franc", "go": "Go", "conditional_go": "Go sous conditions",
    "pivot": "Pivot recommandé", "no_go": "No go", "needs_clarification": "Clarification nécessaire",
}

NOT_RECORDED = ["Modèle d'IA utilisé à chaque étape", "Durée de chaque étape"]

# Where the pipeline may leave technical errors; value = French "where" label.
ERROR_SOURCES = {
    "forgecrawler": "Recherche de sources",
    "competitive_analysis": "Analyse concurrentielle",
    "market_study": "Étude de marché",
    "fact_check_report": "Vérification des faits",
}
ERROR_KEYS = {"errors", "error", "raw_errors", "ddgs_errors", "scraping_errors", "provider_errors",
              "llm_errors", "model_errors", "fallback_errors"}
QUERY_KEYS = {"queries", "query", "search_query"}
MAX_ITEMS = 100


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    """Flatten nested str/list/dict values into clean non-empty strings."""
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [item for element in value for item in _strings(element)]
    if isinstance(value, dict):
        # An error object: keep its message, not its whole structure.
        for key in ("message", "error", "detail"):
            if isinstance(value.get(key), str):
                return _strings(value[key])
    return []


def _collect(value: Any, keys: set[str], depth: int = 0) -> list[str]:
    """Every string stored under one of `keys`, anywhere in `value` (bounded depth)."""
    if depth > 12:
        return []
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys:
                found.extend(_strings(child))
            else:
                found.extend(_collect(child, keys, depth + 1))
    elif isinstance(value, list):
        for child in value:
            found.extend(_collect(child, keys, depth + 1))
    return found


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _step_notes(key: str, block: dict, meta: dict) -> list[str]:
    fallback = bool(block.get("fallback_used"))
    handled = bool(block.get("error_handled"))
    if key == "fact_checker":  # the evaluator also records the fact checker's flags
        fallback = fallback or bool(meta.get("fact_checker_fallback_used"))
        handled = handled or bool(meta.get("fact_checker_error_handled"))
    notes = []
    if fallback:
        notes.append("Réponse de secours utilisée")
    if handled:
        notes.append("Erreur rattrapée pendant l'étape")
    return notes


def _step_error(key: str, meta: dict) -> str | None:
    """The evaluator keeps one message, "<step> failed: <exception>"."""
    message = meta.get("error")
    if not isinstance(message, str) or not message.strip():
        return None
    prefix = f"{key} failed:"
    if message.startswith(prefix):
        return redact(message[len(prefix):].strip())
    return None


def _build_steps(data: dict, analysis_status: str | None) -> list[dict]:
    meta = _dict(data.get("startup_evaluator_meta"))
    completed = set(_strings(meta.get("completed_steps")))
    failed = set(_strings(meta.get("failed_steps")))
    current = meta.get("current_step")
    running = analysis_status in {"running", "queued"}
    debate_meta = _dict(_dict(data.get("debate_room")).get("meta"))

    result = []
    for key, label, block_key in STEPS:
        block = _dict(data.get(block_key)) if block_key else {}
        notes: list[str] = []
        error = None
        if key == "debate_room":
            status = "completed" if debate_meta.get("completed") is True else "not_run"
            if debate_meta.get("error"):
                status, error = "failed", redact(str(debate_meta["error"]))
        elif key in failed:
            status, error = "failed", _step_error(key, meta)
        elif key in completed:
            notes = _step_notes(key, block, meta)
            status = "degraded" if notes else "completed"
        elif running and key == current:
            status = "running"
        else:
            status = "not_run"
        result.append({"key": key, "label": label, "status": status,
                       "status_label": STATUS_LABELS[status], "notes": notes, "error": error})
    return result


# ---------------------------------------------------------------------------
# Summary, sources, errors, queries
# ---------------------------------------------------------------------------

def _summary(project: Any, steps: list[dict]) -> dict:
    done = sum(step["status"] in {"completed", "degraded"} for step in steps)
    degraded = sum(step["status"] == "degraded" for step in steps)
    failed = [step for step in steps if step["status"] == "failed"]
    status = project.analysis_status

    if failed or status == "failed":
        level = "error"
        headline = (f"Analyse en échec à l'étape « {failed[0]['label']} »" if failed
                    else "Analyse en échec")
    elif status in {"running", "queued"}:
        level, headline = "running", "Analyse en cours"
    elif done == 0:
        level, headline = "not_started", "Aucune analyse lancée"
    elif degraded:
        level = "warning"
        plural = "s" if degraded > 1 else ""
        headline = f"Analyse terminée avec {degraded} étape{plural} en repli"
    else:
        level, headline = "ok", "Analyse terminée sans incident"

    started, ended = _aware(project.analysis_started_at), _aware(project.analysis_completed_at)
    duration = int((ended - started).total_seconds()) if started and ended and ended >= started else None
    return {"level": level, "headline": headline, "steps_done": done, "steps_total": len(steps),
            "duration_seconds": duration}


def _sources(data: dict) -> dict:
    crawler = _dict(data.get("forgecrawler"))
    quality = _dict(crawler.get("source_quality"))
    total = _count(crawler.get("sources_count"))
    if total is None and isinstance(crawler.get("sources"), list):
        total = len(crawler["sources"])
    return {
        "status_label": PROCESS_STATUS_LABELS.get(str(crawler.get("status")), "Non exécutée"),
        "confidence_label": CONFIDENCE_LABELS.get(str(crawler.get("confidence_level")), "Inconnue"),
        "total": total or 0,
        "local": _count(crawler.get("local_sources_count")),
        "regional": _count(crawler.get("regional_sources_count")),
        "international": _count(crawler.get("international_sources_count")),
        "local_competitors": _count(crawler.get("local_competitors_count")),
        "market": _count(crawler.get("market_sources_count")),
        "rejected": _count(quality.get("rejected_sources_count")),
        "removed_by_safety_filter": _count(quality.get("removed_from_public_after_safety_filter")),
        "no_relevant_source": bool(crawler.get("no_verified_relevant_source_found")),
    }


def _evidence(data: dict) -> dict:
    score = _dict(data.get("startup_score"))
    coverage = _dict(_dict(data.get("fact_check_report")).get("claim_coverage"))
    verdict = str(data.get("verdict_code") or score.get("verdict_code") or "").lower()
    raw_score = score.get("score")
    return {
        "overall_label": CONFIDENCE_LABELS.get(str(data.get("overall_evidence_confidence")), "Inconnue"),
        "verdict_label": VERDICT_LABELS.get(verdict, "Aucun verdict"),
        "score": raw_score if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool) else None,
        "claims_total": _count(coverage.get("total")),
        "claims_sourced": _count(coverage.get("sourced")),
        "claims_estimated": _count(coverage.get("estimated")),
    }


def _errors(data: dict, steps: list[dict]) -> list[dict]:
    items = [{"where": step["label"], "message": step["error"]} for step in steps if step["error"]]
    for block_key, where in ERROR_SOURCES.items():
        for message in _collect(_dict(data.get(block_key)), ERROR_KEYS):
            items.append({"where": where, "message": redact(message)})
    unique: list[dict] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return unique[:MAX_ITEMS]


def _queries(data: dict) -> dict:
    found = _collect(data, QUERY_KEYS)
    unique: list[str] = []
    seen: set[str] = set()
    for query in found:
        normalized = " ".join(query.split()).casefold()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(" ".join(query.split()))
    return {"total": len(found), "unique": unique[:MAX_ITEMS]}


def build(project: Any) -> dict:
    data = _dict(project.analysis_data)
    steps = _build_steps(data, project.analysis_status)
    return {
        "summary": _summary(project, steps),
        "steps": steps,
        "sources": _sources(data),
        "evidence": _evidence(data),
        "errors": _errors(data, steps),
        "queries": _queries(data),
        "not_recorded": list(NOT_RECORDED),
    }
