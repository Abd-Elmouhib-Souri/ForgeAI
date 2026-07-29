# ============================================================
# backend/app/agents/fact_checker_agent.py
# ============================================================
#
# FactCheckerAgent V4 — Professional Fallback + Context Locked
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

from typing import Any, Dict, List, Set

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder


class FactCheckerAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point used by Startup Evaluator graph.

        Important:
        - This method must never raise an exception.
        - If fact checking cannot be fully completed, it returns a professional fallback report.
        - The final report remains complete without pretending that weak claims are verified.
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

            result["output_language"] = language
            result["context_locked"] = True
            result["error_handled"] = False

            return result

        except Exception as exc:
            return self._build_fallback_fact_check_report(
                state=state,
                language=language,
                error_message=str(exc),
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
                or "Tunisie"
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
            "Tunisie",
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
        source_count = len(profile["sources"])

        relevant_sources = self._filter_relevant_sources(
            sources=profile["sources"],
            project_context=project_context,
        )

        relevant_source_count = len(relevant_sources)

        confidence_level = self._confidence_level(
            source_count=source_count,
            relevant_source_count=relevant_source_count,
            profile=profile,
        )

        claims = self._build_claims(
            profile=profile,
            relevant_sources=relevant_sources,
            language=language,
        )

        source_summary = {
            "total_sources": source_count,
            "sources_with_url": source_count,
            "verified_competitors": self._count_verified_competitors(analysis_data),
            "relevant_sources": relevant_source_count,
            "source_confidence": confidence_level,
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
                f"Fact checking for {profile['title']} is based on the available analysis "
                f"and {relevant_source_count} relevant retained source(s). Claims without reliable sources "
                "must be treated as hypotheses and validated through field research."
            )

            method = "context_locked_source_review"

        else:
            summary = (
                f"La vérification factuelle de {profile['title']} repose sur l’analyse disponible "
                f"et {relevant_source_count} source(s) pertinente(s) retenue(s). Les affirmations sans sources fiables "
                "doivent rester des hypothèses à valider sur le terrain."
            )

            method = "verification_sources_contextuelles"

        return {
            "format": "fact_checker_v4_professional_context_locked",
            "status": "completed",
            "method": method,
            "summary": summary,
            "fact_check_summary": summary,
            "output_language": language,
            "context_locked": True,
            "confidence_level": confidence_level,
            "global_confidence": confidence_level,
            "source_count": source_count,
            "relevant_source_count": relevant_source_count,
            "source_summary": source_summary,
            "claims": claims,
            "claims_to_verify": [claim["claim"] for claim in claims],
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
            "retained_sources": relevant_sources[:8],
            "error_handled": False,
        }

    # ========================================================
    # Claims
    # ========================================================

    def _build_claims(
        self,
        profile: Dict[str, Any],
        relevant_sources: List[Dict[str, Any]],
        language: str,
    ) -> List[Dict[str, Any]]:
        has_sources = len(relevant_sources) > 0

        if language == "en":
            return [
                self._claim(
                    claim=f"The problem described for {profile['title']} is relevant to the target users.",
                    category="problem",
                    status="field_validation_required",
                    confidence="medium",
                    correction="Validate the problem with real target users before product development.",
                    language=language,
                ),
                self._claim(
                    claim=f"The proposed solution can solve the stated problem for {profile['title']}.",
                    category="solution",
                    status="estimated",
                    confidence="medium",
                    correction="Test a reduced MVP with real users before building the complete product.",
                    language=language,
                ),
                self._claim(
                    claim=f"The market opportunity for {profile['title']} is large enough to justify execution.",
                    category="market_size",
                    status="sourced" if has_sources else "field_validation_required",
                    confidence="medium" if has_sources else "low",
                    correction="Confirm market size using reliable sector, regional or customer data.",
                    language=language,
                ),
                self._claim(
                    claim=f"The competition and alternatives in {profile['region']} are correctly identified.",
                    category="local_competition",
                    status="sourced" if has_sources else "not_confirmed",
                    confidence="medium" if has_sources else "low",
                    correction="Manually verify direct and indirect competitors before final positioning.",
                    language=language,
                ),
                self._claim(
                    claim=f"The financial assumptions for {profile['title']} are realistic.",
                    category="finance",
                    status="field_validation_required",
                    confidence="low",
                    correction="Confirm MVP cost, pricing, margins and willingness to pay with real data.",
                    language=language,
                ),
            ]

        return [
            self._claim(
                claim=f"Le problème décrit pour {profile['title']} est pertinent pour les utilisateurs cibles.",
                category="problem",
                status="field_validation_required",
                confidence="medium",
                correction="Valider le problème avec de vrais utilisateurs cibles avant le développement.",
                language=language,
            ),
            self._claim(
                claim=f"La solution proposée peut résoudre le problème décrit pour {profile['title']}.",
                category="solution",
                status="estimated",
                confidence="medium",
                correction="Tester un MVP réduit avec de vrais utilisateurs avant de construire le produit complet.",
                language=language,
            ),
            self._claim(
                claim=f"L’opportunité de marché pour {profile['title']} est suffisante pour justifier l’exécution.",
                category="market_size",
                status="sourced" if has_sources else "field_validation_required",
                confidence="medium" if has_sources else "low",
                correction="Confirmer la taille du marché avec des données sectorielles, régionales ou terrain fiables.",
                language=language,
            ),
            self._claim(
                claim=f"La concurrence et les alternatives dans la région {profile['region']} sont correctement identifiées.",
                category="local_competition",
                status="sourced" if has_sources else "not_confirmed",
                confidence="medium" if has_sources else "low",
                correction="Vérifier manuellement les concurrents directs et indirects avant le positionnement final.",
                language=language,
            ),
            self._claim(
                claim=f"Les hypothèses financières de {profile['title']} sont réalistes.",
                category="finance",
                status="field_validation_required",
                confidence="low",
                correction="Confirmer le coût MVP, le prix, les marges et la volonté de payer avec des données réelles.",
                language=language,
            ),
        ]

    def _claim(
        self,
        claim: str,
        category: str,
        status: str,
        confidence: str,
        correction: str,
        language: str,
    ) -> Dict[str, Any]:
        return {
            "claim": claim,
            "category": category,
            "status": status,
            "public_status": self._public_status_label(status, language),
            "confidence": confidence,
            "public_confidence": self._public_confidence_label(confidence, language),
            "evidence": [],
            "correction": correction,
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
                    f"No strong claim about {profile['title']} should be considered fully verified without relevant sources."
                ]

            return [
                f"Aucune affirmation forte sur {profile['title']} ne doit être considérée comme totalement vérifiée sans source pertinente."
            ]

        if language == "en":
            return [
                f"{len(relevant_sources)} retained source(s) are sufficiently related to the project context.",
                "Some claims can be discussed cautiously when supported by retained sources, but field validation remains required.",
            ]

        return [
            f"{len(relevant_sources)} source(s) retenue(s) sont suffisamment reliées au contexte du projet.",
            "Certaines affirmations peuvent être discutées prudemment lorsqu’elles sont soutenues par des sources retenues, mais une validation terrain reste nécessaire.",
        ]

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

        if language == "en":
            if source_count == 0:
                warnings.append(
                    f"No external source is available to verify {profile['title']}."
                )

            if source_count > 0 and not relevant_sources:
                warnings.append(
                    f"Sources exist, but none are sufficiently linked to the context of {profile['title']}."
                )

            if profile["crawler_confidence"] == "low":
                warnings.append("Dynamic web source confidence is low.")

            if profile["competitive_confidence"] == "low":
                warnings.append("Competitive analysis must be manually verified.")

            if profile["financial_risk_level"] == "high":
                warnings.append("Financial risk is high and requires cost/pricing testing.")

            if not warnings:
                warnings.append(
                    "No automatic blocking signal was detected, but field validation remains required."
                )

            return self._unique(warnings)

        if source_count == 0:
            warnings.append(
                f"Aucune source externe n’est disponible pour vérifier {profile['title']}."
            )

        if source_count > 0 and not relevant_sources:
            warnings.append(
                f"Des sources existent, mais aucune n’est suffisamment reliée au contexte de {profile['title']}."
            )

        if profile["crawler_confidence"] == "low":
            warnings.append("La confiance des sources web dynamiques est faible.")

        if profile["competitive_confidence"] == "low":
            warnings.append("L’analyse concurrentielle doit être vérifiée manuellement.")

        if profile["financial_risk_level"] == "high":
            warnings.append("Le risque financier est élevé et nécessite un test coût/prix.")

        if not warnings:
            warnings.append(
                "Aucun signal bloquant automatique n’a été détecté, mais une validation terrain reste obligatoire."
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
        if language == "en":
            limitations = [
                "This fact-checking report does not replace field validation.",
                "Market size, pricing, competitor positioning and willingness to pay must be confirmed manually.",
            ]

            if source_count == 0:
                limitations.append("No external source was available for automatic verification.")

            if source_count > 0 and not relevant_sources:
                limitations.append(
                    "External sources were found, but none passed the contextual relevance filter."
                )

            return self._unique(limitations)

        limitations = [
            "Cette vérification factuelle ne remplace pas une validation terrain.",
            "La taille du marché, le prix, le positionnement concurrentiel et la volonté de payer doivent être confirmés manuellement.",
        ]

        if source_count == 0:
            limitations.append("Aucune source externe n’était disponible pour la vérification automatique.")

        if source_count > 0 and not relevant_sources:
            limitations.append(
                "Des sources externes ont été trouvées, mais aucune n’a passé le filtre de pertinence contextuelle."
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

    def _collect_sources(self, data: Any) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                url = value.get("url") or value.get("source_url")

                if url:
                    key = str(url).strip().lower()

                    if key and key not in seen:
                        seen.add(key)
                        sources.append(
                            {
                                "title": self._safe_text(
                                    value.get("title") or value.get("name"),
                                    "Source",
                                ),
                                "url": str(url),
                                "snippet": self._safe_text(
                                    value.get("snippet")
                                    or value.get("evidence")
                                    or value.get("why_relevant")
                                    or value.get("extracted_text_preview"),
                                    "",
                                ),
                                "source_type": self._safe_text(
                                    value.get("source_type"),
                                    "",
                                ),
                                "region_match": self._safe_text(
                                    value.get("region_match"),
                                    "",
                                ),
                                "matched_project_terms": self._safe_list(
                                    value.get("matched_project_terms")
                                    or value.get("matched_terms")
                                ),
                                "confidence": self._safe_text(
                                    value.get("confidence"),
                                    "",
                                ),
                            }
                        )

                for item in value.values():
                    walk(item)

            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(data)
        return sources

    def _filter_relevant_sources(
        self,
        sources: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not sources:
            return []

        try:
            filtered = domain_integrity_guard.filter_sources(
                sources=sources,
                project_context=project_context,
                min_overlap=1,
            )
        except Exception:
            filtered = sources

        context_terms = self._context_terms(project_context)

        cleaned: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        for source in filtered:
            score = self._source_relevance_score(source, context_terms)

            if score < 0.20:
                continue

            url = str(source.get("url") or "").strip().lower()

            if url and url in seen_urls:
                continue

            if url:
                seen_urls.add(url)

            cleaned_source = {
                **source,
                "source_relevance_score": round(score, 2),
            }

            cleaned.append(cleaned_source)

        cleaned.sort(
            key=lambda item: float(item.get("source_relevance_score") or 0),
            reverse=True,
        )

        return cleaned

    def _source_relevance_score(
        self,
        source: Dict[str, Any],
        context_terms: List[str],
    ) -> float:
        if not context_terms:
            return 0.30

        title = self._safe_text(source.get("title"), "")
        snippet = self._safe_text(source.get("snippet"), "")
        source_type = self._safe_text(source.get("source_type"), "")
        matched_terms = self._safe_list(source.get("matched_project_terms"))

        source_text = f"{title} {snippet} {source_type} {' '.join(matched_terms)}".lower()

        if not source_text.strip():
            return 0.0

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
            "create",
            "help",
            "short",
            "lite",
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

        if source.get("snippet"):
            score += 0.05

        return max(0.0, min(1.0, score))

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

    # ========================================================
    # Confidence / labels / validation
    # ========================================================

    def _confidence_level(
        self,
        source_count: int = 0,
        relevant_source_count: int = 0,
        profile: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Conservative confidence calculation.

        This method fixes the previous runtime bug.
        It accepts the exact arguments used by _build_fact_check_report.
        """
        try:
            profile = profile or {}

            score = 0

            if source_count >= 8:
                score += 2
            elif source_count >= 3:
                score += 1

            if relevant_source_count >= 5:
                score += 4
            elif relevant_source_count >= 2:
                score += 3
            elif relevant_source_count >= 1:
                score += 1

            if str(profile.get("crawler_confidence") or "").lower() == "high":
                score += 2
            elif str(profile.get("crawler_confidence") or "").lower() == "medium":
                score += 1

            if str(profile.get("competitive_confidence") or "").lower() == "high":
                score += 2
            elif str(profile.get("competitive_confidence") or "").lower() == "medium":
                score += 1

            if str(profile.get("data_confidence") or "").lower() == "low":
                score -= 1

            if score >= 6:
                return "high"

            if score >= 3:
                return "medium"

            return "low"

        except Exception:
            return "low"

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
                "field_validation_required": "Validation terrain requise",
                "not_confirmed": "Non confirmé",
            },
            "en": {
                "sourced": "Sourced",
                "estimated": "Estimated",
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
        try:
            validation = domain_integrity_guard.validate_object(
                data=result,
                project_context=project_context,
            )

            if validation.get("is_valid"):
                return result

            sanitized = domain_integrity_guard.sanitize_object(
                data=result,
                project_context=project_context,
            )

            if isinstance(sanitized, dict):
                sanitized["sanitized_by_domain_guard"] = True
                return sanitized

            return result

        except Exception:
            result["domain_guard_warning"] = (
                "Domain guard validation could not be completed."
                if language == "en"
                else "La validation du garde-fou de domaine n’a pas pu être complétée."
            )
            return result

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