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
