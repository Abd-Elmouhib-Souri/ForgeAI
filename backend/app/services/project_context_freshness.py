from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from app.schemas.analysis_context import ProjectContextPacketV3


CURRENT_PROJECT_CONTEXT_SEMANTICS_VERSION = "project_context_semantics_v11"


class ProjectContextFreshnessAuthority:
    """
    Canonical authority for persisted ProjectContextPacket freshness.

    Schema compatibility proves only that a packet can be parsed.
    Freshness additionally proves that the packet was generated under
    the current canonical semantics and that its persisted identity
    still matches its metadata.
    """

    _INPUT_IDENTITY_FIELDS = (
        "project_name",
        "description",
        "language",
        "target_region",
        "industry_user_input",
    )

    _REQUIRED_META_FIELDS = (
        "canonical_schema_version",
        "canonical_semantics_version",
        "canonical_input_fingerprint",
        "canonical_packet_fingerprint",
    )

    @staticmethod
    def _stable_hash(
        value: Any,
    ) -> str:

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

    @staticmethod
    def _packet_data(
        packet: Any,
    ) -> dict[str, Any]:

        validated = (
            ProjectContextPacketV3
            .model_validate(
                packet
            )
        )

        return validated.model_dump(
            mode="json"
        )

    def canonical_input_payload(
        self,
        packet: Any,
    ) -> dict[str, Any]:

        data = self._packet_data(
            packet
        )

        return {
            key: data.get(key)
            for key
            in self._INPUT_IDENTITY_FIELDS
        }

    def input_fingerprint(
        self,
        packet: Any,
    ) -> str:

        return self._stable_hash(
            self.canonical_input_payload(
                packet
            )
        )

    def packet_fingerprint(
        self,
        packet: Any,
    ) -> str:

        return self._stable_hash(
            self._packet_data(
                packet
            )
        )

    def build_metadata(
        self,
        packet: Any,
    ) -> dict[str, str]:

        data = self._packet_data(
            packet
        )

        return {
            "canonical_schema_version":
                str(
                    data.get(
                        "schema_version"
                    )
                    or ""
                ),
            "canonical_semantics_version":
                CURRENT_PROJECT_CONTEXT_SEMANTICS_VERSION,
            "canonical_input_fingerprint":
                self.input_fingerprint(
                    packet
                ),
            "canonical_packet_fingerprint":
                self.packet_fingerprint(
                    packet
                ),
        }

    def is_current(
        self,
        *,
        packet: Any,
        metadata: Any,
    ) -> bool:

        if not isinstance(
            metadata,
            Mapping,
        ):
            return False

        if any(
            not metadata.get(field)
            for field
            in self._REQUIRED_META_FIELDS
        ):
            return False

        expected = self.build_metadata(
            packet
        )

        for field in self._REQUIRED_META_FIELDS:

            if (
                str(
                    metadata.get(field)
                    or ""
                )
                !=
                str(
                    expected.get(field)
                    or ""
                )
            ):
                return False

        return True


project_context_freshness_authority = (
    ProjectContextFreshnessAuthority()
)
