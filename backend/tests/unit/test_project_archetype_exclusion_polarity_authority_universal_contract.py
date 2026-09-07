from __future__ import annotations

from typing import Any

from app.services.project_archetype_resolver import (
    project_archetype_resolver,
)


IDENTITY_FIELDS = (
    "project_archetype",
    "primary_archetype",
    "vertical",
    "business_motion",
    "interaction_model",
)


def _normalize(
    value: Any,
) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .casefold()
        .split()
    )


def _resolve(
    *,
    description: str,
    industry: str,
    title: str = "Neutral Semantic Boundary",
):
    return (
        project_archetype_resolver
        .resolve(
            title=title,
            description=description,
            industry=industry,
            target_region="Global",
            output_language="en",
            target_users=[
                "operations managers",
                "field operators",
            ],
            problem=(
                "Recurring operational work is coordinated manually."
            ),
            solution=(
                "Centralize operational requests, assignments, "
                "records and completion tracking."
            ),
            business_model=(
                "B2B subscription"
            ),
            workflows=[],
        )
    )


def _identity(
    result,
):
    return {
        field:
            result.get(field)
        for field
        in IDENTITY_FIELDS
    }


def _search_blob(
    result,
) -> str:
    return _normalize(
        " ".join(
            str(value)
            for value
            in (
                result.get(
                    "search_terms"
                )
                or []
            )
        )
    )


def test_explicit_exclusions_cannot_change_archetype_identity() -> None:
    """
    Metamorphic authority invariant.

    Adding capabilities ONLY as explicit exclusions must not change
    the project's structural archetype identity.
    """

    base_description = (
        "A B2B operations platform used by service companies. "
        "Operations managers create service requests, assign field "
        "operators, maintain asset records and track completed work."
    )

    exclusion_only_variant = (
        base_description
        + "\n\n"
        + "The MVP does NOT include:\n"
        + "- employee shift scheduling\n"
        + "- attendance tracking\n"
        + "- payroll processing\n"
        + "- real-time IoT device monitoring\n"
        + "- autonomous hardware control\n"
        + "- buyer-seller marketplace matching\n"
        + "- transaction payment processing\n"
    )

    base = _resolve(
        description=base_description,
        industry=(
            "B2B Field Operations Software"
        ),
    )

    variant = _resolve(
        description=exclusion_only_variant,
        industry=(
            "B2B Field Operations Software"
        ),
    )

    assert (
        _identity(variant)
        ==
        _identity(base)
    ), {
        "base":
            _identity(base),
        "variant":
            _identity(variant),
    }


def test_explicit_exclusions_cannot_become_positive_search_identity() -> None:
    """
    Explicitly excluded capabilities may not be promoted into
    archetype-generated search identity.
    """

    result = _resolve(
        description=(
            "A B2B operations platform used by service companies. "
            "Operations managers create service requests, assign field "
            "operators, maintain asset records and track completed work."
            "\n\n"
            "The MVP does NOT include:\n"
            "- employee shift scheduling\n"
            "- attendance tracking\n"
            "- payroll processing\n"
            "- real-time IoT device monitoring\n"
            "- autonomous hardware control\n"
            "- buyer-seller marketplace matching\n"
            "- transaction payment processing\n"
        ),
        industry=(
            "B2B Field Operations Software"
        ),
    )

    search_blob = _search_blob(
        result
    )

    forbidden_positive_identity_terms = (
        "workforce scheduling",
        "employee scheduling",
        "shift planning",
        "attendance tracking",
        "payroll",
        "iot monitoring",
        "device monitoring",
        "marketplace matching",
    )

    leaked = [
        term
        for term
        in forbidden_positive_identity_terms
        if term
        in search_blob
    ]

    assert leaked == [], {
        "leaked":
            leaked,
        "search_terms":
            result.get(
                "search_terms"
            ),
    }


def test_true_workforce_semantics_remain_detectable() -> None:
    """
    Preservation control.

    Fixing negative-polarity contamination must not suppress a genuine
    workforce product.
    """

    result = (
        project_archetype_resolver
        .resolve(
            title="Neutral Workforce Control",
            description=(
                "A B2B workforce management application. "
                "Managers create employee shifts, track attendance, "
                "approve leave requests and review worked hours. "
                "Employees receive schedules and acknowledge shifts."
            ),
            industry=(
                "Workforce Management Software"
            ),
            target_region="Global",
            output_language="en",
            target_users=[
                "workforce managers",
                "employees",
            ],
            problem=(
                "Employee scheduling and attendance are coordinated manually."
            ),
            solution=(
                "Manage employee shifts, attendance, leave and worked hours."
            ),
            business_model=(
                "B2B subscription"
            ),
            workflows=[],
        )
    )

    assert (
        result.get(
            "vertical"
        )
        ==
        "workforce"
    ), result


def test_true_hardware_iot_semantics_remain_detectable() -> None:
    """
    Preservation control.

    Genuine device-operation semantics must remain distinguishable from
    hardware or IoT terms that appear only inside exclusions.
    """

    result = (
        project_archetype_resolver
        .resolve(
            title="Neutral Device Control",
            description=(
                "A connected industrial monitoring system uses physical "
                "sensors installed on equipment to collect telemetry. "
                "A gateway transmits device measurements and operators "
                "monitor device health and maintenance status."
            ),
            industry=(
                "Industrial IoT Monitoring"
            ),
            target_region="Global",
            output_language="en",
            target_users=[
                "maintenance operators",
            ],
            problem=(
                "Equipment telemetry is not centrally observable."
            ),
            solution=(
                "Collect sensor telemetry from deployed physical devices."
            ),
            business_model=(
                "B2B subscription"
            ),
            workflows=[],
        )
    )

    assert (
        result.get(
            "project_archetype"
        )
        ==
        "hardware_iot"
        or result.get(
            "primary_archetype"
        )
        ==
        "hardware_iot"
    ), result


def test_true_marketplace_semantics_remain_detectable() -> None:
    """
    Preservation control.

    Genuine two-sided exchange semantics must remain recognizable.
    """

    result = (
        project_archetype_resolver
        .resolve(
            title="Neutral Marketplace Control",
            description=(
                "A digital marketplace connects independent providers "
                "with customers requesting services. Providers publish "
                "offers, customers choose a provider, the platform "
                "supports transaction payment and earns a commission "
                "on completed exchanges."
            ),
            industry=(
                "Online Services Marketplace"
            ),
            target_region="Global",
            output_language="en",
            target_users=[
                "customers",
                "independent providers",
            ],
            problem=(
                "Customers and independent providers struggle to find "
                "and transact with each other."
            ),
            solution=(
                "Match customer demand with independent provider supply."
            ),
            business_model=(
                "Transaction commission"
            ),
            workflows=[],
        )
    )

    assert (
        result.get(
            "project_archetype"
        )
        ==
        "two_sided_marketplace"
        or result.get(
            "primary_archetype"
        )
        ==
        "two_sided_marketplace"
    ), result