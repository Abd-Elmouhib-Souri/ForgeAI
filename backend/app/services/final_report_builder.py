from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


class FinalReportBuilder:
    """
    Canonical Final Report projection.

    Authority boundaries:

    - Project context comes from the canonical context packet.
    - Claim semantics come only from EvidenceLedger.
    - Source identity comes only from CanonicalSourceLedger.
    - Final decision comes only from Debate Room judge.
    - Startup score is presentation data and never overrides the judge.
    - This service does not run classification, readiness, evidence,
      competitive, or debate logic.
    """

    FORMAT = "final_report_v1_canonical_projection"
    SCHEMA_VERSION = "final_report_v1"

    CANONICAL_EVIDENCE_STATUSES = {
        "sourced",
        "estimated",
        "not_confirmed",
    }

    CANONICAL_CLAIM_KINDS = {
        "evidence_claim",
        "hypothesis",
        "estimate",
        "recommendation",
        "audit_conclusion",
        "project_input",
    }

    SOURCE_BUCKETS = (
        # Business identity is already canonical here.
        "local_direct_competitor_sources",
        "direct_competitor_sources",
        "adjacent_solution_sources",

        # Geography / benchmark projections.
        "regional_benchmark_sources",
        "international_benchmark_sources",

        # Technology projections.
        "technology_provider_sources",
        "technology_benchmark_sources",

        # Market / ecosystem evidence.
        "local_ecosystem_sources",
        "ecosystem_actor_sources",
        "market_context_sources",
        "market_evidence_sources",

        # Canonical utility buckets exposed by the ledger.
        "official_source_items",
        "directory_sources",
        "evidence_sources",
        "benchmark_sources",
    )

    MODULE_KEYS = (
        "market_study",
        "swot",
        "business_model_canvas",
        "competitive_analysis",
        "personas",
        "financial_estimation",
        "startup_score",
        "debate_room",
        "evidence_ledger",
    )

    def build(
        self,
        analysis_data: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        data = (
            analysis_data
            if isinstance(
                analysis_data,
                dict,
            )
            else {}
        )

        context, context_source = (
            self._canonical_context(
                data
            )
        )

        evidence = (
            self._canonical_evidence(
                data
            )
        )

        competitive = (
            self._canonical_competitive_projection(
                data
            )
        )

        decision = (
            self._debate_decision(
                data
            )
        )

        meeting_preparation = (
            self._meeting_preparation(
                data
            )
        )

        startup_score = (
            self._startup_score_projection(
                data
            )
        )

        executive_summary = (
            self._executive_synthesis(
                evidence=evidence,
                decision=decision,
            )
        )

        return {
            "format": self.FORMAT,
            "schema_version":
                self.SCHEMA_VERSION,

            "authority_contract": {
                "context":
                    context_source,
                "evidence":
                    "evidence_ledger",
                "sources":
                    competitive[
                        "source_ledger_source"
                    ],
                "decision":
                    decision[
                        "source"
                    ],
                "recalculates_readiness":
                    False,
                "reclassifies_sources":
                    False,
                "reclassifies_evidence":
                    False,
                "recalculates_verdict":
                    False,
            },

            "context": context,
            "evidence": evidence,
            "competitive": competitive,
            "decision": decision,

            "executive_summary":
                executive_summary,

            "meeting_preparation":
                meeting_preparation,

            "startup_score":
                startup_score,

            "module_presence":
                {
                    key: isinstance(
                        data.get(key),
                        (dict, list),
                    )
                    and bool(
                        data.get(key)
                    )
                    for key
                    in self.MODULE_KEYS
                },
        }

    # =========================================================
    # Canonical project context
    # =========================================================

    def _canonical_context(
        self,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], str]:
        readiness = self._dict(
            data.get(
                "idea_readiness"
            )
        )

        candidates = (
            (
                "project_context_packet",
                data.get(
                    "project_context_packet"
                ),
            ),
            (
                "structured_project_context",
                data.get(
                    "structured_project_context"
                ),
            ),
            (
                "canonical_context",
                data.get(
                    "canonical_context"
                ),
            ),
            (
                "idea_readiness.project_context_packet",
                readiness.get(
                    "project_context_packet"
                ),
            ),
            (
                "idea_readiness.context_packet",
                readiness.get(
                    "context_packet"
                ),
            ),
        )

        for source, value in candidates:
            if isinstance(
                value,
                dict,
            ) and value:
                return (
                    deepcopy(value),
                    source,
                )

        return {}, ""

    # =========================================================
    # EvidenceLedger consumer
    # =========================================================

    def _canonical_evidence(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        ledger = self._dict(
            data.get(
                "evidence_ledger"
            )
        )

        if not ledger:
            return {
                "ledger_present": False,
                "status_contract": "",
                "canonical_evidence_statuses": [],
                "claims": [],
                "source_index": {},
            }

        # -----------------------------------------------------
        # Canonical EvidenceLedger source catalog.
        # -----------------------------------------------------

        source_index: Dict[
            str,
            Dict[str, Any],
        ] = {}

        raw_source_index = (
            ledger.get(
                "source_index"
            )
        )

        if isinstance(
            raw_source_index,
            dict,
        ):
            for raw_id, raw_source in (
                raw_source_index.items()
            ):
                source_id = str(
                    raw_id
                    or ""
                ).strip()

                if (
                    not source_id
                    or not isinstance(
                        raw_source,
                        dict,
                    )
                ):
                    continue

                compact = deepcopy(
                    raw_source
                )

                # EvidenceLedger.source_index key owns identity.
                compact[
                    "source_id"
                ] = source_id

                source_index[
                    source_id
                ] = compact

        # -----------------------------------------------------
        # Canonical claims.
        # -----------------------------------------------------

        claims: List[
            Dict[str, Any]
        ] = []

        for raw_claim in self._list(
            ledger.get(
                "claims"
            )
        ):
            if not isinstance(
                raw_claim,
                dict,
            ):
                continue

            evidence_status = str(
                raw_claim.get(
                    "evidence_status"
                )
                or ""
            ).strip()

            if (
                evidence_status
                not in
                self.CANONICAL_EVIDENCE_STATUSES
            ):
                evidence_status = ""

            claim_kind = str(
                raw_claim.get(
                    "claim_kind"
                )
                or ""
            ).strip()

            if (
                claim_kind
                not in
                self.CANONICAL_CLAIM_KINDS
            ):
                claim_kind = ""

            raw_validation = (
                raw_claim.get(
                    "validation_required"
                )
            )

            validation_required = (
                raw_validation
                if isinstance(
                    raw_validation,
                    bool,
                )
                else None
            )

            source_ids = (
                self._unique_strings(
                    raw_claim.get(
                        "source_ids"
                    )
                )
            )

            traceability = (
                self._resolve_claim_sources(
                    evidence_status=
                        evidence_status,
                    source_ids=
                        source_ids,
                    source_index=
                        source_index,
                )
            )

            claims.append(
                {
                    "claim_id": str(
                        raw_claim.get(
                            "claim_id"
                        )
                        or ""
                    ).strip(),

                    "path": str(
                        raw_claim.get(
                            "path"
                        )
                        or ""
                    ).strip(),

                    "category": str(
                        raw_claim.get(
                            "category"
                        )
                        or ""
                    ).strip(),

                    "claim": str(
                        raw_claim.get(
                            "claim"
                        )
                        or ""
                    ).strip(),

                    "public_text": str(
                        raw_claim.get(
                            "public_text"
                        )
                        or ""
                    ).strip(),

                    "confidence": str(
                        raw_claim.get(
                            "confidence"
                        )
                        or ""
                    ).strip(),

                    # Canonical semantic axes.
                    "evidence_status":
                        evidence_status,

                    "claim_kind":
                        claim_kind,

                    "validation_required":
                        validation_required,

                    # Canonical references remain visible.
                    "source_ids":
                        source_ids,

                    # Exact source relationship projection.
                    **traceability,
                }
            )

        raw_statuses = (
            ledger.get(
                "canonical_evidence_statuses"
            )
        )

        statuses = [
            status
            for status
            in self._unique_strings(
                raw_statuses
            )
            if status
            in self.CANONICAL_EVIDENCE_STATUSES
        ]

        return {
            "ledger_present": True,

            "status_contract": str(
                ledger.get(
                    "status_contract"
                )
                or ""
            ).strip(),

            "canonical_evidence_statuses":
                statuses,

            "claims":
                claims,

            "source_index":
                source_index,
        }

    # =========================================================
    # CanonicalSourceLedger consumer
    # =========================================================

    def _canonical_source_ledger(
        self,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], str]:
        top_level = data.get(
            "canonical_source_ledger"
        )

        if isinstance(
            top_level,
            dict,
        ) and top_level:
            return (
                top_level,
                "canonical_source_ledger",
            )

        competitive = self._dict(
            data.get(
                "competitive_analysis"
            )
        )

        nested = competitive.get(
            "canonical_source_ledger"
        )

        if isinstance(
            nested,
            dict,
        ) and nested:
            return (
                nested,
                (
                    "competitive_analysis."
                    "canonical_source_ledger"
                ),
            )

        return {}, ""

    def _canonical_competitive_projection(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        ledger, source = (
            self._canonical_source_ledger(
                data
            )
        )

        result: Dict[str, Any] = {
            "source_ledger_present":
                bool(ledger),
            "source_ledger_source":
                source,
            "canonical_sources_count":
                0,
            "canonical_source_ids":
                [],
            "counts":
                {},
        }

        for bucket in self.SOURCE_BUCKETS:
            result[
                self._bucket_id_key(
                    bucket
                )
            ] = []

        if not ledger:
            return result

        result[
            "canonical_source_ids"
        ] = self._source_ids(
            ledger.get(
                "sources"
            )
        )

        # The count is copied from CanonicalSourceLedger.
        # We deliberately do not infer it from list length.
        raw_count = ledger.get(
            "canonical_sources_count"
        )

        if (
            isinstance(
                raw_count,
                (int, float),
            )
            and not isinstance(
                raw_count,
                bool,
            )
        ):
            result[
                "canonical_sources_count"
            ] = max(
                0,
                int(
                    raw_count
                ),
            )

        raw_counts = ledger.get(
            "counts"
        )

        if isinstance(
            raw_counts,
            dict,
        ):
            canonical_counts = {}

            for raw_key, raw_value in (
                raw_counts.items()
            ):
                key = str(
                    raw_key
                    or ""
                ).strip()

                if (
                    not key
                    or isinstance(
                        raw_value,
                        bool,
                    )
                    or not isinstance(
                        raw_value,
                        (int, float),
                    )
                ):
                    continue

                canonical_counts[
                    key
                ] = deepcopy(
                    raw_value
                )

            result[
                "counts"
            ] = canonical_counts

        for bucket in self.SOURCE_BUCKETS:
            result[
                self._bucket_id_key(
                    bucket
                )
            ] = self._source_ids(
                ledger.get(
                    bucket
                )
            )

        return result

    # =========================================================
    # Debate Room is final decision authority
    # =========================================================

    def _debate_decision(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        debate = self._dict(
            data.get(
                "debate_room"
            )
        )

        judge = self._dict(
            debate.get(
                "judge"
            )
        )

        empty = {
            "available": False,
            "source": "",
            "format": "",
            "status": "",
            "verdict_code": "",
            "verdict": "",
            "final_recommendation": "",
            "risk_level": "",
            "argument_strength_score": None,
            "confidence_score": None,
            "debate_synthesis": "",
            "improved_idea": "",
            "next_actions": [],
            "action_plan": [],
            "critical_risks": [],
            "validated_findings": [],
            "validated_opportunities": [],
            "potential_opportunities": [],
            "missing_evidence": [],
            "weak_assumptions": [],
            "go_no_go_conditions": [],
            "go_conditions": [],
            "no_go_conditions": [],
            "decision_by_round": [],
            "committee_vote": {},
            "vetoes": [],
        }

        if not judge:
            return empty

        next_actions = (
            judge.get(
                "next_actions"
            )
        )

        if not isinstance(
            next_actions,
            list,
        ):
            # Compatibility remains within the same Judge authority.
            next_actions = (
                judge.get(
                    "action_plan"
                )
            )

        decision_by_round = []

        for item in self._list(
            judge.get(
                "decision_by_round"
            )
        ):
            if isinstance(
                item,
                dict,
            ):
                decision_by_round.append(
                    deepcopy(
                        item
                    )
                )

        committee_vote = (
            judge.get(
                "committee_vote"
            )
        )

        if not isinstance(
            committee_vote,
            dict,
        ):
            committee_vote = {}

        vetoes = judge.get(
            "vetoes"
        )

        if not isinstance(
            vetoes,
            list,
        ):
            vetoes = []

        return {
            "available": True,
            "source":
                "debate_room.judge",

            "format": str(
                judge.get(
                    "format"
                )
                or ""
            ).strip(),

            "status": str(
                judge.get(
                    "status"
                )
                or ""
            ).strip(),

            "verdict_code": str(
                judge.get(
                    "verdict_code"
                )
                or ""
            ).strip(),

            "verdict": str(
                judge.get(
                    "verdict"
                )
                or ""
            ).strip(),

            "final_recommendation": str(
                judge.get(
                    "final_recommendation"
                )
                or ""
            ).strip(),

            "risk_level": str(
                judge.get(
                    "risk_level"
                )
                or ""
            ).strip(),

            # Scores are copied, never recalculated.
            "argument_strength_score":
                deepcopy(
                    judge.get(
                        "argument_strength_score"
                    )
                ),

            "confidence_score":
                deepcopy(
                    judge.get(
                        "confidence_score"
                    )
                ),

            "debate_synthesis": str(
                judge.get(
                    "debate_synthesis"
                )
                or ""
            ).strip(),

            "improved_idea": str(
                judge.get(
                    "improved_idea"
                )
                or ""
            ).strip(),

            "next_actions":
                self._unique_strings(
                    next_actions
                ),

            "action_plan":
                self._unique_strings(
                    judge.get(
                        "action_plan"
                    )
                ),

            "critical_risks":
                self._unique_strings(
                    judge.get(
                        "critical_risks"
                    )
                ),

            "validated_findings":
                self._unique_strings(
                    judge.get(
                        "validated_findings"
                    )
                ),

            "validated_opportunities":
                self._unique_strings(
                    judge.get(
                        "validated_opportunities"
                    )
                ),

            "potential_opportunities":
                self._unique_strings(
                    judge.get(
                        "potential_opportunities"
                    )
                ),

            "missing_evidence":
                self._unique_strings(
                    judge.get(
                        "missing_evidence"
                    )
                ),

            "weak_assumptions":
                self._unique_strings(
                    judge.get(
                        "weak_assumptions"
                    )
                ),

            # These three axes are copied independently.
            # If explicit GO / NO-GO lists are missing, we do not
            # attempt to split the combined list ourselves.
            "go_no_go_conditions":
                self._unique_strings(
                    judge.get(
                        "go_no_go_conditions"
                    )
                ),

            "go_conditions":
                self._unique_strings(
                    judge.get(
                        "go_conditions"
                    )
                ),

            "no_go_conditions":
                self._unique_strings(
                    judge.get(
                        "no_go_conditions"
                    )
                ),

            "decision_by_round":
                decision_by_round,

            "committee_vote":
                deepcopy(
                    committee_vote
                ),

            "vetoes":
                deepcopy(
                    vetoes
                ),
        }

    def _meeting_preparation(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        debate = self._dict(
            data.get(
                "debate_room"
            )
        )

        preparation = debate.get(
            "meeting_preparation"
        )

        if not isinstance(
            preparation,
            dict,
        ):
            return {}

        return {
            "title": str(
                preparation.get(
                    "title"
                )
                or ""
            ).strip(),

            "project": str(
                preparation.get(
                    "project"
                )
                or ""
            ).strip(),

            "top_questions":
                self._unique_strings(
                    preparation.get(
                        "top_questions"
                    )
                ),

            "recommended_answers":
                self._unique_strings(
                    preparation.get(
                        "recommended_answers"
                    )
                ),

            # Future preparation material, not current evidence.
            "proofs_to_prepare":
                self._unique_strings(
                    preparation.get(
                        "proofs_to_prepare"
                    )
                ),

            "answers_to_avoid":
                self._unique_strings(
                    preparation.get(
                        "answers_to_avoid"
                    )
                ),

            # Round-level evidence/information gaps.
            "unresolved_questions":
                self._unique_strings(
                    preparation.get(
                        "unresolved_questions"
                    )
                ),

            # Q&A uncertainty.
            "unresolved_points":
                self._unique_strings(
                    preparation.get(
                        "unresolved_points"
                    )
                ),

            # Concrete next questions to reduce uncertainty.
            "follow_up_questions":
                self._unique_strings(
                    preparation.get(
                        "follow_up_questions"
                    )
                ),
        }

    # =========================================================
    # Startup score is presentation only
    # =========================================================

    def _resolve_claim_sources(
        self,
        *,
        evidence_status: str,
        source_ids: Any,
        source_index: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Resolve claim references exclusively from
        EvidenceLedger.source_index.

        Only a canonical `sourced` claim may expose the resolved
        references as supporting evidence.

        Every other status keeps resolved references as consulted
        sources so they cannot be promoted into supporting evidence.
        """

        resolved: List[
            Dict[str, Any]
        ] = []

        for source_id in (
            self._unique_strings(
                source_ids
            )
        ):
            raw_source = (
                source_index.get(
                    source_id
                )
            )

            if not isinstance(
                raw_source,
                dict,
            ):
                # Missing canonical source:
                # never reconstruct it elsewhere.
                continue

            canonical_source = deepcopy(
                raw_source
            )

            canonical_source[
                "source_id"
            ] = source_id

            resolved.append(
                canonical_source
            )

        if (
            evidence_status
            == "sourced"
        ):
            return {
                "supporting_evidence":
                    resolved,

                "consulted_sources":
                    [],
            }

        return {
            "supporting_evidence":
                [],

            "consulted_sources":
                resolved,
        }

    def _executive_synthesis(
        self,
        *,
        evidence: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a deterministic executive projection.

        No claim is rewritten or promoted here. EvidenceLedger semantics
        are copied exactly into separate presentation buckets.
        """

        sourced: List[Dict[str, Any]] = []
        estimated: List[Dict[str, Any]] = []
        not_confirmed: List[Dict[str, Any]] = []
        unclassified: List[Dict[str, Any]] = []
        validation_priorities: List[
            Dict[str, Any]
        ] = []

        for raw_claim in self._list(
            evidence.get(
                "claims"
            )
        ):
            if not isinstance(
                raw_claim,
                dict,
            ):
                continue

            claim = (
                self._executive_claim_projection(
                    raw_claim
                )
            )

            # Empty claims cannot become executive assertions.
            if not claim[
                "text"
            ]:
                continue

            status = claim[
                "evidence_status"
            ]

            if status == "sourced":
                sourced.append(
                    claim
                )
            elif status == "estimated":
                estimated.append(
                    claim
                )
            elif status == "not_confirmed":
                not_confirmed.append(
                    claim
                )
            else:
                # Unknown or invalid status is deliberately isolated.
                # It is never upgraded to sourced evidence.
                unclassified.append(
                    claim
                )

            if (
                claim[
                    "validation_required"
                ]
                is True
            ):
                validation_priorities.append(
                    claim
                )

        decision_available = bool(
            decision.get(
                "available"
            )
        )

        return {
            "decision_source": (
                str(
                    decision.get(
                        "source"
                    )
                    or ""
                ).strip()
                if decision_available
                else ""
            ),
            "verdict_code": (
                str(
                    decision.get(
                        "verdict_code"
                    )
                    or ""
                ).strip()
                if decision_available
                else ""
            ),
            "final_recommendation": (
                str(
                    decision.get(
                        "final_recommendation"
                    )
                    or ""
                ).strip()
                if decision_available
                else ""
            ),

            "evidence_counts": {
                "sourced":
                    len(
                        sourced
                    ),
                "estimated":
                    len(
                        estimated
                    ),
                "not_confirmed":
                    len(
                        not_confirmed
                    ),
                "unclassified":
                    len(
                        unclassified
                    ),
                "validation_required":
                    len(
                        validation_priorities
                    ),
            },

            # Bounded executive projections. Full claim catalog remains
            # available under report["evidence"]["claims"].
            "supported_claims":
                sourced[:5],
            "estimated_claims":
                estimated[:5],
            "not_confirmed_claims":
                not_confirmed[:5],
            "unclassified_claims":
                unclassified[:5],
            "validation_priorities":
                validation_priorities[:8],
        }

    def _executive_claim_projection(
        self,
        claim: Dict[str, Any],
    ) -> Dict[str, Any]:
        public_text = str(
            claim.get(
                "public_text"
            )
            or ""
        ).strip()

        canonical_text = str(
            claim.get(
                "claim"
            )
            or ""
        ).strip()

        supporting_evidence = [
            deepcopy(
                item
            )
            for item in self._list(
                claim.get(
                    "supporting_evidence"
                )
            )
            if isinstance(
                item,
                dict,
            )
        ]

        consulted_sources = [
            deepcopy(
                item
            )
            for item in self._list(
                claim.get(
                    "consulted_sources"
                )
            )
            if isinstance(
                item,
                dict,
            )
        ]

        return {
            "claim_id": str(
                claim.get(
                    "claim_id"
                )
                or ""
            ).strip(),

            "path": str(
                claim.get(
                    "path"
                )
                or ""
            ).strip(),

            "category": str(
                claim.get(
                    "category"
                )
                or ""
            ).strip(),

            # Wording only; never semantic authority.
            "text":
                public_text
                or canonical_text,

            "evidence_status": str(
                claim.get(
                    "evidence_status"
                )
                or ""
            ).strip(),

            "claim_kind": str(
                claim.get(
                    "claim_kind"
                )
                or ""
            ).strip(),

            "validation_required":
                claim.get(
                    "validation_required"
                )
                if isinstance(
                    claim.get(
                        "validation_required"
                    ),
                    bool,
                )
                else None,

            "source_ids":
                self._unique_strings(
                    claim.get(
                        "source_ids"
                    )
                ),

            "supporting_evidence":
                supporting_evidence,

            "consulted_sources":
                consulted_sources,
        }

    def _startup_score_projection(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        score = self._dict(
            data.get(
                "startup_score"
            )
        )

        if not score:
            return {}

        allowed = (
            "global_score",
            "innovation",
            "feasibility",
            "profitability",
            "scalability",
            "potential_score",
            "evidence_confidence_score",
            "execution_readiness_score",
            "evidence_confidence_level",
            "score_explanation",
        )

        return {
            key: deepcopy(
                score.get(key)
            )
            for key in allowed
            if key in score
        }

    # =========================================================
    # Generic helpers
    # =========================================================

    def _source_ids(
        self,
        raw_sources: Any,
    ) -> List[str]:
        result: List[str] = []

        for item in self._list(
            raw_sources
        ):
            if not isinstance(
                item,
                dict,
            ):
                continue

            source_id = str(
                item.get(
                    "source_id"
                )
                or ""
            ).strip()

            if (
                source_id
                and source_id
                not in result
            ):
                result.append(
                    source_id
                )

        return result

    def _bucket_id_key(
        self,
        bucket: str,
    ) -> str:
        suffix = "_sources"

        if bucket.endswith(
            suffix
        ):
            bucket = bucket[
                :-len(suffix)
            ]

        return (
            bucket
            + "_source_ids"
        )

    def _unique_strings(
        self,
        value: Any,
    ) -> List[str]:
        result: List[str] = []

        for item in self._list(
            value
        ):
            text = str(
                item
                or ""
            ).strip()

            if (
                text
                and text
                not in result
            ):
                result.append(
                    text
                )

        return result

    @staticmethod
    def _dict(
        value: Any,
    ) -> Dict[str, Any]:
        return (
            value
            if isinstance(
                value,
                dict,
            )
            else {}
        )

    @staticmethod
    def _list(
        value: Any,
    ) -> List[Any]:
        return (
            value
            if isinstance(
                value,
                list,
            )
            else []
        )


final_report_builder = FinalReportBuilder()
