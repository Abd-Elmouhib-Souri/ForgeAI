# ============================================================
# backend/app/agents/swot_agent.py
# ============================================================
#
# SWOTAgent V5.0
# Deterministic + Context-Locked + Language-Locked
#
# Objectifs :
# - supprimer l'appel LLM pour SWOT ;
# - économiser les quotas Gemini/Groq ;
# - empêcher les anciennes contaminations de démo ;
# - produire un SWOT professionnel, stable et lié au projet réel ;
# - respecter output_language fr/en ;
# - ne jamais casser le pipeline Startup Evaluator ;
# - garder les champs compatibles avec le rapport actuel.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class SWOTAgent:
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
            result = self._build_swot(
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
    # SWOT deterministic builder
    # ========================================================

    def _build_swot(
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
            strengths = [
                f"{title} addresses a concrete operational problem for {target_users}.",
                f"The project is positioned in a defined sector: {sector}.",
                f"The first market can be tested in {region} before wider expansion.",
                f"The MVP can stay focused on {mvp_scope} instead of becoming a complex platform too early.",
                "The product can create measurable value if it reduces manual work, improves tracking, or saves time for the first users.",
            ]

            weaknesses = [
                "The first target segment may still be too broad and should be narrowed before scaling.",
                "Willingness to pay is not yet proven through direct interviews or paid pilots.",
                "Adoption may be slow if users are already comfortable with manual or free alternatives.",
                "The MVP may become overloaded if advanced features are added before validating the core workflow.",
                "The project still needs clear proof that the problem is frequent, painful, and urgent enough for the target users.",
            ]

            opportunities = [
                f"Interview {target_users} in {region} to validate the pain level and adoption barriers.",
                "Launch a small pilot focused on the most repeated and painful workflow.",
                f"Position {title} as a specialized solution for {sector}, instead of a generic digital platform.",
                "Use pilot results to identify the strongest paid feature and the most convincing value proposition.",
                "Build early credibility through measurable outcomes such as time saved, better organization, or fewer manual errors.",
            ]

            threats = [
                "Users may continue using spreadsheets, messaging apps, paper processes, or informal tools if the value is not immediate.",
                "Generic international tools may cover part of the need with more mature products.",
                "Price sensitivity in the first market may limit subscription conversion.",
                "A weak onboarding experience may prevent non-technical users from adopting the product.",
                "Competitors can copy the visible features if the product does not build strong customer relationships and workflow depth.",
            ]

            strategic_recommendations = [
                "Reduce the first MVP to one core user segment and one measurable promise.",
                "Run 10 to 20 interviews before adding advanced features.",
                "Test a pilot with real users and measure weekly usage.",
                "Validate willingness to pay before relying on subscription revenue assumptions.",
                "Compare the project against the real alternatives already used by the target users.",
                "Use the first pilot to refine onboarding, pricing, and the main workflow.",
            ]

            summary = (
                f"The SWOT analysis for {title} shows a realistic opportunity in {region}, "
                f"especially if the MVP stays focused on {target_users} and solves the core problem: {problem}. "
                "The main risk is not technical execution alone, but proving urgency, adoption, and willingness to pay."
            )

            strategic_position = (
                f"{title} should be positioned as a focused, practical solution for {target_users} in {sector}, "
                "not as a broad generic platform."
            )

            go_no_go_note = (
                "Go forward only if interviews and pilots confirm repeated pain, active usage, and willingness to pay."
            )

        else:
            strengths = [
                f"{title} répond à un problème opérationnel concret pour {target_users}.",
                f"Le projet est positionné dans un secteur défini : {sector}.",
                f"Le premier marché peut être testé en {region} avant une expansion plus large.",
                f"Le MVP peut rester concentré sur {mvp_scope} au lieu de devenir trop tôt une plateforme complexe.",
                "Le produit peut créer une valeur mesurable s’il réduit le travail manuel, améliore le suivi ou fait gagner du temps aux premiers utilisateurs.",
            ]

            weaknesses = [
                "Le premier segment cible peut encore être trop large et doit être réduit avant le passage à l’échelle.",
                "La volonté de payer n’est pas encore prouvée par des entretiens directs ou des pilotes payants.",
                "L’adoption peut être lente si les utilisateurs sont déjà habitués à des alternatives manuelles ou gratuites.",
                "Le MVP peut devenir trop chargé si des fonctionnalités avancées sont ajoutées avant validation du flux principal.",
                "Le projet doit encore prouver que le problème est fréquent, douloureux et assez urgent pour les utilisateurs ciblés.",
            ]

            opportunities = [
                f"Interroger {target_users} en {region} pour valider le niveau de douleur et les freins d’adoption.",
                "Lancer un petit pilote centré sur le flux le plus répété et le plus douloureux.",
                f"Positionner {title} comme une solution spécialisée pour {sector}, et non comme une plateforme numérique générique.",
                "Utiliser les résultats du pilote pour identifier la fonctionnalité payante la plus forte et la proposition de valeur la plus convaincante.",
                "Construire une crédibilité initiale avec des résultats mesurables : temps gagné, meilleure organisation ou réduction des erreurs manuelles.",
            ]

            threats = [
                "Les utilisateurs peuvent continuer avec des tableurs, messageries, papiers ou outils informels si la valeur n’est pas immédiate.",
                "Des outils internationaux génériques peuvent couvrir une partie du besoin avec des produits plus matures.",
                "La sensibilité au prix sur le premier marché peut limiter la conversion par abonnement.",
                "Un onboarding faible peut empêcher les utilisateurs non techniques d’adopter le produit.",
                "Des concurrents peuvent copier les fonctionnalités visibles si le produit ne construit pas une relation client forte et une vraie profondeur métier.",
            ]

            strategic_recommendations = [
                "Réduire le premier MVP à un segment utilisateur principal et une promesse mesurable.",
                "Faire 10 à 20 entretiens avant d’ajouter des fonctionnalités avancées.",
                "Tester un pilote avec de vrais utilisateurs et mesurer l’usage hebdomadaire.",
                "Valider la volonté de payer avant de baser le modèle sur des hypothèses d’abonnement.",
                "Comparer le projet aux alternatives réellement utilisées par les utilisateurs ciblés.",
                "Utiliser le premier pilote pour améliorer l’onboarding, le prix et le flux principal.",
            ]

            summary = (
                f"L’analyse SWOT de {title} montre une opportunité réaliste en {region}, "
                f"surtout si le MVP reste concentré sur {target_users} et résout le problème central : {problem}. "
                "Le risque principal n’est pas seulement technique : il faut surtout prouver l’urgence, l’adoption et la volonté de payer."
            )

            strategic_position = (
                f"{title} doit être positionné comme une solution pratique et spécialisée pour {target_users} dans {sector}, "
                "et non comme une plateforme générique trop large."
            )

            go_no_go_note = (
                "Continuer seulement si les entretiens et pilotes confirment une douleur répétée, un usage actif et une volonté de payer."
            )

        strengths = self._unique(strengths)
        weaknesses = self._unique(weaknesses)
        opportunities = self._unique(opportunities)
        threats = self._unique(threats)
        strategic_recommendations = self._unique(strategic_recommendations)

        return {
            "format": "swot_v5_context_locked_deterministic",
            "status": "completed",
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
            "strategic_recommendations": strategic_recommendations,
            "swot_matrix": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "opportunities": opportunities,
                "threats": threats,
            },
            "strategic_position": strategic_position,
            "go_no_go_note": go_no_go_note,
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

        sanitized.setdefault("format", "swot_v5_context_locked_deterministic")
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
            return {
                "format": "swot_v5_emergency_fallback",
                "status": "completed",
                "summary": "SWOT analysis completed with a safe fallback. The project should be validated through interviews, a narrow MVP and pilot usage.",
                "strengths": [
                    "The project addresses a practical user problem.",
                    "The MVP can be reduced to one core workflow.",
                    "The idea can be tested with a small pilot.",
                ],
                "weaknesses": [
                    "The target segment may still be too broad.",
                    "Willingness to pay is not yet proven.",
                    "The product needs field validation before scaling.",
                ],
                "opportunities": [
                    "Interview target users.",
                    "Launch a small pilot.",
                    "Measure usage and willingness to pay.",
                ],
                "threats": [
                    "Users may keep existing alternatives.",
                    "Adoption may be slow.",
                    "Price sensitivity may limit conversion.",
                ],
                "strategic_recommendations": [
                    "Reduce the MVP scope.",
                    "Validate the problem with real users.",
                    "Test pricing before scaling.",
                ],
                "swot_matrix": {
                    "strengths": [
                        "The project addresses a practical user problem.",
                        "The MVP can be reduced to one core workflow.",
                        "The idea can be tested with a small pilot.",
                    ],
                    "weaknesses": [
                        "The target segment may still be too broad.",
                        "Willingness to pay is not yet proven.",
                        "The product needs field validation before scaling.",
                    ],
                    "opportunities": [
                        "Interview target users.",
                        "Launch a small pilot.",
                        "Measure usage and willingness to pay.",
                    ],
                    "threats": [
                        "Users may keep existing alternatives.",
                        "Adoption may be slow.",
                        "Price sensitivity may limit conversion.",
                    ],
                },
                "risk_level": "medium",
                "confidence_level": "low",
                "manual_review_required": True,
                "fallback_used": True,
                "error_handled": True,
                "context_locked": True,
                "output_language": output_language,
            }

        return {
            "format": "swot_v5_emergency_fallback",
            "status": "completed",
            "summary": "Analyse SWOT complétée avec un fallback sécurisé. Le projet doit être validé par des entretiens, un MVP réduit et un pilote réel.",
            "strengths": [
                "Le projet répond à un problème utilisateur pratique.",
                "Le MVP peut être réduit à un flux principal.",
                "L’idée peut être testée avec un petit pilote.",
            ],
            "weaknesses": [
                "Le segment cible peut encore être trop large.",
                "La volonté de payer n’est pas encore prouvée.",
                "Le produit doit être validé sur le terrain avant le passage à l’échelle.",
            ],
            "opportunities": [
                "Interroger les utilisateurs ciblés.",
                "Lancer un petit pilote.",
                "Mesurer l’usage et la volonté de payer.",
            ],
            "threats": [
                "Les utilisateurs peuvent garder leurs alternatives actuelles.",
                "L’adoption peut être lente.",
                "La sensibilité au prix peut limiter la conversion.",
            ],
            "strategic_recommendations": [
                "Réduire le périmètre du MVP.",
                "Valider le problème avec de vrais utilisateurs.",
                "Tester le prix avant le passage à l’échelle.",
            ],
            "swot_matrix": {
                "strengths": [
                    "Le projet répond à un problème utilisateur pratique.",
                    "Le MVP peut être réduit à un flux principal.",
                    "L’idée peut être testée avec un petit pilote.",
                ],
                "weaknesses": [
                    "Le segment cible peut encore être trop large.",
                    "La volonté de payer n’est pas encore prouvée.",
                    "Le produit doit être validé sur le terrain avant le passage à l’échelle.",
                ],
                "opportunities": [
                    "Interroger les utilisateurs ciblés.",
                    "Lancer un petit pilote.",
                    "Mesurer l’usage et la volonté de payer.",
                ],
                "threats": [
                    "Les utilisateurs peuvent garder leurs alternatives actuelles.",
                    "L’adoption peut être lente.",
                    "La sensibilité au prix peut limiter la conversion.",
                ],
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
