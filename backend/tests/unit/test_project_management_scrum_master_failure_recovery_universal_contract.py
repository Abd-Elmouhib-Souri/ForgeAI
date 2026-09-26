from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import app.services.project_management_plan_service as pm_module

from app.agents.product_owner_agent import (
    ProductOwnerAgent,
)

from app.agents.scrum_master_agent import (
    AIScrumMasterAgent,
    ScrumMasterGenerationError,
)

from app.schemas.project_management import (
    ScrumMasterAdviceV1,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)


class _StopAfterAdvice(RuntimeError):
    pass


RECOVERABLE_ADVISORY_ERRORS = {
    "generation_temporarily_unavailable":
        "scrum_master_advice_temporarily_unavailable",

    "invalid_model_response":
        "scrum_master_advice_invalid_model_response",

    "advice_authority_rejected":
        "scrum_master_advice_authority_rejected",
}


def _wire_pipeline_to_scrum_boundary(
    monkeypatch: pytest.MonkeyPatch,
    service: ProjectManagementPlanService,
):
    """
    Isolate only the Scrum Master recovery boundary.

    Every deterministic upstream authority is represented by a stable
    sentinel so this contract tests orchestration semantics, not one
    project, provider, country, sector or backlog shape.
    """

    context = SimpleNamespace(language="fr")
    candidate = object()
    canonical = object()
    prioritized = object()

    estimated = SimpleNamespace(
        source_context_hash="src-neutral",
        context_hash="ctx-neutral",
    )

    graph = object()

    monkeypatch.setattr(
        service,
        "_build_context",
        lambda **_: context,
    )

    async def generate_candidate(
        self: ProductOwnerAgent,
        current_context: Any,
    ) -> Any:
        assert current_context is context
        return candidate

    monkeypatch.setattr(
        ProductOwnerAgent,
        "generate_candidate_backlog",
        generate_candidate,
    )

    monkeypatch.setattr(
        pm_module.backlog_policy_engine,
        "canonicalize",
        lambda current_context, current_candidate: (
            canonical
            if (
                current_context is context
                and current_candidate is candidate
            )
            else (_ for _ in ()).throw(
                AssertionError(
                    "Unexpected canonicalization input."
                )
            )
        ),
    )

    monkeypatch.setattr(
        service._priority_policy,
        "apply",
        lambda current_context, current_backlog: (
            SimpleNamespace(
                backlog=prioritized,
                warnings=[],
            )
            if (
                current_context is context
                and current_backlog is canonical
            )
            else (_ for _ in ()).throw(
                AssertionError(
                    "Unexpected priority input."
                )
            )
        ),
    )

    monkeypatch.setattr(
        service._story_point_policy,
        "apply",
        lambda current_context, current_backlog: (
            SimpleNamespace(
                backlog=estimated
            )
            if (
                current_context is context
                and current_backlog is prioritized
            )
            else (_ for _ in ()).throw(
                AssertionError(
                    "Unexpected Story Point input."
                )
            )
        ),
    )

    monkeypatch.setattr(
        service._dependency_builder,
        "build",
        lambda current_backlog: (
            SimpleNamespace(
                graph=graph
            )
            if current_backlog is estimated
            else (_ for _ in ()).throw(
                AssertionError(
                    "Unexpected dependency input."
                )
            )
        ),
    )

    return (
        estimated,
        graph,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "error_code",
        "expected_warning",
    ),
    list(
        RECOVERABLE_ADVISORY_ERRORS.items()
    ),
)
async def test_untrusted_scrum_advice_degrades_to_empty_advisory(
    monkeypatch: pytest.MonkeyPatch,
    error_code: str,
    expected_warning: str,
) -> None:
    """
    Scrum Master advice is non-canonical and advisory.

    Provider unavailability, invalid model output or rejected model
    advice must never fabricate advice and must never prevent the
    deterministic Sprint planner from producing the plan.
    """

    service = ProjectManagementPlanService()

    estimated, graph = (
        _wire_pipeline_to_scrum_boundary(
            monkeypatch,
            service,
        )
    )

    async def reject_advice(
        self: AIScrumMasterAgent,
        backlog: Any,
        dependency_graph: Any,
        planning_settings: Any,
    ) -> Any:
        assert backlog is estimated
        assert dependency_graph is graph

        raise ScrumMasterGenerationError(
            error_code,
            "Synthetic untrusted Scrum Master advice.",
        )

    monkeypatch.setattr(
        AIScrumMasterAgent,
        "generate_advice",
        reject_advice,
    )

    def stop_at_planner(
        backlog: Any,
        dependency_graph: Any,
        planning_settings: Any,
        advice: Any,
    ) -> Any:
        assert backlog is estimated
        assert dependency_graph is graph

        assert isinstance(
            advice,
            ScrumMasterAdviceV1,
        )

        assert (
            advice.source_context_hash
            ==
            estimated.source_context_hash
        )

        assert (
            advice.context_hash
            ==
            estimated.context_hash
        )

        assert advice.recommendations == []

        assert (
            expected_warning
            in advice.warnings
        )

        raise _StopAfterAdvice()

    monkeypatch.setattr(
        service._planner,
        "plan",
        stop_at_planner,
    )

    with pytest.raises(
        _StopAfterAdvice
    ):
        await service.generate(
            project_id=101,
            analysis_data={},
            settings=service.default_settings().model_copy(
                update={
                    "sprint_count_mode": "manual",
                },
                deep=True,
            ),
        )


@pytest.mark.asyncio
async def test_canonical_binding_mismatch_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A canonical input binding mismatch is not an optional-advice
    failure. It signals inconsistent authoritative inputs and must
    therefore remain fail-closed.
    """

    service = ProjectManagementPlanService()

    estimated, graph = (
        _wire_pipeline_to_scrum_boundary(
            monkeypatch,
            service,
        )
    )

    planner_called = False

    async def reject_binding(
        self: AIScrumMasterAgent,
        backlog: Any,
        dependency_graph: Any,
        planning_settings: Any,
    ) -> Any:
        assert backlog is estimated
        assert dependency_graph is graph

        raise ScrumMasterGenerationError(
            "canonical_binding_mismatch",
            "Synthetic canonical input mismatch.",
        )

    monkeypatch.setattr(
        AIScrumMasterAgent,
        "generate_advice",
        reject_binding,
    )

    def planner_must_not_run(*args, **kwargs):
        nonlocal planner_called
        planner_called = True

        raise AssertionError(
            "Planner must not run after canonical binding mismatch."
        )

    monkeypatch.setattr(
        service._planner,
        "plan",
        planner_must_not_run,
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as captured:

        await service.generate(
            project_id=202,
            analysis_data={},
            settings=service.default_settings().model_copy(
                update={
                    "sprint_count_mode": "manual",
                },
                deep=True,
            ),
        )

    assert (
        captured.value.code
        ==
        "canonical_binding_mismatch"
    )

    assert planner_called is False


@pytest.mark.asyncio
async def test_unknown_scrum_failure_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Recovery is intentionally allow-listed.

    Unknown failures may represent programming or integrity defects
    and must not be converted into a fake successful plan.
    """

    service = ProjectManagementPlanService()

    estimated, graph = (
        _wire_pipeline_to_scrum_boundary(
            monkeypatch,
            service,
        )
    )

    planner_called = False

    async def unknown_failure(
        self: AIScrumMasterAgent,
        backlog: Any,
        dependency_graph: Any,
        planning_settings: Any,
    ) -> Any:
        assert backlog is estimated
        assert dependency_graph is graph

        raise ScrumMasterGenerationError(
            "internal_contract_bug",
            "Synthetic internal Scrum Master defect.",
        )

    monkeypatch.setattr(
        AIScrumMasterAgent,
        "generate_advice",
        unknown_failure,
    )

    def planner_must_not_run(*args, **kwargs):
        nonlocal planner_called
        planner_called = True

        raise AssertionError(
            "Planner must not hide an unknown Scrum Master defect."
        )

    monkeypatch.setattr(
        service._planner,
        "plan",
        planner_must_not_run,
    )

    with pytest.raises(
        ScrumMasterGenerationError
    ) as captured:

        await service.generate(
            project_id=303,
            analysis_data={},
            settings=service.default_settings().model_copy(
                update={
                    "sprint_count_mode": "manual",
                },
                deep=True,
            ),
        )

    assert (
        captured.value.code
        ==
        "internal_contract_bug"
    )

    assert planner_called is False