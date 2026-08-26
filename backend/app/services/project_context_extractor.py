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
from app.services.scope_polarity import is_scope_exclusion_statement
from app.services.constraint_semantics import (
    has_explicit_scope_reference,
    is_constraint_statement,
)
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
                r"\br(?:e|\u00e9)serv"
                r"(?:er|e|ent|ait|aient|era|eront|ation)?\b"
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
                r"|\bnotifi(?:er|e|es|ent|ait|ant|cation)\b"
                r"|\bnotif(?:y|ies|ied|ying)\b",
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
        "supervisor",
        "supervisors",
        "superviseur",
        "superviseurs",
        "superviseuse",
        "superviseuses",
        "coordinator",
        "coordinators",
        "coordinateur",
        "coordinateurs",
        "coordinatrice",
        "coordinatrices",
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
        "contractor",
        "contractors",
        "consultant",
        "consultants",
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

        structured = dict(
            intelligence.get(
                "structured_project_context"
            )
            or {}
        )

        explicit_sections = (
            self._explicit_semantic_sections(
                description
            )
        )

        narrative_sections = (
            self._narrative_semantic_sections(
                description
            )
        )

        for (
            field_name,
            narrative_values,
        ) in narrative_sections.items():
            explicit_sections[
                field_name
            ] = unique_texts(
                [
                    *explicit_sections.get(
                        field_name,
                        [],
                    ),
                    *narrative_values,
                ]
            )

        # Explicit user facts outrank inferred structured context.
        for field_name in (
            "solution",
            "value_proposition",
        ):
            explicit_values = (
                explicit_sections.get(
                    field_name
                )
                or []
            )

            if explicit_values:
                structured[
                    field_name
                ] = explicit_values[0]

        for field_name in (
            "input_data",
            "output_decision",
            "human_oversight",
            "maintenance_model",
            "deployment_environment",
        ):
            explicit_values = (
                explicit_sections.get(
                    field_name
                )
                or []
            )

            if explicit_values:
                structured[
                    field_name
                ] = explicit_values

        archetype_context = (
            intelligence.get(
                "archetype_context"
            )
            or {}
        )

        sentences = self._sentences(
            description
        )

        clarification_facts = (
            self._canonical_clarification_facts(
                project_context=project_context,
                idea_readiness=idea_readiness,
                analysis_data=analysis_data,
                structured=structured,
            )
        )

        actors = self._extract_explicit_actors(
            description=description,
            project_context=project_context,
            analysis_data=analysis_data,
        )

        actors = (
            self._reconcile_fresh_declared_actor_authority(
                actors=actors,
                description=description,
            )
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
            language=language,
        )

        # U2 canonical workflow actor membership authority.
        #
        # Explicit business actors discovered while resolving
        # workflows must join the canonical actor registry before
        # transaction and public role projections consume it.
        actors = self._reconcile_workflow_actor_membership(
            actors=actors,
            workflows=workflows,
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
            clarification_facts=clarification_facts,
        )

        # Canonical payer and decision-maker name lists are
        # projections of canonical ActorContext records.
        #
        # Do not re-inject raw declared-role pairs here: doing so would
        # bypass actor identity resolution and recreate lexical aliases
        # that were already collapsed by _extract_explicit_actors().
        #
        # Actor identity is role-aware, so the same real-world actor
        # can still legitimately appear once as PAYER and once as
        # DECISION_MAKER when both relations were explicitly declared.
        payer_names = unique_texts(
            actor.name
            for actor in actors
            if actor.role
            == ActorRole.PAYER
        )

        decision_maker_names = unique_texts(
            actor.name
            for actor in actors
            if actor.role
            == ActorRole.DECISION_MAKER
        )

        # Historical compatibility fallback remains payer-only.
        # It must never manufacture decision-maker authority.
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
            decision_maker_actor_names=decision_maker_names,
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
            input_data=(
                self._canonical_requirement_values(
                    structured,
                    "input_data",
                )
            ),
            output_decision=(
                self._canonical_requirement_values(
                    structured,
                    "output_decision",
                )
            ),
            human_oversight=(
                self._canonical_requirement_values(
                    structured,
                    "human_oversight",
                )
            ),
            maintenance_model=(
                self._canonical_requirement_values(
                    structured,
                    "maintenance_model",
                )
            ),
            deployment_environment=(
                self._deployment_environment(
                    sentences,
                    structured=structured,
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


    def _is_actor_identity_pronoun(
        self,
        value: str,
    ) -> bool:
        """
        Return True when a candidate is only a referential pronoun.

        A pronoun may refer to a previously declared actor, but it is
        never sufficient evidence for creating a new canonical
        ActorContext identity.

        This intentionally performs no coreference resolution.
        """
        key = comparison_key(
            self._clean_actor(
                value
            )
        )

        if not key:
            return False

        pronouns = {
            # French subject pronouns.
            "je",
            "j",
            "tu",
            "il",
            "elle",
            "on",
            "nous",
            "vous",
            "ils",
            "elles",

            # English subject pronouns.
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
        }

        return key in pronouns


    def _actor_alias_identity_key(
        self,
        value: str,
    ) -> str:
        """
        Build a conservative identity key for explicit actor aliases.

        This helper removes only grammatical determiners and generic
        organization wrappers when a meaningful qualifier remains.

        Examples:
            "l'entreprise locataire" -> "locataire"
            "soci?t? locataire"      -> "locataire"
            "client company"         -> "client"

        It deliberately does NOT perform semantic synonym expansion:
            client != customer
            buyer != tenant
            provider != owner

        Those relations require explicit project evidence and must not
        be invented by actor canonicalization.
        """
        name = self._clean_actor(
            value
        )

        key = comparison_key(
            name
        )

        if not key:
            return ""

        tokens = [
            token
            for token in key.split()
            if token
        ]

        if not tokens:
            return ""

        leading_determiners = {
            "l",
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "du",
            "the",
            "a",
            "an",
        }

        while (
            len(tokens) > 1
            and tokens[0]
            in leading_determiners
        ):
            tokens.pop(0)

        organization_wrappers = {
            "entreprise",
            "entreprises",
            "societe",
            "societes",
            "organisation",
            "organisations",
            "organization",
            "organizations",
            "company",
            "companies",
        }

        relation_tokens = {
            "de",
            "d",
            "du",
            "des",
            "of",
        }

        removed_wrapper = False

        while (
            len(tokens) > 1
            and tokens[0]
            in organization_wrappers
        ):
            tokens.pop(0)
            removed_wrapper = True

        if removed_wrapper:
            while (
                len(tokens) > 1
                and tokens[0]
                in relation_tokens
            ):
                tokens.pop(0)

        while (
            len(tokens) > 1
            and tokens[-1]
            in organization_wrappers
        ):
            tokens.pop()

        return clean_text(
            " ".join(
                tokens
            )
        )


    def _extract_explicit_actors(
        self,
        *,
        description: str,
        project_context: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[ActorContext]:
        """
        Extract explicit actors without losing the role relation
        stated by the user.

        A sentence such as "the economic buyer is X" carries more
        semantic authority than keywords contained inside X.
        """
        declared_roles = (
            self._declared_actor_roles(
                description
            )
        )

        declared_groups = (
            self._declared_actor_groups(
                description
            )
        )

        declared_marketplace_sides = (
            self._declared_marketplace_sides(
                description
            )
        )

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

        # Canonical scope polarity owns whether a sentence is
        # positive project evidence or an explicit exclusion.
        #
        # An exclusion may describe an actor or market segment,
        # but it may not independently materialize that entity
        # as a canonical target actor.
        actor_target_sentences = [
            sentence
            for sentence in sentences
            if not is_scope_exclusion_statement(
                sentence
            )
        ]

        high_priority_found = False

        for sentence in actor_target_sentences:
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

                value = (
                    self._actor_declaration_head(
                        value
                    )
                )

                names.extend(
                    self._split_actor_list(
                        value
                    )
                )

        if not high_priority_found:
            for sentence in actor_target_sentences:
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

                    value = (
                        self._actor_declaration_head(
                            value
                        )
                    )

                    names.extend(
                        self._split_actor_list(
                            value
                        )
                    )

        output: List[ActorContext] = []
        seen: set[str] = set()

        # Explicit role declarations have highest authority.
        #
        # Alias identity is role-aware:
        # two lexical variants of the same explicitly declared role
        # collapse to the first user-written canonical label, while
        # the same actor may still carry two different roles if both
        # relations were explicitly declared.
        seen_declared_role_identities: set[
            Tuple[str, str]
        ] = set()

        for raw_name, role in declared_roles:
            name = self._clean_actor(
                raw_name
            )

            key = comparison_key(
                name
            )

            identity_key = (
                self._actor_alias_identity_key(
                    name
                )
                or key
            )

            role_identity = (
                identity_key,
                str(
                    role.value
                ),
            )

            if (
                not name
                or not key
                or self._is_actor_identity_pronoun(
                    name
                )
                or role_identity
                in seen_declared_role_identities
            ):
                continue

            seen_declared_role_identities.add(
                role_identity
            )

            # Preserve exact-name suppression for lower-authority
            # target/group inference later in this method.
            seen.add(
                key
            )

            output.append(
                ActorContext(
                    name=name,
                    role=role,
                    is_explicit=True,
                )
            )

        # Explicit target-user lists remain valid, but their role
        # is inferred only from the actor name when no declaration
        # already supplied a stronger role.
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
                or self._is_actor_identity_pronoun(
                    name
                )
                or key in seen
                or key in self.GENERIC_ACTORS
            ):
                continue

            seen.add(
                key
            )

            role = self._actor_role(
                name
            )

            if role == ActorRole.OTHER:
                for (
                    group_name,
                    group_role,
                ) in declared_groups:
                    group_key = comparison_key(
                        group_name
                    )

                    if (
                        group_key
                        and (
                            group_key in key
                            or key in group_key
                        )
                    ):
                        role = group_role
                        break

            output.append(
                ActorContext(
                    name=name,
                    role=role,
                    is_explicit=True,
                )
            )

        # Actor-group declarations can expose actors that were not
        # present in the target-user phrase. Preserve them without
        # duplicating a more specific actor already extracted.
        for raw_name, role in declared_groups:
            name = self._clean_actor(
                raw_name
            )

            key = comparison_key(
                name
            )

            if (
                not name
                or not key
                or self._is_actor_identity_pronoun(
                    name
                )
                or key in self.GENERIC_ACTORS
            ):
                continue

            # A structural actor declaration may refine a shorter
            # operational reference that was extracted earlier.
            #
            # Example:
            #
            #   "The primary operational user is the shift supervisor."
            #   "The supervisor uses the platform..."
            #
            # Both statements refer to USER authority, but the first
            # statement carries the more specific canonical identity.
            #
            # Refinement is deliberately conservative:
            # - same explicit role;
            # - lexical overlap already accepted by the existing
            #   identity policy;
            # - the structural name must be a strict token superset;
            # - exactly one existing actor may be refined.
            #
            # No semantic synonym inference is introduced here.
            candidate_tokens = {
                token
                for token in key.split()
                if token
            }

            overlapping_indexes: List[int] = []
            refinable_indexes: List[int] = []
            same_role_non_refinable = False

            for index, existing_actor in enumerate(
                output
            ):
                existing_key = comparison_key(
                    existing_actor.name
                )

                if (
                    not existing_key
                    or not (
                        key in existing_key
                        or existing_key in key
                    )
                ):
                    continue

                overlapping_indexes.append(
                    index
                )

                if existing_actor.role != role:
                    continue

                existing_tokens = {
                    token
                    for token
                    in existing_key.split()
                    if token
                }

                if (
                    existing_tokens
                    and existing_tokens
                    < candidate_tokens
                ):
                    refinable_indexes.append(
                        index
                    )
                else:
                    same_role_non_refinable = True

            if (
                len(refinable_indexes) == 1
                and not same_role_non_refinable
            ):
                output[
                    refinable_indexes[0]
                ] = ActorContext(
                    name=name,
                    role=role,
                    is_explicit=True,
                )

                # Preserve the shorter identity key as a suppression
                # alias. Lower-authority target extraction must not
                # re-materialize the abbreviated actor afterwards.
                seen.add(
                    key
                )

                continue

            if overlapping_indexes:
                continue

            seen.add(
                key
            )

            output.append(
                ActorContext(
                    name=name,
                    role=role,
                    is_explicit=True,
                )
            )

        # Explicit individual marketplace-side declarations are
        # structural actor evidence too.
        #
        # Their role is derived from the actor-side semantics, never
        # from whether the user called it the first or second side.
        for name, role in declared_marketplace_sides:
            key = comparison_key(
                name
            )

            if (
                not name
                or not key
                or self._is_actor_identity_pronoun(
                    name
                )
                or key in self.GENERIC_ACTORS
            ):
                continue

            represented = any(
                key in existing_key
                or existing_key in key
                for existing_key in seen
                if existing_key
            )

            if represented:
                continue

            seen.add(
                key
            )

            output.append(
                ActorContext(
                    name=name,
                    role=role,
                    is_explicit=True,
                )
            )

        return output[:8]


    def _declared_marketplace_sides(
        self,
        description: str,
    ) -> List[Tuple[str, ActorRole]]:
        """
        Extract explicitly declared structural sides of a two-sided
        operating model.

        Side order is topology only:
        "first" / "second" never assigns an economic role.

        Economic role authority comes from either:
        - explicit actor semantics, or
        - an explicitly named supply/demand side.
        """
        french_side_first_pattern = re.compile(
            r"\b(?:le|la)\s+"
            r"(?:"
            r"premier|premi(?:e|\u00e8)re|"
            r"second|seconde|"
            r"deuxi(?:e|\u00e8)me|"
            r"1er|1re|2e"
            r")\s+"
            r"(?:"
            r"c(?:o|\u00f4)t(?:e|\u00e9)|"
            r"partie|groupe"
            r")\s+"
            r"(?:est|sont)\s+"
            r"(?:"
            r"(?:"
            r"constitu(?:e|\u00e9)(?:e|es|s)?|"
            r"compos(?:e|\u00e9)(?:e|es|s)?|"
            r"form(?:e|\u00e9)(?:e|es|s)?"
            r")\s+"
            r"(?:d['\u2019]|de|par)\s*"
            r"|"
            r"(?:comprend|comprennent|regroupe|regroupent)"
            r"\s+"
            r")"
            r"(.+?)"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        english_side_first_pattern = re.compile(
            r"\b(?:the\s+)?"
            r"(?:first|second|1st|2nd)\s+"
            r"(?:side|party|group)\s+"
            r"(?:"
            r"is\s+(?:"
            r"made\s+up\s+of|"
            r"composed\s+of|"
            r"formed\s+by"
            r")"
            r"|consists?\s+of"
            r"|comprises?"
            r"|includes?"
            r")\s+"
            r"(.+?)"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        # Actor-first ordinal declarations:
        #
        #   "Les prestataires constituent le second cote..."
        #   "Providers form the second side..."
        #
        # The ordinal is deliberately NOT used to assign the role.
        french_actor_first_ordinal = re.compile(
            r"^\s*"
            r"(?:le\s+|la\s+|les\s+|"
            r"l['\u2019]\s*)?"
            r"(.+?)\s+"
            r"(?:"
            r"constitu(?:e|ent)"
            r"|form(?:e|ent)"
            r"|compos(?:e|ent)"
            r")\s+"
            r"(?:le|la)\s+"
            r"(?:"
            r"premier|premi(?:e|\u00e8)re|"
            r"second|seconde|"
            r"deuxi(?:e|\u00e8)me|"
            r"1er|1re|2e"
            r")\s+"
            r"(?:"
            r"c(?:o|\u00f4)t(?:e|\u00e9)|"
            r"partie|groupe"
            r")"
            r"(?:\s+(?:de|dans)\s+(?:la|le)\s+"
            r"(?:marketplace|plateforme))?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        english_actor_first_ordinal = re.compile(
            r"^\s*(?:the\s+)?"
            r"(.+?)\s+"
            r"(?:"
            r"forms?"
            r"|constitutes?"
            r"|makes?\s+up"
            r")\s+"
            r"(?:the\s+)?"
            r"(?:first|second|1st|2nd)\s+"
            r"(?:side|party|group)"
            r"(?:\s+of\s+(?:the\s+)?"
            r"(?:marketplace|platform))?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        # Explicitly named economic sides DO carry role authority:
        #
        #   "X forms the supply side"
        #   "Y forms the demand side"
        #
        # This is fundamentally different from "first/second side".
        french_actor_first_supply = re.compile(
            r"^\s*"
            r"(?:le\s+|la\s+|les\s+|"
            r"l['\u2019]\s*)?"
            r"(.+?)\s+"
            r"(?:"
            r"constitu(?:e|ent)"
            r"|form(?:e|ent)"
            r"|compos(?:e|ent)"
            r")\s+"
            r"(?:le|la)\s+"
            r"(?:"
            r"c(?:o|\u00f4)t(?:e|\u00e9)|"
            r"partie"
            r")\s+"
            r"(?:offre|fournisseur|vendeur)"
            r"(?:\s+(?:de|dans)\s+(?:la|le)\s+"
            r"(?:marketplace|plateforme))?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        french_actor_first_demand = re.compile(
            r"^\s*"
            r"(?:le\s+|la\s+|les\s+|"
            r"l['\u2019]\s*)?"
            r"(.+?)\s+"
            r"(?:"
            r"constitu(?:e|ent)"
            r"|form(?:e|ent)"
            r"|compos(?:e|ent)"
            r")\s+"
            r"(?:le|la)\s+"
            r"(?:"
            r"c(?:o|\u00f4)t(?:e|\u00e9)|"
            r"partie"
            r")\s+"
            r"(?:demande|acheteur|client)"
            r"(?:\s+(?:de|dans)\s+(?:la|le)\s+"
            r"(?:marketplace|plateforme))?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        english_actor_first_supply = re.compile(
            r"^\s*(?:the\s+)?"
            r"(.+?)\s+"
            r"(?:"
            r"forms?"
            r"|constitutes?"
            r"|makes?\s+up"
            r")\s+"
            r"(?:the\s+)?"
            r"(?:supply|provider|seller)\s+side"
            r"(?:\s+of\s+(?:the\s+)?"
            r"(?:marketplace|platform))?"
            r"(?:\s+and\b.*)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        english_actor_first_demand = re.compile(
            r"^\s*(?:the\s+)?"
            r"(.+?)\s+"
            r"(?:"
            r"forms?"
            r"|constitutes?"
            r"|makes?\s+up"
            r")\s+"
            r"(?:the\s+)?"
            r"(?:demand|buyer|customer)\s+side"
            r"(?:\s+of\s+(?:the\s+)?"
            r"(?:marketplace|platform))?"
            r"(?:\s+and\b.*)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        output: List[
            Tuple[str, ActorRole]
        ] = []

        seen: set[
            Tuple[str, str]
        ] = set()

        def append_candidate(
            raw_actor: str,
            forced_role=None,
        ) -> None:
            raw_actor = clean_text(
                raw_actor
            )

            if not raw_actor:
                return

            role = (
                forced_role
                if forced_role is not None
                else self._marketplace_side_role(
                    raw_actor
                )
            )

            # A merely ordinal side declaration is structural evidence,
            # but it does not prove the economic role by itself.
            if role not in {
                ActorRole.PROVIDER,
                ActorRole.BUYER,
            }:
                return

            name = self._marketplace_side_actor_name(
                raw_actor
            )

            key = comparison_key(
                name
            )

            if not name or not key:
                return

            identity = (
                key,
                role.value,
            )

            if identity in seen:
                return

            seen.add(
                identity
            )

            output.append(
                (
                    name,
                    role,
                )
            )

        ordinal_patterns = (
            french_side_first_pattern,
            english_side_first_pattern,
            french_actor_first_ordinal,
            english_actor_first_ordinal,
        )

        named_side_patterns = (
            (
                french_actor_first_supply,
                ActorRole.PROVIDER,
            ),
            (
                french_actor_first_demand,
                ActorRole.BUYER,
            ),
            (
                english_actor_first_supply,
                ActorRole.PROVIDER,
            ),
            (
                english_actor_first_demand,
                ActorRole.BUYER,
            ),
        )

        for sentence in self._sentences(
            description
        ):
            for pattern in ordinal_patterns:
                match = pattern.search(
                    sentence
                )

                if not match:
                    continue

                append_candidate(
                    match.group(1)
                )

            for pattern, role in named_side_patterns:
                match = pattern.search(
                    sentence
                )

                if not match:
                    continue

                append_candidate(
                    match.group(1),
                    role,
                )

        return output

    def _marketplace_side_role(
        self,
        value: str,
    ) -> ActorRole:
        """
        Resolve supply/demand semantics from an explicitly declared
        side without using side order, sector names or geography.
        """
        key = comparison_key(
            value
        )

        if not key:
            return ActorRole.OTHER

        def matches(
            marker: str,
        ) -> bool:
            normalized = comparison_key(
                marker
            )

            if not normalized:
                return False

            return (
                re.search(
                    rf"(?<!\w)"
                    rf"{re.escape(normalized)}"
                    rf"(?!\w)",
                    key,
                    flags=re.IGNORECASE,
                )
                is not None
            )

        provider_markers = (
            "vendeur",
            "vendeurs",
            "fournisseur",
            "fournisseurs",
            "prestataire",
            "prestataires",
            "producteur",
            "producteurs",
            "offreur",
            "offreurs",
            "proprietaire",
            "proprietaires",
            "bailleur",
            "bailleurs",
            "seller",
            "sellers",
            "supplier",
            "suppliers",
            "provider",
            "providers",
            "owner",
            "owners",
            "proprietor",
            "proprietors",
            "lender",
            "lenders",
            "met en vente",
            "met a disposition",
            "publie",
            "publient",
            "propose",
            "proposent",
            "offre",
            "offrent",
            "vend",
            "vendent",
            "provides",
            "provide",
            "offers",
            "offer",
            "lists",
            "list",
            "sells",
            "sell",
            "rents out",
            "rent out",
        )

        buyer_markers = (
            "acheteur",
            "acheteurs",
            "acquereur",
            "acquereurs",
            "locataire",
            "locataires",
            "demandeur",
            "demandeurs",
            "buyer",
            "buyers",
            "purchaser",
            "purchasers",
            "renter",
            "renters",
            "lessee",
            "lessees",
            "tenant",
            "tenants",
            "besoin",
            "recherche",
            "recherchent",
            "cherche",
            "cherchent",
            "reserve",
            "reservent",
            "commande",
            "commandent",
            "need",
            "needs",
            "needing",
            "searches",
            "search",
            "seeks",
            "seek",
            "books",
            "book",
            "buys",
            "buy",
            "purchases",
            "purchase",
        )

        provider_score = sum(
            matches(
                marker
            )
            for marker in provider_markers
        )

        buyer_score = sum(
            matches(
                marker
            )
            for marker in buyer_markers
        )

        if (
            provider_score > 0
            and provider_score > buyer_score
        ):
            return ActorRole.PROVIDER

        if (
            buyer_score > 0
            and buyer_score > provider_score
        ):
            return ActorRole.BUYER

        # Existing exact actor semantics remain a safe tie-breaker.
        lexical_role = self._actor_role(
            value
        )

        if lexical_role in {
            ActorRole.PROVIDER,
            ActorRole.BUYER,
        }:
            return lexical_role

        return ActorRole.OTHER


    def _marketplace_side_actor_name(
        self,
        value: str,
    ) -> str:
        """
        Keep a concise actor identity for a marketplace side.

        Normally the existing actor cleaner is authoritative. If that
        cleaner would reduce an explicit side definition to a generic
        noun such as "companies", retain the bounded user-written
        qualifier because it is what distinguishes the side.
        """
        raw = clean_text(
            value
        )

        if not raw:
            return ""

        head = self._clean_actor(
            raw
        )

        head_key = comparison_key(
            head
        )

        generic_heads = {
            "entreprise",
            "entreprises",
            "societe",
            "societes",
            "organisation",
            "organisations",
            "organization",
            "organizations",
            "company",
            "companies",
            "business",
            "businesses",
            "personne",
            "personnes",
            "person",
            "people",
        }

        if (
            head
            and head_key not in generic_heads
        ):
            return head

        # Preserve only a bounded explicit side definition.
        candidate = self._compact(
            raw,
            170,
        )

        if len(candidate) > 180:
            return ""

        return candidate


    def _declared_actor_groups(
        self,
        description: str,
    ) -> List[Tuple[str, ActorRole]]:
        """
        Extract explicit structural actor lists declared by the user.

        Group/list declarations are authoritative actor evidence.
        Ordinary predicates such as "users are able to..." must never
        become actor identities.
        """
        # "Primary users are X and Y" is an explicit structural
        # actor declaration, distinct from an ordinary predicate such as
        # "users are responsible for X".
        primary_user_patterns: Tuple[
            Tuple[
                re.Pattern[str],
                ActorRole,
                bool,
                bool,
            ],
            ...,
        ] = (
            # U7 universal colon-labeled operational-user authority.
            #
            # Explicit field-style declarations have the same authority
            # as copular natural-language declarations.
            #
            #   Utilisateur operationnel principal: X
            #   Primary operational user: X
            (
                re.compile(
                    r"\b"
                    r"utilisateur\s+"
                    r"op(?:e|\u00e9)rationnel\s+"
                    r"principal"
                    r"\s*:\s*"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                True,
            ),
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:primary|main|key)\s+"
                    r"operational\s+user"
                    r"\s*:\s*"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                True,
            ),
            # U2 universal actor-first operational-user authority.
            #
            # Explicit relation:
            #
            #   "X is an operational user."
            #   "X are operational users."
            #   "X est un utilisateur operationnel."
            #   "X sont les utilisateurs operationnels."
            #
            # The relation itself owns USER authority.
            # Lexical identity such as "operator" must not downgrade
            # an explicitly declared operational USER relation.
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"un\s+|une\s+|des\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:est|sont)\s+"
                    r"(?:un\s+|une\s+|des\s+|"
                    r"le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"utilisateurs?\s+"
                    r"op(?:e|\u00e9)rationnel(?:le)?s?\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                True,
            ),
            (
                re.compile(
                    r"\b(?:les\s+)?"
                    r"utilisateurs?\s+principaux?"
                    r"\s*(?:"
                    r"sont|incluent|comprennent|regroupent|:"
                    r")\s+"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                True,
                False,
            ),
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:main|primary|key)\s+users?"
                    r"\s*(?:"
                    r"are|include|comprise|consist\s+of|:"
                    r")\s+"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                True,
                False,
            ),

            # Label-first operational-user declarations:
            #
            #   "The primary operational user of Product is X."
            #   "L'utilisateur operationnel principal de Produit est X."
            #
            # The explicit declaration owns USER authority.
            # Product name, sector and archetype do not infer the actor.
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:primary|main|key)\s+"
                    r"operational\s+user"
                    r"(?:\s+of\s+[^.;]+?)?"
                    r"\s+(?:is|will\s+be|would\s+be)\s+"
                    r"(?:the\s+|a\s+|an\s+)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                True,
            ),
            (
                re.compile(
                    r"\b(?:l['\u2019]\s*)?"
                    r"utilisateur\s+"
                    r"op(?:e|\u00e9)rationnel\s+principal"
                    r"(?:\s+de\s+[^.;]+?)?"
                    r"\s+(?:est|sera|serait)\s+"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                True,
            ),

            # Actor-first primary-user declarations:
            #
            #   "Warehouse operators are the primary users."
            #   "The warehouse supervisor is the primary user."
            #   "Les operateurs logistiques sont les utilisateurs principaux."
            #
            # The grammatical subject is the canonical actor identity.
            # Unlike "Primary users are X and Y", one explicit subject
            # can itself denote a valid user group, so require_multiple=False.
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:is|are)\s+"
                    r"(?:the\s+)?"
                    r"(?:main|primary|key)\s+"
                    r"users?\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                False,
            ),
            (
                re.compile(
                    r"^\s*(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:est|sont)\s+"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(?:utilisateur\s+principal|"
                    r"utilisateurs\s+principaux)\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                False,
            ),
        )

        patterns: Tuple[
            Tuple[
                re.Pattern[str],
                ActorRole,
                bool,
                bool,
            ],
            ...,
        ] = (
            *primary_user_patterns,
            # Actor-first secondary-user declarations:
            #
            #   "Employees are secondary users."
            #   "Les employes sont des utilisateurs secondaires."
            #
            # This is explicit structural USER authority, not an
            # archetype-derived persona.
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:is|are)\s+"
                    r"(?:a\s+|an\s+|the\s+)?"
                    r"secondary\s+users?\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                False,
            ),
            (
                re.compile(
                    r"^\s*(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:est|sont)\s+"
                    r"(?:un\s+|une\s+|des\s+|"
                    r"le\s+|la\s+|les\s+)?"
                    r"utilisateurs?\s+secondaires?\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                False,
            ),
            (
                re.compile(
                    r"\b(?:les\s+)?(?:deux\s+)?"
                    r"groupes?\s+d['\u2019]utilisateurs?"
                    r"\s*(?:"
                    r"sont|incluent|comprennent|regroupent|:"
                    r")\s+"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                False,
            ),
            (
                re.compile(
                    r"\b(?:the\s+)?(?:two\s+)?"
                    r"user\s+groups?"
                    r"\s*(?:"
                    r"are|include|comprise|consist\s+of|:"
                    r")\s+"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
                False,
                False,
            ),
            (
                re.compile(
                    r"\b(?:les\s+)?(?:deux\s+)?"
                    r"(?:acteurs?|parties?|c\u00f4t\u00e9s?)"
                    r"\s*(?:"
                    r"sont|incluent|comprennent|regroupent|:"
                    r")\s+"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.OTHER,
                True,
                False,
            ),
            (
                re.compile(
                    r"\b(?:the\s+)?(?:two\s+)?"
                    r"(?:actors?|sides?|parties?)"
                    r"\s*(?:"
                    r"are|include|comprise|consist\s+of|:"
                    r")\s+"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.OTHER,
                True,
                False,
            ),
        )

        output: List[
            Tuple[str, ActorRole]
        ] = []

        seen: set[str] = set()

        for sentence in self._sentences(
            description
        ):
            for (
                pattern,
                fallback_role,
                require_multiple,
                role_assignment_authoritative,
            ) in patterns:
                match = pattern.search(
                    sentence
                )

                if not match:
                    continue

                candidates: List[
                    Tuple[
                        str,
                        ActorRole,
                    ]
                ] = []

                local_seen: set[str] = set()

                group_value = (
                    self._actor_declaration_head(
                        match.group(1)
                    )
                )

                for raw_name in self._split_actor_list(
                    group_value
                ):
                    name = self._clean_actor(
                        raw_name
                    )

                    # Structural actor declarations own actor identity.
                    #
                    # Determiners introducing an item in an explicit
                    # actor declaration are grammatical syntax, not part
                    # of the canonical actor name:
                    #
                    #   "les utilisateurs principaux sont
                    #    le responsable logistique et
                    #    le responsable maintenance"
                    #
                    #       -> "responsable logistique"
                    #       -> "responsable maintenance"
                    #
                    # Apply this normalization only inside the structural
                    # declaration authority. _clean_actor() remains
                    # unchanged globally.
                    name = re.sub(
                        r"^(?:"
                        r"le|la|les|"
                        r"un|une|des|"
                        r"l['\u2019]"
                        r")\s*",
                        "",
                        name,
                        count=1,
                        flags=(
                            re.IGNORECASE
                            | re.UNICODE
                        ),
                    )

                    name = clean_text(
                        name
                    )

                    key = comparison_key(
                        name
                    )

                    if (
                        not name
                        or not key
                        or key in local_seen
                        or key in self.GENERIC_ACTORS
                    ):
                        continue

                    # Structural declarations have two distinct
                    # authority semantics.
                    #
                    # 1. Explicit operational-role assignment:
                    #
                    #      "The primary operational user is X."
                    #
                    #    The declaration itself owns USER authority.
                    #
                    # 2. Structural membership declaration:
                    #
                    #      "The primary users are X and Y."
                    #      "Employees are secondary users."
                    #      "The user groups are X and Y."
                    #
                    #    The declaration proves actor membership but
                    #    must not erase a more precise canonical role
                    #    already supported by the actor phrase itself.
                    #
                    # The pattern metadata decides which semantic rule
                    # applies. No project, sector or actor name is
                    # hard-coded here.
                    if role_assignment_authoritative:
                        role = fallback_role
                    else:
                        role = self._actor_role(
                            name
                        )

                        if role == ActorRole.OTHER:
                            role = fallback_role

                    local_seen.add(
                        key
                    )

                    candidates.append(
                        (
                            name,
                            role,
                        )
                    )

                if (
                    require_multiple
                    and len(candidates) < 2
                ):
                    continue

                for name, role in candidates:
                    key = comparison_key(
                        name
                    )

                    if key in seen:
                        continue

                    seen.add(
                        key
                    )

                    output.append(
                        (
                            name,
                            role,
                        )
                    )

        return output


    def _actor_declaration_head(
        self,
        value: Any,
    ) -> str:
        """
        Keep only the structural actor declaration before a
        descriptive or operational relative clause.

        This boundary must be applied before actor-list splitting.
        """
        text = clean_text(
            value
        )

        if not text:
            return ""

        head = re.split(
            r"\s+\b(?:"
            r"qui|que|dont|o\u00f9|"
            r"lequel|laquelle|lesquels|lesquelles|"
            r"who|which|that|whose|where|"
            r"ayant|souhaitant|cherchant|utilisant|"
            r"g\u00e9rant|gerant|"
            r"having|needing|requiring|using|"
            r"seeking|managing"
            r")\b\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        return clean_text(
            head
        )

    def _role_relation_is_negated(
        self,
        sentence: str,
        role: ActorRole,
    ) -> bool:
        """
        Negative payment/decision statements must never become
        positive canonical role authority.
        """
        key = comparison_key(
            sentence
        )

        if not key:
            return False

        if role == ActorRole.PAYER:
            patterns = (
                r"\bne\s+(?:"
                r"paie|paye|paient|payent|"
                r"paiera|payera|paieront|payeront"
                r")\s+pas\b",

                r"\bn\s+est(?:\s+\w+){0,4}\s+pas"
                r"(?:\s+necessairement)?\b"
                r".*\b(?:"
                r"payeur|paie|paye|payer|abonnement"
                r")\b",

                r"\b(?:does|do|will|would)\s+not\s+pay\b",

                r"\b(?:doesn|don|won|wouldn)\s+t\s+pay\b",

                r"\bis(?:\s+\w+){0,4}\s+not"
                r"(?:\s+necessarily)?\b"
                r".*\b(?:payer|pay|pays|subscription)\b",

                r"\bisn\s+t\b"
                r".*\b(?:payer|pay|pays|subscription)\b",
            )

            return any(
                re.search(
                    pattern,
                    key,
                    flags=re.IGNORECASE,
                )
                for pattern in patterns
            )

        if role == ActorRole.DECISION_MAKER:
            patterns = (
                r"\bne\s+(?:"
                r"decide|decident|decidera|decideront"
                r")\s+pas\b",

                r"\bn\s+est(?:\s+\w+){0,4}\s+pas"
                r"(?:\s+necessairement)?\b"
                r".*\b(?:"
                r"decideur|decide|decision|budget"
                r")\b",

                r"\b(?:does|do|will|would)\s+not\s+decide\b",

                r"\b(?:doesn|don|won|wouldn)\s+t\s+decide\b",

                r"\bis(?:\s+\w+){0,4}\s+not"
                r"(?:\s+necessarily)?\b"
                r".*\b(?:"
                r"decision maker|decides|decision|budget"
                r")\b",

                r"\bisn\s+t\b"
                r".*\b(?:"
                r"decision maker|decides|decision|budget"
                r")\b",
            )

            return any(
                re.search(
                    pattern,
                    key,
                    flags=re.IGNORECASE,
                )
                for pattern in patterns
            )

        return False

    def _role_relation_sentence(
        self,
        sentence: str,
    ) -> str:
        """
        Remove a leading temporal / conditional context clause before
        resolving an explicit actor-role relation.

        The contextual clause is not part of the grammatical subject.

        Examples:
        - "Lorsque la commande est valid?e, la soci?t? paie..."
        - "Once the order is approved, the company pays..."

        Only an initial clause introduced by a conservative set of
        contextual markers and terminated by a comma is removed.
        """
        text = clean_text(
            sentence
        )

        if not text:
            return ""

        prefix, separator, remainder = (
            text.partition(",")
        )

        if (
            not separator
            or not remainder.strip()
        ):
            return text

        prefix_key = comparison_key(
            prefix
        )

        context_markers = (
            "lorsque",
            "quand",
            "si",
            "une fois",
            "des que",
            "apres que",
            "avant que",
            "when",
            "once",
            "if",
            "after",
            "before",
            "as soon as",
        )

        if not any(
            prefix_key == marker
            or prefix_key.startswith(
                marker + " "
            )
            for marker in context_markers
        ):
            return text

        return clean_text(
            remainder
        )


    def _declared_actor_roles(
        self,
        description: str,
    ) -> List[Tuple[str, ActorRole]]:
        """
        Resolve actor roles from explicit linguistic relations.

        The declaration itself has authority:
        operational user, economic buyer, payer or decision-maker.
        The industry never assigns the role.
        """
        relation_context_key = comparison_key(
            description
        )

        marketplace_context = any(
            marker in relation_context_key
            for marker in (
                "marketplace",
                "two sided",
                "deux cotes",
                "mise en relation",
                "met en relation",
                "place de marche",
            )
        )

        english_payment_predicate_pattern = re.compile(
            r"^\s*(?:the\s+|a\s+|an\s+)?"
            r"(.+?)\s+"
            r"(?:"
            r"(?:can|could|may|might)\s+"
            r"(?:choose|decide)\s+to\s+pay"
            r"|(?:chooses?|decides?)\s+to\s+pay"
            r"|(?:can|could|may|might|should|must)\s+pay"
            r"|will\s+pay"
            r"|would\s+pay"
            r"|is\s+paying"
            r"|are\s+paying"
            r"|has\s+paid"
            r"|have\s+paid"
            r"|pays?"
            r"|paid"
            r")\b"
            r"(?:\s+.+?)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        french_payment_predicate_pattern = re.compile(
            r"^\s*"
            r"(?:le\s+|la\s+|les\s+|"
            r"l['\u2019]\s*)?"
            r"(.+?)\s+"
            r"(?:"
            r"pai(?:e|ent|era|eront|erait|eraient)"
            r"|pay(?:e|ent|era|eront|erait|eraient)"
            r"|a\s+pay(?:e|\u00e9)"
            r"|ont\s+pay(?:e|\u00e9)"
            r")\b"
            r"(?:\s+.+?)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        patterns: Tuple[
            Tuple[re.Pattern[str], ActorRole],
            ...,
        ] = (
            # U7 universal purchase-decision and colon-role authority.
            #
            # ----------------------------------------------------------
            # Explicit field-style decision-maker declarations
            # ----------------------------------------------------------
            (
                re.compile(
                    r"\b(?:"
                    r"d(?:e|\u00e9)cideur"
                    r"|d(?:e|\u00e9)cideuse"
                    r")"
                    r"(?:\s+d['\u2019]achat)?"
                    r"(?:\s+(?:"
                    r"principal(?:e)?"
                    r"|secondaire"
                    r"))?"
                    r"\s*:\s*"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            (
                re.compile(
                    r"\b"
                    r"(?:(?:primary|main|key|secondary)\s+)?"
                    r"decision[ -]?maker"
                    r"\s*:\s*"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),

            # ----------------------------------------------------------
            # Explicit field-style payer declarations
            # ----------------------------------------------------------
            (
                re.compile(
                    r"\b"
                    r"payeur"
                    r"(?:\s+(?:"
                    r"(?:e|\u00e9)conomique"
                    r"|principal"
                    r"))?"
                    r"\s*:\s*"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            (
                re.compile(
                    r"\b"
                    r"(?:(?:primary|main|economic)\s+)?"
                    r"payer"
                    r"\s*:\s*"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),

            # ----------------------------------------------------------
            # French acquisition / purchase decision authority
            #
            # Operational decisions remain excluded because the semantic
            # object must explicitly be acquisition, purchase, subscription
            # or adoption.
            # ----------------------------------------------------------
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"peut|peuvent"
                    r"|pourrait|pourraient"
                    r"|doit|doivent"
                    r"|devrait|devraient"
                    r")\s+"
                    r"(?:"
                    r"d(?:e|\u00e9)cider"
                    r"|approuver"
                    r"|autoriser"
                    r"|valider"
                    r")\s+"
                    r"(?:"
                    r"de\s+"
                    r"|d['\u2019]\s*"
                    r")?"
                    r"(?:l['\u2019]\s*)?"
                    r"(?:"
                    r"acquisition"
                    r"|achat"
                    r"|abonnement"
                    r"|adoption"
                    r")\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),

            # ----------------------------------------------------------
            # English acquisition / purchase decision authority
            # ----------------------------------------------------------
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"may|can|could|might"
                    r"|should|must|will|would"
                    r")\s+"
                    r"(?:"
                    r"(?:approve|authorize|validate)\s+"
                    r"(?:the\s+)?"
                    r"(?:"
                    r"purchase"
                    r"|acquisition"
                    r"|subscription"
                    r"|adoption"
                    r"|procurement"
                    r")"
                    r"|decide\s+on\s+"
                    r"(?:the\s+)?"
                    r"(?:"
                    r"purchase"
                    r"|acquisition"
                    r"|subscription"
                    r"|adoption"
                    r")"
                    r")\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            # U2 universal French label-first decision-maker authority.
            #
            # Examples:
            #
            #   "Le decideur principal est le gerant."
            #   "La decideuse principale est la directrice."
            #
            # Label-first and actor-first declarations express the
            # same explicit relation and therefore receive the same
            # canonical DECISION_MAKER authority.
            (
                re.compile(
                    r"\b(?:"
                    r"d(?:e|\u00e9)cideur"
                    r"|d(?:e|\u00e9)cideuse"
                    r")"
                    r"(?:\s+d['\u2019]achat)?"
                    r"(?:\s+principal(?:e)?)?"
                    r"\s+"
                    r"(?:"
                    r"est"
                    r"|serait"
                    r"|sera"
                    r"|peut\s+(?:e|\u00ea)tre"
                    r"|pourrait\s+(?:e|\u00ea)tre"
                    r")"
                    r"(?:\s+(?:"
                    r"probablement|vraisemblablement"
                    r"))?"
                    r"\s+"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"un\s+|une\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            # Explicit request initiation is operational-user authority.
            #
            # This does not imply payment authority. In a marketplace,
            # USER is sufficient to represent the demand-side actor.
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"est\s+l['\u2019]acteur\s+qui\s+"
                    r")?"
                    r"(?:"
                    r"initie|initient"
                    r"|cr(?:e|\u00e9)e"
                    r"|cr(?:e|\u00e9)ent"
                    r"|soumet|soumettent"
                    r"|envoie|envoient"
                    r")\s+"
                    r"(?:la\s+|une\s+|le\s+|un\s+)?"
                    r"(?:demande|requ(?:e|\u00ea)te)\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
            ),
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"is\s+the\s+actor\s+(?:who|that)\s+"
                    r")?"
                    r"(?:"
                    r"initiates?"
                    r"|creates?"
                    r"|submits?"
                    r"|sends?"
                    r")\s+"
                    r"(?:the\s+|a\s+|an\s+)?"
                    r"(?:service\s+)?request\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
            ),

            # Explicit execution of the requested/reserved service is
            # provider authority only in an explicitly two-sided /
            # marketplace context.
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"ex(?:e|\u00e9)cute"
                    r"|ex(?:e|\u00e9)cutent"
                    r"|r(?:e|\u00e9)alise"
                    r"|r(?:e|\u00e9)alisent"
                    r"|effectue|effectuent"
                    r"|fournit|fournissent"
                    r")"
                    r"(?:\s+(?:ensuite|directement))?\s+"
                    r"(?:"
                    r"l['\u2019]\s*"
                    r"|le\s+|la\s+|les\s+"
                    r"|un\s+|une\s+|des\s+"
                    r")?"
                    r"(?=[^.;]{0,120}\b(?:"
                    r"services?"
                    r"|missions?"
                    r"|prestations?"
                    r"|interventions?"
                    r"|travail"
                    r"|travaux"
                    r")\b)"
                    r"[^.;]*?"
                    r"(?:"
                    r"services?"
                    r"|missions?"
                    r"|prestations?"
                    r"|interventions?"
                    r"|travail"
                    r"|travaux"
                    r")\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PROVIDER,
            ),
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"performs?"
                    r"|delivers?"
                    r"|provides?"
                    r"|executes?"
                    r")"
                    r"(?:\s+(?:then|directly))?\s+"
                    r"(?:the\s+|a\s+|an\s+)?"
                    r"(?=[^.;]{0,120}\b(?:"
                    r"services?|missions?|jobs?|work"
                    r")\b)"
                    r"[^.;]*?"
                    r"(?:"
                    r"services?"
                    r"|missions?"
                    r"|jobs?"
                    r"|work"
                    r")\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PROVIDER,
            ),

            # Label-first primary operational-user declarations
            # intentionally do not live in _declared_actor_roles().
            #
            # Canonical ownership:
            #
            #   "The primary operational user is X."
            #   "L'utilisateur operationnel principal est X."
            #
            #       -> _declared_actor_groups()
            #
            # Operational actor-first evidence such as:
            #
            #   "The supervisor uses the platform."
            #   "Le superviseur utilise la plateforme."
            #
            #       -> operational_user_patterns below
            #
            # Keeping these responsibilities separate prevents one
            # explicit relation from materializing competing long and
            # abbreviated identities while preserving USER authority.
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"economic\s+buyer\s+"
                    r"(?:"
                    r"is"
                    r"|would(?:\s+(?:probably|likely|typically))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(.+?)"
                    r"(?="
                    r",\s*(?:but|however|although)\b"
                    r"|[.;]"
                    r"|$"
                    r")",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            (
                re.compile(
                    r"\bacheteur\s+"
                    r"(?:e|\u00e9)conomique\s+"
                    r"(?:est|serait|sera)"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+(.+?)"
                    r"(?="
                    r",\s*(?:mais|cependant)\b"
                    r"|[.;]"
                    r"|$"
                    r")",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            # Actor-first decision-maker declarations:
            #
            #   "Le responsable de site est le decideur principal..."
            #   "The operations director is the primary decision maker..."
            #
            # The grammatical subject is the canonical actor.
            # Qualifiers after the role describe decision scope and are
            # deliberately excluded from the actor identity.
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"est"
                    r"|serait"
                    r"|sera"
                    r")"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+"
                    r"(?:le\s+|la\s+|"
                    r"l['\u2019]\s*)?"
                    r"(?:principal(?:e)?\s+)?"
                    r"(?:"
                    r"d(?:e|\u00e9)cideur"
                    r"|d(?:e|\u00e9)cideuse"
                    r")"
                    r"(?:\s+d['\u2019]achat)?"
                    r"(?:\s+principal(?:e)?)?"
                    r"(?="
                    r"\s+(?:"
                    r"pour\b"
                    r"|charg(?:e|\u00e9)e?\s+de\b"
                    r"|responsable\s+de\b"
                    r"|et\b"
                    r")"
                    r"|[.;]"
                    r"|$"
                    r")",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"is"
                    r"|can\s+be"
                    r"|could\s+be"
                    r"|would(?:\s+(?:probably|likely))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(?:the\s+|a\s+|an\s+)?"
                    r"(?:(?:primary|main|key)\s+)?"
                    r"(?:(?:"
                    r"purchasing"
                    r"|purchase"
                    r"|procurement"
                    r"|buying"
                    r")\s+)?"
                    r"decision[ -]?maker"
                    r"(?="
                    r"\s+(?:"
                    r"for\b"
                    r"|responsible\s+for\b"
                    r"|in\s+charge\s+of\b"
                    r"|and\b"
                    r")"
                    r"|[.;]"
                    r"|$"
                    r")",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),

            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"decision[ -]?maker\s+"
                    r"(?:"
                    r"is"
                    r"|can\s+be"
                    r"|could\s+be"
                    r"|would(?:\s+(?:probably|likely))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(?:the\s+)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            (
                re.compile(
                    r"\bd(?:e|\u00e9)cideur"
                    r"(?:\s+d['\u2019]achat)?\s+"
                    r"(?:"
                    r"est"
                    r"|serait"
                    r"|sera"
                    r"|peut\s+(?:e|\u00ea)tre"
                    r"|pourrait\s+(?:e|\u00ea)tre"
                    r")"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            # Blind-B2 passive purchasing-decision authority.
            #
            # Examples:
            #
            #   The purchasing decision is made by A, B or C.
            #   The procurement decision is taken by A.
            #   La d?cision d'achat est prise par A, B ou C.
            #   La d?cision d'acquisition est valid?e par A.
            #
            # A generic operational decision deliberately does not match:
            #
            #   The scheduling decision is made by A.
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:"
                    r"purchasing"
                    r"|purchase"
                    r"|procurement"
                    r"|buying"
                    r"|acquisition"
                    r")\s+"
                    r"decision\s+"
                    r"(?:"
                    r"is"
                    r"|can\s+be"
                    r"|could\s+be"
                    r"|would(?:\s+(?:probably|likely))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(?:"
                    r"made"
                    r"|taken"
                    r"|approved"
                    r"|validated"
                    r")\s+by\s+"
                    r"(?:the\s+)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),
            (
                re.compile(
                    r"\b(?:la\s+)?"
                    r"d(?:e|\u00e9)cision\s+"
                    r"d['\u2019]"
                    r"(?:"
                    r"achat"
                    r"|acquisition"
                    r")\s+"
                    r"(?:"
                    r"est"
                    r"|serait"
                    r"|sera"
                    r"|peut\s+(?:e|\u00ea)tre"
                    r"|pourrait\s+(?:e|\u00ea)tre"
                    r")\s+"
                    r"(?:"
                    r"prise"
                    r"|faite"
                    r"|valid(?:e|\u00e9)e"
                    r"|approuv(?:e|\u00e9)e"
                    r")\s+par\s+"
                    r"(?:"
                    r"le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*"
                    r")?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.DECISION_MAKER,
            ),

            # Payer declarations are authoritative regardless of
            # grammatical direction:
            #
            #   "the primary payer is X"
            #   "X is the primary payer"
            #   "le payeur principal est X"
            #   "X est le payeur principal"
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:(?:main|primary)\s+)?payer\s+"
                    r"(?:"
                    r"is"
                    r"|would(?:\s+(?:probably|likely))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(?:the\s+)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            # Explicit multi-role declarations:
            #
            #   "X is the customer and primary payer"
            #   "X is the buyer and payer"
            #
            # The explicit payer role remains authoritative even when
            # another business role is stated before it.
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"is"
                    r"|would(?:\s+(?:probably|likely))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(?:the\s+)?"
                    r"[^.;]{1,80}?\s+"
                    r"(?:and|&)\s+"
                    r"(?:the\s+)?"
                    r"(?:(?:main|primary)\s+)?payer"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"is"
                    r"|would(?:\s+(?:probably|likely))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(?:the\s+)?"
                    r"(?:(?:main|primary)\s+)?payer"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            (
                re.compile(
                    r"\b"
                    r"(?:(?:principal|principalement)\s+)?"
                    r"payeur"
                    r"(?:\s+principal)?\s+"
                    r"(?:est|serait|sera)"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+(?:le\s+|la\s+|les\s+)?"
                    r"(.+?)"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            # D?clarations multi-r?les explicites :
            #
            #   "X est le client et le payeur principal"
            #   "X est l'acheteur et le payeur"
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:est|serait|sera)"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+(?:le\s+|la\s+)?"
                    r"[^.;]{1,80}?\s+"
                    r"(?:et|&)\s+"
                    r"(?:le\s+|la\s+)?"
                    r"(?:"
                    r"(?:principal\s+)?payeur"
                    r"|payeur\s+principal"
                    r")"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            (
                re.compile(
                    r"^\s*"
                    r"(?:le\s+|la\s+|les\s+|"
                    r"l['\u2019]\s*)?"
                    r"(.+?)\s+"
                    r"(?:est|serait|sera)"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+(?:le\s+|la\s+)?"
                    r"(?:"
                    r"(?:principal\s+)?payeur"
                    r"|payeur\s+principal"
                    r")"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
            # Explicit payment predicates are authoritative:
            #
            #   "L'entreprise cliente paie un abonnement."
            #   "L'entreprise cliente paiera les frais."
            #   "The client company pays a subscription."
            #   "The client company will pay the fee."
            #
            # The payer is the grammatical subject directly performing
            # the payment action. Capability/delegation statements such
            # as "the platform allows users to pay" do not match because
            # the payment verb is not the subject's predicate.
            (
                french_payment_predicate_pattern,
                ActorRole.PAYER,
            ),
            (
                english_payment_predicate_pattern,
                ActorRole.PAYER,
            ),
        )


        # ----------------------------------------------------------
        # Operational actor-first relations.
        #
        # These predicates identify an explicitly named human or
        # organizational subject interacting with the product or
        # initiating/reviewing a business operation.
        #
        # Role authority remains USER/OPERATOR only. Payment,
        # decision-making and service execution have independent
        # authorities and are deliberately excluded here.
        # ----------------------------------------------------------

        # Request predicates are lexically ambiguous:
        #
        #   "The customer requests a service." -> predicate
        #   "The manager approves the request." -> noun
        #
        # Actor authority therefore reuses the canonical workflow
        # noun-vs-action grammar rather than maintaining a parallel
        # interpretation of request / demande.
        english_operational_request_pattern = re.compile(
            r"^\s*(?:the\s+|a\s+|an\s+)?"
            r"(.+?)\s+"
            r"(requests?)\b"
            r"(?:\s+.+?)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        french_operational_request_pattern = re.compile(
            r"^\s*(?:le\s+|la\s+|les\s+|"
            r"un\s+|une\s+|des\s+|"
            r"l['\u2019]\s*)?"
            r"(.+?)\s+"
            r"(demand(?:e|ent))\b"
            r"(?:\s+.+?)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        operational_user_patterns: Tuple[
            re.Pattern[str],
            ...,
        ] = (
            re.compile(
                r"^\s*(?:the\s+|a\s+|an\s+)?"
                r"(.+?)\s+"
                r"(?:"
                r"uses?"
                r"|reviews?"
                r"|validates?"
                r")\b"
                r"(?:\s+.+?)?"
                r"(?=[.;]|$)",
                re.IGNORECASE,
            ),
            english_operational_request_pattern,
            re.compile(
                r"^\s*(?:le\s+|la\s+|les\s+|"
                r"un\s+|une\s+|des\s+|"
                r"l['\u2019]\s*)?"
                r"(.+?)\s+"
                r"(?:"
                r"utilis(?:e|ent)"
                r"|examin(?:e|ent)"
                r"|valid(?:e|ent)"
                r")\b"
                r"(?:\s+.+?)?"
                r"(?=[.;]|$)",
                re.IGNORECASE,
            ),
            french_operational_request_pattern,
        )

        output: List[
            Tuple[str, ActorRole]
        ] = []

        seen: set[
            Tuple[str, str]
        ] = set()

        for sentence in self._sentences(
            description
        ):
            relation_sentence = (
                self._role_relation_sentence(
                    sentence
                )
            )

            for operational_pattern in operational_user_patterns:
                operational_match = operational_pattern.search(
                    relation_sentence
                )

                if not operational_match:
                    continue

                # Canonical scope polarity owns the matched relation prefix.
                # An exclusion may mention an actor/action, but that negative
                # scope fragment cannot establish operational-user authority.
                if is_scope_exclusion_statement(
                    relation_sentence[
                        :operational_match.end()
                    ]
                ):
                    continue

                # Request / demande is admitted as operational USER
                # authority only when the shared workflow grammar
                # independently confirms that the matched token is an
                # action predicate at the same location.
                if (
                    operational_pattern
                    is english_operational_request_pattern
                    or operational_pattern
                    is french_operational_request_pattern
                ):
                    predicate_start = (
                        operational_match.start(
                            2
                        )
                    )

                    request_is_action = any(
                        occurrence[
                            "action"
                        ]
                        == "demander"
                        and occurrence[
                            "match"
                        ].start()
                        == predicate_start
                        for occurrence in (
                            self._workflow_action_occurrences(
                                relation_sentence
                            )
                        )
                    )

                    if not request_is_action:
                        continue

                operational_name = self._clean_actor(
                    operational_match.group(1)
                )

                operational_key = comparison_key(
                    operational_name
                )

                if (
                    not operational_name
                    or not operational_key
                    or self._is_actor_identity_pronoun(
                        operational_name
                    )
                    or not self._looks_like_actor_phrase(
                        operational_name
                    )
                ):
                    continue

                operational_role = self._actor_role(
                    operational_name
                )

                if operational_role not in {
                    ActorRole.USER,
                    ActorRole.OPERATOR,
                    ActorRole.BUYER,
                    ActorRole.BENEFICIARY,
                }:
                    operational_role = ActorRole.USER

                identity = (
                    operational_key,
                    str(
                        operational_role.value
                    ),
                )

                if identity in seen:
                    continue

                seen.add(
                    identity
                )

                output.append(
                    (
                        operational_name,
                        operational_role,
                    )
                )

            for pattern, role in patterns:
                match = pattern.search(
                    relation_sentence
                )

                if not match:
                    continue

                # Canonical scope polarity owns the matched relation prefix.
                # A negative MVP/product-scope fragment can mention payment,
                # providers or decision roles, but cannot independently
                # materialize canonical actor-role authority.
                if is_scope_exclusion_statement(
                    relation_sentence[
                        :match.end()
                    ]
                ):
                    continue

                payer_subject_override = ""

                if (
                    role == ActorRole.PAYER
                    and (
                        pattern is english_payment_predicate_pattern
                        or pattern is french_payment_predicate_pattern
                    )
                ):
                    # group(1) spans everything preceding the payment
                    # predicate. It can contain a prior coordinated
                    # workflow:
                    #
                    #   "customer books ... and pays ..."
                    #
                    # The shared workflow subject authority owns that
                    # grammatical boundary.
                    payer_prefix = relation_sentence[
                        :match.end(1)
                    ]

                    # U7 universal economic-payer subject boundary.
                    #
                    # Examples:
                    #
                    #   X est le payeur economique et paie...
                    #   X is the economic payer and pays...
                    #
                    # The actor identity is X, never the complete
                    # relational predicate before the payment verb.
                    copular_payer_subject = ""

                    copular_payer_patterns = (
                        re.compile(
                            r"^\s*"
                            r"(?:le\s+|la\s+|les\s+|"
                            r"l['\u2019]\s*)?"
                            r"(.+?)\s+"
                            r"(?:est|serait|sera)\s+"
                            r"(?:le\s+|la\s+|"
                            r"l['\u2019]\s*)?"
                            r"payeur"
                            r"(?:\s+"
                            r"(?:e|\u00e9)conomique"
                            r")?"
                            r"\s+(?:et|&)\s*$",
                            re.IGNORECASE,
                        ),
                        re.compile(
                            r"^\s*(?:the\s+)?"
                            r"(.+?)\s+"
                            r"(?:"
                            r"is"
                            r"|would(?:\s+(?:probably|likely))?\s+be"
                            r"|will\s+be"
                            r")\s+"
                            r"(?:the\s+)?"
                            r"(?:economic\s+)?"
                            r"payer"
                            r"\s+(?:and|&)\s*$",
                            re.IGNORECASE,
                        ),
                    )

                    for copular_pattern in copular_payer_patterns:
                        copular_match = copular_pattern.search(
                            payer_prefix
                        )

                        if not copular_match:
                            continue

                        copular_payer_subject = self._clean_actor(
                            copular_match.group(1)
                        )

                        break

                    payer_subject = (
                        copular_payer_subject
                        or self._clean_actor(
                            self._workflow_subject_candidate(
                                payer_prefix
                            )
                        )
                    )

                    payer_subject_key = comparison_key(
                        payer_subject
                    )

                    # A delegation/capability clause before "pay" means
                    # the grammatical subject does not perform payment.
                    if (
                        not payer_subject_key
                        or re.search(
                            r"\b(?:"
                            r"allows?"
                            r"|enables?"
                            r"|lets?"
                            r"|permits?"
                            r"|authorizes?"
                            r"|asks?"
                            r"|requires?"
                            r"|prompts?"
                            r")\b",
                            payer_subject_key,
                            flags=re.IGNORECASE,
                        )
                        or re.search(
                            r"\b(?:"
                            r"to"
                            r"|can"
                            r"|could"
                            r"|may"
                            r"|might"
                            r"|should"
                            r"|must"
                            r"|cannot"
                            r"|not"
                            r")$",
                            payer_subject_key,
                            flags=re.IGNORECASE,
                        )
                    ):
                        continue

                    payer_subject_override = (
                        payer_subject
                    )

                # Explicit service execution is provider authority
                # independently of project archetype. The grammatical
                # subject must still be a valid canonical actor identity.
                if role == ActorRole.PROVIDER:
                    provider_candidate = self._clean_actor(
                        match.group(1)
                    )

                    if (
                        not provider_candidate
                        or self._is_actor_identity_pronoun(
                            provider_candidate
                        )
                        or not self._looks_like_actor_phrase(
                            provider_candidate
                        )
                    ):
                        continue

                # Avoid turning the whole left-hand side of a compound
                # "X forms the supply side and performs..." sentence
                # into an actor identity. That sentence is handled by
                # _declared_marketplace_sides(), which has stronger
                # structural authority.
                if (
                    role == ActorRole.PROVIDER
                    and any(
                        marker
                        in comparison_key(
                            match.group(1)
                        )
                        for marker in (
                            "supply side",
                            "provider side",
                            "seller side",
                            "marketplace",
                        )
                    )
                ):
                    continue

                if (
                    role
                    in {
                        ActorRole.PAYER,
                        ActorRole.DECISION_MAKER,
                    }
                    and self._role_relation_is_negated(
                        sentence,
                        role,
                    )
                ):
                    continue

                raw_names = (
                    self._split_actor_list(
                        match.group(1)
                    )
                    if (
                        role
                        == ActorRole.DECISION_MAKER
                    )
                    else [
                        payer_subject_override
                        or match.group(1)
                    ]
                )

                # U7 coordinated decision-actor normalization.
                #
                # At this point the surrounding relation has already
                # established DECISION_MAKER authority. We can therefore
                # normalize residual coordinated alternatives locally
                # without weakening the conservative global actor-list
                # grammar.
                #
                # Blind-B2.3 extends only this already-authoritative
                # relation. Global _split_actor_list() remains unchanged.
                if (
                    role
                    == ActorRole.DECISION_MAKER
                ):
                    decision_blob = clean_text(
                        match.group(1)
                    )

                    has_structural_list = (
                        bool(
                            re.search(
                                r"\b(?:ou|or)\b",
                                decision_blob,
                                flags=re.IGNORECASE,
                            )
                        )
                        or decision_blob.count(
                            ","
                        )
                        >= 2
                    )

                    if has_structural_list:
                        raw_names = [
                            item
                            for item
                            in re.split(
                                r"\s*,\s*"
                                r"(?:(?:ou|or)\s+)?"
                                r"|\s+\b(?:ou|or)\b\s+",
                                decision_blob,
                                flags=re.IGNORECASE,
                            )
                            if clean_text(
                                item
                            )
                        ]

                    normalized_raw_names: List[str] = []

                    for raw_name in raw_names:
                        residual_names = re.split(
                            r"\s+\b(?:ou|or)\b\s+",
                            clean_text(
                                raw_name
                            ),
                            flags=re.IGNORECASE,
                        )

                        for residual_name in residual_names:
                            residual_name = re.sub(
                                r"^(?:"
                                r"(?:le|la|les|the|a|an)"
                                r"\b\s+"
                                r"|l['\u2019]\s*"
                                r")",
                                "",
                                clean_text(
                                    residual_name
                                ),
                                flags=re.IGNORECASE,
                            )

                            residual_name = clean_text(
                                residual_name
                            )

                            if residual_name:
                                normalized_raw_names.append(
                                    residual_name
                                )

                    raw_names = normalized_raw_names

                for raw_name in raw_names:
                    name = self._clean_actor(
                        raw_name
                    )

                    key = (
                        comparison_key(name),
                        str(role.value),
                    )

                    if (
                        not name
                        or not key[0]
                        or key in seen
                    ):
                        continue

                    seen.add(
                        key
                    )

                    output.append(
                        (
                            name,
                            role,
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
        # Blind-B2.3 typed problem and decision-list authority.
        #
        # A canonical structured problem is data, not printable prose.
        # Only its semantic pain value may become ProblemContext.pain.
        # Empty structured pain must not suppress stronger fresh evidence
        # from the current user description.
        def structured_problem_text(
            value: Any,
        ) -> str:
            if isinstance(
                value,
                dict,
            ):
                return clean_text(
                    value.get(
                        "pain"
                    )
                )

            if isinstance(
                value,
                str,
            ):
                return clean_text(
                    value
                )

            return ""

        structured_problem = (
            structured_problem_text(
                structured.get(
                    "problem"
                )
            )
            or structured_problem_text(
                structured.get(
                    "core_problem"
                )
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

    # U7-A canonical semantic-section authority.
    #
    # Explicit field-style facts in the user's description outrank
    # inferred structured context. Each value stops at the next
    # recognized semantic label so semantic fields cannot absorb
    # neighboring sections.

    # Golden-R2 canonical refresh authority.
    #
    # These helpers resolve fresh explicit semantics before historical
    # compatibility projections can influence the canonical packet.
    #
    # They are language-grammar based and contain no project, sector,
    # country or archetype fixture.

    def _narrative_semantic_sections(
        self,
        description: str,
    ) -> Dict[str, List[str]]:
        """
        Extract semantic requirements written as ordinary prose.

        Colon-labelled sections remain authoritative through
        _explicit_semantic_sections(). This helper covers equivalent
        narrative formulations such as:

            "The main input data are ..."
            "Les donn?es d'entr?e principales sont ..."

        Human oversight and maintenance require explicit responsibility
        or process language; the mere word "maintenance" is insufficient.
        """
        output: Dict[
            str,
            List[str],
        ] = {
            "input_data": [],
            "output_decision": [],
            "human_oversight": [],
            "maintenance_model": [],
        }

        value_patterns: Dict[
            str,
            Tuple[re.Pattern[str], ...],
        ] = {
            "input_data": (
                re.compile(
                    r"\b(?:les\s+)?"
                    r"donn[e?]es?\s+"
                    r"d['?]entr[e?]e"
                    r"(?:\s+principales?)?\s+"
                    r"(?:sont|incluent|comprennent)\s+"
                    r"(.+)$",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:main\s+|primary\s+)?"
                    r"input\s+data\s+"
                    r"(?:are|is|include|includes|"
                    r"comprise|comprises)\s+"
                    r"(.+)$",
                    re.IGNORECASE,
                ),
            ),

            "output_decision": (
                re.compile(
                    r"\b(?:les\s+)?"
                    r"sorties?\s+principales?\s+"
                    r"(?:sont|incluent|comprennent)\s+"
                    r"(.+)$",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:main\s+|primary\s+)?"
                    r"outputs?\s+"
                    r"(?:are|is|include|includes|"
                    r"comprise|comprises)\s+"
                    r"(.+)$",
                    re.IGNORECASE,
                ),
            ),
        }

        for sentence in self._sentences(
            description
        ):
            for field_name, patterns in (
                value_patterns.items()
            ):
                for pattern in patterns:
                    match = pattern.search(
                        sentence
                    )

                    if not match:
                        continue

                    value = clean_text(
                        match.group(1)
                        .strip(
                            " .,:;"
                        )
                    )

                    if value:
                        output[
                            field_name
                        ].append(
                            value
                        )

                    break

            # Golden-R2.1 normalized French narrative fallback.
            #
            # Recognize ordinary French narrative field declarations
            # through canonical normalized text while preserving the
            # original user value.
            key = comparison_key(
                sentence
            )

            french_narrative_field = ""

            french_input_declaration = bool(
                re.search(
                    r"\bdonnees?\s+(?:d\s+)?entree"
                    r"(?:\s+principales?)?\s+"
                    r"(?:sont|incluent|comprennent)\b",
                    key,
                    flags=re.IGNORECASE,
                )
            )

            french_output_declaration = bool(
                re.search(
                    r"\bsorties?\s+principales?\s+"
                    r"(?:sont|incluent|comprennent)\b",
                    key,
                    flags=re.IGNORECASE,
                )
            )

            if french_input_declaration:
                french_narrative_field = (
                    "input_data"
                )

            elif french_output_declaration:
                french_narrative_field = (
                    "output_decision"
                )

            if french_narrative_field:
                narrative_value_match = re.search(
                    r"\b(?:"
                    r"sont|"
                    r"incluent|"
                    r"comprennent"
                    r")\b\s+(.+)$",
                    sentence,
                    flags=re.IGNORECASE,
                )

                if narrative_value_match:
                    narrative_value = clean_text(
                        narrative_value_match
                        .group(1)
                        .strip(
                            " .,:;"
                        )
                    )

                    if narrative_value:
                        output[
                            french_narrative_field
                        ].append(
                            narrative_value
                        )

            human_markers = (
                "human supervisor",
                "human reviewer",
                "human operator",
                "human validation",
                "human approval",
                "responsable humain",
                "superviseur humain",
                "operateur humain",
                "validation humaine",
                "controle humain",
            )

            human_action_markers = (
                "review",
                "valid",
                "verif",
                "approv",
                "autorisation",
                "responsable",
            )

            if (
                any(
                    marker in key
                    for marker
                    in human_markers
                )
                and any(
                    marker in key
                    for marker
                    in human_action_markers
                )
            ):
                output[
                    "human_oversight"
                ].append(
                    sentence
                )

            maintenance_markers = (
                "maintenance process",
                "maintenance model",
                "maintenance procedure",
                "maintenance responsibility",
                "responsible for maintenance",
                "maintained by",
                "maintains the",
                "processus de maintenance",
                "modele de maintenance",
                "procedure de maintenance",
                "responsabilite de maintenance",
                "responsable de la maintenance",
                "assure la maintenance",
                "maintient le",
            )

            if (
                "maintenance"
                in key
                and any(
                    marker in key
                    for marker
                    in maintenance_markers
                )
            ):
                output[
                    "maintenance_model"
                ].append(
                    sentence
                )

        return {
            field_name:
                unique_texts(
                    values
                )
            for field_name, values
            in output.items()
            if values
        }


    def _canonical_clarification_facts(
        self,
        *,
        project_context: Dict[str, Any],
        idea_readiness: Dict[str, Any] | None,
        analysis_data: Dict[str, Any],
        structured: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Resolve the canonical explicit-fact channel without recursively
        treating arbitrary historical analysis output as user truth.

        Lower-authority historical packet projections are read first.
        More direct current contexts overwrite them.
        """
        result: Dict[
            str,
            str,
        ] = {}

        readiness_data = (
            idea_readiness
            if isinstance(
                idea_readiness,
                dict,
            )
            else {}
        )

        stored_readiness = (
            analysis_data.get(
                "idea_readiness"
            )
            if isinstance(
                analysis_data.get(
                    "idea_readiness"
                ),
                dict,
            )
            else {}
        )

        def nested(
            container: Any,
            key: str,
        ) -> Dict[str, Any]:
            if not isinstance(
                container,
                dict,
            ):
                return {}

            value = container.get(
                key
            )

            return (
                value
                if isinstance(
                    value,
                    dict,
                )
                else {}
            )

        sources = (
            nested(
                analysis_data,
                "legacy_project_context",
            ),
            nested(
                analysis_data,
                "project_context_packet",
            ),
            nested(
                stored_readiness,
                "legacy_project_context",
            ),
            nested(
                stored_readiness,
                "project_context_packet",
            ),
            analysis_data,
            structured,
            nested(
                project_context,
                "legacy_project_context",
            ),
            nested(
                project_context,
                "project_context_packet",
            ),
            project_context,
            nested(
                readiness_data,
                "legacy_project_context",
            ),
            nested(
                readiness_data,
                "project_context_packet",
            ),
            readiness_data,
        )

        for source in sources:
            if not isinstance(
                source,
                dict,
            ):
                continue

            facts = source.get(
                "clarification_facts"
            )

            if not isinstance(
                facts,
                dict,
            ):
                continue

            for raw_field, raw_value in (
                facts.items()
            ):
                field = clean_text(
                    raw_field
                )

                value = clean_text(
                    raw_value
                )

                if (
                    field
                    and value
                ):
                    result[
                        field
                    ] = value

        return result


    def _reconcile_fresh_declared_actor_authority(
        self,
        *,
        actors: Sequence[ActorContext],
        description: str,
    ) -> List[ActorContext]:
        """
        A fresh explicit actor-role relation outranks a malformed legacy
        identity that merely appended role grammar to the same actor.

        Distinct actors and legitimate multi-role actors are preserved.
        """
        declared = (
            self._declared_actor_roles(
                description
            )
        )

        if not declared:
            return list(
                actors
            )

        declared_by_role: Dict[
            ActorRole,
            List[str],
        ] = {}

        for raw_name, role in declared:
            name = self._clean_actor(
                raw_name
            )

            key = comparison_key(
                name
            )

            if (
                not key
                or not name
            ):
                continue

            declared_by_role.setdefault(
                role,
                [],
            ).append(
                key
            )

        relation_markers = {
            ActorRole.PAYER: (
                "payer",
                "payeur",
                "payeur economique",
                "economic payer",
                "economic buyer",
                "acheteur economique",
            ),
            ActorRole.BUYER: (
                "buyer",
                "acheteur",
                "economic buyer",
                "acheteur economique",
            ),
            ActorRole.DECISION_MAKER: (
                "decision maker",
                "decision-maker",
                "decideur",
                "decideuse",
                "purchasing authority",
                "autorite d achat",
            ),
        }

        output: List[
            ActorContext
        ] = []

        seen: set[
            Tuple[str, str]
        ] = set()

        for actor in actors:
            actor_key = comparison_key(
                actor.name
            )

            if not actor_key:
                continue

            discard = False

            fresh_keys = (
                declared_by_role.get(
                    actor.role,
                    [],
                )
            )

            markers = (
                relation_markers.get(
                    actor.role,
                    (),
                )
            )

            for fresh_key in fresh_keys:
                if (
                    actor_key
                    == fresh_key
                ):
                    continue

                if not actor_key.startswith(
                    fresh_key + " "
                ):
                    continue

                suffix = actor_key[
                    len(
                        fresh_key
                    ):
                ].strip()

                if any(
                    marker in suffix
                    for marker
                    in markers
                ):
                    discard = True
                    break

            if discard:
                continue

            identity = (
                actor_key,
                actor.role.value,
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            output.append(
                actor
            )

        return output[:8]


    def _is_monetization_only_solution(
        self,
        value: str,
    ) -> bool:
        """
        Revenue mechanics are business-model facts, not a solution
        mechanism when no non-commercial operation is described.
        """
        text = clean_text(
            value
        )

        if not text:
            return False

        key = comparison_key(
            text
        )

        revenue_pattern = re.compile(
            r"\b(?:"
            r"pay|pays|paid|payment|payments|"
            r"paie|paient|payer|paiement|paiements|"
            r"commission|commissions|"
            r"fee|fees|frais|"
            r"subscription|subscriptions|abonnement|abonnements|"
            r"billing|invoice|invoicing|"
            r"facturation|facture|"
            r"revenue|revenues|revenu|revenus"
            r")\b",
            re.IGNORECASE,
        )

        if not revenue_pattern.search(
            key
        ):
            return False

        occurrences = (
            self._workflow_action_occurrences(
                text
            )
        )

        for occurrence in occurrences:
            action_key = comparison_key(
                occurrence.get(
                    "action"
                )
                or ""
            )

            surface_key = comparison_key(
                occurrence.get(
                    "surface"
                )
                or ""
            )

            payment_action = bool(
                re.fullmatch(
                    r"(?:"
                    r"pay|pays|paid|"
                    r"paie|paient|payer"
                    r")",
                    surface_key,
                    flags=re.IGNORECASE,
                )
                or action_key
                in {
                    "payer",
                }
            )

            if not payment_action:
                return False

        return True


    def _fresh_solution_candidates(
        self,
        sentences: Sequence[str],
    ) -> List[str]:
        """
        Select explicit operational mechanism sentences while excluding
        pure commercial/revenue framing.
        """
        output: List[
            str
        ] = []

        for sentence in sentences:
            if not self._canonical_action(
                sentence
            ):
                continue

            if self._is_problem_sentence(
                sentence
            ):
                continue

            if self._is_scope_only(
                sentence
            ):
                continue

            if self._is_monetization_only_solution(
                sentence
            ):
                continue

            output.append(
                sentence
            )

        return unique_texts(
            output
        )


    def _workflow_has_zero_object_polarity(
        self,
        value: str,
    ) -> bool:
        """
        Reject legacy positive-looking workflow projections whose action
        object itself explicitly denotes zero / none.

        Examples of the grammar class:
            action + no object
            action + directly + aucune object

        Conditional workflows mentioning absence later in the sentence
        are not rejected by this narrow object-position rule.
        """
        text = clean_text(
            value
        )

        if not text:
            return False

        for occurrence in (
            self._workflow_action_occurrences(
                text
            )
        ):
            match = occurrence.get(
                "match"
            )

            if match is None:
                continue

            tail_key = comparison_key(
                text[
                    match.end():
                ]
            )

            if re.match(
                r"^(?:(?:"
                r"directly|directement|"
                r"automatically|automatiquement"
                r")\s+){0,2}"
                r"(?:"
                r"aucun(?:e|s|es)?|"
                r"no|zero"
                r")\b",
                tail_key,
                flags=re.IGNORECASE,
            ):
                return True

        return False


    def _explicit_semantic_sections(
        self,
        description: str,
    ) -> Dict[str, List[str]]:
        label_patterns: Tuple[
            Tuple[str, str],
            ...,
        ] = (
            (
                "solution",
                r"(?:"
                r"proposed\s+solution"
                r"|solution\s+propos(?:e|\u00e9)e"
                r"|solution"
                r")",
            ),
            (
                "value_proposition",
                r"(?:"
                r"value\s+proposition"
                r"|proposed\s+value"
                r"|valeur\s+propos(?:e|\u00e9)e"
                r")",
            ),
            (
                "input_data",
                r"(?:"
                r"input\s+data"
                r"|input\s+information"
                r"|donn(?:e|\u00e9)es?\s+d['\u2019]entr(?:e|\u00e9)e"
                r")",
            ),
            (
                "output_decision",
                r"(?:"
                r"main\s+outputs?"
                r"|outputs?"
                r"|result(?:s)?\s+produced"
                r"|sorties?\s+principales?"
                r"|r(?:e|\u00e9)sultats?\s+produits?"
                r")",
            ),
            (
                "human_oversight",
                r"(?:"
                r"human\s+oversight"
                r"|human\s+validation"
                r"|contr(?:o|\u00f4)le\s+humain"
                r"|validation\s+humaine"
                r")",
            ),
            (
                "maintenance_model",
                r"(?:"
                r"maintenance\s+model"
                r"|maintenance\s+responsibility"
                r"|mod(?:e|\u00e8)le\s+de\s+maintenance"
                r"|responsabilit(?:e|\u00e9)\s+de\s+maintenance"
                r")",
            ),
            (
                "priority_workflow",
                r"(?:"
                r"priority\s+workflow"
                r"|main\s+workflow"
                r"|workflow\s+prioritaire"
                r"|processus\s+prioritaire"
                r")",
            ),
            (
                "business_model",
                r"(?:"
                r"business\s+model"
                r"|revenue\s+model"
                r"|mod(?:e|\u00e8)le\s+(?:e|\u00e9)conomique"
                r")",
            ),
            (
                "payment",
                r"(?:"
                r"payment"
                r"|pricing"
                r"|paiement"
                r"|tarification"
                r")",
            ),
            (
                "deployment_environment",
                r"(?:"
                r"deployment\s+environment"
                r"|operating\s+environment"
                r"|environnement\s+de\s+d(?:e|\u00e9)ploiement"
                r"|environnement\s+d['\u2019]utilisation"
                r")",
            ),
            (
                "business_hypothesis",
                r"(?:"
                r"business\s+hypothesis"
                r"|business\s+assumption"
                r"|hypoth(?:e|\u00e8)se\s+business"
                r"|hypoth(?:e|\u00e8)se\s+commerciale"
                r")",
            ),
            (
                "mvp_scope",
                r"(?:"
                r"mvp\s+scope"
                r"|p(?:e|\u00e9)rim(?:e|\u00e8)tre\s+mvp"
                r"|mvp"
                r")",
            ),
            (
                "constraints",
                r"(?:"
                r"constraints?"
                r"|contraintes?"
                r")",
            ),
            (
                "success_metrics",
                r"(?:"
                r"success\s+metrics?"
                r"|success\s+criteria"
                r"|m(?:e|\u00e9)triques?\s+de\s+succ(?:e|\u00e8)s"
                r"|crit(?:e|\u00e8)res?\s+de\s+succ(?:e|\u00e8)s"
                r")",
            ),
        )

        group_parts: List[str] = []

        for index, (
            _canonical_name,
            pattern,
        ) in enumerate(
            label_patterns
        ):
            group_parts.append(
                f"(?P<section_{index}>{pattern})"
            )

        label_re = re.compile(
            r"(?<!\w)(?:"
            + "|".join(
                group_parts
            )
            + r")\s*[:\uff1a]\s*",
            re.IGNORECASE,
        )

        matches = list(
            label_re.finditer(
                description or ""
            )
        )

        if not matches:
            return {}

        output: Dict[
            str,
            List[str],
        ] = {}

        for index, match in enumerate(
            matches
        ):
            canonical_name = ""

            for group_index, (
                name,
                _pattern,
            ) in enumerate(
                label_patterns
            ):
                if match.group(
                    f"section_{group_index}"
                ):
                    canonical_name = name
                    break

            if not canonical_name:
                continue

            value_start = match.end()

            value_end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(description)
            )

            value = clean_text(
                description[
                    value_start:value_end
                ]
            )

            value = re.sub(
                r"^[\s\-???]+",
                "",
                value,
            )

            value = re.sub(
                r"[\s;]+$",
                "",
                value,
            )

            value = clean_text(
                value
            )

            if not value:
                continue

            output.setdefault(
                canonical_name,
                []
            ).append(
                value
            )

        return {
            key: unique_texts(
                values
            )
            for key, values
            in output.items()
            if values
        }

    def _canonical_requirement_values(
        self,
        structured: Dict[str, Any],
        key: str,
    ) -> List[str]:
        value = (
            structured.get(
                key
            )
            if structured
            else None
        )

        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            values = [
                value
            ]

        elif isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            values = list(
                value
            )

        else:
            values = [
                value
            ]

        return unique_texts(
            clean_text(
                str(item)
            )
            for item in values
            if clean_text(
                str(item)
            )
        )

    def _extract_solution_text(
        self,
        *,
        sentences: Sequence[str],
        structured: Dict[str, Any],
    ) -> str:
        """
        Resolve the canonical operational solution mechanism.

        A valid structured mechanism is preserved.

        When a historical structured projection contains only pricing,
        payment, commission or other revenue mechanics, a fresh explicit
        operational mechanism from the current user description has
        stronger semantic authority.
        """
        structured_solution = clean_text(
            structured.get(
                "solution"
            )
            or structured.get(
                "solution_type"
            )
        )

        fresh_candidates = (
            self._fresh_solution_candidates(
                sentences
            )
        )

        if (
            structured_solution
            and not (
                fresh_candidates
                and self._is_monetization_only_solution(
                    structured_solution
                )
            )
        ):
            return structured_solution

        if fresh_candidates:
            return self._compact(
                " ".join(
                    fresh_candidates[:3]
                ),
                700,
            )

        return structured_solution

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

        for sentence in sentences:
            if not self._contains_any(
                sentence,
                self.MVP_MARKERS,
            ):
                continue

            marker_key = comparison_key(
                sentence
            )

            generic_scope_marker = any(
                marker in marker_key
                for marker in (
                    "limited to",
                    "limite a",
                    "se concentrera sur",
                    "focuses on",
                )
            )

            if (
                generic_scope_marker
                and not has_explicit_scope_reference(
                    sentence
                )
            ):
                continue

            raw_values.append(
                sentence
            )

        normalized_values: List[str] = []

        for raw_value in raw_values:
            if is_scope_exclusion_statement(
                raw_value
            ):
                continue

            normalized = self._normalize_scope_item(
                raw_value
            )

            if not normalized:
                continue

            normalized_values.extend(
                self._split_scope_items(
                    normalized
                )
            )

        # Explicit user-declared MVP scope is authoritative input.
        # Preserve every positive item after polarity filtering and
        # semantic deduplication; do not truncate it to an arbitrary
        # product-feature count.
        return self._semantic_unique(
            normalized_values,
            max_items=None,
        )


    def _split_scope_items(
        self,
        value: Any,
    ) -> List[str]:
        """
        Split explicit MVP/product scope only on real list boundaries.

        Coordinating conjunctions such as and/or/et/ou belong to the
        feature description and must not manufacture extra scope items.
        """
        if value is None:
            return []

        raw_text = str(
            value
        ).strip()

        if not raw_text:
            return []

        return [
            cleaned
            for part in re.split(
                r"\s*(?:;|\r?\n)\s*",
                raw_text,
            )
            if (
                cleaned := clean_text(
                    part
                )
            )
        ]


    def _actor_alias_forms(
        self,
        value: str,
    ) -> set[str]:
        """
        Build conservative comparison forms for an actor identity.

        This is intentionally limited to common singular/plural
        morphology. It is not a general stemming algorithm.

        Examples:
        - operateur / operateurs
        - administrateur / administrateurs
        - operator / operators
        - reviewer / reviewers
        - company / companies
        """
        key = comparison_key(
            value
        )

        if not key:
            return set()

        words = [
            token
            for token in key.split()
            if token
        ]

        if not words:
            return set()

        forms = {
            key,
        }

        last = words[-1]

        singular_candidates = {
            last,
        }

        if (
            len(last) > 4
            and last.endswith("ies")
        ):
            singular_candidates.add(
                f"{last[:-3]}y"
            )

        if (
            len(last) > 3
            and last.endswith("s")
            and not last.endswith(
                (
                    "ss",
                    "us",
                    "is",
                )
            )
        ):
            singular_candidates.add(
                last[:-1]
            )

        for candidate in singular_candidates:
            forms.add(
                " ".join(
                    words[:-1]
                    + [
                        candidate,
                    ]
                )
            )

        return {
            form
            for form in forms
            if form
        }


    def _workflow_subject_candidate(
        self,
        prefix: str,
    ) -> str:
        """
        Extract the closest local subject before a workflow action.

        The result is only an actor candidate. Canonical reconciliation
        happens separately.
        """
        text = clean_text(
            prefix
        )

        if not text:
            return ""

        segments = re.split(
            r"(?:"
            r"[,;:]"
            r"|\b(?:"
            r"quand|lorsque|when|while"
            r")\b"
            r"|lorsqu['\u2019]?"
            r")",
            text,
            flags=re.IGNORECASE,
        )

        candidate = ""

        for raw_segment in reversed(
            segments
        ):
            raw_segment = clean_text(
                raw_segment
            )

            if raw_segment:
                candidate = raw_segment
                break

        if not candidate:
            return ""

        # A new explicit subject may appear after a coordinated
        # predicate:
        #
        #   provider submits ... and buyer accepts ...
        #   transaction is closed et les utilisateurs evaluent ...
        #
        # Only split at a coordinator when the left side already
        # contains an actionable predicate. This avoids breaking
        # compound subjects such as "sales and marketing teams".
        coordinator_matches = list(
            re.finditer(
                r"\b(?:and|et|or|ou|then|puis)\b",
                candidate,
                flags=re.IGNORECASE,
            )
        )

        for coordinator in reversed(
            coordinator_matches
        ):
            left = clean_text(
                candidate[
                    :coordinator.start()
                ]
            )

            right = clean_text(
                candidate[
                    coordinator.end():
                ]
            )

            if (
                right
                and self._workflow_action_occurrences(
                    left
                )
            ):
                candidate = right
                break

        # A trailing coordination / sequence marker before the next
        # predicate inherits the subject of the preceding predicate:
        #
        #   "customer books a service and [pays ...]"
        #   "customer requests a service then [pays ...]"
        #
        # A compound actor such as "sales and marketing team" is
        # preserved because inheritance requires an actionable predicate
        # on the left side.
        trailing_link = re.search(
            r"\b(?:"
            r"and|et|or|ou|"
            r"then|puis|ensuite"
            r")\s*$",
            candidate,
            flags=re.IGNORECASE,
        )

        if trailing_link is not None:
            link_key = comparison_key(
                trailing_link.group(0)
            )

            left = clean_text(
                candidate[
                    :trailing_link.start()
                ]
            )

            left_actions = (
                self._workflow_action_occurrences(
                    left
                )
            )

            if left_actions:
                first_action = min(
                    left_actions,
                    key=lambda item: (
                        item["match"].start()
                    ),
                )

                inherited_subject = (
                    self._workflow_subject_candidate(
                        left[
                            :first_action[
                                "match"
                            ].start()
                        ]
                    )
                )

                if inherited_subject:
                    candidate = (
                        inherited_subject
                    )

            elif link_key in {
                "then",
                "puis",
                "ensuite",
            }:
                # Pure sequencing:
                #
                #   "customer then [pays ...]"
                #
                # contains no preceding action to inherit from.
                candidate = left

        # Control/modal clauses belong to the downstream predicate,
        # not to the local actor identity:
        #
        #   "manager decides to approve ..."
        #   "manager chooses to approve ..."
        #   "user can choose to pay ..."
        #
        # Preserve direct-object choice:
        #
        #   "user can choose a meal"
        #
        # because this boundary is applied only to a prefix that ends
        # in the infinitive connector immediately before another action.
        candidate = re.sub(
            r"\s+\b(?:"
            r"(?:(?:"
            r"can|could|may|might|must|should|"
            r"will|would"
            r")\s+)?"
            r"(?:"
            r"choose|chooses|chose|chosen|choosing|"
            r"decide|decides|decided|deciding"
            r")\s+to"
            r"|"
            r"(?:(?:"
            r"peut|peuvent|doit|doivent|"
            r"pourrait|pourraient"
            r")\s+)?"
            r"(?:"
            r"choisir|choisit|choisissent|"
            r"d(?:e|\u00e9)cider|"
            r"d(?:e|\u00e9)cide|"
            r"d(?:e|\u00e9)cident"
            r")\s+(?:de|d['\u2019])"
            r")\s*$",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        # Modal auxiliaries belong to the predicate, not to the actor.
        candidate = re.sub(
            r"\s+\b(?:"
            r"peut|peuvent|doit|doivent|"
            r"can|may|must|should|could|will"
            r")\b\s*$",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        candidate = re.sub(
            r"^(?:"
            r"(?:le|la|les|un|une|des|"
            r"the|a|an)\b\s*"
            r"|l['\u2019]\s*"
            r")",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        return clean_text(
            candidate.strip(
                " ,;:."
            )
        )


    def _workflow_actor_identity_prefix_match(
        self,
        local_value: str,
        canonical_value: str,
    ) -> bool:
        """
        Reconcile an explicit short local actor with a longer canonical
        actor identity without semantic synonym expansion.

        The local identity must match the beginning of the canonical
        identity token-by-token after conservative singular/plural
        normalization. Ambiguity is handled by the caller.

        Examples:
        - entreprise locataire -> l'entreprise locataire
        - entreprise proprietaire
          -> entreprises proprietaires d'equipements professionnels
        - chauffeurs -> chauffeurs independants
        """
        local_identity = (
            self._actor_alias_identity_key(
                local_value
            )
        )

        canonical_identity = (
            self._actor_alias_identity_key(
                canonical_value
            )
        )

        local_tokens = (
            comparison_key(
                local_identity
            ).split()
        )

        canonical_tokens = (
            comparison_key(
                canonical_identity
            ).split()
        )

        if (
            not local_tokens
            or not canonical_tokens
            or len(local_tokens)
            > len(canonical_tokens)
        ):
            return False

        for local_token, canonical_token in zip(
            local_tokens,
            canonical_tokens,
        ):
            local_forms = (
                self._actor_alias_forms(
                    local_token
                )
            )

            canonical_forms = (
                self._actor_alias_forms(
                    canonical_token
                )
            )

            if not (
                local_forms
                & canonical_forms
            ):
                return False

        return True


    def _workflow_actor_for_sentence(
        self,
        sentence: str,
        *,
        action_start: int,
        actors: Sequence[ActorContext],
        fallback_actor: str = "",
    ) -> str:
        """
        Resolve workflow ownership from the local sentence.

        Priority:
        1. exact canonical actor;
        2. conservative canonical singular/plural alias;
        3. explicit technical executor;
        4. pronoun continuation;
        5. explicit local actor candidate.

        The discourse fallback is used only for pronouns. An unresolved
        explicit subject must never inherit the previous actor silently.
        """
        text = clean_text(
            sentence
        )

        if not text:
            return ""

        prefix = clean_text(
            sentence[
                : max(
                    0,
                    action_start,
                )
            ]
        )

        prefix_key = comparison_key(
            prefix
        )

        if not prefix_key:
            return ""

        subject_candidate = (
            self._workflow_subject_candidate(
                prefix
            )
        )

        subject_key = comparison_key(
            subject_candidate
        )

        # -------------------------------------------------
        # 1. Exact canonical actor mentioned locally.
        # -------------------------------------------------

        exact_matches: List[
            Tuple[
                int,
                int,
                str,
            ]
        ] = []

        for actor in actors:
            actor_key = comparison_key(
                actor.name
            )

            if not actor_key:
                continue

            variants = {
                actor_key,
            }

            geographic_head = re.split(
                r"\s+\b(?:en|in)\b\s+",
                actor_key,
                maxsplit=1,
            )[0].strip()

            if geographic_head:
                variants.add(
                    geographic_head
                )

            for variant in variants:
                if len(variant) < 3:
                    continue

                position = subject_key.rfind(
                    variant
                )

                if position < 0:
                    continue

                exact_matches.append(
                    (
                        position,
                        len(variant),
                        actor.name,
                    )
                )

        if exact_matches:
            exact_matches.sort(
                key=lambda value: (
                    value[0],
                    value[1],
                ),
                reverse=True,
            )

            return exact_matches[0][2]

        # -------------------------------------------------
        # 2. Leading local actor identity reconciliation.
        # -------------------------------------------------

        if subject_candidate:
            subject_words = [
                token
                for token in clean_text(
                    subject_candidate
                ).split()
                if token
            ]

            for prefix_length in range(
                min(
                    len(subject_words),
                    8,
                ),
                0,
                -1,
            ):
                leading_candidate = clean_text(
                    " ".join(
                        subject_words[
                            :prefix_length
                        ]
                    )
                )

                leading_matches = {
                    actor.name
                    for actor in actors
                    if (
                        self._workflow_actor_identity_prefix_match(
                            leading_candidate,
                            actor.name,
                        )
                    )
                }

                # Prefer the longest local identity that resolves
                # to exactly one canonical actor. Short ambiguous
                # heads never select arbitrarily.
                if len(leading_matches) == 1:
                    return next(
                        iter(
                            leading_matches
                        )
                    )

        # -------------------------------------------------
        # 3. Canonical short-identity reconciliation.
        # -------------------------------------------------

        if subject_candidate:
            identity_matches = {
                actor.name
                for actor in actors
                if (
                    self._workflow_actor_identity_prefix_match(
                        subject_candidate,
                        actor.name,
                    )
                )
            }

            # A short local identity is authoritative only when it
            # points to exactly one canonical actor.
            if len(identity_matches) == 1:
                return next(
                    iter(
                        identity_matches
                    )
                )

        # -------------------------------------------------
        # 2. Conservative canonical alias reconciliation.
        # -------------------------------------------------

        if subject_key:
            subject_forms = (
                self._actor_alias_forms(
                    subject_candidate
                )
            )

            alias_matches: List[
                Tuple[
                    int,
                    str,
                ]
            ] = []

            for actor in actors:
                actor_key = comparison_key(
                    actor.name
                )

                if not actor_key:
                    continue

                variants = {
                    actor_key,
                }

                geographic_head = re.split(
                    r"\s+\b(?:en|in)\b\s+",
                    actor_key,
                    maxsplit=1,
                )[0].strip()

                if geographic_head:
                    variants.add(
                        geographic_head
                    )

                for variant in variants:
                    canonical_forms = (
                        self._actor_alias_forms(
                            variant
                        )
                    )

                    if not (
                        subject_forms
                        & canonical_forms
                    ):
                        continue

                    alias_matches.append(
                        (
                            len(variant),
                            actor.name,
                        )
                    )

            if alias_matches:
                alias_matches.sort(
                    key=lambda value: value[0],
                    reverse=True,
                )

                longest = alias_matches[0][0]

                best_names = {
                    name
                    for length, name in alias_matches
                    if length == longest
                }

                # Ambiguous aliases must not choose arbitrarily.
                if len(best_names) == 1:
                    return next(
                        iter(
                            best_names
                        )
                    )

        # -------------------------------------------------
        # 3. Explicit technical executor.
        # -------------------------------------------------

        technical_patterns = (
            (
                r"\b(?:le\s+|la\s+|"
                r"l['\u2019]\s*)?"
                r"syst(?:e|\u00e8)me\b",
                "syst\u00e8me",
            ),
            (
                r"\b(?:the\s+)?system\b",
                "system",
            ),
            (
                r"\b(?:la\s+|"
                r"l['\u2019]\s*)?"
                r"plateforme\b",
                "plateforme",
            ),
            (
                r"\b(?:the\s+)?platform\b",
                "platform",
            ),
            (
                r"\b(?:l['\u2019]\s*)?"
                r"application\b",
                "application",
            ),
            (
                r"\b(?:the\s+)?application\b",
                "application",
            ),
            (
                r"\b(?:le\s+)?logiciel\b",
                "logiciel",
            ),
            (
                r"\b(?:the\s+)?software\b",
                "software",
            ),
        )

        technical_matches: List[
            Tuple[
                int,
                str,
            ]
        ] = []

        for pattern, label in technical_patterns:
            for match in re.finditer(
                pattern,
                prefix,
                flags=re.IGNORECASE,
            ):
                technical_matches.append(
                    (
                        match.start(),
                        label,
                    )
                )

        if technical_matches:
            technical_matches.sort(
                key=lambda value: value[0],
                reverse=True,
            )

            return technical_matches[0][1]

        # -------------------------------------------------
        # 4. Pronoun continuation only.
        # -------------------------------------------------

        if re.fullmatch(
            r"(?:"
            r"il|elle|ils|elles|on|"
            r"he|she|they|it"
            r")",
            subject_key,
        ):
            return clean_text(
                fallback_actor
            )

        # A fragment such as
        # "consulte les offres disponibles" or
        # "proprietaire accepte ou" is not a new actor.
        if (
            subject_candidate
            and self._workflow_action_occurrences(
                subject_candidate
            )
        ):
            return clean_text(
                fallback_actor
            )

        # -------------------------------------------------
        # 5. Explicit local actor not present canonically.
        # -------------------------------------------------

        if (
            subject_candidate
            and self._looks_like_actor_phrase(
                subject_candidate
            )
        ):
            cleaned = self._clean_actor(
                subject_candidate
            )

            if cleaned:
                return cleaned

        # Never leak the previous actor across an unrelated sentence.
        return ""


    def _extract_workflows(
        self,
        *,
        sentences: Sequence[str],
        actors: Sequence[ActorContext],
        mvp_scope: Sequence[str],
        structured: Dict[str, Any],
        language: str,
    ) -> List[WorkflowContext]:
        """
        Build canonical workflows from explicit user actions.

        Multiple coordinated actions in the same sentence are treated
        as separate workflows. Search/intelligence hints remain
        secondary and never override explicit user actions.
        """
        preferred_actor_name = self._preferred_actor(
            actors
        )

        last_actor_name = preferred_actor_name

        scope_keys = {
            comparison_key(item)
            for item in mvp_scope
        }

        candidates: List[
            Dict[str, Any]
        ] = []

        def add_candidates(
            sentence: str,
            *,
            index: int,
            explicit: bool,
            priority_explicit: bool = False,
        ) -> None:
            nonlocal last_actor_name

            occurrences = (
                self._workflow_action_occurrences(
                    sentence
                )
            )

            if not occurrences:
                return

            current_sentence_actor = ""

            alternative_tail_orders: set[int] = set()

            for order, occurrence in enumerate(
                occurrences
            ):
                if order in alternative_tail_orders:
                    continue

                match = occurrence["match"]

                occurrence_actor = (
                    self._workflow_actor_for_sentence(
                        sentence,
                        action_start=match.start(),
                        actors=actors,
                        fallback_actor=(
                            current_sentence_actor
                            or last_actor_name
                        ),
                    )
                )

                if (
                    not occurrence_actor
                    and order > 0
                    and current_sentence_actor
                ):
                    local_subject = (
                        self._workflow_subject_candidate(
                            sentence[
                                :match.start()
                            ]
                        )
                    )

                    if (
                        not local_subject
                        or self._workflow_action_occurrences(
                            local_subject
                        )
                    ):
                        occurrence_actor = (
                            current_sentence_actor
                        )

                if occurrence_actor:
                    current_sentence_actor = (
                        occurrence_actor
                    )
                    last_actor_name = (
                        occurrence_actor
                    )

                next_start = len(
                    sentence
                )

                alternative_occurrence = None

                if (
                    order + 1
                    < len(occurrences)
                ):
                    next_occurrence = (
                        occurrences[
                            order + 1
                        ]
                    )

                    between_actions = (
                        sentence[
                            match.end():
                            next_occurrence[
                                "match"
                            ].start()
                        ]
                    )

                    is_alternative_pair = bool(
                        re.fullmatch(
                            r"\s*(?:or|ou)\s*",
                            between_actions,
                            flags=re.IGNORECASE,
                        )
                    )

                    if is_alternative_pair:
                        alternative_occurrence = (
                            next_occurrence
                        )

                        # "approve or reject X" and
                        # "accepter ou refuser X" express one
                        # explicit business alternative with a
                        # shared object. Preserve the complete
                        # phrase instead of manufacturing two
                        # truncated workflow clauses.
                        alternative_tail_orders.add(
                            order + 1
                        )

                        next_start = (
                            occurrences[
                                order + 2
                            ]["match"].start()
                            if (
                                order + 2
                                < len(
                                    occurrences
                                )
                            )
                            else len(
                                sentence
                            )
                        )
                    else:
                        next_action_start = (
                            next_occurrence[
                                "match"
                            ].start()
                        )

                        next_start = (
                            next_action_start
                        )

                        # ------------------------------------------
                        # Canonical coordinated-predicate boundary.
                        #
                        # The next action occurrence already owns
                        # action identity. The clause boundary must
                        # therefore stop before the coordination /
                        # sequence marker that introduces that next
                        # predicate, including an explicit new subject:
                        #
                        #   books a service
                        #   and the company pays ...
                        #
                        #   reserve un service
                        #   et l'entreprise paie ...
                        #
                        # Use the LAST structural boundary before the
                        # next canonical action so compound objects are
                        # preserved:
                        #
                        #   books transport and accommodation
                        #   and the company pays ...
                        #
                        # No action vocabulary is duplicated here.
                        # ------------------------------------------

                        between_actions = (
                            sentence[
                                match.end():
                                next_action_start
                            ]
                        )

                        predicate_boundaries = list(
                            re.finditer(
                                r"[,;]"
                                r"|\b(?:"
                                r"and|et|or|ou|"
                                r"then|puis|ensuite"
                                r")\b",
                                between_actions,
                                flags=re.IGNORECASE,
                            )
                        )

                        if predicate_boundaries:
                            boundary = (
                                predicate_boundaries[
                                    -1
                                ]
                            )

                            next_start = (
                                match.end()
                                + boundary.start()
                            )

                clause = sentence[
                    match.start():
                    next_start
                ]

                clause = re.sub(
                    r"(?:,\s*|\s+)"
                    r"(?:and|et|then|puis)\s*$",
                    "",
                    clause.strip(),
                    flags=re.IGNORECASE,
                )

                clause = clause.strip(
                    " ,;."
                )

                if not clause:
                    continue

                local_match = (
                    occurrence["pattern"].search(
                        clause
                    )
                )

                if local_match is None:
                    continue

                candidates.append(
                    {
                        "sentence": clause,
                        "action": occurrence[
                            "action"
                        ],
                        "surface": occurrence[
                            "surface"
                        ],
                        "match": local_match,
                        "index": (
                            index * 100
                            + order
                        ),
                        "score": (
                            self._workflow_score(
                                clause,
                                occurrence[
                                    "action"
                                ],
                            )
                            + (
                                100
                                if priority_explicit
                                else 0
                            )
                        ),
                        "explicit": explicit,
                        "priority_explicit": (
                            priority_explicit
                        ),
                        "actor": occurrence_actor,
                        "alternative_action": (
                            alternative_occurrence[
                                "action"
                            ]
                            if alternative_occurrence
                            else ""
                        ),
                        "alternative_surface": (
                            alternative_occurrence[
                                "surface"
                            ]
                            if alternative_occurrence
                            else ""
                        ),
                    }
                )

        # ----------------------------------------------------------
        # Explicit workflow provenance authority.
        #
        # User-declared priority is stronger than lexical action
        # priority:
        #
        #   explicit priority workflow
        #       >
        #   incidental activity
        #
        # This prevents a generic high-priority verb such as
        # "monitor" from replacing a flow explicitly identified by
        # the user.
        #
        # The block can be written as prose:
        #
        #   "Le workflow prioritaire est le suivant: ..."
        #
        # or as a structured section followed by Step/Etape lines.
        # ----------------------------------------------------------

        priority_marker_pattern = re.compile(
            r"\b(?:"
            r"workflow|processus|parcours"
            r")\s+"
            r"(?:"
            r"prioritaire|principal|cle"
            r")\b"
            r"|"
            r"\b(?:"
            r"priority|primary|main|key"
            r")\s+"
            r"(?:workflow|process)\b",
            flags=re.IGNORECASE,
        )

        secondary_transition_pattern = re.compile(
            r"\b(?:"
            r"aussi|egalement|"
            r"also|additionally|in\s+addition"
            r")\b",
            flags=re.IGNORECASE,
        )

        structured_label_pattern = re.compile(
            r"^[^:]{1,80}:\s*",
            flags=re.IGNORECASE,
        )

        step_label_pattern = re.compile(
            r"^(?:etape|step)\s+\d+\b",
            flags=re.IGNORECASE,
        )

        priority_block_active = False

        for index, sentence in enumerate(
            sentences
        ):
            sentence_key = comparison_key(
                sentence
            )

            clean_sentence = clean_text(
                sentence
            )

            has_priority_marker = bool(
                priority_marker_pattern.search(
                    sentence_key
                )
            )

            is_step_label = bool(
                step_label_pattern.match(
                    sentence_key
                )
            )

            if has_priority_marker:
                priority_block_active = True

            elif priority_block_active:
                if secondary_transition_pattern.search(
                    sentence_key
                ):
                    priority_block_active = False

                elif (
                    structured_label_pattern.match(
                        clean_sentence
                    )
                    and not is_step_label
                ):
                    priority_block_active = False

            if self._workflow_sentence_is_non_action_context(
                sentence
            ):
                if (
                    priority_block_active
                    and not has_priority_marker
                    and not is_step_label
                ):
                    priority_block_active = False

                continue

            if self._is_problem_sentence(
                sentence
            ):
                continue

            add_candidates(
                sentence,
                index=index,
                explicit=True,
                priority_explicit=(
                    priority_block_active
                ),
            )

        # Legacy structured workflows may still exist in old persisted
        # packets. They remain lower-confidence compatibility inputs.
        for offset, value in enumerate(
            self._listify(
                structured.get(
                    "priority_workflows"
                )
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

            if self._workflow_has_zero_object_polarity(
                value
            ):
                continue

            before = len(candidates)

            add_candidates(
                value,
                index=10_000 + offset,
                explicit=False,
            )

            for candidate in candidates[
                before:
            ]:
                candidate["score"] -= 15

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

        for candidate_index, candidate in enumerate(
            candidates
        ):
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

            output_text = self._output_phrase(
                candidate["sentence"]
            )

            object_key = comparison_key(
                object_text
            )
            output_key = comparison_key(
                output_text
            )

            if (
                object_key
                and output_key
                and (
                    object_key == output_key
                    or output_key in object_key
                )
            ):
                output_text = ""

            localized_action = (
                self._localized_workflow_action(
                    candidate["action"],
                    candidate["surface"],
                    language,
                )
            )

            alternative_action = (
                candidate.get(
                    "alternative_action"
                )
                or ""
            )

            alternative_surface = (
                candidate.get(
                    "alternative_surface"
                )
                or ""
            )

            if (
                alternative_action
                and alternative_surface
            ):
                localized_alternative_action = (
                    self._localized_workflow_action(
                        alternative_action,
                        alternative_surface,
                        language,
                    )
                )

                object_text = re.sub(
                    (
                        r"^(\s*(?:or|ou)\s+)"
                        + re.escape(
                            alternative_surface
                        )
                        + r"\b"
                    ),
                    lambda match: (
                        match.group(1)
                        + localized_alternative_action
                    ),
                    object_text,
                    count=1,
                    flags=re.IGNORECASE,
                )

            workflow = WorkflowContext(
                name=self._workflow_name(
                    action=localized_action,
                    object_text=object_text,
                    result=result_text,
                    output=output_text,
                    language=language,
                ),
                actor=clean_text(
                    candidate.get(
                        "actor"
                    )
                    or ""
                ),
                action=localized_action,
                object=object_text,
                result=result_text,
                output=output_text,
                is_explicit=bool(
                    candidate["explicit"]
                ),
                confidence=(
                    0.90
                    if (
                        candidate["explicit"]
                        and candidate_index == 0
                    )
                    else (
                        0.82
                        if candidate[
                            "explicit"
                        ]
                        else 0.50
                    )
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


    def _workflow_sentence_is_non_action_context(
        self,
        sentence: str,
    ) -> bool:
        """
        Exclude scope or constraint declarations without erasing
        real actor workflows merely because the sentence mentions
        an MVP, pilot, first version or prototype.

        All matching below is performed on comparison_key(), so the
        rule remains accent-insensitive and the source stays ASCII-safe.
        """
        text = clean_text(
            sentence
        )

        if not text:
            return True

        if is_scope_exclusion_statement(
            text
        ):
            return True

        key = comparison_key(
            text
        )

        meta_context_subject = re.match(
            r"^"
            r"(?:(?:"
            r"l|le|la|les|the|our|notre|nos|"
            r"my|mon|ma|mes"
            r")\s+)?"
            r"(?:(?:"
            r"initial|initiale|"
            r"principal|principale|"
            r"main|primary|key|validation"
            r")\s+)*"
            r"(?:"
            r"objectif|objectifs|"
            r"objective|objectives|"
            r"goal|goals|"
            r"hypothese|hypotheses|"
            r"hypothesis|"
            r"assumption|assumptions"
            r")"
            r"(?:\s+(?:"
            r"initial|initiale|"
            r"principal|principale|"
            r"main|primary|key|"
            r"de\s+validation|of\s+validation"
            r"))*\b",
            key,
            flags=re.IGNORECASE,
        )

        if meta_context_subject is not None:
            return True

        if re.match(
            r"^"
            r"(?:(?:"
            r"the|les|des|our|nos|my|mes|"
            r"your|vos|their|leurs"
            r")\s+)?"
            r"(?:(?:"
            r"main|primary|key|major|"
            r"technical|operational|regulatory|business|"
            r"principal(?:e|es|aux)?"
            r")\s+)*"
            r"(?:constraints?|contraintes?)\b",
            key,
        ):
            return True

        scope_subject = re.match(
            r"^\s*"
            r"(?:(?:the|le|la)\s+)?"
            r"(?:"
            r"mvp"
            r"|minimum\s+viable\s+product"
            r"|first\s+version"
            r"|initial\s+version"
            r"|premiere\s+version"
            r"|version\s+initiale"
            r"|(?:first|premier|premiere)\s+"
            r"(?:pilot|pilote)"
            r"|pilot"
            r"|pilote"
            r"|prototype"
            r")\b",
            key,
            flags=re.IGNORECASE,
        )

        if scope_subject is None:
            return False

        tail_key = key[
            scope_subject.end():
        ].strip(
            " ,:;-"
        )

        if not tail_key:
            return True

        scope_predicate = re.compile(
            r"^(?:"
            r"cover(?:s|ed|ing)?"
            r"|support(?:s|ed|ing)?"
            r"|(?:must|should|shall|will|would|can|could|may)\s+"
            r"(?:"
            r"cover|support|include|contain"
            r"|focus\s+on"
            r"|be\s+limited\s+to"
            r"|be\s+designed\s+to"
            r")"
            r"|(?:"
            r"doit|doivent|"
            r"devra|devront|"
            r"devrait|devraient|"
            r"peut|peuvent|"
            r"pourra|pourront|"
            r"pourrait|pourraient"
            r")\s+"
            r"(?:"
            r"couvrir|inclure|comprendre|contenir"
            r"|se\s+limiter\s+a"
            r"|se\s+concentrer\s+sur"
            r"|prendre\s+en\s+charge"
            r")"
            r"|includ(?:e|es|ed|ing)"
            r"|contain(?:s|ed|ing)?"
            r"|compris(?:e|es|ed|ing)?"
            r"|consist(?:s|ed|ing)?\s+of"
            r"|focus(?:es|ed|ing)?\s+on"
            r"|(?:is|are|was|were|will\s+be)\s+"
            r"limited\s+to"
            r"|(?:is|was|will\s+be)\s+"
            r"designed\s+to"
            r"|couvr(?:e|ent|ira|iront)"
            r"|inclu(?:t|ent|ra|ront)"
            r"|comprend(?:s|ent|ra|ront)?"
            r"|contien(?:t|nent|dra|dront)"
            r"|se\s+limit(?:e|ent|era|eront)\s+a"
            r"|(?:est|sont|sera|seront)\s+"
            r"limit(?:e|ee|es|ees)\s+a"
            r"|se\s+concentr(?:e|ent|era|eront)\s+sur"
            r"|porte(?:nt|ra|ront)?\s+sur"
            r"|prend\s+en\s+charge"
            r")\b",
            flags=re.IGNORECASE,
        )

        if scope_predicate.match(
            tail_key
        ):
            return True

        occurrences = (
            self._workflow_action_occurrences(
                tail_key
            )
        )

        if not occurrences:
            return True

        first_match = occurrences[
            0
        ]["match"]

        prefix = tail_key[
            : first_match.start()
        ].strip()

        # Direct capability of the scope artifact:
        # "The MVP detects ...".
        if not prefix:
            return True

        # Modal capability of the scope artifact:
        # "The MVP will detect ...".
        if re.fullmatch(
            r"(?:"
            r"will|would|can|could|must|should|may|shall"
            r"|doit|doivent|devra|devront"
            r"|peut|peuvent"
            r"|va|vont"
            r")",
            prefix,
        ):
            return True

        # A phrase remains before the first action:
        # "pilot users inspect ..."
        # "the MVP lets users upload ..."
        # Therefore a real actor/delegation is present.
        return False

    def _workflow_match_is_negated_predicate(
        self,
        *,
        sentence: str,
        item: Dict[str, Any],
    ) -> bool:
        """
        Reject an action occurrence when the user explicitly negates
        that predicate.

        This is workflow polarity authority, not MVP/scope authority.

        Examples rejected:
        - "Le logiciel ne commande aucune machine."
        - "Le syst?me ne doit pas envoyer automatiquement..."
        - "The software does not control machines."
        - "The service will not automatically approve requests."

        Positive statements remain eligible.

        The rule is grammar-based and contains no project, sector,
        region or archetype vocabulary.
        """
        match = item.get(
            "match"
        )

        if match is None:
            return False

        prefix_key = comparison_key(
            sentence[
                :match.start()
            ]
        ).strip()

        suffix_key = comparison_key(
            sentence[
                match.end():
            ]
        ).strip()

        prefix_tail = " ".join(
            prefix_key.split()[
                -10:
            ]
        )

        suffix_head = " ".join(
            suffix_key.split()[
                :7
            ]
        )

        # ------------------------------------------------------
        # English predicate negation.
        #
        # does not control
        # will not approve
        # cannot send
        # never records
        # ------------------------------------------------------

        if re.search(
            r"(?:"
            r"\b(?:"
            r"do|does|did|"
            r"is|are|was|were|"
            r"will|would|"
            r"can|could|"
            r"should|must|"
            r"may|might|shall|"
            r"has|have|had"
            r")\s+not\b"
            r"|\bcannot\b"
            r"|\bnever\b"
            r")"
            r"(?:\s+[^\s]+){0,4}\s*$",
            prefix_tail,
            flags=re.IGNORECASE,
        ):
            return True

        # comparison_key() may separate apostrophe contractions:
        #
        # doesn't -> doesn t
        # can't    -> can t
        #
        # Keep those forms inside the same universal authority.
        if re.search(
            r"\b(?:"
            r"don|doesn|didn|"
            r"isn|aren|wasn|weren|"
            r"won|wouldn|"
            r"can|couldn|"
            r"shouldn|mustn|"
            r"hasn|haven|hadn"
            r")\s+t\b"
            r"(?:\s+[^\s]+){0,4}\s*$",
            prefix_tail,
            flags=re.IGNORECASE,
        ):
            return True

        # ------------------------------------------------------
        # French predicate negation.
        #
        # ne commande pas
        # ne commande aucune machine
        # ne doit pas commander
        # ne peut jamais envoyer
        #
        # French commonly splits negation around the predicate,
        # therefore inspect both the close prefix and close suffix.
        # ------------------------------------------------------

        has_french_ne = bool(
            re.search(
                r"(?:^|\s)(?:ne|n)\b",
                prefix_tail,
                flags=re.IGNORECASE,
            )
        )

        if has_french_ne:
            if re.search(
                r"\b(?:"
                r"pas|plus|jamais|"
                r"aucun|aucune|"
                r"aucuns|aucunes|"
                r"rien|personne|ni"
                r")\b",
                prefix_tail,
                flags=re.IGNORECASE,
            ):
                return True

            if re.search(
                r"\b(?:"
                r"pas|plus|jamais|"
                r"aucun|aucune|"
                r"aucuns|aucunes|"
                r"rien|personne|ni"
                r")\b",
                suffix_head,
                flags=re.IGNORECASE,
            ):
                return True

        return False


    def _workflow_match_is_conditional_passive_context(
        self,
        *,
        sentence: str,
        item: Dict[str, Any],
    ) -> bool:
        """
        Reject a passive state predicate used only inside the leading
        conditional clause of a sentence.

        Rejected:
        - Lorsque la demande est acceptee, le client paie...
        - Lorsque la demande a ete acceptee, le client paie...
        - When the request is accepted, the customer pays...
        - When the request has been accepted, the customer pays...

        Preserved:
        - Le fournisseur accepte la demande.
        - When the provider accepts the request, the system sends...
        - The transaction is closed.
        """
        match = item.get(
            "match"
        )

        if match is None:
            return False

        start = match.start()

        if start <= 0:
            return False

        # Only an occurrence located inside the leading clause can
        # represent the passive condition. Later business actions
        # remain eligible.
        clause_delimiter = re.search(
            r"[,;]",
            sentence,
        )

        if (
            clause_delimiter is None
            or start
            >= clause_delimiter.start()
        ):
            return False

        sentence_key = comparison_key(
            sentence
        )

        conditional_start = re.match(
            r"^\s*(?:"
            r"when|if|while|once|"
            r"quand|lorsque|si|lorsqu"
            r")\b",
            sentence_key,
            flags=re.IGNORECASE,
        )

        if conditional_start is None:
            return False

        prefix_key = comparison_key(
            sentence[
                :start
            ]
        ).strip()

        passive_auxiliary = re.search(
            r"(?:"
            r"has\s+been|"
            r"have\s+been|"
            r"had\s+been|"
            r"will\s+be|"
            r"is|are|was|were|"
            r"be|been|being|"
            r"gets|got|"
            r"a\s+ete|"
            r"ont\s+ete|"
            r"avait\s+ete|"
            r"avaient\s+ete|"
            r"sera|seront|"
            r"est|sont|"
            r"etait|etaient"
            r")\s*$",
            prefix_key,
            flags=re.IGNORECASE,
        )

        return (
            passive_auxiliary
            is not None
        )


    def _workflow_action_occurrences(
        self,
        sentence: str,
    ) -> List[Dict[str, Any]]:
        """
        Find every actionable verb occurrence in a sentence.

        ACTION_PATTERNS remain the shared vocabulary.
        The extension below contains only generic workflow verbs;
        it contains no sector, archetype or domain-specific object.
        """
        extra_patterns: Tuple[
            Tuple[re.Pattern[str], str],
            ...,
        ] = (
            # U2 universal comparison workflow authority.
            #
            # Comparison is a real generic business action, not merely
            # a grammatical boundary.
            (
                re.compile(
                    r"\bcompare(?:s|d|ing)?\b"
                    r"|\bcompar"
                    r"(?:"
                    r"er|e|es|ent|"
                    r"ait|aient|"
                    r"era|eront|"
                    r"ant"
                    r")\b",
                    re.IGNORECASE,
                ),
                "comparer",
            ),
            (
                re.compile(
                    r"\bcreat(?:e|es|ed|ing)?\b"
                    r"|\bcr(?:e|\u00e9)"
                    r"(?:er|e|es|ent|ait|ant)?\b",
                    re.IGNORECASE,
                ),
                "creer",
            ),
            (
                re.compile(
                    r"\brecord(?:s|ed|ing)?\b"
                    r"|\benregistr"
                    r"(?:er|e|\u00e9|ent|ait|ant)?\b",
                    re.IGNORECASE,
                ),
                "enregistrer",
            ),
            (
                re.compile(
                    r"\bapprove(?:s|d|ing)?\b"
                    r"|\bvalidate(?:s|d|ing)?\b"
                    r"|\bapprouv"
                    r"(?:er|e|\u00e9|ent|ait|ant)?\b"
                    r"|\bvalid"
                    r"(?:er|e|es|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "approuver",
            ),
            (
                re.compile(
                    r"\bexport(?:s|ed|ing)?\b"
                    r"|\bexport"
                    r"(?:er|e|\u00e9|ent|ait|ant)?\b",
                    re.IGNORECASE,
                ),
                "exporter",
            ),
            (
                re.compile(
                    r"\bupload(?:s|ed|ing)?\b"
                    r"|\bimport"
                    r"(?:er|e|es|ent|ait|ant)\b",
                    re.IGNORECASE,
                ),
                "importer",
            ),
            (
                re.compile(
                    r"\breview(?:s|ed|ing)?\b"
                    r"|\bexamin"
                    r"(?:er|e|es|ent|ait|ant)\b",
                    re.IGNORECASE,
                ),
                "examiner",
            ),
            (
                re.compile(
                    r"\brequest(?:s|ed|ing)?\b"
                    r"|\bdemand"
                    r"(?:er|e|es|ent|ait|ant)\b",
                    re.IGNORECASE,
                ),
                "demander",
            ),
            (
                re.compile(
                    r"\b(?:choose|chooses|chose|chosen|choosing)\b"
                    r"|\bselect(?:s|ed|ing)?\b"
                    r"|\bchois"
                    r"(?:ir|it|issent|issait|issant)\b"
                    r"|\bs(?:e|\u00e9)lectionn"
                    r"(?:er|e|ent|ait|ant)\b",
                    re.IGNORECASE,
                ),
                "choisir",
            ),
            (
                re.compile(
                    r"\breceiv(?:e|es|ed|ing)\b"
                    r"|\brecev"
                    r"(?:oir|ez|ons|ait|ant)\b"
                    r"|\bre(?:c|\u00e7)oi"
                    r"(?:t|vent)\b",
                    re.IGNORECASE,
                ),
                "recevoir",
            ),
            (
                re.compile(
                    r"\bsearch(?:es|ed|ing)?\b"
                    r"|\brecherch"
                    r"(?:er|e|es|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "rechercher",
            ),
            (
                re.compile(
                    r"\bconsult(?:s|ed|ing)?\b"
                    r"|\bconsult"
                    r"(?:er|e|es|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "consulter",
            ),
            (
                re.compile(
                    r"\baccept(?:s|ed|ing)?\b"
                    r"|\baccept"
                    r"(?:er|e|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "accepter",
            ),
            (
                re.compile(
                    r"\breject(?:s|ed|ing)?\b"
                    r"|\bdeclin(?:e|es|ed|ing)\b"
                    r"|\brefus"
                    r"(?:er|e|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "refuser",
            ),
            (
                re.compile(
                    r"\b(?:pay|pays|paid|paying)\b"
                    r"|\bpai(?:e|es|ent)\b"
                    r"|\bpay"
                    r"(?:er|e|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "payer",
            ),
            (
                re.compile(
                    r"\bhand(?:s|ed|ing)?\s+over\b"
                    r"|\bremet"
                    r"(?:tre|s|tent|tait|tant)\b"
                    r"|\bremis(?:e|es)?\b",
                    re.IGNORECASE,
                ),
                "remettre",
            ),
            (
                re.compile(
                    r"\breturn(?:s|ed|ing)?\b"
                    r"|\bretourn"
                    r"(?:er|e|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "retourner",
            ),
            (
                re.compile(
                    r"\bclose(?:s|d|ing)?\b"
                    r"|\bcl(?:o|\u00f4)tur"
                    r"(?:er|e|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "cloturer",
            ),
            (
                re.compile(
                    r"\bevaluat(?:e|es|ed|ing)\b"
                    r"|\brate(?:s|d|ing)?\b"
                    r"|\b(?:e|\u00e9)valu"
                    r"(?:er|e|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b"
                    r"|\bleav(?:e|es|ing)\b"
                    r"(?=[^.!?]{0,60}"
                    r"\b(?:a\s+)?(?:review|rating)\b)"
                    r"|\bleft\b"
                    r"(?=[^.!?]{0,60}"
                    r"\b(?:a\s+)?(?:review|rating)\b)"
                    r"|\blaiss"
                    r"(?:er|e|ent|ait|ant)\b"
                    r"(?=[^.!?]{0,60}"
                    r"\b(?:une\s+)?"
                    r"(?:e|\u00e9)valuation\b)",
                    re.IGNORECASE,
                ),
                "evaluer",
            ),
            (
                re.compile(
                    r"\benter(?:s|ed|ing)?\b"
                    r"|\bfill(?:s|ed|ing)?\s+in\b"
                    r"|\brenseign"
                    r"(?:er|e|es|ent|ons|ez|"
                    r"ait|aient|ant|era|eront|"
                    r"\u00e9|\u00e9e|\u00e9s|\u00e9es)\b"
                    r"|\brempl"
                    r"(?:ir|is|it|issons|issez|issent|"
                    r"issait|issaient|issant|"
                    r"i|ie|ies)\b",
                    re.IGNORECASE,
                ),
                "renseigner",
            ),
        )

        raw: List[
            Dict[str, Any]
        ] = []

        for pattern, action in (
            tuple(self.ACTION_PATTERNS)
            + extra_patterns
        ):
            for match in pattern.finditer(
                sentence
            ):
                raw.append(
                    {
                        "pattern": pattern,
                        "action": action,
                        "match": match,
                        "surface": match.group(0),
                    }
                )

        raw.sort(
            key=lambda item: (
                item["match"].start(),
                -(
                    item["match"].end()
                    - item["match"].start()
                ),
                -self.ACTION_PRIORITY.get(
                    item["action"],
                    50,
                ),
            )
        )

        # ----------------------------------------------------------
        # Control-wrapper authority.
        #
        # "choose" / "choisir" remains a valid business action when
        # it owns a direct object:
        #
        #   "choose a meal"
        #   "choisir une option"
        #
        # It is not a separate workflow when it merely controls a
        # downstream action already recognized by the same lexical
        # authority:
        #
        #   "choose to pay"
        #   "choisir de payer"
        #
        # We resolve this from the already-built raw occurrence set;
        # no parallel action vocabulary is introduced here.
        # ----------------------------------------------------------

        control_wrapper_ids: set[int] = set()

        for item in raw:
            if item["action"] != "choisir":
                continue

            match = item["match"]

            downstream = [
                candidate
                for candidate in raw
                if (
                    candidate is not item
                    and candidate[
                        "match"
                    ].start()
                    >= match.end()
                )
            ]

            if not downstream:
                continue

            next_start = min(
                candidate[
                    "match"
                ].start()
                for candidate in downstream
            )

            connector = sentence[
                match.end():
                next_start
            ]

            if re.fullmatch(
                r"\s*(?:"
                r"to"
                r"|de"
                r"|d['\u2019]"
                r")\s*",
                connector,
                flags=re.IGNORECASE,
            ):
                control_wrapper_ids.add(
                    id(
                        item
                    )
                )

        output: List[
            Dict[str, Any]
        ] = []

        occupied: List[
            Tuple[int, int]
        ] = []

        for item in raw:
            if id(item) in control_wrapper_ids:
                continue

            match = item["match"]

            start = match.start()
            end = match.end()

            if any(
                start < used_end
                and end > used_start
                for used_start, used_end
                in occupied
            ):
                continue

            if self._workflow_match_is_nominal(
                sentence=sentence,
                item=item,
                accepted=output,
            ):
                continue

            if self._workflow_match_is_negated_predicate(
                sentence=sentence,
                item=item,
            ):
                continue

            if (
                self._workflow_match_is_conditional_passive_context(
                    sentence=sentence,
                    item=item,
                )
            ):
                continue

            output.append(
                item
            )

            occupied.append(
                (
                    start,
                    end,
                )
            )

        output.sort(
            key=lambda item: (
                item["match"].start(),
                item["match"].end(),
            )
        )

        return output


    def _workflow_match_has_french_preverbal_object_clitic(
        self,
        *,
        sentence: str,
        item: Dict[str, Any],
    ) -> bool:
        """
        Return True when French ``le``, ``la`` or ``les`` immediately
        before an already-recognized action surface is functioning as
        a preverbal direct-object clitic rather than as a determiner.

        Examples:

            "l'acheteur le reserve"
            "le client la valide"
            "les clients les commandent"

        Counter-example:

            "la reserve du lot"

        This helper decides grammar only. It does not infer a workflow,
        actor role, transaction, object identity, or lifecycle relation.
        """
        match = item.get(
            "match"
        )

        if match is None:
            return False

        prefix = sentence[
            :match.start()
        ].rstrip()

        clitic_match = re.search(
            r"\b(?:le|la|les)\s*$",
            prefix,
            flags=(
                re.IGNORECASE
                | re.UNICODE
            ),
        )

        if clitic_match is None:
            return False

        before_clitic = prefix[
            :clitic_match.start()
        ].rstrip()

        if not before_clitic:
            return False

        # Preserve real nominal frames:
        #
        #   "la reserve du lot"
        #   "la demande de service"
        suffix_key = comparison_key(
            sentence[
                match.end():
            ]
        ).strip()

        if re.match(
            r"^(?:de|du|des|d)\b",
            suffix_key,
            flags=re.IGNORECASE,
        ):
            return False

        # Keep only the local subject clause immediately preceding the
        # clitic. This is grammar, not domain interpretation.
        local_subject_clause = re.split(
            r"[,;]"
            r"|\b(?:"
            r"et|puis|ensuite|mais"
            r")\b",
            before_clitic,
            flags=re.IGNORECASE,
        )[-1].strip()

        if not local_subject_clause:
            return False

        subject = (
            self._workflow_subject_candidate(
                local_subject_clause
            )
        )

        if not clean_text(
            subject
        ):
            return False

        # ----------------------------------------------------------
        # Distinguish a real preverbal object clitic from a nominal
        # determiner inside the object of an already-established
        # predicate.
        #
        # Real clitic:
        #
        #   "publie un lot et l'acheteur le reserve"
        #
        #       prior action: publier
        #       boundary:     "et"
        #
        # Nominal object:
        #
        #   "examine la reserve disponible"
        #
        #       prior action: examiner
        #       boundary:     none
        #
        # Reuse canonical Workflow action authority on the STRICTLY
        # SHORTER prefix. No second action vocabulary is introduced.
        #
        # The recursive shape is bounded because each nested call
        # receives text ending before the current clitic/action.
        # ----------------------------------------------------------

        prior_actions = (
            self._workflow_action_occurrences(
                before_clitic
            )
        )

        if prior_actions:
            previous_match = (
                prior_actions[-1][
                    "match"
                ]
            )

            between_previous_and_clitic = (
                before_clitic[
                    previous_match.end():
                ]
            )

            has_predicate_boundary = bool(
                re.search(
                    r"[,;]"
                    r"|\b(?:"
                    r"and|et|puis|ensuite|mais"
                    r")\b",
                    between_previous_and_clitic,
                    flags=re.IGNORECASE,
                )
            )

            if not has_predicate_boundary:
                return False

        return True


    def _workflow_match_is_nominal(
        self,
        *,
        sentence: str,
        item: Dict[str, Any],
        accepted: Sequence[Dict[str, Any]],
    ) -> bool:
        """
        Reject noun matches and project-description meta actions.

        Examples:
        - "weekly schedules" is a noun phrase;
        - "about schedule changes" is not a new action;
        - "I want to create an application" describes the project,
          not an end-user workflow.
        """
        action_key = comparison_key(
            item["action"]
        )

        surface_key = comparison_key(
            item["surface"]
        )

        match = item["match"]

        prefix = sentence[
            :match.start()
        ].rstrip()

        previous_word_match = re.search(
            r"([^\W\d_]+)\s*$",
            prefix,
            flags=re.UNICODE,
        )

        previous_word = (
            comparison_key(
                previous_word_match.group(1)
            )
            if previous_word_match
            else ""
        )

        # ------------------------------------------------------
        # French "le suivant" / "la suivante" is a nominal or
        # adjectival reference, not the workflow verb "suivre".
        #
        # Example:
        #   "Le workflow prioritaire est le suivant : ..."
        #
        # This rule is grammatical and does not depend on a domain.
        # ------------------------------------------------------

        if (
            surface_key
            in {
                "suivant",
                "suivante",
                "suivants",
                "suivantes",
            }
            and previous_word
            in {
                "le",
                "la",
                "les",
                "un",
                "une",
                "des",
                "du",
            }
        ):
            return True

        # ------------------------------------------------------
        # Policy/control subject authority.
        #
        # Some action vocabulary is also a noun:
        #
        #   "Toute commande fournisseur n?cessite..."
        #   "Any supplier order requires..."
        #
        # In those forms the matched lexical item belongs to the
        # SUBJECT of a rule. It is not the action predicate.
        #
        # Preserve true actions:
        #
        #   "La cliente commande un produit."
        #   "The customers order supplies."
        #
        # The rule requires both:
        #   1. a quantified/determined noun subject;
        #   2. a nearby control predicate after that noun phrase.
        # ------------------------------------------------------

        ambiguous_policy_subject_surfaces = {
            "commande",
            "commandes",
            "order",
            "orders",
            "demande",
            "demandes",
            "request",
            "requests",
            "reservation",
            "reservations",
            "booking",
            "bookings",
            "suivi",
            "monitoring",
            "alerte",
            "alertes",
            "alert",
            "alerts",
        }

        if (
            surface_key
            in ambiguous_policy_subject_surfaces
        ):
            prefix_key = comparison_key(
                prefix
            )

            suffix_key = comparison_key(
                sentence[
                    match.end():
                ]
            ).strip()

            quantified_subject = re.search(
                r"(?:^|\s)"
                r"(?:"
                r"any|every|each|all|"
                r"the|a|an|"
                r"tout|toute|tous|toutes|chaque|"
                r"le|la|les|un|une|des"
                r")"
                r"(?:\s+[^\s]+){0,4}\s*$",
                prefix_key,
                flags=re.IGNORECASE,
            )

            control_predicate = re.match(
                r"^(?:"
                r"(?!(?:"
                r"and|or|then|"
                r"et|ou|puis|ensuite|"
                r"a|an|the|"
                r"un|une|le|la|les|des|du"
                r")\b)"
                r"[^\s]+\s+"
                r"){0,2}"
                r"(?:"
                r"requires?|needs?|"
                r"must|should|shall|"
                r"necessite|necessitent|"
                r"requiert|requierent|"
                r"doit|doivent"
                r")\b",
                suffix_key,
                flags=re.IGNORECASE,
            )

            if (
                quantified_subject is not None
                and control_predicate is not None
            ):
                return True

        # Many workflow vocabulary surfaces are lexically ambiguous:
        # "alert", "request", "booking", "monitoring", "suivi",
        # "demande", "alerte", etc. They may be nouns or verbs.
        #
        # A direct determiner/possessive immediately before the match
        # is strong evidence of nominal use:
        #
        #   "une alerte", "le suivi", "a request", "the monitoring"
        #
        # This grammar-based rule is domain-independent and preserves
        # verbal predicates such as:
        #
        #   "le système alerte", "the customer requests".
        nominal_determiners = {
            "a",
            "an",
            "the",
            "this",
            "that",
            "these",
            "those",
            "my",
            "your",
            "his",
            "her",
            "its",
            "our",
            "their",
            "un",
            "une",
            "le",
            "la",
            "les",
            "ce",
            "cet",
            "cette",
            "ces",
            "mon",
            "ma",
            "mes",
            "ton",
            "ta",
            "tes",
            "son",
            "sa",
            "ses",
            "notre",
            "nos",
            "votre",
            "vos",
            "leur",
            "leurs",
        }

        if previous_word in nominal_determiners:
            french_preverbal_object_clitic = bool(
                previous_word
                in {
                    "le",
                    "la",
                    "les",
                }
                and self._workflow_match_has_french_preverbal_object_clitic(
                    sentence=sentence,
                    item=item,
                )
            )

            if not french_preverbal_object_clitic:
                return True

        # Some workflow vocabulary is both nominal and verbal.
        #
        # A preposition before a noun-form surface is strong nominal
        # evidence:
        #
        #   "demande de reservation"
        #   "offre et de demande"
        #   "booking of equipment"
        #
        # This deliberately applies only to ambiguous noun surfaces.
        # Infinitives such as "de reserver" or "to request" remain
        # eligible workflow actions.
        nominal_prepositions = {
            "de",
            "du",
            "des",
            "d",
            "of",
        }

        ambiguous_nominal_surfaces = {
            "demande",
            "demandes",
            "request",
            "requests",
            "reservation",
            "reservations",
            "booking",
            "bookings",
            "suivi",
            "monitoring",
            "alerte",
            "alertes",
            "alert",
            "alerts",
        }

        if (
            previous_word
            in nominal_prepositions
            and surface_key
            in ambiguous_nominal_surfaces
        ):
            return True

        # Ambiguous workflow vocabulary can appear as a nominal
        # modifier inside a copular project/product description:
        #
        #   "The product is an IoT monitoring device."
        #   "The service is a booking platform."
        #
        # The article-led nominal frame distinguishes these cases from
        # progressive predicates such as:
        #
        #   "The application is monitoring conditions."
        #
        # This is grammatical authority only; no domain vocabulary is
        # used to infer the workflow.
        if (
            surface_key
            in ambiguous_nominal_surfaces
            and re.search(
                r"\b(?:is|are|was|were)\s+"
                r"(?:a|an|the)"
                r"(?:\s+"
                r"[^\W\d_]+"
                r"(?:-[^\W\d_]+)?"
                r"){0,4}$",
                prefix,
                flags=(
                    re.IGNORECASE
                    | re.UNICODE
                ),
            )
        ):
            return True

        if (
            action_key == "planifier"
            and surface_key.startswith(
                "schedul"
            )
        ):
            nominal_predecessors = {
                "a",
                "an",
                "the",
                "about",
                "of",
                "for",
                "current",
                "existing",
                "weekly",
                "daily",
                "monthly",
                "annual",
                "yearly",
                "shift",
                "team",
                "work",
                "their",
                "our",
                "your",
                "this",
                "that",
            }

            if (
                previous_word
                in nominal_predecessors
            ):
                return True

        if action_key == "creer":
            prefix_key = comparison_key(
                prefix
            )

            meta_creation_markers = (
                "i want to",
                "we want to",
                "the idea is to",
                "our idea is to",
                "our goal is to",
                "the project is to",
                "we plan to",
                "je veux",
                "nous voulons",
                "on veut",
                "l idee est de",
                "notre idee est de",
                "notre objectif est de",
                "le projet consiste a",
                "nous prevoyons de",
            )

            if any(
                prefix_key.endswith(
                    marker
                )
                for marker
                in meta_creation_markers
            ):
                return True

        if (
            action_key
            in {
                "enregistrer",
                "exporter",
            }
            and previous_word
            in {
                "a",
                "an",
                "the",
                "this",
                "that",
                "un",
                "une",
                "le",
                "la",
                "les",
                "ce",
                "cette",
            }
        ):
            return True

        if accepted:
            previous = accepted[-1][
                "match"
            ]

            between = sentence[
                previous.end():
                match.start()
            ]

            has_action_separator = bool(
                re.search(
                    r"[,;]"
                    r"|\b(?:and|et)\b",
                    between,
                    flags=re.IGNORECASE,
                )
            )

            # Once an action predicate has already been accepted,
            # another ambiguous lexical surface without an explicit
            # coordination separator is normally part of that action's
            # object rather than a second predicate:
            #
            #   "reviews sensor alerts"
            #                   -> alerts = noun
            #
            # Explicit coordination remains authoritative:
            #
            #   "reviews and alerts the supervisor"
            #                -> alerts = predicate
            if (
                surface_key
                in ambiguous_nominal_surfaces
                and not has_action_separator
            ):
                return True

            if (
                action_key
                in {
                    "creer",
                    "enregistrer",
                    "approuver",
                    "exporter",
                    "demander",
                }
                and not has_action_separator
            ):
                return True

            if (
                action_key == "planifier"
                and surface_key.startswith(
                    "schedul"
                )
                and not has_action_separator
            ):
                return True

        return False


    def _localized_workflow_action(
        self,
        action: str,
        surface: str,
        language: str,
    ) -> str:
        """
        Localize a canonical action without changing its semantics.
        """
        action_key = comparison_key(
            action
        )

        surface_key = comparison_key(
            surface
        )

        # U2 universal comparison workflow authority.
        if action_key == "comparer":
            return (
                "compare"
                if language == "en"
                else "comparer"
            )

        if language == "en":
            if action_key == "planifier":
                if (
                    surface_key.startswith(
                        "creat"
                    )
                    or surface_key.startswith(
                        "cre"
                    )
                ):
                    return "create"

                return "schedule"

            if action_key == "alerter":
                if surface_key.startswith(
                    "notif"
                ):
                    return "notify"

                return "alert"

            if action_key == "approuver":
                if surface_key.startswith(
                    "valid"
                ):
                    return "validate"

                return "approve"

            if action_key == "transmettre":
                if surface_key.startswith(
                    "send"
                ):
                    return "send"

                return "transmit"

            english_actions = {
            "importer": "upload",
            "examiner": "review",
            "demander": "request",
            "choisir": "choose",
            "recevoir": "receive",
            "rechercher": "search",
            "consulter": "consult",
            "accepter": "accept",
            "refuser": "reject",
            "payer": "pay",
            "remettre": "hand over",
            "retourner": "return",
            "cloturer": "close",
            "evaluer": "evaluate",
            "renseigner": "enter",
                "creer": "create",
                "inspecter": "inspect",
                "detecter": "detect",
                "surveiller": "monitor",
                "reserver": "book",
                "commander": "order",
                "gerer": "manage",
                "suivre": "track",
                "mettre en relation": "connect",
                "publier": "publish",
                "classifier": "classify",
                "analyser": "analyze",
                "mesurer": "measure",
                "enregistrer": "record",
                "approuver": "approve",
                "exporter": "export",
            }

            return english_actions.get(
                action_key,
                action,
            )

        if action_key == "approuver":
            if surface_key.startswith(
                "valid"
            ):
                return "valider"

            return "approuver"

        french_actions = {
            "creer": "cr\u00e9er",
            "inspecter": "inspecter",
            "detecter": "d\u00e9tecter",
            "surveiller": "surveiller",
            "reserver": "r\u00e9server",
            "commander": "commander",
            "planifier": "planifier",
            "gerer": "g\u00e9rer",
            "suivre": "suivre",
            "mettre en relation": "mettre en relation",
            "publier": "publier",
            "classifier": "classifier",
            "analyser": "analyser",
            "mesurer": "mesurer",
            "transmettre": "transmettre",
            "alerter": "alerter",
            "enregistrer": "enregistrer",
            "approuver": "approuver",
            "exporter": "exporter",
            "rechercher": "rechercher",
            "consulter": "consulter",
            "accepter": "accepter",
            "refuser": "refuser",
            "payer": "payer",
            "remettre": "remettre",
            "retourner": "retourner",
            "cloturer": "cl\u00f4turer",
            "evaluer": "\u00e9valuer",
            "renseigner": "renseigner",
        }

        return french_actions.get(
            action_key,
            action,
        )

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

        # Archetype scoring consumes only positive or neutral
        # description evidence. Explicit scope exclusions remain
        # canonical scope information, but they must never become
        # positive archetype evidence.
        positive_description = clean_text(
            " ".join(
                sentence
                for sentence in self._sentences(
                    description
                )
                if not is_scope_exclusion_statement(
                    sentence
                )
            )
        )

        searchable_text = clean_text(
            " ".join(
                [
                    industry,
                    positive_description,
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
        Split structural actor lists without confusing coordinated
        modifiers with independent actors.

        Examples:

        - "clients et prestataires"
          -> ["clients", "prestataires"]

        - "buyers and sellers"
          -> ["buyers", "sellers"]

        - "petites et moyennes entreprises"
          -> ["petites et moyennes entreprises"]

        - "small and medium businesses"
          -> ["small and medium businesses"]

        - "dirigeants de petites et moyennes entreprises"
          -> one actor phrase, not two actors.

        Product objects or complements remain attached to the actor
        that owns them.
        """
        text = clean_text(
            value
        )

        if not text:
            return []

        parts = re.split(
            r"\s*(,|;|\bet\b|\band\b|"
            r"\bou\b|\bor\b|\+|/)\s*",
            text,
            flags=re.IGNORECASE,
        )

        if len(parts) <= 1:
            return [text]

        generic_modifiers = {
            "small",
            "medium",
            "large",
            "micro",
            "public",
            "private",
            "local",
            "regional",
            "national",
            "international",
            "petit",
            "petite",
            "petits",
            "petites",
            "moyen",
            "moyenne",
            "moyens",
            "moyennes",
            "grand",
            "grande",
            "grands",
            "grandes",
            "micro",
            "public",
            "publique",
            "publics",
            "publiques",
            "prive",
            "privee",
            "prives",
            "privees",
            "local",
            "locale",
            "locaux",
            "locales",
            "regional",
            "regionale",
            "regionaux",
            "regionales",
            "national",
            "nationale",
            "nationaux",
            "nationales",
            "international",
            "internationale",
            "internationaux",
            "internationales",
        }

        generic_group_nouns = {
            "people",
            "children",
            "staff",
            "personnel",
            "households",
            "menages",
            "workers",
            "employees",
            "farmers",
            "students",
            "citizens",
            "clients",
            "users",
            "customers",
            "buyers",
            "sellers",
            "providers",
            "utilisateurs",
            "acheteurs",
            "vendeurs",
            "prestataires",
            "employes",
            "salaries",
            "agriculteurs",
            "etudiants",
            "citoyens",
        }

        def modifier_fragment(
            fragment: str,
        ) -> bool:
            key = comparison_key(
                fragment
            )

            tokens = [
                token
                for token in key.split()
                if token
            ]

            if (
                not tokens
                or self._looks_like_actor_phrase(
                    fragment
                )
            ):
                return False

            return all(
                token in generic_modifiers
                for token in tokens
            )

        def standalone_group(
            fragment: str,
        ) -> bool:
            if self._looks_like_actor_phrase(
                fragment
            ):
                return True

            key = comparison_key(
                fragment
            )

            tokens = [
                token
                for token in key.split()
                if token
            ]

            if not tokens:
                return False

            if modifier_fragment(
                fragment
            ):
                return False

            last = tokens[-1]

            if last in generic_group_nouns:
                return True

            # Conservative plural-group fallback for actor lists.
            if (
                len(last) > 3
                and last.endswith(
                    (
                        "s",
                        "x",
                    )
                )
            ):
                return True

            return False

        def ends_with_open_modifier(
            fragment: str,
        ) -> bool:
            key = comparison_key(
                fragment
            )

            tokens = [
                token
                for token in key.split()
                if token
            ]

            if len(tokens) < 2:
                return False

            return (
                tokens[-2]
                in {
                    "de",
                    "des",
                    "du",
                    "of",
                }
                and tokens[-1]
                in generic_modifiers
            )

        actors: List[str] = []

        current = clean_text(
            parts[0]
        )

        index = 1

        while index + 1 < len(parts):
            separator = clean_text(
                parts[index]
            )

            next_fragment = clean_text(
                parts[index + 1]
            )

            index += 2

            if not next_fragment:
                continue

            current_is_group = (
                standalone_group(
                    current
                )
            )

            next_is_group = (
                standalone_group(
                    next_fragment
                )
            )

            conjunction = (
                comparison_key(
                    separator
                )
                in {
                    "et",
                    "and",
                    "ou",
                    "or",
                }
            )

            split_here = (
                current_is_group
                and next_is_group
                and not ends_with_open_modifier(
                    current
                )
                and not (
                    conjunction
                    and modifier_fragment(
                        current
                    )
                )
            )

            if split_here:
                actors.append(
                    clean_text(
                        current
                    )
                )

                current = next_fragment
                continue

            if separator in {
                ",",
                ";",
            }:
                current = clean_text(
                    f"{current}{separator} "
                    f"{next_fragment}"
                )
            else:
                current = clean_text(
                    f"{current} {separator} "
                    f"{next_fragment}"
                )

        if current:
            actors.append(
                clean_text(
                    current
                )
            )

        return [
            actor
            for actor in actors
            if actor
        ]

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

    def _explicit_transaction_unit_text(
        self,
        sentences: Sequence[str],
    ) -> str:
        """
        Return an explicitly declared transaction unit.

        Explicit user declarations outrank heuristic reconstruction.

        Supported examples:
        - "L'unite de transaction principale est ..."
        - "L'unite de transaction est ..."
        - "The primary transaction unit is ..."
        - "The transaction unit is ..."

        The extracted value remains user-authored text. No sector or
        archetype-specific interpretation is introduced here.
        """
        patterns = (
            re.compile(
                r"^\s*"
                r"(?:l['\u2019]\s*)?"
                r"unit(?:e|\u00e9)\s+"
                r"de\s+transaction"
                r"(?:\s+principale)?"
                r"\s+(?:est|sera|serait)\s+"
                r"(.+?)"
                r"(?=[.;]|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"^\s*"
                r"(?:the\s+)?"
                r"(?:primary\s+)?"
                r"transaction\s+unit"
                r"\s+(?:is|will\s+be|would\s+be)\s+"
                r"(.+?)"
                r"(?=[.;]|$)",
                re.IGNORECASE,
            ),
        )

        for sentence in sentences:
            text = clean_text(
                sentence
            )

            if not text:
                continue

            for pattern in patterns:
                match = pattern.search(
                    text
                )

                if not match:
                    continue

                value = clean_text(
                    match.group(1)
                )

                value = value.strip(
                    " .,:;"
                )

                if not value:
                    continue

                return self._compact(
                    value,
                    300,
                )

        return ""


    def _transaction_action_is_negated(
        self,
        sentence: str,
        action_match: re.Match[str],
    ) -> bool:
        """
        Prevent a negated action from becoming canonical transaction
        evidence.

        Examples:
        - "ne veulent pas acheter"
        - "ne paie pas"
        - "does not buy"
        - "will not pay"
        - "doesn't purchase"

        The decision is local to the matched action so unrelated
        negation elsewhere in the sentence does not invalidate a valid
        transaction action.
        """
        text = clean_text(
            sentence
        )

        if not text:
            return False

        key = comparison_key(
            text
        )

        if not key:
            return False

        matched_text = clean_text(
            action_match.group(0)
        )

        matched_key = comparison_key(
            matched_text
        )

        if not matched_key:
            return False

        action_start = action_match.start()

        before = clean_text(
            text[
                max(
                    0,
                    action_start - 100,
                ):
                action_start
            ]
        )

        before_key = comparison_key(
            before
        )

        french_patterns = (
            r"\bne\b.{0,70}\bpas\s*$",
            r"\bn\b.{0,70}\bpas\s*$",
            r"\bne\b.{0,70}\bplus\s*$",
            r"\bn\b.{0,70}\bplus\s*$",
            r"\bne\b.{0,70}\bjamais\s*$",
            r"\bn\b.{0,70}\bjamais\s*$",
            r"\bsans\s+$",
        )

        english_patterns = (
            r"\b(?:do|does|did|will|would|can|could|"
            r"should|must|is|are|was|were)\s+not"
            r"(?:\s+\w+){0,5}\s*$",

            r"\b(?:don|doesn|didn|won|wouldn|can|couldn|"
            r"shouldn|mustn|isn|aren|wasn|weren)\s+t"
            r"(?:\s+\w+){0,5}\s*$",

            r"\bnever"
            r"(?:\s+\w+){0,5}\s*$",
        )

        return any(
            re.search(
                pattern,
                before_key,
                flags=re.IGNORECASE,
            )
            for pattern in (
                *french_patterns,
                *english_patterns,
            )
        )


    def _transaction_match_is_grammatically_operational(
        self,
        *,
        sentence: str,
        action: str,
        action_match: re.Match[str],
    ) -> bool:
        """
        Reuse canonical Workflow grammatical authority for a
        Transaction lexical match.

        Transaction owns lifecycle semantics. It must not maintain a
        second grammar for deciding whether an ambiguous lexical
        surface is a predicate, noun, modifier, or passive context.
        """
        item = {
            "pattern": action_match.re,
            "action": action,
            "match": action_match,
            "surface": action_match.group(0),
        }

        if self._workflow_match_is_nominal(
            sentence=sentence,
            item=item,
            accepted=[],
        ):
            return False

        if self._workflow_match_is_conditional_passive_context(
            sentence=sentence,
            item=item,
        ):
            return False

        return True


    def _transaction_action_candidate(
        self,
        sentence: str,
        pattern: re.Pattern[str],
        action: str = "",
    ) -> re.Match[str] | None:
        """
        Return a usable transaction-action match only when the sentence
        is positive operational evidence.

        Ambiguous lexical forms that can also be nouns or modifiers are
        accepted only when their local grammatical context is compatible
        with an action predicate.
        """
        if self._is_scope_only(
            sentence
        ):
            return None

        match = pattern.search(
            sentence
        )

        if not match:
            return None

        if self._transaction_action_is_negated(
            sentence,
            match,
        ):
            return None

        matched_key = comparison_key(
            match.group(0)
        )

        before_key = comparison_key(
            sentence[
                :match.start()
            ]
        )

        # French "demande" can be either:
        #
        #   "le client demande..."  -> predicate
        #   "une demande..."        -> noun
        #
        # Determiner-led nominal use must not become transaction
        # initiation evidence.
        if matched_key == "demande":
            if re.search(
                r"\b(?:"
                r"un|une|le|la|les|"
                r"ce|cet|cette|ces|"
                r"sa|son|ses|"
                r"notre|nos|leur|leurs"
                r")\s*$",
                before_key,
                flags=re.IGNORECASE,
            ):
                return None

        # English past "requested" can be a finite predicate or a
        # participial modifier:
        #
        #   "the client requested a service" -> predicate
        #   "the requested service"          -> modifier
        if matched_key == "requested":
            if re.search(
                r"\b(?:"
                r"the|a|an|"
                r"this|that|these|those|"
                r"its|their|our|your|my"
                r")\s*$",
                before_key,
                flags=re.IGNORECASE,
            ):
                return None

        if not self._transaction_match_is_grammatically_operational(
            sentence=sentence,
            action=action,
            action_match=match,
        ):
            return None

        return match
    def _transaction_initiation_patterns(
        self,
    ) -> Tuple[
        Tuple[
            re.Pattern[str],
            str,
        ],
        ...,
    ]:
        """
        Shared transaction-initiation authority.

        Predicates represent an explicit operational start of an
        exchange. Structural marketplace nouns and participial
        modifiers are not transaction actions.
        """
        return (
            (
                re.compile(
                    r"\bpubl(?:ier|ie|ient|ies)?\b"
                    r"|\bpublish(?:es|ed|ing)?\b"
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
                    r"|\bd\u00e9pos(?:er|e|ent)?\b",
                    re.IGNORECASE,
                ),
                "soumettre",
            ),

            # Explicit initiation predicate:
            #
            # "initie une demande..."
            # "initiates a service request..."
            (
                re.compile(
                    r"\biniti"
                    r"(?:"
                    r"er|e|ent|era|eront|ait|aient"
                    r")\b"
                    r"|\binitiat"
                    r"(?:e|es|ed|ing)\b",
                    re.IGNORECASE,
                ),
                "demander",
            ),

            # English send-request predicate.
            #
            # The send verb becomes initiation authority only when
            # its immediate object is explicitly a request:
            #
            #   "A customer sends a request."
            #   "A customer sent the request."
            #
            # Generic send/delivery statements remain untouched.
            (
                re.compile(
                    r"\b(?:send|sends|sent|sending)\b"
                    r"(?=\s+"
                    r"(?:(?:a|an|the|this|that)\s+)?"
                    r"requests?\b"
                    r")",
                    re.IGNORECASE,
                ),
                "demander",
            ),

            # Direct request predicate.
            #
            # French bare "demand" is intentionally excluded because
            # it collides with the English structural noun "demand".
            #
            # English bare "request" is also excluded conservatively;
            # requests/requested/requesting remain explicit predicates.
            (
                re.compile(
                    r"\bdemand"
                    r"(?:er|e|ent)\b"
                    r"|\brequest"
                    r"(?:s|ed|ing)\b",
                    re.IGNORECASE,
                ),
                "demander",
            ),

            # Reservation / booking is an exchange start.
            (
                re.compile(
                    r"\br(?:e|\u00e9)serv"
                    r"(?:er|e|ent|ait|aient|era|eront)\b"
                    r"|\bbook"
                    r"(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "r\u00e9server",
            ),

            # Order / commande is likewise a transaction event.
            #
            # Lifecycle position determines whether it is initiation
            # or a downstream event. Nominal uses are rejected by the
            # shared grammatical authority.
            (
                re.compile(
                    r"\bcommand(?:er|e|ent)?\b"
                    r"|\border(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "commander",
            ),
        )
    def _transaction_completion_candidate_is_operational(
        self,
        *,
        sentence: str,
        action: str,
        action_match: re.Match[str],
    ) -> bool:
        """
        Validate terminal lifecycle evidence before it can become
        canonical transaction completion.

        A terminal participle used only as an attribute/state label is
        not an operational event:

            "commission sur chaque intervention terminee"
            "fee on each completed transaction"

        Explicit predicates remain valid:

            "l'intervention est terminee"
            "the transaction is completed"
            "the transaction completed"
        """
        if not self._transaction_match_is_grammatically_operational(
            sentence=sentence,
            action=action,
            action_match=action_match,
        ):
            return False

        if action != "terminer":
            return True

        text = clean_text(
            sentence
        )

        if not text:
            return False

        matched_key = comparison_key(
            action_match.group(0)
        )

        before_key = comparison_key(
            text[
                max(
                    0,
                    action_match.start() - 120,
                ):
                action_match.start()
            ]
        )

        after_key = comparison_key(
            text[
                action_match.end():
                min(
                    len(text),
                    action_match.end() + 120,
                )
            ]
        )


        # --------------------------------------------------------------
        # English attributive participles.
        #
        #   "each completed transaction"
        #   "fee on completed transactions"
        #
        # Here "completed" modifies the following noun. It is not an
        # event asserting that the transaction completed.
        # --------------------------------------------------------------

        if matched_key in {
            "completed",
            "finished",
            "finalized",
            "finalised",
        }:
            following_word = re.match(
                r"^([a-z0-9][a-z0-9_-]*)\b",
                after_key,
                flags=re.IGNORECASE,
            )

            attributive_prefix = re.search(
                r"\b(?:"
                r"a|an|the|"
                r"each|every|all|any|"
                r"this|that|these|those|"
                r"per|on|for|of|to|from|with"
                r")\s*$",
                before_key,
                flags=re.IGNORECASE,
            )

            if (
                following_word is not None
                and attributive_prefix is not None
            ):
                return False


        # --------------------------------------------------------------
        # French terminal participles used after a noun.
        #
        #   "chaque intervention terminee"
        #
        # is descriptive.
        #
        #   "l'intervention est terminee"
        #
        # is a real terminal predicate and remains valid.
        # --------------------------------------------------------------

        if matched_key in {
            "terminee",
            "terminees",
            "achevee",
            "achevees",
            "finalisee",
            "finalisees",
        }:
            explicit_copula = re.search(
                r"\b(?:"
                r"est|sont|"
                r"etait|etaient|"
                r"sera|seront"
                r")\s*$",
                before_key,
                flags=re.IGNORECASE,
            )

            explicit_compound_copula = re.search(
                r"\b(?:"
                r"a|ont|avait|avaient|aura|auront"
                r")\s+ete\s*$",
                before_key,
                flags=re.IGNORECASE,
            )

            if (
                explicit_copula is not None
                or explicit_compound_copula is not None
            ):
                return True

            # Without an explicit predicate, feminine terminal
            # participles are treated conservatively as modifiers,
            # not as lifecycle events.
            return False


        return True

    def _transaction_events_are_continuous(
        self,
        *,
        initiation_sentence: str,
        initiation_action: str,
        initiation_match: re.Match[str],
        completion_sentence: str,
        completion_action: str,
        completion_match: re.Match[str],
    ) -> bool:
        """
        Decide whether two already-valid lifecycle events belong to
        the same transaction.

        This authority does not classify actions. Workflow grammar and
        Transaction action/completion authorities have already done
        that upstream.

        Continuity is accepted from generic discourse evidence only:

        1. a meaningful shared transaction-object anchor;
        2. an explicit terminal lifecycle reference;
        3. a strong anaphoric reference;
        4. a conservative economic reference tied to the same actor;
        5. a coordinated same-actor generic reference.

        Mere temporal order, sentence proximity, or actor equality is
        never sufficient by itself.
        """
        initiation_text = clean_text(
            initiation_sentence
        )

        completion_text = clean_text(
            completion_sentence
        )

        if (
            not initiation_text
            or not completion_text
        ):
            return False

        initiation_object = (
            self._transaction_object(
                initiation_text,
                initiation_match,
            )
        )

        completion_object = (
            self._transaction_object(
                completion_text,
                completion_match,
            )
        )

        # ----------------------------------------------------------
        # Generic lexical anchors.
        #
        # comparison_key remains the shared normalization authority.
        # Structural, temporal, and monetary modifiers cannot prove
        # object identity on their own.
        # ----------------------------------------------------------

        non_anchor_tokens = {
            # English structure.
            "a",
            "an",
            "the",
            "of",
            "for",
            "to",
            "from",
            "with",
            "on",
            "in",
            "and",
            "or",
            "this",
            "that",
            "these",
            "those",
            "my",
            "your",
            "our",
            "their",
            "its",

            # French structure.
            "un",
            "une",
            "des",
            "du",
            "de",
            "la",
            "le",
            "les",
            "l",
            "pour",
            "avec",
            "dans",
            "sur",
            "et",
            "ou",
            "ce",
            "cet",
            "cette",
            "ces",
            "mon",
            "ma",
            "mes",
            "ton",
            "ta",
            "tes",
            "son",
            "sa",
            "ses",
            "notre",
            "nos",
            "votre",
            "vos",
            "leur",
            "leurs",

            # Frequency / schedule modifiers.
            "daily",
            "weekly",
            "monthly",
            "annual",
            "yearly",
            "quotidien",
            "quotidienne",
            "hebdomadaire",
            "mensuel",
            "mensuelle",
            "annuel",
            "annuelle",

            # Monetary descriptors cannot prove object identity.
            "fee",
            "fees",
            "price",
            "prices",
            "cost",
            "costs",
            "payment",
            "payments",
            "amount",
            "amounts",
            "frais",
            "prix",
            "cout",
            "couts",
            "paiement",
            "paiements",
            "montant",
            "montants",
        }

        monetary_reference_tokens = {
            "fee",
            "fees",
            "price",
            "prices",
            "cost",
            "costs",
            "payment",
            "payments",
            "amount",
            "amounts",
            "frais",
            "prix",
            "cout",
            "couts",
            "paiement",
            "paiements",
            "montant",
            "montants",
        }

        # These are generic lifecycle / exchange references, not
        # project or sector vocabulary.
        generic_transaction_reference_tokens = {
            "transaction",
            "transactions",
            "exchange",
            "exchanges",
            "echange",
            "echanges",
            "service",
            "services",
            "item",
            "items",
            "product",
            "products",
            "produit",
            "produits",
            "order",
            "orders",
            "commande",
            "commandes",
            "booking",
            "bookings",
            "reservation",
            "reservations",
            "request",
            "requests",
            "demande",
            "demandes",
            "purchase",
            "purchases",
            "achat",
            "achats",
            "delivery",
            "deliveries",
            "livraison",
            "livraisons",
        }

        generic_actor_tokens = {
            "provider",
            "providers",
            "supplier",
            "suppliers",
            "customer",
            "customers",
            "client",
            "clients",
            "buyer",
            "buyers",
            "seller",
            "sellers",
            "company",
            "companies",
            "user",
            "users",
            "prestataire",
            "prestataires",
            "fournisseur",
            "fournisseurs",
            "client",
            "clients",
            "acheteur",
            "acheteurs",
            "vendeur",
            "vendeurs",
            "entreprise",
            "entreprises",
            "utilisateur",
            "utilisateurs",
        }

        def anchor_tokens(
            value: str,
        ) -> set[str]:
            key = comparison_key(
                value
            )

            return {
                token
                for token in key.split()
                if (
                    len(token) > 1
                    and token
                    not in non_anchor_tokens
                )
            }

        initiation_tokens = (
            anchor_tokens(
                initiation_object
            )
        )

        completion_tokens = (
            anchor_tokens(
                completion_object
            )
        )

        # Direct semantic anchor remains the strongest generic signal.
        if (
            initiation_tokens
            & completion_tokens
        ):
            return True

        completion_action_key = (
            comparison_key(
                completion_action
            )
        )

        completion_sentence_key = (
            comparison_key(
                completion_text
            )
        )

        # ----------------------------------------------------------
        # Explicit terminal lifecycle authority.
        #
        # Examples:
        #
        #   "the transaction is closed"
        #   "conclut la transaction"
        #   "l'intervention est terminee"
        #
        # The last form has no object after the terminal predicate, so
        # the referenced object must be recovered from the sentence.
        # ----------------------------------------------------------

        explicit_terminal_action = bool(
            completion_action_key
            in {
                "cloturer",
                "terminer",
            }
            or completion_action_key.startswith(
                "conclure"
            )
        )

        if explicit_terminal_action:
            if re.search(
                r"\b(?:"
                r"transaction"
                r"|exchange"
                r"|echange"
                r")\b",
                completion_sentence_key,
                flags=re.IGNORECASE,
            ):
                return True

            # Terminal participles often put the referenced object
            # BEFORE the predicate:
            #
            #   "l'intervention est terminee"
            #
            # Use this fallback only for canonical terminal-state
            # authority. Generic actor words cannot establish object
            # continuity.
            if (
                completion_action_key
                == "terminer"
            ):
                terminal_sentence_tokens = (
                    anchor_tokens(
                        completion_text
                    )
                )

                terminal_shared_tokens = (
                    initiation_tokens
                    & terminal_sentence_tokens
                ) - generic_actor_tokens

                if terminal_shared_tokens:
                    return True

        # ----------------------------------------------------------
        # Strong pronoun / demonstrative reference.
        # ----------------------------------------------------------

        completion_tail_key = (
            comparison_key(
                completion_text[
                    completion_match.end():
                ]
            )
        )

        if re.match(
            r"^(?:"
            r"(?:(?:for|pour)\s+)?"
            r"(?:"
            r"it|them|this|that"
            r"|cela|ca|lui|eux|elles"
            r")"
            r")\b",
            completion_tail_key,
            flags=re.IGNORECASE,
        ):
            return True

        # ----------------------------------------------------------
        # Subject continuity.
        #
        # Actor equality is NOT sufficient by itself. It is consumed
        # only together with an explicit reference form below.
        # ----------------------------------------------------------

        initiation_subject = (
            self._workflow_subject_candidate(
                initiation_text[
                    :initiation_match.start()
                ]
            )
        )

        completion_subject = (
            self._workflow_subject_candidate(
                completion_text[
                    :completion_match.start()
                ]
            )
        )

        initiation_subject_key = (
            comparison_key(
                initiation_subject
            )
        )

        completion_subject_key = (
            comparison_key(
                completion_subject
            )
        )

        same_subject = bool(
            initiation_subject_key
            and completion_subject_key
            and initiation_subject_key
            == completion_subject_key
        )

        same_sentence = (
            initiation_text
            == completion_text
        )

        # ----------------------------------------------------------
        # French preverbal object-clitic continuity.
        #
        # Grammar authority remains upstream in Workflow:
        #
        #   "l'acheteur le reserve"
        #
        # Transaction consumes that classification as an anaphoric
        # continuity signal; it does NOT re-detect le/la/les itself.
        #
        # The signal is deliberately conservative:
        #
        #   - same sentence;
        #   - a real initiation object anchor exists;
        #   - no intervening accepted action can have introduced a
        #     competing referent.
        #
        # Positive:
        #
        #   "publie un lot et l'acheteur le reserve"
        #
        # Rejected:
        #
        #   "publie un lot, examine une salle puis la reserve"
        # ----------------------------------------------------------

        if (
            same_sentence
            and initiation_tokens
        ):
            completion_item = {
                "pattern":
                    completion_match.re,

                "action":
                    completion_action,

                "match":
                    completion_match,

                "surface":
                    completion_match.group(0),
            }

            completion_has_object_clitic = (
                self._workflow_match_has_french_preverbal_object_clitic(
                    sentence=completion_text,
                    item=completion_item,
                )
            )

            if completion_has_object_clitic:
                intervening_actions = [
                    item
                    for item
                    in self._workflow_action_occurrences(
                        completion_text
                    )
                    if (
                        item[
                            "match"
                        ].start()
                        >= initiation_match.end()
                        and item[
                            "match"
                        ].start()
                        < completion_match.start()
                    )
                ]

                if not intervening_actions:
                    return True

        definite_reference = bool(
            re.match(
                r"^(?:"
                r"(?:(?:for|pour)\s+)?"
                r"(?:"
                r"the|this|that|these|those"
                r"|le|la|les|l"
                r"|ce|cet|cette|ces"
                r")"
                r")\b",
                completion_tail_key,
                flags=re.IGNORECASE,
            )
        )

        completion_object_words = set(
            comparison_key(
                completion_object
            ).split()
        )

        monetary_reference = bool(
            completion_object_words
            & monetary_reference_tokens
        )

        generic_reference = bool(
            completion_tokens
            and completion_tokens
            <= generic_transaction_reference_tokens
        )

        # ----------------------------------------------------------
        # Conservative payment-reference continuity.
        #
        # Positive generic forms:
        #
        #   the fee
        #   the transaction fee
        #   the service fee
        #   le prix du service
        #
        # Negative new-object forms remain rejected:
        #
        #   the monthly analytics subscription
        #   the software fee
        #
        # unless the new noun already shares a real object anchor with
        # the initiation event.
        # ----------------------------------------------------------

        if (
            completion_action_key
            == "payer"
            and same_subject
            and definite_reference
        ):
            if (
                monetary_reference
                and (
                    not completion_tokens
                    or generic_reference
                )
            ):
                return True

            # Same-sentence coordinated generic reference:
            #
            #   demande une intervention ... puis paie le service
            #
            # The same rule does NOT accept a newly introduced
            # qualified subscription/product.
            if (
                same_sentence
                and generic_reference
            ):
                return True

        # ----------------------------------------------------------
        # Non-payment coordinated generic reference.
        #
        # Preserve the previous C4 discourse rule, but prevent an
        # arbitrary newly-qualified object from becoming continuity
        # merely because the actor is the same.
        # ----------------------------------------------------------

        if (
            same_sentence
            and same_subject
            and definite_reference
            and generic_reference
        ):
            return True

        return False


    def _explicit_transaction_lifecycle_selection(
        self,
        sentences: Sequence[str],
    ) -> Dict[str, Any]:
        """
        Select canonical transaction lifecycle events while preserving exact evidence identity.

        Authority rules:

        1. The earliest valid explicit initiation establishes the start.

        2. Strong lifecycle/economic completion events after that start
           establish completion.

        3. Reservation / booking is contextual:
           - it is a start when it is the earliest transaction event;
           - it is a downstream completion when another explicit start
             already exists before it.

        4. Later explicit completion overrides an earlier intermediate
           reservation.

        5. Business-model declarations are not operational lifecycle
           evidence merely because they mention a completed transaction.
        """

        # ------------------------------------------------------------
        # Strong lifecycle / economic completion predicates.
        #
        # Reservation / booking is deliberately NOT included here.
        # It is resolved contextually after initiation authority is
        # established.
        # ------------------------------------------------------------

        completion_patterns: Tuple[
            Tuple[
                re.Pattern[str],
                str,
            ],
            ...,
        ] = (
            (
                re.compile(
                    r"\bclose(?:s|d|ing)?\b"
                    r"|\bcl(?:o|\u00f4)tur"
                    r"(?:er|e|ee|es|ees|ent|ait|ant"
                    r"|era|eront"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "cloturer",
            ),

            (
                re.compile(
                    r"\bconclu"
                    r"(?:re|t|ent|ait|aient|ra|ront)?\b"
                    r"|\bconclud"
                    r"(?:e|es|ed|ing)\b",
                    re.IGNORECASE,
                ),
                "conclure la transaction",
            ),

            (
                re.compile(
                    r"\bcomplete(?:s|d|ing)?\b"
                    r"|\bfinish(?:es|ed|ing)?\b"
                    r"|\bfinaliz(?:e|es|ed|ing)\b"
                    r"|\btermin"
                    r"(?:er|e|ee|es|ees|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b"
                    r"|\bfinalis"
                    r"(?:er|e|ee|es|ees|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b"
                    r"|\bachev"
                    r"(?:er|e|ee|es|ees|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "terminer",
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
                    r"\bvalid(?:er|e|ent)?\b"
                    r"|\bapprouv(?:er|e|ent)?\b"
                    r"|\bapprove(?:s|d|ing)?\b",
                    re.IGNORECASE,
                ),
                "valider",
            ),

            (
                re.compile(
                    r"\bpaie"
                    r"(?:nt|ra|ront|rait|raient)?\b"
                    r"|\bpaye"
                    r"(?:nt|ra|ront|rait|raient)?\b"
                    r"|\bpayer"
                    r"(?:a|ont|ait|aient)?\b"
                    r"|\bpay(?:s|ing)?\b"
                    r"|\bpaid\b",
                    re.IGNORECASE,
                ),
                "payer",
            ),

            (
                re.compile(
                    r"\breturn(?:s|ed|ing)?\b"
                    r"|\bretourn"
                    r"(?:er|e|ee|es|ees|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "retourner",
            ),

            (
                re.compile(
                    r"\bdeliver(?:s|ed|ing)?\b"
                    r"|\bfulfill(?:s|ed|ing)?\b"
                    r"|\blivr"
                    r"(?:er|e|ee|es|ees|ent|ait|ant"
                    r"|\u00e9(?:e|es|s)?)\b",
                    re.IGNORECASE,
                ),
                "livrer",
            ),
        )


        reservation_patterns: Tuple[
            Tuple[
                re.Pattern[str],
                str,
            ],
            ...,
        ] = (
            (
                re.compile(
                    r"\br(?:e|\u00e9)serv"
                    r"(?:er|e|ent|ait|aient|era|eront)\b"
                    r"|\bbook"
                    r"(?:s|ed|ing)?\b",
                    re.IGNORECASE,
                ),
                "reserver",
            ),
        )


        def operational_sentence(
            sentence: str,
        ) -> str:
            """
            Return usable operational evidence or an empty string.

            Economic-model declarations describe monetization and must
            not become transaction lifecycle events.
            """
            sentence_text = clean_text(
                sentence
            )

            if not sentence_text:
                return ""

            if self._is_scope_only(
                sentence_text
            ):
                return ""

            if self._is_problem_sentence(
                sentence_text
            ):
                return ""

            if (
                self._workflow_sentence_is_non_action_context(
                    sentence_text
                )
            ):
                return ""

            # Explicit transaction-unit metadata is object/value authority.
            #
            # "The primary transaction unit is a service booking."
            # defines WHAT is exchanged; it is not evidence that a
            # booking action actually occurred in the lifecycle.
            if self._explicit_transaction_unit_text(
                (sentence_text,)
            ):
                return ""

            sentence_key = comparison_key(
                sentence_text
            )

            if re.match(
                r"^"
                r"(?:(?:le|la|les|the|un|une)\s+)?"
                r"(?:"
                r"modele\s+economique"
                r"|modele\s+de\s+revenus"
                r"|modele\s+de\s+monetisation"
                r"|business\s+model"
                r"|revenue\s+model"
                r"|monetization\s+model"
                r"|monetisation\s+model"
                r"|pricing\s+model"
                r")\b",
                sentence_key,
                flags=re.IGNORECASE,
            ):
                return ""

            return sentence_text


        # ============================================================
        # CANONICAL EVENT SELECTION
        #
        # Transaction lifecycle authority must preserve the exact event
        # identity, not only an action label.
        #
        # We therefore collect every valid explicit initiation event,
        # then ask the existing canonical continuity authority which
        # downstream completion events belong to that initiation.
        #
        # Policy:
        #
        #   - initiation candidates are considered in document order;
        #   - the first initiation owning a complete coherent lifecycle
        #     outranks earlier orphan-only candidates;
        #   - inside one selected lifecycle, the latest coherent
        #     completion remains authoritative, preserving historical
        #     completion precedence;
        #   - when no complete lifecycle exists, the earliest valid
        #     initiation remains as partial evidence;
        #   - when no initiation exists at all, a valid strong
        #     completion may remain as completion-only partial evidence.
        # ============================================================

        initiation_events: List[
            Dict[str, Any]
        ] = []

        for sentence_index, sentence in enumerate(
            sentences
        ):
            sentence_text = operational_sentence(
                sentence
            )

            if not sentence_text:
                continue

            for pattern, action in (
                self._transaction_initiation_patterns()
            ):
                for match in pattern.finditer(
                    sentence_text
                ):
                    if (
                        self._transaction_action_is_negated(
                            sentence_text,
                            match,
                        )
                    ):
                        continue

                    if not (
                        self._transaction_match_is_grammatically_operational(
                            sentence=sentence_text,
                            action=action,
                            action_match=match,
                        )
                    ):
                        continue

                    initiation_events.append(
                        {
                            "location": (
                                sentence_index,
                                match.start(),
                            ),
                            "sentence_index":
                                sentence_index,
                            "sentence":
                                sentence_text,
                            "action":
                                action,
                            "match":
                                match,
                        }
                    )

        initiation_events.sort(
            key=lambda event:
                event[
                    "location"
                ]
        )


        def strong_completion_events_for(
            initiation_event: Dict[str, Any],
        ) -> List[Dict[str, Any]]:
            output: List[
                Dict[str, Any]
            ] = []

            initiation_location = (
                initiation_event[
                    "location"
                ]
            )

            for sentence_index, sentence in enumerate(
                sentences
            ):
                sentence_text = operational_sentence(
                    sentence
                )

                if not sentence_text:
                    continue

                for pattern, action in completion_patterns:
                    for match in pattern.finditer(
                        sentence_text
                    ):
                        if (
                            self._transaction_action_is_negated(
                                sentence_text,
                                match,
                            )
                        ):
                            continue

                        if not (
                            self._transaction_completion_candidate_is_operational(
                                sentence=sentence_text,
                                action=action,
                                action_match=match,
                            )
                        ):
                            continue

                        location = (
                            sentence_index,
                            match.start(),
                        )

                        if (
                            location
                            <= initiation_location
                        ):
                            continue

                        if not (
                            self._transaction_events_are_continuous(
                                initiation_sentence=(
                                    initiation_event[
                                        "sentence"
                                    ]
                                ),
                                initiation_action=(
                                    initiation_event[
                                        "action"
                                    ]
                                ),
                                initiation_match=(
                                    initiation_event[
                                        "match"
                                    ]
                                ),
                                completion_sentence=sentence_text,
                                completion_action=action,
                                completion_match=match,
                            )
                        ):
                            continue

                        output.append(
                            {
                                "location":
                                    location,
                                "sentence_index":
                                    sentence_index,
                                "sentence":
                                    sentence_text,
                                "action":
                                    action,
                                "match":
                                    match,
                            }
                        )

            return output


        def reservation_completion_events_for(
            initiation_event: Dict[str, Any],
        ) -> List[Dict[str, Any]]:
            output: List[
                Dict[str, Any]
            ] = []

            initiation_location = (
                initiation_event[
                    "location"
                ]
            )

            for sentence_index, sentence in enumerate(
                sentences
            ):
                sentence_text = operational_sentence(
                    sentence
                )

                if not sentence_text:
                    continue

                for (
                    pattern,
                    action,
                ) in reservation_patterns:
                    for match in pattern.finditer(
                        sentence_text
                    ):
                        if (
                            self._transaction_action_is_negated(
                                sentence_text,
                                match,
                            )
                        ):
                            continue

                        if not (
                            self._transaction_completion_candidate_is_operational(
                                sentence=sentence_text,
                                action=action,
                                action_match=match,
                            )
                        ):
                            continue

                        location = (
                            sentence_index,
                            match.start(),
                        )

                        # Reservation cannot close itself when it is
                        # the selected initiation event.
                        if (
                            location
                            <= initiation_location
                        ):
                            continue

                        if not (
                            self._transaction_events_are_continuous(
                                initiation_sentence=(
                                    initiation_event[
                                        "sentence"
                                    ]
                                ),
                                initiation_action=(
                                    initiation_event[
                                        "action"
                                    ]
                                ),
                                initiation_match=(
                                    initiation_event[
                                        "match"
                                    ]
                                ),
                                completion_sentence=sentence_text,
                                completion_action=action,
                                completion_match=match,
                            )
                        ):
                            continue

                        output.append(
                            {
                                "location":
                                    location,
                                "sentence_index":
                                    sentence_index,
                                "sentence":
                                    sentence_text,
                                "action":
                                    action,
                                "match":
                                    match,
                            }
                        )

            return output


        # ------------------------------------------------------------
        # First COMPLETE lifecycle in initiation order.
        #
        # For each initiation, preserve the historical rule that the
        # latest coherent downstream completion is the final boundary.
        # ------------------------------------------------------------

        for initiation_event in initiation_events:
            completion_events = (
                strong_completion_events_for(
                    initiation_event
                )
                + reservation_completion_events_for(
                    initiation_event
                )
            )

            if not completion_events:
                continue

            completion_event = max(
                completion_events,
                key=lambda event:
                    event[
                        "location"
                    ],
            )

            return {
                "initiation_action":
                    initiation_event[
                        "action"
                    ],
                "initiation_sentence":
                    initiation_event[
                        "sentence"
                    ],
                "initiation_match":
                    initiation_event[
                        "match"
                    ],
                "initiation_location":
                    initiation_event[
                        "location"
                    ],

                "completion_action":
                    completion_event[
                        "action"
                    ],
                "completion_sentence":
                    completion_event[
                        "sentence"
                    ],
                "completion_match":
                    completion_event[
                        "match"
                    ],
                "completion_location":
                    completion_event[
                        "location"
                    ],
            }


        # ------------------------------------------------------------
        # No complete lifecycle:
        # preserve earliest valid explicit initiation as partial
        # authority exactly as before.
        # ------------------------------------------------------------

        if initiation_events:
            initiation_event = (
                initiation_events[0]
            )

            return {
                "initiation_action":
                    initiation_event[
                        "action"
                    ],
                "initiation_sentence":
                    initiation_event[
                        "sentence"
                    ],
                "initiation_match":
                    initiation_event[
                        "match"
                    ],
                "initiation_location":
                    initiation_event[
                        "location"
                    ],

                "completion_action":
                    "",
                "completion_sentence":
                    "",
                "completion_match":
                    None,
                "completion_location":
                    None,
            }


        # ------------------------------------------------------------
        # Historical completion-only partial evidence.
        #
        # This branch applies ONLY when no initiation exists.
        # Reservation is already an initiation authority, so only the
        # strong completion family is considered here.
        # ------------------------------------------------------------

        completion_only_events: List[
            Dict[str, Any]
        ] = []

        for sentence_index, sentence in enumerate(
            sentences
        ):
            sentence_text = operational_sentence(
                sentence
            )

            if not sentence_text:
                continue

            for pattern, action in completion_patterns:
                for match in pattern.finditer(
                    sentence_text
                ):
                    if (
                        self._transaction_action_is_negated(
                            sentence_text,
                            match,
                        )
                    ):
                        continue

                    if not (
                        self._transaction_completion_candidate_is_operational(
                            sentence=sentence_text,
                            action=action,
                            action_match=match,
                        )
                    ):
                        continue

                    completion_only_events.append(
                        {
                            "location": (
                                sentence_index,
                                match.start(),
                            ),
                            "sentence_index":
                                sentence_index,
                            "sentence":
                                sentence_text,
                            "action":
                                action,
                            "match":
                                match,
                        }
                    )

        if completion_only_events:
            completion_event = max(
                completion_only_events,
                key=lambda event:
                    event[
                        "location"
                    ],
            )

            return {
                "initiation_action":
                    "",
                "initiation_sentence":
                    "",
                "initiation_match":
                    None,
                "initiation_location":
                    None,

                "completion_action":
                    completion_event[
                        "action"
                    ],
                "completion_sentence":
                    completion_event[
                        "sentence"
                    ],
                "completion_match":
                    completion_event[
                        "match"
                    ],
                "completion_location":
                    completion_event[
                        "location"
                    ],
            }


        return {
            "initiation_action":
                "",
            "initiation_sentence":
                "",
            "initiation_match":
                None,
            "initiation_location":
                None,

            "completion_action":
                "",
            "completion_sentence":
                "",
            "completion_match":
                None,
            "completion_location":
                None,
        }


    def _explicit_transaction_flow_bounds(
        self,
        sentences: Sequence[str],
    ) -> Tuple[str, str]:
        """
        Project canonical lifecycle selection to action boundaries.

        Exact event identity is owned by
        ``_explicit_transaction_lifecycle_selection``.
        """
        selection = (
            self._explicit_transaction_lifecycle_selection(
                sentences
            )
        )

        return (
            clean_text(
                selection.get(
                    "initiation_action"
                )
                or ""
            ),
            clean_text(
                selection.get(
                    "completion_action"
                )
                or ""
            ),
        )

    def _explicit_fulfillment_responsibility(
        self,
        *,
        sentences: Sequence[str],
        actors: Sequence[ActorContext],
    ) -> str:
        """
        Resolve who explicitly performs transaction fulfillment.

        Supply-side membership alone is not fulfillment authority.
        A direct execution relation must be explicitly present.

        The extracted subject is resolved to an existing canonical
        ActorContext. This method intentionally does not infer
        fulfillment mode.
        """
        french_pattern = re.compile(
            r"^\s*"
            r"(?:le\s+|la\s+|les\s+|"
            r"l['\u2019]\s*)?"
            r"(.+?)\s+"
            r"(?:"
            r"ex(?:e|\u00e9)cute"
            r"|ex(?:e|\u00e9)cutent"
            r"|r(?:e|\u00e9)alise"
            r"|r(?:e|\u00e9)alisent"
            r"|effectue|effectuent"
            r"|fournit|fournissent"
            r")"
            r"(?:\s+(?:ensuite|directement))?\s+"
            r"(?:"
            r"l['\u2019]\s*"
            r"|le\s+|la\s+|les\s+"
            r"|un\s+|une\s+|des\s+"
            r")?"
            r"(?=[^.;]{0,120}\b(?:"
            r"services?"
            r"|missions?"
            r"|prestations?"
            r"|interventions?"
            r"|travail"
            r"|travaux"
            r")\b)"
            r"[^.;]*?"
            r"(?:"
            r"services?"
            r"|missions?"
            r"|prestations?"
            r"|interventions?"
            r"|travail"
            r"|travaux"
            r")\b"
            r"(?:\s+.+?)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        english_pattern = re.compile(
            r"^\s*(?:the\s+)?"
            r"(.+?)\s+"
            r"(?:"
            r"performs?"
            r"|delivers?"
            r"|provides?"
            r"|executes?"
            r")"
            r"(?:\s+(?:then|directly))?\s+"
            r"(?:the\s+|a\s+|an\s+)?"
            r"(?=[^.;]{0,120}\b(?:"
            r"services?|missions?|jobs?|work"
            r")\b)"
            r"[^.;]*?"
            r"(?:"
            r"services?"
            r"|missions?"
            r"|jobs?"
            r"|work"
            r")\b"
            r"(?:\s+.+?)?"
            r"(?=[.;]|$)",
            re.IGNORECASE,
        )

        actor_by_key: Dict[
            str,
            str,
        ] = {}

        actors_by_alias: Dict[
            str,
            List[str],
        ] = {}

        for actor in actors:
            name = self._clean_actor(
                actor.name
            )

            key = comparison_key(
                name
            )

            if not name or not key:
                continue

            actor_by_key.setdefault(
                key,
                actor.name,
            )

            alias = (
                self._actor_alias_identity_key(
                    name
                )
            )

            if alias:
                actors_by_alias.setdefault(
                    alias,
                    [],
                ).append(
                    actor.name
                )

        for sentence in sentences:
            relation_sentence = (
                self._role_relation_sentence(
                    sentence
                )
            )

            for pattern in (
                french_pattern,
                english_pattern,
            ):
                match = pattern.search(
                    relation_sentence
                )

                if not match:
                    continue

                candidate = self._clean_actor(
                    match.group(1)
                )

                if (
                    not candidate
                    or self._is_actor_identity_pronoun(
                        candidate
                    )
                ):
                    continue

                candidate_key = comparison_key(
                    candidate
                )

                if not candidate_key:
                    continue

                exact_actor = actor_by_key.get(
                    candidate_key
                )

                if exact_actor:
                    return exact_actor

                candidate_alias = (
                    self._actor_alias_identity_key(
                        candidate
                    )
                )

                if candidate_alias:
                    alias_matches = list(
                        dict.fromkeys(
                            actors_by_alias.get(
                                candidate_alias,
                                [],
                            )
                        )
                    )

                    if len(alias_matches) == 1:
                        return alias_matches[0]

                # Reuse the canonical conservative identity matcher
                # already used by workflow ownership. It performs
                # token-by-token singular/plural reconciliation and
                # does not introduce semantic synonym matching.
                identity_matches = list(
                    dict.fromkeys(
                        actor.name
                        for actor in actors
                        if (
                            self._workflow_actor_identity_prefix_match(
                                candidate,
                                actor.name,
                            )
                        )
                    )
                )

                # Ambiguous morphology must never select arbitrarily.
                if len(identity_matches) == 1:
                    return identity_matches[0]

        return ""


    def _extract_transaction_unit(
        self,
        *,
        sentences: Sequence[str],
        actors: Sequence[ActorContext],
        workflows: Sequence[WorkflowContext],
        clarification_facts: Dict[str, Any] | None = None,
    ) -> TransactionUnitContext:
        """
        Extrait l'unité centrale de valeur ou d'opération du projet.
        """
        facts = dict(
            clarification_facts
            or {}
        )

        clarified_supply = self._clean_actor(
            facts.get(
                "supply_side"
            )
        )

        clarified_demand = self._clean_actor(
            facts.get(
                "demand_side"
            )
        )

        supply_actor = (
            clarified_supply
            or next(
                (
                    actor.name
                    for actor in actors
                    if actor.role
                    == ActorRole.PROVIDER
                ),
                "",
            )
        )

        demand_actor = (
            clarified_demand
            or next(
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
        )

        fulfillment_responsibility = (
            self._explicit_fulfillment_responsibility(
                sentences=sentences,
                actors=actors,
            )
        )

        explicit_unit = (
            self._explicit_transaction_unit_text(
                sentences
            )
        )

        if explicit_unit:
            (
                initiation_action,
                completion_action,
            ) = (
                self._explicit_transaction_flow_bounds(
                    sentences
                )
            )

            signal_count = sum(
                bool(value)
                for value in (
                    explicit_unit,
                    supply_actor,
                    demand_actor,
                )
            )

            return TransactionUnitContext(
                name=explicit_unit,
                description=explicit_unit,
                object=explicit_unit,
                supply_actor=supply_actor,
                demand_actor=demand_actor,
                fulfillment_responsibility=fulfillment_responsibility,
                initiation_action=initiation_action,
                completion_action=completion_action,
                value_exchanged=explicit_unit,
                is_explicit=True,
                confidence=round(
                    min(
                        0.98,
                        0.65
                        + signal_count * 0.10,
                    ),
                    2,
                ),
            )

        lifecycle_selection = (
            self._explicit_transaction_lifecycle_selection(
                sentences
            )
        )

        initiation_action = clean_text(
            lifecycle_selection.get(
                "initiation_action"
            )
            or ""
        )

        completion_action = clean_text(
            lifecycle_selection.get(
                "completion_action"
            )
            or ""
        )

        initiation_sentence = clean_text(
            lifecycle_selection.get(
                "initiation_sentence"
            )
            or ""
        )

        initiation_match = (
            lifecycle_selection.get(
                "initiation_match"
            )
        )

        object_text = ""

        if (
            initiation_sentence
            and initiation_match is not None
        ):
            object_text = self._transaction_object(
                initiation_sentence,
                initiation_match,
            )

        # Workflow extraction is not transaction-lifecycle authority.
        #
        # A workflow may enrich the object of an already-established
        # transaction initiation, but it must never manufacture a
        # transaction start or a TransactionUnit on its own.
        if (
            not initiation_action
            and not completion_action
        ):
            return TransactionUnitContext()

        if (
            not object_text
            and initiation_action
        ):
            for workflow in workflows:
                if workflow.object:
                    object_text = workflow.object
                    break

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
            fulfillment_responsibility=fulfillment_responsibility,
            initiation_action=initiation_action,
            completion_action=completion_action,
            value_exchanged=object_text,
            is_explicit=bool(
                initiation_sentence
                or completion_action
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

        # French explicit initiation wrapper normalization.
        #
        # "initie une demande d'intervention"
        #                ->
        # canonical transaction object: "d'intervention"
        #
        # The wrapper is removed only when the selected transaction
        # action is an explicit initiation predicate. Direct request
        # predicates keep their normal object extraction semantics.
        #
        # English remains untouched:
        # "initiates a service request"
        #                ->
        # "service request"
        action_key = comparison_key(
            action_match.group(0)
        )

        if action_key.startswith(
            "initi"
        ):
            tail = re.sub(
                r"^demande\s+",
                "",
                tail,
                count=1,
                flags=re.IGNORECASE,
            )

        return self._compact(
            tail,
            120,
        )

    def _reconcile_workflow_actor_membership(
        self,
        *,
        actors: Sequence[ActorContext],
        workflows: Sequence[WorkflowContext],
    ) -> List[ActorContext]:
        """
        U2 canonical workflow actor membership authority.

        A non-technical actor explicitly owning a canonical workflow
        action must not exist only inside WorkflowContext.actor.

        The actor registry is reconciled before transaction projection,
        so downstream authorities consume one coherent actor set.

        Important boundaries:

        - technical executors are never promoted to business actors;
        - implicit workflows do not manufacture actors;
        - existing canonical actors keep their existing role authority;
        - request initiation establishes operational USER authority;
        - other explicit business workflow owners are materialized
          conservatively using existing actor-role authority.

        No project, sector, region or archetype vocabulary is used.
        """

        output = list(
            actors
        )

        seen = {
            comparison_key(
                actor.name
            )
            for actor in output
            if comparison_key(
                actor.name
            )
        }

        technical_actor_keys = {
            "system",
            "systeme",
            "platform",
            "plateforme",
            "application",
            "software",
            "logiciel",
        }

        request_actions = {
            "demander",
            "request",
            "publier",
            "post",
            "submit",
            "soumettre",
        }

        request_object_markers = (
            "demande",
            "request",
        )

        for workflow in workflows:

            if not getattr(
                workflow,
                "is_explicit",
                False,
            ):
                continue

            name = clean_text(
                workflow.actor
            )

            key = comparison_key(
                name
            )

            if (
                not name
                or not key
                or key in seen
                or key in technical_actor_keys
                or key in self.GENERIC_ACTORS
                or self._is_actor_identity_pronoun(
                    name
                )
            ):
                continue

            # Workflow actor extraction may identify a local subject,
            # but only business-actor-shaped identities are admitted
            # into ActorContext.
            #
            # This prevents sensors, products or arbitrary objects from
            # becoming business actors merely because they execute a
            # technical workflow predicate.
            if not self._looks_like_actor_phrase(
                name
            ):
                continue

            action_key = comparison_key(
                workflow.action
            )

            object_key = comparison_key(
                workflow.object
            )

            role = self._actor_role(
                name
            )

            # Explicit request initiation is operational USER authority.
            #
            # Examples:
            #   responsable maintenance publie une demande
            #   maintenance manager submits a request
            #
            # Publishing something else does not imply USER authority.
            request_initiator = bool(
                action_key
                in request_actions
                and (
                    action_key
                    in {
                        "demander",
                        "request",
                    }
                    or any(
                        marker in object_key
                        for marker
                        in request_object_markers
                    )
                )
            )

            if request_initiator:
                role = ActorRole.USER

            seen.add(
                key
            )

            output.append(
                ActorContext(
                    name=name,
                    role=role,
                    is_explicit=True,
                )
            )

            # Preserve the existing canonical packet bound.
            if len(output) >= 8:
                break

        return output[:8]


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

        # Result/output vocabulary may strengthen a productive
        # business action, but passive receipt must not outrank the
        # initiating action merely because it mentions an output.
        passive_result_action = (
            comparison_key(action)
            in {
                "recevoir",
                "receive",
            }
        )

        if (
            not passive_result_action
            and self._contains_any(
            sentence,
            (
                "alerte",
                "alert",
                "résultat",
                "result",
                "rapport",
                "confirmation",
            ),
            )
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

    def _workflow_purpose_connectors(
        self,
        text: str,
    ) -> List[re.Match[str]]:
        """
        Return explicit purpose connectors conservatively.

        Always-authoritative purpose connectors:
        - afin de
        - pour que
        - so that
        - in order to

        A bare French "pour" is accepted as a purpose boundary only
        when the following phrase starts with an action already known
        by the canonical workflow action vocabulary.

        This deliberately prefers preserving an ambiguous phrase in
        the object over inventing a purpose from a noun that merely
        resembles an infinitive.
        """
        matches: List[
            re.Match[str]
        ] = list(
            re.finditer(
                r"\s+(?:"
                r"afin\s+de"
                r"|pour\s+que"
                r"|so\s+that"
                r"|in\s+order\s+to"
                r")\s+",
                text,
                flags=re.IGNORECASE,
            )
        )

        for match in re.finditer(
            r"\s+pour\s+",
            text,
            flags=re.IGNORECASE,
        ):
            tail = text[
                match.end():
            ].lstrip()

            occurrences = (
                self._workflow_action_occurrences(
                    tail
                )
            )

            if not occurrences:
                continue

            first_match = (
                occurrences[
                    0
                ]["match"]
            )

            if first_match.start() != 0:
                continue

            matches.append(
                match
            )

        matches.sort(
            key=lambda value: (
                value.start(),
                value.end(),
            )
        )

        return matches


    def _workflow_first_purpose_connector(
        self,
        text: str,
        *,
        after: int = -1,
    ) -> re.Match[str] | None:
        """
        Return the first valid purpose connector after the requested
        position.
        """
        for connector in (
            self._workflow_purpose_connectors(
                text
            )
        ):
            if connector.start() > after:
                return connector

        return None


    def _action_object(
        self,
        sentence: str,
        action_match: re.Match[str],
    ) -> str:
        tail = sentence[
            action_match.end():
        ]

        purpose_connector = (
            self._workflow_first_purpose_connector(
                tail
            )
        )

        if purpose_connector is not None:
            tail = tail[
                :purpose_connector.start()
            ]

        # ----------------------------------------------------------
        # Canonical coordinated-action boundary.
        #
        # The object of one workflow must stop before a later workflow
        # predicate already recognized by the shared action authority:
        #
        #   "books a service and pays the fee"
        #   "books a service and the company pays the fee"
        #   "demande une intervention puis paie le service"
        #
        # Do NOT split merely because an object contains "and" / "et":
        #
        #   "books transport and accommodation"
        #
        # In that case there is no later canonical action, so the full
        # coordinated object is preserved.
        # ----------------------------------------------------------

        later_actions = [
            item
            for item
            in self._workflow_action_occurrences(
                sentence
            )
            if (
                item["match"].start()
                >= action_match.end()
            )
        ]

        if later_actions:
            next_action = min(
                later_actions,
                key=lambda item: (
                    item["match"].start(),
                    item["match"].end(),
                ),
            )

            between = sentence[
                action_match.end():
                next_action[
                    "match"
                ].start()
            ]

            boundaries = list(
                re.finditer(
                    r"[,;]"
                    r"|\b(?:"
                    r"and|et|"
                    r"then|puis|ensuite"
                    r")\b",
                    between,
                    flags=re.IGNORECASE,
                )
            )

            if boundaries:
                boundary = boundaries[-1]

                tail = tail[
                    :boundary.start()
                ]

        # Preserve the historical notification/output boundary for
        # surfaces that may not be represented as an independent
        # workflow occurrence.
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
        connectors = (
            self._workflow_purpose_connectors(
                sentence
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
        language: str = "fr",
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
            if language == "en":
                text = (
                    f"{text} to {result}"
                    if text
                    else result
                )
            else:
                text = (
                    f"{text} afin de {result}"
                    if text
                    else result
                )

        if output:
            if language == "en":
                text = (
                    f"{text}, then produce {output}"
                    if text
                    else output
                )
            else:
                text = (
                    f"{text}, puis produire {output}"
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
        """
        Return True only when a sentence expresses an actual
        problem, pain, friction or negative operational consequence.

        Natural-language problem statements must not require an
        artificial label such as "Le probleme principal est...".

        At the same time, positive solution capabilities and MVP
        scope declarations must never become problem authority.
        """
        text = clean_text(
            sentence
        )

        if not text:
            return False

        # Existing explicit declarations remain authoritative.
        if self._contains_any(
            text,
            self.PROBLEM_MARKERS,
        ):
            return True

        key = comparison_key(
            text
        )

        if not key:
            return False

        explicit_problem_prefixes = (
            "le probleme",
            "la difficulte",
            "the problem",
            "the current process",
        )

        if key.startswith(
            explicit_problem_prefixes
        ):
            return True

        # Positive capability/scope declarations must not be
        # reclassified merely because they mention an operational
        # concept also present in a pain statement.
        positive_capability_prefixes = (
            "le mvp comprend",
            "le mvp inclut",
            "mvp comprend",
            "mvp inclut",
            "la plateforme permet",
            "la plateforme affiche",
            "l application permet",
            "l application affiche",
            "le service permet",
            "la solution permet",
            "les utilisateurs peuvent",
            "the mvp includes",
            "the mvp contains",
            "the platform allows",
            "the platform lets",
            "the platform displays",
            "the application allows",
            "the application lets",
            "the service allows",
            "the solution allows",
            "users can",
        )

        if key.startswith(
            positive_capability_prefixes
        ):
            return False

        # Signals describe semantics, not one specific product or
        # industry. They cover common natural formulations of
        # difficulty, friction, unreliability and operational harm.
        difficulty_signals = (
            "il est difficile de",
            "il est souvent difficile de",
            "est difficile de",
            "sont difficiles a",
            "a du mal a",
            "ont du mal a",
            "peine a",
            "peinent a",
            "reste lente",
            "reste lent",
            "reste difficile",
            "is difficult to",
            "is hard to",
            "struggle to",
            "struggles to",
            "struggling to",
            "is slow",
            "remains slow",
            "remains difficult",
        )

        harm_signals = (
            "lent et incertain",
            "lente et incertaine",
            "lent et peu fiable",
            "lente et peu fiable",
            "source d erreur",
            "sources d erreur",
            "erreur prone",
            "error prone",
            "unreliable",
            "incertain",
            "incertaine",
            "inefficace",
            "inefficient",
            "inconsistent",
            "inconsistently",
            "incoherent",
            "breakdown",
            "breakdowns",
            "interruption",
            "interruptions",
            "repeated errors",
            "friction",
            "conflit",
            "conflicts",

            # Blind-B2 natural-language context authority.
            #
            # Generic negative-outcome morphology. These markers are
            # intentionally combined with consequence authority below;
            # none of them independently turns a capability sentence
            # into a problem.
            "conflicting",
            "conflictuel",
            "conflictuelle",
            "long waiting",
            "waiting time",
            "temps d attente",
            "poor ",
            "mauvais",
            "mauvaise",
            "incomplete",
            "incomplet",

            "perte de temps",
            "perdent du temps",
            "temps perdu",
            "wasted time",
            "lose time",
            "lost time",
            "retard",
            "delay",
            "delays",
            "downtime",
        )

        consequence_signals = (
            "ce qui peut",
            "ce qui provoque",
            "ce qui entraine",
            "ce qui entraine",
            "cela provoque",
            "cela entraine",
            "cela entraine",
            "provoque",
            "entraine",
            "entraine",
            "retarde",
            "retardent",
            "prolonge",
            "prolonger",
            "perturbe",
            "perturber",
            "cause",
            "causes",

            # French and English creation/result predicates share
            # the same semantic authority: they introduce an outcome.
            "creer",
            "cree",
            "creent",
            "create",
            "creates",

            "result in",
            "results in",
            "leads to",
            "leading to",
        )

        strong_problem_signals = (
            "impossible de",
            "ne peut pas",
            "ne peuvent pas",
            "cannot",
            "unable to",
            "fails to",
            "fail to",
            "trop lent",
            "trop lente",
            "too slow",
            "trop couteux",
            "trop couteuse",
            "too costly",
            "too much time",
            "too much effort",
            "excessive time",
            "excessive effort",
            "excessive manual effort",
            "time consuming",
            "chronophage",
            "manuellement",
            "manually",
        )

        has_difficulty = any(
            signal in key
            for signal in difficulty_signals
        )

        has_harm = any(
            signal in key
            for signal in harm_signals
        )

        has_consequence = any(
            signal in key
            for signal in consequence_signals
        )

        has_strong_problem = any(
            signal in key
            for signal in strong_problem_signals
        )

        # A strong negative operational statement is independently
        # sufficient.
        if has_strong_problem:
            return True

        # Natural difficulty becomes problem authority when the
        # sentence also carries harm or a consequence.
        if (
            has_difficulty
            and (
                has_harm
                or has_consequence
            )
        ):
            return True

        # Declarative harm plus consequence is also explicit problem
        # evidence even without the words "problem" or "difficulty".
        if (
            has_harm
            and has_consequence
        ):
            return True

        return False

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
        max_items: int | None,
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

            if (
                max_items is not None
                and len(output) >= max_items
            ):
                break

        return output
    def _is_explicit_business_model_statement(
        self,
        sentence: str,
    ) -> bool:
        """
        Decide whether free text actually declares a business /
        revenue model.

        Merely mentioning subscription, commission, sale, rental or
        another monetization noun is insufficient.

        Accepted:
        - explicitly labelled business/revenue-model statements;
        - positive payment / charging relations;
        - positive revenue relations;
        - direct copular monetization declarations.

        Rejected:
        - negative payer-role statements;
        - operational sentences that merely mention monetization;
        - incidental business vocabulary.
        """
        text = clean_text(
            sentence
        )

        if not text:
            return False

        key = comparison_key(
            text
        )

        if not key:
            return False

        if self._explicit_transaction_unit_text(
            [text]
        ):
            return False

        mechanisms = (
            self._business_model_mechanisms(
                text
            )
        )

        # -------------------------------------------------
        # 1. Explicit business-model labels require economic
        #    content, not merely a meta/introduction heading.
        # -------------------------------------------------

        explicit_label_patterns = (
            r"\bmodele\s+economique\b",
            r"\bbusiness\s+model\b",
            r"\brevenue\s+model\b",
            r"\bmodele\s+de\s+revenus?\b",
            r"\bmonetisation\b",
            r"\bmonetization\b",
        )

        explicit_label_match = next(
            (
                match
                for pattern
                in explicit_label_patterns
                for match
                in [
                    re.search(
                        pattern,
                        key,
                        flags=re.IGNORECASE,
                    )
                ]
                if match is not None
            ),
            None,
        )

        if explicit_label_match is not None:
            # A known concrete monetization mechanism makes the
            # labelled statement authoritative immediately.
            if mechanisms:
                return True

            label_tail = key[
                explicit_label_match.end():
            ].strip(
                " .,:;-"
            )

            if not label_tail:
                return False

            # Meta summaries describe the number/structure of revenue
            # streams but do not themselves state the mechanisms.
            meta_summary_patterns = (
                r"^(?:"
                r"comporte|comprend|contient|inclut"
                r"|includes?|contains?|comprises?"
                r"|has|have"
                r")\b"
                r".{0,120}\b(?:"
                r"sources?\s+de\s+revenus?"
                r"|flux\s+de\s+revenus?"
                r"|revenue\s+streams?"
                r"|revenue\s+sources?"
                r"|sources?\s+of\s+revenue"
                r")\b",
            )

            if any(
                re.search(
                    pattern,
                    label_tail,
                    flags=re.IGNORECASE,
                )
                for pattern
                in meta_summary_patterns
            ):
                return False

            # An explicitly unresolved model is not a confirmed
            # business-model declaration.
            unresolved_patterns = (
                r"^(?:(?:"
                r"est|sera|serait|reste"
                r"|is|will\s+be|would\s+be|remains"
                r")\s+)?(?:"
                r"a\s+definir"
                r"|non\s+defini"
                r"|indetermine"
                r"|to\s+be\s+defined"
                r"|undefined"
                r"|undecided"
                r"|unknown"
                r"|tbd"
                r")\b",
            )

            if any(
                re.search(
                    pattern,
                    label_tail,
                    flags=re.IGNORECASE,
                )
                for pattern
                in unresolved_patterns
            ):
                return False

            # Copular labelled declarations remain authoritative even
            # when the concrete mechanism is outside our small
            # mechanism taxonomy:
            # "business model is usage-based pricing".
            concrete_label_patterns = (
                r"^(?:"
                r"envisage\s+)?"
                r"(?:est|sera|serait)\s+.+$",

                r"^(?:"
                r"is|will\s+be|would\s+be"
                r")\s+.+$",

                r"^(?:"
                r"repose|reposera|reposerait"
                r")\s+sur\s+.+$",

                r"^(?:"
                r"is|will\s+be|would\s+be"
                r")\s+based\s+on\s+.+$",
            )

            if any(
                re.search(
                    pattern,
                    label_tail,
                    flags=re.IGNORECASE,
                )
                for pattern
                in concrete_label_patterns
            ):
                return True

            # Also admit labelled non-copular declarations carrying
            # concrete pricing/billing semantics.
            concrete_economic_terms = (
                r"\b(?:"
                r"facturation"
                r"|billing"
                r"|pricing"
                r"|tarifs?"
                r"|prix"
                r"|fees?"
                r"|frais"
                r"|usage\s+based"
                r"|pay\s+per\s+use"
                r"|per\s+use"
                r")\b"
            )

            if re.search(
                concrete_economic_terms,
                label_tail,
                flags=re.IGNORECASE,
            ):
                return True

            return False

        # -------------------------------------------------
        # 2. A monetization noun alone is not enough.
        # -------------------------------------------------

        business_terms = (
            r"(?:"
            r"abonnements?"
            r"|subscriptions?"
            r"|commissions?"
            r"|freemium"
            r"|locations?"
            r"|rentals?"
            r"|ventes?"
            r"|sales?"
            r")"
        )

        if not re.search(
            rf"(?<!\w){business_terms}(?!\w)",
            key,
            flags=re.IGNORECASE,
        ):
            return False

        # -------------------------------------------------
        # 3. Negative role statements must not be promoted.
        #
        # Example:
        # "X n'est pas n?cessairement la personne qui paie
        # l'abonnement."
        # -------------------------------------------------

        if self._role_relation_is_negated(
            text,
            ActorRole.PAYER,
        ):
            return False

        # Additional direct monetization negations.
        negative_patterns = (
            rf"\bne\b.{{0,80}}\bpas\b"
            rf".{{0,80}}(?<!\w){business_terms}(?!\w)",

            rf"\b(?:does|do|is|are|will|would)\s+not\b"
            rf".{{0,80}}(?<!\w){business_terms}(?!\w)",

            rf"\b(?:doesn|don|isn|aren|won|wouldn)\s+t\b"
            rf".{{0,80}}(?<!\w){business_terms}(?!\w)",
        )

        if any(
            re.search(
                pattern,
                key,
                flags=re.IGNORECASE,
            )
            for pattern in negative_patterns
        ):
            return False

        # -------------------------------------------------
        # 4. Positive economic predicates.
        # -------------------------------------------------

        payment_predicates = (
            r"(?:"
            r"paie|paye|paient|payent"
            r"|paiera|payera|paieront|payeront"
            r"|paye|payee|payes|payees"
            r"|facture|facturent|facturee|facturees"
            r"|pay|pays|paid"
            r"|charge|charges|charged"
            r")"
        )

        revenue_predicates = (
            r"(?:"
            r"revenu|revenus"
            r"|revenue|revenues"
            r"|prix|pricing"
            r"|tarif|tarifs"
            r"|monetise|monetisee"
            r"|monetized"
            r")"
        )

        commission_relation_patterns = (
            # FR: prelever / percevoir / prendre / recevoir
            # une commission.
            r"\b(?:"
            r"prelev(?:er|e|ent|ait|era|eront)"
            r"|percev(?:oir|ez|ons|ait|aient|ra|ront)"
            r"|percoi(?:t|vent)"
            r"|prend|prennent|prendra|prendront"
            r"|recoit|recoivent|recevra|recevront"
            r")\b"
            r".{0,80}\bcommissions?\b",

            # EN: collect / take / earn / receive commission.
            r"\b(?:"
            r"collect(?:s|ed|ing)?"
            r"|take|takes|took|taking"
            r"|earn(?:s|ed|ing)?"
            r"|receive(?:s|d|ing)?"
            r")\b"
            r".{0,80}\bcommissions?\b",
        )

        subscription_relation_patterns = (
            # FR subscription relation.
            r"\b(?:"
            r"souscri(?:re|t|ts|vent|vez|vons"
            r"|rait|raient|ra|ront)"
            r")\b"
            r".{0,100}\babonnements?\b",

            # EN subscription relation.
            r"\bsubscribe(?:s|d|ing)?\b"
            r".{0,100}\bsubscriptions?\b",
        )

        if any(
            re.search(
                pattern,
                key,
                flags=re.IGNORECASE,
            )
            for pattern
            in (
                *commission_relation_patterns,
                *subscription_relation_patterns,
            )
        ):
            return True

        positive_patterns = (
            # Actor/company performs payment or charging action.
            rf"\b{payment_predicates}\b"
            rf".{{0,120}}(?<!\w){business_terms}(?!\w)",

            # Monetization model followed by payment/pricing evidence.
            rf"(?<!\w){business_terms}(?!\w)"
            rf".{{0,120}}\b(?:"
            rf"{payment_predicates}|{revenue_predicates}"
            rf")\b",

            # Revenue relation.
            rf"\b{revenue_predicates}\b"
            rf".{{0,120}}(?<!\w){business_terms}(?!\w)",

            # Direct model declaration:
            # "Le service est freemium."
            # "The offering is subscription based."
            rf"\b(?:est|sera|serait|is|will\s+be|would\s+be)\b"
            rf".{{0,40}}(?<!\w){business_terms}(?!\w)",
        )

        return any(
            re.search(
                pattern,
                key,
                flags=re.IGNORECASE,
            )
            for pattern in positive_patterns
        )

    def _business_model_mechanisms(
        self,
        value: Any,
    ) -> set[str]:
        """
        Extract only monetization mechanisms used for conservative
        business-model equivalence.

        The set intentionally distinguishes multi-model strategies:
        subscription + commission must never collapse to subscription.
        """
        key = comparison_key(
            clean_text(
                value
            )
        )

        if not key:
            return set()

        patterns: Tuple[
            Tuple[
                str,
                str,
            ],
            ...,
        ] = (
            (
                "subscription",
                r"\b(?:"
                r"abonnements?"
                r"|subscriptions?"
                r")\b",
            ),
            (
                "commission",
                r"\bcommissions?\b",
            ),
            (
                "freemium",
                r"\bfreemium\b",
            ),
            (
                "rental",
                r"\b(?:"
                r"locations?"
                r"|rentals?"
                r")\b",
            ),
            (
                "sale",
                r"\b(?:"
                r"ventes?"
                r"|sales?"
                r")\b",
            ),
        )

        return {
            label
            for label, pattern in patterns
            if re.search(
                pattern,
                key,
                flags=re.IGNORECASE,
            )
        }

    def _business_model_content_key(
        self,
        value: Any,
    ) -> str:
        """
        Normalize a business-model formulation while preserving its
        economic content.

        Only declaration wrappers are removed. Pricing cadence,
        payer, commissions, tiers and other business information stay
        part of the identity.
        """
        key = comparison_key(
            clean_text(
                value
            )
        )

        if not key:
            return ""

        prefixes = (
            r"^\s*(?:"
            r"le\s+)?"
            r"modele\s+economique"
            r"(?:\s+envisage)?"
            r"\s+(?:est|sera|serait)\s+",

            r"^\s*(?:"
            r"le\s+)?"
            r"modele\s+de\s+revenus?"
            r"\s+(?:est|sera|serait)\s+",

            r"^\s*(?:"
            r"the\s+)?"
            r"business\s+model"
            r"(?:\s+considered|\s+planned)?"
            r"\s+(?:is|will\s+be|would\s+be)\s+",

            r"^\s*(?:"
            r"the\s+)?"
            r"revenue\s+model"
            r"\s+(?:is|will\s+be|would\s+be)\s+",
        )

        normalized = key

        for pattern in prefixes:
            normalized = re.sub(
                pattern,
                "",
                normalized,
                count=1,
                flags=re.IGNORECASE,
            ).strip()

        return normalized.strip(
            " .,:;"
        )

    def _business_models_equivalent(
        self,
        left: Any,
        right: Any,
    ) -> bool:
        """
        Conservative equivalence for business-model formulations.

        Equal mechanism sets are required before containment can mark
        two formulations as duplicates. This prevents a richer
        multi-mechanism model from being erased by a simpler one.
        """
        left_key = (
            self._business_model_content_key(
                left
            )
        )

        right_key = (
            self._business_model_content_key(
                right
            )
        )

        if (
            not left_key
            or not right_key
        ):
            return False

        left_mechanisms = (
            self._business_model_mechanisms(
                left
            )
        )

        right_mechanisms = (
            self._business_model_mechanisms(
                right
            )
        )

        if (
            left_mechanisms
            != right_mechanisms
        ):
            return False

        if left_key == right_key:
            return True

        return (
            left_key in right_key
            or right_key in left_key
        )

    def _dedupe_business_models(
        self,
        values: Sequence[str],
    ) -> List[str]:
        """
        Deduplicate economic reformulations without collapsing
        genuinely distinct monetization mechanisms.

        Input order carries authority. Explicit user formulations are
        therefore passed first and win over equivalent inferred forms.
        """
        output: List[str] = []

        for raw_value in unique_texts(
            values
        ):
            value = clean_text(
                raw_value
            ).strip(
                " .,:;"
            )

            if not value:
                continue

            if any(
                self._business_models_equivalent(
                    value,
                    existing,
                )
                for existing in output
            ):
                continue

            output.append(
                value
            )

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
            if self._is_explicit_business_model_statement(
                sentence
            )
        )

        explicit_models = (
            self._dedupe_business_models(
                explicit_values
            )
        )

        inferred_models = (
            self._dedupe_business_models(
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
        )

        # Explicit user declarations have priority over equivalent
        # structured/inferred reformulations.
        all_models = (
            self._dedupe_business_models(
                [
                    *explicit_models,
                    *inferred_models,
                ]
            )
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
        """
        Build canonical constraints.

        Explicit structured constraint fields remain authoritative
        compatibility/user inputs.

        Free-text sentences are added only when they express
        a real restriction, obligation or operating boundary.
        Domain nouns alone are never sufficient.
        """
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
            text = clean_text(
                sentence
            )

            if not text:
                continue

            key = comparison_key(
                text
            )

            explicitly_labeled = (
                re.match(
                    r"^\s*(?:"
                    r"(?:the\s+)?(?:main\s+)?constraints?"
                    r"|(?:les\s+)?contraintes?"
                    r"(?:\s+principales?)?"
                    r")\b",
                    key,
                    flags=re.IGNORECASE,
                )
                is not None
            )

            if not (
                explicitly_labeled
                or is_constraint_statement(
                    text
                )
            ):
                continue

            value = (
                text.split(
                    ":",
                    1,
                )[1]
                if (
                    explicitly_labeled
                    and ":" in text
                )
                else text
            )

            if explicitly_labeled:
                values.extend(
                    self._split_list(
                        value
                    )
                )
            else:
                values.append(
                    clean_text(
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
        *,
        structured: Optional[
            Dict[str, Any]
        ] = None,
    ) -> List[str]:
        explicit_environment = (
            self._canonical_requirement_values(
                structured or {},
                "deployment_environment",
            )
        )

        if explicit_environment:
            return explicit_environment[:6]

        terms = (
            "serre",
            "greenhouse",
            "terrain",
            "field",
            "usine",
            "factory",
            "h?pital",
            "hospital",
            "?cole",
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
        if is_scope_exclusion_statement(
            text
        ):
            return True

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
        """
        Normalize an actor candidate without turning a descriptive
        proposition into the actor identity itself.

        Geographic qualifiers may legitimately remain part of the actor
        identity. Descriptive relative or action clauses do not.

        Invalid overlong candidates are rejected rather than blindly
        truncated, so ActorContext keeps its schema guard.
        """
        text = clean_text(
            value
        )

        if not text:
            return ""

        text = re.split(
            r"\s*(?::|\u2014|\u2013)\s*"
            r"|\s+\b(?:"
            r"qui|que|dont|o\u00f9|"
            r"lequel|laquelle|lesquels|lesquelles|"
            r"who|which|that|whose|where|"
            r"ayant|souhaitant|cherchant|utilisant|"
            r"g\u00e9rant|gerant|"
            r"having|needing|requiring|using|"
            r"seeking|managing"
            r")\b\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        text = re.sub(
            r"^(?:les|des|aux|the|a|an)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = clean_text(
            text.strip(
                " .,:;"
            )
        )

        if len(text) > 180:
            return ""

        return text

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
