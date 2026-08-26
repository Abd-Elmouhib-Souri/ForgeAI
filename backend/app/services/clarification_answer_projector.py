from __future__ import annotations

import re

from typing import Any, Mapping

from app.schemas.analysis_context import (
    ActorRole,
    ProjectContextPacketV3,
    clean_text,
    comparison_key,
    unique_texts,
)


class ClarificationAnswerProjector:
    """
    Projects explicit, field-bound user clarification answers onto the
    canonical ProjectContextPacketV3.

    Authority rules
    ---------------
    1. A clarification answer is an explicit user fact.
    2. The original project description is never rewritten.
    3. Every answer is preserved in clarification_facts.
    4. A dedicated canonical structure is updated only when the mapping
       from clarification field to canonical structure is unambiguous.
    5. Unknown/unresolved answers are preserved as facts but are never
       projected into structural fields as if they were resolved.
    """

    UNRESOLVED_MARKERS = (
        "unknown",
        "not known",
        "not defined",
        "not defined yet",
        "undefined",
        "not decided",
        "not decided yet",
        "to be defined",
        "to be decided",
        "to decide",
        "tbd",
        "a definir",
        "non defini",
        "pas defini",
        "pas encore defini",
        "a decider",
        "inconnu",
        "inconnue",
    )

    ACTOR_ROLES = {
        "supply_side":
            ActorRole.PROVIDER,

        "demand_side":
            ActorRole.BUYER,

        "operational_user":
            ActorRole.USER,

        "decision_maker":
            ActorRole.DECISION_MAKER,

        "payer":
            ActorRole.PAYER,

        "regulated_provider":
            ActorRole.PROVIDER,

        "beneficiary":
            ActorRole.BENEFICIARY,

        "service_provider":
            ActorRole.PROVIDER,

        "service_client":
            ActorRole.BUYER,

        "creator_side":
            ActorRole.PROVIDER,

        "audience_side":
            ActorRole.BENEFICIARY,
    }

    TRANSACTION_FIELDS = {
        "payment_responsibility":
            "payment_responsibility",

        "trust_mechanism":
            "trust_mechanism",

        "dispute_responsibility":
            "dispute_responsibility",
    }

    def apply(
        self,
        packet: ProjectContextPacketV3,
        answers: Mapping[str, Any] | None,
    ) -> ProjectContextPacketV3:
        """
        Return a new canonical packet enriched by explicit clarification
        answers.
        """
        normalized = (
            self._normalize_answers(
                answers
            )
        )

        if not normalized:
            return packet

        payload = packet.model_dump(
            mode="python"
        )

        original_description = (
            packet.description
        )

        facts = dict(
            payload.get(
                "clarification_facts"
            )
            or {}
        )

        facts.update(
            normalized
        )

        payload[
            "clarification_facts"
        ] = facts

        for field, answer in (
            normalized.items()
        ):
            if not self._is_resolved(
                answer
            ):
                continue

            self._project_structural_fact(
                payload=payload,
                field=field,
                answer=answer,
            )

        # Explicit clarification never rewrites the user's original project
        # description.
        payload[
            "description"
        ] = original_description

        return (
            ProjectContextPacketV3
            .model_validate(
                payload
            )
        )

    def _normalize_answers(
        self,
        answers: Mapping[str, Any] | None,
    ) -> dict[str, str]:
        output: dict[str, str] = {}

        for raw_field, raw_answer in dict(
            answers or {}
        ).items():
            field = clean_text(
                raw_field
            )

            answer = clean_text(
                raw_answer
            )

            if not field:
                continue

            if not answer:
                continue

            output[
                field
            ] = answer

        return output

    def is_resolved(
        self,
        answer: str,
    ) -> bool:
        """
        Return whether an explicit clarification contains resolved
        information rather than an unresolved placeholder.

        comparison_key() owns Unicode/accent normalization.
        """
        return self._is_resolved(
            answer
        )

    def _is_resolved(
        self,
        answer: str,
    ) -> bool:
        key = comparison_key(
            answer
        )

        if not key:
            return False

        return not any(
            comparison_key(
                marker
            )
            in key
            for marker in (
                self.UNRESOLVED_MARKERS
            )
            if comparison_key(
                marker
            )
        )

    def _project_structural_fact(
        self,
        *,
        payload: dict[str, Any],
        field: str,
        answer: str,
    ) -> None:
        """
        Project only structurally unambiguous mappings.

        Other fields remain available through clarification_facts and are
        consumed directly by ContextConfidenceGate.
        """
        if field == "target_region":
            payload[
                "target_region"
            ] = answer
            return

        if field == "problem":
            problem = dict(
                payload.get(
                    "problem"
                )
                or {}
            )

            problem[
                "pain"
            ] = answer

            payload[
                "problem"
            ] = problem
            return

        if field == "solution":
            solution = dict(
                payload.get(
                    "solution"
                )
                or {}
            )

            solution[
                "mechanism"
            ] = answer

            payload[
                "solution"
            ] = solution
            return

        if field == "business_model":
            payload[
                "business_model_hypotheses"
            ] = unique_texts(
                [
                    *(
                        payload.get(
                            "business_model_hypotheses"
                        )
                        or []
                    ),
                    answer,
                ]
            )
            return

        if field == "deployment_environment":
            payload[
                "deployment_environment"
            ] = unique_texts(
                [
                    *(
                        payload.get(
                            "deployment_environment"
                        )
                        or []
                    ),
                    answer,
                ]
            )
            return

        if field == "regulatory_scope":
            payload[
                "regulatory_flags"
            ] = unique_texts(
                [
                    *(
                        payload.get(
                            "regulatory_flags"
                        )
                        or []
                    ),
                    answer,
                ]
            )
            return

        if field == "transaction_unit":
            transaction = dict(
                payload.get(
                    "transaction_unit"
                )
                or {}
            )

            transaction[
                "description"
            ] = answer

            if not clean_text(
                transaction.get(
                    "name"
                )
            ):
                transaction[
                    "name"
                ] = answer

            payload[
                "transaction_unit"
            ] = transaction
            return

        if field == "fulfillment_logistics":
            transaction = dict(
                payload.get(
                    "transaction_unit"
                )
                or {}
            )

            transaction[
                "fulfillment_mode"
            ] = answer

            payload[
                "transaction_unit"
            ] = transaction
            return

        transaction_attribute = (
            self.TRANSACTION_FIELDS.get(
                field
            )
        )

        if transaction_attribute:
            transaction = dict(
                payload.get(
                    "transaction_unit"
                )
                or {}
            )

            transaction[
                transaction_attribute
            ] = answer

            payload[
                "transaction_unit"
            ] = transaction
            return

        actor_role = (
            self.ACTOR_ROLES.get(
                field
            )
        )

        if actor_role is not None:
            actor_identity = (
                self._clarification_actor_identity(
                    answer
                )
            )

            # Full clarification prose has already been preserved in
            # clarification_facts by apply().
            #
            # Only a reliable bounded identity may enter ActorContext.
            # If no identity can be derived safely, do not manufacture
            # one and do not truncate the explicit answer.
            if actor_identity:
                self._project_actor(
                    payload=payload,
                    field=field,
                    actor_name=actor_identity,
                    role=actor_role,
                )

            return

    def _clarification_actor_identity(
        self,
        answer: str,
    ) -> str:
        """
        U5 bounded clarification actor identity authority.

        Clarification facts and actor identities are different concepts.

        A complete descriptive answer remains intact inside
        clarification_facts. ActorContext.name receives only a bounded,
        semantically identifiable actor identity.

        Rules:

        1. Existing short answers remain unchanged.
        2. Long answers may project a noun phrase only when a clear
           copular relation exists:
               X est Y
               X sont Y
               X is Y
               X are Y
               X consists of Y
        3. Relative/descriptive clauses after Y are not part of identity.
        4. No arbitrary character truncation is ever performed.
        5. If no reliable bounded identity can be extracted, return ""
           and preserve only the clarification fact.

        This authority contains no project, sector, country or archetype
        vocabulary.
        """

        value = clean_text(
            answer
        )

        if not value:
            return ""

        # ------------------------------------------------------
        # Existing normal clarification behavior is preserved.
        #
        # Examples:
        #   "equipment owners"
        #   "responsable maintenance"
        #   "PME cliente"
        # ------------------------------------------------------

        if len(value) <= 180:
            return value

        # ------------------------------------------------------
        # Long prose is not an ActorContext.name.
        #
        # Inspect only the first statement for one explicit
        # identity relation. We deliberately do not shorten the
        # text to 180 characters.
        # ------------------------------------------------------

        first_statement = re.split(
            r"(?:\r?\n)+"
            r"|(?<=[.!?;])\s+",
            value,
            maxsplit=1,
        )[0]

        relation = re.search(
            r"\s+(?:"
            r"est"
            r"|sont"
            r"|is"
            r"|are"
            r"|consists?\s+of"
            r"|consist\s+of"
            r")\s+",
            first_statement,
            flags=re.IGNORECASE,
        )

        if relation is None:
            return ""

        candidate = clean_text(
            first_statement[
                relation.end():
            ]
        )

        if not candidate:
            return ""

        # ------------------------------------------------------
        # Identity ends before a relative/descriptive clause.
        #
        # Examples:
        #
        # "industrial companies whose managers..."
        # -> "industrial companies"
        #
        # "le directeur des op?rations qui valide..."
        # -> "le directeur des op?rations"
        # ------------------------------------------------------

        candidate = re.split(
            r"\s+(?:"
            r"qui"
            r"|who"
            r"|whose"
            r"|which"
            r"|that"
            r")\b"
            r"|[,;]",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        candidate = clean_text(
            candidate
        )

        # Remove only a leading grammatical determiner.
        candidate = re.sub(
            r"^(?:"
            r"le\s+"
            r"|la\s+"
            r"|les\s+"
            r"|l['?]\s*"
            r"|un\s+"
            r"|une\s+"
            r"|des\s+"
            r"|du\s+"
            r"|de\s+la\s+"
            r"|de\s+l['?]\s*"
            r"|the\s+"
            r"|a\s+"
            r"|an\s+"
            r")",
            "",
            candidate,
            count=1,
            flags=re.IGNORECASE,
        )

        candidate = clean_text(
            candidate
        ).strip(
            " .,:;-"
        )

        if not candidate:
            return ""

        # ------------------------------------------------------
        # Schema bound is a validation guard, not a truncation
        # target.
        # ------------------------------------------------------

        if len(candidate) > 180:
            return ""

        # A noun identity extending far beyond a normal actor
        # phrase is too ambiguous to project safely.
        if len(
            candidate.split()
        ) > 24:
            return ""

        return candidate


    def _project_actor(
        self,
        *,
        payload: dict[str, Any],
        field: str,
        actor_name: str,
        role: ActorRole,
    ) -> None:
        actors = [
            dict(actor)
            for actor in (
                payload.get(
                    "actors"
                )
                or []
            )
            if isinstance(
                actor,
                Mapping,
            )
        ]

        actor_key = comparison_key(
            actor_name
        )

        matched = False

        for actor in actors:
            if (
                comparison_key(
                    actor.get(
                        "name"
                    )
                )
                != actor_key
            ):
                continue

            # Explicit clarification has higher authority than inference.
            actor[
                "role"
            ] = role.value

            actor[
                "is_explicit"
            ] = True

            matched = True
            break

        if not matched:
            actors.append(
                {
                    "name":
                        actor_name,

                    "role":
                        role.value,

                    "description":
                        "",

                    "is_explicit":
                        True,

                    "decision_power":
                        (
                            "high"
                            if role
                            == ActorRole.DECISION_MAKER
                            else "unknown"
                        ),

                    "buying_power":
                        (
                            "high"
                            if role
                            in {
                                ActorRole.PAYER,
                                ActorRole.BUYER,
                            }
                            else "unknown"
                        ),
                }
            )

        payload[
            "actors"
        ] = actors

        if field == "decision_maker":
            payload[
                "decision_maker_actor_names"
            ] = unique_texts(
                [
                    *(
                        payload.get(
                            "decision_maker_actor_names"
                        )
                        or []
                    ),
                    actor_name,
                ]
            )

        if field == "payer":
            payload[
                "payer_actor_names"
            ] = unique_texts(
                [
                    *(
                        payload.get(
                            "payer_actor_names"
                        )
                        or []
                    ),
                    actor_name,
                ]
            )

        if field in {
            "supply_side",
            "demand_side",
        }:
            transaction = dict(
                payload.get(
                    "transaction_unit"
                )
                or {}
            )

            if field == "supply_side":
                transaction[
                    "supply_actor"
                ] = actor_name
            else:
                transaction[
                    "demand_actor"
                ] = actor_name

            payload[
                "transaction_unit"
            ] = transaction


clarification_answer_projector = (
    ClarificationAnswerProjector()
)
