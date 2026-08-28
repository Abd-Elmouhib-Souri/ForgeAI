from __future__ import annotations

from copy import deepcopy

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
from app.services.backlog_policy_engine import (
    BacklogPolicyEngine,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


def scenarios():
    return [
        {
            "project_id": "policy-logistics-eg",
            "project_name": "Dock Coordination",
            "language": "en",
            "region": "Egypt",
            "industry": "Warehouse operations",
            "actor": "Dock Coordinator",
            "decision_maker": "Operations Director",
            "workflow": "dock_request_review",
            "action": "review",
            "object": "truck appointment request",
            "result": "dock appointment confirmed",
            "scope": "Truck appointment review",
            "exclusion": "Automatic freight payments",
            "title": "Review truck appointment request",
        },
        {
            "project_id": "policy-iot-de",
            "project_name": "Equipment Monitoring",
            "language": "en",
            "region": "Germany",
            "industry": "Industrial IoT",
            "actor": "Maintenance Technician",
            "decision_maker": "Plant Manager",
            "workflow": "equipment_alert_review",
            "action": "review",
            "object": "equipment alert",
            "result": "maintenance action recorded",
            "scope": "Equipment alert review",
            "exclusion": "Autonomous machinery shutdown",
            "title": "Review equipment alert",
        },
        {
            "project_id": "policy-internal-uk",
            "project_name": "Internal Approval Flow",
            "language": "en",
            "region": "United Kingdom",
            "industry": "Internal operations",
            "actor": "Operations Analyst",
            "decision_maker": "Department Manager",
            "workflow": "request_approval",
            "action": "review",
            "object": "internal request",
            "result": "approval decision recorded",
            "scope": "Internal request approval",
            "exclusion": "Public marketplace listings",
            "title": "Review internal request",
        },
        {
            "project_id": "policy-service-tn",
            "project_name": "Coordination Service",
            "language": "fr",
            "region": "Tunisie",
            "industry": "Coordination de services",
            "actor": "Coordinateur",
            "decision_maker": "Responsable des opérations",
            "workflow": "validation_demande",
            "action": "valider",
            "object": "demande de service",
            "result": "décision enregistrée",
            "scope": "Validation des demandes de service",
            "exclusion": "Paiement automatique",
            "title": "Valider une demande de service",
        },
    ]


def make_context(scenario):

    packet = ProjectContextPacketV3(
        project_name=scenario["project_name"],
        language=scenario["language"],
        target_region=scenario["region"],
        industry_user_input=scenario["industry"],

        actors=[
            ActorContext(
                name=scenario["actor"],
                role=ActorRole.USER,
                is_explicit=True,
            ),
            ActorContext(
                name=scenario["decision_maker"],
                role=ActorRole.DECISION_MAKER,
                is_explicit=True,
            ),
        ],

        priority_workflows=[
            WorkflowContext(
                name=scenario["workflow"],
                actor=scenario["actor"],
                action=scenario["action"],
                object=scenario["object"],
                result=scenario["result"],
                is_explicit=True,
                confidence=1.0,
            ),
        ],

        mvp_scope=[
            scenario["scope"],
        ],

        scope_exclusions=[
            scenario["exclusion"],
        ],
    )

    return project_management_context_builder.build(
        packet=packet,
        project_id=scenario["project_id"],
        decision=None,
    )


def make_epic(
    scenario,
    *,
    key="epic_core",
):

    return CandidateEpicV1(
        candidate_key=key,

        title="Core workflow",

        description=(
            "Support the validated operational workflow."
        ),

        business_goal=(
            "Deliver the validated project outcome."
        ),

        provenance_refs=[
            f"workflow:{scenario['workflow']}",
        ],
    )


def make_feature(
    scenario,
    *,
    key="feature_core",
    epic_key="epic_core",
):

    return CandidateFeatureV1(
        candidate_key=key,

        epic_key=epic_key,

        title=scenario["title"],

        description=(
            "Implement the validated MVP capability."
        ),

        business_value=(
            "Support the explicit operational workflow."
        ),

        provenance_refs=[
            f"mvp_scope:{scenario['scope']}",
        ],
    )


def make_story(
    context,
    scenario,
    *,
    key="story_core",
    epic_key="epic_core",
    feature_key="feature_core",
    actor=None,
    story_text=None,
    dependencies=None,
    provenance_refs=None,
):

    actor_name = (
        actor
        if actor is not None
        else scenario["actor"]
    )

    return CandidateUserStoryV1(
        candidate_key=key,

        epic_key=epic_key,

        feature_key=feature_key,

        actor_ref=actor_name,

        title=scenario["title"],

        capability=scenario["title"],

        benefit=(
            "complete the validated workflow"
        ),

        story=(
            story_text
            or
            (
                f"As {actor_name}, I want to "
                f"{scenario['title'].lower()} "
                "so that the validated workflow "
                "can be completed."
            )
        ),

        business_value=(
            "Support the validated operational objective."
        ),

        acceptance_criteria=[
            CandidateAcceptanceCriterionV1(
                statement=(
                    "Given the validated workflow, "
                    "when the actor performs the capability, "
                    "then the expected result is recorded."
                ),

                candidate_testable=True,

                source_ref=(
                    f"workflow:{scenario['workflow']}"
                ),
            ),
        ],

        candidate_priority="must",

        candidate_priority_rationale=(
            "The candidate belongs to explicit MVP scope."
        ),

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "The workflow requires controlled state handling."
        ),

        candidate_dependencies=(
            dependencies
            if dependencies is not None
            else []
        ),

        provenance_refs=(
            provenance_refs
            if provenance_refs is not None
            else [
                f"actor:{scenario['actor']}",
                f"workflow:{scenario['workflow']}",
                f"mvp_scope:{scenario['scope']}",
            ]
        ),

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )


def make_candidate(
    context,
    scenario,
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
                make_epic(
                    scenario
                ),
            ]
        ),

        features=(
            features
            if features is not None
            else [
                make_feature(
                    scenario
                ),
            ]
        ),

        stories=(
            stories
            if stories is not None
            else [
                make_story(
                    context,
                    scenario,
                ),
            ]
        ),

        warnings=[],
    )


def evaluate(
    context,
    candidate,
):
    return BacklogPolicyEngine().evaluate(
        context=context,
        candidate=candidate,
    )


# ============================================================
# CROSS-DOMAIN / COUNTRY / LANGUAGE
# ============================================================


@pytest.mark.parametrize(
    "scenario",
    scenarios(),
)
def test_valid_backlog_is_accepted_across_domains(
    scenario,
) -> None:

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    result = evaluate(
        context,
        candidate,
    )

    assert result.is_valid is True
    assert result.error_codes == []


# ============================================================
# DETERMINISM
# ============================================================


@pytest.mark.parametrize(
    "scenario",
    scenarios(),
)
def test_policy_is_deterministic_across_domains(
    scenario,
) -> None:

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    first = evaluate(
        context,
        candidate,
    )

    second = evaluate(
        context.model_copy(
            deep=True
        ),
        candidate.model_copy(
            deep=True
        ),
    )

    assert first == second


# ============================================================
# IMMUTABILITY
# ============================================================


def test_policy_never_mutates_inputs_across_domains() -> None:

    for scenario in scenarios():

        context = make_context(
            scenario
        )

        candidate = make_candidate(
            context,
            scenario,
        )

        context_before = (
            context.model_dump(
                mode="json"
            )
        )

        candidate_before = (
            candidate.model_dump(
                mode="json"
            )
        )

        evaluate(
            context,
            candidate,
        )

        assert (
            context.model_dump(
                mode="json"
            )
            ==
            context_before
        )

        assert (
            candidate.model_dump(
                mode="json"
            )
            ==
            candidate_before
        )


# ============================================================
# STALE HASH / AUTHORITY
# ============================================================


def test_stale_candidate_is_rejected_after_real_scope_change() -> None:

    scenario = scenarios()[0]

    old_context = make_context(
        scenario
    )

    old_candidate = make_candidate(
        old_context,
        scenario,
    )

    changed = deepcopy(
        scenario
    )

    changed["scope"] = (
        "Truck appointment review "
        "and manual exception handling"
    )

    new_context = make_context(
        changed
    )

    assert (
        old_context.context_hash
        !=
        new_context.context_hash
    )

    result = evaluate(
        new_context,
        old_candidate,
    )

    assert result.is_valid is False

    assert (
        "candidate_authority_rejected"
        in result.error_codes
    )


# ============================================================
# NEGATIVE SCOPE CANNOT BECOME POSITIVE BACKLOG
# ============================================================


def test_scope_exclusion_cannot_gain_positive_backlog_authority() -> None:

    scenario = scenarios()[1]

    context = make_context(
        scenario
    )

    invalid_story = make_story(
        context,
        scenario,
        provenance_refs=[
            (
                "scope_exclusion:"
                +
                scenario["exclusion"]
            )
        ],
    )

    candidate = make_candidate(
        context,
        scenario,
        stories=[
            invalid_story,
        ],
    )

    result = evaluate(
        context,
        candidate,
    )

    assert result.is_valid is False

    assert (
        "candidate_authority_rejected"
        in result.error_codes
    )


# ============================================================
# QUERY / ARCHETYPE NEVER BECOME BACKLOG AUTHORITY
# ============================================================


@pytest.mark.parametrize(
    "bad_ref",
    (
        "query:employee scheduling software",
        "archetype:two_sided_marketplace",
    ),
)
def test_search_or_archetype_provenance_is_rejected(
    bad_ref,
) -> None:

    scenario = scenarios()[2]

    context = make_context(
        scenario
    )

    invalid_story = make_story(
        context,
        scenario,
        provenance_refs=[
            bad_ref,
        ],
    )

    candidate = make_candidate(
        context,
        scenario,
        stories=[
            invalid_story,
        ],
    )

    result = evaluate(
        context,
        candidate,
    )

    assert result.is_valid is False

    assert (
        "candidate_authority_rejected"
        in result.error_codes
    )


# ============================================================
# UNIVERSAL HIERARCHY RULE
# ============================================================


def test_missing_parent_feature_is_rejected_outside_fixture_domain() -> None:

    scenario = scenarios()[3]

    context = make_context(
        scenario
    )

    invalid_story = make_story(
        context,
        scenario,
        feature_key=(
            "feature_absente"
        ),
    )

    candidate = make_candidate(
        context,
        scenario,
        stories=[
            invalid_story,
        ],
    )

    result = evaluate(
        context,
        candidate,
    )

    assert result.is_valid is False

    assert (
        "missing_parent_feature"
        in result.error_codes
    )


# ============================================================
# UNIVERSAL NORMALIZED DUPLICATION
# ============================================================


def test_normalized_duplicate_semantics_are_rejected_in_french_context() -> None:

    scenario = scenarios()[3]

    context = make_context(
        scenario
    )

    text = (
        "En tant que Coordinateur, je veux "
        "valider une demande de service afin "
        "que la décision soit enregistrée."
    )

    normalized_equivalent = (
        "  EN TANT QUE COORDINATEUR,   JE VEUX "
        "VALIDER UNE DEMANDE DE SERVICE AFIN "
        "QUE LA DÉCISION SOIT ENREGISTRÉE.  "
    )

    first = make_story(
        context,
        scenario,
        key="story_validation",
        story_text=text,
    )

    second = make_story(
        context,
        scenario,
        key="story_validation_copy",
        story_text=normalized_equivalent,
    )

    candidate = make_candidate(
        context,
        scenario,
        stories=[
            first,
            second,
        ],
    )

    result = evaluate(
        context,
        candidate,
    )

    assert result.is_valid is False

    assert (
        "duplicate_story_semantics"
        in result.error_codes
    )