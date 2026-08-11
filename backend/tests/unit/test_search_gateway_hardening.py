from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.config import settings
from app.web_search import search_gateway as gateway_module
from app.web_search.providers import ddgs_provider as ddgs_module
from app.web_search.providers import tavily_provider as tavily_module
from app.web_search.providers.gemini_grounded_provider import (
    GeminiGroundedSearchProvider,
)
from app.web_search.providers.tavily_provider import TavilySearchError, TavilySearchProvider
from app.web_search.search_gateway import SearchGateway


def _row(url: str, provider: str = "fake", score: float = 0.5) -> dict:
    return {
        "title": url,
        "url": url,
        "snippet": "result",
        "provider": provider,
        "provider_score": score,
        "grounded": False,
    }


@pytest.fixture(autouse=True)
def clear_gateway_state(monkeypatch):
    SearchGateway.clear_runtime_state()
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(settings, "SEARCH_MIN_RESULTS", 1)
    monkeypatch.setattr(settings, "SEARCH_MAX_RESULTS_PER_QUERY", 8)
    monkeypatch.setattr(settings, "SEARCH_CIRCUIT_FAILURES", 2)
    monkeypatch.setattr(settings, "SEARCH_CIRCUIT_COOLDOWN_SECONDS", 30)
    yield
    SearchGateway.clear_runtime_state()


def test_allow_gemini_fallback_false_is_respected(monkeypatch) -> None:
    class EmptyPrimary:
        name = "tavily"
        enabled = True

        async def search(self, _query):
            return []

    class GeminiFallback:
        name = "gemini_grounded"
        enabled = True
        calls = 0

        async def search(self, _query):
            self.calls += 1
            return [_row("https://example.com/gemini", self.name)]

    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "gemini_grounded")
    gateway = SearchGateway()
    gemini = GeminiFallback()
    gateway.providers = {
        "tavily": EmptyPrimary(),
        "gemini_grounded": gemini,
    }

    rows = asyncio.run(
        gateway.search(
            "query",
            min_results=1,
            allow_gemini_fallback=False,
            bypass_cache=True,
        )
    )
    assert rows == []
    assert gemini.calls == 0


def test_cache_key_isolated_by_required_result_count(monkeypatch) -> None:
    class Primary:
        name = "tavily"
        enabled = True
        calls = 0

        async def search(self, _query):
            self.calls += 1
            return [_row("https://example.com/one", self.name, 0.9)]

    class Fallback:
        name = "ddgs"
        enabled = True
        calls = 0

        async def search(self, _query):
            self.calls += 1
            return [
                _row(f"https://example.com/fallback-{index}", self.name, 0.1)
                for index in range(4)
            ]

    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "ddgs")
    primary = Primary()
    fallback = Fallback()
    gateway = SearchGateway()
    gateway.providers = {"tavily": primary, "ddgs": fallback}

    first = asyncio.run(gateway.search("same query", min_results=1))
    second = asyncio.run(gateway.search("same query", min_results=4))

    assert len(first) == 1
    assert len(second) >= 4
    assert primary.calls == 2
    assert fallback.calls == 1


def test_partial_results_are_not_cached(monkeypatch) -> None:
    class Partial:
        name = "tavily"
        enabled = True
        calls = 0

        async def search(self, _query):
            self.calls += 1
            return [_row("https://example.com/partial", self.name)]

    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "tavily")
    provider = Partial()
    gateway = SearchGateway()
    gateway.providers = {"tavily": provider}

    asyncio.run(gateway.search("partial", min_results=3))
    asyncio.run(gateway.search("partial", min_results=3))
    assert provider.calls == 2


def test_search_many_deduplicates_queries(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_search(query: str, **_kwargs):
        calls.append(query)
        return [_row(f"https://example.com/{len(calls)}")]

    gateway = SearchGateway()
    monkeypatch.setattr(gateway, "search", fake_search)
    rows = asyncio.run(
        gateway.search_many([" Alpha ", "alpha", "Beta", "beta "])
    )
    assert calls == ["Alpha", "Beta"]
    assert len(rows) == 2


def test_circuit_uses_structured_retry_after(monkeypatch) -> None:
    class Failing:
        name = "tavily"
        enabled = True

        async def search(self, _query):
            raise TavilySearchError(
                "rate limited",
                status_code=429,
                retry_after_seconds=120,
            )

    gateway = SearchGateway()
    gateway.providers = {"tavily": Failing()}
    before = __import__("time").time()
    rows = asyncio.run(
        gateway.search(
            "rate limit",
            force_provider="tavily",
            bypass_cache=True,
        )
    )
    assert rows == []
    assert SearchGateway._states["tavily"].open_until >= before + 119


def test_canonical_url_removes_tracking_and_credentials() -> None:
    assert (
        SearchGateway._canonical_url(
            "HTTPS://www.Example.com/path/?utm_source=x&b=2&a=1#fragment"
        )
        == "https://example.com/path?a=1&b=2"
    )
    assert SearchGateway._canonical_url("https://user:pass@example.com/") == ""


def test_ddgs_is_disabled_when_optional_dependency_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(ddgs_module, "_DDGS", None)
    monkeypatch.setattr(settings, "ENABLE_DDGS_FALLBACK", True)
    provider = ddgs_module.DDGSSearchProvider()
    assert provider.enabled is False
    assert asyncio.run(provider.search("query")) == []


def test_gemini_symbolic_quota_code_maps_to_429() -> None:
    code = SimpleNamespace(name="RESOURCE_EXHAUSTED")
    exc = SimpleNamespace(code=code, response=None)
    assert GeminiGroundedSearchProvider._extract_status_code(exc) == 429


@pytest.mark.parametrize(
    ("depth", "expects_chunks"),
    [
        ("basic", False),
        ("ultra-fast", False),
        ("fast", True),
        ("advanced", True),
    ],
)
def test_tavily_chunks_follow_search_depth_contract(
    monkeypatch,
    depth: str,
    expects_chunks: bool,
) -> None:
    captured: dict = {}

    class FakeResponse:
        status_code = 200
        headers = {}

        @staticmethod
        def json():
            return {
                "request_id": "req",
                "usage": {"credits": 1},
                "results": [
                    {
                        "title": "Result",
                        "url": "https://example.com/result",
                        "content": "Relevant",
                        "score": 0.9,
                    }
                ],
            }

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, _endpoint, *, headers, json):
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ENABLE_TAVILY_SEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_SEARCH_DEPTH", depth)
    monkeypatch.setattr(tavily_module.httpx, "AsyncClient", FakeClient)

    rows = asyncio.run(TavilySearchProvider(max_results=3).search("query"))
    assert rows
    assert ("chunks_per_source" in captured["payload"]) is expects_chunks
