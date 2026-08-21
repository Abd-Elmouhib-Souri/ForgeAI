from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _joined_scope(packet) -> str:
    return " | ".join(
        comparison_key(item)
        for item in packet.mvp_scope
    )


def _has_combined_item(
    packet,
    first: str,
    second: str,
) -> bool:
    first_key = comparison_key(first)
    second_key = comparison_key(second)

    return any(
        first_key in comparison_key(item)
        and second_key in comparison_key(item)
        for item in packet.mvp_scope
    )


def test_explicit_mvp_preserves_all_positive_items_without_arbitrary_cap():
    description = """
    Les utilisateurs principaux sont les entreprises clientes.

    Le MVP doit permettre :
    - la création des profils ;
    - la publication des offres ;
    - la recherche et le filtrage des offres ;
    - la gestion des disponibilités ;
    - les demandes de réservation ;
    - l'acceptation ou le refus des demandes ;
    - le paiement des réservations ;
    - le suivi du statut des opérations ;
    - les évaluations après transaction ;
    - un tableau de bord simple.

    Le MVP ne doit pas inclure :
    - une flotte logistique propre ;
    - un service d'assurance interne ;
    - la maintenance prédictive ;
    - la gestion complète des stocks.
    """

    packet = project_context_extractor.extract(
        title="Scope Completeness",
        description=description,
        industry="services",
        target_region="France",
        output_language="fr",
    )

    scope = _joined_scope(
        packet
    )

    required = (
        "création des profils",
        "publication des offres",
        "recherche",
        "filtrage",
        "gestion des disponibilités",
        "demandes de réservation",
        "acceptation",
        "refus des demandes",
        "paiement des réservations",
        "suivi du statut",
        "évaluations après transaction",
        "tableau de bord simple",
    )

    for value in required:
        assert (
            comparison_key(value)
            in scope
        ), packet.mvp_scope

    excluded = (
        "flotte logistique",
        "assurance interne",
        "maintenance prédictive",
        "gestion complète des stocks",
    )

    for value in excluded:
        assert (
            comparison_key(value)
            not in scope
        ), packet.mvp_scope

    assert len(
        packet.mvp_scope
    ) > 8


def test_scope_item_conjunctions_are_not_split_into_fake_features():
    description = """
    The primary users are business operators.

    The MVP must include:
    - account creation;
    - offer publication;
    - search and filtering;
    - availability management;
    - booking requests;
    - accept or reject requests;
    - online payment;
    - transaction status tracking;
    - post-transaction reviews;
    - a simple dashboard.
    """

    packet = project_context_extractor.extract(
        title="Scope Structure",
        description=description,
        industry="services",
        target_region="Europe",
        output_language="en",
    )

    assert _has_combined_item(
        packet,
        "search",
        "filter",
    ), packet.mvp_scope

    assert _has_combined_item(
        packet,
        "accept",
        "reject",
    ), packet.mvp_scope


def test_explicit_mvp_never_becomes_workflow_authority():
    description = """
    The primary users are operators.

    The operators record service requests.

    The MVP must include:
    - account creation;
    - search and filtering;
    - dashboards;
    - reporting;
    - notifications;
    - exports;
    - document storage;
    - audit history;
    - billing;
    - settings.
    """

    packet = project_context_extractor.extract(
        title="Scope Authority",
        description=description,
        industry="software",
        target_region="Europe",
        output_language="en",
    )

    workflow_text = " | ".join(
        comparison_key(
            workflow.sentence
        )
        for workflow
        in packet.priority_workflows
    )

    assert (
        "record service requests"
        in workflow_text
    )

    for forbidden in (
        "dashboards",
        "reporting",
        "exports",
        "document storage",
        "billing",
        "settings",
    ):
        assert (
            comparison_key(forbidden)
            not in workflow_text
        ), [
            workflow.model_dump(
                mode="json"
            )
            for workflow
            in packet.priority_workflows
        ]
