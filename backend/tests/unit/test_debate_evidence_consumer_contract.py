from app.agents.debate_room_graph import (
    DebateRoomGraph,
)


def _analysis_with_claim(
    *,
    evidence_status=None,
    status=None,
    public_status=None,
):
    claim = {
        "category": "problem_context",
        "claim": (
            "The problem requires validation."
        ),
    }

    if evidence_status is not None:
        claim["evidence_status"] = (
            evidence_status
        )

    if status is not None:
        claim["status"] = status

    if public_status is not None:
        claim["public_status"] = (
            public_status
        )

    return {
        "fact_check_report": {
            "claims": [
                claim
            ],
        },
    }


def test_debate_projects_sourced_claim_to_supported() -> None:
    graph = DebateRoomGraph()

    result = graph._claim_status(
        _analysis_with_claim(
            evidence_status="sourced",
        ),
        "problem",
    )

    assert result == "supported"


def test_debate_preserves_estimated_projection() -> None:
    graph = DebateRoomGraph()

    result = graph._claim_status(
        _analysis_with_claim(
            evidence_status="estimated",
        ),
        "problem",
    )

    assert result == "estimated"


def test_debate_preserves_not_confirmed_projection() -> None:
    graph = DebateRoomGraph()

    result = graph._claim_status(
        _analysis_with_claim(
            evidence_status="not_confirmed",
        ),
        "problem",
    )

    assert result == "not_confirmed"


def test_debate_evidence_status_overrides_legacy_and_public_labels() -> None:
    graph = DebateRoomGraph()

    result = graph._claim_status(
        _analysis_with_claim(
            evidence_status="not_confirmed",
            status="sourced",
            public_status="Sourced",
        ),
        "problem",
    )

    assert result == "not_confirmed"


def test_debate_does_not_use_public_status_as_evidence_authority() -> None:
    graph = DebateRoomGraph()

    result = graph._claim_status(
        _analysis_with_claim(
            public_status="Verified",
        ),
        "problem",
    )

    assert result == "not_confirmed"


def test_debate_accepts_only_canonical_legacy_status() -> None:
    graph = DebateRoomGraph()

    assert (
        graph._claim_status(
            _analysis_with_claim(
                status="sourced",
            ),
            "problem",
        )
        == "supported"
    )

    assert (
        graph._claim_status(
            _analysis_with_claim(
                status="verified",
            ),
            "problem",
        )
        == "not_confirmed"
    )


def test_debate_claim_status_has_no_textual_status_heuristics() -> None:
    import inspect

    source = inspect.getsource(
        DebateRoomGraph._claim_status
    )

    assert "public_status" not in source
    assert '"verified"' not in source
    assert '"confirm"' not in source
    assert "evidence_status" in source


def _canonical_projection_analysis():
    return {
        "evidence_ledger": {
            "claims": [
                {
                    "claim_id": "claim_problem_1",
                    "path": "market_study.problem",
                    "category": "problem_context",
                    "claim": (
                        "The workflow problem exists."
                    ),
                    "evidence_status": "sourced",
                    "claim_kind": "evidence_claim",
                    "validation_required": False,
                    "source_ids": [
                        "source_alpha",
                        "source_beta",
                    ],
                },
            ],
            "source_index": {
                "source_alpha": {
                    "title": "Primary source",
                },
                "source_beta": {
                    "title": "Secondary source",
                },
            },
        },
        "fact_check_report": {
            "claims": [
                {
                    "claim_id": "conflicting_fact_checker_claim",
                    "category": "problem_context",
                    "claim": (
                        "Presentation copy must not override ledger."
                    ),
                    "evidence_status": "not_confirmed",
                    "claim_kind": "hypothesis",
                    "validation_required": True,
                    "source_ids": [],
                },
            ],
        },
    }


def test_debate_canonical_projection_preserves_all_evidence_dimensions() -> None:
    graph = DebateRoomGraph()

    projection = graph._claim_evidence_projection(
        _canonical_projection_analysis(),
        "problem",
    )

    assert projection["canonical_claim_found"] is True
    assert projection["canonical_claim_id"] == "claim_problem_1"
    assert projection["evidence_status"] == "sourced"
    assert projection["claim_kind"] == "evidence_claim"
    assert projection["validation_required"] is False
    assert projection["source_ids"] == [
        "source_alpha",
        "source_beta",
    ]
    assert projection["support_status"] == "supported"

    # EvidenceLedger must outrank FactChecker presentation.
    assert (
        graph._claim_status(
            _canonical_projection_analysis(),
            "problem",
        )
        == "supported"
    )


def test_debate_missing_canonical_claim_is_never_upgraded() -> None:
    graph = DebateRoomGraph()

    projection = graph._claim_evidence_projection(
        {
            "evidence_ledger": {
                "claims": [],
            },
            "fact_check_report": {
                "claims": [
                    {
                        "category": "finance",
                        "evidence_status": "sourced",
                    },
                ],
            },
        },
        "finance",
    )

    assert projection["canonical_claim_found"] is False
    assert projection["evidence_status"] == "not_confirmed"
    assert projection["claim_kind"] == ""
    assert projection["validation_required"] is None
    assert projection["source_ids"] == []


def test_debate_question_separates_support_from_canonical_evidence() -> None:
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=1,
        language="en",
        analysis=_canonical_projection_analysis(),
        evidence_category="problem",
        specifications=[
            {
                "asked_by": "committee_chair",
                "addressed_to": "project_defender",
                "support_status": "committee_synthesis",
                "question": "What can we claim?",
                "answer": "Only the supported claim.",
                "reasoning": "Use canonical evidence.",
                "confidence": 0.75,
                "unresolved": (
                    "Validate the remaining assumptions."
                ),
                "follow_up": "What remains unknown?",
                "likely": "What is actually proven?",
                "recommended": (
                    "Present only the sourced claim."
                ),
                "proofs": [
                    "Canonical claim ledger",
                ],
                "avoid": "Everything is validated.",
            },
        ],
    )

    answer = questions[0]["answer"]

    assert answer["support_status"] == "committee_synthesis"
    assert answer["evidence_status"] == "sourced"
    assert answer["claim_kind"] == "evidence_claim"
    assert answer["validation_required"] is False
    assert answer["source_ids"] == [
        "source_alpha",
        "source_beta",
    ]
    assert answer["evidence_ids"] == answer["source_ids"]
    assert answer["canonical_claim_id"] == "claim_problem_1"


def test_debate_adaptive_rounds_have_no_local_evidence_status_key() -> None:
    import inspect

    graph_source = inspect.getsource(
        DebateRoomGraph._adaptive_questions
    )

    assert 'spec.get("status"' not in graph_source
    assert "support_status" in graph_source

    methods = (
        DebateRoomGraph._round_adaptive_problem,
        DebateRoomGraph._round_adaptive_market,
        DebateRoomGraph._round_adaptive_product,
        DebateRoomGraph._round_adaptive_economics,
        DebateRoomGraph._round_adaptive_decision,
    )

    for method in methods:
        source = inspect.getsource(
            method
        )

        assert '"status":' not in source


def test_debate_evidence_packet_prefers_canonical_ledger() -> None:
    graph = DebateRoomGraph()

    packet = graph._evidence_packet(
        _canonical_projection_analysis()
    )

    assert packet["claims_source"] == "evidence_ledger"
    assert packet["claims"][0]["claim_id"] == "claim_problem_1"
    assert "source_alpha" in packet["source_index"]
    assert "source_beta" in packet["source_index"]


def test_debate_resolves_only_sources_from_canonical_source_index() -> None:
    graph = DebateRoomGraph()

    analysis = _canonical_projection_analysis()

    analysis["competitive_analysis"] = {
        "sources": [
            {
                "source_id": "source_missing",
                "title": "Must never leak",
            },
        ],
    }

    source_ids = [
        "source_beta",
        "source_missing",
        "source_alpha",
        "source_beta",
    ]

    result = graph._resolve_evidence_used(
        analysis,
        source_ids,
    )

    assert [
        item["source_id"]
        for item in result
    ] == [
        "source_beta",
        "source_alpha",
    ]

    assert all(
        item["title"]
        != "Must never leak"
        for item in result
    )


def test_debate_question_exposes_exact_canonical_evidence_used() -> None:
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=1,
        language="en",
        analysis=_canonical_projection_analysis(),
        evidence_category="problem",
        specifications=[
            {
                "asked_by": "evidence_auditor",
                "addressed_to": "project_defender",
                "support_status": "supported",
                "question": "What proves the problem?",
                "answer": "The retained evidence.",
                "reasoning": "Use the canonical claim.",
                "confidence": 0.80,
                "unresolved": "Validate remaining assumptions.",
                "follow_up": "Which source is strongest?",
                "likely": "What evidence do you have?",
                "recommended": "Show the retained sources.",
                "proofs": [
                    "Evidence ledger",
                ],
                "avoid": "Everything is proven.",
            },
        ],
    )

    question = questions[0]
    answer = question["answer"]

    assert (
        question["answered_by"]
        == "project_defender"
    )

    assert answer["source_ids"] == [
        "source_alpha",
        "source_beta",
    ]

    assert [
        item["source_id"]
        for item in answer["evidence_used"]
    ] == [
        "source_alpha",
        "source_beta",
    ]

    assert [
        item["title"]
        for item in answer["evidence_used"]
    ] == [
        "Primary source",
        "Secondary source",
    ]


def test_debate_answer_owner_defaults_to_question_recipient() -> None:
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=5,
        language="en",
        analysis={},
        evidence_category="",
        specifications=[
            {
                "asked_by": "committee_chair",
                "addressed_to": "all_committee_members",
                "support_status": "committee_synthesis",
                "question": "What is the committee decision?",
                "answer": "Proceed conditionally.",
                "reasoning": "Collective review.",
                "confidence": 0.75,
                "unresolved": "Define the pilot conditions.",
                "follow_up": "What blocks the next decision?",
                "likely": "What is the decision today?",
                "recommended": "Present the bounded decision.",
                "proofs": [
                    "Decision scorecard",
                ],
                "avoid": "Full rollout is approved.",
            },
        ],
    )

    question = questions[0]

    assert (
        question["addressed_to"]
        == "all_committee_members"
    )

    assert (
        question["answered_by"]
        == "all_committee_members"
    )


def test_debate_explicit_answer_owner_can_differ_from_recipient() -> None:
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=5,
        language="en",
        analysis={},
        evidence_category="",
        specifications=[
            {
                "asked_by": "committee_chair",
                "addressed_to": "all_committee_members",
                "answered_by": "committee_chair",
                "support_status": "committee_synthesis",
                "question": "What is the synthesized decision?",
                "answer": "Conditional go.",
                "reasoning": "Chair synthesis.",
                "confidence": 0.75,
                "unresolved": "Confirm pilot ownership.",
                "follow_up": "Who owns the next review?",
                "likely": "What did the committee decide?",
                "recommended": "State the conditional decision.",
                "proofs": [
                    "Committee scorecard",
                ],
                "avoid": "Everything is approved.",
            },
        ],
    )

    question = questions[0]

    assert (
        question["addressed_to"]
        == "all_committee_members"
    )

    assert (
        question["answered_by"]
        == "committee_chair"
    )


def test_debate_state_contract_contains_traceability_fields() -> None:
    from app.agents.debate_room_state import (
        DebateAnswer,
        DebateQuestion,
    )

    answer_fields = set(
        DebateAnswer.__annotations__
    )

    question_fields = set(
        DebateQuestion.__annotations__
    )

    assert {
        "support_status",
        "evidence_status",
        "claim_kind",
        "validation_required",
        "source_ids",
        "evidence_ids",
        "evidence_used",
        "canonical_claim_id",
        "canonical_claim_found",
        "unresolved_point",
    }.issubset(
        answer_fields
    )

    assert {
        "asked_by",
        "addressed_to",
        "answered_by",
    }.issubset(
        question_fields
    )


def test_debate_market_counts_use_canonical_source_authority() -> None:
    graph = DebateRoomGraph()

    analysis = {
        "competitive_analysis": {
            # Raw/legacy value must not be authoritative.
            "local_competitors_count": 99,
            "sources": [
                {
                    "source_id": "raw_competitive_source",
                },
            ],
            "canonical_source_ledger": {
                "canonical_sources_count": 3,
                "sources": [
                    {
                        "source_id": "canonical_1",
                    },
                    {
                        "source_id": "canonical_2",
                    },
                    {
                        "source_id": "canonical_3",
                    },
                ],
                "local_direct_competitor_sources": [
                    {
                        "source_id": "canonical_direct_1",
                    },
                    {
                        "source_id": "canonical_direct_2",
                    },
                ],
            },
        },
        "forgecrawler": {
            "sources": [
                {
                    "source_id": "raw_forgecrawler_source",
                },
            ],
        },
        "evidence_ledger": {
            "claims": [],
            "source_index": {
                "evidence_1": {
                    "source_id": "evidence_1",
                },
            },
        },
    }

    summary = graph._canonical_source_summary(
        analysis
    )

    assert (
        summary[
            "canonical_source_ledger_present"
        ]
        is True
    )

    assert (
        summary[
            "source_count"
        ]
        == 3
    )

    assert (
        summary[
            "local_direct_competitor_count"
        ]
        == 2
    )

    packet = graph._evidence_packet(
        analysis
    )

    assert packet[
        "source_count"
    ] == 3

    assert packet[
        "local_direct_competitor_count"
    ] == 2

    assert "sources" not in packet


def test_debate_source_summary_fallback_never_reclassifies_raw_sources() -> None:
    graph = DebateRoomGraph()

    analysis = {
        "competitive_analysis": {
            "local_competitors_count": 17,
            "sources": [
                {
                    "source_id": "raw_competitor",
                },
            ],
        },
        "forgecrawler": {
            "sources": [
                {
                    "source_id": "raw_search",
                },
            ],
        },
        "evidence_ledger": {
            "claims": [],
            "source_index": {
                "source_a": {
                    "source_id": "source_a",
                },
                "source_b": {
                    "source_id": "source_b",
                },
            },
        },
    }

    summary = graph._canonical_source_summary(
        analysis
    )

    # EvidenceLedger can provide a conservative source count.
    assert (
        summary[
            "source_count"
        ]
        == 2
    )

    # It cannot provide competitor identity.
    assert (
        summary[
            "local_direct_competitor_count"
        ]
        == 0
    )

    assert (
        summary[
            "canonical_source_ledger_present"
        ]
        is False
    )

    source = __import__(
        "inspect"
    ).getsource(
        DebateRoomGraph._canonical_source_summary
    )

    assert "forgecrawler" not in source
    assert "local_competitors_count" not in source
