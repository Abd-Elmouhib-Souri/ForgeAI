# ============================================================
# backend/app/agents/persona_builder_agent.py
# ============================================================
#
# PersonaBuilderAgent V5.0
# Professional Personas + Context-Locked + Language-Locked
#
# Objectifs :
# - personas professionnels, utiles et non génériques ;
# - aucun appel LLM ;
# - liés uniquement au projet utilisateur ;
# - respect output_language fr/en ;
# - compatible avec analysis_data existant ;
# - éviter les anciens secteurs de démo ;
# - ne jamais casser le pipeline Startup Evaluator.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class PersonaBuilderAgent:
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
            analysis_data = state.get("analysis_data") or {}

            result = self._build_personas(
                context=context,
                analysis_data=analysis_data,
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
    # Persona builder
    # ========================================================

    def _build_personas(
        self,
        *,
        context: Dict[str, str],
        analysis_data: Dict[str, Any],
        output_language: str,
    ) -> Dict[str, Any]:
        title = context["title"]
        sector = context["sector"]
        region = context["region"]
        target_users = context["target_users"]
        problem = context["problem"]
        solution = context["solution"]
        value_proposition = context["value_proposition"]
        business_model = context["business_model"]
        mvp_scope = context["mvp_scope"]

        market_study = self._section(analysis_data, "market_study")
        bmc = self._section(analysis_data, "business_model_canvas")
        financial = self._section(analysis_data, "financial_estimation")

        customer_segments = self._collect_segments(
            context=context,
            market_study=market_study,
            bmc=bmc,
            output_language=output_language,
        )

        revenue_model = self._first_text(
            bmc.get("revenue_streams"),
            financial.get("possible_revenue_streams"),
            financial.get("revenue_streams"),
            business_model,
        )

        if output_language == "en":
            personas = [
                {
                    "id": "primary_operator",
                    "name": self._persona_name_en("Operations Manager", sector),
                    "role": "Primary daily user",
                    "segment": customer_segments[0],
                    "profile": (
                        f"A practical user in {region} who directly manages the daily workflow affected by {problem}. "
                        f"This persona is important because they will use {title} frequently if the MVP saves time and reduces manual work."
                    ),
                    "context": f"Works in or around {sector}, with repeated operational tasks and limited time for complex tools.",
                    "main_pain": problem,
                    "current_alternatives": [
                        "Manual tracking",
                        "Spreadsheets or disconnected files",
                        "Messaging apps and informal coordination",
                        "Existing generic tools that do not fully match the local workflow",
                    ],
                    "expected_value": value_proposition,
                    "adoption_trigger": (
                        f"Adopts {title} if the first MVP proves a fast gain on {mvp_scope} without forcing a complex migration."
                    ),
                    "objections": [
                        "Does not want to learn a complicated new platform.",
                        "Needs proof that the tool saves time from the first week.",
                        "May continue with manual habits if onboarding is weak.",
                    ],
                    "buying_power": "low-to-medium",
                    "decision_power": "medium",
                    "urgency_level": "medium",
                    "success_metrics": [
                        "Less time spent on the repeated workflow",
                        "Better visibility on users, records or tasks",
                        "Fewer manual errors",
                        "Repeated weekly usage",
                    ],
                    "interview_questions": [
                        f"How do you currently handle this problem: {problem}?",
                        "Which part of the workflow wastes the most time?",
                        f"What would make you try {title} for one week?",
                        "What would stop you from using it after the first test?",
                    ],
                },
                {
                    "id": "economic_buyer",
                    "name": self._persona_name_en("Business Owner", sector),
                    "role": "Economic buyer / decision-maker",
                    "segment": customer_segments[1],
                    "profile": (
                        f"A person in {region} who controls budget, validates tools and decides whether {title} is worth paying for."
                    ),
                    "context": f"Responsible for costs, adoption risk and operational results in {sector}.",
                    "main_pain": (
                        f"Needs to justify spending on {title} and prove that it solves a real business problem, not only a technical improvement."
                    ),
                    "current_alternatives": [
                        "Keeping the current manual process",
                        "Using low-cost generic tools",
                        "Postponing digital adoption",
                        "Delegating the problem internally",
                    ],
                    "expected_value": (
                        f"Clear return on value: reduced operational friction, better organization and a credible path to {revenue_model}."
                    ),
                    "adoption_trigger": "Accepts a pilot if the cost is controlled, the onboarding is simple and the expected benefit is measurable.",
                    "objections": [
                        "Unclear return on investment.",
                        "Limited monthly budget.",
                        "Fear of paying for a product that users do not adopt.",
                    ],
                    "buying_power": "medium",
                    "decision_power": "high",
                    "urgency_level": "medium",
                    "success_metrics": [
                        "Pilot usage by real users",
                        "Time saved or administrative load reduced",
                        "Acceptable monthly price",
                        "Low support burden",
                    ],
                    "interview_questions": [
                        "What budget would be acceptable for this type of solution?",
                        "Which proof would convince you to continue after a pilot?",
                        "Who must approve the adoption decision?",
                        "What risk would block payment?",
                    ],
                },
                {
                    "id": "skeptical_adopter",
                    "name": self._persona_name_en("Skeptical User", sector),
                    "role": "Adoption blocker / cautious user",
                    "segment": customer_segments[2],
                    "profile": (
                        f"A potential user who recognizes the problem but is not convinced that a new digital product is necessary."
                    ),
                    "context": f"Uses existing habits in {region} and may resist changing workflow unless the benefit is immediately visible.",
                    "main_pain": problem,
                    "current_alternatives": [
                        "Manual routine",
                        "Paper process",
                        "WhatsApp or email coordination",
                        "Avoiding change until absolutely necessary",
                    ],
                    "expected_value": "A simple, low-risk proof that the product reduces pain without adding more complexity.",
                    "adoption_trigger": "Tries the MVP only if setup is quick, the interface is simple and the first benefit appears immediately.",
                    "objections": [
                        "The problem is annoying but not urgent enough.",
                        "A new tool may create more work.",
                        "The current method is imperfect but familiar.",
                    ],
                    "buying_power": "low",
                    "decision_power": "low-to-medium",
                    "urgency_level": "low-to-medium",
                    "success_metrics": [
                        "Fast first successful action",
                        "No need for long training",
                        "Clear comparison against current method",
                        "Positive feedback after first use",
                    ],
                    "interview_questions": [
                        "Why would you refuse to change your current method?",
                        "What would make the MVP feel simple enough?",
                        "Which feature would you use first?",
                        "What would make you abandon the product?",
                    ],
                },
            ]

            return {
                "format": "persona_builder_v5_context_locked_professional",
                "status": "completed",
                "output_language": "en",
                "context_locked": True,
                "persona_summary": (
                    f"The most relevant personas for {title} are the daily user, the economic buyer and the skeptical adopter. "
                    f"They are all linked to {target_users} in {region}, with the central problem: {problem}."
                ),
                "primary_persona": personas[0],
                "personas": personas,
                "target_segments": customer_segments,
                "buyer_user_difference": (
                    "The daily user feels the workflow pain, while the economic buyer validates budget and adoption risk."
                ),
                "validation_questions": [
                    f"Do {target_users} experience this problem frequently enough: {problem}?",
                    f"Does {title} create a visible benefit during the first MVP test?",
                    "Who pays, who uses, and who blocks adoption?",
                    "What price is acceptable after a successful pilot?",
                    "Which current alternative must the product beat first?",
                ],
                "persona_risks": [
                    "The user and buyer may be different people.",
                    "The first target segment may still be too broad.",
                    "The problem may be real but not urgent enough to trigger payment.",
                    "A weak onboarding experience may block adoption.",
                ],
                "recommended_validation_method": [
                    "Interview at least 5 daily users.",
                    "Interview at least 5 decision-makers.",
                    "Observe the current workflow before proposing features.",
                    "Run a small MVP pilot and measure weekly usage.",
                ],
                "manual_review_required": True,
                "fallback_used": False,
                "error_handled": False,
                "project_context_used": context,
            }

        personas = [
            {
                "id": "primary_operator",
                "name": self._persona_name_fr("Responsable opérationnel", sector),
                "role": "Utilisateur quotidien principal",
                "segment": customer_segments[0],
                "profile": (
                    f"Utilisateur pratique en {region} qui gère directement le flux quotidien touché par le problème : {problem}. "
                    f"Ce persona est important car il utilisera {title} régulièrement si le MVP fait gagner du temps et réduit le travail manuel."
                ),
                "context": f"Travaille dans ou autour de {sector}, avec des tâches répétées et peu de temps pour des outils complexes.",
                "main_pain": problem,
                "current_alternatives": [
                    "Suivi manuel",
                    "Tableurs ou fichiers dispersés",
                    "Messageries et coordination informelle",
                    "Outils génériques qui ne correspondent pas totalement au flux local",
                ],
                "expected_value": value_proposition,
                "adoption_trigger": (
                    f"Adopte {title} si le premier MVP prouve un gain rapide sur {mvp_scope} sans imposer une migration complexe."
                ),
                "objections": [
                    "Ne veut pas apprendre une plateforme compliquée.",
                    "A besoin de preuve que l’outil fait gagner du temps dès la première semaine.",
                    "Peut garder ses habitudes manuelles si l’onboarding est faible.",
                ],
                "buying_power": "faible à moyen",
                "decision_power": "moyen",
                "urgency_level": "moyen",
                "success_metrics": [
                    "Moins de temps passé sur le flux répétitif",
                    "Meilleure visibilité sur les utilisateurs, dossiers ou tâches",
                    "Moins d’erreurs manuelles",
                    "Usage hebdomadaire répété",
                ],
                "interview_questions": [
                    f"Comment gérez-vous aujourd’hui ce problème : {problem} ?",
                    "Quelle partie du flux vous fait perdre le plus de temps ?",
                    f"Qu’est-ce qui vous ferait tester {title} pendant une semaine ?",
                    "Qu’est-ce qui vous ferait arrêter après le premier test ?",
                ],
            },
            {
                "id": "economic_buyer",
                "name": self._persona_name_fr("Décideur économique", sector),
                "role": "Acheteur / décideur",
                "segment": customer_segments[1],
                "profile": (
                    f"Personne en {region} qui contrôle le budget, valide les outils et décide si {title} mérite d’être payé."
                ),
                "context": f"Responsable des coûts, du risque d’adoption et des résultats opérationnels dans {sector}.",
                "main_pain": (
                    f"Doit justifier la dépense liée à {title} et prouver que la solution règle un vrai problème business."
                ),
                "current_alternatives": [
                    "Garder le processus manuel actuel",
                    "Utiliser des outils génériques peu coûteux",
                    "Reporter la digitalisation",
                    "Déléguer le problème en interne",
                ],
                "expected_value": (
                    f"Retour sur valeur clair : moins de friction opérationnelle, meilleure organisation et trajectoire crédible vers {revenue_model}."
                ),
                "adoption_trigger": (
                    "Accepte un pilote si le coût est maîtrisé, l’onboarding simple et le bénéfice attendu mesurable."
                ),
                "objections": [
                    "Retour sur investissement flou.",
                    "Budget mensuel limité.",
                    "Peur de payer pour un produit que les utilisateurs n’adoptent pas.",
                ],
                "buying_power": "moyen",
                "decision_power": "élevé",
                "urgency_level": "moyen",
                "success_metrics": [
                    "Usage du pilote par de vrais utilisateurs",
                    "Temps gagné ou charge administrative réduite",
                    "Prix mensuel acceptable",
                    "Faible besoin de support",
                ],
                "interview_questions": [
                    "Quel budget serait acceptable pour ce type de solution ?",
                    "Quelle preuve vous convaincrait de continuer après un pilote ?",
                    "Qui doit approuver la décision d’adoption ?",
                    "Quel risque bloquerait le paiement ?",
                ],
            },
            {
                "id": "skeptical_adopter",
                "name": self._persona_name_fr("Utilisateur sceptique", sector),
                "role": "Frein d’adoption / utilisateur prudent",
                "segment": customer_segments[2],
                "profile": (
                    "Cible potentielle qui reconnaît le problème mais n’est pas encore convaincue qu’un nouveau produit numérique soit nécessaire."
                ),
                "context": f"Utilise ses habitudes actuelles en {region} et peut refuser le changement si le bénéfice n’est pas immédiat.",
                "main_pain": problem,
                "current_alternatives": [
                    "Routine manuelle",
                    "Processus papier",
                    "Coordination par WhatsApp ou email",
                    "Éviter le changement jusqu’à nécessité forte",
                ],
                "expected_value": "Preuve simple et peu risquée que le produit réduit la douleur sans ajouter de complexité.",
                "adoption_trigger": "Teste le MVP seulement si l’installation est rapide, l’interface simple et le premier bénéfice immédiat.",
                "objections": [
                    "Le problème est gênant mais pas assez urgent.",
                    "Un nouvel outil peut créer plus de travail.",
                    "La méthode actuelle est imparfaite mais familière.",
                ],
                "buying_power": "faible",
                "decision_power": "faible à moyen",
                "urgency_level": "faible à moyen",
                "success_metrics": [
                    "Première action réussie rapidement",
                    "Pas besoin de longue formation",
                    "Comparaison claire avec la méthode actuelle",
                    "Retour positif après la première utilisation",
                ],
                "interview_questions": [
                    "Pourquoi refuseriez-vous de changer votre méthode actuelle ?",
                    "Qu’est-ce qui rendrait le MVP assez simple pour vous ?",
                    "Quelle fonctionnalité utiliseriez-vous en premier ?",
                    "Qu’est-ce qui vous ferait abandonner le produit ?",
                ],
            },
        ]

        return {
            "format": "persona_builder_v5_context_locked_professional",
            "status": "completed",
            "output_language": "fr",
            "context_locked": True,
            "persona_summary": (
                f"Les personas les plus pertinents pour {title} sont l’utilisateur quotidien, le décideur économique "
                f"et l’utilisateur sceptique. Ils sont liés à {target_users} en {region}, avec le problème central : {problem}."
            ),
            "primary_persona": personas[0],
            "personas": personas,
            "target_segments": customer_segments,
            "buyer_user_difference": (
                "L’utilisateur quotidien ressent la douleur opérationnelle, tandis que le décideur économique valide le budget et le risque d’adoption."
            ),
            "validation_questions": [
                f"Est-ce que {target_users} rencontrent ce problème assez souvent : {problem} ?",
                f"Est-ce que {title} crée un bénéfice visible pendant le premier test MVP ?",
                "Qui paie, qui utilise et qui bloque l’adoption ?",
                "Quel prix devient acceptable après un pilote réussi ?",
                "Quelle alternative actuelle le produit doit-il battre en premier ?",
            ],
            "persona_risks": [
                "L’utilisateur et l’acheteur peuvent être deux personnes différentes.",
                "Le premier segment cible peut encore être trop large.",
                "Le problème peut être réel mais pas assez urgent pour déclencher le paiement.",
                "Un onboarding faible peut bloquer l’adoption.",
            ],
            "recommended_validation_method": [
                "Interroger au moins 5 utilisateurs quotidiens.",
                "Interroger au moins 5 décideurs.",
                "Observer le flux actuel avant de proposer des fonctionnalités.",
                "Lancer un petit pilote MVP et mesurer l’usage hebdomadaire.",
            ],
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "project_context_used": context,
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

        bmc = self._section(analysis_data, "business_model_canvas")
        market_study = self._section(analysis_data, "market_study")

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

        target_users = self._first_text(
            structured.get("target_users"),
            project_context.get("target_users"),
            project_context.get("target_market"),
            market_study.get("target_customers"),
            market_study.get("customer_segments"),
            bmc.get("customer_segments"),
            "target users",
        )

        problem = self._safe_text(
            structured.get("problem")
            or structured.get("core_problem")
            or structured.get("main_problem")
            or structured.get("pain_point")
            or project_context.get("problem")
            or project_context.get("core_problem")
            or project_context.get("main_problem"),
            "",
        )

        if not problem:
            problem = self._extract_problem_from_description(description)

        solution = self._safe_text(
            structured.get("solution")
            or structured.get("solution_type")
            or structured.get("value_proposition")
            or project_context.get("solution")
            or project_context.get("solution_type"),
            "",
        )

        if not solution:
            solution = self._first_text(
                bmc.get("value_propositions"),
                bmc.get("value_proposition"),
                analysis_data.get("summary"),
                description,
                "the proposed solution",
            )

        value_proposition = self._first_text(
            bmc.get("value_propositions"),
            bmc.get("value_proposition"),
            structured.get("value_proposition"),
            project_context.get("value_proposition"),
            solution,
            description,
        )

        business_model = self._first_text(
            structured.get("business_model"),
            project_context.get("business_model"),
            bmc.get("revenue_streams"),
            "subscription or pilot-based business model",
        )

        mvp_scope = self._first_text(
            structured.get("mvp_scope"),
            project_context.get("mvp_scope"),
            analysis_data.get("mvp_scope"),
            "a reduced MVP focused on the core workflow",
        )

        context = {
            "title": title,
            "description": description,
            "sector": sector,
            "region": region,
            "target_users": target_users,
            "problem": problem or "the main operational problem described by the project",
            "solution": solution,
            "value_proposition": value_proposition,
            "business_model": business_model,
            "mvp_scope": mvp_scope,
        }

        allowed_context = self._allowed_context(context)

        return {
            key: self._sanitize_text(value, allowed_context=allowed_context)
            for key, value in context.items()
        }

    # ========================================================
    # Segment extraction
    # ========================================================

    def _collect_segments(
        self,
        *,
        context: Dict[str, str],
        market_study: Dict[str, Any],
        bmc: Dict[str, Any],
        output_language: str,
    ) -> List[str]:
        raw_segments: List[str] = []

        raw_segments.extend(self._safe_list(market_study.get("target_customers")))
        raw_segments.extend(self._safe_list(market_study.get("customer_segments")))
        raw_segments.extend(self._safe_list(bmc.get("customer_segments")))
        raw_segments.extend(self._safe_list(context.get("target_users")))

        segments = self._unique([item for item in raw_segments if item])

        if output_language == "en":
            defaults = [
                f"Small organizations or professionals in {context['sector']} in {context['region']}",
                f"Decision-makers serving {context['target_users']}",
                f"Cautious users currently affected by {context['problem']}",
            ]
        else:
            defaults = [
                f"Petites organisations ou professionnels dans {context['sector']} en {context['region']}",
                f"Décideurs qui servent {context['target_users']}",
                f"Utilisateurs prudents actuellement touchés par {context['problem']}",
            ]

        for item in defaults:
            if len(segments) >= 3:
                break
            segments.append(item)

        return self._unique(segments)[:3]

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

        sanitized.setdefault("format", "persona_builder_v5_context_locked_professional")
        sanitized.setdefault("status", "completed")
        sanitized.setdefault("context_locked", True)
        sanitized.setdefault("output_language", output_language)
        sanitized.setdefault("manual_review_required", True)
        sanitized.setdefault("fallback_used", False)
        sanitized.setdefault("error_handled", False)

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

        return text[:1800].strip()

    def _allowed_context(self, context: Dict[str, str]) -> str:
        return self._normalize(
            " ".join(str(value or "") for value in context.values())
        )

    # ========================================================
    # Fallback
    # ========================================================

    def _fallback(self, output_language: str) -> Dict[str, Any]:
        if output_language == "en":
            personas = [
                {
                    "id": "primary_operator",
                    "name": "Primary operational user",
                    "role": "Daily user",
                    "segment": "First target users",
                    "profile": "User who directly feels the workflow problem.",
                    "main_pain": "Manual or inefficient workflow.",
                    "expected_value": "A simple MVP that saves time and reduces operational friction.",
                    "adoption_trigger": "Adopts if the first test creates visible value.",
                    "objections": ["Budget", "Complexity", "Lack of proof"],
                }
            ]

            return {
                "format": "persona_builder_v5_emergency_fallback",
                "status": "completed",
                "output_language": "en",
                "context_locked": True,
                "persona_summary": "Personas completed with a safe fallback.",
                "primary_persona": personas[0],
                "personas": personas,
                "target_segments": ["First target users"],
                "validation_questions": [
                    "Who uses the product daily?",
                    "Who pays for it?",
                    "What blocks adoption?",
                ],
                "persona_risks": [
                    "The target may be too broad.",
                    "The buyer and user may differ.",
                ],
                "manual_review_required": True,
                "fallback_used": True,
                "error_handled": True,
            }

        personas = [
            {
                "id": "primary_operator",
                "name": "Utilisateur opérationnel principal",
                "role": "Utilisateur quotidien",
                "segment": "Premiers utilisateurs ciblés",
                "profile": "Utilisateur qui ressent directement le problème de flux de travail.",
                "main_pain": "Flux manuel ou inefficace.",
                "expected_value": "Un MVP simple qui fait gagner du temps et réduit la friction opérationnelle.",
                "adoption_trigger": "Adopte si le premier test crée une valeur visible.",
                "objections": ["Budget", "Complexité", "Manque de preuve"],
            }
        ]

        return {
            "format": "persona_builder_v5_emergency_fallback",
            "status": "completed",
            "output_language": "fr",
            "context_locked": True,
            "persona_summary": "Personas complétés avec un fallback sécurisé.",
            "primary_persona": personas[0],
            "personas": personas,
            "target_segments": ["Premiers utilisateurs ciblés"],
            "validation_questions": [
                "Qui utilise le produit chaque jour ?",
                "Qui paie ?",
                "Qu’est-ce qui bloque l’adoption ?",
            ],
            "persona_risks": [
                "La cible peut être trop large.",
                "L’acheteur et l’utilisateur peuvent être différents.",
            ],
            "manual_review_required": True,
            "fallback_used": True,
            "error_handled": True,
        }

    # ========================================================
    # Helpers
    # ========================================================

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

        clean = str(value).strip()
        return clean or fallback

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            result: List[str] = []
            for item in value:
                result.extend(self._safe_list(item))
            return self._unique(result)

        if isinstance(value, dict):
            result: List[str] = []

            priority_keys = [
                "segment",
                "name",
                "title",
                "description",
                "value",
                "label",
                "text",
                "summary",
            ]

            for key in priority_keys:
                if key in value:
                    result.extend(self._safe_list(value.get(key)))

            if not result:
                for item in value.values():
                    result.extend(self._safe_list(item))

            return self._unique(result)

        clean = re.sub(r"\s+", " ", str(value or "").strip())

        if not clean:
            return []

        return [clean[:1000]]

    def _extract_problem_from_description(self, description: str) -> str:
        clean = self._safe_text(description)

        if not clean:
            return "the main operational problem described by the project"

        sentences = re.split(r"(?<=[.!?])\s+", clean)

        if sentences:
            return sentences[0][:300]

        return clean[:300]

    def _persona_name_en(self, base: str, sector: str) -> str:
        sector_clean = self._safe_text(sector, "Target Sector")

        if sector_clean.lower() in {"target sector", "sector"}:
            return base

        return f"{base} — {sector_clean}"

    def _persona_name_fr(self, base: str, sector: str) -> str:
        sector_clean = self._safe_text(sector, "secteur cible")

        if sector_clean.lower() in {"target sector", "secteur cible", "sector"}:
            return base

        return f"{base} — {sector_clean}"

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
            clean = re.sub(r"\s+", " ", str(value or "").strip())

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result
