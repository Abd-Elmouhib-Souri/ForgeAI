from __future__ import annotations

from app.schemas.project_management import (
    CandidateComplexityFactorsV1,
    CanonicalBacklogV1,
    CanonicalUserStoryV1,
    ProjectManagementContextV1,
)

from app.services.sprint_cadence_advisor import (
    SprintCadenceAdvisor,
    SprintCadencePolicyV1,
)


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


def _factors(
    **changes,
):

    payload = {
        name: "none"
        for name
        in FACTOR_NAMES
    }

    payload.update(
        changes
    )

    return CandidateComplexityFactorsV1(
        **payload
    )


def _story(
    *,
    story_points: int = 5,
    **factor_changes,
):

    return CanonicalUserStoryV1.model_construct(
        story_id="US-001",
        candidate_complexity="advisory",
        candidate_complexity_rationale=(
            "advisory-only"
        ),
        candidate_complexity_factors=(
            _factors(
                **factor_changes
            )
        ),
        story_points=story_points,
    )


def _backlog(
    *stories,
):

    return CanonicalBacklogV1.model_construct(
        schema_version="canonical_backlog_v1",
        source_context_hash="src-cadence",
        context_hash="ctx-cadence",
        epics=[],
        features=[],
        stories=list(
            stories
        ),
        warnings=[],
    )


def _context(
    *,
    project_name: str = "A",
    industry: str = "generic",
    target_region: str = "R1",
    regulatory_flags=None,
    human_oversight=None,
    unknowns=None,
):

    return ProjectManagementContextV1.model_construct(
        project_name=project_name,
        industry=industry,
        target_region=target_region,
        regulatory_flags=list(
            regulatory_flags
            or []
        ),
        human_oversight=list(
            human_oversight
            or []
        ),
        unknowns=list(
            unknowns
            or []
        ),
        source_context_hash="src-cadence",
        context_hash="ctx-cadence",
    )


def _recommend(
    context,
    backlog,
    *,
    advisor=None,
):

    return (
        advisor
        or SprintCadenceAdvisor()
    ).recommend(
        context=context,
        backlog=backlog,
    )


def test_neutral_delivery_cycle_uses_standard_policy_cadence() -> None:

    result = _recommend(
        _context(),
        _backlog(
            _story()
        ),
    )

    assert (
        result.cadence_band
        ==
        "standard"
    )

    assert (
        result.recommended_sprint_duration_days
        ==
        14
    )


def test_high_uncertainty_with_low_validation_pressure_prefers_short_feedback_cycle() -> None:

    result = _recommend(
        _context(),
        _backlog(
            _story(
                uncertainty="high",
            )
        ),
    )

    assert (
        result.cadence_band
        ==
        "short"
    )

    assert (
        result.recommended_sprint_duration_days
        ==
        7
    )


def test_cross_boundary_validation_pressure_can_extend_cadence() -> None:

    result = _recommend(
        _context(),
        _backlog(
            _story(
                integration_complexity="high",
                external_dependency="high",
                testing_burden="medium",
            )
        ),
    )

    assert (
        result.cadence_band
        ==
        "extended"
    )

    assert (
        result.recommended_sprint_duration_days
        ==
        21
    )


def test_dense_validation_cycle_can_select_long_policy_cadence() -> None:

    result = _recommend(
        _context(
            regulatory_flags=[
                "explicit review required"
            ],
            human_oversight=[
                "human approval required"
            ],
        ),
        _backlog(
            _story(
                integration_complexity="high",
                external_dependency="high",
                testing_burden="high",
                regulatory_risk="high",
                hardware_dependency="high",
            )
        ),
    )

    assert (
        result.cadence_band
        ==
        "long"
    )

    assert (
        result.recommended_sprint_duration_days
        ==
        28
    )


def test_project_country_industry_and_name_do_not_control_cadence() -> None:

    backlog = _backlog(
        _story(
            external_dependency="medium",
            testing_burden="medium",
        )
    )

    first = _recommend(
        _context(
            project_name="Alpha",
            industry="retail",
            target_region="Tunisia",
        ),
        backlog,
    )

    second = _recommend(
        _context(
            project_name="Beta",
            industry="healthcare",
            target_region="Canada",
        ),
        backlog,
    )

    assert (
        first.recommended_sprint_duration_days
        ==
        second.recommended_sprint_duration_days
    )

    assert (
        first.cadence_band
        ==
        second.cadence_band
    )


def test_story_points_never_control_cadence() -> None:

    first = _recommend(
        _context(),
        _backlog(
            _story(
                story_points=1,
                uncertainty="high",
            )
        ),
    )

    second = _recommend(
        _context(),
        _backlog(
            _story(
                story_points=21,
                uncertainty="high",
            )
        ),
    )

    assert (
        first.recommended_sprint_duration_days
        ==
        second.recommended_sprint_duration_days
    )


def test_generic_business_difficulty_does_not_lengthen_cadence() -> None:

    baseline = _recommend(
        _context(),
        _backlog(
            _story()
        ),
    )

    difficult = _recommend(
        _context(),
        _backlog(
            _story(
                business_logic="high",
                data_complexity="high",
                ui_complexity="high",
                security="high",
            )
        ),
    )

    assert (
        difficult.recommended_sprint_duration_days
        ==
        baseline.recommended_sprint_duration_days
    )


def test_policy_durations_are_configurable_without_changing_semantics() -> None:

    advisor = SprintCadenceAdvisor(
        policy=SprintCadencePolicyV1(
            short_days=5,
            standard_days=10,
            extended_days=20,
            long_days=30,
        )
    )

    result = _recommend(
        _context(),
        _backlog(
            _story(
                uncertainty="high",
            )
        ),
        advisor=advisor,
    )

    assert (
        result.cadence_band
        ==
        "short"
    )

    assert (
        result.recommended_sprint_duration_days
        ==
        5
    )


def test_same_release_signals_are_deterministic() -> None:

    context = _context(
        regulatory_flags=[
            "review"
        ]
    )

    backlog = _backlog(
        _story(
            testing_burden="high",
            regulatory_risk="high",
        )
    )

    first = _recommend(
        context,
        backlog,
    )

    second = _recommend(
        context,
        backlog,
    )

    assert first == second
