# ============================================================
# backend/app/agents/fact_checker_agent.py
# ============================================================
#
# FactCheckerAgent V6 — Claim-Compatible Evidence + Context Locked
#
# Objectifs :
# - ne jamais casser le pipeline Startup Evaluator ;
# - corriger le bug `_confidence_level` manquant ;
# - générer toujours un rapport fact_check_report exploitable ;
# - ne jamais inventer de sources ;
# - respecter output_language fr/en ;
# - rester lié au project_context ;
# - signaler clairement les hypothèses, limites et validations terrain.
# ============================================================

from copy import deepcopy
import logging
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder
from app.services.evidence_ledger import evidence_ledger


logger = logging.getLogger(__name__)


class FactCheckerAgent:
    """
    Fact checker déterministe et conservateur.

    Les sources déjà validées par ForgeCrawler, SourceRelevanceGate et
    CompetitiveAnalysisAgent sont conservées. Le Fact Checker ne refait pas
    une troisième classification métier susceptible de supprimer ces sources.
    """

    PUBLIC_SOURCE_PATHS = (
        ("competitive_analysis", "sources"),
        ("competitive_analysis", "public_sources"),
        ("competitive_analysis", "local_competitor_sources"),
        ("competitive_analysis", "regional_competitor_sources"),
        ("competitive_analysis", "international_benchmark_sources"),
        ("competitive_analysis", "market_context_sources"),
        ("competitive_analysis", "market_sources"),
        ("forgecrawler", "sources"),
        ("forgecrawler", "public_sources"),
        ("forgecrawler", "local_competitor_sources"),
        ("forgecrawler", "regional_competitor_sources"),
        ("forgecrawler", "international_benchmark_sources"),
        ("forgecrawler", "market_context_sources"),
        ("forgecrawler", "market_sources"),
    )

    PUBLIC_CARD_PATHS = (
        ("competitive_analysis", "local_direct_competitors"),
        ("competitive_analysis", "local_adjacent_solutions"),
        ("competitive_analysis", "regional_competitors"),
        ("competitive_analysis", "international_benchmarks"),
        ("competitive_analysis", "verified_competitors"),
        ("competitive_analysis", "local_competitors"),
    )

    COMPETITOR_SOURCE_TYPES = {
        "competitor",
        "direct_competitor",
        "probable_direct_competitor",
        "pricing_page",
        "adjacent_solution",
        "technology_benchmark",
        "technology_provider",
    }

    MARKET_SOURCE_TYPES = {
        "market_article",
        "market_evidence",
        "local_market_signal",
        "regulation",
        "directory",
    }

    MARKET_SIZE_CATEGORIES = {"market_size", "market_size_claim"}
    MARKET_DEMAND_CATEGORIES = {
        "market_demand",
        "market_demand_claim",
        "local_market_signal",
        "adoption_signal",
    }
    PROBLEM_CATEGORIES = {"problem_context", "workflow_context", "current_alternatives"}
    SOLUTION_CATEGORIES = {
        "solution_benchmark",
        "competitor_product",
        "technology_benchmark",
        "technology_provider",
    }
    PRICING_CATEGORIES = {"pricing", "pricing_signal"}
    REGULATION_CATEGORIES = {"regulation", "regulatory_evidence"}


    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Point d'entrée principal du Startup Evaluator.

        Garanties :
        - ne lève jamais d'exception vers le graphe ;
        - n'invente jamais de source ;
        - conserve les sources publiques déjà validées en amont ;
        - ne retourne jamais une affirmation vide ;
        - reste lié au contexte du projet et à la langue demandée.
        """
        language = normalize_output_language(state.get("output_language", "fr"))

        try:
            project_context = self._get_project_context(state)
            profile = self._build_profile(state, project_context)

            result = self._build_fact_check_report(
                profile=profile,
                analysis_data=state.get("analysis_data") or {},
                project_context=project_context,
                language=language,
            )

            result = self._validate_or_sanitize(
                result=result,
                project_context=project_context,
                language=language,
            )

            result = self._repair_public_report(
                result=result,
                fallback=result,
                language=language,
            )

            result["output_language"] = language
            result["context_locked"] = True
            result["error_handled"] = False

            logger.info(
                "[FactCheckerAgent][AUDIT] total_sources=%s | relevant_sources=%s | claims=%s",
                result.get("source_count", 0),
                result.get("relevant_source_count", 0),
                len(result.get("claims") or []),
            )

            return result

        except Exception as exc:
            logger.exception(
                "[FactCheckerAgent] Safe fallback used | error=%s",
                str(exc),
            )

            fallback = self._build_fallback_fact_check_report(
                state=state,
                language=language,
                error_message=str(exc),
            )

            return self._repair_public_report(
                result=fallback,
                fallback=fallback,
                language=language,
            )

    # ========================================================
    # Context / profile
    # ========================================================

    def _get_project_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        existing = state.get("project_context")

        if isinstance(existing, dict) and (
            existing.get("anchor_terms")
            or existing.get("strong_keywords")
            or existing.get("project_name")
            or existing.get("title")
        ):
            return existing

        project = state.get("project") or {}

        return project_context_builder.build(
            title=str(
                state.get("title")
                or state.get("project_name")
                or project.get("title")
                or ""
            ),
            description=str(
                state.get("description")
                or project.get("description")
                or ""
            ),
            industry=str(
                state.get("industry")
                or project.get("industry")
                or ""
            ),
            market_region=str(
                state.get("market_region")
                or state.get("region")
                or state.get("target_region")
                or project.get("market_region")
                or ""
            ),
            output_language=str(state.get("output_language") or "fr"),
            analysis_data=state.get("analysis_data") or {},
        )

    def _build_profile(
        self,
        state: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        analysis_data = state.get("analysis_data") or {}

        market_study = analysis_data.get("market_study") or {}
        competitive = analysis_data.get("competitive_analysis") or {}
        forgecrawler = analysis_data.get("forgecrawler") or {}
        financial = analysis_data.get("financial_estimation") or {}
        startup_score = analysis_data.get("startup_score") or {}
        debate_room = analysis_data.get("debate_room") or {}

        language = normalize_output_language(state.get("output_language", "fr"))

        title = self._safe_text(
            project_context.get("project_name")
            or project_context.get("title")
            or state.get("project_name")
            or state.get("title")
            or (state.get("project") or {}).get("title"),
            "Project" if language == "en" else "Projet",
        )

        region = self._safe_text(
            project_context.get("market_region")
            or project_context.get("target_region")
            or state.get("market_region")
            or state.get("region")
            or state.get("target_region")
            or (state.get("project") or {}).get("market_region"),
            "",
        )

        target_market = self._safe_text(
            market_study.get("target_market")
            or analysis_data.get("target_market")
            or analysis_data.get("target_users")
            or project_context.get("target_users")
            or project_context.get("target_market"),
            "",
        )

        sources = self._collect_sources(analysis_data)

        return {
            "title": title,
            "description": self._safe_text(
                project_context.get("description")
                or state.get("description")
                or (state.get("project") or {}).get("description"),
                "",
            ),
            "industry": self._safe_text(
                project_context.get("industry")
                or state.get("industry")
                or (state.get("project") or {}).get("industry"),
                "",
            ),
            "region": region,
            "target_market": target_market,
            "target_users": self._safe_list(
                project_context.get("target_users")
                or analysis_data.get("target_users")
                or target_market
            ),
            "problem": self._safe_text(
                analysis_data.get("problem")
                or analysis_data.get("problem_solved")
                or project_context.get("problem")
                or project_context.get("core_problem"),
                "",
            ),
            "solution": self._safe_text(
                analysis_data.get("proposed_solution")
                or project_context.get("solution")
                or project_context.get("solution_type"),
                "",
            ),
            "market_size": self._safe_text(market_study.get("market_size"), ""),
            "data_confidence": self._safe_text(
                market_study.get("data_confidence"),
                "medium",
            ).lower(),
            "competitive_confidence": self._safe_text(
                competitive.get("confidence_level"),
                "low",
            ).lower(),
            "crawler_status": self._safe_text(forgecrawler.get("status"), "limited"),
            "crawler_confidence": self._safe_text(
                forgecrawler.get("confidence_level"),
                "low",
            ).lower(),
            "financial_risk_level": self._safe_text(
                financial.get("financial_risk_level"),
                "medium",
            ).lower(),
            "startup_score": startup_score.get("global_score"),
            "debate_verdict": (debate_room.get("judge") or {}).get("verdict"),
            "sources": sources,
            "anchor_terms": self._context_terms(project_context),
        }

    # ========================================================
    # Main report
    # ========================================================

    def _build_fact_check_report(
        self,
        profile: Dict[str, Any],
        analysis_data: Dict[str, Any],
        project_context: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        """
        Construit le rapport à partir des sources publiques canoniques.

        Une source internationale de benchmark ne prouve pas :
        - la taille du marché tunisien ;
        - l'existence d'un concurrent local ;
        - la volonté de payer ;
        - la viabilité financière.

        Chaque affirmation reçoit donc uniquement les preuves correspondant
        réellement à sa catégorie.
        """
        source_count = len(profile["sources"])

        relevant_sources = self._filter_relevant_sources(
            sources=profile["sources"],
            project_context=project_context,
        )

        relevant_source_count = len(relevant_sources)
        evidence_groups = self._build_evidence_groups(relevant_sources)

        evidence_confidence = self._evidence_confidence(
            source_count=source_count,
            relevant_source_count=relevant_source_count,
            evidence_groups=evidence_groups,
            profile=profile,
        )
        confidence_level = evidence_confidence["overall_evidence_confidence"]

        base_claims = self._build_claims(
            profile=profile,
            evidence_groups=evidence_groups,
            language=language,
        )
        claim_registry = evidence_ledger.build(analysis_data)
        registry_claims = self._claims_from_registry(
            registry=claim_registry,
            language=language,
            fallback_sources=relevant_sources,
        )
        claims = self._merge_claim_sets(base_claims, registry_claims)
        claims = self._clean_claims(claims)

        source_summary = {
            "total_sources": source_count,
            "sources_with_url": sum(
                1 for source in profile["sources"] if source.get("url")
            ),
            "verified_competitors": len(evidence_groups["local_competitors"]),
            "relevant_sources": relevant_source_count,
            "local_competitor_sources": len(
                evidence_groups["local_competitors"]
            ),
            "regional_benchmarks": len(
                evidence_groups["regional_benchmarks"]
            ),
            "international_benchmarks": len(
                evidence_groups["international_benchmarks"]
            ),
            "market_evidence": len(evidence_groups["market_evidence"]),
            "market_size_evidence": len(evidence_groups["market_size_evidence"]),
            "market_demand_evidence": len(evidence_groups["market_demand_evidence"]),
            "problem_evidence": len(evidence_groups["problem_evidence"]),
            "solution_evidence": len(evidence_groups["solution_evidence"]),
            "pricing_evidence": len(evidence_groups["pricing_evidence"]),
            "local_adjacent_solutions": len(evidence_groups["local_adjacent_solutions"]),
            "source_confidence": confidence_level,
            "evidence_confidence": evidence_confidence,
        }

        warnings = self._warnings(
            profile=profile,
            source_count=source_count,
            relevant_sources=relevant_sources,
            language=language,
        )

        recommended_validation = self._validation_plan(
            profile=profile,
            language=language,
        )

        limitations = self._limitations(
            profile=profile,
            source_count=source_count,
            relevant_sources=relevant_sources,
            language=language,
        )

        if language == "en":
            summary = (
                f"Fact checking for {profile['title']} is based on the available "
                f"analysis and {relevant_source_count} relevant retained source(s). "
                "Only claims directly supported by the corresponding evidence category "
                "are marked as sourced. Other claims remain estimates or require field validation."
            )
            method = "canonical_validated_source_review"

        else:
            summary = (
                f"La vérification factuelle de {profile['title']} repose sur l'analyse "
                f"disponible et {relevant_source_count} source(s) pertinente(s) retenue(s). "
                "Seules les affirmations directement soutenues par la catégorie de preuve "
                "correspondante sont marquées comme sourcées. Les autres restent des "
                "estimations ou nécessitent une validation terrain."
            )
            method = "verification_sources_canoniques_validees"

        return {
            "format": "fact_checker_v6_claim_compatible_evidence",
            "status": "completed",
            "method": method,
            "summary": summary,
            "fact_check_summary": summary,
            "output_language": language,
            "context_locked": True,
            "confidence_level": confidence_level,
            "global_confidence": confidence_level,
            "evidence_confidence": evidence_confidence,
            "source_count": source_count,
            "relevant_source_count": relevant_source_count,
            "source_summary": source_summary,
            "claim_registry_format": claim_registry.get("format"),
            "claim_registry_schema_version": claim_registry.get("schema_version"),
            "claim_coverage": {
                "total": len(claims),
                "section_specific": len(registry_claims),
                "sourced": sum(1 for claim in claims if claim.get("status") == "sourced"),
                "estimated": sum(1 for claim in claims if claim.get("status") == "estimated"),
                "requires_validation": sum(
                    1
                    for claim in claims
                    if claim.get("status") in {"field_validation_required", "not_confirmed"}
                ),
            },
            "claims": claims,
            "claims_to_verify": [
                claim["claim"]
                for claim in claims
                if claim.get("claim")
            ],
            "supported_claims": self._supported_claims(
                profile=profile,
                relevant_sources=relevant_sources,
                language=language,
            ),
            "uncertain_claims": self._uncertain_claims(
                profile=profile,
                language=language,
            ),
            "warnings": warnings,
            "red_flags": warnings,
            "recommended_next_checks": recommended_validation,
            "recommended_validation": recommended_validation,
            "limitations": limitations,
            "retained_sources": [
                self._compact_evidence(source)
                for source in relevant_sources[:8]
            ],
            "error_handled": False,
        }

    # ========================================================
    # Claims
    # ========================================================

    def _build_claims(
        self,
        profile: Dict[str, Any],
        evidence_groups: Dict[str, List[Dict[str, Any]]],
        language: str,
    ) -> List[Dict[str, Any]]:
        """Build claims only from evidence compatible with each claim type."""
        problem_evidence = evidence_groups["problem_evidence"]
        solution_evidence = evidence_groups["solution_evidence"]
        market_size_evidence = evidence_groups["market_size_evidence"]
        market_demand_evidence = evidence_groups["market_demand_evidence"]
        local_competitors = evidence_groups["local_competitors"]
        local_adjacent = evidence_groups["local_adjacent_solutions"]
        regional_benchmarks = evidence_groups["regional_benchmarks"]
        international_benchmarks = evidence_groups["international_benchmarks"]

        # A market-size claim is sourced only when quantitative evidence and
        # a demand/adoption signal both have visible or institutionally credible
        # methodology. Commercial report landing pages remain signals to verify.
        qualified_market_size = [
            source
            for source in market_size_evidence
            if self._is_qualified_market_evidence(source)
        ]
        qualified_market_demand = [
            source
            for source in market_demand_evidence
            if self._is_qualified_market_evidence(source)
        ]
        market_is_sourced = bool(
            qualified_market_size and qualified_market_demand
        )

        if local_competitors:
            competition_status = "sourced"
            competition_confidence = "high" if len(local_competitors) >= 2 else "medium"
            competition_evidence = local_competitors[:3]
            if language == "en":
                competition_claim = (
                    f"{len(local_competitors)} verified direct local competitor source(s) "
                    f"were retained for {profile['title']} in {profile['region']}."
                )
            else:
                competition_claim = (
                    f"{len(local_competitors)} source(s) de concurrent direct local vérifié "
                    f"ont été retenues pour {profile['title']} dans {profile['region']}."
                )
        else:
            comparison_sources = local_adjacent + regional_benchmarks + international_benchmarks
            if comparison_sources:
                competition_status = "sourced"
                competition_confidence = "medium"
                competition_evidence = comparison_sources[:3]
                if language == "en":
                    competition_claim = (
                        f"{len(comparison_sources)} adjacent or benchmark source(s) were retained "
                        f"for {profile['title']}, but no verified direct local competitor was "
                        f"established in {profile['region']}."
                    )
                else:
                    competition_claim = (
                        f"{len(comparison_sources)} source(s) adjacente(s) ou de benchmark ont été "
                        f"retenues pour {profile['title']}, mais aucun concurrent direct local "
                        f"vérifié n'a été établi dans {profile['region']}."
                    )
            else:
                competition_status = "not_confirmed"
                competition_confidence = "low"
                competition_evidence = []
                if language == "en":
                    competition_claim = (
                        f"Direct local competition and close alternatives for {profile['title']} "
                        f"in {profile['region']} are not confirmed."
                    )
                else:
                    competition_claim = (
                        f"La concurrence directe locale et les alternatives proches de "
                        f"{profile['title']} dans {profile['region']} ne sont pas confirmées."
                    )

        if language == "en":
            problem_status = "sourced" if problem_evidence else "field_validation_required"
            market_claim = (
                f"Quantitative market evidence and demand signals support the market opportunity "
                f"for {profile['title']}."
                if market_is_sourced
                else f"The market size and demand for {profile['title']} are not sufficiently "
                     "verified to justify execution without field validation."
            )
            claims = [
                self._claim(
                    claim=f"The problem described for {profile['title']} is relevant to the target users.",
                    category="problem",
                    status=problem_status,
                    confidence="medium" if problem_evidence else "low",
                    correction="Validate frequency, severity and urgency with real target users.",
                    language=language,
                    evidence=problem_evidence[:3],
                ),
                self._claim(
                    claim=f"The proposed solution can solve the stated problem for {profile['title']}.",
                    category="solution",
                    status="estimated",
                    confidence="medium" if solution_evidence else "low",
                    correction="Test a reduced MVP with real users; comparable products prove feasibility, not product-market fit.",
                    language=language,
                    evidence=solution_evidence[:3],
                ),
                self._claim(
                    claim=market_claim,
                    category="market_size",
                    status="sourced" if market_is_sourced else "field_validation_required",
                    confidence="medium" if market_is_sourced else "low",
                    correction="Confirm addressable market size, active demand and reachable customer count with category-compatible data.",
                    language=language,
                    evidence=(
                        qualified_market_size + qualified_market_demand
                        if market_is_sourced
                        else market_size_evidence + market_demand_evidence
                    )[:3],
                ),
                self._claim(
                    claim=competition_claim,
                    category="local_competition",
                    status=competition_status,
                    confidence=competition_confidence,
                    correction="Manually verify product functionality, customer segment, geography and current alternatives.",
                    language=language,
                    evidence=competition_evidence,
                ),
                self._claim(
                    claim=f"The financial assumptions for {profile['title']} are realistic.",
                    category="finance",
                    status="field_validation_required",
                    confidence="low",
                    correction="Confirm MVP cost, pricing, margins, acquisition cost and willingness to pay with real data.",
                    language=language,
                ),
            ]
        else:
            problem_status = "sourced" if problem_evidence else "field_validation_required"
            market_claim = (
                f"Des données quantitatives de marché et des signaux de demande soutiennent "
                f"l'opportunité de marché de {profile['title']}."
                if market_is_sourced
                else f"La taille du marché et la demande pour {profile['title']} ne sont pas "
                     "suffisamment vérifiées pour justifier l'exécution sans validation terrain."
            )
            claims = [
                self._claim(
                    claim=f"Le problème décrit pour {profile['title']} est pertinent pour les utilisateurs cibles.",
                    category="problem",
                    status=problem_status,
                    confidence="medium" if problem_evidence else "low",
                    correction="Valider la fréquence, la gravité et l'urgence avec de vrais utilisateurs cibles.",
                    language=language,
                    evidence=problem_evidence[:3],
                ),
                self._claim(
                    claim=f"La solution proposée peut résoudre le problème décrit pour {profile['title']}.",
                    category="solution",
                    status="estimated",
                    confidence="medium" if solution_evidence else "low",
                    correction="Tester un MVP réduit ; des produits comparables prouvent la faisabilité, pas l'adéquation produit-marché.",
                    language=language,
                    evidence=solution_evidence[:3],
                ),
                self._claim(
                    claim=market_claim,
                    category="market_size",
                    status="sourced" if market_is_sourced else "field_validation_required",
                    confidence="medium" if market_is_sourced else "low",
                    correction="Confirmer le marché adressable, la demande active et le nombre de clients atteignables avec des données compatibles.",
                    language=language,
                    evidence=(
                        qualified_market_size + qualified_market_demand
                        if market_is_sourced
                        else market_size_evidence + market_demand_evidence
                    )[:3],
                ),
                self._claim(
                    claim=competition_claim,
                    category="local_competition",
                    status=competition_status,
                    confidence=competition_confidence,
                    correction="Vérifier manuellement les fonctionnalités, la cible, la zone géographique et les alternatives utilisées.",
                    language=language,
                    evidence=competition_evidence,
                ),
                self._claim(
                    claim=f"Les hypothèses financières de {profile['title']} sont réalistes.",
                    category="finance",
                    status="field_validation_required",
                    confidence="low",
                    correction="Confirmer le coût MVP, le prix, les marges, le coût d'acquisition et la volonté de payer.",
                    language=language,
                ),
            ]
        return self._clean_claims(claims)

    def _claims_from_registry(
        self,
        *,
        registry: Dict[str, Any],
        language: str,
        fallback_sources: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Convert the canonical claim registry into public fact-check cards.

        Publication policy:
        - internal estimates never inherit broad market sources;
        - non-confirmed claims show consulted sources separately;
        - recommendations and audit conclusions are not presented as facts;
        - project-derived market framing is labelled as project input;
        - only supporting evidence remains under the Evidence heading.
        """
        source_index = registry.get("source_index") or {}
        if not isinstance(source_index, dict):
            source_index = {}

        sources_by_url = {
            self._safe_text(source.get("url"), "").lower(): dict(source)
            for source in (fallback_sources or [])
            if isinstance(source, dict) and self._safe_text(source.get("url"), "")
        }

        results: List[Dict[str, Any]] = []
        for item in registry.get("claims") or []:
            if not isinstance(item, dict):
                continue

            claim_text = self._safe_text(item.get("claim"), "")
            if not claim_text:
                continue

            path = self._safe_text(item.get("path"), "")
            if path in {"problem", "proposed_solution"}:
                continue
            if path.startswith("market_study.demand_drivers["):
                continue

            raw_status = self._safe_text(item.get("status"), "not_confirmed")
            status = {
                "sourced": "sourced",
                "estimated": "estimated",
                "hypothesis": "estimated",
                "recommendation": "recommendation",
                "audit_conclusion": "audit_conclusion",
                "project_input": "project_input",
                "not_confirmed": "not_confirmed",
                "field_validation_required": "field_validation_required",
                "rejected": "not_confirmed",
            }.get(raw_status, "field_validation_required")
            status = self._status_for_claim_text(
                status=status,
                claim_text=claim_text,
            )

            confidence = self._safe_text(item.get("confidence"), "low").lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            source_rows: List[Dict[str, Any]] = []
            for source_id in item.get("source_ids") or []:
                source = source_index.get(source_id)
                if not isinstance(source, dict) or not source.get("url"):
                    continue
                source_row = dict(source)
                canonical = sources_by_url.get(
                    self._safe_text(source_row.get("url"), "").lower()
                )
                if canonical:
                    source_row = self._merge_source_records(
                        canonical,
                        source_row,
                    )
                source_rows.append(source_row)

            category = self._safe_text(item.get("category"), "general")
            evidence = list(source_rows)
            consulted_sources: List[Dict[str, Any]] = []

            if path.startswith("financial_estimation."):
                status = "estimated"
                category = "finance"
                confidence = "low"
                evidence = []
                consulted_sources = []
            elif path == "market_study.local_context":
                status = "recommendation"
                category = "recommendation"
                confidence = "low"
                evidence = []
                consulted_sources = []
            elif path == "market_study.local_feasibility":
                status = "audit_conclusion"
                category = "evidence_audit"
                confidence = "low"
                evidence = []
                consulted_sources = list(source_rows)
            elif path == "market_study.market_overview":
                status = "project_input"
                category = "project_input"
                confidence = "medium"
                evidence = []
                consulted_sources = []
            elif path in {
                "market_study.global_potential",
                "market_study.global_market_assessment",
            } and status != "sourced":
                evidence = []
                consulted_sources = list(source_rows)
            elif status in {
                "not_confirmed",
                "field_validation_required",
            }:
                # Keep the legacy evidence array for API compatibility, but
                # explicitly mark it as consulted and insufficient. The
                # frontend renders these cards under a separate heading.
                evidence = list(source_rows)
                consulted_sources = list(source_rows)
            elif status in {"recommendation", "audit_conclusion", "project_input"}:
                evidence = []
                consulted_sources = list(source_rows) if status == "audit_conclusion" else []

            correction = self._registry_correction(
                path=path,
                category=category,
                status=status,
                language=language,
            )
            card = self._claim(
                claim=claim_text,
                category=category,
                status=status,
                confidence=confidence,
                correction=correction,
                language=language,
                evidence=evidence,
                consulted_sources=consulted_sources,
            )
            card.update(
                {
                    "claim_id": self._safe_text(item.get("claim_id"), ""),
                    "path": path,
                    "is_quantitative": bool(item.get("is_quantitative")),
                    "evidence_quality": self._safe_text(
                        item.get("evidence_quality"),
                        "low",
                    ),
                    "evidence_kind": (
                        "consulted_insufficient"
                        if status in {
                            "not_confirmed",
                            "field_validation_required",
                        }
                        else "supporting"
                    ),
                }
            )
            results.append(card)

        priority_prefixes = (
            "market_study.",
            "financial_estimation.",
            "competitive_analysis.",
            "improvement_suggestions[",
        )
        results.sort(
            key=lambda claim: (
                0 if str(claim.get("path") or "").startswith(priority_prefixes) else 1,
                0 if claim.get("is_quantitative") else 1,
                str(claim.get("path") or ""),
            )
        )
        return results[:15]

    def _registry_correction(
        self,
        *,
        path: str,
        category: str,
        status: str,
        language: str,
    ) -> str:
        if status == "sourced":
            return (
                "Vérifier la méthodologie, la date et la compatibilité géographique de la source."
                if language != "en"
                else "Check the source methodology, date and geographic compatibility."
            )
        if status == "recommendation":
            return (
                "Tester cette recommandation pendant un pilote limité avant de l’intégrer au plan définitif."
                if language != "en"
                else "Test this recommendation in a bounded pilot before adding it to the final plan."
            )
        if status == "audit_conclusion":
            return (
                "Cette conclusion décrit la limite des preuves disponibles ; elle ne constitue pas une preuve de demande."
                if language != "en"
                else "This conclusion describes the limits of the available evidence; it is not proof of demand."
            )
        if status == "project_input":
            return (
                "Cette formulation vient du contexte du projet et doit être confirmée par des observations terrain."
                if language != "en"
                else "This statement comes from the project context and must be confirmed through field observation."
            )

        normalized = f"{path} {category}".lower()
        if "financial" in normalized or "finance" in normalized or "pricing" in normalized:
            return (
                "Confirmer cette estimation avec des devis, coûts unitaires, hypothèses et tests de prix documentés."
                if language != "en"
                else "Confirm this estimate with quotes, unit costs, documented assumptions and pricing tests."
            )
        if "local" in normalized or "market" in normalized:
            return (
                "Valider ce signal avec une source locale officielle ou indépendante et des entretiens terrain."
                if language != "en"
                else "Validate this signal with an official or independent local source and field interviews."
            )
        if "technology" in normalized or "solution" in normalized:
            return (
                "Un benchmark prouve une possibilité technique, pas l’adoption ni la performance du projet ; tester le MVP."
                if language != "en"
                else "A benchmark shows technical possibility, not project adoption or performance; test the MVP."
            )
        return (
            "Traiter cette affirmation comme une hypothèse jusqu’à validation directe."
            if language != "en"
            else "Treat this claim as a hypothesis until directly validated."
        )

    def _merge_claim_sets(
        self,
        base_claims: List[Dict[str, Any]],
        registry_claims: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen = set()
        for item in list(base_claims or []) + list(registry_claims or []):
            if not isinstance(item, dict):
                continue
            text = self._safe_text(item.get("claim"), "")
            if not text:
                continue
            key = " ".join(text.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    def _is_qualified_market_evidence(
        self,
        source: Dict[str, Any],
    ) -> bool:
        quality = self._safe_text(
            source.get("evidence_quality"),
            "",
        ).lower()
        if quality == "high":
            return True
        if quality == "medium" and bool(source.get("methodology_visible")):
            return True

        source_type = self._safe_text(source.get("source_type"), "").lower()
        if source_type in {"regulation", "official_evidence"}:
            return True

        try:
            domain = urlparse(self._safe_text(source.get("url"), "")).netloc.lower()
        except Exception:
            domain = ""
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return True
        if domain.endswith(".org") and bool(source.get("methodology_visible")):
            return True

        return False

    def _claim(
        self,
        claim: str,
        category: str,
        status: str,
        confidence: str,
        correction: str,
        language: str,
        evidence: List[Dict[str, Any]] | None = None,
        consulted_sources: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        clean_claim = self._safe_text(claim, "")
        clean_correction = self._safe_text(correction, "")

        return {
            "claim": clean_claim,
            "category": self._safe_text(category, "general"),
            "status": self._safe_text(status, "not_confirmed"),
            "public_status": self._public_status_label(status, language),
            "confidence": self._safe_text(confidence, "low"),
            "public_confidence": self._public_confidence_label(
                confidence,
                language,
            ),
            "evidence": [
                self._compact_evidence(source)
                for source in self._deduplicate_source_list(
                    [item for item in (evidence or []) if isinstance(item, dict)]
                )[:3]
            ],
            "consulted_sources": [
                self._compact_evidence(source)
                for source in self._deduplicate_source_list(
                    [
                        item
                        for item in (consulted_sources or [])
                        if isinstance(item, dict)
                    ]
                )[:3]
            ],
            "correction": clean_correction,
        }

    # ========================================================
    # Supported / uncertain / warnings / validation
    # ========================================================

    def _supported_claims(
        self,
        profile: Dict[str, Any],
        relevant_sources: List[Dict[str, Any]],
        language: str,
    ) -> List[str]:
        if not relevant_sources:
            if language == "en":
                return [
                    f"No strong claim about {profile['title']} should be considered "
                    "fully verified without relevant sources."
                ]

            return [
                f"Aucune affirmation forte sur {profile['title']} ne doit être "
                "considérée comme totalement vérifiée sans source pertinente."
            ]

        groups = self._build_evidence_groups(relevant_sources)

        supported: List[str] = []

        if groups["local_competitors"]:
            if language == "en":
                supported.append(
                    f"{len(groups['local_competitors'])} local competitor or close "
                    "solution source(s) were retained."
                )
            else:
                supported.append(
                    f"{len(groups['local_competitors'])} source(s) de concurrent "
                    "ou de solution proche locale ont été retenues."
                )

        benchmark_count = (
            len(groups["regional_benchmarks"])
            + len(groups["international_benchmarks"])
        )

        if benchmark_count:
            if language == "en":
                supported.append(
                    f"{benchmark_count} regional or international benchmark "
                    "source(s) were retained."
                )
            else:
                supported.append(
                    f"{benchmark_count} source(s) de benchmark régional ou "
                    "international ont été retenues."
                )

        if groups["market_size_evidence"]:
            if language == "en":
                supported.append(
                    f"{len(groups['market_size_evidence'])} market evidence source(s) "
                    "were retained."
                )
            else:
                supported.append(
                    f"{len(groups['market_size_evidence'])} source(s) de preuve marché "
                    "ont été retenues."
                )

        if language == "en":
            supported.append(
                "Retained sources support only the claims matching their evidence "
                "category; field validation remains required."
            )
        else:
            supported.append(
                "Les sources retenues soutiennent uniquement les affirmations "
                "correspondant à leur catégorie de preuve ; une validation terrain "
                "reste nécessaire."
            )

        return self._unique(supported)

    def _uncertain_claims(
        self,
        profile: Dict[str, Any],
        language: str,
    ) -> List[str]:
        if language == "en":
            uncertain = [
                f"The market potential of {profile['title']} still needs confirmation through reliable external data.",
                "Willingness to pay from the target market is not automatically proven.",
                f"The local competition level in {profile['region']} must be manually checked.",
                "Financial assumptions must be validated with real costs and customer pricing tests.",
            ]

            if profile["data_confidence"] in {"low", "medium"}:
                uncertain.append(
                    f"The market study indicates {profile['data_confidence']} confidence, so conclusions must remain cautious."
                )

            return self._unique(uncertain)

        uncertain = [
            f"Le potentiel de marché de {profile['title']} reste à confirmer par des données externes fiables.",
            "La volonté de payer de la cible n’est pas prouvée automatiquement.",
            f"Le niveau de concurrence locale dans {profile['region']} doit être vérifié manuellement.",
            "Les hypothèses financières doivent être validées avec des coûts réels et des tests de prix.",
        ]

        if profile["data_confidence"] in {"low", "medium"}:
            uncertain.append(
                f"L’étude de marché indique une confiance {profile['data_confidence']}, donc les conclusions doivent rester prudentes."
            )

        return self._unique(uncertain)

    def _warnings(
        self,
        profile: Dict[str, Any],
        source_count: int,
        relevant_sources: List[Dict[str, Any]],
        language: str,
    ) -> List[str]:
        warnings: List[str] = []
        groups = self._build_evidence_groups(relevant_sources)

        if language == "en":
            if source_count == 0:
                warnings.append(
                    f"No external source is available to verify {profile['title']}."
                )

            if source_count > 0 and not relevant_sources:
                warnings.append(
                    f"Sources exist, but none can be used as a retained public "
                    f"evidence source for {profile['title']}."
                )

            if relevant_sources and not groups["local_competitors"]:
                warnings.append(
                    "No verified direct local competitor was established. "
                    "Regional or international benchmarks do not prove local competition."
                )

            if not groups["market_size_evidence"]:
                warnings.append(
                    "No retained market-evidence source directly supports the market-size claim."
                )

            if profile["crawler_confidence"] == "low":
                warnings.append("Dynamic web source confidence is low.")

            if profile["competitive_confidence"] == "low":
                warnings.append("Competitive analysis must be manually verified.")

            if profile["financial_risk_level"] == "high":
                warnings.append(
                    "Financial risk is high and requires cost and pricing testing."
                )

            if not warnings:
                warnings.append(
                    "No automatic blocking signal was detected, but field validation "
                    "remains required."
                )

            return self._unique(warnings)

        if source_count == 0:
            warnings.append(
                f"Aucune source externe n'est disponible pour vérifier "
                f"{profile['title']}."
            )

        if source_count > 0 and not relevant_sources:
            warnings.append(
                f"Des sources existent, mais aucune ne peut être utilisée comme "
                f"preuve publique retenue pour {profile['title']}."
            )

        if relevant_sources and not groups["local_competitors"]:
            warnings.append(
                "Aucun concurrent local direct vérifié n'a été établi. "
                "Les benchmarks régionaux ou internationaux ne prouvent pas "
                "la concurrence locale."
            )

        if not groups["market_size_evidence"]:
            warnings.append(
                "Aucune source de preuve marché retenue ne soutient directement "
                "l'affirmation sur la taille du marché."
            )

        if profile["crawler_confidence"] == "low":
            warnings.append(
                "La confiance des sources web dynamiques est faible."
            )

        if profile["competitive_confidence"] == "low":
            warnings.append(
                "L'analyse concurrentielle doit être vérifiée manuellement."
            )

        if profile["financial_risk_level"] == "high":
            warnings.append(
                "Le risque financier est élevé et nécessite un test coût/prix."
            )

        if not warnings:
            warnings.append(
                "Aucun signal bloquant automatique n'a été détecté, mais une "
                "validation terrain reste obligatoire."
            )

        return self._unique(warnings)

    def _validation_plan(
        self,
        profile: Dict[str, Any],
        language: str,
    ) -> List[str]:
        if language == "en":
            return [
                f"Manually verify at least 5 relevant sources for {profile['title']}.",
                "Interview real users matching the target customer profile.",
                f"Test a simple MVP version in the {profile['region']} region.",
                "Compare alternatives actually used by the target users.",
                "Validate pricing, cost and usage frequency before final decision.",
            ]

        return [
            f"Vérifier manuellement au moins 5 sources pertinentes pour {profile['title']}.",
            "Interroger de vrais utilisateurs correspondant à la cible.",
            f"Tester une version simple du MVP dans la région {profile['region']}.",
            "Comparer les alternatives réellement utilisées par la cible.",
            "Valider le prix, le coût et la fréquence d’usage avant décision finale.",
        ]

    def _limitations(
        self,
        profile: Dict[str, Any],
        source_count: int,
        relevant_sources: List[Dict[str, Any]],
        language: str,
    ) -> List[str]:
        groups = self._build_evidence_groups(relevant_sources)

        if language == "en":
            limitations = [
                "This fact-checking report does not replace field validation.",
                "Market size, pricing, competitor positioning and willingness to "
                "pay must be confirmed with category-appropriate evidence.",
            ]

            if source_count == 0:
                limitations.append(
                    "No external source was available for automatic verification."
                )

            if source_count > 0 and not relevant_sources:
                limitations.append(
                    "External sources were found, but no public validated source "
                    "could be retained by the Fact Checker."
                )

            if relevant_sources and not groups["local_competitors"]:
                limitations.append(
                    "Retained benchmarks do not establish the existence or absence "
                    "of direct local competitors."
                )

            if not groups["market_size_evidence"]:
                limitations.append(
                    "No retained source directly validates market size."
                )

            return self._unique(limitations)

        limitations = [
            "Cette vérification factuelle ne remplace pas une validation terrain.",
            "La taille du marché, le prix, le positionnement concurrentiel et la "
            "volonté de payer doivent être confirmés avec des preuves adaptées "
            "à chaque catégorie.",
        ]

        if source_count == 0:
            limitations.append(
                "Aucune source externe n'était disponible pour la vérification automatique."
            )

        if source_count > 0 and not relevant_sources:
            limitations.append(
                "Des sources externes ont été trouvées, mais aucune source publique "
                "validée n'a pu être retenue par le Fact Checker."
            )

        if relevant_sources and not groups["local_competitors"]:
            limitations.append(
                "Les benchmarks retenus n'établissent ni l'existence ni l'absence "
                "de concurrents locaux directs."
            )

        if not groups["market_size_evidence"]:
            limitations.append(
                "Aucune source retenue ne valide directement la taille du marché."
            )

        return self._unique(limitations)

    # ========================================================
    # Fallback
    # ========================================================

    def _build_fallback_fact_check_report(
        self,
        state: Dict[str, Any],
        language: str,
        error_message: str | None = None,
    ) -> Dict[str, Any]:
        project_context: Dict[str, Any] = {}

        try:
            project_context = self._get_project_context(state)
        except Exception:
            project_context = {}

        title = self._safe_text(
            project_context.get("project_name")
            or project_context.get("title")
            or state.get("project_name")
            or state.get("title")
            or (state.get("project") or {}).get("title"),
            "the project" if language == "en" else "le projet",
        )

        if language == "en":
            summary = (
                f"The fact-checking module could not fully verify all claims for {title}. "
                "The analysis remains usable, but market size, pricing, competitors, costs and customer willingness to pay "
                "must be validated with reliable sources and field interviews."
            )

            warnings = [
                "Automatic fact-checking was not fully completed.",
                "Some claims may be based on strategic estimation rather than verified sources.",
                "Market size and financial assumptions require manual validation.",
                "Competitor analysis must be confirmed with source-based research.",
                "Customer willingness to pay must be tested with real target users.",
            ]

            recommended_validation = [
                "Interview users matching the target customer profile.",
                "Manually verify direct and indirect competitors.",
                "Confirm MVP cost with real supplier or development quotes.",
                "Validate pricing through customer discovery.",
                "Replace assumptions with reliable sector or regional data.",
            ]

            limitations = [
                "Automatic fact-checking used a safe fallback.",
                "The report should not be treated as investment-ready without field validation.",
            ]

            claims = [
                self._claim(
                    claim="The identified problem is relevant to the target users.",
                    category="problem",
                    status="field_validation_required",
                    confidence="medium",
                    correction="Validate the problem through interviews with real target users.",
                    language=language,
                ),
                self._claim(
                    claim="The proposed solution can solve the stated problem.",
                    category="solution",
                    status="estimated",
                    confidence="medium",
                    correction="Test a reduced MVP before building a full product.",
                    language=language,
                ),
                self._claim(
                    claim="The business model can be profitable.",
                    category="finance",
                    status="not_confirmed",
                    confidence="low",
                    correction="Confirm costs, pricing and willingness to pay with real users.",
                    language=language,
                ),
            ]

            method = "fallback_fact_check"

        else:
            summary = (
                f"Le module de vérification n’a pas pu confirmer toutes les affirmations pour {title}. "
                "L’analyse reste exploitable, mais la taille du marché, les prix, les concurrents, les coûts "
                "et la volonté de payer doivent être validés avec des sources fiables et des entretiens terrain."
            )

            warnings = [
                "La vérification automatique n’a pas été entièrement complétée.",
                "Certaines affirmations peuvent être basées sur une estimation stratégique plutôt que sur des sources vérifiées.",
                "La taille du marché et les hypothèses financières nécessitent une validation manuelle.",
                "L’analyse concurrentielle doit être confirmée par une recherche sourcée.",
                "La volonté de payer doit être testée avec de vrais utilisateurs cibles.",
            ]

            recommended_validation = [
                "Interroger des utilisateurs correspondant à la cible.",
                "Vérifier manuellement les concurrents directs et indirects.",
                "Confirmer le coût MVP avec des devis réels.",
                "Valider le prix avec des entretiens clients.",
                "Remplacer les hypothèses par des données sectorielles ou régionales fiables.",
            ]

            limitations = [
                "La vérification automatique a utilisé un fallback sécurisé.",
                "Le rapport ne doit pas être considéré comme prêt pour investissement sans validation terrain.",
            ]

            claims = [
                self._claim(
                    claim="Le problème identifié est pertinent pour les utilisateurs cibles.",
                    category="problem",
                    status="field_validation_required",
                    confidence="medium",
                    correction="Valider le problème avec des entretiens auprès de vrais utilisateurs cibles.",
                    language=language,
                ),
                self._claim(
                    claim="La solution proposée peut résoudre le problème décrit.",
                    category="solution",
                    status="estimated",
                    confidence="medium",
                    correction="Tester un MVP réduit avant de construire le produit complet.",
                    language=language,
                ),
                self._claim(
                    claim="Le modèle économique peut être rentable.",
                    category="finance",
                    status="not_confirmed",
                    confidence="low",
                    correction="Confirmer les coûts, le prix et la volonté de payer avec de vrais utilisateurs.",
                    language=language,
                ),
            ]

            method = "verification_fallback"

        return {
            "format": "fact_checker_v4_professional_context_locked",
            "status": "fallback_completed",
            "method": method,
            "summary": summary,
            "fact_check_summary": summary,
            "output_language": language,
            "context_locked": True,
            "confidence_level": "low",
            "global_confidence": "low",
            "source_count": 0,
            "relevant_source_count": 0,
            "source_summary": {
                "total_sources": 0,
                "sources_with_url": 0,
                "verified_competitors": 0,
                "relevant_sources": 0,
                "source_confidence": "low",
            },
            "claims": claims,
            "claims_to_verify": [claim["claim"] for claim in claims],
            "supported_claims": [],
            "uncertain_claims": [claim["claim"] for claim in claims],
            "warnings": warnings,
            "red_flags": warnings,
            "recommended_next_checks": recommended_validation,
            "recommended_validation": recommended_validation,
            "limitations": limitations,
            "retained_sources": [],
            "error_handled": True,
            "internal_error": error_message,
        }

    # ========================================================
    # Source collection / filtering
    # ========================================================

    def _collect_sources(self, analysis_data: Any) -> List[Dict[str, Any]]:
        """
        Collecte uniquement les sources issues des contrats publics connus.

        L'ancien parcours récursif de tout analysis_data pouvait :
        - collecter des URLs qui n'étaient pas des sources ;
        - perdre matched_strong_terms et les indicateurs métier ;
        - dédupliquer trop tôt une source enrichie au profit d'une carte pauvre.

        La nouvelle version privilégie les tableaux canoniques.
        """
        if not isinstance(analysis_data, dict):
            return []

        collected: Dict[str, Dict[str, Any]] = {}

        for path in self.PUBLIC_SOURCE_PATHS:
            for item in self._get_nested_list(analysis_data, path):
                normalized = self._normalize_source(
                    item=item,
                    source_path=".".join(path),
                    upstream_validated=True,
                )

                if not normalized:
                    continue

                signature = self._source_signature(normalized)
                existing = collected.get(signature)

                if existing is None:
                    collected[signature] = normalized
                else:
                    collected[signature] = self._merge_source_records(
                        existing,
                        normalized,
                    )

        # Cartes concurrentielles : fallback seulement.
        for path in self.PUBLIC_CARD_PATHS:
            for item in self._get_nested_list(analysis_data, path):
                normalized = self._normalize_source(
                    item=item,
                    source_path=".".join(path),
                    upstream_validated=True,
                )

                if not normalized:
                    continue

                signature = self._source_signature(normalized)
                existing = collected.get(signature)

                if existing is None:
                    collected[signature] = normalized
                else:
                    collected[signature] = self._merge_source_records(
                        existing,
                        normalized,
                    )

        sources = list(collected.values())
        sources.sort(
            key=lambda source: float(
                source.get("source_relevance_score") or 0
            ),
            reverse=True,
        )

        logger.info(
            "[FactCheckerAgent][SourceCollection] canonical_sources=%s | titles=%s",
            len(sources),
            [source.get("title") for source in sources[:8]],
        )

        return sources

    def _filter_relevant_sources(
        self,
        sources: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Conserve les sources publiques déjà validées en amont.

        Important :
        le Fact Checker ne rappelle pas domain_integrity_guard.filter_sources()
        sur les sources canoniques. Ce second filtrage était la cause du passage
        de 1 source retenue à 0 source pertinente.
        """
        if not sources:
            return []

        context_terms = self._context_terms(project_context)
        cleaned: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        for source in sources:
            if not isinstance(source, dict):
                continue

            if source.get("rejected") is True:
                continue

            if source.get("internal_only") is True:
                continue

            if (
                "public_display" in source
                and source.get("public_display") is False
            ):
                continue

            source_type = self._safe_text(
                source.get("source_type"),
                "",
            ).lower()

            if source_type == "irrelevant":
                continue

            url = self._safe_text(source.get("url"), "")

            if not self._valid_http_url(url):
                continue

            normalized_url = url.lower()

            if normalized_url in seen_urls:
                continue

            upstream_score = self._safe_float(
                source.get("source_relevance_score"),
                0.0,
            )
            deterministic_score = self._source_relevance_score(
                source,
                context_terms,
            )

            if source.get("upstream_validated") is True:
                # La décision de publication a déjà été prise en amont.
                final_score = max(
                    upstream_score,
                    deterministic_score,
                    0.20,
                )
            else:
                # Compatibilité avec d'anciennes structures non validées.
                try:
                    legacy_filtered = domain_integrity_guard.filter_sources(
                        sources=[source],
                        project_context=project_context,
                        min_overlap=1,
                    )
                except Exception:
                    legacy_filtered = [source]

                if not legacy_filtered:
                    continue

                final_score = max(
                    upstream_score,
                    deterministic_score,
                )

                if final_score < 0.20:
                    continue

            seen_urls.add(normalized_url)

            cleaned.append(
                {
                    **source,
                    "source_relevance_score": round(
                        max(0.0, min(1.0, final_score)),
                        2,
                    ),
                }
            )

        cleaned.sort(
            key=lambda item: float(
                item.get("source_relevance_score") or 0
            ),
            reverse=True,
        )

        logger.info(
            "[FactCheckerAgent][SourceFilter] input=%s | relevant=%s | titles=%s",
            len(sources),
            len(cleaned),
            [source.get("title") for source in cleaned[:8]],
        )

        return cleaned

    def _source_relevance_score(
        self,
        source: Dict[str, Any],
        context_terms: List[str],
    ) -> float:
        """
        Score secondaire utilisé pour l'audit et les anciennes structures.

        Le score validé en amont reste prioritaire pour les sources canoniques.
        """
        upstream_score = self._safe_float(
            source.get("source_relevance_score"),
            0.0,
        )

        if not context_terms:
            return max(upstream_score, 0.30)

        title = self._safe_text(source.get("title"), "")
        snippet = self._safe_text(
            source.get("snippet")
            or source.get("why_relevant"),
            "",
        )
        source_type = self._safe_text(source.get("source_type"), "")
        matched_terms = self._safe_list(
            source.get("matched_project_terms")
            or source.get("matched_strong_terms")
        )

        source_text = (
            f"{title} {snippet} {source_type} {' '.join(matched_terms)}"
        ).lower()

        if not source_text.strip():
            return upstream_score

        weak_terms = {
            "app",
            "application",
            "platform",
            "digital",
            "mobile",
            "service",
            "solution",
            "tool",
            "business",
            "startup",
            "online",
            "website",
            "dashboard",
            "management",
            "software",
            "saas",
            "create",
            "help",
            "short",
            "lite",
            "market",
            "industry",
            "product",
        }

        strong_matches = 0
        weak_matches = 0

        for term in context_terms:
            clean_term = str(term or "").strip().lower()

            if len(clean_term) < 3:
                continue

            if clean_term in weak_terms:
                if clean_term in source_text:
                    weak_matches += 1
                continue

            if clean_term in source_text:
                strong_matches += 1

        score = 0.0

        if strong_matches >= 5:
            score += 0.80
        elif strong_matches >= 3:
            score += 0.65
        elif strong_matches >= 2:
            score += 0.45
        elif strong_matches == 1:
            score += 0.25

        if weak_matches >= 3:
            score += 0.08
        elif weak_matches >= 1:
            score += 0.04

        if source.get("url"):
            score += 0.05

        if source.get("snippet") or source.get("why_relevant"):
            score += 0.05

        return max(
            upstream_score,
            max(0.0, min(1.0, score)),
        )

    def _context_terms(self, project_context: Dict[str, Any]) -> List[str]:
        raw_values: List[Any] = [
            project_context.get("project_name"),
            project_context.get("title"),
            project_context.get("industry"),
            project_context.get("market_region"),
            project_context.get("target_region"),
            project_context.get("domain_label"),
            project_context.get("main_use_case"),
            project_context.get("solution_type"),
            project_context.get("core_problem"),
            project_context.get("anchor_terms"),
            project_context.get("strong_keywords"),
            project_context.get("must_match_terms"),
            project_context.get("target_users"),
            project_context.get("target_market"),
        ]

        terms: List[str] = []

        for value in raw_values:
            terms.extend(self._safe_list(value))

        expanded: List[str] = []

        for term in terms:
            clean = str(term or "").strip()

            if not clean:
                continue

            expanded.append(clean)

            for piece in clean.replace("/", " ").replace("-", " ").split():
                if len(piece) >= 4:
                    expanded.append(piece)

        return self._unique(expanded)[:40]


    def _build_evidence_groups(
        self,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        groups: Dict[str, List[Dict[str, Any]]] = {
            "local_competitors": [],
            "local_adjacent_solutions": [],
            "regional_benchmarks": [],
            "international_benchmarks": [],
            "market_size_evidence": [],
            "market_demand_evidence": [],
            "problem_evidence": [],
            "solution_evidence": [],
            "pricing_evidence": [],
            "regulatory_evidence": [],
            "sector_context": [],
            "market_evidence": [],
            "other_relevant": [],
        }

        for source in sources:
            source_type = self._safe_text(source.get("source_type"), "").lower()
            source_role = self._safe_text(source.get("source_role"), "").lower()
            canonical = self._safe_text(source.get("canonical_category"), "").lower()
            region = self._safe_text(source.get("region_match"), "unknown").lower()
            categories = {
                self._safe_text(value, "").lower()
                for value in self._safe_list(source.get("evidence_categories"))
                if self._safe_text(value, "")
            }

            role_blob = " ".join((source_type, source_role, canonical))
            if "technology" in role_blob:
                categories.update({"technology_benchmark", "solution_benchmark"})
            if "adjacent" in role_blob:
                categories.add("solution_benchmark")
            if "market" in role_blob:
                categories.add("sector_context")
            if "local_market" in role_blob:
                categories.add("local_market_signal")
            if "direct_competitor" in role_blob:
                categories.add("competitor_product")
            if source.get("pricing_found") and source_type in {
                "pricing_page",
                "competitor",
                "adjacent_solution",
            }:
                categories.add("pricing")

            if source_type in {"market_article", "market_evidence"}:
                categories.discard("pricing")
                categories.discard("pricing_signal")

            if not categories:
                title_reason = self._safe_text(
                    f"{source.get('title', '')} {source.get('why_relevant', '')} {source.get('snippet', '')}",
                    "",
                ).lower()
                if source.get("is_direct_competitor") is True:
                    categories.update({"competitor_product", "solution_benchmark"})
                if source_type == "pricing_page":
                    categories.add("pricing")
                if source_type == "regulation":
                    categories.add("regulation")
                if source_type in {"market_article", "market_evidence"}:
                    categories.add("sector_context")
                    if any(term in title_reason for term in ("market size", "cagr", "forecast", "taille du marché", "taille du marche")):
                        categories.add("market_size_claim")
                    if any(term in title_reason for term in ("survey", "adoption", "demand", "preference", "enquête", "enquete", "demande")):
                        categories.add("market_demand_claim")
                    if any(term in title_reason for term in ("challenge", "disease", "problem", "risk", "maladie", "problème", "probleme")):
                        categories.add("problem_context")

            direct = bool(source.get("is_direct_competitor")) or "direct_competitor" in role_blob
            product_like = (
                source_type in self.COMPETITOR_SOURCE_TYPES
                or bool(categories & self.SOLUTION_CATEGORIES)
            )
            if direct and region == "local":
                groups["local_competitors"].append(source)
            elif product_like and categories & self.SOLUTION_CATEGORIES:
                if region == "local":
                    groups["local_adjacent_solutions"].append(source)
                elif region == "regional":
                    groups["regional_benchmarks"].append(source)
                else:
                    groups["international_benchmarks"].append(source)

            if categories & self.MARKET_SIZE_CATEGORIES:
                groups["market_size_evidence"].append(source)
            if categories & self.MARKET_DEMAND_CATEGORIES:
                groups["market_demand_evidence"].append(source)
            if categories & self.PROBLEM_CATEGORIES:
                groups["problem_evidence"].append(source)
            if categories & self.SOLUTION_CATEGORIES:
                groups["solution_evidence"].append(source)
            if categories & self.PRICING_CATEGORIES:
                groups["pricing_evidence"].append(source)
            if categories & self.REGULATION_CATEGORIES:
                groups["regulatory_evidence"].append(source)
            if categories & {"sector_context", "regional_context", "local_market_signal"}:
                groups["sector_context"].append(source)

            if categories & (
                self.MARKET_SIZE_CATEGORIES
                | self.MARKET_DEMAND_CATEGORIES
                | {"sector_context", "regional_context", "local_market_signal"}
            ):
                groups["market_evidence"].append(source)
            if not categories:
                groups["other_relevant"].append(source)

        for key, values in groups.items():
            groups[key] = self._deduplicate_source_list(values)
        return groups

    def _deduplicate_source_list(
        self,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()
        for source in sources:
            key = self._source_signature(source)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(source)
        return result

    def _status_for_claim_text(
        self,
        *,
        status: str,
        claim_text: str,
    ) -> str:
        normalized = " ".join(
            self._safe_text(claim_text, "").casefold().split()
        )
        absence_markers = (
            "non confirmé",
            "non confirmée",
            "ne permettent pas de quantifier",
            "ne permet pas de quantifier",
            "données insuffisantes",
            "not confirmed",
            "cannot be quantified",
            "do not allow quantification",
            "insufficient data",
            "no compatible evidence",
        )
        if any(marker in normalized for marker in absence_markers):
            return "not_confirmed"
        return status

    def _evidence_title(self, source: Dict[str, Any]) -> str:
        generic = {
            "",
            "source",
            "external source",
            "source externe",
            "evidence source",
            "source de preuve",
        }
        for key in ("title", "source_title", "name", "vendor_name"):
            candidate = self._safe_text(source.get(key), "")
            if candidate and candidate.casefold() not in generic:
                return candidate
        try:
            domain = urlparse(self._safe_text(source.get("url"), "")).netloc
        except Exception:
            domain = ""
        domain = domain.lower().removeprefix("www.")
        return domain or "Source de preuve"

    def _compact_evidence(
        self,
        source: Dict[str, Any],
    ) -> Dict[str, Any]:
        best_title = self._evidence_title(source)
        return {
            "display_title": best_title,
            "title": best_title,
            "source_title": best_title,
            "name": best_title,
            "url": self._safe_text(source.get("url"), ""),
            "source_type": self._safe_text(source.get("source_type"), "source"),
            "region_match": self._safe_text(source.get("region_match"), "unknown"),
            "confidence": self._safe_text(source.get("confidence"), "low"),
            "evidence_quality": self._safe_text(source.get("evidence_quality"), "low"),
            "methodology_visible": bool(source.get("methodology_visible")),
            "source_role": self._safe_text(source.get("source_role"), ""),
            "canonical_category": self._safe_text(source.get("canonical_category"), ""),
            "source_relevance_score": round(
                self._safe_float(source.get("source_relevance_score"), 0.0),
                2,
            ),
            "why_relevant": self._safe_text(
                source.get("why_relevant") or source.get("snippet"),
                "",
            ),
            "evidence_categories": self._safe_list(source.get("evidence_categories")),
            "is_direct_competitor": bool(source.get("is_direct_competitor")),
        }

    def _clean_claims(
        self,
        claims: Any,
    ) -> List[Dict[str, Any]]:
        if not isinstance(claims, list):
            return []

        cleaned: List[Dict[str, Any]] = []
        seen = set()

        for item in claims:
            if not isinstance(item, dict):
                continue

            claim_text = self._safe_text(
                item.get("claim"),
                "",
            )

            # Une affirmation vide ne doit jamais atteindre le frontend.
            if not claim_text:
                continue

            key = claim_text.lower()

            if key in seen:
                continue

            seen.add(key)

            evidence = item.get("evidence")
            consulted = item.get("consulted_sources")
            clean_evidence: List[Dict[str, Any]] = []
            clean_consulted: List[Dict[str, Any]] = []

            if isinstance(evidence, list):
                for source in evidence:
                    if not isinstance(source, dict):
                        continue
                    compact = self._compact_evidence(source)
                    if compact.get("url"):
                        clean_evidence.append(compact)

            if isinstance(consulted, list):
                for source in consulted:
                    if not isinstance(source, dict):
                        continue
                    compact = self._compact_evidence(source)
                    if compact.get("url"):
                        clean_consulted.append(compact)

            normalized_status = self._status_for_claim_text(
                status=self._safe_text(
                    item.get("status"),
                    "not_confirmed",
                ),
                claim_text=claim_text,
            )
            path = self._safe_text(item.get("path"), "")

            if normalized_status in {
                "not_confirmed",
                "field_validation_required",
            }:
                clean_consulted.extend(clean_evidence)

            if path.startswith("financial_estimation."):
                clean_evidence = []
                clean_consulted = []

            cleaned.append(
                {
                    **item,
                    "claim": claim_text,
                    "category": self._safe_text(
                        item.get("category"),
                        "general",
                    ),
                    "status": normalized_status,
                    "confidence": self._safe_text(
                        item.get("confidence"),
                        "low",
                    ),
                    "correction": self._safe_text(
                        item.get("correction"),
                        "",
                    ),
                    "evidence": self._deduplicate_source_list(clean_evidence)[:3],
                    "consulted_sources": self._deduplicate_source_list(
                        clean_consulted
                    )[:3],
                    "evidence_kind": (
                        "consulted_insufficient"
                        if normalized_status in {
                            "not_confirmed",
                            "field_validation_required",
                        }
                        else self._safe_text(
                            item.get("evidence_kind"),
                            "supporting",
                        )
                    ),
                }
            )

        return cleaned

    def _repair_public_report(
        self,
        result: Dict[str, Any],
        fallback: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        """
        Répare le contrat public après un éventuel sanitizer générique.

        Champs restaurés depuis le rapport déterministe :
        - sources publiques validées ;
        - source_summary et compteurs ;
        - affirmation manquante ou vidée ;
        - labels publics nécessaires au frontend.
        """
        result = dict(result or {})
        fallback = dict(fallback or {})

        fallback_claims = self._clean_claims(
            fallback.get("claims")
        )
        result_claims = self._clean_claims(
            result.get("claims")
        )

        result_by_id = {
            self._safe_text(claim.get("claim_id"), ""): claim
            for claim in result_claims
            if self._safe_text(claim.get("claim_id"), "")
        }
        result_by_path = {
            self._safe_text(claim.get("path"), ""): claim
            for claim in result_claims
            if self._safe_text(claim.get("path"), "")
        }
        result_by_text = {
            " ".join(
                self._safe_text(claim.get("claim"), "").casefold().split()
            ): claim
            for claim in result_claims
            if self._safe_text(claim.get("claim"), "")
        }

        repaired_claims: List[Dict[str, Any]] = []

        # The deterministic report is authoritative. A generic sanitizer may
        # clean wording, but it must never inject unrelated claims or replace a
        # claim merely because it shares the broad "general" category.
        for fallback_claim in fallback_claims:
            claim_id = self._safe_text(fallback_claim.get("claim_id"), "")
            path = self._safe_text(fallback_claim.get("path"), "")
            text_key = " ".join(
                self._safe_text(
                    fallback_claim.get("claim"),
                    "",
                ).casefold().split()
            )
            sanitized_match = (
                result_by_id.get(claim_id)
                or result_by_path.get(path)
                or result_by_text.get(text_key)
            )

            claim = deepcopy(fallback_claim)
            if sanitized_match and self._safe_text(
                sanitized_match.get("claim"),
                "",
            ):
                claim["claim"] = self._safe_text(
                    sanitized_match.get("claim"),
                    claim.get("claim") or "",
                )

            claim["public_status"] = self._public_status_label(
                self._safe_text(
                    claim.get("status"),
                    "not_confirmed",
                ),
                language,
            )
            claim["public_confidence"] = self._public_confidence_label(
                self._safe_text(
                    claim.get("confidence"),
                    "low",
                ),
                language,
            )
            repaired_claims.append(claim)

        repaired_claims = self._clean_claims(repaired_claims)

        result["claims"] = repaired_claims
        result["claims_to_verify"] = [
            claim["claim"]
            for claim in repaired_claims
            if claim.get("claim")
        ]

        # Les sources canoniques sont déjà validées en amont.
        for key in (
            "source_count",
            "relevant_source_count",
            "source_summary",
            "retained_sources",
        ):
            if key in fallback:
                result[key] = deepcopy(fallback[key])

        for key in (
            "format",
            "status",
            "method",
            "summary",
            "fact_check_summary",
            "confidence_level",
            "global_confidence",
            "evidence_confidence",
            "claim_registry_format",
            "claim_registry_schema_version",
            "claim_coverage",
            "supported_claims",
            "uncertain_claims",
            "warnings",
            "red_flags",
            "recommended_next_checks",
            "recommended_validation",
            "limitations",
        ):
            current = result.get(key)

            if current in (None, "", [], {}):
                result[key] = deepcopy(fallback.get(key))

        result["output_language"] = language
        result["context_locked"] = True

        return result

    def _get_nested_list(
        self,
        data: Dict[str, Any],
        path: tuple[str, str],
    ) -> List[Any]:
        first = data.get(path[0])

        if not isinstance(first, dict):
            return []

        value = first.get(path[1])

        return value if isinstance(value, list) else []

    def _normalize_source(
        self,
        *,
        item: Any,
        source_path: str,
        upstream_validated: bool,
    ) -> Dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        url = self._safe_text(item.get("url") or item.get("source_url"), "")
        if not self._valid_http_url(url):
            return {}
        if item.get("rejected") is True or item.get("internal_only") is True:
            return {}
        if "public_display" in item and item.get("public_display") is False:
            return {}

        matched_terms = self._safe_list(
            item.get("matched_strong_terms")
            or item.get("matched_project_terms")
            or item.get("matched_terms")
        )
        return {
            "title": self._safe_text(item.get("title") or item.get("name"), "Source"),
            "url": url,
            "snippet": self._safe_text(
                item.get("snippet") or item.get("evidence")
                or item.get("why_relevant") or item.get("extracted_text_preview"),
                "",
            ),
            "why_relevant": self._safe_text(item.get("why_relevant") or item.get("evidence"), ""),
            "source_type": self._safe_text(item.get("source_type"), "source").lower(),
            "source_role": self._safe_text(item.get("source_role"), "").lower(),
            "canonical_category": self._safe_text(item.get("canonical_category"), "").lower(),
            "region_match": self._safe_text(item.get("region_match") or item.get("region"), "unknown").lower(),
            "matched_project_terms": matched_terms,
            "matched_strong_terms": matched_terms,
            "matched_domain_terms": self._safe_list(item.get("matched_domain_terms")),
            "matched_target_terms": self._safe_list(item.get("matched_target_terms")),
            "matched_use_case_terms": self._safe_list(item.get("matched_use_case_terms")),
            "matched_solution_terms": self._safe_list(item.get("matched_solution_terms")),
            "product_evidence_signals": self._safe_list(item.get("product_evidence_signals")),
            "market_evidence_signals": self._safe_list(item.get("market_evidence_signals")),
            "evidence_categories": self._safe_list(item.get("evidence_categories")),
            "confidence": self._safe_text(item.get("confidence"), "low").lower(),
            "evidence_quality": self._safe_text(item.get("evidence_quality"), "low").lower(),
            "methodology_visible": bool(item.get("methodology_visible")),
            "source_relevance_score": self._safe_float(item.get("source_relevance_score"), 0.0),
            "public_display": item.get("public_display", True),
            "is_direct_competitor": bool(item.get("is_direct_competitor")),
            "same_or_close_target_user": bool(item.get("same_or_close_target_user")),
            "same_or_close_use_case": bool(item.get("same_or_close_use_case")),
            "same_or_close_solution_category": bool(item.get("same_or_close_solution_category")),
            "clear_contextual_link": bool(item.get("clear_contextual_link")),
            "pricing_found": bool(item.get("pricing_found")),
            "upstream_validated": upstream_validated,
            "upstream_source_path": source_path,
        }

    def _merge_source_records(
        self,
        first: Dict[str, Any],
        second: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = dict(first)
        list_fields = {
            "matched_project_terms", "matched_strong_terms", "matched_domain_terms",
            "matched_target_terms", "matched_use_case_terms", "matched_solution_terms",
            "product_evidence_signals", "market_evidence_signals", "evidence_categories",
        }
        boolean_fields = {
            "is_direct_competitor", "same_or_close_target_user",
            "same_or_close_use_case", "same_or_close_solution_category",
            "clear_contextual_link", "pricing_found", "upstream_validated",
        }
        for key, value in second.items():
            current = merged.get(key)
            if key in list_fields:
                merged[key] = self._unique(self._safe_list(current) + self._safe_list(value))
            elif key == "source_relevance_score":
                merged[key] = max(self._safe_float(current, 0.0), self._safe_float(value, 0.0))
            elif key in boolean_fields:
                merged[key] = bool(current) or bool(value)
            elif current in (None, "", [], {}, "source", "unknown", "low") and value not in (None, "", [], {}):
                merged[key] = value
        return merged

    def _source_signature(
        self,
        source: Dict[str, Any],
    ) -> str:
        url = self._safe_text(
            source.get("url"),
            "",
        ).lower()

        if url:
            return url

        return self._safe_text(
            source.get("title"),
            "source",
        ).lower()

    def _valid_http_url(self, value: Any) -> bool:
        try:
            parsed = urlparse(
                self._safe_text(value, "")
            )
            return (
                parsed.scheme in {"http", "https"}
                and bool(parsed.netloc)
            )
        except Exception:
            return False

    def _safe_float(
        self,
        value: Any,
        fallback: float = 0.0,
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    # ========================================================
    # Confidence / labels / validation
    # ========================================================

    def _confidence_level(
        self,
        source_count: int = 0,
        relevant_source_count: int = 0,
        profile: Dict[str, Any] | None = None,
        evidence_groups: Dict[str, List[Dict[str, Any]]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Backward-compatible wrapper around category-aware confidence."""
        return self._evidence_confidence(
            source_count=source_count,
            relevant_source_count=relevant_source_count,
            evidence_groups=evidence_groups or {},
            profile=profile or {},
        )["overall_evidence_confidence"]

    def _evidence_confidence(
        self,
        *,
        source_count: int,
        relevant_source_count: int,
        evidence_groups: Dict[str, List[Dict[str, Any]]],
        profile: Dict[str, Any] | None = None,
    ) -> Dict[str, str]:
        """Calibrate evidence confidence from quality, not source count alone."""
        profile = profile or {}

        def source_quality(source: Dict[str, Any]) -> str:
            explicit = self._safe_text(
                source.get("evidence_quality"),
                "",
            ).lower()
            if explicit in {"low", "medium", "high"}:
                return explicit

            source_type = self._safe_text(
                source.get("source_type"),
                "",
            ).lower()
            if source_type in {
                "competitor",
                "direct_competitor",
                "adjacent_solution",
                "technology_benchmark",
                "technology_provider",
                "pricing_page",
            }:
                return "medium"
            if source_type in {"regulation", "official_source"}:
                return "high"
            return "low"

        def level(
            sources: List[Dict[str, Any]],
            *,
            high_at: int = 2,
            medium_at: int = 1,
        ) -> str:
            qualified = [
                source
                for source in sources
                if source_quality(source) in {"medium", "high"}
            ]
            high_quality = [
                source
                for source in qualified
                if source_quality(source) == "high"
            ]
            if len(qualified) >= high_at:
                return "high"
            if len(qualified) >= medium_at:
                return "medium"
            return "low"

        local_sources = evidence_groups.get("local_competitors") or []
        solution_sources = evidence_groups.get("solution_evidence") or []
        market_size_sources = [
            source
            for source in (evidence_groups.get("market_size_evidence") or [])
            if self._is_qualified_market_evidence(source)
        ]
        demand_sources = [
            source
            for source in (evidence_groups.get("market_demand_evidence") or [])
            if self._is_qualified_market_evidence(source)
        ]
        problem_sources = evidence_groups.get("problem_evidence") or []
        pricing_sources = [
            source
            for source in (evidence_groups.get("pricing_evidence") or [])
            if self._safe_text(source.get("source_type"), "").lower()
            in {"pricing_page", "competitor", "adjacent_solution"}
        ]

        discovery = (
            "high"
            if relevant_source_count >= 6
            else "medium"
            if relevant_source_count >= 2
            else "low"
        )
        solution = level(solution_sources, high_at=3, medium_at=1)
        local = level(local_sources, high_at=2, medium_at=1)
        market_size = level(market_size_sources, high_at=2, medium_at=1)
        market_demand = level(demand_sources, high_at=2, medium_at=1)
        problem = level(problem_sources, high_at=2, medium_at=1)
        pricing = level(pricing_sources, high_at=2, medium_at=1)

        direct_categories = [
            problem,
            market_size,
            market_demand,
            pricing,
            local,
        ]
        direct_supported = sum(
            value in {"medium", "high"} for value in direct_categories
        )

        if (
            problem in {"medium", "high"}
            and market_size in {"medium", "high"}
            and market_demand in {"medium", "high"}
            and solution in {"medium", "high"}
        ):
            overall = "high"
        elif (
            direct_supported >= 2
            and solution in {"medium", "high"}
        ) or (
            discovery == "high"
            and solution == "high"
        ):
            overall = "medium"
        else:
            overall = "low"

        if str(profile.get("data_confidence") or "").lower() == "low":
            overall = "low"

        return {
            "discovery_confidence": discovery,
            "solution_benchmark_confidence": solution,
            "local_competition_confidence": local,
            "market_size_confidence": market_size,
            "market_demand_confidence": market_demand,
            "problem_evidence_confidence": problem,
            "pricing_confidence": pricing,
            "overall_evidence_confidence": overall,
        }

    def _public_confidence_label(self, confidence: str, language: str = "fr") -> str:
        labels = {
            "fr": {
                "high": "Élevée",
                "medium": "Moyenne",
                "low": "Faible",
            },
            "en": {
                "high": "High",
                "medium": "Medium",
                "low": "Low",
            },
        }

        language = normalize_output_language(language)
        return labels[language].get(confidence, labels[language]["low"])

    def _public_status_label(self, status: str, language: str = "fr") -> str:
        labels = {
            "fr": {
                "sourced": "Sourcé",
                "estimated": "Estimé",
                "recommendation": "Recommandation",
                "audit_conclusion": "Conclusion d’audit",
                "project_input": "Fourni par le projet",
                "field_validation_required": "Validation terrain requise",
                "not_confirmed": "Non confirmé",
            },
            "en": {
                "sourced": "Sourced",
                "estimated": "Estimated",
                "recommendation": "Recommendation",
                "audit_conclusion": "Audit conclusion",
                "project_input": "Provided by the project",
                "field_validation_required": "Field validation required",
                "not_confirmed": "Not confirmed",
            },
        }

        language = normalize_output_language(language)
        return labels[language].get(status, labels[language]["not_confirmed"])

    def _validate_or_sanitize(
        self,
        result: Dict[str, Any],
        project_context: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        """
        Applique le garde-fou sans perdre les sources ni créer des claims vides.

        Les affirmations sont générées de manière déterministe à partir du contexte
        du projet. Les sources sont déjà publiques et validées en amont.
        """
        original = deepcopy(result)

        try:
            validation = domain_integrity_guard.validate_object(
                data=result,
                project_context=project_context,
            )

            if validation.get("is_valid"):
                candidate = result
            else:
                sanitized = domain_integrity_guard.sanitize_object(
                    data=result,
                    project_context=project_context,
                )
                candidate = sanitized if isinstance(sanitized, dict) else result
                candidate["sanitized_by_domain_guard"] = True

            return self._repair_public_report(
                result=candidate,
                fallback=original,
                language=language,
            )

        except Exception:
            repaired = self._repair_public_report(
                result=result,
                fallback=original,
                language=language,
            )
            repaired["domain_guard_warning"] = (
                "Domain guard validation could not be completed."
                if language == "en"
                else "La validation du garde-fou de domaine n'a pas pu être complétée."
            )
            return repaired

    # ========================================================
    # Small helpers
    # ========================================================

    def _count_verified_competitors(self, analysis_data: Dict[str, Any]) -> int:
        competitive = analysis_data.get("competitive_analysis") or {}

        candidates = [
            competitive.get("local_direct_competitors"),
            competitive.get("regional_competitors"),
            competitive.get("international_benchmarks"),
        ]

        count = 0

        for item in candidates:
            if isinstance(item, list):
                count += len(item)

        return count

    def _safe_text(self, value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback

        if isinstance(value, str):
            return value.strip() or fallback

        return str(value).strip() or fallback

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            result: List[str] = []

            for item in value:
                if isinstance(item, str):
                    clean = item.strip()
                    if clean:
                        result.append(clean)
                elif item is not None:
                    clean = str(item).strip()
                    if clean:
                        result.append(clean)

            return result

        if isinstance(value, str):
            clean = value.strip()
            return [clean] if clean else []

        return [str(value).strip()] if str(value).strip() else []

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = str(value or "").strip()

            if not clean:
                continue

            key = clean.lower()

            if key not in seen:
                seen.add(key)
                result.append(clean)

        return result