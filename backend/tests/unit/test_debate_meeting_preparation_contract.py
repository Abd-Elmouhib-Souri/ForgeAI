from app.agents.debate_room_graph import (
    DebateRoomGraph,
)


def _question(
    *,
    question_id: str,
    unresolved: str,
    follow_up: str,
    likely: str,
    recommended: str,
    proofs: list[str],
    evidence_used=None,
):
    return {
        "question_id": question_id,
        "asked_by": "evidence_auditor",
        "addressed_to": "project_defender",
        "answered_by": "project_defender",
        "question": "What remains to prove?",
        "answer": {
            "direct_answer": "Validation is still required.",
            "unresolved_point": unresolved,
            "evidence_used": list(
                evidence_used
                or []
            ),
        },
        "follow_up_question": follow_up,
        "meeting_preparation": {
            "likely_real_question": likely,
            "recommended_answer": recommended,
            "proofs_to_prepare": proofs,
            "answer_to_avoid": "Everything is already validated.",
        },
    }


def test_round_projects_q_and_a_uncertainty_into_meeting_preparation() -> None:
    graph = DebateRoomGraph()

    questions = [
        _question(
            question_id="q1",
            unresolved="Real payer is still unknown.",
            follow_up="Who controls the budget?",
            likely="Who pays?",
            recommended="Treat the payer as a hypothesis.",
            proofs=[
                "Offer test",
            ],
            evidence_used=[
                {
                    "source_id": "source_existing",
                    "title": "Existing evidence",
                },
            ],
        ),
        _question(
            question_id="q2",
            unresolved="Repeat use is not measured.",
            follow_up="What repeat-use threshold will you test?",
            likely="Will users come back?",
            recommended="Measure repeat behaviour in the pilot.",
            proofs=[
                "Pilot retention log",
            ],
        ),
    ]

    result = graph._round(
        number=1,
        language="en",
        topic="Validation",
        objective="Separate current evidence from remaining uncertainty.",
        question="What remains uncertain?",
        data_sources=[],
        supporting=[],
        hypotheses=[],
        risks=[],
        missing=[
            "Independent local validation.",
        ],
        validated=[],
        questions=questions,
        decision="CONTINUE_VALIDATION",
        synthesis="More evidence is required.",
        next_action="Run the bounded test.",
        go_conditions=[],
        no_go_conditions=[],
    )

    prep = result[
        "meeting_preparation"
    ]

    assert prep[
        "unresolved_points"
    ] == [
        "Real payer is still unknown.",
        "Repeat use is not measured.",
    ]

    assert prep[
        "follow_up_questions"
    ] == [
        "Who controls the budget?",
        "What repeat-use threshold will you test?",
    ]

    # Existing evidence must never be relabelled as future proof.
    assert prep[
        "proofs_to_prepare"
    ] == [
        "Offer test",
        "Pilot retention log",
    ]

    assert (
        "Existing evidence"
        not in prep[
            "proofs_to_prepare"
        ]
    )

    # Round-level missing evidence remains a separate dimension.
    assert result[
        "unresolved_questions"
    ] == [
        "Independent local validation.",
    ]


def test_global_meeting_preparation_preserves_semantic_dimensions() -> None:
    graph = DebateRoomGraph()

    rounds = [
        {
            "unresolved_questions": [
                "Local demand evidence.",
            ],
            "meeting_preparation": {
                "likely_questions": [
                    "Who pays?",
                ],
                "recommended_answers": [
                    "The payer is still being validated.",
                ],
                "proofs_to_prepare": [
                    "Offer test",
                ],
                "answers_to_avoid": [
                    "Everyone will pay.",
                ],
                "unresolved_points": [
                    "Budget owner is unknown.",
                ],
                "follow_up_questions": [
                    "Who controls the budget?",
                ],
            },
        },
        {
            "unresolved_questions": [
                "Unit economics evidence.",
            ],
            "meeting_preparation": {
                "likely_questions": [
                    "Can this scale?",
                ],
                "recommended_answers": [
                    "Scale depends on observed contribution.",
                ],
                "proofs_to_prepare": [
                    "Pilot cost ledger",
                ],
                "answers_to_avoid": [
                    "Scale solves everything.",
                ],
                "unresolved_points": [
                    "Contribution margin is unknown.",
                    "Budget owner is unknown.",
                ],
                "follow_up_questions": [
                    "What is contribution per completed unit?",
                    "Who controls the budget?",
                ],
            },
        },
    ]

    result = (
        graph._global_meeting_preparation(
            rounds,
            {
                "title": "Universal Project",
            },
            "en",
        )
    )

    assert result[
        "unresolved_questions"
    ] == [
        "Local demand evidence.",
        "Unit economics evidence.",
    ]

    assert result[
        "unresolved_points"
    ] == [
        "Budget owner is unknown.",
        "Contribution margin is unknown.",
    ]

    assert result[
        "follow_up_questions"
    ] == [
        "Who controls the budget?",
        "What is contribution per completed unit?",
    ]

    assert result[
        "proofs_to_prepare"
    ] == [
        "Offer test",
        "Pilot cost ledger",
    ]


def test_meeting_preparation_does_not_consume_evidence_used_as_future_proof() -> None:
    import inspect

    round_source = inspect.getsource(
        DebateRoomGraph._round
    )

    global_source = inspect.getsource(
        DebateRoomGraph._global_meeting_preparation
    )

    assert (
        '"unresolved_points"'
        in round_source
    )

    assert (
        '"follow_up_questions"'
        in round_source
    )

    assert (
        '"unresolved_points"'
        in global_source
    )

    assert (
        '"follow_up_questions"'
        in global_source
    )

    # Canonical evidence remains owned by the Q&A evidence projection.
    assert (
        "evidence_used"
        not in global_source
    )
