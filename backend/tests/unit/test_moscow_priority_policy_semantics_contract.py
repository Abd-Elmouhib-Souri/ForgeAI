from __future__ import annotations

import importlib
import importlib.util

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
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


MODULE = "app.services.moscow_priority_policy"


def module_exists() -> bool:
    return importlib.util.find_spec(
        MODULE
    ) is not None


def skip_until_policy_exists() -> None:
    if not module_exists():
        pytest.skip(
            "MoSCoW semantics blocked by missing "
            "deterministic policy implementation."
        )


def policy_class():
    skip_until_policy_exists()

    module = importlib.import_module(
        MODULE
    )

    return getattr(
        module,
        "MoSCoWPriorityPolicy",
    )


def make_context():

    packet = ProjectContextPacketV3(
        project_name="Priority Semantics",
        language="en",
        target_region="International",
        industry_user_input=(
            "Operational workflow software"
        ),

        actors=[
            ActorContext(
                name="Operator",
                role=ActorRole.USER,
                is_explicit=True,
            ),

            ActorContext(
                name="Operations Manager",
                role=ActorRole.DECISION_MAKER,
                is_explicit=True,
            ),
        ],

        priority_workflows=[
            WorkflowContext(
                name="request_review",
                actor="Operator",
                action="review",
                object="request",
                result="decision recorded",
                is_explicit=True,
                confidence=1.0,
            ),
        ],

        mvp_scope=[
            "Request review",
        ],

        scope_exclusions=[
            "Automatic payment",
        ],
    )

    return (
        project_management_context_builder
        .build(
            packet=packet,
            project_id="priority-semantics",
            decision=None,
        )
    )


def make_story(
    context,
    *,
    story_id="US-001",
    provenance_refs=None,
    candidate_priority="must",
    title="Review request",
    story_text=None,
):

    refs = (
        list(provenance_refs)
        if provenance_refs is not None
        else [
            "actor:Operator",
            "workflow:request_review",
            "mvp_scope:Request review",
        ]
    )

    criterion = (
        CanonicalAcceptanceCriterionV1(
            acceptance_criterion_id=(
                "AC-"
                +
                story_id.split("-")[-1]
            ),

            story_id=story_id,

            statement=(
                "Given a valid request, "
                "when it is reviewed, "
                "then its outcome is recorded."
            ),

            is_testable=True,

            source_ref=(
                "workflow:request_review"
            ),
        )
    )

    return CanonicalUserStoryV1(
        story_id=story_id,
        candidate_key=(
            "candidate_"
            +
            story_id.lower()
        ),
        epic_id="EP-001",
        feature_id="FE-001",
        actor_ref="Operator",

        title=title,

        capability="Review request",

        benefit="record a decision",

        story=(
            story_text
            or
            (
                "As an Operator, I want to review "
                "a request so that a decision "
                "is recorded."
            )
        ),

        business_value=(
            "Support the validated workflow."
        ),

        acceptance_criteria=[
            criterion,
        ],

        candidate_priority=(
            candidate_priority
        ),

        candidate_priority_rationale=(
            "Advisory Product Owner signal."
        ),

        priority=None,

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "Advisory Product Owner estimate."
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

        provenance_refs=refs,

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )


def make_backlog(
    context,
    stories,
):

    epic = CanonicalEpicV1(
        epic_id="EP-001",
        candidate_key="candidate_epic",
        title="Operations",
        description=(
            "Support the validated workflow."
        ),
        business_goal=(
            "Support the validated outcome."
        ),
        provenance_refs=[
            "workflow:request_review",
        ],
    )

    feature = CanonicalFeatureV1(
        feature_id="FE-001",
        candidate_key="candidate_feature",
        epic_id="EP-001",
        title="Request Review",
        description=(
            "Support request review."
        ),
        business_value=(
            "Support the explicit MVP."
        ),

        # Deliberately contains MVP provenance.
        #
        # Story priority MUST use Story evidence,
        # not silently inherit stronger parent evidence.
        provenance_refs=[
            "mvp_scope:Request review",
        ],
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

        stories=list(
            stories
        ),

        warnings=[],
    )


def apply(
    context,
    backlog,
):

    return policy_class()().apply(
        context=context,
        backlog=backlog,
    )


def priority_for(
    refs,
    *,
    candidate_priority="must",
):

    context = make_context()

    story = make_story(
        context,
        provenance_refs=refs,
        candidate_priority=(
            candidate_priority
        ),
    )

    result = apply(
        context,
        make_backlog(
            context,
            [
                story,
            ],
        ),
    )

    return (
        result.backlog.stories[0],
        result.decisions[0],
        result,
    )


# ============================================================
# CORE V1 PRECEDENCE
# ============================================================


def test_workflow_plus_mvp_scope_is_must() -> None:

    story, decision, _ = priority_for(
        [
            "actor:Operator",
            "workflow:request_review",
            "mvp_scope:Request review",
        ]
    )

    assert story.priority == "Must"

    assert (
        "priority_workflow"
        in decision.reason_codes
    )

    assert (
        "mvp_requirement"
        in decision.reason_codes
    )


def test_workflow_without_mvp_binding_is_should() -> None:

    story, decision, _ = priority_for(
        [
            "actor:Operator",
            "workflow:request_review",
        ]
    )

    assert story.priority == "Should"

    assert (
        "priority_workflow"
        in decision.reason_codes
    )


def test_mvp_binding_without_workflow_is_should() -> None:

    story, decision, _ = priority_for(
        [
            "actor:Operator",
            "mvp_scope:Request review",
        ]
    )

    assert story.priority == "Should"

    assert (
        "mvp_requirement"
        in decision.reason_codes
    )


def test_supporting_actor_only_is_could() -> None:

    story, decision, _ = priority_for(
        [
            "actor:Operator",
        ]
    )

    assert story.priority == "Could"

    assert story.priority != "Won't"

    assert (
        "canonical_in_scope"
        in decision.reason_codes
    )


# ============================================================
# PARENT PROVENANCE MUST NOT SILENTLY ELEVATE STORY
# ============================================================


def test_parent_feature_mvp_provenance_does_not_elevate_actor_only_story() -> None:

    story, _, _ = priority_for(
        [
            "actor:Operator",
        ]
    )

    assert story.priority == "Could"


# ============================================================
# PRODUCT OWNER SIGNAL REMAINS NON-AUTHORITATIVE
# ============================================================


@pytest.mark.parametrize(
    "candidate_priority",
    (
        "must",
        "should",
        "could",
        "wont",
        "unexpected",
    ),
)
def test_candidate_priority_cannot_override_story_evidence(
    candidate_priority,
) -> None:

    story, _, _ = priority_for(
        [
            "actor:Operator",
            "workflow:request_review",
        ],

        candidate_priority=(
            candidate_priority
        ),
    )

    assert story.priority == "Should"


# ============================================================
# TEXT IS NOT PRIORITY AUTHORITY
# ============================================================


def test_story_text_paraphrase_does_not_change_priority() -> None:

    context = make_context()

    refs = [
        "actor:Operator",
        "workflow:request_review",
    ]

    first_story = make_story(
        context,
        provenance_refs=refs,
        title="Review request",
    )

    second_story = make_story(
        context,
        provenance_refs=refs,
        title=(
            "Process the operational request"
        ),
        story_text=(
            "As an Operator, I want the request "
            "processed so that the workflow "
            "outcome remains available."
        ),
    )

    first = apply(
        context,
        make_backlog(
            context,
            [
                first_story,
            ],
        ),
    )

    second = apply(
        context,
        make_backlog(
            context,
            [
                second_story,
            ],
        ),
    )

    assert (
        first.backlog.stories[0].priority
        ==
        second.backlog.stories[0].priority
        ==
        "Should"
    )


# ============================================================
# MUST OVERLOAD IS SOFT WARNING ONLY
# ============================================================


def test_must_overload_warns_without_forced_downgrade() -> None:

    context = make_context()

    stories = [
        make_story(
            context,
            story_id=(
                f"US-{index:03d}"
            ),
            provenance_refs=[
                "actor:Operator",
                "workflow:request_review",
                "mvp_scope:Request review",
            ],
        )
        for index in range(
            1,
            5,
        )
    ]

    result = apply(
        context,
        make_backlog(
            context,
            stories,
        ),
    )

    assert all(
        story.priority == "Must"
        for story
        in result.backlog.stories
    )

    assert result.must_ratio == 1.0

    assert (
        "must_overload"
        in result.warnings
    )


# ============================================================
# NO FALSE WON'T FOR CURRENT CANONICAL IN-SCOPE MODEL
# ============================================================


def test_in_scope_story_is_never_invented_as_wont() -> None:

    story, _, _ = priority_for(
        [
            "actor:Operator",
        ]
    )

    assert story.scope_status == "in_scope"

    assert story.priority != "Won't"