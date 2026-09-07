from __future__ import annotations

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
from app.services.candidate_backlog_authority import (
    candidate_backlog_authority_validator,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)
from app.services.project_management_decision_projector import (
    project_management_decision_projector,
)


def _context():
    """
    Generic domain-neutral PM context with two explicit MVP commitments.

    The test intentionally does not encode a country, industry,
    product archetype, or project-specific feature set.
    """

    packet = ProjectContextPacketV3(
        project_name="Backlog Coverage Probe",
        language="en",
        target_region="International",
        industry_user_input="Generic workflow software",
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
            "Decision audit trail",
        ],
        scope_exclusions=[
            "Automatic payments",
        ],
        constraints=[
            "The system must not expose confidential data.",
        ],
    )

    decision = project_management_decision_projector.project(
        debate_judge={
            "status": "completed",
            "verdict_code": "conditional_go",
            "critical_risks": [
                "Retention remains unvalidated.",
            ],
            "next_actions": [
                "Run bounded pilot",
            ],
            "go_no_go_conditions": [
                "GO if repeated use is observed.",
            ],
            "final_recommendation": "Run a bounded pilot.",
        }
    )

    return project_management_context_builder.build(
        packet=packet,
        project_id="coverage-probe",
        decision=decision,
    )


def _candidate(
    context,
    *,
    covered_scope_refs: list[str],
) -> CandidateBacklogV1:

    return CandidateBacklogV1(
        source_context_hash=context.source_context_hash,
        context_hash=context.context_hash,
        epics=[
            CandidateEpicV1(
                candidate_key="epic_operations",
                title="Core operations",
                description="Support the validated workflow.",
                business_goal="Complete the primary workflow.",
                provenance_refs=[
                    "workflow:request_review",
                ],
            )
        ],
        features=[
            CandidateFeatureV1(
                candidate_key="feature_request_review",
                epic_key="epic_operations",
                title="Request review",
                description="Review incoming requests.",
                business_value="Reduce processing delay.",
                provenance_refs=list(
                    covered_scope_refs
                ),
            )
        ],
        stories=[
            CandidateUserStoryV1(
                candidate_key="story_review_request",
                epic_key="epic_operations",
                feature_key="feature_request_review",
                actor_ref="Operator",
                title="Review incoming request",
                capability="review an incoming request",
                benefit="reduce processing delays",
                story=(
                    "As an Operator, I want to review an incoming "
                    "request so that processing delays are reduced."
                ),
                business_value="Faster operational processing.",
                acceptance_criteria=[
                    CandidateAcceptanceCriterionV1(
                        statement=(
                            "Given a pending request, when the Operator "
                            "reviews it, then the result is recorded."
                        ),
                        candidate_testable=True,
                        source_ref="workflow:request_review",
                    )
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
                    "business_logic": "low",
                    "integration_complexity": "none",
                    "data_complexity": "low",
                    "ui_complexity": "low",
                    "security": "unknown",
                    "external_dependency": "none",
                    "uncertainty": "low",
                    "testing_burden": "low",
                    "regulatory_risk": "none",
                    "hardware_dependency": "none",
                },
                candidate_dependencies=[],
                provenance_refs=[
                    "actor:Operator",
                    *covered_scope_refs,
                ],
                source_context_hash=context.source_context_hash,
                warnings=[],
            )
        ],
        warnings=[],
    )


def test_authority_rejects_silent_loss_of_explicit_mvp_scope() -> None:
    """
    REAL RED.

    Every explicit positive MVP-scope commitment must remain
    traceable somewhere in the candidate backlog.

    The authority must not accept a candidate merely because the
    references it DOES contain are individually valid.
    """

    context = _context()

    candidate = _candidate(
        context,
        covered_scope_refs=[
            "mvp_scope:Request review",
        ],
    )

    result = candidate_backlog_authority_validator.validate(
        context=context,
        candidate=candidate,
    )

    assert result.is_valid is False

    assert (
        "canonical_scope_undercovered"
        in result.error_codes
    )

    assert any(
        "Decision audit trail" in error
        for error in result.errors
    )


def test_one_story_may_cover_multiple_explicit_mvp_scope_items() -> None:
    """
    Anti-overfitting control.

    Coverage authority must NOT become a cardinality rule.

    A single story is valid when its candidate graph explicitly
    preserves all authoritative MVP-scope commitments.
    """

    context = _context()

    candidate = _candidate(
        context,
        covered_scope_refs=[
            "mvp_scope:Request review",
            "mvp_scope:Decision audit trail",
        ],
    )

    result = candidate_backlog_authority_validator.validate(
        context=context,
        candidate=candidate,
    )

    assert result.is_valid is True
    assert result.error_codes == []


def test_deterministic_fallback_preserves_all_explicit_mvp_scope_refs() -> None:
    """
    REAL RED for the provider-outage path.

    A deterministic fallback may remain compact and may expose only
    one concrete story, but it must not silently erase explicit
    canonical MVP-scope commitments.

    This is a coverage invariant, not a story-count invariant.
    """

    from app.services.project_management_plan_service import (
        ProjectManagementPlanService,
    )

    context = _context()

    candidate = (
        ProjectManagementPlanService
        ._build_deterministic_candidate(
            context
        )
    )

    refs = {
        ref
        for epic in candidate.epics
        for ref in epic.provenance_refs
    }

    refs.update(
        ref
        for feature in candidate.features
        for ref in feature.provenance_refs
    )

    refs.update(
        ref
        for story in candidate.stories
        for ref in story.provenance_refs
    )

    refs.update(
        criterion.source_ref
        for story in candidate.stories
        for criterion in story.acceptance_criteria
    )

    expected_scope_refs = {
        f"mvp_scope:{value}"
        for value in context.mvp_scope
    }

    assert expected_scope_refs <= refs


def test_deterministic_fallback_semantically_preserves_explicit_mvp_scope() -> None:
    """
    Anti-fake-green contract.

    Provider outage must not be repaired by attaching canonical
    provenance references to an otherwise unrelated backlog item.

    The deterministic fallback may stay compact and one Story may
    cover multiple scope commitments, but every explicit positive
    MVP-scope commitment must also remain visible in the Story-level
    semantic surface.
    """

    from app.services.project_management_plan_service import (
        ProjectManagementPlanService,
    )

    context = _context()

    candidate = (
        ProjectManagementPlanService
        ._build_deterministic_candidate(
            context
        )
    )

    semantic_parts: list[str] = []

    for story in candidate.stories:

        semantic_parts.extend(
            [
                story.title,
                story.capability,
                story.benefit,
                story.story,
                story.business_value,
            ]
        )

        semantic_parts.extend(
            criterion.statement
            for criterion
            in story.acceptance_criteria
        )

    semantic_surface = " ".join(
        str(value)
        for value in semantic_parts
        if value
    ).casefold()

    for value in context.mvp_scope:

        assert value.casefold() in semantic_surface

def test_deterministic_fallback_preserves_localized_french_unicode_integrity() -> None:
    """
    Localized deterministic output must preserve its intended Unicode
    literals instead of silently replacing them with ASCII question marks.

    This contract is independent of project, sector, country and backlog
    cardinality.
    """

    from app.services.project_management_plan_service import (
        ProjectManagementPlanService,
    )

    context = _context().model_copy(
        update={
            "language": "fr",
            "mvp_scope": [
                "Action A",
                "Action B",
            ],
        },
        deep=True,
    )

    candidate = (
        ProjectManagementPlanService
        ._build_deterministic_candidate(
            context
        )
    )

    story = candidate.stories[0]

    values = [
        story.capability,
        story.story,
        story.business_value,
    ]

    values.extend(
        criterion.statement
        for criterion
        in story.acceptance_criteria
    )

    surface = "\n".join(
        str(value)
        for value in values
        if value
    )

    corruption_markers = (
        "r?aliser",
        "p?rim?tre",
        "?tant donn?",
        "r?sultat",
        "enregistr?",
        "tra?able",
        "r?alis?",
    )

    assert not any(
        marker in surface
        for marker in corruption_markers
    )

    expected_unicode = (
        "r\u00e9aliser",
        "p\u00e9rim\u00e8tre",
        "\u00c9tant donn\u00e9",
        "r\u00e9sultat",
        "enregistr\u00e9",
        "tra\u00e7able",
        "r\u00e9alis\u00e9",
        "\u00ab",
        "\u00bb",
    )

    for value in expected_unicode:
        assert value in surface
