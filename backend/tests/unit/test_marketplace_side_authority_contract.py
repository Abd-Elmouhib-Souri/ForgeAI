from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def role_map(description: str):
    return {
        comparison_key(name): role
        for name, role
        in (
            project_context_extractor
            ._declared_marketplace_sides(
                description
            )
        )
    }


def test_french_individual_marketplace_sides_are_detected():
    description = (
        "Le premier c\u00f4t\u00e9 est constitu\u00e9 "
        "d'entreprises propri\u00e9taires de mat\u00e9riel "
        "qui souhaitent proposer leurs actifs. "
        "Le second c\u00f4t\u00e9 est constitu\u00e9 "
        "d'entreprises qui ont besoin temporairement "
        "de ce mat\u00e9riel."
    )

    sides = role_map(
        description
    )

    assert any(
        role == ActorRole.PROVIDER
        for role in sides.values()
    )

    assert any(
        role == ActorRole.BUYER
        for role in sides.values()
    )


def test_side_order_never_assigns_business_role():
    description = (
        "The first side consists of companies "
        "that need temporary access to equipment. "
        "The second side consists of asset owners "
        "who offer unused equipment."
    )

    sides = (
        project_context_extractor
        ._declared_marketplace_sides(
            description
        )
    )

    assert len(sides) == 2

    first_name, first_role = sides[0]
    second_name, second_role = sides[1]

    assert "need" in comparison_key(
        first_name
    )
    assert (
        first_role
        == ActorRole.BUYER
    )

    assert "owner" in comparison_key(
        second_name
    )
    assert (
        second_role
        == ActorRole.PROVIDER
    )


def test_unqualified_sides_do_not_invent_roles():
    description = (
        "The first side consists of advisors. "
        "The second side consists of auditors."
    )

    assert (
        project_context_extractor
        ._declared_marketplace_sides(
            description
        )
        == []
    )


def test_full_packet_projects_marketplace_sides_into_transaction():
    description = (
        "Le probl\u00e8me est le manque d'acc\u00e8s "
        "\u00e0 certains \u00e9quipements. "
        "La plateforme met en relation deux c\u00f4t\u00e9s. "
        "Le premier c\u00f4t\u00e9 est constitu\u00e9 "
        "d'entreprises propri\u00e9taires d'\u00e9quipements "
        "qui souhaitent proposer leurs actifs inutilis\u00e9s. "
        "Le second c\u00f4t\u00e9 est constitu\u00e9 "
        "d'entreprises qui ont besoin temporairement "
        "de ces \u00e9quipements. "
        "Une entreprise propri\u00e9taire publie une offre. "
        "Une entreprise locataire r\u00e9serve l'\u00e9quipement."
    )

    packet = (
        project_context_extractor
        .extract(
            title="TwoSideContract",
            description=description,
            industry="marketplace B2B",
            target_region="Europe",
            output_language="fr",
        )
    )

    providers = [
        actor.name
        for actor in packet.actors
        if (
            actor.role
            == ActorRole.PROVIDER
        )
    ]

    buyers = [
        actor.name
        for actor in packet.actors
        if (
            actor.role
            == ActorRole.BUYER
        )
    ]

    assert providers
    assert buyers

    assert (
        packet.transaction_unit
        .supply_actor
    )

    assert (
        packet.transaction_unit
        .demand_actor
    )

    assert (
        packet.transaction_unit
        .has_two_sides
        is True
    )
