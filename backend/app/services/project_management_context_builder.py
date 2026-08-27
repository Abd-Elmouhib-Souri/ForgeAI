from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import (
    Any,
    Dict,
    Iterable,
)

from app.schemas.analysis_context import (
    ActorRole,
    ProjectContextPacketV3,
    clean_text,
    unique_texts,
)
from app.schemas.project_management import (
    ProjectManagementContextV1,
    ProjectManagementDecisionProjectionV1,
)


class ProjectManagementContextBuilder:
    """
    Deterministic Sprint 4 planning-context authority.

    The builder projects already-canonical Sprint 3 facts into the
    narrower ProjectManagementContextV1 contract.

    It never consumes search results, RAG context, project intelligence,
    archetype hints or raw analysis_data.

    LLMs are not involved in this layer.
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
        project_id: str = "",
        decision: ProjectManagementDecisionProjectionV1 | None = None,
    ) -> ProjectManagementContextV1:
        """
        Build one immutable-by-convention planning projection.

        Hash semantics:

        source_context_hash
            SHA-256 of the authoritative Sprint 3 fields consumed by
            this builder. Unsafe archetype/query/search hints are
            deliberately absent.

        context_hash
            SHA-256 of ProjectManagementContextV1 after deterministic
            projection, excluding the two hash fields themselves.
        """
        if not isinstance(
            packet,
            ProjectContextPacketV3,
        ):
            raise TypeError(
                "packet must be a ProjectContextPacketV3"
            )

        primary_user_actor_names = (
            self._primary_user_actor_names(
                packet
            )
        )

        certified_decision = (
            self._certified_decision(
                decision
            )
        )

        context = ProjectManagementContextV1(
            source_context_schema_version=(
                packet.schema_version
            ),

            project_id=clean_text(
                project_id
            ),

            project_name=packet.project_name,
            language=packet.language,
            target_region=packet.target_region,
            industry=packet.industry_user_input,

            problem=deepcopy(
                packet.problem
            ),

            solution=deepcopy(
                packet.solution
            ),

            actors=deepcopy(
                packet.actors
            ),

            primary_user_actor_names=(
                primary_user_actor_names
            ),

            payer_actor_names=deepcopy(
                packet.payer_actor_names
            ),

            decision_maker_actor_names=deepcopy(
                packet.decision_maker_actor_names
            ),

            partner_actor_names=deepcopy(
                packet.partner_actor_names
            ),

            blocker_actor_names=deepcopy(
                packet.blocker_actor_names
            ),

            priority_workflows=deepcopy(
                packet.priority_workflows
            ),

            transaction_unit=deepcopy(
                packet.transaction_unit
            ),

            mvp_scope=deepcopy(
                packet.mvp_scope
            ),

            scope_exclusions=deepcopy(
                packet.scope_exclusions
            ),

            input_data=deepcopy(
                packet.input_data
            ),

            output_decision=deepcopy(
                packet.output_decision
            ),

            human_oversight=deepcopy(
                packet.human_oversight
            ),

            maintenance_model=deepcopy(
                packet.maintenance_model
            ),

            deployment_environment=deepcopy(
                packet.deployment_environment
            ),

            success_metrics=deepcopy(
                packet.success_metrics
            ),

            business_model_hypotheses=deepcopy(
                packet.business_model_hypotheses
            ),

            constraints=deepcopy(
                packet.constraints
            ),

            regulatory_flags=deepcopy(
                packet.regulatory_flags
            ),

            clarification_facts=deepcopy(
                packet.clarification_facts
            ),

            assumptions=deepcopy(
                packet.assumptions
            ),

            unknowns=deepcopy(
                packet.blocking_missing_fields
            ),

            warnings=deepcopy(
                packet.validation_warnings
            ),

            # Canonical downstream authority enters only through the
            # certified narrow decision projection.
            #
            # Raw Debate Room, Startup Score, Final Report, Evidence
            # Ledger and analysis_data never enter this builder.
            decision_source=(
                certified_decision.decision_source
            ),

            decision_status=(
                certified_decision.decision_status
            ),

            validated_risks=deepcopy(
                certified_decision.validated_risks
            ),

            validated_next_actions=deepcopy(
                certified_decision.validated_next_actions
            ),

            go_no_go_conditions=deepcopy(
                certified_decision.go_no_go_conditions
            ),

            canonical_verdict_code=(
                certified_decision.canonical_verdict_code
            ),

            final_recommendation=(
                certified_decision.final_recommendation
            ),

            forbidden_adjacent_domains=deepcopy(
                packet.forbidden_adjacent_domains
            ),

            source_context_hash="",
            context_hash="",
        )

        source_context_hash = self._stable_sha256(
            self._source_projection(
                packet
            )
        )

        context_hash = self._stable_sha256(
            self._context_projection(
                context
            )
        )

        context.source_context_hash = (
            source_context_hash
        )

        context.context_hash = (
            context_hash
        )

        return context

    def _certified_decision(
        self,
        decision: ProjectManagementDecisionProjectionV1 | None,
    ) -> ProjectManagementDecisionProjectionV1:
        """
        Accept only the narrow canonical decision projection.

        The builder deliberately does not inspect Debate Room,
        Startup Score, Final Report, Evidence Ledger or analysis_data.

        A structurally valid projection without the certified canonical
        source/finality markers remains unknown rather than being
        promoted into planning authority.
        """
        if decision is None:
            return (
                ProjectManagementDecisionProjectionV1()
            )

        if not isinstance(
            decision,
            ProjectManagementDecisionProjectionV1,
        ):
            raise TypeError(
                "decision must be a "
                "ProjectManagementDecisionProjectionV1"
            )

        if (
            decision.decision_source
            !=
            "debate_room.judge"
        ):
            return (
                ProjectManagementDecisionProjectionV1()
            )

        if (
            decision.decision_status
            not in {
                "completed",
                "completed_with_fallback",
            }
        ):
            return (
                ProjectManagementDecisionProjectionV1()
            )

        return decision.model_copy(
            deep=True
        )

    def _primary_user_actor_names(
        self,
        packet: ProjectContextPacketV3,
    ) -> list[str]:
        """
        Derive operational users from canonical actor roles only.

        Payer, buyer and decision-maker status never independently
        materialize a user.
        """
        values = []

        for actor in packet.actors:

            if (
                actor.role
                not in self._PRIMARY_OPERATIONAL_ROLES
            ):
                continue

            name = clean_text(
                actor.name
            )

            if not name:
                continue

            values.append(
                name
            )

        return unique_texts(
            values
        )

    def _source_projection(
        self,
        packet: ProjectContextPacketV3,
    ) -> Dict[str, Any]:
        """
        Return exactly the authoritative source material allowed to
        influence project-management planning.

        Deliberately excluded:

        - description
        - primary_archetype
        - archetype_confidence
        - secondary_archetypes
        - domain_terms
        - use_case_terms
        - solution_terms
        - target_terms
        - search/query/RAG material

        The source hash therefore measures canonical planning input,
        not every field that happens to exist in ProjectContextPacketV3.
        """
        return {
            "source_context_schema_version": (
                packet.schema_version
            ),

            "project_name": packet.project_name,
            "language": packet.language,
            "target_region": packet.target_region,
            "industry": packet.industry_user_input,

            "problem": packet.problem.model_dump(
                mode="json"
            ),

            "solution": packet.solution.model_dump(
                mode="json"
            ),

            "actors": [
                actor.model_dump(
                    mode="json"
                )
                for actor in packet.actors
            ],

            "payer_actor_names": list(
                packet.payer_actor_names
            ),

            "decision_maker_actor_names": list(
                packet.decision_maker_actor_names
            ),

            "partner_actor_names": list(
                packet.partner_actor_names
            ),

            "blocker_actor_names": list(
                packet.blocker_actor_names
            ),

            "priority_workflows": [
                workflow.model_dump(
                    mode="json"
                )
                for workflow
                in packet.priority_workflows
            ],

            "transaction_unit": (
                packet.transaction_unit.model_dump(
                    mode="json"
                )
            ),

            "mvp_scope": list(
                packet.mvp_scope
            ),

            "scope_exclusions": list(
                packet.scope_exclusions
            ),

            "input_data": list(
                packet.input_data
            ),

            "output_decision": list(
                packet.output_decision
            ),

            "human_oversight": list(
                packet.human_oversight
            ),

            "maintenance_model": list(
                packet.maintenance_model
            ),

            "deployment_environment": list(
                packet.deployment_environment
            ),

            "success_metrics": list(
                packet.success_metrics
            ),

            "business_model_hypotheses": list(
                packet.business_model_hypotheses
            ),

            "constraints": list(
                packet.constraints
            ),

            "regulatory_flags": list(
                packet.regulatory_flags
            ),

            "clarification_facts": dict(
                packet.clarification_facts
            ),

            "assumptions": list(
                packet.assumptions
            ),

            "unknowns": list(
                packet.blocking_missing_fields
            ),

            "warnings": list(
                packet.validation_warnings
            ),

            "forbidden_adjacent_domains": list(
                packet.forbidden_adjacent_domains
            ),
        }

    def _context_projection(
        self,
        context: ProjectManagementContextV1,
    ) -> Dict[str, Any]:
        """
        Return the PM context material owned by context_hash.

        Hash fields are excluded to avoid recursive/self-referential
        hashing.
        """
        return context.model_dump(
            mode="json",
            exclude={
                "source_context_hash",
                "context_hash",
            },
        )

    def _stable_sha256(
        self,
        value: Any,
    ) -> str:
        """
        Stable UTF-8 SHA-256 over canonical JSON.

        Dictionary key order is normalized.
        Meaningful list order is intentionally preserved.
        """
        material = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            allow_nan=False,
        )

        return hashlib.sha256(
            material.encode(
                "utf-8"
            )
        ).hexdigest()


project_management_context_builder = (
    ProjectManagementContextBuilder()
)