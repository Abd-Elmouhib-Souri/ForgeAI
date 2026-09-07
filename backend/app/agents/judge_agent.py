# ============================================================
# backend/app/agents/judge_agent.py
# ============================================================
#
# JudgeAgent V3 — Dynamic Context Locked
#
# Objectif :
# - verdict final sans templates métier hardcodés ;
# - décision basée sur score, risques, débat et contexte utilisateur ;
# - respect output_language fr/en ;
# - sortie compatible DebateRoomGraph/frontend.
# ============================================================

from typing import Any, Dict, List

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder


class JudgeAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        project_context = self._get_project_context(state)
        profile = self._build_dynamic_profile(state, project_context)

        result = self._build_judgement(
            state=state,
            profile=profile,
            project_context=project_context,
            language=language,
        )

        validation = domain_integrity_guard.validate_object(
            data=result,
            project_context=project_context,
        )

        if not validation["is_valid"]:
            return domain_integrity_guard.build_safe_agent_fallback(
                project_context=project_context,
                role="judge",
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
            market_region=str(state.get("region") or ""),
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

        project_sentences = project_context.get("project_sentences") or []

        title = str(project_context.get("title") or state.get("title") or "Projet")
        description = str(project_context.get("description") or state.get("description") or "")
        industry = str(project_context.get("industry") or state.get("industry") or "")
        region = str(project_context.get("market_region") or state.get("region") or "")

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

        return {
            "title": title,
            "description": description,
            "industry": industry,
            "region": region,
            "problem": problem,
            "target_users": target_users,
            "value_proposition": value_proposition,
            "revenue": revenue,
            "strengths": self._safe_list(swot.get("strengths")),
            "weaknesses": self._safe_list(swot.get("weaknesses")),
            "opportunities": self._safe_list(swot.get("opportunities"))
            + self._safe_list(market_study.get("opportunities")),
            "threats": self._safe_list(swot.get("threats")),
            "market_risks": self._safe_list(market_study.get("risks")),
            "financial_risk_level": str(financial.get("financial_risk_level") or "medium"),
            "no_local_competitor_found": bool(
                competitive.get("no_local_competitor_found", False)
            ),
            "global_score": self._score_value(startup_score.get("global_score"), fallback=6),
            "innovation": self._score_value(startup_score.get("innovation"), fallback=6),
            "feasibility": self._score_value(startup_score.get("feasibility"), fallback=6),
            "profitability": self._score_value(startup_score.get("profitability"), fallback=6),
            "scalability": self._score_value(startup_score.get("scalability"), fallback=6),
            "data_confidence": str(market_study.get("data_confidence") or "medium").lower(),
            "domain_label": project_context.get("domain_label") or industry or title,
            "anchor_terms": project_context.get("anchor_terms", [])[:12],
        }

    def _build_judgement(
        self,
        *,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        project_context: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        rounds = self._safe_rounds(state.get("rounds"))
        critic_risks = self._collect_critic_risks(rounds)
        missing_evidence = self._collect_missing_evidence(rounds)
        weak_assumptions = self._collect_weak_assumptions(rounds)
        opportunities = self._collect_defender_opportunities(rounds)

        average_risk = self._average_critic_risk(rounds)
        verdict = self._final_verdict(profile, average_risk, rounds)
        risk_level = self._risk_level(profile, average_risk)
        argument_strength_score = self._argument_strength(profile, average_risk)

        if language == "en":
            return {
                "role": "judge",
                "verdict": verdict,
                "argument_strength_score": argument_strength_score,
                "risk_level": risk_level,
                "critical_risks": self._unique(
                    critic_risks
                    + self._en_default_critical_risks(profile)
                )[:6],
                "validated_opportunities": self._unique(
                    opportunities
                    + self._en_default_opportunities(profile)
                )[:5],
                "improved_idea": self._en_improved_idea(profile, verdict),
                "final_recommendation": self._en_final_recommendation(profile, verdict),
                "next_actions": self._en_next_actions(profile, verdict),
                "decision_by_round": self._decision_by_round(rounds),
                "debate_synthesis": self._en_debate_synthesis(
                    profile=profile,
                    verdict=verdict,
                    average_risk=average_risk,
                ),
                "go_no_go_conditions": self._en_go_no_go_conditions(profile),
                "missing_evidence": self._unique(
                    missing_evidence + self._en_default_missing_evidence(profile)
                )[:6],
                "weak_assumptions": self._unique(
                    weak_assumptions + self._en_default_weak_assumptions(profile)
                )[:6],
            }

        return {
            "role": "judge",
            "verdict": verdict,
            "argument_strength_score": argument_strength_score,
            "risk_level": risk_level,
            "critical_risks": self._unique(
                critic_risks
                + self._fr_default_critical_risks(profile)
            )[:6],
            "validated_opportunities": self._unique(
                opportunities
                + self._fr_default_opportunities(profile)
            )[:5],
            "improved_idea": self._fr_improved_idea(profile, verdict),
            "final_recommendation": self._fr_final_recommendation(profile, verdict),
            "next_actions": self._fr_next_actions(profile, verdict),
            "decision_by_round": self._decision_by_round(rounds),
            "debate_synthesis": self._fr_debate_synthesis(
                profile=profile,
                verdict=verdict,
                average_risk=average_risk,
            ),
            "go_no_go_conditions": self._fr_go_no_go_conditions(profile),
            "missing_evidence": self._unique(
                missing_evidence + self._fr_default_missing_evidence(profile)
            )[:6],
            "weak_assumptions": self._unique(
                weak_assumptions + self._fr_default_weak_assumptions(profile)
            )[:6],
        }

    def _final_verdict(
        self,
        profile: Dict[str, Any],
        average_risk: float,
        rounds: List[Dict[str, Any]],
    ) -> str:
        global_score = int(profile.get("global_score") or 6)
        feasibility = int(profile.get("feasibility") or 6)
        profitability = int(profile.get("profitability") or 6)

        abandon_count = 0
        pursue_count = 0

        for round_item in rounds:
            summary = round_item.get("round_summary") or {}
            decision = str(summary.get("decision") or "").upper()

            if decision == "ABANDONNER":
                abandon_count += 1
            elif decision == "POURSUIVRE":
                pursue_count += 1

        if global_score <= 3 or feasibility <= 3 or average_risk >= 9 or abandon_count >= 3:
            return "ABANDONNER"

        if global_score >= 8 and feasibility >= 7 and profitability >= 6 and average_risk <= 5 and pursue_count >= 2:
            return "POURSUIVRE"

        return "PIVOTER"

    def _risk_level(
        self,
        profile: Dict[str, Any],
        average_risk: float,
    ) -> str:
        if average_risk >= 8:
            return "high"

        if average_risk <= 4 and int(profile.get("global_score") or 6) >= 7:
            return "low"

        return "medium"

    def _argument_strength(
        self,
        profile: Dict[str, Any],
        average_risk: float,
    ) -> int:
        score = int(profile.get("global_score") or 6)
        adjusted = round(score - max(0, average_risk - 6) * 0.5)
        return max(1, min(10, int(adjusted)))

    def _fr_improved_idea(self, profile: Dict[str, Any], verdict: str) -> str:
        return (
            f"Reformuler {profile['title']} comme un MVP focalisé sur une seule cible : "
            f"{profile['target_users']}. Le MVP doit tester uniquement le problème suivant : "
            f"{profile['problem']}, avec une proposition de valeur mesurable : "
            f"{profile['value_proposition']}."
        )

    def _en_improved_idea(self, profile: Dict[str, Any], verdict: str) -> str:
        return (
            f"Reframe {profile['title']} as an MVP focused on one target: "
            f"{profile['target_users']}. The MVP should only test the following problem: "
            f"{profile['problem']}, with a measurable value proposition: "
            f"{profile['value_proposition']}."
        )

    def _fr_final_recommendation(self, profile: Dict[str, Any], verdict: str) -> str:
        if verdict == "POURSUIVRE":
            return (
                f"Poursuivre {profile['title']} avec un pilote limité, tout en gardant "
                "des critères stricts de validation terrain."
            )

        if verdict == "ABANDONNER":
            return (
                f"Ne pas développer {profile['title']} dans sa forme actuelle. "
                "Le projet doit être abandonné ou totalement reformulé autour d’un problème plus prouvé."
            )

        return (
            f"Pivoter {profile['title']} avant développement complet : réduire le périmètre, "
            "clarifier la cible, tester la valeur et valider la volonté de payer."
        )

    def _en_final_recommendation(self, profile: Dict[str, Any], verdict: str) -> str:
        if verdict == "POURSUIVRE":
            return (
                f"Continue {profile['title']} with a limited pilot while keeping "
                "strict field validation criteria."
            )

        if verdict == "ABANDONNER":
            return (
                f"Do not build {profile['title']} in its current form. "
                "The project should be abandoned or fully reframed around a better proven problem."
            )

        return (
            f"Pivot {profile['title']} before full development: reduce scope, "
            "clarify the target, test value and validate willingness to pay."
        )

    def _fr_next_actions(self, profile: Dict[str, Any], verdict: str) -> List[str]:
        return [
            f"Interviewer la cible réelle de {profile['title']} : {profile['target_users']}.",
            f"Définir un MVP limité à la résolution de ce problème : {profile['problem']}.",
            f"Construire une maquette ou prototype simple pour tester : {profile['value_proposition']}.",
            f"Tester le prix et la volonté de payer dans la région {profile['region']}.",
            "Comparer manuellement les alternatives déjà utilisées par la cible.",
            "Décider go/no-go uniquement après données terrain mesurables.",
        ]

    def _en_next_actions(self, profile: Dict[str, Any], verdict: str) -> List[str]:
        return [
            f"Interview the real target of {profile['title']}: {profile['target_users']}.",
            f"Define an MVP limited to solving this problem: {profile['problem']}.",
            f"Build a simple mockup or prototype to test: {profile['value_proposition']}.",
            f"Test pricing and willingness to pay in the {profile['region']} region.",
            "Manually compare alternatives already used by the target.",
            "Decide go/no-go only after measurable field data.",
        ]

    def _fr_debate_synthesis(
        self,
        profile: Dict[str, Any],
        verdict: str,
        average_risk: float,
    ) -> str:
        return (
            f"Le débat montre que {profile['title']} possède un potentiel seulement si le projet reste "
            f"strictement lié à son problème réel, sa cible et sa région. Le risque moyen estimé est "
            f"{round(average_risk, 1)}/10. Verdict final : {verdict}."
        )

    def _en_debate_synthesis(
        self,
        profile: Dict[str, Any],
        verdict: str,
        average_risk: float,
    ) -> str:
        return (
            f"The debate shows that {profile['title']} has potential only if the project remains "
            f"strictly linked to its real problem, target and region. Estimated average risk is "
            f"{round(average_risk, 1)}/10. Final verdict: {verdict}."
        )

    def _fr_go_no_go_conditions(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"La cible {profile['target_users']} confirme que le problème est prioritaire.",
            f"Le MVP de {profile['title']} est compris et accepté par la cible.",
            f"Un prototype simple démontre la valeur principale de {profile['title']}.",
            f"La volonté de payer est validée dans la région {profile['region']}.",
            "Les coûts réels restent compatibles avec le modèle de revenu prévu.",
        ]

    def _en_go_no_go_conditions(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"The target {profile['target_users']} confirms that the problem is a priority.",
            f"The MVP of {profile['title']} is understood and accepted by the target.",
            f"A simple prototype demonstrates the main value of {profile['title']}.",
            f"Willingness to pay is validated in the {profile['region']} region.",
            "Real costs remain compatible with the expected revenue model.",
        ]

    def _fr_default_critical_risks(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"Validation terrain insuffisante pour {profile['title']}.",
            f"Cible encore trop large ou mal priorisée pour {profile['title']}.",
            f"Volonté de payer non confirmée dans la région {profile['region']}.",
        ]

    def _en_default_critical_risks(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"Insufficient field validation for {profile['title']}.",
            f"Target still too broad or poorly prioritized for {profile['title']}.",
            f"Willingness to pay not confirmed in the {profile['region']} region.",
        ]

    def _fr_default_opportunities(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"{profile['title']} peut devenir plus crédible avec un MVP réduit et mesurable.",
            f"Une validation courte auprès de {profile['target_users']} peut clarifier la décision.",
        ]

    def _en_default_opportunities(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"{profile['title']} can become more credible with a reduced and measurable MVP.",
            f"A short validation with {profile['target_users']} can clarify the decision.",
        ]

    def _fr_default_missing_evidence(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"Entretiens utilisateurs pour {profile['target_users']}.",
            f"Prototype simple de {profile['title']}.",
            f"Test de prix dans la région {profile['region']}.",
        ]

    def _en_default_missing_evidence(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"User interviews with {profile['target_users']}.",
            f"Simple prototype of {profile['title']}.",
            f"Pricing test in the {profile['region']} region.",
        ]

    def _fr_default_weak_assumptions(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"La cible adoptera réellement {profile['title']}.",
            "Le problème est assez fréquent pour créer un usage répété.",
            "Le modèle économique est compatible avec le pouvoir d’achat de la cible.",
        ]

    def _en_default_weak_assumptions(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"The target will really adopt {profile['title']}.",
            "The problem is frequent enough to create repeated usage.",
            "The business model is compatible with the target's purchasing power.",
        ]

    def _safe_rounds(self, rounds: Any) -> List[Dict[str, Any]]:
        if not isinstance(rounds, list):
            return []

        return [item for item in rounds if isinstance(item, dict)]

    def _collect_critic_risks(self, rounds: List[Dict[str, Any]]) -> List[str]:
        result: List[str] = []

        for item in rounds:
            critic = item.get("critic") or {}
            result.extend(self._safe_list(critic.get("critical_risks")))

        return self._unique(result)

    def _collect_missing_evidence(self, rounds: List[Dict[str, Any]]) -> List[str]:
        result: List[str] = []

        for item in rounds:
            critic = item.get("critic") or {}
            result.extend(self._safe_list(critic.get("missing_evidence")))

        return self._unique(result)

    def _collect_weak_assumptions(self, rounds: List[Dict[str, Any]]) -> List[str]:
        result: List[str] = []

        for item in rounds:
            critic = item.get("critic") or {}
            result.extend(self._safe_list(critic.get("weak_assumptions")))

        return self._unique(result)

    def _collect_defender_opportunities(self, rounds: List[Dict[str, Any]]) -> List[str]:
        result: List[str] = []

        for item in rounds:
            defender = item.get("defender") or {}
            result.extend(self._safe_list(defender.get("opportunities")))

        return self._unique(result)

    def _average_critic_risk(self, rounds: List[Dict[str, Any]]) -> float:
        scores: List[int] = []

        for item in rounds:
            critic = item.get("critic") or {}
            value = critic.get("risk_score")

            try:
                scores.append(max(1, min(10, int(round(float(value))))))
            except Exception:
                pass

        if not scores:
            return 7.0

        return sum(scores) / len(scores)

    def _decision_by_round(self, rounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        decisions: List[Dict[str, Any]] = []

        for item in rounds:
            summary = item.get("round_summary") or {}

            decisions.append(
                {
                    "round": item.get("round"),
                    "topic": item.get("topic"),
                    "decision": summary.get("decision") or "PIVOTER",
                    "synthesis": summary.get("synthesis") or "",
                }
            )

        return decisions

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
