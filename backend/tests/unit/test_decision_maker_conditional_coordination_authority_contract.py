from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)
from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def decision_names(
    description: str,
) -> list[str]:

    extractor = ProjectContextExtractor()

    return [
        name
        for name, role
        in extractor._declared_actor_roles(
            description
        )
        if role == ActorRole.DECISION_MAKER
    ]


@pytest.mark.parametrize(
    (
        "description",
        "required_unconditional",
        "hedge_markers",
    ),
    (
        (
            (
                "Les principaux decideurs sont "
                "le responsable des operations, "
                "le directeur administratif et "
                "eventuellement le directeur general "
                "pour les petites entreprises."
            ),
            (
                "responsable des operations",
                "directeur administratif",
            ),
            (
                "eventuellement",
            ),
        ),
        (
            (
                "The primary decision makers are "
                "the operations manager, "
                "the administrative director and "
                "optionally the general manager "
                "for small companies."
            ),
            (
                "operations manager",
                "administrative director",
            ),
            (
                "optionally",
            ),
        ),
    ),
)
def test_conditional_coordinator_cannot_contaminate_prior_decision_identity(
    description: str,
    required_unconditional: tuple[str, ...],
    hedge_markers: tuple[str, ...],
) -> None:
    """
    An unconditional actor immediately preceding an optional /
    conditional actor must remain an independent canonical identity.

    This contract deliberately does not decide whether the conditional
    actor must itself be materialized as an unconditional decision
    maker in the current schema.
    """

    names = decision_names(
        description
    )

    actual_keys = {
        comparison_key(
            name
        )
        for name in names
        if comparison_key(
            name
        )
    }

    required_keys = {
        comparison_key(
            name
        )
        for name in required_unconditional
    }

    assert required_keys.issubset(
        actual_keys
    ), (
        required_keys,
        actual_keys,
        names,
    )

    for name in names:

        key = comparison_key(
            name
        )

        assert not any(
            marker in key
            for marker in hedge_markers
        ), names


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    (
        (
            "fr",
            (
                "Les principaux decideurs sont "
                "le responsable des operations, "
                "le directeur administratif et "
                "eventuellement le directeur general "
                "pour les petites entreprises."
            ),
            "directeur administratif",
        ),
        (
            "en",
            (
                "The primary decision makers are "
                "the operations manager, "
                "the administrative director and "
                "optionally the general manager "
                "for small companies."
            ),
            "administrative director",
        ),
    ),
)
def test_conditional_coordination_boundary_survives_packet_materialization(
    language: str,
    description: str,
    expected: str,
) -> None:
    """
    The same actor-identity boundary must survive the complete
    ProjectContextPacketV3 materialization path.
    """

    packet = ProjectContextExtractor().extract(
        title="DecisionFlow",
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data={},
    )

    actual_keys = {
        comparison_key(
            name
        )
        for name in packet.decision_maker_actor_names
        if comparison_key(
            name
        )
    }

    assert comparison_key(
        expected
    ) in actual_keys

    forbidden_markers = (
        "eventuellement",
        "optionally",
    )

    for name in packet.decision_maker_actor_names:

        key = comparison_key(
            name
        )

        assert not any(
            marker in key
            for marker in forbidden_markers
        ), packet.decision_maker_actor_names


def test_internal_coordination_remains_part_of_actor_identity() -> None:
    """
    Anti-overfit.

    Ordinary conjunction inside a legitimate actor noun phrase
    must not become a structural list separator.
    """

    description = (
        "The primary decision makers are "
        "the operations manager, "
        "the research and development director, and "
        "the general manager."
    )

    names = decision_names(
        description
    )

    assert (
        "research and development director"
        in names
    )



@pytest.mark.parametrize(
    (
        "description",
        "expected",
    ),
    (
        (
            (
                "Les principaux decideurs sont "
                "le responsable des operations, "
                "le directeur administratif et "
                "le directeur general."
            ),
            (
                "responsable des operations",
                "directeur administratif",
                "directeur general",
            ),
        ),
        (
            (
                "The primary decision makers are "
                "the operations manager, "
                "the administrative director and "
                "the general manager."
            ),
            (
                "operations manager",
                "administrative director",
                "general manager",
            ),
        ),
    ),
)
def test_non_oxford_three_actor_decision_list_is_atomic_and_canonical(
    description: str,
    expected: tuple[str, ...],
) -> None:
    """
    A three-actor list remains structural even when the final
    coordinator is not preceded by an Oxford comma.

        A, B and C
        A, B et C

    must preserve A / B / C as independent actor identities.

    This authority is local to an already-recognized
    DECISION_MAKER relation.
    """

    actual = decision_names(
        description
    )

    actual_keys = {
        comparison_key(
            value
        )
        for value in actual
        if comparison_key(
            value
        )
    }

    expected_keys = {
        comparison_key(
            value
        )
        for value in expected
    }

    assert expected_keys == actual_keys, (
        expected_keys,
        actual_keys,
        actual,
    )


@pytest.mark.parametrize(
    (
        "description",
        "required",
    ),
    (
        (
            (
                "Les principaux decideurs sont "
                "le responsable des operations, "
                "le directeur administratif et "
                "eventuellement le directeur general."
            ),
            (
                "responsable des operations",
                "directeur administratif",
            ),
        ),
        (
            (
                "The primary decision makers are "
                "the operations manager, "
                "the administrative director and "
                "optionally the general manager."
            ),
            (
                "operations manager",
                "administrative director",
            ),
        ),
    ),
)
def test_conditional_terminal_actor_is_not_promoted_to_unconditional_relation(
    description: str,
    required: tuple[str, ...],
) -> None:
    """
    The unconditional prefix of a decision-maker declaration
    remains authoritative.

    A terminal candidate explicitly marked optional/conditional
    must not be emitted as an unconditional DECISION_MAKER.

    The current schema does not need to decide here how that
    conditional relation is represented elsewhere.
    """

    actual = decision_names(
        description
    )

    actual_keys = {
        comparison_key(
            value
        )
        for value in actual
        if comparison_key(
            value
        )
    }

    required_keys = {
        comparison_key(
            value
        )
        for value in required
    }

    assert required_keys.issubset(
        actual_keys
    ), (
        required_keys,
        actual_keys,
        actual,
    )

    conditional_prefixes = (
        "eventuellement ",
        "optionally ",
    )

    assert not any(
        comparison_key(
            value
        ).startswith(
            conditional_prefixes
        )
        for value in actual
    ), actual
