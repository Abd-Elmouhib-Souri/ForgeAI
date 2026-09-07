from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)
from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)
from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Le MVP inclut la gestion des dossiers.",
            False,
        ),
        (
            "The MVP includes case management.",
            False,
        ),
        (
            (
                "Le suivi avanc\u00e9 ne fait pas partie "
                "du premier MVP."
            ),
            True,
        ),
        (
            (
                "Advanced tracking is not part "
                "of the first MVP."
            ),
            True,
        ),
        (
            (
                "Elle n'inclut pas initialement "
                "les rapports avanc\u00e9s."
            ),
            True,
        ),
        (
            (
                "It will not initially include "
                "advanced reports."
            ),
            True,
        ),
        (
            (
                "La fonctionnalit\u00e9 est exclue "
                "du MVP."
            ),
            True,
        ),
        (
            (
                "The feature is excluded "
                "from the MVP."
            ),
            True,
        ),
        (
            (
                "Le module est hors p\u00e9rim\u00e8tre "
                "du MVP."
            ),
            True,
        ),
        (
            (
                "The module is out of scope "
                "for the MVP."
            ),
            True,
        ),
        (
            (
                "Le MVP n'inclut pas seulement "
                "les alertes, il inclut aussi les rapports."
            ),
            False,
        ),
        (
            (
                "The MVP does not only include alerts; "
                "it also includes reports."
            ),
            False,
        ),
    ],
)
def test_scope_exclusion_classifier_is_bilingual_and_polarity_safe(
    text: str,
    expected: bool,
) -> None:
    assert (
        is_scope_exclusion_statement(
            text
        )
        is expected
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "required_terms",
        "excluded_terms",
    ),
    [
        (
            "fr",
            (
                "Le MVP inclut la gestion des dossiers "
                "et les alertes. "
                "Le suivi avanc\u00e9 et l'export automatique "
                "ne font pas partie du premier MVP."
            ),
            (
                "gestion des dossiers",
                "alertes",
            ),
            (
                "suivi avance",
                "export automatique",
            ),
        ),
        (
            "en",
            (
                "The MVP includes case management "
                "and alerts. "
                "Advanced tracking and automatic export "
                "are not part of the first MVP."
            ),
            (
                "case management",
                "alerts",
            ),
            (
                "advanced tracking",
                "automatic export",
            ),
        ),
    ],
)
def test_mvp_exclusions_never_enter_positive_scope_or_workflows(
    language: str,
    description: str,
    required_terms: tuple[str, ...],
    excluded_terms: tuple[str, ...],
) -> None:
    packet = project_context_extractor.extract(
        title="ScopePolarity",
        description=description,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    scope_key = comparison_key(
        " | ".join(
            packet.mvp_scope
        )
    )

    workflow_key = comparison_key(
        " | ".join(
            workflow.sentence
            for workflow
            in packet.priority_workflows
        )
    )

    for term in required_terms:
        assert (
            comparison_key(term)
            in scope_key
        ), packet.mvp_scope

    for term in excluded_terms:
        excluded_key = comparison_key(
            term
        )

        assert (
            excluded_key
            not in scope_key
        ), packet.mvp_scope

        assert (
            excluded_key
            not in workflow_key
        ), [
            workflow.model_dump(
                mode="json"
            )
            for workflow
            in packet.priority_workflows
        ]


@pytest.mark.parametrize(
    ("language", "description"),
    [
        (
            "fr",
            (
                "Le suivi avanc\u00e9 ne fait pas partie "
                "du premier MVP."
            ),
        ),
        (
            "en",
            (
                "Advanced tracking is not part "
                "of the first MVP."
            ),
        ),
    ],
)
def test_exclusion_only_never_creates_positive_mvp_or_workflow(
    language: str,
    description: str,
) -> None:
    packet = project_context_extractor.extract(
        title="ScopePolarity",
        description=description,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    assert packet.mvp_scope == []
    assert packet.priority_workflows == []


@pytest.mark.parametrize(
    (
        "language",
        "negative_main_use_case",
        "solution",
    ),
    [
        (
            "fr",
            (
                "Elle n'inclut pas initialement "
                "les rapports avanc\u00e9s."
            ),
            "Plateforme de traitement des demandes.",
        ),
        (
            "en",
            (
                "It will not initially include "
                "advanced reports."
            ),
            "Request processing platform.",
        ),
    ],
)
def test_project_intelligence_never_promotes_scope_exclusion(
    language: str,
    negative_main_use_case: str,
    solution: str,
) -> None:
    result = project_intelligence_layer.build(
        title="ScopePolarity",
        description=solution,
        industry="software",
        target_region="Europe",
        output_language=language,
        project_context={
            "solution": solution,
        },
        idea_readiness={
            "detected": {
                "main_use_case": negative_main_use_case,
                "mvp_scope": negative_main_use_case,
            },
        },
    )

    structured = (
        result.get(
            "structured_project_context"
        )
        or {}
    )

    assert not is_scope_exclusion_statement(
        structured.get(
            "main_use_case"
        )
    )

    assert not is_scope_exclusion_statement(
        structured.get(
            "mvp_scope"
        )
    )

    assert not structured.get(
        "mvp_scope"
    )


def test_scope_section_heading_supports_accented_and_ascii_perimetre(
) -> None:
    """
    Universal linguistic invariant:

    French scope-section polarity must not depend on whether the user
    writes the canonical accented spelling "périmètre" or its common
    ASCII form "perimetre".

    Both forms must create the same positive/negative section boundary.
    """
    from app.services.scope_polarity import (
        partition_scope_sections,
    )

    cases = (
        "Hors du périmètre :",
        "Hors du perimetre :",
    )

    for heading in cases:
        positive, excluded = (
            partition_scope_sections(
                (
                    "MVP: capability alpha. "
                    f"{heading} capability beta."
                )
            )
        )

        positive_key = (
            positive.casefold()
        )

        excluded_key = (
            excluded.casefold()
        )

        assert (
            "capability alpha"
            in positive_key
        ), (
            heading,
            positive,
            excluded,
        )

        assert (
            "capability beta"
            not in positive_key
        ), (
            heading,
            positive,
            excluded,
        )

        assert (
            "capability beta"
            in excluded_key
        ), (
            heading,
            positive,
            excluded,
        )
