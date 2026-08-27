from __future__ import annotations

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
        title="Planning Control Semantics Contract",
        description=description,
        industry="General project domain",
        target_region="International",
        output_language=language,
    )


def joined(
    values,
) -> str:
    return comparison_key(
        " | ".join(
            str(value)
            for value in values
        )
    )


def test_explicit_exclusion_remains_scope_exclusion_not_positive_mvp() -> None:

    packet = extract(
        (
            "The MVP does not include "
            "automatic payment execution."
        )
    )

    assert (
        "payment"
        in joined(
            packet.scope_exclusions
        )
    )

    assert (
        "payment"
        not in joined(
            packet.mvp_scope
        )
    )


def test_negative_modal_mvp_control_is_constraint_not_positive_scope() -> None:

    packet = extract(
        (
            "The MVP must not autonomously issue "
            "legally binding decisions."
        )
    )

    constraint_text = joined(
        packet.constraints
    )

    assert (
        "legally binding decisions"
        in constraint_text
    ), packet.model_dump(
        mode="json"
    )

    assert (
        "legally binding decisions"
        not in joined(
            packet.mvp_scope
        )
    ), packet.model_dump(
        mode="json"
    )


def test_security_prohibition_is_canonical_constraint() -> None:

    packet = extract(
        (
            "The system must not store passwords "
            "in plaintext."
        )
    )

    constraint_text = joined(
        packet.constraints
    )

    assert (
        "passwords"
        in constraint_text
    ), packet.model_dump(
        mode="json"
    )

    assert (
        "plaintext"
        in constraint_text
    )


def test_positive_mvp_capability_remains_positive_scope() -> None:

    packet = extract(
        (
            "The MVP must allow operators "
            "to approve incoming requests."
        )
    )

    scope_text = joined(
        packet.mvp_scope
    )

    assert (
        "approve incoming requests"
        in scope_text
    ), packet.model_dump(
        mode="json"
    )

    assert (
        "approve incoming requests"
        not in joined(
            packet.constraints
        )
    )


def test_explicit_human_review_is_canonical_human_oversight() -> None:

    packet = extract(
        (
            "A qualified professional must review "
            "every recommendation before final approval."
        )
    )

    oversight_text = joined(
        packet.human_oversight
    )

    assert (
        "qualified professional"
        in oversight_text
    ), packet.model_dump(
        mode="json"
    )

    assert (
        "review"
        in oversight_text
    )


def test_french_negative_modal_control_is_constraint_not_positive_scope() -> None:

    packet = extract(
        (
            "Le MVP ne doit pas prendre automatiquement "
            "de decision juridiquement contraignante."
        ),
        language="fr",
    )

    constraint_text = joined(
        packet.constraints
    )

    assert (
        "juridiquement contraignante"
        in constraint_text
    ), packet.model_dump(
        mode="json"
    )

    assert (
        "juridiquement contraignante"
        not in joined(
            packet.mvp_scope
        )
    )


def test_french_explicit_human_validation_is_human_oversight() -> None:

    packet = extract(
        (
            "Un professionnel qualifie doit valider "
            "chaque recommandation avant la decision finale."
        ),
        language="fr",
    )

    oversight_text = joined(
        packet.human_oversight
    )

    assert (
        "professionnel qualifie"
        in oversight_text
    ), packet.model_dump(
        mode="json"
    )

    assert (
        "valider"
        in oversight_text
    )
