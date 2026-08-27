from __future__ import annotations

import re

import pytest

from app.schemas.analysis_context import (
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def extract(
    description: str,
    *,
    language: str = "en",
):
    return project_context_extractor.extract(
        title="Universal Planning Scope Contract",
        description=description,
        industry="General project domain",
        target_region="International",
        output_language=language,
    )


def normalized_values(
    values,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            comparison_key(value)
            for value in values
            if comparison_key(value)
        )
    )


def packet_workflow_text(
    packet,
) -> str:
    return comparison_key(
        " | ".join(
            (
                getattr(workflow, "sentence", "")
                or getattr(workflow, "name", "")
            )
            for workflow in packet.priority_workflows
        )
    )


@pytest.mark.parametrize(
    (
        "description",
        "expected_terms",
    ),
    (
        # ----------------------------------------------------
        # B2B workflow software
        # ----------------------------------------------------
        (
            (
                "The product helps operations staff review "
                "incoming service requests. "
                "The MVP supports request intake and approval. "
                "The first version explicitly excludes "
                "automatic payment execution."
            ),
            (
                "payment",
                "execution",
            ),
        ),

        # ----------------------------------------------------
        # Genuine two-sided marketplace context.
        #
        # Important: marketplace itself is positive here;
        # an unrelated capability is excluded.
        # ----------------------------------------------------
        (
            (
                "The platform connects independent tutors "
                "with learners who book sessions. "
                "Tutors publish availability and learners "
                "request appointments. "
                "The first release does not include "
                "automatic loan financing."
            ),
            (
                "loan",
                "financing",
            ),
        ),

        # ----------------------------------------------------
        # Hardware / robotics
        # ----------------------------------------------------
        (
            (
                "The system is a mobile inspection robot. "
                "Operators review inspection results. "
                "The prototype does not include "
                "autonomous mechanical repair."
            ),
            (
                "autonomous",
                "repair",
            ),
        ),

        # ----------------------------------------------------
        # Regulated / controlled workflow
        # ----------------------------------------------------
        (
            (
                "The service helps professionals review "
                "submitted cases and prepare recommendations. "
                "A qualified professional makes the final decision. "
                "The MVP explicitly excludes autonomous issuance "
                "of legally binding decisions."
            ),
            (
                "autonomous",
                "decisions",
            ),
        ),
    ),
)
def test_cross_domain_explicit_exclusion_is_preserved(
    description: str,
    expected_terms: tuple[str, ...],
) -> None:

    packet = extract(
        description
    )

    exclusion_text = comparison_key(
        " ".join(
            packet.scope_exclusions
        )
    )

    for term in expected_terms:
        assert (
            comparison_key(term)
            in exclusion_text
        ), (
            term,
            packet.scope_exclusions,
        )


def test_reordering_sentences_does_not_change_scope_exclusion_authority() -> None:

    exclusion = (
        "The first version explicitly excludes "
        "automatic invoice settlement."
    )

    first = extract(
        (
            "The product supports request review. "
            "Operators approve valid requests. "
            f"{exclusion}"
        )
    )

    second = extract(
        (
            f"{exclusion} "
            "Operators approve valid requests. "
            "The product supports request review."
        )
    )

    assert (
        normalized_values(
            first.scope_exclusions
        )
        ==
        normalized_values(
            second.scope_exclusions
        )
    )


def test_irrelevant_text_does_not_mutate_scope_exclusions() -> None:

    base = (
        "The product supports request review. "
        "The first version explicitly excludes "
        "automatic invoice settlement."
    )

    noisy = (
        base
        + " The project team meets every Tuesday "
        "to review delivery progress."
    )

    base_packet = extract(
        base
    )

    noisy_packet = extract(
        noisy
    )

    assert (
        normalized_values(
            base_packet.scope_exclusions
        )
        ==
        normalized_values(
            noisy_packet.scope_exclusions
        )
    )


def test_duplicate_exclusion_is_canonically_deduplicated() -> None:

    exclusion = (
        "The first version explicitly excludes "
        "automatic invoice settlement."
    )

    packet = extract(
        f"{exclusion} {exclusion}"
    )

    normalized = normalized_values(
        packet.scope_exclusions
    )

    assert len(normalized) == len(
        set(normalized)
    )

    assert len(normalized) == 1, (
        packet.scope_exclusions
    )


def test_positive_scope_is_not_published_as_exclusion() -> None:

    packet = extract(
        (
            "The product supports request review. "
            "The first version explicitly includes "
            "automatic invoice settlement."
        )
    )

    exclusion_text = comparison_key(
        " ".join(
            packet.scope_exclusions
        )
    )

    assert (
        "automatic invoice settlement"
        not in exclusion_text
    ), packet.scope_exclusions


def test_negative_scope_does_not_become_positive_workflow() -> None:

    packet = extract(
        (
            "The product supports operational request review. "
            "The first version explicitly excludes "
            "automatic payment execution."
        )
    )

    workflow_text = packet_workflow_text(
        packet
    )

    assert (
        "automatic payment execution"
        not in workflow_text
    ), packet.model_dump(
        mode="json"
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected_term",
    ),
    (
        (
            "en",
            (
                "The first release is delivered without "
                "automatic payment functionality."
            ),
            "payment",
        ),
        (
            "fr",
            (
                "La premiere version est livree sans "
                "execution automatique des paiements."
            ),
            "paiement",
        ),
    ),
)
def test_existing_without_sans_scope_grammar_reaches_canonical_packet(
    language: str,
    description: str,
    expected_term: str,
) -> None:

    packet = extract(
        description,
        language=language,
    )

    exclusion_text = comparison_key(
        " ".join(
            packet.scope_exclusions
        )
    )

    assert (
        comparison_key(expected_term)
        in exclusion_text
    ), packet.scope_exclusions


def test_plain_operational_without_is_not_scope_exclusion() -> None:

    packet = extract(
        (
            "The application works without "
            "an internet connection."
        )
    )

    exclusion_text = comparison_key(
        " ".join(
            packet.scope_exclusions
        )
    )

    assert (
        "internet connection"
        not in exclusion_text
    ), packet.scope_exclusions
