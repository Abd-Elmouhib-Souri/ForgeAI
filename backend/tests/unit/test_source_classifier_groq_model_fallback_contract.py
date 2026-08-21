from __future__ import annotations

import asyncio
from types import SimpleNamespace

import groq

from app.config import settings
from app.services.source_classifier import SourceClassifier


def test_source_classifier_groq_uses_configured_model_fallback(
    monkeypatch,
) -> None:
    calls: list[str] = []

    primary_model = "qa-missing-primary"
    fallback_model = "qa-working-fallback"

    monkeypatch.setattr(
        settings,
        "GROQ_API_KEY",
        "test-groq-key",
    )

    monkeypatch.setattr(
        settings,
        "GROQ_MODEL",
        primary_model,
    )

    monkeypatch.setattr(
        settings,
        "GROQ_FALLBACK_MODEL",
        fallback_model,
    )

    class FakeCompletions:
        async def create(
            self,
            **kwargs,
        ):
            model = str(
                kwargs.get("model") or ""
            )

            calls.append(
                model
            )

            if model == primary_model:
                raise RuntimeError(
                    "404 model_not_found"
                )

            if model != fallback_model:
                raise AssertionError(
                    "Unexpected Groq model: "
                    + model
                )

            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '[{'
                                '"index":0,'
                                '"source_type":"market_evidence",'
                                '"confidence":0.9,'
                                '"same_target":true,'
                                '"same_workflow":false,'
                                '"same_sector":true,'
                                '"product_page":false,'
                                '"reason":"QA fallback model"'
                                '}]'
                            )
                        )
                    )
                ]
            )

    class FakeAsyncGroq:
        def __init__(
            self,
            *,
            api_key,
        ) -> None:
            assert (
                api_key
                == "test-groq-key"
            )

            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    monkeypatch.setattr(
        groq,
        "AsyncGroq",
        FakeAsyncGroq,
    )

    classifier = SourceClassifier()

    result = asyncio.run(
        classifier._classify_groq(
            [
                {
                    "title":
                        "Local market source",

                    "url":
                        "https://example.test/source",

                    "snippet":
                        "Local market evidence.",
                }
            ],
            {
                "structured_project_context": {
                    "sector":
                        "Generic sector",

                    "target_region":
                        "Test region",

                    "target_users": [
                        "Business users",
                    ],

                    "problem":
                        "Generic business problem",

                    "solution":
                        "Generic solution",

                    "priority_workflows": [
                        "Complete core workflow",
                    ],
                }
            },
        )
    )

    assert calls == [
        primary_model,
        fallback_model,
    ]

    assert (
        result[0]["index"]
        == 0
    )

    assert (
        result[0]["source_type"]
        == "market_evidence"
    )


def test_source_classifier_groq_deduplicates_identical_models(
    monkeypatch,
) -> None:
    calls: list[str] = []

    model = "qa-single-model"

    monkeypatch.setattr(
        settings,
        "GROQ_API_KEY",
        "test-groq-key",
    )

    monkeypatch.setattr(
        settings,
        "GROQ_MODEL",
        model,
    )

    monkeypatch.setattr(
        settings,
        "GROQ_FALLBACK_MODEL",
        model,
    )

    class FakeCompletions:
        async def create(
            self,
            **kwargs,
        ):
            calls.append(
                str(
                    kwargs.get("model")
                    or ""
                )
            )

            raise RuntimeError(
                "model unavailable"
            )

    class FakeAsyncGroq:
        def __init__(
            self,
            *,
            api_key,
        ) -> None:
            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    monkeypatch.setattr(
        groq,
        "AsyncGroq",
        FakeAsyncGroq,
    )

    classifier = SourceClassifier()

    try:
        asyncio.run(
            classifier._classify_groq(
                [
                    {
                        "title": "Source",
                    }
                ],
                {},
            )
        )
    except RuntimeError:
        pass

    assert calls == [
        model,
    ]
