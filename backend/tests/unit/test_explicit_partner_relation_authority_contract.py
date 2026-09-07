from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)
from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def extract(
    *,
    description: str,
    language: str,
):
    return ProjectContextExtractor().extract(
        title="PartnerFlow",
        description=description,
        industry="General operations",
        target_region="International",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def role_names(
    packet,
    role: ActorRole,
) -> list[str]:

    return [
        actor.name
        for actor in packet.actors
        if actor.role == role
    ]


def keys(
    values,
) -> set[str]:

    return {
        comparison_key(
            value
        )
        for value in values
        if comparison_key(
            value
        )
    }


# ============================================================
# D3-A ? LABEL-FIRST SINGLE
#
# Explicit semantic relation outranks lexical fallback.
# ============================================================

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
                "Le partenaire operationnel est "
                "le prestataire local."
            ),
            "prestataire local",
        ),
        (
            "en",
            (
                "The operational partner is "
                "the local service provider."
            ),
            "local service provider",
        ),
    ),
)
def test_explicit_partner_relation_materializes_partner_role(
    language: str,
    description: str,
    expected: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    expected_key = comparison_key(
        expected
    )

    assert expected_key in keys(
        role_names(
            packet,
            ActorRole.PARTNER,
        )
    ), (
        language,
        [
            (
                actor.name,
                actor.role.value,
            )
            for actor in packet.actors
        ],
        packet.partner_actor_names,
    )

    assert expected_key in keys(
        packet.partner_actor_names
    )


# ============================================================
# D3-B ? LABEL-FIRST MULTIPLE
# ============================================================

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
                "Les partenaires operationnels sont "
                "le prestataire local et "
                "le centre de service."
            ),
            (
                "prestataire local",
                "centre de service",
            ),
        ),
        (
            "en",
            (
                "The operational partners are "
                "the local service provider and "
                "the service center."
            ),
            (
                "local service provider",
                "service center",
            ),
        ),
    ),
)
def test_explicit_multiple_partner_relations_are_atomic(
    language: str,
    description: str,
    expected: tuple[str, ...],
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    actual = keys(
        role_names(
            packet,
            ActorRole.PARTNER,
        )
    )

    required = {
        comparison_key(
            value
        )
        for value in expected
    }

    assert required.issubset(
        actual
    ), (
        language,
        required,
        actual,
        [
            (
                actor.name,
                actor.role.value,
            )
            for actor in packet.actors
        ],
    )


# ============================================================
# D3-C ? QUALIFIED PARTNER ACTOR
#
# Use a neutral actor head here, not "provider/prestataire".
# This avoids conflating partner relation with provider role.
#
# AutoCare's "garage partenaire" belongs to this grammar class.
# ============================================================

@pytest.mark.parametrize(
    (
        "language",
        "description",
    ),
    (
        (
            "fr",
            (
                "Une demande valide peut etre affectee "
                "a un atelier partenaire."
            ),
        ),
        (
            "en",
            (
                "A valid request can be assigned "
                "to a partner workshop."
            ),
        ),
    ),
)
def test_partner_qualified_actor_materializes_explicit_partner_role(
    language: str,
    description: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    partners = role_names(
        packet,
        ActorRole.PARTNER,
    )

    assert partners, (
        language,
        [
            (
                actor.name,
                actor.role.value,
            )
            for actor in packet.actors
        ],
        packet.partner_actor_names,
        packet.priority_workflows,
    )


# ============================================================
# D3-PROJECTION ? PROVIDER IS INTENTIONALLY INCLUDED IN
# partner_actor_names.
#
# This is NOT an explicit PARTNER relation.
# ============================================================

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
                "Le prestataire local peut recevoir "
                "des notifications."
            ),
            "prestataire local",
        ),
        (
            "en",
            (
                "The local service provider can receive "
                "notifications."
            ),
            "local service provider",
        ),
    ),
)
def test_provider_projection_does_not_become_explicit_partner_role(
    language: str,
    description: str,
    expected: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    expected_key = comparison_key(
        expected
    )

    provider_keys = keys(
        role_names(
            packet,
            ActorRole.PROVIDER,
        )
    )

    partner_keys = keys(
        role_names(
            packet,
            ActorRole.PARTNER,
        )
    )

    projected_keys = keys(
        packet.partner_actor_names
    )

    assert expected_key in provider_keys

    assert expected_key not in partner_keys

    # Existing schema contract:
    # partner_actor_names aggregates PARTNER + PROVIDER.
    assert expected_key in projected_keys


# ============================================================
# D3 NEGATIVE ? NO PARTNER/PROVIDER SEMANTICS
# ============================================================

@pytest.mark.parametrize(
    (
        "language",
        "description",
    ),
    (
        (
            "fr",
            (
                "Le coordinateur externe peut recevoir "
                "des notifications."
            ),
        ),
        (
            "en",
            (
                "The external coordinator can receive "
                "notifications."
            ),
        ),
    ),
)
def test_unrelated_external_actor_does_not_invent_partner_projection(
    language: str,
    description: str,
) -> None:

    packet = extract(
        description=description,
        language=language,
    )

    assert role_names(
        packet,
        ActorRole.PARTNER,
    ) == []

    assert role_names(
        packet,
        ActorRole.PROVIDER,
    ) == []

    assert packet.partner_actor_names == []



# D3 label-head noun-modifier boundary regression.
#
# Lexical presence of partner/partenaire is not sufficient
# to establish ActorRole.PARTNER.
#
# These are product/object noun phrases, not declarations
# of a partner actor relation.
def test_partner_term_used_as_noun_modifier_does_not_create_partner_role():
    from app.schemas.analysis_context import ActorRole
    from app.services.project_context_extractor import (
        ProjectContextExtractor,
    )

    extractor = ProjectContextExtractor()

    cases = (
        (
            "Le portail partenaire est une "
            "fonctionnalite optionnelle."
        ),
        (
            "Le programme partenaire est un "
            "module facultatif."
        ),
        (
            "Le module partenaire est "
            "optionnel."
        ),
        (
            "L'interface partenaire est une "
            "fonctionnalite secondaire."
        ),
        (
            "The partner portal is an optional "
            "product feature."
        ),
        (
            "The partner program is an optional "
            "module."
        ),
    )

    for description in cases:
        declared = extractor._declared_actor_roles(
            description
        )

        explicit_partners = [
            name
            for name, role in declared
            if role == ActorRole.PARTNER
        ]

        assert explicit_partners == [], (
            description,
            explicit_partners,
            declared,
        )
