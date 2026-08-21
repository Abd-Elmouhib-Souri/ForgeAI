from copy import deepcopy

import app.routers.projects as projects
import app.services.public_analysis_sanitizer as public_sanitizer
from app.services.canonical_source_ledger import (
    CanonicalSourceLedger,
)
from app.services.evidence_ledger import (
    EvidenceLedger,
)
from app.services.public_analysis_sanitizer import (
    sanitize_analysis_data_for_public,
)


def _context() -> dict:
    return {
        "title": "Generic Ops Platform",
        "description": (
            "A generic workflow platform for operational teams."
        ),
        "industry": "software",
        "region": "Europe",
        "market_region": "Europe",
        "output_language": "fr",
    }


def test_public_sanitizer_never_rebuilds_evidence_authority(
    monkeypatch,
) -> None:
    def forbidden(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Public projection must not rebuild EvidenceLedger"
        )

    monkeypatch.setattr(
        EvidenceLedger,
        "sanitize_public_claims",
        forbidden,
    )

    ledger = {
        "format": "evidence_ledger_v2_claim_aware",
        "schema_version": "evidence_ledger_v3_role_aware",
        "status_contract": "canonical_evidence_status_v1",
        "claims": [
            {
                "claim_id": "market_overview",
                "path": "market_study.market_overview",
                "category": "market_demand",
                "claim": (
                    "Hypoth?se ? valider : "
                    "adoption must be tested."
                ),
                "public_text": (
                    "Hypoth?se ? valider : "
                    "adoption must be tested."
                ),
                "source_ids": [],
                "status": "estimated",
                "evidence_status": "estimated",
                "claim_kind": "project_input",
                "validation_required": False,
            }
        ],
        "confidence_by_category": {
            "overall_evidence_confidence": "medium",
        },
    }

    analysis = {
        "output_language": "fr",
        "evidence_ledger": deepcopy(
            ledger
        ),
        "evidence_confidence": {
            "overall_evidence_confidence": "medium",
        },
        "overall_evidence_confidence": "medium",
        "search_coverage": "medium",
        "source_relevance_confidence": "medium",
        "verdict_code": "proceed_with_validation",
        "market_study": {
            "market_overview": (
                "Hypoth?se ? valider : "
                "adoption must be tested."
            ),
        },
    }

    result = (
        sanitize_analysis_data_for_public(
            analysis,
            project_context=_context(),
        )
    )

    assert (
        result["evidence_ledger"]
        == ledger
    )

    assert (
        result["overall_evidence_confidence"]
        == "medium"
    )

    assert (
        result["search_coverage"]
        == "medium"
    )

    assert (
        result["source_relevance_confidence"]
        == "medium"
    )

    assert (
        result["verdict_code"]
        == "proceed_with_validation"
    )


def test_public_sanitizer_is_idempotent_for_evidence_authority() -> None:
    ledger = {
        "format": "evidence_ledger_v2_claim_aware",
        "claims": [
            {
                "claim_id": "local_context",
                "path": "market_study.local_context",
                "category": "market_context",
                "claim": (
                    "Recommandation : "
                    "run interviews first."
                ),
                "public_text": (
                    "Recommandation : "
                    "run interviews first."
                ),
                "source_ids": [],
                "status": "estimated",
                "evidence_status": "estimated",
                "claim_kind": "recommendation",
                "validation_required": False,
            }
        ],
        "confidence_by_category": {
            "overall_evidence_confidence": "low",
        },
    }

    analysis = {
        "output_language": "fr",
        "evidence_ledger": deepcopy(
            ledger
        ),
        "overall_evidence_confidence": "low",
        "market_study": {
            "local_context": (
                "Recommandation : "
                "run interviews first."
            ),
        },
    }

    first = (
        sanitize_analysis_data_for_public(
            analysis,
            project_context=_context(),
        )
    )

    second = (
        sanitize_analysis_data_for_public(
            first,
            project_context=_context(),
        )
    )

    assert (
        first["evidence_ledger"]
        == ledger
    )

    assert (
        second["evidence_ledger"]
        == ledger
    )


def test_competitive_public_restore_never_rebuilds_source_authority(
    monkeypatch,
) -> None:
    def forbidden(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Public projection must not rebuild CanonicalSourceLedger"
        )

    monkeypatch.setattr(
        CanonicalSourceLedger,
        "build",
        forbidden,
    )

    source = {
        "title": "Generic Workflow Product",
        "url": "https://example.test/product",
        "confidence": "medium",
        "source_type": "competitor",
        "source_role": "local_direct_competitor",
        "canonical_category": "direct_competitor",
        "canonical_classification": "direct_competitor",
        "canonical_source_id": "src_canonical_1",
        "canonical_vendor_domain": "example.test",
        "vendor_key": "vendor:example.test",
        "vendor_name": "Example",
        "comparison_scope": "local_direct",
        "region_match": "local",
        "public_display": True,
        "evidence_categories": [
            "solution_benchmark",
            "competitor_product",
            "direct_competitor",
        ],
        "source_relevance_score": 0.91,
        "why_relevant": (
            "Comparable operational product."
        ),
    }

    internal = {
        "title": "Internal Debug Source",
        "url": "https://internal.test/debug",
        "internal_only": True,
        "source_role": "local_direct_competitor",
        "canonical_category": "direct_competitor",
        "canonical_source_id": "src_internal",
    }

    ledger = {
        "format": (
            "canonical_source_ledger_v3_"
            "canonical_categories"
        ),
        "sources": [
            source,
            internal,
        ],
        "sources_count": 2,
        "canonical_sources_count": 2,
        "roles": {
            "local_direct_competitor": [
                source,
                internal,
            ],
        },
        "categories": {
            "direct_competitor": [
                source,
                internal,
            ],
        },
        "local_direct_competitor_sources": [
            source,
            internal,
        ],
        "direct_competitor_sources": [
            source,
            internal,
        ],
        "adjacent_solution_sources": [],
        "regional_benchmark_sources": [],
        "international_benchmark_sources": [],
        "technology_provider_sources": [],
        "market_evidence_sources": [],
        "ecosystem_actor_sources": [],
        "evidence_sources": [],
        "benchmark_sources": [],
        "counts": {
            "all": 2,
            "direct_competitors": 2,
            "local_direct_competitors": 2,
        },
    }

    raw = {
        "competitive_analysis": {
            "status": "completed",
            "confidence_level": "medium",
            "source_based": True,
            "context_locked": True,
            "canonical_source_ledger": ledger,
            "sources": [
                source,
                internal,
            ],
        }
    }

    result = (
        projects.restore_public_competitive_analysis(
            raw_analysis_data=raw,
            sanitized_analysis_data={
                "competitive_analysis": {}
            },
        )
    )

    public = result[
        "competitive_analysis"
    ]

    public_ledger = public[
        "canonical_source_ledger"
    ]

    assert (
        public_ledger["sources_count"]
        == 1
    )

    assert (
        len(
            public_ledger["sources"]
        )
        == 1
    )

    item = public_ledger[
        "sources"
    ][0]

    assert (
        item["canonical_source_id"]
        == "src_canonical_1"
    )

    assert (
        item["canonical_category"]
        == "direct_competitor"
    )

    assert (
        item["source_role"]
        == "local_direct_competitor"
    )

    assert (
        item["confidence"]
        == "medium"
    )

    assert (
        item["canonical_vendor_domain"]
        == "example.test"
    )

    assert (
        item["vendor_key"]
        == "vendor:example.test"
    )

    assert (
        public_ledger[
            "categories"
        ][
            "direct_competitor"
        ][0][
            "canonical_source_id"
        ]
        == "src_canonical_1"
    )

    assert (
        public_ledger[
            "roles"
        ][
            "local_direct_competitor"
        ][0][
            "canonical_source_id"
        ]
        == "src_canonical_1"
    )

    assert all(
        item.get(
            "canonical_source_id"
        )
        != "src_internal"
        for item in public_ledger[
            "sources"
        ]
    )


def test_legacy_public_restore_does_not_invent_canonical_ledger() -> None:
    raw = {
        "competitive_analysis": {
            "sources": [
                {
                    "title": "Legacy public source",
                    "url": "https://example.test/legacy",
                    "source_type": "market_article",
                    "public_display": True,
                }
            ]
        }
    }

    result = (
        projects.restore_public_competitive_analysis(
            raw_analysis_data=raw,
            sanitized_analysis_data={
                "competitive_analysis": {}
            },
        )
    )

    competitive = result[
        "competitive_analysis"
    ]

    assert (
        len(
            competitive["sources"]
        )
        == 1
    )

    assert (
        "canonical_source_ledger"
        not in competitive
    )


def test_public_projection_preserves_startup_score_across_domain_guard(
    monkeypatch,
) -> None:
    startup_score = {
        "format": "startup_score_v5_context_locked_deterministic",
        "status": "completed",
        "potential_score": 7.0,
        "score": 7.0,
        "startup_score": 7.0,
        "overall_score": 7.0,
        "final_score": 7.0,
        "score_out_of_10": 7.0,
        "verdict": (
            "Continue conditionally after validation."
        ),
        "verdict_code": "CONDITIONAL_GO",
        "canonical_verdict_code": "conditional_go",
        "go_no_go": (
            "CONDITIONAL GO: validate evidence first."
        ),
        "next_actions": [
            "Define the first pilot.",
            "Recruit target users.",
            "Measure repeated usage.",
            "Test willingness to pay.",
            "Review the decision thresholds.",
        ],
        "recommendations": [
            "Keep the first MVP narrow.",
            "Validate adoption before scaling.",
        ],
    }

    analysis = {
        "output_language": "en",
        "startup_score": deepcopy(
            startup_score
        ),
    }

    def invalid_object(
        *,
        data,
        project_context,
    ):
        return {
            "is_valid": False,
        }

    def guard_sanitizer(
        *,
        data,
        project_context,
    ):
        # The generic guard must never receive canonical StartupScore.
        assert "startup_score" not in data

        mutated = deepcopy(data)
        mutated["unrelated_public_field"] = "safe"
        return mutated

    monkeypatch.setattr(
        public_sanitizer.domain_integrity_guard,
        "validate_object",
        invalid_object,
    )

    monkeypatch.setattr(
        public_sanitizer.domain_integrity_guard,
        "sanitize_object",
        guard_sanitizer,
    )

    result = (
        sanitize_analysis_data_for_public(
            analysis,
            project_context={
                "title": "Generic Workflow Platform",
                "description": (
                    "A generic platform for operational workflows."
                ),
                "industry": "software",
                "region": "Europe",
                "market_region": "Europe",
                "output_language": "en",
            },
        )
    )

    assert (
        result["startup_score"]
        == startup_score
    )

    assert (
        result["startup_score"]["verdict"]
        == startup_score["verdict"]
    )

    assert (
        result["startup_score"]["go_no_go"]
        == startup_score["go_no_go"]
    )

    assert (
        result["startup_score"]["next_actions"]
        == startup_score["next_actions"]
    )

    assert (
        result["startup_score"]["recommendations"]
        == startup_score["recommendations"]
    )

    assert (
        result["startup_score"]["potential_score"]
        == 7.0
    )


def test_public_projection_preserves_debate_question_authority_mode():
    analysis = {
        "output_language": "en",
        "debate_room": {
            "rounds": [
                {
                    "round": 1,
                    "committee_questions": [
                        {
                            "question": "Q1",
                            "answer": {
                                "authority_mode":
                                    "sources",
                                "evidence_status":
                                    "not_confirmed",
                                "source_ids": [
                                    "src_alpha",
                                ],
                                "canonical_claim_id":
                                    "",
                                "canonical_claim_found":
                                    False,
                            },
                        },
                        {
                            "question": "Q2",
                            "answer": {
                                "authority_mode":
                                    "context",
                                "evidence_status":
                                    "not_confirmed",
                                "source_ids":
                                    [],
                                "canonical_claim_id":
                                    "",
                                "canonical_claim_found":
                                    False,
                            },
                        },
                    ],
                    "cross_examination": [
                        {
                            "question": "Q3",
                            "answer": {
                                "authority_mode":
                                    "claim",
                                "evidence_status":
                                    "sourced",
                                "source_ids": [
                                    "src_beta",
                                ],
                                "canonical_claim_id":
                                    "local_feasibility",
                                "canonical_claim_found":
                                    True,
                            },
                        },
                        {
                            "question": "Q4",
                            "answer": {
                                "authority_mode":
                                    "synthesis",
                                "evidence_status":
                                    "not_confirmed",
                                "source_ids":
                                    [],
                                "canonical_claim_id":
                                    "",
                                "canonical_claim_found":
                                    False,
                            },
                        },
                    ],
                },
            ],
        },
    }

    public = sanitize_analysis_data_for_public(
        analysis,
        project_context={
            "title": "Authority QA",
            "description":
                "Synthetic authority transport QA",
            "industry": "generic",
            "market_region": "test",
            "output_language": "en",
        },
    )

    round_data = public[
        "debate_room"
    ][
        "rounds"
    ][0]

    answers = [
        round_data[
            "committee_questions"
        ][0]["answer"],

        round_data[
            "committee_questions"
        ][1]["answer"],

        round_data[
            "cross_examination"
        ][0]["answer"],

        round_data[
            "cross_examination"
        ][1]["answer"],
    ]

    assert [
        answer["authority_mode"]
        for answer in answers
    ] == [
        "sources",
        "context",
        "claim",
        "synthesis",
    ]

    assert (
        answers[0]["evidence_status"]
        == "not_confirmed"
    )

    assert (
        answers[0]["source_ids"]
        == ["src_alpha"]
    )

    assert (
        answers[0]["canonical_claim_id"]
        == ""
    )

    assert (
        answers[2]["canonical_claim_id"]
        == "local_feasibility"
    )

    assert (
        answers[2]["evidence_status"]
        == "sourced"
    )
