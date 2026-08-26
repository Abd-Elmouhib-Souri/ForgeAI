from app.schemas.analysis_context import ActorRole
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


PRONOUN_KEYS = {
    "elle",
    "elles",
    "il",
    "ils",
    "it",
    "they",
    "he",
    "she",
}


def _role_actors(packet, role: ActorRole):
    return [
        actor
        for actor in packet.actors
        if actor.role == role
    ]


def _role_keys(packet, role: ActorRole) -> set[str]:
    return {
        comparison_key(actor.name)
        for actor in _role_actors(
            packet,
            role,
        )
    }


def test_french_pronoun_does_not_create_second_payer_identity() -> None:
    description = """
    L'entreprise cliente est le payeur principal.
    Elle paie le prix de l'intervention.

    Le problème est un processus manuel trop lent.
    """

    packet = project_context_extractor.extract(
        title="Pronoun FR",
        description=description,
        industry="B2B Services",
        target_region="France",
        output_language="fr",
    )

    payer_keys = _role_keys(
        packet,
        ActorRole.PAYER,
    )

    assert (
        comparison_key("entreprise cliente")
        in payer_keys
    ), payer_keys

    assert not (
        payer_keys
        & PRONOUN_KEYS
    ), payer_keys

    assert len(
        _role_actors(
            packet,
            ActorRole.PAYER,
        )
    ) == 1, [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_english_pronoun_does_not_create_second_payer_identity() -> None:
    description = """
    The client company is the primary payer.
    It pays the transaction fee.

    The problem is that the current process is too slow.
    """

    packet = project_context_extractor.extract(
        title="Pronoun EN",
        description=description,
        industry="B2B Services",
        target_region="United Kingdom",
        output_language="en",
    )

    payer_keys = _role_keys(
        packet,
        ActorRole.PAYER,
    )

    assert (
        comparison_key("client company")
        in payer_keys
    ), payer_keys

    assert not (
        payer_keys
        & PRONOUN_KEYS
    ), payer_keys

    assert len(
        _role_actors(
            packet,
            ActorRole.PAYER,
        )
    ) == 1, [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_standalone_pronoun_never_becomes_canonical_actor() -> None:
    """
    A pronoun without a reliable explicit antecedent must not become
    a canonical business actor.
    """

    description = """
    Elle paie les frais.

    Le problème est que le processus actuel est fragmenté.
    """

    packet = project_context_extractor.extract(
        title="No Antecedent",
        description=description,
        industry="Services",
        target_region="France",
        output_language="fr",
    )

    actor_keys = {
        comparison_key(actor.name)
        for actor in packet.actors
    }

    assert not (
        actor_keys
        & PRONOUN_KEYS
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_standalone_english_pronoun_never_becomes_canonical_actor() -> None:
    description = """
    It pays the service fee.

    The problem is that the process is fragmented.
    """

    packet = project_context_extractor.extract(
        title="No Antecedent EN",
        description=description,
        industry="Services",
        target_region="United Kingdom",
        output_language="en",
    )

    actor_keys = {
        comparison_key(actor.name)
        for actor in packet.actors
    }

    assert not (
        actor_keys
        & PRONOUN_KEYS
    ), [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]


def test_distinct_explicit_payers_are_not_collapsed() -> None:
    """
    Pronoun cleanup must not collapse two genuinely distinct actors.
    """

    description = """
    L'entreprise cliente est le payeur principal.
    Le partenaire financier paie les frais de garantie.

    Le problème est que le processus actuel est trop lent.
    """

    packet = project_context_extractor.extract(
        title="Two Payers",
        description=description,
        industry="B2B Services",
        target_region="France",
        output_language="fr",
    )

    payer_keys = _role_keys(
        packet,
        ActorRole.PAYER,
    )

    assert (
        comparison_key("entreprise cliente")
        in payer_keys
    )

    assert (
        comparison_key("partenaire financier")
        in payer_keys
    )

    assert len(
        _role_actors(
            packet,
            ActorRole.PAYER,
        )
    ) == 2


def test_repairlink_pronoun_does_not_pollute_payer_authority() -> None:
    description = """
    RepairLink est une marketplace B2B.

    L'entreprise cliente est l'acteur qui initie la demande
    d'intervention.

    Les techniciens de maintenance vérifiés constituent
    le second côté de la marketplace.

    Le technicien réalise l'intervention.

    L'entreprise cliente est le payeur principal.
    Elle paie le prix de l'intervention.

    Le problème est qu'il est difficile de trouver rapidement
    un intervenant disponible.
    """

    packet = project_context_extractor.extract(
        title="RepairLink",
        description=description,
        industry="B2B Marketplace / Maintenance Services",
        target_region="Tunisie",
        output_language="fr",
    )

    payer_keys = _role_keys(
        packet,
        ActorRole.PAYER,
    )

    assert (
        comparison_key("entreprise cliente")
        in payer_keys
    )

    assert not (
        payer_keys
        & PRONOUN_KEYS
    ), payer_keys

    assert len(
        _role_actors(
            packet,
            ActorRole.PAYER,
        )
    ) == 1, [
        actor.model_dump(mode="json")
        for actor in packet.actors
    ]
