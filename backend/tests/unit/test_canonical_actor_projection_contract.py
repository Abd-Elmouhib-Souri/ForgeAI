from __future__ import annotations

import pytest

from app.agents.bmc_agent import BMCAgent
from app.agents.debate_room_graph import DebateRoomGraph
from app.agents.persona_builder_agent import PersonaBuilderAgent
from app.services.canonical_actor_projection import (
    project_actor_roles,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    [
        (
            "fr",
            (
                "L'organisation cliente paie "
                "des frais de service."
            ),
            "organisation cliente",
        ),
        (
            "en",
            (
                "The client organization pays "
                "a service fee."
            ),
            "client organization",
        ),
    ],
)
def test_canonical_explicit_payer_projects_as_explicit(
    language: str,
    description: str,
    expected: str,
) -> None:
    packet = project_context_extractor.extract(
        title="ActorProjection",
        description=description,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    canonical = packet.model_dump(
        mode="json"
    )

    projection = project_actor_roles(
        canonical=canonical,
    )

    payer = projection[
        "payer"
    ]

    assert payer["value"] == expected
    assert payer["candidate"] == expected
    assert payer["status"] == "explicit"
    assert payer["source"] == "canonical_actor_context"


def test_non_explicit_canonical_actor_is_never_promoted() -> None:
    projection = project_actor_roles(
        canonical={
            "schema_version": "project_context_v3",
            "actors": [
                {
                    "name": "candidate organization",
                    "role": "payer",
                    "is_explicit": False,
                }
            ],
            "payer_actor_names": [
                "candidate organization"
            ],
        },
    )

    payer = projection[
        "payer"
    ]

    assert payer["value"] == ""
    assert payer["candidate"] == "candidate organization"
    assert payer["status"] == "to_confirm"


@pytest.mark.parametrize(
    "status",
    [
        "explicit",
        "user_provided",
        "provided_by_user",
        "validated",
        "confirmed",
    ],
)
def test_legacy_confirmed_status_remains_compatible(
    status: str,
) -> None:
    projection = project_actor_roles(
        structured={
            "actors": {
                "payer": "budget owner",
            },
            "actor_provenance": {
                "payer": status,
            },
        },
        actors={
            "payer": "budget owner",
        },
        provenance={
            "payer": status,
        },
    )

    payer = projection[
        "payer"
    ]

    assert payer["value"] == "budget owner"
    assert payer["status"] == "explicit"


def test_legacy_payer_without_provenance_stays_unconfirmed() -> None:
    projection = project_actor_roles(
        structured={
            "actors": {
                "payer": "candidate payer",
            },
        },
        actors={
            "payer": "candidate payer",
        },
    )

    payer = projection[
        "payer"
    ]

    assert payer["value"] == ""
    assert payer["candidate"] == "candidate payer"
    assert payer["status"] == "to_confirm"


def test_payer_name_list_alone_never_creates_explicit_provenance() -> None:
    projection = project_actor_roles(
        canonical={
            "schema_version": "project_context_v3",
            "actors": [],
            "payer_actor_names": [
                "named organization"
            ],
        },
    )

    payer = projection[
        "payer"
    ]

    assert payer["value"] == ""
    assert payer["candidate"] == "named organization"
    assert payer["status"] == "to_confirm"


def _canonical_packet() -> dict:
    packet = project_context_extractor.extract(
        title="CanonicalHandoff",
        description=(
            "The primary users are operators. "
            "The client company pays a monthly subscription."
        ),
        industry="software",
        target_region="Europe",
        output_language="en",
    )

    return packet.model_dump(
        mode="json"
    )


def test_bmc_consumes_explicit_canonical_payer() -> None:
    canonical = _canonical_packet()

    context = BMCAgent()._context(
        {
            "title": "CanonicalHandoff",
            "industry": "software",
            "region": "Europe",
            "output_language": "en",
            "project_context_packet": canonical,
        }
    )

    payer = context[
        "role_assignments"
    ][
        "payer"
    ]

    assert payer["value"] == "client company"
    assert payer["status"] == "explicit"
    assert context["economic_buyer"] == "client company"


def test_debate_consumes_explicit_canonical_payer() -> None:
    canonical = _canonical_packet()

    context = DebateRoomGraph()._context(
        title="CanonicalHandoff",
        description=(
            "The client company pays "
            "a monthly subscription."
        ),
        industry="software",
        region="Europe",
        project_context=canonical,
        analysis={},
    )

    assert (
        context["economic_buyer_value"]
        == "client company"
    )

    assert (
        context["economic_buyer_status"]
        == "explicit"
    )


def test_persona_consumes_nested_explicit_canonical_payer() -> None:
    canonical = _canonical_packet()

    context = PersonaBuilderAgent()._context(
        {
            "title": "CanonicalHandoff",
            "industry": "software",
            "region": "Europe",
            "output_language": "en",
            "agent_context_packet": {
                "canonical_schema_version": (
                    "agent_context_packet_v3"
                ),
                "project_context_packet": canonical,
                "context_locked": True,
            },
        }
    )

    assert (
        context["economic_buyer"]
        == "client company"
    )

    assert (
        context["explicit_economic_buyer"]
        == "client company"
    )

    assert (
        context["actors"]["payer"]
        == "client company"
    )

    assert "operators" in [
        value.lower()
        for value in context[
            "target_users"
        ]
    ]


def test_canonical_explicit_role_overrides_legacy_hypothesis() -> None:
    projection = project_actor_roles(
        canonical={
            "schema_version": "project_context_v3",
            "actors": [
                {
                    "name": "canonical payer",
                    "role": "payer",
                    "is_explicit": True,
                }
            ],
            "payer_actor_names": [
                "canonical payer"
            ],
        },
        structured={
            "actors": {
                "payer": "legacy hypothesis",
            },
        },
        actors={
            "payer": "legacy hypothesis",
        },
    )

    payer = projection[
        "payer"
    ]

    assert payer["value"] == "canonical payer"
    assert payer["status"] == "explicit"
