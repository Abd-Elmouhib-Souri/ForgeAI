from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)
from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


def _archetypes(
    description: str,
):
    primary, secondary = (
        project_context_extractor
        ._resolve_archetypes(
            description=description,
            industry="Consumer Mobile App / Meal Planning",
            structured={},
        )
    )

    return (
        comparison_key(primary),
        {
            comparison_key(value)
            for value in secondary
        },
    )


def _packet(
    description: str,
):
    return project_context_extractor.extract(
        title="MealMate",
        description=description,
        industry="Consumer Mobile App / Meal Planning",
        target_region="United Kingdom",
        output_language="en",
    )


def _readiness(
    description: str,
):
    return idea_readiness_checker.evaluate(
        title="MealMate",
        description=description,
        industry="Consumer Mobile App / Meal Planning",
        target_region="United Kingdom",
        output_language="en",
        analysis_data={},
    )


BASE = (
    "MealMate is a mobile meal planning application for busy households. "
    "Many users spend too much time deciding what to cook and frequently "
    "buy food that is later wasted. "
    "The household user creates a weekly meal plan and generates "
    "a grocery list. "
    "The household user can pay for a monthly premium subscription. "
    "The household user makes the purchase decision directly. "
    "The first MVP includes meal planning and automatic grocery lists."
)


NEGATIVE_MARKETPLACE = (
    BASE
    + " Restaurant delivery and grocery marketplace features "
      "are not included."
)


POSITIVE_MARKETPLACE = (
    BASE
    + " The product also operates a grocery marketplace connecting "
      "households with grocery suppliers."
)


def test_marketplace_exclusion_is_recognized_as_negative_scope() -> None:
    sentence = (
        "Restaurant delivery and grocery marketplace features "
        "are not included."
    )

    assert (
        is_scope_exclusion_statement(
            sentence
        )
        is True
    )


def test_negative_marketplace_scope_does_not_become_direct_archetype_evidence() -> None:
    primary, secondary = _archetypes(
        NEGATIVE_MARKETPLACE
    )

    marketplace = comparison_key(
        "two_sided_marketplace"
    )

    assert primary != marketplace, (
        primary,
        secondary,
    )

    assert marketplace not in secondary, (
        primary,
        secondary,
    )


def test_positive_marketplace_statement_remains_archetype_evidence() -> None:
    primary, secondary = _archetypes(
        POSITIVE_MARKETPLACE
    )

    marketplace = comparison_key(
        "two_sided_marketplace"
    )

    assert (
        primary == marketplace
        or marketplace in secondary
    ), (
        primary,
        secondary,
    )


def test_negative_marketplace_scope_does_not_pollute_full_packet() -> None:
    packet = _packet(
        NEGATIVE_MARKETPLACE
    )

    marketplace = comparison_key(
        "two_sided_marketplace"
    )

    assert (
        comparison_key(
            packet.primary_archetype
        )
        != marketplace
    ), packet.model_dump(
        mode="json"
    )

    assert marketplace not in {
        comparison_key(value)
        for value
        in packet.secondary_archetypes
    }, packet.model_dump(
        mode="json"
    )


def test_negative_marketplace_scope_does_not_create_supply_demand_blockers() -> None:
    result = _readiness(
        NEGATIVE_MARKETPLACE
    )

    blockers = set(
        result.get("blockers")
        or []
    )

    assert "supply_side" not in blockers, result
    assert "demand_side" not in blockers, result


def test_real_marketplace_still_requires_structural_sides() -> None:
    result = _readiness(
        POSITIVE_MARKETPLACE
    )

    blockers = set(
        result.get("blockers")
        or []
    )

    assert (
        "supply_side" in blockers
        or "demand_side" in blockers
    ), result


def test_french_negative_marketplace_scope_is_not_positive_archetype_evidence() -> None:
    description = (
        "MealMate est une application de planification de repas. "
        "L'utilisateur construit son planning hebdomadaire. "
        "Le MVP ne comprend pas de marketplace alimentaire."
    )

    primary, secondary = (
        project_context_extractor
        ._resolve_archetypes(
            description=description,
            industry="Application mobile grand public",
            structured={},
        )
    )

    marketplace = comparison_key(
        "two_sided_marketplace"
    )

    assert (
        comparison_key(primary)
        != marketplace
    ), (
        primary,
        secondary,
    )

    assert marketplace not in {
        comparison_key(value)
        for value in secondary
    }, (
        primary,
        secondary,
    )


def test_french_positive_marketplace_statement_stays_positive() -> None:
    description = (
        "MealMate est une application de planification de repas. "
        "Le produit comprend une marketplace alimentaire qui met "
        "en relation des foyers avec des fournisseurs."
    )

    primary, secondary = (
        project_context_extractor
        ._resolve_archetypes(
            description=description,
            industry="Application mobile grand public",
            structured={},
        )
    )

    marketplace = comparison_key(
        "two_sided_marketplace"
    )

    assert (
        comparison_key(primary)
        == marketplace
        or marketplace
        in {
            comparison_key(value)
            for value in secondary
        }
    ), (
        primary,
        secondary,
    )



def test_scoped_without_marketplace_is_negative_scope() -> None:
    assert (
        is_scope_exclusion_statement(
            (
                "The first release is delivered "
                "without marketplace functionality."
            )
        )
        is True
    )


def test_scoped_sans_marketplace_is_negative_scope() -> None:
    assert (
        is_scope_exclusion_statement(
            (
                "La premiere version est livree "
                "sans fonctionnalite marketplace."
            )
        )
        is True
    )


def test_operational_without_is_not_scope_exclusion() -> None:
    assert (
        is_scope_exclusion_statement(
            "The application works without an internet connection."
        )
        is False
    )


def test_operational_sans_is_not_scope_exclusion() -> None:
    assert (
        is_scope_exclusion_statement(
            "L'application fonctionne sans connexion internet."
        )
        is False
    )



def test_scoped_initial_release_without_marketplace_is_negative_scope() -> None:
    assert (
        is_scope_exclusion_statement(
            (
                "The initial release is delivered "
                "without marketplace functionality."
            )
        )
        is True
    )
