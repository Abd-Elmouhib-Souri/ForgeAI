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
    CanonicalBacklogV1,
)
from app.services.backlog_policy_engine import (
    BacklogPolicyCanonicalizationError,
    BacklogPolicyEngine,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


def scenarios():

    return [
        {
            "project_id":
                "canonical-logistics-eg",

            "project_name":
                "Dock Coordination",

            "language":
                "en",

            "region":
                "Egypt",

            "industry":
                "Warehouse operations",

            "actor":
                "Dock Coordinator",

            "decision_maker":
                "Operations Director",

            "workflow":
                "dock_appointment_review",

            "action":
                "review",

            "object":
                "truck appointment",

            "result":
                "appointment decision recorded",

            "scope":
                "Truck appointment coordination",

            "exclusion":
                "Automatic freight payment",

            "first_title":
                "Capture truck appointment",

            "second_title":
                "Review truck appointment",
        },

        {
            "project_id":
                "canonical-industrial-de",

            "project_name":
                "Equipment Alert Workflow",

            "language":
                "en",

            "region":
                "Germany",

            "industry":
                "Industrial maintenance",

            "actor":
                "Maintenance Technician",

            "decision_maker":
                "Plant Manager",

            "workflow":
                "equipment_alert_review",

            "action":
                "review",

            "object":
                "equipment alert",

            "result":
                "maintenance decision recorded",

            "scope":
                "Equipment alert review",

            "exclusion":
                "Autonomous machine shutdown",

            "first_title":
                "Capture equipment alert",

            "second_title":
                "Review equipment alert",
        },

        {
            "project_id":
                "canonical-service-tn",

            "project_name":
                "Coordination de demandes",

            "language":
                "fr",

            "region":
                "Tunisie",

            "industry":
                "Coordination de services",

            "actor":
                "Coordinateur",

            "decision_maker":
                "Responsable des opérations",

            "workflow":
                "validation_demande",

            "action":
                "valider",

            "object":
                "demande de service",

            "result":
                "décision enregistrée",

            "scope":
                "Validation des demandes",

            "exclusion":
                "Paiement automatique",

            "first_title":
                "Enregistrer une demande",

            "second_title":
                "Valider une demande",
        },

        {
            "project_id":
                "canonical-internal-fr",

            "project_name":
                "Internal Approval Flow",

            "language":
                "en",

            "region":
                "France",

            "industry":
                "Internal business operations",

            "actor":
                "Operations Analyst",

            "decision_maker":
                "Department Manager",

            "workflow":
                "internal_request_approval",

            "action":
                "approve",

            "object":
                "internal request",

            "result":
                "approval recorded",

            "scope":
                "Internal request approval",

            "exclusion":
                "Public marketplace listing",

            "first_title":
                "Capture internal request",

            "second_title":
                "Approve internal request",
        },
    ]


def make_context(
    scenario,
):

    packet = ProjectContextPacketV3(
        project_name=(
            scenario["project_name"]
        ),

        language=(
            scenario["language"]
        ),

        target_region=(
            scenario["region"]
        ),

        industry_user_input=(
            scenario["industry"]
        ),

        actors=[
            ActorContext(
                name=(
                    scenario["actor"]
                ),

                role=ActorRole.USER,

                is_explicit=True,
            ),

            ActorContext(
                name=(
                    scenario[
                        "decision_maker"
                    ]
                ),

                role=(
                    ActorRole.DECISION_MAKER
                ),

                is_explicit=True,
            ),
        ],

        priority_workflows=[
            WorkflowContext(
                name=(
                    scenario["workflow"]
                ),

                actor=(
                    scenario["actor"]
                ),

                action=(
                    scenario["action"]
                ),

                object=(
                    scenario["object"]
                ),

                result=(
                    scenario["result"]
                ),

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

    return (
        project_management_context_builder.build(
            packet=packet,

            project_id=(
                scenario["project_id"]
            ),

            decision=None,
        )
    )


def make_acceptance(
    scenario,
    statement,
):

    return CandidateAcceptanceCriterionV1(
        statement=statement,

        candidate_testable=True,

        source_ref=(
            "workflow:"
            +
            scenario["workflow"]
        ),
    )


def make_candidate(
    context,
    scenario,
    *,
    key_prefix="candidate",
):

    epic_a = (
        f"{key_prefix}_epic_a"
    )

    epic_b = (
        f"{key_prefix}_epic_b"
    )

    feature_a = (
        f"{key_prefix}_feature_a"
    )

    feature_b = (
        f"{key_prefix}_feature_b"
    )

    story_a = (
        f"{key_prefix}_story_a"
    )

    story_b = (
        f"{key_prefix}_story_b"
    )


    epics = [
        CandidateEpicV1(
            candidate_key=(
                epic_a
            ),

            title=(
                "Intake"
            ),

            description=(
                "Capture the input required "
                "for the validated workflow."
            ),

            business_goal=(
                "Support the validated "
                "operational workflow."
            ),

            provenance_refs=[
                (
                    "workflow:"
                    +
                    scenario["workflow"]
                ),
            ],
        ),

        CandidateEpicV1(
            candidate_key=(
                epic_b
            ),

            title=(
                "Decision"
            ),

            description=(
                "Support the validated "
                "workflow decision."
            ),

            business_goal=(
                "Reach the validated "
                "operational outcome."
            ),

            provenance_refs=[
                (
                    "workflow:"
                    +
                    scenario["workflow"]
                ),
            ],
        ),
    ]


    features = [
        CandidateFeatureV1(
            candidate_key=(
                feature_a
            ),

            epic_key=(
                epic_a
            ),

            title=(
                scenario[
                    "first_title"
                ]
            ),

            description=(
                "Capture the explicit "
                "MVP workflow input."
            ),

            business_value=(
                "Support the explicit MVP."
            ),

            provenance_refs=[
                (
                    "mvp_scope:"
                    +
                    scenario["scope"]
                ),
            ],
        ),

        CandidateFeatureV1(
            candidate_key=(
                feature_b
            ),

            epic_key=(
                epic_b
            ),

            title=(
                scenario[
                    "second_title"
                ]
            ),

            description=(
                "Complete the explicit "
                "MVP workflow."
            ),

            business_value=(
                "Deliver the explicit "
                "workflow outcome."
            ),

            provenance_refs=[
                (
                    "mvp_scope:"
                    +
                    scenario["scope"]
                ),
            ],
        ),
    ]


    first_story = CandidateUserStoryV1(
        candidate_key=(
            story_a
        ),

        epic_key=(
            epic_a
        ),

        feature_key=(
            feature_a
        ),

        actor_ref=(
            scenario["actor"]
        ),

        title=(
            scenario[
                "first_title"
            ]
        ),

        capability=(
            scenario[
                "first_title"
            ]
        ),

        benefit=(
            "prepare the validated workflow"
        ),

        story=(
            f"As {scenario['actor']}, "
            f"I want to "
            f"{scenario['first_title'].lower()} "
            "so that the validated workflow "
            "can begin."
        ),

        business_value=(
            "Support the validated "
            "operational workflow."
        ),

        acceptance_criteria=[
            make_acceptance(
                scenario,

                "Given valid workflow input, "
                "when the actor records it, "
                "then the input is available "
                "for the next workflow step.",
            ),
        ],

        candidate_priority="must",

        candidate_priority_rationale=(
            "Advisory Product Owner input."
        ),

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "Advisory Product Owner input."
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

        provenance_refs=[
            (
                "actor:"
                +
                scenario["actor"]
            ),

            (
                "workflow:"
                +
                scenario["workflow"]
            ),

            (
                "mvp_scope:"
                +
                scenario["scope"]
            ),
        ],

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )


    second_story = CandidateUserStoryV1(
        candidate_key=(
            story_b
        ),

        epic_key=(
            epic_b
        ),

        feature_key=(
            feature_b
        ),

        actor_ref=(
            scenario["actor"]
        ),

        title=(
            scenario[
                "second_title"
            ]
        ),

        capability=(
            scenario[
                "second_title"
            ]
        ),

        benefit=(
            "complete the validated workflow"
        ),

        story=(
            f"As {scenario['actor']}, "
            f"I want to "
            f"{scenario['second_title'].lower()} "
            "so that the validated outcome "
            "is recorded."
        ),

        business_value=(
            "Reach the validated "
            "operational outcome."
        ),

        acceptance_criteria=[
            make_acceptance(
                scenario,

                "Given valid recorded input, "
                "when the actor completes "
                "the workflow decision, "
                "then the expected outcome "
                "is recorded.",
            ),

            make_acceptance(
                scenario,

                "Given a completed decision, "
                "when the workflow is saved, "
                "then its outcome remains "
                "available.",
            ),
        ],

        candidate_priority="must",

        candidate_priority_rationale=(
            "Advisory Product Owner input."
        ),

        candidate_complexity="medium",

        candidate_complexity_rationale=(
            "Advisory Product Owner input."
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
        candidate_dependencies=[
            story_a,
        ],

        provenance_refs=[
            (
                "actor:"
                +
                scenario["actor"]
            ),

            (
                "workflow:"
                +
                scenario["workflow"]
            ),

            (
                "mvp_scope:"
                +
                scenario["scope"]
            ),
        ],

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )


    return CandidateBacklogV1(
        source_context_hash=(
            context.source_context_hash
        ),

        context_hash=(
            context.context_hash
        ),

        epics=epics,

        features=features,

        stories=[
            first_story,
            second_story,
        ],

        warnings=[],
    )


def canonicalize(
    context,
    candidate,
):

    return (
        BacklogPolicyEngine()
        .canonicalize(
            context=context,
            candidate=candidate,
        )
    )


def canonical_ids(
    backlog,
):

    return {
        "epics": [
            item.epic_id
            for item
            in backlog.epics
        ],

        "features": [
            item.feature_id
            for item
            in backlog.features
        ],

        "stories": [
            item.story_id
            for item
            in backlog.stories
        ],

        "acceptance": [
            criterion.acceptance_criterion_id
            for story
            in backlog.stories
            for criterion
            in story.acceptance_criteria
        ],
    }


# ============================================================
# CROSS-DOMAIN / COUNTRY / LANGUAGE
# ============================================================


@pytest.mark.parametrize(
    "scenario",
    scenarios(),
)
def test_canonicalization_is_valid_across_domains(
    scenario,
) -> None:

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    result = canonicalize(
        context,
        candidate,
    )

    assert isinstance(
        result,
        CanonicalBacklogV1,
    )

    assert (
        result.schema_version
        ==
        "canonical_backlog_v1"
    )

    assert canonical_ids(
        result
    ) == {
        "epics": [
            "EP-001",
            "EP-002",
        ],

        "features": [
            "FE-001",
            "FE-002",
        ],

        "stories": [
            "US-001",
            "US-002",
        ],

        "acceptance": [
            "AC-001",
            "AC-002",
            "AC-003",
        ],
    }

    assert all(
        story.scope_status
        ==
        "in_scope"
        for story
        in result.stories
    )

    assert all(
        story.locked is False
        for story
        in result.stories
    )


# ============================================================
# DETERMINISM
# ============================================================


@pytest.mark.parametrize(
    "scenario",
    scenarios(),
)
def test_canonicalization_is_deterministic_across_domains(
    scenario,
) -> None:

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    first = canonicalize(
        context,
        candidate,
    )

    second = canonicalize(
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


def test_canonicalization_never_mutates_inputs() -> None:

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

        canonicalize(
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
# CANDIDATE KEYS ARE NOT ID AUTHORITY
# ============================================================


def test_renaming_all_candidate_keys_preserves_canonical_id_sequence() -> None:

    scenario = scenarios()[0]

    context = make_context(
        scenario
    )

    original = make_candidate(
        context,
        scenario,
        key_prefix="original",
    )

    renamed = make_candidate(
        context,
        scenario,
        key_prefix=(
            "completely_different_llm_keys"
        ),
    )

    first = canonicalize(
        context,
        original,
    )

    second = canonicalize(
        context,
        renamed,
    )

    assert (
        canonical_ids(
            first
        )
        ==
        canonical_ids(
            second
        )
    )

    assert (
        first.stories[1]
        .dependency_hint_ids
        ==
        second.stories[1]
        .dependency_hint_ids
        ==
        [
            "US-001",
        ]
    )


# ============================================================
# ADVISORY PRIORITY / COMPLEXITY DO NOT CONTROL IDS
# ============================================================


def test_advisory_priority_and_complexity_do_not_control_canonical_ids() -> None:

    scenario = scenarios()[1]

    context = make_context(
        scenario
    )

    original = make_candidate(
        context,
        scenario,
    )

    changed_stories = [
        story.model_copy(
            update={
                "candidate_priority":
                    "could",

                "candidate_priority_rationale":
                    "Different advisory signal.",

                "candidate_complexity":
                    "high",

                "candidate_complexity_rationale":
                    "Different advisory estimate.",
            "candidate_complexity_factors": {
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
            },

            deep=True,
        )
        for story
        in original.stories
    ]

    changed = original.model_copy(
        update={
            "stories":
                changed_stories,
        },

        deep=True,
    )

    first = canonicalize(
        context,
        original,
    )

    second = canonicalize(
        context,
        changed,
    )

    assert (
        canonical_ids(
            first
        )
        ==
        canonical_ids(
            second
        )
    )

    assert all(
        story.priority is None
        for story
        in second.stories
    )

    assert all(
        story.story_points is None
        for story
        in second.stories
    )

    assert all(
        story.candidate_priority
        ==
        "could"
        for story
        in second.stories
    )

    assert all(
        story.candidate_complexity
        ==
        "high"
        for story
        in second.stories
    )


# ============================================================
# TEXT CHANGES DO NOT BECOME ID AUTHORITY
# ============================================================


def test_story_text_paraphrase_does_not_control_canonical_ids() -> None:

    scenario = scenarios()[2]

    context = make_context(
        scenario
    )

    original = make_candidate(
        context,
        scenario,
    )

    changed_story = (
        original.stories[0]
        .model_copy(
            update={
                "title":
                    "Préparer la demande",

                "capability":
                    "Préparer la demande",

                "story":
                    (
                        "En tant que Coordinateur, "
                        "je souhaite préparer "
                        "la demande afin de démarrer "
                        "le parcours validé."
                    ),
            },

            deep=True,
        )
    )

    changed = original.model_copy(
        update={
            "stories": [
                changed_story,
                original.stories[1],
            ],
        },

        deep=True,
    )

    first = canonicalize(
        context,
        original,
    )

    second = canonicalize(
        context,
        changed,
    )

    assert (
        canonical_ids(
            first
        )
        ==
        canonical_ids(
            second
        )
    )


# ============================================================
# SCOPE POLARITY REMAINS BINDING
# ============================================================


def test_scope_exclusion_is_rejected_before_canonicalization() -> None:

    scenario = scenarios()[1]

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    invalid_story = (
        candidate.stories[0]
        .model_copy(
            update={
                "provenance_refs": [
                    (
                        "scope_exclusion:"
                        +
                        scenario[
                            "exclusion"
                        ]
                    ),
                ],
            },

            deep=True,
        )
    )

    invalid = candidate.model_copy(
        update={
            "stories": [
                invalid_story,
                candidate.stories[1],
            ],
        },

        deep=True,
    )

    with pytest.raises(
        BacklogPolicyCanonicalizationError
    ) as exc:

        canonicalize(
            context,
            invalid,
        )

    assert (
        exc.value.code
        ==
        "backlog_policy_rejected"
    )


# ============================================================
# STALE CONTEXT REMAINS BINDING
# ============================================================


def test_stale_context_hash_is_rejected_before_canonicalization() -> None:

    scenario = scenarios()[0]

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    stale = candidate.model_copy(
        update={
            "context_hash":
                "f" * 64,
        },

        deep=True,
    )

    with pytest.raises(
        BacklogPolicyCanonicalizationError
    ) as exc:

        canonicalize(
            context,
            stale,
        )

    assert (
        exc.value.code
        ==
        "backlog_policy_rejected"
    )


# ============================================================
# QUERY / ARCHETYPE CANNOT BECOME CANONICAL AUTHORITY
# ============================================================


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "query:employee scheduling software",
        "archetype:two_sided_marketplace",
    ),
)
def test_query_or_archetype_provenance_is_rejected_before_canonicalization(
    unsafe_ref,
) -> None:

    scenario = scenarios()[3]

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    invalid_story = (
        candidate.stories[0]
        .model_copy(
            update={
                "provenance_refs": [
                    unsafe_ref,
                ],
            },

            deep=True,
        )
    )

    invalid = candidate.model_copy(
        update={
            "stories": [
                invalid_story,
                candidate.stories[1],
            ],
        },

        deep=True,
    )

    with pytest.raises(
        BacklogPolicyCanonicalizationError
    ) as exc:

        canonicalize(
            context,
            invalid,
        )

    assert (
        exc.value.code
        ==
        "backlog_policy_rejected"
    )


# ============================================================
# PROVENANCE SURVIVES CANONICALIZATION
# ============================================================


def test_validated_provenance_is_preserved_across_domains() -> None:

    for scenario in scenarios():

        context = make_context(
            scenario
        )

        candidate = make_candidate(
            context,
            scenario,
        )

        result = canonicalize(
            context,
            candidate,
        )

        for source, canonical in zip(
            candidate.epics,
            result.epics,
            strict=True,
        ):

            assert (
                canonical.provenance_refs
                ==
                source.provenance_refs
            )

        for source, canonical in zip(
            candidate.features,
            result.features,
            strict=True,
        ):

            assert (
                canonical.provenance_refs
                ==
                source.provenance_refs
            )

        for source, canonical in zip(
            candidate.stories,
            result.stories,
            strict=True,
        ):

            assert (
                canonical.provenance_refs
                ==
                source.provenance_refs
            )


# ============================================================
# DEPENDENCY CANDIDATES REMAIN HINTS ONLY
# ============================================================


def test_dependency_candidates_are_only_canonical_hint_ids() -> None:

    scenario = scenarios()[0]

    context = make_context(
        scenario
    )

    candidate = make_candidate(
        context,
        scenario,
    )

    result = canonicalize(
        context,
        candidate,
    )

    assert (
        result.stories[0]
        .dependency_hint_ids
        ==
        []
    )

    assert (
        result.stories[1]
        .dependency_hint_ids
        ==
        [
            "US-001",
        ]
    )

    assert all(
        story.dependencies
        ==
        []
        for story
        in result.stories
    )