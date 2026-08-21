from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    comparison_key,
)
from app.services.constraint_semantics import (
    has_explicit_scope_reference,
    is_constraint_statement,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        (
            "L'historique de maintenance est disponible.",
            False,
        ),
        (
            "Maintenance history is available.",
            False,
        ),
        (
            "La plateforme envoie des alertes.",
            False,
        ),
        (
            "The platform sends alerts.",
            False,
        ),
        (
            "Le budget est limit\u00e9 \u00e0 20000 euros.",
            True,
        ),
        (
            "The budget is limited to 20000 euros.",
            True,
        ),
        (
            "La solution doit fonctionner hors ligne.",
            True,
        ),
        (
            "The solution must work offline.",
            True,
        ),
        (
            (
                "Les donn\u00e9es doivent rester h\u00e9berg\u00e9es "
                "dans l'Union europ\u00e9enne."
            ),
            True,
        ),
        (
            (
                "Data must remain hosted "
                "in the European Union."
            ),
            True,
        ),
        (
            (
                "L'application doit \u00eatre compatible "
                "avec le mat\u00e9riel existant."
            ),
            True,
        ),
        (
            (
                "The application must be compatible "
                "with existing hardware."
            ),
            True,
        ),
        (
            (
                "Le d\u00e9ploiement doit \u00eatre termin\u00e9 "
                "dans trois mois."
            ),
            True,
        ),
        (
            (
                "Deployment must be completed "
                "within three months."
            ),
            True,
        ),
        (
            (
                "Le MVP inclut l'historique "
                "de maintenance."
            ),
            False,
        ),
        (
            (
                "The MVP includes "
                "maintenance history."
            ),
            False,
        ),
    ],
)
def test_constraint_classifier_distinguishes_features_and_boundaries(
    sentence: str,
    expected: bool,
) -> None:
    assert (
        is_constraint_statement(
            sentence
        )
        is expected
    )


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        (
            "The budget is limited to 20000 euros.",
            False,
        ),
        (
            "Le budget est limit\u00e9 \u00e0 20000 euros.",
            False,
        ),
        (
            "The MVP is limited to case management.",
            True,
        ),
        (
            (
                "Le MVP est limit\u00e9 \u00e0 "
                "la gestion des dossiers."
            ),
            True,
        ),
    ],
)
def test_scope_reference_requires_real_scope_artifact(
    sentence: str,
    expected: bool,
) -> None:
    assert (
        has_explicit_scope_reference(
            sentence
        )
        is expected
    )


@pytest.mark.parametrize(
    ("language", "description"),
    [
        (
            "fr",
            (
                "La plateforme permet la gestion des dossiers "
                "et l'historique des interventions. "
                "Le budget est limit\u00e9 \u00e0 20000 euros. "
                "La solution doit fonctionner hors ligne. "
                "Le d\u00e9ploiement doit \u00eatre termin\u00e9 "
                "dans trois mois."
            ),
        ),
        (
            "en",
            (
                "The platform provides case management "
                "and intervention history. "
                "The budget is limited to 20000 euros. "
                "The solution must work offline. "
                "Deployment must be completed "
                "within three months."
            ),
        ),
    ],
)
def test_real_constraints_are_extracted_without_feature_pollution(
    language: str,
    description: str,
) -> None:
    packet = project_context_extractor.extract(
        title="ConstraintSemantics",
        description=description,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    constraints_key = comparison_key(
        " | ".join(
            packet.constraints
        )
    )

    assert "budget" in constraints_key

    if language == "fr":
        assert "hors ligne" in constraints_key
        assert "trois mois" in constraints_key
    else:
        assert "offline" in constraints_key
        assert "three months" in constraints_key

    assert (
        "historique des interventions"
        not in constraints_key
    )

    assert (
        "intervention history"
        not in constraints_key
    )


@pytest.mark.parametrize(
    ("language", "description"),
    [
        (
            "fr",
            (
                "Le MVP doit inclure la gestion des v\u00e9hicules, "
                "l'historique de maintenance, les d\u00e9penses "
                "et les alertes."
            ),
        ),
        (
            "en",
            (
                "The MVP must include vehicle management, "
                "maintenance history, expenses and alerts."
            ),
        ),
    ],
)
def test_mvp_features_never_become_constraints(
    language: str,
    description: str,
) -> None:
    packet = project_context_extractor.extract(
        title="ConstraintSemantics",
        description=description,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    assert packet.constraints == []
    assert packet.mvp_scope


@pytest.mark.parametrize(
    ("language", "description"),
    [
        (
            "fr",
            "Le budget est limit\u00e9 \u00e0 20000 euros.",
        ),
        (
            "en",
            "The budget is limited to 20000 euros.",
        ),
    ],
)
def test_budget_limit_never_becomes_mvp_scope(
    language: str,
    description: str,
) -> None:
    packet = project_context_extractor.extract(
        title="ConstraintSemantics",
        description=description,
        industry="software",
        target_region="Europe",
        output_language=language,
    )

    assert packet.mvp_scope == []
    assert packet.constraints
