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
            language=language,
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
                or key in self.GENERIC_ACTORS
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
        Extract explicitly declared individual sides of a two-sided
        operating model.

        Examples:
        - "Le premier cote est constitue de ..."
        - "Le second cote est constitue de ..."
        - "The first side consists of ..."
        - "The second side consists of ..."

        Ordinal position carries no business-role authority.
        Provider / buyer classification comes only from semantic
        evidence inside the declared side.
        """
        french_pattern = re.compile(
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

        english_pattern = re.compile(
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

        output: List[
            Tuple[str, ActorRole]
        ] = []

        seen: set[
            Tuple[str, str]
        ] = set()

        for sentence in self._sentences(
            description
        ):
            match = (
                french_pattern.search(
                    sentence
                )
                or english_pattern.search(
                    sentence
                )
            )

            if not match:
                continue

            raw_actor = clean_text(
                match.group(1)
            )

            role = self._marketplace_side_role(
                raw_actor
            )

            # A declaration of a "side" does not by itself prove
            # which economic role that side plays.
            if role not in {
                ActorRole.PROVIDER,
                ActorRole.BUYER,
            }:
                continue

            name = self._marketplace_side_actor_name(
                raw_actor
            )

            key = comparison_key(
                name
            )

            if not name or not key:
                continue

            identity = (
                key,
                role.value,
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            output.append(
                (
                    name,
                    role,
                )
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
            ],
            ...,
        ] = (
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
            ),
        )

        patterns: Tuple[
            Tuple[
                re.Pattern[str],
                ActorRole,
                bool,
            ],
            ...,
        ] = (
            *primary_user_patterns,
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
        patterns: Tuple[
            Tuple[re.Pattern[str], ActorRole],
            ...,
        ] = (
            (
                re.compile(
                    r"\b(?:the\s+)?"
                    r"(?:main|primary)\s+"
                    r"operational\s+user\s+"
                    r"(?:"
                    r"is"
                    r"|would(?:\s+(?:probably|likely|typically))?\s+be"
                    r"|will\s+be"
                    r")\s+"
                    r"(.+?)"
                    r"(?="
                    r"\s+(?:responsible\s+for|in\s+charge\s+of)\b"
                    r"|,\s*(?:but|however|although)\b"
                    r"|[.;]"
                    r"|$"
                    r")",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
            ),
            (
                re.compile(
                    r"\b(?:utilisateur|usager)\s+"
                    r"op(?:e|\u00e9)rationnel\s+"
                    r"(?:principal\s+)?"
                    r"(?:est|serait|sera)"
                    r"(?:\s+(?:probablement|vraisemblablement))?"
                    r"\s+(.+?)"
                    r"(?="
                    r"\s+(?:responsable\s+de|charg(?:e|\u00e9)e?\s+de)\b"
                    r"|,\s*(?:mais|cependant)\b"
                    r"|[.;]"
                    r"|$"
                    r")",
                    re.IGNORECASE,
                ),
                ActorRole.USER,
            ),
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
                re.compile(
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
                ),
                ActorRole.PAYER,
            ),
            (
                re.compile(
                    r"^\s*(?:the\s+)?"
                    r"(.+?)\s+"
                    r"(?:"
                    r"pay"
                    r"|pays"
                    r"|paid"
                    r"|will\s+pay"
                    r"|would\s+pay"
                    r"|is\s+paying"
                    r"|are\s+paying"
                    r"|has\s+paid"
                    r"|have\s+paid"
                    r")\b"
                    r"(?:\s+.+?)?"
                    r"(?=[.;]|$)",
                    re.IGNORECASE,
                ),
                ActorRole.PAYER,
            ),
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

            for pattern, role in patterns:
                match = pattern.search(
                    relation_sentence
                )

                if not match:
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
                        match.group(1)
                    ]
                )

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
                        next_start = (
                            next_occurrence[
                                "match"
                            ].start()
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
                        ),
                        "explicit": explicit,
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

        for index, sentence in enumerate(
            sentences
        ):
            if self._workflow_sentence_is_non_action_context(
                sentence
            ):
                continue

            if self._is_problem_sentence(
                sentence
            ):
                continue

            add_candidates(
                sentence,
                index=index,
                explicit=True,
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
                    r"|\bapprouv"
                    r"(?:er|e|\u00e9|ent|ait|ant)?\b",
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

        output: List[
            Dict[str, Any]
        ] = []

        occupied: List[
            Tuple[int, int]
        ] = []

        for item in raw:
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


    def _transaction_action_candidate(
        self,
        sentence: str,
        pattern: re.Pattern[str],
    ) -> re.Match[str] | None:
        """
        Return a usable transaction-action match only when the sentence
        is positive operational evidence.
        """
        # Transaction heuristics must consume the canonical
        # scope-polarity authority rather than independently
        # reinterpret MVP / exclusion language.
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

        These predicates represent an operational start of an
        exchange. Generic solution mechanisms such as connecting
        two sides are deliberately excluded.
        """
        return (
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
                    r"|\bd\u00e9pos(?:er|e|ent)?\b",
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

    def _explicit_transaction_flow_bounds(
        self,
        sentences: Sequence[str],
    ) -> Tuple[str, str]:
        """
        Resolve explicit transaction-flow boundaries conservatively.

        The explicitly declared transaction unit remains authoritative
        for the exchanged object/value.

        Separate explicit operational statements may establish a
        transaction start and lifecycle completion.
        """
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

        completion_action = ""

        completion_location: (
            Tuple[int, int]
            | None
        ) = None

        # Latest explicit lifecycle completion wins.
        for sentence_index, sentence in enumerate(
            sentences
        ):
            sentence_text = clean_text(
                sentence
            )

            if not sentence_text:
                continue

            if self._is_scope_only(
                sentence_text
            ):
                continue

            if self._is_problem_sentence(
                sentence_text
            ):
                continue

            if (
                self._workflow_sentence_is_non_action_context(
                    sentence_text
                )
            ):
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

                    location = (
                        sentence_index,
                        match.start(),
                    )

                    if (
                        completion_location is None
                        or location
                        > completion_location
                    ):
                        completion_location = (
                            location
                        )

                        completion_action = (
                            action
                        )

        initiation_action = ""

        # Earliest valid transaction initiation before completion.
        for sentence_index, sentence in enumerate(
            sentences
        ):
            sentence_text = clean_text(
                sentence
            )

            if not sentence_text:
                continue

            if (
                completion_location
                and sentence_index
                > completion_location[0]
            ):
                break

            if self._is_problem_sentence(
                sentence_text
            ):
                continue

            if (
                self._workflow_sentence_is_non_action_context(
                    sentence_text
                )
            ):
                continue

            for pattern, action in (
                self._transaction_initiation_patterns()
            ):
                match = (
                    self._transaction_action_candidate(
                        sentence_text,
                        pattern,
                    )
                )

                if match is None:
                    continue

                if (
                    completion_location
                    and sentence_index
                    == completion_location[0]
                    and match.start()
                    >= completion_location[1]
                ):
                    continue

                initiation_action = (
                    action
                )

                break

            if initiation_action:
                break

        return (
            initiation_action,
            completion_action,
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

        initiation_patterns = (
            self._transaction_initiation_patterns()
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
                match = (
                    self._transaction_action_candidate(
                        sentence,
                        pattern,
                    )
                )

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
                match = (
                    self._transaction_action_candidate(
                        sentence,
                        pattern,
                    )
                )

                if not match:
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
