from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class PersonaBuilderAgent:
    """Build three role-specific personas from the locked intelligence packet."""

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        try:
            context = self._context(state)
            return self._build(context, language)
        except Exception as exc:
            return self._fallback(language, str(exc))

    def _build(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        archetype = context.get("project_archetype") or "generic_digital_product"
        if archetype == "two_sided_marketplace":
            return self._build_marketplace(context, language)
        if archetype == "hardware_iot":
            return self._build_hardware(context, language)
        if archetype in {"consumer_transactional_app", "ecommerce", "regulated_service", "content_community", "analytics_ai_tool", "generic_digital_product"}:
            return self._build_consumer_product(context, language)

        segments = self._segments(context, language)
        names = self._role_names(segments, context, language)
        workflows = self._workflows(context, language)
        alternatives = self._alternatives(context["problem"], language)

        personas = [
            self._operational_user(
                name=names[0],
                segment=segments[0],
                workflow=workflows[0],
                context=context,
                alternatives=alternatives,
                language=language,
            ),
            self._economic_buyer(
                name=names[1],
                segment=segments[1],
                workflow=workflows[1],
                context=context,
                alternatives=alternatives,
                language=language,
            ),
            self._adoption_gatekeeper(
                name=names[2],
                segment=segments[2],
                workflow=workflows[2],
                context=context,
                alternatives=alternatives,
                language=language,
            ),
        ]

        if language == "en":
            summary = (
                f"The persona set for {context['title']} separates the daily operator, "
                "the economic buyer and the adoption gatekeeper. Each profile owns a "
                "different workflow, decision and success metric."
            )
            buyer_user = (
                "The operational user proves usability and repeated workflow value; "
                "the economic buyer validates budget and return; the gatekeeper tests "
                "onboarding, data migration and operational risk."
            )
            validation = [
                f"Observe five {segments[0]} completing: {workflows[0]}.",
                f"Test a real price and pilot scope with three {segments[1]}.",
                f"Ask three {segments[2]} to identify duplicate work, training and data risks.",
                "Run a two-to-four-week pilot and measure activation, weekly reuse and abandonment.",
            ]
            risks = [
                "The user, buyer and adoption blocker may be different people.",
                "A broad segment can hide different workflows and budgets.",
                "A useful product may still fail if data entry or onboarding is slower than the current method.",
            ]
        else:
            summary = (
                f"Les personas de {context['title']} séparent l’opérateur quotidien, "
                "l’acheteur économique et le gardien de l’adoption. Chaque profil possède "
                "un workflow, une décision et une métrique distincts."
            )
            buyer_user = (
                "L’utilisateur opérationnel valide l’utilisabilité et la valeur répétée ; "
                "l’acheteur valide le budget et le retour ; le gardien teste l’onboarding, "
                "la reprise des données et le risque opérationnel."
            )
            validation = [
                f"Observer cinq {segments[0]} pendant : {workflows[0]}.",
                f"Tester un vrai prix et un périmètre pilote avec trois {segments[1]}.",
                f"Demander à trois {segments[2]} d’identifier la double saisie, la formation et les risques de données.",
                "Lancer un pilote de deux à quatre semaines et mesurer activation, réutilisation et abandon.",
            ]
            risks = [
                "L’utilisateur, l’acheteur et le bloqueur d’adoption peuvent être différents.",
                "Un segment large peut masquer des workflows et budgets différents.",
                "Un produit utile peut échouer si la saisie ou l’onboarding est plus lent que la méthode actuelle.",
            ]

        return {
            "format": "persona_builder_v7_distinct_workflows",
            "status": "completed",
            "output_language": language,
            "context_locked": True,
            "persona_summary": summary,
            "summary": summary,
            "primary_persona": personas[0],
            "personas": personas,
            "target_segments": segments,
            "buyer_user_difference": buyer_user,
            "validation_questions": validation,
            "recommended_validation_method": validation,
            "persona_risks": risks,
            "limitations": risks,
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "project_context_used": context,
        }

    def _build_marketplace(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        actors = context.get("actors") or {}
        targets = context.get("target_users") or []
        demand = self._text(actors.get("demand_side") or (targets[0] if targets else ""))
        supply = self._text(actors.get("supply_side") or (targets[1] if len(targets) > 1 else ""))
        operator = self._text(actors.get("operator_or_partner") or (targets[2] if len(targets) > 2 else ""))
        payer = self._text(actors.get("payer") or demand)
        workflows = self._workflows(context, language)
        metrics = context.get("success_metrics") or []
        risks = context.get("risk_dimensions") or []

        demand = demand or ("Demand-side customer" if language == "en" else "Client côté demande")
        supply = supply or ("Supply-side provider" if language == "en" else "Prestataire côté offre")
        operator = operator or ("Platform operator or partner" if language == "en" else "Opérateur ou partenaire de la plateforme")

        if language == "en":
            personas = [
                {
                    "id": "demand_side_user", "name": demand, "persona_name": demand,
                    "role": "Demand-side user and transaction initiator", "segment": demand,
                    "profile": f"A user in {context['region']} who initiates the core transaction and expects a fast, trustworthy result.",
                    "main_pain": context["problem"],
                    "goals": [f"Complete: {workflows[0]}.", "Receive clear confirmation, status and recovery when the transaction fails."],
                    "frustrations": ["Uncertain availability, long waiting time or unclear status.", "Low trust, cancellations or inconsistent service quality."],
                    "current_alternatives": ["Call or message providers directly", "Use an incumbent platform", "Continue offline search"],
                    "expected_value": "A reliable match with transparent status, price and completion.",
                    "adoption_trigger": "Adopts when the first transaction succeeds faster than the current alternative.",
                    "adoption_obstacles": ["No supply in the required area or time", "Trust, safety or payment concerns"],
                    "buying_power": "low-to-medium", "decision_power": "high for own transaction",
                    "success_metrics": metrics[:3] or ["Successful transaction rate", "Time to match", "Repeat usage"],
                    "use_case": workflows[0],
                    "message_to_convince": "Show reliable availability, clear confirmation and a safe recovery path.",
                    "interview_questions": ["How do you complete this transaction today?", "What makes you cancel or switch to another option?"],
                },
                {
                    "id": "supply_side_provider", "name": supply, "persona_name": supply,
                    "role": "Supply-side provider", "segment": supply,
                    "profile": f"A provider in {context['region']} who accepts and fulfils relevant demand while protecting earnings and operating capacity.",
                    "main_pain": "Demand is fragmented, poorly qualified or difficult to accept under clear operating conditions.",
                    "goals": [f"Complete: {workflows[1]}.", "Improve utilization, earnings and predictable demand without losing control."],
                    "frustrations": ["Low-quality requests, cancellations and unpaid time.", "High platform fees or poor geographic matching."],
                    "current_alternatives": ["Direct outreach and manually coordinated transactions", "Existing intermediary or specialized solution", "Established customer or partner network"],
                    "expected_value": "More relevant demand, lower idle time and transparent economics.",
                    "adoption_trigger": "Joins when qualified demand and net earnings exceed current channels.",
                    "adoption_obstacles": ["Weak demand liquidity", "Unclear fees, rules or dispute handling"],
                    "buying_power": "medium", "decision_power": "high for supply participation",
                    "success_metrics": metrics[1:4] or ["Accepted requests", "Completion rate", "Net earnings per active hour"],
                    "use_case": workflows[1],
                    "message_to_convince": "Prove relevant demand, transparent fees and operational control.",
                    "interview_questions": ["Which requests are worth accepting?", "What fee or rule would make you leave the platform?"],
                },
                {
                    "id": "platform_operator", "name": operator, "persona_name": operator,
                    "role": "Platform operations, trust and ecosystem partner", "segment": operator,
                    "profile": f"An operator or partner in {context['region']} responsible for liquidity, quality, safety and compliance.",
                    "main_pain": "The service fails when supply, demand, trust and operational rules are not balanced.",
                    "goals": [f"Complete: {workflows[2]}.", "Keep the marketplace safe, liquid and economically sustainable."],
                    "frustrations": ["Coverage gaps, fraud, complaints and cancellations.", "Growth that increases incentives or support cost faster than revenue."],
                    "current_alternatives": ["Transactions coordinated with generic tools", "Local or sector partners", "Existing operational solutions"],
                    "expected_value": "Predictable marketplace quality, compliance and contribution margin.",
                    "adoption_trigger": "Supports rollout when service thresholds, responsibilities and incident handling are explicit.",
                    "adoption_obstacles": risks[:3] or ["Regulatory constraints", "Trust and safety incidents", "Negative unit economics"],
                    "buying_power": "medium-to-high", "decision_power": "high",
                    "success_metrics": metrics or ["Liquidity by zone", "Cancellation rate", "Contribution margin"],
                    "use_case": workflows[2],
                    "message_to_convince": "Run a bounded launch with supply, safety and economics thresholds.",
                    "interview_questions": ["Which operational threshold blocks launch?", "Who owns incidents, compliance and service quality?"],
                },
            ]
            summary = f"The personas for {context['title']} separate demand, supply and platform operations. Marketplace success requires all three sides to work at the same time."
            buyer_user = f"{payer} initiates or pays for the transaction; {supply} fulfils it; {operator} protects liquidity, trust and compliance."
            validation = [
                f"Observe five {demand} attempting: {workflows[0]}.",
                f"Interview five {supply} about acceptance, earnings and cancellation thresholds.",
                "Run a bounded liquidity test on the first transaction scope before broad rollout.",
                "Measure completed transactions, time to match, repeat use and contribution margin.",
            ]
            persona_risks = risks or ["Demand and supply may not be active under the same transaction conditions.", "Trust, safety, regulation and incentives can block the model."]
        else:
            personas = [
                {
                    "id": "demand_side_user", "name": demand, "persona_name": demand,
                    "role": "Utilisateur côté demande et initiateur de la transaction", "segment": demand,
                    "profile": f"Un utilisateur en {context['region']} qui lance la transaction principale et attend un résultat rapide et fiable.",
                    "main_pain": context["problem"],
                    "goals": [f"Réaliser : {workflows[0]}.", "Recevoir une confirmation, un suivi et une solution claire en cas d’échec."],
                    "frustrations": ["Disponibilité incertaine, attente longue ou statut peu clair.", "Manque de confiance, annulations ou qualité irrégulière."],
                    "current_alternatives": ["Appeler ou contacter directement les prestataires", "Utiliser une plateforme existante", "Continuer la recherche hors ligne"],
                    "expected_value": "Une mise en relation fiable avec statut, prix et réalisation transparents.",
                    "adoption_trigger": "Adopte lorsque la première transaction réussit plus vite que l’alternative actuelle.",
                    "adoption_obstacles": ["Aucune offre disponible dans la zone ou au moment voulu", "Préoccupations de confiance, sécurité ou paiement"],
                    "buying_power": "faible à moyen", "decision_power": "élevé pour sa propre transaction",
                    "success_metrics": metrics[:3] or ["Taux de transaction réussie", "Temps de mise en relation", "Usage répété"],
                    "use_case": workflows[0],
                    "message_to_convince": "Montrer une disponibilité fiable, une confirmation claire et un parcours sécurisé.",
                    "interview_questions": ["Comment réalisez-vous cette transaction aujourd’hui ?", "Qu’est-ce qui vous fait annuler ou choisir une autre option ?"],
                },
                {
                    "id": "supply_side_provider", "name": supply, "persona_name": supply,
                    "role": "Prestataire côté offre", "segment": supply,
                    "profile": f"Un prestataire en {context['region']} qui accepte et réalise les demandes pertinentes tout en protégeant son revenu et sa capacité opérationnelle.",
                    "main_pain": "La demande est dispersée, mal qualifiée ou difficile à accepter selon des conditions opérationnelles claires.",
                    "goals": [f"Réaliser : {workflows[1]}.", "Améliorer l’utilisation, le revenu et la prévisibilité sans perdre le contrôle."],
                    "frustrations": ["Demandes faibles, annulations et temps non rémunéré.", "Frais élevés ou mauvaise correspondance géographique."],
                    "current_alternatives": ["Prospection directe et transactions coordonnées manuellement", "Intermédiaire ou solution spécialisée existante", "Réseau établi de clients ou partenaires"],
                    "expected_value": "Plus de demandes pertinentes, moins de temps mort et une économie transparente.",
                    "adoption_trigger": "Rejoint lorsque la demande qualifiée et le revenu net dépassent les canaux actuels.",
                    "adoption_obstacles": ["Demande insuffisante", "Frais, règles ou gestion des litiges peu clairs"],
                    "buying_power": "moyen", "decision_power": "élevé pour la participation côté offre",
                    "success_metrics": metrics[1:4] or ["Demandes acceptées", "Taux de réalisation", "Revenu net par heure active"],
                    "use_case": workflows[1],
                    "message_to_convince": "Prouver la qualité de la demande, la transparence des frais et le contrôle opérationnel.",
                    "interview_questions": ["Quelles demandes valent la peine d’être acceptées ?", "Quel frais ou quelle règle vous ferait quitter la plateforme ?"],
                },
                {
                    "id": "platform_operator", "name": operator, "persona_name": operator,
                    "role": "Opérations de plateforme, confiance et partenaire écosystème", "segment": operator,
                    "profile": f"Un opérateur ou partenaire en {context['region']} responsable de la liquidité, de la qualité, de la sécurité et de la conformité.",
                    "main_pain": "Le service échoue lorsque l’offre, la demande, la confiance et les règles opérationnelles ne sont pas équilibrées.",
                    "goals": [f"Réaliser : {workflows[2]}.", "Maintenir une marketplace sûre, liquide et économiquement viable."],
                    "frustrations": ["Zones non couvertes, fraude, plaintes et annulations.", "Croissance qui augmente les incitations ou le support plus vite que les revenus."],
                    "current_alternatives": ["Transactions coordonnées avec des outils génériques", "Partenaires locaux ou sectoriels", "Solutions opérationnelles existantes"],
                    "expected_value": "Qualité, conformité et marge contributive prévisibles.",
                    "adoption_trigger": "Soutient le déploiement lorsque les seuils, responsabilités et incidents sont clairement définis.",
                    "adoption_obstacles": risks[:3] or ["Contraintes réglementaires", "Incidents de confiance ou sécurité", "Économie unitaire négative"],
                    "buying_power": "moyen à élevé", "decision_power": "élevé",
                    "success_metrics": metrics or ["Liquidité par zone", "Taux d’annulation", "Marge contributive"],
                    "use_case": workflows[2],
                    "message_to_convince": "Lancer un pilote limité avec des seuils d’offre, de sécurité et d’économie.",
                    "interview_questions": ["Quel seuil opérationnel bloque le lancement ?", "Qui gère les incidents, la conformité et la qualité ?"],
                },
            ]
            summary = f"Les personas de {context['title']} séparent la demande, l’offre et les opérations de plateforme. Le succès exige que les trois côtés fonctionnent simultanément."
            buyer_user = f"{payer} initie ou paie la transaction ; {supply} la réalise ; {operator} protège la liquidité, la confiance et la conformité."
            validation = [
                f"Observer cinq {demand} pendant : {workflows[0]}.",
                f"Interroger cinq {supply} sur l’acceptation, le revenu et les annulations.",
                "Tester la liquidité sur le premier périmètre transactionnel avant un déploiement large.",
                "Mesurer les transactions réalisées, le temps de mise en relation, la réutilisation et la marge contributive.",
            ]
            persona_risks = risks or ["L’offre et la demande peuvent ne pas être actives dans les mêmes conditions transactionnelles.", "La confiance, la sécurité, la réglementation et les incitations peuvent bloquer le modèle."]

        return self._result(
            context=context,
            language=language,
            personas=personas,
            summary=summary,
            buyer_user=buyer_user,
            validation=validation,
            risks=persona_risks,
            format_name="persona_builder_v8_marketplace_aware",
        )

    def _build_hardware(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Build hardware personas without inventing buyer or maintainer roles.

        Target segments supplied by the user remain target-user personas. A segment is
        promoted to economic buyer or technical maintainer only when the original
        description names that responsibility explicitly.
        """
        targets = self._unique(
            [self._text(item) for item in context.get("target_users") or [] if self._text(item)]
        )
        default_targets = (
            ["Primary field user", "Secondary field user", "Deployment stakeholder"]
            if language == "en"
            else ["Utilisateur terrain principal", "Utilisateur terrain secondaire", "Partie prenante au déploiement"]
        )
        for default in default_targets:
            if len(targets) >= 3:
                break
            targets.append(default)
        targets = targets[:3]

        workflows = self._workflows(context, language)
        metrics = self._list(context.get("success_metrics"))
        risks = self._clean_risk_dimensions(
            self._list(context.get("constraints"))
            + self._list(context.get("risk_dimensions"))
        )
        explicit_buyer = self._text(context.get("explicit_economic_buyer"))
        explicit_maintainer = self._text(context.get("explicit_maintainer"))

        personas: List[Dict[str, Any]] = []
        for index, target in enumerate(targets):
            is_buyer = bool(explicit_buyer and self._same_actor(target, explicit_buyer))
            is_maintainer = bool(
                explicit_maintainer and self._same_actor(target, explicit_maintainer)
            )

            if language == "en":
                role = "Explicit field target user"
                if is_buyer:
                    role += " and confirmed economic buyer"
                if is_maintainer:
                    role += " and confirmed technical maintainer"
                profile = (
                    f"An explicitly named target segment in {context['region']} that uses, "
                    "evaluates or is affected by the field device. Purchase and maintenance "
                    "responsibilities are not assumed without direct evidence."
                )
                goals = [
                    workflows[index],
                    "Validate field usefulness, reliability and operating effort in real conditions.",
                ]
                fallback_risks = [
                    "Field reliability remains unproven.",
                    "Deployment, connectivity and maintenance effort require testing.",
                ]
                alternatives = ["Manual inspection", "Existing equipment", "Outsourced service"]
                expected_value = "Reliable field results at an acceptable total deployed cost."
                adoption_trigger = (
                    "Adopts after a bounded field trial meets the agreed accuracy, uptime, "
                    "usability and recovery thresholds."
                )
                message = (
                    "Demonstrate the complete field workflow, measurable limits, maintenance "
                    "responsibility and a safe fallback."
                )
                questions = [
                    "Which field result would make the pilot useful?",
                    "Which failure, operating burden or maintenance condition is unacceptable?",
                ]
                unknown = "unknown — to validate"
                role_status = "explicit_target_user"
                buyer_status = "explicit" if is_buyer else "not_identified"
                maintenance_status = "explicit" if is_maintainer else "not_identified"
            else:
                role = "Utilisateur cible terrain explicitement mentionné"
                if is_buyer:
                    role += " et acheteur économique confirmé"
                if is_maintainer:
                    role += " et mainteneur technique confirmé"
                profile = (
                    f"Un segment cible explicitement mentionné en {context['region']} qui utilise, "
                    "évalue ou subit les effets du dispositif terrain. Les responsabilités "
                    "d’achat et de maintenance ne sont jamais supposées sans preuve directe."
                )
                goals = [
                    workflows[index],
                    "Valider l’utilité terrain, la fiabilité et l’effort d’exploitation en conditions réelles.",
                ]
                fallback_risks = [
                    "La fiabilité terrain reste à démontrer.",
                    "Le déploiement, la connectivité et la maintenance doivent être testés.",
                ]
                alternatives = ["Inspection manuelle", "Équipement existant", "Service externalisé"]
                expected_value = "Des résultats terrain fiables à un coût total déployé acceptable."
                adoption_trigger = (
                    "Adopte après un pilote limité respectant les seuils convenus de précision, "
                    "disponibilité, utilisabilité et reprise."
                )
                message = (
                    "Démontrer le workflow terrain complet, les limites mesurables, la "
                    "responsabilité de maintenance et un mode de repli sûr."
                )
                questions = [
                    "Quel résultat terrain rendrait le pilote utile ?",
                    "Quel échec, effort d’exploitation ou condition de maintenance serait inacceptable ?",
                ]
                unknown = "inconnu — à valider"
                role_status = "utilisateur_cible_explicite"
                buyer_status = "explicite" if is_buyer else "non_identifie"
                maintenance_status = "explicite" if is_maintainer else "non_identifie"

            personas.append(
                {
                    "id": f"hardware_target_user_{index + 1}",
                    "name": target,
                    "persona_name": target,
                    "role": role,
                    "role_status": role_status,
                    "role_source": "user_project_description",
                    "segment": target,
                    "profile": profile,
                    "main_pain": context["problem"],
                    "goals": goals,
                    "frustrations": risks[:3] or fallback_risks,
                    "current_alternatives": alternatives,
                    "expected_value": expected_value,
                    "adoption_trigger": adoption_trigger,
                    "adoption_obstacles": risks[:4] or fallback_risks,
                    "buying_power": "medium" if is_buyer and language == "en" else (
                        "moyen" if is_buyer else unknown
                    ),
                    "decision_power": "high" if is_buyer and language == "en" else (
                        "élevé" if is_buyer else unknown
                    ),
                    "buyer_status": buyer_status,
                    "maintenance_status": maintenance_status,
                    "success_metrics": metrics or (
                        ["Task success", "Detection accuracy", "Availability", "Recovery time"]
                        if language == "en"
                        else ["Réussite de la tâche", "Précision de détection", "Disponibilité", "Temps de reprise"]
                    ),
                    "use_case": workflows[index],
                    "message_to_convince": message,
                    "interview_questions": questions,
                }
            )

        if language == "en":
            buyer_label = explicit_buyer or "not identified in the project description"
            maintainer_label = explicit_maintainer or "not identified in the project description"
            summary = (
                f"The personas for {context['title']} preserve the three explicit target "
                "segments. Buyer and maintainer responsibilities remain separate hypotheses "
                "until the project description or interviews identify them."
            )
            buyer_user = (
                f"Explicit target users: {', '.join(targets)}. Economic buyer: {buyer_label}. "
                f"Technical maintainer: {maintainer_label}."
            )
            validation = [
                f"Run field trials with representatives of: {', '.join(targets)}.",
                "Identify who owns the pilot budget and obtain a real approval or refusal.",
                "Identify who installs, maintains and recovers the device after failure.",
                "Measure accuracy, task completion, availability, maintenance time and deployed cost.",
            ]
        else:
            buyer_label = explicit_buyer or "non identifié dans la description du projet"
            maintainer_label = explicit_maintainer or "non identifié dans la description du projet"
            summary = (
                f"Les personas de {context['title']} conservent les trois segments cibles "
                "explicitement mentionnés. Les responsabilités d’achat et de maintenance "
                "restent des hypothèses tant que la description ou les entretiens ne les identifient pas."
            )
            buyer_user = (
                f"Utilisateurs cibles explicites : {', '.join(targets)}. Acheteur économique : "
                f"{buyer_label}. Mainteneur technique : {maintainer_label}."
            )
            validation = [
                f"Réaliser des essais terrain avec des représentants de : {', '.join(targets)}.",
                "Identifier le détenteur du budget pilote et obtenir une décision réelle.",
                "Identifier qui installe, maintient et remet le dispositif en service après panne.",
                "Mesurer la précision, la réussite de la tâche, la disponibilité, le temps de maintenance et le coût déployé.",
            ]

        result = self._result(
            context=context,
            language=language,
            personas=personas,
            summary=summary,
            buyer_user=buyer_user,
            validation=validation,
            risks=risks,
            format_name="persona_builder_v10_hardware_roles_evidence_locked",
        )
        result["actor_role_map"] = {
            "explicit_target_users": targets,
            "economic_buyer": explicit_buyer or None,
            "economic_buyer_status": "explicit" if explicit_buyer else "to_validate",
            "technical_maintainer": explicit_maintainer or None,
            "technical_maintainer_status": "explicit" if explicit_maintainer else "to_validate",
        }
        return result

    def _build_consumer_product(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        actors = context.get("actors") or {}
        targets = context.get("target_users") or []
        primary = self._text(
            actors.get("demand_side")
            or (targets[0] if targets else ("Primary user" if language == "en" else "Utilisateur principal"))
        )
        payer = self._text(
            actors.get("payer")
            or context.get("economic_buyer")
            or primary
        )
        partner = self._text(
            actors.get("operator_or_partner")
            or (targets[2] if len(targets) > 2 else ("Operational partner" if language == "en" else "Partenaire opérationnel"))
        )
        workflows = self._workflows(context, language)
        metrics = context.get("success_metrics") or []
        risks = context.get("risk_dimensions") or []
        alternatives = self._alternatives(context["problem"], language)

        if language == "en":
            personas = [
                {
                    "id": "primary_consumer",
                    "name": primary,
                    "persona_name": primary,
                    "role": "Primary user",
                    "segment": primary,
                    "profile": f"A person in {context['region']} who directly attempts the core action.",
                    "main_pain": context["problem"],
                    "goals": [f"Complete the intended outcome: {workflows[0]}.", "Understand the result and next step without specialist help."],
                    "frustrations": ["Unclear value before the first successful outcome.", "Too many steps, delays or failed actions."],
                    "current_alternatives": alternatives,
                    "expected_value": "A faster, clearer or more reliable successful outcome.",
                    "adoption_trigger": "Adopts after one complete action produces a visible benefit.",
                    "adoption_obstacles": risks[:3],
                    "buying_power": "low-to-medium",
                    "decision_power": "medium",
                    "success_metrics": metrics or ["Activation", "Successful core action", "Repeat use"],
                    "use_case": workflows[0],
                    "message_to_convince": "Show one complete outcome, the time required and the recovery path when it fails.",
                    "interview_questions": [f"Show how you achieve this outcome today: {workflows[0]}.", "What would make you return after the first use?"],
                },
                {
                    "id": "payer",
                    "name": payer,
                    "persona_name": payer,
                    "role": "Payer or purchase decision-maker",
                    "segment": payer,
                    "profile": f"The actor in {context['region']} who decides whether the outcome is worth paying for.",
                    "main_pain": context["problem"],
                    "goals": [f"Pay only when {workflows[1]} creates measurable value.", "Understand price, risk and alternative cost."],
                    "frustrations": ["A price disconnected from measurable value.", "Unclear recurring benefit or delivery responsibility."],
                    "current_alternatives": alternatives,
                    "expected_value": "A credible value-price relationship and predictable service level.",
                    "adoption_trigger": "Accepts a concrete offer tied to a measurable outcome.",
                    "adoption_obstacles": risks[:3],
                    "buying_power": "medium",
                    "decision_power": "high",
                    "success_metrics": metrics or ["Paid conversion", "Repeat purchase", "Contribution margin"],
                    "use_case": workflows[1],
                    "message_to_convince": "Tie the offer to a measurable result and a reversible first test.",
                    "interview_questions": ["Which result would justify payment?", "What price or risk would cause rejection?"],
                },
                {
                    "id": "operational_partner",
                    "name": partner,
                    "persona_name": partner,
                    "role": "Operational, trust or delivery partner",
                    "segment": partner,
                    "profile": f"An actor in {context['region']} who affects delivery, trust, safety or compliance.",
                    "main_pain": context["problem"],
                    "goals": [f"Ensure {workflows[2]} is reliable and responsibly operated.", "Limit incidents, support burden and unclear ownership."],
                    "frustrations": ["Unclear responsibility when delivery fails.", "Operational load that grows faster than value."],
                    "current_alternatives": alternatives,
                    "expected_value": "Clear ownership, measurable reliability and manageable operational burden.",
                    "adoption_trigger": "Participates when thresholds, responsibilities and escalation are explicit.",
                    "adoption_obstacles": risks[:3],
                    "buying_power": "low-to-medium",
                    "decision_power": "medium-to-high",
                    "success_metrics": metrics or ["Reliability", "Incident rate", "Resolution time"],
                    "use_case": workflows[2],
                    "message_to_convince": "Define responsibilities, acceptance thresholds and a safe fallback.",
                    "interview_questions": ["Which failure is unacceptable?", "Who owns support, recovery and compliance?"],
                },
            ]
            summary = f"The personas for {context['title']} separate the primary user, payer and operational trust partner."
            buyer_user = f"{primary} uses the product; {payer} validates payment; {partner} affects delivery, trust or compliance."
            validation = [f"Observe five {primary} completing the core action.", f"Test payment with three {payer}.", f"Validate delivery and trust constraints with {partner}."]
        else:
            personas = [
                {
                    "id": "primary_consumer",
                    "name": primary,
                    "persona_name": primary,
                    "role": "Utilisateur principal",
                    "segment": primary,
                    "profile": f"Une personne en {context['region']} qui tente directement l’action principale.",
                    "main_pain": context["problem"],
                    "goals": [f"Obtenir le résultat prévu : {workflows[0]}.", "Comprendre le résultat et la prochaine étape sans aide spécialisée."],
                    "frustrations": ["Valeur peu claire avant le premier résultat réussi.", "Trop d’étapes, délais ou actions échouées."],
                    "current_alternatives": alternatives,
                    "expected_value": "Un résultat réussi plus rapide, clair ou fiable.",
                    "adoption_trigger": "Adopte après une action complète produisant un bénéfice visible.",
                    "adoption_obstacles": risks[:3],
                    "buying_power": "faible à moyen",
                    "decision_power": "moyen",
                    "success_metrics": metrics or ["Activation", "Action principale réussie", "Usage répété"],
                    "use_case": workflows[0],
                    "message_to_convince": "Montrer un résultat complet, le temps nécessaire et le chemin de reprise en cas d’échec.",
                    "interview_questions": [f"Montrez comment vous obtenez ce résultat aujourd’hui : {workflows[0]}.", "Qu’est-ce qui vous ferait revenir après le premier usage ?"],
                },
                {
                    "id": "payer",
                    "name": payer,
                    "persona_name": payer,
                    "role": "Payeur ou décideur d’achat",
                    "segment": payer,
                    "profile": f"L’acteur en {context['region']} qui décide si le résultat mérite un paiement.",
                    "main_pain": context["problem"],
                    "goals": [f"Payer seulement si {workflows[1]} crée une valeur mesurable.", "Comprendre le prix, le risque et le coût de l’alternative."],
                    "frustrations": ["Prix déconnecté d’une valeur mesurable.", "Bénéfice répété ou responsabilité de réalisation peu clairs."],
                    "current_alternatives": alternatives,
                    "expected_value": "Un rapport valeur-prix crédible et un niveau de service prévisible.",
                    "adoption_trigger": "Accepte une offre concrète liée à un résultat mesurable.",
                    "adoption_obstacles": risks[:3],
                    "buying_power": "moyen",
                    "decision_power": "élevé",
                    "success_metrics": metrics or ["Conversion payante", "Achat répété", "Marge contributive"],
                    "use_case": workflows[1],
                    "message_to_convince": "Relier l’offre à un résultat mesurable et à un premier test réversible.",
                    "interview_questions": ["Quel résultat justifierait un paiement ?", "Quel prix ou risque provoquerait un refus ?"],
                },
                {
                    "id": "operational_partner",
                    "name": partner,
                    "persona_name": partner,
                    "role": "Partenaire opérationnel, de confiance ou de réalisation",
                    "segment": partner,
                    "profile": f"Un acteur en {context['region']} qui influence la réalisation, la confiance, la sécurité ou la conformité.",
                    "main_pain": context["problem"],
                    "goals": [f"Garantir que {workflows[2]} est fiable et opéré de manière responsable.", "Limiter les incidents, la charge de support et les responsabilités floues."],
                    "frustrations": ["Responsabilité peu claire lorsque la réalisation échoue.", "Charge opérationnelle qui augmente plus vite que la valeur."],
                    "current_alternatives": alternatives,
                    "expected_value": "Responsabilités claires, fiabilité mesurable et charge opérationnelle maîtrisée.",
                    "adoption_trigger": "Participe lorsque les seuils, responsabilités et escalades sont explicites.",
                    "adoption_obstacles": risks[:3],
                    "buying_power": "faible à moyen",
                    "decision_power": "moyen à élevé",
                    "success_metrics": metrics or ["Fiabilité", "Taux d’incident", "Temps de résolution"],
                    "use_case": workflows[2],
                    "message_to_convince": "Définir les responsabilités, les seuils d’acceptation et un mode sûr de repli.",
                    "interview_questions": ["Quel échec est inacceptable ?", "Qui porte le support, la reprise et la conformité ?"],
                },
            ]
            summary = f"Les personas de {context['title']} séparent l’utilisateur principal, le payeur et le partenaire de confiance opérationnel."
            buyer_user = f"{primary} utilise le produit ; {payer} valide le paiement ; {partner} influence la réalisation, la confiance ou la conformité."
            validation = [f"Observer cinq {primary} pendant l’action principale.", f"Tester le paiement avec trois {payer}.", f"Valider la réalisation et la confiance avec {partner}."]

        return self._result(
            context=context,
            language=language,
            personas=personas,
            summary=summary,
            buyer_user=buyer_user,
            validation=validation,
            risks=risks,
            format_name="persona_builder_v9_archetype_aware",
        )

    def _result(
        self,
        *,
        context: Dict[str, Any],
        language: str,
        personas: List[Dict[str, Any]],
        summary: str,
        buyer_user: str,
        validation: List[str],
        risks: List[str],
        format_name: str,
    ) -> Dict[str, Any]:
        normalized_personas, missing_fields = self._normalize_personas(
            personas=personas,
            context=context,
            language=language,
        )
        return {
            "format": format_name,
            "status": "completed",
            "output_language": language,
            "context_locked": True,
            "persona_summary": summary,
            "summary": summary,
            "primary_persona": normalized_personas[0],
            "personas": normalized_personas,
            "target_segments": [item.get("segment") for item in normalized_personas],
            "buyer_user_difference": buyer_user,
            "validation_questions": validation,
            "recommended_validation_method": validation,
            "persona_risks": self._unique(risks),
            "limitations": self._unique(risks),
            "persona_schema_version": "persona_v10_complete",
            "persona_schema_valid": not missing_fields,
            "missing_fields_by_persona": missing_fields,
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "project_context_used": context,
        }

    def _normalize_personas(
        self,
        *,
        personas: List[Dict[str, Any]],
        context: Dict[str, Any],
        language: str,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        actors = context.get("actors") or {}
        targets = self._list(context.get("target_users"))
        workflows = self._workflows(context, language)
        metrics = self._list(context.get("success_metrics"))
        risks = self._list(context.get("risk_dimensions"))
        archetype = self._text(context.get("project_archetype"))

        if archetype == "two_sided_marketplace":
            default_names = [
                self._text(actors.get("demand_side") or (targets[0] if targets else "")),
                self._text(actors.get("supply_side") or (targets[1] if len(targets) > 1 else "")),
                self._text(actors.get("operator_or_partner") or (targets[2] if len(targets) > 2 else "")),
            ]
        else:
            default_names = (targets + (["Primary user", "Economic buyer", "Operational partner"] if language == "en" else ["Utilisateur principal", "Acheteur économique", "Partenaire opérationnel"]))[:3]

        fallback_roles = (
            ["Primary user", "Economic buyer or provider", "Operational and trust owner"]
            if language == "en"
            else ["Utilisateur principal", "Acheteur ou prestataire", "Responsable opérations et confiance"]
        )
        fallback_alternatives = (
            ["Current offline process", "Direct contact", "Existing platform"]
            if language == "en"
            else ["Processus hors ligne actuel", "Contact direct", "Plateforme existante"]
        )
        fallback_questions = (
            ["How is this task completed today?", "What would make you stop using the product?"]
            if language == "en"
            else ["Comment cette tâche est-elle réalisée aujourd’hui ?", "Qu’est-ce qui ferait abandonner le produit ?"]
        )

        normalized: List[Dict[str, Any]] = []
        missing_by_persona: List[Dict[str, Any]] = []
        required_list_fields = (
            "goals",
            "frustrations",
            "current_alternatives",
            "adoption_obstacles",
            "success_metrics",
            "interview_questions",
        )
        required_text_fields = (
            "name",
            "persona_name",
            "role",
            "segment",
            "profile",
            "main_pain",
            "expected_value",
            "adoption_trigger",
            "buying_power",
            "decision_power",
            "use_case",
            "message_to_convince",
        )

        for index in range(3):
            original = dict(personas[index] if index < len(personas) and isinstance(personas[index], dict) else {})
            default_name = self._text(default_names[index] if index < len(default_names) else "") or fallback_roles[index]
            workflow = workflows[index] if index < len(workflows) else workflows[0]

            original["id"] = self._text(original.get("id")) or f"persona_{index + 1}"
            original["name"] = self._text(original.get("name") or original.get("persona_name") or original.get("segment")) or default_name
            original["persona_name"] = self._text(original.get("persona_name") or original.get("name")) or default_name
            original["role"] = self._text(original.get("role") or original.get("segment")) or fallback_roles[index]
            original["segment"] = self._text(original.get("segment") or original.get("name") or original.get("role")) or default_name
            original["profile"] = self._text(original.get("profile")) or (
                f"A role in {context['region']} involved in the project’s primary outcome."
                if language == "en"
                else f"Un rôle en {context['region']} impliqué dans le résultat principal du projet."
            )
            original["main_pain"] = self._text(original.get("main_pain")) or context["problem"]
            original["goals"] = self._list(original.get("goals")) or [workflow]
            original["frustrations"] = self._list(original.get("frustrations")) or risks[:2] or (["Uncertain outcome"] if language == "en" else ["Résultat incertain"])
            original["current_alternatives"] = self._list(original.get("current_alternatives")) or fallback_alternatives
            original["expected_value"] = self._text(original.get("expected_value")) or (
                "A measurable improvement over the current alternative."
                if language == "en"
                else "Une amélioration mesurable par rapport à l’alternative actuelle."
            )
            original["adoption_trigger"] = self._text(original.get("adoption_trigger")) or (
                "Adopts when the first complete outcome is faster, safer or more reliable."
                if language == "en"
                else "Adopte lorsque le premier résultat complet est plus rapide, sûr ou fiable."
            )
            original["adoption_obstacles"] = self._list(original.get("adoption_obstacles")) or risks[:3] or (["Insufficient value or trust"] if language == "en" else ["Valeur ou confiance insuffisante"])
            original["buying_power"] = self._text(original.get("buying_power")) or ("medium" if language == "en" else "moyen")
            original["decision_power"] = self._text(original.get("decision_power")) or ("medium" if language == "en" else "moyen")
            original["success_metrics"] = self._list(original.get("success_metrics")) or metrics[:4] or (["Successful outcome rate"] if language == "en" else ["Taux de résultat réussi"])
            original["use_case"] = self._text(original.get("use_case")) or workflow
            original["message_to_convince"] = self._text(original.get("message_to_convince")) or (
                "Prove the complete outcome with transparent limits and measurable results."
                if language == "en"
                else "Prouver le résultat complet avec des limites transparentes et des mesures concrètes."
            )
            original["interview_questions"] = self._list(original.get("interview_questions")) or fallback_questions

            missing = [field for field in required_text_fields if not self._text(original.get(field))]
            missing.extend(field for field in required_list_fields if not self._list(original.get(field)))
            if missing:
                missing_by_persona.append({"persona_id": original["id"], "missing_fields": missing})
            normalized.append(original)

        return normalized, missing_by_persona

    def _operational_user(
        self,
        *,
        name: str,
        segment: str,
        workflow: str,
        context: Dict[str, Any],
        alternatives: List[str],
        language: str,
    ) -> Dict[str, Any]:
        if language == "en":
            return {
                "id": "primary_user",
                "name": name,
                "persona_name": name,
                "role": "Primary daily user",
                "segment": segment,
                "profile": f"A hands-on professional in {context['region']} who performs the core workflow directly.",
                "main_pain": context["problem"],
                "goals": [f"Complete the workflow quickly and reliably: {workflow}.", "Retrieve accurate history before the next operational decision."],
                "frustrations": ["Missing or fragmented records during field work.", "Repeated manual entry and difficulty finding past information."],
                "current_alternatives": alternatives,
                "expected_value": f"Reduce the time and missing information involved in {workflow}.",
                "adoption_trigger": f"Adopts the product when {workflow} can be completed in under two minutes and reused later.",
                "adoption_obstacles": ["Too many fields during field work.", "Poor connectivity or a mobile interface that is difficult to use."],
                "buying_power": "low-to-medium",
                "decision_power": "medium",
                "success_metrics": ["Time to complete the workflow", "Weekly records completed", "Return rate in the following week"],
                "use_case": workflow,
                "message_to_convince": "Start with one field workflow, keep existing data safe and measure time saved.",
                "interview_questions": [f"Show me how you handle this workflow today: {workflow}.", "What would make you stop using the product after the first week?"],
            }
        return {
            "id": "primary_user",
            "name": name,
            "persona_name": name,
            "role": "Utilisateur quotidien principal",
            "segment": segment,
            "profile": f"Un professionnel de terrain en {context['region']} qui exécute directement le workflow principal.",
            "main_pain": context["problem"],
            "goals": [f"Réaliser {workflow} rapidement et sans erreur.", "Retrouver un historique fiable avant la prochaine décision opérationnelle."],
            "frustrations": ["Informations manquantes ou dispersées sur le terrain.", "Saisie manuelle répétée et difficulté à retrouver l’historique."],
            "current_alternatives": alternatives,
            "expected_value": f"Réduire le temps et les informations manquantes pendant {workflow}.",
            "adoption_trigger": f"Adopte le produit lorsque {workflow} prend moins de deux minutes et peut être réutilisé ensuite.",
            "adoption_obstacles": ["Trop de champs à remplir sur le terrain.", "Mauvaise connexion ou interface mobile difficile."],
            "buying_power": "faible à moyen",
            "decision_power": "moyen",
            "success_metrics": ["Temps pour réaliser le workflow", "Enregistrements terminés chaque semaine", "Retour la semaine suivante"],
            "use_case": workflow,
            "message_to_convince": "Commencer par un workflow terrain, protéger les données existantes et mesurer le temps gagné.",
            "interview_questions": [f"Montrez-moi comment vous réalisez aujourd’hui : {workflow}.", "Qu’est-ce qui vous ferait abandonner après la première semaine ?"],
        }

    def _economic_buyer(
        self,
        *,
        name: str,
        segment: str,
        workflow: str,
        context: Dict[str, Any],
        alternatives: List[str],
        language: str,
    ) -> Dict[str, Any]:
        if language == "en":
            return {
                "id": "economic_buyer",
                "name": name,
                "persona_name": name,
                "role": "Economic buyer and rollout sponsor",
                "segment": segment,
                "profile": f"A budget owner in {context['region']} responsible for adoption, reporting and support cost.",
                "main_pain": "Inconsistent records across users make supervision, reporting and quality control difficult.",
                "goals": [f"Use the product to review and consolidate this workflow: {workflow}.", "Approve a limited pilot with a measurable operational return."],
                "frustrations": ["Data arrives in incompatible formats.", "Support effort and subscription cost are hard to justify without measured gains."],
                "current_alternatives": alternatives[:2] + ["Manual consolidation by a coordinator"],
                "expected_value": "Reduce reporting time and improve completeness across the group.",
                "adoption_trigger": "Approves a pilot when scope, owner, price, success metric and exit condition are explicit.",
                "adoption_obstacles": ["Low adoption among daily users.", "Support and onboarding costs may exceed the subscription benefit."],
                "buying_power": "medium",
                "decision_power": "high",
                "success_metrics": ["Administrative hours saved per cycle", "Record completeness across users", "Pilot conversion at the tested price"],
                "use_case": workflow,
                "message_to_convince": "Run a reversible pilot with a named owner and a quantified reporting gain.",
                "interview_questions": ["Who owns the budget and approves the pilot?", "Which result would justify a recurring payment?"],
            }
        return {
            "id": "economic_buyer",
            "name": name,
            "persona_name": name,
            "role": "Acheteur économique et sponsor du déploiement",
            "segment": segment,
            "profile": f"Un détenteur du budget en {context['region']} responsable de l’adoption, du reporting et du coût de support.",
            "main_pain": "Des dossiers incohérents entre utilisateurs compliquent la supervision, le reporting et le contrôle qualité.",
            "goals": [f"Utiliser {workflow} pour consolider des informations fiables.", "Approuver un pilote limité avec un retour opérationnel mesurable."],
            "frustrations": ["Les données arrivent dans des formats incompatibles.", "Le support et l’abonnement sont difficiles à justifier sans gains mesurés."],
            "current_alternatives": alternatives[:2] + ["Consolidation manuelle par un coordinateur"],
            "expected_value": "Réduire le temps de reporting et améliorer la complétude des dossiers.",
            "adoption_trigger": "Approuve un pilote lorsque le périmètre, le responsable, le prix, la métrique et la condition d’arrêt sont explicites.",
            "adoption_obstacles": ["Faible adoption des utilisateurs quotidiens.", "Le support et l’onboarding peuvent coûter plus que le bénéfice de l’abonnement."],
            "buying_power": "moyen",
            "decision_power": "élevé",
            "success_metrics": ["Heures administratives gagnées par cycle", "Complétude des dossiers", "Conversion du pilote au prix testé"],
            "use_case": workflow,
            "message_to_convince": "Lancer un pilote réversible avec un responsable et un gain de reporting chiffré.",
            "interview_questions": ["Qui détient le budget et approuve le pilote ?", "Quel résultat justifierait un paiement récurrent ?"],
        }

    def _adoption_gatekeeper(
        self,
        *,
        name: str,
        segment: str,
        workflow: str,
        context: Dict[str, Any],
        alternatives: List[str],
        language: str,
    ) -> Dict[str, Any]:
        if language == "en":
            return {
                "id": "adoption_gatekeeper",
                "name": name,
                "persona_name": name,
                "role": "Cautious adopter and workflow gatekeeper",
                "segment": segment,
                "profile": f"A cautious professional in {context['region']} who protects the existing workflow from unnecessary change.",
                "main_pain": "A new system can create duplicate work, data loss or dependency on training and connectivity.",
                "goals": [f"Verify that the product supports {workflow} without data loss or duplicate work.", "Reach the first useful result without specialist assistance."],
                "frustrations": ["Tools that require re-entering old information.", "Complex onboarding and unclear recovery when synchronization fails."],
                "current_alternatives": alternatives[-2:] + ["Continue with the familiar process"],
                "expected_value": "A safe transition with fewer steps, preserved history and a reversible pilot.",
                "adoption_trigger": "Tests the product when setup takes minutes, one real record is imported and the first benefit is visible in one session.",
                "adoption_obstacles": ["Duplicate entry", "Fear of losing history", "Dependence on connectivity or technical support"],
                "buying_power": "low-to-medium",
                "decision_power": "medium",
                "success_metrics": ["Time to first successful action", "Assisted onboarding steps", "Records completed without duplicate entry"],
                "use_case": workflow,
                "message_to_convince": "Preserve the current records, test one task and keep a clear rollback path.",
                "interview_questions": ["Which data must never be lost during adoption?", "What would make this product feel like extra work?"],
            }
        return {
            "id": "adoption_gatekeeper",
            "name": name,
            "persona_name": name,
            "role": "Adoptant prudent et gardien du workflow",
            "segment": segment,
            "profile": f"Un professionnel prudent en {context['region']} qui protège le workflow actuel contre les changements inutiles.",
            "main_pain": "Un nouveau système peut créer une double saisie, une perte de données ou une dépendance à la formation et à la connexion.",
            "goals": [f"Vérifier que {workflow} préserve les données et réduit la double saisie.", "Obtenir le premier résultat utile sans assistance spécialisée."],
            "frustrations": ["Outils imposant de ressaisir les anciennes informations.", "Onboarding complexe et récupération peu claire après un échec de synchronisation."],
            "current_alternatives": alternatives[-2:] + ["Continuer avec le processus habituel"],
            "expected_value": "Une transition sûre, moins d’étapes, un historique préservé et un pilote réversible.",
            "adoption_trigger": "Teste le produit lorsque l’installation prend quelques minutes, qu’un vrai dossier est repris et que le premier bénéfice apparaît en une session.",
            "adoption_obstacles": ["Double saisie", "Peur de perdre l’historique", "Dépendance à la connexion ou au support"],
            "buying_power": "faible à moyen",
            "decision_power": "moyen",
            "success_metrics": ["Temps jusqu’à la première action réussie", "Étapes d’onboarding assistées", "Dossiers terminés sans double saisie"],
            "use_case": workflow,
            "message_to_convince": "Préserver les dossiers actuels, tester une tâche et garder un chemin de retour clair.",
            "interview_questions": ["Quelles données ne doivent jamais être perdues ?", "Qu’est-ce qui donnerait l’impression d’un travail supplémentaire ?"],
        }

    def _context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        analysis = state.get("analysis_data") or {}
        project_context = state.get("project_context") or {}
        intelligence = (
            state.get("project_intelligence")
            or analysis.get("project_intelligence")
            or project_context.get("project_intelligence")
            or {}
        )
        packet = (
            state.get("agent_context_packet")
            or analysis.get("agent_context_packet")
            or project_context.get("agent_context_packet")
            or intelligence.get("agent_context_packet")
            or {}
        )
        structured = (
            state.get("structured_project_context")
            or analysis.get("structured_project_context")
            or project_context.get("structured_project_context")
            or intelligence.get("structured_project_context")
            or packet.get("structured_project_context")
            or {}
        )
        archetype = (
            state.get("archetype_context")
            or analysis.get("archetype_context")
            or project_context.get("archetype_context")
            or intelligence.get("archetype_context")
            or packet.get("archetype_context")
            or {}
        )
        project = state.get("project") or {}
        description = self._text(
            structured.get("description")
            or packet.get("description")
            or project_context.get("description")
            or state.get("description")
            or project.get("description")
        )
        actors = structured.get("actors") or archetype.get("actors") or packet.get("actors") or {}
        if not isinstance(actors, dict):
            actors = {}
        targets = self._list(
            structured.get("target_users")
            or archetype.get("target_users")
            or packet.get("target_users")
            or project_context.get("target_users")
        )
        if not targets:
            targets = self._unique([
                self._text(actors.get("demand_side")),
                self._text(actors.get("supply_side")),
                self._text(actors.get("operator_or_partner")),
            ])
        language = normalize_output_language(state.get("output_language", "fr"))
        if not targets:
            targets = ["Primary user" if language == "en" else "Utilisateur principal"]
        workflows = self._list(
            structured.get("priority_workflows")
            or archetype.get("priority_workflows")
            or packet.get("priority_workflows")
            or structured.get("use_cases")
            or structured.get("use_case_terms")
        )
        constraints = self._clean_risk_dimensions(
            self._list(structured.get("constraints") or packet.get("constraints"))
        )
        risk_dimensions = self._clean_risk_dimensions(
            constraints
            + self._list(
                structured.get("risk_dimensions")
                or archetype.get("risk_dimensions")
                or packet.get("risk_dimensions")
            )
        )
        explicit_buyer = self._extract_explicit_actor(
            description=description,
            targets=targets,
            role="buyer",
        )
        explicit_maintainer = self._extract_explicit_actor(
            description=description,
            targets=targets,
            role="maintainer",
        )
        return {
            "title": self._text(structured.get("project_name") or packet.get("project_name") or state.get("title") or "Project"),
            "description": description,
            "sector": self._text(structured.get("sector") or archetype.get("vertical") or packet.get("sector") or state.get("industry") or "target sector"),
            "region": self._text(structured.get("target_region") or packet.get("target_region") or state.get("region") or "target region"),
            "target_users": targets,
            # Never use the second target as an automatic buyer.
            "economic_buyer": explicit_buyer,
            "explicit_economic_buyer": explicit_buyer,
            "explicit_maintainer": explicit_maintainer,
            "problem": self._text(structured.get("problem") or packet.get("problem") or analysis.get("problem") or "The current workflow requires validation."),
            "solution": self._text(structured.get("solution") or packet.get("solution") or analysis.get("proposed_solution") or "A focused workflow solution."),
            "mvp_scope": self._text(structured.get("mvp_scope") or archetype.get("validation_unit") or packet.get("mvp_scope") or "the first operational workflow"),
            "workflows": workflows,
            "project_archetype": self._text(structured.get("project_archetype") or archetype.get("project_archetype") or packet.get("project_archetype") or "generic_digital_product"),
            "business_motion": self._text(structured.get("business_motion") or archetype.get("business_motion") or packet.get("business_motion") or "unknown"),
            "interaction_model": self._text(structured.get("interaction_model") or archetype.get("interaction_model") or packet.get("interaction_model") or "generic"),
            "actors": actors,
            "business_model": self._text(structured.get("business_model") or archetype.get("business_model") or packet.get("business_model") or "pricing model to validate"),
            "success_metrics": self._list(structured.get("success_metrics") or archetype.get("success_metrics") or packet.get("success_metrics")),
            "constraints": constraints,
            "risk_dimensions": risk_dimensions,
            "evidence_needs": self._list(structured.get("evidence_needs") or archetype.get("evidence_needs") or packet.get("evidence_needs")),
        }

    def _extract_explicit_actor(
        self,
        *,
        description: str,
        targets: List[str],
        role: str,
    ) -> str:
        """Return a target actor only when the original text assigns the role."""
        normalized_description = self._normalize(description)
        if not normalized_description:
            return ""

        if role == "buyer":
            responsibility_markers = (
                "acheteur", "payeur", "detenteur du budget", "responsable des achats",
                "decideur d achat", "budget owner", "economic buyer", "payer",
                "approves the budget", "owns the budget",
            )
        else:
            responsibility_markers = (
                "assure la maintenance", "responsable de la maintenance",
                "maintient le robot", "maintient le dispositif", "mainteneur",
                "technical maintainer", "responsible for maintenance",
                "maintains the robot", "maintains the device",
            )

        if not any(marker in normalized_description for marker in responsibility_markers):
            return ""

        sentences = [
            item.strip()
            for item in re.split(r"[.!?\n]+", description)
            if item.strip()
        ]
        for target in targets:
            normalized_target = self._normalize(target)
            if not normalized_target:
                continue
            significant = [word for word in normalized_target.split() if len(word) >= 5]
            for sentence in sentences:
                normalized_sentence = self._normalize(sentence)
                if not any(marker in normalized_sentence for marker in responsibility_markers):
                    continue
                if normalized_target in normalized_sentence or (
                    significant and sum(word in normalized_sentence for word in significant) >= min(2, len(significant))
                ):
                    return target
        return ""

    def _clean_risk_dimensions(self, values: List[str]) -> List[str]:
        """Keep operational constraints and remove revenue-model fragments."""
        business_fragments = (
            "modele economique", "business model", "sources de revenus",
            "revenue streams", "location du robot", "robot rental",
            "abonnement mensuel", "monthly subscription", "vente du materiel",
            "hardware sale", "combine la location", "combines rental",
            "contrat de maintenance et support", "maintenance contract and support",
        )
        cleaned: List[str] = []
        for value in values:
            text = self._text(value).strip(" .;,-")
            normalized = self._normalize(text)
            if not text or len(text) < 3:
                continue
            if any(fragment in normalized for fragment in business_fragments):
                continue
            # Bare business-model tokens are not useful risk statements.
            bare_normalized = re.sub(
                r"^(?:la|le|les|un|une|the|an?)\s+",
                "",
                normalized,
            ).strip()
            if bare_normalized in {"maintenance", "abonnement", "subscription", "location", "rental"}:
                continue
            cleaned.append(text)
        return self._unique(cleaned)[:12]

    def _same_actor(self, first: str, second: str) -> bool:
        left = self._normalize(first)
        right = self._normalize(second)
        if not left or not right:
            return False
        if left == right or left in right or right in left:
            return True
        left_words = {word for word in left.split() if len(word) >= 5}
        right_words = {word for word in right.split() if len(word) >= 5}
        return bool(left_words and right_words and len(left_words & right_words) >= 2)

    def _segments(self, context: Dict[str, Any], language: str) -> List[str]:
        targets = [
            self._text(item) for item in context["target_users"]
            if self._is_role_like(self._text(item))
        ]
        primary = targets[0] if targets else ("Primary operational user" if language == "en" else "Utilisateur opérationnel principal")
        raw_buyer = context["economic_buyer"] or (targets[1] if len(targets) > 1 else "")
        buyer = raw_buyer if self._is_role_like(raw_buyer) else ("Economic buyer" if language == "en" else "Acheteur économique")
        sector_blob = self._normalize(context.get("sector", ""))
        workforce_sector = any(term in sector_blob for term in (
            "workforce", "employee scheduling", "shift planning", "shift scheduling", "human resources",
        ))
        gatekeeper = targets[2] if len(targets) > 2 else (
            ("Employees or team leads affected by schedule changes" if language == "en" else "Employés ou chefs d’équipe concernés par les changements de planning")
            if workforce_sector
            else (f"Cautious users in {context['sector']}" if language == "en" else f"Utilisateurs prudents dans {context['sector']}")
        )
        return [primary, buyer, gatekeeper]

    def _workflows(self, context: Dict[str, Any], language: str) -> List[str]:
        workflows = [self._text(item) for item in context.get("workflows") or [] if self._text(item)]
        defaults = (
            ["complete the primary operational record", "review and consolidate team records", "migrate one existing record without duplicate work"]
            if language == "en"
            else ["compléter le dossier opérationnel principal", "contrôler et consolider les dossiers de l’équipe", "reprendre un dossier existant sans double saisie"]
        )
        for item in defaults:
            if len(workflows) >= 3:
                break
            workflows.append(item)
        return self._unique(workflows)[:3]

    def _role_names(self, segments: List[str], context: Dict[str, Any], language: str) -> List[str]:
        joined = self._normalize(" ".join(segments + [context["sector"]]))
        if any(term in joined for term in ("beekeeper", "beekeeping", "apiculteur", "apiculture", "honey", "miel")):
            return (
                ["Independent beekeeper", "Honey cooperative manager", "Traceability-focused honey producer"]
                if language == "en"
                else ["Apiculteur indépendant", "Responsable de coopérative apicole", "Producteur de miel axé traçabilité"]
            )
        if any(term in joined for term in ("workforce scheduling", "employee scheduling", "shift planning", "shift scheduling", "attendance", "leave requests", "gestion des horaires", "planning des equipes", "planning des équipes")):
            return (
                ["Shift supervisor or HR assistant", "SME owner or HR manager", "Employee or team lead"]
                if language == "en"
                else ["Superviseur de planning ou assistant RH", "Dirigeant de PME ou responsable RH", "Employé ou chef d’équipe"]
            )
        return [
            self._singular_role(segments[0], language),
            self._singular_role(segments[1], language),
            self._singular_role(segments[2], language),
        ]

    def _alternatives(self, problem: str, language: str) -> List[str]:
        normalized = self._normalize(problem)
        mapping = {
            "notebook": ("Paper notebooks", "Cahiers papier"),
            "paper": ("Paper forms", "Formulaires papier"),
            "whatsapp": ("WhatsApp messages", "Messages WhatsApp"),
            "excel": ("Disconnected Excel files", "Fichiers Excel dispersés"),
            "spreadsheet": ("Generic spreadsheets", "Tableurs génériques"),
            "memory": ("Memory and verbal follow-up", "Mémoire et suivi verbal"),
        }
        items: List[str] = []
        for key, values in mapping.items():
            if key in normalized:
                items.append(values[0] if language == "en" else values[1])
        defaults = ["Manual workflow", "Generic messaging tools", "Informal coordination"] if language == "en" else ["Workflow manuel", "Outils de messagerie génériques", "Coordination informelle"]
        for item in defaults:
            if len(items) >= 4:
                break
            if item not in items:
                items.append(item)
        return items[:4]

    def _is_role_like(self, value: str) -> bool:
        normalized = self._normalize(value)
        if not normalized or len(normalized.split()) > 14:
            return False
        if any(marker in normalized for marker in (
            "still prepare", "prepare weekly", "the first version", "focus only",
            "before developing", "excel sheets", "whatsapp groups",
        )):
            return False
        return any(marker in normalized for marker in (
            "user", "customer", "client", "manager", "owner", "assistant", "supervisor",
            "employee", "worker", "company", "business", "cooperative", "producer",
            "beekeeper", "farmer", "responsable", "directeur", "proprietaire", "employe",
            "entreprise", "restaurant", "factory", "workshop", "retail",
        ))

    def _singular_role(self, value: str, language: str) -> str:
        text = self._text(value).strip(" .")
        if not text:
            return "Target user" if language == "en" else "Utilisateur cible"
        words = text.split()
        if words and words[-1].lower().endswith("s") and len(words[-1]) > 3:
            words[-1] = words[-1][:-1]
        return " ".join(words).title()

    @staticmethod
    def _list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, (tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            # Do not split on every “and/et”: doing so turns complete constraints
            # and business-model sentences into unrelated persona limitations.
            return [
                item.strip()
                for item in re.split(r"[,;\n]+", value)
                if item.strip()
            ]
        return []

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @staticmethod
    def _normalize(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(char for char in text if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", text.lower()).strip()

    @staticmethod
    def _unique(values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            clean = re.sub(r"\s+", " ", str(value or "")).strip()
            if not clean or clean.casefold() in seen:
                continue
            seen.add(clean.casefold())
            result.append(clean)
        return result

    def _fallback(self, language: str, error: str) -> Dict[str, Any]:
        name = "Target workflow user" if language == "en" else "Utilisateur du workflow cible"
        persona = {
            "id": "fallback_primary_user",
            "name": name,
            "role": "Primary user" if language == "en" else "Utilisateur principal",
            "segment": "First target segment" if language == "en" else "Premier segment cible",
            "profile": "Role to validate through interviews." if language == "en" else "Rôle à valider par des entretiens.",
            "main_pain": "Workflow pain requires direct validation." if language == "en" else "La douleur du workflow exige une validation directe.",
            "current_alternatives": ["Manual workflow" if language == "en" else "Workflow manuel"],
            "expected_value": "Measurable workflow improvement." if language == "en" else "Amélioration mesurable du workflow.",
            "adoption_trigger": "Adopts when one task becomes faster and measurable." if language == "en" else "Adopte lorsqu’une tâche devient plus rapide et mesurable.",
            "adoption_obstacles": ["Value is not yet proven." if language == "en" else "La valeur n’est pas encore prouvée."],
            "buying_power": "unknown" if language == "en" else "inconnu",
            "decision_power": "unknown" if language == "en" else "inconnu",
            "success_metrics": ["Weekly reuse" if language == "en" else "Réutilisation hebdomadaire"],
            "interview_questions": ["How is the workflow completed today?" if language == "en" else "Comment le workflow est-il réalisé aujourd’hui ?"],
        }
        return {
            "format": "persona_builder_v7_fallback",
            "status": "fallback_completed",
            "output_language": language,
            "context_locked": True,
            "persona_summary": "Personas require manual validation." if language == "en" else "Les personas exigent une validation manuelle.",
            "primary_persona": persona,
            "personas": [persona],
            "target_segments": [persona["segment"]],
            "buyer_user_difference": "Not yet confirmed." if language == "en" else "Pas encore confirmé.",
            "validation_questions": persona["interview_questions"],
            "recommended_validation_method": persona["interview_questions"],
            "persona_risks": ["Insufficient context." if language == "en" else "Contexte insuffisant."],
            "manual_review_required": True,
            "fallback_used": True,
            "error_handled": True,
            "internal_error": error[:300],
        }