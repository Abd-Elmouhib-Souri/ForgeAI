# ============================================================
# backend/app/agents/market_study_agent.py
# ============================================================
#
# MarketStudyAgent V4.0
# Context-Locked + Language-Locked + Backend-Stable
#
# Objectifs :
# - utiliser le contexte projet réel avant l'appel LLM ;
# - empêcher les anciens secteurs de démo ;
# - produire une étude de marché exploitable et liée au projet ;
# - respecter output_language fr/en ;
# - ne jamais casser le pipeline ;
# - garder une structure compatible avec le rapport actuel ;
# - éviter les phrases génériques non liées à l'idée.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.agents.startup_evaluator_llm import invoke_llm_json
from app.llm.provider import LLMProvider
from app.services.domain_integrity_guard import normalize_output_language


try:
    from app.agents.startup_evaluator_validators import validate_market_study
except Exception:
    def validate_market_study(
        data: Dict[str, Any],
        output_language: str = "fr",
    ) -> Dict[str, Any]:
        return data if isinstance(data, dict) else {}


class MarketStudyAgent:
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

    GENERIC_WEAK_TERMS = {
        "app",
        "platform",
        "digital",
        "mobile",
        "service",
        "solution",
        "dashboard",
        "management",
        "online",
        "tool",
        "startup",
        "business",
    }

    def __init__(self):
        self.llm = LLMProvider()

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output_language = normalize_output_language(state.get("output_language", "fr"))

        try:
            context = self._context(state)

            prompt = self._build_prompt(
                context=context,
                output_language=output_language,
            )

            raw_data = await invoke_llm_json(
                llm=self.llm,
                prompt=prompt,
                task_type="startup_evaluator_market_study",
            )

            if not isinstance(raw_data, dict):
                return self._fallback(
                    context=context,
                    output_language=output_language,
                    reason="llm_non_dict_response",
                )

            cleaned = self._sanitize_object(
                value=raw_data,
                allowed_context=self._allowed_context(context),
            )

            if not isinstance(cleaned, dict):
                return self._fallback(
                    context=context,
                    output_language=output_language,
                    reason="sanitized_non_dict_response",
                )

            try:
                validated = validate_market_study(
                    cleaned,
                    output_language=output_language,
                )
            except Exception:
                validated = cleaned

            if not isinstance(validated, dict):
                validated = cleaned

            return self._normalize_output(
                data=validated,
                context=context,
                output_language=output_language,
                fallback_used=False,
                error_handled=False,
            )

        except Exception:
            return self._fallback(
                context=self._context(state),
                output_language=output_language,
                reason="market_study_agent_exception",
            )

    # ========================================================
    # Prompt
    # ========================================================

    def _build_prompt(
        self,
        *,
        context: Dict[str, str],
        output_language: str,
    ) -> str:
        language_rule = (
            "Respond only in English."
            if output_language == "en"
            else "Réponds uniquement en français."
        )

        return f"""
You are a senior startup market analyst.

{language_rule}

Analyze the market study for the project below.

PROJECT CONTEXT:
- Project name: {context["title"]}
- Description: {context["description"]}
- Sector: {context["sector"]}
- Target region: {context["region"]}
- Target users: {context["target_users"]}
- Main problem: {context["problem"]}
- MVP scope: {context["mvp_scope"]}
- Business model: {context["business_model"]}

STRICT CONTEXT LOCK:
- Stay strictly inside this project context.
- Do not use old demo examples.
- Do not mention pharmacy delivery, medicine stock, super apps, crypto trading, TikTok, food delivery, agriculture robots, or unrelated products.
- Do not invent external statistics.
- If exact numbers are unavailable, explain the qualitative market logic and what must be validated.
- Avoid generic SaaS sentences unless they are connected to the target users and region.
- Make the analysis useful for an MVP decision.

Return valid JSON only.

Expected JSON:
{{
  "summary": "",
  "market_overview": "",
  "target_market": "",
  "target_customers": [],
  "customer_segments": [],
  "market_problem": "",
  "market_need": "",
  "market_size": "",
  "market_trends": [],
  "demand_drivers": [],
  "adoption_barriers": [],
  "market_opportunities": [],
  "go_to_market_channels": [],
  "local_context": "",
  "mvp_validation_plan": [],
  "key_assumptions": [],
  "market_risks": [],
  "recommendations": [],
  "confidence_level": "low|medium|high",
  "manual_review_required": true
}}
"""

    # ========================================================
    # Normalization
    # ========================================================

    def _normalize_output(
        self,
        *,
        data: Dict[str, Any],
        context: Dict[str, str],
        output_language: str,
        fallback_used: bool,
        error_handled: bool,
    ) -> Dict[str, Any]:
        allowed_context = self._allowed_context(context)

        summary = (
            self._safe_text(data.get("summary"))
            or self._default_summary(context, output_language)
        )

        market_overview = (
            self._safe_text(data.get("market_overview"))
            or self._safe_text(data.get("overview"))
            or self._default_market_overview(context, output_language)
        )

        target_market = (
            self._safe_text(data.get("target_market"))
            or self._safe_text(data.get("target_audience"))
            or context["target_users"]
        )

        target_customers = self._safe_list(
            data.get("target_customers")
            or data.get("customer_segments")
            or data.get("target_users")
        )

        customer_segments = self._safe_list(
            data.get("customer_segments")
            or data.get("segments")
            or target_customers
        )

        market_problem = (
            self._safe_text(data.get("market_problem"))
            or self._safe_text(data.get("problem"))
            or context["problem"]
        )

        market_need = (
            self._safe_text(data.get("market_need"))
            or self._safe_text(data.get("need"))
            or self._default_market_need(context, output_language)
        )

        market_size = (
            self._safe_text(data.get("market_size"))
            or self._safe_text(data.get("market_potential"))
            or self._default_market_size(context, output_language)
        )

        market_trends = self._safe_list(
            data.get("market_trends")
            or data.get("trends")
            or data.get("growth_trends")
        )

        demand_drivers = self._safe_list(
            data.get("demand_drivers")
            or data.get("drivers")
        )

        adoption_barriers = self._safe_list(
            data.get("adoption_barriers")
            or data.get("barriers")
            or data.get("market_challenges")
            or data.get("challenges")
        )

        market_opportunities = self._safe_list(
            data.get("market_opportunities")
            or data.get("opportunities")
        )

        go_to_market_channels = self._safe_list(
            data.get("go_to_market_channels")
            or data.get("channels")
            or data.get("distribution_channels")
        )

        local_context = (
            self._safe_text(data.get("local_context"))
            or self._safe_text(data.get("regional_context"))
            or self._default_local_context(context, output_language)
        )

        mvp_validation_plan = self._safe_list(
            data.get("mvp_validation_plan")
            or data.get("validation_plan")
            or data.get("next_validation_steps")
        )

        key_assumptions = self._safe_list(
            data.get("key_assumptions")
            or data.get("assumptions")
        )

        market_risks = self._safe_list(
            data.get("market_risks")
            or data.get("risks")
        )

        recommendations = self._safe_list(
            data.get("recommendations")
            or data.get("next_steps")
        )

        if not target_customers:
            target_customers = self._default_target_customers(context, output_language)

        if not customer_segments:
            customer_segments = target_customers

        if not market_trends:
            market_trends = self._default_market_trends(context, output_language)

        if not demand_drivers:
            demand_drivers = self._default_demand_drivers(context, output_language)

        if not adoption_barriers:
            adoption_barriers = self._default_adoption_barriers(context, output_language)

        if not market_opportunities:
            market_opportunities = self._default_opportunities(context, output_language)

        if not go_to_market_channels:
            go_to_market_channels = self._default_channels(context, output_language)

        if not mvp_validation_plan:
            mvp_validation_plan = self._default_validation_plan(context, output_language)

        if not key_assumptions:
            key_assumptions = self._default_assumptions(context, output_language)

        if not market_risks:
            market_risks = self._default_risks(context, output_language)

        if not recommendations:
            recommendations = self._default_recommendations(context, output_language)

        normalized = {
            "format": "market_study_v4_context_locked",
            "status": "completed",
            "summary": summary,
            "market_overview": market_overview,
            "target_market": target_market,
            "target_customers": self._unique(target_customers)[:8],
            "customer_segments": self._unique(customer_segments)[:8],
            "market_problem": market_problem,
            "market_need": market_need,
            "market_size": market_size,
            "market_trends": self._unique(market_trends)[:8],
            "demand_drivers": self._unique(demand_drivers)[:8],
            "adoption_barriers": self._unique(adoption_barriers)[:8],
            "market_opportunities": self._unique(market_opportunities)[:8],
            "go_to_market_channels": self._unique(go_to_market_channels)[:8],
            "local_context": local_context,
            "mvp_validation_plan": self._unique(mvp_validation_plan)[:8],
            "key_assumptions": self._unique(key_assumptions)[:8],
            "market_risks": self._unique(market_risks)[:8],
            "recommendations": self._unique(recommendations)[:8],

            # Alias compatibles
            "trends": self._unique(market_trends)[:8],
            "opportunities": self._unique(market_opportunities)[:8],
            "barriers": self._unique(adoption_barriers)[:8],
            "challenges": self._unique(adoption_barriers)[:8],

            "confidence_level": self._confidence_level(data),
            "manual_review_required": True,
            "fallback_used": fallback_used,
            "error_handled": error_handled,
            "context_locked": True,
            "output_language": output_language,
            "project_context_used": {
                "title": context["title"],
                "sector": context["sector"],
                "region": context["region"],
                "target_users": context["target_users"],
                "problem": context["problem"],
                "mvp_scope": context["mvp_scope"],
            },
        }

        sanitized = self._sanitize_object(
            value=normalized,
            allowed_context=allowed_context,
        )

        if not isinstance(sanitized, dict):
            return self._fallback(
                context=context,
                output_language=output_language,
                reason="final_sanitize_failed",
            )

        return sanitized

    # ========================================================
    # Fallback
    # ========================================================

    def _fallback(
        self,
        *,
        context: Dict[str, str],
        output_language: str,
        reason: str,
    ) -> Dict[str, Any]:
        return self._normalize_output(
            data={
                "summary": self._default_summary(context, output_language),
                "market_overview": self._default_market_overview(context, output_language),
                "target_market": context["target_users"],
                "target_customers": self._default_target_customers(context, output_language),
                "customer_segments": self._default_target_customers(context, output_language),
                "market_problem": context["problem"],
                "market_need": self._default_market_need(context, output_language),
                "market_size": self._default_market_size(context, output_language),
                "market_trends": self._default_market_trends(context, output_language),
                "demand_drivers": self._default_demand_drivers(context, output_language),
                "adoption_barriers": self._default_adoption_barriers(context, output_language),
                "market_opportunities": self._default_opportunities(context, output_language),
                "go_to_market_channels": self._default_channels(context, output_language),
                "local_context": self._default_local_context(context, output_language),
                "mvp_validation_plan": self._default_validation_plan(context, output_language),
                "key_assumptions": self._default_assumptions(context, output_language),
                "market_risks": self._default_risks(context, output_language),
                "recommendations": self._default_recommendations(context, output_language),
                "confidence_level": "medium",
                "fallback_reason": reason,
            },
            context=context,
            output_language=output_language,
            fallback_used=True,
            error_handled=True,
        )

    # ========================================================
    # Defaults EN/FR
    # ========================================================

    def _default_summary(self, context: Dict[str, str], lang: str) -> str:
        if lang == "en":
            return (
                f"{context['title']} targets {context['target_users']} in {context['region']} "
                f"within {context['sector']}. The market study should focus on validating the urgency of the problem, "
                "the willingness to adopt a new workflow, and the first segment most likely to pay or run a pilot."
            )

        return (
            f"{context['title']} cible {context['target_users']} en {context['region']} "
            f"dans le secteur {context['sector']}. L’étude de marché doit valider l’urgence du problème, "
            "la volonté d’adopter un nouveau flux de travail et le premier segment capable de payer ou tester un pilote."
        )

    def _default_market_overview(self, context: Dict[str, str], lang: str) -> str:
        if lang == "en":
            return (
                f"The relevant market is the group of {context['target_users']} that currently manage the problem manually, "
                "with fragmented tools, or with inefficient internal processes. The opportunity depends on proving that the MVP saves time, "
                "reduces operational friction, and is simple enough for repeated use."
            )

        return (
            f"Le marché pertinent correspond aux {context['target_users']} qui gèrent aujourd’hui ce problème manuellement, "
            "avec des outils dispersés ou des processus internes peu efficaces. L’opportunité dépend de la preuve que le MVP fait gagner du temps, "
            "réduit la friction opérationnelle et reste assez simple pour un usage répété."
        )

    def _default_market_need(self, context: Dict[str, str], lang: str) -> str:
        if lang == "en":
            return (
                f"The core need is to solve this problem: {context['problem']}. "
                "The MVP must prove that this problem is frequent, painful, and important enough to justify adoption."
            )

        return (
            f"Le besoin central est de résoudre ce problème : {context['problem']}. "
            "Le MVP doit prouver que ce problème est fréquent, douloureux et assez important pour justifier l’adoption."
        )

    def _default_market_size(self, context: Dict[str, str], lang: str) -> str:
        if lang == "en":
            return (
                f"The market size cannot be stated reliably without verified local data for {context['region']}. "
                "At this stage, the market should be treated as a niche-to-expand opportunity: start with a narrow pilot segment, "
                "measure adoption, then estimate expansion potential."
            )

        return (
            f"La taille du marché ne peut pas être affirmée de manière fiable sans données locales vérifiées pour {context['region']}. "
            "À ce stade, le marché doit être traité comme une opportunité de niche extensible : commencer par un segment pilote restreint, "
            "mesurer l’adoption, puis estimer le potentiel d’expansion."
        )

    def _default_local_context(self, context: Dict[str, str], lang: str) -> str:
        if lang == "en":
            return (
                f"In {context['region']}, the first validation should focus on direct interviews, small pilots, and practical budget constraints "
                "of the target users rather than broad market claims."
            )

        return (
            f"En {context['region']}, la première validation doit se concentrer sur des entretiens directs, des petits pilotes "
            "et les contraintes budgétaires pratiques des utilisateurs ciblés plutôt que sur des affirmations générales de marché."
        )

    def _default_target_customers(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                f"Early adopters among {context['target_users']}",
                "Small teams with repeated operational pain",
                "Decision-makers who directly feel the workflow inefficiency",
                "Organizations willing to test a simple MVP before full deployment",
            ]

        return [
            f"Premiers adoptants parmi {context['target_users']}",
            "Petites équipes avec une douleur opérationnelle répétée",
            "Décideurs qui ressentent directement l’inefficacité du flux actuel",
            "Organisations prêtes à tester un MVP simple avant un déploiement complet",
        ]

    def _default_market_trends(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "Growing need to reduce manual administrative work",
                "Preference for simple tools that can be adopted quickly",
                "Demand for clearer tracking and better operational visibility",
                "Shift from informal processes toward structured digital workflows",
            ]

        return [
            "Besoin croissant de réduire le travail administratif manuel",
            "Préférence pour des outils simples et rapidement adoptables",
            "Demande de meilleur suivi et de meilleure visibilité opérationnelle",
            "Passage progressif de processus informels vers des flux numériques structurés",
        ]

    def _default_demand_drivers(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                f"Repeated pain around {context['problem']}",
                "Need to save time in daily operations",
                "Need for more reliable tracking",
                "Pressure to appear more professional to end users or clients",
            ]

        return [
            f"Douleur répétée autour du problème : {context['problem']}",
            "Besoin de gagner du temps dans les opérations quotidiennes",
            "Besoin d’un suivi plus fiable",
            "Pression pour paraître plus professionnel auprès des utilisateurs ou clients finaux",
        ]

    def _default_adoption_barriers(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "Limited budget among early users",
                "Resistance to changing existing habits",
                "Need for a very simple onboarding experience",
                "Difficulty proving willingness to pay before pilot results",
            ]

        return [
            "Budget limité chez les premiers utilisateurs",
            "Résistance au changement des habitudes existantes",
            "Besoin d’un onboarding très simple",
            "Difficulté à prouver la volonté de payer avant les résultats pilotes",
        ]

    def _default_opportunities(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "Start with a narrow segment that has frequent operational pain",
                "Use pilots to collect proof of time saved",
                "Position the MVP as a practical workflow improvement",
                "Expand only after repeat usage is validated",
            ]

        return [
            "Commencer par un segment restreint avec une douleur opérationnelle fréquente",
            "Utiliser des pilotes pour collecter des preuves de temps gagné",
            "Positionner le MVP comme une amélioration pratique du flux de travail",
            "Élargir seulement après validation d’un usage répété",
        ]

    def _default_channels(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "Direct outreach to target organizations",
                "Interviews with decision-makers",
                "Small pilot partnerships",
                "Referral through early satisfied users",
            ]

        return [
            "Prospection directe auprès des organisations ciblées",
            "Entretiens avec les décideurs",
            "Petits partenariats pilotes",
            "Recommandation par les premiers utilisateurs satisfaits",
        ]

    def _default_validation_plan(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "Interview 10 to 20 target users about the current workflow",
                "Identify the most painful repeated task",
                "Test a clickable prototype or very small MVP",
                "Measure weekly usage during a pilot",
                "Ask directly about acceptable pricing",
            ]

        return [
            "Interroger 10 à 20 utilisateurs ciblés sur leur flux actuel",
            "Identifier la tâche répétée la plus douloureuse",
            "Tester un prototype cliquable ou un MVP très réduit",
            "Mesurer l’usage hebdomadaire pendant un pilote",
            "Demander directement le prix acceptable",
        ]

    def _default_assumptions(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                f"The problem is frequent enough for {context['target_users']}",
                "The target users are willing to change part of their workflow",
                "A simple MVP can deliver value before advanced features",
                "The target region has enough reachable early adopters",
            ]

        return [
            f"Le problème est assez fréquent pour {context['target_users']}",
            "Les utilisateurs ciblés sont prêts à changer une partie de leur flux de travail",
            "Un MVP simple peut créer de la valeur avant les fonctionnalités avancées",
            "La région cible contient assez de premiers adoptants accessibles",
        ]

    def _default_risks(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "The problem may be real but not urgent enough",
                "Users may prefer free or manual alternatives",
                "The first segment may be too broad",
                "Adoption may require more support than expected",
            ]

        return [
            "Le problème peut être réel mais pas assez urgent",
            "Les utilisateurs peuvent préférer des alternatives gratuites ou manuelles",
            "Le premier segment peut être trop large",
            "L’adoption peut nécessiter plus d’accompagnement que prévu",
        ]

    def _default_recommendations(self, context: Dict[str, str], lang: str) -> List[str]:
        if lang == "en":
            return [
                "Narrow the first target segment before scaling",
                "Validate the problem through interviews before heavy development",
                "Build only the workflow needed for the first pilot",
                "Measure adoption and willingness to pay before adding advanced features",
            ]

        return [
            "Réduire le premier segment cible avant le passage à l’échelle",
            "Valider le problème par des entretiens avant un développement lourd",
            "Construire seulement le flux nécessaire au premier pilote",
            "Mesurer l’adoption et la volonté de payer avant d’ajouter des fonctionnalités avancées",
        ]

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
            "No detailed description provided.",
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
        if not target_users:
            requested_language = str(
                structured.get("output_language")
                or project_context.get("output_language")
                or state.get("output_language")
                or "fr"
            ).lower()
            target_users = (
                "utilisateurs cibles"
                if requested_language.startswith("fr")
                else "target users"
            )

        problem = self._safe_text(
            structured.get("problem")
            or structured.get("main_problem")
            or structured.get("pain_point")
            or project_context.get("problem")
            or project_context.get("main_problem"),
            "the operational problem described by the project",
        )

        mvp_scope = self._safe_text(
            structured.get("mvp_scope")
            or project_context.get("mvp_scope"),
            "a reduced MVP focused on the core workflow",
        )

        business_model = self._safe_text(
            structured.get("business_model")
            or project_context.get("business_model"),
            "subscription or pilot-based business model",
        )

        context = {
            "title": title,
            "description": description,
            "sector": sector,
            "region": region,
            "target_users": target_users,
            "problem": problem,
            "mvp_scope": mvp_scope,
            "business_model": business_model,
        }

        allowed_context = self._allowed_context(context)

        return {
            key: self._sanitize_text(value, allowed_context=allowed_context)
            for key, value in context.items()
        }

    # ========================================================
    # Sanitization helpers
    # ========================================================

    def _allowed_context(self, context: Dict[str, str]) -> str:
        return self._normalize(
            " ".join(str(value or "") for value in context.values())
        )

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

                if isinstance(item, dict):
                    parts = []

                    for dict_value in item.values():
                        if dict_value is None:
                            continue

                        clean_value = str(dict_value).strip()

                        if clean_value:
                            parts.append(clean_value)

                    clean = " | ".join(parts)
                else:
                    clean = str(item).strip()

                clean = re.sub(r"\s+", " ", clean)

                if clean:
                    result.append(clean[:1000])

            return result

        if isinstance(value, str):
            clean = value.strip()
            return [re.sub(r"\s+", " ", clean)[:1000]] if clean else []

        clean = str(value).strip()

        return [re.sub(r"\s+", " ", clean)[:1000]] if clean else []

    def _readable_list(self, value: Any) -> str:
        items = self._safe_list(value)

        if not items:
            return "target users"

        return ", ".join(items[:6])

    def _confidence_level(self, data: Dict[str, Any]) -> str:
        value = self._normalize(data.get("confidence_level") or "medium")

        if value in {"low", "medium", "high"}:
            return value

        if value in {"faible"}:
            return "low"

        if value in {"moyen", "moyenne"}:
            return "medium"

        if value in {"élevé", "eleve", "haute"}:
            return "high"

        return "medium"

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
