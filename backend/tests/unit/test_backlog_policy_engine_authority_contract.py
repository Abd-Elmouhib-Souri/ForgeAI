from __future__ import annotations

import importlib
import importlib.util
import inspect

import pytest

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
    WorkflowContext,
)
from app.schemas.project_management import (
    CandidateAcceptanceCriterionV1,
    CandidateBacklogV1,
    CandidateEpicV1,
    CandidateFeatureV1,
    CandidateUserStoryV1,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


MODULE_NAME = (
    "app.services.backlog_policy_engine"
)


def module_exists() -> bool:
    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def module():
    return importlib.import_module(
        MODULE_NAME
    )


def skip_until_policy_exists() -> None:
    if not module_exists():
        pytest.skip(
            "Blocked by missing deterministic "
            "BacklogPolicyEngine."
        )


def engine_class():
    skip_until_policy_exists()

    return getattr(
        module(),
        "BacklogPolicyEngine",
    )


def result_class():
    skip_until_policy_exists()

    return getattr(
        module(),
        "BacklogPolicyResultV1",
    )


def engine():
    return engine_class()()


def pm_context():

    packet = ProjectContextPacketV3(
        project_name=(
            "Backlog Policy Contract"
        ),

        language="en",

        target_region="International",

        industry_user_input=(
            "B2B workflow software"
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
            "Automatic payments",
        ],
    )

    return (
        project_management_context_builder.build(
            packet=packet,
            project_id="backlog-policy-contract",
            decision=None,
        )
    )


def epic(
    *,
    key="epic_operations",
):

    return CandidateEpicV1(
        candidate_key=key,

        title="Core Operations",

        description=(
            "Support the validated workflow."
        ),

        business_goal=(
            "Complete the primary workflow."
        ),

        provenance_refs=[
            "workflow:request_review",
        ],
    )


def feature(
    *,
    key="feature_request_review",
    epic_key="epic_operations",
):

    return CandidateFeatureV1(
        candidate_key=key,

        epic_key=epic_key,

        title="Request review",

        description=(
            "Review incoming requests."
        ),

        business_value=(
            "Reduce processing delays."
        ),

        provenance_refs=[
            "mvp_scope:Request review",
        ],
    )


def story(
    context,
    *,
    key="story_review_request",
    epic_key="epic_operations",
    feature_key="feature_request_review",
    actor_ref="Operator",
    story_text=None,
    candidate_dependencies=None,
    acceptance_testable=True,
):

    return CandidateUserStoryV1(
        candidate_key=key,

        epic_key=epic_key,

        feature_key=feature_key,

        actor_ref=actor_ref,

        title="Review request",

        capability=(
            "review an incoming request"
        ),

        benefit=(
            "reduce processing delays"
        ),

        story=(
            story_text
            or
            (
                "As an Operator, I want to review "
                "an incoming request so that "
                "processing delays are reduced."
            )
        ),

        business_value=(
            "Faster request processing."
        ),

        acceptance_criteria=[
            CandidateAcceptanceCriterionV1(
                statement=(
                    "Given a pending request, "
                    "when the Operator reviews it, "
                    "then the decision is recorded."
                ),

                candidate_testable=(
                    acceptance_testable
                ),

                source_ref=(
                    "workflow:request_review"
                ),
            ),
        ],

        candidate_priority="must",

        candidate_priority_rationale=(
            "Required by the primary workflow."
        ),

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "Requires workflow state handling."
        ),

        candidate_dependencies=(
            candidate_dependencies
            if candidate_dependencies is not None
            else []
        ),

        provenance_refs=[
            "actor:Operator",
            "workflow:request_review",
        ],

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )


def candidate(
    context,
    *,
    epics=None,
    features=None,
    stories=None,
):

    return CandidateBacklogV1(
        source_context_hash=(
            context.source_context_hash
        ),

        context_hash=(
            context.context_hash
        ),

        epics=(
            epics
            if epics is not None
            else [
                epic(),
            ]
        ),

        features=(
            features
            if features is not None
            else [
                feature(),
            ]
        ),

        stories=(
            stories
            if stories is not None
            else [
                story(
                    context
                ),
            ]
        ),

        warnings=[],
    )


def evaluate(
    context,
    value,
):
    return engine().evaluate(
        context=context,
        candidate=value,
    )


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_backlog_policy_engine_module_exists() -> None:

    assert module_exists(), (
        "Missing deterministic Sprint 4 "
        "BacklogPolicyEngine: "
        "app.services.backlog_policy_engine"
    )


# ============================================================
# PUBLIC API
# ============================================================


def test_backlog_policy_engine_class_exists() -> None:

    skip_until_policy_exists()

    assert hasattr(
        module(),
        "BacklogPolicyEngine",
    )


def test_backlog_policy_result_model_exists() -> None:

    skip_until_policy_exists()

    assert hasattr(
        module(),
        "BacklogPolicyResultV1",
    )


def test_backlog_policy_engine_has_narrow_api() -> None:

    skip_until_policy_exists()

    signature = inspect.signature(
        engine_class().evaluate
    )

    assert set(
        signature.parameters
    ) == {
        "self",
        "context",
        "candidate",
    }

    forbidden = {
        "analysis_data",
        "debate_room",
        "startup_score",
        "final_report",
        "evidence_ledger",
        "project_intelligence",
        "search_results",
        "queries",
        "query_plan",
        "rag_context",
        "archetype_context",
    }

    assert not (
        forbidden
        &
        set(
            signature.parameters
        )
    )


def test_policy_result_is_validation_only_not_planning_authority() -> None:

    skip_until_policy_exists()

    fields = set(
        result_class().model_fields
    )

    required = {
        "schema_version",
        "is_valid",
        "error_codes",
        "errors",
        "warnings",
    }

    assert not (
        required
        -
        fields
    )

    forbidden = {
        "priority",
        "story_points",
        "sprints",
        "sprint_number",
        "canonical_backlog",
        "canonical_ids",
        "locked_stories",
        "architecture",
        "tech_stack",
        "database_schema",
    }

    assert not (
        forbidden
        &
        fields
    )


# ============================================================
# VALID BACKLOG
# ============================================================


def test_valid_candidate_passes_policy() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context
        ),
    )

    assert result.is_valid is True
    assert result.error_codes == []


def test_policy_is_deterministic() -> None:

    skip_until_policy_exists()

    context = pm_context()

    value = candidate(
        context
    )

    first = evaluate(
        context,
        value,
    )

    second = evaluate(
        context.model_copy(
            deep=True
        ),
        value.model_copy(
            deep=True
        ),
    )

    assert first == second


def test_policy_does_not_mutate_context_or_candidate() -> None:

    skip_until_policy_exists()

    context = pm_context()

    value = candidate(
        context
    )

    before_context = context.model_dump(
        mode="json"
    )

    before_candidate = value.model_dump(
        mode="json"
    )

    evaluate(
        context,
        value,
    )

    assert (
        context.model_dump(
            mode="json"
        )
        ==
        before_context
    )

    assert (
        value.model_dump(
            mode="json"
        )
        ==
        before_candidate
    )


# ============================================================
# CANDIDATE AUTHORITY IS A MANDATORY PRECONDITION
# ============================================================


def test_policy_rejects_candidate_with_wrong_context_hash() -> None:

    skip_until_policy_exists()

    context = pm_context()

    value = candidate(
        context
    ).model_copy(
        update={
            "context_hash":
                "f" * 64,
        },
        deep=True,
    )

    result = evaluate(
        context,
        value,
    )

    assert result.is_valid is False

    assert (
        "candidate_authority_rejected"
        in result.error_codes
    )


def test_policy_rejects_candidate_with_unknown_actor() -> None:

    skip_until_policy_exists()

    context = pm_context()

    value = candidate(
        context,
        stories=[
            story(
                context,
                actor_ref="Invented CFO",
            ),
        ],
    )

    result = evaluate(
        context,
        value,
    )

    assert result.is_valid is False

    assert (
        "candidate_authority_rejected"
        in result.error_codes
    )


# ============================================================
# UNIQUE CANDIDATE KEYS
# ============================================================


def test_duplicate_epic_key_is_rejected() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            epics=[
                epic(),
                epic(),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "duplicate_epic_key"
        in result.error_codes
    )


def test_duplicate_feature_key_is_rejected() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            features=[
                feature(),
                feature(),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "duplicate_feature_key"
        in result.error_codes
    )


def test_duplicate_story_key_is_rejected() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context
                ),
                story(
                    context
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "duplicate_story_key"
        in result.error_codes
    )


# ============================================================
# HIERARCHY
# ============================================================


def test_feature_requires_existing_parent_epic() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            features=[
                feature(
                    epic_key="missing_epic",
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "missing_parent_epic"
        in result.error_codes
    )


def test_story_requires_existing_parent_epic() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context,
                    epic_key="missing_epic",
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "missing_parent_epic"
        in result.error_codes
    )


def test_story_requires_existing_parent_feature() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context,
                    feature_key=(
                        "missing_feature"
                    ),
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "missing_parent_feature"
        in result.error_codes
    )


def test_story_epic_must_match_feature_epic() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            epics=[
                epic(
                    key="epic_operations",
                ),
                epic(
                    key="epic_other",
                ),
            ],

            features=[
                feature(
                    key="feature_request_review",
                    epic_key="epic_operations",
                ),
            ],

            stories=[
                story(
                    context,
                    epic_key="epic_other",
                    feature_key=(
                        "feature_request_review"
                    ),
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "story_epic_feature_mismatch"
        in result.error_codes
    )


# ============================================================
# DEPENDENCY TARGET EXISTENCE
# ============================================================


def test_story_dependency_must_reference_existing_story() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context,
                    candidate_dependencies=[
                        "missing_story",
                    ],
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "unknown_dependency_target"
        in result.error_codes
    )


def test_story_cannot_depend_on_itself() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context,
                    key="story_review_request",
                    candidate_dependencies=[
                        "story_review_request",
                    ],
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "self_dependency"
        in result.error_codes
    )


# ============================================================
# ACCEPTANCE POLICY
# ============================================================


def test_story_requires_at_least_one_testable_acceptance_criterion() -> None:

    skip_until_policy_exists()

    context = pm_context()

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context,
                    acceptance_testable=False,
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "untestable_acceptance_criteria"
        in result.error_codes
    )


# ============================================================
# EXACT SEMANTIC DUPLICATION
# ============================================================


def test_normalized_duplicate_story_semantics_are_rejected() -> None:

    skip_until_policy_exists()

    context = pm_context()

    base_story = (
        "As an Operator, I want to review "
        "an incoming request so that "
        "processing delays are reduced."
    )

    reformatted_story = (
        "  AS AN OPERATOR,   I WANT TO REVIEW "
        "AN INCOMING REQUEST SO THAT "
        "PROCESSING DELAYS ARE REDUCED.  "
    )

    result = evaluate(
        context,
        candidate(
            context,
            stories=[
                story(
                    context,
                    key="story_review_request",
                    story_text=base_story,
                ),

                story(
                    context,
                    key="story_review_request_copy",
                    story_text=reformatted_story,
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "duplicate_story_semantics"
        in result.error_codes
    )


# ============================================================
# AUTHORITY BOUNDARY
# ============================================================


@pytest.mark.parametrize(
    "forbidden_name",
    (
        "assign_priority",
        "assign_story_points",
        "assign_sprint",
        "plan_sprints",
        "calculate_velocity",
        "calculate_burndown",
        "build_architecture",
    ),
)
def test_policy_engine_does_not_expose_later_policy_authorities(
    forbidden_name,
) -> None:

    skip_until_policy_exists()

    assert not hasattr(
        engine_class(),
        forbidden_name,
    )