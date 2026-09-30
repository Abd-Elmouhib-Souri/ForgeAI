from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest

from app.llm.json_response import (
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


MODULE_NAME = (
    "app.agents.solution_architect_agent"
)


class FakeLLM:
    """
    Structural fake only.

    S5-D3 must prove prompt construction never performs a provider call.
    """

    def __init__(self) -> None:
        self.calls = []

    async def invoke(
        self,
        prompt,
        task_type,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "task_type": task_type,
            }
        )

        raise AssertionError(
            "LLM provider must not be invoked by structural prompt tests."
        )


def context() -> SolutionArchitectureContextV1:
    return SolutionArchitectureContextV1(
        schema_version=(
            "solution_architecture_context_v1"
        ),
        language="en",
        project_name=(
            "Universal Technical Project"
        ),
        sector=(
            "Operational system"
        ),
        target_region="International",
        target_users=[
            "Operational User",
        ],
        positive_mvp_scope=[
            "Submit an operational request",
            "Review an operational request",
        ],
        explicit_exclusions=[
            "Unrelated marketplace capability",
        ],
        constraints=[
            "Protect sensitive information",
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


def load_module():
    return importlib.import_module(
        MODULE_NAME
    )


def agent_class():
    module = load_module()

    return getattr(
        module,
        "SolutionArchitectAgent",
    )


def error_class():
    module = load_module()

    return getattr(
        module,
        "SolutionArchitectGenerationError",
    )


# =============================================================================
# GREEN CONTROLS
# =============================================================================

def test_control_candidate_schema_is_ready_for_agent_boundary():
    candidate = CandidateSolutionArchitectureV1(
        schema_version=(
            "candidate_solution_architecture_v1"
        ),
        source_context_fingerprint=(
            "b" * 64
        ),
    )

    assert candidate.architecture is None
    assert candidate.stack is None
    assert candidate.uml_diagrams == []
    assert candidate.database is None


def test_control_central_llm_provider_gateway_exists():
    assert inspect.isclass(
        LLMProvider
    )

    assert hasattr(
        LLMProvider,
        "invoke",
    )

    assert inspect.iscoroutinefunction(
        LLMProvider.invoke
    )


def test_control_shared_json_parser_exists():
    parsed = extract_json_object(
        '{"schema_version":"control"}'
    )

    assert parsed == {
        "schema_version":
            "control"
    }


# =============================================================================
# PRODUCT CONTRACTS
# =============================================================================

def test_solution_architect_agent_module_and_public_api_exist():
    cls = agent_class()
    err = error_class()

    assert inspect.isclass(
        cls
    )

    assert issubclass(
        err,
        RuntimeError,
    )

    assert hasattr(
        cls,
        "build_prompt",
    )

    assert hasattr(
        cls,
        "generate_candidate_architecture",
    )

    build_signature = inspect.signature(
        cls.build_prompt
    )

    generation_signature = inspect.signature(
        cls.generate_candidate_architecture
    )

    assert (
        "context"
        in
        build_signature.parameters
    )

    assert (
        "context"
        in
        generation_signature.parameters
    )


def test_agent_uses_provider_composition_and_dependency_injection():
    fake = FakeLLM()

    cls = agent_class()

    agent = cls(
        llm=fake
    )

    assert (
        getattr(
            agent,
            "_llm",
        )
        is fake
    )

    # Sprint 5 follows the modern composition boundary.
    # It must not become a legacy BaseAgent subclass.
    base_names = {
        base.__name__
        for base
        in cls.__mro__[1:]
    }

    assert (
        "BaseAgent"
        not in
        base_names
    )


def test_build_prompt_is_deterministic_immutable_and_provider_free():
    fake = FakeLLM()

    agent = agent_class()(
        llm=fake
    )

    source = context()

    before = source.model_dump(
        mode="json"
    )

    first = agent.build_prompt(
        context=source
    )

    second = agent.build_prompt(
        context=source.model_copy(
            deep=True
        )
    )

    assert isinstance(
        first,
        str,
    )

    assert first.strip()

    assert first == second

    assert fake.calls == []

    assert (
        source.model_dump(
            mode="json"
        )
        ==
        before
    )


def test_prompt_preserves_candidate_only_authority_and_context_binding():
    fake = FakeLLM()

    agent = agent_class()(
        llm=fake
    )

    source = context()

    prompt = agent.build_prompt(
        context=source
    )

    lowered = prompt.lower()

    assert (
        "candidatesolutionarchitecturev1"
        in lowered.replace(
            "_",
            ""
        )
    )

    assert (
        "candidate_solution_architecture_v1"
        in prompt
    )

    assert (
        source.upstream_context_fingerprint
        in prompt
    )

    assert (
        source.project_name
        in prompt
    )

    assert (
        "json"
        in lowered
    )

    assert (
        "plantuml"
        in lowered
    )

    # Candidate layer may propose but must not claim canonical authority.
    assert (
        "candidate"
        in lowered
    )

    assert (
        "canonical"
        in lowered
    )

    # Open architecture/stack semantics must be explicit.
    assert (
        "not_applicable"
        in prompt
    )

    assert (
        "do not force"
        in lowered
        or
        "must not force"
        in lowered
    )

    assert fake.calls == []


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_structural_shell_rejects_invalid_runtime_input_before_provider_execution():
    fake = FakeLLM()

    agent = agent_class()(
        llm=fake
    )

    with pytest.raises(
        TypeError
    ):
        agent.build_prompt(
            context={
                "project_name":
                    "not canonical",
            }
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


def test_agent_source_respects_sprint5_authority_boundaries():
    module = load_module()

    path = Path(
        inspect.getsourcefile(
            module
        )
    )

    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    imported_modules = set()
    imported_names = set()

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

    assert (
        "app.llm.provider"
        in imported_modules
    )

    assert (
        "SolutionArchitectureContextV1"
        in imported_names
    )

    assert (
        "CandidateSolutionArchitectureV1"
        in imported_names
    )

    # The agent consumes the already-built S5 context.
    # It must not bypass it and consume the upstream project packet.
    assert (
        "ProjectContextPacketV3"
        not in imported_names
    )

    # Candidate agent must not construct canonical truth itself.
    assert (
        "CanonicalSolutionArchitectureV1"
        not in imported_names
    )

    # Renderer/provider responsibilities are later layers.
    forbidden_modules = {
        "app.integrations.kroki_client",
        "app.services.diagram_renderer",
    }

    assert not (
        imported_modules
        &
        forbidden_modules
    )
