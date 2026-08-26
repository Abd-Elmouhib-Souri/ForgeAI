from __future__ import annotations

import asyncio
import copy
from unittest.mock import patch

import pytest

import app.rag.web_dynamic_rag as module


def _service():
    return (
        module.DynamicWebRAGService
        .__new__(
            module.DynamicWebRAGService
        )
    )


def _context(
    *,
    top_locked: bool | None,
    structured_locked: bool,
):
    structured = {
        "context_locked":
            structured_locked,

        "target_region":
            "Canonland",

        "market_region":
            "Canonland",
    }

    context = {
        "target_region":
            "Canonland",

        "market_region":
            "Canonland",

        "structured_project_context":
            copy.deepcopy(
                structured
            ),
    }

    if top_locked is not None:
        context[
            "context_locked"
        ] = top_locked

    return context


def test_locked_normal_transport_preserves_project_context_once() -> None:
    service = _service()

    calls = []


    class FakeLocalMarketSearchService:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            pass

        async def search_local_market(
            self,
            **kwargs,
        ):
            calls.append(
                copy.deepcopy(
                    kwargs
                )
            )

            return []


    context = (
        _context(
            top_locked=True,
            structured_locked=True,
        )
    )


    with patch.object(
        module,
        "LocalMarketSearchService",
        FakeLocalMarketSearchService,
    ):
        result = asyncio.run(
            service._search_web_results(
                sector="Generic Operations",
                region="Driftland",
                description="Generic operational service.",
                project_context=copy.deepcopy(
                    context
                ),
                output_language="en",
            )
        )


    assert result == []
    assert len(calls) == 1

    call = calls[0]

    assert (
        call.get(
            "project_context",
            {},
        ).get(
            "structured_project_context",
            {},
        ).get(
            "target_region"
        )
        == "Canonland"
    )

    assert (
        call.get(
            "output_language"
        )
        == "en"
    )


def test_locked_top_level_context_does_not_retry_without_context_after_typeerror() -> None:
    service = _service()

    calls = []


    class FakeLocalMarketSearchService:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            pass

        async def search_local_market(
            self,
            **kwargs,
        ):
            calls.append(
                copy.deepcopy(
                    kwargs
                )
            )

            raise TypeError(
                "synthetic downstream TypeError"
            )


    context = (
        _context(
            top_locked=True,
            structured_locked=True,
        )
    )


    with patch.object(
        module,
        "LocalMarketSearchService",
        FakeLocalMarketSearchService,
    ):
        with pytest.raises(
            TypeError,
            match="synthetic downstream TypeError",
        ):
            asyncio.run(
                service._search_web_results(
                    sector="Generic Operations",
                    region="Driftland",
                    description="Generic operational service.",
                    project_context=copy.deepcopy(
                        context
                    ),
                    output_language="en",
                )
            )


    # Locked authority must never be silently discarded.
    assert len(calls) == 1

    assert (
        "project_context"
        in calls[0]
    )

    assert (
        calls[0].get(
            "output_language"
        )
        == "en"
    )


def test_locked_structured_only_context_does_not_retry_without_context_after_typeerror() -> None:
    service = _service()

    calls = []


    class FakeLocalMarketSearchService:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            pass

        async def search_local_market(
            self,
            **kwargs,
        ):
            calls.append(
                copy.deepcopy(
                    kwargs
                )
            )

            raise TypeError(
                "synthetic structured-lock TypeError"
            )


    # Top-level context_locked intentionally absent.
    # Structured lock alone must still be authoritative.
    context = (
        _context(
            top_locked=None,
            structured_locked=True,
        )
    )


    with patch.object(
        module,
        "LocalMarketSearchService",
        FakeLocalMarketSearchService,
    ):
        with pytest.raises(
            TypeError,
            match="synthetic structured-lock TypeError",
        ):
            asyncio.run(
                service._search_web_results(
                    sector="Generic Operations",
                    region="Driftland",
                    description="Generic operational service.",
                    project_context=copy.deepcopy(
                        context
                    ),
                    output_language="en",
                )
            )


    assert len(calls) == 1

    assert (
        "project_context"
        in calls[0]
    )


def test_unlocked_legacy_context_can_keep_contextless_typeerror_retry() -> None:
    service = _service()

    calls = []


    class FakeLocalMarketSearchService:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            pass

        async def search_local_market(
            self,
            **kwargs,
        ):
            calls.append(
                copy.deepcopy(
                    kwargs
                )
            )

            if (
                "project_context"
                in kwargs
            ):
                raise TypeError(
                    "synthetic legacy signature TypeError"
                )

            return [
                {
                    "title":
                        "legacy result",
                }
            ]


    context = (
        _context(
            top_locked=False,
            structured_locked=False,
        )
    )


    with patch.object(
        module,
        "LocalMarketSearchService",
        FakeLocalMarketSearchService,
    ):
        result = asyncio.run(
            service._search_web_results(
                sector="Generic Operations",
                region="Driftland",
                description="Generic operational service.",
                project_context=copy.deepcopy(
                    context
                ),
                output_language="en",
            )
        )


    assert (
        result
        == [
            {
                "title":
                    "legacy result",
            }
        ]
    )

    assert len(calls) == 2

    assert (
        "project_context"
        in calls[0]
    )

    assert (
        "project_context"
        not in calls[1]
    )
