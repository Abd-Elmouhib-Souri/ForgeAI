# ============================================================
# backend/app/agents/debate_room_graph.py
# ============================================================
#
# DebateRoomGraph V7.0
# Debate Room Pro+ — Project Review Committee
#
# Objectifs :
# - supprimer les anciens agents Defender/Critic/Judge ;
# - supprimer les appels LLM du Debate Room ;
# - supprimer les faux positifs du domain_integrity_guard global ;
# - produire un comité professionnel structuré ;
# - respecter output_language fr/en ;
# - rester compatible avec le frontend actuel :
#   analysis_data.debate_room.rounds
#   analysis_data.debate_room.judge
#   analysis_data.debate_room.meta
# - ne jamais casser l'analyse complète.
# ============================================================

from __future__ import annotations

import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.services.domain_integrity_guard import normalize_output_language

logger = logging.getLogger(__name__)

StepCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class DebateRoomGraph:
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

    def __init__(self, step_callback: Optional[StepCallback] = None):
        self.step_callback = step_callback

    async def run(
        self,
        project_id: int,
        title: str,
        description: str,
        industry: str = "",
        region: str = "Tunisie",
        output_language: str = "fr",
        project_context: Optional[Dict[str, Any]] = None,
        analysis_data: Optional[Dict[str, Any]] = None,
        max_rounds: int = 5,
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)
        effective_max_rounds = self._normalize_max_rounds(max_rounds)
        analysis_payload = analysis_data or {}

        context = self._context(
            title=title,
            description=description,
            industry=industry,
            region=region,
            output_language=language,
            project_context=project_context or {},
            analysis_data=analysis_payload,
        )

        debate_plan = self._build_debate_plan(language)[:effective_max_rounds]

        state: Dict[str, Any] = {
            "project_id": project_id,
            "title": context["title"],
            "description": context["description"],
            "industry": context["sector"],
            "region": context["region"],
            "output_language": language,
            "project_context": context,
            "analysis_data": analysis_payload,
            "round": 1,
            "max_rounds": effective_max_rounds,
            "debate_plan": debate_plan,
            "rounds": [],
            "judge": {},
            "completed_steps": [],
            "failed_steps": [],
            "current_step": "debate_room_pro_started",
            "progress": 0,
            "completed": False,
            "error": None,
            "context_locked": True,
        }

        try:
            rounds: List[Dict[str, Any]] = []

            for round_context in debate_plan:
                round_number = int(round_context["round"])

                moderator = self._build_moderator_message(
                    round_number=round_number,
                    round_context=round_context,
                    context=context,
                    output_language=language,
                )

                defender = self._build_defender_position(
                    round_context=round_context,
                    context=context,
                    analysis_data=analysis_payload,
                    output_language=language,
                )

                state["round"] = round_number
                state["pending_moderator"] = moderator
                state["pending_defender"] = defender
                state["current_step"] = f"debate_room_pro_round_{round_number}_defender"
                state["completed_steps"] = list(state.get("completed_steps", [])) + [
                    f"round_{round_number}_moderator",
                    f"round_{round_number}_defender",
                ]
                state["progress"] = self._calculate_progress(
                    completed_rounds=len(rounds),
                    max_rounds=effective_max_rounds,
                    defender_done=True,
                    completed=False,
                )
                await self._notify(state)

                critic = self._build_critic_position(
                    round_context=round_context,
                    context=context,
                    analysis_data=analysis_payload,
                    output_language=language,
                )

                round_summary = self._build_round_summary(
                    round_context=round_context,
                    defender=defender,
                    critic=critic,
                    context=context,
                    output_language=language,
                )

                round_item = {
                    "round": round_number,
                    "topic": round_context["topic"],
                    "focus": round_context["focus"],
                    "key_question": round_context["key_question"],
                    "committee_roles": round_context["committee_roles"],
                    "moderator": moderator,
                    "defender": defender,
                    "critic": critic,
                    "round_summary": round_summary,
                    "context_locked": True,
                    "output_language": language,
                }

                round_item = self._sanitize_object(
                    value=round_item,
                    allowed_context=self._allowed_context(context),
                )

                rounds.append(round_item)

                state["rounds"] = rounds
                state["pending_moderator"] = {}
                state["pending_defender"] = {}
                state["current_step"] = f"debate_room_pro_round_{round_number}_critic"
                state["completed_steps"] = list(state.get("completed_steps", [])) + [
                    f"round_{round_number}_critic"
                ]
                state["progress"] = self._calculate_progress(
                    completed_rounds=len(rounds),
                    max_rounds=effective_max_rounds,
                    defender_done=False,
                    completed=False,
                )
                await self._notify(state)

            judge = self._build_judge(
                rounds=rounds,
                context=context,
                analysis_data=analysis_payload,
                output_language=language,
            )

            judge = self._sanitize_object(
                value=judge,
                allowed_context=self._allowed_context(context),
            )

            state["judge"] = judge
            state["completed"] = True
            state["current_step"] = "debate_room_pro_judge"
            state["completed_steps"] = list(state.get("completed_steps", [])) + ["judge"]
            state["progress"] = 100
            state["error"] = None
            await self._notify(state)

            return {
                "debate_room": {
                    "format": "debate_room_pro_v7_project_review_committee",
                    "title": (
                        "Debate Room Pro+ — Project Review Committee"
                        if language == "en"
                        else "Salle de débat stratégique — Comité de validation projet"
                    ),
                    "status": "completed",
                    "max_rounds": effective_max_rounds,
                    "committee": self._committee(language),
                    "rounds": rounds,
                    "judge": judge,
                    "meta": {
                        "completed_steps": state.get("completed_steps", []),
                        "failed_steps": state.get("failed_steps", []),
                        "progress": 100,
                        "current_step": "debate_room_pro_judge",
                        "completed": True,
                        "error": None,
                        "output_language": language,
                        "context_locked": True,
                        "llm_used": False,
                    },
                    "context_locked": True,
                    "output_language": language,
                    "project_context_used": context,
                }
            }

        except Exception as exc:
            logger.exception("[DebateRoomGraph] Deterministic Debate Room failed")

            fallback = self._fallback_judge(
                context=context,
                output_language=language,
                error=str(exc),
            )

            return {
                "debate_room": {
                    "format": "debate_room_pro_v7_emergency_fallback",
                    "status": "completed",
                    "max_rounds": effective_max_rounds,
                    "committee": self._committee(language),
                    "rounds": [],
                    "judge": fallback,
                    "meta": {
                        "completed_steps": [],
                        "failed_steps": ["debate_room_pro"],
                        "progress": 100,
                        "current_step": "debate_room_pro_fallback_completed",
                        "completed": True,
                        "error": str(exc),
                        "output_language": language,
                        "context_locked": True,
                        "llm_used": False,
                    },
                    "context_locked": True,
                    "output_language": language,
                    "project_context_used": context,
                }
            }

    # ========================================================
    # Debate plan
    # ========================================================

    def _build_debate_plan(self, output_language: str = "fr") -> List[Dict[str, Any]]:
        language = normalize_output_language(output_language)

        if language == "en":
            return [
                {
                    "round": 1,
                    "topic": "Problem, target and urgency",
                    "focus": "Validate whether the project solves a clear and repeated pain for a precise first target.",
                    "key_question": "Is the problem important enough for the first users to change behavior?",
                    "committee_roles": ["Moderator", "Project Owner", "Customer Representative", "Product Manager"],
                    "defender_role": "Project Owner",
                    "critic_role": "Customer Representative",
                },
                {
                    "round": 2,
                    "topic": "Market, positioning and alternatives",
                    "focus": "Assess the first market, current alternatives, competitive pressure and positioning.",
                    "key_question": "Can the project win against the real alternatives already used by the target users?",
                    "committee_roles": ["Moderator", "Market & Sales Manager", "Operations / Field Expert", "Customer Representative"],
                    "defender_role": "Market & Sales Manager",
                    "critic_role": "Operations / Field Expert",
                },
                {
                    "round": 3,
                    "topic": "MVP, product scope and technical feasibility",
                    "focus": "Check whether the MVP can be built with a reduced scope and clear first workflow.",
                    "key_question": "Is the MVP realistic without adding unnecessary complexity?",
                    "committee_roles": ["Moderator", "CTO / Technical Lead", "Product Manager", "Operations / Field Expert"],
                    "defender_role": "CTO / Technical Lead",
                    "critic_role": "Product Manager",
                },
                {
                    "round": 4,
                    "topic": "Business model, pricing and financial risk",
                    "focus": "Evaluate revenue logic, MVP budget, pricing and financial sustainability.",
                    "key_question": "Can the project create enough value to justify payment?",
                    "committee_roles": ["Moderator", "CFO / Finance Manager", "Market & Sales Manager", "Project Owner"],
                    "defender_role": "CFO / Finance Manager",
                    "critic_role": "Market & Sales Manager",
                },
                {
                    "round": 5,
                    "topic": "Final strategic decision and execution plan",
                    "focus": "Turn the debate into a go/no-go decision, improved idea and concrete next actions.",
                    "key_question": "Should the team continue, pivot or stop, and what must be done next?",
                    "committee_roles": ["Moderator", "Executive Judge", "Project Owner", "Full Committee"],
                    "defender_role": "Project Owner",
                    "critic_role": "Executive Judge",
                },
            ]

        return [
            {
                "round": 1,
                "topic": "Problème, cible et urgence",
                "focus": "Valider si le projet résout une douleur claire et répétée pour une première cible précise.",
                "key_question": "Le problème est-il assez important pour pousser les premiers utilisateurs à changer leurs habitudes ?",
                "committee_roles": ["Moderator", "Project Owner", "Customer Representative", "Product Manager"],
                "defender_role": "Project Owner",
                "critic_role": "Customer Representative",
            },
            {
                "round": 2,
                "topic": "Marché, positionnement et alternatives",
                "focus": "Évaluer le premier marché, les alternatives actuelles, la pression concurrentielle et le positionnement.",
                "key_question": "Le projet peut-il gagner face aux alternatives réellement utilisées par les utilisateurs ciblés ?",
                "committee_roles": ["Moderator", "Market & Sales Manager", "Operations / Field Expert", "Customer Representative"],
                "defender_role": "Market & Sales Manager",
                "critic_role": "Operations / Field Expert",
            },
            {
                "round": 3,
                "topic": "MVP, périmètre produit et faisabilité technique",
                "focus": "Vérifier si le MVP peut être construit avec un périmètre réduit et un premier flux clair.",
                "key_question": "Le MVP est-il réaliste sans ajouter une complexité inutile ?",
                "committee_roles": ["Moderator", "CTO / Technical Lead", "Product Manager", "Operations / Field Expert"],
                "defender_role": "CTO / Technical Lead",
                "critic_role": "Product Manager",
            },
            {
                "round": 4,
                "topic": "Business model, prix et risque financier",
                "focus": "Évaluer la logique de revenu, le budget MVP, la tarification et la durabilité financière.",
                "key_question": "Le projet crée-t-il assez de valeur pour justifier un paiement ?",
                "committee_roles": ["Moderator", "CFO / Finance Manager", "Market & Sales Manager", "Project Owner"],
                "defender_role": "CFO / Finance Manager",
                "critic_role": "Market & Sales Manager",
            },
            {
                "round": 5,
                "topic": "Décision stratégique finale et plan d’exécution",
                "focus": "Transformer le débat en décision go/no-go, version améliorée et actions concrètes.",
                "key_question": "Faut-il poursuivre, pivoter ou arrêter, et que faut-il faire ensuite ?",
                "committee_roles": ["Moderator", "Executive Judge", "Project Owner", "Full Committee"],
                "defender_role": "Project Owner",
                "critic_role": "Executive Judge",
            },
        ]

    # ========================================================
    # Round builders
    # ========================================================

    def _build_moderator_message(
        self,
        *,
        round_number: int,
        round_context: Dict[str, Any],
        context: Dict[str, str],
        output_language: str,
    ) -> Dict[str, Any]:
        if output_language == "en":
            instruction = (
                f"Round {round_number} examines {context['title']} through the lens of: {round_context['focus']}"
            )
        else:
            instruction = (
                f"Le tour {round_number} examine {context['title']} selon l’angle suivant : {round_context['focus']}"
            )

        return {
            "role": "Moderator",
            "round": round_number,
            "topic": round_context["topic"],
            "focus": round_context["focus"],
            "key_question": round_context["key_question"],
            "instruction": instruction,
            "context_locked": True,
        }

    def _build_defender_position(
        self,
        *,
        round_context: Dict[str, Any],
        context: Dict[str, str],
        analysis_data: Dict[str, Any],
        output_language: str,
    ) -> Dict[str, Any]:
        title = context["title"]
        target_users = context["target_users"]
        region = context["region"]
        problem = context["problem"]
        mvp_scope = context["mvp_scope"]
        business_model = context["business_model"]

        round_number = int(round_context["round"])

        if output_language == "en":
            base_points = {
                1: [
                    f"{title} focuses on a concrete pain for {target_users}: {problem}.",
                    f"The first validation can happen in {region} with interviews and a narrow pilot.",
                    "The project has enough clarity to test demand before building a large platform.",
                ],
                2: [
                    f"The positioning can be defensible if {title} stays specialized for {target_users}.",
                    "The product should compete first against manual workflows and generic tools, not against every global platform.",
                    "A local and workflow-specific approach can create early differentiation.",
                ],
                3: [
                    f"The MVP can be reduced to: {mvp_scope}.",
                    "A narrow MVP lowers cost, delivery risk and onboarding complexity.",
                    "The first version should prove usage before adding advanced automation.",
                ],
                4: [
                    f"The business model can start with {business_model}.",
                    "Revenue should be validated through pilots before assuming scalable subscriptions.",
                    "The financial plan is acceptable if acquisition and support costs stay controlled.",
                ],
                5: [
                    f"The committee should continue {title} as a focused MVP, not as a broad platform.",
                    "The best path is field validation, pilot usage and pricing tests.",
                    "The idea should be improved by narrowing the first target and proving measurable value.",
                ],
            }

            return {
                "role": round_context["defender_role"],
                "position": "CONTINUE_WITH_FOCUSED_MVP",
                "thesis": f"{title} deserves continued validation if execution stays narrow and evidence-based.",
                "supporting_points": base_points.get(round_number, base_points[5]),
                "opportunities": self._opportunities(context, output_language),
                "assumptions_to_validate": self._assumptions(context, output_language),
                "recommended_action": "Continue with a narrow MVP and validate adoption before scaling.",
                "evidence_used": self._evidence_used(analysis_data, output_language),
                "context_locked": True,
            }

        base_points = {
            1: [
                f"{title} se concentre sur une douleur concrète pour {target_users} : {problem}.",
                f"La première validation peut se faire en {region} avec des entretiens et un pilote réduit.",
                "Le projet est assez clair pour tester la demande avant de construire une grande plateforme.",
            ],
            2: [
                f"Le positionnement peut être défendable si {title} reste spécialisé pour {target_users}.",
                "Le produit doit d’abord concurrencer les flux manuels et les outils génériques, pas toutes les plateformes mondiales.",
                "Une approche locale et spécifique au flux métier peut créer une différenciation initiale.",
            ],
            3: [
                f"Le MVP peut être réduit à : {mvp_scope}.",
                "Un MVP réduit diminue le coût, le risque de livraison et la complexité d’onboarding.",
                "La première version doit prouver l’usage avant d’ajouter une automatisation avancée.",
            ],
            4: [
                f"Le modèle économique peut démarrer avec {business_model}.",
                "Le revenu doit être validé par des pilotes avant de supposer des abonnements scalables.",
                "Le plan financier est acceptable si les coûts d’acquisition et de support restent maîtrisés.",
            ],
            5: [
                f"Le comité doit poursuivre {title} comme MVP ciblé, pas comme plateforme trop large.",
                "La meilleure trajectoire est validation terrain, usage pilote et test du prix.",
                "L’idée doit être améliorée en réduisant la première cible et en prouvant une valeur mesurable.",
            ],
        }

        return {
            "role": round_context["defender_role"],
            "position": "POURSUIVRE_AVEC_MVP_CIBLÉ",
            "thesis": f"{title} mérite une validation continue si l’exécution reste ciblée et basée sur des preuves.",
            "supporting_points": base_points.get(round_number, base_points[5]),
            "opportunities": self._opportunities(context, output_language),
            "assumptions_to_validate": self._assumptions(context, output_language),
            "recommended_action": "Continuer avec un MVP réduit et valider l’adoption avant le passage à l’échelle.",
            "evidence_used": self._evidence_used(analysis_data, output_language),
            "context_locked": True,
        }

    def _build_critic_position(
        self,
        *,
        round_context: Dict[str, Any],
        context: Dict[str, str],
        analysis_data: Dict[str, Any],
        output_language: str,
    ) -> Dict[str, Any]:
        title = context["title"]
        target_users = context["target_users"]
        problem = context["problem"]
        mvp_scope = context["mvp_scope"]

        round_number = int(round_context["round"])

        if output_language == "en":
            risks_by_round = {
                1: [
                    f"The pain may exist but may not be urgent enough for {target_users} to pay or change behavior.",
                    "The first target segment may still be too wide.",
                    "The team still needs direct evidence from user interviews.",
                ],
                2: [
                    "The real competitor may be the current manual workflow, not another SaaS product.",
                    "Generic tools may be good enough for some users.",
                    "Positioning must be more specific than simply being a digital platform.",
                ],
                3: [
                    f"The MVP scope can still become too large if {mvp_scope} is not reduced to the first workflow.",
                    "Technical execution is less risky than adoption and onboarding.",
                    "The first version must avoid advanced features before repeated use is proven.",
                ],
                4: [
                    "Subscription revenue is not proven until users accept a real price.",
                    "Customer acquisition and support costs can be underestimated.",
                    "The project needs pilot data before financial assumptions are trusted.",
                ],
                5: [
                    "The project should not scale before proving repeated weekly usage.",
                    "The improved idea must be narrower than the original broad version.",
                    "The go/no-go conditions must be strict and measurable.",
                ],
            }

            return {
                "role": round_context["critic_role"],
                "position": "PIVOT_BEFORE_SCALING",
                "critical_risks": risks_by_round.get(round_number, risks_by_round[5]),
                "missing_evidence": self._missing_evidence(context, output_language),
                "objections": [
                    f"{title} may be useful, but usefulness is not enough without adoption and willingness to pay.",
                    f"The first MVP must prove that solving '{problem}' creates measurable value.",
                ],
                "risk_score": self._round_risk_score(round_number),
                "mitigation_requests": self._mitigation_requests(context, output_language),
                "context_locked": True,
            }

        risks_by_round = {
            1: [
                f"La douleur peut exister mais ne pas être assez urgente pour pousser {target_users} à payer ou changer d’habitude.",
                "Le premier segment cible peut encore être trop large.",
                "L’équipe doit encore obtenir des preuves directes par entretiens utilisateurs.",
            ],
            2: [
                "Le vrai concurrent peut être le flux manuel actuel, pas forcément un autre SaaS.",
                "Des outils génériques peuvent suffire à une partie des utilisateurs.",
                "Le positionnement doit être plus spécifique qu’une simple plateforme numérique.",
            ],
            3: [
                f"Le périmètre MVP peut encore devenir trop large si {mvp_scope} n’est pas réduit au premier flux.",
                "Le risque principal n’est pas seulement technique, mais aussi l’adoption et l’onboarding.",
                "La première version doit éviter les fonctionnalités avancées avant de prouver l’usage répété.",
            ],
            4: [
                "Le revenu par abonnement n’est pas prouvé tant que les utilisateurs n’acceptent pas un vrai prix.",
                "Les coûts d’acquisition et de support peuvent être sous-estimés.",
                "Le projet a besoin de données de pilote avant de fiabiliser les hypothèses financières.",
            ],
            5: [
                "Le projet ne doit pas passer à l’échelle avant de prouver un usage hebdomadaire répété.",
                "La version améliorée doit être plus étroite que l’idée initiale trop large.",
                "Les conditions go/no-go doivent être strictes et mesurables.",
            ],
        }

        return {
            "role": round_context["critic_role"],
            "position": "PIVOTER_AVANT_SCALE",
            "critical_risks": risks_by_round.get(round_number, risks_by_round[5]),
            "missing_evidence": self._missing_evidence(context, output_language),
            "objections": [
                f"{title} peut être utile, mais l’utilité ne suffit pas sans adoption et volonté de payer.",
                f"Le premier MVP doit prouver que résoudre « {problem} » crée une valeur mesurable.",
            ],
            "risk_score": self._round_risk_score(round_number),
            "mitigation_requests": self._mitigation_requests(context, output_language),
            "context_locked": True,
        }

    def _build_round_summary(
        self,
        *,
        round_context: Dict[str, Any],
        defender: Dict[str, Any],
        critic: Dict[str, Any],
        context: Dict[str, str],
        output_language: str,
    ) -> Dict[str, Any]:
        validated_points = self._unique_strings(
            self._safe_list(defender.get("supporting_points"))[:2]
            + self._safe_list(defender.get("opportunities"))[:1]
        )

        remaining_risks = self._unique_strings(
            self._safe_list(critic.get("critical_risks"))[:3]
            + self._safe_list(critic.get("missing_evidence"))[:2]
        )

        decision = self._round_decision(
            critic_risk_score=critic.get("risk_score"),
            output_language=output_language,
        )

        if output_language == "en":
            synthesis = (
                f"The committee accepts that {context['title']} has validation potential, "
                f"but requires evidence before scale. Temporary decision: {decision}."
            )
            next_instruction = "Transform the remaining risks into validation tasks for the next execution step."
        else:
            synthesis = (
                f"Le comité accepte que {context['title']} possède un potentiel de validation, "
                f"mais exige des preuves avant le passage à l’échelle. Décision provisoire : {decision}."
            )
            next_instruction = "Transformer les risques restants en tâches de validation pour la prochaine étape d’exécution."

        return {
            "validated_points": validated_points,
            "remaining_risks": remaining_risks,
            "decision": decision,
            "synthesis": synthesis,
            "next_committee_instruction": next_instruction,
            "context_locked": True,
        }

    # ========================================================
    # Judge
    # ========================================================

    def _build_judge(
        self,
        *,
        rounds: List[Dict[str, Any]],
        context: Dict[str, str],
        analysis_data: Dict[str, Any],
        output_language: str,
    ) -> Dict[str, Any]:
        score = self._score_from_analysis(analysis_data)
        decision = self._final_decision(score, output_language)

        sellable_features = self._sellable_features(context, output_language)
        critical_risks = self._critical_risks(context, analysis_data, output_language)
        next_actions = self._next_actions(context, output_language)
        go_no_go_conditions = self._go_no_go_conditions(context, output_language)

        if output_language == "en":
            final_verdict = (
                f"{context['title']} should continue as a focused MVP validation project. "
                "The committee does not recommend full-scale development yet."
            )

            improved_idea_version = (
                f"Build {context['title']} as a focused solution for {context['target_users']} in {context['region']}, "
                f"centered on solving: {context['problem']}. The first version should cover {context['mvp_scope']} "
                "and prove weekly usage before adding advanced modules."
            )

            mvp_recommendation = (
                f"Launch a narrow MVP around {context['mvp_scope']}. Avoid broad platform features until user adoption is proven."
            )

            prototype_estimate = (
                f"Use the current financial estimation as the first budget reference: {context['budget_reference']}. "
                "Keep the prototype lightweight and prioritize reusable components."
            )

            cost_reduction_strategy = [
                "Reduce the MVP to one workflow and one target segment.",
                "Use existing hosting and open-source components where possible.",
                "Avoid custom integrations until a pilot confirms demand.",
                "Use manual onboarding during the first pilot instead of building automation too early.",
            ]

            business_model = (
                f"Start with pilot validation, then test {context['business_model']} only after users confirm value and willingness to pay."
            )

            committee_summary = (
                "The committee agrees on a conditional GO: continue validation, narrow the MVP, collect field evidence, then decide whether to scale."
            )

        else:
            final_verdict = (
                f"{context['title']} doit continuer comme projet de validation MVP ciblé. "
                "Le comité ne recommande pas encore un développement complet à grande échelle."
            )

            improved_idea_version = (
                f"Construire {context['title']} comme une solution ciblée pour {context['target_users']} en {context['region']}, "
                f"centrée sur le problème suivant : {context['problem']}. La première version doit couvrir {context['mvp_scope']} "
                "et prouver un usage hebdomadaire avant d’ajouter des modules avancés."
            )

            mvp_recommendation = (
                f"Lancer un MVP réduit autour de {context['mvp_scope']}. Éviter les fonctionnalités de plateforme large avant de prouver l’adoption."
            )

            prototype_estimate = (
                f"Utiliser l’estimation financière actuelle comme première référence budgétaire : {context['budget_reference']}. "
                "Garder le prototype léger et prioriser les composants réutilisables."
            )

            cost_reduction_strategy = [
                "Réduire le MVP à un seul flux et un seul segment cible.",
                "Utiliser l’hébergement existant et des composants open-source lorsque c’est possible.",
                "Éviter les intégrations personnalisées avant confirmation de la demande par pilote.",
                "Faire un onboarding manuel au premier pilote au lieu de construire trop tôt de l’automatisation.",
            ]

            business_model = (
                f"Commencer par une validation pilote, puis tester {context['business_model']} seulement après confirmation de la valeur et de la volonté de payer."
            )

            committee_summary = (
                "Le comité valide un GO conditionnel : continuer la validation, réduire le MVP, collecter des preuves terrain, puis décider du passage à l’échelle."
            )

        return {
            "format": "debate_room_judge_v7_project_review_committee",
            "role": "Executive Judge",
            "decision": decision,
            "final_verdict": final_verdict,
            "committee_decision_summary": committee_summary,
            "improved_idea_version": improved_idea_version,
            "mvp_recommendation": mvp_recommendation,
            "prototype_or_material_estimate": prototype_estimate,
            "cost_reduction_strategy": cost_reduction_strategy,
            "target_people": self._target_people(context, output_language),
            "target_zones": self._target_zones(context, output_language),
            "sellable_features": sellable_features,
            "business_model": business_model,
            "critical_risks": critical_risks,
            "go_no_go_conditions": go_no_go_conditions,
            "next_actions": next_actions,
            "score_reference": score,
            "confidence_level": "high" if score >= 7 else "medium",
            "manual_review_required": True,
            "context_locked": True,
            "output_language": output_language,
            "rounds_reviewed": len(rounds),
        }

    # ========================================================
    # Context
    # ========================================================

    def _context(
        self,
        *,
        title: str,
        description: str,
        industry: str,
        region: str,
        output_language: str,
        project_context: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> Dict[str, str]:
        structured = (
            project_context.get("structured_project_context")
            or analysis_data.get("structured_project_context")
            or analysis_data.get("project_intelligence", {}).get("structured_project_context")
            or {}
        )

        bmc = self._section(analysis_data, "business_model_canvas")
        financial = self._section(analysis_data, "financial_estimation")
        market = self._section(analysis_data, "market_study")
        personas = self._section(analysis_data, "persona_builder")

        clean_title = self._safe_text(
            structured.get("project_name")
            or structured.get("title")
            or project_context.get("title")
            or title,
            "Project",
        )

        clean_description = self._safe_text(
            structured.get("description")
            or project_context.get("description")
            or description,
            "",
        )

        clean_sector = self._safe_text(
            structured.get("sector")
            or structured.get("industry")
            or project_context.get("industry")
            or industry,
            "target sector",
        )

        clean_region = self._safe_text(
            structured.get("target_region")
            or structured.get("market_region")
            or project_context.get("market_region")
            or region,
            "target region",
        )

        target_users = self._first_text(
            structured.get("target_users"),
            project_context.get("target_users"),
            personas.get("target_segments"),
            market.get("target_customers"),
            market.get("customer_segments"),
            bmc.get("customer_segments"),
            "target users",
        )

        problem = self._safe_text(
            structured.get("problem")
            or structured.get("core_problem")
            or structured.get("main_problem")
            or structured.get("pain_point")
            or project_context.get("problem")
            or market.get("market_problem"),
            "",
        )

        if not problem:
            problem = self._extract_problem_from_description(clean_description)

        solution = self._first_text(
            structured.get("solution"),
            structured.get("solution_type"),
            structured.get("value_proposition"),
            project_context.get("solution"),
            bmc.get("value_propositions"),
            bmc.get("value_proposition"),
            clean_description,
            "the proposed solution",
        )

        mvp_scope = self._first_text(
            structured.get("mvp_scope"),
            project_context.get("mvp_scope"),
            financial.get("project_context_used", {}).get("mvp_scope") if isinstance(financial.get("project_context_used"), dict) else None,
            analysis_data.get("mvp_scope"),
            "a reduced MVP focused on the core workflow",
        )

        business_model = self._first_text(
            structured.get("business_model"),
            project_context.get("business_model"),
            bmc.get("business_model_note"),
            bmc.get("revenue_streams"),
            financial.get("pricing_model"),
            "pilot then subscription model",
        )

        budget_reference = self._first_text(
            financial.get("mvp_budget_estimate"),
            financial.get("initial_costs"),
            financial.get("funding_needs"),
            "lean MVP budget to validate during planning",
        )

        context = {
            "title": clean_title,
            "description": clean_description,
            "sector": clean_sector,
            "region": clean_region,
            "target_users": target_users,
            "problem": problem,
            "solution": solution,
            "mvp_scope": mvp_scope,
            "business_model": business_model,
            "budget_reference": budget_reference,
            "output_language": output_language,
        }

        allowed_context = self._allowed_context(context)

        return {
            key: self._sanitize_text(value, allowed_context=allowed_context)
            for key, value in context.items()
        }

    # ========================================================
    # Business content helpers
    # ========================================================

    def _committee(self, output_language: str) -> List[str]:
        return [
            "Moderator",
            "Project Owner",
            "CTO / Technical Lead",
            "Product Manager",
            "Market & Sales Manager",
            "CFO / Finance Manager",
            "Operations / Field Expert",
            "Customer Representative",
            "Executive Judge",
        ]

    def _opportunities(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                f"Validate demand with {context['target_users']} in {context['region']}.",
                f"Position {context['title']} as a focused solution for {context['sector']}.",
                "Use pilot evidence to refine pricing and onboarding.",
            ]

        return [
            f"Valider la demande avec {context['target_users']} en {context['region']}.",
            f"Positionner {context['title']} comme solution ciblée pour {context['sector']}.",
            "Utiliser les preuves du pilote pour améliorer le prix et l’onboarding.",
        ]

    def _assumptions(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                f"{context['target_users']} face the problem often enough.",
                "The MVP creates visible value within the first week of use.",
                "The buyer accepts a paid pilot or subscription after validation.",
            ]

        return [
            f"{context['target_users']} rencontrent le problème assez souvent.",
            "Le MVP crée une valeur visible dès la première semaine d’usage.",
            "L’acheteur accepte un pilote payant ou un abonnement après validation.",
        ]

    def _missing_evidence(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                "Interview evidence from the first target users.",
                "Pilot usage data.",
                "Real pricing feedback.",
                "Comparison with current alternatives.",
            ]

        return [
            "Preuves d’entretiens avec les premiers utilisateurs ciblés.",
            "Données d’usage pilote.",
            "Retour réel sur le prix.",
            "Comparaison avec les alternatives actuelles.",
        ]

    def _mitigation_requests(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                "Reduce the MVP to the smallest useful workflow.",
                "Define measurable success metrics before building.",
                "Test adoption with real users before scaling.",
            ]

        return [
            "Réduire le MVP au plus petit flux utile.",
            "Définir des métriques de succès mesurables avant développement.",
            "Tester l’adoption avec de vrais utilisateurs avant le passage à l’échelle.",
        ]

    def _sellable_features(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                f"Core workflow linked to {context['mvp_scope']}.",
                "Simple dashboard for daily tracking.",
                "User or record management adapted to the first target segment.",
                "Progress, status or activity visibility.",
                "Basic export or certificate/report generation if validated by users.",
            ]

        return [
            f"Flux principal lié à {context['mvp_scope']}.",
            "Tableau de bord simple pour le suivi quotidien.",
            "Gestion des utilisateurs ou dossiers adaptée au premier segment cible.",
            "Visibilité sur le progrès, le statut ou l’activité.",
            "Export basique ou génération de certificat/rapport si validé par les utilisateurs.",
        ]

    def _critical_risks(
        self,
        context: Dict[str, str],
        analysis_data: Dict[str, Any],
        output_language: str,
    ) -> List[str]:
        swot = self._section(analysis_data, "swot")
        startup_score = self._section(analysis_data, "startup_score")
        persona_builder = self._section(analysis_data, "persona_builder")

        extracted = []
        extracted.extend(self._safe_list(swot.get("threats"))[:2])
        extracted.extend(self._safe_list(startup_score.get("weaknesses"))[:2])
        extracted.extend(self._safe_list(persona_builder.get("persona_risks"))[:2])

        if output_language == "en":
            defaults = [
                "Users may keep current manual or generic alternatives.",
                "Willingness to pay may remain unproven.",
                "The MVP may become too broad before validation.",
                "Onboarding friction may slow adoption.",
            ]
        else:
            defaults = [
                "Les utilisateurs peuvent garder les alternatives manuelles ou génériques actuelles.",
                "La volonté de payer peut rester non prouvée.",
                "Le MVP peut devenir trop large avant validation.",
                "La friction d’onboarding peut ralentir l’adoption.",
            ]

        return self._unique_strings(extracted + defaults)[:6]

    def _target_people(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                context["target_users"],
                "Daily operational users",
                "Economic decision-makers",
                "Skeptical users who currently use manual alternatives",
            ]

        return [
            context["target_users"],
            "Utilisateurs opérationnels quotidiens",
            "Décideurs économiques",
            "Utilisateurs sceptiques qui utilisent actuellement des alternatives manuelles",
        ]

    def _target_zones(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                context["region"],
                "First pilot locations where interviews are easiest",
                "Expansion zones only after proof of adoption",
            ]

        return [
            context["region"],
            "Premières zones pilotes où les entretiens sont les plus faciles",
            "Zones d’expansion seulement après preuve d’adoption",
        ]

    def _go_no_go_conditions(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                "GO if at least 10 interviews confirm repeated pain.",
                "GO if pilot users complete the core workflow weekly.",
                "GO if at least one buyer accepts a real price discussion.",
                "NO-GO for scaling if users do not return after the first test.",
                "NO-GO for advanced features before the core MVP is used repeatedly.",
            ]

        return [
            "GO si au moins 10 entretiens confirment une douleur répétée.",
            "GO si les utilisateurs pilotes complètent le flux principal chaque semaine.",
            "GO si au moins un acheteur accepte une vraie discussion de prix.",
            "NO-GO passage à l’échelle si les utilisateurs ne reviennent pas après le premier test.",
            "NO-GO fonctionnalités avancées avant usage répété du MVP principal.",
        ]

    def _next_actions(self, context: Dict[str, str], output_language: str) -> List[str]:
        if output_language == "en":
            return [
                "Write a one-page MVP scope focused on the core workflow.",
                "Prepare an interview script for daily users and buyers.",
                "Recruit 10 to 20 target users for validation.",
                "Build a clickable prototype or minimal working MVP.",
                "Measure activation, weekly usage and willingness to pay.",
                "Update the report after pilot evidence is collected.",
            ]

        return [
            "Rédiger une page de périmètre MVP centrée sur le flux principal.",
            "Préparer un script d’entretien pour utilisateurs quotidiens et acheteurs.",
            "Recruter 10 à 20 utilisateurs ciblés pour validation.",
            "Construire un prototype cliquable ou un MVP minimal fonctionnel.",
            "Mesurer l’activation, l’usage hebdomadaire et la volonté de payer.",
            "Mettre à jour le rapport après collecte de preuves pilote.",
        ]

    def _evidence_used(self, analysis_data: Dict[str, Any], output_language: str) -> List[str]:
        available = []

        for key in [
            "market_study",
            "business_model_canvas",
            "financial_estimation",
            "swot",
            "startup_score",
            "persona_builder",
            "competitive_analysis",
            "fact_checker",
        ]:
            section = analysis_data.get(key)
            if isinstance(section, dict) and section:
                available.append(key)

        if available:
            return available

        if output_language == "en":
            return ["Project description", "Structured project context"]

        return ["Description du projet", "Contexte structuré du projet"]

    # ========================================================
    # Decisions and scoring
    # ========================================================

    def _round_decision(self, *, critic_risk_score: Any, output_language: str) -> str:
        try:
            risk = int(float(critic_risk_score))
        except Exception:
            risk = 7

        if output_language == "en":
            if risk >= 8:
                return "PIVOT_REQUIRED"
            if risk >= 6:
                return "CONDITIONAL_GO"
            return "GO"

        if risk >= 8:
            return "PIVOT_NÉCESSAIRE"
        if risk >= 6:
            return "GO_CONDITIONNEL"
        return "GO"

    def _final_decision(self, score: float, output_language: str) -> str:
        if output_language == "en":
            if score >= 7:
                return "CONDITIONAL_GO_FOR_MVP"
            if score >= 6:
                return "PIVOT_BEFORE_MVP"
            return "NO_GO_BEFORE_REPOSITIONING"

        if score >= 7:
            return "GO_CONDITIONNEL_POUR_MVP"
        if score >= 6:
            return "PIVOTER_AVANT_MVP"
        return "NO_GO_AVANT_REPOSITIONNEMENT"

    def _round_risk_score(self, round_number: int) -> int:
        risk_by_round = {
            1: 6,
            2: 7,
            3: 6,
            4: 7,
            5: 7,
        }

        return risk_by_round.get(round_number, 7)

    def _score_from_analysis(self, analysis_data: Dict[str, Any]) -> float:
        startup_score = self._section(analysis_data, "startup_score")

        for key in ["score", "startup_score", "overall_score", "final_score", "score_out_of_10"]:
            value = startup_score.get(key)
            try:
                if value is not None:
                    return round(float(value), 1)
            except Exception:
                continue

        try:
            return round(float(analysis_data.get("startup_score") or 7.0), 1)
        except Exception:
            return 7.0

    # ========================================================
    # Sanitization
    # ========================================================

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

        return text[:2200].strip()

    def _allowed_context(self, context: Dict[str, str]) -> str:
        return self._normalize(" ".join(str(value or "") for value in context.values()))

    # ========================================================
    # Fallback
    # ========================================================

    def _fallback_judge(
        self,
        *,
        context: Dict[str, str],
        output_language: str,
        error: str,
    ) -> Dict[str, Any]:
        if output_language == "en":
            return {
                "format": "debate_room_judge_v7_emergency_fallback",
                "role": "Executive Judge",
                "decision": "CONDITIONAL_GO_FOR_MVP",
                "final_verdict": "Continue only with a reduced MVP and field validation.",
                "committee_decision_summary": "Safe fallback used. Manual review recommended.",
                "improved_idea_version": f"Validate {context['title']} with a narrow MVP for {context['target_users']}.",
                "mvp_recommendation": "Build only the core workflow first.",
                "prototype_or_material_estimate": "Use a lean prototype budget and validate exact cost manually.",
                "cost_reduction_strategy": ["Reduce scope", "Use existing tools", "Avoid custom integrations early"],
                "target_people": [context["target_users"]],
                "target_zones": [context["region"]],
                "sellable_features": ["Core workflow", "Simple dashboard", "Basic reporting"],
                "business_model": "Pilot first, subscription only after validation.",
                "critical_risks": ["Adoption risk", "Pricing risk", "Scope creep"],
                "go_no_go_conditions": ["GO only after interviews and pilot usage."],
                "next_actions": ["Interview users", "Build a small MVP", "Test willingness to pay"],
                "error_handled": True,
                "error": error,
                "context_locked": True,
                "output_language": output_language,
            }

        return {
            "format": "debate_room_judge_v7_emergency_fallback",
            "role": "Executive Judge",
            "decision": "GO_CONDITIONNEL_POUR_MVP",
            "final_verdict": "Continuer seulement avec un MVP réduit et une validation terrain.",
            "committee_decision_summary": "Fallback sécurisé utilisé. Revue manuelle recommandée.",
            "improved_idea_version": f"Valider {context['title']} avec un MVP réduit pour {context['target_users']}.",
            "mvp_recommendation": "Construire seulement le flux principal en premier.",
            "prototype_or_material_estimate": "Utiliser un budget prototype léger et valider le coût exact manuellement.",
            "cost_reduction_strategy": ["Réduire le périmètre", "Utiliser des outils existants", "Éviter les intégrations personnalisées au début"],
            "target_people": [context["target_users"]],
            "target_zones": [context["region"]],
            "sellable_features": ["Flux principal", "Tableau de bord simple", "Reporting basique"],
            "business_model": "Pilote d’abord, abonnement seulement après validation.",
            "critical_risks": ["Risque d’adoption", "Risque de prix", "Élargissement excessif du périmètre"],
            "go_no_go_conditions": ["GO seulement après entretiens et usage pilote."],
            "next_actions": ["Interroger les utilisateurs", "Construire un petit MVP", "Tester la volonté de payer"],
            "error_handled": True,
            "error": error,
            "context_locked": True,
            "output_language": output_language,
        }

    # ========================================================
    # Generic helpers
    # ========================================================

    def _calculate_progress(
        self,
        *,
        completed_rounds: int,
        max_rounds: int,
        defender_done: bool,
        completed: bool,
    ) -> int:
        if completed:
            return 100

        base = int((completed_rounds / max_rounds) * 85)

        if defender_done:
            base += 5

        return max(0, min(95, base))

    def _normalize_max_rounds(self, max_rounds: int) -> int:
        try:
            requested = int(max_rounds)
        except Exception:
            requested = 5

        if requested < 5:
            return 5

        return min(5, requested)

    def _section(self, analysis_data: Dict[str, Any], key: str) -> Dict[str, Any]:
        value = analysis_data.get(key)
        return value if isinstance(value, dict) else {}

    def _first_text(self, *values: Any) -> str:
        for value in values:
            items = self._safe_list(value)

            if items:
                return items[0]

        return ""

    def _safe_text(self, value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback

        if isinstance(value, list):
            items = self._safe_list(value)
            return items[0] if items else fallback

        if isinstance(value, dict):
            items = self._safe_list(value)
            return items[0] if items else fallback

        clean = re.sub(r"\s+", " ", str(value or "").strip())

        return clean or fallback

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            result: List[str] = []

            for item in value:
                result.extend(self._safe_list(item))

            return self._unique_strings(result)

        if isinstance(value, dict):
            result: List[str] = []

            priority_keys = [
                "segment",
                "name",
                "title",
                "description",
                "summary",
                "value",
                "label",
                "text",
                "role",
                "main_pain",
                "expected_value",
            ]

            for key in priority_keys:
                if key in value:
                    result.extend(self._safe_list(value.get(key)))

            if not result:
                for item in value.values():
                    result.extend(self._safe_list(item))

            return self._unique_strings(result)

        clean = re.sub(r"\s+", " ", str(value or "").strip())

        if not clean:
            return []

        return [clean[:1200]]

    def _extract_problem_from_description(self, description: str) -> str:
        clean = self._safe_text(description)

        if not clean:
            return "the main operational problem described by the project"

        sentences = re.split(r"(?<=[.!?])\s+", clean)

        if sentences:
            return sentences[0][:320]

        return clean[:320]

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

    def _unique_strings(self, items: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for item in items:
            clean = re.sub(r"\s+", " ", str(item or "").strip())

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result

    async def _notify(self, state: Dict[str, Any]) -> None:
        if not self.step_callback:
            return

        try:
            await self.step_callback(dict(state))
        except Exception:
            logger.exception("[DebateRoomGraph] Step callback failed")
