from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.schemas.analysis_context import (
    clean_text,
    unique_texts,
)
from app.schemas.project_management import (
    ProjectManagementDecisionProjectionV1,
)


class ProjectManagementDecisionProjector:
    """
    Deterministic projection of Sprint 3's canonical committee decision.

    Canonical authority:
        debate_room.judge

    Accepted final states:
        completed
        completed_with_fallback

    Startup Score, Final Report, Evidence Ledger, project intelligence,
    search results, RAG context and raw analysis_data are not inputs.
    """

    _FINAL_STATUSES = frozenset(
        {
            "completed",
            "completed_with_fallback",
        }
    )

    _DECISION_SOURCE = (
        "debate_room.judge"
    )

    def project(
        self,
        *,
        debate_judge: Mapping[str, Any] | None,
    ) -> ProjectManagementDecisionProjectionV1:
        """
        Project a final Debate Room Judge result into the narrow
        Sprint 4 decision contract.

        Missing, malformed or non-final Judge state remains unknown.
        """
        if not isinstance(
            debate_judge,
            Mapping,
        ):
            return self._empty()

        status = self._normalize_token(
            debate_judge.get(
                "status"
            )
        )

        if status not in self._FINAL_STATUSES:
            return self._empty()

        return ProjectManagementDecisionProjectionV1(
            decision_source=(
                self._DECISION_SOURCE
            ),

            decision_status=status,

            canonical_verdict_code=(
                self._normalize_token(
                    debate_judge.get(
                        "verdict_code"
                    )
                )
            ),

            # Only Judge critical_risks enter this field.
            #
            # missing_evidence and weak_assumptions remain
            # semantically separate and cannot be promoted here.
            validated_risks=(
                self._string_list(
                    debate_judge.get(
                        "critical_risks"
                    )
                )
            ),

            validated_next_actions=(
                self._string_list(
                    debate_judge.get(
                        "next_actions"
                    )
                )
            ),

            go_no_go_conditions=(
                self._string_list(
                    debate_judge.get(
                        "go_no_go_conditions"
                    )
                )
            ),

            final_recommendation=clean_text(
                debate_judge.get(
                    "final_recommendation"
                )
            ),
        )

    def _empty(
        self,
    ) -> ProjectManagementDecisionProjectionV1:
        return (
            ProjectManagementDecisionProjectionV1()
        )

    def _string_list(
        self,
        value: Any,
    ) -> list[str]:
        """
        Preserve semantic order while removing empty/duplicate entries.
        """
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            raw_values = [
                value
            ]

        elif isinstance(
            value,
            (
                list,
                tuple,
            ),
        ):
            raw_values = list(
                value
            )

        else:
            return []

        cleaned = [
            clean_text(item)
            for item in raw_values
            if clean_text(item)
        ]

        return unique_texts(
            cleaned
        )

    def _normalize_token(
        self,
        value: Any,
    ) -> str:
        """
        Normalize machine codes without inventing semantic mappings.

        CONDITIONAL_GO
        Conditional Go
        conditional-go

        all become:

        conditional_go
        """
        text = clean_text(
            value
        ).casefold()

        if not text:
            return ""

        text = re.sub(
            r"[\s\-]+",
            "_",
            text,
        )

        text = re.sub(
            r"_+",
            "_",
            text,
        )

        return text.strip(
            "_"
        )


project_management_decision_projector = (
    ProjectManagementDecisionProjector()
)