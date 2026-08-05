from __future__ import annotations

import json

from app.services.project_archetype_resolver import (
    ProjectArchetypeResolver,
)


def test_resolver_does_not_invent_actors_or_workflows() -> None:
    resolver = ProjectArchetypeResolver()

    result = resolver.resolve(
        title="Neutral Exchange",
        description=(
            "A two-sided marketplace connects buyers and sellers "
            "for a transaction."
        ),
        industry="B2B marketplace",
        target_region="Tunisia",
        output_language="en",
    )

    assert (
        result["project_archetype"]
        == "two_sided_marketplace"
    )
    assert result["target_users"] == []
    assert result["priority_workflows"] == []
    assert result["core_action"] == ""

    actors = result["actors"]

    assert actors["demand_side"] == ""
    assert actors["supply_side"] == ""
    assert actors["operator_or_partner"] == ""
    assert actors["payer"] == ""
    assert actors["explicit_targets"] == []


def test_resolver_preserves_only_explicit_context() -> None:
    resolver = ProjectArchetypeResolver()

    result = resolver.resolve(
        title="OpsFlow",
        description=(
            "A SaaS workflow product for field teams."
        ),
        industry="B2B workflow SaaS",
        target_region="France",
        output_language="en",
        target_users=[
            "Field coordinators",
            "Operations managers",
        ],
        workflows=[
            "record a completed field inspection",
            "review the inspection result",
        ],
        business_model=(
            "Monthly subscription per organization"
        ),
    )

    assert result["target_users"] == [
        "Field coordinators",
        "Operations managers",
    ]
    assert result["priority_workflows"] == [
        "record a completed field inspection",
        "review the inspection result",
    ]
    assert (
        result["core_action"]
        == "record a completed field inspection"
    )
    assert (
        result["business_model_hypothesis"]
        == "Monthly subscription per organization"
    )


def test_resolver_has_no_readiness_authority() -> None:
    resolver = ProjectArchetypeResolver()

    result = resolver.resolve(
        title="Sensor Review",
        description=(
            "An IoT sensor sends measurements to an AI "
            "analysis dashboard."
        ),
        industry="IoT and AI",
        output_language="en",
    )

    serialized = json.dumps(
        result,
        ensure_ascii=False,
    )

    assert "ready_for_agents" not in serialized
    assert (
        result["authority"][
            "decides_readiness"
        ]
        is False
    )
    assert (
        result["authority"][
            "resolves_actor_roles"
        ]
        is False
    )
    assert (
        result["authority"][
            "invents_workflows"
        ]
        is False
    )


def test_resolver_exposes_secondary_archetypes() -> None:
    resolver = ProjectArchetypeResolver()

    result = resolver.resolve(
        title="Vision Device",
        description=(
            "A connected IoT camera uses computer vision "
            "and machine learning to detect anomalies."
        ),
        industry="Industrial IoT and AI",
        output_language="en",
    )

    assert result["project_archetype"] == "hardware_iot"
    assert (
        "analytics_ai_tool"
        in result["secondary_archetypes"]
    )
    assert result["archetype_scores"]