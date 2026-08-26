from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _bounds(
    description: str,
):
    sentences = (
        project_context_extractor
        ._sentences(
            description
        )
    )

    return (
        project_context_extractor
        ._explicit_transaction_flow_bounds(
            sentences
        )
    )


def test_reservation_after_prior_publication_is_contextual_completion_fr() -> None:
    start, completion = _bounds(
        (
            "Le vendeur publie un lot. "
            "L'acheteur reserve le lot."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("reserver")
    ), (
        start,
        completion,
    )


def test_booking_after_prior_publication_is_contextual_completion_en() -> None:
    start, completion = _bounds(
        (
            "The seller publishes an item. "
            "The buyer books the item."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("reserver")
    ), (
        start,
        completion,
    )


def test_booking_without_prior_start_remains_transaction_start() -> None:
    start, completion = _bounds(
        (
            "The buyer books a provider service. "
            "The provider delivers the service. "
            "The buyer pays the fee."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("reserver")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("payer")
    ), (
        start,
        completion,
    )


def test_later_conclusion_overrides_intermediate_reservation() -> None:
    start, completion = _bounds(
        (
            "Le vendeur publie un lot. "
            "L'acheteur reserve le lot "
            "et conclut la transaction."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key(
            "conclure la transaction"
        )
    ), (
        start,
        completion,
    )


def test_business_model_completed_transaction_is_not_operational_completion() -> None:
    start, completion = _bounds(
        (
            "Le vendeur publie un lot. "
            "Le modele economique est une commission "
            "par transaction terminee."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert completion == "", (
        start,
        completion,
    )



def test_explicit_transaction_unit_booking_is_not_lifecycle_completion() -> None:
    start, completion = _bounds(
        (
            "A customer sends a request. "
            "The primary transaction unit is a service booking."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("demander")
    ), (
        start,
        completion,
    )

    assert completion == "", (
        start,
        completion,
    )


def test_explicit_transaction_unit_booking_does_not_manufacture_start() -> None:
    start, completion = _bounds(
        (
            "The transaction is closed. "
            "The primary transaction unit is a service booking."
        )
    )

    assert start == "", (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("cloturer")
    ), (
        start,
        completion,
    )



def test_commission_on_completed_intervention_does_not_override_payment() -> None:
    start, completion = _bounds(
        (
            "L'entreprise cliente initie une demande d'intervention. "
            "Le technicien realise l'intervention. "
            "L'entreprise cliente paie le prix de l'intervention. "
            "RepairLink preleve une commission sur chaque intervention "
            "terminee avec succes."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("demander")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("payer")
    ), (
        start,
        completion,
    )


def test_fee_on_completed_transaction_does_not_manufacture_completion_en() -> None:
    start, completion = _bounds(
        (
            "The seller publishes an item. "
            "The platform charges a fee on each completed transaction."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert completion == "", (
        start,
        completion,
    )


def test_explicit_completed_state_remains_valid_completion() -> None:
    start, completion = _bounds(
        (
            "L'entreprise cliente initie une demande d'intervention. "
            "Le technicien realise l'intervention et "
            "l'entreprise confirme que l'intervention est terminee."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("demander")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("terminer")
    ), (
        start,
        completion,
    )


def test_explicit_closed_transaction_remains_valid_completion() -> None:
    start, completion = _bounds(
        (
            "The provider publishes an offer. "
            "The transaction is closed."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("publier")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("cloturer")
    ), (
        start,
        completion,
    )


def test_payment_after_explicit_completed_state_remains_final_completion() -> None:
    start, completion = _bounds(
        (
            "L'entreprise cliente initie une demande d'intervention. "
            "Le technicien realise l'intervention et "
            "l'entreprise confirme que l'intervention est terminee. "
            "L'entreprise cliente paie le prix de l'intervention."
        )
    )

    assert (
        comparison_key(start)
        == comparison_key("demander")
    ), (
        start,
        completion,
    )

    assert (
        comparison_key(completion)
        == comparison_key("payer")
    ), (
        start,
        completion,
    )
