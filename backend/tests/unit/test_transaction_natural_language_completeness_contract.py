from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)
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


def _initiation_matches(
    sentence: str,
):
    matches = []

    for pattern, action in (
        project_context_extractor
        ._transaction_initiation_patterns()
    ):
        match = (
            project_context_extractor
            ._transaction_action_candidate(
                sentence,
                pattern,
            )
        )

        if match is not None:
            matches.append(
                (
                    action,
                    match.group(0),
                )
            )

    return matches


def test_english_initiated_request_keeps_request_object_and_payment_completion() -> None:
    description = """
    ServiceLink is a B2B marketplace.

    The client company initiates a service request.

    The contractor performs the requested service.

    The client company pays the service fee.

    The problem is that the current process is too slow.
    """

    packet = _extract(
        title="English Request Pay",
        description=description,
        language="en",
    )

    transaction = packet.transaction_unit

    assert transaction.initiation_action, (
        transaction.model_dump(mode="json")
    )

    assert (
        comparison_key(transaction.object)
        == comparison_key("service request")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.fulfillment_responsibility
        )
        == comparison_key("contractor")
    )


def test_direct_english_request_verb_keeps_its_object() -> None:
    description = """
    ServiceLink is a B2B marketplace.

    The client company requests a maintenance service.

    The contractor performs the requested service.

    The client company pays the service fee.

    The problem is that the current process is too slow.
    """

    packet = _extract(
        title="Direct Request Verb",
        description=description,
        language="en",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(transaction.object)
        == comparison_key("maintenance service")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )


def test_nominal_demand_side_is_not_an_initiation_action() -> None:
    sentence = (
        "The client company forms the demand side."
    )

    matches = _initiation_matches(
        sentence
    )

    assert not matches, matches


def test_requested_adjective_is_not_an_initiation_action() -> None:
    sentence = (
        "The contractor performs the requested service."
    )

    matches = _initiation_matches(
        sentence
    )

    assert not matches, matches


def test_booking_is_transaction_start_not_transaction_completion() -> None:
    description = """
    BookingLink is a B2B marketplace.

    The client company books a provider service.

    The provider delivers the service.

    The client company pays the transaction fee.

    The problem is that booking currently takes too long.
    """

    packet = _extract(
        title="Booking Lifecycle",
        description=description,
        language="en",
    )

    transaction = packet.transaction_unit

    assert transaction.initiation_action, (
        transaction.model_dump(mode="json")
    )

    assert (
        comparison_key(transaction.object)
        == comparison_key("provider service")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        != comparison_key(
            transaction.initiation_action
        )
    ), transaction.model_dump(
        mode="json"
    )


def test_negated_payment_does_not_close_transaction() -> None:
    description = """
    ServiceLink is a B2B marketplace.

    The client company requests a service.

    The contractor performs the requested service.

    The client company does not pay a transaction fee.

    The problem is that the current process is too slow.
    """

    packet = _extract(
        title="Negated Payment",
        description=description,
        language="en",
    )

    assert (
        comparison_key(
            packet.transaction_unit.completion_action
        )
        != comparison_key("payer")
    ), packet.transaction_unit.model_dump(
        mode="json"
    )


def test_french_reference_transaction_remains_stable() -> None:
    description = """
    ServiceLink est une marketplace B2B.

    L'entreprise cliente initie une demande d'intervention.

    Le prestataire realise ensuite l'intervention.

    L'entreprise cliente paie le prix du service.

    Le probleme est que le processus actuel est trop lent.
    """

    packet = _extract(
        title="French Reference",
        description=description,
        language="fr",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key("demander")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(transaction.object)
        == comparison_key("d'intervention")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )


def test_explicit_english_request_payment_has_no_transaction_flow_blocker() -> None:
    description = """
    ServiceLink is a B2B marketplace.

    The client company initiates a service request.

    The contractor performs the requested service.

    The client company pays the service fee.

    The problem is that the current process is too slow.
    """

    result = idea_readiness_checker.evaluate(
        title="English Readiness",
        description=description,
        industry="B2B Marketplace / Services",
        target_region="United Kingdom",
        output_language="en",
        analysis_data={},
    )

    blockers = set(
        result.get("blockers")
        or []
    )

    assert (
        "transaction_flow"
        not in blockers
    ), result



def test_english_publish_and_send_request_are_transaction_initiations() -> None:
    publish_matches = _initiation_matches(
        "A provider publishes an offer."
    )

    send_request_matches = _initiation_matches(
        "A customer sends a request."
    )

    assert publish_matches, publish_matches
    assert send_request_matches, send_request_matches


def test_english_send_request_keeps_request_as_transaction_object() -> None:
    description = """
    ServiceLink is a B2B marketplace.

    The customer sends a request.

    The provider performs the requested service.

    The customer pays the service fee.

    The problem is that the current process is too slow.
    """

    packet = _extract(
        title="English Send Request",
        description=description,
        language="en",
    )

    transaction = packet.transaction_unit

    assert (
        comparison_key(
            transaction.initiation_action
        )
        == comparison_key("demander")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.object
        )
        == comparison_key("request")
    ), transaction.model_dump(
        mode="json"
    )

    assert (
        comparison_key(
            transaction.completion_action
        )
        == comparison_key("payer")
    ), transaction.model_dump(
        mode="json"
    )
