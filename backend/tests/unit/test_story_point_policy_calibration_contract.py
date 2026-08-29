from __future__ import annotations

from itertools import permutations

import pytest


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


SEVERITY_RANK = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}


UNKNOWN = "unknown"


TIER_BANDS = (
    (0, 0, "very_small", 1),
    (1, 5, "small", 2),
    (6, 10, "moderate", 3),
    (11, 15, "medium", 5),
    (16, 20, "large", 8),
    (21, 25, "very_large", 13),
    (26, 30, "extreme", 21),
)


def _profile(
    value: str,
) -> dict[str, str]:
    return {
        name: value
        for name in FACTOR_NAMES
    }


def _upper_bound_load(
    profile: dict[str, str],
) -> int:
    if set(profile) != set(FACTOR_NAMES):
        raise ValueError(
            "profile must contain exactly the ten factors"
        )

    known_count = sum(
        value != UNKNOWN
        for value in profile.values()
    )

    if known_count == 0:
        raise ValueError(
            "all complexity factors are unknown"
        )

    load = 0

    for value in profile.values():
        if value == UNKNOWN:
            # Conservative upper bound only.
            # The canonical value remains unknown.
            load += 3
            continue

        if value not in SEVERITY_RANK:
            raise ValueError(
                f"unsupported complexity signal: {value}"
            )

        load += SEVERITY_RANK[value]

    return load


def _story_points_for_load(
    load: int,
) -> int:
    for (
        minimum,
        maximum,
        _tier,
        story_points,
    ) in TIER_BANDS:
        if minimum <= load <= maximum:
            return story_points

    raise ValueError(
        f"load outside V1 calibration range: {load}"
    )


def _estimate(
    profile: dict[str, str],
) -> int:
    return _story_points_for_load(
        _upper_bound_load(
            profile
        )
    )


def test_calibration_has_exact_ten_factor_dimensions() -> None:
    assert len(FACTOR_NAMES) == 10
    assert len(set(FACTOR_NAMES)) == 10


def test_known_severity_encoding_is_equal_step_and_factor_neutral() -> None:
    assert SEVERITY_RANK == {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }


def test_tier_table_matches_fibonacci_qualitative_vocabulary() -> None:
    assert TIER_BANDS == (
        (0, 0, "very_small", 1),
        (1, 5, "small", 2),
        (6, 10, "moderate", 3),
        (11, 15, "medium", 5),
        (16, 20, "large", 8),
        (21, 25, "very_large", 13),
        (26, 30, "extreme", 21),
    )


def test_tier_table_covers_every_possible_known_load_exactly_once() -> None:
    covered = []

    for (
        minimum,
        maximum,
        _tier,
        _story_points,
    ) in TIER_BANDS:
        covered.extend(
            range(
                minimum,
                maximum + 1,
            )
        )

    assert covered == list(
        range(31)
    )


def test_story_points_are_monotonic_over_complete_load_range() -> None:
    outputs = [
        _story_points_for_load(load)
        for load in range(31)
    ]

    assert outputs == sorted(
        outputs
    )


def test_uniform_known_profiles_have_explicit_v1_calibration() -> None:
    assert _estimate(
        _profile("none")
    ) == 1

    assert _estimate(
        _profile("low")
    ) == 3

    assert _estimate(
        _profile("medium")
    ) == 8

    assert _estimate(
        _profile("high")
    ) == 21


def test_partial_unknown_uses_conservative_upper_bound_not_none() -> None:
    baseline = _profile("none")

    one_unknown = dict(
        baseline
    )

    one_unknown[
        "external_dependency"
    ] = UNKNOWN

    assert (
        _upper_bound_load(
            baseline
        )
        ==
        0
    )

    assert (
        _upper_bound_load(
            one_unknown
        )
        ==
        3
    )

    assert _estimate(
        baseline
    ) == 1

    assert _estimate(
        one_unknown
    ) == 2


def test_unknown_is_not_rewritten_as_a_known_signal() -> None:
    profile = _profile("none")

    profile[
        "security"
    ] = UNKNOWN

    before = dict(
        profile
    )

    _upper_bound_load(
        profile
    )

    assert profile == before
    assert profile["security"] == UNKNOWN


def test_all_unknown_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="all complexity factors are unknown",
    ):
        _upper_bound_load(
            _profile(
                UNKNOWN
            )
        )


def test_increasing_known_severity_cannot_reduce_story_points() -> None:
    signals = (
        "none",
        "low",
        "medium",
        "high",
    )

    for factor in FACTOR_NAMES:
        outputs = []

        for signal in signals:
            profile = _profile(
                "none"
            )

            profile[
                factor
            ] = signal

            outputs.append(
                _estimate(
                    profile
                )
            )

        assert outputs == sorted(
            outputs
        ), (
            factor,
            outputs,
        )


def test_factor_identity_has_no_hidden_weight() -> None:
    outputs = set()

    for factor in FACTOR_NAMES:
        profile = _profile(
            "none"
        )

        profile[
            factor
        ] = "high"

        outputs.add(
            _estimate(
                profile
            )
        )

    assert len(outputs) == 1


def test_factor_representation_order_cannot_change_calibration() -> None:
    values = (
        "high",
        "medium",
        "low",
        "none",
        "none",
        "none",
        "none",
        "none",
        "none",
        "none",
    )

    baseline_profile = dict(
        zip(
            FACTOR_NAMES,
            values,
            strict=True,
        )
    )

    expected = _estimate(
        baseline_profile
    )

    sample_orders = (
        FACTOR_NAMES,
        tuple(
            reversed(
                FACTOR_NAMES
            )
        ),
        (
            FACTOR_NAMES[3],
            FACTOR_NAMES[7],
            FACTOR_NAMES[1],
            FACTOR_NAMES[9],
            FACTOR_NAMES[0],
            FACTOR_NAMES[5],
            FACTOR_NAMES[2],
            FACTOR_NAMES[8],
            FACTOR_NAMES[4],
            FACTOR_NAMES[6],
        ),
    )

    for order in sample_orders:
        reordered = {
            name: baseline_profile[name]
            for name in order
        }

        assert (
            _estimate(
                reordered
            )
            ==
            expected
        )


@pytest.mark.parametrize(
    (
        "load",
        "expected",
    ),
    (
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
    ),
)
def test_every_calibration_boundary_is_explicit(
    load: int,
    expected: int,
) -> None:
    assert (
        _story_points_for_load(
            load
        )
        ==
        expected
    )


def test_twenty_one_is_the_only_extreme_tier_output() -> None:
    extreme_rows = [
        row
        for row in TIER_BANDS
        if row[2] == "extreme"
    ]

    assert extreme_rows == [
        (
            26,
            30,
            "extreme",
            21,
        )
    ]
