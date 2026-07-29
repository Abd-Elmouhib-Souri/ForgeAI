from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple


class DomainIntegrityGuard:
    """
    Dynamic Project Context Guard.

    Objectif :
    - ne pas prédire tous les domaines possibles ;
    - construire le contexte depuis l'input utilisateur ;
    - empêcher la contamination entre projets ;
    - autoriser les sorties en français ou anglais ;
    - valider les textes, objets et sources avant sauvegarde.
    """

    def __init__(self) -> None:
        self.stop_words = self._build_stop_words()
        self.generic_business_terms = self._build_generic_business_terms()
        self.generic_tech_terms = self._build_generic_tech_terms()
        self.cross_language_aliases = self._build_cross_language_aliases()

    def build_project_context(
        self,
        *,
        title: str,
        description: str,
        industry: Optional[str] = None,
        market_region: Optional[str] = None,
        output_language: str = "fr",
        analysis_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trusted_text_parts = [
            title or "",
            description or "",
            industry or "",
            market_region or "",
        ]

        safe_analysis_text = self._extract_safe_analysis_text(analysis_data or {})
        trusted_text_parts.extend(safe_analysis_text)

        raw_text = "\n".join(trusted_text_parts)
        normalized_text = self._normalize(raw_text)

        title_terms = self._extract_keywords(title or "", max_items=30)
        description_terms = self._extract_keywords(description or "", max_items=120)
        industry_terms = self._extract_keywords(industry or "", max_items=30)
        analysis_terms = self._extract_keywords(
            " ".join(safe_analysis_text),
            max_items=100,
        )

        core_terms = unique_list(
            title_terms
            + industry_terms
            + description_terms
            + analysis_terms
        )

        core_terms = self._expand_with_cross_language_aliases(core_terms)

        anchor_terms = unique_list(
            title_terms
            + industry_terms
            + self._extract_high_signal_terms(description or "")
        )

        anchor_terms = self._expand_with_cross_language_aliases(anchor_terms)

        core_phrases = unique_list(
            self._extract_key_phrases(title or "", max_items=20)
            + self._extract_key_phrases(industry or "", max_items=20)
            + self._extract_key_phrases(description or "", max_items=80)
        )

        project_sentences = self._extract_representative_sentences(
            text=description or "",
            max_items=8,
        )

        language = normalize_output_language(output_language)
        domain_label = self._build_dynamic_domain_label(
            title=title,
            industry=industry,
            core_terms=core_terms,
        )

        context = {
            "title": title or "",
            "description": description or "",
            "industry": industry or "",
            "market_region": market_region or "",
            "output_language": language,
            "language_instruction": self.language_instruction(language),
            "domain_label": domain_label,
            "core_terms": core_terms,
            "anchor_terms": anchor_terms,
            "core_phrases": core_phrases,
            "project_sentences": project_sentences,
            "normalized_project_text": normalized_text,
        }

        context["domain_instruction"] = self.build_domain_instruction(context)

        return context

    def language_instruction(self, output_language: str) -> str:
        language = normalize_output_language(output_language)

        if language == "en":
            return (
                "LANGUAGE LOCK: Answer only in English. "
                "All JSON string values, recommendations, risks, personas, summaries, "
                "and final report content must be written in English."
            )

        return (
            "LANGUAGE LOCK: Réponds uniquement en français. "
            "Toutes les valeurs textuelles JSON, recommandations, risques, personas, "
            "résumés et contenus du rapport final doivent être en français."
        )

    def build_domain_instruction(self, project_context: Dict[str, Any]) -> str:
        language = normalize_output_language(project_context.get("output_language"))

        if language == "en":
            return (
                "STRICT PROJECT CONTEXT LOCK\n"
                "Generate content only from the current user's project input.\n\n"
                f"Project title: {project_context.get('title')}\n"
                f"Industry: {project_context.get('industry') or 'not specified'}\n"
                f"Target region: {project_context.get('market_region') or 'not specified'}\n"
                f"Dynamic context label: {project_context.get('domain_label')}\n\n"
                f"High-signal project terms: {', '.join(project_context.get('anchor_terms', [])[:40])}\n"
                f"Project phrases: {', '.join(project_context.get('core_phrases', [])[:20])}\n\n"
                "Rules:\n"
                "- Do not reuse examples, risks, competitors, MVPs, actions, or personas from another project.\n"
                "- Do not introduce a specific sector unless it appears in the user input or trusted analysis fields.\n"
                "- Every output must match the project title, description, industry, target users, problem, MVP and region.\n"
                "- When evidence is missing, say validation is required instead of inventing sector-specific content.\n"
                "- Output language must be English.\n"
            )

        return (
            "STRICT PROJECT CONTEXT LOCK\n"
            "Génère du contenu uniquement depuis l'input du projet utilisateur actuel.\n\n"
            f"Titre du projet : {project_context.get('title')}\n"
            f"Secteur : {project_context.get('industry') or 'non spécifié'}\n"
            f"Région cible : {project_context.get('market_region') or 'non spécifiée'}\n"
            f"Contexte dynamique : {project_context.get('domain_label')}\n\n"
            f"Termes forts du projet : {', '.join(project_context.get('anchor_terms', [])[:40])}\n"
            f"Phrases clés du projet : {', '.join(project_context.get('core_phrases', [])[:20])}\n\n"
            "Règles :\n"
            "- Ne réutilise jamais des exemples, risques, concurrents, MVP, actions ou personas d'un autre projet.\n"
            "- N'introduis jamais un secteur spécifique s'il n'apparaît pas dans l'input utilisateur ou les analyses fiables.\n"
            "- Chaque sortie doit correspondre au titre, à la description, au secteur, à la cible, au problème, au MVP et à la région.\n"
            "- Si une preuve manque, indique qu'une validation est nécessaire au lieu d'inventer un contenu métier.\n"
            "- La langue de sortie doit être le français.\n"
        )

    def validate_text(
        self,
        *,
        text: str,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        text = str(text or "").strip()

        if not text:
            return self._valid_result()

        sentences = self._split_sentences(text)

        invalid_sentences: List[Dict[str, Any]] = []
        valid_sentences = 0

        for sentence in sentences:
            sentence_validation = self.validate_sentence(
                sentence=sentence,
                project_context=project_context,
            )

            if sentence_validation["is_valid"]:
                valid_sentences += 1
            else:
                invalid_sentences.append(sentence_validation)

        is_contaminated = False

        if invalid_sentences and valid_sentences == 0:
            is_contaminated = True

        if len(invalid_sentences) >= 2:
            is_contaminated = True

        return {
            "is_valid": not is_contaminated,
            "is_contaminated": is_contaminated,
            "invalid_sentences": invalid_sentences,
            "valid_sentences": valid_sentences,
            "total_sentences": len(sentences),
        }

    def validate_sentence(
        self,
        *,
        sentence: str,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        sentence = str(sentence or "").strip()

        if not sentence:
            return self._valid_result()

        sentence_keywords = self._extract_keywords(sentence, max_items=80)
        sentence_keywords = self._expand_with_cross_language_aliases(sentence_keywords)

        if not sentence_keywords:
            return self._valid_result()

        project_terms = set(project_context.get("core_terms") or []) | set(
            project_context.get("anchor_terms") or []
        )

        overlap = sorted(set(sentence_keywords) & project_terms)

        specific_terms = [
            term
            for term in sentence_keywords
            if term not in self.generic_business_terms
            and term not in self.generic_tech_terms
            and term not in self.stop_words
            and len(term) >= 4
        ]

        if self._is_generic_business_sentence(sentence_keywords):
            return {
                "is_valid": True,
                "is_contaminated": False,
                "sentence": sentence,
                "reason": "generic_business_sentence",
                "overlap": overlap,
                "specific_terms": specific_terms,
            }

        if overlap:
            return {
                "is_valid": True,
                "is_contaminated": False,
                "sentence": sentence,
                "reason": "has_project_overlap",
                "overlap": overlap,
                "specific_terms": specific_terms,
            }

        if len(specific_terms) <= 1 and len(sentence_keywords) <= 6:
            return {
                "is_valid": True,
                "is_contaminated": False,
                "sentence": sentence,
                "reason": "too_short_to_judge",
                "overlap": overlap,
                "specific_terms": specific_terms,
            }

        return {
            "is_valid": False,
            "is_contaminated": True,
            "sentence": sentence,
            "reason": "specific_terms_without_project_overlap",
            "overlap": overlap,
            "specific_terms": specific_terms,
        }

    def validate_object(
        self,
        *,
        data: Any,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        texts = self._collect_texts(data)
        contaminated_items: List[Dict[str, Any]] = []

        for path, text in texts:
            validation = self.validate_text(
                text=text,
                project_context=project_context,
            )

            if validation["is_contaminated"]:
                contaminated_items.append(
                    {
                        "path": path,
                        "text_preview": text[:260],
                        "invalid_sentences": validation["invalid_sentences"],
                    }
                )

        return {
            "is_valid": len(contaminated_items) == 0,
            "contaminated_count": len(contaminated_items),
            "contaminated_items": contaminated_items,
        }

    def sanitize_text(
        self,
        *,
        text: str,
        project_context: Dict[str, Any],
        fallback: Optional[str] = None,
    ) -> str:
        validation = self.validate_text(
            text=text,
            project_context=project_context,
        )

        if validation["is_valid"]:
            return text

        if fallback:
            return fallback

        return self._fallback_sentence(project_context)

    def sanitize_object(
        self,
        *,
        data: Any,
        project_context: Dict[str, Any],
    ) -> Any:
        cloned = deepcopy(data)

        return self._sanitize_recursive(
            value=cloned,
            project_context=project_context,
        )

    def filter_sources(
        self,
        *,
        sources: List[Dict[str, Any]],
        project_context: Dict[str, Any],
        min_overlap: int = 1,
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []

        project_terms = set(project_context.get("core_terms") or []) | set(
            project_context.get("anchor_terms") or []
        )

        for source in sources:
            source_text = " ".join(
                [
                    str(source.get("title") or ""),
                    str(source.get("snippet") or ""),
                    str(source.get("extracted_text_preview") or ""),
                    str(source.get("why_relevant") or ""),
                    str(source.get("url") or ""),
                ]
            )

            source_keywords = self._extract_keywords(source_text, max_items=100)
            source_keywords = self._expand_with_cross_language_aliases(source_keywords)
            overlap = sorted(set(source_keywords) & project_terms)

            if len(overlap) >= min_overlap:
                filtered.append(source)

        return filtered

    def build_safe_agent_fallback(
        self,
        *,
        project_context: Dict[str, Any],
        round_number: Optional[int] = None,
        role: str = "agent",
    ) -> Dict[str, Any]:
        language = normalize_output_language(project_context.get("output_language"))
        title = project_context.get("title") or "this project"
        domain_label = project_context.get("domain_label") or "the project context"
        project_sentences = project_context.get("project_sentences") or []

        if language == "en":
            problem_sentence = (
                project_sentences[0]
                if project_sentences
                else "The main problem must be validated with real target users."
            )

            base_actions = [
                "Interview users matching the target described in the project.",
                "Build an MVP limited to one main promise.",
                "Compare the real alternatives already used by this target.",
                "Measure repeated usage, real cost and willingness to pay.",
            ]

            if role == "critic":
                return {
                    "role": "critic",
                    "round": round_number or 1,
                    "main_objection": (
                        f"{title} must be challenged only inside its real context: {domain_label}."
                    ),
                    "critical_risks": [
                        "The priority problem is not yet confirmed by real users.",
                        "The MVP may remain too broad if one core promise is not selected.",
                        "Willingness to pay and repeated usage are not yet proven.",
                    ],
                    "weak_assumptions": [
                        "The described target will adopt the solution.",
                        "The MVP will create measurable value quickly.",
                        "The real cost will remain compatible with the target market.",
                    ],
                    "missing_evidence": [
                        "User interviews linked to the project target.",
                        "Prototype or demo of one feature.",
                        "Pricing test or payment intent.",
                    ],
                    "counter_recommendation": (
                        f"Refocus {title} on this starting problem: {problem_sentence}"
                    ),
                    "risk_score": 7,
                }

            if role == "judge":
                return {
                    "role": "judge",
                    "verdict": "PIVOTER",
                    "argument_strength_score": 6,
                    "risk_level": "medium",
                    "critical_risks": [
                        "Insufficient field validation.",
                        "MVP still needs to be narrowed.",
                        "Willingness to pay is not confirmed.",
                    ],
                    "validated_opportunities": [
                        f"The project can be interesting if this problem is confirmed: {problem_sentence}",
                        "A reduced MVP can make the decision more reliable.",
                    ],
                    "improved_idea": (
                        f"Reduce {title} to one target, one pain point and one measurable action."
                    ),
                    "final_recommendation": (
                        "Pivot toward a short pilot before any full development."
                    ),
                    "next_actions": base_actions,
                    "decision_by_round": [],
                    "debate_synthesis": (
                        f"The debate must remain strictly linked to {title} and its context: {domain_label}."
                    ),
                    "go_no_go_conditions": [
                        "Target user clarified.",
                        "Single MVP defined.",
                        "Prototype tested.",
                        "Willingness to pay validated.",
                    ],
                    "missing_evidence": [],
                    "weak_assumptions": [],
                }

            return {
                "role": "defender",
                "round": round_number or 1,
                "position": "PIVOTER",
                "main_argument": (
                    f"{title} is worth studying, but only inside its real context: {domain_label}."
                ),
                "supporting_points": [
                    f"Project starting point: {problem_sentence}",
                    "The defensible version must stay focused on a clear target.",
                    "The MVP must test one promise before any extension.",
                ],
                "opportunities": [
                    "An innovative project becomes credible when the first use case is measurable.",
                    "A short field validation can reduce risk.",
                ],
                "response_to_previous_critic": (
                    "The correct answer is to transform objections into measurable field tests."
                ),
                "assumptions": [
                    "The described target really faces the problem.",
                    "The reduced MVP can test value quickly.",
                    "User feedback will allow an objective decision.",
                ],
                "opportunity_score": 6,
            }

        problem_sentence = (
            project_sentences[0]
            if project_sentences
            else "Le problème principal doit être validé auprès de la cible réelle."
        )

        base_actions = [
            "Interviewer des utilisateurs correspondant à la cible décrite dans le projet.",
            "Construire un MVP limité à une seule promesse principale.",
            "Comparer les alternatives réellement utilisées par cette cible.",
            "Mesurer l’usage répété, le coût réel et la volonté de payer.",
        ]

        if role == "critic":
            return {
                "role": "critic",
                "round": round_number or 1,
                "main_objection": (
                    f"{title} doit être challengé uniquement dans son contexte réel : {domain_label}."
                ),
                "critical_risks": [
                    "Le problème prioritaire n’est pas encore confirmé par des utilisateurs réels.",
                    "Le MVP peut rester trop large si une seule promesse n’est pas choisie.",
                    "La volonté de payer et l’usage répété ne sont pas encore prouvés.",
                ],
                "weak_assumptions": [
                    "La cible décrite adoptera la solution.",
                    "Le MVP produira une valeur mesurable rapidement.",
                    "Le coût réel restera compatible avec le marché cible.",
                ],
                "missing_evidence": [
                    "Entretiens utilisateurs liés à la cible du projet.",
                    "Prototype ou démonstration d’une seule fonctionnalité.",
                    "Test de prix ou intention de paiement.",
                ],
                "counter_recommendation": (
                    f"Recentrer {title} sur le problème suivant : {problem_sentence}"
                ),
                "risk_score": 7,
            }

        if role == "judge":
            return {
                "role": "judge",
                "verdict": "PIVOTER",
                "argument_strength_score": 6,
                "risk_level": "medium",
                "critical_risks": [
                    "Validation terrain insuffisante.",
                    "MVP encore à préciser.",
                    "Volonté de payer non confirmée.",
                ],
                "validated_opportunities": [
                    f"Le projet peut être intéressant si le problème décrit est confirmé : {problem_sentence}",
                    "Un MVP réduit peut permettre une décision plus fiable.",
                ],
                "improved_idea": (
                    f"Réduire {title} à un MVP centré sur une seule cible, une seule douleur et une seule action mesurable."
                ),
                "final_recommendation": (
                    "Pivoter vers un pilote court avant tout développement complet."
                ),
                "next_actions": base_actions,
                "decision_by_round": [],
                "debate_synthesis": (
                    f"Le débat doit rester strictement lié à {title} et au contexte : {domain_label}."
                ),
                "go_no_go_conditions": [
                    "Cible utilisateur précisée.",
                    "MVP unique défini.",
                    "Prototype testé.",
                    "Volonté de payer validée.",
                ],
                "missing_evidence": [],
                "weak_assumptions": [],
            }

        return {
            "role": "defender",
            "round": round_number or 1,
            "position": "PIVOTER",
            "main_argument": (
                f"{title} mérite d’être étudié, mais uniquement dans son contexte réel : {domain_label}."
            ),
            "supporting_points": [
                f"Point de départ du projet : {problem_sentence}",
                "La version défendable doit rester centrée sur une cible claire.",
                "Le MVP doit tester une seule promesse avant toute extension.",
            ],
            "opportunities": [
                "Un projet innovant peut devenir crédible si le premier cas d’usage est mesurable.",
                "Une validation terrain courte peut réduire fortement le risque.",
            ],
            "response_to_previous_critic": (
                "La réponse correcte est de transformer les objections en tests terrain mesurables."
            ),
            "assumptions": [
                "La cible décrite rencontre réellement le problème.",
                "Le MVP réduit peut tester la valeur rapidement.",
                "Les retours utilisateurs permettront une décision objective.",
            ],
            "opportunity_score": 6,
        }

    def _fallback_sentence(self, project_context: Dict[str, Any]) -> str:
        language = normalize_output_language(project_context.get("output_language"))
        title = project_context.get("title") or "ce projet"
        domain_label = project_context.get("domain_label") or "le contexte du projet"

        if language == "en":
            return (
                f"This part must be reformulated to stay strictly linked to {title}. "
                f"The dynamic context is: {domain_label}. Field validation is required."
            )

        return (
            f"Cette partie doit être reformulée pour rester strictement liée à {title}. "
            f"Le contexte dynamique est : {domain_label}. Une validation terrain est nécessaire."
        )

    def _sanitize_recursive(
        self,
        *,
        value: Any,
        project_context: Dict[str, Any],
    ) -> Any:
        if isinstance(value, str):
            validation = self.validate_text(
                text=value,
                project_context=project_context,
            )
            return value if validation["is_valid"] else ""

        if isinstance(value, list):
            return [
                item
                for item in [
                    self._sanitize_recursive(
                        value=item,
                        project_context=project_context,
                    )
                    for item in value
                ]
                if not self._is_empty_value(item)
            ]

        if isinstance(value, dict):
            return {
                key: self._sanitize_recursive(
                    value=item,
                    project_context=project_context,
                )
                for key, item in value.items()
            }

        return value

    def _extract_safe_analysis_text(self, analysis_data: Dict[str, Any]) -> List[str]:
        safe_fields = [
            "summary",
            "problem",
            "problem_solved",
            "target_users",
            "target_market",
            "proposed_solution",
            "detected_sector",
        ]

        result: List[str] = []

        for field in safe_fields:
            value = analysis_data.get(field)
            if isinstance(value, str) and value.strip():
                result.append(value.strip())

        market_study = analysis_data.get("market_study") or {}

        if isinstance(market_study, dict):
            for field in ["target_market"]:
                value = market_study.get(field)
                if isinstance(value, str) and value.strip():
                    result.append(value.strip())

            values = market_study.get("customer_segments")
            if isinstance(values, list):
                result.extend(str(item) for item in values if str(item).strip())

        return result

    def _collect_texts(self, data: Any, path: str = "root") -> List[Tuple[str, str]]:
        collected: List[Tuple[str, str]] = []

        if isinstance(data, str):
            collected.append((path, data))
            return collected

        if isinstance(data, list):
            for index, item in enumerate(data):
                collected.extend(self._collect_texts(item, f"{path}[{index}]"))
            return collected

        if isinstance(data, dict):
            for key, value in data.items():
                collected.extend(self._collect_texts(value, f"{path}.{key}"))
            return collected

        return collected

    def _split_sentences(self, text: str) -> List[str]:
        chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _extract_keywords(self, text: str, max_items: int = 80) -> List[str]:
        normalized = self._normalize(text)
        words = re.findall(r"[a-z0-9][a-z0-9+-]{2,}", normalized)

        keywords: List[str] = []

        for word in words:
            if word in self.stop_words:
                continue
            if len(word) < 3:
                continue
            keywords.append(word)

        filtered_words = [word for word in words if word not in self.stop_words]

        for index in range(len(filtered_words) - 1):
            bigram = f"{filtered_words[index]} {filtered_words[index + 1]}"
            if len(bigram) >= 7:
                keywords.append(bigram)

        return unique_list(keywords)[:max_items]

    def _expand_with_cross_language_aliases(self, terms: List[str]) -> List[str]:
        expanded = list(terms)
        normalized_terms = {self._normalize(term) for term in terms}

        for key, aliases in self.cross_language_aliases.items():
            normalized_aliases = {self._normalize(alias) for alias in aliases}

            if key in normalized_terms or normalized_terms.intersection(normalized_aliases):
                expanded.extend(aliases)

        return unique_list(expanded)

    def _extract_high_signal_terms(self, text: str) -> List[str]:
        keywords = self._extract_keywords(text, max_items=120)

        high_signal = [
            keyword
            for keyword in keywords
            if keyword not in self.generic_business_terms
            and keyword not in self.generic_tech_terms
            and len(keyword) >= 5
        ]

        return unique_list(high_signal)[:45]

    def _extract_key_phrases(self, text: str, max_items: int = 50) -> List[str]:
        clean_text = str(text or "").replace("\n", " ")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        phrases: List[str] = []

        for match in re.finditer(
            r"\b[A-Z][A-Za-z0-9+-]*(?:\s+[A-Z][A-Za-z0-9+-]*){0,4}\b",
            clean_text,
        ):
            phrase = match.group(0).strip()
            if len(phrase) >= 4:
                phrases.append(phrase)

        lowered = clean_text.lower()

        markers = [
            "mvp",
            "target customers",
            "target users",
            "business model",
            "first version",
            "the goal",
            "the project solves",
            "customers are",
            "users will",
            "la cible",
            "le problème",
            "la solution",
            "le mvp",
            "le modèle économique",
        ]

        for marker in markers:
            index = lowered.find(marker)
            if index >= 0:
                phrases.append(clean_text[index : index + 180].strip())

        return unique_list(phrases)[:max_items]

    def _extract_representative_sentences(
        self,
        *,
        text: str,
        max_items: int,
    ) -> List[str]:
        sentences = self._split_sentences(text)

        ranked = sorted(
            sentences,
            key=lambda item: self._sentence_importance(item),
            reverse=True,
        )

        return ranked[:max_items]

    def _sentence_importance(self, sentence: str) -> int:
        lowered = sentence.lower()
        score = 0

        markers = [
            "mvp",
            "target",
            "customers",
            "users",
            "problem",
            "solves",
            "goal",
            "business model",
            "first version",
            "première version",
            "cible",
            "problème",
            "solution",
            "marché",
        ]

        for marker in markers:
            if marker in lowered:
                score += 3

        score += min(10, len(self._extract_keywords(sentence, max_items=20)))
        return score

    def _build_dynamic_domain_label(
        self,
        *,
        title: str,
        industry: Optional[str],
        core_terms: List[str],
    ) -> str:
        if industry:
            return industry

        if title:
            return title

        if core_terms:
            return " / ".join(core_terms[:4])

        return "dynamic project context"

    def _is_generic_business_sentence(self, sentence_keywords: List[str]) -> bool:
        if not sentence_keywords:
            return True

        specific = [
            term
            for term in sentence_keywords
            if term not in self.generic_business_terms
            and term not in self.generic_tech_terms
            and term not in self.stop_words
        ]

        generic_count = sum(
            1
            for term in sentence_keywords
            if term in self.generic_business_terms
            or term in self.generic_tech_terms
        )

        return generic_count >= 2 and len(specific) <= 3

    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, list):
            return len(value) == 0
        if isinstance(value, dict):
            return all(self._is_empty_value(item) for item in value.values())
        return False

    def _normalize(self, value: str) -> str:
        value = str(value or "")
        value = value.replace("?", " ")
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower()
        value = value.replace("’", "'").replace("`", "'")
        value = re.sub(r"[^a-z0-9\s/+-]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _valid_result(self) -> Dict[str, Any]:
        return {
            "is_valid": True,
            "is_contaminated": False,
            "invalid_sentences": [],
            "valid_sentences": 1,
            "total_sentences": 1,
        }

    def _build_stop_words(self) -> Set[str]:
        return {
            "the", "and", "for", "with", "from", "that", "this", "they",
            "them", "their", "there", "will", "would", "could", "should",
            "can", "may", "are", "was", "were", "been", "have", "has",
            "had", "not", "but", "one", "two", "all", "any", "more",
            "most", "into", "than", "then", "also", "very", "many", "much",
            "such", "dans", "pour", "avec", "sans", "des", "les", "une",
            "aux", "sur", "qui", "que", "est", "sont", "être", "etre",
            "avoir", "plus", "moins", "très", "tres", "tout", "tous",
            "cela", "cette", "comme", "afin", "avant", "après", "apres",
            "tunisie", "tunisia", "global", "local", "region", "région",
            "marche", "marché", "near", "small", "simple",
        }

    def _build_generic_business_terms(self) -> Set[str]:
        return {
            "startup", "projet", "project", "idea", "idee", "idée",
            "business", "model", "mvp", "prototype", "pilot", "pilote",
            "test", "tests", "validate", "validation", "valider", "validated",
            "target", "cible", "users", "user", "utilisateur", "utilisateurs",
            "customers", "clients", "segment", "segments", "problem",
            "problème", "probleme", "solution", "value", "valeur", "risk",
            "risque", "risques", "opportunity", "opportunité", "opportunite",
            "opportunites", "opportunités", "revenue", "revenus", "pricing",
            "prix", "cost", "cout", "coût", "budget", "roi", "market",
            "marché", "marche", "competition", "concurrence", "competitor",
            "concurrent", "concurrents", "alternative", "alternatives",
            "differentiation", "différenciation", "differenciation",
            "adoption", "usage", "retention", "traction", "go/no-go",
            "roadmap", "scaling", "scalability", "faisabilité", "faisabilite",
            "rentabilité", "rentabilite", "interviewer", "interview",
            "interviews", "entretiens", "terrain", "hypothese", "hypothèse",
            "preuve", "preuves", "evidence", "measure", "measuring",
            "mesurer", "metrics", "kpi", "willingness", "payer", "pay",
            "payment", "repeated", "répété", "repete",
        }

    def _build_generic_tech_terms(self) -> Set[str]:
        return {
            "app", "application", "platform", "plateforme", "saas",
            "software", "logiciel", "dashboard", "api", "database", "data",
            "données", "donnees", "web", "mobile", "cloud", "backend",
            "frontend", "react", "nextjs", "fastapi", "postgresql",
            "mongodb", "firebase", "vercel", "sms", "email", "notification",
            "notifications", "ai", "ia", "intelligence", "artificial",
            "automation", "automatisation", "digital", "numérique", "numerique",
            "whatsapp",
        }

    def _build_cross_language_aliases(self) -> Dict[str, List[str]]:
        return {
            "clinic": [
                "clinic", "clinics", "clinique", "cliniques", "cabinet",
                "cabinet medical", "cabinet médical", "medical office",
                "medical offices", "centre medical", "centre médical",
            ],
            "medical": [
                "medical", "médical", "medicale", "médicale", "health",
                "healthtech", "santé", "sante", "doctor", "doctors",
                "medecin", "médecin", "medecins", "médecins",
            ],
            "patient": [
                "patient", "patients", "malade", "malades",
            ],
            "appointment": [
                "appointment", "appointments", "rendez vous", "rendez-vous",
                "consultation", "consultations",
            ],
            "queue": [
                "queue", "waiting", "waiting list", "waiting time",
                "wait time", "file attente", "file d attente", "file d'attente",
                "temps attente", "temps d attente", "attente",
            ],
            "secretary": [
                "secretary", "secretaries", "secretaire", "secrétaire",
                "secretaires", "secrétaires", "assistant medical",
                "assistante medicale",
            ],
            "dentist": [
                "dentist", "dentists", "dentiste", "dentistes",
            ],
            "pharmacy": [
                "pharmacy", "pharmacie", "pharmacies", "officine",
                "officines", "pharmacien", "pharmacienne",
            ],
            "stock": [
                "stock", "inventory", "inventaire", "rupture", "ruptures",
                "reapprovisionnement", "réapprovisionnement",
            ],
        }


def normalize_output_language(value: Optional[str]) -> str:
    cleaned = str(value or "fr").strip().lower()

    if cleaned in {"fr", "français", "francais", "french"}:
        return "fr"

    if cleaned in {"en", "english", "anglais"}:
        return "en"

    return "fr"


def unique_list(values: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()

    for value in values:
        clean = str(value or "").strip()

        if not clean:
            continue

        key = clean.lower()

        if key not in seen:
            seen.add(key)
            result.append(clean)

    return result


domain_integrity_guard = DomainIntegrityGuard()