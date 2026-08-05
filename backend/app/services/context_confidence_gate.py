from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ContextConfidence,
    ContextReadinessStatus,
    ProjectContextPacketV3,
    WorkflowContext,
    clean_text,
    comparison_key,
    unique_texts,
)


@dataclass(frozen=True)
class ContextGatePolicy:
    """
    Configuration du gate de contexte.

    Les seuils mesurent uniquement la qualité et la complétude
    des informations fournies avant le lancement des agents.
    """

    ready_score: float = 0.80
    cautious_score: float = 0.75
    clarification_score: float = 0.50
    maximum_score: float = 0.94

    allow_ready_cautious: bool = True
    require_region_for_regulated_projects: bool = True

    minimum_specific_archetype_confidence: float = 0.55
    blocking_archetype_confidence: float = 0.40


@dataclass(frozen=True)
class ArchetypeGateAssessment:
    """
    Résultat des règles de complétude propres à l'archétype.
    """

    blocking_missing_fields: tuple[str, ...] = ()
    ambiguous_fields: tuple[str, ...] = ()
    critical_contradictions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


class ContextConfidenceGate:
    """
    Décide si ForgeAI possède suffisamment de contexte pour lancer
    les agents d'analyse.

    Ce service ne mesure pas :

    - la validation du marché ;
    - la rentabilité ;
    - la qualité des sources ;
    - la demande réelle ;
    - la faisabilité validée sur le terrain.

    Il mesure uniquement si l'idée est assez bien décrite pour être
    analysée sans produire de suppositions excessives.
    """

    GENERIC_ARCHETYPES = {
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
    }

    GENERIC_ACTORS = {
        "client",
        "clients",
        "user",
        "users",
        "utilisateur",
        "utilisateurs",
        "customer",
        "customers",
        "client payeur",
        "utilisateur principal",
        "operateur terrain",
        "opérateur terrain",
        "acheteur operationnel",
        "acheteur opérationnel",
    }

    REGULATED_RISK_DOMAINS = {
        "health",
        "medical",
        "finance",
        "financial",
        "legal",
        "children",
        "insurance",
        "banking",
        "regulated_service",
    }

    BUSINESS_MODEL_MARKERS = {
        "modèle économique",
        "modele economique",
        "business model",
        "modèle de revenu",
        "modele de revenu",
        "revenue model",
        "source de revenu",
        "revenu proviendra",
        "revenus proviendront",
        "revenue comes from",
        "monétisation",
        "monetisation",
        "monetization",
        "abonnement",
        "subscription",
        "commission",
        "vente",
        "sale",
        "location",
        "rental",
        "licence",
        "license",
        "freemium",
        "publicité",
        "publicite",
        "advertising",
        "paiement",
        "payment",
        "tarif",
        "pricing",
        "payant",
        "paid plan",
    }

    ARCHETYPE_ALIASES = {
        "marketplace": "two_sided_marketplace",
        "two sided marketplace": "two_sided_marketplace",
        "two_sided_marketplace": "two_sided_marketplace",
        "place de marche": "two_sided_marketplace",
        "ecommerce": "ecommerce",
        "e commerce": "ecommerce",
        "hardware iot": "hardware_iot",
        "hardware_iot": "hardware_iot",
        "iot": "hardware_iot",
        "robotique": "hardware_iot",
        "b2b workflow saas": "b2b_workflow_saas",
        "b2b_workflow_saas": "b2b_workflow_saas",
        "saas": "b2b_workflow_saas",
        "analytics ai tool": "analytics_ai_tool",
        "analytics_ai_tool": "analytics_ai_tool",
        "ai tool": "analytics_ai_tool",
        "regulated service": "regulated_service",
        "regulated_service": "regulated_service",
        "professional service": "professional_service",
        "professional_service": "professional_service",
        "content community": "content_community",
        "content_community": "content_community",
    }

    ARCHETYPE_BLOCKING_REQUIREMENTS = {
        "two_sided_marketplace": (
            "supply_side",
            "demand_side",
            "transaction_unit",
            "transaction_flow",
            "payment_responsibility",
            "fulfillment_logistics",
            "trust_mechanism",
            "dispute_responsibility",
        ),
        "ecommerce": (
            "transaction_unit",
            "payment_responsibility",
            "fulfillment_logistics",
        ),
        "b2b_workflow_saas": (
            "priority_workflow",
        ),
        "hardware_iot": (
            "deployment_environment",
            "priority_workflow",
        ),
        "analytics_ai_tool": (
            "priority_workflow",
            "input_data",
            "output_decision",
        ),
        "regulated_service": (
            "target_region",
            "priority_workflow",
        ),
        "professional_service": (
            "priority_workflow",
            "deliverable",
        ),
        "content_community": (
            "priority_workflow",
        ),
    }

    ARCHETYPE_AMBIGUOUS_REQUIREMENTS = {
        "two_sided_marketplace": (
            "business_model",
        ),
        "ecommerce": (
            "return_refund_policy",
        ),
        "b2b_workflow_saas": (
            "operational_user",
            "decision_maker",
            "payer",
        ),
        "hardware_iot": (
            "maintenance_model",
            "operational_safety",
        ),
        "analytics_ai_tool": (
            "human_oversight",
        ),
        "regulated_service": (
            "regulated_provider",
            "beneficiary",
            "regulatory_scope",
            "professional_responsibility",
        ),
        "professional_service": (
            "service_provider",
            "service_client",
        ),
        "content_community": (
            "creator_side",
            "audience_side",
            "moderation_model",
        ),
    }

    UNRESOLVED_MARKERS = {
        "pas encore defini",
        "pas encore definie",
        "non defini",
        "non definie",
        "a definir",
        "reste a definir",
        "n est pas defini",
        "ne sont pas definis",
        "inconnu",
        "inconnue",
        "a clarifier",
        "non precise",
        "non precisee",
        "not defined",
        "not yet defined",
        "unknown",
        "to be defined",
        "undecided",
        "tbd",
    }

    REQUIREMENT_MARKERS = {
        "payment_responsibility": {
            "paiement",
            "payment",
            "reglement",
            "règlement",
            "encaissement",
            "facturation",
            "billing",
            "escrow",
            "hors plateforme",
            "offline payment",
        },
        "fulfillment_logistics": {
            "transport",
            "logistique",
            "logistics",
            "livraison",
            "delivery",
            "expedition",
            "expédition",
            "remise",
            "retrait",
            "collecte",
            "fulfillment",
            "execution du service",
            "exécution du service",
            "realisation de la prestation",
            "réalisation de la prestation",
        },
        "trust_mechanism": {
            "verification",
            "vérification",
            "confiance",
            "trust",
            "identite",
            "identité",
            "kyc",
            "notation",
            "rating",
            "controle qualite",
            "contrôle qualité",
            "certification",
        },
        "dispute_responsibility": {
            "litige",
            "litiges",
            "dispute",
            "disputes",
            "arbitrage",
            "reclamation",
            "réclamation",
            "remboursement",
            "refund",
        },
        "return_refund_policy": {
            "retour",
            "returns",
            "return policy",
            "remboursement",
            "refund",
            "retractation",
            "rétractation",
            "garantie",
            "warranty",
        },
        "human_oversight": {
            "supervision humaine",
            "human oversight",
            "validation humaine",
            "human review",
            "revue humaine",
        },
        "moderation_model": {
            "moderation",
            "modération",
            "moderateur",
            "modérateur",
            "signalement",
            "regles de communaute",
            "règles de communauté",
        },
    }

    REQUIREMENT_REASONS = {
        "supply_side": (
            "A two-sided model requires an explicit supply-side actor."
        ),
        "demand_side": (
            "A two-sided model requires an explicit demand-side actor."
        ),
        "transaction_unit": (
            "The central product, service, booking, asset, or result "
            "being exchanged is not identified."
        ),
        "transaction_flow": (
            "The operation needs a clear start and completion condition."
        ),
        "payment_responsibility": (
            "The payment responsibility or explicit off-platform "
            "payment policy is not defined."
        ),
        "fulfillment_logistics": (
            "The delivery, transport, handover, or service fulfillment "
            "model is not defined."
        ),
        "trust_mechanism": (
            "The verification or trust mechanism is not defined."
        ),
        "dispute_responsibility": (
            "The dispute, complaint, refund, or arbitration "
            "responsibility is not defined."
        ),
        "deployment_environment": (
            "A hardware or IoT project requires a concrete "
            "deployment environment."
        ),
        "input_data": (
            "The data or information entering the AI workflow "
            "is not identified."
        ),
        "output_decision": (
            "The result, recommendation, or decision produced "
            "by the AI workflow is not identified."
        ),
        "deliverable": (
            "The service deliverable or completion result "
            "is not identified."
        ),
    }

    def __init__(
        self,
        policy: ContextGatePolicy | None = None,
    ) -> None:
        self.policy = policy or ContextGatePolicy()

    def evaluate(
        self,
        packet: ProjectContextPacketV3,
    ) -> ContextConfidence:
        """
        Évalue un ProjectContextPacketV3 et retourne la décision
        canonique du gate.
        """
        missing_fields: List[str] = []
        ambiguous_fields: List[str] = []
        blockers: List[str] = []
        reasons: List[str] = []

        field_scores: Dict[str, float] = {}

        # --------------------------------------------------------------
        # Problème
        # --------------------------------------------------------------

        problem_quality = self._problem_quality(
            packet
        )

        field_scores["problem"] = (
            0.18 * problem_quality
        )

        if problem_quality == 0:
            missing_fields.append(
                "problem"
            )
            blockers.append(
                "problem"
            )

        elif problem_quality < 0.70:
            ambiguous_fields.append(
                "problem"
            )

        # --------------------------------------------------------------
        # Solution
        # --------------------------------------------------------------

        solution_quality = self._solution_quality(
            packet
        )

        field_scores["solution"] = (
            0.16 * solution_quality
        )

        if solution_quality == 0:
            missing_fields.append(
                "solution"
            )
            blockers.append(
                "solution"
            )

        elif solution_quality < 0.70:
            ambiguous_fields.append(
                "solution"
            )

        # --------------------------------------------------------------
        # Acteurs
        # --------------------------------------------------------------

        actors_quality = self._actors_quality(
            packet.actors
        )

        field_scores["actors"] = (
            0.16 * actors_quality
        )

        if actors_quality == 0:
            missing_fields.append(
                "actors"
            )
            blockers.append(
                "actors"
            )

        elif actors_quality < 0.70:
            ambiguous_fields.append(
                "actors"
            )

        # --------------------------------------------------------------
        # Workflow
        # --------------------------------------------------------------

        workflow_quality = self._workflow_quality(
            packet.priority_workflows,
            packet.mvp_scope,
        )

        field_scores["priority_workflow"] = (
            0.22 * workflow_quality
        )

        if workflow_quality == 0:
            missing_fields.append(
                "priority_workflow"
            )
            blockers.append(
                "priority_workflow"
            )

        elif workflow_quality < 0.70:
            ambiguous_fields.append(
                "priority_workflow"
            )

        # --------------------------------------------------------------
        # Nom
        # --------------------------------------------------------------

        project_name_present = bool(
            clean_text(
                packet.project_name
            )
        )

        field_scores["project_name"] = (
            0.04
            if project_name_present
            else 0.0
        )

        if not project_name_present:
            ambiguous_fields.append(
                "project_name"
            )

        # --------------------------------------------------------------
        # Région
        # --------------------------------------------------------------

        target_region_present = bool(
            clean_text(
                packet.target_region
            )
        )

        field_scores["target_region"] = (
            0.07
            if target_region_present
            else 0.0
        )

        if not target_region_present:
            ambiguous_fields.append(
                "target_region"
            )

        # --------------------------------------------------------------
        # Archétype
        # --------------------------------------------------------------

        archetype_specific = (
            self._has_specific_archetype(
                packet
            )
        )

        field_scores["project_archetype"] = (
            0.06
            if archetype_specific
            else 0.0
        )

        if not archetype_specific:
            ambiguous_fields.append(
                "project_archetype"
            )

        # --------------------------------------------------------------
        # Modèle économique explicite
        # --------------------------------------------------------------

        explicit_business_model = (
            self._has_explicit_business_model(
                packet
            )
        )

        field_scores["business_model"] = (
            0.04
            if explicit_business_model
            else 0.0
        )

        if not explicit_business_model:
            ambiguous_fields.append(
                "business_model"
            )

            reasons.append(
                "No explicit business model was found "
                "in the user-provided project description."
            )

        # --------------------------------------------------------------
        # Périmètre MVP
        # --------------------------------------------------------------

        mvp_scope_present = bool(
            packet.mvp_scope
        )

        field_scores["mvp_scope"] = (
            0.03
            if mvp_scope_present
            else 0.0
        )

        if not mvp_scope_present:
            ambiguous_fields.append(
                "mvp_scope"
            )

        # --------------------------------------------------------------
        # Contraintes
        # --------------------------------------------------------------

        constraints_present = bool(
            packet.constraints
        )

        field_scores["constraints"] = (
            0.02
            if constraints_present
            else 0.0
        )

        if not constraints_present:
            ambiguous_fields.append(
                "constraints"
            )

        # --------------------------------------------------------------
        # Métriques de succès
        # --------------------------------------------------------------

        success_metrics_present = bool(
            packet.success_metrics
        )

        field_scores["success_metrics"] = (
            0.01
            if success_metrics_present
            else 0.0
        )

        if not success_metrics_present:
            ambiguous_fields.append(
                "success_metrics"
            )

        # --------------------------------------------------------------
        # Projets réglementés
        # --------------------------------------------------------------

        if (
            self._requires_region(
                packet
            )
            and not target_region_present
        ):
            blockers.append(
                "target_region"
            )

            reasons.append(
                "A target region is required for "
                "regulated or high-risk projects."
            )

        # --------------------------------------------------------------
        # Invariants structurels
        # --------------------------------------------------------------

        invariant_issues = self._invariant_issues(
            packet
        )

        reasons.extend(
            invariant_issues
        )

        if any(
            issue.startswith(
                "workflow_scope_collision"
            )
            for issue in invariant_issues
        ):
            blockers.append(
                "priority_workflow"
            )

            ambiguous_fields.append(
                "priority_workflow"
            )

        if any(
            issue.startswith(
                "core_term_forbidden"
            )
            for issue in invariant_issues
        ):
            blockers.append(
                "domain_integrity"
            )

        # --------------------------------------------------------------
        # Exigences propres à l'archétype
        # --------------------------------------------------------------

        archetype_assessment = (
            self._archetype_assessment(
                packet
            )
        )

        blockers.extend(
            archetype_assessment
            .blocking_missing_fields
        )

        ambiguous_fields.extend(
            archetype_assessment
            .ambiguous_fields
        )

        reasons.extend(
            archetype_assessment.reasons
        )

        if (
            archetype_assessment
            .critical_contradictions
        ):
            blockers.append(
                "critical_contradictions"
            )

            reasons.extend(
                (
                    "critical_contradiction: "
                    + contradiction
                )
                for contradiction
                in archetype_assessment
                .critical_contradictions
            )

        # --------------------------------------------------------------
        # Score
        # --------------------------------------------------------------

        score = sum(
            field_scores.values()
        )

        score += self._explicitness_bonus(
            packet
        )

        score -= self._quality_penalty(
            packet,
            invariant_issues,
        )

        score = round(
            max(
                0.0,
                min(
                    self.policy.maximum_score,
                    score,
                ),
            ),
            2,
        )

        missing_fields = unique_texts(
            missing_fields
        )

        ambiguous_fields = unique_texts(
            ambiguous_fields
        )

        blockers = unique_texts(
            blockers
        )

        status = self._status_for(
            score=score,
            missing_fields=missing_fields,
            blockers=blockers,
            ambiguous_fields=ambiguous_fields,
        )

        reasons.extend(
            [
                f"context_score={score:.2f}",
                (
                    "Context completeness is separate "
                    "from market validation."
                ),
            ]
        )

        clarification_fields = unique_texts(
            [
                *missing_fields,
                *ambiguous_fields,
                *blockers,
            ]
        )

        questions = self._clarification_questions(
            fields=clarification_fields,
            language=packet.language,
        )

        return ContextConfidence(
            score=score,
            status=status,
            missing_fields=missing_fields,
            ambiguous_fields=ambiguous_fields,
            blockers=blockers,
            clarification_questions=questions,
            reasons=unique_texts(
                reasons
            ),
        )

    def apply(
        self,
        packet: ProjectContextPacketV3,
    ) -> ProjectContextPacketV3:
        """
        Retourne une copie du packet contenant la décision canonique.
        """
        assessment = self._archetype_assessment(
            packet
        )

        confidence = self.evaluate(
            packet
        )

        return packet.model_copy(
            update={
                "confidence": confidence,
                "blocking_missing_fields": (
                    unique_texts(
                        [
                            *packet
                            .blocking_missing_fields,
                            *assessment
                            .blocking_missing_fields,
                        ]
                    )
                ),
                "critical_contradictions": (
                    unique_texts(
                        [
                            *packet
                            .critical_contradictions,
                            *assessment
                            .critical_contradictions,
                        ]
                    )
                ),
            },
            deep=True,
        )

    def should_run_agents(
        self,
        packet_or_confidence: (
            ProjectContextPacketV3
            | ContextConfidence
        ),
    ) -> bool:
        """
        Retourne True lorsque les agents lourds peuvent être lancés.
        """
        if isinstance(
            packet_or_confidence,
            ProjectContextPacketV3,
        ):
            evaluated_packet = self.apply(
                packet_or_confidence
            )

            if (
                evaluated_packet
                .blocking_missing_fields
                or evaluated_packet
                .critical_contradictions
            ):
                return False

            confidence = (
                evaluated_packet.confidence
            )
        else:
            confidence = packet_or_confidence

        if confidence.blockers:
            return False

        if (
            confidence.status
            == ContextReadinessStatus.READY
        ):
            return True

        if (
            self.policy.allow_ready_cautious
            and confidence.status
            == ContextReadinessStatus.READY_CAUTIOUS
        ):
            return True

        return False

    def to_runtime_payload(
        self,
        packet: ProjectContextPacketV3,
    ) -> Dict[str, Any]:
        """
        Retourne un payload compatible avec le pipeline Sprint 3.
        """
        evaluated_packet = self.apply(
            packet
        )

        confidence = evaluated_packet.confidence

        blockers = unique_texts(
            [
                *confidence.blockers,
                *evaluated_packet
                .blocking_missing_fields,
                *(
                    ["critical_contradictions"]
                    if evaluated_packet
                    .critical_contradictions
                    else []
                ),
            ]
        )

        ready_for_agents = bool(
            self.should_run_agents(
                confidence
            )
            and not evaluated_packet
            .blocking_missing_fields
            and not evaluated_packet
            .critical_contradictions
        )

        return {
            "format": (
                "context_confidence_gate_v1"
            ),
            "schema_version": (
                evaluated_packet.schema_version
            ),
            "status": (
                confidence.status.value
            ),
            "score": (
                confidence.score
            ),
            "threshold": (
                self.policy.cautious_score
            ),
            "ready_for_agents": (
                ready_for_agents
            ),
            "missing_fields": list(
                confidence.missing_fields
            ),
            "ambiguous_fields": list(
                confidence.ambiguous_fields
            ),
            "blocking_missing_fields": list(
                evaluated_packet
                .blocking_missing_fields
            ),
            "critical_contradictions": list(
                evaluated_packet
                .critical_contradictions
            ),
            "archetype_confidence": (
                evaluated_packet
                .archetype_confidence
            ),
            "blockers": blockers,
            "questions": list(
                confidence.clarification_questions
            ),
            "clarification_questions": list(
                confidence.clarification_questions
            ),
            "reasons": list(
                confidence.reasons
            ),
            "output_language": (
                evaluated_packet.language
            ),
            "project_context_packet": (
                evaluated_packet.model_dump(
                    mode="json"
                )
            ),
            "legacy_project_context": (
                evaluated_packet.to_legacy_dict()
            ),
        }


    def evaluate_mapping(
        self,
        data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Évalue un packet sérialisé provenant de Redis ou de la base.
        """
        packet = (
            ProjectContextPacketV3.model_validate(
                dict(
                    data
                )
            )
        )

        return self.to_runtime_payload(
            packet
        )

    def _archetype_assessment(
        self,
        packet: ProjectContextPacketV3,
    ) -> ArchetypeGateAssessment:
        """
        Applique une matrice universelle d'exigences par archétype.

        Les règles utilisent uniquement le type d'opération, les rôles,
        les responsabilités et les informations explicites du projet.
        Elles ne dépendent jamais du nom du projet.
        """
        archetype = self._canonical_archetype(
            packet.primary_archetype
        )

        blocking = list(
            packet.blocking_missing_fields
        )

        ambiguous: List[str] = []

        contradictions = list(
            packet.critical_contradictions
        )

        reasons: List[str] = []

        if (
            archetype
            and archetype
            != "generic_digital_product"
        ):
            archetype_confidence = float(
                packet.archetype_confidence
                or 0.0
            )

            if (
                archetype_confidence
                < self.policy
                .blocking_archetype_confidence
            ):
                blocking.append(
                    "archetype_confidence"
                )

                reasons.append(
                    "The archetype confidence is too low "
                    "to select reliable project-specific rules."
                )

            elif (
                archetype_confidence
                < self.policy
                .minimum_specific_archetype_confidence
            ):
                ambiguous.append(
                    "archetype_confidence"
                )

        for requirement in (
            self.ARCHETYPE_BLOCKING_REQUIREMENTS.get(
                archetype,
                (),
            )
        ):
            if self._requirement_is_present(
                packet,
                requirement,
            ):
                continue

            blocking.append(
                requirement
            )

            reason = (
                self.REQUIREMENT_REASONS.get(
                    requirement
                )
            )

            if reason:
                reasons.append(
                    reason
                )

        for requirement in (
            self.ARCHETYPE_AMBIGUOUS_REQUIREMENTS.get(
                archetype,
                (),
            )
        ):
            if self._requirement_is_present(
                packet,
                requirement,
            ):
                continue

            ambiguous.append(
                requirement
            )

        contradictions.extend(
            self._critical_contradictions(
                packet
            )
        )

        return ArchetypeGateAssessment(
            blocking_missing_fields=tuple(
                unique_texts(
                    blocking
                )
            ),
            ambiguous_fields=tuple(
                unique_texts(
                    ambiguous
                )
            ),
            critical_contradictions=tuple(
                unique_texts(
                    contradictions
                )
            ),
            reasons=tuple(
                unique_texts(
                    reasons
                )
            ),
        )

    def _requirement_is_present(
        self,
        packet: ProjectContextPacketV3,
        requirement: str,
    ) -> bool:
        """
        Résout une exigence universelle à partir du packet canonique.
        """
        transaction = packet.transaction_unit
        workflow = packet.primary_workflow

        if requirement == "supply_side":
            return bool(
                clean_text(
                    transaction.supply_actor
                )
                or self._has_actor_role(
                    packet,
                    {
                        ActorRole.PROVIDER,
                    },
                )
            )

        if requirement == "demand_side":
            return bool(
                clean_text(
                    transaction.demand_actor
                )
                or self._has_actor_role(
                    packet,
                    {
                        ActorRole.BUYER,
                        ActorRole.USER,
                        ActorRole.BENEFICIARY,
                    },
                )
            )

        if requirement == "transaction_unit":
            return bool(
                transaction.has_named_object
            )

        if requirement == "transaction_flow":
            return bool(
                clean_text(
                    transaction.initiation_action
                )
                and clean_text(
                    transaction.completion_action
                )
            )

        if requirement == "payment_responsibility":
            return self._concept_is_resolved(
                packet=packet,
                explicit_values=(
                    transaction
                    .payment_responsibility,
                ),
                markers=(
                    self.REQUIREMENT_MARKERS[
                        requirement
                    ]
                ),
            )

        if requirement == "fulfillment_logistics":
            return self._concept_is_resolved(
                packet=packet,
                explicit_values=(
                    transaction
                    .fulfillment_responsibility,
                    transaction.fulfillment_mode,
                ),
                markers=(
                    self.REQUIREMENT_MARKERS[
                        requirement
                    ]
                ),
            )

        if requirement == "trust_mechanism":
            return self._concept_is_resolved(
                packet=packet,
                explicit_values=(
                    transaction.trust_mechanism,
                ),
                markers=(
                    self.REQUIREMENT_MARKERS[
                        requirement
                    ]
                ),
            )

        if requirement == "dispute_responsibility":
            return self._concept_is_resolved(
                packet=packet,
                explicit_values=(
                    transaction
                    .dispute_responsibility,
                ),
                markers=(
                    self.REQUIREMENT_MARKERS[
                        requirement
                    ]
                ),
            )

        if requirement in {
            "return_refund_policy",
            "human_oversight",
            "moderation_model",
        }:
            return self._concept_is_resolved(
                packet=packet,
                explicit_values=(),
                markers=(
                    self.REQUIREMENT_MARKERS[
                        requirement
                    ]
                ),
            )

        if requirement == "priority_workflow":
            return bool(
                workflow
                and workflow.is_actionable
            )

        if requirement == "business_model":
            return bool(
                packet.business_model_hypotheses
            )

        if requirement == "operational_user":
            return self._has_actor_role(
                packet,
                {
                    ActorRole.USER,
                    ActorRole.OPERATOR,
                    ActorRole.BENEFICIARY,
                },
            )

        if requirement == "decision_maker":
            return bool(
                packet.decision_maker_actor_names
                or self._has_actor_role(
                    packet,
                    {
                        ActorRole.DECISION_MAKER,
                    },
                )
            )

        if requirement == "payer":
            return bool(
                packet.payer_actor_names
                or self._has_actor_role(
                    packet,
                    {
                        ActorRole.PAYER,
                        ActorRole.BUYER,
                    },
                )
            )

        if requirement == "deployment_environment":
            return bool(
                packet.deployment_environment
            )

        if requirement == "maintenance_model":
            return self._contains_text_marker(
                packet,
                {
                    "maintenance",
                    "reparation",
                    "réparation",
                    "support terrain",
                    "field support",
                    "installateur",
                },
            )

        if requirement == "operational_safety":
            return self._contains_text_marker(
                packet,
                {
                    "securite",
                    "sécurité",
                    "safety",
                    "fiabilite",
                    "fiabilité",
                    "autonomie",
                    "battery",
                    "batterie",
                    "energie",
                    "énergie",
                },
            )

        if requirement == "input_data":
            return bool(
                workflow
                and clean_text(
                    workflow.object
                )
            )

        if requirement == "output_decision":
            return bool(
                workflow
                and (
                    clean_text(
                        workflow.result
                    )
                    or clean_text(
                        workflow.output
                    )
                )
            )

        if requirement == "target_region":
            return bool(
                clean_text(
                    packet.target_region
                )
            )

        if requirement == "regulated_provider":
            return self._has_actor_role(
                packet,
                {
                    ActorRole.PROVIDER,
                    ActorRole.OPERATOR,
                    ActorRole.MAINTAINER,
                },
            )

        if requirement == "beneficiary":
            return self._has_actor_role(
                packet,
                {
                    ActorRole.BENEFICIARY,
                    ActorRole.USER,
                    ActorRole.BUYER,
                },
            )

        if requirement == "regulatory_scope":
            return bool(
                packet.regulatory_flags
                or packet.risk_domains
            )

        if requirement == "professional_responsibility":
            return self._contains_text_marker(
                packet,
                {
                    "responsabilite professionnelle",
                    "responsabilité professionnelle",
                    "licensed professional",
                    "validation medicale",
                    "validation médicale",
                    "supervision humaine",
                },
            )

        if requirement == "service_provider":
            return self._has_actor_role(
                packet,
                {
                    ActorRole.PROVIDER,
                    ActorRole.OPERATOR,
                    ActorRole.PARTNER,
                },
            )

        if requirement == "service_client":
            return self._has_actor_role(
                packet,
                {
                    ActorRole.BUYER,
                    ActorRole.USER,
                    ActorRole.BENEFICIARY,
                },
            )

        if requirement == "deliverable":
            return bool(
                workflow
                and (
                    clean_text(
                        workflow.result
                    )
                    or clean_text(
                        workflow.output
                    )
                    or clean_text(
                        transaction.value_exchanged
                    )
                )
            )

        if requirement == "creator_side":
            return self._contains_text_marker(
                packet,
                {
                    "createur",
                    "créateur",
                    "auteur",
                    "publisher",
                    "contributor",
                },
            )

        if requirement == "audience_side":
            return self._contains_text_marker(
                packet,
                {
                    "membre",
                    "audience",
                    "abonne",
                    "abonné",
                    "lecteur",
                    "viewer",
                    "community",
                },
            )

        return False

    def _critical_contradictions(
        self,
        packet: ProjectContextPacketV3,
    ) -> List[str]:
        """
        Détecte les contradictions qui rendent le packet inexploitable.
        """
        transaction = packet.transaction_unit

        supply_key = comparison_key(
            transaction.supply_actor
        )

        demand_key = comparison_key(
            transaction.demand_actor
        )

        contradictions: List[str] = []

        if (
            supply_key
            and demand_key
            and supply_key == demand_key
        ):
            contradictions.append(
                "transaction_supply_and_demand_are_identical"
            )

        return unique_texts(
            contradictions
        )

    def _canonical_archetype(
        self,
        value: Any,
    ) -> str:
        key = comparison_key(
            value
        )

        if not key:
            return "generic_digital_product"

        return self.ARCHETYPE_ALIASES.get(
            key,
            clean_text(value),
        )

    def _has_actor_role(
        self,
        packet: ProjectContextPacketV3,
        roles: set[ActorRole],
    ) -> bool:
        return any(
            actor.role in roles
            for actor in packet.actors
        )

    def _explicit_text(
        self,
        packet: ProjectContextPacketV3,
    ) -> str:
        """
        Texte explicitement fourni ou conservé dans le packet.

        Les responsabilités critiques ne doivent pas être considérées
        définies uniquement parce qu'une ancienne couche a généré
        une hypothèse générique.
        """
        return clean_text(
            " ".join(
                [
                    packet.description,
                    " ".join(
                        packet.constraints
                    ),
                    " ".join(
                        packet.assumptions
                    ),
                ]
            )
        )

    def _contains_text_marker(
        self,
        packet: ProjectContextPacketV3,
        markers: Iterable[str],
    ) -> bool:
        key = comparison_key(
            self._explicit_text(
                packet
            )
        )

        return any(
            comparison_key(marker)
            in key
            for marker in markers
            if comparison_key(marker)
        )

    def _concept_is_resolved(
        self,
        *,
        packet: ProjectContextPacketV3,
        explicit_values: Sequence[Any],
        markers: Iterable[str],
    ) -> bool:
        """
        Vérifie qu'un concept est réellement défini.

        Une phrase comme « le paiement n'est pas encore défini » ne
        constitue jamais une preuve de complétude.
        """
        if any(
            clean_text(value)
            for value in explicit_values
        ):
            return True

        marker_keys = {
            comparison_key(marker)
            for marker in markers
            if comparison_key(marker)
        }

        if not marker_keys:
            return False

        relevant_sentences = [
            sentence
            for sentence in self._sentences(
                self._explicit_text(
                    packet
                )
            )
            if any(
                marker_key
                in comparison_key(
                    sentence
                )
                for marker_key
                in marker_keys
            )
        ]

        if not relevant_sentences:
            return False

        unresolved_keys = {
            comparison_key(marker)
            for marker in self.UNRESOLVED_MARKERS
            if comparison_key(marker)
        }

        return any(
            not any(
                unresolved_key
                in comparison_key(
                    sentence
                )
                for unresolved_key
                in unresolved_keys
            )
            for sentence in relevant_sentences
        )

    def _sentences(
        self,
        value: Any,
    ) -> List[str]:
        text = clean_text(
            value
        )

        if not text:
            return []

        return unique_texts(
            part
            for part in re.split(
                r"(?<=[.!?])\s+|\n+",
                text,
            )
            if clean_text(
                part
            )
        )

    def _status_for(
        self,
        *,
        score: float,
        missing_fields: Sequence[str],
        blockers: Sequence[str],
        ambiguous_fields: Sequence[str],
    ) -> ContextReadinessStatus:
        """
        Calcule le statut final.
        """
        if blockers or missing_fields:
            if (
                score
                < self.policy.clarification_score
            ):
                return (
                    ContextReadinessStatus
                    .INSUFFICIENT_CONTEXT
                )

            return (
                ContextReadinessStatus
                .NEEDS_CLARIFICATION
            )

        if (
            score
            >= self.policy.ready_score
            and not ambiguous_fields
        ):
            return (
                ContextReadinessStatus.READY
            )

        if (
            score
            >= self.policy.cautious_score
        ):
            return (
                ContextReadinessStatus
                .READY_CAUTIOUS
            )

        if (
            score
            >= self.policy.clarification_score
        ):
            return (
                ContextReadinessStatus
                .NEEDS_CLARIFICATION
            )

        return (
            ContextReadinessStatus
            .INSUFFICIENT_CONTEXT
        )

    def _problem_quality(
        self,
        packet: ProjectContextPacketV3,
    ) -> float:
        """
        Évalue la précision du problème.
        """
        pain = clean_text(
            packet.problem.pain
        )

        if not pain:
            return 0.0

        score = 0.55

        if len(
            pain
        ) >= 40:
            score += 0.20

        if packet.problem.actors_affected:
            score += 0.10

        if packet.problem.current_alternatives:
            score += 0.10

        if packet.problem.consequences:
            score += 0.05

        return min(
            1.0,
            score,
        )

    def _solution_quality(
        self,
        packet: ProjectContextPacketV3,
    ) -> float:
        """
        Évalue la précision de la solution.
        """
        mechanism = clean_text(
            packet.solution.mechanism
        )

        if not mechanism:
            return 0.0

        score = 0.55

        if len(
            mechanism
        ) >= 40:
            score += 0.20

        if packet.solution.delivery_mode:
            score += 0.10

        if packet.solution.required_capabilities:
            score += 0.10

        if packet.solution.core_value:
            score += 0.05

        return min(
            1.0,
            score,
        )

    def _actors_quality(
        self,
        actors: Sequence[ActorContext],
    ) -> float:
        """
        Évalue la spécificité des acteurs.
        """
        if not actors:
            return 0.0

        generic_actor_keys = {
            comparison_key(
                value
            )
            for value in self.GENERIC_ACTORS
        }

        specific_actors = [
            actor
            for actor in actors
            if (
                comparison_key(
                    actor.name
                )
                not in generic_actor_keys
                and not actor.is_generic
            )
        ]

        if not specific_actors:
            return 0.30

        explicit_count = sum(
            actor.is_explicit
            for actor in specific_actors
        )

        score = 0.55

        score += min(
            0.25,
            len(
                specific_actors
            ) * 0.07,
        )

        score += min(
            0.20,
            explicit_count * 0.06,
        )

        return min(
            1.0,
            score,
        )

    def _workflow_quality(
        self,
        workflows: Sequence[WorkflowContext],
        mvp_scope: Sequence[str],
    ) -> float:
        """
        Vérifie que le workflow principal représente une vraie action.
        """
        actionable_workflows = [
            workflow
            for workflow in workflows
            if workflow.is_actionable
        ]

        if not actionable_workflows:
            return 0.0

        primary = actionable_workflows[0]

        score = 0.55

        if primary.actor:
            score += 0.08

        if primary.object:
            score += 0.12

        if primary.result:
            score += 0.10

        if primary.output:
            score += 0.07

        if primary.is_explicit:
            score += 0.08

        workflow_key = comparison_key(
            primary.sentence
        )

        scope_keys = {
            comparison_key(
                value
            )
            for value in mvp_scope
        }

        if (
            workflow_key
            and workflow_key in scope_keys
        ):
            score -= 0.60

        return max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

    def _has_specific_archetype(
        self,
        packet: ProjectContextPacketV3,
    ) -> bool:
        """
        Vérifie que l'archétype n'est pas générique.
        """
        archetype_key = comparison_key(
            packet.primary_archetype
        )

        generic_keys = {
            comparison_key(
                value
            )
            for value in self.GENERIC_ARCHETYPES
        }

        return bool(
            archetype_key
            and archetype_key not in generic_keys
        )

    def _has_explicit_business_model(
        self,
        packet: ProjectContextPacketV3,
    ) -> bool:
        """
        Vérifie que le modèle économique provient réellement du texte
        utilisateur.

        Les hypothèses générées par ProjectIntelligenceLayer ne doivent
        pas augmenter le score du contexte.

        Une hypothèse est considérée explicite lorsque :

        - la description contient un marqueur économique clair ;
        - ou la formulation complète de l'hypothèse apparaît dans
          la description originale.
        """
        description_key = comparison_key(
            packet.description
        )

        if not description_key:
            return False

        for marker in self.BUSINESS_MODEL_MARKERS:
            marker_key = comparison_key(
                marker
            )

            if (
                marker_key
                and marker_key in description_key
            ):
                return True

        for hypothesis in (
            packet.business_model_hypotheses
        ):
            hypothesis_key = comparison_key(
                hypothesis
            )

            if not hypothesis_key:
                continue

            if hypothesis_key in description_key:
                return True

            if (
                len(
                    hypothesis_key.split()
                )
                >= 4
                and description_key
                in hypothesis_key
            ):
                return True

        return False

    def _explicitness_bonus(
        self,
        packet: ProjectContextPacketV3,
    ) -> float:
        """
        Petit bonus pour les informations explicitement écrites.
        """
        bonus = 0.0

        if (
            packet.actors
            and all(
                actor.is_explicit
                for actor in packet.actors
            )
        ):
            bonus += 0.01

        if (
            packet.primary_workflow
            and packet.primary_workflow.is_explicit
        ):
            bonus += 0.01

        return bonus

    def _quality_penalty(
        self,
        packet: ProjectContextPacketV3,
        invariant_issues: Sequence[str],
    ) -> float:
        """
        Pénalise les incohérences structurelles.
        """
        penalty = 0.0

        if packet.validation_warnings:
            penalty += min(
                0.08,
                len(
                    packet.validation_warnings
                ) * 0.02,
            )

        penalty += min(
            0.15,
            len(
                invariant_issues
            ) * 0.05,
        )

        if (
            packet.actors
            and all(
                actor.is_generic
                for actor in packet.actors
            )
        ):
            penalty += 0.12

        return penalty

    def _requires_region(
        self,
        packet: ProjectContextPacketV3,
    ) -> bool:
        """
        Rend la région obligatoire pour les projets réglementés.
        """
        if not (
            self.policy
            .require_region_for_regulated_projects
        ):
            return False

        project_values = {
            comparison_key(
                value
            )
            for value in [
                packet.primary_archetype,
                *packet.secondary_archetypes,
                *packet.risk_domains,
                *packet.regulatory_flags,
            ]
            if comparison_key(
                value
            )
        }

        regulated_values = {
            comparison_key(
                value
            )
            for value
            in self.REGULATED_RISK_DOMAINS
        }

        return bool(
            project_values.intersection(
                regulated_values
            )
        )

    def _invariant_issues(
        self,
        packet: ProjectContextPacketV3,
    ) -> List[str]:
        """
        Vérifie les invariants communs à toutes les idées.
        """
        issues: List[str] = []

        scope_keys = {
            comparison_key(
                value
            )
            for value in packet.mvp_scope
            if comparison_key(
                value
            )
        }

        workflow_keys = {
            comparison_key(
                workflow.sentence
            )
            for workflow in packet.priority_workflows
            if comparison_key(
                workflow.sentence
            )
        }

        if scope_keys.intersection(
            workflow_keys
        ):
            issues.append(
                "workflow_scope_collision: "
                "workflow equals MVP scope"
            )

        core_terms = unique_texts(
            [
                *packet.sector_labels,
                *packet.domain_terms,
                *packet.use_case_terms,
                *packet.solution_terms,
                *packet.target_terms,
            ]
        )

        core_keys = {
            comparison_key(
                value
            )
            for value in core_terms
            if comparison_key(
                value
            )
        }

        forbidden_keys = {
            comparison_key(
                value
            )
            for value
            in packet.forbidden_adjacent_domains
            if comparison_key(
                value
            )
        }

        collisions = sorted(
            core_keys.intersection(
                forbidden_keys
            )
        )

        if collisions:
            issues.append(
                "core_term_forbidden: "
                + ", ".join(
                    collisions[:5]
                )
            )

        explicit_actors = [
            actor
            for actor in packet.actors
            if actor.is_explicit
        ]

        generic_inferred = [
            actor.name
            for actor in packet.actors
            if (
                not actor.is_explicit
                and actor.is_generic
            )
        ]

        if (
            explicit_actors
            and generic_inferred
        ):
            issues.append(
                "generic_actor_leakage: "
                + ", ".join(
                    generic_inferred
                )
            )

        return unique_texts(
            issues
        )

    def _clarification_questions(
        self,
        *,
        fields: Iterable[str],
        language: str,
    ) -> List[str]:
        """
        Génère les questions de clarification dans la langue du projet.
        """
        language_key = comparison_key(
            language
        )

        french_questions = {
            "project_name": (
                "Quel nom souhaitez-vous donner au projet ?"
            ),
            "problem": (
                "Quel problème concret, fréquent et coûteux "
                "souhaitez-vous résoudre ?"
            ),
            "solution": (
                "Comment la solution résout-elle concrètement "
                "ce problème ?"
            ),
            "actors": (
                "Qui utilisera la solution, qui paiera et "
                "qui décidera de l’achat ?"
            ),
            "priority_workflow": (
                "Quelle action principale l’utilisateur "
                "doit-il accomplir de bout en bout ?"
            ),
            "target_region": (
                "Dans quel pays ou quelle région "
                "le projet sera-t-il lancé ?"
            ),
            "project_archetype": (
                "S’agit-il principalement d’un logiciel, "
                "d’une marketplace, d’un service ou "
                "d’un produit matériel ?"
            ),
            "business_model": (
                "Qui paiera et selon quel modèle de revenu ?"
            ),
            "mvp_scope": (
                "Quel est le périmètre exact de la "
                "première version testable ?"
            ),
            "constraints": (
                "Quelles contraintes techniques, financières, "
                "opérationnelles ou réglementaires "
                "sont déjà connues ?"
            ),
            "success_metrics": (
                "Quels indicateurs permettront de vérifier "
                "que le pilote fonctionne ?"
            ),
            "domain_integrity": (
                "Quels domaines proches doivent être exclus "
                "de l’analyse ?"
            ),
            "archetype_confidence": (
                "Quel est le type principal du projet et quels "
                "signaux le prouvent ?"
            ),
            "supply_side": (
                "Qui fournit, vend ou exécute l’offre principale ?"
            ),
            "demand_side": (
                "Qui recherche, réserve, achète ou reçoit cette offre ?"
            ),
            "transaction_unit": (
                "Quel produit, service, lot, réservation ou résultat "
                "constitue l’unité centrale de valeur ?"
            ),
            "transaction_flow": (
                "Comment l’opération commence-t-elle et quand "
                "est-elle terminée ?"
            ),
            "payment_responsibility": (
                "Qui gère le paiement, sur la plateforme ou hors plateforme ?"
            ),
            "fulfillment_logistics": (
                "Qui gère la livraison, le transport, la remise "
                "ou l’exécution du service ?"
            ),
            "trust_mechanism": (
                "Comment les acteurs, produits ou services seront-ils vérifiés ?"
            ),
            "dispute_responsibility": (
                "Qui gère les litiges, réclamations ou remboursements ?"
            ),
            "return_refund_policy": (
                "Quelle politique de retour, remboursement ou garantie s’applique ?"
            ),
            "operational_user": (
                "Qui utilise concrètement le produit au quotidien ?"
            ),
            "decision_maker": (
                "Qui décide de l’achat ou du déploiement ?"
            ),
            "payer": (
                "Qui paie réellement le produit ou l’abonnement ?"
            ),
            "deployment_environment": (
                "Dans quel environnement physique le produit sera-t-il déployé ?"
            ),
            "maintenance_model": (
                "Qui installe, maintient et répare le produit ?"
            ),
            "operational_safety": (
                "Quelles contraintes de sécurité, fiabilité, énergie "
                "ou autonomie s’appliquent ?"
            ),
            "input_data": (
                "Quelles données ou informations alimentent l’outil ?"
            ),
            "output_decision": (
                "Quel résultat, recommandation ou décision l’outil produit-il ?"
            ),
            "human_oversight": (
                "Quelle validation humaine est requise ?"
            ),
            "regulated_provider": (
                "Quel professionnel ou organisme autorisé fournit le service ?"
            ),
            "beneficiary": (
                "Qui bénéficie directement du service ?"
            ),
            "regulatory_scope": (
                "Quelles règles ou autorisations s’appliquent ?"
            ),
            "professional_responsibility": (
                "Qui porte la responsabilité professionnelle finale ?"
            ),
            "service_provider": (
                "Qui réalise la prestation professionnelle ?"
            ),
            "service_client": (
                "Qui commande et valide la prestation ?"
            ),
            "deliverable": (
                "Quel livrable ou résultat marque la fin de la mission ?"
            ),
            "creator_side": (
                "Qui crée ou publie le contenu principal ?"
            ),
            "audience_side": (
                "Qui consulte ou interagit avec ce contenu ?"
            ),
            "moderation_model": (
                "Qui modère les contenus et traite les signalements ?"
            ),
            "critical_contradictions": (
                "Quelles informations contradictoires doivent être corrigées ?"
            ),
        }

        english_questions = {
            "project_name": (
                "What name should be used for the project?"
            ),
            "problem": (
                "What concrete, recurring, and costly problem "
                "do you want to solve?"
            ),
            "solution": (
                "How does the solution solve that problem "
                "in practice?"
            ),
            "actors": (
                "Who will use the solution, who will pay, "
                "and who will make the buying decision?"
            ),
            "priority_workflow": (
                "What end-to-end action must the user complete?"
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
                "Who will pay and through which revenue model?"
            ),
            "mvp_scope": (
                "What is the exact scope of the first "
                "testable version?"
            ),
            "constraints": (
                "Which technical, financial, operational, "
                "or regulatory constraints are already known?"
            ),
            "success_metrics": (
                "Which metrics will show that the pilot works?"
            ),
            "domain_integrity": (
                "Which adjacent domains must be excluded "
                "from the analysis?"
            ),
            "archetype_confidence": (
                "What is the project's main type and which signals prove it?"
            ),
            "supply_side": (
                "Who supplies, sells, or performs the main offer?"
            ),
            "demand_side": (
                "Who searches for, books, buys, or receives the offer?"
            ),
            "transaction_unit": (
                "Which product, service, booking, asset, or result "
                "is the central unit of value?"
            ),
            "transaction_flow": (
                "How does the operation start and when is it complete?"
            ),
            "payment_responsibility": (
                "Who manages payment, on or off the platform?"
            ),
            "fulfillment_logistics": (
                "Who manages delivery, transport, handover, or fulfillment?"
            ),
            "trust_mechanism": (
                "How will actors, products, or services be verified?"
            ),
            "dispute_responsibility": (
                "Who manages disputes, complaints, or refunds?"
            ),
            "return_refund_policy": (
                "Which return, refund, or warranty policy applies?"
            ),
            "operational_user": (
                "Who uses the product in the daily workflow?"
            ),
            "decision_maker": (
                "Who decides to buy or deploy the product?"
            ),
            "payer": (
                "Who actually pays for the product or subscription?"
            ),
            "deployment_environment": (
                "In which physical environment will the product be deployed?"
            ),
            "maintenance_model": (
                "Who installs, maintains, and repairs the product?"
            ),
            "operational_safety": (
                "Which safety, reliability, energy, or autonomy constraints apply?"
            ),
            "input_data": (
                "Which data or information feeds the tool?"
            ),
            "output_decision": (
                "Which result, recommendation, or decision does the tool produce?"
            ),
            "human_oversight": (
                "Which human validation is required?"
            ),
            "regulated_provider": (
                "Which licensed professional or organization provides the service?"
            ),
            "beneficiary": (
                "Who directly benefits from the service?"
            ),
            "regulatory_scope": (
                "Which rules or authorizations apply?"
            ),
            "professional_responsibility": (
                "Who carries final professional responsibility?"
            ),
            "service_provider": (
                "Who performs the professional service?"
            ),
            "service_client": (
                "Who orders and validates the service?"
            ),
            "deliverable": (
                "Which deliverable or result marks completion?"
            ),
            "creator_side": (
                "Who creates or publishes the main content?"
            ),
            "audience_side": (
                "Who views or interacts with the content?"
            ),
            "moderation_model": (
                "Who moderates content and handles reports?"
            ),
            "critical_contradictions": (
                "Which contradictory details must be corrected?"
            ),
        }

        arabic_questions = {
            "project_name": (
                "ما الاسم الذي تريد استخدامه للمشروع؟"
            ),
            "problem": (
                "ما المشكلة الملموسة والمتكررة والمكلفة "
                "التي تريد حلها؟"
            ),
            "solution": (
                "كيف يحل المنتج هذه المشكلة عملياً؟"
            ),
            "actors": (
                "من سيستخدم الحل، ومن سيدفع، "
                "ومن سيتخذ قرار الشراء؟"
            ),
            "priority_workflow": (
                "ما الإجراء الرئيسي الذي يجب على المستخدم "
                "إكماله من البداية إلى النهاية؟"
            ),
            "target_region": (
                "في أي بلد أو منطقة سيتم إطلاق المشروع؟"
            ),
            "project_archetype": (
                "هل المشروع برنامج، أو سوقاً رقمية، "
                "أو خدمة، أو منتجاً مادياً؟"
            ),
            "business_model": (
                "من سيدفع وما نموذج الإيرادات؟"
            ),
            "mvp_scope": (
                "ما النطاق الدقيق لأول نسخة قابلة للاختبار؟"
            ),
            "constraints": (
                "ما القيود التقنية أو المالية أو التشغيلية "
                "أو التنظيمية المعروفة؟"
            ),
            "success_metrics": (
                "ما المؤشرات التي ستثبت نجاح التجربة؟"
            ),
            "domain_integrity": (
                "ما المجالات القريبة التي يجب استبعادها "
                "من التحليل؟"
            ),
            "archetype_confidence": (
                "ما النوع الرئيسي للمشروع وما المؤشرات التي تثبته؟"
            ),
            "supply_side": (
                "من يوفّر أو يبيع أو ينفّذ العرض الرئيسي؟"
            ),
            "demand_side": (
                "من يبحث عن العرض أو يحجزه أو يشتريه أو يستلمه؟"
            ),
            "transaction_unit": (
                "ما المنتج أو الخدمة أو الحجز أو النتيجة التي تمثل "
                "وحدة القيمة الأساسية؟"
            ),
            "transaction_flow": (
                "كيف تبدأ العملية ومتى تعتبر مكتملة؟"
            ),
            "payment_responsibility": (
                "من يدير الدفع، داخل المنصة أم خارجها؟"
            ),
            "fulfillment_logistics": (
                "من يدير التسليم أو النقل أو تنفيذ الخدمة؟"
            ),
            "trust_mechanism": (
                "كيف سيتم التحقق من الأطراف أو المنتجات أو الخدمات؟"
            ),
            "dispute_responsibility": (
                "من يدير النزاعات والشكاوى والاسترداد؟"
            ),
            "return_refund_policy": (
                "ما سياسة الإرجاع أو الاسترداد أو الضمان؟"
            ),
            "operational_user": (
                "من يستخدم المنتج فعلياً في العمل اليومي؟"
            ),
            "decision_maker": (
                "من يقرر الشراء أو النشر؟"
            ),
            "payer": (
                "من يدفع فعلياً مقابل المنتج أو الاشتراك؟"
            ),
            "deployment_environment": (
                "في أي بيئة مادية سيتم نشر المنتج؟"
            ),
            "maintenance_model": (
                "من يركّب المنتج ويصونه ويصلحه؟"
            ),
            "operational_safety": (
                "ما قيود السلامة والموثوقية والطاقة والاستقلالية؟"
            ),
            "input_data": (
                "ما البيانات أو المعلومات التي تغذي الأداة؟"
            ),
            "output_decision": (
                "ما النتيجة أو التوصية أو القرار الذي تنتجه الأداة؟"
            ),
            "human_oversight": (
                "ما المراجعة البشرية المطلوبة؟"
            ),
            "regulated_provider": (
                "من هو المهني أو الجهة المرخصة التي تقدم الخدمة؟"
            ),
            "beneficiary": (
                "من يستفيد مباشرة من الخدمة؟"
            ),
            "regulatory_scope": (
                "ما القواعد أو التراخيص المطبقة؟"
            ),
            "professional_responsibility": (
                "من يتحمل المسؤولية المهنية النهائية؟"
            ),
            "service_provider": (
                "من ينفذ الخدمة المهنية؟"
            ),
            "service_client": (
                "من يطلب الخدمة ويعتمدها؟"
            ),
            "deliverable": (
                "ما التسليم أو النتيجة التي تنهي المهمة؟"
            ),
            "creator_side": (
                "من ينشئ أو ينشر المحتوى الرئيسي؟"
            ),
            "audience_side": (
                "من يشاهد أو يتفاعل مع المحتوى؟"
            ),
            "moderation_model": (
                "من يدير الإشراف على المحتوى والبلاغات؟"
            ),
            "critical_contradictions": (
                "ما المعلومات المتناقضة التي يجب تصحيحها؟"
            ),
        }

        if language_key == "ar":
            questions = arabic_questions

        elif language_key == "en":
            questions = english_questions

        else:
            questions = french_questions

        return unique_texts(
            questions.get(
                field,
                field,
            )
            for field in fields
            if field
        )[:10]


context_confidence_gate = (
    ContextConfidenceGate()
)