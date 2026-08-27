from __future__ import annotations

import ast
import inspect
import json
import textwrap

import pytest

from app.agents import product_owner_agent as product_owner_module
from app.agents.product_owner_agent import (
    ProductOwnerAgent,
)
from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
    WorkflowContext,
)
from app.schemas.project_management import (
    CandidateBacklogV1,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


class FakeLLM:
    def __init__(
        self,
        *,
        response=None,
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls = []

    async def invoke(
        self,
        prompt: str,
        task_type: str = "general",
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "task_type": task_type,
            }
        )

        if self.error is not None:
            raise self.error

        return self.response


def make_context():

    packet = ProjectContextPacketV3(
        project_name=(
            "Product Owner Runtime Probe"
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
            project_id="po-runtime-probe",
            decision=None,
        )
    )


def valid_payload(
    context,
):
    return {
        "schema_version": (
            "candidate_backlog_v1"
        ),

        "source_context_hash": (
            context.source_context_hash
        ),

        "context_hash": (
            context.context_hash
        ),

        "epics": [
            {
                "candidate_key": (
                    "epic_operations"
                ),

                "title": (
                    "Core Operations"
                ),

                "description": (
                    "Support the validated "
                    "operational workflow."
                ),

                "business_goal": (
                    "Complete the validated "
                    "request review workflow."
                ),

                "provenance_refs": [
                    "workflow:request_review",
                ],
            },
        ],

        "features": [
            {
                "candidate_key": (
                    "feature_request_review"
                ),

                "epic_key": (
                    "epic_operations"
                ),

                "title": (
                    "Request review"
                ),

                "description": (
                    "Allow the validated actor "
                    "to review incoming requests."
                ),

                "business_value": (
                    "Reduce processing delay."
                ),

                "provenance_refs": [
                    "mvp_scope:Request review",
                ],
            },
        ],

        "stories": [
            {
                "candidate_key": (
                    "story_review_request"
                ),

                "epic_key": (
                    "epic_operations"
                ),

                "feature_key": (
                    "feature_request_review"
                ),

                "actor_ref": "Operator",

                "title": (
                    "Review incoming request"
                ),

                "capability": (
                    "review an incoming request"
                ),

                "benefit": (
                    "reduce processing delays"
                ),

                "story": (
                    "As an Operator, I want to "
                    "review an incoming request "
                    "so that processing delays "
                    "are reduced."
                ),

                "business_value": (
                    "Faster operational processing."
                ),

                "acceptance_criteria": [
                    {
                        "statement": (
                            "Given a pending request, "
                            "when the Operator reviews it, "
                            "then the decision is recorded."
                        ),

                        "candidate_testable": True,

                        "source_ref": (
                            "workflow:request_review"
                        ),
                    },
                ],

                "candidate_priority": "must",

                "candidate_priority_rationale": (
                    "Required by the canonical "
                    "primary workflow."
                ),

                "candidate_complexity": "medium",

                "candidate_complexity_rationale": (
                    "Requires workflow-state handling."
                ),

                "candidate_dependencies": [],

                "provenance_refs": [
                    "actor:Operator",
                    "workflow:request_review",
                ],

                "source_context_hash": (
                    context.source_context_hash
                ),

                "warnings": [],
            },
        ],

        "warnings": [],
    }


def valid_json(
    context,
):
    return json.dumps(
        valid_payload(
            context
        ),
        ensure_ascii=False,
    )


def runtime_has_not_implemented_raise() -> bool:

    source = inspect.getsource(
        ProductOwnerAgent.generate_candidate_backlog
    )

    tree = ast.parse(
        textwrap.dedent(
            source
        )
    )

    for node in ast.walk(
        tree
    ):
        if not isinstance(
            node,
            ast.Raise,
        ):
            continue

        exc = node.exc

        if isinstance(
            exc,
            ast.Call,
        ):
            exc = exc.func

        if (
            isinstance(
                exc,
                ast.Name,
            )
            and exc.id == "NotImplementedError"
        ):
            return True

    return False


def skip_until_runtime_enabled() -> None:

    if runtime_has_not_implemented_raise():
        pytest.skip(
            "Blocked by Product Owner "
            "runtime generation implementation."
        )


def generation_error_class():

    return getattr(
        product_owner_module,
        "ProductOwnerGenerationError",
    )


# ============================================================
# FIRST WRONG LAYER
# ============================================================


@pytest.mark.asyncio
async def test_product_owner_runtime_generation_is_enabled() -> None:

    context = make_context()

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    agent = ProductOwnerAgent(
        llm=provider
    )

    result = await agent.generate_candidate_backlog(
        context=context
    )

    assert isinstance(
        result,
        CandidateBacklogV1,
    )


# ============================================================
# PROVIDER CONTRACT
# ============================================================


@pytest.mark.asyncio
async def test_runtime_uses_injected_provider_once() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    agent = ProductOwnerAgent(
        llm=provider
    )

    await agent.generate_candidate_backlog(
        context=context
    )

    assert len(
        provider.calls
    ) == 1


@pytest.mark.asyncio
async def test_runtime_uses_product_owner_task_type() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    agent = ProductOwnerAgent(
        llm=provider
    )

    await agent.generate_candidate_backlog(
        context=context
    )

    assert (
        provider.calls[0][
            "task_type"
        ]
        ==
        "product_owner_candidate_backlog"
    )


@pytest.mark.asyncio
async def test_runtime_prompt_is_the_deterministic_prompt() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    agent = ProductOwnerAgent(
        llm=provider
    )

    expected_prompt = agent.build_prompt(
        context=context
    )

    await agent.generate_candidate_backlog(
        context=context
    )

    assert (
        provider.calls[0][
            "prompt"
        ]
        ==
        expected_prompt
    )


# ============================================================
# STRUCTURED OUTPUT
# ============================================================


@pytest.mark.asyncio
async def test_runtime_returns_strict_candidate_backlog() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    result = await ProductOwnerAgent(
        llm=provider
    ).generate_candidate_backlog(
        context=context
    )

    assert isinstance(
        result,
        CandidateBacklogV1,
    )

    assert (
        result.schema_version
        ==
        "candidate_backlog_v1"
    )


@pytest.mark.asyncio
async def test_runtime_accepts_markdown_fenced_json_only() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=(
            "```json\n"
            +
            valid_json(
                context
            )
            +
            "\n```"
        )
    )

    result = await ProductOwnerAgent(
        llm=provider
    ).generate_candidate_backlog(
        context=context
    )

    assert isinstance(
        result,
        CandidateBacklogV1,
    )


# ============================================================
# HASH BINDING
# ============================================================


@pytest.mark.asyncio
async def test_runtime_preserves_context_hashes() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    result = await ProductOwnerAgent(
        llm=provider
    ).generate_candidate_backlog(
        context=context
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

    assert all(
        story.source_context_hash
        ==
        context.source_context_hash

        for story
        in result.stories
    )


# ============================================================
# CONTEXT IMMUTABILITY
# ============================================================


@pytest.mark.asyncio
async def test_runtime_does_not_mutate_context() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    before = context.model_dump(
        mode="json"
    )

    provider = FakeLLM(
        response=valid_json(
            context
        )
    )

    await ProductOwnerAgent(
        llm=provider
    ).generate_candidate_backlog(
        context=context
    )

    assert (
        context.model_dump(
            mode="json"
        )
        ==
        before
    )


# ============================================================
# FAILURE CONTRACT
# ============================================================


@pytest.mark.asyncio
async def test_empty_model_response_is_not_fabricated() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response=""
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


@pytest.mark.asyncio
async def test_invalid_json_is_not_fabricated() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        response="{not valid json"
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


@pytest.mark.asyncio
async def test_provider_failure_is_not_replaced_with_fake_backlog() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    provider = FakeLLM(
        error=RuntimeError(
            "all configured models failed"
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "generation_temporarily_unavailable"
    )


@pytest.mark.asyncio
async def test_strict_schema_rejects_final_authority_field() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "stories"
    ][0][
        "story_points"
    ] = 5

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "invalid_model_response"
    )


# ============================================================
# DETERMINISTIC AUTHORITY GATE
# ============================================================


@pytest.mark.asyncio
async def test_wrong_backlog_source_hash_is_rejected() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "source_context_hash"
    ] = (
        "f"
        *
        64
    )

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_wrong_context_hash_is_rejected() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "context_hash"
    ] = (
        "e"
        *
        64
    )

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_wrong_story_source_hash_is_rejected() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "stories"
    ][0][
        "source_context_hash"
    ] = (
        "d"
        *
        64
    )

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_invented_actor_is_rejected() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "stories"
    ][0][
        "actor_ref"
    ] = "Invented CFO"

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_scope_exclusion_cannot_become_positive_story() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "stories"
    ][0][
        "provenance_refs"
    ] = [
        (
            "scope_exclusion:"
            "Automatic payments"
        ),
    ]

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_rag_provenance_has_no_runtime_authority() -> None:

    skip_until_runtime_enabled()

    context = make_context()

    payload = valid_payload(
        context
    )

    payload[
        "stories"
    ][0][
        "provenance_refs"
    ] = [
        "rag:generic benchmark",
    ]

    provider = FakeLLM(
        response=json.dumps(
            payload
        )
    )

    error_type = generation_error_class()

    with pytest.raises(
        error_type
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


# ============================================================
# ARCHITECTURE BOUNDARY
# ============================================================


def test_runtime_does_not_import_startup_evaluator_parser() -> None:

    skip_until_runtime_enabled()

    source = inspect.getsource(
        product_owner_module
    ).casefold()

    assert (
        "startup_evaluator_llm"
        not in source
    )


def test_runtime_does_not_create_direct_provider_specific_clients() -> None:

    skip_until_runtime_enabled()

    source = inspect.getsource(
        product_owner_module
    ).casefold()

    forbidden = (
        "chatgroq",
        "chatgooglegenerativeai",
        "langchain_groq",
        "langchain_google_genai",
    )

    assert all(
        token not in source
        for token in forbidden
    )