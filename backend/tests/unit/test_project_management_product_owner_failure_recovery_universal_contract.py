from __future__ import annotations

from typing import Any

import pytest

import app.services.project_management_plan_service as pm_module
from app.agents.product_owner_agent import (
    ProductOwnerAgent,
    ProductOwnerGenerationError,
)
from app.services.project_management_plan_service import (
    ProjectManagementPlanService,
)


class _StopAfterCandidate(RuntimeError):
    pass


RECOVERABLE_UNTRUSTED_CANDIDATE_CODES = (
    "generation_temporarily_unavailable",
    "invalid_model_response",
    "candidate_authority_rejected",
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_code",
    RECOVERABLE_UNTRUSTED_CANDIDATE_CODES,
)
async def test_untrusted_product_owner_result_uses_deterministic_fallback(
    monkeypatch: pytest.MonkeyPatch,
    error_code: str,
) -> None:
    """
    Universal recovery invariant.

    An LLM Product Owner result that cannot become a trusted candidate
    must never become canonical and must not prevent the deterministic,
    canonical-data-only recovery path from running.

    This is intentionally independent of project, sector, country,
    provider and story count.
    """

    service = ProjectManagementPlanService()

    context = object()
    deterministic_candidate = object()

    fallback_inputs: list[Any] = []

    monkeypatch.setattr(
        service,
        "_build_context",
        lambda **_: context,
    )

    def deterministic_fallback(
        current_context: Any,
    ) -> Any:
        fallback_inputs.append(
            current_context
        )

        return deterministic_candidate

    monkeypatch.setattr(
        service,
        "_build_deterministic_candidate",
        deterministic_fallback,
    )

    async def reject_candidate(
        self: ProductOwnerAgent,
        current_context: Any,
    ) -> Any:
        assert current_context is context

        raise ProductOwnerGenerationError(
            error_code,
            "Synthetic untrusted Product Owner result.",
        )

    monkeypatch.setattr(
        ProductOwnerAgent,
        "generate_candidate_backlog",
        reject_candidate,
    )

    def stop_at_canonicalization(
        current_context: Any,
        candidate: Any,
    ) -> Any:
        assert current_context is context
        assert candidate is deterministic_candidate

        raise _StopAfterCandidate()

    monkeypatch.setattr(
        pm_module.backlog_policy_engine,
        "canonicalize",
        stop_at_canonicalization,
    )

    with pytest.raises(
        _StopAfterCandidate
    ):
        await service.generate(
            project_id=101,
            analysis_data={},
        )

    assert fallback_inputs == [
        context
    ]


@pytest.mark.asyncio
async def test_unknown_product_owner_error_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Recovery must be allow-listed.

    Unknown Product Owner failures can represent a programming,
    contract or integrity defect and must not be hidden by fallback.
    """

    service = ProjectManagementPlanService()

    context = object()

    fallback_called = False

    monkeypatch.setattr(
        service,
        "_build_context",
        lambda **_: context,
    )

    def deterministic_fallback(
        current_context: Any,
    ) -> Any:
        nonlocal fallback_called

        fallback_called = True

        return object()

    monkeypatch.setattr(
        service,
        "_build_deterministic_candidate",
        deterministic_fallback,
    )

    async def internal_failure(
        self: ProductOwnerAgent,
        current_context: Any,
    ) -> Any:
        assert current_context is context

        raise ProductOwnerGenerationError(
            "internal_contract_bug",
            "Synthetic internal Product Owner defect.",
        )

    monkeypatch.setattr(
        ProductOwnerAgent,
        "generate_candidate_backlog",
        internal_failure,
    )

    with pytest.raises(
        ProductOwnerGenerationError
    ) as exc_info:
        await service.generate(
            project_id=202,
            analysis_data={},
        )

    assert (
        exc_info.value.code
        ==
        "internal_contract_bug"
    )

    assert fallback_called is False