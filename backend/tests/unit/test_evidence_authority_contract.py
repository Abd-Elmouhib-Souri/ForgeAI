from app.services.evidence_ledger import EvidenceLedger


def _claims_by_path(data):
    ledger = EvidenceLedger().build(data)

    return (
        ledger,
        {
            item["path"]: item
            for item in ledger["claims"]
        },
    )


def test_evidence_ledger_exposes_one_canonical_status_axis() -> None:
    ledger, claims = _claims_by_path(
        {
            "market_study": {
                "market_size": (
                    "Non confirmé. Les preuves retenues ne "
                    "permettent pas de quantifier ce marché."
                ),
                "market_trends": [
                    "Signal à valider : adoption potentielle."
                ],
            },
            "financial_estimation": {
                "estimated_mvp_budget": "25 000 TND",
            },
            "competitive_analysis": {
                "sources": [],
            },
        }
    )

    assert (
        ledger["status_contract"]
        == "canonical_evidence_status_v1"
    )

    assert set(
        ledger["canonical_evidence_statuses"]
    ) == {
        "sourced",
        "estimated",
        "not_confirmed",
    }

    assert claims

    for claim in claims.values():
        assert claim["status"] in {
            "sourced",
            "estimated",
            "not_confirmed",
        }

        assert (
            claim["evidence_status"]
            == claim["status"]
        )


def test_financial_estimate_is_not_external_evidence() -> None:
    _, claims = _claims_by_path(
        {
            "financial_estimation": {
                "estimated_mvp_budget": "25 000 TND",
            },
            "competitive_analysis": {
                "sources": [],
            },
        }
    )

    claim = claims[
        "financial_estimation.estimated_mvp_budget"
    ]

    assert claim["evidence_status"] == "estimated"
    assert claim["claim_kind"] == "estimate"
    assert claim["validation_required"] is True
    assert claim["source_ids"] == []


def test_non_confirmed_claim_requires_validation() -> None:
    _, claims = _claims_by_path(
        {
            "market_study": {
                "market_size": (
                    "Non confirmé. Les données sont "
                    "insuffisantes pour quantifier le marché."
                ),
            },
            "competitive_analysis": {
                "sources": [],
            },
        }
    )

    claim = claims[
        "market_study.market_size"
    ]

    assert (
        claim["evidence_status"]
        == "not_confirmed"
    )
    assert claim["claim_kind"] == "evidence_claim"
    assert claim["validation_required"] is True


def test_claim_kind_is_independent_from_evidence_status() -> None:
    _, claims = _claims_by_path(
        {
            "market_study": {
                "market_overview": (
                    "The project targets operational teams."
                ),
                "local_context": (
                    "Recommendation: validate the local context "
                    "with field interviews."
                ),
                "local_feasibility": (
                    "Cautious conclusion: local feasibility "
                    "requires further evidence."
                ),
            },
            "competitive_analysis": {
                "sources": [],
            },
        }
    )

    assert (
        claims["market_study.market_overview"][
            "claim_kind"
        ]
        == "project_input"
    )

    assert (
        claims["market_study.local_context"][
            "claim_kind"
        ]
        == "recommendation"
    )

    assert (
        claims["market_study.local_feasibility"][
            "claim_kind"
        ]
        == "audit_conclusion"
    )

    for path in (
        "market_study.market_overview",
        "market_study.local_context",
        "market_study.local_feasibility",
    ):
        assert (
            claims[path]["evidence_status"]
            in {
                "estimated",
                "not_confirmed",
                "sourced",
            }
        )


def test_external_market_claim_without_source_is_not_confirmed() -> None:
    ledger = EvidenceLedger().build(
        {
            "market_study": {
                "global_potential": (
                    "The global smart beekeeping market "
                    "is expanding rapidly."
                ),
                "market_trends": [
                    "Demand for traceable honey is rising."
                ],
            },
            "forgecrawler": {
                "sources": [],
            },
        }
    )

    claims = {
        item["path"]: item
        for item in ledger["claims"]
    }

    global_claim = claims[
        "market_study.global_potential"
    ]

    trend_claim = claims[
        "market_study.market_trends[0]"
    ]

    assert global_claim["source_ids"] == []
    assert (
        global_claim["evidence_status"]
        == "not_confirmed"
    )
    assert (
        global_claim["status"]
        == "not_confirmed"
    )
    assert global_claim["validation_required"] is True

    assert trend_claim["source_ids"] == []
    assert (
        trend_claim["evidence_status"]
        == "not_confirmed"
    )
    assert trend_claim["validation_required"] is True


def test_public_sanitizer_neutralizes_unsupported_global_claim() -> None:
    from app.services.evidence_ledger import (
        evidence_ledger,
    )

    result = evidence_ledger.sanitize_public_claims(
        {
            "output_language": "en",
            "market_study": {
                "global_potential": (
                    "The global smart beekeeping market "
                    "is expanding rapidly."
                ),
            },
            "forgecrawler": {
                "sources": [],
            },
        }
    )

    text = result["market_study"][
        "global_potential"
    ].lower()

    assert "does not confirm" in text

    ledger = result["evidence_ledger"]

    claim = next(
        item
        for item in ledger["claims"]
        if (
            item["path"]
            == "market_study.global_potential"
        )
    )

    assert claim["source_ids"] == []
    assert (
        claim["evidence_status"]
        == "not_confirmed"
    )


def test_local_feasibility_without_local_evidence_is_not_confirmed() -> None:
    from app.services.evidence_ledger import (
        evidence_ledger,
    )

    raw = {
        "output_language": "en",
        "market_study": {
            "local_feasibility": (
                "Tunisia has strong demand and lacks digital tools."
            ),
        },
        "forgecrawler": {
            "sources": [],
        },
    }

    ledger = evidence_ledger.build(
        raw
    )

    claim = next(
        item
        for item in ledger["claims"]
        if (
            item["path"]
            == "market_study.local_feasibility"
        )
    )

    assert claim["source_ids"] == []
    assert claim["claim_kind"] == "audit_conclusion"

    assert (
        claim["evidence_status"]
        == "not_confirmed"
    )

    assert (
        claim["status"]
        == "not_confirmed"
    )

    assert claim["validation_required"] is True

    sanitized = evidence_ledger.sanitize_public_claims(
        raw
    )

    public_text = sanitized[
        "market_study"
    ][
        "local_feasibility"
    ].lower()

    assert "does not confirm" in public_text

    sanitized_claim = next(
        item
        for item in sanitized[
            "evidence_ledger"
        ][
            "claims"
        ]
        if (
            item["path"]
            == "market_study.local_feasibility"
        )
    )

    assert (
        sanitized_claim["evidence_status"]
        == "not_confirmed"
    )
    assert sanitized_claim["validation_required"] is True


def test_fact_checker_preserves_canonical_registry_semantics() -> None:
    from app.agents.fact_checker_agent import (
        FactCheckerAgent,
    )
    from app.services.evidence_ledger import (
        evidence_ledger,
    )

    analysis = {
        "output_language": "en",
        "market_study": {
            "global_potential": (
                "Demand for this workflow is expanding."
            ),
            "local_feasibility": (
                "The initial region has strong demand."
            ),
        },
        "financial_estimation": {
            "estimated_mvp_budget": "25 000",
        },
        "forgecrawler": {
            "sources": [],
        },
        "competitive_analysis": {
            "sources": [],
        },
    }

    ledger = evidence_ledger.build(
        analysis
    )

    cards = (
        FactCheckerAgent()
        ._claims_from_registry(
            registry=ledger,
            language="en",
            fallback_sources=[],
        )
    )

    ledger_by_id = {
        item["claim_id"]: item
        for item in ledger["claims"]
    }

    cards_by_id = {
        item["claim_id"]: item
        for item in cards
    }

    for claim_id, card in (
        cards_by_id.items()
    ):
        canonical = ledger_by_id[
            claim_id
        ]

        assert (
            card["status"]
            == canonical[
                "evidence_status"
            ]
        )

        assert (
            card["evidence_status"]
            == canonical[
                "evidence_status"
            ]
        )

        assert (
            card["claim_kind"]
            == canonical[
                "claim_kind"
            ]
        )

        assert (
            card[
                "validation_required"
            ]
            == canonical[
                "validation_required"
            ]
        )

        assert (
            card["source_ids"]
            == canonical[
                "source_ids"
            ]
        )

    local = cards_by_id[
        "local_feasibility"
    ]

    assert (
        local["status"]
        == "not_confirmed"
    )

    assert (
        local["evidence_status"]
        == "not_confirmed"
    )

    assert (
        local["claim_kind"]
        == "audit_conclusion"
    )

    assert (
        local["validation_required"]
        is True
    )


def test_fact_checker_cleaner_does_not_reclassify_canonical_status() -> None:
    from app.agents.fact_checker_agent import (
        FactCheckerAgent,
    )

    agent = FactCheckerAgent()

    cleaned = agent._clean_claims(
        [
            {
                "claim_id": "canonical-test",
                "path": "market_study.test",
                "claim": (
                    "This wording says not confirmed, "
                    "but the cleaner must not infer truth."
                ),
                "category": "market_demand",
                "status": "estimated",
                "evidence_status": "estimated",
                "claim_kind": "estimate",
                "validation_required": True,
                "confidence": "low",
                "evidence": [],
                "consulted_sources": [],
                "correction": "",
            }
        ]
    )

    assert len(cleaned) == 1

    assert (
        cleaned[0]["status"]
        == "estimated"
    )

    assert (
        cleaned[0]["evidence_status"]
        == "estimated"
    )

    assert (
        cleaned[0]["claim_kind"]
        == "estimate"
    )


def test_fact_checker_registry_exposes_problem_and_solution_claims() -> None:
    from app.agents.fact_checker_agent import (
        FactCheckerAgent,
    )
    from app.services.evidence_ledger import (
        evidence_ledger,
    )

    analysis = {
        "problem": (
            "Operational teams lose time because "
            "the workflow is fragmented."
        ),
        "proposed_solution": (
            "A digital workflow centralizes the process "
            "and records each completed action."
        ),
        "forgecrawler": {
            "sources": [],
        },
        "competitive_analysis": {
            "sources": [],
        },
    }

    ledger = evidence_ledger.build(
        analysis
    )

    cards = (
        FactCheckerAgent()
        ._claims_from_registry(
            registry=ledger,
            language="en",
            fallback_sources=[],
        )
    )

    cards_by_id = {
        item["claim_id"]: item
        for item in cards
    }

    assert "problem_relevance" in cards_by_id
    assert "solution_feasibility" in cards_by_id

    for claim_id in (
        "problem_relevance",
        "solution_feasibility",
    ):
        canonical = next(
            item
            for item in ledger["claims"]
            if item["claim_id"] == claim_id
        )

        public = cards_by_id[
            claim_id
        ]

        assert (
            public["status"]
            == canonical["evidence_status"]
        )
        assert (
            public["evidence_status"]
            == canonical["evidence_status"]
        )
        assert (
            public["claim_kind"]
            == canonical["claim_kind"]
        )
        assert (
            public["validation_required"]
            == canonical["validation_required"]
        )
        assert (
            public["source_ids"]
            == canonical["source_ids"]
        )


def test_fact_checker_has_no_competing_claim_builder_calls() -> None:
    import inspect

    from app.agents.fact_checker_agent import (
        FactCheckerAgent,
    )

    source = inspect.getsource(
        FactCheckerAgent
    )

    assert "self._build_claims(" not in source
    assert "self._merge_claim_sets(" not in source
    assert "self._status_for_claim_text(" not in source


def test_fact_checker_claim_coverage_uses_canonical_semantics() -> None:
    import inspect

    from app.agents.fact_checker_agent import (
        FactCheckerAgent,
    )

    source = inspect.getsource(
        FactCheckerAgent._build_fact_check_report
    )

    assert "registry_claims" not in source
    assert '"validation_required"' in source
    assert '"evidence_status"' in source


def test_fact_checker_public_label_prefers_evidence_status() -> None:
    import inspect

    from app.agents.fact_checker_agent import (
        FactCheckerAgent,
    )

    source = inspect.getsource(
        FactCheckerAgent._repair_public_report
    )

    assert "evidence_status" in source
    assert (
        'claim.get("evidence_status")'
        in source
    )
