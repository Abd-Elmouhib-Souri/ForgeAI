from types import SimpleNamespace

from app.services.project_context_extractor import (
    project_context_extractor,
)


def actors(*names):
    return [
        SimpleNamespace(
            name=name
        )
        for name in names
    ]


def resolve(
    sentence,
    surface,
    canonical_actors,
    fallback="",
):
    start = sentence.casefold().find(
        surface.casefold()
    )

    assert start >= 0

    return (
        project_context_extractor
        ._workflow_actor_for_sentence(
            sentence,
            action_start=start,
            actors=canonical_actors,
            fallback_actor=fallback,
        )
    )


def test_company_wrapper_alias_maps_to_canonical_actor():
    canonical = actors(
        "l\u2019entreprise locataire",
    )

    sentence = (
        "Une entreprise locataire "
        "recherche une offre."
    )

    assert resolve(
        sentence,
        "recherche",
        canonical,
    ) == "l\u2019entreprise locataire"


def test_short_unique_actor_identity_maps_to_long_canonical_actor():
    canonical = actors(
        (
            "entreprises propri\u00e9taires "
            "d\u2019\u00e9quipements professionnels"
        ),
    )

    sentence = (
        "Une entreprise propri\u00e9taire "
        "cr\u00e9e une annonce."
    )

    assert resolve(
        sentence,
        "cr\u00e9e",
        canonical,
    ) == (
        "entreprises propri\u00e9taires "
        "d\u2019\u00e9quipements professionnels"
    )


def test_coordinated_action_fragment_uses_previous_actor():
    canonical = actors(
        "l\u2019entreprise locataire",
    )

    sentence = (
        "Une entreprise locataire recherche une offre, "
        "consulte les options."
    )

    first = resolve(
        sentence,
        "recherche",
        canonical,
    )

    second = resolve(
        sentence,
        "consulte",
        canonical,
        fallback=first,
    )

    assert first == "l\u2019entreprise locataire"
    assert second == "l\u2019entreprise locataire"


def test_new_explicit_subject_replaces_previous_actor():
    canonical = actors(
        "provider",
        "buyer",
    )

    sentence = (
        "The provider sends a request "
        "and the buyer accepts it."
    )

    assert resolve(
        sentence,
        "accepts",
        canonical,
        fallback="provider",
    ) == "buyer"


def test_ambiguous_short_identity_is_not_forced():
    canonical = actors(
        "customer administrators",
        "customer operators",
    )

    sentence = (
        "The customer reviews the record."
    )

    resolved = resolve(
        sentence,
        "reviews",
        canonical,
        fallback="",
    )

    assert resolved != "customer administrators"
    assert resolved != "customer operators"



def test_leading_actor_survives_unrecognized_prior_predicate():
    canonical = actors(
        "passagers urbains",
    )

    sentence = (
        "Le passager saisit son point de depart "
        "et demande une course."
    )

    assert resolve(
        sentence,
        "demande",
        canonical,
    ) == "passagers urbains"


def test_actor_mentioned_as_object_is_not_reused_as_next_subject():
    canonical = actors(
        "customer",
    )

    sentence = (
        "The item is handed over to the customer, "
        "then returned."
    )

    assert resolve(
        sentence,
        "returned",
        canonical,
        fallback="",
    ) == ""
