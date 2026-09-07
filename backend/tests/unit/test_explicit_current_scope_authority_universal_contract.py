from __future__ import annotations

from typing import Any

from app.schemas.analysis_context import (
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _keys(
    values: list[str],
) -> list[str]:
    return [
        comparison_key(value)
        for value in values
        if comparison_key(value)
    ]


def _packet(
    description: str,
    *,
    analysis_data: dict[str, Any] | None = None,
):
    return ProjectContextExtractor().extract(
        title="Neutral Scope Authority",
        description=description,
        industry="software",
        target_region="Global",
        output_language="en",
        project_context={},
        idea_readiness={},
        analysis_data=analysis_data or {},
    )


def test_current_explicit_mvp_scope_outranks_stale_derived_scope_en() -> None:
    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "Business objective:\n"
        "Reduce manual coordination.",
        analysis_data={
            "mvp_scope_items": [
                "legacy derived capability",
            ],
        },
    )

    assert _keys(packet.mvp_scope) == _keys(
        [
            "account access",
        ]
    ), packet.mvp_scope


def test_current_explicit_exclusions_outrank_stale_derived_exclusions_en() -> None:
    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "Explicitly out of scope for the MVP:\n"
        "- automatic billing\n"
        "Business objective:\n"
        "Reduce manual coordination.",
        analysis_data={
            "scope_exclusions": [
                "legacy derived exclusion",
            ],
        },
    )

    assert _keys(packet.scope_exclusions) == _keys(
        [
            "automatic billing",
        ]
    ), packet.scope_exclusions


def test_current_explicit_mvp_scope_outranks_stale_derived_scope_fr() -> None:
    packet = _packet(
        "Une plateforme generique de gestion.\n"
        "Fonctionnalites MVP:\n"
        "- acces au compte\n"
        "Objectif metier:\n"
        "Reduire la coordination manuelle.",
        analysis_data={
            "mvp_scope_items": [
                "ancienne capacite derivee",
            ],
        },
    )

    assert _keys(packet.mvp_scope) == _keys(
        [
            "acces au compte",
        ]
    ), packet.mvp_scope


def test_current_explicit_exclusions_outrank_stale_derived_exclusions_fr() -> None:
    packet = _packet(
        "Une plateforme generique de gestion.\n"
        "Fonctionnalites MVP:\n"
        "- acces au compte\n"
        "Exclusions du MVP:\n"
        "- facturation automatique\n"
        "Objectif metier:\n"
        "Reduire la coordination manuelle.",
        analysis_data={
            "scope_exclusions": [
                "ancienne exclusion derivee",
            ],
        },
    )

    assert _keys(packet.scope_exclusions) == _keys(
        [
            "facturation automatique",
        ]
    ), packet.scope_exclusions


def test_explicit_positive_authority_does_not_erase_negative_fallback() -> None:
    packet = _packet(
        "A generic workflow platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "Business objective:\n"
        "Reduce manual coordination.",
        analysis_data={
            "scope_exclusions": [
                "persisted canonical exclusion",
            ],
        },
    )

    assert _keys(packet.mvp_scope) == _keys(
        [
            "account access",
        ]
    ), packet.mvp_scope

    assert _keys(packet.scope_exclusions) == _keys(
        [
            "persisted canonical exclusion",
        ]
    ), packet.scope_exclusions


def test_explicit_negative_authority_does_not_erase_positive_fallback() -> None:
    packet = _packet(
        "A generic workflow platform.\n"
        "Explicitly out of scope for the MVP:\n"
        "- automatic billing\n"
        "Business objective:\n"
        "Reduce manual coordination.",
        analysis_data={
            "mvp_scope_items": [
                "persisted canonical capability",
            ],
        },
    )

    assert _keys(packet.mvp_scope) == _keys(
        [
            "persisted canonical capability",
        ]
    ), packet.mvp_scope

    assert _keys(packet.scope_exclusions) == _keys(
        [
            "automatic billing",
        ]
    ), packet.scope_exclusions