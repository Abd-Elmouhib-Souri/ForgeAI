from __future__ import annotations

from app.schemas.analysis_context import (
    ContextReadinessStatus,
)
from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)


def test_complete_project_uses_canonical_context() -> None:
    result = idea_readiness_checker.evaluate(
        title="GreenWatch Robot",
        description="""
        GreenWatch est un robot autonome pour les propriétaires
        de serres et les coopératives agricoles en Tunisie.

        Le robot inspecte les cultures afin de détecter
        les plantes malades et transmet les résultats
        à un tableau de bord avec une alerte.

        Le problème est que l'inspection manuelle demande
        trop de temps et détecte les anomalies trop tard.

        Les premiers clients ciblés sont les propriétaires
        de serres et les coopératives agricoles.

        Le MVP sera limité à une seule serre.

        Le modèle économique combine la location du robot
        et un abonnement.

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

    assert (
        result["format"]
        == "idea_readiness_v1_context_confidence"
    )

    assert (
        result["canonical_format"]
        == "idea_readiness_v3_project_context"
    )

    assert (
        result["schema_version"]
        == "project_context_v3"
    )

    assert (
        result["ready_for_agents"]
        is True
    )

    assert result["score"] <= 0.94

    assert (
        "project_context_packet"
        in result
    )

    assert (
        "legacy_project_context"
        in result
    )

    assert (
        result["detected"][
            "project_archetype"
        ]
        == "hardware_iot"
    )

    assert (
        "une seule serre"
        in result["detected"][
            "mvp_scope"
        ]
    )


def test_vague_project_is_blocked() -> None:
    result = idea_readiness_checker.evaluate(
        title="Student App",
        description=(
            "Je veux créer une application "
            "pour les étudiants."
        ),
        industry="Éducation",
        target_region="",
        output_language="fr",
    )

    assert (
        result["ready_for_agents"]
        is False
    )

    assert result["status"] in {
        (
            ContextReadinessStatus
            .NEEDS_CLARIFICATION
            .value
        ),
        (
            ContextReadinessStatus
            .INSUFFICIENT_CONTEXT
            .value
        ),
    }

    assert result["blockers"]

    assert result["questions"]


def test_inferred_business_model_is_not_confirmed() -> None:
    result = idea_readiness_checker.evaluate(
        title="FixTrack",
        description="""
        FixTrack permet aux techniciens de maintenance
        de signaler une panne, joindre une photo et suivre
        l'intervention jusqu'à sa résolution.

        Le problème est que les demandes envoyées
        par téléphone sont perdues.

        Les premiers utilisateurs ciblés sont les techniciens,
        les responsables maintenance et les gestionnaires
        de sites.

        Le MVP couvrira un seul site industriel.
        """,
        industry="Maintenance industrielle",
        target_region="Tunisie",
        output_language="fr",
    )

    assert (
        "business_model"
        in result[
            "ambiguous_fields"
        ]
    )

    assert (
        result["detected"][
            "business_model"
        ]
        == ""
    )

    assert (
        result["status"]
        != ContextReadinessStatus
        .READY
        .value
    )

    assert any(
        item["key"]
        == "business_model"
        and item["checked"]
        is False
        for item
        in result["checklist"]
    )


def test_explicit_business_model_is_preserved() -> None:
    result = idea_readiness_checker.evaluate(
        title="ShiftFlow",
        description="""
        ShiftFlow est un logiciel SaaS B2B destiné
        aux responsables RH et aux responsables
        de production en France.

        Le responsable crée les horaires des équipes
        et suit les absences.

        Le problème est que la planification sur Excel
        provoque des conflits d'horaires et beaucoup
        de travail manuel.

        Les premiers clients ciblés sont les PME
        industrielles, les responsables RH
        et les responsables de production.

        Le MVP couvrira une seule usine.

        Le revenu proviendra d'un abonnement mensuel
        par site industriel.
        """,
        industry="Gestion RH et industrie",
        target_region="France",
        output_language="fr",
    )

    assert (
        "business_model"
        not in result[
            "ambiguous_fields"
        ]
    )

    assert (
        "abonnement"
        in result["detected"][
            "business_model"
        ].lower()
    )

    assert (
        result["detected"][
            "main_use_case"
        ]
    )


def test_existing_packet_can_be_reused() -> None:
    first = idea_readiness_checker.evaluate(
        title="TaxiSmart",
        description="""
        TaxiSmart est une application de réservation
        destinée aux passagers et aux chauffeurs
        de taxi en Tunisie.

        Le passager réserve une course et reçoit
        une confirmation.

        Le problème est que les passagers perdent
        du temps à chercher un taxi disponible.

        Les premiers clients ciblés sont les passagers
        urbains, les chauffeurs indépendants
        et les petites flottes de taxis.

        Le MVP sera limité au Grand Tunis.

        Le modèle économique repose sur une commission
        par course.
        """,
        industry="Transport urbain et mobilité",
        target_region="Tunisie",
        output_language="fr",
    )

    second = idea_readiness_checker.evaluate(
        title="TaxiSmart",
        description=(
            first[
                "project_context_packet"
            ][
                "description"
            ]
        ),
        industry="Transport urbain et mobilité",
        target_region="Tunisie",
        output_language="fr",
        analysis_data={
            "project_context_packet": (
                first[
                    "project_context_packet"
                ]
            ),
        },
    )

    assert (
        second[
            "project_context_packet"
        ]
        == first[
            "project_context_packet"
        ]
    )

    assert (
        second[
            "legacy_project_context"
        ][
            "project_name"
        ]
        == "TaxiSmart"
    )