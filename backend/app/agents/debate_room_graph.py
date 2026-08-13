from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from app.services.domain_integrity_guard import normalize_output_language

logger = logging.getLogger(__name__)

StepCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class DebateRoomGraph:
    """Deterministic Strategic Investment Committee.

    The committee consumes the locked Project Intelligence and Evidence packets.
    It never invents evidence. Every round exposes the questions, answers,
    confidence, unresolved points and meeting-preparation material required to
    defend the project in a real investor, jury or customer meeting.
    """

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
        analysis = analysis_data or {}
        context = self._context(
            title=title,
            description=description,
            industry=industry,
            region=region,
            project_context=project_context or {},
            analysis=analysis,
        )
        evidence = self._evidence_packet(analysis)
        round_count = max(1, min(int(max_rounds or 5), 5))
        committee = self._committee(language)
        room_title = self._t(
            language,
            "Debate Room Pro — Strategic Investment Committee",
            "Debate Room Pro — Comité stratégique d’investissement",
        )
        state: Dict[str, Any] = {
            "project_id": project_id,
            "format": "debate_room_pro_v9_investment_committee",
            "title": room_title,
            "status": "running",
            "committee": committee,
            "meeting_preparation": {},
            "current_step": "debate_room_started",
            "progress": 0,
            "rounds": [],
            "completed_steps": [],
            "failed_steps": [],
            "completed": False,
        }

        try:
            if context.get("project_archetype") == "b2b_workflow_saas":
                builders = [
                    self._round_problem,
                    self._round_market,
                    self._round_mvp,
                    self._round_finance,
                    self._round_decision,
                ][:round_count]
            else:
                builders = [
                    self._round_adaptive_problem,
                    self._round_adaptive_market,
                    self._round_adaptive_product,
                    self._round_adaptive_economics,
                    self._round_adaptive_decision,
                ][:round_count]
            rounds: List[Dict[str, Any]] = []
            for index, builder in enumerate(builders, start=1):
                item = builder(index, context, analysis, evidence, language)
                rounds.append(item)
                state.update(
                    {
                        "rounds": rounds,
                        "completed_steps": [f"round_{number}" for number in range(1, index + 1)],
                        "current_step": f"debate_room_round_{index}",
                        "progress": int((index / max(round_count, 1)) * 85),
                    }
                )
                await self._notify(state)

            judge = self._judge(rounds, context, analysis, evidence, language)
            meeting_preparation = self._global_meeting_preparation(
                rounds, context, language
            )
            state.update(
                {
                    "judge": judge,
                    "meeting_preparation": meeting_preparation,
                    "status": "completed",
                    "current_step": "debate_room_judge",
                    "progress": 100,
                    "completed": True,
                }
            )
            await self._notify(state)

            return {
                "debate_room": {
                    "format": "debate_room_pro_v9_investment_committee",
                    "title": room_title,
                    "status": "completed",
                    "max_rounds": round_count,
                    "committee": committee,
                    "rounds": rounds,
                    "judge": judge,
                    "meeting_preparation": meeting_preparation,
                    "meta": {
                        "progress": 100,
                        "completed": True,
                        "output_language": language,
                        "context_locked": True,
                        "llm_used": False,
                        "evidence_aware": True,
                        "questions_visible": True,
                        "meeting_preparation_enabled": True,
                    },
                    "context_locked": True,
                    "output_language": language,
                    "project_context_used": context,
                    "evidence_packet_used": evidence,
                }
            }
        except Exception as exc:
            logger.exception("[DebateRoomGraph] Failed")
            fallback = self._fallback(context, language, str(exc))
            return {
                "debate_room": {
                    "format": "debate_room_pro_v9_fallback",
                    "status": "completed_with_fallback",
                    "rounds": [],
                    "judge": fallback,
                    "meta": {
                        "progress": 100,
                        "completed": True,
                        "error": str(exc),
                        "fallback_used": True,
                    },
                    "output_language": language,
                    "context_locked": True,
                }
            }

    async def _notify(self, state: Dict[str, Any]) -> None:
        if not self.step_callback:
            return
        try:
            await self.step_callback(dict(state))
        except Exception:
            logger.exception("[DebateRoomGraph] step_callback failed")

    # ------------------------------------------------------------------
    # Round builders
    # ------------------------------------------------------------------

    def _adaptive_questions(
        self,
        *,
        number: int,
        language: str,
        specifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        questions: List[Dict[str, Any]] = []
        for index, spec in enumerate(specifications[:4], start=1):
            asked_by = spec.get("asked_by", "evidence_auditor")
            evidence_status = spec.get("status", "field_validation_required")
            explicit_confidence = spec.get("confidence")
            confidence = (
                float(explicit_confidence)
                if explicit_confidence is not None
                else self._adaptive_question_confidence(
                    asked_by=asked_by,
                    evidence_status=evidence_status,
                    round_number=number,
                )
            )
            questions.append(
                self._question(
                    round_number=number,
                    index=index,
                    asked_by=asked_by,
                    addressed_to=spec.get("addressed_to", "project_defender"),
                    question=spec["question"],
                    direct_answer=spec["answer"],
                    reasoning=spec["reasoning"],
                    confidence=confidence,
                    evidence_status=evidence_status,
                    unresolved=spec["unresolved"],
                    follow_up=spec["follow_up"],
                    likely_real_question=spec["likely"],
                    recommended_answer=spec["recommended"],
                    proofs=spec.get("proofs", []),
                    avoid=spec["avoid"],
                )
            )
        return questions

    def _round_adaptive_problem(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        actor = context["primary_target"]
        action = context["priority_workflow"]
        validation_unit = context.get("validation_unit") or self._t(language, "core user action", "action utilisateur principale")
        specs = [
            {
                "asked_by": "customer_problem_analyst",
                "question": self._frequency_question(context, language),
                "answer": self._t(language, "The project description defines the intended action, but real frequency and failure rate have not yet been measured.", "La description définit l’action visée, mais la fréquence réelle et le taux d’échec ne sont pas encore mesurés."),
                "reasoning": self._t(language, f"The first action to validate is: {action}.", f"La première action à valider est : {action}."),
                "unresolved": self._t(language, "Measure attempts, failures, delay and current alternatives with real users.", "Mesurer les tentatives, échecs, délais et alternatives actuelles avec de vrais utilisateurs."),
                "follow_up": self._t(language, "Which event will be counted as one real attempt?", "Quel événement sera compté comme une tentative réelle ?"),
                "likely": self._t(language, "What proves that the problem is frequent enough?", "Qu’est-ce qui prouve que le problème est assez fréquent ?"),
                "recommended": self._t(language, "We treat frequency as a hypothesis and will measure attempts and failed outcomes during a bounded field test.", "Nous traitons la fréquence comme une hypothèse et mesurerons les tentatives et résultats échoués pendant un test terrain limité."),
                "proofs": self._t_list(language, ["Observation log", "Attempt and failure baseline"], ["Journal d’observation", "Base des tentatives et échecs"]),
                "avoid": self._t(language, "Everyone needs this.", "Tout le monde en a besoin."),
            },
            {
                "asked_by": "customer_problem_analyst",
                "question": self._t(language, "Who initiates the action, who fulfils it and who can block it?", "Qui initie l’action, qui la réalise et qui peut la bloquer ?"),
                "answer": self._actor_map_answer(context, language),
                "reasoning": self._t(language, "Different actors may own usage, fulfilment, payment, trust or approval.", "Des acteurs différents peuvent porter l’usage, la réalisation, le paiement, la confiance ou l’approbation."),
                "unresolved": self._t(language, "Confirm the actor map and decision rights through interviews.", "Confirmer la carte des acteurs et les droits de décision par entretiens."),
                "follow_up": self._t(language, "Which actor has the strongest reason not to participate?", "Quel acteur a la raison la plus forte de ne pas participer ?"),
                "likely": self._t(language, "Who is the real customer?", "Qui est le vrai client ?"),
                "recommended": self._t(language, "We separate the primary user, the fulfilment partner, the payer and the operational gatekeeper before setting the offer.", "Nous séparons l’utilisateur principal, le partenaire de réalisation, le payeur et le gardien opérationnel avant de définir l’offre."),
                "proofs": self._t_list(language, ["Actor map", "Interview records"], ["Carte des acteurs", "Comptes rendus d’entretiens"]),
                "avoid": self._t(language, "The same person is obviously user and buyer.", "La même personne est évidemment utilisateur et acheteur."),
            },
            {
                "asked_by": "risk_execution_officer",
                "question": self._t(language, "Why would the target switch from the current alternative?", "Pourquoi la cible quitterait-elle l’alternative actuelle ?"),
                "answer": self._t(language, "Switching is credible only if the project improves a measurable outcome without adding unacceptable friction or risk.", "Le changement est crédible seulement si le projet améliore un résultat mesurable sans ajouter une friction ou un risque inacceptable."),
                "reasoning": context["problem"],
                "unresolved": self._t(language, "Identify the strongest existing alternative and switching cost.", "Identifier l’alternative actuelle la plus forte et le coût de changement."),
                "follow_up": self._t(language, "Which measurable result must improve in the first session?", "Quel résultat mesurable doit s’améliorer dès la première session ?"),
                "likely": self._t(language, "Why is the current method not good enough?", "Pourquoi la méthode actuelle n’est-elle pas suffisante ?"),
                "recommended": self._t(language, "The pilot will compare completion, delay, failure, trust and repeat use against the current alternative.", "Le pilote comparera réalisation, délai, échec, confiance et réutilisation face à l’alternative actuelle."),
                "proofs": self._t_list(language, ["Before/after comparison", "Switching-cost interviews"], ["Comparaison avant/après", "Entretiens sur le coût de changement"]),
                "avoid": self._t(language, "Digital is automatically better.", "Le numérique est automatiquement meilleur."),
            },
            {
                "asked_by": "evidence_auditor",
                "question": self._t(language, "What result would falsify the problem hypothesis?", "Quel résultat réfuterait l’hypothèse du problème ?"),
                "answer": self._t(language, "The hypothesis fails if the action is rare, existing alternatives are satisfactory or the target refuses the proposed change.", "L’hypothèse échoue si l’action est rare, les alternatives satisfaisantes ou la cible refuse le changement proposé."),
                "reasoning": self._t(language, "A decision-ready analysis must define failure conditions before the pilot.", "Une analyse décisionnelle doit définir les conditions d’échec avant le pilote."),
                "unresolved": self._t(language, "Set explicit problem-frequency and switching thresholds.", "Définir des seuils explicites de fréquence et de changement."),
                "follow_up": self._t(language, "Who approves the stop or pivot decision?", "Qui approuve la décision d’arrêt ou pivot ?"),
                "likely": self._t(language, "What would make you stop?", "Qu’est-ce qui vous ferait arrêter ?"),
                "recommended": self._t(language, "We will stop or pivot when the predefined frequency, outcome or adoption thresholds are not met.", "Nous arrêterons ou pivoterons lorsque les seuils prédéfinis de fréquence, résultat ou adoption ne sont pas atteints."),
                "proofs": self._t_list(language, ["Pre-registered thresholds"], ["Seuils préenregistrés"]),
                "avoid": self._t(language, "The problem cannot be disproved.", "Le problème ne peut pas être réfuté."),
            },
        ]
        questions = self._adaptive_questions(number=number, language=language, specifications=specs)
        return self._round(number, language,
            self._t(language, "Problem, actors and behaviour", "Problème, acteurs et comportement"),
            self._t(language, "Validate frequency, actor roles and behaviour change before building the full product.", "Valider fréquence, rôles et changement de comportement avant de construire le produit complet."),
            self._t(language, "Is the problem frequent and important enough for the required actors to change behaviour?", "Le problème est-il assez fréquent et important pour que les acteurs nécessaires changent de comportement ?"),
            ["project_intelligence", "customer_observation", "actor_map"],
            [self._t(language, f"The project defines a measurable action: {action}.", f"Le projet définit une action mesurable : {action}."), self._t(language, "The actor map can be tested before full development.", "La carte des acteurs peut être testée avant le développement complet.")],
            [self._t(language, "Hypothesis: the primary actor experiences repeated pain and the required partners will participate.", "Hypothèse : l’acteur principal rencontre une douleur répétée et les partenaires nécessaires participeront.")],
            context.get("risk_dimensions")[:2] or [self._t(language, "The action may be too rare or existing alternatives may be sufficient.", "L’action peut être trop rare ou les alternatives actuelles suffisantes.")],
            context.get("evidence_needs")[:2] or [self._t(language, "Observed attempts and actor interviews.", "Tentatives observées et entretiens acteurs.")],
            [], questions, "CONDITIONAL_GO",
            self._t(language, "The project is defined enough for a behavioural validation, but frequency and actor participation remain unproven.", "Le projet est assez défini pour une validation comportementale, mais la fréquence et la participation des acteurs restent non prouvées."),
            self._t(language, "Observe the core action and validate every required actor.", "Observer l’action principale et valider chaque acteur nécessaire."),
            [self._t(language, "The core action occurs repeatedly and produces measurable current loss.", "L’action principale se produit de manière répétée et crée une perte actuelle mesurable."), self._t(language, "Every required actor accepts the proposed role in a pilot.", "Chaque acteur nécessaire accepte son rôle dans un pilote.")],
            [self._t(language, "The problem is rare or the required actors refuse to participate.", "Le problème est rare ou les acteurs nécessaires refusent de participer.")])

    def _round_adaptive_market(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        sources = evidence.get("sources") or []
        source_count = len(sources)
        competitors = self._section(analysis, "competitive_analysis")
        direct_count = int(self._number(competitors.get("local_competitors_count"), 0))
        specs = [
            {"asked_by":"market_competition_analyst", "question":self._t(language,"Which verified products or services solve the same validation unit for the same actors?","Quels produits ou services vérifiés résolvent la même unité de validation pour les mêmes acteurs ?"), "answer":self._t(language,f"The retained evidence currently contains {source_count} unique source(s) and {direct_count} verified local direct competitor(s).",f"Les preuves retenues contiennent actuellement {source_count} source(s) unique(s) et {direct_count} concurrent(s) direct(s) local(aux) vérifié(s)."), "reasoning":self._t(language,"Articles, directories and adjacent products must not be presented as direct competitors.","Les articles, annuaires et produits adjacents ne doivent pas être présentés comme concurrents directs."), "confidence":0.7 if source_count else 0.3, "status":"supported" if source_count else "not_confirmed", "unresolved":self._t(language,"Manually verify product function, active geography, target actors and current activity.","Vérifier manuellement la fonction, la géographie active, les acteurs ciblés et l’activité actuelle."), "follow_up":self._t(language,"Which source was manually verified most recently?","Quelle source a été vérifiée manuellement le plus récemment ?"), "likely":self._t(language,"Who are the closest alternatives?","Quelles sont les alternatives les plus proches ?"), "recommended":self._t(language,"We separate direct products, adjacent solutions, evidence pages and offline alternatives; only verified product evidence enters the direct list.","Nous séparons produits directs, solutions adjacentes, pages de preuve et alternatives hors ligne ; seules les preuves produit vérifiées entrent dans la liste directe."), "proofs":self._t_list(language,["Verified product pages","Feature and actor comparison"],["Pages produit vérifiées","Comparaison fonctionnalités et acteurs"]), "avoid":self._t(language,"There is no competition.","Il n’existe aucune concurrence.")},
            {"asked_by":"customer_problem_analyst", "question":self._t(language,"What do the target actors use today instead of the project?","Qu’utilisent aujourd’hui les acteurs ciblés à la place du projet ?"), "answer":self._t(language,"The strongest alternative may be an offline process, direct contact, an incumbent platform or simply abandoning the action.","L’alternative la plus forte peut être un processus hors ligne, un contact direct, une plateforme établie ou l’abandon de l’action."), "reasoning":self._t(language,"Replacement behaviour matters more than a feature-only competitor list.","Le comportement de remplacement compte davantage qu’une liste de fonctionnalités."), "unresolved":self._t(language,"Observe the actual current journey and switching cost.","Observer le parcours actuel réel et le coût de changement."), "follow_up":self._t(language,"Which alternative is hardest to replace and why?","Quelle alternative est la plus difficile à remplacer et pourquoi ?"), "likely":self._t(language,"Why will users switch?","Pourquoi les utilisateurs changeront-ils ?"), "recommended":self._t(language,"We will prove a measurable advantage against the current behaviour, not assume that a new app is enough.","Nous prouverons un avantage mesurable face au comportement actuel, sans supposer qu’une nouvelle application suffit."), "proofs":self._t_list(language,["Current-journey map","Switching-cost evidence"],["Carte du parcours actuel","Preuves du coût de changement"]), "avoid":self._t(language,"Our features are better, so users will switch.","Nos fonctionnalités sont meilleures, donc les utilisateurs changeront.")},
            {"asked_by":"evidence_auditor", "question":self._t(language,"Do the retained sources prove local demand or only feasibility and context?","Les sources retenues prouvent-elles la demande locale ou seulement la faisabilité et le contexte ?"), "answer":self._t(language,"International or adjacent evidence can show feasibility, but local demand and willingness to pay require compatible local evidence and field tests.","Les preuves internationales ou adjacentes peuvent montrer la faisabilité, mais la demande locale et la volonté de payer exigent des preuves locales compatibles et des tests terrain."), "reasoning":self._t(language,f"The current evidence level is {evidence.get('level','low')}.",f"Le niveau de preuve actuel est {evidence.get('level','low')}."), "unresolved":self._t(language,"Find category-compatible local data and run interviews or transactions.","Trouver des données locales compatibles et réaliser entretiens ou transactions."), "follow_up":self._t(language,"Which local source has visible methodology?","Quelle source locale possède une méthodologie visible ?"), "likely":self._t(language,"What proves demand in the launch market?","Qu’est-ce qui prouve la demande sur le marché de lancement ?"), "recommended":self._t(language,"We currently treat local demand as a hypothesis and will validate it with compatible data and a bounded pilot.","Nous traitons actuellement la demande locale comme une hypothèse et la validerons avec des données compatibles et un pilote limité."), "proofs":self._t_list(language,["Official or independent local data","Pilot evidence"],["Données locales officielles ou indépendantes","Preuves du pilote"]), "avoid":self._t(language,"A search result proves demand.","Un résultat de recherche prouve la demande.")},
            {"asked_by":"red_team_challenger", "question":self._t(language,"Could an apparent market gap mean weak demand rather than opportunity?","Un espace de marché apparent peut-il signifier une faible demande plutôt qu’une opportunité ?"), "answer":self._t(language,"Yes. Absence of a verified direct competitor is ambiguous and never proves an attractive empty market.","Oui. L’absence de concurrent direct vérifié est ambiguë et ne prouve jamais un marché vide attractif."), "reasoning":self._t(language,"Opportunity requires both demand evidence and a credible advantage against alternatives.","L’opportunité exige des preuves de demande et un avantage crédible face aux alternatives."), "unresolved":self._t(language,"Define what evidence would change the positioning.","Définir quelle preuve modifierait le positionnement."), "follow_up":self._t(language,"What finding would trigger a pivot?","Quel résultat déclencherait un pivot ?"), "likely":self._t(language,"Why has nobody won this market already?","Pourquoi personne n’a déjà gagné ce marché ?"), "recommended":self._t(language,"We do not call absence a gap; the pilot will determine whether it reflects unmet demand, weak urgency or structural constraints.","Nous n’appelons pas l’absence un gap ; le pilote déterminera si elle reflète une demande non satisfaite, une faible urgence ou des contraintes structurelles."), "proofs":self._t_list(language,["Alternative map","Demand evidence"],["Carte des alternatives","Preuves de demande"]), "avoid":self._t(language,"No competitor means guaranteed opportunity.","Aucun concurrent signifie une opportunité garantie.")},
        ]
        questions=self._adaptive_questions(number=number,language=language,specifications=specs)
        return self._round(number,language,self._t(language,"Market, alternatives and evidence","Marché, alternatives et preuves"),self._t(language,"Separate direct competitors, adjacent solutions, evidence pages and current alternatives.","Séparer concurrents directs, solutions adjacentes, pages de preuve et alternatives actuelles."),self._t(language,"Is there compatible evidence that the project can win in the launch market?","Existe-t-il des preuves compatibles que le projet peut gagner sur le marché de lancement ?"),["competitive_analysis","forgecrawler","fact_check_report"],[self._t(language,f"The source pipeline retained {source_count} unique source(s) for review.",f"Le pipeline de sources a retenu {source_count} source(s) unique(s) à examiner.")],[self._t(language,"Hypothesis: the project offers a meaningful advantage against the strongest current alternative.","Hypothèse : le projet offre un avantage significatif face à l’alternative actuelle la plus forte.")],[self._t(language,"Search evidence may be incomplete or category-incompatible.","Les preuves de recherche peuvent être incomplètes ou incompatibles avec la catégorie.")],self._global_missing_evidence(analysis,language)[:3],[],questions,"CONDITIONAL_GO",self._t(language,"The market can be tested, but source compatibility, local demand and switching behaviour remain bounded evidence questions.","Le marché peut être testé, mais la compatibilité des sources, la demande locale et le changement restent des questions de preuve."),self._t(language,"Verify the closest alternatives and collect local behavioural evidence.","Vérifier les alternatives les plus proches et collecter des preuves comportementales locales."),[self._t(language,"A measurable advantage is demonstrated against the strongest alternative.","Un avantage mesurable est démontré face à l’alternative la plus forte."),self._t(language,"At least one compatible local demand signal is observed.","Au moins un signal local de demande compatible est observé.")],[self._t(language,"No advantage is observed or structural constraints make the market inaccessible.","Aucun avantage n’est observé ou des contraintes structurelles rendent le marché inaccessible.")])

    def _round_adaptive_product(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        action=context["priority_workflow"]; metrics=context.get("success_metrics") or []
        metric_text=", ".join(metrics[:3]) if metrics else self._t(language,"completion, repeat use and reliability","réalisation, réutilisation et fiabilité")
        specs=[
            {"asked_by":"product_technology_architect","question":self._t(language,"What is the smallest complete experience that proves value?","Quelle est la plus petite expérience complète qui prouve la valeur ?"),"answer":self._t(language,f"The first test should cover one end-to-end action: {action}.",f"Le premier test doit couvrir une action de bout en bout : {action}."),"reasoning":self._t(language,"A partial screen or feature does not prove that the user reaches the intended outcome.","Un écran ou une fonctionnalité partielle ne prouve pas que l’utilisateur atteint le résultat visé."),"confidence":0.7,"status":"estimated","unresolved":self._t(language,"Define start, success, failure and recovery events.","Définir les événements de départ, succès, échec et reprise."),"follow_up":self._t(language,"Which features can be removed without breaking the end-to-end test?","Quelles fonctionnalités peuvent être retirées sans casser le test de bout en bout ?"),"likely":self._t(language,"What exactly is in the MVP?","Que contient exactement le MVP ?"),"recommended":self._t(language,"The MVP includes only the data and steps required to complete and measure the core action; secondary features are excluded.","Le MVP contient seulement les données et étapes nécessaires pour réaliser et mesurer l’action principale ; les fonctions secondaires sont exclues."),"proofs":self._t_list(language,["Clickable or operational flow","Explicit exclusions"],["Parcours cliquable ou opérationnel","Exclusions explicites"]),"avoid":self._t(language,"The MVP includes every requested feature.","Le MVP contient toutes les fonctionnalités demandées.")},
            {"asked_by":"product_technology_architect","question":self._t(language,"Can the experience work in the real user environment?","L’expérience peut-elle fonctionner dans l’environnement réel ?"),"answer":self._t(language,"Technical plausibility is not enough; the pilot must test the real device, network, data, partner and operating conditions.","La plausibilité technique ne suffit pas ; le pilote doit tester l’appareil, le réseau, les données, partenaires et conditions réelles."),"reasoning":self._t(language,f"Acceptance should be measured through {metric_text}.",f"L’acceptation doit être mesurée par {metric_text}."),"unresolved":self._t(language,"Define environment-specific acceptance and recovery criteria.","Définir des critères d’acceptation et de reprise propres à l’environnement."),"follow_up":self._t(language,"What happens after a failed or interrupted action?","Que se passe-t-il après une action échouée ou interrompue ?"),"likely":self._t(language,"How reliable is the solution in real conditions?","Quelle est la fiabilité de la solution en conditions réelles ?"),"recommended":self._t(language,"We will test the complete journey, failure states, recovery and operational ownership before scaling.","Nous testerons le parcours complet, les états d’échec, la reprise et la responsabilité opérationnelle avant expansion."),"proofs":self._t_list(language,["Environment test results","Failure and recovery log"],["Résultats des tests d’environnement","Journal d’échec et reprise"]),"avoid":self._t(language,"It worked once in development.","Cela a fonctionné une fois en développement.")},
            {"asked_by":"risk_execution_officer","question":self._t(language,"Which technical or operational failure can destroy repeated use?","Quel échec technique ou opérationnel peut détruire l’usage répété ?"),"answer":self._t(language,"The blocking failure depends on the archetype and must be selected from the project risk dimensions, not a generic SaaS template.","L’échec bloquant dépend de l’archétype et doit venir des risques du projet, pas d’un template SaaS générique."),"reasoning":"; ".join(context.get("risk_dimensions")[:3]),"confidence":0.65,"status":"supported","unresolved":self._t(language,"Assign an owner, threshold and mitigation to each blocking risk.","Attribuer un responsable, un seuil et une réduction à chaque risque bloquant."),"follow_up":self._t(language,"What is the rollback or safe fallback?","Quel est le retour arrière ou mode sûr ?"),"likely":self._t(language,"What can make users abandon after the first attempt?","Qu’est-ce qui peut faire abandonner après la première tentative ?"),"recommended":self._t(language,"We will measure the archetype-specific failure modes and stop when reliability, trust or operational thresholds are missed.","Nous mesurerons les modes d’échec propres à l’archétype et arrêterons lorsque les seuils de fiabilité, confiance ou opérations ne sont pas atteints."),"proofs":self._t_list(language,["Risk register","Rollback test"],["Registre des risques","Test de retour arrière"]),"avoid":self._t(language,"There are no critical technical risks.","Il n’existe aucun risque technique critique.")},
            {"asked_by":"red_team_challenger","question":self._t(language,"Could the team deliver the product while proving no user value?","L’équipe peut-elle livrer le produit sans prouver de valeur utilisateur ?"),"answer":self._t(language,"Yes. Delivery and validation are separate; success requires a completed outcome, repeated use and an improvement against the baseline.","Oui. Livraison et validation sont distinctes ; le succès exige un résultat réalisé, un usage répété et une amélioration face à la base."),"reasoning":self._t(language,"Feature completion is not a customer or business outcome.","La livraison de fonctionnalités n’est pas un résultat client ou business."),"unresolved":self._t(language,"Put outcome metrics in the MVP Definition of Done.","Mettre les métriques de résultat dans la Definition of Done du MVP."),"follow_up":self._t(language,"Which metric can fail even if the application works?","Quelle métrique peut échouer même si l’application fonctionne ?"),"likely":self._t(language,"How do you know the MVP creates value?","Comment savez-vous que le MVP crée de la valeur ?"),"recommended":self._t(language,"We judge the MVP by successful outcomes, repeat behaviour and measurable improvement, not by deployed features.","Nous jugeons le MVP par les résultats réussis, le comportement répété et l’amélioration mesurable, pas par les fonctionnalités déployées."),"proofs":self._t_list(language,["Outcome dashboard","Baseline comparison"],["Tableau des résultats","Comparaison à la base"]),"avoid":self._t(language,"The product works, therefore the idea is validated.","Le produit fonctionne, donc l’idée est validée.")},
        ]
        questions=self._adaptive_questions(number=number,language=language,specifications=specs)
        return self._round(number,language,self._t(language,"Product, delivery and real-world feasibility","Produit, réalisation et faisabilité réelle"),self._t(language,"Reduce the first release to one complete, measurable validation unit.","Réduire la première version à une unité de validation complète et mesurable."),self._t(language,"Can the smallest complete experience prove value and reliability in real conditions?","La plus petite expérience complète peut-elle prouver valeur et fiabilité en conditions réelles ?"),["project_intelligence","solution_analysis","risk_dimensions"],[self._t(language,f"A focused pilot can begin with: {action}.",f"Un pilote ciblé peut commencer par : {action}."),self._t(language,f"The key metrics are: {metric_text}.",f"Les métriques clés sont : {metric_text}.")],[self._t(language,"Hypothesis: the smallest complete experience produces a measurable first outcome.","Hypothèse : la plus petite expérience complète produit un premier résultat mesurable.")],context.get("risk_dimensions")[:3],context.get("evidence_needs")[:3],[],questions,"CONDITIONAL_GO",self._t(language,"The product is testable when the MVP is defined by an end-to-end outcome and archetype-specific acceptance criteria.","Le produit est testable lorsque le MVP est défini par un résultat de bout en bout et des critères propres à l’archétype."),self._t(language,"Prototype the complete core action and test outcome, failure and recovery.","Prototyper l’action principale complète et tester résultat, échec et reprise."),[self._t(language,"Target users complete the core action and repeat it under real conditions.","Les utilisateurs ciblés réalisent l’action principale et la répètent en conditions réelles."),self._t(language,"Reliability and recovery meet the predefined thresholds.","La fiabilité et la reprise respectent les seuils prédéfinis.")],[self._t(language,"The experience fails, creates unacceptable risk or users do not repeat it.","L’expérience échoue, crée un risque inacceptable ou les utilisateurs ne la répètent pas.")])

    def _round_adaptive_economics(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        model=context["business_model"]; unit=context.get("validation_unit") or self._t(language,"successful unit","unité réussie")
        specs=[
            {"asked_by":"business_financial_analyst","question":self._t(language,"Who pays, for which outcome and at what decision point?","Qui paie, pour quel résultat et à quel moment de décision ?"),"answer":self._payer_answer(context, language),"reasoning":self._t(language,"A monetization hypothesis is not payment evidence.","Une hypothèse de monétisation n’est pas une preuve de paiement."),"confidence":0.4,"status":"field_validation_required","unresolved":self._t(language,"Test concrete offers with the real payer.","Tester des offres concrètes avec le vrai payeur."),"follow_up":self._t(language,"What budget, transaction or value event triggers payment?","Quel budget, transaction ou événement de valeur déclenche le paiement ?"),"likely":self._t(language,"Who is the paying customer?","Qui est le client payeur ?"),"recommended":self._t(language,"The payer remains a hypothesis until a real decision-maker accepts or rejects a concrete offer tied to a measurable outcome.","Le payeur reste une hypothèse jusqu’à ce qu’un vrai décideur accepte ou refuse une offre concrète liée à un résultat mesurable."),"proofs":self._t_list(language,["Offer tests","Decision rationale"],["Tests d’offres","Justification de décision"]),"avoid":self._t(language,"Users like it, so they will pay.","Les utilisateurs l’aiment, donc ils paieront.")},
            {"asked_by":"business_financial_analyst","question":self._t(language,f"What is the contribution margin per successful {unit}?",f"Quelle est la marge contributive par {unit} réussie ?"),"answer":self._t(language,"The margin is unknown until direct delivery, partner, support, infrastructure, incentive and payment costs are measured.","La marge est inconnue avant mesure des coûts directs de réalisation, partenaires, support, infrastructure, incitations et paiement."),"reasoning":self._t(language,"Revenue without variable delivery cost is not unit economics.","Un revenu sans coût variable de réalisation n’est pas une économie unitaire."),"unresolved":self._t(language,"Build a bottom-up unit-cost model from the pilot.","Construire un modèle bottom-up des coûts unitaires à partir du pilote."),"follow_up":self._t(language,"Which cost grows directly with each successful unit?","Quel coût augmente directement avec chaque unité réussie ?"),"likely":self._t(language,"What are your unit economics?","Quelle est votre économie unitaire ?"),"recommended":self._t(language,"We will calculate contribution from observed revenue minus every variable delivery and support cost, then include acquisition and retention.","Nous calculerons la contribution avec le revenu observé moins chaque coût variable de réalisation et support, puis intégrerons acquisition et rétention."),"proofs":self._t_list(language,["Bottom-up cost model","Pilot operations log"],["Modèle de coût bottom-up","Journal d’opérations du pilote"]),"avoid":self._t(language,"Cloud hosting is cheap, so margins are high.","Le cloud est bon marché, donc les marges sont élevées.")},
            {"asked_by":"risk_execution_officer","question":self._t(language,"Can acquisition, incentives, operations or support structurally exceed revenue?","L’acquisition, les incitations, les opérations ou le support peuvent-ils dépasser structurellement le revenu ?"),"answer":self._t(language,"Yes. The dominant cost depends on the archetype and must be measured during the first complete pilot.","Oui. Le coût dominant dépend de l’archétype et doit être mesuré pendant le premier pilote complet."),"reasoning":"; ".join(context.get("risk_dimensions")[:3]),"unresolved":self._t(language,"Set a maximum acceptable cost and support burden before launch.","Définir un coût et une charge de support maximum acceptables avant lancement."),"follow_up":self._t(language,"Which cost has the highest uncertainty?","Quel coût possède la plus forte incertitude ?"),"likely":self._t(language,"Can this model scale profitably?","Ce modèle peut-il passer à l’échelle de manière rentable ?"),"recommended":self._t(language,"We will not claim scalability until the pilot measures acquisition, fulfilment, support, repeat use and contribution margin.","Nous ne prétendrons pas pouvoir passer à l’échelle avant mesure de l’acquisition, réalisation, support, réutilisation et marge contributive."),"proofs":self._t_list(language,["Cost sensitivity analysis","Support log"],["Analyse de sensibilité des coûts","Journal de support"]),"avoid":self._t(language,"Scale will automatically solve the economics.","L’échelle résoudra automatiquement l’économie.")},
            {"asked_by":"evidence_auditor","question":self._t(language,"Which financial numbers are quotes, observations, estimates or hypotheses?","Quels chiffres financiers sont des devis, observations, estimations ou hypothèses ?"),"answer":self._t(language,"Current figures remain planning estimates unless tied to a quote, observed transaction, paid offer or pilot cost.","Les chiffres actuels restent des estimations de planification sauf s’ils sont liés à un devis, une transaction observée, une offre payée ou un coût pilote."),"reasoning":self._t(language,"Financial confidence cannot exceed the quality of the underlying evidence.","La confiance financière ne peut dépasser la qualité des preuves sous-jacentes."),"unresolved":self._t(language,"Label every figure and replace assumptions with direct evidence.","Étiqueter chaque chiffre et remplacer les hypothèses par des preuves directes."),"follow_up":self._t(language,"Which estimate can become a quote this week?","Quelle estimation peut devenir un devis cette semaine ?"),"likely":self._t(language,"How reliable is the financial model?","Quelle est la fiabilité du modèle financier ?"),"recommended":self._t(language,"The model is preliminary; the next version will use provider quotes and observed pilot revenue, cost, retention and support data.","Le modèle est préliminaire ; la prochaine version utilisera des devis et les données observées de revenu, coût, rétention et support."),"proofs":self._t_list(language,["Provider quotes","Observed pilot ledger"],["Devis fournisseurs","Registre observé du pilote"]),"avoid":self._t(language,"The forecast is accurate because AI calculated it.","La prévision est exacte parce que l’IA l’a calculée.")},
        ]
        questions=self._adaptive_questions(number=number,language=language,specifications=specs)
        return self._round(number,language,self._t(language,"Business model and unit economics","Modèle économique et économie unitaire"),self._t(language,"Separate a plausible monetization model from payment and contribution evidence.","Séparer un modèle plausible des preuves de paiement et contribution."),self._t(language,"Can the project earn viable contribution from a successful validation unit?","Le projet peut-il obtenir une contribution viable par unité de validation réussie ?"),["business_model_canvas","financial_estimation","pilot_economics"],[self._t(language,f"The current monetization hypothesis is: {model}.",f"L’hypothèse actuelle de monétisation est : {model}."),self._t(language,"A bounded offer and cost test can be run before scaling.","Un test limité d’offre et de coûts peut être réalisé avant expansion.")],[self._t(language,"Hypothesis: the payer accepts a concrete offer and contribution remains positive.","Hypothèse : le payeur accepte une offre concrète et la contribution reste positive.")],context.get("risk_dimensions")[:3],context.get("evidence_needs")[:3],[],questions,"CONDITIONAL_GO",self._t(language,"The model deserves a real offer and unit-cost test, not a scale commitment.","Le modèle mérite un vrai test d’offre et de coût unitaire, pas un engagement de croissance."),self._t(language,"Test concrete offers and measure every variable cost around the successful unit.","Tester des offres concrètes et mesurer chaque coût variable autour de l’unité réussie."),[self._t(language,"At least one real payer accepts a concrete offer.","Au moins un vrai payeur accepte une offre concrète."),self._t(language,"Observed contribution margin is positive at the pilot level.","La marge contributive observée est positive au niveau pilote.")],[self._t(language,"Payers reject the value-price relationship or variable cost structurally exceeds revenue.","Les payeurs rejettent le rapport valeur-prix ou le coût variable dépasse structurellement le revenu.")])

    def _round_adaptive_decision(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        metrics=context.get("success_metrics") or []
        metric_text=", ".join(metrics[:4]) if metrics else self._t(language,"successful outcome, repeat use, reliability and contribution","résultat réussi, usage répété, fiabilité et contribution")
        specs=[
            {"asked_by":"committee_chair","addressed_to":"all_committee_members","question":self._t(language,"Should the project proceed to a bounded pilot, pivot or stop?","Le projet doit-il passer à un pilote limité, pivoter ou s’arrêter ?"),"answer":self._t(language,"Proceed only to a bounded pilot while blocking evidence is collected.","Passer uniquement à un pilote limité pendant la collecte des preuves bloquantes."),"reasoning":self._t(language,f"The decision must be based on {metric_text} and the current evidence level {evidence.get('level','low')}.",f"La décision doit reposer sur {metric_text} et le niveau de preuve actuel {evidence.get('level','low')}."),"confidence":0.75,"status":"committee_synthesis","unresolved":self._t(language,"Name the pilot owner, cohort, dates, metrics and stop conditions.","Nommer le responsable, la cohorte, les dates, métriques et conditions d’arrêt."),"follow_up":self._t(language,"Which condition blocks the next investment decision?","Quelle condition bloque la prochaine décision d’investissement ?"),"likely":self._t(language,"What is the decision today?","Quelle est la décision aujourd’hui ?"),"recommended":self._t(language,"The decision is Conditional Go for a bounded pilot, not approval for full rollout or scaling.","La décision est un GO conditionnel pour un pilote limité, pas une approbation du déploiement complet ou de l’expansion."),"proofs":self._t_list(language,["Pilot charter","Decision scorecard"],["Charte du pilote","Tableau de décision"]),"avoid":self._t(language,"The score means we should build everything.","Le score signifie qu’il faut tout construire.")},
            {"asked_by":"red_team_challenger","question":self._t(language,"Which single assumption can destroy the project?","Quelle hypothèse unique peut détruire le projet ?"),"answer":self._t(language,"The project fails if the required actors do not complete and repeat the validation unit at viable risk and contribution.","Le projet échoue si les acteurs nécessaires ne réalisent et ne répètent pas l’unité de validation avec un risque et une contribution viables."),"reasoning":self._t(language,"Adoption, delivery and economics are jointly falsifiable.","Adoption, réalisation et économie sont falsifiables ensemble."),"unresolved":self._t(language,"Pre-register the decisive failure threshold.","Préenregistrer le seuil d’échec décisif."),"follow_up":self._t(language,"What exact result triggers a pivot?","Quel résultat exact déclenche un pivot ?"),"likely":self._t(language,"What would make you stop?","Qu’est-ce qui vous ferait arrêter ?"),"recommended":self._t(language,"We will stop or pivot when the core outcome, repeat behaviour, risk or contribution threshold is missed.","Nous arrêterons ou pivoterons lorsque le résultat principal, la répétition, le risque ou la contribution manque le seuil."),"proofs":self._t_list(language,["Predefined no-go thresholds"],["Seuils NO-GO prédéfinis"]),"avoid":self._t(language,"We will keep improving until it works.","Nous continuerons à améliorer jusqu’à ce que cela fonctionne.")},
            {"asked_by":"evidence_auditor","question":self._t(language,"Which claims are supported and which remain hypotheses?","Quelles affirmations sont soutenues et lesquelles restent des hypothèses ?"),"answer":self._t(language,"Project structure and testability may be clear; demand, repeat use, payment, local constraints and economics remain hypotheses unless directly evidenced.","La structure et la testabilité peuvent être claires ; demande, usage répété, paiement, contraintes locales et économie restent des hypothèses sans preuve directe."),"reasoning":self._t(language,"The evidence label must remain visible in the final decision.","Le statut de preuve doit rester visible dans la décision finale."),"unresolved":self._t(language,"Downgrade every unsupported claim before presentation.","Rétrograder chaque affirmation non soutenue avant présentation."),"follow_up":self._t(language,"Which claim has the greatest decision impact?","Quelle affirmation a le plus grand impact sur la décision ?"),"likely":self._t(language,"What can you confidently claim today?","Que pouvez-vous affirmer avec confiance aujourd’hui ?"),"recommended":self._t(language,"We can claim the project is structured and testable; we cannot yet claim product-market fit or scalable economics.","Nous pouvons affirmer que le projet est structuré et testable ; pas encore qu’il possède un product-market fit ou une économie scalable."),"proofs":self._t_list(language,["Claim-to-evidence matrix"],["Matrice affirmation-preuve"]),"avoid":self._t(language,"The analysis validated the market.","L’analyse a validé le marché.")},
            {"asked_by":"risk_execution_officer","question":self._t(language,"What is the least risky next action?","Quelle est la prochaine action la moins risquée ?"),"answer":self._t(language,f"Run a bounded pilot around {context['priority_workflow']} and measure {metric_text}.",f"Lancer un pilote limité autour de {context['priority_workflow']} et mesurer {metric_text}."),"reasoning":self._t(language,"A bounded experiment buys evidence before irreversible investment.","Une expérience limitée achète des preuves avant un investissement irréversible."),"confidence":0.85,"status":"supported","unresolved":self._t(language,"Set ownership, schedule, instrumentation and rollback.","Définir responsabilité, calendrier, instrumentation et retour arrière."),"follow_up":self._t(language,"Who owns the next decision and on what date?","Qui possède la prochaine décision et à quelle date ?"),"likely":self._t(language,"What will you do next week?","Que ferez-vous la semaine prochaine ?"),"recommended":self._t(language,"We will recruit the bounded cohort, instrument the complete validation unit and review predefined GO, PIVOT and NO-GO thresholds.","Nous recruterons la cohorte limitée, instrumenterons l’unité complète et examinerons les seuils GO, PIVOT et NO-GO prédéfinis."),"proofs":self._t_list(language,["Pilot plan","Instrumentation plan","Review date"],["Plan pilote","Plan d’instrumentation","Date de revue"]),"avoid":self._t(language,"We will continue building the platform.","Nous continuerons à développer la plateforme.")},
        ]
        questions=self._adaptive_questions(number=number,language=language,specifications=specs)
        return self._round(number,language,self._t(language,"Investment committee decision","Décision du comité d’investissement"),self._t(language,"Convert the evidence into one bounded decision and experiment plan.","Transformer les preuves en une décision limitée et un plan d’expérience."),self._t(language,"Should the project continue, pivot or stop at this evidence level?","Le projet doit-il continuer, pivoter ou s’arrêter à ce niveau de preuve ?"),["startup_score","evidence_confidence","rounds_1_4"],[self._t(language,"The project is structured enough for a bounded test.","Le projet est assez structuré pour un test limité."),self._t(language,"The next decision can use archetype-specific metrics.","La prochaine décision peut utiliser des métriques propres à l’archétype.")],[self._t(language,"Hypothesis: the bounded pilot demonstrates repeat value and viable delivery economics.","Hypothèse : le pilote limité démontre une valeur répétée et une économie de réalisation viable.")],context.get("risk_dimensions")[:3],self._global_missing_evidence(analysis,language),[],questions,"CONDITIONAL_GO",self._t(language,"The committee authorizes a bounded pilot, not full rollout, under explicit evidence, behaviour, risk and economics conditions.","Le comité autorise un pilote limité, pas un déploiement complet, sous conditions explicites de preuve, comportement, risque et économie."),self._t(language,"Run the pilot and decide GO, PIVOT or NO-GO without expanding scope first.","Lancer le pilote et décider GO, PIVOT ou NO-GO sans élargir le périmètre."),[self._t(language,"The core outcome is completed and repeated by the required actors.","Le résultat principal est réalisé et répété par les acteurs nécessaires."),self._t(language,"Archetype-specific reliability and risk thresholds are met.","Les seuils de fiabilité et risque propres à l’archétype sont atteints."),self._t(language,"At least one real payer accepts the offer and contribution remains viable.","Au moins un vrai payeur accepte l’offre et la contribution reste viable.")],[self._t(language,"Actors do not repeat the outcome, risk is unacceptable or the economics are structurally negative.","Les acteurs ne répètent pas le résultat, le risque est inacceptable ou l’économie est structurellement négative.")])

    def _round_problem(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        problem_status = self._claim_status(analysis, "problem")
        supported = problem_status == "supported"
        validated = [
            self._t(language, "The retained evidence supports the existence of the stated workflow problem.", "Les preuves retenues soutiennent l’existence du problème de workflow décrit.")
        ] if supported else []
        hypotheses = [] if supported else [
            self._t(language, f"Hypothesis: {context['primary_target']} experiences the problem frequently and urgently.", f"Hypothèse : {context['primary_target']} rencontre le problème fréquemment et avec urgence.")
        ]
        questions = [
            self._question(
                round_number=number,
                index=1,
                asked_by="customer_problem_analyst",
                addressed_to="project_defender",
                question=self._t(language, "How frequently does the problem occur in the target user's real workflow?", "À quelle fréquence le problème apparaît-il dans le workflow réel de l’utilisateur cible ?"),
                direct_answer=self._t(language, "The project description identifies a recurring operational problem, but its frequency has not yet been measured with users.", "La description identifie un problème opérationnel récurrent, mais sa fréquence n’a pas encore été mesurée auprès des utilisateurs."),
                reasoning=self._t(language, f"The current problem statement is: {context['problem']}", f"Le problème actuel est : {context['problem']}"),
                confidence=0.75 if supported else 0.35,
                evidence_status="supported" if supported else "field_validation_required",
                unresolved=self._t(language, "Measure occurrences, time loss and consequences with at least five target users.", "Mesurer les occurrences, le temps perdu et les conséquences auprès d’au moins cinq utilisateurs cibles."),
                follow_up=self._t(language, "Which observation method and time period will be used?", "Quelle méthode d’observation et quelle période seront utilisées ?"),
                likely_real_question=self._t(language, "How do you know this problem is urgent rather than merely inconvenient?", "Comment savez-vous que ce problème est urgent et pas seulement gênant ?"),
                recommended_answer=self._t(language, "We do not claim urgency is validated yet. We will measure frequency, time loss and failed tasks during field interviews and workflow observation.", "Nous ne prétendons pas encore que l’urgence est validée. Nous mesurerons la fréquence, le temps perdu et les tâches échouées pendant les entretiens et observations terrain."),
                proofs=[self._t(language, "Interview notes", "Notes d’entretien"), self._t(language, "Observed workflow timings", "Mesures de temps du workflow"), self._t(language, "Examples of missing or duplicated records", "Exemples de dossiers manquants ou dupliqués")],
                avoid=self._t(language, "Everyone has this problem.", "Tout le monde rencontre ce problème."),
            ),
            self._question(
                round_number=number,
                index=2,
                asked_by="risk_execution_officer",
                addressed_to="customer_problem_analyst",
                question=self._t(language, "Why would the user change the current method?", "Pourquoi l’utilisateur changerait-il sa méthode actuelle ?"),
                direct_answer=self._t(language, f"Change is plausible only if {context['priority_workflow']} becomes faster, safer or easier to retrieve than the current alternative.", f"Le changement est plausible uniquement si {context['priority_workflow']} devient plus rapide, plus sûr ou plus facile à retrouver que l’alternative actuelle."),
                reasoning=self._t(language, "Usefulness alone does not prove repeated adoption.", "L’utilité seule ne prouve pas l’adoption répétée."),
                confidence=0.5,
                evidence_status="hypothesis",
                unresolved=self._t(language, "Define a measurable first-session benefit and a weekly reuse threshold.", "Définir un bénéfice mesurable dès la première session et un seuil de réutilisation hebdomadaire."),
                follow_up=self._t(language, "What result must be visible during the first week?", "Quel résultat doit être visible pendant la première semaine ?"),
                likely_real_question=self._t(language, "Why is the current manual method not good enough?", "Pourquoi la méthode manuelle actuelle n’est-elle pas suffisante ?"),
                recommended_answer=self._t(language, "The product must prove a concrete gain against the current method; the pilot will compare task time, missing information and reuse.", "Le produit doit prouver un gain concret face à la méthode actuelle ; le pilote comparera le temps, les informations manquantes et la réutilisation."),
                proofs=[self._t(language, "Before/after workflow comparison", "Comparaison du workflow avant/après"), self._t(language, "Weekly reuse data", "Données de réutilisation hebdomadaire")],
                avoid=self._t(language, "Digital is automatically better than paper.", "Le numérique est automatiquement meilleur que le papier."),
            ),
            self._question(
                round_number=number,
                index=3,
                asked_by="evidence_auditor",
                addressed_to="project_defender",
                question=self._t(language, "Which part of this argument is evidence and which part is assumption?", "Quelle partie de cet argument est une preuve et quelle partie est une hypothèse ?"),
                direct_answer=self._t(language, "The project definition is known; frequency, severity, urgency and willingness to change remain assumptions unless field evidence exists.", "La définition du projet est connue ; la fréquence, la gravité, l’urgence et la volonté de changer restent des hypothèses sans preuve terrain."),
                reasoning=self._t(language, f"Overall evidence confidence is {evidence['level']}.", f"La confiance globale des preuves est {evidence['level']}."),
                confidence=evidence["score"] / 10,
                evidence_status="supported" if supported else "not_confirmed",
                unresolved=self._t(language, "Separate founder statements from observed customer evidence in the report.", "Séparer les déclarations du fondateur des preuves client observées dans le rapport."),
                follow_up=self._t(language, "What result would falsify the problem hypothesis?", "Quel résultat réfuterait l’hypothèse du problème ?"),
                likely_real_question=self._t(language, "What evidence would make you stop pursuing this problem?", "Quelle preuve vous ferait abandonner ce problème ?"),
                recommended_answer=self._t(language, "We would stop or pivot if users rarely experience the problem, do not value the proposed gain, or refuse to change their workflow.", "Nous arrêterions ou pivoterions si les utilisateurs rencontrent rarement le problème, ne valorisent pas le gain ou refusent de changer leur workflow."),
                proofs=[self._t(language, "Explicit falsification thresholds", "Seuils explicites de réfutation")],
                avoid=self._t(language, "The problem cannot be disproved.", "Le problème ne peut pas être réfuté."),
            ),
            self._question(
                round_number=number,
                index=4,
                asked_by="customer_problem_analyst",
                addressed_to="business_financial_analyst",
                question=self._t(language, "Are the user and economic buyer the same person?", "L’utilisateur et l’acheteur économique sont-ils la même personne ?"),
                direct_answer=(
                    self._t(
                        language,
                        f"The operational target is {context['primary_target']}; the economic buyer is explicitly identified as {context['economic_buyer_value']}.",
                        f"La cible opérationnelle est {context['primary_target']} ; l’acheteur économique est explicitement identifié comme {context['economic_buyer_value']}.",
                    )
                    if context.get("economic_buyer_status") == "explicit"
                    else self._t(
                        language,
                        f"The operational target is {context['primary_target']}; the economic buyer is not yet identified.",
                        f"La cible opérationnelle est {context['primary_target']} ; l’acheteur économique n’est pas encore identifié.",
                    )
                ),
                reasoning=self._t(language, "Adoption and payment decisions may belong to different roles.", "Les décisions d’adoption et de paiement peuvent appartenir à des rôles différents."),
                confidence=0.45,
                evidence_status="field_validation_required",
                unresolved=self._t(language, "Map the user, sponsor, budget owner and adoption blocker.", "Cartographier l’utilisateur, le sponsor, le détenteur du budget et le bloqueur d’adoption."),
                follow_up=self._t(language, "Who can approve, block or renew the purchase?", "Qui peut approuver, bloquer ou renouveler l’achat ?"),
                likely_real_question=self._t(language, "Who signs the contract and who uses the product every day?", "Qui signe le contrat et qui utilise le produit chaque jour ?"),
                recommended_answer=self._t(language, "We separate daily users from budget owners and will interview both before setting the pricing model.", "Nous séparons les utilisateurs quotidiens des détenteurs du budget et interrogerons les deux avant de fixer le modèle tarifaire."),
                proofs=[self._t(language, "Decision-making map", "Carte de décision")],
                avoid=self._t(language, "The user will obviously pay.", "L’utilisateur paiera évidemment."),
            ),
        ]
        return self._round(
            number=number,
            language=language,
            topic=self._t(language, "Problem, customer and urgency", "Problème, client et urgence"),
            objective=self._t(language, "Determine whether the pain justifies behaviour change.", "Déterminer si la douleur justifie un changement de comportement."),
            question=self._t(language, "Is the problem frequent, severe and urgent enough to trigger adoption?", "Le problème est-il assez fréquent, grave et urgent pour déclencher l’adoption ?"),
            data_sources=["project_intelligence.problem", "project_intelligence.primary_target", "fact_check_report.problem"],
            supporting=[self._t(language, f"The project identifies a concrete workflow: {context['priority_workflow']}.", f"Le projet identifie un workflow concret : {context['priority_workflow']}."), self._t(language, f"The first operational target is {context['primary_target']}.", f"La première cible opérationnelle est {context['primary_target']}.")],
            hypotheses=hypotheses,
            risks=[self._t(language, "The pain may be real but not urgent enough to change behaviour.", "La douleur peut être réelle sans être assez urgente pour changer les habitudes."), self._t(language, "The user and buyer may be different people.", "L’utilisateur et l’acheteur peuvent être différents.")],
            missing=[self._t(language, "Observed workflows from at least five users.", "Workflows observés auprès d’au moins cinq utilisateurs."), self._t(language, "Measured frequency, severity and current cost.", "Fréquence, gravité et coût actuel mesurés.")],
            validated=validated,
            questions=questions,
            decision="SUPPORTED" if supported else "CONDITIONAL_GO",
            synthesis=self._t(language, "The problem is specific enough for field validation, but urgency and behaviour change are not yet proven.", "Le problème est assez précis pour une validation terrain, mais l’urgence et le changement de comportement ne sont pas encore prouvés."),
            next_action=self._t(language, "Observe five target users and quantify the current workflow.", "Observer cinq utilisateurs cibles et quantifier le workflow actuel."),
            go_conditions=[self._t(language, "Users report a recurring problem and measurable operational loss.", "Les utilisateurs signalent un problème récurrent et une perte opérationnelle mesurable.")],
            no_go_conditions=[self._t(language, "The problem is rare, low-impact or users refuse to change the workflow.", "Le problème est rare, peu impactant ou les utilisateurs refusent de changer le workflow.")],
        )

    def _round_market(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        sources = self._sources(analysis)
        direct = [s for s in sources if bool(s.get("is_direct_competitor"))]
        adjacent = [s for s in sources if str(s.get("source_type") or "") == "adjacent_solution"]
        local = [s for s in sources if str(s.get("region_match") or "") == "local"]
        manual = self._t(language, "paper, spreadsheets, messaging tools and informal coordination", "papier, tableurs, messagerie et coordination informelle")
        questions = [
            self._question(number, 1, "market_competition_analyst", "project_defender", self._t(language, "Which verified products solve the same workflow for the same target?", "Quels produits vérifiés résolvent le même workflow pour la même cible ?"), self._t(language, f"{len(direct)} verified direct product(s) and {len(adjacent)} adjacent solution(s) are currently retained.", f"{len(direct)} produit(s) direct(s) vérifié(s) et {len(adjacent)} solution(s) adjacente(s) sont actuellement retenus."), self._t(language, "A shared keyword or article is not treated as a competitor.", "Un mot-clé commun ou un article n’est pas traité comme concurrent."), 0.7 if direct or adjacent else 0.35, "supported" if direct or adjacent else "not_confirmed", self._t(language, "Manually verify product functionality, target, geography and current activity.", "Vérifier manuellement les fonctionnalités, la cible, la géographie et l’activité actuelle."), self._t(language, "Which product was manually checked most recently?", "Quel produit a été vérifié manuellement le plus récemment ?"), self._t(language, "Who are your three closest competitors and why?", "Quels sont vos trois concurrents les plus proches et pourquoi ?"), self._t(language, "We separate direct products, adjacent solutions, articles and manual alternatives; only verified product pages enter the competitor list.", "Nous séparons produits directs, solutions adjacentes, articles et alternatives manuelles ; seules les pages produit vérifiées entrent dans la liste des concurrents."), [self._t(language, "Product pages", "Pages produit"), self._t(language, "Feature comparison", "Comparaison fonctionnelle")], self._t(language, "There is no competition.", "Il n’existe aucune concurrence.")),
            self._question(number, 2, "customer_problem_analyst", "market_competition_analyst", self._t(language, "What do users actually use instead of this product?", "Qu’utilisent réellement les utilisateurs à la place de ce produit ?"), self._t(language, f"The strongest alternatives may be {manual}, not another specialist SaaS.", f"Les alternatives les plus fortes peuvent être {manual}, et non un autre SaaS spécialisé."), self._t(language, "The replacement behaviour must be compared with the current workflow.", "Le comportement de remplacement doit être comparé au workflow actuel."), 0.55, "hypothesis", self._t(language, "Observe the current tool stack and switching cost.", "Observer les outils actuels et le coût de changement."), self._t(language, "Which current tool is hardest to replace?", "Quel outil actuel est le plus difficile à remplacer ?"), self._t(language, "Why will users switch from a free method?", "Pourquoi les utilisateurs quitteront-ils une méthode gratuite ?"), self._t(language, "The pilot must prove a measurable gain over the current method, not only feature superiority over software competitors.", "Le pilote doit prouver un gain mesurable face à la méthode actuelle, pas seulement une supériorité fonctionnelle sur des logiciels."), [self._t(language, "Current workflow inventory", "Inventaire du workflow actuel"), self._t(language, "Switching-cost interview", "Entretien sur le coût de changement")], self._t(language, "Our features are better, so users will switch.", "Nos fonctionnalités sont meilleures, donc les utilisateurs changeront.")),
            self._question(number, 3, "evidence_auditor", "market_competition_analyst", self._t(language, "Do the retained sources prove local demand or only international feasibility?", "Les sources retenues prouvent-elles la demande locale ou seulement la faisabilité internationale ?"), self._t(language, f"The current evidence level is {evidence['level']}. International benchmarks can show feasibility but do not prove local demand or willingness to pay.", f"Le niveau de preuve actuel est {evidence['level']}. Les benchmarks internationaux montrent une faisabilité, mais ne prouvent pas la demande locale ni la volonté de payer."), self._t(language, f"{len(local)} retained source(s) have a local marker, but each claim still requires category-compatible evidence.", f"{len(local)} source(s) retenue(s) possèdent un marqueur local, mais chaque affirmation exige une preuve compatible avec sa catégorie."), evidence["score"] / 10, "not_confirmed" if evidence["level"] == "low" else "supported", self._t(language, "Find official local data and conduct field interviews.", "Trouver des données locales officielles et mener des entretiens terrain."), self._t(language, "Which local source has visible methodology and category-compatible data?", "Quelle source locale possède une méthodologie visible et des données compatibles ?"), self._t(language, "What proves demand in the first market?", "Qu’est-ce qui prouve la demande sur le premier marché ?"), self._t(language, "We currently treat demand as a hypothesis and will validate it with official data, interviews and a pilot.", "Nous traitons actuellement la demande comme une hypothèse et la validerons par des données officielles, des entretiens et un pilote."), [self._t(language, "Official sector data", "Données sectorielles officielles"), self._t(language, "Local interview results", "Résultats d’entretiens locaux")], self._t(language, "A market report headline proves demand.", "Le titre d’un rapport de marché prouve la demande.")),
            self._question(number, 4, "red_team_challenger", "project_defender", self._t(language, "Could the absence of a verified local competitor indicate weak demand instead of a market gap?", "L’absence de concurrent local vérifié peut-elle indiquer une faible demande plutôt qu’un espace de marché ?"), self._t(language, "Yes. The absence of a retained competitor is ambiguous and must never be presented as proof of an empty market.", "Oui. L’absence de concurrent retenu est ambiguë et ne doit jamais être présentée comme preuve d’un marché vide."), self._t(language, "A market gap becomes credible only after customer demand and alternative mapping are validated.", "Un espace de marché devient crédible uniquement après validation de la demande client et des alternatives."), 0.85, "supported", self._t(language, "Verify local actors manually and test demand before positioning the gap.", "Vérifier manuellement les acteurs locaux et tester la demande avant de positionner l’espace."), self._t(language, "What finding would change the positioning?", "Quel résultat modifierait le positionnement ?"), self._t(language, "Why has nobody built this locally?", "Pourquoi personne ne l’a construit localement ?"), self._t(language, "We do not assume the gap is attractive; the pilot will determine whether it reflects unmet demand or low urgency.", "Nous ne supposons pas que l’espace est attractif ; le pilote déterminera s’il reflète une demande non satisfaite ou une faible urgence."), [self._t(language, "Local actor map", "Cartographie des acteurs locaux"), self._t(language, "Demand interviews", "Entretiens de demande")], self._t(language, "No competitor means a guaranteed opportunity.", "Aucun concurrent signifie une opportunité garantie.")),
        ]
        return self._round(number, language, self._t(language, "Market, alternatives and positioning", "Marché, alternatives et positionnement"), self._t(language, "Separate comparable products, adjacent solutions, evidence pages and current alternatives.", "Séparer produits comparables, solutions adjacentes, pages de preuve et alternatives actuelles."), self._t(language, "Can the project win against the alternatives already used by the target users?", "Le projet peut-il gagner face aux alternatives déjà utilisées par les utilisateurs cibles ?"), ["forgecrawler.sources", "competitive_analysis", "evidence_ledger.competition"], [self._t(language, f"The source gate retains {len(direct)} direct and {len(adjacent)} adjacent solution(s).", f"Le filtre retient {len(direct)} solution(s) directe(s) et {len(adjacent)} solution(s) adjacente(s).")], [self._t(language, "Hypothesis: a specialized local workflow can outperform generic tools.", "Hypothèse : un workflow local spécialisé peut dépasser les outils génériques.")], [self._t(language, "Manual alternatives may be stronger than specialist software.", "Les alternatives manuelles peuvent être plus fortes que les logiciels spécialisés."), self._t(language, "International benchmarks do not prove local demand.", "Les benchmarks internationaux ne prouvent pas la demande locale.")], [self._t(language, "Manual verification of local products and alternatives.", "Vérification manuelle des produits et alternatives locales."), self._t(language, "Official or independent local demand evidence.", "Preuves locales officielles ou indépendantes de demande.")], [], questions, "CONDITIONAL_GO", self._t(language, "The positioning is plausible for a pilot, but the local market gap and switching behaviour remain unverified.", "Le positionnement est plausible pour un pilote, mais l’espace local et le comportement de changement restent non vérifiés."), self._t(language, "Map current alternatives and manually verify the closest local and international products.", "Cartographier les alternatives actuelles et vérifier manuellement les produits locaux et internationaux les plus proches."), [self._t(language, "A distinct workflow advantage is demonstrated against current alternatives.", "Un avantage de workflow distinct est démontré face aux alternatives actuelles.")], [self._t(language, "Users see no advantage over free current methods or a close competitor already dominates the segment.", "Les utilisateurs ne voient aucun avantage face aux méthodes gratuites ou un concurrent proche domine déjà le segment.")])

    def _round_mvp(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        workflows = context["priority_workflows"]
        first = workflows[0]
        questions = [
            self._question(number, 1, "product_technology_architect", "project_defender", self._t(language, "What is the smallest workflow that can prove value?", "Quel est le plus petit workflow capable de prouver la valeur ?"), self._t(language, f"The pilot should begin with one measurable workflow: {first}.", f"Le pilote doit commencer par un workflow mesurable : {first}."), self._t(language, "Secondary features must not be required to demonstrate the first benefit.", "Les fonctionnalités secondaires ne doivent pas être nécessaires pour démontrer le premier bénéfice."), 0.75, "estimated", self._t(language, "Define the exact screen flow, completion time and success event.", "Définir le parcours écran exact, le temps de réalisation et l’événement de succès."), self._t(language, "Which features can be removed from the first pilot?", "Quelles fonctionnalités peuvent être retirées du premier pilote ?"), self._t(language, "What exactly is in the MVP?", "Que contient exactement le MVP ?"), self._t(language, f"The first pilot is limited to {first}, the minimum data required and one reusable result. Other workflows are deferred.", f"Le premier pilote est limité à {first}, aux données minimales et à un résultat réutilisable. Les autres workflows sont reportés."), [self._t(language, "Clickable flow", "Parcours cliquable"), self._t(language, "Explicit excluded-feature list", "Liste explicite des fonctionnalités exclues")], self._t(language, "The MVP contains every requested feature.", "Le MVP contient toutes les fonctionnalités demandées.")),
            self._question(number, 2, "customer_problem_analyst", "product_technology_architect", self._t(language, "Can the first task be completed in the user's real environment?", "La première tâche peut-elle être réalisée dans l’environnement réel de l’utilisateur ?"), self._t(language, "Technical feasibility is plausible, but connectivity, mobile usability and onboarding must be tested in the actual context.", "La faisabilité technique est plausible, mais la connexion, l’usage mobile et l’onboarding doivent être testés dans le contexte réel."), self._t(language, f"The target region is {context['region']} and the workflow is {first}.", f"La région cible est {context['region']} et le workflow est {first}."), 0.55, "estimated", self._t(language, "Run the prototype on the real device, network and field conditions.", "Tester le prototype sur le vrai appareil, le vrai réseau et les conditions terrain."), self._t(language, "What happens offline or after synchronization failure?", "Que se passe-t-il hors ligne ou après un échec de synchronisation ?"), self._t(language, "How will the product work with poor connectivity?", "Comment le produit fonctionnera-t-il avec une mauvaise connexion ?"), self._t(language, "The pilot will test offline capture, synchronization recovery and a clear saved-state indicator before wider rollout.", "Le pilote testera la saisie hors ligne, la reprise de synchronisation et un indicateur clair d’enregistrement avant tout déploiement plus large."), [self._t(language, "Offline test results", "Résultats des tests hors ligne"), self._t(language, "Synchronization recovery test", "Test de reprise de synchronisation")], self._t(language, "Connectivity will not be a problem.", "La connexion ne sera pas un problème.")),
            self._question(number, 3, "risk_execution_officer", "product_technology_architect", self._t(language, "What technical risk can block repeated use?", "Quel risque technique peut bloquer l’usage répété ?"), self._t(language, "Duplicate entry, data loss, slow mobile input and unclear onboarding are the principal adoption risks.", "La double saisie, la perte de données, la saisie mobile lente et un onboarding peu clair sont les principaux risques d’adoption."), self._t(language, "The MVP must prove reliability and workflow speed, not only successful deployment.", "Le MVP doit prouver la fiabilité et la vitesse du workflow, pas seulement un déploiement réussi."), 0.7, "supported", self._t(language, "Set performance, recovery and onboarding acceptance criteria.", "Définir des critères d’acceptation de performance, de reprise et d’onboarding."), self._t(language, "What is the rollback path if the pilot fails?", "Quel est le chemin de retour si le pilote échoue ?"), self._t(language, "What prevents the MVP from becoming extra work?", "Qu’est-ce qui empêche le MVP de devenir un travail supplémentaire ?"), self._t(language, "The product must replace one task, import or preserve existing data and avoid parallel mandatory entry.", "Le produit doit remplacer une tâche, reprendre ou préserver les données existantes et éviter une saisie parallèle obligatoire."), [self._t(language, "Task-time benchmark", "Benchmark du temps de tâche"), self._t(language, "Data recovery test", "Test de récupération des données")], self._t(language, "Users can keep both systems indefinitely.", "Les utilisateurs peuvent garder les deux systèmes indéfiniment.")),
            self._question(number, 4, "red_team_challenger", "project_defender", self._t(language, "Could the team build a technically complete product that proves no customer value?", "L’équipe peut-elle construire un produit techniquement complet qui ne prouve aucune valeur client ?"), self._t(language, "Yes. Delivery is not validation; success requires repeated completion of the target workflow and measurable improvement.", "Oui. La livraison n’est pas une validation ; le succès exige la répétition du workflow cible et une amélioration mesurable."), self._t(language, "Technical completion and product-market evidence are separate dimensions.", "La réalisation technique et la preuve produit-marché sont deux dimensions séparées."), 0.9, "supported", self._t(language, "Make activation, reuse and task improvement part of the MVP Definition of Done.", "Intégrer activation, réutilisation et amélioration de tâche dans la Definition of Done du MVP."), self._t(language, "Which metric can fail even if the application works?", "Quelle métrique peut échouer même si l’application fonctionne ?"), self._t(language, "How do you know the MVP creates value?", "Comment savez-vous que le MVP crée de la valeur ?"), self._t(language, "We define value through task completion, time saved, weekly reuse and user willingness to continue—not through feature delivery alone.", "Nous définissons la valeur par la tâche terminée, le temps gagné, la réutilisation et la volonté de continuer—notamment pas par la seule livraison de fonctionnalités."), [self._t(language, "Activation and reuse dashboard", "Tableau d’activation et de réutilisation")], self._t(language, "The product works, therefore the idea is validated.", "Le produit fonctionne, donc l’idée est validée.")),
        ]
        return self._round(number, language, self._t(language, "Product, MVP and technical feasibility", "Produit, MVP et faisabilité technique"), self._t(language, "Reduce the first release to one measurable operational workflow.", "Réduire la première version à un workflow opérationnel mesurable."), self._t(language, "Can the MVP prove value without building the full platform?", "Le MVP peut-il prouver la valeur sans construire toute la plateforme ?"), ["project_intelligence.priority_workflows", "project_intelligence.mvp_scope", "startup_score.execution_readiness"], [self._t(language, f"A focused pilot can begin with: {first}.", f"Un pilote ciblé peut commencer par : {first}."), self._t(language, "The technical path is plausible with a reduced scope.", "La voie technique est plausible avec un périmètre réduit.")], [self._t(language, "Hypothesis: the first workflow creates measurable value in the first week.", "Hypothèse : le premier workflow crée une valeur mesurable pendant la première semaine.")], [self._t(language, "The MVP may still include too many workflows.", "Le MVP peut encore contenir trop de workflows."), self._t(language, "Connectivity, onboarding and duplicate entry can prevent reuse.", "La connexion, l’onboarding et la double saisie peuvent empêcher la réutilisation.")], [self._t(language, "Clickable workflow test with target users.", "Test du workflow cliquable avec les utilisateurs cibles."), self._t(language, "Offline, recovery and task-time tests.", "Tests hors ligne, de reprise et de temps de tâche.")], [], questions, "CONDITIONAL_GO", self._t(language, "Technical feasibility is plausible, but the pilot must prove one workflow rather than deliver the whole product.", "La faisabilité technique est plausible, mais le pilote doit prouver un workflow plutôt que livrer tout le produit."), self._t(language, f"Prototype {first} and test completion, reuse and recovery.", f"Prototyper {first} et tester la réalisation, la réutilisation et la reprise."), [self._t(language, "Five users complete the workflow and at least three reuse it the following week.", "Cinq utilisateurs terminent le workflow et au moins trois le réutilisent la semaine suivante.")], [self._t(language, "The workflow is slower than the current method, creates duplicate entry or users do not return.", "Le workflow est plus lent que la méthode actuelle, crée une double saisie ou les utilisateurs ne reviennent pas.")])

    def _round_finance(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        financial = self._section(analysis, "financial_estimation")
        model = context["business_model"]
        questions = [
            self._question(number, 1, "business_financial_analyst", "project_defender", self._t(language, "Who pays, for what measurable value and at what decision point?", "Qui paie, pour quelle valeur mesurable et à quel moment de décision ?"), self._payer_answer(context, language), self._t(language, "A plausible revenue model is not evidence of payment.", "Un modèle de revenus plausible n’est pas une preuve de paiement."), 0.4, "field_validation_required", self._t(language, "Test three real prices with economic buyers and record the decision rationale.", "Tester trois vrais prix avec des acheteurs économiques et enregistrer la justification de décision."), self._t(language, "What budget line and approval process will fund the purchase?", "Quelle ligne budgétaire et quel processus d’approbation financeront l’achat ?"), self._t(language, "Who is the paying customer?", "Qui est le client payeur ?"), self._t(
                language,
                "The payer is not treated as known until a real budget owner accepts or rejects a concrete offer.",
                "Le payeur n’est pas considéré comme connu avant qu’un vrai détenteur du budget accepte ou refuse une offre concrète.",
            ), [self._t(language, "Price-test records", "Comptes rendus des tests de prix"), self._t(language, "Buyer approval map", "Carte d’approbation de l’acheteur")], self._t(language, "Users said they liked it, so they will pay.", "Les utilisateurs l’aiment, donc ils paieront.")),
            self._question(number, 2, "risk_execution_officer", "business_financial_analyst", self._t(language, "Could acquisition, onboarding and support cost exceed subscription revenue?", "Les coûts d’acquisition, d’onboarding et de support peuvent-ils dépasser les revenus d’abonnement ?"), self._t(language, "Yes. Early customers may require high-touch onboarding, training and field support.", "Oui. Les premiers clients peuvent exiger un onboarding, une formation et un support terrain importants."), str(financial.get("roi_outlook") or self._t(language, "Unit economics are not yet verified.", "L’économie unitaire n’est pas encore vérifiée.")), 0.6, "estimated", self._t(language, "Measure onboarding hours, support requests, acquisition effort and gross margin during the pilot.", "Mesurer les heures d’onboarding, les demandes de support, l’effort d’acquisition et la marge pendant le pilote."), self._t(language, "What support model remains viable at the tested price?", "Quel modèle de support reste viable au prix testé ?"), self._t(language, "What are your unit economics?", "Quelle est votre économie unitaire ?"), self._t(language, "We will calculate unit economics from pilot data: price, acquisition effort, onboarding hours, support cost, infrastructure and retention.", "Nous calculerons l’économie unitaire à partir du pilote : prix, effort d’acquisition, heures d’onboarding, support, infrastructure et rétention."), [self._t(language, "Bottom-up cost model", "Modèle de coût bottom-up"), self._t(language, "Pilot support log", "Journal de support du pilote")], self._t(language, "Cloud hosting is cheap, so margins will be high.", "L’hébergement cloud est bon marché, donc les marges seront élevées.")),
            self._question(number, 3, "customer_problem_analyst", "business_financial_analyst", self._t(language, "Which result makes the price acceptable to the buyer?", "Quel résultat rend le prix acceptable pour l’acheteur ?"), self._t(language, "The price must be connected to time saved, fewer errors, better reporting or revenue/risk impact—not to the number of features.", "Le prix doit être relié au temps gagné, aux erreurs évitées, au meilleur reporting ou à l’impact revenu/risque, et non au nombre de fonctionnalités."), self._t(language, "Value-based pricing requires a measurable baseline.", "Une tarification fondée sur la valeur exige une base mesurable."), 0.55, "hypothesis", self._t(language, "Measure the buyer's current cost and acceptable payback period.", "Mesurer le coût actuel de l’acheteur et la période de retour acceptable."), self._t(language, "Would the buyer prefer per-user, per-record or organization pricing?", "L’acheteur préfère-t-il un prix par utilisateur, dossier ou organisation ?"), self._t(language, "Why is this price justified?", "Pourquoi ce prix est-il justifié ?"), self._t(language, "The price will be justified by a measured operational outcome and tested against alternative packages with real buyers.", "Le prix sera justifié par un résultat opérationnel mesuré et testé face à plusieurs offres auprès de vrais acheteurs."), [self._t(language, "Current-cost baseline", "Base de coût actuelle"), self._t(language, "Package preference test", "Test de préférence d’offre")], self._t(language, "This price is standard for SaaS.", "Ce prix est standard pour un SaaS.")),
            self._question(number, 4, "evidence_auditor", "project_defender", self._t(language, "Which financial figures are sourced, estimated or still unknown?", "Quels chiffres financiers sont sourcés, estimés ou encore inconnus ?"), self._t(language, "Current financial figures are planning estimates until quotes, pilot costs, price acceptance and retention are recorded.", "Les chiffres financiers actuels sont des estimations de planification jusqu’à l’obtention de devis, coûts pilote, acceptation de prix et rétention."), self._t(language, f"Evidence confidence is {evidence['level']} and finance requires direct validation.", f"La confiance des preuves est {evidence['level']} et les finances exigent une validation directe."), evidence["score"] / 10, "estimated", self._t(language, "Label every figure as quote, observed cost, estimate or hypothesis.", "Étiqueter chaque chiffre comme devis, coût observé, estimation ou hypothèse."), self._t(language, "Which number can be replaced by a real quote this week?", "Quel chiffre peut être remplacé par un vrai devis cette semaine ?"), self._t(language, "How reliable are your financial projections?", "Quelle est la fiabilité de vos projections financières ?"), self._t(language, "They are preliminary estimates; the next version will replace assumptions with provider quotes and pilot conversion, support and retention data.", "Ce sont des estimations préliminaires ; la prochaine version remplacera les hypothèses par des devis et des données de conversion, support et rétention du pilote."), [self._t(language, "Provider quotes", "Devis fournisseurs"), self._t(language, "Observed pilot costs", "Coûts pilote observés")], self._t(language, "The forecast is accurate because the model calculated it.", "La prévision est exacte parce que le modèle l’a calculée.")),
        ]
        return self._round(number, language, self._t(language, "Business model, pricing and financial viability", "Modèle économique, prix et viabilité financière"), self._t(language, "Distinguish a plausible model from payment evidence and viable unit economics.", "Distinguer un modèle plausible d’une preuve de paiement et d’une économie unitaire viable."), self._t(language, "Who will pay, how much and for which measurable outcome?", "Qui paiera, combien et pour quel résultat mesurable ?"), ["project_intelligence.business_model", "financial_estimation", "evidence_ledger.pricing"], [self._t(language, f"The initial model is: {model}.", f"Le modèle initial est : {model}."), self._t(language, "A limited paid pilot can test the economic decision before scaling.", "Un pilote payant limité peut tester la décision économique avant le passage à l’échelle.")], [self._t(language, "Hypothesis: a real budget owner will pay for a measurable workflow gain.", "Hypothèse : un vrai détenteur du budget paiera pour un gain de workflow mesurable.")], [self._t(language, "Willingness to pay is not validated.", "La volonté de payer n’est pas validée."), self._t(language, "Acquisition, onboarding and support may exceed early revenue.", "L’acquisition, l’onboarding et le support peuvent dépasser les premiers revenus.")], [self._t(language, "Three real price tests with economic buyers.", "Trois vrais tests de prix avec des acheteurs économiques."), self._t(language, "Bottom-up MVP and support cost model.", "Modèle bottom-up des coûts MVP et support."), self._t(language, "Pilot retention and conversion data.", "Données de rétention et conversion du pilote.")], [], questions, "CONDITIONAL_GO", self._t(language, "The model deserves a payment test, not a full financial commitment.", "Le modèle mérite un test de paiement, pas un engagement financier complet."), self._t(language, "Test three concrete offers and measure acquisition, onboarding, support and retention.", "Tester trois offres concrètes et mesurer acquisition, onboarding, support et rétention."), [self._t(language, "At least one economic buyer accepts a concrete pilot offer and the measured support cost remains viable.", "Au moins un acheteur économique accepte une offre pilote concrète et le coût de support mesuré reste viable.")], [self._t(language, "All buyers reject the tested value/price relationship or support cost makes the offer structurally unviable.", "Tous les acheteurs rejettent le rapport valeur/prix ou le support rend l’offre structurellement non viable.")])

    def _round_decision(self, number: int, context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        score = self._section(analysis, "startup_score")
        potential = self._number(score.get("potential_score") or score.get("score"), 6.0)
        readiness = self._number(score.get("execution_readiness_score"), 5.0)
        questions = [
            self._question(number, 1, "committee_chair", "all_members", self._t(language, "Should the project proceed to a pilot, pivot or stop?", "Le projet doit-il passer à un pilote, pivoter ou s’arrêter ?"), self._t(language, "Proceed only to a narrow validation pilot while the blocking evidence is collected.", "Passer uniquement à un pilote de validation réduit pendant la collecte des preuves bloquantes."), self._t(language, f"Potential is {potential:.1f}/10, evidence confidence is {evidence['score']:.1f}/10 and execution readiness is {readiness:.1f}/10.", f"Le potentiel est {potential:.1f}/10, la confiance des preuves {evidence['score']:.1f}/10 et la préparation à l’exécution {readiness:.1f}/10."), 0.8, "committee_synthesis", self._t(language, "Complete the pilot conditions before investing in full development or scaling.", "Remplir les conditions du pilote avant d’investir dans le développement complet ou le passage à l’échelle."), self._t(language, "Which condition blocks the next investment decision?", "Quelle condition bloque la prochaine décision d’investissement ?"), self._t(language, "What is your decision today?", "Quelle est votre décision aujourd’hui ?"), self._t(language, "The decision is Conditional Go for a limited pilot, not approval for full rollout. The next investment decision depends on workflow reuse, price acceptance and local evidence.", "La décision est un GO conditionnel pour un pilote limité, et non une approbation du déploiement complet. La prochaine décision dépend de la réutilisation, de l’acceptation du prix et des preuves locales."), [self._t(language, "Committee vote", "Vote du comité"), self._t(language, "Explicit pilot scorecard", "Tableau de bord explicite du pilote")], self._t(language, "The project received 7/10, so we should build everything.", "Le projet a reçu 7/10, donc il faut tout construire.")),
            self._question(number, 2, "red_team_challenger", "committee_chair", self._t(language, "Which single assumption can destroy the project?", "Quelle hypothèse unique peut détruire le projet ?"), self._t(language, "The project fails if target users do not repeatedly use the priority workflow or no economic buyer accepts the tested value/price relationship.", "Le projet échoue si les utilisateurs ne réutilisent pas le workflow prioritaire ou si aucun acheteur économique n’accepte le rapport valeur/prix testé."), self._t(language, "Adoption and payment are the two principal falsifiable assumptions.", "L’adoption et le paiement sont les deux hypothèses falsifiables principales."), 0.85, "supported", self._t(language, "Pre-register reuse and payment failure thresholds.", "Préenregistrer les seuils d’échec de réutilisation et de paiement."), self._t(language, "What exact result triggers a pivot?", "Quel résultat exact déclenche un pivot ?"), self._t(language, "What would make you stop?", "Qu’est-ce qui vous ferait arrêter ?"), self._t(language, "We will stop or pivot if users do not return, the workflow is slower than the current method, or buyers reject the tested value at viable prices.", "Nous arrêterons ou pivoterons si les utilisateurs ne reviennent pas, si le workflow est plus lent ou si les acheteurs rejettent la valeur aux prix viables."), [self._t(language, "Predefined no-go thresholds", "Seuils NO-GO prédéfinis")], self._t(language, "We will keep improving until users accept it.", "Nous continuerons à améliorer jusqu’à ce que les utilisateurs acceptent.")),
            self._question(number, 3, "evidence_auditor", "committee_chair", self._t(language, "Which findings are validated and which remain hypotheses?", "Quels résultats sont validés et lesquels restent des hypothèses ?"), self._t(language, "The project structure and technical plausibility are clearer; customer urgency, local demand, payment and unit economics remain hypotheses unless supported by direct evidence.", "La structure du projet et la plausibilité technique sont plus claires ; l’urgence client, la demande locale, le paiement et l’économie unitaire restent des hypothèses sans preuve directe."), self._t(language, "Validated opportunities remain empty when compatible evidence is absent.", "Les opportunités validées restent vides en l’absence de preuves compatibles."), evidence["score"] / 10, "evidence_audit", self._t(language, "Keep evidence statuses visible in the final memo and meeting preparation.", "Garder les statuts de preuve visibles dans le mémo final et la préparation de réunion."), self._t(language, "Which claim should be downgraded before the meeting?", "Quelle affirmation doit être rétrogradée avant la réunion ?"), self._t(language, "What can you confidently claim today?", "Que pouvez-vous affirmer avec confiance aujourd’hui ?"), self._t(language, "We can claim the project is defined and testable; we cannot yet claim local demand, product-market fit or financial viability.", "Nous pouvons affirmer que le projet est défini et testable ; nous ne pouvons pas encore affirmer la demande locale, le product-market fit ou la viabilité financière."), [self._t(language, "Claim-to-evidence matrix", "Matrice affirmation-preuve")], self._t(language, "The analysis validated the market.", "L’analyse a validé le marché.")),
            self._question(number, 4, "risk_execution_officer", "committee_chair", self._t(language, "What is the least risky next action?", "Quelle est la prochaine action la moins risquée ?"), self._t(language, f"Run a two-to-four-week pilot focused on {context['priority_workflow']} with explicit reuse, task-time, price and support metrics.", f"Lancer un pilote de deux à quatre semaines centré sur {context['priority_workflow']} avec des métriques explicites de réutilisation, temps, prix et support."), self._t(language, "A narrow experiment buys evidence before major product investment.", "Une expérience réduite achète des preuves avant un investissement produit important."), 0.9, "supported", self._t(language, "Name the pilot owner, users, dates, metrics and stop conditions.", "Nommer le responsable, les utilisateurs, les dates, les métriques et les conditions d’arrêt."), self._t(language, "Who owns the next decision and on what date?", "Qui possède la prochaine décision et à quelle date ?"), self._t(language, "What will you do next week?", "Que ferez-vous la semaine prochaine ?"), self._t(language, "We will recruit the pilot cohort, test one workflow and schedule a decision review against predefined GO, PIVOT and NO-GO thresholds.", "Nous recruterons la cohorte pilote, testerons un workflow et planifierons une revue de décision selon des seuils GO, PIVOT et NO-GO prédéfinis."), [self._t(language, "Pilot charter", "Charte du pilote"), self._t(language, "Decision review date", "Date de revue de décision")], self._t(language, "We will continue developing the platform.", "Nous continuerons à développer la plateforme.")),
        ]
        return self._round(number, language, self._t(language, "Investment committee decision", "Décision du comité d’investissement"), self._t(language, "Convert the previous rounds into one bounded decision and experiment plan.", "Transformer les tours précédents en une décision limitée et un plan d’expérience."), self._t(language, "Should the project continue, pivot or stop at this evidence level?", "Le projet doit-il continuer, pivoter ou s’arrêter à ce niveau de preuve ?"), ["startup_score", "evidence_confidence", "debate_rounds_1_4"], [self._t(language, "The project is sufficiently defined for a focused pilot.", "Le projet est suffisamment défini pour un pilote ciblé."), self._t(language, "The next decision can be based on measurable evidence.", "La prochaine décision peut être fondée sur des preuves mesurables.")], [self._t(language, "Hypothesis: the pilot will demonstrate repeated workflow value and payment interest.", "Hypothèse : le pilote démontrera une valeur répétée du workflow et un intérêt de paiement.")], [self._t(language, "Evidence is too weak for full rollout or scaling.", "Les preuves sont trop faibles pour un déploiement complet ou le passage à l’échelle."), self._t(language, "Adoption and payment can still invalidate the project.", "L’adoption et le paiement peuvent encore invalider le projet.")], self._global_missing_evidence(analysis, language), [], questions, "CONDITIONAL_GO", self._t(language, "The committee authorizes a limited pilot under explicit evidence, reuse, payment and cost conditions.", "Le comité autorise un pilote limité sous conditions explicites de preuve, réutilisation, paiement et coût."), self._t(language, "Run the pilot, review the scorecard and decide GO, PIVOT or NO-GO without expanding scope first.", "Lancer le pilote, revoir le tableau de bord et décider GO, PIVOT ou NO-GO sans élargir le périmètre."), [self._t(language, "Five users complete the priority workflow and at least three reuse it.", "Cinq utilisateurs terminent le workflow prioritaire et au moins trois le réutilisent."), self._t(language, "At least one economic buyer accepts a concrete pilot offer.", "Au moins un acheteur économique accepte une offre pilote concrète."), self._t(language, "Task time, support cost and data reliability meet the pilot thresholds.", "Le temps de tâche, le coût de support et la fiabilité des données respectent les seuils du pilote.")], [self._t(language, "Users do not return or the workflow creates extra work.", "Les utilisateurs ne reviennent pas ou le workflow crée du travail supplémentaire."), self._t(language, "Buyers reject the tested value/price relationship.", "Les acheteurs rejettent le rapport valeur/prix testé."), self._t(language, "A critical technical, regulatory or operational risk cannot be mitigated.", "Un risque technique, réglementaire ou opérationnel critique ne peut pas être réduit.")])

    # ------------------------------------------------------------------
    # Shared round / judge construction
    # ------------------------------------------------------------------

    def _round(self, number: int, language: str, topic: str, objective: str, question: str, data_sources: List[str], supporting: List[str], hypotheses: List[str], risks: List[str], missing: List[str], validated: List[str], questions: List[Dict[str, Any]], decision: str, synthesis: str, next_action: str, go_conditions: List[str], no_go_conditions: List[str]) -> Dict[str, Any]:
        assumptions = self._unique(hypotheses)
        critical_risks = self._unique(risks)
        missing_evidence = self._unique(missing)
        return {
            "round": number,
            "topic": topic,
            "objective": objective,
            "main_question": question,
            "moderator": {
                "role": "committee_chair",
                "round": number,
                "topic": topic,
                "focus": objective,
                "key_question": question,
                "data_sources": data_sources,
            },
            "member_positions": self._member_positions(number, language, decision),
            "defender": {
                "role": "project_defender",
                "round": number,
                "position": "conditional_support",
                "main_argument": supporting[0] if supporting else "",
                "supporting_points": self._unique(supporting)[:3],
                "opportunities": assumptions[:2],
                "assumptions": assumptions[:3],
                "opportunity_score": 6.0,
            },
            "critic": {
                "role": "critical_analyst",
                "round": number,
                "main_objection": critical_risks[0] if critical_risks else "",
                "critical_risks": critical_risks[:3],
                "weak_assumptions": assumptions[:3],
                "missing_evidence": missing_evidence[:4],
                "counter_recommendation": next_action,
                "risk_score": 7.0 if critical_risks else 4.0,
            },
            "committee_questions": questions,
            "cross_examination": questions[1:3],
            "evidence_audit": [
                {
                    "claim": item,
                    "status": "supported",
                    "confidence": "medium",
                }
                for item in validated
            ] + [
                {
                    "claim": item,
                    "status": "field_validation_required",
                    "confidence": "low",
                }
                for item in assumptions
            ],
            "agreements": self._unique(validated + supporting[:1]),
            "disagreements": critical_risks[:2],
            "unresolved_questions": missing_evidence,
            "meeting_preparation": {
                "likely_questions": [q["meeting_preparation"]["likely_real_question"] for q in questions],
                "recommended_answers": [q["meeting_preparation"]["recommended_answer"] for q in questions],
                "proofs_to_prepare": self._unique([proof for q in questions for proof in q["meeting_preparation"]["proofs_to_prepare"]]),
                "answers_to_avoid": [q["meeting_preparation"]["answer_to_avoid"] for q in questions],
            },
            "round_summary": {
                "validated_points": self._unique(validated),
                "potential_opportunities": assumptions,
                "remaining_risks": self._unique(critical_risks + missing_evidence),
                "decision": decision,
                "synthesis": synthesis,
                "next_action": next_action,
                "go_conditions": go_conditions,
                "no_go_conditions": no_go_conditions,
            },
            "context_locked": True,
            "output_language": language,
        }

    def _question(self, round_number: int, index: int, asked_by: str, addressed_to: str, question: str, direct_answer: str, reasoning: str, confidence: float, evidence_status: str, unresolved: str, follow_up: str, likely_real_question: str, recommended_answer: str, proofs: List[str], avoid: str) -> Dict[str, Any]:
        return {
            "question_id": f"round_{round_number}_q_{index}",
            "asked_by": asked_by,
            "addressed_to": addressed_to,
            "question": question,
            "question_type": "evidence_challenge" if asked_by in {"evidence_auditor", "red_team_challenger"} else "committee_review",
            "answer": {
                "direct_answer": direct_answer,
                "reasoning_summary": reasoning,
                "confidence": round(max(0.0, min(1.0, confidence)), 2),
                "evidence_status": evidence_status,
                "evidence_ids": [],
                "unresolved_point": unresolved,
            },
            "follow_up_question": follow_up,
            "meeting_preparation": {
                "likely_real_question": likely_real_question,
                "recommended_answer": recommended_answer,
                "proofs_to_prepare": proofs,
                "answer_to_avoid": avoid,
            },
        }

    def _judge(self, rounds: List[Dict[str, Any]], context: Dict[str, Any], analysis: Dict[str, Any], evidence: Dict[str, Any], language: str) -> Dict[str, Any]:
        score = self._section(analysis, "startup_score")
        potential = self._number(score.get("potential_score") or score.get("score"), 6.0)
        readiness = self._number(score.get("execution_readiness_score"), 5.0)
        evidence_score = self._number(score.get("evidence_confidence_score"), evidence["score"])
        votes = self._votes(evidence_score, readiness, language)
        vote_counts = Counter(vote["vote"] for vote in votes)
        verdict = "CONDITIONAL_GO"
        validated = self._unique([item for rnd in rounds for item in (rnd.get("round_summary") or {}).get("validated_points", [])])
        hypotheses = self._unique([item for rnd in rounds for item in (rnd.get("round_summary") or {}).get("potential_opportunities", [])])
        risks = self._unique([item for rnd in rounds for item in (rnd.get("round_summary") or {}).get("remaining_risks", [])])
        go_conditions = self._unique([item for rnd in rounds for item in (rnd.get("round_summary") or {}).get("go_conditions", [])])
        no_go_conditions = self._unique([item for rnd in rounds for item in (rnd.get("round_summary") or {}).get("no_go_conditions", [])])
        missing = self._global_missing_evidence(analysis, language)
        investment = round(max(0.0, min(10.0, potential * 0.35 + evidence_score * 0.30 + readiness * 0.35)), 1)
        return {
            "format": "investment_committee_memo_v9",
            "status": "completed",
            "context_locked": True,
            "output_language": language,
            "role": "committee_chair",
            "verdict": verdict,
            "verdict_code": "conditional_go",
            "argument_strength_score": round((potential + readiness) / 2, 1),
            "confidence_score": evidence_score,
            "risk_level": "high" if evidence_score < 4.5 else "medium",
            "potential_score": potential,
            "evidence_confidence_score": evidence_score,
            "execution_readiness_score": readiness,
            "investment_attractiveness_score": investment,
            "committee_votes": votes,
            "committee_vote": dict(vote_counts),
            "vetoes": [vote for vote in votes if vote.get("veto")],
            "validated_findings": validated,
            "validated_opportunities": [],
            "potential_opportunities": hypotheses[:8] or [self._t(language, "Hypothesis: the focused pilot can create measurable workflow value.", "Hypothèse : le pilote ciblé peut créer une valeur de workflow mesurable.")],
            "critical_risks": risks[:10],
            "missing_evidence": missing,
            "improved_idea": self._t(language, f"Position {context['title']} around one priority workflow—{context['priority_workflow']}—and expand only after repeated use and payment evidence.", f"Positionner {context['title']} autour d’un workflow prioritaire — {context['priority_workflow']} — et élargir uniquement après preuve de réutilisation et de paiement."),
            "final_recommendation": self._t(language, "Continue only to a limited pilot. Do not approve full rollout or scaling until the GO conditions are met.", "Continuer uniquement vers un pilote limité. Ne pas approuver le déploiement complet ou le passage à l’échelle avant satisfaction des conditions GO."),
            "next_actions": [
                self._t(language, "Observe five target users and measure the current workflow.", "Observer cinq utilisateurs cibles et mesurer le workflow actuel."),
                self._t(language, "Run a two-to-four-week pilot with reuse and task-time metrics.", "Lancer un pilote de deux à quatre semaines avec des métriques de réutilisation et de temps."),
                self._t(language, "Test three concrete prices with economic buyers.", "Tester trois prix concrets avec des acheteurs économiques."),
            ],
            "action_plan": [
                self._t(language, "Week 1: interviews, workflow observation and competitor verification.", "Semaine 1 : entretiens, observation du workflow et vérification des concurrents."),
                self._t(language, "Weeks 2–4: narrow pilot and evidence collection.", "Semaines 2–4 : pilote réduit et collecte des preuves."),
                self._t(language, "Decision review: GO, PIVOT or NO-GO against predefined thresholds.", "Revue de décision : GO, PIVOT ou NO-GO selon les seuils prédéfinis."),
            ],
            "decision_by_round": [
                {
                    "round": rnd.get("round"),
                    "topic": rnd.get("topic"),
                    "decision": (rnd.get("round_summary") or {}).get("decision"),
                    "critic_risk_score": (rnd.get("critic") or {}).get("risk_score"),
                    "main_objection": (rnd.get("critic") or {}).get("main_objection"),
                    "synthesis": (rnd.get("round_summary") or {}).get("synthesis"),
                }
                for rnd in rounds
            ],
            "debate_synthesis": self._t(language, "The committee agrees that the project is testable and potentially useful, but customer urgency, local demand, repeated use, payment and unit economics remain insufficiently evidenced.", "Le comité convient que le projet est testable et potentiellement utile, mais l’urgence client, la demande locale, l’usage répété, le paiement et l’économie unitaire restent insuffisamment prouvés."),
            "go_no_go_conditions": go_conditions[:8],
            "go_conditions": go_conditions[:8],
            "no_go_conditions": no_go_conditions[:8],
            "weak_assumptions": hypotheses[:8],
        }

    def _votes(self, evidence_score: float, readiness: float, language: str) -> List[Dict[str, Any]]:
        base_confidence = 0.30 + (0.04 * evidence_score) + (0.03 * readiness)
        role_adjustments = {
            "customer_problem_analyst": 0.00,
            "market_competition_analyst": -0.10,
            "product_technology_architect": 0.07,
            "business_financial_analyst": -0.04,
            "risk_execution_officer": 0.04,
            "evidence_auditor": -0.07,
        }
        base = [
            ("customer_problem_analyst", "CONDITIONAL_GO", self._t(language, "The problem deserves a measured field test.", "Le problème mérite un test terrain mesuré.")),
            ("market_competition_analyst", "INSUFFICIENT_EVIDENCE", self._t(language, "Local demand and competitive mapping remain incomplete.", "La demande locale et la cartographie concurrentielle restent incomplètes.")),
            ("product_technology_architect", "CONDITIONAL_GO", self._t(language, "A narrow workflow pilot is technically feasible.", "Un pilote de workflow réduit est techniquement faisable.")),
            ("business_financial_analyst", "CONDITIONAL_GO", self._t(language, "The model deserves a real payment test, not scaling.", "Le modèle mérite un vrai test de paiement, pas un passage à l’échelle.")),
            ("risk_execution_officer", "CONDITIONAL_GO", self._t(language, "Risks are manageable only with explicit pilot thresholds.", "Les risques sont gérables uniquement avec des seuils pilote explicites.")),
            ("evidence_auditor", "PIVOT" if evidence_score < 2.5 else "CONDITIONAL_GO", self._t(language, "Claims must remain cautious until compatible evidence is collected.", "Les affirmations doivent rester prudentes jusqu’à collecte de preuves compatibles.")),
        ]
        votes: List[Dict[str, Any]] = []
        for member, vote, reason in base:
            veto = member == "risk_execution_officer" and readiness < 3.0
            confidence = round(
                max(
                    0.25,
                    min(
                        0.90,
                        base_confidence + role_adjustments.get(member, 0.0),
                    ),
                ),
                2,
            )
            votes.append({
                "member": member,
                "vote": vote,
                "confidence": confidence,
                "confidence_basis": {
                    "evidence_score": round(evidence_score, 2),
                    "execution_readiness_score": round(readiness, 2),
                    "role_adjustment": role_adjustments.get(member, 0.0),
                    "formula": "0.30 + 0.04×evidence + 0.03×readiness + role adjustment",
                },
                "blocking_conditions": [self._t(language, "Complete the relevant pilot evidence before scaling.", "Compléter les preuves pilote pertinentes avant le passage à l’échelle.")],
                "reason": reason,
                "veto": veto,
            })
        return votes


    # ------------------------------------------------------------------
    # Context and evidence helpers
    # ------------------------------------------------------------------

    CONFIRMED_ACTOR_STATUSES = {
        "explicit",
        "user_provided",
        "confirmed",
        "validated",
        "provided_by_user",
    }

    def _actor_record(
        self,
        *,
        role: str,
        aliases: Iterable[str],
        structured: Dict[str, Any],
        actors: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, str]:
        provenance = (
            structured.get("actor_provenance")
            or actors.get("provenance")
            or project_context.get("actor_provenance")
            or {}
        )
        if not isinstance(provenance, dict):
            provenance = {}

        raw: Any = None
        status = ""

        for key in aliases:
            if actors.get(key) not in (None, ""):
                raw = actors.get(key)
                break
            if structured.get(key) not in (None, ""):
                raw = structured.get(key)
                break
            if project_context.get(key) not in (None, ""):
                raw = project_context.get(key)
                break

        if isinstance(raw, dict):
            status = self._text(
                raw.get("status")
                or raw.get("source")
                or raw.get("provenance")
            ).lower()
            candidate = self._text(
                raw.get("value")
                or raw.get("name")
                or raw.get("actor")
                or raw.get("label")
            )
        else:
            candidate = self._text(raw)

        provenance_value = provenance.get(role)
        if isinstance(provenance_value, dict):
            status = status or self._text(
                provenance_value.get("status")
                or provenance_value.get("source")
                or provenance_value.get("provenance")
            ).lower()
        else:
            status = status or self._text(provenance_value).lower()

        for key in aliases:
            status = status or self._text(
                structured.get(f"{key}_status")
                or actors.get(f"{key}_status")
                or project_context.get(f"{key}_status")
            ).lower()

        confirmed = status in self.CONFIRMED_ACTOR_STATUSES
        return {
            "value": candidate if confirmed else "",
            "candidate": candidate,
            "status": "explicit" if confirmed else "to_confirm",
        }

    def _context(self, *, title: str, description: str, industry: str, region: str, project_context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        intelligence = self._section(analysis, "project_intelligence") or self._section(project_context, "project_intelligence")
        structured = (
            self._section(analysis, "structured_project_context")
            or self._section(project_context, "structured_project_context")
            or self._section(intelligence, "structured_project_context")
            or project_context
        )
        language = normalize_output_language(
            structured.get("output_language")
            or project_context.get("output_language")
            or "fr"
        )
        targets = self._list(structured.get("target_users"))
        if not targets:
            targets = self._list(self._section(analysis, "market_study").get("target_users"))
        if not targets:
            targets = [self._t(language, "target user", "utilisateur cible")]

        workflows = self._list(
            structured.get("priority_workflows")
            or structured.get("use_cases")
            or structured.get("use_case_terms")
        )
        if not workflows:
            workflows = [
                self._text(
                    structured.get("main_use_case")
                    or structured.get("mvp_scope")
                    or "first operational workflow"
                )
            ]

        problem = self._text(
            structured.get("problem")
            or self._section(analysis, "business_analysis").get("problem")
            or description
        )
        solution = self._text(
            structured.get("solution")
            or self._section(analysis, "business_analysis").get("solution")
            or description
        )
        business_model = self._text(
            structured.get("business_model")
            or self._section(analysis, "business_model_canvas").get("revenue_streams")
            or "pricing model to validate"
        )

        actors = structured.get("actors") or project_context.get("actors") or {}
        if not isinstance(actors, dict):
            actors = {}

        project_archetype = self._text(
            structured.get("project_archetype")
            or project_context.get("project_archetype")
            or "generic_digital_product"
        )

        role_assignments = {
            "payer": self._actor_record(
                role="payer",
                aliases=("payer", "economic_buyer", "budget_owner"),
                structured=structured,
                actors=actors,
                project_context=project_context,
            ),
            "technical_maintainer": self._actor_record(
                role="technical_maintainer",
                aliases=("technical_maintainer", "maintenance_owner", "maintainer"),
                structured=structured,
                actors=actors,
                project_context=project_context,
            ),
            "demand_side": self._actor_record(
                role="demand_side",
                aliases=("demand_side",),
                structured=structured,
                actors=actors,
                project_context=project_context,
            ),
            "supply_side": self._actor_record(
                role="supply_side",
                aliases=("supply_side",),
                structured=structured,
                actors=actors,
                project_context=project_context,
            ),
            "operator_or_partner": self._actor_record(
                role="operator_or_partner",
                aliases=("operator_or_partner", "platform_operator"),
                structured=structured,
                actors=actors,
                project_context=project_context,
            ),
        }

        primary_target = self._text(
            structured.get("primary_target")
            or actors.get("primary_user")
            or actors.get("field_operator")
            or targets[0]
        )
        if isinstance(actors.get("primary_user"), dict):
            primary_target = self._text(
                actors["primary_user"].get("value")
                or actors["primary_user"].get("name")
                or primary_target
            )

        demand_actor = (
            role_assignments["demand_side"]["value"]
            if project_archetype == "two_sided_marketplace"
            else ""
        )
        supply_actor = (
            role_assignments["supply_side"]["value"]
            if project_archetype == "two_sided_marketplace"
            else ""
        )
        operator_actor = (
            role_assignments["operator_or_partner"]["value"]
            if project_archetype == "two_sided_marketplace"
            else ""
        )
        payer_value = role_assignments["payer"]["value"]
        payer_label = payer_value or self._t(
            language,
            "not identified — to validate",
            "non identifié — à valider",
        )
        maintainer_value = role_assignments["technical_maintainer"]["value"]
        maintainer_label = maintainer_value or self._t(
            language,
            "not identified — to validate",
            "non identifié — à valider",
        )

        success_metrics = self._unique(
            self._list(
                structured.get("success_metrics")
                or project_context.get("success_metrics")
            )
        )
        risk_dimensions = self._unique(
            self._list(
                structured.get("risk_dimensions")
                or project_context.get("risk_dimensions")
            )
        )
        evidence_needs = self._unique(
            self._list(
                structured.get("evidence_needs")
                or project_context.get("evidence_needs")
            )
        )

        return {
            "title": self._text(structured.get("project_name") or structured.get("title") or title or "Project"),
            "description": self._text(description),
            "sector": self._text(structured.get("sector") or structured.get("industry") or industry or "target sector"),
            "region": self._text(structured.get("target_region") or structured.get("market_region") or region or "target region"),
            "problem": problem,
            "solution": solution,
            "target_users": targets,
            "primary_target": primary_target,
            "economic_buyer": payer_label,
            "economic_buyer_value": payer_value,
            "economic_buyer_status": role_assignments["payer"]["status"],
            "technical_maintainer": maintainer_label,
            "technical_maintainer_value": maintainer_value,
            "technical_maintainer_status": role_assignments["technical_maintainer"]["status"],
            "priority_workflows": workflows[:6],
            "priority_workflow": self._text(structured.get("priority_workflow") or structured.get("core_action") or workflows[0]),
            "mvp_scope": self._text(structured.get("mvp_scope") or workflows),
            "business_model": business_model,
            "project_archetype": project_archetype,
            "vertical": self._text(structured.get("vertical") or project_context.get("vertical") or "general"),
            "business_motion": self._text(structured.get("business_motion") or project_context.get("business_motion") or "unknown"),
            "interaction_model": self._text(structured.get("interaction_model") or project_context.get("interaction_model") or "generic"),
            "validation_unit": self._text(structured.get("validation_unit") or project_context.get("validation_unit") or "core action"),
            "actors": actors,
            "role_assignments": role_assignments,
            "demand_actor": demand_actor,
            "supply_actor": supply_actor,
            "operator_actor": operator_actor,
            "success_metrics": success_metrics,
            "risk_dimensions": risk_dimensions,
            "evidence_needs": evidence_needs,
        }

    def _frequency_question(self, context: Dict[str, Any], language: str) -> str:
        actor = self._text(context["primary_target"])
        action = self._text(context["priority_workflow"])
        french_actor = actor
        lowered_actor = actor.casefold()
        if actor and not lowered_actor.startswith(
            ("le ", "la ", "les ", "l’", "l'", "un ", "une ", "des ")
        ):
            french_actor = f"les {actor}"

        return self._t(
            language,
            f"How often is the following action currently performed by {actor}: {action}?",
            f"À quelle fréquence l’action suivante est-elle actuellement réalisée "
            f"par {french_actor} : {action} ?",
        )

    def _adaptive_question_confidence(
        self,
        *,
        asked_by: str,
        evidence_status: str,
        round_number: int,
    ) -> float:
        status_base = {
            "supported": 0.68,
            "sourced": 0.66,
            "estimated": 0.52,
            "committee_synthesis": 0.72,
            "field_validation_required": 0.36,
            "not_confirmed": 0.32,
        }.get(str(evidence_status or "").lower(), 0.38)
        role_adjustment = {
            "customer_problem_analyst": 0.04,
            "market_competition_analyst": 0.02,
            "product_technology_architect": 0.03,
            "business_finance_analyst": 0.01,
            "risk_execution_officer": -0.01,
            "evidence_auditor": -0.03,
            "red_team_challenger": -0.05,
            "committee_chair": 0.05,
        }.get(str(asked_by or "").lower(), 0.0)
        round_adjustment = min(0.03, max(0.0, (round_number - 1) * 0.005))
        return round(
            max(0.20, min(0.90, status_base + role_adjustment + round_adjustment)),
            2,
        )

    def _actor_map_answer(self, context: Dict[str, Any], language: str) -> str:
        users = ", ".join(self._text(item) for item in context.get("target_users") or [])
        if context.get("project_archetype") == "two_sided_marketplace":
            demand = context.get("demand_actor") or self._t(language, "not identified", "non identifié")
            supply = context.get("supply_actor") or self._t(language, "not identified", "non identifié")
            operator = context.get("operator_actor") or self._t(language, "not identified", "non identifié")
            return self._t(
                language,
                f"Explicit marketplace roles currently confirmed: demand={demand}, supply={supply}, operator={operator}. Unconfirmed roles remain hypotheses.",
                f"Rôles marketplace explicitement confirmés : demande={demand}, offre={supply}, opérateur={operator}. Les rôles non confirmés restent des hypothèses.",
            )

        return self._t(
            language,
            f"The explicitly targeted user segments are {users}. The payer and technical maintainer are not identified unless separately confirmed.",
            f"Les segments utilisateurs explicitement ciblés sont : {users}. Le payeur et le mainteneur technique ne sont pas identifiés tant qu’ils ne sont pas confirmés séparément.",
        )

    def _payer_answer(self, context: Dict[str, Any], language: str) -> str:
        model = context["business_model"]
        if context.get("economic_buyer_status") == "explicit":
            return self._t(
                language,
                f"The explicitly identified payer is {context['economic_buyer_value']}. The current monetization hypothesis is: {model}.",
                f"Le payeur explicitement identifié est {context['economic_buyer_value']}. L’hypothèse de monétisation actuelle est : {model}.",
            )
        return self._t(
            language,
            f"The economic payer is not yet identified. The monetization model remains a hypothesis to test with real budget owners: {model}.",
            f"Le payeur économique n’est pas encore identifié. Le modèle de monétisation reste une hypothèse à tester avec de vrais détenteurs du budget : {model}.",
        )

    def _evidence_packet(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        score = self._section(analysis, "startup_score")
        level = self._evidence_level(analysis)
        return {
            "level": level,
            "score": self._number(score.get("evidence_confidence_score"), self._evidence_score(level)),
            "sources": self._sources(analysis),
            "claims": self._list(self._section(analysis, "fact_check_report").get("claims")),
            "confidence_by_category": self._section(analysis, "evidence_confidence"),
        }

    def _sources(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Any] = []
        for section_name, keys in (("forgecrawler", ("sources", "public_sources", "retained_sources")), ("competitive_analysis", ("sources", "external_sources", "retained_sources", "public_sources"))):
            section = self._section(analysis, section_name)
            for key in keys:
                value = section.get(key)
                if isinstance(value, list):
                    candidates.extend(value)
        seen = set()
        result: List[Dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            key = str(item.get("url") or item.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _claim_status(
        self,
        analysis: Dict[str, Any],
        category: str,
    ) -> str:
        """Project canonical claim evidence into Debate Room semantics.

        EvidenceLedger / FactChecker remain authoritative for claim evidence
        status. Debate Room only performs the explicit presentation mapping:

        sourced       -> supported
        estimated     -> estimated
        not_confirmed -> not_confirmed

        Public labels and textual status heuristics must never participate in
        this decision.
        """
        canonical_to_debate = {
            "sourced": "supported",
            "estimated": "estimated",
            "not_confirmed": "not_confirmed",
        }

        category_key = str(
            category or ""
        ).casefold()

        for claim in self._list(
            self._section(
                analysis,
                "fact_check_report",
            ).get("claims")
        ):
            if not isinstance(
                claim,
                dict,
            ):
                continue

            haystack = (
                f"{claim.get('category', '')} "
                f"{claim.get('claim', '')}"
            ).casefold()

            if (
                category_key
                and category_key not in haystack
            ):
                continue

            # Current canonical contract.
            canonical_status = str(
                claim.get(
                    "evidence_status"
                )
                or ""
            ).strip().casefold()

            # Backward compatibility for older persisted reports:
            # legacy `status` is accepted only when it already belongs to
            # the canonical EvidenceLedger vocabulary.
            if not canonical_status:
                legacy_status = str(
                    claim.get("status")
                    or ""
                ).strip().casefold()

                if legacy_status in {
                    "sourced",
                    "estimated",
                    "not_confirmed",
                }:
                    canonical_status = (
                        legacy_status
                    )

            return canonical_to_debate.get(
                canonical_status,
                "not_confirmed",
            )

        return "not_confirmed"

    def _evidence_level(self, analysis: Dict[str, Any]) -> str:
        score = self._section(analysis, "startup_score")
        ledger = self._section(analysis, "evidence_confidence")
        fact = self._section(analysis, "fact_check_report")
        value = score.get("evidence_confidence_level") or ledger.get("overall_evidence_confidence") or analysis.get("overall_evidence_confidence") or fact.get("global_confidence") or "low"
        normalized = str(value).lower()
        if "high" in normalized or "élev" in normalized:
            return "high"
        if "medium" in normalized or "moy" in normalized:
            return "medium"
        return "low"

    def _global_missing_evidence(self, analysis: Dict[str, Any], language: str) -> List[str]:
        report = self._section(analysis, "fact_check_report")
        items = self._list(report.get("recommended_next_checks")) + self._list(report.get("limitations"))
        if not items:
            items = [self._t(language, "Observed customer workflows and urgency.", "Workflows clients observés et urgence."), self._t(language, "Official local market evidence and competitor verification.", "Preuves officielles du marché local et vérification concurrentielle."), self._t(language, "Real price tests and pilot unit economics.", "Vrais tests de prix et économie unitaire du pilote.")]
        return self._unique([self._text(item) for item in items])[:8]

    def _committee(self, language: str) -> List[Dict[str, str]]:
        members = [
            ("committee_chair", "Committee Chair", "Président du comité", "Direct the sessions, resolve contradictions and issue the bounded decision.", "Diriger les sessions, résoudre les contradictions et émettre la décision limitée."),
            ("customer_problem_analyst", "Customer and Problem Analyst", "Analyste client et problème", "Test frequency, urgency, behaviour and buyer/user separation.", "Tester fréquence, urgence, comportement et séparation acheteur/utilisateur."),
            ("market_competition_analyst", "Market and Competition Analyst", "Analyste marché et concurrence", "Separate direct products, adjacent solutions, evidence pages and manual alternatives.", "Séparer produits directs, solutions adjacentes, pages de preuve et alternatives manuelles."),
            ("product_technology_architect", "Product and Technology Architect", "Architecte produit et technologie", "Define the smallest valuable workflow and its technical acceptance criteria.", "Définir le plus petit workflow utile et ses critères techniques."),
            ("business_financial_analyst", "Business and Financial Analyst", "Analyste business et financier", "Identify the buyer, test pricing and examine unit economics.", "Identifier l’acheteur, tester le prix et examiner l’économie unitaire."),
            ("risk_execution_officer", "Risk and Execution Officer", "Responsable risque et exécution", "Identify blocking risks, mitigations, vetoes and stop conditions.", "Identifier les risques bloquants, réductions, vétos et conditions d’arrêt."),
            ("evidence_auditor", "Evidence Auditor", "Auditeur des preuves", "Label every claim as supported, estimated, hypothesis or not confirmed.", "Étiqueter chaque affirmation comme soutenue, estimée, hypothèse ou non confirmée."),
            ("red_team_challenger", "Red Team Challenger", "Challenger Red Team", "Attack the three assumptions most likely to destroy the project.", "Attaquer les trois hypothèses les plus susceptibles de détruire le projet."),
        ]
        return [{"id": mid, "role": en if language == "en" else fr, "mandate": mandate_en if language == "en" else mandate_fr, "voting_member": mid not in {"committee_chair", "red_team_challenger"}} for mid, en, fr, mandate_en, mandate_fr in members]

    def _member_positions(self, number: int, language: str, decision: str) -> List[Dict[str, Any]]:
        focus = {
            1: ["customer_problem_analyst", "risk_execution_officer", "evidence_auditor"],
            2: ["market_competition_analyst", "customer_problem_analyst", "evidence_auditor"],
            3: ["product_technology_architect", "customer_problem_analyst", "risk_execution_officer"],
            4: ["business_financial_analyst", "customer_problem_analyst", "risk_execution_officer"],
            5: ["committee_chair", "evidence_auditor", "red_team_challenger"],
        }.get(number, [])
        return [{"member": member, "position": "conditional_support" if decision == "CONDITIONAL_GO" else decision.lower(), "confidence": "medium", "summary": self._t(language, "Support is conditional on the stated evidence and pilot requirements.", "Le soutien dépend des preuves et conditions pilote indiquées.")} for member in focus]

    def _global_meeting_preparation(self, rounds: List[Dict[str, Any]], context: Dict[str, Any], language: str) -> Dict[str, Any]:
        questions: List[str] = []
        answers: List[str] = []
        proofs: List[str] = []
        avoid: List[str] = []
        unresolved: List[str] = []
        for rnd in rounds:
            prep = rnd.get("meeting_preparation") or {}
            questions.extend(self._list(prep.get("likely_questions")))
            answers.extend(self._list(prep.get("recommended_answers")))
            proofs.extend(self._list(prep.get("proofs_to_prepare")))
            avoid.extend(self._list(prep.get("answers_to_avoid")))
            unresolved.extend(self._list(rnd.get("unresolved_questions")))
        return {
            "title": self._t(language, "Real meeting preparation", "Préparation à une réunion réelle"),
            "project": context["title"],
            "top_questions": self._unique(questions)[:12],
            "recommended_answers": self._unique(answers)[:12],
            "proofs_to_prepare": self._unique(proofs)[:12],
            "answers_to_avoid": self._unique(avoid)[:10],
            "unresolved_questions": self._unique(unresolved)[:10],
        }

    def _fallback(self, context: Dict[str, Any], language: str, error: str) -> Dict[str, Any]:
        return {
            "format": "investment_committee_memo_v9_fallback",
            "status": "completed_with_fallback",
            "verdict": "INSUFFICIENT_EVIDENCE",
            "verdict_code": "insufficient_evidence",
            "risk_level": "high",
            "argument_strength_score": 2.0,
            "confidence_score": 1.0,
            "validated_opportunities": [],
            "potential_opportunities": [self._t(language, "Hypothesis: the project may justify a reduced validation test.", "Hypothèse : le projet peut justifier un test de validation réduit.")],
            "critical_risks": [self._t(language, "The committee could not complete its structured review.", "Le comité n’a pas pu terminer sa revue structurée.")],
            "missing_evidence": [self._t(language, "Manual review of the analysis is required.", "Une revue manuelle de l’analyse est requise.")],
            "final_recommendation": self._t(language, "Do not scale. Review the analysis and rerun the committee.", "Ne pas passer à l’échelle. Revoir l’analyse et relancer le comité."),
            "improved_idea": self._t(language, f"Reduce {context.get('title', 'the project')} to one measurable workflow.", f"Réduire {context.get('title', 'le projet')} à un workflow mesurable."),
            "next_actions": [self._t(language, "Review the error and validate the project manually.", "Revoir l’erreur et valider le projet manuellement.")],
            "go_no_go_conditions": [self._t(language, "NO-GO for scaling until the review is complete.", "NO-GO pour le passage à l’échelle tant que la revue n’est pas terminée.")],
            "error": error,
        }

    @staticmethod
    def _section(data: Dict[str, Any], key: str) -> Dict[str, Any]:
        value = data.get(key)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _list(value: Any) -> List[Any]:
        if isinstance(value, list):
            return value
        if value in (None, ""):
            return []
        return [value]

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        return " ".join(str(value or "").split()).strip()

    @staticmethod
    def _number(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _evidence_score(level: str) -> float:
        return {"low": 3.0, "medium": 5.5, "high": 8.0}.get(level, 3.0)

    @staticmethod
    def _unique(items: Iterable[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for item in items:
            text = " ".join(str(item or "").split()).strip()
            if not text or text.casefold() in seen:
                continue
            seen.add(text.casefold())
            result.append(text)
        return result

    @staticmethod
    def _t_list(language: str, english: List[str], french: List[str]) -> List[str]:
        return english if language == "en" else french

    @staticmethod
    def _t(language: str, english: str, french: str) -> str:
        return english if language == "en" else french