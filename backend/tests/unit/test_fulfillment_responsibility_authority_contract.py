from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _extract(
    *,
    title: str,
    description: str,
    language: str,
):
    return project_context_extractor.extract(
        title=title,
        description=description,
        industry="B2B Marketplace / Services",
        target_region=(
            "France"
            if language == "fr"
            else "United Kingdom"
        ),
        output_language=language,
    )


def test_french_explicit_service_execution_sets_fulfillment_responsibility() -> None:
    description = """
    ServiceLink est une marketplace B2B.

    L'entreprise cliente initie une demande.

    Le prestataire r\u00e9alise ensuite l'intervention.

    L'entreprise cliente paie le service.

    Le probl\u00e8me est que le processus actuel est trop lent.
    """

    packet = _extract(
        title="Fulfillment FR",
        description=description,
        language="fr",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(
            transaction.fulfillment_responsibility
        )
        == comparison_key(
            "prestataire"
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_english_explicit_service_execution_sets_fulfillment_responsibility() -> None:
    description = """
    ServiceLink is a B2B marketplace.

    The client company initiates a service request.

    The contractor performs the requested service.

    The client company pays the service fee.

    The problem is that the current process is too slow.
    """

    packet = _extract(
        title="Fulfillment EN",
        description=description,
        language="en",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(
            transaction.fulfillment_responsibility
        )
        == comparison_key(
            "contractor"
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_repairlink_explicit_technician_execution_sets_responsibility() -> None:
    description = """
    RepairLink est une marketplace B2B.

    L'entreprise cliente est l'acteur qui initie
    la demande d'intervention.

    Les techniciens de maintenance v\u00e9rifi\u00e9s constituent
    le second c\u00f4t\u00e9 de la marketplace.

    L'entreprise cliente choisit une proposition.

    Le technicien r\u00e9alise ensuite l'intervention.

    L'entreprise cliente est le payeur principal.

    Le probl\u00e8me est qu'il est difficile de trouver
    rapidement un intervenant disponible.
    """

    packet = _extract(
        title="RepairLink",
        description=description,
        language="fr",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(
            transaction.fulfillment_responsibility
        )
        == comparison_key(
            "technicien"
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_price_proposal_alone_does_not_prove_fulfillment_responsibility() -> None:
    """
    Offering a price or delay is commercial participation,
    not sufficient evidence that the actor executes fulfillment.
    """

    description = """
    ServiceLink est une marketplace B2B.

    L'entreprise cliente initie une demande.

    Le prestataire propose un prix et un d\u00e9lai.

    L'entreprise cliente choisit une proposition.

    Le probl\u00e8me est que le processus actuel est trop lent.
    """

    packet = _extract(
        title="Proposal Only",
        description=description,
        language="fr",
    )

    assert (
        packet.transaction_unit.fulfillment_responsibility
        == ""
    ), packet.transaction_unit.model_dump(
        mode="json"
    )


def test_supply_side_membership_alone_does_not_prove_fulfillment_responsibility() -> None:
    """
    Structural supply-side authority must not be silently converted
    into fulfillment responsibility.
    """

    description = """
    ServiceLink is a two-sided B2B marketplace.

    Verified contractors form the supply side of the marketplace.

    The client company initiates a service request.

    The problem is that sourcing a provider is too slow.
    """

    packet = _extract(
        title="Supply Side Only",
        description=description,
        language="en",
    )

    assert (
        packet.transaction_unit.fulfillment_responsibility
        == ""
    ), packet.transaction_unit.model_dump(
        mode="json"
    )


def test_execution_responsibility_does_not_invent_fulfillment_mode() -> None:
    """
    Knowing who performs the service does not establish whether
    fulfillment is onsite, remote, delivered, shipped, or otherwise.
    """

    description = """
    ServiceLink est une marketplace B2B.

    L'entreprise cliente initie une demande.

    Le prestataire ex\u00e9cute la prestation.

    Le probl\u00e8me est que le processus actuel est trop lent.
    """

    packet = _extract(
        title="Responsibility Without Mode",
        description=description,
        language="fr",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(
            transaction.fulfillment_responsibility
        )
        == comparison_key(
            "prestataire"
        )
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        transaction.fulfillment_mode
        == ""
    ), transaction.model_dump(
        mode="json"
    )
