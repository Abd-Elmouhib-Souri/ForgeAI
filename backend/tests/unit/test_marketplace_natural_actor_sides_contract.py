from app.schemas.analysis_context import ActorRole
from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _actor_keys(packet, role: ActorRole) -> set[str]:
    return {
        comparison_key(actor.name)
        for actor in packet.actors
        if actor.role == role
    }


def _demand_actor_keys(packet) -> set[str]:
    return {
        comparison_key(actor.name)
        for actor in packet.actors
        if actor.role
        in {
            ActorRole.USER,
            ActorRole.BUYER,
            ActorRole.BENEFICIARY,
        }
    }


def test_explicit_marketplace_second_side_becomes_provider() -> None:
    """
    Actor-first ordinal-side syntax is structural evidence, but the
    ordinal itself must never assign supply/demand semantics.

    The role below comes from explicit provider semantics in the
    actor identity, not from the words "second side".
    """

    description = """
    ServiceLink est une marketplace B2B.

    Les prestataires de maintenance v\u00e9rifi\u00e9s constituent
    le second c\u00f4t\u00e9 de la marketplace.

    Le probl\u00e8me est la difficult\u00e9 \u00e0 trouver rapidement
    un prestataire disponible.
    """

    packet = project_context_extractor.extract(
        title="ServiceLink",
        description=description,
        industry="B2B Marketplace / Services",
        target_region="Tunisie",
        output_language="fr",
    )

    providers = _actor_keys(
        packet,
        ActorRole.PROVIDER,
    )

    expected = comparison_key(
        "prestataires de maintenance v\u00e9rifi\u00e9s"
    )

    assert expected in providers, {
        "expected": expected,
        "providers": providers,
        "actors": [
            actor.model_dump(mode="json")
            for actor in packet.actors
        ],
    }


def test_ordinal_marketplace_side_does_not_invent_economic_role() -> None:
    """
    First/second side is topology, not economic-role authority.
    A semantically neutral actor must remain unclassified.
    """

    description = """
    NeutralExchange est une marketplace \u00e0 deux c\u00f4t\u00e9s.

    Les \u00e9quipes Alpha constituent le second c\u00f4t\u00e9
    de la marketplace.

    Le probl\u00e8me est un processus fragment\u00e9.
    """

    packet = project_context_extractor.extract(
        title="NeutralExchange",
        description=description,
        industry="Marketplace",
        target_region="France",
        output_language="fr",
    )

    neutral = comparison_key(
        "\u00e9quipes Alpha"
    )

    structural = (
        _actor_keys(
            packet,
            ActorRole.PROVIDER,
        )
        | _demand_actor_keys(
            packet
        )
    )

    assert neutral not in structural, [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_explicit_transaction_initiator_becomes_demand_side() -> None:
    description = """
    RepairLink est une marketplace B2B.

    L'entreprise cliente est l'acteur qui initie
    la demande d'intervention.

    Elle décrit la panne, la localisation et le niveau d'urgence.

    Les techniciens proposent ensuite une intervention.

    Le problème est le délai nécessaire pour trouver
    un technicien disponible.
    """

    packet = project_context_extractor.extract(
        title="RepairLink",
        description=description,
        industry="B2B Marketplace / Maintenance Services",
        target_region="Tunisie",
        output_language="fr",
    )

    demand = _demand_actor_keys(
        packet
    )

    expected = comparison_key(
        "entreprise cliente"
    )

    assert expected in demand, {
        "expected": expected,
        "demand": demand,
        "actors": [
            actor.model_dump(mode="json")
            for actor in packet.actors
        ],
    }


def test_provider_execution_statement_is_structural_supply_evidence() -> None:
    """
    An actor explicitly executing the marketplace's offered service
    is supply-side evidence. The rule must remain domain-neutral.
    """

    description = """
    ServiceBridge est une marketplace de services.

    Les cabinets partenaires exécutent les missions réservées
    par les entreprises clientes.

    Les entreprises clientes créent une demande et choisissent
    une proposition.

    Le problème est que la recherche d'un prestataire fiable
    prend trop de temps.
    """

    packet = project_context_extractor.extract(
        title="ServiceBridge",
        description=description,
        industry="Marketplace B2B",
        target_region="France",
        output_language="fr",
    )

    providers = _actor_keys(
        packet,
        ActorRole.PROVIDER,
    )

    assert (
        comparison_key("cabinets partenaires")
        in providers
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_english_natural_supply_and_demand_relations_are_supported() -> None:
    description = """
    FieldLink is a two-sided B2B marketplace.

    Verified contractors form the supply side of the marketplace
    and perform the requested field service.

    The client company initiates the service request and selects
    one contractor proposal.

    The problem is that sourcing a reliable contractor is slow
    and unpredictable.
    """

    packet = project_context_extractor.extract(
        title="FieldLink",
        description=description,
        industry="B2B services marketplace",
        target_region="United Kingdom",
        output_language="en",
    )

    providers = _actor_keys(
        packet,
        ActorRole.PROVIDER,
    )

    demand = _demand_actor_keys(
        packet
    )

    assert (
        comparison_key("verified contractors")
        in providers
    ), providers

    assert (
        comparison_key("client company")
        in demand
    ), demand


def test_payer_declaration_alone_does_not_invent_marketplace_side() -> None:
    """
    Payment authority is separate from structural marketplace-side
    authority.
    """

    description = """
    NeutralHub est une marketplace B2B.

    La société cliente est le payeur principal.

    Le problème est un processus manuel coûteux.
    """

    packet = project_context_extractor.extract(
        title="NeutralHub",
        description=description,
        industry="B2B Marketplace",
        target_region="France",
        output_language="fr",
    )

    payer_key = comparison_key(
        "société cliente"
    )

    structural_keys = (
        _actor_keys(
            packet,
            ActorRole.PROVIDER,
        )
        | _demand_actor_keys(packet)
    )

    assert (
        payer_key
        not in structural_keys
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_generic_actor_mention_does_not_invent_supply_side() -> None:
    """
    Mentioning actors in descriptive copy is weaker than declaring
    their structural marketplace role.
    """

    description = """
    ExampleHub est une plateforme numérique.

    La page d'accueil présente plusieurs entreprises,
    consultants et techniciens.

    Le problème est que les informations sont dispersées.
    """

    packet = project_context_extractor.extract(
        title="ExampleHub",
        description=description,
        industry="Digital Platform",
        target_region="France",
        output_language="fr",
    )

    assert not _actor_keys(
        packet,
        ActorRole.PROVIDER,
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_repairlink_natural_sides_remove_structural_blockers() -> None:
    description = """
    RepairLink TN est une marketplace B2B qui met en relation
    les restaurants, hôtels et petits commerces tunisiens avec
    des techniciens de maintenance vérifiés.

    Il est souvent difficile de comparer rapidement les
    disponibilités, les prix et la fiabilité des intervenants,
    ce qui peut prolonger l'arrêt d'un équipement et perturber
    l'activité.

    L'entreprise cliente est l'acteur qui initie la demande
    d'intervention.

    Les techniciens de maintenance vérifiés constituent
    le second côté de la marketplace.

    Ils peuvent consulter les demandes compatibles avec leurs
    compétences et proposer un prix et un délai.

    L'entreprise cliente choisit une proposition.
    Le technicien réalise ensuite l'intervention.

    L'entreprise cliente paie l'intervention.
    RepairLink prélève une commission sur chaque intervention
    terminée.
    """

    result = idea_readiness_checker.evaluate(
        title="RepairLink TN",
        description=description,
        industry="B2B Marketplace / Maintenance Services",
        target_region="Tunisie",
        output_language="fr",
        analysis_data={},
    )

    packet = dict(
        result.get("project_context_packet")
        or {}
    )

    transaction = dict(
        packet.get("transaction_unit")
        or {}
    )

    blockers = set(
        result.get("blockers")
        or []
    )

    assert (
        "supply_side"
        not in blockers
    ), result

    assert (
        "demand_side"
        not in blockers
    ), result

    assert transaction.get(
        "supply_actor"
    ), transaction

    assert transaction.get(
        "demand_actor"
    ), transaction
