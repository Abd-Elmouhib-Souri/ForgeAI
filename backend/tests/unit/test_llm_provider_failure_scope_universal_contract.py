from __future__ import annotations

import pytest

from app.config import settings
from app.llm.provider import LLMProvider


@pytest.fixture(autouse=True)
def clear_shared_provider_health():
    """
    Circuit health is class-level runtime state.

    Every contract starts and ends with an isolated health registry so
    test ordering can never affect the result.
    """
    LLMProvider._shared_health.clear()

    yield

    LLMProvider._shared_health.clear()


def _provider_and_config():
    provider = LLMProvider()

    assert provider.model_configs, (
        "The universal provider contract requires at least one configured "
        "model in the test environment."
    )

    return provider, provider.model_configs[0]


def _health(provider: LLMProvider, config):
    key = provider._model_key(config)

    return provider._shared_health.get(key)


def test_unknown_request_failure_does_not_poison_model_global_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Universal invariant:

    An error whose provider/model scope is unknown must not be promoted
    into model-global unavailability.

    "unknown" means ForgeAI has not established that the model or provider
    itself is unhealthy.  The failure may belong only to one request,
    prompt, output mode, schema, payload size or task.

    Therefore an unrelated later task must remain allowed to try the model.
    """

    monkeypatch.setattr(
        settings,
        "LLM_CIRCUIT_FAILURES",
        1,
    )

    provider, config = _provider_and_config()

    provider._record_failure(
        config,
        "unknown",
    )

    # The invariant is behavioral, not representational.
    #
    # Production may either leave no shared health entry at all or retain
    # an empty healthy entry.  Neither implementation may carry a global
    # failure count or open the model-global circuit.
    health_before_probe = _health(
        provider,
        config,
    )

    if health_before_probe is not None:
        assert health_before_probe.failures == 0, (
            "UNKNOWN_SCOPE_FAILURE_POISONED_MODEL_GLOBAL_FAILURE_COUNT"
        )
        assert health_before_probe.open_until == 0.0, (
            "UNKNOWN_SCOPE_FAILURE_POISONED_MODEL_GLOBAL_OPEN_UNTIL"
        )

    assert provider._circuit_is_open(config) is False, (
        "UNKNOWN_SCOPE_FAILURE_OPENED_MODEL_GLOBAL_CIRCUIT"
    )

    health_after_probe = _health(
        provider,
        config,
    )

    assert health_after_probe is not None
    assert health_after_probe.failures == 0
    assert health_after_probe.open_until == 0.0


def test_configuration_failure_still_opens_global_circuit_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Anti-overfit guard:

    Proven configuration failures are model/provider-global enough to
    protect all tasks.  Fixing unknown failure scope must not disable the
    circuit breaker.
    """

    monkeypatch.setattr(
        settings,
        "LLM_CIRCUIT_FAILURES",
        99,
    )

    provider, config = _provider_and_config()

    provider._record_failure(
        config,
        "configuration",
    )

    assert provider._circuit_is_open(config) is True, (
        "CONFIGURATION_FAILURE_MUST_OPEN_GLOBAL_CIRCUIT"
    )


def test_temporary_provider_failure_remains_circuit_eligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Current conservative invariant:

    A failure already classified as temporary provider/model
    unavailability remains eligible for the global circuit.

    This contract deliberately does not decide yet whether the production
    threshold should be greater than one.
    """

    monkeypatch.setattr(
        settings,
        "LLM_CIRCUIT_FAILURES",
        1,
    )

    provider, config = _provider_and_config()

    provider._record_failure(
        config,
        "temporary",
    )

    assert provider._circuit_is_open(config) is True, (
        "TEMPORARY_PROVIDER_FAILURE_MUST_REMAIN_CIRCUIT_ELIGIBLE"
    )


def test_success_resets_global_provider_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Existing success semantics must remain intact.
    """

    monkeypatch.setattr(
        settings,
        "LLM_CIRCUIT_FAILURES",
        1,
    )

    provider, config = _provider_and_config()

    provider._record_failure(
        config,
        "temporary",
    )

    assert provider._circuit_is_open(config) is True

    provider._record_success(
        config,
    )

    health = _health(
        provider,
        config,
    )

    assert health is not None
    assert health.failures == 0
    assert provider._circuit_is_open(config) is False