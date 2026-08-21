from app.agents.debate_room_graph import (
    DebateRoomGraph,
)


def _spec(**extra):
    spec = {
        "asked_by": "evidence_auditor",
        "addressed_to": "project_defender",
        "question": "What is the evidence authority?",
        "answer": "Use only the declared authority.",
        "reasoning": "Authority must be explicit.",
        "confidence": 0.8,
        "support_status": "supported",
        "unresolved": "Validate remaining unknowns.",
        "follow_up": "What remains unproven?",
        "likely": "Which evidence is authoritative?",
        "recommended": "Show only canonical evidence.",
        "proofs": [
            "Canonical authority",
        ],
        "avoid": "Infer evidence from the topic.",
    }
    spec.update(extra)
    return spec


def _analysis():
    return {
        "evidence_ledger": {
            "claims": [
                {
                    "claim_id": "market_size",
                    "path": "market_study.market_size",
                    "category": "market_size",
                    "claim": "Market size is not confirmed.",
                    "evidence_status": "not_confirmed",
                    "claim_kind": "evidence_claim",
                    "validation_required": True,
                    "source_ids": [],
                },
                {
                    "claim_id": "local_feasibility",
                    "path": "market_study.local_feasibility",
                    "category": "market_context",
                    "claim": "Local feasibility has evidence.",
                    "evidence_status": "sourced",
                    "claim_kind": "audit_conclusion",
                    "validation_required": False,
                    "source_ids": [
                        "evidence_local_1",
                        "evidence_local_2",
                    ],
                },
            ],
            "source_index": {
                "evidence_local_1": {
                    "source_id": "evidence_local_1",
                    "title": "Local evidence one",
                },
                "evidence_local_2": {
                    "source_id": "evidence_local_2",
                    "title": "Local evidence two",
                },
            },
        },
        "competitive_analysis": {
            "canonical_source_ledger": {
                "format": (
                    "canonical_source_ledger_v3_"
                    "canonical_categories"
                ),
                "canonical_sources_count": 3,
                "sources": [
                    {
                        "canonical_source_id":
                            "canonical_direct_1",
                        "title": "Direct competitor one",
                        "source_role":
                            "direct_competitor",
                    },
                    {
                        "canonical_source_id":
                            "canonical_direct_2",
                        "title": "Direct competitor two",
                        "source_role":
                            "direct_competitor",
                    },
                    {
                        # Legacy identity remains consumable.
                        "source_id":
                            "legacy_adjacent_1",
                        "title": "Adjacent solution",
                        "source_role":
                            "adjacent_solution",
                    },
                ],
                "local_direct_competitor_sources": [
                    {
                        "canonical_source_id":
                            "canonical_direct_1",
                        "title": "Direct competitor one",
                        "source_role":
                            "direct_competitor",
                    },
                    {
                        "canonical_source_id":
                            "canonical_direct_2",
                        "title": "Direct competitor two",
                        "source_role":
                            "direct_competitor",
                    },
                ],
                "adjacent_solution_sources": [
                    {
                        "source_id":
                            "legacy_adjacent_1",
                        "title": "Adjacent solution",
                        "source_role":
                            "adjacent_solution",
                    },
                ],
            },
        },
    }


def test_explicit_claim_authority_outranks_broad_round_category():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=2,
        language="en",
        analysis=_analysis(),
        evidence_category="market",
        specifications=[
            _spec(
                authority_mode="claim",
                canonical_claim_id="local_feasibility",
            ),
        ],
    )

    answer = questions[0]["answer"]

    # Must NOT inherit the first broad "market" claim.
    assert answer["canonical_claim_id"] == "local_feasibility"
    assert answer["canonical_claim_found"] is True

    assert answer["evidence_status"] == "sourced"
    assert answer["claim_kind"] == "audit_conclusion"
    assert answer["validation_required"] is False

    assert answer["source_ids"] == [
        "evidence_local_1",
        "evidence_local_2",
    ]

    assert [
        item["source_id"]
        for item in answer["evidence_used"]
    ] == [
        "evidence_local_1",
        "evidence_local_2",
    ]


def test_missing_explicit_claim_never_falls_back_to_broad_category():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=2,
        language="en",
        analysis=_analysis(),
        evidence_category="market",
        specifications=[
            _spec(
                authority_mode="claim",
                canonical_claim_id="claim_does_not_exist",
            ),
        ],
    )

    answer = questions[0]["answer"]

    assert answer["canonical_claim_found"] is False
    assert answer["canonical_claim_id"] == ""
    assert answer["evidence_status"] == "not_confirmed"
    assert answer["claim_kind"] == ""
    assert answer["validation_required"] is None
    assert answer["source_ids"] == []
    assert answer["evidence_used"] == []


def test_explicit_source_scope_consumes_exact_canonical_bucket():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=2,
        language="en",
        analysis=_analysis(),
        evidence_category="market",
        specifications=[
            _spec(
                authority_mode="sources",
                canonical_source_scope=(
                    "local_direct_competitor_sources"
                ),
            ),
        ],
    )

    answer = questions[0]["answer"]

    # Source authority is not a fake EvidenceLedger claim.
    assert answer["canonical_claim_found"] is False
    assert answer["canonical_claim_id"] == ""

    assert answer["source_ids"] == [
        "canonical_direct_1",
        "canonical_direct_2",
    ]

    assert [
        item["source_id"]
        for item in answer["evidence_used"]
    ] == [
        "canonical_direct_1",
        "canonical_direct_2",
    ]

    assert [
        item["title"]
        for item in answer["evidence_used"]
    ] == [
        "Direct competitor one",
        "Direct competitor two",
    ]


def test_source_scope_accepts_legacy_source_id_without_reclassification():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=2,
        language="en",
        analysis=_analysis(),
        evidence_category="market",
        specifications=[
            _spec(
                authority_mode="sources",
                canonical_source_scope=(
                    "adjacent_solution_sources"
                ),
            ),
        ],
    )

    answer = questions[0]["answer"]

    assert answer["canonical_claim_found"] is False
    assert answer["canonical_claim_id"] == ""

    assert answer["source_ids"] == [
        "legacy_adjacent_1",
    ]

    assert [
        item["source_id"]
        for item in answer["evidence_used"]
    ] == [
        "legacy_adjacent_1",
    ]


def test_invalid_explicit_source_scope_never_falls_back_to_market_claim():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=2,
        language="en",
        analysis=_analysis(),
        evidence_category="market",
        specifications=[
            _spec(
                authority_mode="sources",
                canonical_source_scope=(
                    "bucket_that_does_not_exist"
                ),
            ),
        ],
    )

    answer = questions[0]["answer"]

    assert answer["canonical_claim_found"] is False
    assert answer["canonical_claim_id"] == ""
    assert answer["source_ids"] == []
    assert answer["evidence_used"] == []


def test_explicit_synthesis_authority_never_inherits_broad_claim():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=5,
        language="en",
        analysis=_analysis(),
        # Deliberately non-empty to prove synthesis blocks fallback.
        evidence_category="market",
        specifications=[
            _spec(
                authority_mode="synthesis",
                support_status="committee_synthesis",
            ),
        ],
    )

    answer = questions[0]["answer"]

    assert answer["support_status"] == "committee_synthesis"

    assert answer["canonical_claim_found"] is False
    assert answer["canonical_claim_id"] == ""
    assert answer["evidence_status"] == "not_confirmed"
    assert answer["claim_kind"] == ""
    assert answer["validation_required"] is None
    assert answer["source_ids"] == []
    assert answer["evidence_used"] == []


# ---------------------------------------------------------------------------
# Production adaptive-round authority contract.
#
# Every production question must explicitly declare the authority it consumes.
# The broad round evidence_category remains compatibility-only and must not be
# the implicit truth selector for current production specs.
# ---------------------------------------------------------------------------

import ast
import inspect
import textwrap


def _production_authority_specs(method):
    source = textwrap.dedent(
        inspect.getsource(method)
    )

    tree = ast.parse(source)

    specs_node = None

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        for target in node.targets:
            if (
                isinstance(
                    target,
                    ast.Name,
                )
                and target.id == "specs"
            ):
                specs_node = node.value
                break

        if specs_node is not None:
            break

    assert isinstance(
        specs_node,
        ast.List,
    )

    result = []

    for item in specs_node.elts:
        assert isinstance(
            item,
            ast.Dict,
        )

        authority = {}

        for key_node, value_node in zip(
            item.keys,
            item.values,
        ):
            if not isinstance(
                key_node,
                ast.Constant,
            ):
                continue

            key = key_node.value

            if key not in {
                "authority_mode",
                "canonical_claim_id",
                "canonical_source_scope",
            }:
                continue

            if isinstance(
                value_node,
                ast.Constant,
            ):
                authority[key] = (
                    value_node.value
                )

        result.append(
            authority
        )

    return result


def test_production_adaptive_questions_declare_explicit_authority():
    methods = (
        DebateRoomGraph._round_adaptive_problem,
        DebateRoomGraph._round_adaptive_market,
        DebateRoomGraph._round_adaptive_product,
        DebateRoomGraph._round_adaptive_economics,
        DebateRoomGraph._round_adaptive_decision,
    )

    for method in methods:
        specs = (
            _production_authority_specs(
                method
            )
        )

        assert len(specs) == 4

        assert all(
            str(
                spec.get(
                    "authority_mode"
                )
                or ""
            ).strip()
            for spec in specs
        )


def test_market_round_uses_exact_source_and_claim_authorities():
    specs = _production_authority_specs(
        DebateRoomGraph._round_adaptive_market
    )

    # Verified direct competitors consume the canonical
    # competitor bucket, never a broad market claim.
    assert specs[0] == {
        "authority_mode": "sources",
        "canonical_source_scope":
            "local_direct_competitor_sources",
    }

    # Current alternatives are primarily behavioural/contextual.
    assert specs[1] == {
        "authority_mode": "context",
    }

    # The local-demand/context distinction already has an
    # explicit EvidenceLedger audit conclusion.
    assert specs[2] == {
        "authority_mode": "claim",
        "canonical_claim_id":
            "local_feasibility",
    }

    # Market-gap interpretation is committee analysis, not a
    # fabricated evidence attachment.
    assert specs[3] == {
        "authority_mode": "synthesis",
    }


def test_problem_round_does_not_reuse_one_problem_claim_for_every_question():
    specs = _production_authority_specs(
        DebateRoomGraph._round_adaptive_problem
    )

    assert specs == [
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "synthesis",
        },
    ]


def test_product_round_uses_context_not_arbitrary_solution_hypothesis():
    specs = _production_authority_specs(
        DebateRoomGraph._round_adaptive_product
    )

    assert specs == [
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "synthesis",
        },
    ]


def test_economics_round_does_not_reuse_budget_claim_for_every_question():
    specs = _production_authority_specs(
        DebateRoomGraph._round_adaptive_economics
    )

    assert specs == [
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
        {
            "authority_mode": "context",
        },
    ]


def test_decision_round_is_explicit_committee_synthesis():
    specs = _production_authority_specs(
        DebateRoomGraph._round_adaptive_decision
    )

    assert specs == [
        {
            "authority_mode": "synthesis",
        },
        {
            "authority_mode": "synthesis",
        },
        {
            "authority_mode": "synthesis",
        },
        {
            "authority_mode": "synthesis",
        },
    ]


def test_debate_answer_projects_declared_authority_mode():
    graph = DebateRoomGraph()

    cases = (
        (
            {
                "authority_mode": "claim",
                "canonical_claim_id": "local_feasibility",
            },
            "claim",
        ),
        (
            {
                "authority_mode": "sources",
                "canonical_source_scope":
                    "local_direct_competitor_sources",
            },
            "sources",
        ),
        (
            {
                "authority_mode": "context",
            },
            "context",
        ),
        (
            {
                "authority_mode": "synthesis",
            },
            "synthesis",
        ),
    )

    for authority, expected in cases:
        questions = graph._adaptive_questions(
            number=2,
            language="en",
            analysis=_analysis(),
            evidence_category="market",
            specifications=[
                _spec(
                    **authority
                ),
            ],
        )

        answer = questions[0]["answer"]

        assert (
            answer["authority_mode"]
            == expected
        )


def test_legacy_question_authority_is_explicitly_marked_legacy():
    graph = DebateRoomGraph()

    questions = graph._adaptive_questions(
        number=1,
        language="en",
        analysis=_analysis(),
        evidence_category="market",
        specifications=[
            _spec(),
        ],
    )

    answer = questions[0]["answer"]

    assert (
        answer["authority_mode"]
        == "legacy_category"
    )
