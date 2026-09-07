from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

from app.services.domain_integrity_guard import normalize_output_language
from app.services.scope_polarity import partition_scope_sections


@dataclass(frozen=True)
class ArchetypeProfile:
    code: str
    business_motion: str
    interaction_model: str
    validation_unit_en: str
    validation_unit_fr: str


class ProjectArchetypeResolver:
    """Resolve a project into an operational archetype before downstream agents.

    The resolver is deliberately deterministic and domain-agnostic. It does not
    invent market facts. It maps the user idea to the most useful analysis lens
    (B2B workflow, marketplace, consumer transaction, hardware/IoT, etc.) and
    exposes actors, core actions, search phrases, metrics and risks.
    """

    PROFILES = {
        "two_sided_marketplace": ArchetypeProfile(
            "two_sided_marketplace", "b2b2c", "two_sided",
            "core transaction", "transaction principale",
        ),
        "consumer_transactional_app": ArchetypeProfile(
            "consumer_transactional_app", "b2c", "single_sided_transaction",
            "core transaction", "transaction principale",
        ),
        "b2b_workflow_saas": ArchetypeProfile(
            "b2b_workflow_saas", "b2b", "workflow",
            "core workflow", "workflow principal",
        ),
        "ecommerce": ArchetypeProfile(
            "ecommerce", "b2c", "commerce",
            "purchase journey", "parcours d’achat",
        ),
        "hardware_iot": ArchetypeProfile(
            "hardware_iot", "b2b", "device_operation",
            "field operation", "opération terrain",
        ),
        "analytics_ai_tool": ArchetypeProfile(
            "analytics_ai_tool", "b2b", "analysis_workflow",
            "analysis workflow", "workflow d’analyse",
        ),
        "content_community": ArchetypeProfile(
            "content_community", "b2c", "engagement",
            "engagement loop", "boucle d’engagement",
        ),
        "regulated_service": ArchetypeProfile(
            "regulated_service", "b2b2c", "regulated_workflow",
            "regulated service journey", "parcours de service réglementé",
        ),
        "generic_digital_product": ArchetypeProfile(
            "generic_digital_product", "unknown", "generic",
            "core user action", "action utilisateur principale",
        ),
    }

    MARKETPLACE_SIGNALS = {
        "marketplace", "two-sided marketplace", "two sided marketplace",
        "plateforme", "platform", "two-sided", "two sided",
        "place de marche", "place de marché", "mise en relation",
        "met en relation", "mettre en relation", "relie", "relier",
        "connecte", "connectent", "connect", "connects", "connecting",
        "connecter", "matching", "match", "commission",
        "provider", "providers", "prestataire", "prestataires",
        "seller", "sellers", "vendeur", "vendeurs",
        "buyer", "buyers", "acheteur", "acheteurs",
        "driver", "drivers", "chauffeur", "chauffeurs",
        "passenger", "passengers", "passager", "passagers",
        "recruiter", "recruiters", "recruteur", "recruteurs",
        "company publish", "companies publish", "entreprise publie",
        "entreprises publient", "publish offers", "publier des offres",
    }
    TRANSACTION_SIGNALS = {
        "book", "booking", "reserve", "reservation", "réserver", "reservation",
        "order", "commander", "pay", "payer", "purchase", "acheter", "request",
        "demander", "ride", "course", "trip", "trajet", "appointment", "rendez vous",
    }
    B2B_WORKFLOW_SIGNALS = {
        "dashboard", "records", "record", "reporting", "export", "exports", "admin",
        "saas", "manager", "managers", "supervisor", "hr", "employee", "attendance", "shift",
        "workflow", "process", "gestion", "planning", "présence", "presence",
        "congé", "conge", "dossier", "dossiers", "suivi", "saisie", "excel", "spreadsheet",
    }
    HARDWARE_SIGNALS = {
        "robot", "sensor", "capteur", "camera", "caméra", "iot", "device",
        "hardware", "raspberry", "esp32", "stm32", "lidar", "motor", "moteur",
        "drone", "embedded", "embarque", "embarqué", "prototype physique",
    }
    AI_SIGNALS = {
        "artificial intelligence", "intelligence artificielle", " ai ", "machine learning",
        "computer vision", "vision par ordinateur", "predict", "prédire", "predire",
        "detect", "détecter", "detecter", "generate", "générer", "generer",
        "analytics", "analyse automatique", "classifier", "classification",
    }
    CONTENT_SIGNALS = {
        "community", "communauté", "communaute", "social network", "réseau social",
        "reseau social", "content", "contenu", "creator", "créateur", "createur",
        "forum", "newsletter", "media", "média", "blog", "followers",
    }
    COMMERCE_SIGNALS = {
        "ecommerce", "e-commerce", "online store", "boutique en ligne", "cart",
        "panier", "product catalog", "catalogue produits", "checkout", "livraison",
        "delivery", "retail", "commerce", "shop", "store", "magasin",
    }
    REGULATED_SIGNALS = {
        "health", "medical", "patient", "doctor", "clinic", "santé", "sante",
        "médecin", "medecin", "clinique", "finance", "bank", "banque", "insurance",
        "assurance", "legal", "juridique", "law", "avocat", "pharmacy", "pharmacie",
    }

    VERTICALS: Dict[str, Dict[str, Any]] = {
        "mobility_taxi": {
            "signals": {
                "taxi", "cab", "chauffeur", "driver", "passenger", "passager",
                "ride hailing", "ride-hailing", "e hailing", "e-hailing", "course taxi",
                "transport urbain", "urban mobility", "pickup", "prise en charge",
                "destination", "trajet", "ride booking", "taxi booking",
            },
            "identity_signals": {
                'course taxi',
                'e hailing',
                'e-hailing',
                'ride hailing',
                'ride-hailing',
                'taxi',
                'taxi booking',
            },
            "actors_en": ["Passenger seeking a ride", "Taxi driver", "Taxi fleet or platform operator"],
            "actors_fr": ["Passager cherchant un taxi", "Chauffeur de taxi", "Exploitant de flotte ou opérateur de plateforme"],
            "workflows_en": [
                "book a taxi by pickup area and destination",
                "accept and complete a relevant ride request",
                "monitor coverage, cancellations and service quality",
            ],
            "workflows_fr": [
                "réserver un taxi selon la zone de prise en charge et la destination",
                "accepter et réaliser une demande de course pertinente",
                "suivre la couverture, les annulations et la qualité de service",
            ],
            "search_terms": [
                "taxi booking app", "ride hailing", "e hailing", "taxi dispatch software",
                "application reservation taxi", "application réservation taxi",
                "commande taxi", "mise en relation taxi chauffeur",
            ],
            "queries_en": [
                "taxi booking app Tunisia", "ride hailing Tunisia", "e hailing taxi Tunisia",
                "taxi dispatch platform Tunisia", "online taxi reservation Tunisia",
            ],
            "queries_fr": [
                "application réservation taxi Tunisie", "commander taxi application Tunisie",
                "plateforme mise en relation taxi chauffeur Tunisie",
                "réservation taxi en ligne Tunisie", "application mobilité urbaine taxi Tunisie",
            ],
            "monetization_en": "commission or service fee per completed ride, with optional driver or fleet plans",
            "monetization_fr": "commission ou frais de service par course réalisée, avec des offres optionnelles pour chauffeurs ou flottes",
            "metrics_en": ["successful ride match rate", "median pickup time", "ride completion rate", "repeat passengers", "active drivers by zone"],
            "metrics_fr": ["taux de mise en relation réussie", "temps médian de prise en charge", "taux de courses réalisées", "passagers récurrents", "chauffeurs actifs par zone"],
            "risks_en": ["insufficient driver liquidity by zone and time", "regulatory constraints", "passenger and driver safety", "cancellations and no-shows", "unit economics after driver incentives"],
            "risks_fr": ["offre insuffisante de chauffeurs selon la zone et l’heure", "contraintes réglementaires", "sécurité des passagers et chauffeurs", "annulations et absences", "économie unitaire après incitations chauffeurs"],
        },
        "internship_jobs": {
            "signals": {
                "internship", "internships", "stage", "stages", "student", "students",
                "étudiant", "etudiant", "étudiants", "etudiants", "cv", "resume",
                "recruiter", "recruteur", "job offer", "offre de stage", "offres de stage",
            },
            "actors_en": ["Student looking for an internship", "Company recruiter or internship manager", "University career-service partner"],
            "actors_fr": ["Étudiant cherchant un stage", "Recruteur ou responsable de stages en entreprise", "Service carrière d’un établissement"],
            "workflows_en": ["search and apply for a relevant internship", "publish and review internship applications", "verify offer quality and placement outcomes"],
            "workflows_fr": ["chercher et candidater à un stage pertinent", "publier une offre et examiner les candidatures", "vérifier la qualité des offres et les résultats de placement"],
            "search_terms": ["internship platform", "internship job board", "student recruitment platform", "plateforme stages", "offres de stage étudiants"],
            "queries_en": ["internship platform Tunisia", "student internship job board Tunisia", "companies publish internship offers Tunisia"],
            "queries_fr": ["plateforme stages étudiants Tunisie", "offres de stage entreprises Tunisie", "site recrutement stages Tunisie"],
            "monetization_en": "employer listing fees, recruitment subscriptions or sponsored placement services",
            "monetization_fr": "frais de publication pour les entreprises, abonnements de recrutement ou services de placement sponsorisés",
            "metrics_en": ["qualified applications per offer", "time to first application", "placement rate", "active employers", "repeat employer postings"],
            "metrics_fr": ["candidatures qualifiées par offre", "temps avant la première candidature", "taux de placement", "entreprises actives", "publications répétées des employeurs"],
            "risks_en": ["low-quality or duplicate offers", "insufficient employer supply", "student trust and fraud", "seasonality", "weak placement outcomes"],
            "risks_fr": ["offres faibles ou dupliquées", "offre insuffisante d’entreprises", "confiance des étudiants et fraude", "saisonnalité", "résultats de placement faibles"],
        },
        "workforce": {
            "signals": {'workforce', 'shift', 'attendance', 'leave request', 'pr\xe9sence', 'presence', 'cong\xe9', 'conge', 'employee scheduling', 'employee schedule', 'planning du personnel'},
            "actors_en": ["Shift supervisor or HR assistant", "SME owner or HR manager", "Employee or team lead"],
            "actors_fr": ["Superviseur de planning ou assistant RH", "Dirigeant de PME ou responsable RH", "Employé ou chef d’équipe"],
            "workflows_en": ["create weekly shift schedules", "record attendance", "manage leave requests", "export monthly payroll preparation data"],
            "workflows_fr": ["créer le planning hebdomadaire des équipes", "enregistrer les présences", "gérer les demandes de congé", "exporter les données mensuelles pour la préparation de la paie"],
            "search_terms": ["workforce scheduling", "employee scheduling", "shift planning", "attendance tracking", "gestion planning personnel"],
            "queries_en": ["workforce scheduling software Tunisia", "employee scheduling attendance Tunisia"],
            "queries_fr": ["logiciel planning personnel Tunisie", "gestion horaires présence employés Tunisie"],
            "monetization_en": "monthly subscription based on active employees or organization size",
            "monetization_fr": "abonnement mensuel selon le nombre d’employés actifs ou la taille de l’organisation",
            "metrics_en": ["schedule preparation time", "attendance completeness", "weekly active managers", "employee acknowledgment rate"],
            "metrics_fr": ["temps de préparation des plannings", "complétude des présences", "responsables actifs chaque semaine", "taux d’accusé de réception des employés"],
            "risks_en": ["duplicate entry", "poor employee adoption", "payroll integration complexity", "support cost"],
            "risks_fr": ["double saisie", "faible adoption des employés", "complexité d’intégration paie", "coût de support"],
        },
    }

    ACTOR_TERMS = {
        "client": ("Customer", "Client"),
        "clients": ("Customers", "Clients"),
        "passager": ("Passenger", "Passager"),
        "passagers": ("Passengers", "Passagers"),
        "chauffeur": ("Driver", "Chauffeur"),
        "chauffeurs": ("Drivers", "Chauffeurs"),
        "driver": ("Driver", "Chauffeur"),
        "drivers": ("Drivers", "Chauffeurs"),
        "student": ("Student", "Étudiant"),
        "students": ("Students", "Étudiants"),
        "etudiant": ("Student", "Étudiant"),
        "etudiants": ("Students", "Étudiants"),
        "étudiant": ("Student", "Étudiant"),
        "étudiants": ("Students", "Étudiants"),
        "company": ("Company", "Entreprise"),
        "companies": ("Companies", "Entreprises"),
        "entreprise": ("Company", "Entreprise"),
        "entreprises": ("Companies", "Entreprises"),
        "employee": ("Employee", "Employé"),
        "employees": ("Employees", "Employés"),
        "employe": ("Employee", "Employé"),
        "employes": ("Employees", "Employés"),
        "manager": ("Manager", "Responsable"),
        "managers": ("Managers", "Responsables"),
        "farmer": ("Farmer", "Agriculteur"),
        "farmers": ("Farmers", "Agriculteurs"),
        "patient": ("Patient", "Patient"),
        "patients": ("Patients", "Patients"),
        "doctor": ("Doctor", "Médecin"),
        "doctors": ("Doctors", "Médecins"),
        "seller": ("Seller", "Vendeur"),
        "sellers": ("Sellers", "Vendeurs"),
        "buyer": ("Buyer", "Acheteur"),
        "buyers": ("Buyers", "Acheteurs"),
        "provider": ("Service provider", "Prestataire"),
        "providers": ("Service providers", "Prestataires"),
    }

    ACTION_PATTERNS = [
        (r"\b(?:réserver|reserver)\s+(?:un|une|des)?\s*([a-zà-ÿ0-9 -]{2,45})", "book", "réserver"),
        (r"\bbook\s+(?:a|an|the)?\s*([a-z0-9 -]{2,45})", "book", "réserver"),
        (r"\b(?:trouver|chercher)\s+([a-zà-ÿ0-9 -]{2,45})", "find", "trouver"),
        (r"\b(?:find|search for)\s+([a-z0-9 -]{2,45})", "find", "trouver"),
        (r"\b(?:publier|poster)\s+([a-zà-ÿ0-9 -]{2,45})", "publish", "publier"),
        (r"\b(?:publish|post)\s+([a-z0-9 -]{2,45})", "publish", "publier"),
        (r"\b(?:suivre|gérer|gerer)\s+([a-zà-ÿ0-9 -]{2,45})", "manage", "gérer"),
        (r"\b(?:track|manage)\s+([a-z0-9 -]{2,45})", "manage", "gérer"),
    ]

    def resolve(
        self,
        *,
        title: str = "",
        description: str = "",
        industry: str = "",
        target_region: str = "",
        output_language: str = "fr",
        target_users: Sequence[str] | None = None,
        problem: str = "",
        solution: str = "",
        business_model: str = "",
        workflows: Sequence[str] | None = None,
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)

        # Canonical scope-polarity authority owns the semantic boundary.
        #
        # Explicitly excluded MVP capabilities may remain useful as
        # negative project truth, but they must never become positive
        # archetype, vertical or search identity signals.
        positive_description, _ = (
            partition_scope_sections(
                description
            )
        )

        text = self._normalize(" ".join([
            title, positive_description, industry, problem, solution, business_model,
            " ".join(target_users or []), " ".join(workflows or []),
        ]))

        vertical, vertical_score = self._detect_vertical(text)
        (
            archetype,
            secondary_archetypes,
            archetype_scores,
            signals,
        ) = self._detect_archetype(
            text,
            vertical,
        )
        profile = self.PROFILES[archetype]
        vertical_profile = self.VERTICALS.get(vertical, {})

        # The resolver preserves caller-provided actors and workflows only.
        # Actor roles and transaction semantics belong to the canonical
        # ProjectContextExtractor, never to this service.
        explicit_actors = self._explicit_values(
            target_users or [],
            maximum=8,
        )
        explicit_workflows = self._explicit_values(
            workflows or [],
            maximum=8,
        )
        search_terms = self._search_terms(
            text=text,
            vertical=vertical,
            vertical_profile=vertical_profile,
            industry=industry,
        )
        search_queries = self._queries(
            vertical_profile=vertical_profile,
            search_terms=search_terms,
            target_region=target_region,
            language=language,
        )
        metrics = self._localized(
            vertical_profile.get("metrics_en"),
            vertical_profile.get("metrics_fr"),
            language,
        )
        risks = self._localized(
            vertical_profile.get("risks_en"),
            vertical_profile.get("risks_fr"),
            language,
        )

        if not metrics:
            metrics = self._default_metrics(
                archetype,
                language,
            )
        if not risks:
            risks = self._default_risks(
                archetype,
                language,
            )

        # Preserve only an explicit business model. The resolver must not
        # manufacture monetization and then present it as project context.
        monetization = self._compact_explicit_monetization(
            business_model,
            language,
        )

        confidence = self._archetype_confidence(
            archetype=archetype,
            archetype_scores=archetype_scores,
            vertical_score=vertical_score,
            has_explicit_actors=bool(explicit_actors),
            has_explicit_workflows=bool(explicit_workflows),
            search_terms=search_terms,
        )

        validation_unit = (
            profile.validation_unit_en
            if language == "en"
            else profile.validation_unit_fr
        )
        core_action = (
            explicit_workflows[0]
            if explicit_workflows
            else ""
        )

        return {
            "format": "project_archetype_v2_authority_limited",
            "project_archetype": archetype,
            "primary_archetype": archetype,
            "secondary_archetypes": secondary_archetypes,
            "archetype_scores": archetype_scores,
            "vertical": vertical or "general",
            "business_motion": profile.business_motion,
            "interaction_model": profile.interaction_model,
            "validation_unit": validation_unit,
            "actors": {
                "demand_side": "",
                "supply_side": "",
                "operator_or_partner": "",
                "payer": "",
                "explicit_targets": explicit_actors,
            },
            "target_users": explicit_actors,
            "priority_workflows": explicit_workflows,
            "core_action": core_action,
            "business_model_hypothesis": monetization,
            "success_metrics": metrics,
            "risk_dimensions": risks,
            "evidence_needs": self._evidence_needs(
                archetype,
                language,
            ),
            "search_terms": search_terms,
            "search_queries": search_queries,
            "signals": signals,
            "confidence": confidence,
            "archetype_confidence": confidence,
            "output_language": language,
            "authority": {
                "detects_archetype": True,
                "builds_project_context_packet": False,
                "resolves_actor_roles": False,
                "invents_workflows": False,
                "decides_readiness": False,
            },
            "non_authoritative_fields": [
                "success_metrics",
                "risk_dimensions",
                "evidence_needs",
                "search_terms",
                "search_queries",
            ],
        }

    def _detect_vertical(self, text: str) -> tuple[str, int]:
        best_name = ""
        best_score = 0
        for name, profile in self.VERTICALS.items():
            identity_signals = profile.get("identity_signals", profile.get("signals", set()))
            score = sum(1 for term in identity_signals if self._term_in_text(term, text))
            if score > best_score:
                best_name = name
                best_score = score
        return best_name, best_score

    def _detect_archetype(
        self,
        text: str,
        vertical: str,
    ) -> tuple[
        str,
        List[str],
        Dict[str, int],
        List[str],
    ]:
        scores = {
            "two_sided_marketplace": self._score(
                text,
                self.MARKETPLACE_SIGNALS,
            ),
            "consumer_transactional_app": self._score(
                text,
                self.TRANSACTION_SIGNALS,
            ),
            "b2b_workflow_saas": self._score(
                text,
                self.B2B_WORKFLOW_SIGNALS,
            ),
            "hardware_iot": self._score(
                text,
                self.HARDWARE_SIGNALS,
            ),
            "analytics_ai_tool": self._score(
                text,
                self.AI_SIGNALS,
            ),
            "content_community": self._score(
                text,
                self.CONTENT_SIGNALS,
            ),
            "ecommerce": self._score(
                text,
                self.COMMERCE_SIGNALS,
            ),
            "regulated_service": self._score(
                text,
                self.REGULATED_SIGNALS,
            ),
        }

        # Vertical profiles may strengthen archetype detection, but they do not
        # inject their actors or workflows into the project context.
        if vertical in {
            "mobility_taxi",
            "internship_jobs",
        }:
            scores[
                "two_sided_marketplace"
            ] += 4

        if vertical == "workforce":
            scores[
                "b2b_workflow_saas"
            ] += 4

        # Historical eligibility thresholds remain the admission policy.
        #
        # Once admitted, however, the resolver's own published scores are
        # the primary authority. The previous priority ladder could select
        # a low-score archetype merely because it crossed its threshold
        # first.
        #
        # Historical order is retained only as a deterministic tie policy.
        selection_order = (
            "hardware_iot",
            "two_sided_marketplace",
            "ecommerce",
            "regulated_service",
            "b2b_workflow_saas",
            "consumer_transactional_app",
            "analytics_ai_tool",
            "content_community",
        )

        eligible = {
            "hardware_iot":
                scores["hardware_iot"] >= 2,

            "two_sided_marketplace":
                scores["two_sided_marketplace"] >= 3,

            "ecommerce":
                scores["ecommerce"] >= 3,

            "regulated_service":
                (
                    scores["regulated_service"] >= 3
                    and scores[
                        "consumer_transactional_app"
                    ] >= 1
                ),

            "b2b_workflow_saas":
                scores["b2b_workflow_saas"] >= 3,

            "consumer_transactional_app":
                scores[
                    "consumer_transactional_app"
                ] >= 2,

            "analytics_ai_tool":
                scores["analytics_ai_tool"] >= 2,

            "content_community":
                scores["content_community"] >= 2,
        }

        eligible_archetypes = [
            name
            for name in selection_order
            if eligible[name]
        ]

        if eligible_archetypes:

            dominant_score = max(
                scores[name]
                for name in eligible_archetypes
            )

            selected = next(
                name
                for name in selection_order
                if (
                    eligible[name]
                    and scores[name]
                    ==
                    dominant_score
                )
            )

        else:

            selected = "generic_digital_product"

        primary_score = (
            scores.get(
                selected,
                0,
            )
            if selected
            != "generic_digital_product"
            else 0
        )
        secondary_threshold = max(
            2,
            int(
                round(
                    primary_score * 0.45
                )
            ),
        )
        secondary_archetypes = [
            name
            for name, value in sorted(
                scores.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
            if (
                name != selected
                and value >= secondary_threshold
            )
        ][:3]

        signals = [
            f"{name}:{value}"
            for name, value in scores.items()
            if value > 0
        ]

        return (
            selected,
            secondary_archetypes,
            {
                name: value
                for name, value in scores.items()
                if value > 0
            },
            signals,
        )

    def _archetype_confidence(
        self,
        *,
        archetype: str,
        archetype_scores: Dict[str, int],
        vertical_score: int,
        has_explicit_actors: bool,
        has_explicit_workflows: bool,
        search_terms: Sequence[str],
    ) -> float:
        if archetype == "generic_digital_product":
            return 0.40

        primary_score = float(
            archetype_scores.get(
                archetype,
                0,
            )
        )
        next_score = max(
            (
                float(value)
                for name, value
                in archetype_scores.items()
                if name != archetype
            ),
            default=0.0,
        )
        margin = max(
            0.0,
            primary_score - next_score,
        )

        confidence = 0.40
        confidence += min(
            0.20,
            primary_score * 0.04,
        )
        confidence += min(
            0.12,
            margin * 0.03,
        )
        confidence += min(
            0.08,
            vertical_score * 0.02,
        )
        confidence += (
            0.04
            if has_explicit_actors
            else 0.0
        )
        confidence += (
            0.04
            if has_explicit_workflows
            else 0.0
        )
        confidence += (
            0.04
            if len(search_terms) >= 2
            else 0.0
        )

        return round(
            min(
                0.94,
                confidence,
            ),
            2,
        )

    def _actors(
        self,
        *,
        text: str,
        vertical_profile: Dict[str, Any],
        explicit: List[str],
        language: str,
        archetype: str,
    ) -> List[str]:
        vertical = self._localized(vertical_profile.get("actors_en"), vertical_profile.get("actors_fr"), language)
        if vertical:
            return self._unique(vertical)[:3]

        cleaned_explicit = [self._clean_actor(item) for item in explicit if self._clean_actor(item)]
        if cleaned_explicit:
            return self._unique(cleaned_explicit)[:3]

        found: List[str] = []
        for term, labels in self.ACTOR_TERMS.items():
            if self._term_in_text(term, text):
                found.append(labels[0] if language == "en" else labels[1])

        if archetype == "two_sided_marketplace":
            defaults = self._t_list(
                language,
                ["Demand-side customer", "Supply-side provider", "Platform operator or partner"],
                ["Client côté demande", "Prestataire côté offre", "Opérateur ou partenaire de la plateforme"],
            )
        elif archetype == "hardware_iot":
            defaults = self._t_list(
                language,
                ["Field operator", "Operational buyer", "Technical maintainer"],
                ["Opérateur terrain", "Acheteur opérationnel", "Responsable maintenance technique"],
            )
        elif archetype == "b2b_workflow_saas":
            defaults = self._t_list(
                language,
                ["Daily operational user", "Budget owner", "Adoption gatekeeper"],
                ["Utilisateur opérationnel quotidien", "Détenteur du budget", "Responsable de l’adoption"],
            )
        else:
            defaults = self._t_list(
                language,
                ["Primary user", "Paying customer", "Operational partner"],
                ["Utilisateur principal", "Client payeur", "Partenaire opérationnel"],
            )

        for item in defaults:
            if len(found) >= 3:
                break
            found.append(item)
        return self._unique(found)[:3]

    def _workflows(
        self,
        *,
        text: str,
        vertical_profile: Dict[str, Any],
        explicit: List[str],
        language: str,
        archetype: str,
    ) -> List[str]:
        vertical = self._localized(vertical_profile.get("workflows_en"), vertical_profile.get("workflows_fr"), language)
        if vertical:
            return self._unique(vertical)[:4]

        result = [self._clean_workflow(item) for item in explicit if self._clean_workflow(item)]
        for pattern, verb_en, verb_fr in self.ACTION_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            obj = self._clean_workflow_object(match.group(1))
            if not obj:
                continue
            verb = verb_en if language == "en" else verb_fr
            result.append(f"{verb} {obj}")

        defaults = {
            "two_sided_marketplace": self._t_list(
                language,
                ["complete the core demand-side transaction", "fulfil a relevant request", "monitor matching quality and trust"],
                ["réaliser la transaction principale côté demande", "répondre à une demande pertinente", "suivre la qualité de mise en relation et la confiance"],
            ),
            "consumer_transactional_app": self._t_list(
                language,
                ["complete the core transaction", "receive confirmation and status updates", "resolve a failed transaction"],
                ["réaliser la transaction principale", "recevoir la confirmation et le suivi", "résoudre une transaction échouée"],
            ),
            "hardware_iot": self._t_list(
                language,
                ["complete the primary field operation", "review device output", "maintain and recover the device"],
                ["réaliser l’opération terrain principale", "consulter le résultat du dispositif", "maintenir et remettre en service le dispositif"],
            ),
            "b2b_workflow_saas": self._t_list(
                language,
                ["complete the primary operational workflow", "review and consolidate results", "onboard users without duplicate work"],
                ["réaliser le workflow opérationnel principal", "contrôler et consolider les résultats", "intégrer les utilisateurs sans double saisie"],
            ),
        }
        for item in defaults.get(archetype, self._t_list(
            language,
            ["complete the core user action", "review the result", "recover from a failed action"],
            ["réaliser l’action utilisateur principale", "consulter le résultat", "reprendre après un échec"],
        )):
            if len(result) >= 3:
                break
            result.append(item)
        return self._unique(result)[:4]

    def _search_terms(
        self,
        *,
        text: str,
        vertical: str,
        vertical_profile: Dict[str, Any],
        industry: str,
    ) -> List[str]:
        terms = list(vertical_profile.get("search_terms") or [])
        industry_terms = [
            token for token in self._tokens(self._normalize(industry))
            if token not in {"technology", "technologie", "digital", "application", "app", "saas"}
        ]
        if industry_terms:
            terms.append(" ".join(industry_terms[:3]))

        if not terms:
            action_terms = []
            for pattern, _, _ in self.ACTION_PATTERNS:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    action_terms.append(self._clean_workflow_object(match.group(1)))
            terms.extend(action_terms)

        if vertical:
            terms.append(vertical.replace("_", " "))
        return self._unique([item for item in terms if item])[:20]

    def _queries(
        self,
        *,
        vertical_profile: Dict[str, Any],
        search_terms: List[str],
        target_region: str,
        language: str,
    ) -> Dict[str, List[str]]:
        fr = list(vertical_profile.get("queries_fr") or [])
        en = list(vertical_profile.get("queries_en") or [])
        region = target_region or ("Tunisia" if language == "en" else "Tunisie")
        primary = search_terms[0] if search_terms else "digital product"
        if not fr:
            fr = [f"{primary} {region}", f"concurrents {primary} {region}"]
        if not en:
            en = [f"{primary} {region}", f"{primary} competitors {region}"]
        return {
            "local_fr": self._unique(fr)[:6],
            "local_en": self._unique(en)[:6],
            "all": self._unique(fr + en)[:10],
        }

    def _monetization(self, vertical_profile: Dict[str, Any], archetype: str, explicit: str, language: str) -> str:
        compact_explicit = self._compact_explicit_monetization(explicit, language)
        if compact_explicit:
            return compact_explicit
        vertical = vertical_profile.get("monetization_en") if language == "en" else vertical_profile.get("monetization_fr")
        if vertical:
            return str(vertical)
        defaults = {
            "two_sided_marketplace": self._t(language, "commission or service fee per completed transaction", "commission ou frais de service par transaction réalisée"),
            "consumer_transactional_app": self._t(language, "transaction fee, subscription or freemium plan to validate", "frais de transaction, abonnement ou offre freemium à valider"),
            "b2b_workflow_saas": self._t(language, "monthly subscription based on organization size or usage", "abonnement mensuel selon la taille de l’organisation ou l’usage"),
            "hardware_iot": self._t(language, "hardware sale or lease plus optional recurring software and support", "vente ou location du matériel avec logiciel et support récurrents optionnels"),
            "ecommerce": self._t(language, "product margin, delivery fee or marketplace commission", "marge produit, frais de livraison ou commission marketplace"),
            "content_community": self._t(language, "membership, sponsorship, advertising or premium content", "adhésion, sponsoring, publicité ou contenu premium"),
        }
        return defaults.get(archetype, self._t(language, "pricing model to validate", "modèle de revenus à valider"))


    def _compact_explicit_monetization(self, explicit: str, language: str) -> str:
        """Keep only a real revenue hypothesis, never the whole idea sentence."""
        value = re.sub(r"\s+", " ", str(explicit or "")).strip(" .;,")
        if len(value) < 4:
            return ""

        normalized = self._normalize(value)
        markers = (
            "commission", "frais", "abonnement", "subscription", "fee",
            "licence", "license", "marge", "margin", "vente", "sale",
            "location", "lease", "publicite", "advertising", "sponsoring",
        )
        if not any(self._term_in_text(marker, normalized) for marker in markers):
            return ""

        # A clean short value can be preserved as written by the user.
        if len(value.split()) <= 16 and len(value) <= 140:
            return value

        patterns = (
            r"(?:commission|frais(?: de service)?|abonnement|subscription|transaction fee|service fee|licen[cs]e|marge|margin|vente|sale|location|lease|publicit[eé]|advertising|sponsoring)[^.;]{0,110}",
        )
        for pattern in patterns:
            match = re.search(pattern, value, flags=re.IGNORECASE)
            if match:
                candidate = re.sub(r"\s+", " ", match.group(0)).strip(" .;,")
                if 2 <= len(candidate.split()) <= 18:
                    return candidate

        # Long multi-purpose text is not a monetization hypothesis. Let the
        # archetype/vertical default provide a concise professional model.
        return ""

    def _payer(self, archetype: str, demand: str, supply: str, operator: str, language: str) -> str:
        if archetype in {"two_sided_marketplace", "consumer_transactional_app", "ecommerce"}:
            return demand
        if archetype == "hardware_iot":
            return operator or self._t(language, "Operational buyer", "Acheteur opérationnel")
        return supply or operator or demand

    def _default_metrics(self, archetype: str, language: str) -> List[str]:
        mapping = {
            "two_sided_marketplace": (
                ["transaction completion rate", "time to match", "active supply", "repeat demand", "contribution margin per transaction"],
                ["taux de transactions réalisées", "temps de mise en relation", "offre active", "demande récurrente", "marge contributive par transaction"],
            ),
            "hardware_iot": (
                ["task success rate", "measurement accuracy", "uptime", "maintenance time", "cost per deployed unit"],
                ["taux de réussite de la tâche", "précision des mesures", "disponibilité", "temps de maintenance", "coût par unité déployée"],
            ),
            "b2b_workflow_saas": (
                ["activation", "time saved", "weekly active users", "retention", "support cost"],
                ["activation", "temps gagné", "utilisateurs actifs hebdomadaires", "rétention", "coût de support"],
            ),
        }
        values = mapping.get(archetype, (
            ["activation", "successful core action", "repeat usage", "conversion", "support incidents"],
            ["activation", "action principale réussie", "usage répété", "conversion", "incidents de support"],
        ))
        return values[0] if language == "en" else values[1]

    def _default_risks(self, archetype: str, language: str) -> List[str]:
        mapping = {
            "two_sided_marketplace": (
                ["insufficient supply or demand liquidity", "trust and safety", "disintermediation", "regulatory constraints", "negative unit economics"],
                ["liquidité insuffisante de l’offre ou de la demande", "confiance et sécurité", "contournement de la plateforme", "contraintes réglementaires", "économie unitaire négative"],
            ),
            "hardware_iot": (
                ["field reliability", "hardware cost", "maintenance burden", "false measurements", "deployment complexity"],
                ["fiabilité terrain", "coût matériel", "charge de maintenance", "mesures erronées", "complexité de déploiement"],
            ),
            "b2b_workflow_saas": (
                ["slow adoption", "duplicate entry", "integration cost", "support burden", "weak willingness to pay"],
                ["adoption lente", "double saisie", "coût d’intégration", "charge de support", "faible volonté de payer"],
            ),
        }
        values = mapping.get(archetype, (
            ["weak recurring need", "poor onboarding", "low retention", "unclear payer", "operational execution risk"],
            ["besoin récurrent faible", "onboarding insuffisant", "faible rétention", "payeur mal identifié", "risque d’exécution opérationnelle"],
        ))
        return values[0] if language == "en" else values[1]

    def _evidence_needs(self, archetype: str, language: str) -> List[str]:
        mapping = {
            "two_sided_marketplace": (
                ["demand frequency and urgency", "supply availability by geography and time", "matching and cancellation data", "regulatory constraints", "take-rate and incentive economics"],
                ["fréquence et urgence de la demande", "disponibilité de l’offre selon la zone et l’heure", "données de mise en relation et d’annulation", "contraintes réglementaires", "économie de commission et d’incitation"],
            ),
            "hardware_iot": (
                ["field task accuracy", "hardware bill of materials", "reliability tests", "maintenance requirements", "deployment constraints"],
                ["précision de la tâche terrain", "nomenclature et coût matériel", "tests de fiabilité", "besoins de maintenance", "contraintes de déploiement"],
            ),
            "b2b_workflow_saas": (
                ["observed workflow frequency", "time and error baseline", "budget owner", "pilot reuse", "support cost"],
                ["fréquence du workflow observé", "base de temps et d’erreurs", "détenteur du budget", "réutilisation du pilote", "coût de support"],
            ),
        }
        values = mapping.get(archetype, (
            ["problem frequency", "current alternatives", "successful core action", "repeat usage", "real payment test"],
            ["fréquence du problème", "alternatives actuelles", "action principale réussie", "usage répété", "vrai test de paiement"],
        ))
        return values[0] if language == "en" else values[1]

    @staticmethod
    def _score(text: str, signals: Iterable[str]) -> int:
        return sum(1 for term in signals if ProjectArchetypeResolver._term_in_text(term, text))

    @staticmethod
    def _term_in_text(term: str, text: str) -> bool:
        normalized = ProjectArchetypeResolver._normalize(term)
        if not normalized:
            return False
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text))

    @staticmethod
    def _normalize(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = text.lower().replace("’", "'")
        text = re.sub(r"[^a-z0-9' -]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _tokens(value: str) -> List[str]:
        return [token for token in re.findall(r"[a-z0-9]+", value) if len(token) >= 3]

    def _explicit_values(
        self,
        values: Sequence[Any],
        *,
        maximum: int,
    ) -> List[str]:
        result: List[str] = []

        for value in values:
            clean = re.sub(
                r"\s+",
                " ",
                str(
                    value
                    or ""
                ),
            ).strip(
                " .,:;-"
            )

            if not clean:
                continue

            if len(
                clean.split()
            ) > 24:
                continue

            result.append(
                clean
            )

        return self._unique(
            result
        )[:maximum]

    def _clean_actor(self, value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;-")
        if not text or len(text.split()) > 12:
            return ""
        if any(marker in self._normalize(text) for marker in ("the first version", "excel sheets", "whatsapp groups", "before developing")):
            return ""
        return text

    def _clean_workflow(self, value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;-")
        normalized = self._normalize(text)
        if not text or len(text.split()) > 12:
            return ""
        if any(marker in normalized for marker in ("resolu trouver", "region destination resolu", "the first version", "before developing", "a reduced mvp")):
            return ""
        return text

    def _clean_workflow_object(self, value: str) -> str:
        text = re.split(r"\b(?:pour|afin|qui|because|so that|with|avec)\b", value, maxsplit=1)[0]
        text = re.sub(r"\b(?:selon|according to)\b.*$", "", text).strip()
        text = re.sub(r"\s+", " ", text).strip(" .,:;-")
        return " ".join(text.split()[:7])

    @staticmethod
    def _localized(en: Any, fr: Any, language: str) -> List[str]:
        value = en if language == "en" else fr
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return []

    @staticmethod
    def _unique(values: Iterable[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            text = re.sub(r"\s+", " ", str(value or "")).strip()
            if not text or text.casefold() in seen:
                continue
            seen.add(text.casefold())
            result.append(text)
        return result

    @staticmethod
    def _t(language: str, english: str, french: str) -> str:
        return english if language == "en" else french

    @staticmethod
    def _t_list(language: str, english: List[str], french: List[str]) -> List[str]:
        return english if language == "en" else french


project_archetype_resolver = ProjectArchetypeResolver()
