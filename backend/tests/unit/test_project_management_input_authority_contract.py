from __future__ import annotations

import re

import pytest

from app.schemas.analysis_context import (
    ProjectContextPacketV3,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def normalize(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().casefold(),
    )


def joined(values: object) -> str:
    if not isinstance(
        values,
        (list, tuple),
    ):
        return normalize(values)

    return " | ".join(
        normalize(value)
        for value in values
    )


def extract(
    description: str,
    *,
    language: str,
) -> ProjectContextPacketV3:

    return project_context_extractor.extract(
        title="Planning Authority Contract",
        description=description,
        industry="B2B operations software",
        target_region="Europe",
        output_language=language,
    )


def test_packet_schema_has_canonical_scope_exclusions() -> None:
    """
    Sprint 4 needs one canonical authority for explicit
    out-of-scope capabilities.

    Product Owner, Scrum Master and planner must not create
    their own interpretation of negative scope.
    """

    assert (
        "scope_exclusions"
        in ProjectContextPacketV3.model_fields
    ), (
        "ProjectContextPacketV3 has no canonical "
        "scope_exclusions field."
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected_terms",
    ),
    (
        (
            "en",
            (
                "The product helps operations teams process "
                "service requests. "
                "The MVP covers request intake and approval. "
                "The first version explicitly excludes "
                "automatic payment execution."
            ),
            (
                "automatic",
                "payment",
            ),
        ),
        (
            "fr",
            (
                "Le produit aide les équipes opérationnelles "
                "à traiter les demandes de service. "
                "Le MVP couvre la saisie et la validation "
                "des demandes. "
                "La première version exclut explicitement "
                "l'exécution automatique des paiements."
            ),
            (
                "automatique",
                "paiement",
            ),
        ),
    ),
)
def test_explicit_scope_exclusion_reaches_canonical_packet(
    language: str,
    description: str,
    expected_terms: tuple[str, ...],
) -> None:

    packet = extract(
        description,
        language=language,
    )

    exclusions = joined(
        getattr(
            packet,
            "scope_exclusions",
            [],
        )
    )

    for term in expected_terms:

        assert normalize(term) in exclusions, (
            term,
            exclusions,
        )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "forbidden_fragments",
    ),
    (
        (
            "en",
            (
                "The system supports operational request review. "
                "The first version does not execute payments "
                "and does not autonomously approve purchases."
            ),
            (
                "execute payments",
                "autonomously approve purchases",
            ),
        ),
        (
            "fr",
            (
                "Le système aide à examiner les demandes. "
                "La première version n'exécute pas les paiements "
                "et n'approuve pas automatiquement les achats."
            ),
            (
                "exécute pas les paiements",
                "approuve pas automatiquement",
            ),
        ),
    ),
)
def test_negative_scope_cannot_become_positive_planning_workflow(
    language: str,
    description: str,
    forbidden_fragments: tuple[str, ...],
) -> None:

    packet = extract(
        description,
        language=language,
    )

    workflow_text = " | ".join(
        normalize(
            getattr(
                workflow,
                "sentence",
                "",
            )
            or getattr(
                workflow,
                "name",
                "",
            )
        )
        for workflow
        in packet.priority_workflows
    )

    for forbidden in forbidden_fragments:

        assert (
            normalize(forbidden)
            not in workflow_text
        ), (
            forbidden,
            workflow_text,
        )
