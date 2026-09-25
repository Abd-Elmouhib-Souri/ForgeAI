"""
Per-minute token limit contracts (observed 25 Sept 2026, project 31).

Real Groq free-tier errors from the user's logs:

  413 "Request too large ... (TPM): Limit 8000, Requested 12738"
      -> the prompt (~4.7k) + max_tokens=8000 can never fit a 8000 TPM
         budget: every call failed, whatever the wait.
  429 "Rate limit reached ... (TPM): Limit 8000, Used 7888, Requested 6120.
       Please try again in 7.66s"
      -> the minute budget refills within seconds: waiting succeeds.
  429 "Request too large ... (OTPM): Limit 1000, Requested 2305"
      -> the model's output cap is too small for a structured answer.

Contracts: shrink max_tokens to fit, honour short provider-advised waits,
skip models that cannot fit, never poison shared circuit health.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.llm import provider as provider_module
from app.llm.provider import LLMModelConfig, LLMProvider, LLMUnavailableError

TOO_LARGE_TPM = (
    "Error code: 413 - {'error': {'message': 'Request too large for model `m` in organization `o` "
    "service tier `on_demand` on tokens per minute (TPM): Limit 8000, Requested 12738, "
    "please reduce your message size and try again.'}}"
)
RATE_LIMITED = (
    "Error code: 429 - {'error': {'message': 'Rate limit reached for model `m` in organization `o` "
    "service tier `on_demand` on tokens per minute (TPM): Limit 8000, Used 7888, Requested 6120. "
    "Please try again in 7.66s. Need more tokens? Upgrade to Dev Tier today.'}}"
)
RATE_LIMITED_LONG = RATE_LIMITED.replace("7.66s", "2m5.1s")
OTPM_TOO_SMALL = (
    "Error code: 429 - {'error': {'message': \"Request too large for model `m` in organization `o` "
    "service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Requested 2305. Try again\"}}"
)


class _Response:
    def __init__(self, content):
        self.content = content


class FakeModel:
    """Scripted chat model: records max_tokens of every call."""

    def __init__(self, outcomes, max_tokens=8000):
        self.outcomes = list(outcomes)
        self.max_tokens = max_tokens
        self.sent_max_tokens = []

    def bind(self, **kwargs):
        parent = self

        class _Bound:
            async def ainvoke(self, prompt):
                return await parent._call(kwargs.get("max_tokens"))

        return _Bound()

    async def ainvoke(self, prompt):
        return await self._call(None)

    async def _call(self, max_tokens):
        self.sent_max_tokens.append(max_tokens)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(outcome)


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    LLMProvider._shared_health.clear()
    LLMProvider._learned_token_limits.clear()
    monkeypatch.setattr(settings, "LLM_RATE_LIMIT_MAX_WAIT_SECONDS", 20.0)
    monkeypatch.setattr(settings, "LLM_MIN_OUTPUT_TOKENS", 1200)
    yield
    LLMProvider._shared_health.clear()
    LLMProvider._learned_token_limits.clear()


def make_provider(monkeypatch, models: dict[str, FakeModel]):
    configs = [LLMModelConfig("groq", name, 600, "k", i) for i, name in enumerate(models, 1)]
    provider = object.__new__(LLMProvider)
    provider.model_configs = configs

    async def fake_get(config, *, structured=False):
        return models[config.model_name]

    monkeypatch.setattr(provider, "_get_or_create_model", fake_get)
    return provider


@pytest.fixture
def sleeps(monkeypatch):
    recorded = []

    async def fake_sleep(seconds):
        recorded.append(seconds)

    monkeypatch.setattr(provider_module.asyncio, "sleep", fake_sleep)
    return recorded


PROMPT = "x" * 12000  # ~3.8k estimated tokens


@pytest.mark.asyncio
async def test_413_tpm_shrinks_max_tokens_and_succeeds(monkeypatch, sleeps):
    model = FakeModel([RuntimeError(TOO_LARGE_TPM), '{"ok": true}'])
    provider = make_provider(monkeypatch, {"primary": model})

    assert await provider.invoke(PROMPT, "t") == '{"ok": true}'
    # Prompt = 12738 - 8000 = 4738 tokens -> 8000 - 4738 - margin.
    assert model.sent_max_tokens[0] is None
    assert model.sent_max_tokens[1] == 8000 - 4738 - provider_module._TOKEN_SAFETY_MARGIN
    assert sleeps == []
    assert provider._circuit_is_open(provider.model_configs[0]) is False


@pytest.mark.asyncio
async def test_learned_limit_fits_the_next_call_before_sending(monkeypatch, sleeps):
    model = FakeModel([RuntimeError(TOO_LARGE_TPM), "a", "b"])
    provider = make_provider(monkeypatch, {"primary": model})
    await provider.invoke(PROMPT, "t")
    await provider.invoke(PROMPT, "t")
    # Second call: no wasted 413, budget computed up front.
    expected = 8000 - provider_module._estimate_tokens(PROMPT) - provider_module._TOKEN_SAFETY_MARGIN
    assert model.sent_max_tokens[2] == expected


@pytest.mark.asyncio
async def test_short_rate_limit_waits_the_advised_delay(monkeypatch, sleeps):
    model = FakeModel([RuntimeError(RATE_LIMITED), "done"])
    provider = make_provider(monkeypatch, {"primary": model})

    assert await provider.invoke("short prompt", "t") == "done"
    assert len(sleeps) == 1 and 7.66 <= sleeps[0] <= 8.0
    assert provider._circuit_is_open(provider.model_configs[0]) is False


@pytest.mark.asyncio
async def test_long_rate_limit_falls_through_to_the_next_model(monkeypatch, sleeps):
    first = FakeModel([RuntimeError(RATE_LIMITED_LONG)])
    second = FakeModel(["from fallback"])
    provider = make_provider(monkeypatch, {"primary": first, "fallback": second})

    assert await provider.invoke("short prompt", "t") == "from fallback"
    assert sleeps == []  # 125 s is above LLM_RATE_LIMIT_MAX_WAIT_SECONDS


@pytest.mark.asyncio
async def test_output_cap_too_small_skips_model_without_opening_circuit(monkeypatch, sleeps):
    small = FakeModel([RuntimeError(OTPM_TOO_SMALL)])
    big = FakeModel(["ok"])
    provider = make_provider(monkeypatch, {"small": small, "big": big})

    assert await provider.invoke("short prompt", "t") == "ok"
    assert provider._circuit_is_open(provider.model_configs[0]) is False
    # Next call: the small model is skipped before sending anything.
    big.outcomes.append("ok2")
    assert await provider.invoke("short prompt", "t") == "ok2"
    assert len(small.sent_max_tokens) == 1


@pytest.mark.asyncio
async def test_all_models_too_large_reports_a_retryable_failure(monkeypatch, sleeps):
    from app.services.llm_failure_classifier import LLM_QUOTA_OR_UNAVAILABLE, classify

    model = FakeModel([RuntimeError(OTPM_TOO_SMALL)])
    provider = make_provider(monkeypatch, {"only": model})
    with pytest.raises(LLMUnavailableError) as caught:
        await provider.invoke("short prompt", "t")
    assert caught.value.failures == {"groq:only": "too_large"}
    assert classify(caught.value).code == LLM_QUOTA_OR_UNAVAILABLE


def test_gpt_oss_models_get_bounded_reasoning(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_REASONING_EFFORT", "low")
    gpt = LLMModelConfig("groq", "openai/gpt-oss-120b", 30, "k", 1)
    other = LLMModelConfig("groq", "qwen/qwen3.8-27b", 30, "k", 2)
    assert LLMProvider._groq_reasoning_kwargs(gpt) == {"reasoning_effort": "low"}
    assert LLMProvider._groq_reasoning_kwargs(other) == {}
    monkeypatch.setattr(settings, "GROQ_REASONING_EFFORT", "")
    assert LLMProvider._groq_reasoning_kwargs(gpt) == {}
