from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def extract(
    description: str,
    *,
    language: str = "en",
    industry: str = "",
):
    extractor = ProjectContextExtractor()

    return extractor.extract(
        title="UniversalContract",
        description=description,
        industry=industry,
        target_region="",
        output_language=language,
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
# POSITIVE REFINEMENT
#
# Structural explicit identity must survive a later abbreviated
# operational reference.
# ============================================================


def test_manufacturing_shift_supervisor_refinement_en():
    packet = extract(
        (
            "The primary operational user is the shift supervisor. "
            "The supervisor uses the system to publish schedules."
        ),
        industry="manufacturing",
    )

    assert "shift supervisor" in names(packet), rows(packet)


def test_manufacturing_shift_supervisor_refinement_fr():
    packet = extract(
        (
            "L’utilisateur opérationnel principal est "
            "le superviseur d’équipe. "
            "Le superviseur utilise le système pour publier "
            "les plannings."
        ),
        language="fr",
        industry="industrie",
    )

    assert "superviseur d’équipe" in names(packet), rows(packet)


def test_healthcare_nurse_coordinator_refinement_en():
    packet = extract(
        (
            "The primary operational user is the nurse coordinator. "
            "The coordinator reviews patient workflow alerts."
        ),
        industry="healthcare",
    )

    assert "nurse coordinator" in names(packet), rows(packet)


def test_professional_service_field_coordinator_refinement_en():
    packet = extract(
        (
            "The primary operational user is the field service coordinator. "
            "The coordinator reviews service requests."
        ),
        industry="professional services",
    )

    assert "field service coordinator" in names(packet), rows(packet)


def test_internal_tool_warehouse_supervisor_refinement_en():
    packet = extract(
        (
            "The primary operational user is the warehouse supervisor. "
            "The supervisor reviews inventory anomalies."
        ),
        industry="internal operations",
    )

    assert "warehouse supervisor" in names(packet), rows(packet)


def test_french_maintenance_coordinator_refinement():
    packet = extract(
        (
            "L’utilisateur opérationnel principal est "
            "le coordinateur de maintenance. "
            "Le coordinateur utilise la plateforme pour "
            "examiner les demandes."
        ),
        language="fr",
        industry="maintenance",
    )

    assert "coordinateur de maintenance" in names(packet), rows(packet)


# ============================================================
# NEGATIVE / AMBIGUOUS CONTROLS
#
# Shared lexical head does NOT prove same identity.
# ============================================================


def test_two_distinct_manager_identities_are_not_collapsed():
    packet = extract(
        (
            "The primary users are the product manager "
            "and the customer success manager."
        )
    )

    actor_names = names(packet)

    assert "product manager" in actor_names, rows(packet)
    assert "customer success manager" in actor_names, rows(packet)


def test_two_distinct_supervisor_identities_are_not_collapsed():
    packet = extract(
        (
            "The primary users are the shift supervisor "
            "and the safety supervisor."
        ),
        industry="manufacturing",
    )

    actor_names = names(packet)

    assert "shift supervisor" in actor_names, rows(packet)
    assert "safety supervisor" in actor_names, rows(packet)


def test_two_distinct_coordinator_identities_are_not_collapsed():
    packet = extract(
        (
            "The primary users are the logistics coordinator "
            "and the maintenance coordinator."
        ),
        industry="operations",
    )

    actor_names = names(packet)

    assert "logistics coordinator" in actor_names, rows(packet)
    assert "maintenance coordinator" in actor_names, rows(packet)


def test_french_distinct_manager_identities_are_not_collapsed():
    packet = extract(
        (
            "Les utilisateurs principaux sont "
            "le responsable logistique "
            "et le responsable maintenance."
        ),
        language="fr",
        industry="operations",
    )

    actor_names = names(packet)

    assert "responsable logistique" in actor_names, rows(packet)
    assert "responsable maintenance" in actor_names, rows(packet)


# ============================================================
# ROLE AUTHORITY PRESERVATION
#
# Lexical similarity cannot override a different explicit role.
# ============================================================


def test_similar_names_with_distinct_roles_are_preserved():
    packet = extract(
        (
            "The primary operational user is the operations manager. "
            "The general manager is the primary decision maker "
            "for purchasing."
        ),
        industry="B2B SaaS",
    )

    actor_rows = rows(packet)

    assert any(
        name.lower() == "operations manager"
        and role in {"user", "operator", "beneficiary"}
        for name, role in actor_rows
    ), actor_rows

    assert any(
        name.lower() == "general manager"
        and role == "decision_maker"
        for name, role in actor_rows
    ), actor_rows


# ============================================================
# NO PROJECT / SECTOR AUTHORITY
#
# Same semantic rule must work without meaningful industry hints.
# ============================================================


def test_refinement_does_not_depend_on_sector_or_project_name():
    packet = extract(
        (
            "The primary operational user is the regional coordinator. "
            "The coordinator uses the platform every day."
        ),
        industry="",
    )

    assert "regional coordinator" in names(packet), rows(packet)
