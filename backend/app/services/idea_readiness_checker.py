# ============================================================
# backend/app/services/idea_readiness_checker.py
# ============================================================
#
# IdeaReadinessChecker V1 — Context Confidence Score
#
# Objectifs :
# - analyser la clarté de l'idée avant les agents lourds ;
# - détecter les champs manquants ;
# - détecter les champs ambigus ;
# - produire un score de confiance contextuelle ;
# - générer des questions guidées ;
# - générer des checklists à afficher côté frontend ;
# - fournir des hypothèses prudentes si certaines informations manquent ;
# - ne jamais appeler de LLM : service déterministe, rapide et stable.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.services.domain_integrity_guard import normalize_output_language


class IdeaReadinessChecker:
    MIN_READY_SCORE = 0.75

    GENERIC_SECTORS = {
        "",
        "non spécifié",
        "non specifie",
        "not specified",
        "unknown",
        "general",
        "startup",
        "business",
        "tech",
        "technology",
        "saas",
        "app",
        "application",
    }

    GENERIC_REGIONS = {
        "",
        "global",
        "international",
        "worldwide",
        "unknown",
        "non spécifié",
        "non specifie",
        "not specified",
    }

    PROBLEM_HINTS = {
        "problem",
        "problème",
        "probleme",
        "pain",
        "struggle",
        "difficult",
        "difficile",
        "hard",
        "manual",
        "fragmented",
        "scattered",
        "inefficient",
        "inefficace",
        "perte",
        "loss",
        "waste",
        "slow",
        "lent",
        "cost",
        "coût",
        "cout",
        "risk",
        "risque",
        "lack",
        "manque",
        "besoin",
        "need",
    }

    SOLUTION_HINTS = {
        "solution",
        "platform",
        "plateforme",
        "app",
        "application",
        "robot",
        "saas",
        "dashboard",
        "system",
        "système",
        "systeme",
        "tool",
        "outil",
        "helps",
        "aide",
        "automate",
        "automatiser",
        "manage",
        "gérer",
        "gerer",
        "detect",
        "détecter",
        "detecter",
        "create",
        "créer",
        "creer",
        "track",
        "suivre",
    }

    TARGET_HINTS = {
        "users",
        "utilisateurs",
        "clients",
        "target",
        "cible",
        "farmers",
        "agriculteurs",
        "students",
        "étudiants",
        "etudiants",
        "teachers",
        "enseignants",
        "instructors",
        "formateurs",
        "centers",
        "centres",
        "doctors",
        "médecins",
        "medecins",
        "patients",
        "freelance",
        "companies",
        "entreprises",
        "training centers",
        "centres de formation",
    }

    BUSINESS_HINTS = {
        "subscription",
        "abonnement",
        "pricing",
        "price",
        "prix",
        "freemium",
        "commission",
        "paid",
        "pay",
        "payer",
        "revenue",
        "revenu",
        "business model",
        "modèle économique",
        "modele economique",
        "plans",
        "monthly",
        "mensuel",
    }

    MVP_HINTS = {
        "mvp",
        "first version",
        "première version",
        "premiere version",
        "prototype",
        "pilot",
        "pilote",
        "beta",
        "minimum",
        "core features",
        "features",
        "fonctionnalités",
        "fonctionnalites",
    }

    def evaluate(
        self,
        *,
        title: str = "",
        description: str = "",
        industry: str = "",
        target_region: str = "",
        output_language: str = "fr",
        project_context: Dict[str, Any] | None = None,
        analysis_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)
        project_context = project_context or {}
        analysis_data = analysis_data or {}

        title = self._clean_text(title or project_context.get("title") or project_context.get("project_name") or "")
        description = self._clean_text(description or project_context.get("description") or "")
        industry = self._clean_text(industry or project_context.get("industry") or "")
        target_region = self._clean_text(
            target_region
            or project_context.get("market_region")
            or project_context.get("target_region")
            or ""
        )

        text_blob = self._clean_text(
            " ".join(
                [
                    title,
                    description,
                    industry,
                    target_region,
                    self._safe_join(project_context.get("target_users")),
                    self._safe_join(project_context.get("anchor_terms")),
                    self._safe_join(project_context.get("strong_keywords")),
                    self._safe_join(analysis_data.get("target_users")),
                ]
            )
        )

        detected = self._detect_fields(
            title=title,
            description=description,
            industry=industry,
            target_region=target_region,
            text_blob=text_blob,
            project_context=project_context,
        )

        missing_fields, ambiguous_fields = self._field_quality(detected)

        score, scoring_details = self._score(
            detected=detected,
            missing_fields=missing_fields,
            ambiguous_fields=ambiguous_fields,
        )

        ready_for_agents = score >= self.MIN_READY_SCORE

        assumptions = self._assumptions(
            detected=detected,
            missing_fields=missing_fields,
            language=language,
        )

        questions = self._questions(
            missing_fields=missing_fields,
            ambiguous_fields=ambiguous_fields,
            language=language,
        )

        checklist = self._checklist(language=language)

        suggested_options = self._suggested_options(
            detected=detected,
            language=language,
        )

        status = "ready" if ready_for_agents else "needs_clarification"

        recommendation = self._recommendation(
            score=score,
            ready_for_agents=ready_for_agents,
            missing_fields=missing_fields,
            ambiguous_fields=ambiguous_fields,
            language=language,
        )

        return {
            "format": "idea_readiness_v1_context_confidence",
            "status": status,
            "score": score,
            "ready_for_agents": ready_for_agents,
            "threshold": self.MIN_READY_SCORE,
            "detected": detected,
            "missing_fields": missing_fields,
            "ambiguous_fields": ambiguous_fields,
            "assumptions": assumptions,
            "questions": questions,
            "suggested_options": suggested_options,
            "checklist": checklist,
            "scoring_details": scoring_details,
            "recommendation": recommendation,
            "output_language": language,
        }

    # ========================================================
    # Detection
    # ========================================================

    def _detect_fields(
        self,
        *,
        title: str,
        description: str,
        industry: str,
        target_region: str,
        text_blob: str,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        lower_blob = text_blob.lower()

        target_users = self._extract_target_users(
            description=description,
            project_context=project_context,
        )

        problem = self._extract_sentence_by_hints(
            text=description,
            hints=self.PROBLEM_HINTS,
        )

        solution = self._extract_sentence_by_hints(
            text=description,
            hints=self.SOLUTION_HINTS,
        )

        business_model = self._extract_sentence_by_hints(
            text=description,
            hints=self.BUSINESS_HINTS,
        )

        mvp = self._extract_sentence_by_hints(
            text=description,
            hints=self.MVP_HINTS,
        )

        use_case = self._extract_use_case(
            description=description,
            solution=solution,
            project_context=project_context,
        )

        return {
            "project_name": title,
            "description_length": len(description),
            "sector": industry,
            "target_region": target_region,
            "target_users": target_users,
            "problem": problem,
            "solution": solution,
            "main_use_case": use_case,
            "business_model": business_model,
            "mvp_scope": mvp,
            "has_problem_signal": self._contains_any(lower_blob, self.PROBLEM_HINTS),
            "has_solution_signal": self._contains_any(lower_blob, self.SOLUTION_HINTS),
            "has_target_signal": self._contains_any(lower_blob, self.TARGET_HINTS) or bool(target_users),
            "has_business_signal": self._contains_any(lower_blob, self.BUSINESS_HINTS),
            "has_mvp_signal": self._contains_any(lower_blob, self.MVP_HINTS),
        }

    def _field_quality(self, detected: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        missing_fields: List[str] = []
        ambiguous_fields: List[str] = []

        project_name = self._clean_text(detected.get("project_name"))
        sector = self._clean_text(detected.get("sector")).lower()
        region = self._clean_text(detected.get("target_region")).lower()
        target_users = detected.get("target_users") or []
        problem = self._clean_text(detected.get("problem"))
        solution = self._clean_text(detected.get("solution"))
        business_model = self._clean_text(detected.get("business_model"))
        mvp_scope = self._clean_text(detected.get("mvp_scope"))

        if not project_name or len(project_name) < 3:
            missing_fields.append("project_name")

        if not sector or sector in self.GENERIC_SECTORS:
            missing_fields.append("sector")
        elif sector in {"edtech", "hrtech", "healthtech", "agritech", "fintech"}:
            ambiguous_fields.append("sector_detail")

        if not region or region in self.GENERIC_REGIONS:
            ambiguous_fields.append("target_region")

        if not target_users:
            missing_fields.append("target_users")

        if not problem or len(problem) < 30:
            missing_fields.append("problem")

        if not solution or len(solution) < 30:
            missing_fields.append("solution")

        if not business_model:
            ambiguous_fields.append("business_model")

        if not mvp_scope:
            ambiguous_fields.append("mvp_scope")

        return self._unique(missing_fields), self._unique(ambiguous_fields)

    # ========================================================
    # Score
    # ========================================================

    def _score(
        self,
        *,
        detected: Dict[str, Any],
        missing_fields: List[str],
        ambiguous_fields: List[str],
    ) -> Tuple[float, Dict[str, Any]]:
        weights = {
            "project_name": 0.08,
            "description_depth": 0.14,
            "sector": 0.10,
            "target_region": 0.07,
            "target_users": 0.16,
            "problem": 0.18,
            "solution": 0.18,
            "business_model": 0.05,
            "mvp_scope": 0.04,
        }

        details: Dict[str, Any] = {}

        project_name_ok = bool(self._clean_text(detected.get("project_name")))
        description_length = int(detected.get("description_length") or 0)

        sector = self._clean_text(detected.get("sector")).lower()
        region = self._clean_text(detected.get("target_region")).lower()

        details["project_name"] = weights["project_name"] if project_name_ok else 0.0

        if description_length >= 500:
            details["description_depth"] = weights["description_depth"]
        elif description_length >= 250:
            details["description_depth"] = weights["description_depth"] * 0.75
        elif description_length >= 120:
            details["description_depth"] = weights["description_depth"] * 0.45
        else:
            details["description_depth"] = 0.0

        details["sector"] = (
            weights["sector"]
            if sector and sector not in self.GENERIC_SECTORS
            else 0.0
        )

        details["target_region"] = (
            weights["target_region"]
            if region and region not in self.GENERIC_REGIONS
            else weights["target_region"] * 0.35
        )

        details["target_users"] = (
            weights["target_users"]
            if detected.get("target_users")
            else 0.0
        )

        details["problem"] = (
            weights["problem"]
            if detected.get("has_problem_signal") and self._clean_text(detected.get("problem"))
            else 0.0
        )

        details["solution"] = (
            weights["solution"]
            if detected.get("has_solution_signal") and self._clean_text(detected.get("solution"))
            else 0.0
        )

        details["business_model"] = (
            weights["business_model"]
            if detected.get("has_business_signal")
            else weights["business_model"] * 0.25
        )

        details["mvp_scope"] = (
            weights["mvp_scope"]
            if detected.get("has_mvp_signal")
            else weights["mvp_scope"] * 0.25
        )

        raw_score = sum(float(value) for value in details.values())

        penalty = 0.0
        penalty += 0.08 * len(missing_fields)
        penalty += 0.035 * len(ambiguous_fields)

        final_score = max(0.0, min(1.0, raw_score - penalty))

        details["raw_score"] = round(raw_score, 3)
        details["penalty"] = round(penalty, 3)
        details["final_score"] = round(final_score, 3)

        return round(final_score, 2), details

    # ========================================================
    # Questions / checklist / recommendations
    # ========================================================

    def _questions(
        self,
        *,
        missing_fields: List[str],
        ambiguous_fields: List[str],
        language: str,
    ) -> List[str]:
        fr = {
            "project_name": "Quel est le nom du projet ou de la solution ?",
            "sector": "Dans quel secteur principal se situe l’idée ?",
            "target_users": "Qui va utiliser ou payer cette solution en premier ?",
            "problem": "Quel problème précis cette cible rencontre aujourd’hui ?",
            "solution": "Comment votre solution résout-elle ce problème concrètement ?",
            "target_region": "Dans quel pays ou marché voulez-vous commencer ?",
            "business_model": "Comment pensez-vous gagner de l’argent avec cette solution ?",
            "mvp_scope": "Quelle est la première version minimale à construire ?",
            "sector_detail": "Pouvez-vous préciser le sous-secteur exact ou le cas d’usage métier ?",
        }

        en = {
            "project_name": "What is the name of the project or solution?",
            "sector": "What is the main sector of this idea?",
            "target_users": "Who will use or pay for this solution first?",
            "problem": "What exact problem does this target face today?",
            "solution": "How does your solution solve this problem concretely?",
            "target_region": "Which country or market do you want to start with?",
            "business_model": "How do you plan to make money with this solution?",
            "mvp_scope": "What is the minimum first version to build?",
            "sector_detail": "Can you specify the exact sub-sector or business use case?",
        }

        labels = en if language == "en" else fr

        keys = self._unique(missing_fields + ambiguous_fields)

        questions = [labels[key] for key in keys if key in labels]

        return questions[:8]

    def _checklist(self, language: str) -> List[Dict[str, Any]]:
        if language == "en":
            items = [
                ("project_name", "Project name is clear"),
                ("sector", "Sector and sub-sector are clear"),
                ("target_users", "First target users are defined"),
                ("problem", "Main problem is specific"),
                ("solution", "Solution is concrete"),
                ("target_region", "Launch region is defined"),
                ("mvp_scope", "MVP scope is reduced"),
                ("business_model", "Business model is described"),
                ("alternatives", "Current alternatives are mentioned"),
                ("success_metric", "A measurable success metric is defined"),
            ]
        else:
            items = [
                ("project_name", "Le nom du projet est clair"),
                ("sector", "Le secteur et sous-secteur sont clairs"),
                ("target_users", "Les premiers utilisateurs cibles sont définis"),
                ("problem", "Le problème principal est précis"),
                ("solution", "La solution est concrète"),
                ("target_region", "La région de lancement est définie"),
                ("mvp_scope", "Le périmètre MVP est réduit"),
                ("business_model", "Le modèle économique est décrit"),
                ("alternatives", "Les alternatives actuelles sont mentionnées"),
                ("success_metric", "Un indicateur de succès mesurable est défini"),
            ]

        return [
            {
                "key": key,
                "label": label,
                "checked": False,
                "required": key in {
                    "project_name",
                    "sector",
                    "target_users",
                    "problem",
                    "solution",
                },
            }
            for key, label in items
        ]

    def _suggested_options(
        self,
        *,
        detected: Dict[str, Any],
        language: str,
    ) -> Dict[str, List[str]]:
        sector = self._clean_text(detected.get("sector")).lower()

        if language == "en":
            base = {
                "target_region": [
                    "Tunisia",
                    "North Africa",
                    "France",
                    "Europe",
                    "Global",
                ],
                "business_model": [
                    "Monthly subscription",
                    "Freemium",
                    "Commission",
                    "Direct sale",
                    "Rental",
                    "Service-based model",
                    "B2B SaaS",
                ],
                "mvp_scope": [
                    "One target user",
                    "One core feature",
                    "One measurable result",
                    "Manual pilot before automation",
                    "Landing page + interviews",
                    "Clickable prototype",
                ],
            }

            if "edtech" in sector or "hrtech" in sector:
                base["target_users"] = [
                    "Small training centers",
                    "Independent instructors",
                    "Language teachers",
                    "Coding bootcamps",
                    "Professional training providers",
                    "Learners needing certificates",
                ]
            elif "health" in sector or "med" in sector:
                base["target_users"] = [
                    "Patients",
                    "Doctors",
                    "Private clinics",
                    "Medical offices",
                    "Receptionists",
                    "Healthcare administrators",
                ]
            elif "agri" in sector or "robot" in sector:
                base["target_users"] = [
                    "Small greenhouse owners",
                    "Farmers using plastic tunnels",
                    "Agricultural technicians",
                    "Nurseries",
                    "Agricultural cooperatives",
                ]
            else:
                base["target_users"] = [
                    "Small businesses",
                    "Freelancers",
                    "Students",
                    "Professionals",
                    "Local organizations",
                    "End customers",
                ]

            return base

        base = {
            "target_region": [
                "Tunisie",
                "Afrique du Nord",
                "France",
                "Europe",
                "Global",
            ],
            "business_model": [
                "Abonnement mensuel",
                "Freemium",
                "Commission",
                "Vente directe",
                "Location",
                "Service à la demande",
                "SaaS B2B",
            ],
            "mvp_scope": [
                "Une seule cible",
                "Une seule fonctionnalité principale",
                "Un seul résultat mesurable",
                "Pilote manuel avant automatisation",
                "Landing page + interviews",
                "Prototype cliquable",
            ],
        }

        if "edtech" in sector or "hrtech" in sector:
            base["target_users"] = [
                "Petits centres de formation",
                "Formateurs indépendants",
                "Professeurs de langues",
                "Bootcamps de programmation",
                "Organismes de formation professionnelle",
                "Apprenants ayant besoin de certificats",
            ]
        elif "health" in sector or "med" in sector or "santé" in sector or "sante" in sector:
            base["target_users"] = [
                "Patients",
                "Médecins",
                "Cliniques privées",
                "Cabinets médicaux",
                "Secrétaires médicales",
                "Administrateurs de santé",
            ]
        elif "agri" in sector or "robot" in sector:
            base["target_users"] = [
                "Propriétaires de petites serres",
                "Agriculteurs avec tunnels plastiques",
                "Techniciens agricoles",
                "Pépinières",
                "Coopératives agricoles",
            ]
        else:
            base["target_users"] = [
                "Petites entreprises",
                "Freelances",
                "Étudiants",
                "Professionnels",
                "Organisations locales",
                "Clients finaux",
            ]

        return base

    def _assumptions(
        self,
        *,
        detected: Dict[str, Any],
        missing_fields: List[str],
        language: str,
    ) -> List[str]:
        assumptions: List[str] = []

        if "target_region" in missing_fields or not detected.get("target_region"):
            assumptions.append(
                "The launch region is assumed from the project settings and must be confirmed."
                if language == "en"
                else "La région de lancement est supposée depuis les paramètres du projet et doit être confirmée."
            )

        if "business_model" in missing_fields or not detected.get("business_model"):
            assumptions.append(
                "The business model is not fully validated and must be tested with target users."
                if language == "en"
                else "Le modèle économique n’est pas entièrement validé et doit être testé avec les utilisateurs cibles."
            )

        if "mvp_scope" in missing_fields or not detected.get("mvp_scope"):
            assumptions.append(
                "The MVP should be reduced to one target, one pain point and one measurable result."
                if language == "en"
                else "Le MVP doit être réduit à une cible, un problème et un résultat mesurable."
            )

        return assumptions

    def _recommendation(
        self,
        *,
        score: float,
        ready_for_agents: bool,
        missing_fields: List[str],
        ambiguous_fields: List[str],
        language: str,
    ) -> str:
        if language == "en":
            if ready_for_agents:
                if ambiguous_fields:
                    return (
                        "The idea is clear enough to start the full analysis. "
                        "Some points remain ambiguous and should be listed as assumptions or limitations."
                    )

                return "The idea is clear enough to start the full analysis."

            return (
                "The idea is not clear enough for a reliable full analysis. "
                "Ask the user to complete the missing fields before launching the agents."
            )

        if ready_for_agents:
            if ambiguous_fields:
                return (
                    "L’idée est assez claire pour lancer l’analyse complète. "
                    "Certains points restent ambigus et doivent être listés comme hypothèses ou limites."
                )

            return "L’idée est assez claire pour lancer l’analyse complète."

        return (
            "L’idée n’est pas assez claire pour une analyse fiable. "
            "Il faut demander à l’utilisateur de compléter les informations manquantes avant de lancer les agents."
        )

    # ========================================================
    # Extractors
    # ========================================================

    def _extract_target_users(
        self,
        *,
        description: str,
        project_context: Dict[str, Any],
    ) -> List[str]:
        explicit = self._safe_list(project_context.get("target_users"))

        if explicit:
            return explicit[:8]

        patterns = [
            r"(?:target users are|first target users are|target users include)\s+(.+?)(?:\.|\n|$)",
            r"(?:users are|customers are|clients are)\s+(.+?)(?:\.|\n|$)",
            r"(?:les utilisateurs cibles sont|les premiers utilisateurs sont|les clients cibles sont)\s+(.+?)(?:\.|\n|$)",
            r"(?:la cible est|les cibles sont)\s+(.+?)(?:\.|\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description, flags=re.IGNORECASE)

            if not match:
                continue

            extracted = match.group(1)
            users = self._split_items(extracted)

            if users:
                return users[:8]

        sentence = self._extract_sentence_by_hints(
            text=description,
            hints=self.TARGET_HINTS,
        )

        return self._split_items(sentence)[:6]

    def _extract_use_case(
        self,
        *,
        description: str,
        solution: str,
        project_context: Dict[str, Any],
    ) -> str:
        explicit = self._clean_text(
            project_context.get("main_use_case")
            or project_context.get("use_case")
        )

        if explicit:
            return explicit

        if solution:
            return solution

        return self._extract_sentence_by_hints(
            text=description,
            hints=self.SOLUTION_HINTS,
        )

    def _extract_sentence_by_hints(self, text: str, hints: set[str]) -> str:
        text = self._clean_text(text)

        if not text:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            clean = self._clean_text(sentence)
            lower = clean.lower()

            if len(clean) < 20:
                continue

            score = sum(1 for hint in hints if hint in lower)

            if score > best_score:
                best_score = score
                best_sentence = clean

        return best_sentence if best_score > 0 else ""

    # ========================================================
    # Helpers
    # ========================================================

    def _contains_any(self, text: str, hints: set[str]) -> bool:
        lower = text.lower()
        return any(hint in lower for hint in hints)

    def _split_items(self, value: str) -> List[str]:
        clean = self._clean_text(value)

        if not clean:
            return []

        parts = re.split(r",|;|\band\b|\bet\b|\+|/", clean, flags=re.IGNORECASE)

        result = []

        for part in parts:
            item = self._clean_text(part)

            if len(item) >= 3:
                result.append(item)

        return self._unique(result)

    def _safe_join(self, value: Any) -> str:
        return " ".join(self._safe_list(value))

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            result = []

            for item in value:
                if item is None:
                    continue

                clean = self._clean_text(str(item))

                if clean:
                    result.append(clean)

            return result

        if isinstance(value, str):
            clean = self._clean_text(value)

            if not clean:
                return []

            if "," in clean or ";" in clean:
                return self._split_items(clean)

            return [clean]

        clean = self._clean_text(str(value))
        return [clean] if clean else []

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""

        text = str(value)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = self._clean_text(value)

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result


idea_readiness_checker = IdeaReadinessChecker()