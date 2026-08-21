from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def declared(
    sentence: str,
    role: ActorRole,
):
    return [
        name
        for name, actual_role
        in (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )
        if actual_role == role
    ]


def keys(values):
    return [
        comparison_key(value)
        for value in values
    ]


def test_french_temporal_clause_is_not_part_of_payer_identity():
    names = declared(
        (
            "Lorsque la r\u00e9servation est accept\u00e9e, "
            "la soci\u00e9t\u00e9 cliente paie les frais."
        ),
        ActorRole.PAYER,
    )

    assert len(names) == 1

    assert (
        comparison_key(
            names[0]
        )
        == "societe cliente"
    )

    assert "lorsque" not in comparison_key(
        names[0]
    )


def test_english_temporal_clause_is_not_part_of_payer_identity():
    names = declared(
        (
            "Once the booking is accepted, "
            "the client company pays the fee."
        ),
        ActorRole.PAYER,
    )

    assert len(names) == 1

    assert (
        comparison_key(
            names[0]
        )
        == "client company"
    )


def test_french_modal_purchase_decision_declaration_splits_alternatives():
    names = declared(
        (
            "Le d\u00e9cideur d'achat peut \u00eatre "
            "le responsable des achats ou "
            "le responsable d'exploitation."
        ),
        ActorRole.DECISION_MAKER,
    )

    normalized = keys(
        names
    )

    assert any(
        "responsable des achats" in value
        for value in normalized
    )

    assert any(
        "responsable d exploitation" in value
        for value in normalized
    )

    assert len(names) == 2


def test_english_modal_decision_declaration_splits_alternatives():
    names = declared(
        (
            "The decision maker can be "
            "the procurement manager or "
            "the operations manager."
        ),
        ActorRole.DECISION_MAKER,
    )

    normalized = keys(
        names
    )

    assert any(
        "procurement manager" in value
        for value in normalized
    )

    assert any(
        "operations manager" in value
        for value in normalized
    )

    assert len(names) == 2


def test_payer_and_decision_authorities_remain_independent():
    packet = (
        project_context_extractor
        .extract(
            title="RoleAuthorityContract",
            description=(
                "Le probl\u00e8me est un processus lent. "
                "La plateforme centralise le workflow. "
                "Le payeur est l'entreprise cliente. "
                "Le d\u00e9cideur d'achat peut \u00eatre "
                "le responsable des achats ou "
                "le responsable d'exploitation."
            ),
            industry="logiciel B2B",
            target_region="Tunisie",
            output_language="fr",
        )
    )

    payer_keys = keys(
        packet.payer_actor_names
    )

    decision_keys = keys(
        packet.decision_maker_actor_names
    )

    assert any(
        "entreprise cliente" in value
        for value in payer_keys
    )

    assert not any(
        "entreprise cliente" == value
        for value in decision_keys
    )

    assert any(
        "responsable des achats" in value
        for value in decision_keys
    )

    assert any(
        "responsable d exploitation" in value
        for value in decision_keys
    )
