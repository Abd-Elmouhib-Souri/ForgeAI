from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
    comparison_key,
)


def extract(
    description: str,
    *,
    language: str,
):
    return ProjectContextExtractor().extract(
        title="NaturalLanguageAuthorityProbe",
        description=description,
        industry="B2B operations",
        target_region="Europe",
        output_language=language,
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def normalized_names(values):
    return {
        comparison_key(value)
        for value in values
    }


# ============================================================
# BLIND-B1 — NATURAL PROBLEM CONSEQUENCE AUTHORITY
# ============================================================

def test_english_natural_negative_consequences_materialize_problem():
    packet = extract(
        (
            "Teams currently coordinate requests through email "
            "and spreadsheets. "
            "This can create conflicting schedules, long waiting times, "
            "poor resource utilization and incomplete handovers."
        ),
        language="en",
    )

    problem = comparison_key(
        packet.problem.pain
    )

    assert problem

    assert any(
        marker in problem
        for marker in (
            "conflicting schedules",
            "long waiting times",
            "poor resource utilization",
            "incomplete handovers",
        )
    )


def test_french_natural_negative_consequences_materialize_problem():
    packet = extract(
        (
            "Les équipes coordonnent actuellement les demandes "
            "par e-mail et tableurs. "
            "Cela peut créer des créneaux conflictuels, "
            "de longs temps d'attente, "
            "une mauvaise utilisation des ressources "
            "et des transmissions incomplètes."
        ),
        language="fr",
    )

    problem = comparison_key(
        packet.problem.pain
    )

    assert problem

    assert any(
        marker in problem
        for marker in (
            "creneaux conflictuels",
            "temps d attente",
            "mauvaise utilisation",
            "transmissions incompletes",
        )
    )


def test_positive_operational_capability_is_not_problem():
    packet = extract(
        (
            "The application coordinates requests and displays "
            "the current operating schedule."
        ),
        language="en",
    )

    assert (
        comparison_key(
            packet.problem.pain
        )
        == ""
    )


# ============================================================
# BLIND-B2 — PASSIVE PURCHASE DECISION AUTHORITY
# ============================================================

def test_english_passive_purchasing_decision_materializes_all_deciders():
    packet = extract(
        (
            "The purchasing decision is made by the finance director, "
            "procurement manager, or operations director. "
            "Operational users use the application daily."
        ),
        language="en",
    )

    decision_makers = normalized_names(
        packet.decision_maker_actor_names
    )

    assert {
        "finance director",
        "procurement manager",
        "operations director",
    }.issubset(
        decision_makers
    )


def test_french_passive_purchase_decision_materializes_all_deciders():
    packet = extract(
        (
            "La décision d'achat est prise par le directeur financier, "
            "la responsable des achats ou le directeur des opérations. "
            "Les utilisateurs opérationnels utilisent "
            "l'application quotidiennement."
        ),
        language="fr",
    )

    decision_makers = normalized_names(
        packet.decision_maker_actor_names
    )

    assert {
        "directeur financier",
        "responsable des achats",
        "directeur des operations",
    }.issubset(
        decision_makers
    )


def test_generic_operational_passive_decision_is_not_buying_authority():
    packet = extract(
        (
            "The scheduling decision is made by "
            "the operations supervisor. "
            "The organization purchases the software separately."
        ),
        language="en",
    )

    decision_makers = normalized_names(
        packet.decision_maker_actor_names
    )

    assert (
        "operations supervisor"
        not in decision_makers
    )


# Blind-B2.1 real-blind extended authority.
#
# These contracts cover two generic authority boundaries discovered
# only by the real blind replay:
#
# 1. Once a purchasing relation has established DECISION_MAKER
#    authority, comma-separated actor identities must not depend on
#    a closed profession vocabulary.
#
# 2. A structured ProblemContext mapping is structured data, never
#    printable problem prose. Its `pain` member owns the semantic value.


def test_passive_purchase_decision_structural_comma_list_keeps_each_actor():
    extractor = ProjectContextExtractor()

    roles = [
        (
            comparison_key(name),
            role.value,
        )
        for name, role
        in extractor._declared_actor_roles(
            (
                "The purchasing decision is made by "
                "alpha lead, beta lead, or gamma lead."
            )
        )
    ]

    decision_names = {
        name
        for name, role
        in roles
        if role == "decision_maker"
    }

    assert decision_names == {
        "alpha lead",
        "beta lead",
        "gamma lead",
    }


def test_french_passive_purchase_structural_comma_list_keeps_each_actor():
    extractor = ProjectContextExtractor()

    roles = [
        (
            comparison_key(name),
            role.value,
        )
        for name, role
        in extractor._declared_actor_roles(
            (
                "La d\u00e9cision d'achat est prise par "
                "alpha responsable, beta responsable, "
                "ou gamma responsable."
            )
        )
    ]

    decision_names = {
        name
        for name, role
        in roles
        if role == "decision_maker"
    }

    assert decision_names == {
        "alpha responsable",
        "beta responsable",
        "gamma responsable",
    }


def test_empty_structured_problem_object_cannot_override_fresh_problem():
    packet = ProjectContextExtractor().extract(
        title="StructuredProblemTypeProbe",
        description=(
            "Teams rely on several manual handoffs. "
            "This creates recurring delays, conflicting updates "
            "and incomplete information."
        ),
        industry="B2B operations",
        target_region="Europe",
        output_language="en",
        project_context={
            "context_locked": True,
            "problem": {
                "actors_affected": [],
                "pain": "",
                "frequency": "",
                "severity": "",
                "current_alternatives": [],
                "consequences": [],
            },
        },
        idea_readiness={},
        analysis_data={},
    )

    pain = comparison_key(
        packet.problem.pain
    )

    assert pain
    assert "recurring delays" in pain

    assert not pain.startswith(
        "{"
    )

    assert "actors_affected" not in pain


def test_populated_structured_problem_object_uses_semantic_pain_value():
    packet = ProjectContextExtractor().extract(
        title="StructuredProblemTypeProbe",
        description=(
            "The service supports a routine business workflow."
        ),
        industry="B2B operations",
        target_region="Europe",
        output_language="en",
        project_context={
            "context_locked": True,
            "problem": {
                "actors_affected": [
                    "operations teams",
                ],
                "pain": (
                    "Manual reconciliation causes "
                    "recurring processing delays."
                ),
                "frequency": "weekly",
                "severity": "medium",
                "current_alternatives": [],
                "consequences": [
                    "late processing",
                ],
            },
        },
        idea_readiness={},
        analysis_data={},
    )

    pain = comparison_key(
        packet.problem.pain
    )

    assert (
        pain
        == (
            "manual reconciliation causes "
            "recurring processing delays"
        )
    )

    assert "actors_affected" not in pain
    assert not pain.startswith("{")


def test_plain_string_structured_problem_remains_supported():
    packet = ProjectContextExtractor().extract(
        title="StructuredProblemTypeProbe",
        description=(
            "The service supports a routine business workflow."
        ),
        industry="B2B operations",
        target_region="Europe",
        output_language="en",
        project_context={
            "context_locked": True,
            "problem": (
                "Manual reconciliation causes "
                "recurring processing delays."
            ),
        },
        idea_readiness={},
        analysis_data={},
    )

    assert (
        comparison_key(
            packet.problem.pain
        )
        == (
            "manual reconciliation causes "
            "recurring processing delays"
        )
    )
