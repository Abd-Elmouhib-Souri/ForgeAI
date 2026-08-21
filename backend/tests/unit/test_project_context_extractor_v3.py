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

    # Preserve the explicit user workflow action rather than
    # manufacturing a booking verb from the nominal project
    # description ("reservation de taxis").
    assert packet.primary_workflow.action == "demander"
    assert packet.primary_workflow.object == "une course"

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

def test_explicit_action_chains_exclude_scope_and_constraint_sentences() -> None:
    cases = [
        {
            "title": "Inspection Device",
            "industry": "Industrial inspection",
            "region": "France",
            "description": (
                "Technicians inspect machines with a camera, "
                "detect anomalies, then send results to a dashboard. "
                "The MVP covers one production line and detects "
                "three defect categories. "
                "Constraints include battery autonomy, connectivity "
                "and maintenance."
            ),
            "required": (
                "inspect machines",
                "detect anomalies",
                "send results",
            ),
            "forbidden": (
                "three defect categories",
                "battery autonomy",
            ),
        },
        {
            "title": "InvoiceFlow",
            "industry": "B2B SaaS",
            "region": "Europe",
            "description": (
                "Accountants upload invoices, review extracted data, "
                "then approve or reject each invoice. "
                "The MVP supports PDF, PNG and JPEG files. "
                "Constraints include processing latency, auditability "
                "and integration cost."
            ),
            "required": (
                "upload invoices",
                "review extracted data",
                "approve or reject each invoice",
            ),
            "forbidden": (
                "supports pdf",
                "processing latency",
            ),
        },
        {
            "title": "CareBooking",
            "industry": "Healthcare services",
            "region": "Europe",
            "description": (
                "Patients request an appointment, choose an available "
                "slot, then receive a confirmation. "
                "The first pilot covers one clinic and three specialties. "
                "Constraints include staff availability, privacy "
                "and scheduling capacity."
            ),
            "required": (
                "request an appointment",
                "choose an available slot",
                "receive a confirmation",
            ),
            "forbidden": (
                "pilot covers one clinic",
                "scheduling capacity",
            ),
        },
    ]

    for case in cases:
        packet = project_context_extractor.extract(
            title=case["title"],
            description=case["description"],
            industry=case["industry"],
            target_region=case["region"],
            output_language="en",
        )

        workflow_text = " | ".join(
            comparison_key(
                workflow.sentence
            )
            for workflow
            in packet.priority_workflows
        )

        for expected in case["required"]:
            assert (
                comparison_key(expected)
                in workflow_text
            ), (
                case["title"],
                expected,
                workflow_text,
            )

        for forbidden in case["forbidden"]:
            assert (
                comparison_key(forbidden)
                not in workflow_text
            ), (
                case["title"],
                forbidden,
                workflow_text,
            )

        for workflow in packet.priority_workflows:
            workflow_key = comparison_key(
                workflow.sentence
            )

            assert not workflow_key.endswith(
                " then"
            )

            assert not workflow_key.endswith(
                " puis"
            )

            object_key = comparison_key(
                workflow.object
            )
            output_key = comparison_key(
                workflow.output
            )

            if object_key and output_key:
                assert output_key not in object_key

        assert_no_scope_workflow_collision(
            packet
        )

def test_action_word_inside_existing_action_object_does_not_split_workflow() -> None:
    packet = project_context_extractor.extract(
        title="AccessFlow",
        description=(
            "Reviewers approve access requests and notify users "
            "when access changes. "
            "The MVP supports one team. "
            "Constraints include auditability."
        ),
        industry="Workflow software",
        target_region="Europe",
        output_language="en",
    )

    workflows = packet.priority_workflows

    assert any(
        workflow.action == "approve"
        and "access request"
        in workflow.object.lower()
        for workflow in workflows
    )

    assert any(
        workflow.action == "notify"
        and "access change"
        in workflow.object.lower()
        for workflow in workflows
    )

    assert not any(
        workflow.action == "request"
        for workflow in workflows
    )

    assert_no_scope_workflow_collision(
        packet
    )

def test_scope_labels_preserve_real_actor_actions_but_block_scope_subjects() -> None:
    cases = (
        (
            "For the MVP, operators upload invoices and approve them.",
            False,
            {"importer", "approuver"},
        ),
        (
            "The MVP lets users upload invoices and approve them.",
            False,
            {"importer", "approuver"},
        ),
        (
            "Pilot users inspect machines and send results.",
            False,
            {"inspecter", "transmettre"},
        ),
        (
            "The MVP covers one production line and detects three defect categories.",
            True,
            {"d\u00e9tecter"},
        ),
        (
            "The MVP detects three defect categories.",
            True,
            {"d\u00e9tecter"},
        ),
    )

    for sentence, expected_blocked, expected_actions in cases:
        blocked = (
            project_context_extractor
            ._workflow_sentence_is_non_action_context(
                sentence
            )
        )

        occurrences = (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )

        actions = {
            item["action"]
            for item in occurrences
        }

        assert blocked is expected_blocked, sentence

        assert expected_actions.issubset(
            actions
        ), (
            sentence,
            expected_actions,
            actions,
        )

def test_constraint_declarations_with_determiners_never_become_workflows() -> None:
    constraint_sentences = (
        (
            "The main constraints are detection accuracy, "
            "connectivity and maintenance."
        ),
        (
            "Les contraintes principales sont la precision de la "
            "d\u00e9tection, la connectivit\u00e9 et la maintenance."
        ),
        (
            "Les principales contraintes sont la disponibilite, "
            "la securite et la maintenance."
        ),
    )

    for sentence in constraint_sentences:
        assert (
            project_context_extractor
            ._workflow_sentence_is_non_action_context(
                sentence
            )
            is True
        ), sentence

    packet = project_context_extractor.extract(
        title="InspectionFlow",
        description=(
            "Technicians inspect equipment and send results. "
            "Les contraintes principales sont la precision de la "
            "d\u00e9tection, la connectivit\u00e9 et la maintenance."
        ),
        industry="Industrial operations",
        target_region="Europe",
        output_language="en",
    )

    workflow_text = comparison_key(
        " | ".join(
            workflow.sentence
            for workflow in packet.priority_workflows
        )
    )

    assert (
        comparison_key("inspect equipment")
        in workflow_text
    )

    assert (
        comparison_key("connectivite")
        not in workflow_text
    )

    assert (
        comparison_key("maintenance")
        not in workflow_text
    )

def test_actor_descriptive_clause_boundary_is_universal() -> None:
    cases = (
        (
            (
                "les particuliers en R\u00e9publique tch\u00e8que "
                "qui ont besoin de petites r\u00e9parations "
                "\u00e0 domicile"
            ),
            "particuliers en R\u00e9publique tch\u00e8que",
        ),
        (
            (
                "the warehouse operators who manage "
                "inbound shipments every day"
            ),
            "warehouse operators",
        ),
        (
            (
                "des techniciens de maintenance ayant besoin "
                "d'un suivi en temps r\u00e9el"
            ),
            "techniciens de maintenance",
        ),
    )

    for raw_value, expected in cases:
        actual = (
            project_context_extractor
            ._clean_actor(
                raw_value
            )
        )

        assert (
            comparison_key(actual)
            == comparison_key(expected)
        )


def test_descriptive_target_clause_never_overflows_actor_context() -> None:
    description = (
        "HomeService est une marketplace numerique destinee aux "
        "particuliers en R\u00e9publique tch\u00e8que qui ont besoin "
        "de petites reparations \u00e0 domicile : montage de meubles, "
        "remplacement d'un robinet, reparation d'une porte, "
        "installation d'une lampe ou autres petits travaux. "
        "La plateforme permet aux clients de publier une demande, "
        "recevoir des propositions de professionnels verifies, "
        "choisir un prestataire, reserver un creneau et payer via "
        "la plateforme. "
        "Le probleme principal est la difficulte a trouver rapidement "
        "un professionnel disponible et fiable. "
        "Le modele economique repose sur une commission par transaction."
    )

    packet = project_context_extractor.extract(
        title="HomeService",
        description=description,
        industry="Marketplace de services",
        target_region="Europe",
        output_language="fr",
    )

    actor_names = packet.actor_names()

    actor_keys = {
        comparison_key(value)
        for value in actor_names
    }

    assert (
        comparison_key(
            "particuliers en R\u00e9publique tch\u00e8que"
        )
        in actor_keys
    )

    assert all(
        len(actor.name) <= 180
        for actor in packet.actors
    )

    assert all(
        "montage de meubles"
        not in comparison_key(actor.name)
        for actor in packet.actors
    )

    assert all(
        "remplacement d'un robinet"
        not in comparison_key(actor.name)
        for actor in packet.actors
    )


def test_unbounded_actor_candidate_is_rejected_not_truncated() -> None:
    raw_value = (
        "responsables op\u00e9rationnels "
        + (
            "avec une description metier extremement longue "
            * 12
        )
    )

    assert len(raw_value) > 180

    cleaned = (
        project_context_extractor
        ._clean_actor(
            raw_value
        )
    )

    assert cleaned == ""


def test_payer_declarations_are_bidirectional_and_bilingual() -> None:
    cases = (
        (
            (
                "The primary payer is "
                "the private customer."
            ),
            "private customer",
        ),
        (
            (
                "The private customer is "
                "the primary payer."
            ),
            "private customer",
        ),
        (
            (
                "Le payeur principal est "
                "le client particulier."
            ),
            "client particulier",
        ),
        (
            (
                "Le client particulier est "
                "le payeur principal."
            ),
            "client particulier",
        ),
    )

    for sentence, expected_name in cases:
        resolved = (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )

        assert len(resolved) == 1

        name, role = resolved[0]

        assert (
            name.casefold()
            == expected_name.casefold()
        )

        assert role.value == "payer"


def test_explicit_actor_first_payer_reaches_canonical_packet() -> None:
    description = (
        "La solution est destin\u00e9e aux techniciens "
        "qui supervisent les op\u00e9rations terrain. "
        "Le responsable du site est le payeur principal."
    )

    packet = project_context_extractor.extract(
        title="FieldOps",
        description=description,
        industry="services operationnels",
        target_region="Europe",
        output_language="fr",
    )

    assert any(
        actor.name.casefold()
        == "responsable du site"
        and actor.role.value == "payer"
        and actor.is_explicit
        for actor in packet.actors
    )

    assert any(
        value.casefold()
        == "responsable du site"
        for value in packet.payer_actor_names
    )


def test_explicit_actor_group_declarations_are_bilingual_and_structural() -> None:
    cases = (
        (
            (
                "Les deux groupes d'utilisateurs sont "
                "les m\u00e9nages et les prestataires de services."
            ),
            "m\u00e9nages",
            "prestataires de services",
        ),
        (
            (
                "The user groups are households "
                "and service providers."
            ),
            "households",
            "service providers",
        ),
    )

    for sentence, demand_name, supply_name in cases:
        declared = (
            project_context_extractor
            ._declared_actor_groups(
                sentence
            )
        )

        roles = {
            comparison_key(name): role.value
            for name, role in declared
        }

        assert (
            roles[
                comparison_key(demand_name)
            ]
            == "user"
        )

        assert (
            roles[
                comparison_key(supply_name)
            ]
            == "provider"
        )


def test_actor_group_declaration_populates_transaction_sides() -> None:
    description = (
        "ServiceLink est une marketplace de services. "
        "Les deux groupes d'utilisateurs sont les m\u00e9nages "
        "et les prestataires de services. "
        "Les m\u00e9nages publient une demande puis "
        "r\u00e9servent un service. "
        "Le probl\u00e8me est la difficult\u00e9 \u00e0 trouver "
        "rapidement un prestataire disponible. "
        "La plateforme facilite la mise en relation et la "
        "r\u00e9servation. "
        "Le mod\u00e8le \u00e9conomique est une commission."
    )

    packet = project_context_extractor.extract(
        title="ServiceLink",
        description=description,
        industry="marketplace de services",
        target_region="Europe",
        output_language="fr",
    )

    assert any(
        actor.role.value == "user"
        and "m\u00e9nages"
        in actor.name.casefold()
        for actor in packet.actors
    )

    assert any(
        actor.role.value == "provider"
        and "prestataire"
        in actor.name.casefold()
        for actor in packet.actors
    )

    assert (
        packet.transaction_unit
        .demand_actor
    )

    assert (
        packet.transaction_unit
        .supply_actor
    )

    assert (
        packet.transaction_unit
        .has_two_sides
        is True
    )


def test_actor_group_parser_rejects_predicates_as_actor_lists() -> None:
    sentences = (
        (
            "Les utilisateurs sont responsables "
            "de confirmer la r\u00e9servation."
        ),
        (
            "Users are able to book and pay online."
        ),
        (
            "The actors are responsible for support."
        ),
    )

    for sentence in sentences:
        assert (
            project_context_extractor
            ._declared_actor_groups(
                sentence
            )
            == []
        )



def test_actor_coordination_distinguishes_modifiers_from_actor_groups() -> None:
    cases = (
        (
            "petites et moyennes entreprises alg\u00e9riennes",
            (
                "petites et moyennes entreprises alg\u00e9riennes",
            ),
        ),
        (
            "small and medium businesses",
            (
                "small and medium businesses",
            ),
        ),
        (
            "responsables de flotte et responsables logistiques",
            (
                "responsables de flotte",
                "responsables logistiques",
            ),
        ),
        (
            "clients et prestataires",
            (
                "clients",
                "prestataires",
            ),
        ),
        (
            "buyers and sellers",
            (
                "buyers",
                "sellers",
            ),
        ),
        (
            (
                "dirigeants de petites et moyennes "
                "entreprises"
            ),
            (
                (
                    "dirigeants de petites et moyennes "
                    "entreprises"
                ),
            ),
        ),
    )

    for raw_value, expected in cases:
        actual = (
            project_context_extractor
            ._split_actor_list(
                raw_value
            )
        )

        assert [
            comparison_key(
                value
            )
            for value in actual
        ] == [
            comparison_key(
                value
            )
            for value in expected
        ]


def test_multi_role_payer_declarations_are_bilingual() -> None:
    cases = (
        (
            (
                "L'entreprise propri\u00e9taire de la flotte "
                "est le client et le payeur principal."
            ),
            "entreprise propri\u00e9taire de la flotte",
        ),
        (
            (
                "La soci\u00e9t\u00e9 cliente est "
                "l'acheteur et le payeur principal."
            ),
            "soci\u00e9t\u00e9 cliente",
        ),
        (
            (
                "The fleet-owning company is "
                "the customer and primary payer."
            ),
            "fleet-owning company",
        ),
        (
            (
                "The operating company is "
                "the buyer and the primary payer."
            ),
            "operating company",
        ),
    )

    for sentence, expected_name in cases:
        declared = (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )

        payer_names = [
            name
            for name, role in declared
            if role.value == "payer"
        ]

        assert any(
            comparison_key(name)
            == comparison_key(expected_name)
            for name in payer_names
        )


def test_b2b_compound_target_and_multi_role_payer_reach_packet() -> None:
    description = (
        "FleetOps est une solution SaaS destin\u00e9e aux "
        "petites et moyennes entreprises alg\u00e9riennes. "
        "Les utilisateurs principaux sont les responsables "
        "de flotte et les responsables logistiques. "
        "L'entreprise propri\u00e9taire de la flotte est "
        "le client et le payeur principal. "
        "Le probl\u00e8me principal est la dispersion des "
        "informations de maintenance. "
        "La solution centralise le suivi des op\u00e9rations."
    )

    packet = project_context_extractor.extract(
        title="FleetOps",
        description=description,
        industry="SaaS B2B",
        target_region="Alg\u00e9rie",
        output_language="fr",
    )

    actor_keys = {
        comparison_key(
            actor.name
        )
        for actor in packet.actors
    }

    assert (
        comparison_key(
            "petites et moyennes entreprises alg\u00e9riennes"
        )
        in actor_keys
    )

    assert (
        comparison_key(
            "petites"
        )
        not in actor_keys
    )

    assert any(
        comparison_key(
            actor.name
        )
        == comparison_key(
            "entreprise propri\u00e9taire de la flotte"
        )
        and actor.role.value == "payer"
        for actor in packet.actors
    )

    assert any(
        comparison_key(
            payer
        )
        == comparison_key(
            "entreprise propri\u00e9taire de la flotte"
        )
        for payer in packet.payer_actor_names
    )



def test_primary_user_declaration_and_workflow_actor_ownership_are_universal() -> None:
    description = (
        "Les utilisateurs principaux sont les op\u00e9rateurs "
        "et les administrateurs. "
        "L'entreprise est le payeur principal. "
        "L'op\u00e9rateur enregistre une demande. "
        "L'administrateur approuve le dossier. "
        "Le syst\u00e8me envoie une alerte."
    )

    packet = project_context_extractor.extract(
        title="WorkflowRoles",
        description=description,
        industry="logiciel",
        target_region="Europe",
        output_language="fr",
    )

    actor_keys = {
        comparison_key(actor.name): actor.role.value
        for actor in packet.actors
    }

    assert (
        comparison_key("op\u00e9rateurs")
        in actor_keys
    )

    assert (
        comparison_key("administrateurs")
        in actor_keys
    )

    # A structural "primary users" declaration proves actor
    # membership but must not erase a more precise canonical role.
    assert (
        actor_keys[
            comparison_key("op\u00e9rateurs")
        ]
        == "operator"
    )

    assert any(
        comparison_key(actor.name)
        == comparison_key("entreprise")
        and actor.role.value == "payer"
        for actor in packet.actors
    )

    workflows = packet.priority_workflows

    by_action = {
        workflow.action: workflow
        for workflow in workflows
    }

    assert (
        comparison_key(
            by_action["enregistrer"].actor
        )
        == comparison_key("op\u00e9rateurs")
    )

    assert (
        comparison_key(
            by_action["approuver"].actor
        )
        == comparison_key("administrateurs")
    )

    assert (
        comparison_key(
            by_action["transmettre"].actor
        )
        == comparison_key("syst\u00e8me")
    )

    assert all(
        comparison_key(workflow.actor)
        != comparison_key("entreprise")
        for workflow in workflows
    )


def test_primary_user_declaration_is_bilingual_and_structural() -> None:
    cases = (
        (
            (
                "Les utilisateurs principaux sont "
                "les techniciens et les superviseurs."
            ),
            (
                "techniciens",
                "superviseurs",
            ),
        ),
        (
            (
                "The primary users are "
                "technicians and supervisors."
            ),
            (
                "technicians",
                "supervisors",
            ),
        ),
    )

    for sentence, expected in cases:
        declared = (
            project_context_extractor
            ._declared_actor_groups(
                sentence
            )
        )

        actual = {
            comparison_key(name): role.value
            for name, role in declared
        }

        for name in expected:
            assert (
                comparison_key(name)
                in actual
            )


def test_workflow_actor_resolution_does_not_assign_payer_globally() -> None:
    description = (
        "The primary users are operators and reviewers. "
        "The company is the primary payer. "
        "The operators record a request. "
        "The reviewers approve the request. "
        "The system sends a confirmation."
    )

    packet = project_context_extractor.extract(
        title="RoleOwnership",
        description=description,
        industry="workflow software",
        target_region="Europe",
        output_language="en",
    )

    workflows = packet.priority_workflows

    assert workflows

    assert all(
        comparison_key(workflow.actor)
        != comparison_key("company")
        for workflow in workflows
    )

    assert any(
        comparison_key(workflow.actor)
        == comparison_key("operators")
        for workflow in workflows
    )

    assert any(
        comparison_key(workflow.actor)
        == comparison_key("reviewers")
        for workflow in workflows
    )

    assert any(
        comparison_key(workflow.actor)
        == comparison_key("system")
        for workflow in workflows
    )



def test_inferred_workflow_never_becomes_implicit_mvp_scope() -> None:
    """
    A workflow can be explicit and actionable without implying that
    the user has defined an MVP.
    """
    from app.services.project_intelligence_layer import (
        project_intelligence_layer,
    )

    cases = (
        (
            "en",
            (
                "The primary users are operators and reviewers. "
                "The company is the primary payer. "
                "The operators record a request. "
                "The reviewers approve the request. "
                "The system sends a confirmation."
            ),
        ),
        (
            "fr",
            (
                "Les utilisateurs principaux sont les op\u00e9rateurs "
                "et les superviseurs. "
                "L'entreprise est le payeur principal. "
                "Les op\u00e9rateurs enregistrent une demande. "
                "Le syst\u00e8me envoie une confirmation."
            ),
        ),
    )

    for language, description in cases:
        intelligence = project_intelligence_layer.build(
            title="WorkflowOnly",
            description=description,
            industry="workflow software",
            target_region="Europe",
            output_language=language,
        )

        structured = (
            intelligence.get(
                "structured_project_context"
            )
            or {}
        )

        assert not structured.get(
            "mvp_scope"
        )


def test_missing_mvp_does_not_swallow_valid_workflow() -> None:
    description = (
        "The primary users are operators and reviewers. "
        "The company is the primary payer. "
        "The operators record a request. "
        "The reviewers approve the request. "
        "The system sends a confirmation."
    )

    packet = project_context_extractor.extract(
        title="RoleOwnership",
        description=description,
        industry="workflow software",
        target_region="Europe",
        output_language="en",
    )

    assert packet.mvp_scope == []

    workflows = packet.priority_workflows

    assert any(
        comparison_key(workflow.actor)
        == comparison_key("operators")
        and workflow.action == "record"
        for workflow in workflows
    )

    assert any(
        comparison_key(workflow.actor)
        == comparison_key("reviewers")
        and workflow.action == "approve"
        for workflow in workflows
    )

    assert any(
        comparison_key(workflow.actor)
        == comparison_key("system")
        and workflow.action == "send"
        for workflow in workflows
    )


def test_explicit_mvp_remains_available_when_user_declares_it() -> None:
    description = (
        "The primary users are operators. "
        "The operators record requests. "
        "The first version includes invoice management."
    )

    packet = project_context_extractor.extract(
        title="ExplicitMVP",
        description=description,
        industry="workflow software",
        target_region="Europe",
        output_language="en",
    )

    assert packet.mvp_scope

    serialized_scope = " ".join(
        comparison_key(item)
        for item in packet.mvp_scope
    )

    assert "invoice" in serialized_scope



def test_nominal_action_surfaces_do_not_become_workflows() -> None:
    """
    Ambiguous noun surfaces must not be promoted to their homonymous
    workflow action.

    A sentence may still contain another genuine verb, including a
    passive verb such as "recorded" or "sent".
    """
    nominal_cases = (
        (
            "Une alerte est affich\u00e9e.",
            "alerter",
            "alerte",
        ),
        (
            "Le suivi GPS est disponible.",
            "suivre",
            "suivi",
        ),
        (
            "Une demande est enregistr\u00e9e.",
            "demander",
            "demande",
        ),
        (
            "La r\u00e9servation est confirm\u00e9e.",
            "r\u00e9server",
            "r\u00e9servation",
        ),
        (
            "La surveillance est continue.",
            "surveiller",
            "surveillance",
        ),
        (
            "Une notification est envoy\u00e9e.",
            "alerter",
            "notification",
        ),
        (
            "An alert is displayed.",
            "alerter",
            "alert",
        ),
        (
            "The monitoring is continuous.",
            "surveiller",
            "monitoring",
        ),
        (
            "A request is recorded.",
            "demander",
            "request",
        ),
        (
            "A booking is confirmed.",
            "r\u00e9server",
            "booking",
        ),
        (
            "A notification is sent.",
            "alerter",
            "notification",
        ),
    )

    for (
        sentence,
        forbidden_action,
        forbidden_surface,
    ) in nominal_cases:
        occurrences = (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )

        assert not any(
            item["action"] == forbidden_action
            and comparison_key(item["surface"])
            == comparison_key(forbidden_surface)
            for item in occurrences
        ), (
            sentence,
            [
                (
                    item["action"],
                    item["surface"],
                )
                for item in occurrences
            ],
        )


def test_ambiguous_action_surfaces_remain_verbs_in_predicate_position() -> None:
    verbal_cases = (
        (
            "Le syst\u00e8me alerte l'utilisateur.",
            "alerter",
        ),
        (
            "L'op\u00e9rateur suit le dossier.",
            "suivre",
        ),
        (
            "Le client demande une validation.",
            "demander",
        ),
        (
            "Le client r\u00e9serve un cr\u00e9neau.",
            "r\u00e9server",
        ),
        (
            "Le syst\u00e8me surveille la temp\u00e9rature.",
            "surveiller",
        ),
        (
            "Le syst\u00e8me notifie l'utilisateur.",
            "alerter",
        ),
        (
            "The system alerts the user.",
            "alerter",
        ),
        (
            "The operator monitors the process.",
            "surveiller",
        ),
        (
            "The customer requests approval.",
            "demander",
        ),
        (
            "The customer books a slot.",
            "r\u00e9server",
        ),
        (
            "The system notifies the user.",
            "alerter",
        ),
        (
            "The system notified the user.",
            "alerter",
        ),
        (
            "The system is notifying the user.",
            "alerter",
        ),
    )

    for sentence, expected_action in verbal_cases:
        occurrences = (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )

        assert any(
            item["action"]
            == expected_action
            for item in occurrences
        ), (
            sentence,
            [
                (
                    item["action"],
                    item["surface"],
                )
                for item in occurrences
            ],
        )


def test_transmitted_alert_remains_one_complete_workflow_action() -> None:
    cases = (
        (
            "Le syst\u00e8me envoie une alerte.",
            "transmettre",
            "une alerte",
        ),
        (
            "The system sends an alert.",
            "send",
            "an alert",
        ),
    )

    for sentence, expected_action, expected_object in cases:
        packet = project_context_extractor.extract(
            title="NotificationFlow",
            description=sentence,
            industry="logiciel",
            target_region="Europe",
            output_language=(
                "fr"
                if sentence.startswith("Le ")
                else "en"
            ),
        )

        workflows = packet.priority_workflows

        assert len(workflows) == 1

        workflow = workflows[0]

        assert (
            comparison_key(
                workflow.action
            )
            == comparison_key(
                expected_action
            )
        )

        assert (
            comparison_key(
                workflow.object
            )
            == comparison_key(
                expected_object
            )
        )



@pytest.mark.parametrize(
    (
        "language",
        "sentence",
        "expected_payer",
    ),
    [
        (
            "fr",
            (
                "L'entreprise cliente paie "
                "un abonnement mensuel."
            ),
            "entreprise cliente",
        ),
        (
            "fr",
            (
                "L'entreprise cliente paye "
                "les frais mensuels."
            ),
            "entreprise cliente",
        ),
        (
            "fr",
            (
                "L'entreprise cliente paiera "
                "les frais de service."
            ),
            "entreprise cliente",
        ),
        (
            "fr",
            (
                "L'entreprise cliente a pay\u00e9 "
                "les frais initiaux."
            ),
            "entreprise cliente",
        ),
        (
            "en",
            (
                "The client company pays "
                "a monthly subscription."
            ),
            "client company",
        ),
        (
            "en",
            (
                "The client company paid "
                "the setup fee."
            ),
            "client company",
        ),
        (
            "en",
            (
                "The client company will pay "
                "the monthly fee."
            ),
            "client company",
        ),
        (
            "en",
            (
                "The client company is paying "
                "the service fee."
            ),
            "client company",
        ),
    ],
)
def test_explicit_payment_predicate_assigns_payer_role(
    language: str,
    sentence: str,
    expected_payer: str,
) -> None:
    declared = (
        project_context_extractor
        ._declared_actor_roles(
            sentence
        )
    )

    assert any(
        comparison_key(name)
        == comparison_key(expected_payer)
        and role.value == "payer"
        for name, role in declared
    )

    packet = project_context_extractor.extract(
        title="PaymentActor",
        description=sentence,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    assert any(
        comparison_key(name)
        == comparison_key(expected_payer)
        for name in packet.payer_actor_names
    )

    # Payment authority must not silently become
    # decision-making authority.
    assert not any(
        comparison_key(name)
        == comparison_key(expected_payer)
        for name in packet.decision_maker_actor_names
    )

    assert any(
        comparison_key(actor.name)
        == comparison_key(expected_payer)
        and actor.role.value == "payer"
        and actor.is_explicit
        for actor in packet.actors
    )


@pytest.mark.parametrize(
    (
        "language",
        "sentence",
        "forbidden_actor",
    ),
    [
        (
            "fr",
            (
                "La plateforme permet aux clients "
                "de payer en ligne."
            ),
            "plateforme",
        ),
        (
            "en",
            (
                "The platform allows customers "
                "to pay online."
            ),
            "platform",
        ),
    ],
)
def test_payment_capability_does_not_make_platform_the_payer(
    language: str,
    sentence: str,
    forbidden_actor: str,
) -> None:
    packet = project_context_extractor.extract(
        title="PaymentCapability",
        description=sentence,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    assert not any(
        comparison_key(name)
        == comparison_key(forbidden_actor)
        for name in packet.payer_actor_names
    )
