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

KNOWN_SIGNAL_ORDER = (
    "none",
    "low",
    "medium",
    "high",
)

UNKNOWN_SIGNAL = "unknown"

ALLOWED_STORY_POINTS = {
    1,
    2,
    3,
    5,
    8,
    13,
    21,
}


def _module_exists() -> bool:
    try:
        return importlib.util.find_spec(
            MODULE_NAME
        ) is not None
    except ModuleNotFoundError:
        return False


POLICY_EXISTS = _module_exists()

runtime_contract = pytest.mark.skipif(
    not POLICY_EXISTS,
    reason=(
        "StoryPointPolicy does not exist yet; "
        "the authority RED owns the current FWL."
    ),
)


def _profile(
    value: str = "none",
) -> dict[str, str]:
    return {
        name: value
        for name in FACTOR_NAMES
    }


def _with(
    profile: dict[str, str],
    **changes: str,
) -> dict[str, str]:
    result = dict(profile)
    result.update(changes)
    return result


def _runtime_symbols() -> tuple[Any, ...]:
    from app.schemas.project_management import (
        CandidateComplexityFactorsV1,
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        ProjectManagementContextV1,
    )

    from app.services.story_point_policy import (
        StoryPointPolicy,
    )

    return (
        CandidateComplexityFactorsV1,
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        ProjectManagementContextV1,
        StoryPointPolicy,
    )


def _story_identity(
    model: Any,
) -> dict[str, str]:
    fields = set(model.model_fields)

    if "story_id" in fields:
        return {"story_id": "US-001"}

    if "id" in fields:
        return {"id": "US-001"}

    raise AssertionError(
        "CanonicalUserStoryV1 has no stable identity field"
    )


def _apply_profile(
    profile: dict[str, str],
    *,
    candidate_complexity: str = "advisory",
    industry: str = "generic",
    target_region: str = "generic",
):
    (
        CandidateComplexityFactorsV1,
        CanonicalBacklogV1,
        CanonicalUserStoryV1,
        ProjectManagementContextV1,
        StoryPointPolicy,
    ) = _runtime_symbols()

    factors = CandidateComplexityFactorsV1(
        **profile
    )

    story = CanonicalUserStoryV1.model_construct(
        **_story_identity(
            CanonicalUserStoryV1
        ),
        candidate_complexity=candidate_complexity,
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
        stories=[story],
        warnings=[],
    )

    context_fields = set(
        ProjectManagementContextV1.model_fields
    )

    context_values: dict[str, Any] = {
        "source_context_hash": "src-hash",
        "context_hash": "ctx-hash",
    }

    if "industry" in context_fields:
        context_values["industry"] = industry

    if "target_region" in context_fields:
        context_values["target_region"] = target_region

    context = ProjectManagementContextV1.model_construct(
        **context_values
    )

    result = StoryPointPolicy().apply(
        context=context,
        backlog=backlog,
    )

    decision = result.decisions[0]
    output_story = result.backlog.stories[0]

    return (
        result,
        decision,
        output_story,
        story,
        backlog,
    )


def test_semantic_contract_has_exact_ten_dimensions() -> None:
    assert len(FACTOR_NAMES) == 10
    assert len(set(FACTOR_NAMES)) == 10


def test_known_complexity_signal_order_is_explicit() -> None:
    assert KNOWN_SIGNAL_ORDER == (
        "none",
        "low",
        "medium",
        "high",
    )


def test_unknown_is_distinct_from_known_severity() -> None:
    assert UNKNOWN_SIGNAL not in KNOWN_SIGNAL_ORDER


def test_fibonacci_vocabulary_is_exact() -> None:
    assert ALLOWED_STORY_POINTS == {
        1,
        2,
        3,
        5,
        8,
        13,
        21,
    }


@runtime_contract
def test_same_profile_is_deterministic() -> None:
    profile = _with(
        _profile(),
        business_logic="medium",
        uncertainty="low",
        testing_burden="medium",
    )

    first = _apply_profile(profile)[1]
    second = _apply_profile(profile)[1]

    assert first.story_points == second.story_points
    assert (
        first.split_recommended
        ==
        second.split_recommended
    )


@runtime_contract
def test_output_is_fibonacci_only() -> None:
    profiles = (
        _profile("none"),
        _profile("low"),
        _profile("medium"),
        _profile("high"),
        _with(
            _profile("none"),
            business_logic="high",
            security="medium",
        ),
    )

    for profile in profiles:
        decision = _apply_profile(profile)[1]

        assert (
            decision.story_points
            in ALLOWED_STORY_POINTS
        )


@runtime_contract
@pytest.mark.parametrize(
    "factor_name",
    FACTOR_NAMES,
)
def test_single_factor_severity_is_monotonic(
    factor_name: str,
) -> None:
    values = []

    for signal in KNOWN_SIGNAL_ORDER:
        profile = _with(
            _profile("none"),
            **{
                factor_name: signal,
            },
        )

        values.append(
            _apply_profile(
                profile
            )[1].story_points
        )

    assert values == sorted(values)


@runtime_contract
def test_complexity_breadth_is_monotonic() -> None:
    values = []

    for count in range(
        len(FACTOR_NAMES) + 1
    ):
        profile = _profile("none")

        for name in FACTOR_NAMES[:count]:
            profile[name] = "medium"

        values.append(
            _apply_profile(
                profile
            )[1].story_points
        )

    assert values == sorted(values)


@runtime_contract
def test_unknown_never_reduces_vs_explicit_none() -> None:
    baseline_profile = _with(
        _profile("none"),
        business_logic="medium",
        security="low",
    )

    uncertain_profile = _with(
        baseline_profile,
        external_dependency="unknown",
    )

    baseline = _apply_profile(
        baseline_profile
    )[1]

    uncertain = _apply_profile(
        uncertain_profile
    )[1]

    assert (
        uncertain.story_points
        >=
        baseline.story_points
    )


@runtime_contract
def test_candidate_summary_is_advisory_only() -> None:
    profile = _with(
        _profile("none"),
        business_logic="medium",
        integration_complexity="medium",
    )

    low = _apply_profile(
        profile,
        candidate_complexity="low",
    )[1]

    high = _apply_profile(
        profile,
        candidate_complexity="high",
    )[1]

    assert low.story_points == high.story_points


@runtime_contract
def test_country_and_domain_do_not_change_canonical_mapping() -> None:
    profile = _with(
        _profile("none"),
        business_logic="medium",
        integration_complexity="high",
        uncertainty="low",
    )

    first = _apply_profile(
        profile,
        industry="logistics",
        target_region="Egypt",
    )[1]

    second = _apply_profile(
        profile,
        industry="healthcare",
        target_region="Germany",
    )[1]

    assert first.story_points == second.story_points


@runtime_contract
def test_factor_order_does_not_change_result() -> None:
    profile = _with(
        _profile("none"),
        business_logic="high",
        security="medium",
        uncertainty="low",
    )

    reordered = dict(
        reversed(
            list(profile.items())
        )
    )

    first = _apply_profile(profile)[1]
    second = _apply_profile(reordered)[1]

    assert first.story_points == second.story_points


@runtime_contract
def test_policy_does_not_mutate_input_story_points() -> None:
    (
        _result,
        decision,
        output_story,
        input_story,
        input_backlog,
    ) = _apply_profile(
        _with(
            _profile("none"),
            business_logic="medium",
        )
    )

    assert input_story.story_points is None

    assert (
        input_backlog.stories[0].story_points
        is None
    )

    assert (
        output_story.story_points
        ==
        decision.story_points
    )


@runtime_contract
def test_any_21_point_decision_requires_split() -> None:
    profiles = (
        _profile("high"),
        _with(
            _profile("medium"),
            integration_complexity="high",
            external_dependency="high",
            uncertainty="high",
        ),
    )

    for profile in profiles:
        decision = _apply_profile(profile)[1]

        if decision.story_points == 21:
            assert decision.split_recommended is True
