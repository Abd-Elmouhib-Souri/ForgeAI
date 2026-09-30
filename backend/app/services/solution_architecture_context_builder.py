from __future__ import annotations

import hashlib
import json

from app.schemas.analysis_context import (
    ActorRole,
    ProjectContextPacketV3,
)
from app.schemas.solution_architecture import (
    ArchitectureActorV1,
    ArchitectureTransactionUnitV1,
    ArchitectureWorkflowV1,
    SolutionArchitectureContextV1,
    TechnicalSignalsV1,
)


class SolutionArchitectureContextBuilder:
    """
    Deterministic authority boundary between ProjectContextPacketV3
    and SolutionArchitectureContextV1.

    This layer performs projection only.

    It does not select an architecture, technology, deployment topology
    or renderer. Those decisions belong to later Sprint 5 authorities.
    """

    _PRIMARY_OPERATIONAL_ROLES = frozenset(
        {
            ActorRole.USER,
            ActorRole.OPERATOR,
        }
    )

    def build(
        self,
        *,
        packet: ProjectContextPacketV3,
    ) -> SolutionArchitectureContextV1:
        """
        Build one deterministic technical-context projection.

        Unknown technical facts remain unknown. This builder does not
        infer architecture choices from narrative hints or archetypes.
        """

        if not isinstance(
            packet,
            ProjectContextPacketV3,
        ):
            raise TypeError(
                "packet must be a ProjectContextPacketV3"
            )

        actors = [
            ArchitectureActorV1(
                name=actor.name,
                role=actor.role.value,
                description=actor.description,
                is_explicit=actor.is_explicit,
                is_generic=actor.is_generic,
            )
            for actor in packet.actors
        ]

        workflows = []

        for workflow in packet.priority_workflows:
            # ArchitectureWorkflowV1 represents a fully bound
            # operational relation. Incomplete upstream relations
            # remain upstream rather than being fabricated here.
            if not (
                workflow.name
                and workflow.actor
                and workflow.action
                and workflow.object
            ):
                continue

            workflows.append(
                ArchitectureWorkflowV1(
                    name=workflow.name,
                    actor=workflow.actor,
                    action=workflow.action,
                    object=workflow.object,
                    result=workflow.result,
                    output=workflow.output,
                    frequency=workflow.frequency,
                    is_explicit=workflow.is_explicit,
                    confidence=workflow.confidence,
                )
            )

        transaction = None

        if packet.transaction_unit.name:
            transaction = (
                ArchitectureTransactionUnitV1(
                    name=packet.transaction_unit.name,
                    description=(
                        packet
                        .transaction_unit
                        .description
                    ),
                    supply_actor=(
                        packet
                        .transaction_unit
                        .supply_actor
                        or None
                    ),
                    demand_actor=(
                        packet
                        .transaction_unit
                        .demand_actor
                        or None
                    ),
                )
            )

        sector = (
            packet.industry_user_input
            or (
                packet.sector_labels[0]
                if packet.sector_labels
                else None
            )
        )

        target_users = (
            self._primary_operational_users(
                packet
            )
        )

        signals = TechnicalSignalsV1(
            regulatory_context=list(
                packet.regulatory_flags
            ),
            deployment_constraints=list(
                packet.deployment_environment
            ),
        )

        # Build once with a neutral fingerprint, then calculate the
        # fingerprint from the exact canonical projection itself.
        context = SolutionArchitectureContextV1(
            schema_version=(
                "solution_architecture_context_v1"
            ),
            language=packet.language,
            project_name=packet.project_name,
            sector=sector,
            target_region=(
                packet.target_region
                or None
            ),
            target_users=target_users,
            actors=actors,
            priority_workflows=workflows,
            transaction_unit=transaction,
            positive_mvp_scope=list(
                packet.mvp_scope
            ),
            explicit_exclusions=list(
                packet.scope_exclusions
            ),
            input_data=list(
                packet.input_data
            ),
            output_decision=list(
                packet.output_decision
            ),
            human_oversight=list(
                packet.human_oversight
            ),
            maintenance_model=list(
                packet.maintenance_model
            ),
            assumptions=list(
                packet.assumptions
            ),
            forbidden_adjacent_domains=list(
                packet.forbidden_adjacent_domains
            ),
            constraints=list(
                packet.constraints
            ),
            technical_signals=signals,
            upstream_context_fingerprint=(
                "0" * 64
            ),
        )

        projection = context.model_dump(
            mode="json",
            exclude={
                "upstream_context_fingerprint",
            },
        )

        fingerprint = self._sha256(
            projection
        )

        return context.model_copy(
            update={
                "upstream_context_fingerprint":
                    fingerprint,
            }
        )

    def _primary_operational_users(
        self,
        packet: ProjectContextPacketV3,
    ) -> list[str]:
        """
        Preserve canonical actor-role authority.

        USER and OPERATOR are operational-user roles. Other roles remain
        present in `actors` but are not silently promoted to target users.
        """

        names = []
        seen = set()

        for actor in packet.actors:
            if (
                actor.role
                not in
                self._PRIMARY_OPERATIONAL_ROLES
            ):
                continue

            name = actor.name.strip()

            if not name:
                continue

            key = name.casefold()

            if key in seen:
                continue

            seen.add(
                key
            )

            names.append(
                name
            )

        return names

    @staticmethod
    def _sha256(
        value: dict,
    ) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

        return hashlib.sha256(
            payload
        ).hexdigest()


solution_architecture_context_builder = (
    SolutionArchitectureContextBuilder()
)
