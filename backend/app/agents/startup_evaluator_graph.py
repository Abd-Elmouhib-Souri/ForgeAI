# ============================================================
# backend/app/agents/startup_evaluator_graph.py
# ============================================================
#
# StartupEvaluatorGraph V7.0 — Professional Agent Pipeline
#
# Corrections :
# - garde Lot Backend 2A : Idea Readiness Check ;
# - garde Lot Backend 2B : Project Intelligence Layer + Query Planner ;
# - remplace le sanitizer graph trop agressif ;
# - supprime les faux positifs "Contamination détectée" sur financial_estimation ;
# - garde une vraie détection des anciennes contaminations de démo ;
# - rend la détection context-aware ;
# - prépare les tests futurs, y compris HealthTech ;
# - ne casse pas le pipeline ;
# - ne touche pas encore au frontend.
# ============================================================

import logging
import re
import unicodedata
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urlparse

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from langgraph.graph import END, StateGraph

from app.agents.bmc_agent import BMCAgent
from app.agents.competitive_analysis_agent import CompetitiveAnalysisAgent
from app.agents.fact_checker_agent import FactCheckerAgent
from app.agents.financial_estimation_agent import FinancialEstimationAgent
from app.agents.market_study_agent import MarketStudyAgent
from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.agents.startup_evaluator_state import StartupEvaluatorState
from app.agents.startup_score_agent import StartupScoreAgent
from app.agents.swot_agent import SWOTAgent
from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.idea_readiness_checker import idea_readiness_checker
from app.services.evidence_ledger import evidence_ledger
from app.services.project_context_builder import project_context_builder
from app.services.project_intelligence_layer import project_intelligence_layer

logger = logging.getLogger(__name__)

StepCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class StartupEvaluatorGraph:
    def __init__(self):
        self.market_study_agent = MarketStudyAgent()
        self.swot_agent = SWOTAgent()
        self.bmc_agent = BMCAgent()
        self.competitive_analysis_agent = CompetitiveAnalysisAgent()
        self.financial_estimation_agent = FinancialEstimationAgent()
        self.startup_score_agent = StartupScoreAgent()
        self.persona_builder_agent = PersonaBuilderAgent()
        self.fact_checker_agent = FactCheckerAgent()

        self.on_step_complete: Optional[StepCallback] = None
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(StartupEvaluatorState)

        workflow.add_node("market_study", self.market_study_node)
        workflow.add_node("swot", self.swot_node)
        workflow.add_node("bmc", self.bmc_node)
        workflow.add_node("competitive_analysis", self.competitive_analysis_node)
        workflow.add_node("financial_estimation", self.financial_estimation_node)
        workflow.add_node("startup_score", self.startup_score_node)
        workflow.add_node("persona_builder", self.persona_builder_node)
        workflow.add_node("fact_checker", self.fact_checker_node)

        # Evidence-first pipeline: sources are collected before the market study,
        # and the Startup Score is computed only after Fact Checker.
        workflow.set_entry_point("competitive_analysis")

        workflow.add_edge("competitive_analysis", "market_study")
        workflow.add_edge("market_study", "swot")
        workflow.add_edge("swot", "bmc")
        workflow.add_edge("bmc", "financial_estimation")
        workflow.add_edge("financial_estimation", "persona_builder")
        workflow.add_edge("persona_builder", "fact_checker")
        workflow.add_edge("fact_checker", "startup_score")
        workflow.add_edge("startup_score", END)

        return workflow.compile()

    async def run(
        self,
        input_data: Dict[str, Any],
        on_step_complete: Optional[StepCallback] = None,
    ) -> Dict[str, Any]:
        """
        Exécute le pipeline avec un gate de contexte obligatoire.

        Ordre garanti :

        1. construction du contexte de base ;
        2. extraction du ProjectContextPacketV3 ;
        3. Context Confidence Gate ;
        4. arrêt immédiat si clarification nécessaire ;
        5. Project Intelligence Layer ;
        6. agents, recherches et scoring.

        Aucun flag d'entrée ne peut désactiver le gate.
        """
        self.on_step_complete = on_step_complete

        try:
            output_language = normalize_output_language(
                input_data.get("output_language", "fr")
            )

            analysis_data = dict(
                input_data.get("analysis_data") or {}
            )

            title = str(
                input_data.get("title") or ""
            ).strip()

            description = str(
                input_data.get("description") or ""
            ).strip()

            industry = str(
                input_data.get("industry") or ""
            ).strip()

            target_region = str(
                input_data.get("market_region")
                or input_data.get("region")
                or input_data.get("target_region")
                or ""
            ).strip()

            supplied_project_context = (
                input_data.get("project_context")
            )

            if isinstance(
                supplied_project_context,
                dict,
            ):
                base_project_context = dict(
                    supplied_project_context
                )
            else:
                base_project_context = (
                    project_context_builder.build(
                        title=title,
                        description=description,
                        industry=industry,
                        market_region=target_region,
                        output_language=output_language,
                        analysis_data=analysis_data,
                    )
                )

            idea_readiness = (
                idea_readiness_checker.evaluate(
                    title=title,
                    description=description,
                    industry=industry,
                    target_region=target_region,
                    output_language=output_language,
                    project_context=(
                        base_project_context
                    ),
                    analysis_data=analysis_data,
                )
            )

            analysis_data = (
                self._store_canonical_readiness(
                    analysis_data=analysis_data,
                    idea_readiness=idea_readiness,
                )
            )

            pre_intelligence_context = (
                self._build_pre_intelligence_context(
                    base_project_context=(
                        base_project_context
                    ),
                    idea_readiness=idea_readiness,
                )
            )

            readiness_state: StartupEvaluatorState = {
                "project_id": int(
                    input_data.get(
                        "project_id",
                        0,
                    )
                    or 0
                ),
                "title": title,
                "description": description,
                "industry": industry,
                "region": target_region,
                "output_language": output_language,
                "project_context": (
                    pre_intelligence_context
                ),
                "analysis_data": analysis_data,
                "completed_steps": [
                    "idea_readiness_check",
                ],
                "failed_steps": [],
                "current_step": (
                    "idea_readiness_check"
                ),
                "progress": 5,
                "error": None,
                "partial_completion": False,
            }

            if not idea_readiness.get(
                "ready_for_agents",
                False,
            ):
                logger.info(
                    "[StartupEvaluatorGraph] "
                    "Analyse bloquée par le Context Gate "
                    "| status=%s | score=%s | blockers=%s",
                    idea_readiness.get("status"),
                    idea_readiness.get("score"),
                    idea_readiness.get(
                        "blockers",
                        [],
                    ),
                )

                return await (
                    self
                    ._return_needs_clarification_state(
                        readiness_state
                    )
                )

            project_intelligence = (
                project_intelligence_layer.build(
                    title=title,
                    description=description,
                    industry=industry,
                    target_region=target_region,
                    output_language=output_language,
                    project_context=(
                        pre_intelligence_context
                    ),
                    idea_readiness=idea_readiness,
                    analysis_data=analysis_data,
                )
            )

            merged_project_context = (
                project_intelligence_layer
                .merge_into_project_context(
                    base_project_context=(
                        pre_intelligence_context
                    ),
                    intelligence=(
                        project_intelligence
                    ),
                )
            )

            project_context = (
                self._lock_canonical_context(
                    merged_project_context=(
                        merged_project_context
                    ),
                    idea_readiness=idea_readiness,
                )
            )

            agent_context_packet = (
                self._build_agent_context_packet(
                    project_intelligence=(
                        project_intelligence
                    ),
                    idea_readiness=(
                        idea_readiness
                    ),
                )
            )

            analysis_data[
                "project_intelligence"
            ] = project_intelligence

            analysis_data[
                "structured_project_context"
            ] = project_intelligence.get(
                "structured_project_context",
                {},
            )

            analysis_data[
                "query_planner"
            ] = project_intelligence.get(
                "query_planner",
                {},
            )

            analysis_data[
                "agent_context_packet"
            ] = agent_context_packet

            analysis_data[
                "needs_clarification"
            ] = False

            analysis_data[
                "project_context_meta"
            ] = {
                "domain_label": (
                    project_context.get(
                        "domain_label"
                    )
                ),
                "output_language": (
                    output_language
                ),
                "anchor_terms": (
                    project_context.get(
                        "anchor_terms",
                        [],
                    )[:30]
                ),
                "strong_keywords": (
                    project_context.get(
                        "strong_keywords",
                        [],
                    )[:30]
                ),
                "must_match_terms": (
                    project_context.get(
                        "must_match_terms",
                        [],
                    )[:20]
                ),
                "context_locked": True,
                "canonical_schema_version": (
                    idea_readiness.get(
                        "schema_version"
                    )
                ),
                "readiness_enforced": True,
                "idea_readiness_status": (
                    idea_readiness.get(
                        "status"
                    )
                ),
                "idea_readiness_score": (
                    idea_readiness.get(
                        "score",
                        0,
                    )
                ),
                "ready_for_agents": True,
                "project_intelligence_status": (
                    project_intelligence.get(
                        "status"
                    )
                ),
                "context_confidence": (
                    (
                        idea_readiness.get(
                            "context_confidence"
                        )
                        or {}
                    ).get(
                        "score",
                        idea_readiness.get(
                            "score",
                            0,
                        ),
                    )
                ),
            }

            initial_state: StartupEvaluatorState = {
                **readiness_state,
                "project_context": (
                    project_context
                ),
                "analysis_data": analysis_data,
                "completed_steps": [
                    "idea_readiness_check",
                    "project_intelligence_layer",
                ],
                "current_step": (
                    "project_intelligence_layer"
                ),
                "progress": 7,
            }

            final_state = await self.app.ainvoke(
                initial_state
            )

            final_analysis_data = dict(
                final_state.get(
                    "analysis_data"
                )
                or {}
            )

            failed_steps = list(
                final_state.get(
                    "failed_steps",
                    [],
                )
                or []
            )

            completed_steps = list(
                final_state.get(
                    "completed_steps",
                    [],
                )
                or []
            )

            partial_completion = bool(
                final_state.get(
                    "partial_completion",
                    False,
                )
                or failed_steps
            )

            final_analysis_data[
                "partial_completion"
            ] = partial_completion

            final_analysis_data[
                "needs_clarification"
            ] = False

            final_analysis_data[
                "startup_evaluator_meta"
            ] = {
                **(
                    final_analysis_data.get(
                        "startup_evaluator_meta"
                    )
                    or {}
                ),
                "completed_steps": (
                    completed_steps
                ),
                "failed_steps": failed_steps,
                "progress": final_state.get(
                    "progress",
                    0,
                ),
                "current_step": (
                    final_state.get(
                        "current_step",
                        "completed",
                    )
                ),
                "error": final_state.get(
                    "error"
                ),
                "output_language": (
                    output_language
                ),
                "context_locked": True,
                "canonical_schema_version": (
                    idea_readiness.get(
                        "schema_version"
                    )
                ),
                "readiness_enforced": True,
                "pipeline_blocked_before_agents": (
                    False
                ),
                "heavy_agents_started": True,
                "idea_readiness_status": (
                    idea_readiness.get(
                        "status"
                    )
                ),
                "idea_readiness_score": (
                    idea_readiness.get(
                        "score",
                        0,
                    )
                ),
                "ready_for_agents": True,
                "project_intelligence_status": (
                    project_intelligence.get(
                        "status"
                    )
                ),
                "context_confidence": (
                    (
                        idea_readiness.get(
                            "context_confidence"
                        )
                        or {}
                    ).get(
                        "score",
                        idea_readiness.get(
                            "score",
                            0,
                        ),
                    )
                ),
            }

            final_state[
                "analysis_data"
            ] = final_analysis_data

            final_state[
                "partial_completion"
            ] = partial_completion

            return dict(
                final_state
            )

        finally:
            self.on_step_complete = None

    def _store_canonical_readiness(
        self,
        *,
        analysis_data: Dict[str, Any],
        idea_readiness: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Persiste la même vérité canonique pour tout le run.
        """
        stored = dict(
            analysis_data
        )

        project_context_packet = dict(
            idea_readiness.get(
                "project_context_packet"
            )
            or {}
        )

        context_confidence = dict(
            idea_readiness.get(
                "context_confidence"
            )
            or {}
        )

        legacy_project_context = dict(
            idea_readiness.get(
                "legacy_project_context"
            )
            or {}
        )

        stored[
            "idea_readiness"
        ] = idea_readiness

        stored[
            "project_context_packet"
        ] = project_context_packet

        stored[
            "context_confidence"
        ] = context_confidence

        stored[
            "legacy_project_context"
        ] = legacy_project_context

        stored[
            "context_extraction_quality"
        ] = {
            "schema_version": (
                idea_readiness.get(
                    "schema_version"
                )
            ),
            "status": (
                idea_readiness.get(
                    "status"
                )
            ),
            "score": (
                idea_readiness.get(
                    "score",
                    0,
                )
            ),
            "missing_fields": list(
                idea_readiness.get(
                    "missing_fields",
                    [],
                )
                or []
            ),
            "ambiguous_fields": list(
                idea_readiness.get(
                    "ambiguous_fields",
                    [],
                )
                or []
            ),
            "blockers": list(
                idea_readiness.get(
                    "blockers",
                    [],
                )
                or []
            ),
            "ready_for_agents": bool(
                idea_readiness.get(
                    "ready_for_agents",
                    False,
                )
            ),
            "readiness_enforced": True,
        }

        return stored

    def _build_pre_intelligence_context(
        self,
        *,
        base_project_context: Dict[str, Any],
        idea_readiness: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Construit le contexte utilisé par la Project Intelligence Layer.

        Le contexte canonique V3 écrase les anciennes inférences pour
        les champs métier structurants.
        """
        context = dict(
            base_project_context or {}
        )

        legacy_context = dict(
            idea_readiness.get(
                "legacy_project_context"
            )
            or {}
        )

        context.update(
            legacy_context
        )

        context[
            "project_context_packet"
        ] = dict(
            idea_readiness.get(
                "project_context_packet"
            )
            or {}
        )

        context[
            "context_confidence"
        ] = dict(
            idea_readiness.get(
                "context_confidence"
            )
            or {}
        )

        context[
            "idea_readiness"
        ] = {
            "schema_version": (
                idea_readiness.get(
                    "schema_version"
                )
            ),
            "status": (
                idea_readiness.get(
                    "status"
                )
            ),
            "score": (
                idea_readiness.get(
                    "score",
                    0,
                )
            ),
            "ready_for_agents": bool(
                idea_readiness.get(
                    "ready_for_agents",
                    False,
                )
            ),
            "missing_fields": list(
                idea_readiness.get(
                    "missing_fields",
                    [],
                )
                or []
            ),
            "ambiguous_fields": list(
                idea_readiness.get(
                    "ambiguous_fields",
                    [],
                )
                or []
            ),
            "blockers": list(
                idea_readiness.get(
                    "blockers",
                    [],
                )
                or []
            ),
        }

        context[
            "context_locked"
        ] = True

        return context

    def _lock_canonical_context(
        self,
        *,
        merged_project_context: Dict[str, Any],
        idea_readiness: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Réapplique le contexte V3 après la Project Intelligence Layer.

        Cette étape empêche une ancienne inférence de remplacer le nom,
        la région, les acteurs, le workflow, le MVP ou l'archétype
        validés par le gate.
        """
        context = dict(
            merged_project_context or {}
        )

        legacy_context = dict(
            idea_readiness.get(
                "legacy_project_context"
            )
            or {}
        )

        context.update(
            legacy_context
        )

        context[
            "project_context_packet"
        ] = dict(
            idea_readiness.get(
                "project_context_packet"
            )
            or {}
        )

        context[
            "context_confidence"
        ] = dict(
            idea_readiness.get(
                "context_confidence"
            )
            or {}
        )

        context[
            "context_locked"
        ] = True

        context[
            "canonical_schema_version"
        ] = idea_readiness.get(
            "schema_version"
        )

        return context

    def _build_agent_context_packet(
        self,
        *,
        project_intelligence: Dict[str, Any],
        idea_readiness: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Étend le packet historique sans casser ses consommateurs.

        Tous les agents reçoivent désormais le même packet V3 et la
        même décision de confiance.
        """
        agent_packet = dict(
            project_intelligence.get(
                "agent_context_packet"
            )
            or {}
        )

        agent_packet[
            "canonical_schema_version"
        ] = "agent_context_packet_v3"

        agent_packet[
            "project_context_packet"
        ] = dict(
            idea_readiness.get(
                "project_context_packet"
            )
            or {}
        )

        agent_packet[
            "context_confidence"
        ] = dict(
            idea_readiness.get(
                "context_confidence"
            )
            or {}
        )

        agent_packet[
            "legacy_project_context"
        ] = dict(
            idea_readiness.get(
                "legacy_project_context"
            )
            or {}
        )

        agent_packet[
            "idea_readiness"
        ] = {
            "schema_version": (
                idea_readiness.get(
                    "schema_version"
                )
            ),
            "status": (
                idea_readiness.get(
                    "status"
                )
            ),
            "score": (
                idea_readiness.get(
                    "score",
                    0,
                )
            ),
            "ready_for_agents": bool(
                idea_readiness.get(
                    "ready_for_agents",
                    False,
                )
            ),
            "missing_fields": list(
                idea_readiness.get(
                    "missing_fields",
                    [],
                )
                or []
            ),
            "ambiguous_fields": list(
                idea_readiness.get(
                    "ambiguous_fields",
                    [],
                )
                or []
            ),
            "blockers": list(
                idea_readiness.get(
                    "blockers",
                    [],
                )
                or []
            ),
        }

        agent_packet[
            "context_locked"
        ] = True

        return agent_packet

    async def _return_needs_clarification_state(
        self,
        state: StartupEvaluatorState,
    ) -> Dict[str, Any]:
        """
        Retourne avant Project Intelligence, Tavily, ForgeCrawler et LLM.
        """
        analysis_data = dict(
            state.get("analysis_data") or {}
        )

        idea_readiness = dict(
            analysis_data.get(
                "idea_readiness"
            )
            or {}
        )

        analysis_data[
            "needs_clarification"
        ] = True

        analysis_data[
            "partial_completion"
        ] = False

        analysis_data[
            "pipeline_stop"
        ] = {
            "stage": (
                "context_confidence_gate"
            ),
            "reason": (
                "needs_clarification"
            ),
            "external_search_started": False,
            "project_intelligence_started": False,
            "heavy_agents_started": False,
        }

        analysis_data[
            "startup_evaluator_meta"
        ] = {
            "completed_steps": [
                "idea_readiness_check",
            ],
            "failed_steps": [],
            "progress": 5,
            "current_step": (
                "needs_clarification"
            ),
            "error": None,
            "output_language": (
                state.get(
                    "output_language",
                    "fr",
                )
            ),
            "context_locked": True,
            "canonical_schema_version": (
                idea_readiness.get(
                    "schema_version"
                )
            ),
            "readiness_enforced": True,
            "pipeline_blocked_before_agents": (
                True
            ),
            "external_search_started": False,
            "project_intelligence_started": False,
            "heavy_agents_started": False,
            "idea_readiness_status": (
                idea_readiness.get(
                    "status"
                )
            ),
            "idea_readiness_score": (
                idea_readiness.get(
                    "score",
                    0,
                )
            ),
            "ready_for_agents": False,
            "missing_fields": list(
                idea_readiness.get(
                    "missing_fields",
                    [],
                )
                or []
            ),
            "ambiguous_fields": list(
                idea_readiness.get(
                    "ambiguous_fields",
                    [],
                )
                or []
            ),
            "blockers": list(
                idea_readiness.get(
                    "blockers",
                    [],
                )
                or []
            ),
        }

        clarification_state: StartupEvaluatorState = {
            **state,
            "analysis_data": analysis_data,
            "completed_steps": [
                "idea_readiness_check",
            ],
            "failed_steps": [],
            "current_step": (
                "needs_clarification"
            ),
            "progress": 5,
            "error": None,
            "partial_completion": False,
        }

        await self._notify_step_complete(
            clarification_state
        )

        return dict(
            clarification_state
        )

    async def market_study_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        new_state = await self._run_agent_step(
            state=state,
            step_name="market_study",
            result_key="market_study",
            progress=32,
            agent=self.market_study_agent,
        )

        analysis_data = dict(new_state.get("analysis_data") or {})
        market_study = analysis_data.get("market_study")

        if isinstance(market_study, dict):
            enriched_market = self._enrich_market_study_from_evidence(
                market_study=dict(market_study),
                analysis_data=analysis_data,
                output_language=str(new_state.get("output_language") or "fr"),
            )
            analysis_data["market_study"] = enriched_market
            new_state = {**new_state, "analysis_data": analysis_data}

            # _run_agent_step already emitted a callback. Emit the enriched
            # evidence-aware payload as the authoritative market-study state.
            await self._notify_step_complete(new_state)

        return new_state

    async def swot_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        return await self._run_agent_step(
            state=state,
            step_name="swot",
            result_key="swot",
            progress=45,
            agent=self.swot_agent,
        )

    async def bmc_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        return await self._run_agent_step(
            state=state,
            step_name="business_model_canvas",
            result_key="business_model_canvas",
            progress=58,
            agent=self.bmc_agent,
        )

    async def competitive_analysis_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        new_state = await self._run_agent_step(
            state=state,
            step_name="competitive_analysis",
            result_key="competitive_analysis",
            progress=18,
            agent=self.competitive_analysis_agent,
        )
        analysis_data = dict(new_state.get("analysis_data") or {})
        analysis_data = self._normalize_public_source_quality(analysis_data)

        ledger = evidence_ledger.build(analysis_data)
        analysis_data["evidence_ledger"] = ledger
        analysis_data["evidence_confidence"] = (
            ledger.get("confidence_by_category") or {}
        )
        analysis_data["overall_evidence_confidence"] = (
            analysis_data["evidence_confidence"].get(
                "overall_evidence_confidence"
            )
            or "low"
        )

        enriched_state: StartupEvaluatorState = {
            **new_state,
            "analysis_data": analysis_data,
        }
        await self._notify_step_complete(enriched_state)
        return enriched_state

    def _normalize_public_source_quality(
        self,
        analysis_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Attach methodology-aware quality without changing source roles."""
        data = dict(analysis_data or {})
        source_keys = {
            "sources",
            "public_sources",
            "local_competitor_sources",
            "regional_competitor_sources",
            "international_benchmark_sources",
            "technology_provider_sources",
            "adjacent_solution_sources",
            "market_context_sources",
            "market_sources",
            "local_direct_competitors",
            "local_adjacent_solutions",
            "regional_competitors",
            "international_benchmarks",
            "technology_providers",
        }

        for section_name in ("competitive_analysis", "forgecrawler"):
            section = data.get(section_name)
            if not isinstance(section, dict):
                continue

            normalized_section = dict(section)
            for key in source_keys:
                rows = normalized_section.get(key)
                if not isinstance(rows, list):
                    continue
                normalized_section[key] = [
                    self._source_with_quality(row)
                    for row in rows
                    if isinstance(row, dict)
                ]
            data[section_name] = normalized_section

        return data

    def _source_with_quality(self, source: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(source)
        explicit_quality = str(
            row.get("evidence_quality")
            or row.get("methodology_quality")
            or ""
        ).strip().lower()

        try:
            domain = urlparse(str(row.get("url") or "")).netloc.lower()
        except Exception:
            domain = ""

        source_type = str(row.get("source_type") or "").strip().lower()
        source_role = str(row.get("source_role") or "").strip().lower()
        low_methodology_domains = {
            "scribd.com",
            "www.scribd.com",
            "marketsandmarkets.com",
            "www.marketsandmarkets.com",
            "marketresearchfuture.com",
            "www.marketresearchfuture.com",
            "snsinsider.com",
            "www.snsinsider.com",
            "rootsanalysis.com",
            "www.rootsanalysis.com",
            "ensun.io",
            "www.ensun.io",
            "fdatabot.com",
            "www.fdatabot.com",
        }

        if explicit_quality in {"low", "medium", "high"}:
            quality = explicit_quality
        elif domain in low_methodology_domains:
            quality = "low"
        elif source_type in {"regulation", "official_evidence"}:
            quality = "high"
        elif domain.endswith(".gov") or domain.endswith(".edu"):
            quality = "high"
        elif domain.endswith(".org") or source_role == "official_evidence":
            quality = "medium"
        elif source_type in {
            "technology_benchmark",
            "adjacent_solution",
            "competitor",
            "pricing_page",
        }:
            quality = "medium"
        else:
            quality = "low"

        methodology_blob = " ".join(
            str(row.get(key) or "")
            for key in ("title", "snippet", "extracted_text_preview")
        ).lower()
        negative_methodology_markers = (
            "without visible methodology",
            "methodology not visible",
            "methodology unavailable",
            "méthodologie non visible",
            "méthodologie absente",
            "méthodologie indisponible",
        )
        methodology_visible = bool(row.get("methodology_visible"))
        if not methodology_visible and not any(
            marker in methodology_blob for marker in negative_methodology_markers
        ):
            methodology_visible = any(
                marker in methodology_blob
                for marker in (
                    "methodology",
                    "méthodologie",
                    "sample size",
                    "échantillon",
                    "official statistics",
                    "statistiques officielles",
                )
            )

        row["evidence_quality"] = quality
        row["methodology_visible"] = methodology_visible

        # Confidence on a public card describes evidence strength, not only
        # semantic relevance. Commercial report pages and document hosts stay
        # low even when their topic match is acceptable.
        if quality == "low":
            row["confidence"] = "low"
        elif quality == "high":
            row["confidence"] = "high"
        elif str(row.get("confidence") or "").lower() not in {
            "low",
            "medium",
            "high",
        }:
            row["confidence"] = "medium"

        return row

    def _enrich_market_study_from_evidence(
        self,
        *,
        market_study: Dict[str, Any],
        analysis_data: Dict[str, Any],
        output_language: str,
    ) -> Dict[str, Any]:
        """Fill evidence-aware local feasibility and cautious trend signals."""
        language = normalize_output_language(output_language)
        ledger = analysis_data.get("evidence_ledger")
        if not isinstance(ledger, dict):
            ledger = evidence_ledger.build(analysis_data)

        sources = [
            dict(item)
            for item in (ledger.get("source_index") or {}).values()
            if isinstance(item, dict)
        ]

        local_sources = [
            source
            for source in sources
            if str(source.get("region_match") or "").lower() == "local"
            and set(source.get("evidence_categories") or [])
            & {
                "regional_context",
                "sector_context",
                "local_market_signal",
                "market_demand",
                "market_demand_claim",
                "solution_benchmark",
            }
        ]
        technology_sources = [
            source
            for source in sources
            if set(source.get("evidence_categories") or [])
            & {"technology_benchmark", "solution_benchmark"}
        ]
        market_sources = [
            source
            for source in sources
            if set(source.get("evidence_categories") or [])
            & {
                "market_size",
                "market_size_claim",
                "market_demand",
                "market_demand_claim",
                "sector_context",
            }
        ]

        if language == "en":
            local_signal = (
                "Retained local sources provide sector and ecosystem signals, "
                "but they do not yet prove active demand, budget availability "
                "or willingness to pay."
                if local_sources
                else "No compatible local evidence currently confirms demand, "
                "adoption or willingness to pay; local feasibility requires "
                "official data and field interviews."
            )
            trend_candidates = []
            if technology_sources:
                trend_candidates.append(
                    "Retained technology benchmarks show that related automation, "
                    "sensing or analysis workflows exist; transfer to the target "
                    "region and use case remains to be tested."
                )
            if market_sources:
                trend_candidates.append(
                    "Retained market pages are secondary market signals. Their "
                    "figures and methodologies must be checked before being used "
                    "for an investment decision."
                )
        else:
            local_signal = (
                "Les sources locales retenues constituent des signaux de contexte "
                "sectoriel et d’écosystème, mais elles ne prouvent pas encore une "
                "demande active, un budget disponible ni la volonté de payer."
                if local_sources
                else "Aucune preuve locale compatible ne confirme actuellement la "
                "demande, l’adoption ou la volonté de payer ; la faisabilité locale "
                "doit être validée par des données officielles et des entretiens terrain."
            )
            trend_candidates = []
            if technology_sources:
                trend_candidates.append(
                    "Les benchmarks technologiques retenus montrent l’existence de "
                    "workflows proches d’automatisation, de capteurs ou d’analyse ; "
                    "leur transférabilité au cas d’usage et à la région cible reste à tester."
                )
            if market_sources:
                trend_candidates.append(
                    "Les pages de marché retenues sont des signaux secondaires. "
                    "Leurs chiffres et leurs méthodologies doivent être vérifiés "
                    "avant toute décision d’investissement."
                )

        def missing(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() in {"", "—", "-", "n/a", "N/A"}
            if isinstance(value, list):
                return not [item for item in value if str(item or "").strip()]
            return False

        if missing(market_study.get("local_feasibility")):
            market_study["local_feasibility"] = local_signal
        if missing(market_study.get("local_context")):
            market_study["local_context"] = local_signal

        existing_trends = market_study.get("market_trends") or market_study.get("trends")
        if missing(existing_trends):
            market_study["market_trends"] = trend_candidates or [
                (
                    "No market trend is sufficiently supported by the retained evidence."
                    if language == "en"
                    else "Aucune tendance de marché n’est suffisamment soutenue par les preuves retenues."
                )
            ]
        market_study["trends"] = list(market_study.get("market_trends") or [])
        market_study["evidence_basis"] = [
            {
                "source_id": source.get("source_id"),
                "title": source.get("title"),
                "region_match": source.get("region_match"),
                "source_type": source.get("source_type"),
                "evidence_quality": source.get("evidence_quality"),
            }
            for source in sources[:8]
        ]
        market_study["local_evidence_status"] = (
            "signal_only" if local_sources else "unverified"
        )
        market_study["market_evidence_status"] = (
            "secondary_signals" if market_sources else "unverified"
        )
        return market_study

    async def financial_estimation_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        return await self._run_agent_step(
            state=state,
            step_name="financial_estimation",
            result_key="financial_estimation",
            progress=72,
            agent=self.financial_estimation_agent,
        )

    async def startup_score_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        return await self._run_agent_step(
            state=state,
            step_name="startup_score",
            result_key="startup_score",
            progress=100,
            agent=self.startup_score_agent,
        )

    async def persona_builder_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        analysis_data = dict(state.get("analysis_data") or {})
        completed_steps = list(state.get("completed_steps") or [])
        failed_steps = list(state.get("failed_steps") or [])

        step_name = "persona_builder"
        result_key = "persona_builder"
        progress = 84

        try:
            project_payload = project_context_builder.project_payload(
                project_id=state.get("project_id"),
                title=state.get("title", ""),
                description=state.get("description", ""),
                industry=state.get("industry") or "",
                market_region=state.get("region") or "",
                output_language=state.get("output_language", "fr"),
            )

            result = await self.persona_builder_agent.run(
                {
                    "project": project_payload,
                    "project_context": state.get("project_context", {}),
                    "analysis_data": analysis_data,
                    "project_intelligence": analysis_data.get("project_intelligence", {}),
                    "structured_project_context": analysis_data.get("structured_project_context", {}),
                    "agent_context_packet": analysis_data.get("agent_context_packet", {}),
                    "project_context_packet": analysis_data.get("project_context_packet", {}),
                    "context_confidence": analysis_data.get("context_confidence", {}),
                    "idea_readiness": analysis_data.get("idea_readiness", {}),
                    "legacy_project_context": analysis_data.get("legacy_project_context", {}),
                    "query_planner": analysis_data.get("query_planner", {}),
                    "output_language": state.get("output_language", "fr"),
                    "title": state.get("title", ""),
                    "description": state.get("description", ""),
                    "industry": state.get("industry") or "",
                    "region": state.get("region") or "",
                }
            )

            result = self._sanitize_agent_result(
                result=result,
                state=state,
                role="persona_builder",
            )

            analysis_data[result_key] = result

            if step_name not in completed_steps:
                completed_steps.append(step_name)

            analysis_data["partial_completion"] = bool(
                state.get("partial_completion", False)
            )

            new_state: StartupEvaluatorState = {
                **state,
                "analysis_data": analysis_data,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "current_step": step_name,
                "progress": progress,
                "error": None,
            }

            await self._notify_step_complete(new_state)
            return new_state

        except Exception as exc:
            return await self._agent_step_failed(
                state=state,
                step_name=step_name,
                progress=progress,
                error=exc,
            )

    async def fact_checker_node(self, state: StartupEvaluatorState) -> StartupEvaluatorState:
        analysis_data = dict(state.get("analysis_data") or {})
        completed_steps = list(state.get("completed_steps") or [])
        failed_steps = list(state.get("failed_steps") or [])

        step_name = "fact_checker"
        result_key = "fact_check_report"
        progress = 94

        try:
            project_payload = project_context_builder.project_payload(
                project_id=state.get("project_id"),
                title=state.get("title", ""),
                description=state.get("description", ""),
                industry=state.get("industry") or "",
                market_region=state.get("region") or "",
                output_language=state.get("output_language", "fr"),
            )

            fact_checker_state = {
                **dict(state),
                "project": project_payload,
                "project_context": state.get("project_context", {}),
                "analysis_data": analysis_data,
                "project_intelligence": analysis_data.get("project_intelligence", {}),
                "structured_project_context": analysis_data.get("structured_project_context", {}),
                "agent_context_packet": analysis_data.get("agent_context_packet", {}),
                "project_context_packet": analysis_data.get("project_context_packet", {}),
                "context_confidence": analysis_data.get("context_confidence", {}),
                "idea_readiness": analysis_data.get("idea_readiness", {}),
                "legacy_project_context": analysis_data.get("legacy_project_context", {}),
                "query_planner": analysis_data.get("query_planner", {}),
                "output_language": state.get("output_language", "fr"),
                "title": state.get("title", ""),
                "description": state.get("description", ""),
                "industry": state.get("industry") or "",
                "region": state.get("region") or "",
            }

            result = await self.fact_checker_agent.run(fact_checker_state)

            if not isinstance(result, dict):
                result = self.fact_checker_agent._build_fallback_fact_check_report(
                    state=fact_checker_state,
                    language=normalize_output_language(
                        state.get("output_language", "fr")
                    ),
                    error_message="FactCheckerAgent returned a non-dict result.",
                )

            result = self._sanitize_agent_result(
                result=result,
                state=state,
                role="fact_checker",
            )

            if not isinstance(result, dict):
                result = self.fact_checker_agent._build_fallback_fact_check_report(
                    state=fact_checker_state,
                    language=normalize_output_language(
                        state.get("output_language", "fr")
                    ),
                    error_message="FactChecker result became invalid after sanitization.",
                )

            analysis_data[result_key] = result
            analysis_data = evidence_ledger.sanitize_public_claims(analysis_data)

            if step_name not in completed_steps:
                completed_steps.append(step_name)

            if result.get("status") == "fallback_completed":
                if "fact_checker_fallback" not in completed_steps:
                    completed_steps.append("fact_checker_fallback")

                analysis_data["fact_checker_fallback_used"] = True
                analysis_data["fact_checker_error_handled"] = True

            analysis_data["partial_completion"] = bool(
                state.get("partial_completion", False)
            )

            analysis_data["startup_evaluator_meta"] = {
                **analysis_data.get("startup_evaluator_meta", {}),
                "fact_checker_status": result.get("status"),
                "fact_checker_error_handled": bool(result.get("error_handled")),
                "fact_checker_fallback_used": result.get("status") == "fallback_completed",
            }

            new_state: StartupEvaluatorState = {
                **state,
                "analysis_data": analysis_data,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "current_step": step_name,
                "progress": progress,
                "error": None,
                "partial_completion": bool(state.get("partial_completion", False)),
            }

            await self._notify_step_complete(new_state)
            return new_state

        except Exception as exc:
            logger.exception(
                "[StartupEvaluatorGraph] fact_checker hard failure handled with fallback: %s",
                str(exc),
            )

            fact_checker_state = {
                **dict(state),
                "analysis_data": analysis_data,
                "output_language": state.get("output_language", "fr"),
            }

            fallback = self.fact_checker_agent._build_fallback_fact_check_report(
                state=fact_checker_state,
                language=normalize_output_language(state.get("output_language", "fr")),
                error_message=str(exc),
            )

            analysis_data[result_key] = fallback
            analysis_data = evidence_ledger.sanitize_public_claims(analysis_data)
            analysis_data["fact_checker_fallback_used"] = True
            analysis_data["fact_checker_error_handled"] = True
            analysis_data["partial_completion"] = bool(
                state.get("partial_completion", False)
            )

            if step_name not in completed_steps:
                completed_steps.append(step_name)

            if "fact_checker_fallback" not in completed_steps:
                completed_steps.append("fact_checker_fallback")

            new_state: StartupEvaluatorState = {
                **state,
                "analysis_data": analysis_data,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "current_step": step_name,
                "progress": progress,
                "error": None,
                "partial_completion": bool(state.get("partial_completion", False)),
            }

            await self._notify_step_complete(new_state)
            return new_state

    async def _run_agent_step(
        self,
        state: StartupEvaluatorState,
        step_name: str,
        result_key: str,
        progress: int,
        agent: Any,
    ) -> StartupEvaluatorState:
        analysis_data = dict(state.get("analysis_data") or {})
        completed_steps = list(state.get("completed_steps") or [])
        failed_steps = list(state.get("failed_steps") or [])

        try:
            logger.info("[StartupEvaluatorGraph] Démarrage step=%s", step_name)

            agent_state = {
                **dict(state),
                "project_intelligence": analysis_data.get("project_intelligence", {}),
                "structured_project_context": analysis_data.get("structured_project_context", {}),
                "agent_context_packet": analysis_data.get("agent_context_packet", {}),
                "project_context_packet": analysis_data.get("project_context_packet", {}),
                "context_confidence": analysis_data.get("context_confidence", {}),
                "idea_readiness": analysis_data.get("idea_readiness", {}),
                "legacy_project_context": analysis_data.get("legacy_project_context", {}),
                "query_planner": analysis_data.get("query_planner", {}),
            }

            result = await agent.run(agent_state)

            extra_analysis_data = {}

            if isinstance(result, dict):
                extra_analysis_data = result.pop("__extra_analysis_data", {}) or {}

            result = self._sanitize_agent_result(
                result=result,
                state=state,
                role=step_name,
            )

            if isinstance(extra_analysis_data, dict):
                if step_name == "competitive_analysis":
                    # ForgeCrawler has already passed its dedicated relevance and
                    # public-safety gates. A generic graph sanitizer must not
                    # reclassify or delete these validated source structures.
                    forgecrawler_payload = extra_analysis_data.get("forgecrawler")

                    if isinstance(forgecrawler_payload, dict):
                        analysis_data["forgecrawler"] = dict(forgecrawler_payload)

                        logger.info(
                            "[SourcePipeline][Graph] ForgeCrawler preserved | "
                            "sources=%s | local=%s | regional=%s | "
                            "international=%s | market=%s",
                            len(forgecrawler_payload.get("sources") or []),
                            len(
                                forgecrawler_payload.get(
                                    "local_competitor_sources"
                                )
                                or []
                            ),
                            len(
                                forgecrawler_payload.get(
                                    "regional_competitor_sources"
                                )
                                or []
                            ),
                            len(
                                forgecrawler_payload.get(
                                    "international_benchmark_sources"
                                )
                                or []
                            ),
                            len(
                                forgecrawler_payload.get(
                                    "market_context_sources"
                                )
                                or []
                            ),
                        )

                    other_extra_data = {
                        key: value
                        for key, value in extra_analysis_data.items()
                        if key != "forgecrawler"
                    }

                    if other_extra_data:
                        sanitized_other_data = self._sanitize_extra_analysis_data(
                            data=other_extra_data,
                            state=state,
                        )
                        analysis_data.update(sanitized_other_data)
                else:
                    sanitized_extra_data = self._sanitize_extra_analysis_data(
                        data=extra_analysis_data,
                        state=state,
                    )
                    analysis_data.update(sanitized_extra_data)

            analysis_data[result_key] = result

            if step_name not in completed_steps:
                completed_steps.append(step_name)

            analysis_data["partial_completion"] = bool(
                state.get("partial_completion", False)
            )

            new_state: StartupEvaluatorState = {
                **state,
                "analysis_data": analysis_data,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "current_step": step_name,
                "progress": progress,
                "error": None,
            }

            await self._notify_step_complete(new_state)

            logger.info("[StartupEvaluatorGraph] Step terminé step=%s", step_name)

            return new_state

        except Exception as exc:
            return await self._agent_step_failed(
                state=state,
                step_name=step_name,
                progress=progress,
                error=exc,
            )

    # ========================================================
    # Context-aware sanitizer
    # ========================================================

    def _sanitize_agent_result(
        self,
        *,
        result: Any,
        state: StartupEvaluatorState,
        role: str,
    ) -> Any:
        """
        Graph-level sanitizer V6.2.

        Important :
        - financial_estimation est maintenant déterministe et sans LLM ;
        - competitive_analysis possède déjà son propre strict relevance gate ;
        - donc le graph ne doit plus relogger de faux positifs pour ces rôles ;
        - les autres agents restent contrôlés par le sanitizer context-aware.
        """

        try:
            internally_guarded_roles = {
                "competitive_analysis",
                "financial_estimation",
                # PersonaBuilderAgent is deterministic, schema-validated and
                # archetype-aware. Re-running the broad text guard here removes
                # valid generic fields such as buying power and interview prompts.
                "persona_builder",
            }

            if role in internally_guarded_roles:
                return result

            project_context = state.get("project_context", {}) or {}

            allowed_context = self._build_allowed_context_for_contamination(
                state=state,
                project_context=project_context,
            )

            contamination_count = self._detect_context_aware_contamination(
                value=result,
                allowed_context=allowed_context,
            )

            if contamination_count <= 0:
                return result

            logger.warning(
                "[StartupEvaluatorGraph] Contamination détectée | role=%s | count=%s",
                role,
                contamination_count,
            )

            return self._context_aware_sanitize_object(
                value=result,
                allowed_context=allowed_context,
            )

        except Exception as exc:
            logger.warning(
                "[StartupEvaluatorGraph] Sanitize skipped | role=%s | error=%s",
                role,
                str(exc),
            )
            return result

    def _sanitize_extra_analysis_data(
        self,
        *,
        data: Dict[str, Any],
        state: StartupEvaluatorState,
    ) -> Dict[str, Any]:
        try:
            project_context = state.get("project_context", {}) or {}
            allowed_context = self._build_allowed_context_for_contamination(
                state=state,
                project_context=project_context,
            )

            sanitized = self._context_aware_sanitize_object(
                value=data,
                allowed_context=allowed_context,
            )

            return sanitized if isinstance(sanitized, dict) else {}

        except Exception:
            try:
                return domain_integrity_guard.sanitize_object(
                    data=data,
                    project_context=state.get("project_context", {}),
                )
            except Exception:
                return data if isinstance(data, dict) else {}

    def _build_allowed_context_for_contamination(
        self,
        *,
        state: StartupEvaluatorState,
        project_context: Dict[str, Any],
    ) -> str:
        parts = [
            state.get("title", ""),
            state.get("description", ""),
            state.get("industry", ""),
            state.get("region", ""),
            state.get("output_language", ""),
        ]

        self._append_nested_values(parts, project_context)

        return self._normalize_contamination_text(" ".join(str(p) for p in parts if p))

    def _append_nested_values(self, parts: list[str], value: Any) -> None:
        if value is None:
            return

        if isinstance(value, dict):
            for nested_value in value.values():
                self._append_nested_values(parts, nested_value)
            return

        if isinstance(value, list):
            for item in value:
                self._append_nested_values(parts, item)
            return

        clean = str(value).strip()

        if clean:
            parts.append(clean)

    def _detect_context_aware_contamination(
        self,
        *,
        value: Any,
        allowed_context: str,
    ) -> int:
        text = self._normalize_contamination_text(str(value or ""))

        if not text:
            return 0

        count = 0

        for term in self._strict_demo_forbidden_terms():
            normalized_term = self._normalize_contamination_text(term)

            if not normalized_term:
                continue

            if normalized_term in allowed_context:
                continue

            if normalized_term in text:
                count += text.count(normalized_term)

        healthcare_context = self._context_mentions_healthcare(allowed_context)

        for term in self._healthcare_contextual_terms():
            normalized_term = self._normalize_contamination_text(term)

            if not normalized_term:
                continue

            if normalized_term in allowed_context:
                continue

            if healthcare_context:
                continue

            if normalized_term in text:
                count += text.count(normalized_term)

        return count

    def _context_aware_sanitize_object(
        self,
        *,
        value: Any,
        allowed_context: str,
    ) -> Any:
        if isinstance(value, dict):
            cleaned: Dict[str, Any] = {}

            for key, item in value.items():
                clean_key = str(key or "").strip()

                if not clean_key:
                    continue

                if clean_key in {
                    "debug",
                    "raw_data",
                    "raw_response",
                    "raw_data_backup",
                    "raw_data_backup_hidden",
                    "internal_error",
                }:
                    continue

                cleaned_item = self._context_aware_sanitize_object(
                    value=item,
                    allowed_context=allowed_context,
                )

                if self._is_empty_value(cleaned_item):
                    continue

                cleaned[clean_key] = cleaned_item

            return cleaned

        if isinstance(value, list):
            cleaned_list = []

            for item in value:
                cleaned_item = self._context_aware_sanitize_object(
                    value=item,
                    allowed_context=allowed_context,
                )

                if self._is_empty_value(cleaned_item):
                    continue

                cleaned_list.append(cleaned_item)

            return cleaned_list

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value

        return self._context_aware_sanitize_text(
            value=value,
            allowed_context=allowed_context,
        )

    def _context_aware_sanitize_text(
        self,
        *,
        value: Any,
        allowed_context: str,
    ) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)

        terms_to_remove = list(self._strict_demo_forbidden_terms())

        if not self._context_mentions_healthcare(allowed_context):
            terms_to_remove.extend(self._healthcare_contextual_terms())

        for term in terms_to_remove:
            normalized_term = self._normalize_contamination_text(term)

            if not normalized_term:
                continue

            if normalized_term in allowed_context:
                continue

            text = re.sub(
                re.escape(term),
                "",
                text,
                flags=re.IGNORECASE,
            )

        return text[:1500].strip()

    def _strict_demo_forbidden_terms(self) -> set[str]:
        return {
            "pharmacy delivery",
            "medicine delivery",
            "medicine stock",
            "stock medicine",
            "stock medicines",
            "stock médicaments",
            "stock medicaments",
            "pharmasoft",
            "infopharma",
            "medstock",
            "orange max it",
            "crypto trading",
            "stock trading",
            "forex trading",
            "tiktok growth",
            "tiktok analytics",
            "food delivery",
            "restaurant delivery",
            "agrobot",
            "greenhouse robot",
            "robot agricole",
            "network cell info lite",
            "opera web browser",
            "free ai short video generator",
            "chrome web store skillbridge",
        }

    def _healthcare_contextual_terms(self) -> set[str]:
        return {
            "doctor appointment",
            "medical appointment",
            "clinic booking",
            "patient scheduling",
            "telemedicine",
            "healthcare booking",
        }

    def _context_mentions_healthcare(self, allowed_context: str) -> bool:
        healthcare_markers = {
            "healthtech",
            "health care",
            "healthcare",
            "medical",
            "clinic",
            "doctor",
            "patient",
            "hospital",
            "médecin",
            "medecin",
            "clinique",
            "santé",
            "sante",
        }

        return any(marker in allowed_context for marker in healthcare_markers)

    def _normalize_contamination_text(self, value: Any) -> str:
        text = str(value or "").replace("’", "'").lower()
        text = "".join(
            char
            for char in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(char)
        )
        return re.sub(r"\s+", " ", text).strip()

    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, str):
            return value.strip() == ""

        if isinstance(value, list):
            return len(value) == 0

        if isinstance(value, dict):
            return len(value) == 0

        return False

    async def _agent_step_failed(
        self,
        *,
        state: StartupEvaluatorState,
        step_name: str,
        progress: int,
        error: Exception,
    ) -> StartupEvaluatorState:
        error_message = f"{step_name} failed: {str(error)}"
        logger.exception("[StartupEvaluatorGraph] %s", error_message)

        analysis_data = dict(state.get("analysis_data") or {})
        completed_steps = list(state.get("completed_steps") or [])
        failed_steps = list(state.get("failed_steps") or [])

        if step_name not in failed_steps:
            failed_steps.append(step_name)

        analysis_data["partial_completion"] = True

        new_state: StartupEvaluatorState = {
            **state,
            "analysis_data": analysis_data,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "current_step": step_name,
            "progress": progress,
            "error": error_message,
            "partial_completion": True,
        }

        await self._notify_step_complete(new_state)

        return new_state

    async def _notify_step_complete(self, state: StartupEvaluatorState) -> None:
        if self.on_step_complete is None:
            return

        await self.on_step_complete(dict(state))