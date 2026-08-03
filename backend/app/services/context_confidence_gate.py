from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from app.schemas.analysis_context import (
    ActorContext,
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
        Retourne une copie du packet contenant la décision du gate.
        """
        confidence = self.evaluate(
            packet
        )

        return packet.model_copy(
            update={
                "confidence": confidence,
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
            confidence = (
                packet_or_confidence.confidence
            )
        else:
            confidence = packet_or_confidence

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
                self.should_run_agents(
                    confidence
                )
            ),
            "missing_fields": list(
                confidence.missing_fields
            ),
            "ambiguous_fields": list(
                confidence.ambiguous_fields
            ),
            "blockers": list(
                confidence.blockers
            ),
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