# ============================================================
# backend/app/agents/financial_estimation_agent.py
# ============================================================
#
# FinancialEstimationAgent V5.5
# Deterministic + Context-Locked + No LLM
#
# Objectifs :
# - aucun appel LLM pour financial_estimation ;
# - aucune dépendance LLMProvider / invoke_llm_json ;
# - sortie financière stable et exploitable ;
# - partial=False ;
# - champs compatibles avec le rapport actuel ;
# - finance prudente, non hallucinée, basée sur le contexte projet ;
# - préparation pour Quality Gate final.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class FinancialEstimationAgent:
    DEMO_OFFTOPIC_TERMS = {
        "pharmacy delivery",
        "medicine delivery",
        "stock trading",
        "crypto trading",
        "forex trading",
        "tiktok",
        "super app",
        "orange max it",
        "food delivery",
        "restaurant delivery",
    }

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output_language = normalize_output_language(state.get("output_language", "fr"))

        try:
            context = self._context(state)
            result = self._build_financial_estimation(
                context=context,
                output_language=output_language,
            )

            return self._final_public_sanitize(
                data=result,
                context=context,
                output_language=output_language,
            )

        except Exception:
            return self._emergency_fallback(output_language)

    # ========================================================
    # Deterministic financial estimation
    # ========================================================

    def _build_financial_estimation(
        self,
        *,
        context: Dict[str, str],
        output_language: str,
    ) -> Dict[str, Any]:
        if output_language == "en":
            summary = (
                f"The financial estimate for {context['title']} is a cautious MVP-level assessment. "
                f"The project targets {context['target_users']} in {context['region']}. "
                "At this stage, pricing, customer acquisition cost, subscription conversion and break-even must be validated through real pilots."
            )

            mvp_budget_estimate = (
                "Indicative MVP budget to validate manually: product specification, web application development, "
                "database setup, authentication, admin dashboard, core workflow implementation, hosting setup and first user tests."
            )

            infrastructure_cost_estimate = (
                "Initial infrastructure should remain lean: cloud hosting, managed database, domain name, email service, "
                "basic monitoring and backup. Costs should be confirmed with real provider quotes before execution."
            )

            initial_costs = [
                "Product specification and MVP scope definition",
                "Frontend development for the user-facing workflow",
                "Backend development for accounts, projects and core data",
                "Database design and deployment",
                "Authentication and basic admin configuration",
                "Initial hosting, domain and email setup",
                "First pilot preparation and user testing",
            ]

            monthly_costs = [
                "Hosting and database services",
                "Maintenance and bug fixing",
                "Customer support and onboarding",
                "Small marketing and outreach budget",
                "Third-party services used by the MVP",
            ]

            possible_revenue_streams = self._revenue_streams_en(context)

            pricing_model = (
                "Start with a simple pilot price, then validate tiered monthly subscriptions. "
                "The first pricing test should measure willingness to pay before adding advanced paid features."
            )

            break_even_point = (
                "Break-even should be calculated only after measuring three real values: average paid subscription, "
                "monthly operating cost and realistic number of paying customers."
            )

            funding_needs = (
                "Funding should first cover MVP development, hosting, user interviews, pilot onboarding and basic commercial validation. "
                "Large-scale spending should wait until usage and payment intent are confirmed."
            )

            assumptions = [
                f"The first target region is {context['region']}.",
                f"The first target users are {context['target_users']}.",
                "The MVP focuses on one main workflow before advanced features.",
                "Customer acquisition cost is not yet validated.",
                "Willingness to pay must be confirmed through interviews or pilots.",
                "Revenue projections are not reliable before real pilot usage.",
            ]

            financial_risks = [
                "Users may find the product useful but not urgent enough to pay.",
                "The MVP may become too broad before market validation.",
                "Local price sensitivity can reduce paid conversion.",
                "Customer acquisition may require direct sales instead of only online marketing.",
                "Financial projections remain weak without real pilot data.",
            ]

            recommended_kpis = [
                "Pilot customers contacted",
                "Active pilot customers",
                "Weekly usage frequency",
                "Pilot-to-paid conversion rate",
                "Average monthly revenue per customer",
                "Customer acquisition cost",
                "First-month retention",
            ]

            roi_outlook = (
                f"Cautious ROI outlook: {context['title']} can become financially viable only if the MVP proves recurring usage, "
                "clear willingness to pay and a repeatable acquisition channel."
            )

            financial_note = (
                "Financial figures are initial estimates. They must be confirmed with quotes, real costs, acceptable pricing and field interviews."
            )

        else:
            summary = (
                f"L’estimation financière de {context['title']} est une évaluation prudente au niveau MVP. "
                f"Le projet cible {context['target_users']} en {context['region']}. "
                "À ce stade, le prix, le coût d’acquisition, la conversion payante et le seuil de rentabilité doivent être validés par de vrais pilotes."
            )

            mvp_budget_estimate = (
                "Budget MVP indicatif à valider manuellement : spécification produit, développement de l’application web, "
                "base de données, authentification, tableau de bord admin, flux principal, hébergement et premiers tests utilisateurs."
            )

            infrastructure_cost_estimate = (
                "L’infrastructure initiale doit rester légère : hébergement cloud, base de données, nom de domaine, email, "
                "monitoring simple et sauvegarde. Les coûts doivent être confirmés par des devis réels avant exécution."
            )

            initial_costs = [
                "Spécification produit et cadrage MVP",
                "Développement frontend du parcours utilisateur",
                "Développement backend des comptes, projets et données principales",
                "Conception et déploiement de la base de données",
                "Authentification et configuration admin de base",
                "Hébergement initial, domaine et email",
                "Préparation du pilote et tests utilisateurs",
            ]

            monthly_costs = [
                "Hébergement et base de données",
                "Maintenance et correction des bugs",
                "Support client et onboarding",
                "Petit budget marketing et prospection",
                "Services tiers utilisés par le MVP",
            ]

            possible_revenue_streams = self._revenue_streams_fr(context)

            pricing_model = (
                "Commencer avec un prix pilote simple, puis valider des abonnements mensuels par niveaux. "
                "Le premier test de prix doit mesurer la volonté de payer avant d’ajouter des fonctionnalités payantes avancées."
            )

            break_even_point = (
                "Le seuil de rentabilité doit être calculé seulement après mesure de trois valeurs réelles : abonnement moyen payé, "
                "coût mensuel d’exploitation et nombre réaliste de clients payants."
            )

            funding_needs = (
                "Le financement doit d’abord couvrir le développement MVP, l’hébergement, les entretiens utilisateurs, l’onboarding pilote "
                "et la validation commerciale de base. Les dépenses importantes doivent attendre la confirmation de l’usage et de l’intention de paiement."
            )

            assumptions = [
                f"La première région cible est {context['region']}.",
                f"Les premiers utilisateurs ciblés sont {context['target_users']}.",
                "Le MVP se concentre sur un flux principal avant les fonctionnalités avancées.",
                "Le coût d’acquisition client n’est pas encore validé.",
                "La volonté de payer doit être confirmée par entretiens ou pilotes.",
                "Les projections de revenus ne sont pas fiables avant un usage pilote réel.",
            ]

            financial_risks = [
                "Les utilisateurs peuvent trouver le produit utile mais pas assez urgent pour payer.",
                "Le MVP peut devenir trop large avant validation marché.",
                "La sensibilité au prix local peut réduire la conversion payante.",
                "L’acquisition client peut nécessiter de la vente directe et pas seulement du marketing en ligne.",
                "Les projections financières restent faibles sans données réelles de pilote.",
            ]

            recommended_kpis = [
                "Clients pilotes contactés",
                "Clients pilotes actifs",
                "Fréquence d’usage hebdomadaire",
                "Taux de conversion pilote vers paiement",
                "Revenu mensuel moyen par client",
                "Coût d’acquisition client",
                "Rétention après le premier mois",
            ]

            roi_outlook = (
                f"Perspective ROI prudente : {context['title']} peut devenir rentable seulement si le MVP prouve un usage récurrent, "
                "une volonté de payer claire et un canal d’acquisition répétable."
            )

            financial_note = (
                "Les chiffres financiers sont des estimations initiales. Ils doivent être confirmés avec des devis, des coûts réels, un prix acceptable et des entretiens terrain."
            )

        cost_structure = self._unique(initial_costs + monthly_costs)

        return {
            "format": "financial_estimation_v5_5_deterministic_context_locked",
            "status": "completed",
            "summary": summary,

            "mvp_budget_estimate": mvp_budget_estimate,
            "infrastructure_cost_estimate": infrastructure_cost_estimate,
            "possible_revenue_streams": possible_revenue_streams,
            "pricing_model": pricing_model,
            "break_even_point": break_even_point,
            "cost_structure": cost_structure,

            "initial_costs": initial_costs,
            "monthly_costs": monthly_costs,
            "revenue_streams": possible_revenue_streams,
            "pricing_strategy": pricing_model,
            "break_even_analysis": break_even_point,
            "funding_needs": funding_needs,
            "assumptions": assumptions,
            "financial_risks": financial_risks,
            "recommended_kpis": recommended_kpis,
            "roi_outlook": roi_outlook,
            "financial_note": financial_note,

            "financial_risk_level": "medium",
            "confidence_level": "medium",
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "context_locked": True,
            "output_language": output_language,

            "project_context_used": {
                "title": context["title"],
                "sector": context["sector"],
                "region": context["region"],
                "target_users": context["target_users"],
                "business_model": context["business_model"],
                "mvp_scope": context["mvp_scope"],
            },
        }

    def _revenue_streams_en(self, context: Dict[str, str]) -> List[str]:
        streams = [
            "Monthly subscription for active organizations",
            "Tiered paid plan based on active users or managed records",
            "Annual subscription with discount",
            "Setup or onboarding fee for professional customers",
            "Premium add-ons after the core MVP is validated",
        ]

        business_model = context.get("business_model", "").strip()

        if business_model and business_model.lower() not in {
            "subscription or pilot-based business model",
            "business model",
            "unknown",
        }:
            streams.insert(0, business_model)

        return self._unique(streams)[:6]

    def _revenue_streams_fr(self, context: Dict[str, str]) -> List[str]:
        streams = [
            "Abonnement mensuel pour les organisations actives",
            "Plan payant par niveau selon les utilisateurs ou dossiers gérés",
            "Abonnement annuel avec remise",
            "Frais d’installation ou d’onboarding pour les clients professionnels",
            "Options premium après validation du MVP principal",
        ]

        business_model = context.get("business_model", "").strip()

        if business_model and business_model.lower() not in {
            "modèle économique par abonnement ou pilote",
            "modèle économique",
            "inconnu",
        }:
            streams.insert(0, business_model)

        return self._unique(streams)[:6]

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

        business_model = self._safe_text(
            structured.get("business_model")
            or project_context.get("business_model"),
            "subscription or pilot-based business model",
        )

        mvp_scope = self._safe_text(
            structured.get("mvp_scope")
            or project_context.get("mvp_scope"),
            "reduced MVP",
        )

        return {
            "title": self._sanitize_text(title, allowed_context=""),
            "sector": self._sanitize_text(sector, allowed_context=""),
            "region": self._sanitize_text(region, allowed_context=""),
            "target_users": self._sanitize_text(target_users, allowed_context=""),
            "business_model": self._sanitize_text(business_model, allowed_context=""),
            "mvp_scope": self._sanitize_text(mvp_scope, allowed_context=""),
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
        allowed_context = self._normalize(
            " ".join(
                [
                    context.get("title", ""),
                    context.get("sector", ""),
                    context.get("region", ""),
                    context.get("target_users", ""),
                    context.get("business_model", ""),
                    context.get("mvp_scope", ""),
                ]
            )
        )

        sanitized = self._sanitize_object(data, allowed_context=allowed_context)

        if not isinstance(sanitized, dict):
            return self._emergency_fallback(output_language)

        sanitized.setdefault("format", "financial_estimation_v5_5_deterministic_context_locked")
        sanitized.setdefault("status", "completed")
        sanitized.setdefault("financial_risk_level", "medium")
        sanitized.setdefault("confidence_level", "medium")
        sanitized.setdefault("manual_review_required", True)
        sanitized.setdefault("context_locked", True)
        sanitized.setdefault("output_language", output_language)

        return sanitized

    def _sanitize_object(self, value: Any, *, allowed_context: str) -> Any:
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
                    item,
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
                    item,
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

        return text[:900].strip()

    def _emergency_fallback(self, output_language: str) -> Dict[str, Any]:
        if output_language == "en":
            return {
                "format": "financial_estimation_v5_5_emergency_fallback",
                "status": "completed",
                "summary": "Financial estimation is available as a cautious MVP-level assessment. Pricing, costs and revenue must be validated manually.",
                "mvp_budget_estimate": "Indicative MVP budget to validate manually.",
                "infrastructure_cost_estimate": "Initial infrastructure should remain limited and validated with real provider costs.",
                "possible_revenue_streams": [
                    "Monthly subscription",
                    "Paid pilot",
                    "Setup or onboarding fee",
                ],
                "pricing_model": "Start with a pilot price, then validate tiered subscription plans.",
                "break_even_point": "Break-even must be calculated after real pilot data.",
                "cost_structure": [
                    "MVP development",
                    "Hosting",
                    "Maintenance",
                    "Customer support",
                    "Marketing tests",
                ],
                "initial_costs": [
                    "MVP development",
                    "Product specification",
                    "Initial setup",
                ],
                "monthly_costs": [
                    "Hosting",
                    "Maintenance",
                    "Support",
                ],
                "revenue_streams": [
                    "Monthly subscription",
                    "Paid pilot",
                    "Setup fee",
                ],
                "pricing_strategy": "Validate pricing with pilot customers before scaling.",
                "break_even_analysis": "Break-even remains indicative without real usage and payment data.",
                "funding_needs": "Funding should cover MVP, hosting and first pilots.",
                "assumptions": [
                    "The MVP must be validated with real users.",
                    "Willingness to pay is not yet proven.",
                ],
                "financial_risks": [
                    "Price sensitivity",
                    "Weak conversion to paid plan",
                    "Unvalidated acquisition cost",
                ],
                "recommended_kpis": [
                    "Pilot customers",
                    "Paid conversion rate",
                    "Monthly revenue per customer",
                ],
                "roi_outlook": "Cautious ROI outlook until real pilot data is collected.",
                "financial_note": "Financial figures must be confirmed manually.",
                "financial_risk_level": "medium",
                "confidence_level": "low",
                "manual_review_required": True,
                "fallback_used": True,
                "error_handled": True,
                "context_locked": True,
                "output_language": output_language,
            }

        return {
            "format": "financial_estimation_v5_5_emergency_fallback",
            "status": "completed",
            "summary": "L’estimation financière est disponible comme évaluation prudente au niveau MVP. Les prix, coûts et revenus doivent être validés manuellement.",
            "mvp_budget_estimate": "Budget MVP indicatif à valider manuellement.",
            "infrastructure_cost_estimate": "L’infrastructure initiale doit rester limitée et validée avec des coûts réels.",
            "possible_revenue_streams": [
                "Abonnement mensuel",
                "Pilote payant",
                "Frais d’installation ou d’onboarding",
            ],
            "pricing_model": "Commencer avec un prix pilote, puis valider des plans d’abonnement par niveaux.",
            "break_even_point": "Le seuil de rentabilité doit être calculé après des données réelles de pilote.",
            "cost_structure": [
                "Développement MVP",
                "Hébergement",
                "Maintenance",
                "Support client",
                "Tests marketing",
            ],
            "initial_costs": [
                "Développement MVP",
                "Spécification produit",
                "Configuration initiale",
            ],
            "monthly_costs": [
                "Hébergement",
                "Maintenance",
                "Support",
            ],
            "revenue_streams": [
                "Abonnement mensuel",
                "Pilote payant",
                "Frais d’installation",
            ],
            "pricing_strategy": "Valider le prix avec des clients pilotes avant le passage à l’échelle.",
            "break_even_analysis": "Le seuil de rentabilité reste indicatif sans données réelles d’usage et de paiement.",
            "funding_needs": "Le financement doit couvrir le MVP, l’hébergement et les premiers pilotes.",
            "assumptions": [
                "Le MVP doit être validé avec de vrais utilisateurs.",
                "La volonté de payer n’est pas encore prouvée.",
            ],
            "financial_risks": [
                "Sensibilité au prix",
                "Faible conversion vers le plan payant",
                "Coût d’acquisition non validé",
            ],
            "recommended_kpis": [
                "Clients pilotes",
                "Taux de conversion payante",
                "Revenu mensuel par client",
            ],
            "roi_outlook": "Perspective ROI prudente jusqu’à collecte de données réelles de pilote.",
            "financial_note": "Les chiffres financiers doivent être confirmés manuellement.",
            "financial_risk_level": "medium",
            "confidence_level": "low",
            "manual_review_required": True,
            "fallback_used": True,
            "error_handled": True,
            "context_locked": True,
            "output_language": output_language,
        }

    # ========================================================
    # Helpers
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

        return ", ".join(items[:5])

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

    def _normalize(self, value: Any) -> str:
        text = str(value or "").lower()
        text = text.replace("’", "'")
        text = re.sub(r"\s+", " ", text).strip()

        return text

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
