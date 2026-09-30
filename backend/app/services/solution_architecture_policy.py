from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.solution_architecture import (
    CandidateSolutionArchitectureV1,
    SolutionArchitectureContextV1,
)


class ArchitecturePolicyIssueV1(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    code: str
    severity: Literal[
        "error",
        "warning",
    ]
    path: str
    message: str


class ArchitecturePolicyResultV1(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: Literal[
        "architecture_policy_result_v1"
    ] = "architecture_policy_result_v1"

    accepted: bool

    errors: list[
        ArchitecturePolicyIssueV1
    ] = Field(
        default_factory=list
    )

    warnings: list[
        ArchitecturePolicyIssueV1
    ] = Field(
        default_factory=list
    )


class ArchitecturePolicyAuthority:
    """
    Deterministic authority between the LLM candidate and future
    canonical architecture assembly.

    The authority is deliberately project/domain/country agnostic.
    Unknown context is not converted into fabricated requirements.
    """

    _ADVANCED_ARCHITECTURE_MARKERS = (
        "microservice",
        "service mesh",
        "kubernetes",
        "k8s",
        "cloud native",
        "cloudnative",
        "active active",
        "multi region",
        "multiregion",
    )

    _HIGH_SCALE_MARKERS = (
        "high",
        "large",
        "massive",
        "global",
        "enterprise",
        "million",
        "millions",
        "elev",
        "important",
    )

    _HIGH_AVAILABILITY_MARKERS = (
        "high availability",
        "haute disponibilite",
        "critical",
        "critique",
        "24/7",
        "99.9",
        "99.99",
        "continuous",
        "continu",
        "active active",
        "multi region",
    )

    _HIGH_COMPLEXITY_MARKERS = (
        "high",
        "complex",
        "multiple",
        "many",
        "numerous",
        "eleve",
        "complexe",
        "multiples",
        "nombreux",
    )

    _NO_PERSISTENCE_MARKERS = (
        "no persistence",
        "without persistence",
        "stateless",
        "no database",
        "without database",
        "sans persistance",
        "sans base de donnees",
        "aucune persistance",
        "aucune base de donnees",
    )

    _DATABASE_LAYER_NAMES = {
        "database",
        "db",
        "persistence",
        "datastore",
        "data store",
        "base de donnees",
        "base donnees",
    }

    def evaluate(
        self,
        *,
        context: SolutionArchitectureContextV1,
        candidate: CandidateSolutionArchitectureV1,
    ) -> ArchitecturePolicyResultV1:
        if not isinstance(
            context,
            SolutionArchitectureContextV1,
        ):
            raise TypeError(
                "context must be SolutionArchitectureContextV1"
            )

        if not isinstance(
            candidate,
            CandidateSolutionArchitectureV1,
        ):
            raise TypeError(
                "candidate must be CandidateSolutionArchitectureV1"
            )

        errors = []
        warnings = []

        def error(
            code,
            path,
            message,
        ):
            errors.append(
                ArchitecturePolicyIssueV1(
                    code=code,
                    severity="error",
                    path=path,
                    message=message,
                )
            )

        if (
            candidate.source_context_fingerprint
            !=
            context.upstream_context_fingerprint
        ):
            error(
                "context_fingerprint_mismatch",
                "source_context_fingerprint",
                (
                    "Candidate context fingerprint does not match "
                    "the canonical architecture context."
                ),
            )

        if candidate.architecture is None:
            error(
                "architecture_missing",
                "architecture",
                (
                    "Candidate architecture proposal is required "
                    "before canonical validation."
                ),
            )

        layers = (
            candidate.stack.layers
            if candidate.stack is not None
            else []
        )

        seen_layers = set()

        for index, layer in enumerate(
            layers
        ):
            normalized_layer = self._normalize(
                layer.layer
            )

            if normalized_layer in seen_layers:
                error(
                    "duplicate_technical_layer",
                    f"stack.layers[{index}].layer",
                    (
                        "Technical layer names must be unique "
                        "after semantic normalization."
                    ),
                )

            seen_layers.add(
                normalized_layer
            )

            if (
                layer.status
                in {
                    "recommended",
                    "conditional",
                }
                and
                not self._clean(
                    layer.technology
                )
            ):
                error(
                    "active_layer_missing_technology",
                    f"stack.layers[{index}].technology",
                    (
                        "An active technical layer must identify "
                        "its proposed technology."
                    ),
                )

            if (
                layer.status
                ==
                "not_applicable"
                and
                self._clean(
                    layer.technology
                )
            ):
                error(
                    "not_applicable_layer_has_technology",
                    f"stack.layers[{index}].technology",
                    (
                        "A not-applicable layer cannot carry "
                        "a technology recommendation."
                    ),
                )

        architecture_text = ""

        if candidate.architecture is not None:
            architecture_text = " ".join(
                [
                    candidate.architecture.style,
                    *candidate.architecture.rationale,
                    *candidate.architecture.conditions,
                ]
            )

        stack_text = " ".join(
            " ".join(
                filter(
                    None,
                    [
                        layer.layer,
                        layer.technology,
                        layer.justification,
                    ],
                )
            )
            for layer
            in layers
        )

        proposal_text = self._normalize(
            architecture_text
            + " "
            + stack_text
        )

        advanced = any(
            marker
            in proposal_text
            for marker
            in self._ADVANCED_ARCHITECTURE_MARKERS
        )

        if (
            advanced
            and
            not self._has_advanced_support(
                context
            )
        ):
            error(
                "advanced_complexity_without_support",
                "architecture",
                (
                    "Advanced distributed architecture requires "
                    "explicit scale, availability, integration, "
                    "deployment, or equivalent technical evidence."
                ),
            )

        no_persistence = self._explicit_no_persistence(
            context
        )

        if no_persistence:
            database = candidate.database

            if (
                database is not None
                and
                database.status
                in {
                    "recommended",
                    "conditional",
                }
            ):
                error(
                    "database_conflicts_with_no_persistence",
                    "database",
                    (
                        "Database recommendation conflicts with "
                        "an explicit no-persistence constraint."
                    ),
                )

            for index, layer in enumerate(
                layers
            ):
                normalized_layer = self._normalize(
                    layer.layer
                )

                if (
                    normalized_layer
                    in
                    self._DATABASE_LAYER_NAMES
                    and
                    layer.status
                    in {
                        "recommended",
                        "conditional",
                    }
                ):
                    error(
                        "database_conflicts_with_no_persistence",
                        f"stack.layers[{index}]",
                        (
                            "Persistence layer conflicts with an "
                            "explicit no-persistence constraint."
                        ),
                    )

        return ArchitecturePolicyResultV1(
            accepted=(
                len(errors)
                ==
                0
            ),
            errors=errors,
            warnings=warnings,
        )

    def _has_advanced_support(
        self,
        context: SolutionArchitectureContextV1,
    ) -> bool:
        signals = (
            context.technical_signals
        )

        scale = self._normalize(
            signals.expected_scale
        )

        availability = self._normalize(
            signals.availability_requirement
        )

        integrations = self._normalize(
            signals.integration_complexity
        )

        deployment = self._normalize(
            " ".join(
                signals.deployment_constraints
            )
        )

        if any(
            marker in scale
            for marker in self._HIGH_SCALE_MARKERS
        ):
            return True

        if any(
            marker in availability
            for marker in self._HIGH_AVAILABILITY_MARKERS
        ):
            return True

        if any(
            marker in integrations
            for marker in self._HIGH_COMPLEXITY_MARKERS
        ):
            return True

        if (
            signals.multi_tenant_requirement
            is True
            and
            any(
                marker in scale
                for marker
                in self._HIGH_SCALE_MARKERS
            )
        ):
            return True

        if any(
            marker
            in deployment
            for marker
            in (
                "multi region",
                "multiregion",
                "distributed",
                "kubernetes",
                "service mesh",
            )
        ):
            return True

        return False

    def _explicit_no_persistence(
        self,
        context: SolutionArchitectureContextV1,
    ) -> bool:
        values = [
            *context.constraints,
            *context.explicit_exclusions,
        ]

        normalized = self._normalize(
            " ".join(
                values
            )
        )

        return any(
            marker
            in normalized
            for marker
            in self._NO_PERSISTENCE_MARKERS
        )

    @staticmethod
    def _clean(
        value,
    ):
        if value is None:
            return ""

        return str(
            value
        ).strip()

    @classmethod
    def _normalize(
        cls,
        value,
    ):
        text = cls._clean(
            value
        )

        text = unicodedata.normalize(
            "NFKD",
            text,
        )

        text = "".join(
            char
            for char
            in text
            if not unicodedata.combining(
                char
            )
        )

        text = text.casefold()

        text = re.sub(
            r"[^a-z0-9./+_-]+",
            " ",
            text,
        )

        return " ".join(
            text.split()
        )


architecture_policy_authority = (
    ArchitecturePolicyAuthority()
)
