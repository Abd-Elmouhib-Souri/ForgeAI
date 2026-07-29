# ============================================================
# backend/app/agents/defender_agent.py
# ============================================================
#
# DefenderAgent V3 — Dynamic Context Locked
#
# Objectif :
# - supprimer les templates métier hardcodés ;
# - ne plus utiliser pharmacy/agritech/robotics/super_app ;
# - défendre uniquement l'idée de l'utilisateur ;
# - respecter output_language fr/en ;
# - rester compatible avec DebateRoomGraph.
# ============================================================

from typing import Any, Dict, List, Optional

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder


class DefenderAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        round_number = int(state.get("round", 1))

        project_context = self._get_project_context(state)
        profile = self._build_dynamic_profile(state, project_context)

        result = self._build_defense(
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
                role="defender",
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
        bmc = analysis_data.get("business_model_canvas") or {}
        financial = analysis_data.get("financial_estimation") or {}
        score = analysis_data.get("startup_score") or {}

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
            description[:240],
        )

        target_users = self._first_non_empty(
            analysis_data.get("target_users"),
            analysis_data.get("target_market"),
            market_study.get("target_market"),
            self._join_first_items(market_study.get("customer_segments"), 2),
            "la cible décrite par l'utilisateur",
        )

        value_proposition = self._first_non_empty(
            bmc.get("value_proposition"),
            analysis_data.get("proposed_solution"),
            analysis_data.get("summary"),
            description[:280],
        )

        revenue = self._first_non_empty(
            bmc.get("revenue_streams"),
            self._join_first_items(financial.get("possible_revenue_streams"), 2),
            "modèle économique à valider avec la cible",
        )

        strengths = self._safe_list((analysis_data.get("swot") or {}).get("strengths"))
        opportunities = self._safe_list(market_study.get("opportunities"))
        risks = self._safe_list(market_study.get("risks"))

        global_score = self._score_value(score.get("global_score"))
        innovation_score = self._score_value(
            score.get("innovation"),
            fallback=self._score_value(analysis_data.get("innovation_score"), fallback=6),
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
            "strengths": strengths,
            "opportunities": opportunities,
            "risks": risks,
            "global_score": global_score,
            "innovation_score": innovation_score,
            "anchor_terms": project_context.get("anchor_terms", [])[:12],
            "domain_label": project_context.get("domain_label") or industry or title,
        }

    def _build_defense(
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
        previous_critic = self._last_critic(state)

        opportunity_score = self._opportunity_score(profile)
        position = self._position_from_score(opportunity_score)

        if language == "en":
            return {
                "role": "defender",
                "round": round_number,
                "position": position,
                "main_argument": (
                    f"{profile['title']} can still be defended because it addresses this project-specific problem: "
                    f"{profile['problem']}. The defense must remain limited to the target context: "
                    f"{profile['target_users']} in {profile['region']}."
                ),
                "supporting_points": self._en_supporting_points(profile, topic, question),
                "opportunities": self._en_opportunities(profile),
                "response_to_previous_critic": self._en_response_to_critic(
                    previous_critic=previous_critic,
                    profile=profile,
                ),
                "assumptions": self._en_assumptions(profile),
                "opportunity_score": opportunity_score,
            }

        return {
            "role": "defender",
            "round": round_number,
            "position": position,
            "main_argument": (
                f"{profile['title']} peut encore être défendu car il répond au problème spécifique suivant : "
                f"{profile['problem']}. La défense doit rester limitée au contexte cible : "
                f"{profile['target_users']} dans la région {profile['region']}."
            ),
            "supporting_points": self._fr_supporting_points(profile, topic, question),
            "opportunities": self._fr_opportunities(profile),
            "response_to_previous_critic": self._fr_response_to_critic(
                previous_critic=previous_critic,
                profile=profile,
            ),
            "assumptions": self._fr_assumptions(profile),
            "opportunity_score": opportunity_score,
        }

    def _fr_supporting_points(
        self,
        profile: Dict[str, Any],
        topic: str,
        question: str,
    ) -> List[str]:
        points = [
            f"Le projet reste aligné avec son problème central : {profile['problem']}.",
            f"La cible défendable est clairement liée à : {profile['target_users']}.",
            f"La proposition de valeur à défendre est : {profile['value_proposition']}.",
        ]

        strengths = self._safe_list(profile.get("strengths"))

        for strength in strengths[:2]:
            points.append(f"Force déjà identifiée dans l’analyse : {strength}.")

        points.append(
            f"Pour le tour actuel, la défense doit répondre à cette question : {question or topic}."
        )

        return self._unique(points)[:5]

    def _en_supporting_points(
        self,
        profile: Dict[str, Any],
        topic: str,
        question: str,
    ) -> List[str]:
        points = [
            f"The project remains aligned with its central problem: {profile['problem']}.",
            f"The defensible target is clearly linked to: {profile['target_users']}.",
            f"The value proposition to defend is: {profile['value_proposition']}.",
        ]

        strengths = self._safe_list(profile.get("strengths"))

        for strength in strengths[:2]:
            points.append(f"Strength already identified in the analysis: {strength}.")

        points.append(
            f"For this round, the defense should answer this question: {question or topic}."
        )

        return self._unique(points)[:5]

    def _fr_opportunities(self, profile: Dict[str, Any]) -> List[str]:
        opportunities = [
            f"Transformer {profile['title']} en MVP centré sur une seule cible peut réduire le risque.",
            f"La région {profile['region']} peut être testée par un pilote court auprès de la cible décrite.",
            f"Le modèle économique peut être validé progressivement : {profile['revenue']}.",
        ]

        for opportunity in self._safe_list(profile.get("opportunities"))[:2]:
            opportunities.append(f"Opportunité issue de l’étude de marché : {opportunity}.")

        return self._unique(opportunities)[:5]

    def _en_opportunities(self, profile: Dict[str, Any]) -> List[str]:
        opportunities = [
            f"Turning {profile['title']} into an MVP focused on one target can reduce risk.",
            f"The {profile['region']} region can be tested through a short pilot with the described target.",
            f"The business model can be validated progressively: {profile['revenue']}.",
        ]

        for opportunity in self._safe_list(profile.get("opportunities"))[:2]:
            opportunities.append(f"Opportunity from market study: {opportunity}.")

        return self._unique(opportunities)[:5]

    def _fr_assumptions(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"La cible suivante rencontre réellement le problème : {profile['target_users']}.",
            f"La première version de {profile['title']} peut produire une valeur mesurable rapidement.",
            f"Le coût et le prix restent acceptables dans la région {profile['region']}.",
        ]

    def _en_assumptions(self, profile: Dict[str, Any]) -> List[str]:
        return [
            f"The following target really experiences the problem: {profile['target_users']}.",
            f"The first version of {profile['title']} can create measurable value quickly.",
            f"The cost and pricing remain acceptable in the {profile['region']} region.",
        ]

    def _fr_response_to_critic(
        self,
        *,
        previous_critic: Optional[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> str:
        if not previous_critic:
            return (
                f"La bonne approche est de défendre {profile['title']} par un MVP réduit, "
                "des preuves terrain et des mesures d’usage réelles."
            )

        objection = previous_critic.get("main_objection") or self._join_first_items(
            previous_critic.get("critical_risks"),
            1,
        )

        return (
            f"L’objection précédente est pertinente : {objection}. "
            f"La réponse n’est pas d’élargir {profile['title']}, mais de tester rapidement "
            f"le problème suivant auprès de la cible réelle : {profile['problem']}."
        )

    def _en_response_to_critic(
        self,
        *,
        previous_critic: Optional[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> str:
        if not previous_critic:
            return (
                f"The right approach is to defend {profile['title']} through a reduced MVP, "
                "field evidence and real usage metrics."
            )

        objection = previous_critic.get("main_objection") or self._join_first_items(
            previous_critic.get("critical_risks"),
            1,
        )

        return (
            f"The previous objection is relevant: {objection}. "
            f"The answer is not to broaden {profile['title']}, but to quickly test "
            f"the following problem with the real target: {profile['problem']}."
        )

    def _opportunity_score(self, profile: Dict[str, Any]) -> int:
        global_score = int(profile.get("global_score") or 6)
        innovation_score = int(profile.get("innovation_score") or 6)

        score = round((global_score + innovation_score) / 2)

        if profile.get("target_users"):
            score += 1

        if profile.get("value_proposition"):
            score += 1

        return max(1, min(10, int(score)))

    def _position_from_score(self, score: int) -> str:
        if score >= 8:
            return "POURSUIVRE"

        if score <= 3:
            return "ABANDONNER"

        return "PIVOTER"

    def _last_critic(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rounds = state.get("rounds") or []

        if not isinstance(rounds, list) or not rounds:
            return None

        for item in reversed(rounds):
            if isinstance(item, dict) and isinstance(item.get("critic"), dict):
                return item["critic"]

        return None

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