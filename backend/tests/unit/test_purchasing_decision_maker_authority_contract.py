from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _decision_makers(
    description: str,
    *,
    language: str = "en",
) -> list[str]:
    packet = project_context_extractor.extract(
        title="Decision Maker Contract",
        description=description,
        industry="Generic B2B / Product",
        target_region="Europe",
        output_language=language,
    )

    return [
        comparison_key(
            actor.name
        )
        for actor in packet.actors
        if actor.role == ActorRole.DECISION_MAKER
    ]


def _assert_only_decision_maker(
    description: str,
    expected: str,
    *,
    language: str = "en",
) -> None:
    actual = _decision_makers(
        description,
        language=language,
    )

    assert actual == [
        comparison_key(
            expected
        )
    ], (
        description,
        actual,
    )


def test_base_main_decision_maker_remains_supported() -> None:
    _assert_only_decision_maker(
        (
            "The farm owner is the main "
            "decision maker."
        ),
        "farm owner",
    )


def test_purchasing_decision_maker_is_supported() -> None:
    _assert_only_decision_maker(
        (
            "The farm owner is the main purchasing "
            "decision maker."
        ),
        "farm owner",
    )


def test_purchase_decision_maker_is_supported() -> None:
    _assert_only_decision_maker(
        (
            "The plant director is the primary purchase "
            "decision maker."
        ),
        "plant director",
    )


def test_procurement_decision_maker_is_supported() -> None:
    _assert_only_decision_maker(
        (
            "The procurement director is the primary "
            "procurement decision maker."
        ),
        "procurement director",
    )


def test_buying_decision_maker_is_supported() -> None:
    _assert_only_decision_maker(
        (
            "The business owner is the main buying "
            "decision maker."
        ),
        "business owner",
    )


def test_decision_maker_can_be_followed_by_explicit_action() -> None:
    _assert_only_decision_maker(
        (
            "The farm owner is the main purchasing "
            "decision maker and authorizes "
            "the equipment purchase."
        ),
        "farm owner",
    )


def test_existing_decision_scope_suffix_remains_supported() -> None:
    _assert_only_decision_maker(
        (
            "The farm owner is the main decision maker "
            "for purchasing equipment."
        ),
        "farm owner",
    )


def test_purchase_authorization_alone_is_not_role_authority() -> None:
    assert not _decision_makers(
        (
            "The farm owner authorizes "
            "the equipment purchase."
        )
    )


def test_negated_base_decision_maker_is_rejected() -> None:
    assert not _decision_makers(
        (
            "The farm owner is not the main "
            "decision maker."
        )
    )


def test_negated_purchasing_decision_maker_is_rejected() -> None:
    assert not _decision_makers(
        (
            "The farm owner is not the main purchasing "
            "decision maker."
        )
    )


def test_french_actor_first_purchase_decision_maker_is_supported() -> None:
    _assert_only_decision_maker(
        (
            "Le proprietaire est le decideur "
            "d'achat principal."
        ),
        "proprietaire",
        language="fr",
    )


def test_french_purchase_decision_maker_can_have_continuation() -> None:
    _assert_only_decision_maker(
        (
            "Le proprietaire est le decideur "
            "d'achat principal et autorise l'achat."
        ),
        "proprietaire",
        language="fr",
    )


def test_french_negated_purchase_decision_maker_is_rejected() -> None:
    assert not _decision_makers(
        (
            "Le proprietaire n'est pas le decideur "
            "d'achat principal."
        ),
        language="fr",
    )
