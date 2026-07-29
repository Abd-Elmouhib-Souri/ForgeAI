# ============================================================
# backend/app/agents/critic_agent.py
# ============================================================
#
# CriticAgent V3 — Dynamic Context Locked
#
# Objectif :
# - critiquer uniquement selon le projet utilisateur ;
# - supprimer les secteurs hardcodés ;
# - respecter output_language fr/en ;
# - produire risques, hypothèses faibles et preuves manquantes.
# ============================================================

from typing import Any, Dict, List

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder


class CriticAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        round_number = int(state.get("round", 1))

        project_context = self._get_project_context(state)
        profile = self._build_dynamic_profile(state, project_context)

        result = self._build_critique(
            state=state,
            profile=profile,
            project_context=project_context,
            round_number=round_number,
            language=language,
        )

        validation = domain_integrity_guard.validate_object(
            data=result,
            project_context=project_context,
        )

        if not validation["is_valid"]:
            return domain_integrity_guard.build_safe_agent_fallback(
                project_context=project_context,
                round_number=round_number,
                role="critic",
            )

        return result

    def _get_project_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        existing = state.get("project_context")

        if isinstance(existing, dict) and existing.get("anchor_terms"):
            return existing

        return project_context_builder.build(
            title=str(state.get("title") or ""),
            description=str(state.get("description") or ""),
            industry=str(state.get("industry") or ""),
            market_region=str(state.get("region") or "Tunisie"),
            output_language=str(state.get("output_language") or "fr"),
            analysis_data=state.get("analysis_data") or {},
        )

    def _build_dynamic_profile(
        self,
        state: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        analysis_data = state.get("analysis_data") or {}

        market_study = analysis_data.get("market_study") or {}
        swot = analysis_data.get("swot") or {}
        bmc = analysis_data.get("business_model_canvas") or {}
        financial = analysis_data.get("financial_estimation") or {}
        startup_score = analysis_data.get("startup_score") or {}
        competitive = analysis_data.get("competitive_analysis") or {}
        forgecrawler = analysis_data.get("forgecrawler") or {}

        project_sentences = project_context.get("project_sentences") or []

        title = str(project_context.get("title") or state.get("title") or "Projet")
        description = str(project_context.get("description") or state.get("description") or "")
        industry = str(project_context.get("industry") or state.get("industry") or "")
        region = str(project_context.get("market_region") or state.get("region") or "Tunisie")

        problem = self._first_non_empty(
            analysis_data.get("problem"),
            analysis_data.get("problem_solved"),
            market_study.get("target_market"),
            project_sentences[0] if project_sentences else None,
            description[:260],
        )

        target_users = self._first_non_empty(
            analysis_data.get("target_users"),
            analysis_data.get("target_market"),
            market_study.get("target_market"),
            self._join_first_items(market_study.get("customer_segments"), 2),
            "cible à préciser",
        )

        value_proposition = self._first_non_empty(
            bmc.get("value_proposition"),
            analysis_data.get("proposed_solution"),
            analysis_data.get("summary"),
            description[:260],
        )

        revenue = self._first_non_empty(
            bmc.get("revenue_streams"),
            self._join_first_items(financial.get("possible_revenue_streams"), 2),
            "revenus à valider",
        )

        data_confidence = str(market_study.get("data_confidence") or "medium").lower()
        crawler_confidence = str(
            forgecrawler.get("confidence_level")
            or competitive.get("confidence_level")
            or "low"
        ).lower()

        global_score = self._score_value(startup_score.get("global_score"), fallback=6)
        feasibility = self._score_value(startup_score.get("feasibility"), fallback=6)
        profitability = self._score_value(startup_score.get("profitability"), fallback=6)
        scalability = self._score_value(startup_score.get("scalability"), fallback=6)

        return {
            "title": title,
            "description": description,
            "industry": industry,
            "region": region,
            "problem": problem,
            "target_users": target_users,
            "value_proposition": value_proposition,
            "revenue": revenue,
            "market_risks": self._safe_list(market_study.get("risks")),
            "weaknesses": self._safe_list(swot.get("weaknesses")),
            "threats": self._safe_list(swot.get("threats")),
            "financial_risk_level": str(financial.get("financial_risk_level") or "medium"),
            "data_confidence": data_confidence,
            "crawler_confidence": crawler_confidence,
            "no_local_competitor_found": bool(
                competitive.get("no_local_competitor_found", False)
            ),
            "global_score": global_score,
            "feasibility": feasibility,
            "profitability": profitability,
            "scalability": scalability,
            "domain_label": project_context.get("domain_label") or industry or title,
            "anchor_terms": project_context.get("anchor_terms", [])[:12],
        }

    def _build_critique(
        self,
        *,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        project_context: Dict[str, Any],
        round_number: int,
        language: str,
    ) -> Dict[str, Any]:
        topic = str(state.get("round_topic") or "")
        question = str(state.get("round_question") or "")
        defender = state.get("pending_defender") or {}

        risk_score = self._risk_score(profile)

        if language == "en":
            return {
                "role": "critic",
                "round": round_number,
                "main_objection": self._en_main_objection(profile, topic, question),
                "critical_risks": self._en_critical_risks(profile, defender),
                "weak_assumptions": self._en_weak_assumptions(profile),
                "missing_evidence": self._en_missing_evidence(profile),
                "counter_recommendation": self._en_counter_recommendation(profile),
                "risk_score": risk_score,
            }

        return {
            "role": "critic",
            "round": round_number,
            "main_objection": self._fr_main_objection(profile, topic, question),
            "critical_risks": self._fr_critical_risks(profile, defender),
            "weak_assumptions": self._fr_weak_assumptions(profile),
            "missing_evidence": self._fr_missing_evidence(profile),
            "counter_recommendation": self._fr_counter_recommendation(profile),
            "risk_score": risk_score,
        }

    def _fr_main_objection(
        self,
        profile: Dict[str, Any],
        topic: str,
        question: str,
    ) -> str:
        return (
            f"La principale objection contre {profile['title']} est que le lien entre le problème, "
            f"la cible et la volonté de payer n’est pas encore suffisamment prouvé. "
            f"Le tour actuel porte sur : {question or topic}."
        )

    def _en_main_objection(
        self,
        profile: Dict[str, Any],
        topic: str,
        question: str,
    ) -> str:
        return (
            f"The main objection against {profile['title']} is that the link between the problem, "
            f"the target users and willingness to pay is not proven enough yet. "
            f"This round focuses on: {question or topic}."
        )

    def _fr_critical_risks(
        self,
        profile: Dict[str, Any],
        defender: Dict[str, Any],
    ) -> List[str]:
        risks = [
            f"Le problème à résoudre pour {profile['target_users']} peut être moins prioritaire que prévu.",
            f"La proposition de valeur de {profile['title']} peut rester trop large si le MVP n’est pas réduit.",
            f"Le modèle de revenu reste risqué tant que la cible n’a pas confirmé la volonté de payer : {profile['revenue']}.",
        ]

        if profile.get("feasibility", 6) <= 5:
            risks.append(
                f"La faisabilité de {profile['title']} doit être vérifiée par un prototype fonctionnel réduit."
            )

        if profile.get("profitability", 6) <= 5:
            risks.append(
                f"La rentabilité de {profile['title']} reste incertaine sans test de prix et coût réel."
            )

        if profile.get("data_confidence") in {"low", "medium"}:
            risks.append(
                f"Les données disponibles pour {profile['title']} restent insuffisantes pour une décision forte."
            )

        risks.extend(self._safe_list(profile.get("market_risks"))[:2])
        risks.extend(self._safe_list(profile.get("weaknesses"))[:2])

        return self._unique(risks)[:6]

    def _en_critical_risks(
        self,
        profile: Dict[str, Any],
        defender: Dict[str, Any],
    ) -> List[str]:
        risks = [
            f"The problem for {profile['target_users']} may be less urgent than expected.",
            f"The value proposition of {profile['title']} may remain too broad if the MVP is not reduced.",
            f"The revenue model remains risky until the target confirms willingness to pay: {profile['revenue']}.",
        ]

        if profile.get("feasibility", 6) <= 5:
            risks.append(
                f"The feasibility of {profile['title']} must be checked through a reduced working prototype."
            )

        if profile.get("profitability", 6) <= 5:
            risks.append(
                f"The profitability of {profile['title']} remains uncertain without a price test and real cost estimate."
            )

        if profile.get("data_confidence") in {"low", "medium"}:
            risks.append(
                f"The available data for {profile['title']} is still insufficient for a strong decision."
            )

        risks.extend(self._safe_list(profile.get("market_risks"))[:2])
        risks.extend(self._safe_list(profile.get("weaknesses"))[:2])

        return self._unique(risks)[:6]

    def _fr_weak_assumptions(self, profile: Dict[str, Any]) -> List[str]:
        assumptions = [
            f"La cible adoptera réellement {profile['title']} dans la région {profile['region']}.",
            f"La douleur décrite est assez forte pour créer un usage répété.",
            f"Le MVP peut être construit sans complexité excessive.",
            f"La proposition de valeur est plus convaincante que les alternatives déjà utilisées par la cible.",
        ]

        if profile.get("no_local_competitor_found"):
            assumptions.append(
                "L’absence de concurrent local vérifié ne prouve pas automatiquement l’existence d’un marché."
            )

        return self._unique(assumptions)[:5]

    def _en_weak_assumptions(self, profile: Dict[str, Any]) -> List[str]:
        assumptions = [
            f"The target will really adopt {profile['title']} in the {profile['region']} region.",
            "The described pain is strong enough to create repeated usage.",
            "The MVP can be built without excessive complexity.",
            "The value proposition is more convincing than alternatives already used by the target.",
        ]

        if profile.get("no_local_competitor_found"):
            assumptions.append(
                "The absence of a verified local competitor does not automatically prove that a market exists."
            )

        return self._unique(assumptions)[:5]

    def _fr_missing_evidence(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"Entretiens avec la cible réelle de {profile['title']} : {profile['target_users']}.",
            f"Preuve que le problème suivant est fréquent et prioritaire : {profile['problem']}.",
            f"Prototype limité montrant la valeur principale de {profile['title']}.",
            f"Test de prix ou intention de paiement dans la région {profile['region']}.",
            "Comparaison manuelle avec les alternatives réellement utilisées par la cible.",
        ]

    def _en_missing_evidence(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"Interviews with the real target of {profile['title']}: {profile['target_users']}.",
            f"Evidence that the following problem is frequent and important: {profile['problem']}.",
            f"Reduced prototype showing the main value of {profile['title']}.",
            f"Pricing test or payment intent in the {profile['region']} region.",
            "Manual comparison with alternatives actually used by the target.",
        ]

    def _fr_counter_recommendation(self, profile: Dict[str, Any]) -> str:
        return (
            f"Avant d’élargir {profile['title']}, il faut réduire le MVP à une seule promesse, "
            f"tester cette promesse auprès de {profile['target_users']} et mesurer l’usage réel."
        )

    def _en_counter_recommendation(self, profile: Dict[str, Any]) -> str:
        return (
            f"Before expanding {profile['title']}, reduce the MVP to one promise, "
            f"test that promise with {profile['target_users']} and measure real usage."
        )

    def _risk_score(self, profile: Dict[str, Any]) -> int:
        base = 10 - int(profile.get("global_score") or 6)

        if profile.get("data_confidence") == "low":
            base += 2
        elif profile.get("data_confidence") == "medium":
            base += 1

        if profile.get("crawler_confidence") == "low":
            base += 1

        if profile.get("financial_risk_level") == "high":
            base += 2
        elif profile.get("financial_risk_level") == "medium":
            base += 1

        if profile.get("no_local_competitor_found"):
            base += 1

        return max(1, min(10, base))

    def _first_non_empty(self, *values: Any) -> str:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def _join_first_items(self, value: Any, count: int) -> str:
        items = self._safe_list(value)
        return ", ".join(items[:count])

    def _safe_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        if isinstance(value, str) and value.strip():
            return [value.strip()]

        return []

    def _score_value(self, value: Any, fallback: int = 6) -> int:
        try:
            return max(1, min(10, int(round(float(value)))))
        except Exception:
            return fallback

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