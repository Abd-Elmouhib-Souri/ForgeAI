from __future__ import annotations

import ast
import importlib
import inspect
import re

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


SCHEMA_MODULE = (
    "app.schemas.project_management"
)

POLICY_MODULE = (
    "app.services.backlog_policy_engine"
)

CANONICAL_MODELS = (
    "CanonicalAcceptanceCriterionV1",
    "CanonicalEpicV1",
    "CanonicalFeatureV1",
    "CanonicalUserStoryV1",
    "CanonicalBacklogV1",
)


def schema_module():
    return importlib.import_module(
        SCHEMA_MODULE
    )


def policy_module():
    return importlib.import_module(
        POLICY_MODULE
    )


def canonical_schema_exists() -> bool:

    module = schema_module()

    return all(
        hasattr(
            module,
            name,
        )
        for name
        in CANONICAL_MODELS
    )


def canonicalize_exists() -> bool:

    return hasattr(
        BacklogPolicyEngine,
        "canonicalize",
    )


def canonicalization_error_exists() -> bool:

    return hasattr(
        policy_module(),
        "BacklogPolicyCanonicalizationError",
    )


def canonical_authority_exists() -> bool:

    return (
        canonical_schema_exists()
        and canonicalize_exists()
        and canonicalization_error_exists()
    )


def skip_until_canonical_authority_exists() -> None:

    if not canonical_authority_exists():

        pytest.skip(
            "Blocked by missing CanonicalBacklogV1 "
            "projection in BacklogPolicyEngine."
        )


def canonical_models():

    skip_until_canonical_authority_exists()

    module = schema_module()

    return {
        name: getattr(
            module,
            name,
        )
        for name in CANONICAL_MODELS
    }


def canonical_backlog_class():

    return canonical_models()[
        "CanonicalBacklogV1"
    ]


def error_class():

    skip_until_canonical_authority_exists()

    return getattr(
        policy_module(),
        "BacklogPolicyCanonicalizationError",
    )


def make_context():

    packet = ProjectContextPacketV3(
        project_name="Canonical Backlog Contract",

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

    return project_management_context_builder.build(
        packet=packet,
        project_id=(
            "canonical-backlog-contract"
        ),
        decision=None,
    )


def make_acceptance(
    statement: str,
):

    return CandidateAcceptanceCriterionV1(
        statement=statement,

        candidate_testable=True,

        source_ref=(
            "workflow:request_review"
        ),
    )


def make_epic(
    *,
    key: str,
    title: str,
):

    return CandidateEpicV1(
        candidate_key=key,

        title=title,

        description=(
            f"{title} capability group."
        ),

        business_goal=(
            "Support the validated workflow."
        ),

        provenance_refs=[
            "workflow:request_review",
        ],
    )


def make_feature(
    *,
    key: str,
    epic_key: str,
    title: str,
):

    return CandidateFeatureV1(
        candidate_key=key,

        epic_key=epic_key,

        title=title,

        description=(
            f"{title} capability."
        ),

        business_value=(
            "Support the validated MVP."
        ),

        provenance_refs=[
            "mvp_scope:Request review",
        ],
    )


def make_story(
    context,
    *,
    key: str,
    epic_key: str,
    feature_key: str,
    title: str,
    story_text: str,
    criteria,
    dependencies=None,
    candidate_priority="must",
    candidate_complexity="medium",
):

    return CandidateUserStoryV1(
        candidate_key=key,

        epic_key=epic_key,

        feature_key=feature_key,

        actor_ref="Operator",

        title=title,

        capability=title,

        benefit=(
            "complete the validated workflow"
        ),

        story=story_text,

        business_value=(
            "Support the validated "
            "operational outcome."
        ),

        acceptance_criteria=criteria,

        candidate_priority=(
            candidate_priority
        ),

        candidate_priority_rationale=(
            "Advisory Product Owner input."
        ),

        candidate_complexity=(
            candidate_complexity
        ),

        candidate_complexity_rationale=(
            "Advisory Product Owner input."
        ),

        candidate_dependencies=(
            dependencies
            if dependencies is not None
            else []
        ),

        provenance_refs=[
            "actor:Operator",
            "workflow:request_review",
            "mvp_scope:Request review",
        ],

        source_context_hash=(
            context.source_context_hash
        ),

        warnings=[],
    )


def make_candidate(
    context,
):

    return CandidateBacklogV1(
        source_context_hash=(
            context.source_context_hash
        ),

        context_hash=(
            context.context_hash
        ),

        epics=[
            make_epic(
                key="candidate_epic_alpha",
                title="Request Intake",
            ),

            make_epic(
                key="candidate_epic_beta",
                title="Request Decision",
            ),
        ],

        features=[
            make_feature(
                key="candidate_feature_alpha",
                epic_key="candidate_epic_alpha",
                title="Capture request",
            ),

            make_feature(
                key="candidate_feature_beta",
                epic_key="candidate_epic_beta",
                title="Review request",
            ),
        ],

        stories=[
            make_story(
                context,
                key="candidate_story_alpha",
                epic_key="candidate_epic_alpha",
                feature_key=(
                    "candidate_feature_alpha"
                ),
                title="Capture request",
                story_text=(
                    "As an Operator, I want to "
                    "capture an incoming request "
                    "so that it can be reviewed."
                ),
                criteria=[
                    make_acceptance(
                        "Given a new request, "
                        "when it is captured, "
                        "then its information is recorded."
                    ),
                ],
            ),

            make_story(
                context,
                key="candidate_story_beta",
                epic_key="candidate_epic_beta",
                feature_key=(
                    "candidate_feature_beta"
                ),
                title="Review request",
                story_text=(
                    "As an Operator, I want to "
                    "review a captured request "
                    "so that a decision is recorded."
                ),
                criteria=[
                    make_acceptance(
                        "Given a captured request, "
                        "when it is reviewed, "
                        "then the decision is recorded."
                    ),

                    make_acceptance(
                        "Given a completed review, "
                        "when the decision is saved, "
                        "then the request has a "
                        "recorded outcome."
                    ),
                ],
                dependencies=[
                    "candidate_story_alpha",
                ],
            ),
        ],

        warnings=[],
    )


def canonicalize(
    context,
    candidate,
):

    return BacklogPolicyEngine().canonicalize(
        context=context,
        candidate=candidate,
    )


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_backlog_policy_engine_canonical_authority_exists() -> None:

    assert canonical_authority_exists(), (
        "Missing deterministic CanonicalBacklogV1 "
        "projection authority in BacklogPolicyEngine."
    )


# ============================================================
# TRUE AUTHORITY SURFACE
# ============================================================


def test_no_parallel_canonical_backlog_service_is_required() -> None:

    skip_until_canonical_authority_exists()

    assert (
        importlib.util.find_spec(
            "app.services.canonical_backlog_builder"
        )
        is None
    )


def test_canonicalize_has_narrow_api() -> None:

    skip_until_canonical_authority_exists()

    signature = inspect.signature(
        BacklogPolicyEngine.canonicalize
    )

    assert set(
        signature.parameters
    ) == {
        "self",
        "context",
        "candidate",
    }


def test_existing_evaluate_api_is_preserved() -> None:

    signature = inspect.signature(
        BacklogPolicyEngine.evaluate
    )

    assert set(
        signature.parameters
    ) == {
        "self",
        "context",
        "candidate",
    }


# ============================================================
# CANONICAL SCHEMA
# ============================================================


def test_canonical_models_are_strict() -> None:

    skip_until_canonical_authority_exists()

    for model in canonical_models().values():

        assert (
            model.model_config.get(
                "extra"
            )
            ==
            "forbid"
        )


def test_canonical_acceptance_shape() -> None:

    skip_until_canonical_authority_exists()

    model = canonical_models()[
        "CanonicalAcceptanceCriterionV1"
    ]

    assert set(
        model.model_fields
    ) == {
        "acceptance_criterion_id",
        "story_id",
        "statement",
        "is_testable",
        "source_ref",
    }


def test_canonical_epic_shape() -> None:

    skip_until_canonical_authority_exists()

    model = canonical_models()[
        "CanonicalEpicV1"
    ]

    assert set(
        model.model_fields
    ) == {
        "epic_id",
        "candidate_key",
        "title",
        "description",
        "business_goal",
        "provenance_refs",
    }


def test_canonical_feature_shape() -> None:

    skip_until_canonical_authority_exists()

    model = canonical_models()[
        "CanonicalFeatureV1"
    ]

    assert set(
        model.model_fields
    ) == {
        "feature_id",
        "candidate_key",
        "epic_id",
        "title",
        "description",
        "business_value",
        "provenance_refs",
    }


def test_canonical_story_shape_is_future_policy_ready() -> None:

    skip_until_canonical_authority_exists()

    model = canonical_models()[
        "CanonicalUserStoryV1"
    ]

    assert set(
        model.model_fields
    ) == {
        "story_id",
        "candidate_key",
        "epic_id",
        "feature_id",
        "actor_ref",
        "title",
        "capability",
        "benefit",
        "story",
        "business_value",
        "acceptance_criteria",
        "candidate_priority",
        "candidate_priority_rationale",
        "priority",
        "candidate_complexity",
        "candidate_complexity_rationale",
        "story_points",
        "dependencies",
        "dependency_hint_ids",
        "scope_status",
        "locked",
        "provenance_refs",
        "source_context_hash",
        "warnings",
    }


def test_canonical_backlog_shape() -> None:

    skip_until_canonical_authority_exists()

    model = canonical_models()[
        "CanonicalBacklogV1"
    ]

    assert set(
        model.model_fields
    ) == {
        "schema_version",
        "source_context_hash",
        "context_hash",
        "epics",
        "features",
        "stories",
        "warnings",
    }


# ============================================================
# VALID CANONICALIZATION
# ============================================================


def test_admitted_candidate_becomes_canonical_backlog() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    result = canonicalize(
        context,
        make_candidate(
            context
        ),
    )

    assert isinstance(
        result,
        canonical_backlog_class(),
    )

    assert (
        result.schema_version
        ==
        "canonical_backlog_v1"
    )

    assert (
        result.source_context_hash
        ==
        context.source_context_hash
    )

    assert (
        result.context_hash
        ==
        context.context_hash
    )


# ============================================================
# CANONICAL IDS
# ============================================================


def test_canonical_ids_are_backend_controlled_and_deterministic() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    result = canonicalize(
        context,
        make_candidate(
            context
        ),
    )

    assert [
        item.epic_id
        for item in result.epics
    ] == [
        "EP-001",
        "EP-002",
    ]

    assert [
        item.feature_id
        for item in result.features
    ] == [
        "FE-001",
        "FE-002",
    ]

    assert [
        item.story_id
        for item in result.stories
    ] == [
        "US-001",
        "US-002",
    ]

    acceptance_ids = [
        item.acceptance_criterion_id
        for story in result.stories
        for item in story.acceptance_criteria
    ]

    assert acceptance_ids == [
        "AC-001",
        "AC-002",
        "AC-003",
    ]


def test_canonical_id_formats() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    result = canonicalize(
        context,
        make_candidate(
            context
        ),
    )

    patterns = {
        "epic":
            re.compile(
                r"^EP-\d{3}$"
            ),

        "feature":
            re.compile(
                r"^FE-\d{3}$"
            ),

        "story":
            re.compile(
                r"^US-\d{3}$"
            ),

        "acceptance":
            re.compile(
                r"^AC-\d{3}$"
            ),
    }

    assert all(
        patterns["epic"].fullmatch(
            item.epic_id
        )
        for item in result.epics
    )

    assert all(
        patterns["feature"].fullmatch(
            item.feature_id
        )
        for item in result.features
    )

    assert all(
        patterns["story"].fullmatch(
            item.story_id
        )
        for item in result.stories
    )

    assert all(
        patterns["acceptance"].fullmatch(
            criterion.acceptance_criterion_id
        )
        for story in result.stories
        for criterion
        in story.acceptance_criteria
    )


# ============================================================
# HIERARCHY
# ============================================================


def test_canonical_hierarchy_uses_canonical_ids() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    result = canonicalize(
        context,
        make_candidate(
            context
        ),
    )

    assert (
        result.features[0].epic_id
        ==
        "EP-001"
    )

    assert (
        result.features[1].epic_id
        ==
        "EP-002"
    )

    assert (
        result.stories[0].epic_id
        ==
        "EP-001"
    )

    assert (
        result.stories[0].feature_id
        ==
        "FE-001"
    )

    assert (
        result.stories[1].epic_id
        ==
        "EP-002"
    )

    assert (
        result.stories[1].feature_id
        ==
        "FE-002"
    )


def test_acceptance_criteria_reference_canonical_story_ids() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    result = canonicalize(
        context,
        make_candidate(
            context
        ),
    )

    assert all(
        item.story_id
        ==
        "US-001"
        for item
        in result.stories[0].acceptance_criteria
    )

    assert all(
        item.story_id
        ==
        "US-002"
        for item
        in result.stories[1].acceptance_criteria
    )


# ============================================================
# DEPENDENCY HINTS ≠ DEPENDENCY GRAPH
# ============================================================


def test_candidate_dependencies_become_hint_ids_only() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    result = canonicalize(
        context,
        make_candidate(
            context
        ),
    )

    assert (
        result.stories[0].dependency_hint_ids
        ==
        []
    )

    assert (
        result.stories[1].dependency_hint_ids
        ==
        [
            "US-001",
        ]
    )

    assert (
        result.stories[0].dependencies
        ==
        []
    )

    assert (
        result.stories[1].dependencies
        ==
        []
    )


# ============================================================
# ADVISORY DATA PRESERVED, FINAL POLICY UNDECIDED
# ============================================================


def test_candidate_advisory_values_are_preserved_but_not_promoted() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    candidate = make_candidate(
        context
    )

    result = canonicalize(
        context,
        candidate,
    )

    for source, canonical in zip(
        candidate.stories,
        result.stories,
        strict=True,
    ):

        assert (
            canonical.candidate_priority
            ==
            source.candidate_priority
        )

        assert (
            canonical.candidate_priority_rationale
            ==
            source.candidate_priority_rationale
        )

        assert (
            canonical.candidate_complexity
            ==
            source.candidate_complexity
        )

        assert (
            canonical.candidate_complexity_rationale
            ==
            source.candidate_complexity_rationale
        )

        assert canonical.priority is None
        assert canonical.story_points is None

        assert canonical.scope_status == "in_scope"
        assert canonical.locked is False


# ============================================================
# CANDIDATE KEYS = TRACEABILITY ONLY
# ============================================================


def test_candidate_keys_are_not_canonical_ids() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    candidate = make_candidate(
        context
    )

    result = canonicalize(
        context,
        candidate,
    )

    candidate_keys = {
        item.candidate_key
        for item in candidate.epics
    }

    candidate_keys.update(
        item.candidate_key
        for item in candidate.features
    )

    candidate_keys.update(
        item.candidate_key
        for item in candidate.stories
    )

    canonical_ids = {
        item.epic_id
        for item in result.epics
    }

    canonical_ids.update(
        item.feature_id
        for item in result.features
    )

    canonical_ids.update(
        item.story_id
        for item in result.stories
    )

    assert not (
        candidate_keys
        &
        canonical_ids
    )


# ============================================================
# DETERMINISM / IMMUTABILITY
# ============================================================


def test_same_admitted_backlog_produces_same_canonical_output() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    candidate = make_candidate(
        context
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


def test_canonicalization_does_not_mutate_inputs() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    candidate = make_candidate(
        context
    )

    context_before = context.model_dump(
        mode="json"
    )

    candidate_before = candidate.model_dump(
        mode="json"
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
# EXISTING POLICY GATE REMAINS MANDATORY
# ============================================================


def test_stale_candidate_is_rejected_before_canonicalization() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    stale = make_candidate(
        context
    ).model_copy(
        update={
            "context_hash":
                "f" * 64,
        },
        deep=True,
    )

    with pytest.raises(
        error_class()
    ) as exc:

        canonicalize(
            context,
            stale,
        )

    assert (
        getattr(
            exc.value,
            "code",
            None,
        )
        ==
        "backlog_policy_rejected"
    )


def test_structurally_invalid_candidate_is_rejected() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    candidate = make_candidate(
        context
    )

    invalid_story = (
        candidate.stories[0].model_copy(
            update={
                "feature_key":
                    "missing_feature",
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
        error_class()
    ) as exc:

        canonicalize(
            context,
            invalid,
        )

    assert (
        getattr(
            exc.value,
            "code",
            None,
        )
        ==
        "backlog_policy_rejected"
    )


# ============================================================
# PROVENANCE
# ============================================================


def test_validated_provenance_is_preserved() -> None:

    skip_until_canonical_authority_exists()

    context = make_context()

    candidate = make_candidate(
        context
    )

    result = canonicalize(
        context,
        candidate,
    )

    assert (
        result.epics[0].provenance_refs
        ==
        candidate.epics[0].provenance_refs
    )

    assert (
        result.features[0].provenance_refs
        ==
        candidate.features[0].provenance_refs
    )

    assert (
        result.stories[0].provenance_refs
        ==
        candidate.stories[0].provenance_refs
    )

    assert (
        result.stories[0]
        .acceptance_criteria[0]
        .source_ref
        ==
        candidate.stories[0]
        .acceptance_criteria[0]
        .source_ref
    )


# ============================================================
# NO EXTERNAL INTELLIGENCE / NO LATER PLANNING AUTHORITY
# ============================================================


def test_canonicalization_has_no_external_intelligence_authority() -> None:

    skip_until_canonical_authority_exists()

    source = inspect.getsource(
        policy_module()
    )

    tree = ast.parse(
        source
    )

    imports = []

    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            imports.append(
                node.module
                or ""
            )

        elif isinstance(
            node,
            ast.Import,
        ):

            imports.extend(
                alias.name
                for alias
                in node.names
            )

    forbidden_prefixes = (
        "app.agents",
        "app.rag",
        "app.web_search",
        "langchain",
        "langgraph",
        "google",
        "groq",
    )

    for imported in imports:

        assert not any(
            imported.startswith(
                prefix
            )
            for prefix
            in forbidden_prefixes
        )


@pytest.mark.parametrize(
    "forbidden_name",
    (
        "assign_priority",
        "assign_story_points",
        "assign_sprint",
        "plan_sprints",
        "calculate_velocity",
        "calculate_burndown",
        "build_dependency_graph",
    ),
)
def test_backlog_policy_does_not_absorb_later_authorities(
    forbidden_name,
) -> None:

    skip_until_canonical_authority_exists()

    assert not hasattr(
        BacklogPolicyEngine,
        forbidden_name,
    )