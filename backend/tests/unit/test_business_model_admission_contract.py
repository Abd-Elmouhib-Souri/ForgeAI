import pytest

from app.services.project_context_extractor import (
    project_context_extractor,
)


@pytest.mark.parametrize(
    "sentence",
    (
        (
            "L'unite de transaction principale "
            "est une location mensuelle."
        ),
        (
            "The primary transaction unit "
            "is a monthly rental."
        ),
        (
            "Le modele economique comporte "
            "deux sources de revenus distinctes."
        ),
        (
            "The business model includes "
            "two distinct revenue streams."
        ),
    ),
)
def test_transaction_or_meta_business_statement_is_not_model(
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
    (
        (
            "La plateforme preleve une commission "
            "sur chaque transaction."
        ),
        (
            "La plateforme percoit une commission "
            "sur chaque transaction."
        ),
        (
            "The platform collects a commission "
            "on each transaction."
        ),
        (
            "The platform takes a commission "
            "on each transaction."
        ),
    ),
)
def test_direct_commission_relation_is_business_model(
    sentence,
):
    assert (
        project_context_extractor
        ._is_explicit_business_model_statement(
            sentence
        )
    )


@pytest.mark.parametrize(
    "sentence",
    (
        (
            "Les entreprises peuvent souscrire "
            "a un abonnement mensuel."
        ),
        (
            "Companies can subscribe "
            "to a monthly subscription."
        ),
    ),
)
def test_direct_subscription_relation_is_business_model(
    sentence,
):
    assert (
        project_context_extractor
        ._is_explicit_business_model_statement(
            sentence
        )
    )


@pytest.mark.parametrize(
    "sentence",
    (
        (
            "Le modele economique est "
            "une facturation a l'usage."
        ),
        (
            "The business model is "
            "usage-based pricing."
        ),
    ),
)
def test_labelled_concrete_unknown_mechanism_is_preserved(
    sentence,
):
    assert (
        project_context_extractor
        ._is_explicit_business_model_statement(
            sentence
        )
    )


@pytest.mark.parametrize(
    "sentence",
    (
        (
            "Le modele economique comprend "
            "un abonnement et une commission."
        ),
        (
            "The business model includes "
            "a subscription and a commission."
        ),
    ),
)
def test_labelled_known_mechanisms_are_preserved(
    sentence,
):
    assert (
        project_context_extractor
        ._is_explicit_business_model_statement(
            sentence
        )
    )


def test_free_text_extraction_keeps_only_real_monetization_models():
    sentences = [
        (
            "L'unite de transaction principale "
            "est une reservation mensuelle."
        ),
        (
            "Le modele economique comporte "
            "deux sources de revenus distinctes."
        ),
        (
            "La plateforme preleve une commission "
            "sur chaque transaction."
        ),
        (
            "Les entreprises peuvent souscrire "
            "a un abonnement mensuel."
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

    assert len(
        explicit_models
    ) == 2

    joined = " | ".join(
        explicit_models
    ).casefold()

    assert "commission" in joined
    assert "abonnement" in joined

    assert "unite de transaction" not in joined
    assert "deux sources de revenus" not in joined

    assert all_models == explicit_models
