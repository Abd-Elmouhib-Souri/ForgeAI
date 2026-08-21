import pytest

from app.services.project_context_extractor import (
    project_context_extractor,
)


@pytest.mark.parametrize(
    "sentence",
    [
        (
            "Le technicien utilise la plateforme chaque jour "
            "et n\u2019est pas n\u00e9cessairement la personne "
            "qui d\u00e9cide du budget ou qui paie "
            "l\u2019abonnement."
        ),
        (
            "The technician uses the platform every day and "
            "is not necessarily the person who decides the "
            "budget or pays the subscription."
        ),
        (
            "La documentation explique les options "
            "d\u2019abonnement disponibles dans l\u2019interface."
        ),
        (
            "The onboarding guide describes the subscription "
            "settings available in the interface."
        ),
    ],
)
def test_incidental_or_negative_business_vocabulary_is_not_model(
    sentence,
):
    assert not (
        project_context_extractor
        ._is_explicit_business_model_statement(
            sentence
        )
    )


@pytest.mark.parametrize(
    "sentence",
    [
        (
            "Le mod\u00e8le \u00e9conomique envisag\u00e9 "
            "est un abonnement mensuel pay\u00e9 "
            "par l\u2019entreprise."
        ),
        (
            "The business model is a monthly subscription "
            "paid by the client company."
        ),
        (
            "Les clients paient un abonnement mensuel."
        ),
        (
            "Customers pay a monthly subscription."
        ),
        (
            "La plateforme facture une commission "
            "sur chaque transaction."
        ),
        (
            "The platform charges a commission "
            "on each transaction."
        ),
        (
            "Le service est freemium."
        ),
        (
            "The service is freemium."
        ),
    ],
)
def test_positive_monetization_declaration_is_business_model(
    sentence,
):
    assert (
        project_context_extractor
        ._is_explicit_business_model_statement(
            sentence
        )
    )


def test_free_text_extraction_rejects_negative_role_statement():
    sentences = [
        (
            "Le technicien n\u2019est pas n\u00e9cessairement "
            "la personne qui paie l\u2019abonnement."
        ),
        (
            "Le mod\u00e8le \u00e9conomique est "
            "un abonnement mensuel."
        ),
    ]

    all_models, explicit_models = (
        project_context_extractor
        ._extract_business_models(
            sentences=sentences,
            structured={},
            project_context={},
            analysis_data={},
        )
    )

    assert len(explicit_models) == 1

    assert (
        "mod\u00e8le \u00e9conomique"
        in explicit_models[0].casefold()
    )

    assert all(
        "technicien"
        not in model.casefold()
        for model in all_models
    )


def test_structured_business_model_remains_authoritative():
    value = (
        "enterprise subscription with annual billing"
    )

    all_models, explicit_models = (
        project_context_extractor
        ._extract_business_models(
            sentences=[],
            structured={},
            project_context={
                "business_model": value,
            },
            analysis_data={},
        )
    )

    assert value in explicit_models
    assert value in all_models



@pytest.mark.parametrize(
    (
        "explicit_value",
        "inferred_value",
    ),
    [
        (
            (
                "Le mod\u00e8le \u00e9conomique envisag\u00e9 "
                "est un abonnement mensuel pay\u00e9 "
                "par l\u2019entreprise."
            ),
            (
                "abonnement mensuel pay\u00e9 "
                "par l\u2019entreprise"
            ),
        ),
        (
            (
                "The business model is a monthly subscription "
                "paid by the client company."
            ),
            (
                "monthly subscription "
                "paid by the client company"
            ),
        ),
    ],
)
def test_equivalent_explicit_and_inferred_business_models_collapse(
    explicit_value,
    inferred_value,
):
    all_models, explicit_models = (
        project_context_extractor
        ._extract_business_models(
            sentences=[
                explicit_value,
            ],
            structured={
                "business_model": (
                    inferred_value
                ),
            },
            project_context={},
            analysis_data={},
        )
    )

    assert len(
        explicit_models
    ) == 1

    assert len(
        all_models
    ) == 1

    assert (
        all_models[0]
        == explicit_models[0]
    )


@pytest.mark.parametrize(
    "models",
    [
        (
            "abonnement mensuel",
            (
                "abonnement mensuel et "
                "commission sur chaque transaction"
            ),
        ),
        (
            "monthly subscription",
            (
                "monthly subscription plus "
                "commission on each transaction"
            ),
        ),
        (
            "freemium",
            "freemium avec commission",
        ),
        (
            "freemium",
            "freemium with commission",
        ),
    ],
)
def test_distinct_monetization_mechanisms_are_preserved(
    models,
):
    result = (
        project_context_extractor
        ._dedupe_business_models(
            list(models)
        )
    )

    assert len(
        result
    ) == 2


@pytest.mark.parametrize(
    "models",
    [
        (
            "abonnement mensuel",
            "abonnement annuel",
        ),
        (
            "monthly subscription",
            "annual subscription",
        ),
    ],
)
def test_same_mechanism_with_distinct_pricing_cadence_is_preserved(
    models,
):
    result = (
        project_context_extractor
        ._dedupe_business_models(
            list(models)
        )
    )

    assert len(
        result
    ) == 2


@pytest.mark.parametrize(
    (
        "explicit_value",
        "inferred_value",
    ),
    [
        (
            (
                "Le mod\u00e8le \u00e9conomique est "
                "un abonnement mensuel pay\u00e9 "
                "par l\u2019entreprise."
            ),
            (
                "abonnement mensuel pay\u00e9 "
                "par l\u2019entreprise"
            ),
        ),
        (
            (
                "The business model is "
                "a monthly subscription paid "
                "by the customer."
            ),
            (
                "a monthly subscription "
                "paid by the customer"
            ),
        ),
    ],
)
def test_explicit_business_model_wins_over_equivalent_inferred_form(
    explicit_value,
    inferred_value,
):
    result = (
        project_context_extractor
        ._dedupe_business_models(
            [
                explicit_value,
                inferred_value,
            ]
        )
    )

    assert result == [
        explicit_value.rstrip(".")
    ]
