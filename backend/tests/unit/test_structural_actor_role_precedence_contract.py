from __future__ import annotations

from app.schemas.analysis_context import (
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def declared_roles(description: str):
    extractor = ProjectContextExtractor()

    return {
        comparison_key(name): role.value
        for name, role in (
            extractor._declared_actor_groups(
                description
            )
        )
    }


def role_for(
    description: str,
    actor_name: str,
):
    return declared_roles(
        description
    ).get(
        comparison_key(
            actor_name
        )
    )


# ============================================================
# Structural membership declarations.
#
# These prove participation in the product/context but must
# preserve a more precise lexical canonical role when one is
# already available.
# ============================================================


def test_primary_user_list_preserves_specific_operator_role_fr():
    description = (
        "Les utilisateurs principaux sont "
        "les op\u00e9rateurs et les administrateurs."
    )

    assert role_for(
        description,
        "op\u00e9rateurs",
    ) == "operator"

    assert role_for(
        description,
        "administrateurs",
    ) == "user"


def test_user_group_membership_preserves_provider_role_fr():
    description = (
        "Les deux groupes d'utilisateurs sont "
        "les m\u00e9nages et "
        "les prestataires de services."
    )

    assert role_for(
        description,
        "m\u00e9nages",
    ) == "user"

    assert role_for(
        description,
        "prestataires de services",
    ) == "provider"


def test_user_group_membership_preserves_provider_role_en():
    description = (
        "The user groups are households "
        "and service providers."
    )

    assert role_for(
        description,
        "households",
    ) == "user"

    assert role_for(
        description,
        "service providers",
    ) == "provider"


def test_actor_first_primary_membership_preserves_operator_role_fr():
    description = (
        "Les op\u00e9rateurs logistiques sont "
        "les utilisateurs principaux."
    )

    assert role_for(
        description,
        "op\u00e9rateurs logistiques",
    ) == "operator"


def test_actor_first_primary_membership_preserves_operator_role_en():
    description = (
        "Warehouse operators are "
        "the primary users."
    )

    assert role_for(
        description,
        "warehouse operators",
    ) == "operator"


def test_secondary_user_membership_preserves_operator_role_fr():
    description = (
        "Les employ\u00e9s sont "
        "des utilisateurs secondaires."
    )

    assert role_for(
        description,
        "employ\u00e9s",
    ) == "operator"


def test_secondary_user_membership_preserves_operator_role_en():
    description = (
        "Employees are secondary users."
    )

    assert role_for(
        description,
        "Employees",
    ) == "operator"


# ============================================================
# Explicit operational-role assignment.
#
# These declarations explicitly state USER authority and must
# not be reclassified by incidental domain vocabulary.
# ============================================================


def test_label_first_operational_user_role_is_authoritative_fr():
    description = (
        "L\u2019utilisateur op\u00e9rationnel principal est "
        "le coordinateur de maintenance."
    )

    assert role_for(
        description,
        "coordinateur de maintenance",
    ) == "user"


def test_label_first_operational_user_role_is_authoritative_en():
    description = (
        "The primary operational user is "
        "the maintenance coordinator."
    )

    assert role_for(
        description,
        "maintenance coordinator",
    ) == "user"
