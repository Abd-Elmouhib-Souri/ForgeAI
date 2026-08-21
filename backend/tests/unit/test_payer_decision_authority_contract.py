import re

import pytest

from app.schemas.analysis_context import comparison_key
from app.services.project_context_extractor import (
    project_context_extractor,
)


def actor_key(value):
    """
    Compare actor identity independently from a leading article.

    Surface labels may legitimately preserve:
    le / la / l' / the / a / an.
    That formatting difference must not change actor identity.
    """
    key = comparison_key(
        value
    )

    return re.sub(
        r"^(?:"
        r"le|la|les|l|"
        r"the|a|an"
        r")\s+",
        "",
        key,
        flags=re.IGNORECASE,
    ).strip()


def keys(values):
    return {
        actor_key(value)
        for value in values
    }


@pytest.mark.parametrize(
    (
        "language",
        "sentence",
        "actor",
    ),
    [
        (
            "fr",
            (
                "L\u2019entreprise cliente paie "
                "un abonnement mensuel."
            ),
            "entreprise cliente",
        ),
        (
            "en",
            (
                "The client company pays "
                "a monthly subscription."
            ),
            "client company",
        ),
    ],
)
def test_payer_only_never_becomes_decision_maker(
    language,
    sentence,
    actor,
):
    packet = (
        project_context_extractor
        .extract(
            title="RoleAuthority",
            description=sentence,
            industry="software",
            target_region="Europe",
            output_language=language,
        )
    )

    assert (
        actor_key(actor)
        in keys(
            packet.payer_actor_names
        )
    )

    assert (
        actor_key(actor)
        not in keys(
            packet.decision_maker_actor_names
        )
    )


@pytest.mark.parametrize(
    (
        "language",
        "sentence",
        "actor",
    ),
    [
        (
            "fr",
            (
                "Le d\u00e9cideur est "
                "la directrice des op\u00e9rations."
            ),
            "directrice des op\u00e9rations",
        ),
        (
            "en",
            (
                "The decision-maker is "
                "the operations director."
            ),
            "operations director",
        ),
    ],
)
def test_decision_maker_only_never_becomes_payer(
    language,
    sentence,
    actor,
):
    packet = (
        project_context_extractor
        .extract(
            title="RoleAuthority",
            description=sentence,
            industry="software",
            target_region="Europe",
            output_language=language,
        )
    )

    assert (
        actor_key(actor)
        in keys(
            packet.decision_maker_actor_names
        )
    )

    assert (
        actor_key(actor)
        not in keys(
            packet.payer_actor_names
        )
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "actor",
    ),
    [
        (
            "fr",
            (
                "L\u2019entreprise cliente paie "
                "un abonnement mensuel. "
                "Le d\u00e9cideur est "
                "l\u2019entreprise cliente."
            ),
            "entreprise cliente",
        ),
        (
            "en",
            (
                "The client company pays "
                "a monthly subscription. "
                "The decision-maker is "
                "the client company."
            ),
            "client company",
        ),
    ],
)
def test_same_actor_can_hold_both_roles_only_when_both_are_declared(
    language,
    description,
    actor,
):
    packet = (
        project_context_extractor
        .extract(
            title="RoleAuthority",
            description=description,
            industry="software",
            target_region="Europe",
            output_language=language,
        )
    )

    expected = comparison_key(
        actor
    )

    assert (
        expected
        in keys(
            packet.payer_actor_names
        )
    )

    assert (
        expected
        in keys(
            packet.decision_maker_actor_names
        )
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "payer",
        "decision_maker",
    ),
    [
        (
            "fr",
            (
                "L\u2019entreprise cliente paie "
                "l\u2019abonnement. "
                "Le d\u00e9cideur est "
                "le directeur financier."
            ),
            "entreprise cliente",
            "directeur financier",
        ),
        (
            "en",
            (
                "The client company pays "
                "the subscription. "
                "The decision-maker is "
                "the finance director."
            ),
            "client company",
            "finance director",
        ),
    ],
)
def test_distinct_payer_and_decision_maker_remain_distinct(
    language,
    description,
    payer,
    decision_maker,
):
    packet = (
        project_context_extractor
        .extract(
            title="RoleAuthority",
            description=description,
            industry="software",
            target_region="Europe",
            output_language=language,
        )
    )

    payer_keys = keys(
        packet.payer_actor_names
    )

    decision_keys = keys(
        packet.decision_maker_actor_names
    )

    assert (
        actor_key(payer)
        in payer_keys
    )

    assert (
        actor_key(decision_maker)
        in decision_keys
    )

    assert (
        actor_key(decision_maker)
        not in payer_keys
    )

    assert (
        actor_key(payer)
        not in decision_keys
    )
