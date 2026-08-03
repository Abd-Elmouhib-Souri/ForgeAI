from __future__ import annotations

from typing import Iterable

import pytest

from app.schemas.analysis_context import (
    ContextReadinessStatus,
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def normalized_contains(
    values: Iterable[str],
    expected: str,
) -> bool:
    expected_key = comparison_key(expected)

    return any(
        expected_key in comparison_key(value)
        or comparison_key(value) in expected_key
        for value in values
    )


def assert_no_scope_workflow_collision(
    packet,
) -> None:
    scope_keys = {
        comparison_key(value)
        for value in packet.mvp_scope
    }

    workflow_keys = {
        comparison_key(workflow.sentence)
        for workflow in packet.priority_workflows
    }

    assert not scope_keys.intersection(
        workflow_keys
    )


def assert_no_core_forbidden_terms(
    packet,
) -> None:
    core_terms = (
        packet.sector_labels
        + packet.domain_terms
        + packet.use_case_terms
        + packet.solution_terms
        + packet.target_terms
    )

    core_keys = {
        comparison_key(value)
        for value in core_terms
    }

    forbidden_keys = {
        comparison_key(value)
        for value in packet.forbidden_adjacent_domains
    }

    assert not core_keys.intersection(
        forbidden_keys
    )


def test_greenwatch_hardware_context() -> None:
    description = """
    Je souhaite créer GreenWatch Robot, un petit robot autonome destiné
    aux exploitations agricoles et aux serres en Tunisie.

    Le robot se déplace entre les rangées de plantes afin d’inspecter
    régulièrement les cultures.

    Il utilise une caméra, des capteurs environnementaux et un modèle
    d’intelligence artificielle pour détecter les plantes malades,
    les feuilles desséchées et les signes de manque d’eau.

    Il transmet les résultats à un tableau de bord et envoie une alerte.

    Le problème principal est que l’inspection manuelle demande beaucoup
    de temps et détecte parfois les problèmes trop tard.

    Les premiers clients ciblés sont les propriétaires de serres,
    les exploitations agricoles de taille moyenne, les pépinières
    et les coopératives agricoles tunisiennes.

    Le premier MVP sera limité à une seule serre.

    Le modèle économique combine la vente ou la location du robot
    avec un abonnement mensuel.

    Les principales contraintes sont le coût du matériel, la poussière,
    l’humidité, l’autonomie de la batterie et la maintenance.
    """

    packet = project_context_extractor.extract(
        title="GreenWatch Robot",
        description=description,
        industry=(
            "Agriculture intelligente, robotique "
            "et intelligence artificielle"
        ),
        target_region="Tunisie",
        output_language="fr",
    )

    assert packet.primary_archetype == "hardware_iot"

    assert "b2b_workflow_saas" in (
        packet.secondary_archetypes
    )

    assert "analytics_ai_tool" in (
        packet.secondary_archetypes
    )

    actor_names = packet.actor_names()

    assert normalized_contains(
        actor_names,
        "propriétaires de serres",
    )

    assert normalized_contains(
        actor_names,
        "exploitations agricoles de taille moyenne",
    )

    assert normalized_contains(
        actor_names,
        "pépinières",
    )

    assert normalized_contains(
        actor_names,
        "coopératives agricoles tunisiennes",
    )

    assert packet.primary_workflow is not None

    assert (
        packet.primary_workflow.action
        == "inspecter"
    )

    assert normalized_contains(
        [packet.primary_workflow.result],
        "détecter les plantes malades",
    )

    assert normalized_contains(
        packet.mvp_scope,
        "une seule serre",
    )

    assert packet.confidence.score <= 0.94
    assert packet.ready_for_agents is True

    assert packet.confidence.status in {
        ContextReadinessStatus.READY,
        ContextReadinessStatus.READY_CAUTIOUS,
    }

    assert all(
        "problème principal"
        not in comparison_key(
            workflow.sentence
        )
        for workflow in packet.priority_workflows
    )

    assert_no_scope_workflow_collision(
        packet
    )

    assert_no_core_forbidden_terms(
        packet
    )


def test_transport_marketplace_context() -> None:
    description = """
    TaxiSmart est une application mobile de réservation de taxis
    destinée aux passagers et aux chauffeurs de taxi en Tunisie.

    Le passager saisit son point de départ et sa destination,
    demande une course et reçoit une confirmation d’un chauffeur
    disponible.

    Les chauffeurs reçoivent les demandes proches et peuvent les accepter.

    Le problème est que les passagers perdent du temps à chercher
    un taxi disponible et ne connaissent pas toujours le tarif attendu.

    Les premiers clients ciblés sont les passagers urbains,
    les chauffeurs indépendants et les petites flottes de taxis.

    Le MVP sera limité au Grand Tunis.

    Le modèle économique repose sur une commission par course
    et un abonnement optionnel pour les chauffeurs.
    """

    packet = project_context_extractor.extract(
        title="TaxiSmart",
        description=description,
        industry=(
            "Transport urbain et mobilité"
        ),
        target_region="Tunisie",
        output_language="fr",
    )

    assert (
        packet.primary_archetype
        == "two_sided_marketplace"
    )

    actor_names = packet.actor_names()

    assert normalized_contains(
        actor_names,
        "passagers urbains",
    )

    assert normalized_contains(
        actor_names,
        "chauffeurs indépendants",
    )

    assert normalized_contains(
        actor_names,
        "petites flottes de taxis",
    )

    assert packet.primary_workflow is not None

    assert packet.primary_workflow.action in {
        "réserver",
        "commander",
    }

    assert normalized_contains(
        packet.mvp_scope,
        "Grand Tunis",
    )

    assert packet.ready_for_agents is True

    assert_no_scope_workflow_collision(
        packet
    )

    assert_no_core_forbidden_terms(
        packet
    )


def test_b2b_saas_context() -> None:
    description = """
    ShiftFlow est un logiciel SaaS B2B destiné aux responsables RH
    et aux responsables de production des petites usines en France.

    Le responsable crée les horaires des équipes, affecte les employés
    aux postes et suit les absences depuis un tableau de bord.

    Le problème actuel est que la planification est réalisée sur
    des feuilles Excel, ce qui provoque des conflits d’horaires
    et beaucoup de travail manuel.

    Les premiers clients ciblés sont les PME industrielles,
    les responsables RH et les responsables de production.

    Le MVP couvrira la création des horaires, les absences
    et l’export PDF pour une seule usine.

    Le revenu proviendra d’un abonnement mensuel par site industriel.
    """

    packet = project_context_extractor.extract(
        title="ShiftFlow",
        description=description,
        industry="Gestion RH et industrie",
        target_region="France",
        output_language="fr",
    )

    assert (
        packet.primary_archetype
        == "b2b_workflow_saas"
    )

    assert packet.primary_workflow is not None

    assert packet.primary_workflow.action in {
        "planifier",
        "gérer",
        "suivre",
    }

    assert normalized_contains(
        packet.actor_names(),
        "PME industrielles",
    )

    assert normalized_contains(
        packet.actor_names(),
        "responsables RH",
    )

    assert packet.ready_for_agents is True

    assert_no_scope_workflow_collision(
        packet
    )


def test_explicit_actors_override_generic_fallbacks() -> None:
    description = """
    Une plateforme destinée aux responsables de restaurants
    et aux fournisseurs alimentaires en Tunisie.

    Les premiers clients ciblés sont les restaurants indépendants,
    les petites chaînes de restauration et les grossistes alimentaires.

    Le restaurant commande ses produits auprès de fournisseurs vérifiés.

    Le problème est que les commandes sont actuellement réalisées
    par téléphone et sont difficiles à suivre.

    Le revenu provient d’une commission sur chaque commande.
    """

    packet = project_context_extractor.extract(
        title="FoodSupply",
        description=description,
        industry="Approvisionnement alimentaire B2B",
        target_region="Tunisie",
        output_language="fr",
    )

    actor_names = packet.actor_names()

    assert normalized_contains(
        actor_names,
        "restaurants indépendants",
    )

    assert normalized_contains(
        actor_names,
        "petites chaînes de restauration",
    )

    assert normalized_contains(
        actor_names,
        "grossistes alimentaires",
    )

    forbidden_generic_names = {
        "client",
        "clients",
        "client payeur",
        "utilisateur",
        "utilisateur principal",
        "opérateur terrain",
        "acheteur opérationnel",
    }

    assert not {
        comparison_key(value)
        for value in actor_names
    }.intersection(
        {
            comparison_key(value)
            for value in forbidden_generic_names
        }
    )


def test_mvp_scope_is_not_priority_workflow() -> None:
    description = """
    Une application destinée aux étudiants universitaires en Tunisie.

    L’étudiant réserve une séance avec un tuteur et reçoit
    une confirmation dans l’application.

    Le problème est qu’il est difficile de trouver rapidement
    un tuteur disponible dans une matière précise.

    Les premiers utilisateurs ciblés sont les étudiants universitaires
    et les tuteurs indépendants.

    Le premier MVP sera limité à une seule université.

    La plateforme prélèvera une commission sur chaque réservation.
    """

    packet = project_context_extractor.extract(
        title="TutorConnect",
        description=description,
        industry="Éducation et tutorat",
        target_region="Tunisie",
        output_language="fr",
    )

    assert normalized_contains(
        packet.mvp_scope,
        "une seule université",
    )

    assert packet.primary_workflow is not None

    assert (
        comparison_key(
            packet.primary_workflow.sentence
        )
        != comparison_key(
            "une seule université"
        )
    )

    assert_no_scope_workflow_collision(
        packet
    )


def test_core_terms_never_become_forbidden() -> None:
    description = """
    Un robot agricole autonome inspecte les plantes dans une serre,
    détecte les maladies et envoie des alertes.

    Les premiers clients ciblés sont les propriétaires de serres.

    Le problème est que l’inspection manuelle est lente.

    Le MVP sera limité à une serre.
    """

    packet = project_context_extractor.extract(
        title="AgriRobot",
        description=description,
        industry="Robotique agricole",
        target_region="Tunisie",
        output_language="fr",
        project_context={
            "forbidden_adjacent_domains": [
                "robot agricole",
                "cryptomonnaie",
            ]
        },
    )

    forbidden_keys = {
        comparison_key(value)
        for value in packet.forbidden_adjacent_domains
    }

    assert (
        comparison_key(
            "robot agricole"
        )
        not in forbidden_keys
    )

    assert (
        comparison_key(
            "cryptomonnaie"
        )
        in forbidden_keys
    )

    assert_no_core_forbidden_terms(
        packet
    )


def test_vague_idea_requires_clarification() -> None:
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

    assert packet.ready_for_agents is False

    assert packet.confidence.status in {
        ContextReadinessStatus.NEEDS_CLARIFICATION,
        ContextReadinessStatus.INSUFFICIENT_CONTEXT,
    }

    assert packet.confidence.missing_fields

    assert "target_region" in (
        packet.confidence.ambiguous_fields
    )

    assert (
        packet.confidence.clarification_questions
    )


def test_missing_business_model_can_be_ready_cautious() -> None:
    description = """
    Une application permet aux techniciens de maintenance
    de signaler une panne, joindre une photo et suivre
    l’intervention jusqu’à sa résolution.

    Le problème est que les demandes sont actuellement envoyées
    par téléphone et sont souvent perdues.

    Les premiers utilisateurs ciblés sont les techniciens,
    les responsables maintenance et les gestionnaires de sites.

    Le MVP couvrira un seul site industriel.
    """

    packet = project_context_extractor.extract(
        title="FixTrack",
        description=description,
        industry="Maintenance industrielle",
        target_region="Tunisie",
        output_language="fr",
    )

    assert "business_model" in (
        packet.confidence.ambiguous_fields
    )

    assert packet.confidence.score < 0.94

    assert packet.confidence.status in {
        ContextReadinessStatus.READY_CAUTIOUS,
        ContextReadinessStatus.NEEDS_CLARIFICATION,
    }


@pytest.mark.parametrize(
    (
        "title",
        "description",
        "industry",
        "region",
    ),
    [
        (
            "HealthConnect",
            """
            Une plateforme permet aux patients de réserver
            une consultation auprès d’un médecin.

            Le problème est le délai nécessaire pour trouver
            un rendez-vous disponible.

            Les premiers utilisateurs sont les patients,
            les médecins et les cliniques privées.

            Le MVP sera limité à une ville.

            La plateforme prélèvera une commission.
            """,
            "Santé numérique",
            "Tunisie",
        ),
        (
            "ShopLocal",
            """
            Une boutique en ligne permet aux artisans locaux
            de publier leurs produits et aux consommateurs
            de les commander.

            Le problème est le manque de visibilité des artisans.

            Les premiers utilisateurs sont les artisans
            et les consommateurs urbains.

            Le MVP sera limité à une région.

            Le revenu proviendra d’une commission.
            """,
            "Commerce électronique",
            "France",
        ),
    ],
)
def test_context_packet_general_invariants(
    title: str,
    description: str,
    industry: str,
    region: str,
) -> None:
    packet = project_context_extractor.extract(
        title=title,
        description=description,
        industry=industry,
        target_region=region,
        output_language="fr",
    )

    assert packet.schema_version == (
        "project_context_v3"
    )

    assert packet.project_name == title

    assert packet.language == "fr"

    assert packet.confidence.score <= 0.94

    assert_no_scope_workflow_collision(
        packet
    )

    assert_no_core_forbidden_terms(
        packet
    )