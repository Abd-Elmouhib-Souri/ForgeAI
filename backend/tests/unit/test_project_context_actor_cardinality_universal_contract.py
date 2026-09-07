from __future__ import annotations

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


STRUCTURED_TARGETS = [
    "workflow coordinator",
    "production supervisor",
    "inventory manager",
    "quality reviewer",
    "business buyer",
    "delivery partner",
]


def _names(
    actors,
):
    return [
        actor.name
        for actor
        in actors
    ]


def test_structured_target_population_is_not_silently_truncated() -> None:
    """
    Structured current-project actor evidence is canonical population
    evidence. Distinct identities must not disappear because the list
    crosses an arbitrary implementation cardinality.
    """
    extractor = ProjectContextExtractor()

    actors = extractor._fallback_actors(
        structured={
            "target_users":
                STRUCTURED_TARGETS,
        },
        archetype_context={},
    )

    assert _names(
        actors
    ) == STRUCTURED_TARGETS


def test_fresh_relation_reconciliation_preserves_unrelated_actor_population() -> None:
    """
    Adding fresh role authority may clean/upgrade the related identity,
    but must not truncate unrelated already-canonical actors.
    """
    extractor = ProjectContextExtractor()

    actors = [
        ActorContext(
            name=f"canonical participant {index}",
            role=ActorRole.OTHER,
            is_explicit=True,
        )
        for index
        in range(
            1,
            11,
        )
    ]

    reconciled = (
        extractor
        ._reconcile_fresh_declared_actor_authority(
            actors=actors,
            description=(
                "Decision maker: independent approver."
            ),
        )
    )

    assert _names(
        reconciled
    ) == _names(
        actors
    )


def test_workflow_reconciliation_never_truncates_existing_canonical_actors() -> None:
    """
    Workflow discovery may enrich actor membership.
    It must never discard valid actors already supplied by the
    canonical actor authority.
    """
    extractor = ProjectContextExtractor()

    actors = [
        ActorContext(
            name=f"canonical participant {index}",
            role=ActorRole.OTHER,
            is_explicit=True,
        )
        for index
        in range(
            1,
            11,
        )
    ]

    reconciled = (
        extractor
        ._reconcile_workflow_actor_membership(
            actors=actors,
            workflows=[],
        )
    )

    assert _names(
        reconciled
    ) == _names(
        actors
    )


def test_public_packet_preserves_structured_population_with_explicit_relation() -> None:
    """
    A distinct explicit decision-maker relation must coexist with every
    distinct structured actor declared by the current description.
    """
    description = (
        "Primary operational users:\n"
        "- workflow coordinator\n"
        "- production supervisor\n"
        "- inventory manager\n"
        "- quality reviewer\n"
        "External users:\n"
        "- business buyer\n"
        "- delivery partner\n"
        "Decision makers:\n"
        "- organization owner\n"
        "MVP capabilities:\n"
        "- record management"
    )

    packet = (
        ProjectContextExtractor()
        .extract(
            title="Neutral Actor Cardinality",
            description=description,
            industry="software",
            target_region="Global",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )

    actual = set(
        _names(
            packet.actors
        )
    )

    expected = set(
        STRUCTURED_TARGETS
        + [
            "organization owner",
        ]
    )

    assert expected.issubset(
        actual
    )

    assert "delivery partner" in (
        packet.partner_actor_names
    )


def test_small_structured_population_remains_stable() -> None:
    """
    Removing arbitrary truncation must not require or manufacture
    additional actors for small valid populations.
    """
    extractor = ProjectContextExtractor()

    source = [
        "workflow coordinator",
        "delivery partner",
    ]

    actors = extractor._fallback_actors(
        structured={
            "target_users":
                source,
        },
        archetype_context={},
    )

    assert _names(
        actors
    ) == source


def test_explicit_project_context_actor_population_is_not_silently_truncated() -> None:
    """
    Explicit current-project target-user evidence is canonical actor
    evidence. Its preservation must not depend on an arbitrary maximum
    actor count.
    """
    extractor = ProjectContextExtractor()

    source = [
        f"explicit participant {index}"
        for index
        in range(
            1,
            11,
        )
    ]

    actors = (
        extractor
        ._extract_explicit_actors(
            description="",
            project_context={
                "target_users":
                    source,
            },
            analysis_data={},
        )
    )

    assert _names(
        actors
    ) == source
