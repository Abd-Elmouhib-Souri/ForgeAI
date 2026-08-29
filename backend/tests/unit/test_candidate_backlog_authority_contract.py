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
from app.services.project_management_decision_projector import (
    project_management_decision_projector,
)


MODULE_NAME = (
    "app.services."
    "candidate_backlog_authority"
)


def module_exists() -> bool:

    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def skip_until_authority_exists() -> None:

    if not module_exists():

        pytest.skip(
            "Blocked by deterministic "
            "CandidateBacklog authority validator."
        )


def authority_module():

    return importlib.import_module(
        MODULE_NAME
    )


def validator():

    loaded = authority_module()

    singleton = getattr(
        loaded,
        "candidate_backlog_authority_validator",
        None,
    )

    if singleton is not None:
        return singleton

    cls = getattr(
        loaded,
        "CandidateBacklogAuthorityValidator",
    )

    return cls()


def pm_context():

    packet = ProjectContextPacketV3(
        project_name=(
            "Candidate Authority Probe"
        ),

        language="en",

        target_region=(
            "International"
        ),

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

        constraints=[
            (
                "The system must not expose "
                "confidential data."
            ),
        ],
    )

    decision = (
        project_management_decision_projector.project(
            debate_judge={
                "status": "completed",

                "verdict_code": (
                    "conditional_go"
                ),

                "critical_risks": [
                    (
                        "Retention remains "
                        "unvalidated."
                    ),
                ],

                "next_actions": [
                    "Run bounded pilot",
                ],

                "go_no_go_conditions": [
                    (
                        "GO if repeated use "
                        "is observed."
                    ),
                ],

                "final_recommendation": (
                    "Run a bounded pilot."
                ),
            }
        )
    )

    return (
        project_management_context_builder.build(
            packet=packet,
            project_id="authority-probe",
            decision=decision,
        )
    )


def criterion(
    source_ref=(
        "workflow:request_review"
    ),
):

    return (
        CandidateAcceptanceCriterionV1(
            statement=(
                "Given a pending request, "
                "when the Operator reviews it, "
                "then the result is recorded."
            ),

            candidate_testable=True,

            source_ref=source_ref,
        )
    )


def epic(
    *,
    provenance_refs=None,
):

    return CandidateEpicV1(
        candidate_key="epic_operations",

        title="Core Operations",

        description=(
            "Support the validated operation."
        ),

        business_goal=(
            "Complete the primary workflow."
        ),

        provenance_refs=(
            provenance_refs
            if provenance_refs is not None
            else [
                "workflow:request_review",
            ]
        ),
    )


def feature(
    *,
    provenance_refs=None,
):

    return CandidateFeatureV1(
        candidate_key=(
            "feature_request_review"
        ),

        epic_key="epic_operations",

        title="Request review",

        description=(
            "Review incoming requests."
        ),

        business_value=(
            "Reduce processing delay."
        ),

        provenance_refs=(
            provenance_refs
            if provenance_refs is not None
            else [
                "mvp_scope:Request review",
            ]
        ),
    )


def story(
    context,
    *,
    actor_ref="Operator",
    provenance_refs=None,
    source_context_hash=None,
    acceptance_source_ref=(
        "workflow:request_review"
    ),
):

    return CandidateUserStoryV1(
        candidate_key=(
            "story_review_request"
        ),

        epic_key="epic_operations",

        feature_key=(
            "feature_request_review"
        ),

        actor_ref=actor_ref,

        title=(
            "Review incoming request"
        ),

        capability=(
            "review an incoming request"
        ),

        benefit=(
            "reduce processing delays"
        ),

        story=(
            "As an Operator, I want to review "
            "an incoming request so that "
            "processing delays are reduced."
        ),

        business_value=(
            "Faster operational processing."
        ),

        acceptance_criteria=[
            criterion(
                acceptance_source_ref
            ),
        ],

        candidate_priority="must",

        candidate_priority_rationale=(
            "Required by the primary workflow."
        ),

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "Requires workflow-state handling."
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
        candidate_dependencies=[],

        provenance_refs=(
            provenance_refs
            if provenance_refs is not None
            else [
                "actor:Operator",
                "workflow:request_review",
            ]
        ),

        source_context_hash=(
            source_context_hash
            if source_context_hash is not None
            else context.source_context_hash
        ),

        warnings=[],
    )


def candidate(
    context,
    *,
    source_context_hash=None,
    context_hash=None,
    epic_provenance=None,
    feature_provenance=None,
    story_provenance=None,
    actor_ref="Operator",
    story_source_context_hash=None,
    acceptance_source_ref=(
        "workflow:request_review"
    ),
):

    return CandidateBacklogV1(
        source_context_hash=(
            source_context_hash
            if source_context_hash is not None
            else context.source_context_hash
        ),

        context_hash=(
            context_hash
            if context_hash is not None
            else context.context_hash
        ),

        epics=[
            epic(
                provenance_refs=(
                    epic_provenance
                ),
            ),
        ],

        features=[
            feature(
                provenance_refs=(
                    feature_provenance
                ),
            ),
        ],

        stories=[
            story(
                context,
                actor_ref=actor_ref,
                provenance_refs=(
                    story_provenance
                ),
                source_context_hash=(
                    story_source_context_hash
                ),
                acceptance_source_ref=(
                    acceptance_source_ref
                ),
            ),
        ],

        warnings=[],
    )


def validate(
    context,
    value,
):

    return validator().validate(
        context=context,
        candidate=value,
    )


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_candidate_backlog_authority_module_exists() -> None:

    assert module_exists(), (
        "Missing deterministic Sprint 4 "
        "CandidateBacklog authority validator: "
        "app.services.candidate_backlog_authority"
    )


# ============================================================
# NARROW AUTHORITY API
# ============================================================


def test_authority_validator_has_narrow_api() -> None:

    skip_until_authority_exists()

    signature = inspect.signature(
        validator().validate
    )

    parameters = set(
        signature.parameters
    )

    assert parameters == {
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
        parameters
    )


# ============================================================
# VALID CANONICAL BINDING
# ============================================================


def test_valid_candidate_is_accepted() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context
        ),
    )

    assert result.is_valid is True
    assert result.error_codes == []


def test_validation_is_deterministic() -> None:

    skip_until_authority_exists()

    context = pm_context()
    value = candidate(
        context
    )

    first = validate(
        context,
        value,
    )

    second = validate(
        context.model_copy(
            deep=True
        ),
        value.model_copy(
            deep=True
        ),
    )

    assert first == second


# ============================================================
# HASH AUTHORITY
# ============================================================


def test_backlog_source_context_hash_must_match_pm_context() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context,
            source_context_hash=(
                "f"
                *
                64
            ),
        ),
    )

    assert result.is_valid is False

    assert (
        "source_context_hash_mismatch"
        in result.error_codes
    )


def test_backlog_context_hash_must_match_pm_context() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context,
            context_hash=(
                "e"
                *
                64
            ),
        ),
    )

    assert result.is_valid is False

    assert (
        "context_hash_mismatch"
        in result.error_codes
    )


def test_every_story_source_hash_must_match_pm_context() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context,
            story_source_context_hash=(
                "d"
                *
                64
            ),
        ),
    )

    assert result.is_valid is False

    assert (
        "story_source_context_hash_mismatch"
        in result.error_codes
    )


# ============================================================
# ACTOR AUTHORITY
# ============================================================


def test_story_actor_ref_must_resolve_to_canonical_actor() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context,
            actor_ref="Invented CFO",
        ),
    )

    assert result.is_valid is False

    assert (
        "unknown_actor_ref"
        in result.error_codes
    )


def test_known_non_primary_actor_can_still_resolve() -> None:

    skip_until_authority_exists()

    context = pm_context()

    value = candidate(
        context,
        actor_ref=(
            "Operations Manager"
        ),
        story_provenance=[
            (
                "actor:"
                "Operations Manager"
            ),
            "workflow:request_review",
        ],
    )

    result = validate(
        context,
        value,
    )

    assert (
        "unknown_actor_ref"
        not in result.error_codes
    )


# ============================================================
# PROVENANCE RESOLUTION
# ============================================================


@pytest.mark.parametrize(
    (
        "location",
        "unknown_ref",
    ),
    (
        (
            "epic",
            "workflow:not_real",
        ),
        (
            "feature",
            "mvp_scope:not_real",
        ),
        (
            "story",
            "actor:Imaginary User",
        ),
        (
            "acceptance",
            "workflow:not_real",
        ),
    ),
)
def test_unknown_provenance_ref_is_rejected(
    location,
    unknown_ref,
) -> None:

    skip_until_authority_exists()

    context = pm_context()

    kwargs = {}

    if location == "epic":
        kwargs[
            "epic_provenance"
        ] = [
            unknown_ref
        ]

    elif location == "feature":
        kwargs[
            "feature_provenance"
        ] = [
            unknown_ref
        ]

    elif location == "story":
        kwargs[
            "story_provenance"
        ] = [
            unknown_ref
        ]

    else:
        kwargs[
            "acceptance_source_ref"
        ] = unknown_ref

    result = validate(
        context,
        candidate(
            context,
            **kwargs,
        ),
    )

    assert result.is_valid is False

    assert (
        "unresolved_provenance_ref"
        in result.error_codes
    )


@pytest.mark.parametrize(
    "ref",
    (
        "actor:Operator",
        "workflow:request_review",
        "mvp_scope:Request review",
        (
            "constraint:"
            "The system must not expose "
            "confidential data."
        ),
        (
            "validated_next_action:"
            "Run bounded pilot"
        ),
        (
            "go_no_go_condition:"
            "GO if repeated use is observed."
        ),
    ),
)
def test_known_canonical_provenance_namespaces_resolve(
    ref,
) -> None:

    skip_until_authority_exists()

    context = pm_context()

    value = candidate(
        context,
        story_provenance=[
            ref
        ],
    )

    result = validate(
        context,
        value,
    )

    assert (
        "unresolved_provenance_ref"
        not in result.error_codes
    )


# ============================================================
# NEGATIVE SCOPE CANNOT BECOME POSITIVE SUPPORT
# ============================================================


def test_scope_exclusion_cannot_be_positive_story_provenance() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context,
            story_provenance=[
                (
                    "scope_exclusion:"
                    "Automatic payments"
                ),
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "negative_scope_provenance"
        in result.error_codes
    )


# ============================================================
# SEARCH / RAG / ARCHETYPE HAVE NO PROVENANCE AUTHORITY
# ============================================================


@pytest.mark.parametrize(
    "ref",
    (
        "search:marketplace software",
        "rag:generic benchmark",
        "query:warehouse competitors",
        "archetype:two_sided_marketplace",
    ),
)
def test_noncanonical_intelligence_namespaces_are_rejected(
    ref,
) -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context,
            story_provenance=[
                ref
            ],
        ),
    )

    assert result.is_valid is False

    assert (
        "unresolved_provenance_ref"
        in result.error_codes
    )


# ============================================================
# IMMUTABILITY
# ============================================================


def test_authority_validation_does_not_mutate_context_or_candidate() -> None:

    skip_until_authority_exists()

    context = pm_context()
    value = candidate(
        context
    )

    context_before = context.model_dump(
        mode="json"
    )

    candidate_before = value.model_dump(
        mode="json"
    )

    validate(
        context,
        value,
    )

    assert (
        context.model_dump(
            mode="json"
        )
        ==
        context_before
    )

    assert (
        value.model_dump(
            mode="json"
        )
        ==
        candidate_before
    )


# ============================================================
# THIS LAYER MUST NOT CANONICALIZE
# ============================================================


def test_authority_gate_does_not_assign_canonical_backlog_authority() -> None:

    skip_until_authority_exists()

    context = pm_context()

    result = validate(
        context,
        candidate(
            context
        ),
    )

    forbidden = {
        "canonical_backlog",
        "story_points",
        "priority",
        "sprints",
        "locked_stories",
        "canonical_ids",
    }

    assert not (
        forbidden
        &
        set(
            result.model_fields
        )
    )