from __future__ import annotations

import importlib
import importlib.util

import pytest
from pydantic import (
    BaseModel,
    ValidationError,
)


SCHEMA_MODULE = (
    "app.schemas.project_management"
)

FACTOR_MODEL = (
    "CandidateComplexityFactorsV1"
)

FACTOR_FIELD = (
    "candidate_complexity_factors"
)


EXPECTED_FACTORS = {
    "business_logic",
    "integration_complexity",
    "data_complexity",
    "ui_complexity",
    "security",
    "external_dependency",
    "uncertainty",
    "testing_burden",
    "regulatory_risk",
    "hardware_dependency",
}


ALLOWED_SIGNALS = {
    "none",
    "low",
    "medium",
    "high",
    "unknown",
}


def schema_module():
    return importlib.import_module(
        SCHEMA_MODULE
    )


def factor_model_exists() -> bool:

    return hasattr(
        schema_module(),
        FACTOR_MODEL,
    )


def skip_until_factor_model_exists() -> None:

    if not factor_model_exists():

        pytest.skip(
            "Blocked by missing structured "
            "Story Point estimation input."
        )


def factor_model():

    skip_until_factor_model_exists()

    return getattr(
        schema_module(),
        FACTOR_MODEL,
    )


def candidate_story_model():

    return getattr(
        schema_module(),
        "CandidateUserStoryV1",
    )


def canonical_story_model():

    return getattr(
        schema_module(),
        "CanonicalUserStoryV1",
    )


def payload(
    value: object,
) -> dict[str, object]:

    return {
        factor:
            value
        for factor
        in EXPECTED_FACTORS
    }


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_structured_story_point_factor_model_exists() -> None:

    assert factor_model_exists(), (
        "Missing structured Story Point estimation input: "
        "CandidateComplexityFactorsV1"
    )


# ============================================================
# STRICT MODEL
# ============================================================


def test_factor_model_is_strict_pydantic() -> None:

    skip_until_factor_model_exists()

    model = factor_model()

    assert issubclass(
        model,
        BaseModel,
    )

    assert (
        model.model_config.get(
            "extra"
        )
        ==
        "forbid"
    )


def test_factor_model_contains_exact_plan_dimensions() -> None:

    skip_until_factor_model_exists()

    assert set(
        factor_model().model_fields
    ) == EXPECTED_FACTORS


def test_all_complexity_dimensions_are_required() -> None:

    skip_until_factor_model_exists()

    for field in (
        factor_model()
        .model_fields
        .values()
    ):

        assert field.is_required()


# ============================================================
# UNIVERSAL SIGNAL VOCABULARY
# ============================================================


@pytest.mark.parametrize(
    "signal",
    (
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    ),
)
def test_each_supported_signal_is_valid(
    signal,
) -> None:

    skip_until_factor_model_exists()

    instance = factor_model()(
        **payload(
            signal
        )
    )

    dumped = instance.model_dump()

    assert set(
        dumped.values()
    ) == {
        signal
    }


@pytest.mark.parametrize(
    "invalid_signal",
    (
        "",
        "very_low",
        "very_high",
        "critical",
        "n/a",
        1,
        5,
        None,
    ),
)
def test_unsupported_factor_signal_is_rejected(
    invalid_signal,
) -> None:

    skip_until_factor_model_exists()

    with pytest.raises(
        ValidationError
    ):

        factor_model()(
            **payload(
                invalid_signal
            )
        )


def test_unknown_is_distinct_from_none() -> None:

    skip_until_factor_model_exists()

    unknown = factor_model()(
        **payload(
            "unknown"
        )
    )

    none = factor_model()(
        **payload(
            "none"
        )
    )

    assert unknown != none

    assert set(
        unknown.model_dump().values()
    ) == {
        "unknown"
    }

    assert set(
        none.model_dump().values()
    ) == {
        "none"
    }


# ============================================================
# CANDIDATE -> CANONICAL FLOW
# ============================================================


def test_candidate_story_exposes_structured_complexity_factors() -> None:

    skip_until_factor_model_exists()

    assert (
        FACTOR_FIELD
        in
        candidate_story_model().model_fields
    )


def test_canonical_story_preserves_structured_complexity_factors() -> None:

    skip_until_factor_model_exists()

    assert (
        FACTOR_FIELD
        in
        canonical_story_model().model_fields
    )


# ============================================================
# OLD SUMMARY SIGNAL REMAINS SEPARATE
# ============================================================


def test_candidate_complexity_summary_remains_separate() -> None:

    skip_until_factor_model_exists()

    candidate_fields = (
        candidate_story_model()
        .model_fields
    )

    canonical_fields = (
        canonical_story_model()
        .model_fields
    )

    assert (
        "candidate_complexity"
        in candidate_fields
    )

    assert (
        "candidate_complexity"
        in canonical_fields
    )

    assert (
        FACTOR_FIELD
        in candidate_fields
    )

    assert (
        FACTOR_FIELD
        in canonical_fields
    )

    assert (
        FACTOR_FIELD
        !=
        "candidate_complexity"
    )


# ============================================================
# FINAL STORY POINT AUTHORITY REMAINS SEPARATE
# ============================================================


def test_factor_model_does_not_contain_final_authority_fields() -> None:

    skip_until_factor_model_exists()

    forbidden = {
        "story_points",
        "split_recommended",
        "priority",
        "sprint",
        "sprint_id",
        "sprint_number",
        "dependencies",
        "locked",
    }

    leaked = (
        forbidden
        &
        set(
            factor_model().model_fields
        )
    )

    assert not leaked


def test_canonical_story_keeps_story_points_separate() -> None:

    skip_until_factor_model_exists()

    fields = (
        canonical_story_model()
        .model_fields
    )

    assert "story_points" in fields

    assert FACTOR_FIELD in fields

    assert (
        FACTOR_FIELD
        !=
        "story_points"
    )


# ============================================================
# NO SILENT DEFAULTS
# ============================================================


def test_missing_factor_is_rejected() -> None:

    skip_until_factor_model_exists()

    complete = payload(
        "low"
    )

    complete.pop(
        "hardware_dependency"
    )

    with pytest.raises(
        ValidationError
    ):

        factor_model()(
            **complete
        )


def test_extra_factor_is_rejected() -> None:

    skip_until_factor_model_exists()

    complete = payload(
        "low"
    )

    complete[
        "country_complexity"
    ] = "high"

    with pytest.raises(
        ValidationError
    ):

        factor_model()(
            **complete
        )


# ============================================================
# STORY POINT POLICY MUST STILL NOT EXIST
# ============================================================


def test_story_point_policy_is_not_used_to_hide_missing_input() -> None:

    skip_until_factor_model_exists()

    spec = importlib.util.find_spec(
        "app.services.story_point_policy"
    )

    assert spec is None, (
        "StoryPointPolicy must not be implemented "
        "before structured estimation input "
        "has its own GREEN authority contract."
    )


# ============================================================
# STRUCTURED INPUT ITSELF IS REQUIRED
# ============================================================


def test_candidate_story_requires_structured_complexity_factors() -> None:

    skip_until_factor_model_exists()

    field = (
        candidate_story_model()
        .model_fields[
            FACTOR_FIELD
        ]
    )

    assert field.is_required()


def test_canonical_story_requires_structured_complexity_factors() -> None:

    skip_until_factor_model_exists()

    field = (
        canonical_story_model()
        .model_fields[
            FACTOR_FIELD
        ]
    )

    assert field.is_required()


def test_candidate_story_factor_field_uses_exact_factor_model() -> None:

    skip_until_factor_model_exists()

    field = (
        candidate_story_model()
        .model_fields[
            FACTOR_FIELD
        ]
    )

    assert (
        field.annotation
        is
        factor_model()
    )


def test_canonical_story_factor_field_uses_exact_factor_model() -> None:

    skip_until_factor_model_exists()

    field = (
        canonical_story_model()
        .model_fields[
            FACTOR_FIELD
        ]
    )

    assert (
        field.annotation
        is
        factor_model()
    )


# ============================================================
# PRODUCT OWNER STRUCTURED OUTPUT CONTRACT
# ============================================================


def test_product_owner_prompt_requires_structured_complexity_factor_contract() -> None:

    import inspect

    from app.agents.product_owner_agent import (
        ProductOwnerAgent,
    )


    source = inspect.getsource(
        ProductOwnerAgent.build_prompt
    )


    required_tokens = (
        "candidate_complexity_factors",
        "business_logic",
        "integration_complexity",
        "data_complexity",
        "ui_complexity",
        "security",
        "external_dependency",
        "uncertainty",
        "testing_burden",
        "regulatory_risk",
        "hardware_dependency",
        "none",
        "low",
        "medium",
        "high",
        "unknown",
    )


    missing = [
        token
        for token
        in required_tokens
        if token not in source
    ]


    assert not missing, (
        "Product Owner prompt is missing the structured "
        "complexity output contract: "
        + ", ".join(
            missing
        )
    )


    assert (
        "Do not assign final Story Points"
        in source
    )


    assert (
        "Candidate complexity is advisory only"
        in source
    )
