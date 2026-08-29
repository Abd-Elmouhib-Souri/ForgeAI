from __future__ import annotations

import importlib.util
from typing import Any

import pytest


MODULE_NAME = "app.services.story_point_policy"


FACTOR_NAMES = (
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
)


CALIBRATION_BOUNDARIES = (
    (0, 1),
    (1, 2),
    (5, 2),
    (6, 3),
    (10, 3),
    (11, 5),
    (15, 5),
    (16, 8),
    (20, 8),
    (21, 13),
    (25, 13),
    (26, 21),
    (30, 21),
)


def _module_exists() -> bool:
    try:
        return (
            importlib.util.find_spec(
                MODULE_NAME
            )
            is not None
        )
    except ModuleNotFoundError:
        return False


POLICY_EXISTS = _module_exists()


runtime_contract = pytest.mark.skipif(
    not POLICY_EXISTS,
    reason=(
        "StoryPointPolicy does not exist yet; "
        "authority RED remains the current FWL."
    ),
)


def _profile_for_load(
    target_load: int,
) -> dict[str, str]:
    if not 0 <= target_load <= 30:
        raise ValueError(
            "target load must be in 0..30"
        )

    profile = {
        name: "none"
        for name in FACTOR_NAMES
    }

    remaining = target_load

    for name in FACTOR_NAMES:
        if remaining >= 3:
            profile[name] = "high"
            remaining -= 3
            continue

        if remaining == 2:
            profile[name] = "medium"
            remaining = 0
            continue

        if remaining == 1:
            profile[name] = "low"
            remaining = 0
            continue

        break

    assert remaining == 0

    return profile


def _story_identity(
    model: Any,
) -> dict[str, str]:
    fields = set(
        model.model_fields
    )

    if "story_id" in fields:
        return {
            "story_id": "US-001"
        }

    if "id" in fields:
        return {
            "id": "US-001"
        }

    raise AssertionError(
        "CanonicalUserStoryV1 exposes "
        "no stable story identity"
    )


def _runtime_symbols() -> tuple[Any, ...]:
    from app.schemas.project_management import (
        CandidateComplexityFactorsV1,
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        ProjectManagementContextV1,
    )

    from app.services.story_point_policy import (
        StoryPointPolicy,
        StoryPointPolicyError,
    )

    return (
        CandidateComplexityFactorsV1,
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        ProjectManagementContextV1,
        StoryPointPolicy,
        StoryPointPolicyError,
    )


def _apply(
    profile: dict[str, str],
):
    (
        CandidateComplexityFactorsV1,
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        ProjectManagementContextV1,
        StoryPointPolicy,
        _StoryPointPolicyError,
    ) = _runtime_symbols()

    factors = CandidateComplexityFactorsV1(
        **profile
    )

    story = CanonicalUserStoryV1.model_construct(
        **_story_identity(
            CanonicalUserStoryV1
        ),
        candidate_complexity="advisory",
        candidate_complexity_rationale="advisory-only",
        candidate_complexity_factors=factors,
        story_points=None,
    )

    backlog = CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash="src-hash",
        context_hash="ctx-hash",
        epics=[],
        features=[],
        stories=[
            story
        ],
        warnings=[],
    )

    context = ProjectManagementContextV1.model_construct(
        source_context_hash="src-hash",
        context_hash="ctx-hash",
    )

    return StoryPointPolicy().apply(
        context=context,
        backlog=backlog,
    )


def test_binding_contract_records_all_v1_boundaries() -> None:
    assert CALIBRATION_BOUNDARIES == (
        (0, 1),
        (1, 2),
        (5, 2),
        (6, 3),
        (10, 3),
        (11, 5),
        (15, 5),
        (16, 8),
        (20, 8),
        (21, 13),
        (25, 13),
        (26, 21),
        (30, 21),
    )


@runtime_contract
@pytest.mark.parametrize(
    (
        "load",
        "expected_story_points",
    ),
    CALIBRATION_BOUNDARIES,
)
def test_runtime_policy_matches_every_v1_calibration_boundary(
    load: int,
    expected_story_points: int,
) -> None:
    result = _apply(
        _profile_for_load(
            load
        )
    )

    assert len(
        result.decisions
    ) == 1

    decision = result.decisions[0]
    output_story = result.backlog.stories[0]

    assert (
        decision.story_points
        ==
        expected_story_points
    )

    assert (
        output_story.story_points
        ==
        expected_story_points
    )

    assert (
        decision.split_recommended
        is (
            expected_story_points
            == 21
        )
    )


@runtime_contract
def test_runtime_uniform_profiles_match_v1_calibration() -> None:
    expected = {
        "none": 1,
        "low": 3,
        "medium": 8,
        "high": 21,
    }

    for signal, story_points in expected.items():
        profile = {
            name: signal
            for name in FACTOR_NAMES
        }

        decision = _apply(
            profile
        ).decisions[0]

        assert (
            decision.story_points
            ==
            story_points
        )


@runtime_contract
def test_runtime_partial_unknown_uses_conservative_upper_bound() -> None:
    profile = {
        name: "none"
        for name in FACTOR_NAMES
    }

    profile[
        "external_dependency"
    ] = "unknown"

    decision = _apply(
        profile
    ).decisions[0]

    assert decision.story_points == 2


@runtime_contract
def test_runtime_all_unknown_fails_closed() -> None:
    (
        _CandidateComplexityFactorsV1,
        _CanonicalBacklogV1,
        _CanonicalUserStoryV1,
        _ProjectManagementContextV1,
        _StoryPointPolicy,
        StoryPointPolicyError,
    ) = _runtime_symbols()

    profile = {
        name: "unknown"
        for name in FACTOR_NAMES
    }

    with pytest.raises(
        StoryPointPolicyError
    ):
        _apply(
            profile
        )


@runtime_contract
def test_runtime_factor_identity_has_equal_weight() -> None:
    outputs = set()

    for factor in FACTOR_NAMES:
        profile = {
            name: "none"
            for name in FACTOR_NAMES
        }

        profile[
            factor
        ] = "high"

        outputs.add(
            _apply(
                profile
            ).decisions[0].story_points
        )

    assert outputs == {
        2
    }
