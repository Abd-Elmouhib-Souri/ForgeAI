from app.schemas.analysis_context import ActorRole
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _decision_actors(packet):
    return [
        actor
        for actor in packet.actors
        if actor.role == ActorRole.DECISION_MAKER
    ]


def _decision_keys(packet) -> set[str]:
    return {
        comparison_key(actor.name)
        for actor in _decision_actors(packet)
    }


def _payer_keys(packet) -> set[str]:
    return {
        comparison_key(actor.name)
        for actor in packet.actors
        if actor.role == ActorRole.PAYER
    }


def test_french_actor_first_decision_maker_is_canonical() -> None:
    description = """
    Le responsable de site est le d\u00e9cideur principal
    pour accepter une proposition.

    Le probl\u00e8me est que le processus actuel prend trop de temps.
    """

    packet = project_context_extractor.extract(
        title="Decision FR",
        description=description,
        industry="B2B Services",
        target_region="France",
        output_language="fr",
    )

    expected = comparison_key(
        "responsable de site"
    )

    assert expected in _decision_keys(
        packet
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_english_actor_first_decision_maker_is_canonical() -> None:
    description = """
    The operations director is the primary decision maker
    for approving the purchase.

    The problem is that the current process is too slow.
    """

    packet = project_context_extractor.extract(
        title="Decision EN",
        description=description,
        industry="B2B Services",
        target_region="United Kingdom",
        output_language="en",
    )

    expected = comparison_key(
        "operations director"
    )

    assert expected in _decision_keys(
        packet
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_repairlink_compound_decision_actor_is_detected() -> None:
    description = """
    RepairLink est une marketplace B2B.

    L'entreprise cliente est l'acteur qui initie la demande
    d'intervention.

    Le technicien r\u00e9alise l'intervention.

    L'entreprise cliente est le payeur principal.

    Le responsable ou propri\u00e9taire de l'\u00e9tablissement
    client est le d\u00e9cideur principal pour accepter une
    proposition et autoriser le paiement.

    Le probl\u00e8me est qu'il est difficile de trouver rapidement
    un intervenant disponible.
    """

    packet = project_context_extractor.extract(
        title="RepairLink",
        description=description,
        industry="B2B Marketplace / Maintenance Services",
        target_region="Tunisie",
        output_language="fr",
    )

    keys = _decision_keys(
        packet
    )

    assert keys, [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]

    assert any(
        "responsable" in key
        or "proprietaire" in key
        for key in keys
    ), keys


def test_negative_french_decision_statement_does_not_create_authority() -> None:
    description = """
    Le responsable de site n'est pas le d\u00e9cideur principal.

    Le probl\u00e8me est que le processus actuel est fragment\u00e9.
    """

    packet = project_context_extractor.extract(
        title="Negative Decision FR",
        description=description,
        industry="B2B Services",
        target_region="France",
        output_language="fr",
    )

    assert (
        comparison_key("responsable de site")
        not in _decision_keys(packet)
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_negative_english_decision_statement_does_not_create_authority() -> None:
    description = """
    The site manager is not the primary decision maker.

    The problem is that the current process is fragmented.
    """

    packet = project_context_extractor.extract(
        title="Negative Decision EN",
        description=description,
        industry="B2B Services",
        target_region="United Kingdom",
        output_language="en",
    )

    assert (
        comparison_key("site manager")
        not in _decision_keys(packet)
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_decision_maker_authority_does_not_invent_payer_role() -> None:
    description = """
    Le responsable de site est le d\u00e9cideur principal
    pour accepter la proposition.

    Le probl\u00e8me est que le processus actuel est trop lent.
    """

    packet = project_context_extractor.extract(
        title="Decision Role Separation",
        description=description,
        industry="B2B Services",
        target_region="France",
        output_language="fr",
    )

    expected = comparison_key(
        "responsable de site"
    )

    assert expected in _decision_keys(
        packet
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]

    assert expected not in _payer_keys(
        packet
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]
