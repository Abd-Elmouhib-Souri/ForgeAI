# ============================================================
# backend/app/agents/bmc_agent.py
# ============================================================
#
# BMCAgent V5.0
# Deterministic + Context-Locked + Language-Locked
#
# Objectifs :
# - supprimer l'appel IA pour le Business Model Canvas ;
# - réduire les quotas Gemini/Groq ;
# - empêcher les anciennes contaminations de démo ;
# - produire un BMC professionnel, stable et lié au projet réel ;
# - respecter output_language fr/en ;
# - ne jamais casser le pipeline Startup Evaluator ;
# - garder les champs compatibles avec le rapport actuel.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class BMCAgent:
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

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output_language = normalize_output_language(state.get("output_language", "fr"))

        try:
            context = self._context(state)

            result = self._build_bmc(
                context=context,
                output_language=output_language,
            )

            return self._final_public_sanitize(
                data=result,
                context=context,
                output_language=output_language,
            )

        except Exception:
            return self._fallback(output_language)

    # ========================================================
    # Deterministic BMC builder
    # ========================================================

    def _build_bmc(
        self,
        *,
        context: Dict[str, str],
        output_language: str,
    ) -> Dict[str, Any]:
        title = context["title"]
        sector = context["sector"]
        region = context["region"]
        target_users = context["target_users"]
        problem = context["problem"]
        solution = context["solution"]
        business_model = context["business_model"]
        mvp_scope = context["mvp_scope"]

        if output_language == "en":
            customer_segments = [
                f"Primary early adopters: {target_users}.",
                f"Small organizations or professionals in {region} that repeatedly face the problem: {problem}.",
                "Decision-makers who directly feel the operational cost of the current workflow.",
                "Users willing to test a focused MVP before adopting a full platform.",
            ]

            value_propositions = [
                f"{title} helps {target_users} solve a concrete operational problem: {problem}.",
                "The product reduces manual work, fragmented tracking and repetitive coordination tasks.",
                "The MVP focuses on one practical workflow instead of a broad generic platform.",
                f"The solution is specialized for {sector} and adapted to the first market in {region}.",
            ]

            channels = [
                "Direct outreach to the first target organizations.",
                "Field interviews with decision-makers and operational users.",
                "Pilot partnerships with a small number of early adopters.",
                "Referrals from satisfied pilot users.",
                "Simple demo page explaining the core workflow and measurable benefit.",
            ]

            customer_relationships = [
                "High-touch onboarding during the first pilot phase.",
                "Direct feedback loops with early users.",
                "Support focused on helping users complete the core workflow quickly.",
                "Continuous improvement based on usage and adoption data.",
            ]

            revenue_streams = [
                "Pilot fee for early validation when possible.",
                "Monthly subscription adapted to the size of the target user.",
                "Tiered pricing based on usage, number of users, or active records.",
                "Optional setup or onboarding fee for organizations that need support.",
            ]

            key_resources = [
                "A simple and reliable MVP covering the core workflow.",
                "User feedback from interviews and pilots.",
                "Clear understanding of the target segment and its budget limits.",
                "Product documentation and onboarding material.",
                "Basic analytics to measure usage, retention and workflow completion.",
            ]

            key_activities = [
                "Validate the problem with real target users.",
                "Build and maintain the MVP scope.",
                "Run pilots and collect usage feedback.",
                "Improve onboarding and reduce friction.",
                "Test pricing and willingness to pay.",
            ]

            key_partnerships = [
                f"Pilot partners in {region}.",
                f"Professionals or organizations active in {sector}.",
                "Early adopters who can provide feedback and referrals.",
                "Technical partners only if they reduce delivery cost or speed up validation.",
            ]

            cost_structure = [
                "MVP development and maintenance.",
                "Hosting, database and basic infrastructure.",
                "Customer support and onboarding during pilots.",
                "Prospection, interviews and pilot acquisition.",
                "Product improvements based on real user feedback.",
            ]

            summary = (
                f"The Business Model Canvas for {title} should remain focused on a narrow first segment: {target_users}. "
                f"The model is strongest if the MVP proves that solving '{problem}' creates enough value to support {business_model}."
            )

            business_model_note = (
                f"The recommended model is to start with pilots, then move toward {business_model} only after adoption and willingness to pay are validated."
            )

            validation_priorities = [
                "Confirm that the target users face the problem frequently.",
                "Confirm that the MVP scope is enough to create value.",
                "Measure weekly usage during a pilot.",
                "Test willingness to pay with real pricing conversations.",
                "Identify the smallest paid feature that users understand immediately.",
            ]

            risk_note = (
                "The main business risk is building too many features before proving that the first segment will adopt and pay."
            )

        else:
            customer_segments = [
                f"Premiers adoptants principaux : {target_users}.",
                f"Petites organisations ou professionnels en {region} qui rencontrent souvent ce problème : {problem}.",
                "Décideurs qui ressentent directement le coût opérationnel du flux actuel.",
                "Utilisateurs prêts à tester un MVP ciblé avant d’adopter une plateforme complète.",
            ]

            value_propositions = [
                f"{title} aide {target_users} à résoudre un problème opérationnel concret : {problem}.",
                "Le produit réduit le travail manuel, le suivi dispersé et les tâches répétitives de coordination.",
                "Le MVP se concentre sur un flux pratique au lieu d’une plateforme générique trop large.",
                f"La solution est spécialisée pour {sector} et adaptée au premier marché en {region}.",
            ]

            channels = [
                "Prospection directe auprès des premières organisations ciblées.",
                "Entretiens terrain avec les décideurs et utilisateurs opérationnels.",
                "Partenariats pilotes avec un petit nombre de premiers adoptants.",
                "Recommandations par les premiers utilisateurs satisfaits.",
                "Page de démonstration simple expliquant le flux principal et le bénéfice mesurable.",
            ]

            customer_relationships = [
                "Onboarding accompagné pendant la première phase pilote.",
                "Boucles de feedback directes avec les premiers utilisateurs.",
                "Support centré sur la réussite rapide du flux principal.",
                "Amélioration continue basée sur l’usage réel et les données d’adoption.",
            ]

            revenue_streams = [
                "Frais de pilote lorsque c’est possible.",
                "Abonnement mensuel adapté à la taille de la cible.",
                "Tarification par niveau selon l’usage, le nombre d’utilisateurs ou les dossiers actifs.",
                "Frais optionnels de configuration ou d’accompagnement pour les organisations qui en ont besoin.",
            ]

            key_resources = [
                "Un MVP simple et fiable couvrant le flux principal.",
                "Feedback utilisateur provenant des entretiens et pilotes.",
                "Compréhension claire du segment cible et de ses limites budgétaires.",
                "Documentation produit et support d’onboarding.",
                "Analytics basiques pour mesurer l’usage, la rétention et la complétion du flux.",
            ]

            key_activities = [
                "Valider le problème avec de vrais utilisateurs ciblés.",
                "Construire et maintenir le périmètre MVP.",
                "Lancer des pilotes et collecter les retours d’usage.",
                "Améliorer l’onboarding et réduire les frictions.",
                "Tester le prix et la volonté de payer.",
            ]

            key_partnerships = [
                f"Partenaires pilotes en {region}.",
                f"Professionnels ou organisations actifs dans {sector}.",
                "Premiers adoptants capables de donner du feedback et des recommandations.",
                "Partenaires techniques seulement s’ils réduisent le coût ou accélèrent la validation.",
            ]

            cost_structure = [
                "Développement et maintenance du MVP.",
                "Hébergement, base de données et infrastructure basique.",
                "Support client et onboarding pendant les pilotes.",
                "Prospection, entretiens et acquisition de pilotes.",
                "Améliorations produit basées sur les retours utilisateurs réels.",
            ]

            summary = (
                f"Le Business Model Canvas de {title} doit rester concentré sur un premier segment étroit : {target_users}. "
                f"Le modèle devient solide si le MVP prouve que résoudre « {problem} » crée assez de valeur pour soutenir {business_model}."
            )

            business_model_note = (
                f"Le modèle recommandé est de commencer par des pilotes, puis d’évoluer vers {business_model} seulement après validation de l’adoption et de la volonté de payer."
            )

            validation_priorities = [
                "Confirmer que les utilisateurs ciblés rencontrent souvent le problème.",
                "Confirmer que le périmètre MVP suffit à créer de la valeur.",
                "Mesurer l’usage hebdomadaire pendant un pilote.",
                "Tester la volonté de payer avec de vraies discussions de prix.",
                "Identifier la plus petite fonctionnalité payante immédiatement compréhensible.",
            ]

            risk_note = (
                "Le principal risque business est de construire trop de fonctionnalités avant de prouver que le premier segment adopte et paie."
            )

        customer_segments = self._unique(customer_segments)
        value_propositions = self._unique(value_propositions)
        channels = self._unique(channels)
        customer_relationships = self._unique(customer_relationships)
        revenue_streams = self._unique(revenue_streams)
        key_resources = self._unique(key_resources)
        key_activities = self._unique(key_activities)
        key_partnerships = self._unique(key_partnerships)
        cost_structure = self._unique(cost_structure)
        validation_priorities = self._unique(validation_priorities)

        return {
            "format": "bmc_v5_context_locked_deterministic",
            "status": "completed",
            "summary": summary,

            # Standard Business Model Canvas blocks
            "customer_segments": customer_segments,
            "value_propositions": value_propositions,
            "channels": channels,
            "customer_relationships": customer_relationships,
            "revenue_streams": revenue_streams,
            "key_resources": key_resources,
            "key_activities": key_activities,
            "key_partnerships": key_partnerships,
            "cost_structure": cost_structure,

            # Aliases compatibles avec différents frontends
            "value_proposition": value_propositions,
            "key_partners": key_partnerships,
            "costs": cost_structure,
            "customers": customer_segments,
            "relationships": customer_relationships,
            "revenues": revenue_streams,

            "business_model_note": business_model_note,
            "validation_priorities": validation_priorities,
            "risk_note": risk_note,

            "canvas": {
                "customer_segments": customer_segments,
                "value_propositions": value_propositions,
                "channels": channels,
                "customer_relationships": customer_relationships,
                "revenue_streams": revenue_streams,
                "key_resources": key_resources,
                "key_activities": key_activities,
                "key_partnerships": key_partnerships,
                "cost_structure": cost_structure,
            },

            "risk_level": "medium",
            "confidence_level": "medium",
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "context_locked": True,
            "output_language": output_language,
            "project_context_used": {
                "title": title,
                "sector": sector,
                "region": region,
                "target_users": target_users,
                "problem": problem,
                "solution": solution,
                "business_model": business_model,
                "mvp_scope": mvp_scope,
            },
        }

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
            "",
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

        problem = self._safe_text(
            structured.get("problem")
            or structured.get("core_problem")
            or structured.get("main_problem")
            or structured.get("pain_point")
            or project_context.get("problem")
            or project_context.get("core_problem")
            or project_context.get("main_problem"),
            "the identified operational problem",
        )

        solution = self._safe_text(
            structured.get("solution")
            or structured.get("solution_type")
            or structured.get("value_proposition")
            or project_context.get("solution")
            or project_context.get("solution_type"),
            "the proposed solution",
        )

        business_model = self._safe_text(
            structured.get("business_model")
            or project_context.get("business_model"),
            "subscription or pilot-based business model",
        )

        mvp_scope = self._safe_text(
            structured.get("mvp_scope")
            or project_context.get("mvp_scope"),
            "a reduced MVP focused on the core workflow",
        )

        context = {
            "title": title,
            "description": description,
            "sector": sector,
            "region": region,
            "target_users": target_users,
            "problem": problem,
            "solution": solution,
            "business_model": business_model,
            "mvp_scope": mvp_scope,
        }

        allowed_context = self._allowed_context(context)

        return {
            key: self._sanitize_text(value, allowed_context=allowed_context)
            for key, value in context.items()
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
        allowed_context = self._allowed_context(context)

        sanitized = self._sanitize_object(
            value=data,
            allowed_context=allowed_context,
        )

        if not isinstance(sanitized, dict):
            return self._fallback(output_language)

        sanitized.setdefault("format", "bmc_v5_context_locked_deterministic")
        sanitized.setdefault("status", "completed")
        sanitized.setdefault("risk_level", "medium")
        sanitized.setdefault("confidence_level", "medium")
        sanitized.setdefault("manual_review_required", True)
        sanitized.setdefault("fallback_used", False)
        sanitized.setdefault("error_handled", False)
        sanitized.setdefault("context_locked", True)
        sanitized.setdefault("output_language", output_language)

        sanitized.pop("internal_error", None)
        sanitized.pop("raw_data_backup", None)
        sanitized.pop("raw_response", None)
        sanitized.pop("debug", None)

        return sanitized

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

    def _allowed_context(self, context: Dict[str, str]) -> str:
        return self._normalize(
            " ".join(str(value or "") for value in context.values())
        )

    # ========================================================
    # Emergency fallback
    # ========================================================

    def _fallback(self, output_language: str) -> Dict[str, Any]:
        if output_language == "en":
            customer_segments = [
                "Early adopters with a repeated operational problem.",
                "Small teams or organizations willing to test a focused MVP.",
            ]
            value_propositions = [
                "A simple product that improves one core workflow.",
                "Reduced manual work and better operational visibility.",
            ]
            channels = [
                "Direct outreach.",
                "Pilot partnerships.",
                "Referrals from early users.",
            ]
            customer_relationships = [
                "Guided onboarding.",
                "Direct feedback loops.",
            ]
            revenue_streams = [
                "Pilot fee.",
                "Monthly subscription after validation.",
            ]
            key_resources = [
                "Focused MVP.",
                "User feedback.",
                "Basic infrastructure.",
            ]
            key_activities = [
                "Problem validation.",
                "MVP development.",
                "Pilot testing.",
            ]
            key_partnerships = [
                "Pilot users.",
                "Relevant local partners.",
            ]
            cost_structure = [
                "Development and maintenance.",
                "Hosting and infrastructure.",
                "Customer support and onboarding.",
            ]

            return {
                "format": "bmc_v5_emergency_fallback",
                "status": "completed",
                "summary": "Business Model Canvas completed with a safe fallback. The project should validate its first segment, MVP scope and willingness to pay before scaling.",
                "customer_segments": customer_segments,
                "value_propositions": value_propositions,
                "channels": channels,
                "customer_relationships": customer_relationships,
                "revenue_streams": revenue_streams,
                "key_resources": key_resources,
                "key_activities": key_activities,
                "key_partnerships": key_partnerships,
                "cost_structure": cost_structure,
                "value_proposition": value_propositions,
                "key_partners": key_partnerships,
                "costs": cost_structure,
                "canvas": {
                    "customer_segments": customer_segments,
                    "value_propositions": value_propositions,
                    "channels": channels,
                    "customer_relationships": customer_relationships,
                    "revenue_streams": revenue_streams,
                    "key_resources": key_resources,
                    "key_activities": key_activities,
                    "key_partnerships": key_partnerships,
                    "cost_structure": cost_structure,
                },
                "risk_level": "medium",
                "confidence_level": "low",
                "manual_review_required": True,
                "fallback_used": True,
                "error_handled": True,
                "context_locked": True,
                "output_language": output_language,
            }

        customer_segments = [
            "Premiers adoptants avec un problème opérationnel répété.",
            "Petites équipes ou organisations prêtes à tester un MVP ciblé.",
        ]
        value_propositions = [
            "Un produit simple qui améliore un flux principal.",
            "Réduction du travail manuel et meilleure visibilité opérationnelle.",
        ]
        channels = [
            "Prospection directe.",
            "Partenariats pilotes.",
            "Recommandations par les premiers utilisateurs.",
        ]
        customer_relationships = [
            "Onboarding accompagné.",
            "Boucles de feedback directes.",
        ]
        revenue_streams = [
            "Frais de pilote.",
            "Abonnement mensuel après validation.",
        ]
        key_resources = [
            "MVP ciblé.",
            "Feedback utilisateur.",
            "Infrastructure basique.",
        ]
        key_activities = [
            "Validation du problème.",
            "Développement du MVP.",
            "Tests pilotes.",
        ]
        key_partnerships = [
            "Utilisateurs pilotes.",
            "Partenaires locaux pertinents.",
        ]
        cost_structure = [
            "Développement et maintenance.",
            "Hébergement et infrastructure.",
            "Support client et onboarding.",
        ]

        return {
            "format": "bmc_v5_emergency_fallback",
            "status": "completed",
            "summary": "Business Model Canvas complété avec un fallback sécurisé. Le projet doit valider son premier segment, son périmètre MVP et la volonté de payer avant le passage à l’échelle.",
            "customer_segments": customer_segments,
            "value_propositions": value_propositions,
            "channels": channels,
            "customer_relationships": customer_relationships,
            "revenue_streams": revenue_streams,
            "key_resources": key_resources,
            "key_activities": key_activities,
            "key_partnerships": key_partnerships,
            "cost_structure": cost_structure,
            "value_proposition": value_propositions,
            "key_partners": key_partnerships,
            "costs": cost_structure,
            "canvas": {
                "customer_segments": customer_segments,
                "value_propositions": value_propositions,
                "channels": channels,
                "customer_relationships": customer_relationships,
                "revenue_streams": revenue_streams,
                "key_resources": key_resources,
                "key_activities": key_activities,
                "key_partnerships": key_partnerships,
                "cost_structure": cost_structure,
            },
            "risk_level": "medium",
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

        return ", ".join(items[:6])

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
