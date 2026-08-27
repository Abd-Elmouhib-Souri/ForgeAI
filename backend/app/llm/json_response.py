from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


class JSONResponseError(ValueError):
    """
    Raised when an LLM response cannot be represented as one strict
    JSON object.

    This helper deliberately does not repair malformed JSON.
    """


_FENCED_JSON = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
    flags=(
        re.IGNORECASE
        |
        re.DOTALL
    ),
)


def extract_json_object(
    raw_response: Any,
) -> dict[str, Any]:
    """
    Extract exactly one JSON object.

    Accepted:
    - an existing Mapping;
    - a plain JSON object string;
    - a Markdown-fenced JSON object.

    Rejected:
    - empty output;
    - malformed JSON;
    - arrays/scalars;
    - prose surrounding JSON.

    The function never invents or repairs model output.
    """

    if isinstance(
        raw_response,
        Mapping,
    ):
        return dict(
            raw_response
        )

    content = getattr(
        raw_response,
        "content",
        raw_response,
    )

    if isinstance(
        content,
        Mapping,
    ):
        return dict(
            content
        )

    if content is None:
        raise JSONResponseError(
            "Empty model response."
        )

    if isinstance(
        content,
        bytes,
    ):
        try:
            text = content.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise JSONResponseError(
                "Model response is not valid UTF-8."
            ) from exc
    else:
        text = str(
            content
        )

    text = text.strip()

    if not text:
        raise JSONResponseError(
            "Empty model response."
        )

    fenced = _FENCED_JSON.fullmatch(
        text
    )

    if fenced is not None:
        text = fenced.group(
            1
        ).strip()

    if not text:
        raise JSONResponseError(
            "Empty JSON payload."
        )

    try:
        parsed = json.loads(
            text
        )

    except json.JSONDecodeError as exc:
        raise JSONResponseError(
            "Model response is not valid JSON."
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise JSONResponseError(
            "Model response must be one JSON object."
        )

    return parsed