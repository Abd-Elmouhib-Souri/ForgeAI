from __future__ import annotations

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def fr(value: str) -> str:
    return (
        value
        .replace(
            "{E_ACUTE}",
            chr(0x00E9),
        )
        .replace(
            "{E_GRAVE}",
            chr(0x00E8),
        )
        .replace(
            "{A_GRAVE}",
            chr(0x00E0),
        )
    )


def extract(
    description: str,
    *,
    language: str = "en",
):
    return project_context_extractor.extract(
        title="UniversalActorGrammar",
        description=description,
        industry="B2B software",
        target_region=(
            "Belgium"
            if language == "en"
            else "Belgique"
        ),
        output_language=language,
    )


def role_names(
    packet,
    role: str,
):
    return {
        comparison_key(
            actor.name
        )
        for actor
        in packet.actors
        if actor.role.value
        == role
    }


def test_runtime_unicode_builder_is_exact():
    value = fr(
        "op{E_ACUTE}rationnel | "
        "D{E_ACUTE}cideur | "
        "op{E_ACUTE}rations | "
        "{E_ACUTE}conomique | "
        "Apr{E_GRAVE}s"
    )

    assert chr(0x00E9) in value
    assert chr(0x00E8) in value
    assert "?" not in value

    assert (
        value
        ==
        (
            "op"
            + chr(0x00E9)
            + "rationnel | D"
            + chr(0x00E9)
            + "cideur | op"
            + chr(0x00E9)
            + "rations | "
            + chr(0x00E9)
            + "conomique | Apr"
            + chr(0x00E8)
            + "s"
        )
    )


def test_colon_labeled_actor_roles_are_materialized():
    description = fr(
        "Utilisateur op{E_ACUTE}rationnel principal : "
        "responsable logistique. "
        "D{E_ACUTE}cideur principal : "
        "directrice des op{E_ACUTE}rations. "
        "D{E_ACUTE}cideur secondaire : "
        "responsable des achats. "
        "Payeur : entreprise cliente."
    )

    packet = extract(
        description,
        language="fr",
    )

    users = role_names(
        packet,
        "user",
    )

    decision_makers = role_names(
        packet,
        "decision_maker",
    )

    payers = role_names(
        packet,
        "payer",
    )

    assert (
        comparison_key(
            "responsable logistique"
        )
        in users
    ), users

    assert (
        comparison_key(
            fr(
                "directrice des "
                "op{E_ACUTE}rations"
            )
        )
        in decision_makers
    ), decision_makers

    assert (
        comparison_key(
            "responsable des achats"
        )
        in decision_makers
    ), decision_makers

    assert (
        comparison_key(
            "entreprise cliente"
        )
        in payers
    ), payers


def test_french_coordinated_modal_purchase_decision():
    description = fr(
        "Le directeur financier, "
        "le responsable des achats "
        "ou le directeur des op{E_ACUTE}rations "
        "peut d{E_ACUTE}cider "
        "de l'acquisition de la solution."
    )

    packet = extract(
        description,
        language="fr",
    )

    decision_makers = role_names(
        packet,
        "decision_maker",
    )

    expected = {
        comparison_key(
            "directeur financier"
        ),
        comparison_key(
            "responsable des achats"
        ),
        comparison_key(
            fr(
                "directeur des "
                "op{E_ACUTE}rations"
            )
        ),
    }

    assert expected.issubset(
        decision_makers
    ), decision_makers


def test_operational_decision_is_not_purchase_authority():
    description = fr(
        "Le responsable maintenance utilise la plateforme. "
        "Apr{E_GRAVE}s une alerte, "
        "il d{E_ACUTE}cide d'envoyer un technicien. "
        "Le directeur des op{E_ACUTE}rations "
        "peut d{E_ACUTE}cider "
        "de l'acquisition de la solution."
    )

    packet = extract(
        description,
        language="fr",
    )

    decision_makers = role_names(
        packet,
        "decision_maker",
    )

    assert (
        comparison_key(
            fr(
                "directeur des "
                "op{E_ACUTE}rations"
            )
        )
        in decision_makers
    ), decision_makers

    assert (
        comparison_key(
            "responsable maintenance"
        )
        not in decision_makers
    ), decision_makers


def test_payer_identity_stops_before_relation_predicate_tail():
    description = fr(
        "L'entreprise cliente est le payeur "
        "{E_ACUTE}conomique "
        "et paie directement l'abonnement."
    )

    packet = extract(
        description,
        language="fr",
    )

    payers = role_names(
        packet,
        "payer",
    )

    assert (
        comparison_key(
            "entreprise cliente"
        )
        in payers
    ), payers

    for payer in payers:

        assert (
            "est le payeur"
            not in payer
        ), payers

        assert (
            "paie directement"
            not in payer
        ), payers


def test_english_modal_purchase_decision():
    packet = extract(
        (
            "The finance director, procurement manager, "
            "or operations director may approve the purchase "
            "of the platform."
        ),
        language="en",
    )

    decision_makers = role_names(
        packet,
        "decision_maker",
    )

    expected = {
        comparison_key(
            "finance director"
        ),
        comparison_key(
            "procurement manager"
        ),
        comparison_key(
            "operations director"
        ),
    }

    assert expected.issubset(
        decision_makers
    ), decision_makers


def test_english_payer_identity_stops_before_predicate_tail():
    packet = extract(
        (
            "The client company is the economic payer "
            "and pays the subscription directly."
        ),
        language="en",
    )

    payers = role_names(
        packet,
        "payer",
    )

    assert (
        comparison_key(
            "client company"
        )
        in payers
    ), payers

    for payer in payers:

        assert (
            "is the economic payer"
            not in payer
        ), payers

        assert (
            "pays the subscription"
            not in payer
        ), payers
