
from __future__ import annotations

from app.schemas.analysis_context import (
    comparison_key,
)
from app.services.project_context_extractor import (
    ProjectContextExtractor,
)
from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


def _packet(
    description: str,
):
    return ProjectContextExtractor().extract(
        title="Neutral Product",
        description=description,
        industry="Business software",
        target_region="International",
        output_language="en",
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def _keys(
    values,
) -> set[str]:

    return {
        comparison_key(
            value
        )
        for value in values
        if comparison_key(
            value
        )
    }


def test_existing_mvp_does_not_include_grammar_remains_supported() -> None:

    assert is_scope_exclusion_statement(
        "The MVP does not include advanced accounting."
    )


def test_negative_security_control_is_not_scope_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        "The system must not store credentials in plaintext."
    )


def test_operational_negative_behavior_is_not_scope_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        (
            "The application does not lose pending requests "
            "during reconnect."
        )
    )


def test_positive_capability_is_not_scope_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        "The MVP provides request tracking."
    )


def test_product_does_not_collect_capability_in_mvp_is_scope_exclusion() -> None:

    assert is_scope_exclusion_statement(
        (
            "The product does not collect transaction payments "
            "in the MVP."
        )
    )


def test_platform_does_not_provide_capability_in_mvp_is_scope_exclusion() -> None:

    assert is_scope_exclusion_statement(
        (
            "The platform does not provide advanced accounting "
            "in the MVP."
        )
    )


def test_service_does_not_perform_capability_in_first_release_is_scope_exclusion() -> None:

    assert is_scope_exclusion_statement(
        (
            "The service does not perform physical delivery "
            "in the first release."
        )
    )


def test_freeform_negated_mvp_capability_routes_out_of_positive_scope() -> None:

    packet = _packet(
        (
            "The MVP provides request tracking. "
            "The platform does not provide advanced accounting "
            "in the MVP."
        )
    )

    positive = _keys(
        packet.mvp_scope
    )

    excluded = _keys(
        packet.scope_exclusions
    )

    assert not any(
        "advanced accounting"
        in value
        for value in positive
    ), packet.mvp_scope

    assert any(
        "advanced accounting"
        in value
        for value in excluded
    ), packet.scope_exclusions


def test_french_product_capability_negation_with_mvp_scope_is_exclusion() -> None:

    assert is_scope_exclusion_statement(
        (
            "La plateforme ne fournit pas de comptabilite avancee "
            "dans le MVP."
        )
    )


def test_french_negative_security_control_remains_not_scope_exclusion() -> None:

    assert not is_scope_exclusion_statement(
        (
            "Le systeme ne doit pas stocker "
            "les mots de passe en clair."
        )
    )
