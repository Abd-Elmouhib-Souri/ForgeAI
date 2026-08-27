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
    CandidateBacklogV1,
    ProjectManagementContextV1,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


MODULE_NAME = (
    "app.agents."
    "product_owner_agent"
)


def module_exists() -> bool:

    return (
        importlib.util.find_spec(
            MODULE_NAME
        )
        is not None
    )


def skip_until_agent_exists() -> None:

    if not module_exists():

        pytest.skip(
            "Blocked by Sprint 4 "
            "AI Product Owner agent."
        )


def module():

    return importlib.import_module(
        MODULE_NAME
    )


def agent_class():

    return getattr(
        module(),
        "ProductOwnerAgent",
    )


def make_context():

    packet = ProjectContextPacketV3(
        project_name="PO Authority Probe",

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

    return (
        project_management_context_builder.build(
            packet=packet,
            project_id="po-probe",
            decision=None,
        )
    )


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_product_owner_agent_module_exists() -> None:

    assert module_exists(), (
        "Missing Sprint 4 AI Product Owner agent: "
        "app.agents.product_owner_agent"
    )


# ============================================================
# TYPE / ROLE CONTRACT
# ============================================================


def test_product_owner_agent_class_exists() -> None:

    skip_until_agent_exists()

    cls = agent_class()

    assert inspect.isclass(
        cls
    )


def test_product_owner_agent_has_candidate_only_role() -> None:

    skip_until_agent_exists()

    cls = agent_class()

    assert hasattr(
        cls,
        "generate_candidate_backlog",
    )


# ============================================================
# NARROW INPUT API
# ============================================================


def test_product_owner_generation_api_accepts_pm_context_only() -> None:

    skip_until_agent_exists()

    signature = inspect.signature(
        agent_class().generate_candidate_backlog
    )

    parameters = set(
        signature.parameters
    )

    # self + canonical PM context.
    assert parameters == {
        "self",
        "context",
    }

    forbidden = {
        "description",
        "raw_description",
        "project",
        "packet",
        "project_context",
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


def test_product_owner_input_annotation_is_pm_context() -> None:

    skip_until_agent_exists()

    hints = inspect.get_annotations(
        agent_class().generate_candidate_backlog,
        eval_str=True,
    )

    assert (
        hints.get(
            "context"
        )
        is
        ProjectManagementContextV1
    )


# ============================================================
# OUTPUT CONTRACT
# ============================================================


def test_product_owner_output_annotation_is_candidate_backlog() -> None:

    skip_until_agent_exists()

    hints = inspect.get_annotations(
        agent_class().generate_candidate_backlog,
        eval_str=True,
    )

    return_type = hints.get(
        "return"
    )

    assert (
        return_type
        is CandidateBacklogV1
        or (
            getattr(
                return_type,
                "__args__",
                ()
            )
            and CandidateBacklogV1
            in return_type.__args__
        )
    )


# ============================================================
# NO CANONICAL BACKLOG AUTHORITY
# ============================================================


@pytest.mark.parametrize(
    "forbidden_name",
    (
        "story_points",
        "assign_story_points",
        "canonical_priority",
        "assign_priority",
        "assign_sprint",
        "sprint_number",
        "canonical_ids",
        "assign_canonical_ids",
        "locked",
        "lock_story",
        "architecture",
        "tech_stack",
        "database_schema",
    ),
)
def test_product_owner_does_not_expose_final_authority_methods(
    forbidden_name,
) -> None:

    skip_until_agent_exists()

    cls = agent_class()

    assert not hasattr(
        cls,
        forbidden_name,
    )


# ============================================================
# NO RAW INTELLIGENCE DEPENDENCIES
# ============================================================


def test_product_owner_module_has_no_direct_rag_search_or_archetype_imports() -> None:

    skip_until_agent_exists()

    source = inspect.getsource(
        module()
    )

    forbidden_fragments = (
        "project_intelligence",
        "search_gateway",
        "local_market_search",
        "forgecrawler",
        "forge_crawler",
        "retriever",
        "vectorstore",
        "chromadb",
        "query_planner",
        "project_archetype",
        "archetype_resolver",
    )

    lowered = source.casefold()

    leaked = [
        fragment
        for fragment
        in forbidden_fragments
        if fragment.casefold()
        in lowered
    ]

    assert leaked == []


# ============================================================
# NO POLICY ENGINE INSIDE PRODUCT OWNER
# ============================================================


def test_product_owner_does_not_embed_backlog_policy_engine() -> None:

    skip_until_agent_exists()

    source = inspect.getsource(
        module()
    ).casefold()

    assert (
        "backlogpolicyengine"
        not in source
    )

    assert (
        "backlog_policy_engine"
        not in source
    )


# ============================================================
# PROMPT CONTRACT SURFACE
# ============================================================


def test_product_owner_exposes_prompt_builder() -> None:

    skip_until_agent_exists()

    cls = agent_class()

    assert hasattr(
        cls,
        "build_prompt",
    )


def test_prompt_builder_accepts_only_pm_context() -> None:

    skip_until_agent_exists()

    signature = inspect.signature(
        agent_class().build_prompt
    )

    assert set(
        signature.parameters
    ) == {
        "self",
        "context",
    }


# ============================================================
# CONTEXT IMMUTABILITY CONTRACT
# ============================================================


def test_product_owner_contract_uses_immutable_context_semantics() -> None:

    skip_until_agent_exists()

    context = make_context()

    before = context.model_dump(
        mode="json"
    )

    # The existence of the agent must not require mutating
    # the canonical context simply to build its prompt.
    #
    # No provider call occurs here.
    try:
        instance = agent_class()()

    except TypeError:
        pytest.skip(
            "Constructor requires provider injection; "
            "runtime contract will cover that separately."
        )

    instance.build_prompt(
        context=context,
    )

    assert (
        context.model_dump(
            mode="json"
        )
        ==
        before
    )


# ============================================================
# HASHES MUST BE REPRESENTED IN PROMPT CONTRACT
# ============================================================


def test_product_owner_prompt_contains_context_hash_bindings() -> None:

    skip_until_agent_exists()

    context = make_context()

    try:
        instance = agent_class()()

    except TypeError:
        pytest.skip(
            "Constructor requires provider injection; "
            "runtime prompt contract follows."
        )

    prompt = instance.build_prompt(
        context=context,
    )

    text = str(
        prompt
    )

    assert (
        context.source_context_hash
        in text
    )

    assert (
        context.context_hash
        in text
    )


# ============================================================
# EXCLUSIONS / UNKNOWN AUTHORITY MUST BE PRESENT IN PROMPT
# ============================================================


def test_product_owner_prompt_contains_negative_scope_guardrails() -> None:

    skip_until_agent_exists()

    context = make_context()

    try:
        instance = agent_class()()

    except TypeError:
        pytest.skip(
            "Constructor requires provider injection; "
            "runtime prompt contract follows."
        )

    prompt = instance.build_prompt(
        context=context,
    )

    text = str(
        prompt
    ).casefold()

    assert (
        "automatic payments"
        in text
    )

    assert (
        "scope_exclusions"
        in text
        or "scope exclusions"
        in text
    )


# ============================================================
# PRODUCT OWNER MUST REMAIN CANDIDATE-ONLY
# ============================================================


def test_candidate_backlog_model_still_owns_no_final_authority() -> None:

    fields = set(
        CandidateBacklogV1.model_fields
    )

    assert "story_points" not in fields
    assert "priority" not in fields
    assert "sprints" not in fields
    assert "canonical_ids" not in fields