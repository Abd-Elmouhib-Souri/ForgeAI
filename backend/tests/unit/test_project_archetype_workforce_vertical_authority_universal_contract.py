from __future__ import annotations

from app.services.project_archetype_resolver import (
    project_archetype_resolver,
)


WORKFORCE_SEARCH_IDENTITY = (
    "workforce scheduling",
    "employee scheduling",
    "shift planning",
    "attendance tracking",
    "gestion planning personnel",
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
    language: str = "en",
):
    return (
        project_archetype_resolver
        .resolve(
            title=title,
            description=description,
            industry=industry,
            target_region="Global",
            output_language=language,
            target_users=target_users,
            problem=problem,
            solution=solution,
            business_model="B2B subscription",
            workflows=workflows,
        )
    )


def _assert_not_workforce(
    result,
) -> None:
    assert (
        result.get(
            "vertical"
        )
        !=
        "workforce"
    ), result


def _assert_no_workforce_search_identity(
    result,
) -> None:
    blob = " ".join(
        result.get(
            "search_terms"
        )
        or []
    ).casefold()

    leaked = [
        term
        for term in WORKFORCE_SEARCH_IDENTITY
        if term
        in blob
    ]

    assert leaked == [], {
        "vertical":
            result.get(
                "vertical"
            ),
        "leaked":
            leaked,
        "search_terms":
            result.get(
                "search_terms"
            ),
    }


def test_generic_operational_schedule_cannot_establish_workforce_vertical() -> None:
    """
    'Schedule' is a generic operational verb.

    Scheduling an asset, intervention, appointment, delivery, inspection,
    job or other domain object does not by itself establish workforce
    management semantics.
    """

    result = _resolve(
        title=(
            "Neutral Service Operations"
        ),
        description=(
            "A B2B operations application manages service requests, "
            "equipment inspections and completed interventions."
        ),
        industry=(
            "Operations Management Software"
        ),
        problem=(
            "Operational interventions are coordinated manually."
        ),
        solution=(
            "Centralize requests, equipment records and intervention history."
        ),
        target_users=[
            "operations managers",
            "service operators",
        ],
        workflows=[
            "create service request",
            "schedule equipment inspection",
            "record completed intervention",
        ],
    )

    _assert_not_workforce(
        result
    )

    _assert_no_workforce_search_identity(
        result
    )


def test_generic_operational_planning_cannot_establish_workforce_vertical() -> None:
    """
    'Planning' is also a generic operational concept.

    Capacity, asset, maintenance, route, production or service planning
    is not equivalent to employee/workforce management.
    """

    result = _resolve(
        title=(
            "Neutral Asset Operations"
        ),
        description=(
            "A B2B platform supports equipment maintenance planning, "
            "asset history and inspection records."
        ),
        industry=(
            "Asset Operations Software"
        ),
        problem=(
            "Equipment interventions and maintenance planning are fragmented."
        ),
        solution=(
            "Centralize asset records, inspection history "
            "and maintenance planning."
        ),
        target_users=[
            "operations managers",
            "maintenance coordinators",
        ],
        workflows=[
            "review equipment record",
            "plan maintenance intervention",
            "record inspection result",
        ],
    )

    _assert_not_workforce(
        result
    )

    _assert_no_workforce_search_identity(
        result
    )


def test_adding_generic_schedule_cannot_flip_existing_non_workforce_identity() -> None:
    """
    Metamorphic invariant.

    Adding an operational scheduling step must not convert an otherwise
    unchanged non-workforce project into workforce management.
    """

    base = _resolve(
        title=(
            "Neutral Operations Platform"
        ),
        description=(
            "A B2B operations platform manages requests, "
            "equipment records and completed work."
        ),
        industry=(
            "Operations Management Software"
        ),
        problem=(
            "Operational work is coordinated manually."
        ),
        solution=(
            "Centralize requests, equipment records and completed work."
        ),
        target_users=[
            "operations managers",
            "service operators",
        ],
        workflows=[
            "create request",
            "record completed work",
        ],
    )

    scheduled = _resolve(
        title=(
            "Neutral Operations Platform"
        ),
        description=(
            "A B2B operations platform manages requests, "
            "equipment records and completed work."
        ),
        industry=(
            "Operations Management Software"
        ),
        problem=(
            "Operational work is coordinated manually."
        ),
        solution=(
            "Centralize requests, equipment records and completed work."
        ),
        target_users=[
            "operations managers",
            "service operators",
        ],
        workflows=[
            "create request",
            "schedule equipment inspection",
            "record completed work",
        ],
    )

    assert (
        base.get(
            "vertical"
        )
        !=
        "workforce"
    ), base

    assert (
        scheduled.get(
            "vertical"
        )
        ==
        base.get(
            "vertical"
        )
    ), {
        "base":
            base.get(
                "vertical"
            ),
        "scheduled":
            scheduled.get(
                "vertical"
            ),
        "scheduled_search_terms":
            scheduled.get(
                "search_terms"
            ),
    }


def test_french_generic_planning_cannot_establish_workforce_vertical() -> None:
    """
    The invariant is multilingual.

    'Planning des interventions' is operational planning unless positive
    workforce semantics actually establish employee/team management.
    """

    result = _resolve(
        title=(
            "Opérations techniques"
        ),
        description=(
            "Une plateforme B2B centralise le planning des interventions "
            "techniques, les équipements et l'historique des opérations."
        ),
        industry=(
            "Logiciel de gestion des opérations"
        ),
        problem=(
            "Le planning des interventions techniques est géré manuellement."
        ),
        solution=(
            "Centraliser les interventions, les équipements "
            "et le planning opérationnel."
        ),
        target_users=[
            "responsables des opérations",
            "techniciens terrain",
        ],
        workflows=[
            "créer une intervention",
            "planifier une inspection",
            "enregistrer le résultat",
        ],
        language="fr",
    )

    _assert_not_workforce(
        result
    )

    _assert_no_workforce_search_identity(
        result
    )


def test_explicit_employee_schedule_semantics_remain_workforce() -> None:
    """
    Recall preservation.

    Removing generic ambiguity must not remove genuine employee-scheduling
    detection.
    """

    result = _resolve(
        title=(
            "Neutral Team Scheduling"
        ),
        description=(
            "A company application manages the employee schedule "
            "for operational teams."
        ),
        industry=(
            "Team Workforce Software"
        ),
        problem=(
            "Managers prepare the employee schedule manually."
        ),
        solution=(
            "Create and publish the employee schedule."
        ),
        target_users=[
            "team managers",
            "employees",
        ],
        workflows=[
            "create employee schedule",
            "publish employee schedule",
        ],
    )

    assert (
        result.get(
            "vertical"
        )
        ==
        "workforce"
    ), result


def test_explicit_workforce_management_remains_detectable() -> None:
    """
    Strong positive workforce semantics remain authoritative.
    """

    result = _resolve(
        title=(
            "Neutral Workforce Management"
        ),
        description=(
            "A workforce management platform lets managers "
            "create employee shifts, record attendance, "
            "manage leave requests and review worked hours."
        ),
        industry=(
            "Workforce Management Software"
        ),
        problem=(
            "Employee scheduling and attendance are coordinated manually."
        ),
        solution=(
            "Manage shifts, attendance, leave requests and worked hours."
        ),
        target_users=[
            "workforce managers",
            "employees",
        ],
        workflows=[
            "create employee shift",
            "record attendance",
            "manage leave request",
        ],
    )

    assert (
        result.get(
            "vertical"
        )
        ==
        "workforce"
    ), result


def test_french_explicit_personnel_planning_remains_workforce() -> None:
    """
    French positive workforce semantics remain detectable without relying
    on generic 'planning' alone.
    """

    result = _resolve(
        title=(
            "Gestion des équipes"
        ),
        description=(
            "Une application gère le planning du personnel "
            "et les horaires des employés."
        ),
        industry=(
            "Gestion du personnel"
        ),
        problem=(
            "Le planning du personnel est préparé manuellement."
        ),
        solution=(
            "Créer et publier le planning du personnel."
        ),
        target_users=[
            "responsables RH",
            "employés",
        ],
        workflows=[
            "créer le planning du personnel",
            "publier les horaires des employés",
        ],
        language="fr",
    )

    assert (
        result.get(
            "vertical"
        )
        ==
        "workforce"
    ), result