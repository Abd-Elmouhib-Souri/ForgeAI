from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Literal

import httpx

from app.schemas.solution_architecture import (
    UMLDiagramBundleV1,
)


class KrokiRenderError(
    RuntimeError
):
    """
    Typed renderer/integration failure.

    A KrokiRenderError never invalidates canonical PlantUML truth.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code

        super().__init__(
            message
        )


@dataclass(
    frozen=True
)
class KrokiRenderResult:
    diagram_type: str

    status: Literal[
        "rendered",
        "unavailable",
        "failed",
    ]

    svg: str | None = None

    error_code: str | None = None

    error_message: str | None = None


class KrokiClient:
    """
    Backend-only Kroki adapter.

    Canonical PlantUML source belongs to ForgeAI.
    Kroki only converts validated source into a visual representation.
    """

    _SUPPORTED_ENGINES = {
        "plantuml",
    }

    _SUPPORTED_FORMATS = {
        "svg",
    }

    _SVG_RE = re.compile(
        r"<svg\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str | None,
        timeout_seconds: float = 10.0,
        max_source_bytes: int = 131072,
        api_token: str | None = None,
        transport: (
            httpx.AsyncBaseTransport
            |
            httpx.BaseTransport
            |
            None
        ) = None,
    ) -> None:
        self.enabled = bool(
            enabled
        )

        self.base_url = (
            str(
                base_url
                or ""
            )
            .strip()
            .rstrip(
                "/"
            )
        )

        self.timeout_seconds = float(
            timeout_seconds
        )

        self.max_source_bytes = int(
            max_source_bytes
        )

        self.api_token = (
            str(
                api_token
            ).strip()
            if api_token
            else
            None
        )

        self._transport = transport

        if (
            self.enabled
            and
            not self.base_url
        ):
            raise KrokiRenderError(
                "renderer_configuration_error",
                (
                    "Kroki is enabled but "
                    "KROKI_BASE_URL is not configured."
                ),
            )

        if (
            self.timeout_seconds
            <=
            0
        ):
            raise KrokiRenderError(
                "renderer_configuration_error",
                (
                    "Kroki timeout must be positive."
                ),
            )

        if (
            self.max_source_bytes
            <=
            0
        ):
            raise KrokiRenderError(
                "renderer_configuration_error",
                (
                    "Kroki maximum source size "
                    "must be positive."
                ),
            )

    @classmethod
    def from_environment(
        cls,
    ) -> "KrokiClient":
        enabled_text = (
            os.getenv(
                "KROKI_ENABLED",
                "false",
            )
            .strip()
            .casefold()
        )

        enabled = (
            enabled_text
            in
            {
                "1",
                "true",
                "yes",
                "on",
            }
        )

        base_url = os.getenv(
            "KROKI_BASE_URL"
        )

        api_token = os.getenv(
            "KROKI_API_TOKEN"
        )

        timeout_text = os.getenv(
            "KROKI_TIMEOUT_SECONDS",
            "10",
        )

        max_source_text = os.getenv(
            "KROKI_MAX_SOURCE_BYTES",
            "131072",
        )

        try:
            timeout_seconds = float(
                timeout_text
            )

            max_source_bytes = int(
                max_source_text
            )

        except ValueError as exc:
            raise KrokiRenderError(
                "renderer_configuration_error",
                (
                    "Kroki numeric configuration "
                    "is invalid."
                ),
            ) from exc

        return cls(
            enabled=enabled,
            base_url=base_url,
            timeout_seconds=(
                timeout_seconds
            ),
            max_source_bytes=(
                max_source_bytes
            ),
            api_token=api_token,
        )

    def _validate_request(
        self,
        *,
        engine: str,
        source: str,
        output_format: str,
    ) -> bytes:
        if not self.enabled:
            raise KrokiRenderError(
                "renderer_disabled",
                (
                    "Kroki rendering is disabled."
                ),
            )

        normalized_engine = (
            str(
                engine
                or ""
            )
            .strip()
            .casefold()
        )

        if (
            normalized_engine
            not in
            self._SUPPORTED_ENGINES
        ):
            raise KrokiRenderError(
                "renderer_unsupported_engine",
                (
                    "Unsupported Kroki rendering engine."
                ),
            )

        normalized_format = (
            str(
                output_format
                or ""
            )
            .strip()
            .casefold()
        )

        if (
            normalized_format
            not in
            self._SUPPORTED_FORMATS
        ):
            raise KrokiRenderError(
                "renderer_unsupported_format",
                (
                    "Unsupported Kroki output format."
                ),
            )

        text = str(
            source
            or ""
        )

        if not text.strip():
            raise KrokiRenderError(
                "renderer_empty_source",
                (
                    "Renderer source must not be empty."
                ),
            )

        payload = text.encode(
            "utf-8"
        )

        if (
            len(
                payload
            )
            >
            self.max_source_bytes
        ):
            raise KrokiRenderError(
                "renderer_source_too_large",
                (
                    "Renderer source exceeds "
                    "the configured maximum payload size."
                ),
            )

        return payload

    async def render(
        self,
        *,
        engine: str,
        source: str,
        output_format: str = "svg",
    ) -> str:
        payload = self._validate_request(
            engine=engine,
            source=source,
            output_format=output_format,
        )

        normalized_engine = (
            engine
            .strip()
            .casefold()
        )

        normalized_format = (
            output_format
            .strip()
            .casefold()
        )

        url = (
            self.base_url
            +
            "/"
            +
            normalized_engine
            +
            "/"
            +
            normalized_format
        )

        headers = {
            "Content-Type":
                "text/plain; charset=utf-8",

            "Accept":
                "image/svg+xml",
        }

        if self.api_token:
            headers[
                "Authorization"
            ] = (
                "Bearer "
                +
                self.api_token
            )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self._transport,
            ) as client:

                response = await client.post(
                    url,
                    content=payload,
                    headers=headers,
                )

        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RequestError,
        ) as exc:
            raise KrokiRenderError(
                "renderer_unavailable",
                (
                    "Kroki renderer is temporarily "
                    "unavailable."
                ),
            ) from exc

        status = (
            response.status_code
        )

        if status == 429:
            raise KrokiRenderError(
                "renderer_rate_limited",
                (
                    "Kroki renderer rate limit reached."
                ),
                status_code=status,
            )

        if (
            status
            >=
            500
        ):
            raise KrokiRenderError(
                "renderer_unavailable",
                (
                    "Kroki renderer returned "
                    "a server-side failure."
                ),
                status_code=status,
            )

        if (
            status
            >=
            400
        ):
            raise KrokiRenderError(
                "renderer_invalid_request",
                (
                    "Kroki rejected the rendering request."
                ),
                status_code=status,
            )

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
            .split(
                ";",
                1,
            )[
                0
            ]
            .strip()
            .casefold()
        )

        body = (
            response.text
            or ""
        ).strip()

        if (
            content_type
            !=
            "image/svg+xml"
        ):
            raise KrokiRenderError(
                "renderer_invalid_response",
                (
                    "Kroki response has an "
                    "unexpected content type."
                ),
                status_code=status,
            )

        if not body:
            raise KrokiRenderError(
                "renderer_invalid_response",
                (
                    "Kroki returned an empty SVG response."
                ),
                status_code=status,
            )

        if not self._SVG_RE.search(
            body
        ):
            raise KrokiRenderError(
                "renderer_invalid_response",
                (
                    "Kroki response does not contain "
                    "an SVG document."
                ),
                status_code=status,
            )

        return body

    async def render_uml_bundle(
        self,
        bundle: UMLDiagramBundleV1,
    ) -> dict[
        str,
        KrokiRenderResult,
    ]:
        if not isinstance(
            bundle,
            UMLDiagramBundleV1,
        ):
            raise TypeError(
                "bundle must be a UMLDiagramBundleV1"
            )

        ordered = (
            (
                "use_case",
                bundle.use_case,
            ),
            (
                "class",
                bundle.class_diagram,
            ),
            (
                "sequence",
                bundle.sequence,
            ),
            (
                "activity",
                bundle.activity,
            ),
        )

        output = {}

        for (
            diagram_type,
            diagram,
        ) in ordered:

            try:
                svg = await self.render(
                    engine="plantuml",
                    source=diagram.source,
                    output_format="svg",
                )

                output[
                    diagram_type
                ] = KrokiRenderResult(
                    diagram_type=diagram_type,
                    status="rendered",
                    svg=svg,
                )

            except KrokiRenderError as exc:
                unavailable_codes = {
                    "renderer_unavailable",
                    "renderer_rate_limited",
                    "renderer_disabled",
                }

                status = (
                    "unavailable"
                    if (
                        exc.code
                        in
                        unavailable_codes
                    )
                    else
                    "failed"
                )

                output[
                    diagram_type
                ] = KrokiRenderResult(
                    diagram_type=diagram_type,
                    status=status,
                    svg=None,
                    error_code=exc.code,
                    error_message=str(
                        exc
                    ),
                )

        return output
