from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect

import pytest
from pydantic import BaseModel

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
    return importlib.util.find_spec(MODULE) is not None


def skip_until_policy_exists() -> None:
    if not module_exists():
        pytest.skip(
            "Blocked by missing deterministic "
            "MoSCoWPriorityPolicy."
        )


def policy_module():
    skip_until_policy_exists()
    return importlib.import_module(MODULE)


def policy_class():
    return getattr(
        policy_module(),
        "MoSCoWPriorityPolicy",
    )


def result_class():
    return getattr(
        policy_module(),
        "MoSCoWPriorityResultV1",
    )


def decision_class():
    return getattr(
        policy_module(),
        "MoSCoWPriorityDecisionV1",
    )


def error_class():
    return getattr(
        policy_module(),
        "MoSCoWPriorityPolicyError",
    )


def make_context():

    packet = ProjectContextPacketV3(
        project_name="MoSCoW Contract",
        language="en",
        target_region="International",
        industry_user_input="B2B workflow software",

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
        project_id="moscow-contract",
        decision=None,
    )


def make_backlog(
    context,
    *,
    candidate_priority="must",
):

    criterion = CanonicalAcceptanceCriterionV1(
        acceptance_criterion_id="AC-001",
        story_id="US-001",
        statement=(
            "Given a valid request, "
            "when it is reviewed, "
            "then its outcome is recorded."
        ),
        is_testable=True,
        source_ref="workflow:request_review",
    )

    epic = CanonicalEpicV1(
        epic_id="EP-001",
        candidate_key="candidate_epic",
        title="Request Workflow",
        description="Support request review.",
        business_goal=(
            "Support the validated workflow."
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
        description="Review incoming requests.",
        business_value=(
            "Support the validated workflow."
        ),
        provenance_refs=[
            "mvp_scope:Request review",
        ],
    )

    story = CanonicalUserStoryV1(
        story_id="US-001",
        candidate_key="candidate_story",
        epic_id="EP-001",
        feature_id="FE-001",
        actor_ref="Operator",
        title="Review request",
        capability="Review request",
        benefit="record a decision",
        story=(
            "As an Operator, I want to review "
            "a request so that a decision is recorded."
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

        story_points=None,
        dependencies=[],
        dependency_hint_ids=[],
        scope_status="in_scope",
        locked=False,

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

    return CanonicalBacklogV1(
        source_context_hash=(
            context.source_context_hash
        ),

        context_hash=(
            context.context_hash
        ),

        epics=[epic],
        features=[feature],
        stories=[story],
        warnings=[],
    )


def apply_policy(
    context,
    backlog,
):

    return policy_class()().apply(
        context=context,
        backlog=backlog,
    )


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_moscow_priority_policy_module_exists() -> None:

    assert module_exists(), (
        "Missing deterministic Sprint 4 "
        "MoSCoWPriorityPolicy: "
        "app.services.moscow_priority_policy"
    )


# ============================================================
# PUBLIC AUTHORITY
# ============================================================


def test_policy_public_symbols_exist() -> None:

    skip_until_policy_exists()

    module = policy_module()

    for name in (
        "MoSCoWPriorityPolicy",
        "MoSCoWPriorityResultV1",
        "MoSCoWPriorityDecisionV1",
        "MoSCoWPriorityPolicyError",
    ):

        assert hasattr(
            module,
            name,
        )


def test_apply_has_narrow_api() -> None:

    skip_until_policy_exists()

    signature = inspect.signature(
        policy_class().apply
    )

    assert set(
        signature.parameters
    ) == {
        "self",
        "context",
        "backlog",
    }


# ============================================================
# STRICT RESULT / EXPLAINABILITY
# ============================================================


def test_result_models_are_strict_pydantic_models() -> None:

    skip_until_policy_exists()

    for model in (
        result_class(),
        decision_class(),
    ):

        assert issubclass(
            model,
            BaseModel,
        )

        assert (
            model.model_config.get("extra")
            ==
            "forbid"
        )


def test_result_contract_contains_explainability() -> None:

    skip_until_policy_exists()

    assert set(
        result_class().model_fields
    ) == {
        "schema_version",
        "backlog",
        "decisions",
        "must_ratio",
        "warnings",
    }

    assert set(
        decision_class().model_fields
    ) == {
        "story_id",
        "priority",
        "reason_codes",
        "evidence_refs",
    }


# ============================================================
# CANONICAL MOSCOW VOCABULARY
# ============================================================


def test_policy_outputs_only_canonical_moscow_values() -> None:

    skip_until_policy_exists()

    context = make_context()

    result = apply_policy(
        context,
        make_backlog(context),
    )

    assert (
        result.backlog.stories[0].priority
        in {
            "Must",
            "Should",
            "Could",
            "Won't",
        }
    )


# ============================================================
# PRODUCT OWNER SIGNAL REMAINS ADVISORY
# ============================================================


@pytest.mark.parametrize(
    "first_signal,second_signal",
    (
        ("must", "could"),
        ("should", "must"),
        ("could", "wont"),
        ("wont", "must"),
        (
            "unexpected",
            "another unexpected",
        ),
    ),
)
def test_candidate_priority_alone_cannot_control_final_priority(
    first_signal,
    second_signal,
) -> None:

    skip_until_policy_exists()

    context = make_context()

    first = apply_policy(
        context,
        make_backlog(
            context,
            candidate_priority=first_signal,
        ),
    )

    second = apply_policy(
        context,
        make_backlog(
            context,
            candidate_priority=second_signal,
        ),
    )

    assert (
        first.backlog.stories[0].priority
        ==
        second.backlog.stories[0].priority
    )


# ============================================================
# EXPLAINABLE DECISION
# ============================================================


def test_each_story_has_explainable_priority_decision() -> None:

    skip_until_policy_exists()

    context = make_context()

    result = apply_policy(
        context,
        make_backlog(context),
    )

    assert len(result.decisions) == 1

    decision = result.decisions[0]

    assert decision.story_id == "US-001"

    assert decision.priority in {
        "Must",
        "Should",
        "Could",
        "Won't",
    }

    assert decision.reason_codes
    assert decision.evidence_refs


# ============================================================
# DETERMINISM / IMMUTABILITY
# ============================================================


def test_policy_is_deterministic() -> None:

    skip_until_policy_exists()

    context = make_context()
    backlog = make_backlog(context)

    first = apply_policy(
        context,
        backlog,
    )

    second = apply_policy(
        context.model_copy(
            deep=True
        ),
        backlog.model_copy(
            deep=True
        ),
    )

    assert first == second


def test_policy_does_not_mutate_inputs() -> None:

    skip_until_policy_exists()

    context = make_context()
    backlog = make_backlog(context)

    context_before = context.model_dump(
        mode="json"
    )

    backlog_before = backlog.model_dump(
        mode="json"
    )

    apply_policy(
        context,
        backlog,
    )

    assert (
        context.model_dump(
            mode="json"
        )
        ==
        context_before
    )

    assert (
        backlog.model_dump(
            mode="json"
        )
        ==
        backlog_before
    )


# ============================================================
# HASH BINDING
# ============================================================


def test_context_hash_mismatch_fails_closed() -> None:

    skip_until_policy_exists()

    context = make_context()

    stale = make_backlog(
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

        apply_policy(
            context,
            stale,
        )

    assert (
        exc.value.code
        ==
        "context_hash_mismatch"
    )


def test_source_context_hash_mismatch_fails_closed() -> None:

    skip_until_policy_exists()

    context = make_context()

    stale = make_backlog(
        context
    ).model_copy(
        update={
            "source_context_hash":
                "e" * 64,
        },
        deep=True,
    )

    with pytest.raises(
        error_class()
    ) as exc:

        apply_policy(
            context,
            stale,
        )

    assert (
        exc.value.code
        ==
        "source_context_hash_mismatch"
    )


# ============================================================
# NARROW AUTHORITY
# ============================================================


def test_policy_preserves_non_priority_authorities() -> None:

    skip_until_policy_exists()

    context = make_context()
    backlog = make_backlog(context)

    result = apply_policy(
        context,
        backlog,
    )

    output = result.backlog

    assert (
        output.source_context_hash
        ==
        backlog.source_context_hash
    )

    assert (
        output.context_hash
        ==
        backlog.context_hash
    )

    assert output.epics == backlog.epics
    assert output.features == backlog.features

    assert (
        output.stories[0].story_id
        ==
        backlog.stories[0].story_id
    )

    assert (
        output.stories[0].story_points
        ==
        backlog.stories[0].story_points
    )

    assert (
        output.stories[0].dependencies
        ==
        backlog.stories[0].dependencies
    )

    assert (
        output.stories[0].dependency_hint_ids
        ==
        backlog.stories[0].dependency_hint_ids
    )

    assert (
        output.stories[0].locked
        ==
        backlog.stories[0].locked
    )


# ============================================================
# MUST OVERLOAD = SOFT WARNING
# ============================================================


def test_must_overload_is_warning_not_reprioritization() -> None:

    skip_until_policy_exists()

    context = make_context()

    backlog = make_backlog(context)

    original_story = backlog.stories[0]

    stories = [
        original_story.model_copy(
            update={
                "story_id":
                    f"US-{index:03d}",
            },
            deep=True,
        )
        for index
        in range(1, 5)
    ]

    overloaded = backlog.model_copy(
        update={
            "stories":
                stories,
        },
        deep=True,
    )

    result = apply_policy(
        context,
        overloaded,
    )

    must_count = sum(
        1
        for story
        in result.backlog.stories
        if story.priority == "Must"
    )

    if must_count / len(
        result.backlog.stories
    ) > 0.5:

        assert "must_overload" in result.warnings


# ============================================================
# NO EXTERNAL INTELLIGENCE AUTHORITY
# ============================================================


def test_policy_has_no_llm_rag_or_search_authority() -> None:

    skip_until_policy_exists()

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
                node.module or ""
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
            imported.startswith(prefix)
            for prefix
            in forbidden_prefixes
        )


# ============================================================
# LATER AUTHORITIES REMAIN SEPARATE
# ============================================================


@pytest.mark.parametrize(
    "forbidden_name",
    (
        "assign_story_points",
        "build_dependency_graph",
        "assign_sprint",
        "plan_sprints",
        "calculate_velocity",
        "calculate_burndown",
        "build_architecture",
    ),
)
def test_policy_does_not_absorb_later_authorities(
    forbidden_name,
) -> None:

    skip_until_policy_exists()

    assert not hasattr(
        policy_class(),
        forbidden_name,
    )