
from __future__ import annotations

import pytest

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def extract(
    description: str,
    *,
    language: str = "fr",
):
    return project_context_extractor.extract(
        title="UniversalSemanticWorkflow",
        description=description,
        industry="B2B software",
        target_region=(
            "Tunisie"
            if language == "fr"
            else "United Kingdom"
        ),
        output_language=language,
    )


def workflow_keys(packet):
    return [
        comparison_key(
            workflow.sentence
        )
        for workflow
        in (
            packet.priority_workflows
            or []
        )
    ]


def primary_key(packet):
    if not packet.primary_workflow:
        return ""

    return comparison_key(
        packet.primary_workflow.sentence
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "forbidden_terms",
        "expected_any",
    ),
    [
        (
            "fr",
            (
                "Le workflow prioritaire est le suivant : "
                "un mouvement modifie la quantite du stock. "
                "La plateforme compare le niveau au seuil. "
                "Un niveau insuffisant genere une alerte. "
                "Le responsable stock consulte l'alerte. "
                "Le responsable stock verifie la situation. "
                "La plateforme prepare une suggestion "
                "de reapprovisionnement. "
                "Le responsable stock valide, modifie "
                "ou reporte la decision. "
                "Toute commande fournisseur necessite "
                "une validation humaine par "
                "un utilisateur autorise."
            ),
            (
                "commande fournisseur necessite",
                "validation humaine par un utilisateur",
            ),
            (
                "mouvement",
                "stock",
                "alerte",
                "reapprovisionnement",
                "responsable stock",
            ),
        ),
        (
            "en",
            (
                "The priority workflow is the following: "
                "a stock movement changes the available quantity. "
                "The platform compares inventory with the threshold. "
                "A low level generates an alert. "
                "The inventory manager reviews the alert. "
                "The inventory manager verifies the situation. "
                "The platform prepares a replenishment suggestion. "
                "The inventory manager approves, changes, "
                "or postpones the replenishment decision. "
                "Any supplier order requires human approval "
                "by an authorized user."
            ),
            (
                "supplier order requires human approval",
                "requires human approval",
            ),
            (
                "stock movement",
                "inventory",
                "alert",
                "replenishment",
                "inventory manager",
            ),
        ),
    ],
)
def test_explicit_labeled_workflow_beats_control_rule(
    language: str,
    description: str,
    forbidden_terms: tuple[str, ...],
    expected_any: tuple[str, ...],
) -> None:
    packet = extract(
        description,
        language=language,
    )

    primary = primary_key(
        packet
    )

    assert primary, (
        packet.priority_workflows
    )

    assert not any(
        comparison_key(term)
        in primary
        for term in forbidden_terms
    ), (
        packet.primary_workflow.model_dump(
            mode="json"
        )
        if packet.primary_workflow
        else None
    )

    assert any(
        comparison_key(term)
        in primary
        for term in expected_any
    ), (
        packet.primary_workflow.model_dump(
            mode="json"
        )
        if packet.primary_workflow
        else None
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "forbidden_action",
        "expected_any",
    ),
    [
        (
            "fr",
            (
                "Le workflow prioritaire concerne "
                "la passation entre equipes. "
                "Un operateur enregistre un incident. "
                "Le chef d'equipe verifie la passation. "
                "L'equipe suivante consulte les informations. "
                "Le logiciel ne commande directement "
                "aucune machine industrielle."
            ),
            "commander directement aucune machine",
            (
                "incident",
                "passation",
                "consulte",
                "informations",
            ),
        ),
        (
            "en",
            (
                "The priority workflow concerns "
                "handover between shifts. "
                "An operator records an incident. "
                "The team leader reviews the handover. "
                "The next shift reads the information. "
                "The software does not directly control "
                "any industrial machine."
            ),
            "control any industrial machine",
            (
                "incident",
                "handover",
                "information",
            ),
        ),
    ],
)
def test_negative_capability_never_becomes_positive_workflow(
    language: str,
    description: str,
    forbidden_action: str,
    expected_any: tuple[str, ...],
) -> None:
    packet = extract(
        description,
        language=language,
    )

    all_workflows = workflow_keys(
        packet
    )

    forbidden = comparison_key(
        forbidden_action
    )

    assert all(
        forbidden not in item
        for item in all_workflows
    ), [
        workflow.model_dump(
            mode="json"
        )
        for workflow
        in packet.priority_workflows
    ]

    primary = primary_key(
        packet
    )

    assert primary

    assert any(
        comparison_key(term)
        in primary
        for term in expected_any
    ), (
        packet.primary_workflow.model_dump(
            mode="json"
        )
        if packet.primary_workflow
        else None
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "forbidden_primary",
        "expected_any",
    ),
    [
        (
            "fr",
            (
                "Le workflow prioritaire est le suivant : "
                "un capteur mesure la consommation. "
                "La plateforme detecte une anomalie. "
                "Le responsable recoit une alerte. "
                "Le responsable verifie la situation. "
                "Le responsable decide de l'intervention. "
                "Le responsable confirme le resultat. "
                "Les responsables utilisent aussi "
                "le tableau de bord pour surveiller "
                "les installations."
            ),
            "surveiller les installations",
            (
                "mesure",
                "consommation",
                "anomalie",
                "alerte",
                "intervention",
                "resultat",
            ),
        ),
        (
            "en",
            (
                "The priority workflow is the following: "
                "a sensor measures consumption. "
                "The platform detects an anomaly. "
                "The manager receives an alert. "
                "The manager verifies the situation. "
                "The manager decides on the intervention. "
                "The manager confirms the result. "
                "Managers also use the dashboard "
                "to monitor the installations."
            ),
            "monitor the installations",
            (
                "measure",
                "consumption",
                "anomaly",
                "alert",
                "intervention",
                "result",
            ),
        ),
    ],
)
def test_explicit_priority_flow_beats_secondary_generic_activity(
    language: str,
    description: str,
    forbidden_primary: str,
    expected_any: tuple[str, ...],
) -> None:
    packet = extract(
        description,
        language=language,
    )

    primary = primary_key(
        packet
    )

    assert primary

    assert (
        comparison_key(
            forbidden_primary
        )
        not in primary
    ), (
        packet.primary_workflow.model_dump(
            mode="json"
        )
        if packet.primary_workflow
        else None
    )

    assert any(
        comparison_key(term)
        in primary
        for term in expected_any
    ), (
        packet.primary_workflow.model_dump(
            mode="json"
        )
        if packet.primary_workflow
        else None
    )
