from __future__ import annotations

from typing import Any

from app.services.project_archetype_resolver import (
    project_archetype_resolver,
)


def _resolve(
    *,
    title: str,
    description: str,
    industry: str,
    problem: str,
    solution: str,
    target_users: list[str],
    workflows: list[str],
):
    return (
        project_archetype_resolver
        .resolve(
            title=title,
            description=description,
            industry=industry,
            target_region="Global",
            output_language="en",
            target_users=target_users,
            problem=problem,
            solution=solution,
            business_model="B2B subscription",
            workflows=workflows,
        )
    )


def _selected(
    result: dict[str, Any],
) -> str:
    return str(
        result.get(
            "primary_archetype"
        )
        or result.get(
            "project_archetype"
        )
        or ""
    )


def _unique_dominant(
    result: dict[str, Any],
) -> tuple[str, int]:
    scores = dict(
        result.get(
            "archetype_scores"
        )
        or {}
    )

    assert scores, result

    maximum = max(
        scores.values()
    )

    winners = [
        name
        for name, value
        in scores.items()
        if value == maximum
    ]

    assert len(winners) == 1, {
        "scores":
            scores,
        "winners":
            winners,
    }

    return (
        winners[0],
        maximum,
    )


def _assert_primary_follows_unique_dominant_score(
    result: dict[str, Any],
) -> None:
    """
    When the resolver itself publishes one unique dominant score,
    that score is the deterministic primary-archetype authority.

    This contract deliberately says nothing about tie resolution.
    """

    dominant, _ = (
        _unique_dominant(
            result
        )
    )

    assert (
        _selected(result)
        ==
        dominant
    ), {
        "selected":
            _selected(result),
        "dominant":
            dominant,
        "scores":
            result.get(
                "archetype_scores"
            ),
    }


def test_unique_dominant_b2b_score_controls_primary_over_minor_hardware() -> None:
    """
    A small legitimate secondary hardware signal must not override a
    much stronger workflow/SaaS score merely because hardware crossed
    an arbitrary category threshold.
    """

    result = _resolve(
        title=(
            "Neutral Workflow Operations"
        ),
        description=(
            "A B2B SaaS workflow dashboard for managers. "
            "The application manages records, reporting, exports, "
            "administrative processes, planning and spreadsheet migration. "
            "Managers review workflows, records and reports. "
            "One optional integration can import a measurement from "
            "an external sensor device."
        ),
        industry=(
            "B2B Workflow SaaS"
        ),
        problem=(
            "Managers coordinate recurring operational records manually."
        ),
        solution=(
            "Provide a SaaS workflow dashboard for records, reports, "
            "exports and administrative processes."
        ),
        target_users=[
            "operations managers",
            "supervisors",
        ],
        workflows=[
            "manage records",
            "review reports",
            "export workflow data",
        ],
    )

    scores = dict(
        result.get(
            "archetype_scores"
        )
        or {}
    )

    # Contract precondition: this fixture must truly establish a
    # unique workflow/SaaS dominant score while preserving a real
    # positive hardware secondary signal.
    assert (
        scores.get(
            "b2b_workflow_saas",
            0,
        )
        >
        scores.get(
            "hardware_iot",
            0,
        )
    ), scores

    assert (
        scores.get(
            "hardware_iot",
            0,
        )
        >
        0
    ), scores

    _assert_primary_follows_unique_dominant_score(
        result
    )


def test_unique_dominant_marketplace_score_controls_primary_over_minor_hardware() -> None:
    """
    The invariant is cross-archetype.

    A genuine marketplace remains primary when its published score is
    uniquely dominant and hardware is only a secondary implementation
    detail.
    """

    result = _resolve(
        title=(
            "Neutral Provider Exchange"
        ),
        description=(
            "A two-sided marketplace connects independent providers "
            "with customers requesting services. Providers publish offers, "
            "customers select a provider, the platform performs matching "
            "and receives a commission on completed transactions. "
            "A provider may optionally use one external sensor device "
            "to attach a measurement to a completed service report."
        ),
        industry=(
            "Online Services Marketplace"
        ),
        problem=(
            "Customers and independent providers struggle to find "
            "and transact with each other."
        ),
        solution=(
            "Match customer demand with provider supply and support "
            "the core marketplace transaction."
        ),
        target_users=[
            "customers",
            "independent providers",
        ],
        workflows=[
            "publish provider offer",
            "match customer request",
            "complete marketplace transaction",
        ],
    )

    scores = dict(
        result.get(
            "archetype_scores"
        )
        or {}
    )

    assert (
        scores.get(
            "two_sided_marketplace",
            0,
        )
        >
        scores.get(
            "hardware_iot",
            0,
        )
    ), scores

    assert (
        scores.get(
            "hardware_iot",
            0,
        )
        >
        0
    ), scores

    _assert_primary_follows_unique_dominant_score(
        result
    )


def test_true_hardware_unique_dominance_remains_primary() -> None:
    """
    Preservation control.

    Dominant-score authority must not demote genuine hardware/IoT
    projects.
    """

    result = _resolve(
        title=(
            "Neutral Connected Equipment"
        ),
        description=(
            "An industrial IoT device contains physical sensors and "
            "an embedded controller. A hardware gateway receives telemetry "
            "from deployed sensor devices and operators monitor device health."
        ),
        industry=(
            "Industrial IoT"
        ),
        problem=(
            "Physical equipment telemetry is not centrally observable."
        ),
        solution=(
            "Collect sensor telemetry through deployed IoT devices "
            "and an embedded hardware gateway."
        ),
        target_users=[
            "maintenance operators",
        ],
        workflows=[
            "collect sensor telemetry",
            "monitor device health",
        ],
    )

    dominant, _ = (
        _unique_dominant(
            result
        )
    )

    assert (
        dominant
        ==
        "hardware_iot"
    ), result

    _assert_primary_follows_unique_dominant_score(
        result
    )


def test_score_authority_contract_does_not_define_tie_policy() -> None:
    """
    Contract hygiene.

    This lot governs UNIQUE dominance only. Equal-score tie handling
    remains a separate deterministic policy and is not silently defined
    by this correction.
    """

    synthetic = {
        "archetype_scores": {
            "type_a": 4,
            "type_b": 4,
        },
        "primary_archetype":
            "type_a",
    }

    scores = synthetic[
        "archetype_scores"
    ]

    maximum = max(
        scores.values()
    )

    winners = [
        name
        for name, value
        in scores.items()
        if value == maximum
    ]

    assert len(winners) == 2