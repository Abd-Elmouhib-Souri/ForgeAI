from __future__ import annotations

from typing import Any

from app.services.project_archetype_resolver import (
    project_archetype_resolver,
)


TAXI_SEARCH_IDENTITY_MARKERS = (
    "taxi booking",
    "ride hailing",
    "e hailing",
    "taxi dispatch",
    "commande taxi",
    "reservation taxi",
    "réservation taxi",
    "mise en relation taxi chauffeur",
)


def _normalize(
    value: Any,
) -> str:

    return " ".join(
        str(
            value
            or ""
        )
        .casefold()
        .split()
    )


def _primary(
    result,
) -> str:

    return _normalize(
        result.get(
            "primary_archetype"
        )
        or
        result.get(
            "project_archetype"
        )
    )


def _search_blob(
    result,
) -> str:

    return _normalize(
        " ".join(
            str(value)
            for value in (
                result.get(
                    "search_terms"
                )
                or []
            )
        )
    )


def _resolve(
    *,
    description: str,
    workflows: list[str],
    industry: str = "Operational Logistics Management",
    title: str = "Neutral Operations Platform",
    target_users: list[str] | None = None,
    problem: str = (
        "Operational teams need auditable coordination."
    ),
    solution: str = (
        "Centralize requests, transfers and completion records."
    ),
    business_model: str = "B2B subscription",
    language: str = "en",
):

    return (
        project_archetype_resolver
        .resolve(
            title=title,
            description=description,
            industry=industry,
            target_region="Global",
            output_language=language,
            target_users=(
                target_users
                or [
                    "operations coordinator",
                ]
            ),
            problem=problem,
            solution=solution,
            business_model=business_model,
            workflows=workflows,
        )
    )


def _assert_no_taxi_identity(
    result,
) -> None:

    assert (
        _normalize(
            result.get(
                "vertical"
            )
        )
        !=
        "mobility_taxi"
    ), result

    search_blob = _search_blob(
        result
    )

    leaked = [
        marker
        for marker
        in TAXI_SEARCH_IDENTITY_MARKERS
        if marker
        in search_blob
    ]

    assert leaked == [], {
        "leaked_taxi_identity":
            leaked,

        "result":
            result,
    }


def _assert_true_taxi_identity(
    result,
) -> None:

    assert (
        _normalize(
            result.get(
                "vertical"
            )
        )
        ==
        "mobility_taxi"
    ), result

    search_blob = _search_blob(
        result
    )

    assert any(
        marker
        in search_blob
        for marker
        in TAXI_SEARCH_IDENTITY_MARKERS
    ), result


def test_generic_pickup_cannot_establish_taxi_vertical_identity() -> None:
    """
    Pickup is a generic logistics/operations concept.

    It cannot, by itself, establish taxi identity or inject taxi-specific
    research terms.
    """

    result = _resolve(
        description=(
            "A B2B custody platform coordinates pickup "
            "of operational items between facilities."
        ),
        workflows=[
            "create pickup request",
            "record custody transfer",
            "confirm receipt",
        ],
    )

    _assert_no_taxi_identity(
        result
    )


def test_generic_destination_cannot_establish_taxi_vertical_identity() -> None:
    """
    Destination is a generic movement/logistics concept.

    It cannot, by itself, establish taxi identity.
    """

    result = _resolve(
        description=(
            "A B2B transfer platform records where operational "
            "items must be delivered and confirms their destination."
        ),
        workflows=[
            "create transfer request",
            "record handoff",
            "confirm destination receipt",
        ],
    )

    _assert_no_taxi_identity(
        result
    )


def test_multiple_generic_logistics_terms_still_do_not_create_taxi_identity() -> None:
    """
    Multiple weak generic logistics concepts do not become taxi evidence
    merely because several of them occur together.
    """

    result = _resolve(
        industry=(
            "Industrial Equipment Logistics"
        ),
        description=(
            "Industrial equipment teams coordinate pickup requests, "
            "custody handoffs and destination receipt records."
        ),
        workflows=[
            "create equipment pickup request",
            "record equipment handoff",
            "confirm destination receipt",
        ],
    )

    _assert_no_taxi_identity(
        result
    )


def test_generic_delivery_driver_role_cannot_establish_taxi_identity() -> None:
    """
    Driver is not intrinsically a taxi actor.

    Delivery, freight, service and industrial operations may all contain
    drivers without being taxi or ride-hailing products.
    """

    result = _resolve(
        industry=(
            "Distribution Operations"
        ),
        description=(
            "A B2B distribution platform lets an operations coordinator "
            "assign a delivery driver to a shipment and confirm receipt."
        ),
        target_users=[
            "operations coordinator",
            "delivery driver",
        ],
        workflows=[
            "assign delivery driver",
            "record shipment handoff",
            "confirm delivery receipt",
        ],
    )

    _assert_no_taxi_identity(
        result
    )


def test_generic_french_prise_en_charge_cannot_establish_taxi_identity() -> None:
    """
    'Prise en charge' is a generic French operational expression.

    It may describe case handling, healthcare, support or logistics and
    therefore cannot establish taxi identity by itself.
    """

    result = _resolve(
        industry=(
            "Gestion opérationnelle B2B"
        ),
        title=(
            "Plateforme opérationnelle neutre"
        ),
        description=(
            "La plateforme enregistre la prise en charge "
            "d'un dossier opérationnel et sa clôture."
        ),
        target_users=[
            "coordinateur opérationnel",
        ],
        workflows=[
            "enregistrer la prise en charge du dossier",
            "suivre le traitement",
            "confirmer la clôture",
        ],
        problem=(
            "Le suivi des dossiers opérationnels est manuel."
        ),
        solution=(
            "Centraliser le suivi des dossiers."
        ),
        language="fr",
    )

    _assert_no_taxi_identity(
        result
    )


def test_adding_generic_pickup_is_identity_invariant_for_non_taxi_project() -> None:
    """
    Metamorphic invariant.

    Adding a generic pickup operation to an otherwise identical non-taxi
    project cannot flip its vertical or primary archetype into taxi /
    marketplace identity.
    """

    base = _resolve(
        description=(
            "A B2B custody platform records transfer requests, "
            "handoffs and completed receipts."
        ),
        workflows=[
            "create transfer request",
            "record custody handoff",
            "confirm receipt",
        ],
    )

    mutated = _resolve(
        description=(
            "A B2B custody platform records pickup requests, "
            "handoffs and completed receipts."
        ),
        workflows=[
            "create pickup request",
            "record custody handoff",
            "confirm receipt",
        ],
    )

    assert (
        _normalize(
            mutated.get(
                "vertical"
            )
        )
        ==
        _normalize(
            base.get(
                "vertical"
            )
        )
    ), {
        "base":
            base,

        "mutated":
            mutated,
    }

    assert (
        _primary(
            mutated
        )
        ==
        _primary(
            base
        )
    ), {
        "base":
            base,

        "mutated":
            mutated,
    }

    _assert_no_taxi_identity(
        mutated
    )


def test_explicit_taxi_booking_remains_sufficient_strong_evidence() -> None:
    """
    Recall preservation.

    A single semantically strong taxi-specific concept may still establish
    the taxi vertical. No arbitrary minimum-signal-count rule is allowed.
    """

    result = _resolve(
        title=(
            "Neutral Taxi Booking Service"
        ),
        industry=(
            "Taxi Services"
        ),
        description=(
            "A taxi booking platform lets customers request "
            "a taxi and drivers accept the booking."
        ),
        target_users=[
            "taxi passengers",
            "taxi drivers",
        ],
        workflows=[
            "book taxi",
            "driver accepts taxi booking",
            "complete taxi trip",
        ],
        business_model=(
            "commission per completed booking"
        ),
    )

    _assert_true_taxi_identity(
        result
    )


def test_explicit_ride_hailing_remains_sufficient_strong_evidence() -> None:
    """
    A clearly stated ride-hailing product must preserve mobility recall.
    """

    result = _resolve(
        title=(
            "Neutral Ride Hailing Service"
        ),
        industry=(
            "Ride Hailing"
        ),
        description=(
            "A ride hailing platform matches riders "
            "with drivers for requested rides."
        ),
        target_users=[
            "riders",
            "drivers",
        ],
        workflows=[
            "request ride",
            "accept ride request",
            "complete ride",
        ],
        business_model=(
            "commission per completed ride"
        ),
    )

    _assert_true_taxi_identity(
        result
    )


def test_explicit_french_taxi_identity_remains_supported() -> None:
    """
    Strong taxi identity must remain supported independently of language.
    """

    result = _resolve(
        title=(
            "Service de réservation de taxi"
        ),
        industry=(
            "Services de taxi"
        ),
        description=(
            "Une plateforme de réservation de taxi "
            "met en relation des clients et des chauffeurs."
        ),
        target_users=[
            "clients",
            "chauffeurs de taxi",
        ],
        workflows=[
            "réserver un taxi",
            "accepter une réservation taxi",
            "terminer la course taxi",
        ],
        business_model=(
            "commission par course"
        ),
        language="fr",
    )

    _assert_true_taxi_identity(
        result
    )