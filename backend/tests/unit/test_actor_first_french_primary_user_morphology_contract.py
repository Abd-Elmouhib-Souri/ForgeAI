from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def extract(
    description: str,
):
    return ProjectContextExtractor().extract(
        title="UniversalFrenchActorGrammar",
        description=description,
        industry="",
        target_region="",
        output_language="fr",
    )


def rows(packet):
    result = []

    for actor in packet.actors or []:
        role = actor.role

        if hasattr(role, "value"):
            role = role.value

        result.append(
            (
                actor.name,
                role,
            )
        )

    return result


def names(packet):
    return {
        actor.name.lower()
        for actor in packet.actors or []
    }


# ============================================================
# French actor-first primary-user morphology.
#
# Existing lexical authority must support both:
#
#   utilisateur principal
#   utilisateurs principaux
#
# without depending on project, sector or actor profession.
# ============================================================


def test_french_actor_first_masculine_singular_primary_user():
    packet = extract(
        (
            "Le superviseur d\u2019\u00e9quipe est "
            "l\u2019utilisateur principal."
        )
    )

    assert (
        "superviseur d\u2019\u00e9quipe"
        in names(packet)
    ), rows(packet)


def test_french_actor_first_second_masculine_singular_identity():
    packet = extract(
        (
            "Le coordinateur r\u00e9gional est "
            "l\u2019utilisateur principal."
        )
    )

    assert (
        "coordinateur r\u00e9gional"
        in names(packet)
    ), rows(packet)


def test_french_actor_first_masculine_plural_primary_users():
    packet = extract(
        (
            "Les op\u00e9rateurs logistiques sont "
            "les utilisateurs principaux."
        )
    )

    assert (
        "op\u00e9rateurs logistiques"
        in names(packet)
    ), rows(packet)
