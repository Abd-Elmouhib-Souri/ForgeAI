from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ContextConfidence,
    ProblemContext,
    ProjectContextPacketV3,
    SolutionContext,
    TransactionUnitContext,
    WorkflowContext,
    clean_text,
    comparison_key,
    unique_texts,
)
from app.services.domain_integrity_guard import normalize_output_language
from app.services.project_intelligence_layer import project_intelligence_layer


class ProjectContextExtractor:
    """
    Extrait un contexte universel et canonique pour tous les agents ForgeAI.

    Principes :
    - les informations explicites de l'utilisateur sont prioritaires ;
    - le workflow principal est séparé du périmètre MVP ;
    - le secteur et l'archétype sont distincts ;
    - les phrases de problème ne deviennent jamais des workflows ;
    - les termes centraux du projet ne peuvent pas devenir interdits ;
    - la confiance de contexte mesure la complétude, pas la validation marché.
    """

    TARGET_PATTERNS = (
        re.compile(
            r"(?:les\s+)?(?:premiers?\s+)?"
            r"(?:clients?|utilisateurs?|usagers?|"
            r"bénéficiaires?|beneficiaires?)\s+"
            r"(?:ciblés?|cibles?|visés?|vises?)\s+"
            r"(?:sont|seront|incluent|comprennent)\s+(.+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:target|primary)\s+"
            r"(?:customers?|users?|beneficiaries)\s+"
            r"(?:are|include)\s+(.+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:destiné|destinee|destinée|destines|destinés|"
            r"conçu|concue|conçue)\s+"
            r"(?:principalement\s+)?(?:à|aux|pour)\s+(.+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:designed|intended|built)\s+"
            r"(?:mainly\s+)?for\s+(.+)",
            re.IGNORECASE,
        ),
    )

    ACTION_PATTERNS: Tuple[
        Tuple[re.Pattern[str], str],
        ...,
    ] = (
        (
            re.compile(
                r"\binspect(?:er|e|ionner|s|ing)?\b",
                re.IGNORECASE,
            ),
            "inspecter",
        ),
        (
            re.compile(
                r"\bdétect(?:er|e|ion|ions)?\b"
                r"|\bdetect(?:s|ed|ing|ion)?\b",
                re.IGNORECASE,
            ),
            "détecter",
        ),
        (
            re.compile(
                r"\bsurveill(?:er|e|ance)?\b"
                r"|\bmonitor(?:s|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "surveiller",
        ),
        (
            re.compile(
                r"\bréserv(?:er|e|ation)?\b"
                r"|\bbook(?:s|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "réserver",
        ),
        (
            re.compile(
                r"\bcommand(?:er|e)?\b"
                r"|\border(?:s|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "commander",
        ),
        (
            re.compile(
                r"\bplanifi(?:er|e|es|ent|ons|ez|ait|ant|cation)?\b"
                r"|\bcr(?:é|e)(?:er|e|es|ent|ait|ant)?\b"
                r"(?=[^.!?]{0,80}"
                r"\b(?:horaire|planning|calendrier)s?\b)"
                r"|\borganis(?:er|e|es|ent|ait|ant)?\b"
                r"(?=[^.!?]{0,80}"
                r"\b(?:horaire|planning|équipe|equipe)s?\b)"
                r"|\bschedul(?:e|es|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "planifier",
        ),
        (
            re.compile(
                r"\bgér(?:er|e)?\b"
                r"|\bmanage(?:s|d|ing)?\b",
                re.IGNORECASE,
            ),
            "gérer",
        ),
        (
            re.compile(
                r"\bsuiv(?:re|i|is|ons|ez|ent|ant|ra|ront)?\b"
                r"|\bsuit\b"
                r"|\btrack(?:s|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "suivre",
        ),
        (
            re.compile(
                r"\bmettre en relation\b"
                r"|\bconnect(?:er|e|s|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "mettre en relation",
        ),
        (
            re.compile(
                r"\bpubl(?:ier|ie|ish|ishes|ished|ishing)?\b"
                r"|\bpost(?:s|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "publier",
        ),
        (
            re.compile(
                r"\bclassifi(?:er|e|cation)?\b"
                r"|\bclassif(?:y|ies|ied|ying|ication)?\b",
                re.IGNORECASE,
            ),
            "classifier",
        ),
        (
            re.compile(
                r"\banalys(?:er|e|is|ing)?\b"
                r"|\banalyz(?:e|es|ed|ing)?\b",
                re.IGNORECASE,
            ),
            "analyser",
        ),
        (
            re.compile(
                r"\bmesur(?:er|e)?\b"
                r"|\bmeasure(?:s|d|ing)?\b",
                re.IGNORECASE,
            ),
            "mesurer",
        ),
        (
            re.compile(
                r"\btransmet(?:tre|s|tent|tant|tra|tront)?\b"
                r"|\benvoi(?:e|er|ent|era|eront)?\b"
                r"|\bsend(?:s|ing|sent)?\b",
                re.IGNORECASE,
            ),
            "transmettre",
        ),
        (
            re.compile(
                r"\balert(?:er|e|s|ed|ing)?\b"
                r"|\bnotifi(?:er|e|cation)?\b"
                r"|\bnotify\b",
                re.IGNORECASE,
            ),
            "alerter",
        ),
    )

    ACTION_PRIORITY = {
        "inspecter": 100,
        "surveiller": 95,
        "réserver": 95,
        "commander": 95,
        "planifier": 90,
        "gérer": 88,
        "mettre en relation": 88,
        "analyser": 85,
        "classifier": 84,
        "mesurer": 82,
        "détecter": 80,
        "suivre": 78,
        "transmettre": 70,
        "alerter": 65,
        "publier": 65,
    }

    MVP_MARKERS = (
        "mvp",
        "première version",
        "premiere version",
        "first version",
        "version initiale",
        "initial version",
        "limité à",
        "limite a",
        "limited to",
        "se concentrera sur",
        "focuses on",
    )

    BUSINESS_MARKERS = (
        "modèle économique",
        "modele economique",
        "business model",
        "abonnement",
        "subscription",
        "commission",
        "vente",
        "sale",
        "location",
        "rental",
        "freemium",
    )

    CONSTRAINT_MARKERS = (
        "contraintes",
        "constraints",
        "coût du matériel",
        "cout du materiel",
        "hardware cost",
        "maintenance",
        "autonomie",
        "battery life",
        "réglementation",
        "reglementation",
        "regulation",
    )

    PROBLEM_MARKERS = (
        "problème principal",
        "probleme principal",
        "le problème est",
        "le probleme est",
        "problème identifié",
        "probleme identifie",
        "inspection manuelle",
        "méthode actuelle",
        "methode actuelle",
        "current process",
        "current alternative",
        "demande beaucoup de temps",
        "trop tard",
        "entraîne",
        "entraine",
        "perte",
        "gaspillage",
        "risque",
    )

    GENERIC_ACTORS = {
        "client",
        "clients",
        "utilisateur",
        "utilisateurs",
        "user",
        "users",
        "customer",
        "customers",
        "primary user",
        "utilisateur principal",
        "field operator",
        "operateur terrain",
        "operational buyer",
        "acheteur operationnel",
        "client payeur",
    }

    ACTOR_HEAD_MARKERS = (
        # Acteurs génériques
        "acteur",
        "acteurs",
        "personne",
        "personnes",
        "utilisateur",
        "utilisateurs",
        "usager",
        "usagers",
        "client",
        "clients",
        "customer",
        "customers",
        "user",
        "users",

        # Organisations
        "entreprise",
        "entreprises",
        "société",
        "sociétés",
        "societe",
        "societes",
        "company",
        "companies",
        "business",
        "businesses",
        "organisation",
        "organisations",
        "organization",
        "organizations",
        "coopérative",
        "coopératives",
        "cooperative",
        "cooperatives",

        # Offre et demande
        "vendeur",
        "vendeurs",
        "vendeuse",
        "vendeuses",
        "seller",
        "sellers",
        "fournisseur",
        "fournisseurs",
        "supplier",
        "suppliers",
        "prestataire",
        "prestataires",
        "provider",
        "providers",
        "producteur",
        "producteurs",
        "producer",
        "producers",
        "acheteur",
        "acheteurs",
        "acheteuse",
        "acheteuses",
        "buyer",
        "buyers",
        "acquéreur",
        "acquéreurs",
        "acquereur",
        "acquereurs",

        # Décision et paiement
        "payeur",
        "payeurs",
        "financeur",
        "financeurs",
        "décideur",
        "décideurs",
        "decideur",
        "decideurs",
        "responsable",
        "responsables",
        "manager",
        "managers",
        "directeur",
        "directeurs",
        "dirigeant",
        "dirigeants",
        "propriétaire",
        "propriétaires",
        "proprietaire",
        "proprietaires",
        "owner",
        "owners",

        # Opérations et maintenance
        "technicien",
        "techniciens",
        "technician",
        "technicians",
        "opérateur",
        "opérateurs",
        "operateur",
        "operateurs",
        "operator",
        "operators",
        "ouvrier",
        "ouvriers",
        "employé",
        "employés",
        "employe",
        "employes",
        "employee",
        "employees",
        "mainteneur",
        "mainteneurs",
        "réparateur",
        "réparateurs",
        "reparateur",
        "reparateurs",
        "installateur",
        "installateurs",
        "intégrateur",
        "intégrateurs",
        "integrateur",
        "integrateurs",

        # Partenaires et autorités
        "partenaire",
        "partenaires",
        "partner",
        "partners",
        "autorité",
        "autorités",
        "autorite",
        "autorites",
        "régulateur",
        "régulateurs",
        "regulateur",
        "regulateurs",
        "regulator",
        "regulators",
        "administration",
        "administrations",

        # Agriculture
        "agriculteur",
        "agriculteurs",
        "farmer",
        "farmers",
        "exploitation",
        "exploitations",
        "ferme",
        "fermes",
        "pépinière",
        "pépinières",
        "pepiniere",
        "pepinieres",

        # Santé
        "patient",
        "patients",
        "médecin",
        "médecins",
        "medecin",
        "medecins",
        "doctor",
        "doctors",
        "infirmier",
        "infirmiers",
        "infirmière",
        "infirmières",
        "clinique",
        "cliniques",
        "hôpital",
        "hôpitaux",
        "hopital",
        "hopitaux",

        # Éducation
        "élève",
        "élèves",
        "eleve",
        "eleves",
        "étudiant",
        "étudiants",
        "etudiant",
        "etudiants",
        "student",
        "students",
        "enseignant",
        "enseignants",
        "teacher",
        "teachers",
        "école",
        "écoles",
        "ecole",
        "ecoles",
        "université",
        "universités",
        "universite",
        "universites",

        # Communauté
        "bénéficiaire",
        "bénéficiaires",
        "beneficiaire",
        "beneficiaires",
        "citoyen",
        "citoyens",
        "membre",
        "membres",
        "member",
        "members",
        "créateur",
        "créateurs",
        "createur",
        "createurs",
        "creator",
        "creators",
        "modérateur",
        "modérateurs",
        "moderateur",
        "moderateurs",
    )

    def extract(
        self,
        *,
        title: str = "",
        description: str = "",
        industry: str = "",
        target_region: str = "",
        output_language: str = "fr",
        project_context: Dict[str, Any] | None = None,
        idea_readiness: Dict[str, Any] | None = None,
        analysis_data: Dict[str, Any] | None = None,
    ) -> ProjectContextPacketV3:
        """
        Produit le contexte canonique du projet.

        Cette méthode ne modifie aucune donnée en base.
        """
        project_context = project_context or {}
        analysis_data = analysis_data or {}

        language = normalize_output_language(
            output_language
        )

        title = clean_text(
            title
            or project_context.get("project_name")
            or project_context.get("title")
        )

        description = clean_text(
            description
            or project_context.get("description")
        )

        industry = clean_text(
            industry
            or project_context.get("industry")
        )

        target_region = clean_text(
            target_region
            or project_context.get("target_region")
            or project_context.get("market_region")
        )

        intelligence = project_intelligence_layer.build(
            title=title,
            description=description,
            industry=industry,
            target_region=target_region,
            output_language=language,
            project_context=project_context,
            idea_readiness=idea_readiness or {},
            analysis_data=analysis_data,
        )

        structured = (
            intelligence.get(
                "structured_project_context"
            )
            or {}
        )

        archetype_context = (
            intelligence.get(
                "archetype_context"
            )
            or {}
        )

        sentences = self._sentences(
            description
        )

        actors = self._extract_explicit_actors(
            description=description,
            project_context=project_context,
            analysis_data=analysis_data,
        )

        if not actors:
            actors = self._fallback_actors(
                structured=structured,
                archetype_context=archetype_context,
            )

        mvp_scope = self._extract_mvp_scope(
            sentences=sentences,
            structured=structured,
            project_context=project_context,
            analysis_data=analysis_data,
        )

        workflows = self._extract_workflows(
            sentences=sentences,
            actors=actors,
            mvp_scope=mvp_scope,
            structured=structured,
        )

        problem = ProblemContext(
            pain=self._extract_problem_text(
                sentences=sentences,
                structured=structured,
            )
        )

        solution = SolutionContext(
            mechanism=self._extract_solution_text(
                sentences=sentences,
                structured=structured,
            ),
            core_value=clean_text(
                structured.get(
                    "value_proposition"
                )
            ),
            delivery_mode=self._delivery_mode(
                description
            ),
            required_capabilities=self._capabilities(
                description
            ),
        )

        (
            business_models,
            explicit_business_models,
        ) = self._extract_business_models(
            sentences=sentences,
            structured=structured,
            project_context=project_context,
            analysis_data=analysis_data,
        )

        constraints = self._constraints(
            sentences=sentences,
            project_context=project_context,
            analysis_data=analysis_data,
        )

        (
            primary_archetype,
            secondary_archetypes,
        ) = self._resolve_archetypes(
            description=description,
            industry=industry,
            structured=structured,
        )

        archetype_confidence = self._archetype_confidence(
            primary_archetype=primary_archetype,
            secondary_archetypes=secondary_archetypes,
            description=description,
            industry=industry,
        )

        transaction_unit = self._extract_transaction_unit(
            sentences=sentences,
            actors=actors,
            workflows=workflows,
        )

        payer_names = unique_texts(
            actor.name
            for actor in actors
            if actor.role
            in {
                ActorRole.BUYER,
                ActorRole.PAYER,
                ActorRole.DECISION_MAKER,
            }
        )

        if not payer_names:
            payer_names = unique_texts(
                [
                    structured.get(
                        "economic_buyer"
                    ),
                    (
                        archetype_context.get(
                            "actors"
                        )
                        or {}
                    ).get("payer"),
                ]
            )

        confidence = self._confidence(
            title=title,
            target_region=target_region,
            problem=problem,
            solution=solution,
            actors=actors,
            workflows=workflows,
            archetype=primary_archetype,
            business_models=explicit_business_models,
            mvp_scope=mvp_scope,
            constraints=constraints,
            language=language,
        )

        return ProjectContextPacketV3(
            project_name=title,
            description=description,
            language=language,
            target_region=target_region,
            industry_user_input=industry,
            sector_labels=unique_texts(
                self._listify(
                    structured.get(
                        "sector_tags"
                    )
                )
                + self._split_list(
                    industry
                )
            ),
            primary_archetype=primary_archetype,
            archetype_confidence=archetype_confidence,
            secondary_archetypes=secondary_archetypes,
            risk_domains=self._listify(
                structured.get(
                    "risk_dimensions"
                )
            ),
            problem=problem,
            solution=solution,
            actors=actors,
            payer_actor_names=payer_names,
            decision_maker_actor_names=payer_names,
            partner_actor_names=unique_texts(
                actor.name
                for actor in actors
                if actor.role
                in {
                    ActorRole.PARTNER,
                    ActorRole.PROVIDER,
                }
            ),
            blocker_actor_names=unique_texts(
                actor.name
                for actor in actors
                if actor.role
                == ActorRole.REGULATORY_BLOCKER
            ),
            priority_workflows=workflows,
            transaction_unit=transaction_unit,
            mvp_scope=mvp_scope,
            deployment_environment=(
                self._deployment_environment(
                    sentences
                )
            ),
            success_metrics=self._listify(
                structured.get(
                    "success_metrics"
                )
            ),
            business_model_hypotheses=(
                business_models
            ),
            constraints=constraints,
            regulatory_flags=(
                self._regulatory_flags(
                    f"{industry} {description}"
                )
            ),
            domain_terms=unique_texts(
                self._listify(
                    intelligence.get(
                        "domain_concepts"
                    )
                )
                + self._listify(
                    structured.get(
                        "sector_tags"
                    )
                )
            ),
            use_case_terms=unique_texts(
                value
                for workflow in workflows
                for value in (
                    workflow.action,
                    workflow.object,
                    workflow.result,
                    workflow.output,
                )
            ),
            solution_terms=self._listify(
                intelligence.get(
                    "solution_terms"
                )
            ),
            target_terms=unique_texts(
                actor.name
                for actor in actors
            ),
            forbidden_adjacent_domains=(
                unique_texts(
                    self._listify(
                        project_context.get(
                            "forbidden_adjacent_domains"
                        )
                    )
                    + self._listify(
                        analysis_data.get(
                            "forbidden_adjacent_domains"
                        )
                    )
                )
            ),
            assumptions=unique_texts(
                self._listify(
                    project_context.get(
                        "assumptions"
                    )
                )
                + self._listify(
                    analysis_data.get(
                        "assumptions"
                    )
                )
            ),
            confidence=confidence,
        )

    def _extract_explicit_actors(
        self,
        *,
        description: str,
        project_context: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[ActorContext]:
        """
        Les acteurs explicitement écrits sont prioritaires.
        """
        names = (
            self._listify(
                project_context.get(
                    "target_users"
                )
            )
            + self._listify(
                analysis_data.get(
                    "target_users"
                )
            )
        )

        sentences = self._sentences(
            description
        )

        high_priority_found = False

        for sentence in sentences:
            for pattern in self.TARGET_PATTERNS[:2]:
                match = pattern.search(
                    sentence
                )

                if not match:
                    continue

                high_priority_found = True

                value = re.split(
                    r"[.;]",
                    match.group(1),
                    maxsplit=1,
                )[0]

                names.extend(
                    self._split_actor_list(
                        value
                    )
                )

        if not high_priority_found:
            for sentence in sentences:
                for pattern in self.TARGET_PATTERNS[2:]:
                    match = pattern.search(
                        sentence
                    )

                    if not match:
                        continue

                    value = re.split(
                        r"[.;]",
                        match.group(1),
                        maxsplit=1,
                    )[0]

                    names.extend(
                        self._split_actor_list(
                            value
                        )
                    )

        output: List[ActorContext] = []
        seen: set[str] = set()

        for raw_name in names:
            name = self._clean_actor(
                raw_name
            )

            key = comparison_key(
                name
            )

            if (
                not name
                or not key
                or key in seen
                or key in self.GENERIC_ACTORS
            ):
                continue

            seen.add(
                key
            )

            output.append(
                ActorContext(
                    name=name,
                    role=self._actor_role(
                        name
                    ),
                    is_explicit=True,
                )
            )

        return output

    def _fallback_actors(
        self,
        *,
        structured: Dict[str, Any],
        archetype_context: Dict[str, Any],
    ) -> List[ActorContext]:
        """
        Utilise les acteurs inférés seulement si aucun acteur explicite
        n'a été extrait.
        """
        names = self._listify(
            structured.get(
                "target_users"
            )
        )

        if not names:
            names = self._listify(
                archetype_context.get(
                    "target_users"
                )
            )

        output: List[ActorContext] = []
        seen: set[str] = set()

        for raw_name in names:
            name = self._clean_actor(
                raw_name
            )

            key = comparison_key(
                name
            )

            if (
                not name
                or not key
                or key in seen
                or key in self.GENERIC_ACTORS
            ):
                continue

            seen.add(
                key
            )

            output.append(
                ActorContext(
                    name=name,
                    role=self._actor_role(
                        name
                    ),
                    is_explicit=False,
                )
            )

        return output[:4]

    def _extract_problem_text(
        self,
        *,
        sentences: Sequence[str],
        structured: Dict[str, Any],
    ) -> str:
        structured_problem = clean_text(
            structured.get(
                "problem"
            )
            or structured.get(
                "core_problem"
            )
        )

        if structured_problem:
            return structured_problem

        candidates = [
            sentence
            for sentence in sentences
            if self._is_problem_sentence(
                sentence
            )
        ]

        if not candidates:
            return ""

        return self._compact(
            candidates[0],
            500,
        )

    def _extract_solution_text(
        self,
        *,
        sentences: Sequence[str],
        structured: Dict[str, Any],
    ) -> str:
        structured_solution = clean_text(
            structured.get(
                "solution"
            )
            or structured.get(
                "solution_type"
            )
        )

        if structured_solution:
            return structured_solution

        candidates = [
            sentence
            for sentence in sentences
            if (
                self._canonical_action(
                    sentence
                )
                and not self._is_problem_sentence(
                    sentence
                )
                and not self._is_scope_only(
                    sentence
                )
            )
        ]

        return self._compact(
            " ".join(
                candidates[:3]
            ),
            700,
        )

    def _extract_mvp_scope(
        self,
        *,
        sentences: Sequence[str],
        structured: Dict[str, Any],
        project_context: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[str]:
        """
        Extrait et déduplique le périmètre du MVP.
        """
        raw_values = (
            self._listify(
                project_context.get(
                    "mvp_scope_items"
                )
            )
            + self._listify(
                analysis_data.get(
                    "mvp_scope_items"
                )
            )
            + self._listify(
                structured.get(
                    "mvp_scope"
                )
            )
        )

        raw_values.extend(
            sentence
            for sentence in sentences
            if self._contains_any(
                sentence,
                self.MVP_MARKERS,
            )
        )

        normalized_values: List[str] = []

        for raw_value in raw_values:
            normalized = self._normalize_scope_item(
                raw_value
            )

            if not normalized:
                continue

            normalized_values.extend(
                self._split_list(
                    normalized
                )
            )

        return self._semantic_unique(
            normalized_values,
            max_items=8,
        )

    def _extract_workflows(
        self,
        *,
        sentences: Sequence[str],
        actors: Sequence[ActorContext],
        mvp_scope: Sequence[str],
        structured: Dict[str, Any],
    ) -> List[WorkflowContext]:
        """
        Construit de vrais workflows métier.

        Les phrases de problème et de périmètre MVP sont exclues.
        """
        actor_name = self._preferred_actor(
            actors
        )

        scope_keys = {
            comparison_key(
                item
            )
            for item in mvp_scope
        }

        candidates: List[
            Dict[str, Any]
        ] = []

        for index, sentence in enumerate(
            sentences
        ):
            if self._is_scope_only(
                sentence
            ):
                continue

            if self._is_problem_sentence(
                sentence
            ):
                continue

            action, match = (
                self._canonical_action_with_match(
                    sentence
                )
            )

            if not action or match is None:
                continue

            candidates.append(
                {
                    "sentence": sentence,
                    "action": action,
                    "match": match,
                    "index": index,
                    "score": self._workflow_score(
                        sentence,
                        action,
                    ),
                    "explicit": True,
                }
            )

        for value in self._listify(
            structured.get(
                "priority_workflows"
            )
        ):
            if self._is_scope_only(
                value
            ):
                continue

            if self._is_problem_sentence(
                value
            ):
                continue

            action, match = (
                self._canonical_action_with_match(
                    value
                )
            )

            if not action or match is None:
                continue

            candidates.append(
                {
                    "sentence": value,
                    "action": action,
                    "match": match,
                    "index": 10_000,
                    "score": (
                        self._workflow_score(
                            value,
                            action,
                        )
                        - 15
                    ),
                    "explicit": False,
                }
            )

        if not candidates:
            return []

        candidates.sort(
            key=lambda item: (
                -item["score"],
                item["index"],
            )
        )

        output: List[
            WorkflowContext
        ] = []

        seen: set[str] = set()

        primary = candidates[0]

        primary_object = self._action_object(
            primary["sentence"],
            primary["match"],
        )

        primary_result = (
            self._result_after_action(
                primary["sentence"],
                primary["match"],
                primary["action"],
            )
        )

        if not primary_result:
            primary_result = (
                self._supporting_result(
                    candidates,
                    primary,
                )
            )

        primary_output = (
            self._supporting_output(
                candidates
            )
        )

        primary_workflow = WorkflowContext(
            name=self._workflow_name(
                action=primary["action"],
                object_text=primary_object,
                result=primary_result,
                output=primary_output,
            ),
            actor=actor_name,
            action=primary["action"],
            object=primary_object,
            result=primary_result,
            output=primary_output,
            is_explicit=bool(
                primary["explicit"]
            ),
            confidence=(
                0.90
                if primary["explicit"]
                else 0.60
            ),
        )

        primary_key = comparison_key(
            primary_workflow.sentence
        )

        if (
            primary_key
            and primary_key
            not in scope_keys
            and primary_workflow.is_actionable
        ):
            output.append(
                primary_workflow
            )

            seen.add(
                primary_key
            )

        for candidate in candidates:
            object_text = self._action_object(
                candidate["sentence"],
                candidate["match"],
            )

            result_text = (
                self._result_after_action(
                    candidate["sentence"],
                    candidate["match"],
                    candidate["action"],
                )
            )

            output_text = (
                self._output_phrase(
                    candidate["sentence"]
                )
            )

            workflow = WorkflowContext(
                name=self._workflow_name(
                    action=candidate[
                        "action"
                    ],
                    object_text=object_text,
                    result=result_text,
                    output=output_text,
                ),
                actor=actor_name,
                action=candidate[
                    "action"
                ],
                object=object_text,
                result=result_text,
                output=output_text,
                is_explicit=bool(
                    candidate["explicit"]
                ),
                confidence=(
                    0.82
                    if candidate[
                        "explicit"
                    ]
                    else 0.50
                ),
            )

            key = comparison_key(
                workflow.sentence
            )

            if not key:
                continue

            if key in seen:
                continue

            if key in scope_keys:
                continue

            if not workflow.is_actionable:
                continue

            if self._workflow_is_subsumed(
                workflow,
                output,
            ):
                continue

            output.append(
                workflow
            )

            seen.add(
                key
            )

            if len(output) >= 4:
                break

        return output

    def _confidence(
        self,
        *,
        title: str,
        target_region: str,
        problem: ProblemContext,
        solution: SolutionContext,
        actors: Sequence[ActorContext],
        workflows: Sequence[WorkflowContext],
        archetype: str,
        business_models: Sequence[str],
        mvp_scope: Sequence[str],
        constraints: Sequence[str],
        language: str,
    ) -> ContextConfidence:
        """
        Mesure la complétude du contexte.

        Le score maximal est limité à 0.94, car une description complète
        ne constitue pas une validation du marché.
        """
        score = (
            0.04
            if title
            else 0.0
        )

        missing_fields: List[str] = []
        ambiguous_fields: List[str] = []

        required_fields = (
            (
                "problem",
                bool(
                    problem.pain
                ),
                0.17,
            ),
            (
                "solution",
                bool(
                    solution.mechanism
                ),
                0.15,
            ),
            (
                "actors",
                bool(
                    actors
                ),
                0.15,
            ),
            (
                "priority_workflow",
                bool(
                    workflows
                    and workflows[
                        0
                    ].is_actionable
                ),
                0.22,
            ),
        )

        for (
            field_name,
            present,
            weight,
        ) in required_fields:
            if present:
                score += weight
            else:
                missing_fields.append(
                    field_name
                )

        if target_region:
            score += 0.08
        else:
            ambiguous_fields.append(
                "target_region"
            )

        if (
            archetype
            and archetype
            != "generic_digital_product"
        ):
            score += 0.07
        else:
            ambiguous_fields.append(
                "project_archetype"
            )

        if business_models:
            score += 0.05
        else:
            ambiguous_fields.append(
                "business_model"
            )

        if mvp_scope:
            score += 0.04
        else:
            ambiguous_fields.append(
                "mvp_scope"
            )

        if constraints:
            score += 0.03

        if (
            actors
            and all(
                actor.is_explicit
                for actor in actors
            )
        ):
            score += 0.02

        if (
            workflows
            and workflows[
                0
            ].is_explicit
        ):
            score += 0.02

        score = round(
            min(
                0.94,
                score,
            ),
            2,
        )

        blockers = [
            field_name
            for field_name
            in (
                "problem",
                "solution",
                "actors",
                "priority_workflow",
            )
            if field_name
            in missing_fields
        ]

        return ContextConfidence(
            score=score,
            missing_fields=missing_fields,
            ambiguous_fields=(
                unique_texts(
                    ambiguous_fields
                )
            ),
            blockers=blockers,
            clarification_questions=(
                self._questions(
                    [
                        *missing_fields,
                        *ambiguous_fields,
                    ],
                    language,
                )
            ),
            reasons=[
                (
                    f"context_score="
                    f"{score:.2f}"
                ),
                (
                    "Context completeness "
                    "is separate from "
                    "market validation."
                ),
            ],
        )

    def _resolve_archetypes(
        self,
        *,
        description: str,
        industry: str,
        structured: Dict[str, Any],
    ) -> Tuple[
        str,
        List[str],
    ]:
        """
        Résout l'archétype principal et les archétypes secondaires.

        Règles universelles :

        1. Les preuves explicites présentes dans la description
           et le secteur fourni par l'utilisateur sont prioritaires.

        2. L'ancien ProjectIntelligenceLayer fournit seulement
           un signal secondaire. Il ne peut pas écraser une preuve
           explicite plus forte.

        3. Une capacité IA intégrée à un robot ne transforme pas
           automatiquement le projet en simple outil analytics/IA.

        4. Un projet peut conserver plusieurs archétypes :
           hardware + SaaS + IA, marketplace + SaaS, etc.
        """
        structured_primary = clean_text(
            structured.get(
                "project_archetype"
            )
        )

        structured_secondary = unique_texts(
            self._listify(
                structured.get(
                    "secondary_archetypes"
                )
            )
        )

        structured_sector_terms = unique_texts(
            self._listify(
                structured.get(
                    "sector_tags"
                )
            )
        )

        structured_solution_terms = unique_texts(
            [
                clean_text(
                    structured.get(
                        "solution"
                    )
                ),
                clean_text(
                    structured.get(
                        "solution_type"
                    )
                ),
                clean_text(
                    structured.get(
                        "delivery_mode"
                    )
                ),
            ]
        )

        searchable_text = clean_text(
            " ".join(
                [
                    industry,
                    description,
                    *structured_sector_terms,
                    *structured_solution_terms,
                ]
            )
        )

        key = comparison_key(
            searchable_text
        )

        known_archetypes = (
            "hardware_iot",
            "b2b_workflow_saas",
            "two_sided_marketplace",
            "analytics_ai_tool",
            "ecommerce",
            "regulated_service",
            "professional_service",
            "content_community",
        )

        evidence_scores: Dict[
            str,
            float,
        ] = {
            archetype: 0.0
            for archetype in known_archetypes
        }

        final_scores: Dict[
            str,
            float,
        ] = {
            archetype: 0.0
            for archetype in known_archetypes
        }

        matched_terms: Dict[
            str,
            List[str],
        ] = {
            archetype: []
            for archetype in known_archetypes
        }

        def add_evidence(
            archetype: str,
            term: str,
            weight: float,
        ) -> None:
            normalized_term = comparison_key(
                term
            )

            if (
                not normalized_term
                or normalized_term not in key
            ):
                return

            evidence_scores.setdefault(
                archetype,
                0.0,
            )

            final_scores.setdefault(
                archetype,
                0.0,
            )

            matched_terms.setdefault(
                archetype,
                [],
            )

            evidence_scores[
                archetype
            ] += weight

            final_scores[
                archetype
            ] += weight

            matched_terms[
                archetype
            ].append(
                term
            )

        # ----------------------------------------------------------
        # Hardware / IoT
        # ----------------------------------------------------------

        for term, weight in (
            ("robot autonome", 5.0),
            ("robot mobile", 4.0),
            ("robot", 3.0),
            ("hardware", 3.0),
            ("iot", 3.0),
            ("objet connecté", 3.0),
            ("device", 2.5),
            ("équipement", 2.0),
            ("equipment", 2.0),
            ("capteur", 2.0),
            ("capteurs", 2.0),
            ("sensor", 2.0),
            ("sensors", 2.0),
            ("caméra", 1.5),
            ("camera", 1.5),
            ("batterie", 1.5),
            ("battery", 1.5),
            ("maintenance matérielle", 1.5),
            ("fabrication", 1.5),
            ("manufacturing", 1.5),
        ):
            add_evidence(
                "hardware_iot",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # SaaS B2B / outil de workflow
        # ----------------------------------------------------------

        for term, weight in (
            ("saas b2b", 5.0),
            ("logiciel saas", 4.0),
            ("b2b saas", 4.0),
            ("saas", 3.0),
            ("logiciel", 2.0),
            ("software", 2.0),
            ("tableau de bord", 2.0),
            ("dashboard", 2.0),
            ("abonnement mensuel", 2.0),
            ("subscription", 2.0),
            ("gestion des équipes", 2.0),
            ("gestion rh", 2.0),
            ("workflow", 1.5),
            ("par organisation", 1.5),
            ("par entreprise", 1.5),
            ("par site industriel", 1.5),
        ):
            add_evidence(
                "b2b_workflow_saas",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # Marketplace à deux côtés
        # ----------------------------------------------------------

        for term, weight in (
            ("marketplace", 5.0),
            ("place de marché", 5.0),
            ("mise en relation", 4.0),
            ("mettre en relation", 4.0),
            ("deux côtés", 3.0),
            ("two sided", 3.0),
            ("prestataires", 2.0),
            ("providers", 2.0),
            ("chauffeurs", 2.0),
            ("vendeurs", 2.0),
            ("acheteurs", 2.0),
            ("commission par transaction", 3.0),
            ("commission par course", 3.0),
            ("commission par réservation", 3.0),
            ("commission", 1.5),
        ):
            add_evidence(
                "two_sided_marketplace",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # IA / analytics
        # ----------------------------------------------------------

        for term, weight in (
            ("outil ia", 4.0),
            ("ai tool", 4.0),
            ("plateforme ia", 3.5),
            ("intelligence artificielle", 2.0),
            ("machine learning", 2.0),
            ("computer vision", 2.0),
            ("vision par ordinateur", 2.0),
            ("analytics", 2.0),
            ("analyse prédictive", 2.0),
            ("predictive analytics", 2.0),
            ("classification automatique", 1.5),
            ("modèle d’intelligence artificielle", 1.5),
            ("modele d intelligence artificielle", 1.5),
        ):
            add_evidence(
                "analytics_ai_tool",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # E-commerce
        # ----------------------------------------------------------

        for term, weight in (
            ("e commerce", 5.0),
            ("commerce électronique", 5.0),
            ("boutique en ligne", 4.0),
            ("online store", 4.0),
            ("panier", 2.0),
            ("catalogue produits", 2.0),
            ("catalogue de produits", 2.0),
            ("commande en ligne", 2.0),
            ("paiement en ligne", 2.0),
            ("livraison", 1.5),
        ):
            add_evidence(
                "ecommerce",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # Produit ou service réglementé
        # ----------------------------------------------------------

        for term, weight in (
            ("télémédecine", 5.0),
            ("telemedecine", 5.0),
            ("diagnostic médical", 4.0),
            ("medical diagnosis", 4.0),
            ("patient", 2.0),
            ("patients", 2.0),
            ("médecin", 2.0),
            ("medecin", 2.0),
            ("clinique", 2.0),
            ("banque", 2.5),
            ("banking", 2.5),
            ("crédit", 2.5),
            ("credit", 2.5),
            ("assurance", 2.5),
            ("insurance", 2.5),
            ("juridique", 2.0),
            ("legal", 2.0),
            ("réglementé", 2.0),
            ("regulated", 2.0),
        ):
            add_evidence(
                "regulated_service",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # Service professionnel
        # ----------------------------------------------------------

        for term, weight in (
            ("service professionnel", 4.0),
            ("professional service", 4.0),
            ("cabinet", 2.0),
            ("consultant", 2.0),
            ("consulting", 2.0),
            ("agence", 2.0),
            ("prestation", 2.0),
            ("accompagnement", 1.5),
            ("audit", 1.5),
        ):
            add_evidence(
                "professional_service",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # Communauté / contenu
        # ----------------------------------------------------------

        for term, weight in (
            ("communauté", 4.0),
            ("communaute", 4.0),
            ("community", 4.0),
            ("créateurs de contenu", 3.0),
            ("createurs de contenu", 3.0),
            ("social network", 3.0),
            ("réseau social", 3.0),
            ("publication de contenu", 2.0),
            ("membres", 1.5),
            ("abonnés", 1.5),
        ):
            add_evidence(
                "content_community",
                term,
                weight,
            )

        # ----------------------------------------------------------
        # Bonus de cohérence entre plusieurs signaux
        # ----------------------------------------------------------

        hardware_terms = {
            comparison_key(
                value
            )
            for value in matched_terms[
                "hardware_iot"
            ]
        }

        if (
            comparison_key(
                "robot"
            )
            in hardware_terms
            and any(
                comparison_key(
                    term
                )
                in hardware_terms
                for term in (
                    "capteur",
                    "capteurs",
                    "sensor",
                    "sensors",
                    "caméra",
                    "camera",
                    "batterie",
                    "battery",
                )
            )
        ):
            evidence_scores[
                "hardware_iot"
            ] += 3.0

            final_scores[
                "hardware_iot"
            ] += 3.0

        marketplace_terms = (
            matched_terms[
                "two_sided_marketplace"
            ]
        )

        if (
            len(
                unique_texts(
                    marketplace_terms
                )
            )
            >= 2
        ):
            evidence_scores[
                "two_sided_marketplace"
            ] += 2.0

            final_scores[
                "two_sided_marketplace"
            ] += 2.0

        saas_terms = (
            matched_terms[
                "b2b_workflow_saas"
            ]
        )

        if (
            any(
                comparison_key(
                    term
                )
                in {
                    comparison_key(
                        "saas"
                    ),
                    comparison_key(
                        "logiciel saas"
                    ),
                    comparison_key(
                        "saas b2b"
                    ),
                }
                for term in saas_terms
            )
            and any(
                comparison_key(
                    term
                )
                in {
                    comparison_key(
                        "abonnement mensuel"
                    ),
                    comparison_key(
                        "subscription"
                    ),
                    comparison_key(
                        "par organisation"
                    ),
                    comparison_key(
                        "par entreprise"
                    ),
                    comparison_key(
                        "par site industriel"
                    ),
                }
                for term in saas_terms
            )
        ):
            evidence_scores[
                "b2b_workflow_saas"
            ] += 2.0

            final_scores[
                "b2b_workflow_saas"
            ] += 2.0

        # ----------------------------------------------------------
        # Ancienne inférence : simple prior, jamais autorité absolue
        # ----------------------------------------------------------

        generic_archetype_keys = {
            comparison_key(
                value
            )
            for value in (
                "",
                "generic",
                "generic digital product",
                "generic_digital_product",
                "application",
                "app",
                "platform",
                "plateforme",
                "startup",
                "business",
            )
        }

        structured_primary_key = comparison_key(
            structured_primary
        )

        if (
            structured_primary
            and structured_primary_key
            not in generic_archetype_keys
        ):
            final_scores.setdefault(
                structured_primary,
                0.0,
            )

            evidence_scores.setdefault(
                structured_primary,
                0.0,
            )

            # Petit prior seulement.
            final_scores[
                structured_primary
            ] += 1.0

        for secondary in structured_secondary:
            secondary_key = comparison_key(
                secondary
            )

            if (
                not secondary
                or secondary_key
                in generic_archetype_keys
            ):
                continue

            final_scores.setdefault(
                secondary,
                0.0,
            )

            evidence_scores.setdefault(
                secondary,
                0.0,
            )

            final_scores[
                secondary
            ] += 0.40

        # ----------------------------------------------------------
        # Fallback si aucun signal explicite
        # ----------------------------------------------------------

        strongest_explicit_score = max(
            evidence_scores.values(),
            default=0.0,
        )

        if strongest_explicit_score <= 0:
            if (
                structured_primary
                and structured_primary_key
                not in generic_archetype_keys
            ):
                secondary_values = unique_texts(
                    [
                        *structured_secondary,
                    ]
                )

                return (
                    structured_primary,
                    [
                        value
                        for value
                        in secondary_values
                        if comparison_key(
                            value
                        )
                        != structured_primary_key
                    ][:3],
                )

            return (
                "generic_digital_product",
                [],
            )

        # ----------------------------------------------------------
        # Classement déterministe
        # ----------------------------------------------------------

        tie_break_priority = {
            "hardware_iot": 0,
            "two_sided_marketplace": 1,
            "ecommerce": 2,
            "regulated_service": 3,
            "b2b_workflow_saas": 4,
            "analytics_ai_tool": 5,
            "professional_service": 6,
            "content_community": 7,
        }

        eligible_archetypes = [
            archetype
            for archetype, score
            in final_scores.items()
            if (
                score > 0
                or evidence_scores.get(
                    archetype,
                    0.0,
                ) > 0
            )
        ]

        ranked = sorted(
            eligible_archetypes,
            key=lambda archetype: (
                -final_scores.get(
                    archetype,
                    0.0,
                ),
                -evidence_scores.get(
                    archetype,
                    0.0,
                ),
                tie_break_priority.get(
                    archetype,
                    100,
                ),
                archetype,
            ),
        )

        primary_archetype = (
            ranked[0]
            if ranked
            else "generic_digital_product"
        )

        primary_score = final_scores.get(
            primary_archetype,
            0.0,
        )

        secondary_archetypes: List[str] = []

        for candidate in ranked[1:]:
            candidate_evidence = (
                evidence_scores.get(
                    candidate,
                    0.0,
                )
            )

            candidate_score = (
                final_scores.get(
                    candidate,
                    0.0,
                )
            )

            # Un secondaire doit disposer d'une vraie preuve
            # ou représenter une part significative du projet.
            if (
                candidate_evidence < 1.5
                and candidate_score
                < primary_score * 0.30
            ):
                continue

            secondary_archetypes.append(
                candidate
            )

            if (
                len(
                    secondary_archetypes
                )
                >= 3
            ):
                break

        return (
            primary_archetype,
            unique_texts(
                secondary_archetypes
            ),
        )


    def _looks_like_actor_phrase(
        self,
        value: str,
    ) -> bool:
        """
        Détermine si un fragment introduit probablement un nouvel acteur.

        Un objet, un produit ou un matériel ne doit pas devenir un acteur
        uniquement parce qu'il apparaît après une virgule ou « ou ».
        """
        text = clean_text(value)
        key = comparison_key(text)

        if not key:
            return False

        if self._actor_role(text) != ActorRole.OTHER:
            return True

        return any(
            re.search(
                rf"\b{re.escape(comparison_key(marker))}\b",
                key,
            )
            is not None
            for marker in self.ACTOR_HEAD_MARKERS
            if comparison_key(marker)
        )

    def _split_actor_list(
        self,
        value: Any,
    ) -> List[str]:
        """
        Découpe une liste d'acteurs sans transformer leurs objets
        ou leurs catégories de produits en acteurs autonomes.

        Exemple :

        « entreprises vendeuses et entreprises acheteuses de pièces,
        matériaux ou équipements »

        devient deux acteurs, et non quatre.
        """
        text = clean_text(value)

        if not text:
            return []

        fragments = [
            clean_text(part)
            for part in re.split(
                r"\s*(?:,|;|\bet\b|\band\b|"
                r"\bou\b|\bor\b|\+|/)\s*",
                text,
                flags=re.IGNORECASE,
            )
            if clean_text(part)
        ]

        actors: List[str] = []

        for fragment in fragments:
            if (
                not actors
                or self._looks_like_actor_phrase(
                    fragment
                )
            ):
                actors.append(fragment)
                continue

            actors[-1] = clean_text(
                f"{actors[-1]}, {fragment}"
            )

        return actors

    def _actor_role(
        self,
        name: str,
    ) -> ActorRole:
        """
        Résout le rôle métier à partir des signaux les plus précis.

        Les mots génériques comme « entreprise » ou « société » ne
        suffisent jamais à classer automatiquement un acteur comme acheteur.
        """
        key = comparison_key(name)

        if not key:
            return ActorRole.OTHER

        role_signals = (
            (
                ActorRole.REGULATORY_BLOCKER,
                (
                    "autorite",
                    "regulateur",
                    "regulator",
                    "administration",
                    "ministere",
                ),
            ),
            (
                ActorRole.PAYER,
                (
                    "payeur",
                    "payer",
                    "financeur",
                    "paie",
                    "paye",
                    "finance",
                    "souscrit",
                ),
            ),
            (
                ActorRole.DECISION_MAKER,
                (
                    "decideur",
                    "responsable achat",
                    "responsable des achats",
                    "procurement manager",
                    "approbateur",
                    "valideur",
                ),
            ),
            (
                ActorRole.PROVIDER,
                (
                    "vendeur",
                    "vendeuse",
                    "vendeurs",
                    "vendeuses",
                    "fournisseur",
                    "supplier",
                    "seller",
                    "provider",
                    "prestataire",
                    "producteur",
                    "offreur",
                    "met en vente",
                    "met a disposition",
                    "publie ses",
                ),
            ),
            (
                ActorRole.BUYER,
                (
                    "acheteur",
                    "acheteuse",
                    "acheteurs",
                    "acheteuses",
                    "acquereur",
                    "buyer",
                    "purchaser",
                    "client acheteur",
                    "recherche des",
                    "recherche les",
                    "reserve",
                    "commande",
                ),
            ),
            (
                ActorRole.MAINTAINER,
                (
                    "maintenance",
                    "mainteneur",
                    "reparateur",
                    "installateur",
                    "integrateur",
                ),
            ),
            (
                ActorRole.OPERATOR,
                (
                    "technicien",
                    "ouvrier",
                    "operateur",
                    "operator",
                    "employee",
                    "employe",
                    "agent terrain",
                ),
            ),
            (
                ActorRole.PARTNER,
                (
                    "partenaire",
                    "partner",
                    "centre de recherche",
                    "universite",
                ),
            ),
            (
                ActorRole.BENEFICIARY,
                (
                    "beneficiaire",
                    "patient",
                    "eleve",
                    "citoyen",
                    "usager final",
                ),
            ),
        )

        for role, signals in role_signals:
            if any(
                comparison_key(signal) in key
                for signal in signals
            ):
                return role

        if any(
            comparison_key(term) in key
            for term in (
                "entreprise",
                "societe",
                "company",
                "organisation",
                "organization",
                "cooperative",
                "exploitation",
                "pepiniere",
                "proprietaire",
                "owner",
                "dirigeant",
                "responsable",
                "manager",
            )
        ):
            return ActorRole.OTHER

        if any(
            term in key
            for term in (
                "utilisateur",
                "user",
                "usager",
                "client",
                "customer",
            )
        ):
            return ActorRole.USER

        return ActorRole.OTHER

    def _archetype_confidence(
        self,
        *,
        primary_archetype: str,
        secondary_archetypes: Sequence[str],
        description: str,
        industry: str,
    ) -> float:
        """
        Estime la confiance d'archétype à partir de signaux explicites.
        """
        if (
            not primary_archetype
            or primary_archetype
            == "generic_digital_product"
        ):
            return 0.25

        searchable = comparison_key(
            f"{industry} {description}"
        )

        marker_groups = {
            "two_sided_marketplace": (
                "marketplace",
                "place de marche",
                "mise en relation",
                "vendeur",
                "acheteur",
                "commission",
            ),
            "hardware_iot": (
                "robot",
                "hardware",
                "iot",
                "capteur",
                "sensor",
                "equipement",
            ),
            "b2b_workflow_saas": (
                "saas",
                "logiciel",
                "workflow",
                "tableau de bord",
                "dashboard",
                "abonnement",
            ),
            "analytics_ai_tool": (
                "intelligence artificielle",
                "machine learning",
                "analytics",
                "analyse predictive",
                "computer vision",
            ),
            "ecommerce": (
                "e commerce",
                "boutique en ligne",
                "panier",
                "commande",
                "livraison",
            ),
            "regulated_service": (
                "patient",
                "medecin",
                "banque",
                "assurance",
                "juridique",
                "reglemente",
            ),
            "professional_service": (
                "consultant",
                "cabinet",
                "agence",
                "prestation",
                "audit",
            ),
            "content_community": (
                "communaute",
                "community",
                "createur",
                "reseau social",
                "contenu",
            ),
        }

        matched = sum(
            1
            for marker in marker_groups.get(
                primary_archetype,
                (),
            )
            if comparison_key(marker) in searchable
        )

        confidence = 0.55 + min(
            0.35,
            matched * 0.07,
        )

        if secondary_archetypes:
            confidence -= min(
                0.10,
                len(secondary_archetypes) * 0.03,
            )

        return round(
            max(
                0.0,
                min(
                    0.95,
                    confidence,
                ),
            ),
            2,
        )

    def _extract_transaction_unit(
        self,
        *,
        sentences: Sequence[str],
        actors: Sequence[ActorContext],
        workflows: Sequence[WorkflowContext],
    ) -> TransactionUnitContext:
        """
        Extrait l'unité centrale de valeur ou d'opération du projet.
        """
        supply_actor = next(
            (
                actor.name
                for actor in actors
                if actor.role
                == ActorRole.PROVIDER
            ),
            "",
        )

        demand_actor = next(
            (
                actor.name
                for actor in actors
                if actor.role
                in {
                    ActorRole.BUYER,
                    ActorRole.USER,
                    ActorRole.BENEFICIARY,
                }
            ),
            "",
        )

        initiation_patterns = (
            (
                re.compile(
                    r"\bpubl(?:ier|ie|ient|ies)?\b"
                    r"|\bpost(?:e|ent|s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "publier",
            ),
            (
                re.compile(
                    r"\bpropos(?:er|e|ent)?\b"
                    r"|\boffr(?:ir|e|ent)?\b"
                    r"|\blist(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "proposer",
            ),
            (
                re.compile(
                    r"\bsoumet(?:tre|s|tent)?\b"
                    r"|\bdepos(?:er|e|ent)?\b"
                    r"|\bdépos(?:er|e|ent)?\b",
                    re.IGNORECASE,
                ),
                "soumettre",
            ),
            (
                re.compile(
                    r"\bdemand(?:er|e|ent)?\b"
                    r"|\brequest(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "demander",
            ),
        )

        completion_patterns = (
            (
                re.compile(
                    r"\bréserv(?:er|e|ent|ation)?\b"
                    r"|\breserv(?:er|e|ent|ation)?\b"
                    r"|\bbook(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "réserver",
            ),
            (
                re.compile(
                    r"\bachet(?:er|e|ent)?\b"
                    r"|\bbuy(?:s|ing)?\b"
                    r"|\bbought\b",
                    re.IGNORECASE,
                ),
                "acheter",
            ),
            (
                re.compile(
                    r"\bcommand(?:er|e|ent)?\b"
                    r"|\border(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "commander",
            ),
            (
                re.compile(
                    r"\bconclu(?:re|t|ent)?\b"
                    r"|\bfinalis(?:er|e|ent)?\b"
                    r"|\bcomplete(?:s|d|ing)?\b",
                    re.IGNORECASE,
                ),
                "conclure la transaction",
            ),
            (
                re.compile(
                    r"\bvalid(?:er|e|ent)?\b"
                    r"|\bapprouv(?:er|e|ent)?\b",
                    re.IGNORECASE,
                ),
                "valider",
            ),
            (
                re.compile(
                    r"\bpay(?:er|e|ent)?\b"
                    r"|\bpaie(?:nt)?\b"
                    r"|\bpaiement\b"
                    r"|\bpayment\b",
                    re.IGNORECASE,
                ),
                "payer",
            ),
            (
                re.compile(
                    r"\blivr(?:er|e|ent|aison)?\b"
                    r"|\bdeliver(?:s|ed|ing|y)?\b",
                    re.IGNORECASE,
                ),
                "livrer",
            ),
        )

        initiation_action = ""
        initiation_sentence = ""
        initiation_match: re.Match[str] | None = None

        completion_action = ""
        completion_sentence = ""

        for sentence in sentences:
            for pattern, action in initiation_patterns:
                match = pattern.search(sentence)

                if not match:
                    continue

                initiation_action = action
                initiation_sentence = sentence
                initiation_match = match
                break

            if initiation_action:
                break

        for sentence in sentences:
            for pattern, action in completion_patterns:
                if not pattern.search(sentence):
                    continue

                completion_action = action
                completion_sentence = sentence
                break

            if completion_action:
                break

        object_text = ""

        if (
            initiation_sentence
            and initiation_match is not None
        ):
            object_text = self._transaction_object(
                initiation_sentence,
                initiation_match,
            )

        if not object_text:
            for workflow in workflows:
                if workflow.object:
                    object_text = workflow.object
                    break

        if not initiation_action and workflows:
            initiation_action = workflows[0].action

        if (
            not object_text
            and not initiation_action
            and not completion_action
        ):
            return TransactionUnitContext()

        parts: List[str] = []

        if initiation_action and object_text:
            parts.append(
                f"{initiation_action} {object_text}"
            )
        elif object_text:
            parts.append(object_text)
        elif initiation_action:
            parts.append(initiation_action)

        if completion_action:
            parts.append(completion_action)

        description = clean_text(
            ", puis ".join(parts)
        )

        signal_count = sum(
            bool(value)
            for value in (
                object_text,
                initiation_action,
                completion_action,
                supply_actor,
                demand_actor,
            )
        )

        return TransactionUnitContext(
            name=description,
            description=description,
            object=object_text,
            supply_actor=supply_actor,
            demand_actor=demand_actor,
            initiation_action=initiation_action,
            completion_action=completion_action,
            value_exchanged=object_text,
            is_explicit=bool(
                initiation_sentence
                or completion_sentence
            ),
            confidence=round(
                min(
                    0.95,
                    0.35
                    + signal_count * 0.11,
                ),
                2,
            ),
        )

    def _transaction_object(
        self,
        sentence: str,
        action_match: re.Match[str],
    ) -> str:
        """
        Extrait l'objet immédiat de l'action d'initiation.
        """
        tail = clean_text(
            sentence[
                action_match.end():
            ]
        )

        tail = re.split(
            r"\s+(?:avec|contenant|qui|afin de|pour|"
            r"puis|ensuite|and|with|that)\s+",
            tail,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        tail = re.split(
            r"\s+et\s+(?:le|la|les|l['’])",
            tail,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        tail = re.sub(
            r"^(?:un|une|des|du|de la|de l['’]|le|la|les|"
            r"a|an|the)\s+",
            "",
            tail.strip(
                " .,:;"
            ),
            flags=re.IGNORECASE,
        )

        return self._compact(
            tail,
            120,
        )

    def _preferred_actor(
        self,
        actors: Sequence[
            ActorContext
        ],
    ) -> str:
        preferred_roles = (
            ActorRole.OPERATOR,
            ActorRole.USER,
            ActorRole.BENEFICIARY,
            ActorRole.BUYER,
        )

        for role in preferred_roles:
            for actor in actors:
                if actor.role == role:
                    return actor.name

        return (
            actors[0].name
            if actors
            else ""
        )

    def _canonical_action(
        self,
        text: str,
    ) -> str:
        action, _match = (
            self._canonical_action_with_match(
                text
            )
        )

        return action

    def _canonical_action_with_match(
        self,
        text: str,
    ) -> Tuple[
        str,
        re.Match[str] | None,
    ]:
        for pattern, action in (
            self.ACTION_PATTERNS
        ):
            match = pattern.search(
                text
            )

            if match:
                return (
                    action,
                    match,
                )

        return (
            "",
            None,
        )

    def _workflow_score(
        self,
        sentence: str,
        action: str = "",
    ) -> int:
        action = (
            action
            or self._canonical_action(
                sentence
            )
        )

        score = self.ACTION_PRIORITY.get(
            action,
            50,
        )

        if self._contains_any(
            sentence,
            (
                "afin de",
                "pour",
                "so that",
                "in order to",
            ),
        ):
            score += 8

        if self._contains_any(
            sentence,
            (
                "alerte",
                "alert",
                "résultat",
                "result",
                "rapport",
                "confirmation",
            ),
        ):
            score += 4

        if self._contains_any(
            sentence,
            self.MVP_MARKERS,
        ):
            score -= 40

        if self._is_problem_sentence(
            sentence
        ):
            score -= 100

        return score

    def _action_object(
        self,
        sentence: str,
        action_match: re.Match[str],
    ) -> str:
        tail = sentence[
            action_match.end():
        ]

        tail = re.split(
            r"\s+(?:afin de|pour|"
            r"so that|in order to)\s+",
            tail,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        tail = re.split(
            r"\s+(?:et|and)\s+"
            r"(?:transmet|envoi|alert|notifi)",
            tail,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        return self._compact(
            tail.strip(
                " .,:;"
            ),
            150,
        )

    def _result_after_action(
        self,
        sentence: str,
        action_match: re.Match[str],
        action: str,
    ) -> str:
        connectors = list(
            re.finditer(
                r"\s+(?:afin de|pour|"
                r"so that|in order to)\s+",
                sentence,
                flags=re.IGNORECASE,
            )
        )

        for connector in connectors:
            if (
                connector.start()
                <= action_match.start()
            ):
                continue

            clause = self._compact(
                sentence[
                    connector.end():
                ].strip(
                    " .,:;"
                ),
                180,
            )

            if not clause:
                continue

            if comparison_key(
                clause
            ).startswith(
                comparison_key(
                    action
                )
            ):
                continue

            return clause

        return ""

    def _supporting_result(
        self,
        candidates: Sequence[
            Dict[str, Any]
        ],
        primary: Dict[str, Any],
    ) -> str:
        result_actions = {
            "détecter",
            "analyser",
            "classifier",
            "mesurer",
        }

        ordered = sorted(
            candidates,
            key=lambda item: (
                item["index"]
            ),
        )

        for candidate in ordered:
            if candidate is primary:
                continue

            if (
                candidate["action"]
                not in result_actions
            ):
                continue

            object_text = (
                self._action_object(
                    candidate[
                        "sentence"
                    ],
                    candidate[
                        "match"
                    ],
                )
            )

            if not object_text:
                continue

            return self._compact(
                (
                    f"{candidate['action']} "
                    f"{object_text}"
                ),
                180,
            )

        return ""

    def _supporting_output(
        self,
        candidates: Sequence[
            Dict[str, Any]
        ],
    ) -> str:
        output_actions = {
            "transmettre",
            "alerter",
            "publier",
        }

        ordered = sorted(
            candidates,
            key=lambda item: (
                item["index"]
            ),
        )

        for candidate in ordered:
            if (
                candidate["action"]
                not in output_actions
            ):
                continue

            phrase = self._output_phrase(
                candidate[
                    "sentence"
                ]
            )

            if phrase:
                return phrase

        return ""

    def _output_phrase(
        self,
        sentence: str,
    ) -> str:
        transmission_pattern = re.compile(
            r"(?:transmet(?:tre|s|tent)?|"
            r"envoi(?:e|er|ent)?)\s+(.+)",
            re.IGNORECASE,
        )

        match = transmission_pattern.search(
            sentence
        )

        if match:
            value = match.group(
                1
            ).strip(
                " .,:;"
            )

            value = re.sub(
                r"\s+(?:et|and)\s+"
                r"envoi(?:e|er|ent)?\s+",
                " et ",
                value,
                flags=re.IGNORECASE,
            )

            return self._compact(
                value,
                180,
            )

        fallback = re.search(
            r"(?:alerte|notification|rapport|"
            r"dashboard|tableau de bord).+",
            sentence,
            flags=re.IGNORECASE,
        )

        if fallback:
            return self._compact(
                fallback.group(
                    0
                ).strip(
                    " .,:;"
                ),
                180,
            )

        return ""

    def _workflow_name(
        self,
        *,
        action: str,
        object_text: str,
        result: str,
        output: str,
    ) -> str:
        text = clean_text(
            " ".join(
                part
                for part in (
                    action,
                    object_text,
                )
                if part
            )
        )

        if result:
            text = (
                f"{text} afin de "
                f"{result}"
                if text
                else result
            )

        if output:
            text = (
                f"{text}, puis produire "
                f"{output}"
                if text
                else output
            )

        return self._compact(
            text,
            260,
        )

    def _workflow_is_subsumed(
        self,
        workflow: WorkflowContext,
        existing: Sequence[
            WorkflowContext
        ],
    ) -> bool:
        key = comparison_key(
            workflow.sentence
        )

        for current in existing:
            current_key = comparison_key(
                current.sentence
            )

            if (
                key
                and current_key
                and (
                    key in current_key
                    or current_key in key
                )
            ):
                return True

            if (
                workflow.action
                == current.action
                and comparison_key(
                    workflow.object
                )
                == comparison_key(
                    current.object
                )
            ):
                return True

        return False

    def _is_problem_sentence(
        self,
        sentence: str,
    ) -> bool:
        if self._contains_any(
            sentence,
            self.PROBLEM_MARKERS,
        ):
            return True

        key = comparison_key(
            sentence
        )

        return key.startswith(
            (
                "le probleme",
                "la difficulte",
                "the problem",
                "the current process",
            )
        )

    def _normalize_scope_item(
        self,
        value: str,
    ) -> str:
        text = clean_text(
            value
        )

        if not text:
            return ""

        prefix_pattern = (
            r"^(?:le|la|the)?\s*"
            r"(?:premier|première|premiere|first)?\s*"
            r"(?:mvp|version|prototype)?\s*"
            r"(?:sera|serait|is|will be)?\s*"
            r"(?:limité|limitee|limitée|limited|"
            r"concentré|concentree|concentrée|focused)?\s*"
            r"(?:à|sur|to|on|only)?\s*"
            r"[:\-]?\s*"
        )

        for _ in range(
            2
        ):
            cleaned = re.sub(
                prefix_pattern,
                "",
                text,
                flags=re.IGNORECASE,
            )

            if cleaned == text:
                break

            text = cleaned

        return clean_text(
            text.strip(
                " .,:;"
            )
        )

    def _semantic_unique(
        self,
        values: Sequence[str],
        *,
        max_items: int,
    ) -> List[str]:
        output: List[str] = []
        keys: List[str] = []

        for value in unique_texts(
            values
        ):
            cleaned = clean_text(
                value
            ).strip(
                " .,:;"
            )

            key = comparison_key(
                cleaned
            )

            if not key:
                continue

            duplicate = any(
                (
                    key == existing
                    or key in existing
                    or existing in key
                )
                for existing in keys
            )

            if duplicate:
                continue

            output.append(
                cleaned
            )

            keys.append(
                key
            )

            if len(output) >= max_items:
                break

        return output
    def _extract_business_models(
        self,
        *,
        sentences: Sequence[str],
        structured: Dict[str, Any],
        project_context: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> Tuple[
        List[str],
        List[str],
    ]:
        """
        Sépare les modèles économiques explicitement fournis
        par l'utilisateur des hypothèses produites par les anciennes
        couches d'intelligence.

        Retourne :
        - tous les modèles économiques utilisables comme hypothèses ;
        - uniquement les modèles explicitement fournis.

        Une hypothèse inférée ne doit pas augmenter artificiellement
        le Context Confidence Score.
        """
        explicit_values: List[str] = []

        for source in (
            project_context,
            analysis_data,
        ):
            explicit_values.extend(
                self._listify(
                    source.get(
                        "business_model"
                    )
                )
            )

            explicit_values.extend(
                self._listify(
                    source.get(
                        "business_model_hypotheses"
                    )
                )
            )

            explicit_values.extend(
                self._listify(
                    source.get(
                        "revenue_model"
                    )
                )
            )

            explicit_values.extend(
                self._listify(
                    source.get(
                        "monetization"
                    )
                )
            )

        explicit_values.extend(
            sentence
            for sentence in sentences
            if self._contains_any(
                sentence,
                self.BUSINESS_MARKERS,
            )
        )

        explicit_models = unique_texts(
            explicit_values
        )

        inferred_models = unique_texts(
            self._listify(
                structured.get(
                    "business_model"
                )
            )
            + self._listify(
                structured.get(
                    "revenue_model"
                )
            )
        )

        all_models = unique_texts(
            [
                *explicit_models,
                *inferred_models,
            ]
        )

        return (
            all_models,
            explicit_models,
        )

    def _constraints(
        self,
        *,
        sentences: Sequence[str],
        project_context: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[str]:
        values = (
            self._listify(
                project_context.get(
                    "constraints"
                )
            )
            + self._listify(
                analysis_data.get(
                    "constraints"
                )
            )
        )

        for sentence in sentences:
            if not self._contains_any(
                sentence,
                self.CONSTRAINT_MARKERS,
            ):
                continue

            value = (
                sentence.split(
                    ":",
                    1,
                )[1]
                if ":" in sentence
                else sentence
            )

            values.extend(
                self._split_list(
                    value
                )
            )

        return unique_texts(
            values
        )[:12]

    def _delivery_mode(
        self,
        text: str,
    ) -> str:
        key = comparison_key(
            text
        )

        modes: List[str] = []

        if any(
            term in key
            for term in (
                "robot",
                "capteur",
                "sensor",
                "device",
                "hardware",
            )
        ):
            modes.append(
                "hardware_iot"
            )

        if any(
            term in key
            for term in (
                "application",
                "app",
                "mobile",
            )
        ):
            modes.append(
                "mobile_app"
            )

        if any(
            term in key
            for term in (
                "dashboard",
                "tableau de bord",
                "web",
                "saas",
            )
        ):
            modes.append(
                "web_saas"
            )

        return "+".join(
            unique_texts(
                modes
            )
        )

    def _capabilities(
        self,
        text: str,
    ) -> List[str]:
        key = comparison_key(
            text
        )

        mapping = {
            "camera": "caméra",
            "capteur": "capteurs",
            "sensor": "capteurs",
            "intelligence artificielle": (
                "intelligence artificielle"
            ),
            "machine learning": (
                "machine learning"
            ),
            "computer vision": (
                "vision par ordinateur"
            ),
            "dashboard": (
                "tableau de bord"
            ),
            "tableau de bord": (
                "tableau de bord"
            ),
            "alerte": "alertes",
            "notification": (
                "notifications"
            ),
        }

        return unique_texts(
            label
            for term, label
            in mapping.items()
            if term in key
        )

    def _deployment_environment(
        self,
        sentences: Sequence[str],
    ) -> List[str]:
        terms = (
            "serre",
            "greenhouse",
            "terrain",
            "field",
            "usine",
            "factory",
            "hôpital",
            "hospital",
            "école",
            "school",
            "cloud",
            "offline",
            "sur site",
        )

        return unique_texts(
            sentence
            for sentence in sentences
            if self._contains_any(
                sentence,
                terms,
            )
        )[:6]

    def _regulatory_flags(
        self,
        text: str,
    ) -> List[str]:
        key = comparison_key(
            text
        )

        mapping = {
            "health": (
                "patient",
                "medecin",
                "diagnostic",
                "medical",
                "clinique",
            ),
            "finance": (
                "banque",
                "bank",
                "paiement",
                "payment",
                "credit",
                "assurance",
            ),
            "legal": (
                "juridique",
                "legal",
                "loi",
                "law",
                "tribunal",
            ),
            "children": (
                "enfant",
                "children",
                "mineur",
                "minor",
            ),
        }

        return [
            domain
            for domain, terms
            in mapping.items()
            if any(
                term in key
                for term in terms
            )
        ]

    def _questions(
        self,
        fields: Sequence[str],
        language: str,
    ) -> List[str]:
        french_questions = {
            "problem": (
                "Quel problème concret et fréquent "
                "souhaitez-vous résoudre ?"
            ),
            "solution": (
                "Comment la solution résout-elle "
                "concrètement ce problème ?"
            ),
            "actors": (
                "Qui utilisera la solution et qui "
                "prendra la décision d’achat ?"
            ),
            "priority_workflow": (
                "Quelle action principale l’utilisateur "
                "doit-il accomplir de bout en bout ?"
            ),
            "target_region": (
                "Dans quelle région ou quel pays "
                "le projet sera-t-il lancé ?"
            ),
            "project_archetype": (
                "S’agit-il principalement d’un logiciel, "
                "d’une marketplace, d’un service ou "
                "d’un produit matériel ?"
            ),
            "business_model": (
                "Qui paiera et selon quel modèle "
                "de revenu ?"
            ),
            "mvp_scope": (
                "Quel est le périmètre exact de la "
                "première version testable ?"
            ),
        }

        english_questions = {
            "problem": (
                "What concrete and recurring problem "
                "do you want to solve?"
            ),
            "solution": (
                "How does the solution solve that "
                "problem in practice?"
            ),
            "actors": (
                "Who will use the solution and who "
                "will make the buying decision?"
            ),
            "priority_workflow": (
                "What end-to-end action must the "
                "user complete?"
            ),
            "target_region": (
                "In which country or region will "
                "the project launch?"
            ),
            "project_archetype": (
                "Is this mainly software, a marketplace, "
                "a service, or a hardware product?"
            ),
            "business_model": (
                "Who will pay and through which "
                "revenue model?"
            ),
            "mvp_scope": (
                "What is the exact scope of the "
                "first testable version?"
            ),
        }

        mapping = (
            english_questions
            if language == "en"
            else french_questions
        )

        return unique_texts(
            mapping.get(
                field,
                field,
            )
            for field in fields
        )[:8]

    def _is_scope_only(
        self,
        text: str,
    ) -> bool:
        return (
            self._contains_any(
                text,
                self.MVP_MARKERS,
            )
            and not self._canonical_action(
                text
            )
        )

    def _clean_actor(
        self,
        value: str,
    ) -> str:
        text = re.sub(
            r"^(?:les|des|aux|the|a|an)\s+",
            "",
            clean_text(
                value
            ),
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s+(?:en|dans|in)\s+"
            r"(?:tunisie|tunisia|europe|"
            r"afrique|africa).*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return clean_text(
            text.strip(
                " .,:;"
            )
        )

    def _split_list(
        self,
        value: Any,
    ) -> List[str]:
        text = clean_text(
            value
        )

        if not text:
            return []

        return [
            clean_text(
                part
            )
            for part in re.split(
                r"\s*(?:,|;|\bet\b|\band\b|"
                r"\bou\b|\bor\b|\+|/)\s*",
                text,
                flags=re.IGNORECASE,
            )
            if clean_text(
                part
            )
        ]

    def _listify(
        self,
        value: Any,
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            return [
                value
            ]

        if isinstance(
            value,
            dict,
        ):
            return unique_texts(
                item
                for item
                in value.values()
                if isinstance(
                    item,
                    str,
                )
            )

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            output: List[str] = []

            for item in value:
                if isinstance(
                    item,
                    dict,
                ):
                    output.extend(
                        clean_text(
                            item.get(
                                key
                            )
                        )
                        for key in (
                            "name",
                            "label",
                            "title",
                            "value",
                        )
                        if clean_text(
                            item.get(
                                key
                            )
                        )
                    )

                elif clean_text(
                    item
                ):
                    output.append(
                        clean_text(
                            item
                        )
                    )

            return unique_texts(
                output
            )

        cleaned = clean_text(
            value
        )

        return [
            cleaned
        ] if cleaned else []

    def _contains_any(
        self,
        text: str,
        markers: Iterable[str],
    ) -> bool:
        key = comparison_key(
            text
        )

        return any(
            comparison_key(
                marker
            )
            in key
            for marker in markers
        )

    def _sentences(
        self,
        text: str,
    ) -> List[str]:
        return unique_texts(
            part
            for part in re.split(
                r"(?<=[.!?])\s+|\n+",
                clean_text(
                    text
                ),
            )
            if clean_text(
                part
            )
        )

    def _compact(
        self,
        text: str,
        limit: int = 220,
    ) -> str:
        text = clean_text(
            text
        )

        if len(
            text
        ) <= limit:
            return text

        head = text[
            : limit - 3
        ]

        if " " in head:
            head = head.rsplit(
                " ",
                1,
            )[0]

        return clean_text(
            head
            + "..."
        )


project_context_extractor = (
    ProjectContextExtractor()
)