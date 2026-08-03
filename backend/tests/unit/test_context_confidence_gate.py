from __future__ import annotations

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ContextReadinessStatus,
    ProblemContext,
    ProjectContextPacketV3,
    SolutionContext,
    WorkflowContext,
)
from app.services.context_confidence_gate import (
    context_confidence_gate,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def test_complete_context_can_run_agents() -> None:
    packet = project_context_extractor.extract(
        title="GreenWatch Robot",
        description="""
        GreenWatch est un robot autonome pour les propriétaires de serres
        et les coopératives agricoles en Tunisie.

        Le robot inspecte les cultures afin de détecter les plantes malades
        et transmet les résultats à un tableau de bord avec une alerte.

        Le problème est que l'inspection manuelle demande trop de temps
        et détecte les anomalies trop tard.

        Les premiers clients ciblés sont les propriétaires de serres
        et les coopératives agricoles.

        Le MVP sera limité à une seule serre.

        Le modèle économique combine la location du robot et un abonnement.

        Les contraintes principales sont le coût du matériel,
        l'autonomie et la maintenance.
        """,
        industry=(
            "Agriculture intelligente "
            "et robotique"
        ),
        target_region="Tunisie",
        output_language="fr",
    )

    evaluated = (
        context_confidence_gate.apply(
            packet
        )
    )

    assert (
        context_confidence_gate
        .should_run_agents(
            evaluated
        )
        is True
    )

    assert (
        evaluated.confidence.status
        in {
            ContextReadinessStatus.READY,
            ContextReadinessStatus.READY_CAUTIOUS,
        }
    )

    assert (
        evaluated.confidence.score
        <= 0.94
    )

    assert not (
        evaluated.confidence.blockers
    )


def test_vague_idea_is_blocked() -> None:
    packet = project_context_extractor.extract(
        title="Student App",
        description=(
            "Je veux créer une application "
            "pour les étudiants."
        ),
        industry="Éducation",
        target_region="",
        output_language="fr",
    )

    evaluated = (
        context_confidence_gate.apply(
            packet
        )
    )

    assert (
        context_confidence_gate
        .should_run_agents(
            evaluated
        )
        is False
    )

    assert (
        evaluated.confidence.status
        in {
            ContextReadinessStatus.NEEDS_CLARIFICATION,
            ContextReadinessStatus.INSUFFICIENT_CONTEXT,
        }
    )

    assert (
        evaluated.confidence.blockers
    )

    assert (
        evaluated
        .confidence
        .clarification_questions
    )


def test_missing_business_model_is_ready_cautious_at_best() -> None:
    packet = project_context_extractor.extract(
        title="FixTrack",
        description="""
        FixTrack permet aux techniciens de maintenance de signaler une panne,
        joindre une photo et suivre l'intervention jusqu'à sa résolution.

        Le problème est que les demandes envoyées par téléphone sont perdues.

        Les premiers utilisateurs ciblés sont les techniciens,
        les responsables maintenance et les gestionnaires de sites.

        Le MVP couvrira un seul site industriel.
        """,
        industry="Maintenance industrielle",
        target_region="Tunisie",
        output_language="fr",
    )

    evaluated = (
        context_confidence_gate.apply(
            packet
        )
    )

    assert (
        "business_model"
        in evaluated
        .confidence
        .ambiguous_fields
    )

    assert (
        evaluated.confidence.status
        != ContextReadinessStatus.READY
    )


def test_regulated_project_without_region_is_blocked() -> None:
    packet = ProjectContextPacketV3(
        project_name="HealthConnect",
        description=(
            "Plateforme de réservation médicale."
        ),
        language="fr",
        target_region="",
        industry_user_input="Santé numérique",
        primary_archetype="regulated_service",
        risk_domains=[
            "health",
        ],
        regulatory_flags=[
            "health",
        ],
        problem=ProblemContext(
            pain=(
                "Les patients attendent longtemps "
                "pour trouver un rendez-vous "
                "médical disponible."
            ),
        ),
        solution=SolutionContext(
            mechanism=(
                "Une plateforme permet de rechercher "
                "un médecin et réserver un rendez-vous."
            ),
            delivery_mode="web_saas",
        ),
        actors=[
            ActorContext(
                name="patients",
                role=ActorRole.USER,
                is_explicit=True,
            ),
            ActorContext(
                name="médecins",
                role=ActorRole.PROVIDER,
                is_explicit=True,
            ),
        ],
        priority_workflows=[
            WorkflowContext(
                name=(
                    "réserver un rendez-vous médical"
                ),
                actor="patients",
                action="réserver",
                object="un rendez-vous médical",
                result=(
                    "obtenir une confirmation"
                ),
                is_explicit=True,
                confidence=0.90,
            ),
        ],
        mvp_scope=[
            "une spécialité médicale",
        ],
        business_model_hypotheses=[
            "commission par réservation",
        ],
    )

    evaluated = (
        context_confidence_gate.apply(
            packet
        )
    )

    assert (
        context_confidence_gate
        .should_run_agents(
            evaluated
        )
        is False
    )

    assert (
        "target_region"
        in evaluated
        .confidence
        .blockers
    )

    assert (
        evaluated.confidence.status
        == ContextReadinessStatus.NEEDS_CLARIFICATION
    )


def test_runtime_payload_preserves_legacy_compatibility() -> None:
    packet = ProjectContextPacketV3(
        project_name="SimpleFlow",
        description=(
            "Outil de gestion de demandes internes."
        ),
        target_region="France",
        industry_user_input="SaaS B2B",
        primary_archetype="b2b_workflow_saas",
        problem=ProblemContext(
            pain=(
                "Les demandes internes sont perdues "
                "dans les échanges par email."
            ),
        ),
        solution=SolutionContext(
            mechanism=(
                "Un outil centralise les demandes "
                "et leur suivi."
            ),
            delivery_mode="web_saas",
        ),
        actors=[
            ActorContext(
                name="responsables opérationnels",
                role=ActorRole.USER,
                is_explicit=True,
            ),
        ],
        priority_workflows=[
            WorkflowContext(
                name=(
                    "suivre une demande jusqu'à "
                    "sa résolution"
                ),
                actor="responsables opérationnels",
                action="suivre",
                object="une demande",
                result="obtenir sa résolution",
                is_explicit=True,
                confidence=0.90,
            ),
        ],
        mvp_scope=[
            "un seul service",
        ],
        business_model_hypotheses=[
            "abonnement mensuel",
        ],
    )

    payload = (
        context_confidence_gate
        .to_runtime_payload(
            packet
        )
    )

    assert (
        payload["format"]
        == "context_confidence_gate_v1"
    )

    assert (
        "project_context_packet"
        in payload
    )

    assert (
        "legacy_project_context"
        in payload
    )

    assert (
        payload[
            "legacy_project_context"
        ][
            "project_name"
        ]
        == "SimpleFlow"
    )