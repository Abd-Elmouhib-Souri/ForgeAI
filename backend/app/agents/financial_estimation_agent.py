from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple

from app.services.domain_integrity_guard import normalize_output_language


class FinancialEstimationAgent:
    """Deterministic, archetype-aware financial planning agent.

    The agent never presents planning ranges as verified market prices. Every
    range is explicitly labelled as an internal hypothesis that must be replaced
    by supplier quotes, payroll assumptions and pilot observations.
    """

    FORMAT = "financial_estimation_v6_archetype_aware"

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        try:
            context = self._context(state)
            if context["project_archetype"] == "two_sided_marketplace":
                result = self._build_marketplace_finance(context, language)
            elif context["project_archetype"] == "hardware_iot":
                result = self._build_hardware_finance(context, language)
            else:
                result = self._build_digital_finance(context, language)
            return self._sanitize(result, language)
        except Exception:
            return self._emergency_fallback(language)

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    def _build_hardware_finance(
        self,
        context: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        currency = self._currency_for_region(context["region"])
        complexity = self._hardware_complexity(context)

        if complexity == "high":
            ranges = {
                "engineering": (9000, 22000),
                "mechanical": (2500, 8000),
                "electronics": (3000, 9000),
                "embedded_ai": (5000, 16000),
                "field_tests": (2500, 9000),
                "deployment": (1500, 5000),
                "contingency": (3500, 10000),
            }
        else:
            ranges = {
                "engineering": (5000, 13000),
                "mechanical": (1200, 4500),
                "electronics": (1800, 6000),
                "embedded_ai": (3000, 10000),
                "field_tests": (1500, 5000),
                "deployment": (800, 3000),
                "contingency": (1800, 6000),
            }

        factor = self._regional_cost_factor(context["region"], currency)
        ranges = {
            key: (round(low * factor), round(high * factor))
            for key, (low, high) in ranges.items()
        }
        low_total = sum(low for low, _ in ranges.values())
        high_total = sum(high for _, high in ranges.values())

        labels_fr = {
            "engineering": "Conception système, mécanique et intégration",
            "mechanical": "Châssis, motorisation, boîtier et alimentation",
            "electronics": "Composants électroniques, caméra, capteurs et calcul embarqué",
            "embedded_ai": "Firmware, navigation, IA et tableau de bord",
            "field_tests": "Essais terrain, jeux de données et itérations",
            "deployment": "Installation, formation et outillage de déploiement",
            "contingency": "Réserve pour pannes, remplacement et imprévus",
        }
        labels_en = {
            "engineering": "System, mechanical and integration engineering",
            "mechanical": "Chassis, drive system, enclosure and power",
            "electronics": "Electronic components, camera, sensors and edge compute",
            "embedded_ai": "Firmware, navigation, AI and dashboard",
            "field_tests": "Field tests, datasets and iterations",
            "deployment": "Installation, training and deployment tooling",
            "contingency": "Failure, replacement and contingency reserve",
        }
        labels = labels_en if language == "en" else labels_fr
        breakdown = [
            {
                "category": labels[key],
                "min": low,
                "max": high,
                "currency": currency,
                "evidence_status": "planning_assumption",
            }
            for key, (low, high) in ranges.items()
        ]

        core_action = self._core_action(context, language)
        success_metrics = context["success_metrics"] or self._default_hardware_metrics(language)
        constraints = context["constraints"] or context["risk_dimensions"]
        business_model = context["business_model"]

        if language == "en":
            summary = (
                f"{context['title']} is a hardware/IoT project. The first financial decision is not a national rollout; "
                f"it is whether one reliable field prototype can complete '{core_action}' at an acceptable deployed cost."
            )
            budget = (
                f"Internal planning range for one field-ready MVP: {self._money(low_total, currency)}–"
                f"{self._money(high_total, currency)}. This is not a supplier quote."
            )
            infra = (
                "Recurring infrastructure should include only services required by the pilot: connectivity, telemetry, storage, "
                "monitoring, firmware delivery, dashboard hosting and technical support."
            )
            initial_costs = [item["category"] for item in breakdown]
            monthly_costs = [
                "Connectivity and telemetry",
                "Dashboard hosting, storage and monitoring",
                "Preventive maintenance and replacement stock",
                "Technical support and field interventions",
                "Firmware, model and application updates",
            ]
            revenues = self._unique([
                business_model,
                "Robot lease or paid deployment",
                "Hardware sale with installation",
                "Maintenance and support contract",
                "Recurring dashboard, analytics or alerting subscription",
            ])
            pricing = (
                "Price from total deployed cost and measurable customer value. Test a paid pilot first, then compare lease, sale and "
                "service-bundle offers with the real budget owner."
            )
            break_even = (
                "Calculate contribution per deployed unit: collected price minus bill of materials, assembly, logistics, installation, "
                "failure reserve, maintenance, support and recurring infrastructure."
            )
            funding = (
                "Fund one reliable prototype, a repeatable installation process and a measured pilot before inventory or manufacturing volume."
            )
            assumptions = [
                f"The planning currency is {currency} for the region {context['region'] or 'not specified'}.",
                "The range covers one field-ready MVP and a limited pilot, not mass production.",
                "Internal labour and external contractor costs may change the range materially.",
                "Every component and service cost must be replaced by a current quote.",
            ]
            risks = self._unique(constraints + [
                "Component price or availability changes",
                "Field reliability below the acceptance threshold",
                "Maintenance and support effort higher than expected",
                "Customer value does not justify the deployed cost",
            ])
            roi = (
                "ROI becomes credible only after the pilot measures avoided inspection time or losses, total deployed cost, maintenance "
                "effort, availability and useful lifetime."
            )
            note = (
                "All numeric ranges are internal planning hypotheses. They are not market facts and must be replaced by supplier quotes, "
                "staffing assumptions and observed pilot costs."
            )
        else:
            summary = (
                f"{context['title']} est un projet matériel/IoT. La première décision financière n’est pas un déploiement national : "
                f"il faut vérifier si un prototype terrain fiable peut réaliser « {core_action} » avec un coût déployé acceptable."
            )
            budget = (
                f"Fourchette interne de planification pour un MVP prêt au terrain : {self._money(low_total, currency)} à "
                f"{self._money(high_total, currency)}. Cette fourchette n’est pas un devis fournisseur."
            )
            infra = (
                "Les coûts récurrents doivent couvrir uniquement les services nécessaires au pilote : connectivité, télémétrie, stockage, "
                "monitoring, mises à jour firmware, hébergement du tableau de bord et support technique."
            )
            initial_costs = [item["category"] for item in breakdown]
            monthly_costs = [
                "Connectivité et télémétrie",
                "Hébergement du tableau de bord, stockage et monitoring",
                "Maintenance préventive et stock de remplacement",
                "Support technique et interventions terrain",
                "Mises à jour firmware, modèles IA et application",
            ]
            revenues = self._unique([
                business_model,
                "Location du robot ou déploiement pilote payant",
                "Vente du matériel avec installation",
                "Contrat de maintenance et support",
                "Abonnement récurrent au tableau de bord, aux alertes ou aux analyses",
            ])
            pricing = (
                "Fixer le prix à partir du coût total déployé et de la valeur client mesurée. Tester d’abord un pilote payant, puis comparer "
                "les offres de location, vente et service groupé avec le véritable détenteur du budget."
            )
            break_even = (
                "Calculer la contribution par dispositif déployé : prix encaissé moins composants, assemblage, logistique, installation, "
                "réserve de panne, maintenance, support et infrastructure récurrente."
            )
            funding = (
                "Financer un prototype fiable, un processus d’installation répétable et un pilote mesuré avant de constituer du stock ou de lancer une fabrication en volume."
            )
            assumptions = [
                f"La devise de planification est {currency} pour la région {context['region'] or 'non définie'}.",
                "La fourchette couvre un MVP prêt au terrain et un pilote limité, pas une production de masse.",
                "Le coût de la main-d’œuvre interne ou de prestataires peut modifier fortement la fourchette.",
                "Chaque coût de composant et de service doit être remplacé par un devis actuel.",
            ]
            risks = self._unique(constraints + [
                "Variation du prix ou de la disponibilité des composants",
                "Fiabilité terrain inférieure au seuil d’acceptation",
                "Maintenance et support plus lourds que prévu",
                "Valeur client insuffisante face au coût déployé",
            ])
            roi = (
                "Le ROI devient crédible seulement après mesure, pendant le pilote, du temps ou des pertes évités, du coût total déployé, "
                "de la maintenance, de la disponibilité et de la durée de vie utile."
            )
            note = (
                "Toutes les fourchettes chiffrées sont des hypothèses internes de planification. Elles ne constituent pas des faits de marché "
                "et doivent être remplacées par des devis fournisseurs, des hypothèses de personnel et les coûts observés du pilote."
            )

        return self._base_result(
            context=context,
            language=language,
            summary=summary,
            mvp_budget=budget,
            infrastructure=infra,
            breakdown=breakdown,
            initial_costs=initial_costs,
            monthly_costs=monthly_costs,
            revenues=revenues,
            pricing=pricing,
            break_even=break_even,
            funding=funding,
            assumptions=assumptions,
            risks=risks,
            kpis=success_metrics + self._default_hardware_finance_kpis(language),
            roi=roi,
            note=note,
            currency=currency,
            budget_min=low_total,
            budget_max=high_total,
            risk_level="high",
        )

    def _build_marketplace_finance(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        currency = self._currency_for_region(context["region"])
        factor = self._regional_cost_factor(context["region"], currency)
        low, high = round(12000 * factor), round(38000 * factor)
        core = self._core_action(context, language)
        business_model = context["business_model"]
        actors = context["actors"]
        demand = actors.get("demand_side") or actors.get("primary_user") or context["target_users"]
        supply = actors.get("supply_side") or ("prestataires" if language != "en" else "providers")

        if language == "en":
            summary = f"{context['title']} must prove liquidity and positive contribution economics around one completed transaction: {core}."
            budget = f"Internal planning range for a constrained marketplace MVP and pilot: {self._money(low, currency)}–{self._money(high, currency)}."
            infra = "API, database, notifications, identity, payments or reconciliation, observability and operational incident logs."
            initial = ["Demand transaction flow", "Provider onboarding and availability", "Matching and status logic", "Operations console", "Trust and safety controls", "Limited-zone pilot"]
            monthly = ["Cloud and monitoring", "Payment and messaging fees", "Provider acquisition or incentives", "Support and dispute handling", "Compliance and local operations"]
            revenues = self._unique([business_model, "Commission or service fee per completed transaction", "Professional provider plan after liquidity is proven"])
            pricing = "Test a transparent take rate or fixed fee on a real completed transaction."
            break_even = "Use completed transactions: fee collected minus payment cost, incentives, variable support and fulfilment cost."
            funding = "Fund one constrained geography or segment until both sides transact repeatedly without unsustainable incentives."
            assumptions = [f"Demand actor: {demand}.", f"Supply actor: {supply}.", "Both sides can be active in the same place and time window.", "The tested fee preserves value for both sides."]
            risks = context["risk_dimensions"] or ["Insufficient liquidity", "Negative contribution after incentives", "High cancellation and support burden", "Regulatory or safety cost"]
            kpis = context["success_metrics"] + ["Contribution margin per completed transaction", "Variable cost per completed transaction", "Repeat transaction rate"]
            roi = "ROI is credible only after repeated transactions and positive contribution margin are observed."
            note = "The range is an internal planning hypothesis and must be replaced by staffing, provider, payment and compliance quotes."
        else:
            summary = f"{context['title']} doit prouver la liquidité et une contribution positive autour d’une transaction réalisée : {core}."
            budget = f"Fourchette interne pour un MVP marketplace et un pilote limités : {self._money(low, currency)} à {self._money(high, currency)}."
            infra = "API, base de données, notifications, identité, paiement ou rapprochement, observabilité et journal des incidents."
            initial = ["Parcours transactionnel côté demande", "Onboarding et disponibilité côté offre", "Mise en relation et suivi des statuts", "Console d’opérations", "Contrôles de confiance et sécurité", "Pilote sur une zone limitée"]
            monthly = ["Cloud et monitoring", "Frais de paiement et messagerie", "Acquisition ou incitations des prestataires", "Support et gestion des litiges", "Conformité et opérations locales"]
            revenues = self._unique([business_model, "Commission ou frais de service par transaction réalisée", "Offre professionnelle après preuve de liquidité"])
            pricing = "Tester une commission transparente ou des frais fixes sur une vraie transaction terminée."
            break_even = "Utiliser les transactions terminées : frais encaissés moins paiement, incitations, support variable et coût de réalisation."
            funding = "Financer une zone ou un segment limité jusqu’à obtenir des transactions répétées sans incitations non soutenables."
            assumptions = [f"Acteur demande : {demand}.", f"Acteur offre : {supply}.", "Les deux côtés peuvent être actifs au même endroit et au même moment.", "Les frais testés préservent la valeur des deux côtés."]
            risks = context["risk_dimensions"] or ["Liquidité insuffisante", "Contribution négative après incitations", "Annulations et support élevés", "Coût réglementaire ou de sécurité"]
            kpis = context["success_metrics"] + ["Marge contributive par transaction terminée", "Coût variable par transaction", "Taux de transactions répétées"]
            roi = "Le ROI devient crédible après observation de transactions répétées et d’une marge contributive positive."
            note = "La fourchette est une hypothèse interne à remplacer par des coûts de personnel, prestataires, paiement et conformité."

        breakdown = [{"category": item, "min": None, "max": None, "currency": currency, "evidence_status": "quote_required"} for item in initial]
        return self._base_result(context=context, language=language, summary=summary, mvp_budget=budget, infrastructure=infra, breakdown=breakdown, initial_costs=initial, monthly_costs=monthly, revenues=revenues, pricing=pricing, break_even=break_even, funding=funding, assumptions=assumptions, risks=risks, kpis=kpis, roi=roi, note=note, currency=currency, budget_min=low, budget_max=high, risk_level="high")

    def _build_digital_finance(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        currency = self._currency_for_region(context["region"])
        factor = self._regional_cost_factor(context["region"], currency)
        archetype = context["project_archetype"]
        base = (8000, 26000) if archetype in {"regulated_service", "analytics_ai_tool"} else (5000, 18000)
        low, high = round(base[0] * factor), round(base[1] * factor)
        core = self._core_action(context, language)
        business_model = context["business_model"]

        if language == "en":
            summary = f"{context['title']} must prove successful and repeated completion of '{core}' before growth forecasts become credible."
            budget = f"Internal planning range for a focused digital MVP and first pilot: {self._money(low, currency)}–{self._money(high, currency)}."
            infra = "Lean cloud hosting, managed database, monitoring, backups, email or notifications, analytics and required third-party APIs."
            initial = ["Product specification and UX", "Core frontend and backend workflow", "Authentication and data model", "Analytics and experiment instrumentation", "Pilot onboarding and user tests"]
            monthly = ["Cloud and database", "Monitoring and backups", "Support and maintenance", "Third-party APIs", "Small acquisition experiments"]
            revenues = self._unique([business_model, "Paid pilot or setup fee", "Subscription or usage fee after repeat value is proven"])
            pricing = "Test concrete offers with the actual payer; measure conversion, repeat use and delivery cost."
            break_even = "Calculate contribution per active paying customer or successful core action, then include acquisition and retention."
            funding = "Fund a complete core workflow and one measurable acquisition experiment before scaling marketing."
            assumptions = ["Users complete and repeat the core action.", "The payer accepts a concrete offer.", "Acquisition and delivery costs remain below lifetime contribution."]
            risks = context["risk_dimensions"] or ["Weak retention", "High acquisition cost", "Low paid conversion", "Operational, trust or privacy failures"]
            kpis = context["success_metrics"] + ["Activation", "Successful core action", "Repeat use", "Paid conversion", "Contribution margin", "Retention"]
            roi = "ROI becomes credible after repeated value, paid conversion and positive contribution are measured."
            note = "The numeric range is an internal planning hypothesis, not a verified development quote."
        else:
            summary = f"{context['title']} doit prouver la réalisation réussie et répétée de « {core} » avant toute prévision crédible de croissance."
            budget = f"Fourchette interne pour un MVP numérique ciblé et un premier pilote : {self._money(low, currency)} à {self._money(high, currency)}."
            infra = "Hébergement cloud léger, base de données gérée, monitoring, sauvegardes, email ou notifications, analytics et API tierces nécessaires."
            initial = ["Spécification produit et UX", "Parcours principal frontend et backend", "Authentification et modèle de données", "Analytics et instrumentation des expériences", "Onboarding pilote et tests utilisateurs"]
            monthly = ["Cloud et base de données", "Monitoring et sauvegardes", "Support et maintenance", "API tierces", "Petites expériences d’acquisition"]
            revenues = self._unique([business_model, "Pilote payant ou frais de configuration", "Abonnement ou frais d’usage après preuve de valeur répétée"])
            pricing = "Tester des offres concrètes avec le véritable payeur et mesurer conversion, usage répété et coût de réalisation."
            break_even = "Calculer la contribution par client payant actif ou action principale réussie, puis intégrer acquisition et rétention."
            funding = "Financer un parcours principal complet et une expérience d’acquisition mesurable avant d’augmenter le marketing."
            assumptions = ["Les utilisateurs réalisent et répètent l’action principale.", "Le payeur accepte une offre concrète.", "Les coûts d’acquisition et de réalisation restent inférieurs à la contribution vie client."]
            risks = context["risk_dimensions"] or ["Faible rétention", "Coût d’acquisition élevé", "Faible conversion payante", "Échecs opérationnels, de confiance ou confidentialité"]
            kpis = context["success_metrics"] + ["Activation", "Action principale réussie", "Usage répété", "Conversion payante", "Marge contributive", "Rétention"]
            roi = "Le ROI devient crédible après mesure d’une valeur répétée, d’une conversion payante et d’une contribution positive."
            note = "La fourchette chiffrée est une hypothèse interne de planification, pas un devis de développement vérifié."

        breakdown = [{"category": item, "min": None, "max": None, "currency": currency, "evidence_status": "quote_required"} for item in initial]
        return self._base_result(context=context, language=language, summary=summary, mvp_budget=budget, infrastructure=infra, breakdown=breakdown, initial_costs=initial, monthly_costs=monthly, revenues=revenues, pricing=pricing, break_even=break_even, funding=funding, assumptions=assumptions, risks=risks, kpis=kpis, roi=roi, note=note, currency=currency, budget_min=low, budget_max=high, risk_level="high" if archetype == "regulated_service" else "medium")

    # ------------------------------------------------------------------
    # Contract and context
    # ------------------------------------------------------------------

    def _base_result(
        self,
        *,
        context: Dict[str, Any],
        language: str,
        summary: str,
        mvp_budget: str,
        infrastructure: str,
        breakdown: List[Dict[str, Any]],
        initial_costs: List[str],
        monthly_costs: List[str],
        revenues: List[str],
        pricing: str,
        break_even: str,
        funding: str,
        assumptions: List[str],
        risks: List[str],
        kpis: List[str],
        roi: str,
        note: str,
        currency: str,
        budget_min: int,
        budget_max: int,
        risk_level: str,
    ) -> Dict[str, Any]:
        initial_costs = self._unique(initial_costs)
        monthly_costs = self._unique(monthly_costs)
        revenues = self._unique(revenues)
        return {
            "format": self.FORMAT,
            "status": "completed",
            "summary": summary,
            "mvp_budget_estimate": mvp_budget,
            "mvp_budget_min": budget_min,
            "mvp_budget_max": budget_max,
            "currency": currency,
            "budget_breakdown": breakdown,
            "budget_basis": "internal_planning_assumption",
            "budget_confidence": "low",
            "infrastructure_cost_estimate": infrastructure,
            "possible_revenue_streams": revenues,
            "pricing_model": pricing,
            "break_even_point": break_even,
            "cost_structure": self._unique(initial_costs + monthly_costs),
            "initial_costs": initial_costs,
            "monthly_costs": monthly_costs,
            "revenue_streams": revenues,
            "pricing_strategy": pricing,
            "break_even_analysis": break_even,
            "funding_needs": funding,
            "assumptions": self._unique(assumptions),
            "financial_risks": self._unique(risks),
            "recommended_kpis": self._unique(kpis),
            "roi_outlook": roi,
            "financial_note": note,
            "financial_risk_level": risk_level,
            "confidence_level": "low",
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "context_locked": True,
            "output_language": language,
            "project_context_used": {
                "title": context["title"],
                "sector": context["sector"],
                "region": context["region"],
                "target_users": context["target_users"],
                "business_model": context["business_model"],
                "mvp_scope": context["mvp_scope"],
                "project_archetype": context["project_archetype"],
                "priority_workflows": context["priority_workflows"],
                "success_metrics": context["success_metrics"],
                "constraints": context["constraints"],
            },
        }

    def _context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        analysis = state.get("analysis_data") or {}
        project_context = state.get("project_context") or {}
        intelligence = state.get("project_intelligence") or analysis.get("project_intelligence") or project_context.get("project_intelligence") or {}
        structured = state.get("structured_project_context") or analysis.get("structured_project_context") or project_context.get("structured_project_context") or intelligence.get("structured_project_context") or {}
        canonical = self._canonical_packet(state, analysis, project_context)

        title = self._text(structured.get("project_name") or structured.get("title") or canonical.get("project_name") or project_context.get("title") or state.get("title"), "Project")
        sector = self._text(structured.get("sector") or structured.get("industry") or canonical.get("domain_label") or project_context.get("industry") or state.get("industry"), "")
        region = self._text(structured.get("target_region") or structured.get("market_region") or canonical.get("target_region") or project_context.get("market_region") or state.get("region"), "")
        target_values = structured.get("target_users") or canonical.get("actors") or project_context.get("target_users") or []
        target_users = self._readable_list(target_values)
        business_model = self._text(structured.get("business_model") or self._first(canonical.get("business_model_hypotheses")) or project_context.get("business_model"), "Business model to validate")
        mvp_scope = self._readable_list(structured.get("mvp_scope") or canonical.get("mvp_scope") or project_context.get("mvp_scope") or [])
        workflows = self._list(structured.get("priority_workflows") or structured.get("priority_workflow") or canonical.get("priority_workflow") or canonical.get("priority_workflows"))
        success_metrics = self._list(structured.get("success_metrics") or canonical.get("success_metrics") or project_context.get("success_metrics"))
        constraints = self._list(structured.get("constraints") or canonical.get("constraints") or project_context.get("constraints"))
        risks = self._list(structured.get("risk_dimensions") or project_context.get("risk_dimensions"))
        actors = structured.get("actors") or project_context.get("actors") or {}
        if isinstance(canonical.get("actors"), list):
            actors = dict(actors) if isinstance(actors, dict) else {}
            actors.setdefault("target_users", canonical["actors"])

        return {
            "title": title,
            "sector": sector,
            "region": region,
            "target_users": target_users,
            "business_model": business_model,
            "mvp_scope": mvp_scope,
            "project_archetype": self._text(structured.get("project_archetype") or canonical.get("project_archetype") or project_context.get("project_archetype"), "generic_digital_product"),
            "validation_unit": self._text(structured.get("validation_unit") or canonical.get("validation_unit"), ""),
            "priority_workflows": workflows,
            "success_metrics": success_metrics,
            "constraints": constraints,
            "risk_dimensions": risks,
            "actors": actors if isinstance(actors, dict) else {},
        }

    def _canonical_packet(self, state: Dict[str, Any], analysis: Dict[str, Any], project_context: Dict[str, Any]) -> Dict[str, Any]:
        candidates = [
            state.get("project_context_packet"), state.get("canonical_context"),
            analysis.get("project_context_packet"), analysis.get("canonical_context"),
            analysis.get("context_packet"), project_context.get("project_context_packet"),
            project_context.get("canonical_context"),
        ]
        readiness = analysis.get("idea_readiness") or {}
        candidates.extend([readiness.get("context_packet"), readiness.get("project_context_packet"), readiness.get("canonical_context")])
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate
        return {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _hardware_complexity(self, context: Dict[str, Any]) -> str:
        text = " ".join([context["mvp_scope"], *context["priority_workflows"], *context["constraints"]]).lower()
        score = sum(term in text for term in ("autonome", "autonomous", "slam", "navigation", "computer vision", "vision", "robot", "motor", "moteur", "terrain", "field"))
        return "high" if score >= 3 else "medium"

    def _core_action(self, context: Dict[str, Any], language: str) -> str:
        generic = {"core action", "core workflow", "réaliser l’opération terrain principale", "operation terrain principale", "main field operation"}
        for value in context["priority_workflows"]:
            clean = self._text(value)
            if clean and clean.lower() not in generic:
                return clean
        if context["validation_unit"]:
            return context["validation_unit"]
        return "réaliser le workflow principal" if language != "en" else "complete the core workflow"

    def _currency_for_region(self, region: str) -> str:
        text = self._normalize(region)
        mapping = [
            (("tunisie", "tunisia"), "TND"), (("france", "belgique", "belgium", "germany", "allemagne", "italy", "italie", "spain", "espagne", "europe"), "EUR"),
            (("czech", "tcheque", "tchèque", "czechia"), "CZK"), (("morocco", "maroc"), "MAD"), (("algeria", "algérie", "algerie"), "DZD"),
            (("usa", "united states", "états-unis", "etats-unis"), "USD"), (("uk", "united kingdom", "royaume-uni"), "GBP"),
        ]
        for names, currency in mapping:
            if any(name in text for name in names):
                return currency
        return "USD"

    def _regional_cost_factor(self, region: str, currency: str) -> float:
        # The base ranges are authored in TND-like planning units. Factors are
        # intentionally coarse and are never presented as exchange rates.
        return {"TND": 1.0, "EUR": 0.55, "USD": 0.60, "GBP": 0.50, "MAD": 3.2, "DZD": 45.0, "CZK": 13.5}.get(currency, 0.60)

    def _money(self, value: int, currency: str) -> str:
        return f"{value:,.0f} {currency}".replace(",", " ")

    def _default_hardware_metrics(self, language: str) -> List[str]:
        return ["Field task success", "Accuracy", "Uptime", "Failure rate", "Maintenance time", "Deployed unit cost"] if language == "en" else ["Réussite de la tâche terrain", "Précision", "Disponibilité", "Taux de panne", "Temps de maintenance", "Coût unitaire déployé"]

    def _default_hardware_finance_kpis(self, language: str) -> List[str]:
        return ["Bill of materials per unit", "Installation cost", "Monthly support cost", "Failure reserve", "Contribution per deployed unit"] if language == "en" else ["Nomenclature par unité", "Coût d’installation", "Coût mensuel de support", "Réserve de panne", "Contribution par unité déployée"]

    def _sanitize(self, value: Any, language: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return self._emergency_fallback(language)
        return self._sanitize_object(value)

    def _sanitize_object(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self._sanitize_object(v) for k, v in value.items() if str(k) not in {"debug", "raw_data", "raw_response", "internal_error"} and not self._empty(v)}
        if isinstance(value, list):
            return [self._sanitize_object(v) for v in value if not self._empty(v)]
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value

    def _emergency_fallback(self, language: str) -> Dict[str, Any]:
        fr = language != "en"
        return {
            "format": self.FORMAT,
            "status": "completed",
            "summary": "Estimation financière prudente à compléter par des devis." if fr else "Cautious financial estimate to complete with quotes.",
            "mvp_budget_estimate": "Fourchette indisponible : fournir le périmètre, la région et l’archétype." if fr else "Range unavailable: provide scope, region and archetype.",
            "infrastructure_cost_estimate": "À confirmer par devis." if fr else "Confirm with quotes.",
            "possible_revenue_streams": [],
            "initial_costs": [],
            "monthly_costs": [],
            "financial_risk_level": "high",
            "confidence_level": "low",
            "manual_review_required": True,
            "fallback_used": True,
            "error_handled": True,
            "context_locked": True,
            "output_language": language,
        }

    def _text(self, value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback
        if isinstance(value, dict):
            for key in ("action", "mechanism", "core_value", "pain", "value", "label", "name"):
                if value.get(key):
                    return self._text(value[key], fallback)
            return fallback
        clean = re.sub(r"\s+", " ", str(value)).strip()
        return clean or fallback

    def _list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            if any(key in value for key in ("action", "mechanism", "pain", "value")):
                text = self._text(value)
                return [text] if text else []
            result: List[str] = []
            for item in value.values():
                result.extend(self._list(item))
            return self._unique(result)
        if isinstance(value, (list, tuple, set)):
            result: List[str] = []
            for item in value:
                result.extend(self._list(item))
            return self._unique(result)
        text = self._text(value)
        return [text] if text else []

    def _readable_list(self, value: Any) -> str:
        return ", ".join(self._list(value)[:8])

    def _first(self, value: Any) -> str:
        items = self._list(value)
        return items[0] if items else ""

    def _unique(self, values: Iterable[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            clean = self._text(value)
            if not clean:
                continue
            key = clean.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(clean)
        return result

    def _normalize(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()

    def _empty(self, value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}