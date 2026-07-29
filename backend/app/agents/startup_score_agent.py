# ============================================================
# backend/app/agents/startup_score_agent.py
# ============================================================
#
# StartupScoreAgent V5.0
# Deterministic + Context-Locked + Language-Locked
#
# Objectifs :
# - supprimer l'appel LLM pour le scoring ;
# - réduire fortement les quotas Gemini/Groq ;
# - produire un score stable, explicable et lié au projet réel ;
# - respecter output_language fr/en ;
# - ne jamais casser le pipeline Startup Evaluator ;
# - garder les champs compatibles avec le rapport actuel ;
# - éviter toute contamination des anciens projets de démo.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class StartupScoreAgent:
    DEMO_OFFTOPIC_TERMS = {
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
        "super app",
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

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output_language = normalize_output_language(state.get("output_language", "fr"))

        try:
            context = self._context(state)
            analysis_data = state.get("analysis_data") or {}

            result = self._build_score(
                state=state,
                analysis_data=analysis_data,
                context=context,
                output_language=output_language,
            )

            return self._final_public_sanitize(
                data=result,
                context=context,
                output_language=output_language,
            )

        except Exception:
            return self._fallback(output_language)

    # ========================================================
    # Deterministic scoring
    # ========================================================

    def _build_score(
        self,
        *,
        state: Dict[str, Any],
        analysis_data: Dict[str, Any],
        context: Dict[str, str],
        output_language: str,
    ) -> Dict[str, Any]:
        title = context["title"]
        sector = context["sector"]
        region = context["region"]
        target_users = context["target_users"]
        problem = context["problem"]
        solution = context["solution"]
        mvp_scope = context["mvp_scope"]
        business_model = context["business_model"]

        readiness_score = self._to_float(
            analysis_data.get("idea_readiness_score")
            or state.get("idea_readiness_score"),
            default=0.7,
        )

        context_confidence = self._to_float(
            analysis_data.get("context_confidence")
            or state.get("context_confidence"),
            default=0.7,
        )

        market_study = self._section(analysis_data, "market_study")
        swot = self._section(analysis_data, "swot")
        bmc = self._section(analysis_data, "business_model_canvas")
        financial = self._section(analysis_data, "financial_estimation")
        competitive = self._section(analysis_data, "competitive_analysis")
        fact_checker = self._section(analysis_data, "fact_checker")

        market_quality = self._section_quality(market_study)
        swot_quality = self._section_quality(swot)
        bmc_quality = self._section_quality(bmc)
        financial_quality = self._section_quality(financial)
        competitive_quality = self._section_quality(competitive)
        fact_quality = self._section_quality(fact_checker)

        context_text = self._normalize(
            " ".join(
                [
                    title,
                    sector,
                    region,
                    target_users,
                    problem,
                    solution,
                    mvp_scope,
                    business_model,
                ]
            )
        )

        has_clear_problem = self._has_meaningful_text(problem)
        has_clear_target = self._has_meaningful_text(target_users)
        has_clear_sector = self._has_meaningful_text(sector)
        has_clear_region = self._has_meaningful_text(region)
        has_clear_mvp = self._has_meaningful_text(mvp_scope)
        has_business_model = self._has_meaningful_text(business_model)

        problem_solution_fit = 5.5
        if has_clear_problem:
            problem_solution_fit += 1.0
        if has_clear_target:
            problem_solution_fit += 0.7
        if self._mentions_any(context_text, ["pain", "problem", "problème", "manual", "manuel", "workflow", "flux", "time", "temps"]):
            problem_solution_fit += 0.5
        if readiness_score >= 0.8:
            problem_solution_fit += 0.5

        market_potential = 5.0
        if has_clear_sector:
            market_potential += 0.7
        if has_clear_region:
            market_potential += 0.6
        if market_quality >= 0.75:
            market_potential += 0.8
        if competitive_quality >= 0.6:
            market_potential += 0.3
        if self._normalize(region) in {"tunisia", "tunisie", "tunisian market", "marché tunisien", "marche tunisien"}:
            market_potential += 0.2

        execution_feasibility = 5.5
        if has_clear_mvp:
            execution_feasibility += 1.0
        if self._mentions_any(context_text, ["mvp", "pilot", "pilote", "simple", "reduced", "réduit", "reduit"]):
            execution_feasibility += 0.6
        if financial_quality >= 0.75:
            execution_feasibility += 0.5
        if context_confidence >= 0.8:
            execution_feasibility += 0.4

        business_model_strength = 5.0
        if has_business_model:
            business_model_strength += 0.9
        if bmc_quality >= 0.75:
            business_model_strength += 0.8
        if financial_quality >= 0.75:
            business_model_strength += 0.6
        if self._mentions_any(context_text, ["subscription", "abonnement", "pilot", "pilote", "saas", "monthly", "mensuel"]):
            business_model_strength += 0.4

        competitive_advantage = 5.0
        if competitive_quality >= 0.75:
            competitive_advantage += 0.6
        if self._mentions_any(context_text, ["specialized", "spécialisé", "specialise", "focused", "ciblé", "cible", "local", "tunisia", "tunisie"]):
            competitive_advantage += 0.7
        if swot_quality >= 0.75:
            competitive_advantage += 0.5

        innovation = 5.5
        if self._mentions_any(context_text, ["ai", "ia", "automation", "automatisation", "analytics", "dashboard", "workflow", "platform", "plateforme", "saas"]):
            innovation += 0.6
        if solution and solution.lower() not in {"the proposed solution", "la solution proposée"}:
            innovation += 0.5
        if has_clear_mvp:
            innovation += 0.3

        scalability = 5.3
        if self._mentions_any(context_text, ["saas", "platform", "plateforme", "subscription", "abonnement", "multi-user", "cloud"]):
            scalability += 0.8
        if has_clear_sector and has_clear_target:
            scalability += 0.5
        if has_clear_region:
            scalability += 0.3

        financial_viability = 5.0
        if financial_quality >= 0.75:
            financial_viability += 0.9
        if has_business_model:
            financial_viability += 0.6
        if bmc_quality >= 0.75:
            financial_viability += 0.4
        if self._mentions_any(context_text, ["paid", "pay", "pricing", "price", "payer", "prix", "tarification", "subscription", "abonnement"]):
            financial_viability += 0.4

        risk_management = 5.0
        if swot_quality >= 0.75:
            risk_management += 0.7
        if fact_quality >= 0.75:
            risk_management += 0.4
        if context_confidence >= 0.8:
            risk_management += 0.5
        if readiness_score >= 0.8:
            risk_management += 0.4

        breakdown = {
            "problem_solution_fit": self._score(problem_solution_fit),
            "market_potential": self._score(market_potential),
            "execution_feasibility": self._score(execution_feasibility),
            "business_model_strength": self._score(business_model_strength),
            "competitive_advantage": self._score(competitive_advantage),
            "innovation": self._score(innovation),
            "scalability": self._score(scalability),
            "financial_viability": self._score(financial_viability),
            "risk_management": self._score(risk_management),
        }

        weighted_score = (
            breakdown["problem_solution_fit"] * 0.17
            + breakdown["market_potential"] * 0.14
            + breakdown["execution_feasibility"] * 0.13
            + breakdown["business_model_strength"] * 0.13
            + breakdown["competitive_advantage"] * 0.10
            + breakdown["innovation"] * 0.08
            + breakdown["scalability"] * 0.10
            + breakdown["financial_viability"] * 0.10
            + breakdown["risk_management"] * 0.05
        )

        score = self._round_half(self._score(weighted_score))

        verdict = self._verdict(score, output_language)
        risk_level = self._risk_level(score)
        confidence_level = self._confidence_level(context_confidence, readiness_score)

        strengths = self._strengths(
            context=context,
            breakdown=breakdown,
            output_language=output_language,
        )

        weaknesses = self._weaknesses(
            context=context,
            breakdown=breakdown,
            output_language=output_language,
        )

        recommendations = self._recommendations(
            context=context,
            breakdown=breakdown,
            output_language=output_language,
        )

        next_actions = self._next_actions(
            context=context,
            score=score,
            output_language=output_language,
        )

        if output_language == "en":
            summary = (
                f"{title} receives a startup score of {score}/10. "
                f"The score reflects a context-locked assessment of the project in {sector}, targeting {target_users} in {region}. "
                f"The opportunity is credible if the team validates the problem, adoption and willingness to pay through a narrow MVP."
            )

            score_explanation = (
                f"The score is based on problem clarity, target segment quality, MVP feasibility, business model readiness, "
                f"financial logic and risk control. The strongest factor is the ability to test a focused MVP around: {problem}."
            )

            investment_readiness = (
                "Not investment-ready yet. Better suited for interviews, prototype validation and pilot preparation."
                if score < 7.5
                else "Potentially ready for early pilot funding, provided the team can show field validation and usage evidence."
            )

        else:
            summary = (
                f"{title} obtient un score startup de {score}/10. "
                f"Le score reflète une évaluation verrouillée sur le contexte du projet dans {sector}, ciblant {target_users} en {region}. "
                "L’opportunité est crédible si l’équipe valide le problème, l’adoption et la volonté de payer avec un MVP réduit."
            )

            score_explanation = (
                f"Le score est basé sur la clarté du problème, la qualité du segment cible, la faisabilité du MVP, "
                f"la maturité du modèle économique, la logique financière et la maîtrise des risques. Le point central à tester est : {problem}."
            )

            investment_readiness = (
                "Pas encore prêt pour investissement. Le projet est plutôt prêt pour des entretiens, un prototype et une préparation de pilote."
                if score < 7.5
                else "Potentiellement prêt pour un financement pilote initial, si l’équipe montre des preuves terrain et d’usage."
            )

        return {
            "format": "startup_score_v5_context_locked_deterministic",
            "status": "completed",

            # Score aliases
            "score": score,
            "startup_score": score,
            "overall_score": score,
            "final_score": score,
            "score_out_of_10": score,

            "summary": summary,
            "score_explanation": score_explanation,
            "verdict": verdict,
            "risk_level": risk_level,
            "confidence_level": confidence_level,
            "investment_readiness": investment_readiness,

            "breakdown": breakdown,
            "score_breakdown": breakdown,
            "criteria_scores": breakdown,

            # Compatibility with older frontend keys
            "innovation": breakdown["innovation"],
            "market": breakdown["market_potential"],
            "execution": breakdown["execution_feasibility"],
            "financial": breakdown["financial_viability"],
            "business_model": breakdown["business_model_strength"],
            "competition": breakdown["competitive_advantage"],
            "scalability": breakdown["scalability"],
            "risk": breakdown["risk_management"],

            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "next_actions": next_actions,

            "go_no_go": self._go_no_go(score, output_language),
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "score_warning": None,
            "context_locked": True,
            "output_language": output_language,

            "scoring_inputs": {
                "idea_readiness_score": readiness_score,
                "context_confidence": context_confidence,
                "market_study_quality": market_quality,
                "swot_quality": swot_quality,
                "bmc_quality": bmc_quality,
                "financial_quality": financial_quality,
                "competitive_quality": competitive_quality,
                "fact_checker_quality": fact_quality,
            },

            "project_context_used": {
                "title": title,
                "sector": sector,
                "region": region,
                "target_users": target_users,
                "problem": problem,
                "solution": solution,
                "business_model": business_model,
                "mvp_scope": mvp_scope,
            },
        }

    # ========================================================
    # Interpretation helpers
    # ========================================================

    def _verdict(self, score: float, lang: str) -> str:
        if lang == "en":
            if score >= 8:
                return "Strong potential — validate with pilots before scaling."
            if score >= 7:
                return "Promising — continue with a focused MVP and field validation."
            if score >= 6:
                return "Moderate potential — narrow the target and validate demand."
            return "Weak-to-moderate potential — rethink positioning before building."

        if score >= 8:
            return "Fort potentiel — valider par des pilotes avant le passage à l’échelle."
        if score >= 7:
            return "Prometteur — continuer avec un MVP ciblé et une validation terrain."
        if score >= 6:
            return "Potentiel moyen — réduire la cible et valider la demande."
        return "Potentiel faible à moyen — retravailler le positionnement avant de construire."

    def _go_no_go(self, score: float, lang: str) -> str:
        if lang == "en":
            if score >= 7:
                return "GO for MVP validation, not yet GO for full-scale development."
            if score >= 6:
                return "CONDITIONAL GO: validate the problem and willingness to pay first."
            return "NO-GO for development until the problem, target and value proposition are clarified."

        if score >= 7:
            return "GO pour validation MVP, mais pas encore GO pour développement complet à grande échelle."
        if score >= 6:
            return "GO CONDITIONNEL : valider d’abord le problème et la volonté de payer."
        return "NO-GO développement tant que le problème, la cible et la valeur ne sont pas clarifiés."

    def _risk_level(self, score: float) -> str:
        if score >= 8:
            return "low"
        if score >= 6.5:
            return "medium"
        return "high"

    def _confidence_level(self, context_confidence: float, readiness_score: float) -> str:
        avg = (context_confidence + readiness_score) / 2

        if avg >= 0.8:
            return "high"
        if avg >= 0.55:
            return "medium"
        return "low"

    def _strengths(
        self,
        *,
        context: Dict[str, str],
        breakdown: Dict[str, float],
        output_language: str,
    ) -> List[str]:
        title = context["title"]
        target_users = context["target_users"]
        region = context["region"]

        if output_language == "en":
            items = [
                f"{title} has a clear first target around {target_users}.",
                f"The project can be tested in {region} with a narrow MVP before scaling.",
                "The concept is suitable for pilot validation because the core workflow can be reduced.",
            ]

            if breakdown["problem_solution_fit"] >= 7:
                items.append("The problem-solution fit appears promising if interviews confirm repeated pain.")

            if breakdown["business_model_strength"] >= 7:
                items.append("The business model has a credible starting path through pilots or subscriptions.")

            return self._unique(items)

        items = [
            f"{title} possède une première cible claire autour de {target_users}.",
            f"Le projet peut être testé en {region} avec un MVP réduit avant le passage à l’échelle.",
            "Le concept est adapté à une validation pilote car le flux principal peut être réduit.",
        ]

        if breakdown["problem_solution_fit"] >= 7:
            items.append("L’adéquation problème-solution semble prometteuse si les entretiens confirment une douleur répétée.")

        if breakdown["business_model_strength"] >= 7:
            items.append("Le modèle économique possède une trajectoire crédible via pilotes ou abonnements.")

        return self._unique(items)

    def _weaknesses(
        self,
        *,
        context: Dict[str, str],
        breakdown: Dict[str, float],
        output_language: str,
    ) -> List[str]:
        if output_language == "en":
            items = [
                "The willingness to pay still needs direct validation.",
                "The first segment may still be too broad and should be narrowed.",
                "The project should avoid adding advanced features before proving repeated use.",
            ]

            if breakdown["competitive_advantage"] < 7:
                items.append("The competitive advantage must be strengthened with clearer differentiation.")

            if breakdown["financial_viability"] < 7:
                items.append("Financial assumptions need pilot data before they can be trusted.")

            return self._unique(items)

        items = [
            "La volonté de payer doit encore être validée directement.",
            "Le premier segment peut encore être trop large et doit être réduit.",
            "Le projet doit éviter d’ajouter des fonctionnalités avancées avant de prouver l’usage répété.",
        ]

        if breakdown["competitive_advantage"] < 7:
            items.append("L’avantage concurrentiel doit être renforcé par une différenciation plus claire.")

        if breakdown["financial_viability"] < 7:
            items.append("Les hypothèses financières doivent être validées par des données de pilote.")

        return self._unique(items)

    def _recommendations(
        self,
        *,
        context: Dict[str, str],
        breakdown: Dict[str, float],
        output_language: str,
    ) -> List[str]:
        if output_language == "en":
            return self._unique(
                [
                    "Run 10 to 20 interviews with the first target users.",
                    "Reduce the MVP to one core workflow and one measurable promise.",
                    "Test willingness to pay before building advanced features.",
                    "Use pilot usage data to refine pricing, onboarding and positioning.",
                    "Compare the product against the real alternatives currently used by the target users.",
                ]
            )

        return self._unique(
            [
                "Faire 10 à 20 entretiens avec les premiers utilisateurs ciblés.",
                "Réduire le MVP à un flux principal et une promesse mesurable.",
                "Tester la volonté de payer avant de construire les fonctionnalités avancées.",
                "Utiliser les données d’usage pilote pour améliorer le prix, l’onboarding et le positionnement.",
                "Comparer le produit aux alternatives réellement utilisées par les utilisateurs ciblés.",
            ]
        )

    def _next_actions(
        self,
        *,
        context: Dict[str, str],
        score: float,
        output_language: str,
    ) -> List[str]:
        if output_language == "en":
            return self._unique(
                [
                    "Define the smallest useful MVP screen flow.",
                    "Prepare a user interview script.",
                    "Recruit pilot users from the first target segment.",
                    "Track activation, weekly usage and willingness to pay.",
                    "Update the score after pilot evidence is collected.",
                ]
            )

        return self._unique(
            [
                "Définir le plus petit flux MVP utile.",
                "Préparer un script d’entretien utilisateur.",
                "Recruter des utilisateurs pilotes dans le premier segment cible.",
                "Suivre l’activation, l’usage hebdomadaire et la volonté de payer.",
                "Mettre à jour le score après collecte de preuves terrain.",
            ]
        )

    # ========================================================
    # Context extraction
    # ========================================================

    def _context(self, state: Dict[str, Any]) -> Dict[str, str]:
        analysis_data = state.get("analysis_data") or {}
        project_context = state.get("project_context") or {}

        project_intelligence = (
            state.get("project_intelligence")
            or analysis_data.get("project_intelligence")
            or project_context.get("project_intelligence")
            or {}
        )

        structured = (
            state.get("structured_project_context")
            or analysis_data.get("structured_project_context")
            or project_context.get("structured_project_context")
            or project_intelligence.get("structured_project_context")
            or {}
        )

        title = self._safe_text(
            structured.get("project_name")
            or structured.get("title")
            or project_context.get("project_name")
            or project_context.get("title")
            or state.get("title"),
            "Project",
        )

        description = self._safe_text(
            structured.get("description")
            or project_context.get("description")
            or state.get("description"),
            "",
        )

        sector = self._safe_text(
            structured.get("sector")
            or structured.get("industry")
            or project_context.get("sector")
            or project_context.get("industry")
            or state.get("industry"),
            "target sector",
        )

        region = self._safe_text(
            structured.get("target_region")
            or structured.get("market_region")
            or project_context.get("target_region")
            or project_context.get("market_region")
            or state.get("region"),
            "target region",
        )

        target_users = self._readable_list(
            structured.get("target_users")
            or project_context.get("target_users")
            or project_context.get("target_market")
            or "target users"
        )

        problem = self._safe_text(
            structured.get("problem")
            or structured.get("core_problem")
            or structured.get("main_problem")
            or structured.get("pain_point")
            or project_context.get("problem")
            or project_context.get("core_problem")
            or project_context.get("main_problem"),
            "the identified operational problem",
        )

        solution = self._safe_text(
            structured.get("solution")
            or structured.get("solution_type")
            or structured.get("value_proposition")
            or project_context.get("solution")
            or project_context.get("solution_type"),
            "the proposed solution",
        )

        business_model = self._safe_text(
            structured.get("business_model")
            or project_context.get("business_model"),
            "subscription or pilot-based business model",
        )

        mvp_scope = self._safe_text(
            structured.get("mvp_scope")
            or project_context.get("mvp_scope"),
            "a reduced MVP focused on the core workflow",
        )

        context = {
            "title": title,
            "description": description,
            "sector": sector,
            "region": region,
            "target_users": target_users,
            "problem": problem,
            "solution": solution,
            "business_model": business_model,
            "mvp_scope": mvp_scope,
        }

        allowed_context = self._allowed_context(context)

        return {
            key: self._sanitize_text(value, allowed_context=allowed_context)
            for key, value in context.items()
        }

    # ========================================================
    # Sanitization
    # ========================================================

    def _final_public_sanitize(
        self,
        *,
        data: Dict[str, Any],
        context: Dict[str, str],
        output_language: str,
    ) -> Dict[str, Any]:
        allowed_context = self._allowed_context(context)

        sanitized = self._sanitize_object(
            value=data,
            allowed_context=allowed_context,
        )

        if not isinstance(sanitized, dict):
            return self._fallback(output_language)

        sanitized.setdefault("format", "startup_score_v5_context_locked_deterministic")
        sanitized.setdefault("status", "completed")
        sanitized.setdefault("context_locked", True)
        sanitized.setdefault("output_language", output_language)

        sanitized.pop("internal_error", None)
        sanitized.pop("raw_data_backup", None)
        sanitized.pop("raw_response", None)
        sanitized.pop("debug", None)

        return sanitized

    def _sanitize_object(self, *, value: Any, allowed_context: str) -> Any:
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

                cleaned_item = self._sanitize_object(
                    value=item,
                    allowed_context=allowed_context,
                )

                if self._is_empty(cleaned_item):
                    continue

                cleaned[clean_key] = cleaned_item

            return cleaned

        if isinstance(value, list):
            cleaned_list: List[Any] = []

            for item in value:
                cleaned_item = self._sanitize_object(
                    value=item,
                    allowed_context=allowed_context,
                )

                if self._is_empty(cleaned_item):
                    continue

                cleaned_list.append(cleaned_item)

            return cleaned_list

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value

        return self._sanitize_text(value, allowed_context=allowed_context)

    def _sanitize_text(self, value: Any, *, allowed_context: str) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)

        normalized_allowed_context = self._normalize(allowed_context)

        for forbidden in self.DEMO_OFFTOPIC_TERMS:
            normalized_forbidden = self._normalize(forbidden)

            if normalized_forbidden and normalized_forbidden in normalized_allowed_context:
                continue

            text = re.sub(
                re.escape(forbidden),
                "",
                text,
                flags=re.IGNORECASE,
            )

        return text[:1500].strip()

    def _allowed_context(self, context: Dict[str, str]) -> str:
        return self._normalize(
            " ".join(str(value or "") for value in context.values())
        )

    # ========================================================
    # Data helpers
    # ========================================================

    def _section(self, analysis_data: Dict[str, Any], key: str) -> Dict[str, Any]:
        value = analysis_data.get(key)

        if isinstance(value, dict):
            return value

        return {}

    def _section_quality(self, section: Dict[str, Any]) -> float:
        if not isinstance(section, dict) or not section:
            return 0.0

        status = self._normalize(section.get("status"))
        context_locked = bool(section.get("context_locked", False))
        fallback_used = bool(section.get("fallback_used", False))
        error_handled = bool(section.get("error_handled", False))

        quality = 0.45

        if status in {"completed", "complete", "done"}:
            quality += 0.25

        if context_locked:
            quality += 0.2

        if not fallback_used:
            quality += 0.07

        if not error_handled:
            quality += 0.03

        return max(0.0, min(1.0, quality))

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default

            return float(value)

        except Exception:
            return default

    def _score(self, value: float) -> float:
        return round(max(1.0, min(10.0, float(value))), 1)

    def _round_half(self, value: float) -> float:
        return round(float(value) * 2) / 2

    def _has_meaningful_text(self, value: Any) -> bool:
        text = self._normalize(value)

        if not text:
            return False

        generic = {
            "project",
            "target sector",
            "target region",
            "target users",
            "the identified operational problem",
            "the proposed solution",
            "subscription or pilot-based business model",
            "a reduced mvp focused on the core workflow",
        }

        return text not in generic and len(text) >= 4

    def _mentions_any(self, text: str, terms: List[str]) -> bool:
        normalized_text = self._normalize(text)

        for term in terms:
            if self._normalize(term) in normalized_text:
                return True

        return False

    # ========================================================
    # Emergency fallback
    # ========================================================

    def _fallback(self, output_language: str) -> Dict[str, Any]:
        if output_language == "en":
            return {
                "format": "startup_score_v5_emergency_fallback",
                "status": "completed",
                "score": 6.0,
                "startup_score": 6.0,
                "overall_score": 6.0,
                "final_score": 6.0,
                "summary": "Startup score completed with a safe deterministic fallback. The project needs clearer field validation before scaling.",
                "score_explanation": "The score is conservative because the scoring agent could not safely access the full project context.",
                "verdict": "Moderate potential — validate the problem, MVP and willingness to pay.",
                "risk_level": "medium",
                "confidence_level": "low",
                "breakdown": {
                    "problem_solution_fit": 6.0,
                    "market_potential": 6.0,
                    "execution_feasibility": 6.0,
                    "business_model_strength": 6.0,
                    "competitive_advantage": 5.5,
                    "innovation": 6.0,
                    "scalability": 6.0,
                    "financial_viability": 5.5,
                    "risk_management": 6.0,
                },
                "score_breakdown": {
                    "problem_solution_fit": 6.0,
                    "market_potential": 6.0,
                    "execution_feasibility": 6.0,
                    "business_model_strength": 6.0,
                    "competitive_advantage": 5.5,
                    "innovation": 6.0,
                    "scalability": 6.0,
                    "financial_viability": 5.5,
                    "risk_management": 6.0,
                },
                "strengths": [
                    "The idea can be validated with a small MVP.",
                    "The project may solve a practical user problem.",
                ],
                "weaknesses": [
                    "The target and willingness to pay need more validation.",
                    "The business assumptions need pilot evidence.",
                ],
                "recommendations": [
                    "Run user interviews.",
                    "Test a focused MVP.",
                    "Validate willingness to pay.",
                ],
                "next_actions": [
                    "Prepare interviews.",
                    "Recruit pilot users.",
                    "Measure weekly usage.",
                ],
                "go_no_go": "CONDITIONAL GO for validation only.",
                "manual_review_required": True,
                "fallback_used": True,
                "error_handled": True,
                "score_warning": "Emergency fallback used.",
                "context_locked": True,
                "output_language": output_language,
            }

        return {
            "format": "startup_score_v5_emergency_fallback",
            "status": "completed",
            "score": 6.0,
            "startup_score": 6.0,
            "overall_score": 6.0,
            "final_score": 6.0,
            "summary": "Score startup complété avec un fallback déterministe sécurisé. Le projet doit encore être validé sur le terrain avant le passage à l’échelle.",
            "score_explanation": "Le score est conservateur car l’agent de scoring n’a pas pu accéder de manière sûre à tout le contexte projet.",
            "verdict": "Potentiel moyen — valider le problème, le MVP et la volonté de payer.",
            "risk_level": "medium",
            "confidence_level": "low",
            "breakdown": {
                "problem_solution_fit": 6.0,
                "market_potential": 6.0,
                "execution_feasibility": 6.0,
                "business_model_strength": 6.0,
                "competitive_advantage": 5.5,
                "innovation": 6.0,
                "scalability": 6.0,
                "financial_viability": 5.5,
                "risk_management": 6.0,
            },
            "score_breakdown": {
                "problem_solution_fit": 6.0,
                "market_potential": 6.0,
                "execution_feasibility": 6.0,
                "business_model_strength": 6.0,
                "competitive_advantage": 5.5,
                "innovation": 6.0,
                "scalability": 6.0,
                "financial_viability": 5.5,
                "risk_management": 6.0,
            },
            "strengths": [
                "L’idée peut être validée avec un petit MVP.",
                "Le projet peut résoudre un problème utilisateur pratique.",
            ],
            "weaknesses": [
                "La cible et la volonté de payer doivent être mieux validées.",
                "Les hypothèses business nécessitent des preuves de pilote.",
            ],
            "recommendations": [
                "Faire des entretiens utilisateurs.",
                "Tester un MVP ciblé.",
                "Valider la volonté de payer.",
            ],
            "next_actions": [
                "Préparer les entretiens.",
                "Recruter des utilisateurs pilotes.",
                "Mesurer l’usage hebdomadaire.",
            ],
            "go_no_go": "GO CONDITIONNEL pour validation uniquement.",
            "manual_review_required": True,
            "fallback_used": True,
            "error_handled": True,
            "score_warning": "Fallback d’urgence utilisé.",
            "context_locked": True,
            "output_language": output_language,
        }

    # ========================================================
    # Generic helpers
    # ========================================================

    def _safe_text(self, value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback

        clean = str(value).strip()

        return clean or fallback

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            result: List[str] = []

            for item in value:
                if item is None:
                    continue

                clean = str(item).strip()

                if clean:
                    result.append(clean)

            return result

        if isinstance(value, str):
            clean = value.strip()
            return [clean] if clean else []

        clean = str(value).strip()

        return [clean] if clean else []

    def _readable_list(self, value: Any) -> str:
        items = self._safe_list(value)

        if not items:
            return "target users"

        return ", ".join(items[:6])

    def _normalize(self, value: Any) -> str:
        text = str(value or "").lower()
        text = text.replace("’", "'")
        text = text.replace("é", "e")
        text = text.replace("è", "e")
        text = text.replace("ê", "e")
        text = text.replace("à", "a")
        text = text.replace("ù", "u")
        text = text.replace("ç", "c")
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _is_empty(self, value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, str):
            return value.strip() == ""

        if isinstance(value, list):
            return len(value) == 0

        if isinstance(value, dict):
            return len(value) == 0

        return False

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = str(value or "").strip()

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result
