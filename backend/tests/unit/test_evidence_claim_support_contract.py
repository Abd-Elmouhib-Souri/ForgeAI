from app.services.evidence_ledger import EvidenceLedger


def _claim_by_id(
    ledger,
    claim_id,
):
    return next(
        (
            claim
            for claim in ledger["claims"]
            if claim["claim_id"] == claim_id
        ),
        None,
    )


def _source(
    *,
    title,
    url,
    snippet,
    category,
):
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source_type": "market_article",
        "source_role": "market_evidence",
        "canonical_category": "market_evidence",
        "region_match": "international",
        "public_display": True,
        "evidence_categories": [
            category,
        ],
        "source_relevance_score": 0.80,
    }


def test_market_need_is_never_promoted_to_solution_feasibility() -> None:
    ledger = EvidenceLedger().build(
        {
            "market_study": {
                "market_need": (
                    "Teams still manage the process manually "
                    "and need to prove that the problem is "
                    "frequent and painful."
                ),
            },
            "competitive_analysis": {
                "sources": [
                    _source(
                        title=(
                            "Workflow automation platform"
                        ),
                        url=(
                            "https://example.test/"
                            "workflow-platform"
                        ),
                        snippet=(
                            "A workflow automation product "
                            "for operational teams."
                        ),
                        category=(
                            "solution_benchmark"
                        ),
                    ),
                ],
            },
        }
    )

    assert (
        _claim_by_id(
            ledger,
            "solution_feasibility",
        )
        is None
    )


def test_problem_claim_rejects_category_only_support() -> None:
    ledger = EvidenceLedger().build(
        {
            "problem": (
                "Manual invoice reconciliation causes "
                "duplicate supplier payments."
            ),
            "competitive_analysis": {
                "sources": [
                    _source(
                        title=(
                            "Warehouse temperature monitoring"
                        ),
                        url=(
                            "https://example.test/"
                            "warehouse-monitoring"
                        ),
                        snippet=(
                            "Sensors monitor warehouse "
                            "temperature and humidity."
                        ),
                        category=(
                            "problem_context"
                        ),
                    ),
                ],
            },
        }
    )

    claim = _claim_by_id(
        ledger,
        "problem_relevance",
    )

    assert claim is not None
    assert claim["source_ids"] == []
    assert (
        claim["evidence_status"]
        == "not_confirmed"
    )
    assert (
        claim["validation_required"]
        is True
    )


def test_problem_claim_keeps_semantically_matching_support() -> None:
    ledger = EvidenceLedger().build(
        {
            "problem": (
                "Manual invoice reconciliation causes "
                "duplicate supplier payments."
            ),
            "competitive_analysis": {
                "sources": [
                    _source(
                        title=(
                            "Manual invoice reconciliation "
                            "and duplicate supplier payments"
                        ),
                        url=(
                            "https://example.test/"
                            "invoice-errors"
                        ),
                        snippet=(
                            "Manual invoice reconciliation "
                            "can create duplicate supplier "
                            "payments and accounting errors."
                        ),
                        category=(
                            "problem_context"
                        ),
                    ),
                ],
            },
        }
    )

    claim = _claim_by_id(
        ledger,
        "problem_relevance",
    )

    assert claim is not None
    assert claim["source_ids"]
    assert (
        claim["evidence_status"]
        == "sourced"
    )


def test_solution_claim_rejects_category_only_support() -> None:
    ledger = EvidenceLedger().build(
        {
            "proposed_solution": (
                "An automated invoice reconciliation "
                "workflow matches purchase orders "
                "with supplier invoices."
            ),
            "competitive_analysis": {
                "sources": [
                    _source(
                        title=(
                            "Fleet route optimization"
                        ),
                        url=(
                            "https://example.test/"
                            "route-optimization"
                        ),
                        snippet=(
                            "Software optimizes vehicle "
                            "routes and delivery schedules."
                        ),
                        category=(
                            "solution_benchmark"
                        ),
                    ),
                ],
            },
        }
    )

    claim = _claim_by_id(
        ledger,
        "solution_feasibility",
    )

    assert claim is not None
    assert claim["source_ids"] == []
    assert (
        claim["evidence_status"]
        == "not_confirmed"
    )


def test_solution_claim_keeps_semantically_matching_support() -> None:
    ledger = EvidenceLedger().build(
        {
            "proposed_solution": (
                "An automated invoice reconciliation "
                "workflow matches purchase orders "
                "with supplier invoices."
            ),
            "competitive_analysis": {
                "sources": [
                    _source(
                        title=(
                            "Automated invoice reconciliation"
                        ),
                        url=(
                            "https://example.test/"
                            "invoice-reconciliation"
                        ),
                        snippet=(
                            "The platform automatically "
                            "matches supplier invoices "
                            "with purchase orders."
                        ),
                        category=(
                            "solution_benchmark"
                        ),
                    ),
                ],
            },
        }
    )

    claim = _claim_by_id(
        ledger,
        "solution_feasibility",
    )

    assert claim is not None
    assert claim["source_ids"]
    assert (
        claim["evidence_status"]
        == "sourced"
    )
