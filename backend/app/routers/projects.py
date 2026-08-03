import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.business_analyst_agent import AIBusinessAnalystAgent
from app.agents.debate_room_graph import DebateRoomGraph
from app.agents.startup_evaluator_graph import StartupEvaluatorGraph
from app.database import AsyncSessionLocal, get_db
from app.models import Project, User
from app.schemas.project import (
    ProjectAnalysisResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.security import get_current_user
from app.services.domain_integrity_guard import normalize_output_language
from app.services.idea_readiness_checker import idea_readiness_checker
from app.services.project_context_builder import project_context_builder
from app.services.public_analysis_sanitizer import sanitize_analysis_data_for_public
from app.services.analysis_run_guard import analysis_run_guard
from app.services.evidence_ledger import evidence_ledger
from app.services.canonical_source_ledger import canonical_source_ledger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_market_region(region: Optional[str]) -> str:
    """
    Normalise la région sans inventer de pays par défaut.

    Une région absente reste vide afin que le ContextConfidenceGate puisse
    la signaler comme ambiguë ou bloquante selon le type de projet.
    """
    if region is None:
        return ""

    return str(region).strip()


def public_analysis_step(
    step: Optional[str],
    output_language: str = "fr",
) -> Optional[str]:
    if not step:
        return step

    language = normalize_output_language(output_language)
    cleaned = step

    if language == "en":
        replacements = {
            "Préparation de l’analyse": "Preparing analysis",
            "Préparation des données projet": "Preparing project data",
            "Clarification du projet requise": "Project clarification required",
            "Sprint 2 - RAG global/local et analyse initiale": "Initial project analysis",
            "Sprint 2 terminé - préparation Startup Evaluator": "Initial analysis completed - preparing strategic evaluation",
            "Sprint 3 - lancement Startup Evaluator": "Launching strategic evaluation",
            "Sprint 3 terminé - lancement Debate Room": "Strategic evaluation completed - launching debate room",
            "Debate Room - lancement du débat stratégique": "Launching strategic debate",
            "Analyse Sprint 3 + Debate Room terminée partiellement": "Strategic analysis partially completed",
            "Analyse Sprint 3 + Debate Room terminée": "Strategic analysis completed",
            "Erreur pendant l’analyse": "Analysis error",
            "Sprint 2": "Initial analysis",
            "Sprint 3": "Strategic analysis",
            "Startup Evaluator": "Strategic evaluator",
            "startup_evaluator": "strategic evaluator",
            "Debate Room": "Strategic debate",
            "LangGraph": "analysis workflow",
            "RAG": "available sources",
            "ForgeCrawler": "external sources",
            "Fact Checker": "Claim verification",
            "fact_checker": "claim verification",
            "persona_builder": "Customer personas",
            "competitive_analysis": "Competitive analysis",
            "financial_estimation": "Financial estimation",
            "market_study": "Market study",
            "business_model_canvas": "Business model canvas",
            "startup_score": "Startup score",
        }
    else:
        replacements = {
            "Clarification du projet requise": "Clarification du projet requise",
            "Sprint 2 - RAG global/local et analyse initiale": "Analyse initiale du projet",
            "Sprint 2": "Analyse initiale",
            "Sprint 3": "Analyse stratégique",
            "Startup Evaluator": "Évaluation stratégique",
            "startup_evaluator": "évaluation stratégique",
            "Debate Room": "Débat stratégique",
            "LangGraph": "workflow d’analyse",
            "RAG": "sources disponibles",
            "ForgeCrawler": "sources externes",
            "Fact Checker": "Vérification des affirmations",
            "fact_checker": "Vérification des affirmations",
            "persona_builder": "Personas clients",
            "competitive_analysis": "Analyse concurrentielle",
            "financial_estimation": "Estimation financière",
            "market_study": "Étude de marché",
            "business_model_canvas": "Business Model Canvas",
            "startup_score": "Score startup",
        }

    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)

    return cleaned


def public_analysis_error(
    error: Optional[str],
    output_language: str = "fr",
) -> Optional[str]:
    if not error:
        return None

    language = normalize_output_language(output_language)

    if language == "en":
        return (
            "Part of the analysis could not be completed automatically. "
            "The available results remain accessible and should be validated "
            "through field research."
        )

    return (
        "Une partie de l’analyse n’a pas pu être complétée automatiquement. "
        "Les résultats disponibles restent consultables et doivent être validés "
        "par une étude terrain."
    )


def build_public_project_context(project: Project) -> dict:
    return {
        "title": project.title,
        "description": project.description,
        "industry": project.industry,
        "region": project.market_region,
        "market_region": project.market_region,
        "output_language": getattr(project, "output_language", "fr"),
    }


# ============================================================
# Public competitive analysis restore
# ============================================================
#
# Pourquoi ce bloc existe :
# - ForgeCrawler + SourceRelevanceGate filtrent déjà les sources.
# - StartupEvaluatorGraph ne sanitize pas competitive_analysis.
# - Mais projects.py repasse tout analysis_data dans le public sanitizer.
# - Ce sanitizer peut supprimer/écraser les nouvelles clés sources.
# - On restaure donc uniquement les champs publics sûrs.
#
# Ce bloc ne restaure jamais :
# - debug
# - raw_data
# - internal_only=True
# - rejected=True
# - raw_response
# ============================================================

def _safe_public_source_item(source: Any) -> dict:
    if not isinstance(source, dict):
        return {}

    if source.get("rejected") is True:
        return {}

    if source.get("internal_only") is True:
        return {}

    allowed_fields = {
        "title",
        "url",
        "snippet",
        "extracted_text_preview",
        "extraction_method",
        "text_extracted",
        "pricing_found",
        "confidence",
        "source_type",
        "source_role",
        "comparison_scope",
        "region_match",
        "is_direct_competitor",
        "technology_supplier",
        "canonical_source_id",
        "why_relevant",
        "source_relevance_score",
        "public_display",
        "matched_strong_terms",
        "matched_weak_terms",
        "matched_forbidden_terms",
        "rejection_reason",
    }

    clean_source = {}

    for key in allowed_fields:
        if key in source:
            clean_source[key] = source.get(key)

    return clean_source


def _safe_public_source_list(value: Any) -> List[dict]:
    if not isinstance(value, list):
        return []

    result: List[dict] = []

    for item in value:
        clean_item = _safe_public_source_item(item)

        if clean_item.get("title") or clean_item.get("url"):
            result.append(clean_item)

    return result


def restore_public_competitive_analysis(
    raw_analysis_data: Optional[dict],
    sanitized_analysis_data: Optional[dict],
) -> Optional[dict]:
    """
    Restore public-safe competitive_analysis after global public sanitizer.

    Important :
    - Ne restaure que les sources déjà filtrées par ForgeCrawler.
    - Ne restaure pas les sources internes.
    - Ne restaure pas les sources rejetées.
    - Ne restaure pas le debug.
    """

    if not isinstance(raw_analysis_data, dict):
        return sanitized_analysis_data

    if not isinstance(sanitized_analysis_data, dict):
        return sanitized_analysis_data

    raw_competitive = raw_analysis_data.get("competitive_analysis") or {}

    if not isinstance(raw_competitive, dict):
        return sanitized_analysis_data

    raw_sources = _safe_public_source_list(
        raw_competitive.get("sources")
        or raw_competitive.get("public_sources")
    )
    source_ledger = canonical_source_ledger.build(raw_sources)
    raw_sources = list(source_ledger.get("sources") or [])
    raw_local_sources = list(
        source_ledger.get("local_direct_competitor_sources") or []
    )
    raw_adjacent_sources = list(
        source_ledger.get("adjacent_solution_sources") or []
    )
    raw_regional_sources = list(
        source_ledger.get("regional_benchmark_sources") or []
    )
    raw_international_sources = list(
        source_ledger.get("international_benchmark_sources") or []
    )
    raw_technology_sources = list(
        source_ledger.get("technology_provider_sources") or []
    )
    raw_market_sources = list(
        source_ledger.get("evidence_sources") or []
    )

    restored_sources_count = int(source_ledger.get("sources_count") or len(raw_sources))
    restored_local_count = len(raw_local_sources)
    restored_regional_count = len(raw_regional_sources)
    restored_international_count = len(raw_international_sources)
    restored_technology_count = len(raw_technology_sources)
    restored_market_count = len(raw_market_sources)

    if restored_sources_count <= 0:
        return sanitized_analysis_data

    sanitized = dict(sanitized_analysis_data)
    public_competitive = dict(sanitized.get("competitive_analysis") or {})

    public_competitive.update(
        {
            "format": raw_competitive.get("format")
            or public_competitive.get("format")
            or "competitive_analysis_public_restored",
            "status": raw_competitive.get("status")
            or public_competitive.get("status")
            or "completed",
            "confidence_level": raw_competitive.get("confidence_level")
            or public_competitive.get("confidence_level")
            or "medium",
            "source_based": True,
            "context_locked": bool(raw_competitive.get("context_locked", True)),
            "target_region": raw_competitive.get("target_region")
            or public_competitive.get("target_region"),
            "sources_count": restored_sources_count,
            "canonical_sources_count": restored_sources_count,
            "canonical_source_ledger": source_ledger,
            "local_competitors_found": restored_local_count > 0,
            "local_competitors_count": restored_local_count,
            "regional_competitors_count": restored_regional_count,
            "international_benchmarks_count": restored_international_count,
            "technology_providers_count": restored_technology_count,
            "market_sources_count": restored_market_count,
            "sources": raw_sources,
            "public_sources": raw_sources,
            "local_competitor_sources": raw_local_sources,
            "regional_competitor_sources": raw_regional_sources,
            "international_benchmark_sources": raw_international_sources,
            "technology_provider_sources": raw_technology_sources,
            "adjacent_solution_sources": raw_adjacent_sources,
            "market_context_sources": raw_market_sources,
            "no_verified_relevant_source_found": False,
            "no_source_message": "",
            "limitations": raw_competitive.get("limitations")
            or public_competitive.get("limitations")
            or [],
        }
    )

    # Aliases pour compatibilité avec différentes versions frontend.
    public_competitive["verified_competitors"] = raw_local_sources
    public_competitive["local_competitors"] = raw_local_sources
    public_competitive["regional_competitors"] = raw_regional_sources
    public_competitive["international_benchmarks"] = raw_international_sources
    public_competitive["technology_providers"] = raw_technology_sources
    public_competitive["local_adjacent_solutions"] = raw_adjacent_sources
    public_competitive["market_sources"] = raw_market_sources

    public_competitive["external_sources"] = {
        "sources_count": restored_sources_count,
        "canonical_sources_count": restored_sources_count,
        "local_competitors_count": restored_local_count,
        "local_adjacent_solutions_count": len(raw_adjacent_sources),
        "regional_competitors_count": restored_regional_count,
        "international_benchmarks_count": restored_international_count,
        "technology_providers_count": restored_technology_count,
        "market_sources_count": restored_market_count,
        "canonical_source_ledger": source_ledger,
        "sources": raw_sources,
        "public_sources": raw_sources,
        "local_competitor_sources": raw_local_sources,
        "regional_competitor_sources": raw_regional_sources,
        "international_benchmark_sources": raw_international_sources,
        "technology_provider_sources": raw_technology_sources,
        "adjacent_solution_sources": raw_adjacent_sources,
        "market_context_sources": raw_market_sources,
        "verified_competitors": raw_local_sources,
        "local_competitors": raw_local_sources,
        "regional_competitors": raw_regional_sources,
        "international_benchmarks": raw_international_sources,
        "technology_providers": raw_technology_sources,
        "local_adjacent_solutions": raw_adjacent_sources,
        "market_sources": raw_market_sources,
    }

    sanitized["competitive_analysis"] = public_competitive

    return sanitized


def log_public_source_integrity(
    *,
    project_id: int,
    raw_analysis_data: Optional[dict],
    public_analysis_data: Optional[dict],
) -> None:
    raw_competitive = (
        (raw_analysis_data or {}).get("competitive_analysis")
        or {}
    )
    public_competitive = (
        (public_analysis_data or {}).get("competitive_analysis")
        or {}
    )

    raw_count = len(raw_competitive.get("sources") or [])
    public_count = len(public_competitive.get("sources") or [])

    if raw_count != public_count:
        logger.error(
            "[SourcePipeline][IntegrityError] "
            "project_id=%s | raw=%s | public=%s",
            project_id,
            raw_count,
            public_count,
        )
    else:
        logger.info(
            "[SourcePipeline][IntegrityOK] "
            "project_id=%s | sources=%s",
            project_id,
            public_count,
        )


def project_to_public_response(project: Project) -> dict:
    output_language = normalize_output_language(
        getattr(project, "output_language", "fr")
    )

    public_context = build_public_project_context(project)

    sanitized_analysis_data = sanitize_analysis_data_for_public(
        project.analysis_data,
        project_context=public_context,
    )

    sanitized_analysis_data = restore_public_competitive_analysis(
        raw_analysis_data=project.analysis_data,
        sanitized_analysis_data=sanitized_analysis_data,
    )

    log_public_source_integrity(
        project_id=project.id,
        raw_analysis_data=project.analysis_data,
        public_analysis_data=sanitized_analysis_data,
    )

    return {
        "id": project.id,
        "user_id": project.user_id,
        "title": project.title,
        "description": project.description,
        "industry": project.industry,
        "market_region": project.market_region,
        "output_language": output_language,
        "status": project.status,
        "startup_score": project.startup_score,
        "analysis_status": project.analysis_status,
        "analysis_step": public_analysis_step(
            project.analysis_step,
            output_language,
        ),
        "analysis_progress": project.analysis_progress,
        "analysis_data": sanitized_analysis_data,
        "analysis_error": public_analysis_error(
            project.analysis_error,
            output_language,
        ),
        "analysis_started_at": project.analysis_started_at,
        "analysis_completed_at": project.analysis_completed_at,
        "analysis_run_id": project.analysis_run_id,
        "analysis_heartbeat_at": project.analysis_heartbeat_at,
        "analysis_attempt": project.analysis_attempt,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def analysis_to_public_response(project: Project) -> dict:
    output_language = normalize_output_language(
        getattr(project, "output_language", "fr")
    )

    public_context = build_public_project_context(project)

    sanitized_analysis_data = sanitize_analysis_data_for_public(
        project.analysis_data,
        project_context=public_context,
    )

    sanitized_analysis_data = restore_public_competitive_analysis(
        raw_analysis_data=project.analysis_data,
        sanitized_analysis_data=sanitized_analysis_data,
    )

    log_public_source_integrity(
        project_id=project.id,
        raw_analysis_data=project.analysis_data,
        public_analysis_data=sanitized_analysis_data,
    )

    return {
        "project_id": project.id,
        "analysis_status": project.analysis_status,
        "analysis_step": public_analysis_step(
            project.analysis_step,
            output_language,
        ),
        "analysis_progress": project.analysis_progress,
        "analysis_data": sanitized_analysis_data,
        "analysis_error": public_analysis_error(
            project.analysis_error,
            output_language,
        ),
        "analysis_started_at": project.analysis_started_at,
        "analysis_completed_at": project.analysis_completed_at,
        "analysis_run_id": project.analysis_run_id,
        "analysis_heartbeat_at": project.analysis_heartbeat_at,
        "analysis_attempt": project.analysis_attempt,
    }


def extract_official_startup_score(
    analysis_data: Optional[dict],
    fallback_score: Optional[float] = None,
) -> Optional[float]:
    """
    Score officiel du projet.

    Priorité :
    1. analysis_data.startup_score.score
    2. analysis_data.startup_score.startup_score
    3. analysis_data.startup_score.overall_score
    4. analysis_data.startup_score.final_score
    5. analysis_data.startup_score.score_out_of_10
    6. analysis_data.startup_score.global_score
    7. fallback_score
    """

    if not isinstance(analysis_data, dict):
        return fallback_score

    startup_score_data = analysis_data.get("startup_score") or {}

    if not isinstance(startup_score_data, dict):
        return fallback_score

    score_keys = [
        "potential_score",
        "score",
        "startup_score",
        "overall_score",
        "final_score",
        "score_out_of_10",
        "global_score",
    ]

    for key in score_keys:
        value = startup_score_data.get(key)

        try:
            if value is None:
                continue

            score = float(value)

            if 0 <= score <= 10:
                return score

        except Exception:
            continue

    return fallback_score


async def get_project_or_404(
    project_id: int,
    db: AsyncSession,
    current_user: User,
) -> Project:
    query = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )

    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable ou accès interdit.",
        )

    return project


async def set_analysis_progress(
    db: AsyncSession,
    project: Project,
    step: str,
    progress: int,
    status_value: Optional[str] = None,
) -> None:
    project.analysis_step = step
    project.analysis_progress = max(0, min(100, int(progress)))

    if status_value is not None:
        project.analysis_status = status_value

    await db.commit()


def _build_readiness_analysis_data(
    idea_readiness: dict,
) -> dict:
    """
    Construit le paquet de persistance canonique du préflight.

    Ces clés sont enregistrées avant tout agent coûteux afin que le frontend
    puisse afficher immédiatement le score, les champs ambigus et les
    questions de clarification.
    """
    readiness = dict(idea_readiness or {})
    ready_for_agents = bool(readiness.get("ready_for_agents", False))

    return {
        "idea_readiness": readiness,
        "context_extraction_quality": {
            "score": readiness.get("score", 0),
            "status": readiness.get("status"),
            "missing_fields": list(readiness.get("missing_fields") or []),
            "ambiguous_fields": list(readiness.get("ambiguous_fields") or []),
            "blockers": list(readiness.get("blockers") or []),
            "ready_for_agents": ready_for_agents,
        },
        "project_context_packet": dict(
            readiness.get("project_context_packet") or {}
        ),
        "context_confidence": dict(
            readiness.get("context_confidence") or {}
        ),
        "legacy_project_context": dict(
            readiness.get("legacy_project_context") or {}
        ),
        "needs_clarification": not ready_for_agents,
        "partial_completion": False,
    }


def _analysis_requires_clarification(
    state_or_result: Optional[dict],
) -> bool:
    """
    Détecte un arrêt de clarification provenant du préflight ou du graphe.
    """
    payload = dict(state_or_result or {})
    analysis_data = payload.get("analysis_data") or {}

    if payload.get("current_step") == "needs_clarification":
        return True

    if analysis_data.get("needs_clarification") is True:
        return True

    readiness = analysis_data.get("idea_readiness") or {}

    return readiness.get("ready_for_agents") is False


def _clarification_step(output_language: str) -> str:
    language = normalize_output_language(output_language)

    if language == "en":
        return "Project clarification required"

    if language == "ar":
        return "يلزم توضيح فكرة المشروع"

    return "Clarification du projet requise"


async def _persist_needs_clarification(
    *,
    db: AsyncSession,
    project: Project,
    analysis_data: Optional[dict],
    output_language: str,
) -> None:
    """
    Persiste un état terminal non échoué et non terminé.

    Aucun score marché, débat ou résultat d'agent n'est fabriqué lorsque le
    contexte est insuffisant.
    """
    stored_data = dict(analysis_data or {})
    stored_data["needs_clarification"] = True
    stored_data["partial_completion"] = False

    project.analysis_data = stored_data
    project.analysis_status = "needs_clarification"
    project.analysis_step = _clarification_step(output_language)
    project.analysis_progress = 10
    project.analysis_error = None
    project.analysis_completed_at = None
    project.analysis_heartbeat_at = utc_now()

    await db.commit()


@analysis_run_guard.limit
async def run_project_analysis_background(project_id: int, run_id: str) -> None:
    logger.info(
        "[ProjectAnalysis] Démarrage background task | project_id=%s",
        project_id,
    )

    async with AsyncSessionLocal() as db:
        try:
            project = await db.get(Project, project_id)

            if project is None:
                logger.error(
                    "[ProjectAnalysis] Projet introuvable | project_id=%s",
                    project_id,
                )
                return
            if project.analysis_run_id != run_id:
                logger.warning("[ProjectAnalysis] stale run ignored | project_id=%s | run_id=%s", project_id, run_id)
                return

            project.analysis_status = "running"
            project.analysis_step = "Préparation de l’analyse"
            project.analysis_progress = 5
            project.analysis_error = None
            project.analysis_started_at = project.analysis_started_at or utc_now()
            project.analysis_completed_at = None

            await db.commit()

            await set_analysis_progress(
                db=db,
                project=project,
                step="Préparation des données projet",
                progress=15,
                status_value="running",
            )

            market_region = normalize_market_region(project.market_region)
            output_language = normalize_output_language(
                getattr(project, "output_language", "fr")
            )

            agent_input = {
                "title": project.title or "",
                "description": project.description or "",
                "industry": project.industry or "",
                "region": market_region,
                "market_region": market_region,
                "target_region": market_region,
                "output_language": output_language,
            }

            # ------------------------------------------------------------
            # Préflight canonique obligatoire
            # ------------------------------------------------------------
            # Aucun agent, aucune recherche web et aucun Debate Room ne doit
            # démarrer avant cette décision.
            idea_readiness = idea_readiness_checker.evaluate(
                title=agent_input["title"],
                description=agent_input["description"],
                industry=agent_input["industry"],
                target_region=market_region,
                output_language=output_language,
                analysis_data={},
            )

            readiness_analysis_data = _build_readiness_analysis_data(
                idea_readiness
            )

            if not idea_readiness.get("ready_for_agents", False):
                await _persist_needs_clarification(
                    db=db,
                    project=project,
                    analysis_data=readiness_analysis_data,
                    output_language=output_language,
                )

                logger.info(
                    "[ProjectAnalysis] Clarification requise avant agents | "
                    "project_id=%s | score=%s | missing=%s | ambiguous=%s",
                    project_id,
                    idea_readiness.get("score", 0),
                    idea_readiness.get("missing_fields", []),
                    idea_readiness.get("ambiguous_fields", []),
                )
                return

            project_context = project_context_builder.build(
                title=agent_input["title"],
                description=agent_input["description"],
                industry=agent_input["industry"],
                market_region=market_region,
                output_language=output_language,
                analysis_data=readiness_analysis_data,
            )

            agent_input.update(
                {
                    "project_context": project_context,
                    "analysis_data": readiness_analysis_data,
                    "idea_readiness": idea_readiness,
                    "project_context_packet": readiness_analysis_data.get(
                        "project_context_packet", {}
                    ),
                    "context_confidence": readiness_analysis_data.get(
                        "context_confidence", {}
                    ),
                    "legacy_project_context": readiness_analysis_data.get(
                        "legacy_project_context", {}
                    ),
                }
            )

            logger.info(
                "[ProjectAnalysis] Agent input préparé | project_id=%s | industry=%s | region=%s | lang=%s",
                project_id,
                agent_input["industry"],
                agent_input["region"],
                output_language,
            )

            await set_analysis_progress(
                db=db,
                project=project,
                step="Sprint 2 - RAG global/local et analyse initiale",
                progress=25,
                status_value="running",
            )

            business_agent = AIBusinessAnalystAgent()
            base_analysis_result = await business_agent.run(agent_input)

            project = await db.get(Project, project_id)

            if project is None:
                logger.error(
                    "[ProjectAnalysis] Projet supprimé pendant Sprint 2 | project_id=%s",
                    project_id,
                )
                return

            if project.analysis_run_id != run_id:
                logger.warning(
                    "[ProjectAnalysis] stale Sprint 2 result ignored | "
                    "project_id=%s | run_id=%s",
                    project_id,
                    run_id,
                )
                return

            base_analysis = dict(base_analysis_result or {})

            # Les données canoniques du préflight gagnent toujours sur une
            # éventuelle clé homonyme retournée par un ancien agent.
            base_analysis.update(readiness_analysis_data)

            project_context = project_context_builder.build(
                title=agent_input["title"],
                description=agent_input["description"],
                industry=agent_input["industry"],
                market_region=market_region,
                output_language=output_language,
                analysis_data=base_analysis,
            )

            base_analysis["project_context_meta"] = {
                "domain_label": project_context.get("domain_label"),
                "output_language": output_language,
                "anchor_terms": project_context.get("anchor_terms", [])[:30],
            }

            project.analysis_data = base_analysis
            project.analysis_status = "running"
            project.analysis_step = "Sprint 2 terminé - préparation Startup Evaluator"
            project.analysis_progress = 35
            project.analysis_error = None

            innovation_score = base_analysis.get("innovation_score")

            if isinstance(innovation_score, (int, float)):
                project.startup_score = float(innovation_score)

            await db.commit()

            async def save_startup_evaluator_step(state: dict) -> None:
                current_project = await db.get(Project, project_id)

                if current_project is None:
                    logger.error(
                        "[ProjectAnalysis] Projet introuvable pendant save step | project_id=%s",
                        project_id,
                    )
                    return
                if current_project.analysis_run_id != run_id:
                    logger.warning("[ProjectAnalysis] stale evaluator callback ignored | project_id=%s | run_id=%s", project_id, run_id)
                    return

                graph_progress = int(state.get("progress") or 0)
                mapped_progress = 35 + int(graph_progress * 0.60)
                mapped_progress = max(35, min(95, mapped_progress))

                current_step = state.get("current_step") or "startup_evaluator"
                current_error = state.get("error")
                current_analysis_data = state.get("analysis_data") or {}

                if _analysis_requires_clarification(state):
                    await _persist_needs_clarification(
                        db=db,
                        project=current_project,
                        analysis_data=current_analysis_data,
                        output_language=output_language,
                    )
                    return

                current_project.analysis_data = current_analysis_data
                current_project.analysis_status = "running"
                current_project.analysis_heartbeat_at = utc_now()
                current_project.analysis_step = f"Sprint 3 - {current_step}"
                current_project.analysis_progress = mapped_progress

                official_step_score = extract_official_startup_score(
                    current_analysis_data,
                    fallback_score=current_project.startup_score,
                )

                if isinstance(official_step_score, (int, float)):
                    current_project.startup_score = float(official_step_score)

                if current_error:
                    current_project.analysis_error = str(current_error)[:2000]

                competitive_payload = (
                    current_analysis_data.get("competitive_analysis")
                    or {}
                )
                forgecrawler_payload = (
                    current_analysis_data.get("forgecrawler")
                    or {}
                )

                logger.info(
                    "[SourcePipeline][Persistence] project_id=%s | "
                    "step=%s | competitive_sources=%s | "
                    "forgecrawler_sources=%s",
                    project_id,
                    current_step,
                    len(competitive_payload.get("sources") or []),
                    len(forgecrawler_payload.get("sources") or []),
                )

                await db.commit()

            await set_analysis_progress(
                db=db,
                project=project,
                step="Sprint 3 - lancement Startup Evaluator",
                progress=40,
                status_value="running",
            )

            graph = StartupEvaluatorGraph()

            graph_result = await graph.run(
                {
                    "project_id": project_id,
                    "title": agent_input["title"],
                    "description": agent_input["description"],
                    "industry": agent_input["industry"],
                    "region": market_region,
                    "market_region": market_region,
                    "target_region": market_region,
                    "output_language": output_language,
                    "project_context": project_context,
                    "analysis_data": base_analysis,
                    "idea_readiness": idea_readiness,
                    "project_context_packet": base_analysis.get(
                        "project_context_packet", {}
                    ),
                    "context_confidence": base_analysis.get(
                        "context_confidence", {}
                    ),
                    "legacy_project_context": base_analysis.get(
                        "legacy_project_context", {}
                    ),
                },
                on_step_complete=save_startup_evaluator_step,
            )

            project = await db.get(Project, project_id)

            if project is None:
                logger.error(
                    "[ProjectAnalysis] Projet supprimé pendant Sprint 3 | project_id=%s",
                    project_id,
                )
                return

            if project.analysis_run_id != run_id:
                logger.warning(
                    "[ProjectAnalysis] stale Sprint 3 result ignored | "
                    "project_id=%s | run_id=%s",
                    project_id,
                    run_id,
                )
                return

            if _analysis_requires_clarification(graph_result):
                await _persist_needs_clarification(
                    db=db,
                    project=project,
                    analysis_data=graph_result.get("analysis_data") or {},
                    output_language=output_language,
                )
                return

            final_analysis_data = graph_result.get("analysis_data") or {}
            final_analysis_data = evidence_ledger.sanitize_public_claims(
                final_analysis_data
            )

            official_score = extract_official_startup_score(
                final_analysis_data,
                fallback_score=(
                    float(innovation_score)
                    if isinstance(innovation_score, (int, float))
                    else project.startup_score
                ),
            )

            if isinstance(official_score, (int, float)):
                project.startup_score = float(official_score)

            project.analysis_data = final_analysis_data
            project.analysis_status = "running"
            project.analysis_step = "Sprint 3 terminé - lancement Debate Room"
            project.analysis_progress = 95
            project.analysis_error = None

            await db.commit()

            debate_failed = False

            async def save_debate_room_step(state: dict) -> None:
                current_project = await db.get(Project, project_id)

                if current_project is None:
                    logger.error(
                        "[ProjectAnalysis] Projet introuvable pendant Debate Room | project_id=%s",
                        project_id,
                    )
                    return
                if current_project.analysis_run_id != run_id:
                    logger.warning(
                        "[ProjectAnalysis] stale debate callback ignored | project_id=%s | run_id=%s",
                        project_id,
                        run_id,
                    )
                    return

                debate_progress = int(state.get("progress") or 0)
                mapped_progress = 95 + int(debate_progress * 0.04)
                mapped_progress = max(95, min(99, mapped_progress))

                current_step = state.get("current_step") or "debate_room"
                current_error = state.get("error")

                existing_analysis_data = current_project.analysis_data or {}
                updated_analysis_data = dict(existing_analysis_data)

                updated_analysis_data["debate_room"] = {
                    "format": state.get(
                        "format", "debate_room_pro_v9_investment_committee"
                    ),
                    "title": state.get("title"),
                    "status": state.get("status", "running"),
                    "committee": state.get("committee", []),
                    "rounds": state.get("rounds", []),
                    "judge": state.get("judge", {}),
                    "meeting_preparation": state.get(
                        "meeting_preparation", {}
                    ),
                    "meta": {
                        "completed_steps": state.get("completed_steps", []),
                        "failed_steps": state.get("failed_steps", []),
                        "progress": state.get("progress", 0),
                        "current_step": state.get("current_step"),
                        "completed": state.get("completed", False),
                        "error": state.get("error"),
                        "output_language": output_language,
                        "context_locked": True,
                    },
                }

                current_project.analysis_data = updated_analysis_data
                current_project.analysis_status = "running"
                current_project.analysis_heartbeat_at = utc_now()
                current_project.analysis_step = f"Debate Room - {current_step}"
                current_project.analysis_progress = mapped_progress

                official_step_score = extract_official_startup_score(
                    updated_analysis_data,
                    fallback_score=current_project.startup_score,
                )

                if isinstance(official_step_score, (int, float)):
                    current_project.startup_score = float(official_step_score)

                if current_error:
                    current_project.analysis_error = str(current_error)[:2000]

                await db.commit()

            await set_analysis_progress(
                db=db,
                project=project,
                step="Debate Room - lancement du débat stratégique",
                progress=95,
                status_value="running",
            )

            try:
                debate_graph = DebateRoomGraph(
                    step_callback=save_debate_room_step,
                )

                debate_result = await debate_graph.run(
                    project_id=project_id,
                    title=agent_input["title"],
                    description=agent_input["description"],
                    industry=agent_input["industry"],
                    region=market_region,
                    output_language=output_language,
                    project_context=project_context,
                    analysis_data=final_analysis_data,
                    max_rounds=5,
                )

                debate_room_data = debate_result.get("debate_room") or {}

                final_analysis_data = dict(final_analysis_data)
                final_analysis_data["debate_room"] = debate_room_data
                # Reapply the canonical publication gate after the debate so
                # every public section reads the same confidence contract.
                final_analysis_data = evidence_ledger.sanitize_public_claims(
                    final_analysis_data
                )

            except Exception as debate_exc:
                debate_failed = True
                logger.exception(
                    "[ProjectAnalysis] Debate Room échouée | project_id=%s",
                    project_id,
                )

                safe_judge = {
                    "role": "judge",
                    "verdict": (
                        "PREUVES_INSUFFISANTES"
                        if output_language == "fr"
                        else "INSUFFICIENT_EVIDENCE"
                    ),
                    "verdict_code": "insufficient_evidence",
                    "argument_strength_score": 0,
                    "risk_level": "medium",
                    "critical_risks": [
                        (
                            "Le débat stratégique n'a pas pu être généré correctement."
                            if output_language == "fr"
                            else "The strategic debate could not be generated correctly."
                        )
                    ],
                    "validated_opportunities": [],
                    "improved_idea": (
                        "Revoir le projet avec plus de données terrain."
                        if output_language == "fr"
                        else "Review the project with more field evidence."
                    ),
                    "final_recommendation": (
                        "Continuer l'analyse principale, mais relancer le débat stratégique plus tard."
                        if output_language == "fr"
                        else "Continue using the main analysis, but rerun the strategic debate later."
                    ),
                    "next_actions": [
                        (
                            "Vérifier les données disponibles."
                            if output_language == "fr"
                            else "Check the available data."
                        ),
                        (
                            "Relancer l'analyse stratégique."
                            if output_language == "fr"
                            else "Rerun the strategic analysis."
                        ),
                    ],
                }

                final_analysis_data = dict(final_analysis_data)
                final_analysis_data["debate_room"] = {
                    "format": "debate_room_pro_v9_fallback",
                    "status": "completed_with_fallback",
                    "committee": [],
                    "rounds": [],
                    "judge": safe_judge,
                    "meeting_preparation": {},
                    "meta": {
                        "completed_steps": [],
                        "failed_steps": ["debate_room"],
                        "progress": 0,
                        "current_step": "debate_room_failed",
                        "completed": False,
                        "error": str(debate_exc)[:1000],
                        "output_language": output_language,
                        "context_locked": True,
                    },
                }
                final_analysis_data = evidence_ledger.sanitize_public_claims(
                    final_analysis_data
                )

            project = await db.get(Project, project_id)

            if project is None:
                logger.error(
                    "[ProjectAnalysis] Projet supprimé avant finalisation | project_id=%s",
                    project_id,
                )
                return
            if project.analysis_run_id != run_id:
                logger.warning(
                    "[ProjectAnalysis] stale final write ignored | project_id=%s | run_id=%s",
                    project_id,
                    run_id,
                )
                return

            startup_meta = final_analysis_data.get("startup_evaluator_meta", {})
            startup_failed_steps = startup_meta.get("failed_steps", []) or []

            debate_room_data = final_analysis_data.get("debate_room", {}) or {}
            debate_meta = debate_room_data.get("meta", {}) or {}

            debate_completed = bool(debate_meta.get("completed", False))
            debate_failed_steps = debate_meta.get("failed_steps", []) or []

            partial_completion = bool(final_analysis_data.get("partial_completion"))

            all_failed_steps = list(startup_failed_steps)

            if debate_failed or debate_failed_steps or not debate_completed:
                if "debate_room" not in all_failed_steps:
                    all_failed_steps.append("debate_room")

            has_partial_result = bool(partial_completion or all_failed_steps)

            official_score = extract_official_startup_score(
                final_analysis_data,
                fallback_score=project.startup_score,
            )

            if isinstance(official_score, (int, float)):
                project.startup_score = float(official_score)

            project.analysis_data = final_analysis_data
            project.analysis_status = "completed"
            project.analysis_step = (
                "Analyse Sprint 3 + Debate Room terminée partiellement"
                if has_partial_result
                else "Analyse Sprint 3 + Debate Room terminée"
            )
            project.analysis_progress = 100
            project.analysis_completed_at = utc_now()
            project.analysis_heartbeat_at = utc_now()

            if has_partial_result:
                project.analysis_error = (
                    "Analyse partiellement terminée. "
                    f"Étapes échouées : {all_failed_steps}"
                )[:2000]
            else:
                project.analysis_error = None

            await db.commit()

            logger.info(
                "[ProjectAnalysis] Analyse complète terminée | project_id=%s | score=%s | partial=%s",
                project_id,
                project.startup_score,
                has_partial_result,
            )

        except Exception as exc:
            await db.rollback()

            logger.exception(
                "[ProjectAnalysis] Analyse échouée | project_id=%s",
                project_id,
            )

            project = await db.get(Project, project_id)

            if project is not None:
                project.analysis_status = "failed"
                project.analysis_step = "Erreur pendant l’analyse"
                project.analysis_progress = 100
                project.analysis_error = str(exc)[:2000]
                project.analysis_completed_at = utc_now()

                await db.commit()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_project = Project(
        title=project_in.title,
        description=project_in.description,
        industry=project_in.industry,
        market_region=normalize_market_region(project_in.market_region),
        output_language=normalize_output_language(project_in.output_language),
        user_id=current_user.id,
    )

    db.add(new_project)

    await db.commit()
    await db.refresh(new_project)

    return project_to_public_response(new_project)


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )

    result = await db.execute(query)
    projects = result.scalars().all()

    return [project_to_public_response(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_or_404(project_id, db, current_user)

    return project_to_public_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_or_404(project_id, db, current_user)

    update_data = project_in.model_dump(exclude_unset=True)

    if "market_region" in update_data:
        update_data["market_region"] = normalize_market_region(
            update_data["market_region"]
        )

    if "output_language" in update_data:
        update_data["output_language"] = normalize_output_language(
            update_data["output_language"]
        )

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return project_to_public_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_or_404(project_id, db, current_user)

    await db.delete(project)
    await db.commit()

    return None


@router.post(
    "/{project_id}/analyze/start",
    response_model=ProjectAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_project_analysis(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_or_404(project_id, db, current_user)

    if project.analysis_status in {"queued", "running"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une analyse est déjà en cours pour ce projet.",
        )

    run_id = analysis_run_guard.new_run_id()
    project.analysis_run_id = run_id
    project.analysis_attempt = int(project.analysis_attempt or 0) + 1
    project.analysis_heartbeat_at = utc_now()
    project.analysis_status = "queued"
    project.analysis_step = "Analyse en attente d’un créneau"
    project.analysis_progress = 2
    project.analysis_data = None
    project.analysis_error = None
    project.analysis_started_at = utc_now()
    project.analysis_completed_at = None

    await db.commit()
    await db.refresh(project)

    background_tasks.add_task(
        run_project_analysis_background,
        project.id,
        run_id,
    )

    return analysis_to_public_response(project)


@router.get(
    "/{project_id}/analysis",
    response_model=ProjectAnalysisResponse,
)
async def get_project_analysis(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_or_404(project_id, db, current_user)

    return analysis_to_public_response(project)