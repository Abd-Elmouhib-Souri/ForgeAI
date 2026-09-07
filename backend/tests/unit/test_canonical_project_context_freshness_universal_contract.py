from __future__ import annotations

import hashlib
import json

import pytest

from app.agents.startup_evaluator_graph import StartupEvaluatorGraph

from app.schemas.analysis_context import (
    ProjectContextPacketV3,
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)

from app.services.project_management_plan_service import (
    ProjectManagementPlanError,
    project_management_plan_service,
)


CURRENT_SEMANTICS_VERSION = "project_context_semantics_v11"

LEGACY_SEMANTICS_VERSION = "project_context_semantics_v10"

V9_SEMANTICS_VERSION = "project_context_semantics_v9"

V8_SEMANTICS_VERSION = "project_context_semantics_v8"

V7_SEMANTICS_VERSION = "project_context_semantics_v7"

V6_SEMANTICS_VERSION = "project_context_semantics_v6"

OLDER_LEGACY_SEMANTICS_VERSION = (
    'project_context_semantics_v4'
)

OLDEST_LEGACY_SEMANTICS_VERSION = (
    'project_context_semantics_v3'
)

EARLIEST_LEGACY_SEMANTICS_VERSION = (
    'project_context_semantics_v2'
)


def _stable_hash(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _packet() -> ProjectContextPacketV3:
    return ProjectContextExtractor().extract(
        title="Neutral Freshness Project",
        description=(
            "A generic workflow platform.\n"
            "Primary operational users:\n"
            "- operations coordinator\n"
            "MVP capabilities:\n"
            "- account access\n"
            "- record management\n"
            "Explicitly out of scope for the MVP:\n"
            "- automatic billing\n"
            "Business objective:\n"
            "Reduce manual coordination."
        ),
        industry="software",
        target_region="Global",
        output_language="en",
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def _packet_data(packet):
    return (
        ProjectContextPacketV3
        .model_validate(packet)
        .model_dump(mode="json")
    )


def _canonical_input_payload(packet):
    data = _packet_data(packet)

    return {
        key: data.get(key)
        for key in (
            "project_name",
            "description",
            "language",
            "target_region",
            "industry_user_input",
        )
    }


def _input_fingerprint(packet) -> str:
    return _stable_hash(
        _canonical_input_payload(packet)
    )


def _packet_fingerprint(packet) -> str:
    return _stable_hash(
        _packet_data(packet)
    )


def _fresh_meta(packet):
    data = _packet_data(packet)

    return {
        "canonical_schema_version":
            data.get("schema_version"),
        "canonical_semantics_version":
            CURRENT_SEMANTICS_VERSION,
        "canonical_input_fingerprint":
            _input_fingerprint(packet),
        "canonical_packet_fingerprint":
            _packet_fingerprint(packet),
    }


def _analysis_data(
    packet,
    *,
    meta=None,
    include_meta=True,
):
    data = {
        "project_context_packet":
            _packet_data(packet),
    }

    if include_meta:
        data["project_context_meta"] = (
            dict(meta)
            if meta is not None
            else {}
        )

    return data


def _assert_stale(analysis_data) -> None:
    with pytest.raises(
        ProjectManagementPlanError
    ) as captured:

        project_management_plan_service._build_context(
            project_id=999,
            analysis_data=analysis_data,
        )

    assert (
        captured.value.code
        ==
        "project_context_stale"
    )


def test_analysis_persistence_emits_canonical_freshness_identity() -> None:
    packet = _packet()

    graph = object.__new__(
        StartupEvaluatorGraph
    )

    stored = graph._store_canonical_readiness(
        analysis_data={},
        idea_readiness={
            "schema_version":
                packet.schema_version,
            "status":
                "ready",
            "score":
                1.0,
            "ready_for_agents":
                True,
            "project_context_packet":
                packet.model_dump(mode="json"),
            "context_confidence":
                {},
            "legacy_project_context":
                {},
        },
    )

    meta = stored.get(
        "project_context_meta"
    )

    assert isinstance(meta, dict)

    assert (
        meta.get("canonical_schema_version")
        ==
        packet.schema_version
    )

    assert (
        meta.get("canonical_semantics_version")
        ==
        CURRENT_SEMANTICS_VERSION
    )

    assert (
        meta.get("canonical_input_fingerprint")
        ==
        _input_fingerprint(packet)
    )

    assert (
        meta.get("canonical_packet_fingerprint")
        ==
        _packet_fingerprint(packet)
    )


def test_packet_without_freshness_metadata_is_rejected() -> None:
    packet = _packet()

    _assert_stale(
        _analysis_data(
            packet,
            include_meta=False,
        )
    )


def test_legacy_schema_only_metadata_is_rejected() -> None:
    packet = _packet()

    _assert_stale(
        _analysis_data(
            packet,
            meta={
                "canonical_schema_version":
                    packet.schema_version,
            },
        )
    )


def test_previous_canonical_semantics_generation_is_rejected() -> None:
    """
    A canonical packet produced under the immediately previous
    extraction semantics is stale after an intentional semantics bump,
    even when schema and deterministic fingerprints still match.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = LEGACY_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_older_canonical_semantics_generation_is_rejected() -> None:
    """
    Older canonical generations remain stale after multiple intentional
    semantics migrations.

    This prevents a previous-old packet from becoming current again by
    accident when the immediately previous generation changes.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = OLDER_LEGACY_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_oldest_canonical_semantics_generation_is_rejected() -> None:
    """
    All older canonical extraction generations remain stale.

    An intentional migration must never accidentally make an older
    generation current again.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = OLDEST_LEGACY_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_earliest_canonical_semantics_generation_is_rejected() -> None:
    """
    The earliest retained canonical generation remains stale after
    subsequent intentional semantic migrations.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = EARLIEST_LEGACY_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )



def test_v5_canonical_semantics_generation_is_rejected() -> None:
    """
    A canonical packet generated under semantics v5 remains stale after
    migration to current canonical extraction semantics v7.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = "project_context_semantics_v5"

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )



def test_v6_canonical_semantics_generation_is_rejected() -> None:
    """
    V6 is stale once canonical extraction semantics move to V8.

    Historical packets may not silently regain authority merely because
    their schema and deterministic fingerprints are still valid.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = V6_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )



def test_v7_canonical_semantics_generation_is_rejected() -> None:
    """
    V7 is historical once canonical extraction semantics move to V9.

    Historical canonical packets may never regain authority merely
    because schema and deterministic fingerprints still happen to match.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = V7_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )



def test_v8_canonical_semantics_generation_is_rejected() -> None:
    """
    V8 is historical once canonical extraction semantics move to V10.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = V8_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )



def test_v9_canonical_semantics_generation_is_rejected() -> None:
    """
    V9 is historical once canonical extraction semantics move to V11.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = V9_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_wrong_semantics_version_is_rejected() -> None:
    packet = _packet()

    meta = _fresh_meta(packet)

    meta["canonical_semantics_version"] = (
        "project_context_semantics_legacy"
    )

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_wrong_canonical_input_fingerprint_is_rejected() -> None:
    packet = _packet()

    meta = _fresh_meta(packet)

    meta["canonical_input_fingerprint"] = (
        "0" * 64
    )

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_wrong_packet_fingerprint_is_rejected() -> None:
    packet = _packet()

    meta = _fresh_meta(packet)

    meta["canonical_packet_fingerprint"] = (
        "f" * 64
    )

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )


def test_current_freshness_identity_allows_pm_consumption() -> None:
    packet = _packet()

    context = (
        project_management_plan_service
        ._build_context(
            project_id=999,
            analysis_data=_analysis_data(
                packet,
                meta=_fresh_meta(packet),
            ),
        )
    )

    assert context.project_id == "999"

    assert any(
        comparison_key(value)
        ==
        comparison_key("account access")
        for value in context.mvp_scope
    )


# Historical generation retained explicitly after semantics v6 migration.
V1_SEMANTICS_VERSION = "project_context_semantics_v1"


def test_v1_canonical_semantics_generation_is_rejected() -> None:
    """
    Packets created with the oldest recorded canonical semantics generation
    remain stale after future semantics migrations.
    """

    packet = _packet()

    meta = _fresh_meta(
        packet
    )

    meta[
        "canonical_semantics_version"
    ] = V1_SEMANTICS_VERSION

    _assert_stale(
        _analysis_data(
            packet,
            meta=meta,
        )
    )
