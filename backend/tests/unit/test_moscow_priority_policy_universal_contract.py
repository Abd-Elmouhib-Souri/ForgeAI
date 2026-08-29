from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
    WorkflowContext,
)
from app.schemas.project_management import (
    CanonicalAcceptanceCriterionV1,
    CanonicalBacklogV1,
    CanonicalEpicV1,
    CanonicalFeatureV1,
    CanonicalUserStoryV1,
)
from app.services.moscow_priority_policy import (
    MoSCoWPriorityPolicy,
    MoSCoWPriorityPolicyError,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


PROJECT_VARIANTS = (
    {
        "case_id": "logistics_tunisia_en",
        "language": "en",
        "region": "Tunisia",
        "industry": "Warehouse operations",
        "actor": "Dock Operator",
        "workflow": "review_slot",
        "mvp": "Appointment review",
    },
    {
        "case_id": "healthcare_france_fr",
        "language": "fr",
        "region": "France",
        "industry": "Healthcare scheduling",
        "actor": "Coordinateur",
        "workflow": "review_booking",
        "mvp": "Validation rendez-vous",
    },
    {
        "case_id": "maintenance_germany_en",
        "language": "en",
        "region": "Germany",
        "industry": "Industrial maintenance",
        "actor": "Technician",
        "workflow": "inspect_asset",
        "mvp": "Asset inspection",
    },
    {
        "case_id": "education_canada_fr",
        "language": "fr",
        "region": "Canada",
        "industry": "Education administration",
        "actor": "Agent",
        "workflow": "review_application",
        "mvp": "Validation dossier",
    },
)


SCENARIOS = (
    (
        "workflow_and_mvp",
        "Must",
    ),
    (
        "workflow_only",
        "Should",
    ),
    (
        "mvp_only",
        "Should",
    ),
    (
        "support_only",
        "Could",
    ),
)


def make_context(
    variant,
):

    packet = ProjectContextPacketV3(
        project_name=(
            "Universal Priority "
            + variant["case_id"]
        ),

        language=(
            variant["language"]
        ),

        target_region=(
            variant["region"]
        ),

        industry_user_input=(
            variant["industry"]
        ),

        actors=[
            ActorContext(
                name=variant["actor"],
                role=ActorRole.USER,
                is_explicit=True,
            ),

            ActorContext(
                name="Decision Maker",
                role=ActorRole.DECISION_MAKER,
                is_explicit=True,
            ),
        ],

        priority_workflows=[
            WorkflowContext(
                name=variant["workflow"],
                actor=variant["actor"],
                action="review",
                object="item",
                result="decision recorded",
                is_explicit=True,
                confidence=1.0,
            ),
        ],

        mvp_scope=[
            variant["mvp"],
        ],

        scope_exclusions=[
            "Autonomous irreversible decision",
        ],
    )

    return (
        project_management_context_builder
        .build(
            packet=packet,
            project_id=(
                "universal-"
                + variant["case_id"]
            ),
            decision=None,
        )
    )


def refs_for(
    variant,
    scenario,
):

    actor_ref = (
        "actor:"
        + variant["actor"]
    )

    workflow_ref = (
        "workflow:"
        + variant["workflow"]
    )

    mvp_ref = (
        "mvp_scope:"
        + variant["mvp"]
    )

    if scenario == "workflow_and_mvp":

        return [
            actor_ref,
            workflow_ref,
            mvp_ref,
        ]

    if scenario == "workflow_only":

        return [
            actor_ref,
            workflow_ref,
        ]

    if scenario == "mvp_only":

        return [
            actor_ref,
            mvp_ref,
        ]

    if scenario == "support_only":

        return [
            actor_ref,
        ]

    raise AssertionError(
        scenario
    )


def make_backlog(
    context,
    variant,
    refs,
    *,
    input_priority=None,
):

    source_ref = (
        refs[0]
        if refs
        else (
            "actor:"
            + variant["actor"]
        )
    )

    criterion = (
        CanonicalAcceptanceCriterionV1(
            acceptance_criterion_id="AC-001",
            story_id="US-001",

            statement=(
                "Given a valid item, "
                "when the action is completed, "
                "then the result is recorded."
            ),

            is_testable=True,

            source_ref=source_ref,
        )
    )

    epic = CanonicalEpicV1(
        epic_id="EP-001",
        candidate_key="candidate_epic",
        title="Operations",
        description="Support canonical work.",
        business_goal="Support project outcome.",
        provenance_refs=[
            (
                "actor:"
                + variant["actor"]
            ),
        ],
    )

    feature = CanonicalFeatureV1(
        feature_id="FE-001",
        candidate_key="candidate_feature",
        epic_id="EP-001",
        title="Operational capability",
        description="Support canonical operation.",
        business_value="Support validated scope.",

        # Deliberately neutral parent evidence.
        provenance_refs=[
            (
                "actor:"
                + variant["actor"]
            ),
        ],
    )

    story = CanonicalUserStoryV1(
        story_id="US-001",
        candidate_key="candidate_story",
        epic_id="EP-001",
        feature_id="FE-001",

        actor_ref=(
            variant["actor"]
        ),

        title="Perform operation",
        capability="Perform operation",
        benefit="record the expected result",

        story=(
            "As an operational user, "
            "I want to perform the operation "
            "so that its result is recorded."
        ),

        business_value=(
            "Support validated scope."
        ),

        acceptance_criteria=[
            criterion,
        ],

        candidate_priority="must",

        candidate_priority_rationale=(
            "Advisory only."
        ),

        priority=input_priority,

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "Advisory only."
        ),

        candidate_complexity_factors={
            'business_logic': 'unknown',
            'integration_complexity': 'unknown',
            'data_complexity': 'unknown',
            'ui_complexity': 'unknown',
            'security': 'unknown',
            'external_dependency': 'unknown',
            'uncertainty': 'unknown',
            'testing_burden': 'unknown',
            'regulatory_risk': 'unknown',
            'hardware_dependency': 'unknown',
        },
        story_points=None,

        dependencies=[],

        dependency_hint_ids=[],

        scope_status="in_scope",

        locked=False,

        provenance_refs=list(
            refs
        ),

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )

    return CanonicalBacklogV1(
        source_context_hash=(
            context.source_context_hash
        ),

        context_hash=(
            context.context_hash
        ),

        epics=[
            epic,
        ],

        features=[
            feature,
        ],

        stories=[
            story,
        ],

        warnings=[],
    )


def apply(
    context,
    backlog,
):

    return MoSCoWPriorityPolicy().apply(
        context=context,
        backlog=backlog,
    )


@pytest.mark.parametrize(
    "variant",
    PROJECT_VARIANTS,
    ids=[
        item["case_id"]
        for item
        in PROJECT_VARIANTS
    ],
)
@pytest.mark.parametrize(
    "scenario,expected",
    SCENARIOS,
    ids=[
        item[0]
        for item
        in SCENARIOS
    ],
)
def test_priority_semantics_are_cross_domain_country_and_language_invariant(
    variant,
    scenario,
    expected,
) -> None:

    context = make_context(
        variant
    )

    backlog = make_backlog(
        context,
        variant,
        refs_for(
            variant,
            scenario,
        ),
    )

    result = apply(
        context,
        backlog,
    )

    assert (
        result.backlog.stories[0].priority
        ==
        expected
    )


def test_query_and_archetype_refs_cannot_elevate_priority() -> None:

    variant = PROJECT_VARIANTS[0]

    context = make_context(
        variant
    )

    refs = [
        (
            "actor:"
            + variant["actor"]
        ),
        "query:marketplace scheduling",
        "archetype:two_sided_marketplace",
        "search:workforce platform",
    ]

    result = apply(
        context,
        make_backlog(
            context,
            variant,
            refs,
        ),
    )

    assert (
        result.backlog.stories[0].priority
        ==
        "Could"
    )


def test_provenance_order_does_not_change_priority() -> None:

    variant = PROJECT_VARIANTS[1]

    context = make_context(
        variant
    )

    workflow_ref = (
        "workflow:"
        + variant["workflow"]
    )

    mvp_ref = (
        "mvp_scope:"
        + variant["mvp"]
    )

    actor_ref = (
        "actor:"
        + variant["actor"]
    )

    first = apply(
        context,
        make_backlog(
            context,
            variant,
            [
                actor_ref,
                workflow_ref,
                mvp_ref,
            ],
        ),
    )

    second = apply(
        context,
        make_backlog(
            context,
            variant,
            [
                mvp_ref,
                actor_ref,
                workflow_ref,
            ],
        ),
    )

    assert (
        first.backlog.stories[0].priority
        ==
        second.backlog.stories[0].priority
        ==
        "Must"
    )


def test_duplicate_provenance_does_not_change_priority() -> None:

    variant = PROJECT_VARIANTS[2]

    context = make_context(
        variant
    )

    workflow_ref = (
        "workflow:"
        + variant["workflow"]
    )

    mvp_ref = (
        "mvp_scope:"
        + variant["mvp"]
    )

    result = apply(
        context,
        make_backlog(
            context,
            variant,
            [
                workflow_ref,
                workflow_ref,
                mvp_ref,
                mvp_ref,
            ],
        ),
    )

    assert (
        result.backlog.stories[0].priority
        ==
        "Must"
    )

    assert (
        len(
            result.decisions[0].evidence_refs
        )
        ==
        2
    )


def test_policy_is_idempotent() -> None:

    variant = PROJECT_VARIANTS[0]

    context = make_context(
        variant
    )

    backlog = make_backlog(
        context,
        variant,
        refs_for(
            variant,
            "workflow_and_mvp",
        ),
    )

    first = apply(
        context,
        backlog,
    )

    second = apply(
        context,
        first.backlog,
    )

    assert first == second


def test_empty_backlog_is_stable() -> None:

    variant = PROJECT_VARIANTS[3]

    context = make_context(
        variant
    )

    populated = make_backlog(
        context,
        variant,
        refs_for(
            variant,
            "workflow_only",
        ),
    )

    empty = populated.model_copy(
        update={
            "stories": [],
        },
        deep=True,
    )

    result = apply(
        context,
        empty,
    )

    assert result.decisions == []

    assert result.must_ratio == 0.0

    assert result.warnings == []

    assert result.backlog.stories == []


def test_story_source_hash_mismatch_fails_closed() -> None:

    variant = PROJECT_VARIANTS[0]

    context = make_context(
        variant
    )

    backlog = make_backlog(
        context,
        variant,
        refs_for(
            variant,
            "workflow_only",
        ),
    )

    stale_story = (
        backlog.stories[0]
        .model_copy(
            update={
                "source_context_hash":
                    "d" * 64,
            },
            deep=True,
        )
    )

    stale = backlog.model_copy(
        update={
            "stories": [
                stale_story,
            ],
        },
        deep=True,
    )

    with pytest.raises(
        MoSCoWPriorityPolicyError
    ) as exc:

        apply(
            context,
            stale,
        )

    assert (
        exc.value.code
        ==
        "source_context_hash_mismatch"
    )


def test_preexisting_priority_does_not_compete_with_policy_authority() -> None:

    variant = PROJECT_VARIANTS[0]

    context = make_context(
        variant
    )

    backlog = make_backlog(
        context,
        variant,
        refs_for(
            variant,
            "workflow_and_mvp",
        ),
        input_priority="Won't",
    )

    result = apply(
        context,
        backlog,
    )

    assert (
        result.backlog.stories[0].priority
        ==
        "Must"
    )