import inspect

from app.services.final_report_builder import (
    FinalReportBuilder,
)


def _analysis():
    return {
        "project_context_packet": {
            "schema_version":
                "project_context_v3",
            "project_name":
                "Universal Project",
            "sector":
                "Canonical Sector",
            "target_region":
                "Canonical Region",
        },

        "evidence_ledger": {
            "status_contract":
                "canonical_evidence_status_v1",
            "canonical_evidence_statuses": [
                "sourced",
                "estimated",
                "not_confirmed",
            ],
            "claims": [
                {
                    "claim_id":
                        "claim_problem",
                    "path":
                        "market_study.problem",
                    "category":
                        "problem_context",
                    "claim":
                        "Canonical problem claim",
                    "public_text":
                        "Canonical public problem claim",
                    "confidence":
                        "high",
                    "evidence_status":
                        "sourced",
                    "claim_kind":
                        "evidence_claim",
                    "validation_required":
                        False,
                    "source_ids": [
                        "source_a",
                        "source_b",
                        "source_a",
                    ],
                },
                {
                    "claim_id":
                        "claim_finance",
                    "path":
                        "financial_estimation.estimated_mvp_budget",
                    "category":
                        "finance",
                    "claim":
                        "Planning estimate",
                    "public_text":
                        "Planning estimate",
                    "confidence":
                        "low",
                    "evidence_status":
                        "estimated",
                    "claim_kind":
                        "estimate",
                    "validation_required":
                        True,
                    "source_ids": [],
                },
            ],
            "source_index": {
                "source_a": {
                    "title":
                        "Primary evidence",
                },
                "source_b": {
                    "title":
                        "Secondary evidence",
                },
            },
        },

        # Presentation data deliberately conflicts with
        # EvidenceLedger. It must never win.
        "fact_check_report": {
            "claims": [
                {
                    "claim_id":
                        "fake_factchecker_claim",
                    "claim":
                        "Fake promoted claim",
                    "evidence_status":
                        "sourced",
                },
            ],
        },

        "competitive_analysis": {
            "local_competitors_count":
                99,
            "direct_competitors": [
                {
                    "source_id":
                        "raw_fake_competitor",
                },
            ],
            "canonical_source_ledger": {
                "canonical_sources_count":
                    4,
                "sources": [
                    {
                        "source_id":
                            "source_a",
                    },
                    {
                        "source_id":
                            "source_b",
                    },
                    {
                        "source_id":
                            "source_direct",
                    },
                    {
                        "source_id":
                            "source_adjacent",
                    },
                ],
                "local_direct_competitor_sources": [
                    {
                        "source_id":
                            "source_direct",
                    },
                ],
                "adjacent_solution_sources": [
                    {
                        "source_id":
                            "source_adjacent",
                    },
                ],
                "market_evidence_sources": [
                    {
                        "source_id":
                            "source_a",
                    },
                ],
            },
        },

        "debate_room": {
            "judge": {
                "verdict_code":
                    "conditional_go",
                "verdict":
                    "CONDITIONAL_GO",
                "final_recommendation":
                    "Run the bounded pilot.",
                "risk_level":
                    "medium",
                "next_actions": [
                    "Run pilot",
                    "Validate payer",
                ],
            },
            "meeting_preparation": {
                "unresolved_points": [
                    "Payer is not confirmed.",
                ],
                "follow_up_questions": [
                    "Who controls the budget?",
                ],
            },
        },

        # Deliberately conflicting alternative verdicts.
        "verdict_code":
            "go",

        "startup_score": {
            "global_score":
                7.5,
            "innovation":
                8.0,
            "feasibility":
                7.0,
            "profitability":
                6.5,
            "scalability":
                7.0,
            "canonical_verdict_code":
                "go",
            "verdict_code":
                "go",
            "score_explanation":
                "Score explanation.",
        },
    }


def test_final_report_uses_only_evidence_ledger_claim_semantics() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    evidence = report[
        "evidence"
    ]

    assert evidence[
        "ledger_present"
    ] is True

    claims = evidence[
        "claims"
    ]

    assert [
        item[
            "claim_id"
        ]
        for item in claims
    ] == [
        "claim_problem",
        "claim_finance",
    ]

    assert (
        "fake_factchecker_claim"
        not in {
            item[
                "claim_id"
            ]
            for item in claims
        }
    )

    problem = claims[0]

    assert (
        problem[
            "evidence_status"
        ]
        == "sourced"
    )

    assert (
        problem[
            "claim_kind"
        ]
        == "evidence_claim"
    )

    assert (
        problem[
            "validation_required"
        ]
        is False
    )

    assert problem[
        "source_ids"
    ] == [
        "source_a",
        "source_b",
    ]


def test_final_report_does_not_fallback_to_fact_checker_for_evidence() -> None:
    analysis = {
        "fact_check_report": {
            "claims": [
                {
                    "claim_id":
                        "presentation_only",
                    "evidence_status":
                        "sourced",
                },
            ],
        },
    }

    report = FinalReportBuilder().build(
        analysis
    )

    assert (
        report[
            "evidence"
        ][
            "ledger_present"
        ]
        is False
    )

    assert (
        report[
            "evidence"
        ][
            "claims"
        ]
        == []
    )


def test_final_report_decision_is_owned_only_by_debate_judge() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    decision = report[
        "decision"
    ]

    assert (
        decision[
            "source"
        ]
        == "debate_room.judge"
    )

    assert (
        decision[
            "verdict_code"
        ]
        == "conditional_go"
    )

    assert (
        decision[
            "verdict"
        ]
        == "CONDITIONAL_GO"
    )

    assert (
        decision[
            "final_recommendation"
        ]
        == "Run the bounded pilot."
    )

    assert decision[
        "next_actions"
    ] == [
        "Run pilot",
        "Validate payer",
    ]

    # Startup score must never become decision authority.
    assert (
        report[
            "startup_score"
        ].get(
            "verdict_code"
        )
        is None
    )

    assert (
        report[
            "startup_score"
        ].get(
            "canonical_verdict_code"
        )
        is None
    )


def test_final_report_competitors_use_only_canonical_source_ledger() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    competitive = report[
        "competitive"
    ]

    assert (
        competitive[
            "source_ledger_present"
        ]
        is True
    )

    assert (
        competitive[
            "source_ledger_source"
        ]
        == (
            "competitive_analysis."
            "canonical_source_ledger"
        )
    )

    assert (
        competitive[
            "canonical_sources_count"
        ]
        == 4
    )

    assert competitive[
        "local_direct_competitor_source_ids"
    ] == [
        "source_direct",
    ]

    assert competitive[
        "adjacent_solution_source_ids"
    ] == [
        "source_adjacent",
    ]

    assert (
        "raw_fake_competitor"
        not in competitive[
            "canonical_source_ids"
        ]
    )


def test_final_report_preserves_one_canonical_source_catalog() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    source_index = report[
        "evidence"
    ][
        "source_index"
    ]

    assert set(
        source_index
    ) == {
        "source_a",
        "source_b",
    }

    assert (
        source_index[
            "source_a"
        ][
            "source_id"
        ]
        == "source_a"
    )

    claims = report[
        "evidence"
    ][
        "claims"
    ]

    # Claims reference sources by ID instead of embedding copies.
    assert claims[0][
        "source_ids"
    ] == [
        "source_a",
        "source_b",
    ]

    assert (
        "evidence_used"
        not in claims[0]
    )


def test_final_report_context_prefers_canonical_project_packet() -> None:
    analysis = _analysis()

    analysis[
        "structured_project_context"
    ] = {
        "project_name":
            "Older alternative context",
    }

    report = FinalReportBuilder().build(
        analysis
    )

    assert (
        report[
            "authority_contract"
        ][
            "context"
        ]
        == "project_context_packet"
    )

    assert (
        report[
            "context"
        ][
            "project_name"
        ]
        == "Universal Project"
    )


def test_final_report_builder_has_no_parallel_authority_calls() -> None:
    source = inspect.getsource(
        FinalReportBuilder
    )

    forbidden = (
        "fact_check_report",
        "forgecrawler",
        "local_competitors_count",
        "direct_competitors",
        "verified_competitors",
        "ready_for_agents",
        "source_relevance_gate",
        "source_role_resolver",
        "evidence_ledger.build",
        "canonical_source_ledger.build",
    )

    for token in forbidden:
        assert (
            token
            not in source
        ), token

    assert (
        '"evidence_ledger"'
        in source
    )

    assert (
        '"canonical_source_ledger"'
        in source
    )

    assert (
        '"debate_room"'
        in source
    )


def test_final_report_contract_declares_non_authoritative_projection() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    authority = report[
        "authority_contract"
    ]

    assert (
        authority[
            "recalculates_readiness"
        ]
        is False
    )

    assert (
        authority[
            "reclassifies_sources"
        ]
        is False
    )

    assert (
        authority[
            "reclassifies_evidence"
        ]
        is False
    )

    assert (
        authority[
            "recalculates_verdict"
        ]
        is False
    )


def test_final_report_executive_summary_partitions_canonical_claims() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    summary = report[
        "executive_summary"
    ]

    assert summary[
        "evidence_counts"
    ] == {
        "sourced": 1,
        "estimated": 1,
        "not_confirmed": 0,
        "unclassified": 0,
        "validation_required": 1,
    }

    assert [
        item[
            "claim_id"
        ]
        for item in summary[
            "supported_claims"
        ]
    ] == [
        "claim_problem",
    ]

    assert [
        item[
            "claim_id"
        ]
        for item in summary[
            "estimated_claims"
        ]
    ] == [
        "claim_finance",
    ]

    assert (
        summary[
            "supported_claims"
        ][0][
            "text"
        ]
        == "Canonical public problem claim"
    )

    assert (
        summary[
            "estimated_claims"
        ][0][
            "evidence_status"
        ]
        == "estimated"
    )


def test_final_report_executive_summary_never_promotes_unknown_status() -> None:
    analysis = _analysis()

    analysis[
        "evidence_ledger"
    ][
        "claims"
    ].append(
        {
            "claim_id":
                "legacy_verified_claim",
            "path":
                "market_study.legacy",
            "category":
                "market",
            "claim":
                "Legacy claim",
            "public_text":
                "Legacy claim",
            "evidence_status":
                "verified",
            "claim_kind":
                "evidence_claim",
            "validation_required":
                False,
            "source_ids": [
                "source_a",
            ],
        }
    )

    report = FinalReportBuilder().build(
        analysis
    )

    summary = report[
        "executive_summary"
    ]

    assert [
        item[
            "claim_id"
        ]
        for item in summary[
            "supported_claims"
        ]
    ] == [
        "claim_problem",
    ]

    assert [
        item[
            "claim_id"
        ]
        for item in summary[
            "unclassified_claims"
        ]
    ] == [
        "legacy_verified_claim",
    ]

    assert (
        summary[
            "unclassified_claims"
        ][0][
            "evidence_status"
        ]
        == ""
    )


def test_final_report_executive_validation_priorities_preserve_semantics() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    priorities = report[
        "executive_summary"
    ][
        "validation_priorities"
    ]

    assert [
        item[
            "claim_id"
        ]
        for item in priorities
    ] == [
        "claim_finance",
    ]

    priority = priorities[0]

    assert (
        priority[
            "evidence_status"
        ]
        == "estimated"
    )

    assert (
        priority[
            "claim_kind"
        ]
        == "estimate"
    )

    assert (
        priority[
            "validation_required"
        ]
        is True
    )

    assert priority[
        "source_ids"
    ] == []


def test_final_report_executive_decision_mirrors_debate_judge_only() -> None:
    analysis = _analysis()

    analysis[
        "verdict_code"
    ] = "go"

    analysis[
        "startup_score"
    ][
        "canonical_verdict_code"
    ] = "go"

    report = FinalReportBuilder().build(
        analysis
    )

    summary = report[
        "executive_summary"
    ]

    assert (
        summary[
            "decision_source"
        ]
        == "debate_room.judge"
    )

    assert (
        summary[
            "verdict_code"
        ]
        == "conditional_go"
    )

    assert (
        summary[
            "final_recommendation"
        ]
        == "Run the bounded pilot."
    )


def test_final_report_executive_synthesis_has_no_parallel_authority() -> None:
    source = inspect.getsource(
        FinalReportBuilder._executive_synthesis
    )

    for forbidden in (
        "fact_check_report",
        "forgecrawler",
        "competitive_analysis",
        "startup_score",
        "ready_for_agents",
        "canonical_source_ledger",
        "source_relevance_gate",
        "source_role_resolver",
        "evidence_ledger.build",
    ):
        assert (
            forbidden
            not in source
        ), forbidden

    for required in (
        '"supported_claims"',
        '"estimated_claims"',
        '"not_confirmed_claims"',
        '"unclassified_claims"',
        '"validation_priorities"',
    ):
        assert required in source


def test_final_report_competitive_projection_copies_canonical_counts() -> None:
    analysis = _analysis()

    ledger = analysis[
        "competitive_analysis"
    ][
        "canonical_source_ledger"
    ]

    ledger[
        "counts"
    ] = {
        "all": 4,
        "direct_competitors": 2,
        "local_direct_competitors": 1,
        "adjacent_solutions": 1,
        "technology_benchmarks": 0,
        "market_evidence": 1,
    }

    ledger[
        "direct_competitor_sources"
    ] = [
        {
            "source_id":
                "source_direct",
        },
        {
            "source_id":
                "source_direct_other_market",
        },
    ]

    ledger[
        "market_context_sources"
    ] = [
        {
            "source_id":
                "source_a",
        },
    ]

    ledger[
        "official_source_items"
    ] = [
        {
            "source_id":
                "source_b",
        },
    ]

    report = FinalReportBuilder().build(
        analysis
    )

    competitive = report[
        "competitive"
    ]

    assert competitive[
        "counts"
    ] == ledger[
        "counts"
    ]

    assert competitive[
        "direct_competitor_source_ids"
    ] == [
        "source_direct",
        "source_direct_other_market",
    ]

    assert competitive[
        "local_direct_competitor_source_ids"
    ] == [
        "source_direct",
    ]

    assert competitive[
        "market_context_source_ids"
    ] == [
        "source_a",
    ]

    assert competitive[
        "official_source_items_source_ids"
    ] == [
        "source_b",
    ]


def test_final_report_competitive_projection_does_not_recompute_missing_count() -> None:
    analysis = _analysis()

    ledger = analysis[
        "competitive_analysis"
    ][
        "canonical_source_ledger"
    ]

    ledger.pop(
        "canonical_sources_count",
        None,
    )

    assert len(
        ledger[
            "sources"
        ]
    ) == 4

    report = FinalReportBuilder().build(
        analysis
    )

    # The report is a projector, not the canonical counter.
    assert (
        report[
            "competitive"
        ][
            "canonical_sources_count"
        ]
        == 0
    )

    # Canonical identities remain available independently.
    assert len(
        report[
            "competitive"
        ][
            "canonical_source_ids"
        ]
    ) == 4


def test_final_report_decision_projects_professional_judge_contract() -> None:
    analysis = _analysis()

    judge = analysis[
        "debate_room"
    ][
        "judge"
    ]

    judge.update(
        {
            "format":
                "investment_committee_memo_v9",
            "status":
                "completed",
            "argument_strength_score":
                6.8,
            "confidence_score":
                0.61,
            "debate_synthesis":
                "Pilot justified, scaling not justified.",
            "improved_idea":
                "Run the narrow validated workflow first.",
            "action_plan": [
                "Week 1: observation",
                "Weeks 2-4: pilot",
            ],
            "critical_risks": [
                "Weak repeated use",
            ],
            "validated_findings": [
                "The workflow is testable.",
            ],
            "validated_opportunities": [
                "A bounded pilot is feasible.",
            ],
            "potential_opportunities": [
                "Hypothesis: repeated value exists.",
            ],
            "missing_evidence": [
                "Real payment evidence",
            ],
            "weak_assumptions": [
                "Hypothesis: payer accepts the offer.",
            ],
            "go_no_go_conditions": [
                "Observed decision threshold",
            ],
            "go_conditions": [
                "Repeated use observed",
            ],
            "no_go_conditions": [
                "No repeated use observed",
            ],
            "decision_by_round": [
                {
                    "round": 1,
                    "decision":
                        "CONDITIONAL_GO",
                },
            ],
            "committee_vote": {
                "CONDITIONAL_GO": 5,
                "INSUFFICIENT_EVIDENCE": 1,
            },
            "vetoes": [],
        }
    )

    # Conflicting non-Judge values must still be irrelevant.
    analysis[
        "verdict_code"
    ] = "go"

    analysis[
        "startup_score"
    ][
        "canonical_verdict_code"
    ] = "go"

    decision = (
        FinalReportBuilder()
        .build(
            analysis
        )[
            "decision"
        ]
    )

    assert (
        decision[
            "source"
        ]
        == "debate_room.judge"
    )

    assert (
        decision[
            "verdict_code"
        ]
        == "conditional_go"
    )

    assert decision[
        "go_conditions"
    ] == [
        "Repeated use observed",
    ]

    assert decision[
        "no_go_conditions"
    ] == [
        "No repeated use observed",
    ]

    assert decision[
        "critical_risks"
    ] == [
        "Weak repeated use",
    ]

    assert decision[
        "missing_evidence"
    ] == [
        "Real payment evidence",
    ]

    assert decision[
        "weak_assumptions"
    ] == [
        "Hypothesis: payer accepts the offer.",
    ]

    assert decision[
        "decision_by_round"
    ] == [
        {
            "round": 1,
            "decision":
                "CONDITIONAL_GO",
        },
    ]

    assert decision[
        "committee_vote"
    ] == {
        "CONDITIONAL_GO": 5,
        "INSUFFICIENT_EVIDENCE": 1,
    }


def test_final_report_never_invents_go_no_go_split() -> None:
    analysis = _analysis()

    judge = analysis[
        "debate_room"
    ][
        "judge"
    ]

    judge[
        "go_no_go_conditions"
    ] = [
        "Combined condition only",
    ]

    judge.pop(
        "go_conditions",
        None,
    )

    judge.pop(
        "no_go_conditions",
        None,
    )

    decision = (
        FinalReportBuilder()
        .build(
            analysis
        )[
            "decision"
        ]
    )

    assert decision[
        "go_no_go_conditions"
    ] == [
        "Combined condition only",
    ]

    assert decision[
        "go_conditions"
    ] == []

    assert decision[
        "no_go_conditions"
    ] == []


def test_final_report_meeting_preparation_preserves_distinct_semantics() -> None:
    analysis = _analysis()

    analysis[
        "debate_room"
    ][
        "meeting_preparation"
    ] = {
        "title":
            "Real meeting preparation",
        "project":
            "Universal Project",
        "top_questions": [
            "Who pays?",
        ],
        "recommended_answers": [
            "The payer remains under validation.",
        ],
        "proofs_to_prepare": [
            "Offer test",
        ],
        "answers_to_avoid": [
            "Everyone will pay.",
        ],
        "unresolved_questions": [
            "Local demand evidence.",
        ],
        "unresolved_points": [
            "Budget owner is unknown.",
        ],
        "follow_up_questions": [
            "Who controls the budget?",
        ],

        # Must not leak into the preparation projection.
        "evidence_used": [
            {
                "source_id":
                    "source_a",
            },
        ],
    }

    preparation = (
        FinalReportBuilder()
        .build(
            analysis
        )[
            "meeting_preparation"
        ]
    )

    assert preparation[
        "proofs_to_prepare"
    ] == [
        "Offer test",
    ]

    assert preparation[
        "unresolved_questions"
    ] == [
        "Local demand evidence.",
    ]

    assert preparation[
        "unresolved_points"
    ] == [
        "Budget owner is unknown.",
    ]

    assert preparation[
        "follow_up_questions"
    ] == [
        "Who controls the budget?",
    ]

    assert (
        "evidence_used"
        not in preparation
    )


def test_final_report_7d_projection_methods_have_no_parallel_authority() -> None:
    competitive_source = inspect.getsource(
        FinalReportBuilder
        ._canonical_competitive_projection
    )

    decision_source = inspect.getsource(
        FinalReportBuilder
        ._debate_decision
    )

    meeting_source = inspect.getsource(
        FinalReportBuilder
        ._meeting_preparation
    )

    for forbidden in (
        "forgecrawler",
        "local_competitors_count",
        "verified_competitors",
        "source_relevance_gate",
        "source_role_resolver",
        "canonical_source_ledger.build",
    ):
        assert (
            forbidden
            not in competitive_source
        ), forbidden

    for forbidden in (
        "startup_score",
        "fact_check_report",
        "evidence_ledger",
        "competitive_analysis",
        "ready_for_agents",
    ):
        assert (
            forbidden
            not in decision_source
        ), forbidden

    assert (
        "evidence_used"
        not in meeting_source
    )


def test_final_report_sourced_claim_resolves_supporting_evidence() -> None:
    report = FinalReportBuilder().build(
        _analysis()
    )

    claim = next(
        item
        for item in report[
            "evidence"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_problem"
    )

    assert claim[
        "evidence_status"
    ] == "sourced"

    assert [
        item[
            "source_id"
        ]
        for item in claim[
            "supporting_evidence"
        ]
    ] == [
        "source_a",
        "source_b",
    ]

    assert claim[
        "consulted_sources"
    ] == []

    assert (
        claim[
            "supporting_evidence"
        ][0][
            "title"
        ]
        == "Primary evidence"
    )


def test_final_report_not_confirmed_sources_are_consulted_not_supporting() -> None:
    analysis = _analysis()

    analysis[
        "evidence_ledger"
    ][
        "claims"
    ].append(
        {
            "claim_id":
                "claim_market_unconfirmed",
            "path":
                "market_study.market_size",
            "category":
                "market_size",
            "claim":
                "The market size is not confirmed.",
            "public_text":
                "The market size is not confirmed.",
            "confidence":
                "low",
            "evidence_status":
                "not_confirmed",
            "claim_kind":
                "evidence_claim",
            "validation_required":
                True,
            "source_ids": [
                "source_a",
            ],
        }
    )

    report = FinalReportBuilder().build(
        analysis
    )

    claim = next(
        item
        for item in report[
            "evidence"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_market_unconfirmed"
    )

    assert claim[
        "supporting_evidence"
    ] == []

    assert [
        item[
            "source_id"
        ]
        for item in claim[
            "consulted_sources"
        ]
    ] == [
        "source_a",
    ]


def test_final_report_estimated_claim_never_promotes_referenced_source() -> None:
    analysis = _analysis()

    finance = next(
        item
        for item in analysis[
            "evidence_ledger"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_finance"
    )

    finance[
        "source_ids"
    ] = [
        "source_b",
    ]

    report = FinalReportBuilder().build(
        analysis
    )

    claim = next(
        item
        for item in report[
            "evidence"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_finance"
    )

    assert claim[
        "evidence_status"
    ] == "estimated"

    assert claim[
        "supporting_evidence"
    ] == []

    assert [
        item[
            "source_id"
        ]
        for item in claim[
            "consulted_sources"
        ]
    ] == [
        "source_b",
    ]


def test_final_report_missing_source_index_entry_is_never_reconstructed() -> None:
    analysis = _analysis()

    claim = analysis[
        "evidence_ledger"
    ][
        "claims"
    ][0]

    claim[
        "source_ids"
    ] = [
        "source_a",
        "missing_source",
        "raw_fake_competitor",
    ]

    # These raw locations must never repair the missing canonical IDs.
    analysis[
        "competitive_analysis"
    ][
        "direct_competitors"
    ] = [
        {
            "source_id":
                "raw_fake_competitor",
            "title":
                "Raw competitor must not leak",
        },
    ]

    report = FinalReportBuilder().build(
        analysis
    )

    canonical = next(
        item
        for item in report[
            "evidence"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_problem"
    )

    assert canonical[
        "source_ids"
    ] == [
        "source_a",
        "missing_source",
        "raw_fake_competitor",
    ]

    assert [
        item[
            "source_id"
        ]
        for item in canonical[
            "supporting_evidence"
        ]
    ] == [
        "source_a",
    ]

    assert (
        "missing_source"
        not in {
            item[
                "source_id"
            ]
            for item in canonical[
                "supporting_evidence"
            ]
        }
    )

    assert (
        "raw_fake_competitor"
        not in {
            item[
                "source_id"
            ]
            for item in canonical[
                "supporting_evidence"
            ]
        }
    )


def test_final_report_executive_claim_preserves_exact_source_relationship() -> None:
    analysis = _analysis()

    analysis[
        "evidence_ledger"
    ][
        "claims"
    ].append(
        {
            "claim_id":
                "claim_unconfirmed_trace",
            "path":
                "market_study.local_demand",
            "category":
                "local_market",
            "claim":
                "Local demand remains unconfirmed.",
            "public_text":
                "Local demand remains unconfirmed.",
            "confidence":
                "low",
            "evidence_status":
                "not_confirmed",
            "claim_kind":
                "evidence_claim",
            "validation_required":
                True,
            "source_ids": [
                "source_a",
            ],
        }
    )

    report = FinalReportBuilder().build(
        analysis
    )

    summary_claim = next(
        item
        for item in report[
            "executive_summary"
        ][
            "not_confirmed_claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_unconfirmed_trace"
    )

    assert summary_claim[
        "supporting_evidence"
    ] == []

    assert [
        item[
            "source_id"
        ]
        for item in summary_claim[
            "consulted_sources"
        ]
    ] == [
        "source_a",
    ]

    assert (
        summary_claim[
            "validation_required"
        ]
        is True
    )


def test_final_report_claim_source_resolver_has_no_parallel_authority() -> None:
    source = inspect.getsource(
        FinalReportBuilder
        ._resolve_claim_sources
    )

    for forbidden in (
        "fact_check_report",
        "FactChecker",
        "forgecrawler",
        "competitive_analysis",
        "canonical_source_ledger",
        "source_relevance_gate",
        "source_role_resolver",
        "web_search",
    ):
        assert (
            forbidden
            not in source
        ), forbidden

    assert (
        "source_index.get"
        in source
    )

    assert (
        "evidence_status"
        in source
    )

    assert (
        '"sourced"'
        in source
    )

    assert (
        '"supporting_evidence"'
        in source
    )

    assert (
        '"consulted_sources"'
        in source
    )


def test_final_report_pipeline_builds_once_after_terminal_sanitization() -> None:
    import inspect

    from app.routers import projects


    source = inspect.getsource(
        projects.run_project_analysis_background
    )

    build_token = (
        "final_report_builder.build("
    )

    assert (
        source.count(
            build_token
        )
        == 1
    )

    build_position = source.index(
        build_token
    )

    # One pre-Debate gate + success gate + fallback gate
    # all occur textually before the common terminal projection.
    assert (
        source[
            :build_position
        ].count(
            "evidence_ledger.sanitize_public_claims("
        )
        == 3
    )

    assert (
        source.index(
            "DebateRoomGraph("
        )
        < build_position
    )

    assert (
        source.index(
            "stale final write ignored"
        )
        < build_position
    )

    assert (
        build_position
        < source.index(
            "project.analysis_data = final_analysis_data",
            build_position,
        )
    )


def test_final_report_pipeline_is_not_built_for_clarification_or_progress_callbacks() -> None:
    import ast
    import inspect

    from app.routers import projects


    source = inspect.getsource(
        projects.run_project_analysis_background
    )

    build_position = source.index(
        "final_report_builder.build("
    )

    clarification_position = source.index(
        "_analysis_requires_clarification(graph_result)"
    )

    assert (
        clarification_position
        < build_position
    )

    background_tree = ast.parse(
        inspect.getsource(
            projects.run_project_analysis_background
        )
    )

    for callback_name in (
        "save_startup_evaluator_step",
        "save_debate_room_step",
    ):
        callback = next(
            node
            for node in ast.walk(
                background_tree
            )
            if (
                isinstance(
                    node,
                    ast.AsyncFunctionDef,
                )
                and node.name
                == callback_name
            )
        )

        callback_source = ast.get_source_segment(
            inspect.getsource(
                projects.run_project_analysis_background
            ),
            callback,
        ) or ""

        assert (
            "final_report_builder"
            not in callback_source
        )


def test_public_sanitizer_preserves_final_report_authority_axes() -> None:
    from app.services.public_analysis_sanitizer import (
        sanitize_analysis_data_for_public,
    )


    analysis = _analysis()

    analysis[
        "final_report"
    ] = FinalReportBuilder().build(
        analysis
    )

    public = sanitize_analysis_data_for_public(
        analysis,
        project_context={
            "title":
                "Universal Project",
            "description":
                "A universal workflow project.",
            "industry":
                "Canonical Sector",
            "market_region":
                "Canonical Region",
            "output_language":
                "en",
        },
    )

    assert isinstance(
        public,
        dict,
    )

    assert (
        "final_report"
        in public
    )

    report = public[
        "final_report"
    ]

    assert (
        report[
            "authority_contract"
        ][
            "recalculates_readiness"
        ]
        is False
    )

    assert (
        report[
            "authority_contract"
        ][
            "reclassifies_sources"
        ]
        is False
    )

    assert (
        report[
            "authority_contract"
        ][
            "reclassifies_evidence"
        ]
        is False
    )

    assert (
        report[
            "authority_contract"
        ][
            "recalculates_verdict"
        ]
        is False
    )

    assert (
        report[
            "decision"
        ][
            "source"
        ]
        == "debate_room.judge"
    )

    assert (
        report[
            "decision"
        ][
            "verdict_code"
        ]
        == "conditional_go"
    )

    claim = next(
        item
        for item in report[
            "evidence"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_problem"
    )

    assert (
        claim[
            "evidence_status"
        ]
        == "sourced"
    )

    assert (
        claim[
            "claim_kind"
        ]
        == "evidence_claim"
    )

    assert (
        claim[
            "validation_required"
        ]
        is False
    )

    assert claim[
        "source_ids"
    ] == [
        "source_a",
        "source_b",
    ]

    assert [
        item[
            "source_id"
        ]
        for item in claim[
            "supporting_evidence"
        ]
    ] == [
        "source_a",
        "source_b",
    ]


def test_public_final_report_sources_are_sanitized_without_losing_traceability() -> None:
    from app.services.public_analysis_sanitizer import (
        sanitize_analysis_data_for_public,
    )


    analysis = _analysis()

    source = analysis[
        "evidence_ledger"
    ][
        "source_index"
    ][
        "source_a"
    ]

    source.update(
        {
            "url":
                "https://example.org/source-a",
            "raw_error":
                "must never be public",
            "search_query":
                "private runtime query",
            "private_runtime_payload":
                "internal-only",
        }
    )

    analysis[
        "final_report"
    ] = FinalReportBuilder().build(
        analysis
    )

    public = sanitize_analysis_data_for_public(
        analysis,
        project_context={
            "title":
                "Universal Project",
            "description":
                "A universal workflow project.",
            "industry":
                "Canonical Sector",
            "market_region":
                "Canonical Region",
            "output_language":
                "en",
        },
    )

    report = public[
        "final_report"
    ]

    canonical_source = report[
        "evidence"
    ][
        "source_index"
    ][
        "source_a"
    ]

    assert (
        canonical_source[
            "source_id"
        ]
        == "source_a"
    )

    assert (
        canonical_source[
            "title"
        ]
        == "Primary evidence"
    )

    assert (
        canonical_source[
            "url"
        ]
        == "https://example.org/source-a"
    )

    for forbidden in (
        "raw_error",
        "search_query",
        "private_runtime_payload",
    ):
        assert (
            forbidden
            not in canonical_source
        )

    claim = next(
        item
        for item in report[
            "evidence"
        ][
            "claims"
        ]
        if item[
            "claim_id"
        ]
        == "claim_problem"
    )

    support = claim[
        "supporting_evidence"
    ][0]

    assert (
        support[
            "source_id"
        ]
        == "source_a"
    )

    for forbidden in (
        "raw_error",
        "search_query",
        "private_runtime_payload",
    ):
        assert (
            forbidden
            not in support
        )

    assert (
        report[
            "decision"
        ][
            "source"
        ]
        == "debate_room.judge"
    )

    assert (
        claim[
            "evidence_status"
        ]
        == "sourced"
    )

    assert (
        claim[
            "claim_kind"
        ]
        == "evidence_claim"
    )
