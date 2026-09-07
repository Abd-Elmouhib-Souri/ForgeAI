from __future__ import annotations

from app.services.project_intelligence_layer import (
    ProjectIntelligenceLayer,
)


def _resolve(
    *,
    explicit_buyer: str = "",
    target_users=None,
    archetype_context=None,
    language: str = "en",
) -> str:

    return (
        ProjectIntelligenceLayer()
        ._economic_buyer(
            explicit_buyer=explicit_buyer,
            target_users=list(
                target_users
                or []
            ),
            industry="software",
            language=language,
            archetype_context=dict(
                archetype_context
                or {}
            ),
        )
    )


def test_explicit_buyer_authority_is_not_reclassified_by_generic_actor_lexicon(
    monkeypatch,
) -> None:
    """
    explicit_buyer is an already-established role authority.

    A later generic actor classifier cannot veto that authority.
    """

    pil = ProjectIntelligenceLayer()

    monkeypatch.setattr(
        pil,
        "_is_actor_phrase",
        lambda value: False,
    )

    assert (
        pil._economic_buyer(
            explicit_buyer=(
                "operating organization"
            ),
            target_users=[],
            industry="software",
            language="en",
            archetype_context={},
        )
        ==
        "operating organization"
    )


def test_explicit_buyer_authority_is_vocabulary_independent() -> None:
    """
    Equivalent explicit payer identities must not depend on
    project-, sector-, or fixture-specific marker words.
    """

    values = (
        "operating organization",
        "finance organization",
        "client organization",
        "organisation cliente",
    )

    for value in values:

        assert (
            _resolve(
                explicit_buyer=value
            )
            ==
            value
        )


def test_empty_explicit_buyer_does_not_infer_payer_from_target_position() -> None:
    """
    No explicit payer means target-user list order has no payer authority.
    """

    assert (
        _resolve(
            explicit_buyer="",
            target_users=(
                "operations coordinator",
                "inventory manager",
            ),
        )
        ==
        ""
    )


def test_empty_explicit_buyer_does_not_infer_payer_from_industry() -> None:
    """
    Industry labels are not payer evidence.
    """

    assert (
        _resolve(
            explicit_buyer="",
            target_users=(),
        )
        ==
        ""
    )


def test_existing_authoritative_actor_payer_fallback_is_preserved() -> None:
    """
    Existing canonical actor payer evidence remains a valid fallback.
    """

    assert (
        _resolve(
            explicit_buyer="",
            archetype_context={
                "actors": {
                    "payer":
                        "confirmed budget owner",
                }
            },
        )
        ==
        "confirmed budget owner"
    )