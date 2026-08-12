from __future__ import annotations

import asyncio

import pytest

from app.config import settings
from app.services.forgecrawler import ForgeCrawler
from app.services.project_intelligence_layer import project_intelligence_layer
from app.services.source_relevance_gate import source_relevance_gate
from app.web_search.local_market_search import LocalMarketSearchService
from app.web_search.providers import tavily_provider as tavily_provider_module
from app.web_search.providers.tavily_provider import TavilySearchError, TavilySearchProvider
from app.web_search.search_gateway import SearchGateway


NAWBA_DESCRIPTION = """Nawba Tunisia is a workforce management platform for small Tunisian
factories, workshops, restaurants and retail businesses. Managers create weekly
shifts, record attendance, approve leave requests and notify employees when a
schedule changes. The main operational user is the supervisor or HR assistant.
The economic buyer is the company owner or HR manager."""


def _nawba_context():
    intelligence = project_intelligence_layer.build(
        title="Nawba Tunisia",
        description=NAWBA_DESCRIPTION,
        industry="Human Resources / Workforce Scheduling / SME SaaS",
        target_region="Tunisie",
        output_language="en",
    )
    return project_intelligence_layer.merge_into_project_context(
        base_project_context={}, intelligence=intelligence
    )


def test_tavily_response_contract_filters_low_scores(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_MIN_SCORE", 0.35)
    provider = TavilySearchProvider(max_results=8)
    rows = provider._normalize_response(
        body={
            "request_id": "req-1",
            "usage": {"credits": 1},
            "results": [
                {
                    "title": "Strong result",
                    "url": "https://example.com/strong",
                    "content": "Relevant content",
                    "score": 0.91,
                },
                {
                    "title": "Weak result",
                    "url": "https://example.com/weak",
                    "content": "Weak content",
                    "score": 0.10,
                },
            ],
        },
        query="workforce scheduling Tunisia",
    )
    assert len(rows) == 1
    assert rows[0]["provider"] == "tavily"
    assert rows[0]["provider_score"] == 0.91
    assert rows[0]["tavily_credits"] == 1



def test_tavily_search_uses_bearer_and_minimal_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {}

        @staticmethod
        def json():
            return {
                "request_id": "req-contract",
                "usage": {"credits": 1},
                "results": [
                    {
                        "title": "Tavily result",
                        "url": "https://example.com/tavily",
                        "content": "Relevant result",
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

        async def post(self, endpoint, *, headers, json):
            captured["endpoint"] = endpoint
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-tavily-contract-key")
    monkeypatch.setattr(settings, "ENABLE_TAVILY_SEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_SAFE_SEARCH", False)
    monkeypatch.setattr(tavily_provider_module.httpx, "AsyncClient", FakeClient)

    rows = asyncio.run(TavilySearchProvider(max_results=8).search("test query"))
    assert rows[0]["provider"] == "tavily"
    assert captured["headers"]["Authorization"] == "Bearer test-tavily-contract-key"
    assert captured["payload"]["include_answer"] is False
    assert captured["payload"]["include_raw_content"] is False
    assert captured["payload"]["include_usage"] is True
    assert "safe_search" not in captured["payload"]
    assert "exact_match" not in captured["payload"]



def test_tavily_safe_search_is_sent_only_with_explicit_enterprise_opt_in(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {}

        @staticmethod
        def json():
            return {
                "request_id": "req-enterprise",
                "usage": {"credits": 1},
                "results": [
                    {
                        "title": "Enterprise result",
                        "url": "https://example.com/enterprise",
                        "content": "Relevant result",
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

        async def post(self, endpoint, *, headers, json):
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-tavily-contract-key")
    monkeypatch.setattr(settings, "ENABLE_TAVILY_SEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_SAFE_SEARCH", True)
    monkeypatch.setattr(tavily_provider_module.httpx, "AsyncClient", FakeClient)

    rows = asyncio.run(TavilySearchProvider(max_results=8).search("test query"))
    assert rows[0]["provider"] == "tavily"
    assert captured["payload"]["safe_search"] is True

def test_tavily_provider_exposes_retry_after(monkeypatch):
    class FakeResponse:
        status_code = 429
        headers = {"retry-after": "12"}
        text = "rate limited"

        @staticmethod
        def json():
            return {"detail": {"error": "rate limited"}}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-tavily-contract-key")
    monkeypatch.setattr(settings, "ENABLE_TAVILY_SEARCH", True)
    monkeypatch.setattr(tavily_provider_module.httpx, "AsyncClient", FakeClient)

    with pytest.raises(TavilySearchError) as exc_info:
        asyncio.run(TavilySearchProvider(max_results=8).search("test query"))
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_seconds == 12

def test_gateway_uses_tavily_then_ddgs(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "ddgs")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setattr(settings, "ENABLE_TAVILY_SEARCH", True)
    monkeypatch.setattr(settings, "ENABLE_DDGS_FALLBACK", True)
    gateway = SearchGateway()
    assert gateway.provider_order()[:2] == ["tavily", "ddgs"]


@pytest.mark.parametrize("status_code", [401, 429, 432, 433])
def test_gateway_falls_back_when_tavily_fails(monkeypatch, status_code):
    class FailingTavily:
        name = "tavily"
        enabled = True

        async def search(self, _query):
            raise TavilySearchError(
                "controlled Tavily failure",
                status_code=status_code,
                retry_after_seconds=1,
            )

    class WorkingDDGS:
        name = "ddgs"
        enabled = True

        async def search(self, query):
            return [
                {
                    "title": "Fallback result",
                    "url": "https://fallback.example/result",
                    "snippet": "DDGS fallback",
                    "provider": "ddgs",
                    "search_query": query,
                }
            ]

    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "ddgs")
    monkeypatch.setattr(settings, "SEARCH_MIN_RESULTS", 1)
    SearchGateway._states.clear()
    SearchGateway._memory_cache.clear()
    gateway = SearchGateway()
    gateway.providers = {"tavily": FailingTavily(), "ddgs": WorkingDDGS()}

    rows = asyncio.run(
        gateway.search(
            f"controlled fallback {status_code}",
            min_results=1,
            bypass_cache=True,
        )
    )
    assert len(rows) == 1
    assert rows[0]["provider"] == "ddgs"
    assert SearchGateway._states["tavily"].open_until > 0



def test_gateway_falls_back_when_tavily_times_out(monkeypatch):
    class TimeoutTavily:
        name = "tavily"
        enabled = True

        async def search(self, _query):
            raise asyncio.TimeoutError("controlled Tavily timeout")

    class WorkingDDGS:
        name = "ddgs"
        enabled = True

        async def search(self, query):
            return [
                {
                    "title": "Timeout fallback result",
                    "url": "https://fallback.example/timeout",
                    "snippet": "DDGS timeout fallback",
                    "provider": "ddgs",
                    "search_query": query,
                }
            ]

    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "ddgs")
    monkeypatch.setattr(settings, "SEARCH_MIN_RESULTS", 1)
    SearchGateway._states.clear()
    SearchGateway._memory_cache.clear()
    gateway = SearchGateway()
    gateway.providers = {"tavily": TimeoutTavily(), "ddgs": WorkingDDGS()}

    rows = asyncio.run(
        gateway.search(
            "controlled timeout fallback",
            min_results=1,
            bypass_cache=True,
        )
    )
    assert len(rows) == 1
    assert rows[0]["provider"] == "ddgs"


def test_gateway_uses_ddgs_when_tavily_key_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PRIMARY_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "SEARCH_FALLBACK_PROVIDER", "ddgs")
    monkeypatch.setattr(settings, "ENABLE_TAVILY_SEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    monkeypatch.setattr(settings, "ENABLE_DDGS_FALLBACK", True)
    gateway = SearchGateway()
    assert gateway.provider_order()[0] == "ddgs"
    assert "tavily" not in gateway.provider_order()

def test_nawba_local_queries_are_bilingual_and_specific():
    service = LocalMarketSearchService()
    queries = service.build_queries(
        sector="Human Resources / Workforce Scheduling / SME SaaS",
        region="Tunisie",
        description=NAWBA_DESCRIPTION,
        project_context=_nawba_context(),
    )
    lowered = [query.lower() for query in queries]
    assert any("logiciel" in query and "tunisie" in query for query in lowered)
    assert any("software" in query and "tunisia" in query for query in lowered)
    assert any("planning" in query or "scheduling" in query for query in lowered)
    assert all(len(query.split()) <= 9 for query in queries)


def test_workday_localized_pages_are_deduplicated_by_vendor():
    crawler = ForgeCrawler(max_sources=8)
    sources = [
        crawler._enrich_vendor_identity(
            {
                "title": "Workforce Scheduling Management Software | Workday US",
                "url": "https://www.workday.com/en-us/products/workforce-management/scheduling.html",
                "source_type": "adjacent_solution",
                "source_relevance_score": 0.86,
                "evidence_categories": ["solution_benchmark"],
                "public_display": True,
            }
        ),
        crawler._enrich_vendor_identity(
            {
                "title": "Workforce Scheduling Management Software | Workday SG",
                "url": "https://www.workday.com/en-sg/products/workforce-management/scheduling.html",
                "source_type": "adjacent_solution",
                "source_relevance_score": 0.84,
                "evidence_categories": ["solution_benchmark"],
                "public_display": True,
            }
        ),
    ]
    kept, removed = crawler._select_public_sources(sources)
    assert len(kept) == 1
    assert kept[0]["vendor_name"] == "Workday"
    assert kept[0]["vendor_key"] == "vendor:workday.com"
    assert len(removed) == 1


def test_same_workflow_different_market_is_international_benchmark_for_nawba():
    decision = source_relevance_gate.evaluate_source(
        source={
            "title": "Healthcare Workforce Management Solutions - QGenda",
            "url": "https://www.qgenda.com/healthcare-workforce-management",
            "snippet": (
                "Healthcare workforce scheduling for hospitals, physicians and nurses."
            ),
            "extracted_text_preview": (
                "QGenda is a healthcare workforce management platform for hospitals, "
                "physicians and nurses. Features, customers, integrations, book a demo, "
                "shift schedules and schedule changes."
            ),
            "text_extracted": True,
        },
        project_context=_nawba_context(),
    )
    assert decision["sector_mismatch"] is False
    assert decision["mismatch_terms"] == []
    assert decision["source_type"] == "adjacent_solution"
    assert decision["source_role"] == "international_benchmark"
    assert decision["canonical_category"] == "technology_benchmark"
    assert decision["comparison_scope"] == "international_benchmark"
    assert decision["region_match"] == "international"
    assert decision["is_direct_competitor"] is False
    assert decision["public_display"] is True
    assert "solution_benchmark" in decision["evidence_categories"]
