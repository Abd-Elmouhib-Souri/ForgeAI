from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.agents.solution_architect_agent import (
    SolutionArchitectAgent,
    SolutionArchitectGenerationError,
)
from app.llm.json_response import (
    JSONResponseError,
    extract_json_object,
)
from app.llm.provider import (
    LLMProvider,
)
from app.schemas.solution_architecture import (
    CandidateSolutionArchitectureV1,
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
)


TASK_TYPE = (
    "solution_architect_candidate_architecture"
)


class FakeLLM:
    def __init__(
        self,
        *,
        response: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls = []

    async def invoke(
        self,
        prompt: str,
        task_type: str,
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "task_type": task_type,
            }
        )

        if self.error is not None:
            raise self.error

        assert self.response is not None

        return self.response


def context() -> SolutionArchitectureContextV1:
    return SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name="Runtime Contract Project",
        sector="Neutral operational system",
        target_region="International",
        target_users=[
            "Operational User",
        ],
        actors=[],
        priority_workflows=[],
        transaction_unit=None,
        positive_mvp_scope=[
            "Process one operational request",
        ],
        explicit_exclusions=[
            "Unrelated marketplace capability",
        ],
        input_data=[
            "request information",
        ],
        output_decision=[
            "review result",
        ],
        human_oversight=[
            "Human final review",
        ],
        maintenance_model=[
            "Organization maintained",
        ],
        assumptions=[],
        forbidden_adjacent_domains=[
            "unrelated marketplace",
        ],
        constraints=[
            "Protect sensitive project information",
        ],
        technical_signals=(
            TechnicalSignalsV1(
                regulatory_context=[
                    "applicable privacy requirements",
                ],
                deployment_constraints=[
                    "managed deployment environment",
                ],
            )
        ),
        upstream_context_fingerprint=(
            "a" * 64
        ),
    )


def valid_candidate_json(
    *,
    fingerprint: str = "b" * 64,
) -> str:
    return (
        "{"
        '"schema_version":'
        '"candidate_solution_architecture_v1",'
        '"source_context_fingerprint":'
        f'"{fingerprint}",'
        '"architecture":{'
        '"style":"contextual modular architecture",'
        '"rationale":["Match the supplied project context."],'
        '"quality_attributes":["maintainability"],'
        '"constraints_addressed":[],'
        '"alternatives":[],'
        '"risks":[],'
        '"conditions":[]'
        "},"
        '"stack":{'
        '"layers":[]'
        "},"
        '"uml_diagrams":[],'
        '"database":null,'
        '"assumptions":[],'
        '"warnings":[],'
        '"confidence":0.74'
        "}"
    )


# =============================================================================
# GREEN CONTROLS
# =============================================================================

def test_control_structural_agent_and_candidate_contract_are_ready():
    assert inspect.isclass(
        SolutionArchitectAgent
    )

    assert inspect.isclass(
        CandidateSolutionArchitectureV1
    )

    assert hasattr(
        SolutionArchitectAgent,
        "generate_candidate_architecture",
    )


def test_control_shared_provider_and_json_gateway_are_ready():
    assert inspect.isclass(
        LLMProvider
    )

    assert inspect.iscoroutinefunction(
        LLMProvider.invoke
    )

    assert callable(
        extract_json_object
    )

    assert issubclass(
        JSONResponseError,
        Exception,
    )


@pytest.mark.asyncio
async def test_control_invalid_input_is_rejected_before_provider_execution():
    fake = FakeLLM(
        response=valid_candidate_json()
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    with pytest.raises(
        TypeError
    ):
        await agent.generate_candidate_architecture(
            context={
                "project_name":
                    "not canonical",
            }
        )

    assert fake.calls == []


# =============================================================================
# PRODUCT RUNTIME CONTRACTS
# =============================================================================

@pytest.mark.asyncio
async def test_runtime_valid_json_uses_one_provider_call_and_returns_candidate():
    source = context()

    before = source.model_dump(
        mode="json"
    )

    fake = FakeLLM(
        response=valid_candidate_json()
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    candidate = (
        await agent
        .generate_candidate_architecture(
            context=source
        )
    )

    assert isinstance(
        candidate,
        CandidateSolutionArchitectureV1,
    )

    assert len(
        fake.calls
    ) == 1

    assert (
        fake.calls[0][
            "task_type"
        ]
        ==
        TASK_TYPE
    )

    assert (
        source.project_name
        in
        fake.calls[0][
            "prompt"
        ]
    )

    assert (
        source.upstream_context_fingerprint
        in
        fake.calls[0][
            "prompt"
        ]
    )

    assert (
        source.model_dump(
            mode="json"
        )
        ==
        before
    )


@pytest.mark.asyncio
async def test_runtime_provider_failure_is_typed_and_fails_closed():
    source = context()

    fake = FakeLLM(
        error=TimeoutError(
            "provider unavailable"
        )
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    with pytest.raises(
        SolutionArchitectGenerationError
    ) as caught:
        await agent.generate_candidate_architecture(
            context=source
        )

    assert (
        caught.value.code
        ==
        "generation_temporarily_unavailable"
    )

    assert len(
        fake.calls
    ) == 1


@pytest.mark.asyncio
async def test_runtime_invalid_json_is_typed_and_does_not_fabricate_candidate():
    fake = FakeLLM(
        response=(
            "This is not JSON and must "
            "not become architecture truth."
        )
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    with pytest.raises(
        SolutionArchitectGenerationError
    ) as caught:
        await agent.generate_candidate_architecture(
            context=context()
        )

    assert (
        caught.value.code
        ==
        "invalid_model_response"
    )

    assert len(
        fake.calls
    ) == 1


@pytest.mark.asyncio
async def test_runtime_invalid_candidate_schema_is_typed_and_fails_closed():
    fake = FakeLLM(
        response=(
            "{"
            '"schema_version":'
            '"candidate_solution_architecture_v1",'
            '"source_context_fingerprint":'
            '"' + ("c" * 64) + '",'
            '"confidence":7.5'
            "}"
        )
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    with pytest.raises(
        SolutionArchitectGenerationError
    ) as caught:
        await agent.generate_candidate_architecture(
            context=context()
        )

    assert (
        caught.value.code
        ==
        "invalid_model_response"
    )

    assert len(
        fake.calls
    ) == 1


@pytest.mark.asyncio
async def test_runtime_context_fingerprint_is_imposed_by_forgeai_not_llm():
    source = context()

    llm_supplied_fingerprint = (
        "f" * 64
    )

    assert (
        llm_supplied_fingerprint
        !=
        source.upstream_context_fingerprint
    )

    fake = FakeLLM(
        response=valid_candidate_json(
            fingerprint=(
                llm_supplied_fingerprint
            )
        )
    )

    agent = SolutionArchitectAgent(
        llm=fake
    )

    candidate = (
        await agent
        .generate_candidate_architecture(
            context=source
        )
    )

    assert (
        candidate.source_context_fingerprint
        ==
        source.upstream_context_fingerprint
    )

    assert (
        candidate.source_context_fingerprint
        !=
        llm_supplied_fingerprint
    )

    assert len(
        fake.calls
    ) == 1


def test_runtime_source_uses_shared_parser_validation_and_no_canonical_authority():
    source_path = Path(
        inspect.getsourcefile(
            SolutionArchitectAgent
        )
    )

    source = source_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    imported_modules = set()
    imported_names = set()
    loaded_names = set()
    attribute_names = set()
    string_constants = set()

    candidate_model_validate_call = False

    for node in ast.walk(
        tree
    ):
        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                imported_modules.add(
                    alias.name
                )

        if isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module:
                imported_modules.add(
                    node.module
                )

            for alias in node.names:
                imported_names.add(
                    alias.name
                )

        if (
            isinstance(
                node,
                ast.Name,
            )
            and
            isinstance(
                node.ctx,
                ast.Load,
            )
        ):
            loaded_names.add(
                node.id
            )

        if isinstance(
            node,
            ast.Attribute,
        ):
            attribute_names.add(
                node.attr
            )

        if (
            isinstance(
                node,
                ast.Constant,
            )
            and
            isinstance(
                node.value,
                str,
            )
        ):
            string_constants.add(
                node.value
            )

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        function = node.func

        if not isinstance(
            function,
            ast.Attribute,
        ):
            continue

        if (
            function.attr
            !=
            "model_validate"
        ):
            continue

        owner = function.value

        if (
            isinstance(
                owner,
                ast.Name,
            )
            and
            owner.id
            ==
            "CandidateSolutionArchitectureV1"
        ):
            candidate_model_validate_call = True

    assert (
        "extract_json_object"
        in imported_names
    )

    assert (
        "JSONResponseError"
        in imported_names
    )

    assert (
        "ValidationError"
        in imported_names
    )

    assert candidate_model_validate_call

    assert (
        "solution_architect_candidate_architecture"
        in string_constants
    )

    semantic_identifiers = (
        imported_names
        |
        loaded_names
        |
        attribute_names
    )

    forbidden_identifiers = {
        "CanonicalSolutionArchitectureV1",
        "candidate_backlog_authority_validator",
        "BacklogPolicyEngine",
        "kroki_client",
        "diagram_renderer",
    }

    assert not (
        semantic_identifiers
        &
        forbidden_identifiers
    )

    for module_name in imported_modules:
        for forbidden in forbidden_identifiers:
            assert not (
                module_name == forbidden
                or
                module_name.endswith(
                    "." + forbidden
                )
            )
