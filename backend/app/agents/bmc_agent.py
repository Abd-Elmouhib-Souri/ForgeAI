from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from app.services.domain_integrity_guard import normalize_output_language


class BMCAgent:
    """Deterministic Business Model Canvas based on the canonical context."""

    FORMAT = "bmc_v6_archetype_aware"

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        try:
            context = self._context(state)
            if context["project_archetype"] == "two_sided_marketplace":
                result = self._marketplace_canvas(context, language)
            elif context["project_archetype"] == "hardware_iot":
                result = self._hardware_canvas(context, language)
            else:
                result = self._digital_canvas(context, language)
            return self._finalize(result, context, language)
        except Exception:
            return self._fallback(language)

    # ------------------------------------------------------------------
    # Canvas builders
    # ------------------------------------------------------------------

    def _hardware_canvas(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        users = context["target_user_list"]
        actors = context["actors"]
        assignments = context["role_assignments"]
        primary = (
            self._actor_text(actors.get("field_operator"))
            or self._actor_text(actors.get("primary_user"))
            or self._first(users)
        )
        payer = assignments["payer"]["value"] or (
            "Not identified — validate with the budget owner"
            if language == "en"
            else "Non identifié — à valider avec le détenteur du budget"
        )
        maintainer = assignments["technical_maintainer"]["value"] or (
            "Not identified — validate during the pilot"
            if language == "en"
            else "Non identifié — à valider pendant le pilote"
        )

        workflow = self._core_action(context, language)
        workflows = self._specific_workflows(context, language)
        metrics = context["success_metrics"]
        constraints = context["constraints"] or context["risk_dimensions"]
        sector = context["sector"]
        region = context["region"]
        model = context["business_model"]

        if language == "en":
            segments = self._unique([
                *[f"Operational user: {item}." for item in users[:4]],
                f"Economic buyer: {payer}.",
                f"Maintenance or deployment role: {maintainer}.",
            ])
            values = self._unique([
                f"Automate or improve the field workflow: {workflow}.",
                f"Detect and report operational anomalies earlier than the current process: {context['problem']}.",
                "Provide a measurable, repeatable inspection result with alerts and traceability.",
                "Reduce manual inspection effort only when the pilot proves accuracy, availability and acceptable maintenance.",
            ])
            channels = [
                "On-site demonstrations in representative operating conditions",
                "Paid pilots with a small number of launch customers",
                f"Direct B2B sales to organizations in {sector or 'the target sector'}",
                "Industry associations, cooperatives and technical integrators",
                "Referrals based on measured pilot outcomes",
            ]
            relationships = [
                "Guided installation and operator training",
                "Preventive and corrective maintenance contract",
                "Performance dashboard and periodic pilot review",
                "Technical support with incident, recovery and replacement procedures",
            ]
            revenues = self._unique([
                model,
                "Robot lease or paid deployment",
                "Hardware sale with installation",
                "Maintenance and support contract",
                "Recurring dashboard, alerts or analytics subscription",
            ])
            resources = [
                "Validated mechanical and electronic design",
                "Firmware, navigation, AI models and dashboard software",
                "Domain-specific training and validation dataset",
                "Field test results and acceptance criteria",
                "Bill of materials, suppliers and maintenance documentation",
            ]
            activities = self._unique([
                *workflows,
                "Prototype integration and field validation",
                "Reliability, safety, recovery and environmental testing",
                "Dataset collection, annotation and model evaluation",
                "Manufacturing, installation and deployment quality control",
                "Maintenance, incident analysis and product iteration",
            ])
            partners = self._hardware_partners(context, language)
            costs = [
                "Components, chassis, power system and assembly",
                "Camera, sensors, edge computing and connectivity",
                "Firmware, AI, dashboard and data infrastructure",
                "Testing, installation, training and pilot operations",
                "Maintenance, spare parts, warranty reserve and support",
                "Certification or safety work when required",
            ]
            summary = (
                f"{context['title']} is a hardware/IoT business. Its model becomes credible only when one deployment reliably performs "
                f"'{workflow}', creates measurable value for {primary or 'the field operator'} and remains maintainable at a viable total cost."
            )
            note = f"The current revenue hypothesis is {model}. Compare sale, lease and service-bundle offers with the real budget owner."
            priorities = self._unique([
                "Confirm the economic buyer and purchasing process",
                "Measure the current manual baseline and the value created by the robot",
                "Validate deployed unit cost and maintenance burden",
                *metrics,
                *constraints,
            ])
            risk_note = "The main risk is a functional prototype whose reliability, maintenance burden or deployed cost prevents repeated adoption."
        else:
            segments = self._unique([
                *[f"Utilisateur opérationnel : {item}." for item in users[:4]],
                f"Acheteur économique : {payer}.",
                f"Maintenance ou déploiement : {maintainer}.",
            ])
            values = self._unique([
                f"Automatiser ou améliorer le workflow terrain : {workflow}.",
                f"Détecter et signaler les anomalies plus tôt que le processus actuel : {context['problem']}.",
                "Fournir un résultat d’inspection mesurable et répétable avec alertes et traçabilité.",
                "Réduire l’effort d’inspection manuelle seulement si le pilote prouve précision, disponibilité et maintenance acceptable.",
            ])
            channels = [
                "Démonstrations sur site dans des conditions représentatives",
                "Pilotes payants avec un nombre limité de clients de lancement",
                f"Vente B2B directe aux organisations du secteur {sector or 'ciblé'}",
                "Associations professionnelles, coopératives et intégrateurs techniques",
                "Recommandations fondées sur les résultats mesurés du pilote",
            ]
            relationships = [
                "Installation accompagnée et formation des opérateurs",
                "Contrat de maintenance préventive et corrective",
                "Tableau de bord de performance et revues périodiques du pilote",
                "Support technique avec procédures d’incident, reprise et remplacement",
            ]
            revenues = self._unique([
                model,
                "Location du robot ou déploiement pilote payant",
                "Vente du matériel avec installation",
                "Contrat de maintenance et support",
                "Abonnement au tableau de bord, aux alertes ou aux analyses",
            ])
            resources = [
                "Conception mécanique et électronique validée",
                "Firmware, navigation, modèles IA et logiciel du tableau de bord",
                "Jeu de données métier pour entraînement et validation",
                "Résultats d’essais terrain et critères d’acceptation",
                "Nomenclature, fournisseurs et documentation de maintenance",
            ]
            activities = self._unique([
                *workflows,
                "Intégration du prototype et validation terrain",
                "Tests de fiabilité, sécurité, reprise et environnement",
                "Collecte, annotation et évaluation des données",
                "Fabrication, installation et contrôle qualité du déploiement",
                "Maintenance, analyse des incidents et itérations produit",
            ])
            partners = self._hardware_partners(context, language)
            costs = [
                "Composants, châssis, alimentation et assemblage",
                "Caméra, capteurs, calcul embarqué et connectivité",
                "Firmware, IA, tableau de bord et infrastructure de données",
                "Essais, installation, formation et opérations du pilote",
                "Maintenance, pièces de rechange, réserve de garantie et support",
                "Certification ou sécurité lorsque nécessaire",
            ]
            summary = (
                f"{context['title']} est un modèle matériel/IoT. Il devient crédible lorsqu’un déploiement réalise de façon fiable "
                f"« {workflow} », crée une valeur mesurable pour {primary or 'l’opérateur terrain'} et reste maintenable à un coût total viable."
            )
            note = f"L’hypothèse de revenus actuelle est : {model}. Comparer vente, location et offre groupée avec le véritable détenteur du budget."
            priorities = self._unique([
                "Confirmer l’acheteur économique et le processus d’achat",
                "Mesurer la situation manuelle actuelle et la valeur créée par le robot",
                "Valider le coût unitaire déployé et la charge de maintenance",
                *metrics,
                *constraints,
            ])
            risk_note = "Le risque principal est un prototype fonctionnel dont la fiabilité, la maintenance ou le coût déployé bloque l’adoption répétée."

        return self._result(
            segments=segments,
            values=values,
            channels=channels,
            relationships=relationships,
            revenues=revenues,
            resources=resources,
            activities=activities,
            partners=partners,
            costs=costs,
            summary=summary,
            note=note,
            priorities=priorities,
            risk_note=risk_note,
            risk_level="high",
        )

    def _marketplace_canvas(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        actors = context["actors"]
        users = context["target_user_list"]
        assignments = context["role_assignments"]
        demand = (
            assignments["demand_side"]["value"]
            or self._actor_text(actors.get("primary_user"))
            or self._first(users)
        )
        supply = assignments["supply_side"]["value"]
        operator = assignments["operator_or_partner"]["value"]
        payer = assignments["payer"]["value"]
        core = self._core_action(context, language)
        model = context["business_model"]
        region = context["region"]

        if language == "en":
            segments = [f"Demand side: {demand}.", f"Supply side: {supply or 'not identified — to validate'}.", f"Platform or ecosystem operator: {operator or 'not identified — to validate'}.", f"Paying participant: {payer or 'not identified — to validate'}."]
            values = [f"For {demand}: complete {core} with reliable availability and confirmation.", f"For {supply or 'the supply side to validate'}: receive relevant demand with transparent economics.", "For the operator: improve liquidity, quality, trust and incident handling.", f"Solve the launch-market problem: {context['problem']}."]
            channels = ["Bounded launch around one transaction type and one priority segment", "Direct supply recruitment and onboarding", "Local digital acquisition and partnerships", "Referral after completed transactions"]
            relationships = ["Real-time status and support", "Identity, trust, rating and dispute mechanisms", "Supply onboarding and operational communication"]
            revenues = self._unique([model, "Commission or service fee per completed transaction", "Professional provider plan after liquidity is proven"])
            resources = ["Matching and transaction infrastructure", "Active demand and supply under compatible transaction conditions", "Trust, safety, support and compliance processes", "Liquidity and contribution analytics"]
            activities = ["Recruit and activate both sides", "Operate matching, cancellations and incidents", "Measure completion, repeat use and unit economics", "Validate local regulation and partner responsibilities"]
            partners = [f"Local supply and ecosystem partners in {region or 'the launch market'}", "Payment, identity, mapping and communication providers", "Regulatory or professional stakeholders when required"]
            costs = ["Product and matching infrastructure", "Supply acquisition and incentives", "Support, trust and safety", "Payment, mapping, messaging and compliance"]
            summary = f"{context['title']} is a two-sided marketplace. It must prove simultaneous demand, supply, trust and positive economics around {core}."
            note = f"The revenue hypothesis is {model}; measure it after incentives, support, payment and compliance costs."
            priorities = context["evidence_needs"] or ["Demand frequency", "Supply availability", "Transaction completion", "Repeat use", "Contribution margin"]
            risk_note = "The main risk is liquidity failure: demand and supply may not be active under compatible transaction conditions."
        else:
            segments = [f"Côté demande : {demand}.", f"Côté offre : {supply or 'non identifié — à valider'}.", f"Opérateur de plateforme ou écosystème : {operator or 'non identifié — à valider'}.", f"Participant payeur : {payer or 'non identifié — à valider'}."]
            values = [f"Pour {demand} : réaliser {core} avec disponibilité et confirmation fiables.", f"Pour {supply or 'le côté offre à valider'} : recevoir une demande pertinente avec une économie transparente.", "Pour l’opérateur : améliorer liquidité, qualité, confiance et gestion des incidents.", f"Résoudre le problème du marché de lancement : {context['problem']}."]
            channels = ["Lancement limité autour d’un type de transaction et d’un segment prioritaire", "Recrutement et onboarding directs du côté offre", "Acquisition numérique locale et partenariats", "Recommandation après les transactions réussies"]
            relationships = ["Suivi et support en temps réel", "Identité, confiance, notation et gestion des litiges", "Onboarding et communication opérationnelle du côté offre"]
            revenues = self._unique([model, "Commission ou frais de service par transaction terminée", "Offre professionnelle après preuve de liquidité"])
            resources = ["Infrastructure de mise en relation et transaction", "Demande et offre actives dans des conditions transactionnelles compatibles", "Processus de confiance, sécurité, support et conformité", "Analytics de liquidité et contribution"]
            activities = ["Recruter et activer les deux côtés", "Opérer mise en relation, annulations et incidents", "Mesurer réalisation, répétition et économie unitaire", "Valider la réglementation locale et les responsabilités"]
            partners = [f"Partenaires locaux côté offre et écosystème en {region or 'marché de lancement'}", "Prestataires de paiement, identité, cartographie et communication", "Acteurs réglementaires ou professionnels si nécessaire"]
            costs = ["Produit et infrastructure de mise en relation", "Acquisition et incitations côté offre", "Support, confiance et sécurité", "Paiement, cartographie, messagerie et conformité"]
            summary = f"{context['title']} est une marketplace à deux côtés. Elle doit prouver simultanément demande, offre, confiance et économie positive autour de {core}."
            note = f"L’hypothèse de revenus est {model}; la mesurer après incitations, support, paiement et conformité."
            priorities = context["evidence_needs"] or ["Fréquence de la demande", "Disponibilité de l’offre", "Réalisation de la transaction", "Usage répété", "Marge contributive"]
            risk_note = "Le risque principal est l’échec de liquidité : demande et offre peuvent ne pas être actives dans des conditions transactionnelles compatibles."

        return self._result(segments=segments, values=values, channels=channels, relationships=relationships, revenues=revenues, resources=resources, activities=activities, partners=partners, costs=costs, summary=summary, note=note, priorities=priorities, risk_note=risk_note, risk_level="high")

    def _digital_canvas(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        users = context["target_user_list"]
        primary = self._first(users) or ("Primary user" if language == "en" else "Utilisateur principal")
        assignments = context["role_assignments"]
        payer = assignments["payer"]["value"] or (
            "Not identified — to validate"
            if language == "en"
            else "Non identifié — à valider"
        )
        core = self._core_action(context, language)
        model = context["business_model"]
        region = context["region"]
        regulated = context["project_archetype"] == "regulated_service"

        if language == "en":
            segments = self._unique([*[f"Target user: {item}." for item in users[:5]], f"Paying customer: {payer}."])
            values = [f"Help {primary} complete {core} with less friction.", f"Solve the stated problem: {context['problem']}.", f"Deliver the proposed mechanism: {context['solution']}.", "Make the result measurable through activation, successful completion and repeat use."]
            channels = ["Direct outreach to the narrow launch segment", "Targeted digital acquisition", "Pilot partnerships", "Referral after successful use"]
            relationships = ["Clear onboarding", "In-product guidance and support", "Status, recovery and feedback loops", "Privacy and trust controls" if regulated else "Usage feedback and continuous improvement"]
            revenues = self._unique([model, "Paid pilot or setup fee", "Subscription or usage fee after repeat value is proven"])
            resources = ["Reliable core product", "User and workflow analytics", "Operational support and documentation", "Validated domain data and integrations where required"]
            activities = ["Validate the core action", "Improve activation, conversion and retention", "Operate support and recovery", "Test pricing and willingness to pay"]
            partners = [f"Relevant launch and distribution partners in {region or 'the target market'}", "Payment, identity, infrastructure or domain providers as required"]
            costs = ["Product development", "Cloud and third-party services", "Acquisition and onboarding", "Operations, support and compliance"]
            summary = f"{context['title']} must prove that users complete and repeat {core}, and that the payer accepts {model}."
            note = "The model remains a hypothesis until conversion, retention and delivery cost are measured."
            priorities = context["evidence_needs"] or ["Successful core action", "Repeat use", "Paid conversion", "Delivery cost", "Retention"]
            risk_note = "The main risk is weak repeat value or acquisition and delivery costs above revenue."
        else:
            segments = self._unique([*[f"Utilisateur cible : {item}." for item in users[:5]], f"Client payeur : {payer}."])
            values = [f"Aider {primary} à réaliser {core} avec moins de friction.", f"Résoudre le problème déclaré : {context['problem']}.", f"Livrer le mécanisme proposé : {context['solution']}.", "Rendre le résultat mesurable par activation, réalisation réussie et usage répété."]
            channels = ["Prospection directe du segment de lancement", "Acquisition numérique ciblée", "Partenariats pilotes", "Recommandation après un usage réussi"]
            relationships = ["Onboarding clair", "Guidage dans le produit et support", "Statut, reprise et boucles de feedback", "Contrôles de confidentialité et confiance" if regulated else "Feedback d’usage et amélioration continue"]
            revenues = self._unique([model, "Pilote payant ou frais de configuration", "Abonnement ou frais d’usage après preuve de valeur répétée"])
            resources = ["Produit principal fiable", "Analytics utilisateurs et workflow", "Support opérationnel et documentation", "Données métier et intégrations validées si nécessaires"]
            activities = ["Valider l’action principale", "Améliorer activation, conversion et rétention", "Opérer support et reprise", "Tester le prix et la volonté de payer"]
            partners = [f"Partenaires de lancement et distribution en {region or 'marché cible'}", "Prestataires de paiement, identité, infrastructure ou métier selon le besoin"]
            costs = ["Développement produit", "Cloud et services tiers", "Acquisition et onboarding", "Opérations, support et conformité"]
            summary = f"{context['title']} doit prouver que les utilisateurs réalisent et répètent {core}, et que le payeur accepte {model}."
            note = "Le modèle reste une hypothèse tant que conversion, rétention et coût de réalisation ne sont pas mesurés."
            priorities = context["evidence_needs"] or ["Action principale réussie", "Usage répété", "Conversion payante", "Coût de réalisation", "Rétention"]
            risk_note = "Le risque principal est une faible valeur répétée ou des coûts d’acquisition et de réalisation supérieurs aux revenus."

        return self._result(segments=segments, values=values, channels=channels, relationships=relationships, revenues=revenues, resources=resources, activities=activities, partners=partners, costs=costs, summary=summary, note=note, priorities=priorities, risk_note=risk_note, risk_level="high" if regulated else "medium")

    # ------------------------------------------------------------------
    # Contract and context
    # ------------------------------------------------------------------

    def _result(self, *, segments: List[str], values: List[str], channels: List[str], relationships: List[str], revenues: List[str], resources: List[str], activities: List[str], partners: List[str], costs: List[str], summary: str, note: str, priorities: List[str], risk_note: str, risk_level: str) -> Dict[str, Any]:
        segments = self._unique(segments); values = self._unique(values); channels = self._unique(channels)
        relationships = self._unique(relationships); revenues = self._unique(revenues); resources = self._unique(resources)
        activities = self._unique(activities); partners = self._unique(partners); costs = self._unique(costs)
        return {
            "format": self.FORMAT,
            "status": "completed",
            "summary": summary,
            "customer_segments": segments,
            "value_propositions": values,
            "channels": channels,
            "customer_relationships": relationships,
            "revenue_streams": revenues,
            "key_resources": resources,
            "key_activities": activities,
            "key_partnerships": partners,
            "cost_structure": costs,
            "value_proposition": values,
            "key_partners": partners,
            "costs": costs,
            "customers": segments,
            "relationships": relationships,
            "revenues": revenues,
            "business_model_note": note,
            "validation_priorities": self._unique(priorities),
            "risk_note": risk_note,
            "canvas": {
                "customer_segments": segments,
                "value_propositions": values,
                "channels": channels,
                "customer_relationships": relationships,
                "revenue_streams": revenues,
                "key_resources": resources,
                "key_activities": activities,
                "key_partnerships": partners,
                "cost_structure": costs,
            },
            "risk_level": risk_level,
            "confidence_level": "medium",
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "context_locked": True,
        }

    def _finalize(self, result: Dict[str, Any], context: Dict[str, Any], language: str) -> Dict[str, Any]:
        result["output_language"] = language
        result["actor_role_provenance"] = context["role_assignments"]
        result["project_context_used"] = {
            "title": context["title"], "sector": context["sector"], "region": context["region"],
            "target_users": context["target_user_list"], "problem": context["problem"], "solution": context["solution"],
            "business_model": context["business_model"], "mvp_scope": context["mvp_scope"],
            "project_archetype": context["project_archetype"], "priority_workflows": context["priority_workflows"],
            "success_metrics": context["success_metrics"], "constraints": context["constraints"],
        }
        return self._clean_object(result)

    def _context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        analysis = state.get("analysis_data") or {}; project_context = state.get("project_context") or {}
        intelligence = state.get("project_intelligence") or analysis.get("project_intelligence") or project_context.get("project_intelligence") or {}
        structured = state.get("structured_project_context") or analysis.get("structured_project_context") or project_context.get("structured_project_context") or intelligence.get("structured_project_context") or {}
        canonical = self._canonical_packet(state, analysis, project_context)
        users = self._list(structured.get("target_users") or canonical.get("actors") or project_context.get("target_users"))
        actors = structured.get("actors") or project_context.get("actors") or {}
        if not isinstance(actors, dict): actors = {}
        actors = dict(actors)
        actors.setdefault("target_users", users)
        actor_provenance = (
            structured.get("actor_provenance")
            or canonical.get("actor_provenance")
            or actors.get("provenance")
            or {}
        )
        if not isinstance(actor_provenance, dict):
            actor_provenance = {}
        role_assignments = self._role_assignments(
            structured=structured,
            canonical=canonical,
            actors=actors,
            provenance=actor_provenance,
        )
        return {
            "title": self._text(structured.get("project_name") or structured.get("title") or canonical.get("project_name") or project_context.get("title") or state.get("title"), "Project"),
            "sector": self._text(structured.get("sector") or structured.get("industry") or canonical.get("domain_label") or project_context.get("industry") or state.get("industry")),
            "region": self._text(structured.get("target_region") or structured.get("market_region") or canonical.get("target_region") or project_context.get("market_region") or state.get("region")),
            "target_user_list": users,
            "target_users": ", ".join(users),
            "economic_buyer": self._text(structured.get("economic_buyer") or canonical.get("payer") or actors.get("payer")),
            "problem": self._packet_text(structured.get("problem") or structured.get("core_problem") or canonical.get("problem") or project_context.get("problem"), "the identified problem"),
            "solution": self._packet_text(structured.get("solution") or canonical.get("solution") or project_context.get("solution"), "the proposed solution"),
            "business_model": self._text(structured.get("business_model") or self._first(self._list(canonical.get("business_model_hypotheses"))) or project_context.get("business_model"), "Business model to validate"),
            "mvp_scope": ", ".join(self._list(structured.get("mvp_scope") or canonical.get("mvp_scope") or project_context.get("mvp_scope"))),
            "project_archetype": self._text(structured.get("project_archetype") or canonical.get("project_archetype") or project_context.get("project_archetype"), "generic_digital_product"),
            "validation_unit": self._packet_text(structured.get("validation_unit") or canonical.get("validation_unit")),
            "actors": actors,
            "actor_provenance": actor_provenance,
            "role_assignments": role_assignments,
            "priority_workflows": self._list(structured.get("priority_workflows") or structured.get("priority_workflow") or canonical.get("priority_workflow")),
            "success_metrics": self._list(structured.get("success_metrics") or canonical.get("success_metrics")),
            "constraints": self._list(structured.get("constraints") or canonical.get("constraints")),
            "risk_dimensions": self._list(structured.get("risk_dimensions") or project_context.get("risk_dimensions")),
            "evidence_needs": self._list(structured.get("evidence_needs") or project_context.get("evidence_needs")),
        }

    def _canonical_packet(self, state: Dict[str, Any], analysis: Dict[str, Any], project_context: Dict[str, Any]) -> Dict[str, Any]:
        readiness = analysis.get("idea_readiness") or {}
        for value in (state.get("project_context_packet"), state.get("canonical_context"), analysis.get("project_context_packet"), analysis.get("canonical_context"), analysis.get("context_packet"), readiness.get("context_packet"), readiness.get("project_context_packet"), project_context.get("canonical_context")):
            if isinstance(value, dict): return value
        return {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    CONFIRMED_ROLE_STATUSES = {
        "explicit",
        "user_provided",
        "confirmed",
        "validated",
        "provided_by_user",
    }

    def _role_assignments(
        self,
        *,
        structured: Dict[str, Any],
        canonical: Dict[str, Any],
        actors: Dict[str, Any],
        provenance: Dict[str, Any],
    ) -> Dict[str, Dict[str, str]]:
        aliases = {
            "payer": ("payer", "economic_buyer", "budget_owner"),
            "technical_maintainer": (
                "technical_maintainer",
                "maintenance_owner",
                "maintainer",
            ),
            "demand_side": ("demand_side",),
            "supply_side": ("supply_side",),
            "operator_or_partner": ("operator_or_partner", "platform_operator"),
        }
        assignments: Dict[str, Dict[str, str]] = {}

        for role, keys in aliases.items():
            raw: Any = None
            status = ""

            for key in keys:
                if key in actors and actors.get(key) not in (None, ""):
                    raw = actors.get(key)
                    break
                if key in structured and structured.get(key) not in (None, ""):
                    raw = structured.get(key)
                    break
                if key in canonical and canonical.get(key) not in (None, ""):
                    raw = canonical.get(key)
                    break

            if isinstance(raw, dict):
                status = self._text(
                    raw.get("status")
                    or raw.get("provenance")
                    or raw.get("source")
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

            for key in keys:
                status = status or self._text(
                    structured.get(f"{key}_status")
                    or actors.get(f"{key}_status")
                    or canonical.get(f"{key}_status")
                ).lower()

            confirmed = status in self.CONFIRMED_ROLE_STATUSES
            assignments[role] = {
                "value": candidate if confirmed else "",
                "candidate": candidate,
                "status": "explicit" if confirmed else "to_confirm",
            }

        return assignments

    def _actor_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return self._text(
                value.get("value")
                or value.get("name")
                or value.get("actor")
                or value.get("label")
            )
        return self._text(value)

    def _hardware_partners(self, context: Dict[str, Any], language: str) -> List[str]:
        sector = context["sector"].lower()
        region = context["region"]
        if language == "en":
            values = ["Component, battery and enclosure suppliers", "Pilot sites and operational users", "Manufacturing, integration or maintenance partners", "Connectivity or cloud providers when required"]
            if any(term in sector for term in ("agri", "farm", "agriculture")): values.extend(["Agricultural cooperatives, greenhouse operators and nurseries", "Agronomists or crop-protection specialists for validation"])
            if region: values.append(f"Local technical and distribution partners in {region}")
        else:
            values = ["Fournisseurs de composants, batteries et boîtiers", "Sites pilotes et utilisateurs opérationnels", "Partenaires de fabrication, intégration ou maintenance", "Fournisseurs de connectivité ou cloud si nécessaires"]
            if any(term in sector for term in ("agri", "agriculture")): values.extend(["Coopératives agricoles, exploitants de serres et pépinières", "Agronomes ou spécialistes phytosanitaires pour la validation"])
            if region: values.append(f"Partenaires techniques et distributeurs locaux en {region}")
        return self._unique(values)

    def _core_action(self, context: Dict[str, Any], language: str) -> str:
        generic = {"core action", "core workflow", "réaliser l’opération terrain principale", "main field operation"}
        for value in context["priority_workflows"]:
            if value and value.lower() not in generic: return value
        if context["validation_unit"]: return context["validation_unit"]
        if context["mvp_scope"]: return context["mvp_scope"]
        return "réaliser l’action principale" if language != "en" else "complete the core action"

    def _specific_workflows(self, context: Dict[str, Any], language: str) -> List[str]:
        values = [item for item in context["priority_workflows"] if item and "opération terrain principale" not in item.lower() and "core action" not in item.lower()]
        return values or [self._core_action(context, language)]

    def _packet_text(self, value: Any, fallback: str = "") -> str:
        if isinstance(value, dict):
            for key in ("pain", "mechanism", "core_value", "action", "result", "output", "value"):
                if value.get(key): return self._text(value[key], fallback)
            return fallback
        return self._text(value, fallback)

    def _clean_object(self, value: Any) -> Any:
        if isinstance(value, dict): return {str(k): self._clean_object(v) for k, v in value.items() if v not in (None, "", [], {})}
        if isinstance(value, list): return [self._clean_object(v) for v in value if v not in (None, "", [], {})]
        if isinstance(value, str): return re.sub(r"\s+", " ", value).strip()
        return value

    def _fallback(self, language: str) -> Dict[str, Any]:
        fr = language != "en"
        labels = ["Segment utilisateur principal", "Acheteur économique"] if fr else ["Primary user segment", "Economic buyer"]
        values = ["Résoudre un workflow principal mesurable"] if fr else ["Solve one measurable core workflow"]
        result = self._result(segments=labels, values=values, channels=["Prospection directe" if fr else "Direct outreach"], relationships=["Onboarding accompagné" if fr else "Guided onboarding"], revenues=["Pilote payant" if fr else "Paid pilot"], resources=["MVP ciblé" if fr else "Focused MVP"], activities=["Validation terrain" if fr else "Field validation"], partners=["Partenaires pilotes" if fr else "Pilot partners"], costs=["Développement, pilote et support" if fr else "Development, pilot and support"], summary="Canvas prudent à compléter avec le contexte projet." if fr else "Cautious canvas to complete with project context.", note="Le modèle doit être validé." if fr else "The model must be validated.", priorities=["Entretiens et pilote" if fr else "Interviews and pilot"], risk_note="Preuves insuffisantes." if fr else "Insufficient evidence.", risk_level="medium")
        result.update({"output_language": language, "fallback_used": True, "error_handled": True, "confidence_level": "low"})
        return result

    def _text(self, value: Any, fallback: str = "") -> str:
        if value is None: return fallback
        clean = re.sub(r"\s+", " ", str(value)).strip()
        return clean or fallback

    def _list(self, value: Any) -> List[str]:
        if value is None: return []
        if isinstance(value, dict):
            if any(key in value for key in ("action", "pain", "mechanism", "value", "name")): return [self._packet_text(value)]
            result: List[str] = []
            for item in value.values(): result.extend(self._list(item))
            return self._unique(result)
        if isinstance(value, (list, tuple, set)):
            result: List[str] = []
            for item in value: result.extend(self._list(item))
            return self._unique(result)
        text = self._text(value)
        return [text] if text else []

    def _first(self, values: Any) -> str:
        items = self._list(values)
        return items[0] if items else ""

    def _unique(self, values: Iterable[Any]) -> List[str]:
        result: List[str] = []; seen = set()
        for value in values:
            clean = self._text(value)
            if not clean: continue
            key = clean.casefold()
            if key in seen: continue
            seen.add(key); result.append(clean)
        return result