from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def test_french_organization_wrappers_share_identity():
    first = (
        project_context_extractor
        ._actor_alias_identity_key(
            "l'entreprise locataire"
        )
    )

    second = (
        project_context_extractor
        ._actor_alias_identity_key(
            "soci\u00e9t\u00e9 locataire"
        )
    )

    assert first == "locataire"
    assert second == "locataire"


def test_english_organization_wrappers_share_identity():
    first = (
        project_context_extractor
        ._actor_alias_identity_key(
            "the client company"
        )
    )

    second = (
        project_context_extractor
        ._actor_alias_identity_key(
            "client organization"
        )
    )

    assert first == "client"
    assert second == "client"


def test_distinct_business_qualifiers_are_not_merged():
    provider = (
        project_context_extractor
        ._actor_alias_identity_key(
            "entreprise propri\u00e9taire"
        )
    )

    renter = (
        project_context_extractor
        ._actor_alias_identity_key(
            "soci\u00e9t\u00e9 locataire"
        )
    )

    assert provider != renter


def test_same_role_aliases_collapse_in_canonical_packet():
    packet = (
        project_context_extractor
        .extract(
            title="AliasContract",
            description=(
                "Le probl\u00e8me est un processus lent. "
                "La plateforme centralise les op\u00e9rations. "
                "Le payeur est l'entreprise locataire. "
                "Lorsque la commande est valid\u00e9e, "
                "la soci\u00e9t\u00e9 locataire paie les frais."
            ),
            industry="logiciel B2B",
            target_region="Tunisie",
            output_language="fr",
        )
    )

    payer_keys = [
        (
            project_context_extractor
            ._actor_alias_identity_key(
                name
            )
        )
        for name in packet.payer_actor_names
    ]

    assert payer_keys == [
        "locataire"
    ]


def test_same_identity_can_keep_two_explicit_roles():
    packet = (
        project_context_extractor
        .extract(
            title="MultiRoleContract",
            description=(
                "Le probl\u00e8me est un processus lent. "
                "La plateforme centralise les op\u00e9rations. "
                "Le payeur est l'entreprise cliente. "
                "Le d\u00e9cideur est la soci\u00e9t\u00e9 cliente."
            ),
            industry="logiciel B2B",
            target_region="Tunisie",
            output_language="fr",
        )
    )

    role_pairs = {
        (
            project_context_extractor
            ._actor_alias_identity_key(
                actor.name
            ),
            actor.role,
        )
        for actor in packet.actors
    }

    assert (
        "cliente",
        ActorRole.PAYER,
    ) in role_pairs

    assert (
        "cliente",
        ActorRole.DECISION_MAKER,
    ) in role_pairs
