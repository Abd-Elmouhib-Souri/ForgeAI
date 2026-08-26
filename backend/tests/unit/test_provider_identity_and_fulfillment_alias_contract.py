from app.schemas.analysis_context import (
    ActorRole,
)

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _packet(
    description: str,
):
    return project_context_extractor.extract(
        title="Provider Identity Contract",
        description=description,
        industry="Professional Services",
        target_region="Europe",
        output_language="en",
    )


def _provider_keys(
    description: str,
) -> set[str]:
    packet = _packet(
        description
    )

    return {
        comparison_key(
            actor.name
        )
        for actor in packet.actors
        if actor.role == ActorRole.PROVIDER
    }


def test_contractor_execution_materializes_provider() -> None:
    providers = _provider_keys(
        "The contractor performs the requested service."
    )

    assert comparison_key(
        "contractor"
    ) in providers, providers


def test_consultant_execution_materializes_provider() -> None:
    providers = _provider_keys(
        "A consultant delivers the audit service."
    )

    assert comparison_key(
        "consultant"
    ) in providers, providers


def test_singular_execution_subject_reconciles_plural_canonical_provider() -> None:
    seed_packet = project_context_extractor.extract(
        title="Plural Provider Seed",
        description=(
            "This is a two sided marketplace. "
            "Contractors form the supply side."
        ),
        industry="Marketplace",
        target_region="Europe",
        output_language="en",
    )

    providers = [
        actor
        for actor in seed_packet.actors
        if actor.role == ActorRole.PROVIDER
    ]

    assert any(
        comparison_key(
            actor.name
        )
        == comparison_key(
            "Contractors"
        )
        for actor in providers
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in seed_packet.actors
    ]

    fulfillment = (
        project_context_extractor
        ._explicit_fulfillment_responsibility(
            sentences=[
                (
                    "The contractor performs "
                    "the requested service."
                )
            ],
            actors=seed_packet.actors,
        )
    )

    assert (
        comparison_key(
            fulfillment
        )
        == comparison_key(
            "Contractors"
        )
    ), fulfillment


def test_technical_execution_subjects_remain_non_provider() -> None:
    cases = (
        (
            "The platform performs "
            "the matching service."
        ),
        (
            "The system executes "
            "the processing work."
        ),
        (
            "The device performs "
            "the measurement work."
        ),
    )

    forbidden = {
        "platform",
        "system",
        "device",
    }

    for description in cases:
        providers = _provider_keys(
            description
        )

        assert not (
            providers
            & forbidden
        ), (
            description,
            providers,
        )
