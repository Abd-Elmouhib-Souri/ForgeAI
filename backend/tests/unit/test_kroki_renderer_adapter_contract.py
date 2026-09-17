from __future__ import annotations

import importlib
import json
from pathlib import Path

import httpx
import pytest

from app.schemas.solution_architecture import (
    UMLDiagramBundleV1,
    UMLDiagramV1,
)


def module():
    return importlib.import_module(
        "app.integrations.kroki_client"
    )


def valid_sources():
    return {
        "use_case": (
            "@startuml\n"
            "actor User\n"
            "usecase Process\n"
            "@enduml"
        ),

        "class": (
            "@startuml\n"
            "class Record\n"
            "@enduml"
        ),

        "sequence": (
            "@startuml\n"
            "actor User\n"
            "participant Service\n"
            "User -> Service: process\n"
            "@enduml"
        ),

        "activity": (
            "@startuml\n"
            "start\n"
            ":Process;\n"
            "stop\n"
            "@enduml"
        ),
    }


def bundle():
    sources = valid_sources()

    return UMLDiagramBundleV1(
        use_case=UMLDiagramV1(
            diagram_type="use_case",
            syntax="plantuml",
            source=sources[
                "use_case"
            ],
            validation_status="valid",
        ),

        class_diagram=UMLDiagramV1(
            diagram_type="class",
            syntax="plantuml",
            source=sources[
                "class"
            ],
            validation_status="valid",
        ),

        sequence=UMLDiagramV1(
            diagram_type="sequence",
            syntax="plantuml",
            source=sources[
                "sequence"
            ],
            validation_status="valid",
        ),

        activity=UMLDiagramV1(
            diagram_type="activity",
            syntax="plantuml",
            source=sources[
                "activity"
            ],
            validation_status="valid",
        ),
    )


# =============================================================================
# CONTROL ? CANONICAL UML SOURCE EXISTS INDEPENDENTLY OF RENDERER
# =============================================================================

def test_00_control_canonical_uml_bundle_exists_without_renderer():
    value = bundle()

    assert (
        value.use_case.syntax
        ==
        "plantuml"
    )

    assert (
        value.class_diagram.validation_status
        ==
        "valid"
    )

    assert (
        value.sequence.source.startswith(
            "@startuml"
        )
    )

    assert (
        value.activity.source.endswith(
            "@enduml"
        )
    )


# =============================================================================
# I1 ? PUBLIC ADAPTER API
# =============================================================================

def test_01_kroki_client_public_api_exists():
    value = module()

    assert hasattr(
        value,
        "KrokiClient",
    )

    assert hasattr(
        value,
        "KrokiRenderError",
    )

    assert hasattr(
        value,
        "KrokiRenderResult",
    )


# =============================================================================
# I1 ? CONFIG MUST NOT SILENTLY INVENT A PUBLIC ENDPOINT
# =============================================================================

def test_02_enabled_renderer_requires_configured_base_url():
    value = module()

    with pytest.raises(
        value.KrokiRenderError
    ) as caught:
        value.KrokiClient(
            enabled=True,
            base_url=None,
        )

    assert (
        caught.value.code
        ==
        "renderer_configuration_error"
    )


# =============================================================================
# I2 ? POST /plantuml/svg
# =============================================================================

@pytest.mark.asyncio
async def test_03_render_plantuml_posts_plain_text_and_returns_svg():
    value = module()

    requests = []

    def handler(
        request: httpx.Request,
    ):
        requests.append(
            request
        )

        assert (
            request.method
            ==
            "POST"
        )

        assert (
            request.url.path
            ==
            "/plantuml/svg"
        )

        assert (
            request.headers[
                "content-type"
            ].startswith(
                "text/plain"
            )
        )

        assert (
            request.headers[
                "accept"
            ]
            ==
            "image/svg+xml"
        )

        assert (
            request.content.decode(
                "utf-8"
            )
            ==
            valid_sources()[
                "class"
            ]
        )

        return httpx.Response(
            200,
            headers={
                "Content-Type":
                    "image/svg+xml",
            },
            text=(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                "<text>ok</text>"
                "</svg>"
            ),
        )

    transport = httpx.MockTransport(
        handler
    )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        transport=transport,
    )

    svg = await client.render(
        engine="plantuml",
        source=valid_sources()[
            "class"
        ],
        output_format="svg",
    )

    assert len(
        requests
    ) == 1

    assert (
        "<svg"
        in
        svg
    )


# =============================================================================
# I2 ? OPTIONAL AUTH GATEWAY TOKEN
# =============================================================================

@pytest.mark.asyncio
async def test_04_optional_api_token_is_sent_only_when_configured():
    value = module()

    observed = {}

    def handler(
        request: httpx.Request,
    ):
        observed[
            "authorization"
        ] = request.headers.get(
            "authorization"
        )

        return httpx.Response(
            200,
            headers={
                "Content-Type":
                    "image/svg+xml",
            },
            text=(
                '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
            ),
        )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        api_token="test-token",
        transport=httpx.MockTransport(
            handler
        ),
    )

    await client.render(
        engine="plantuml",
        source=valid_sources()[
            "use_case"
        ],
    )

    assert (
        observed[
            "authorization"
        ]
        ==
        "Bearer test-token"
    )


# =============================================================================
# I2 ? PAYLOAD LIMIT BEFORE NETWORK
# =============================================================================

@pytest.mark.asyncio
async def test_05_oversized_source_is_rejected_before_http_call():
    value = module()

    calls = []

    def handler(
        request: httpx.Request,
    ):
        calls.append(
            request
        )

        return httpx.Response(
            200,
            headers={
                "Content-Type":
                    "image/svg+xml",
            },
            text="<svg></svg>",
        )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        max_source_bytes=10,
        transport=httpx.MockTransport(
            handler
        ),
    )

    with pytest.raises(
        value.KrokiRenderError
    ) as caught:
        await client.render(
            engine="plantuml",
            source=(
                "@startuml\n"
                "class ThisSourceIsTooLarge\n"
                "@enduml"
            ),
        )

    assert (
        caught.value.code
        ==
        "renderer_source_too_large"
    )

    assert calls == []


# =============================================================================
# I3 ? CLIENT ERROR
# =============================================================================

@pytest.mark.asyncio
async def test_06_http_400_is_typed_invalid_renderer_request():
    value = module()

    def handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            400,
            text="invalid source",
        )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        transport=httpx.MockTransport(
            handler
        ),
    )

    with pytest.raises(
        value.KrokiRenderError
    ) as caught:
        await client.render(
            engine="plantuml",
            source=valid_sources()[
                "class"
            ],
        )

    assert (
        caught.value.code
        ==
        "renderer_invalid_request"
    )


# =============================================================================
# I3 ? PROVIDER / RENDERER OUTAGE
# =============================================================================

@pytest.mark.asyncio
async def test_07_http_503_is_renderer_unavailable():
    value = module()

    def handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            503,
            text="temporarily unavailable",
        )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        transport=httpx.MockTransport(
            handler
        ),
    )

    with pytest.raises(
        value.KrokiRenderError
    ) as caught:
        await client.render(
            engine="plantuml",
            source=valid_sources()[
                "sequence"
            ],
        )

    assert (
        caught.value.code
        ==
        "renderer_unavailable"
    )


# =============================================================================
# I3 ? INVALID RESPONSE MUST FAIL RENDERER, NOT CANONICAL SOURCE
# =============================================================================

@pytest.mark.asyncio
async def test_08_non_svg_response_fails_closed():
    value = module()

    def handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            200,
            headers={
                "Content-Type":
                    "text/plain",
            },
            text="not svg",
        )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        transport=httpx.MockTransport(
            handler
        ),
    )

    with pytest.raises(
        value.KrokiRenderError
    ) as caught:
        await client.render(
            engine="plantuml",
            source=valid_sources()[
                "activity"
            ],
        )

    assert (
        caught.value.code
        ==
        "renderer_invalid_response"
    )


# =============================================================================
# I4 ? ONE RENDER FAILURE MUST NOT DESTROY THE UML BUNDLE
# =============================================================================

@pytest.mark.asyncio
async def test_09_bundle_render_isolates_one_renderer_failure_and_preserves_source():
    value = module()

    original = bundle()

    before = original.model_dump(
        mode="json"
    )

    counter = {
        "value":
            0,
    }

    def handler(
        request: httpx.Request,
    ):
        counter[
            "value"
        ] += 1

        if (
            counter[
                "value"
            ]
            ==
            3
        ):
            return httpx.Response(
                503,
                text="renderer unavailable",
            )

        return httpx.Response(
            200,
            headers={
                "Content-Type":
                    "image/svg+xml",
            },
            text=(
                '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
            ),
        )

    client = value.KrokiClient(
        enabled=True,
        base_url=(
            "http://renderer.internal"
        ),
        transport=httpx.MockTransport(
            handler
        ),
    )

    rendered = await client.render_uml_bundle(
        original
    )

    assert (
        len(
            rendered
        )
        ==
        4
    )

    assert (
        sum(
            1
            for item
            in rendered.values()
            if item.status
            ==
            "rendered"
        )
        ==
        3
    )

    assert (
        sum(
            1
            for item
            in rendered.values()
            if item.status
            ==
            "unavailable"
        )
        ==
        1
    )

    failed = [
        item
        for item
        in rendered.values()
        if item.status
        ==
        "unavailable"
    ]

    assert (
        failed[
            0
        ].error_code
        ==
        "renderer_unavailable"
    )

    assert (
        original.model_dump(
            mode="json"
        )
        ==
        before
    )


# =============================================================================
# I1/I3 ? ENVIRONMENT CONFIG + AUTHORITY BOUNDARY
# =============================================================================

def test_10_renderer_source_has_no_public_endpoint_llm_or_persistence_authority(
    monkeypatch,
):
    value = module()

    monkeypatch.setenv(
        "KROKI_ENABLED",
        "true",
    )

    monkeypatch.setenv(
        "KROKI_BASE_URL",
        "http://renderer.internal",
    )

    monkeypatch.setenv(
        "KROKI_TIMEOUT_SECONDS",
        "7",
    )

    monkeypatch.setenv(
        "KROKI_MAX_SOURCE_BYTES",
        "2048",
    )

    monkeypatch.setenv(
        "KROKI_API_TOKEN",
        "optional-token",
    )

    client = (
        value
        .KrokiClient
        .from_environment()
    )

    assert client.enabled is True
    assert client.base_url == "http://renderer.internal"
    assert client.timeout_seconds == 7.0
    assert client.max_source_bytes == 2048
    assert client.api_token == "optional-token"

    source_path = Path(
        value.__file__
    )

    source = source_path.read_text(
        encoding="utf-8"
    )

    assert "kroki.io" not in source
    assert "LLMProvider" not in source
    assert "analysis_data" not in source
    assert "CanonicalSolutionArchitectureV1(" not in source
