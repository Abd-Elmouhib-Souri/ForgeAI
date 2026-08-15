from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class DebateAnswer(TypedDict, total=False):
    direct_answer: str
    reasoning_summary: str
    confidence: float

    support_status: str

    evidence_status: str
    claim_kind: str
    validation_required: Optional[bool]

    source_ids: List[str]
    evidence_ids: List[str]
    evidence_used: List[Dict[str, Any]]

    canonical_claim_id: str
    canonical_claim_found: bool

    unresolved_point: str


class DebateQuestion(TypedDict, total=False):
    question_id: str
    asked_by: str
    addressed_to: str
    answered_by: str
    question: str
    question_type: str
    answer: DebateAnswer
    follow_up_question: str
    meeting_preparation: Dict[str, Any]


class DebateRoomState(TypedDict, total=False):
    project_id: int
    title: str
    description: str
    industry: str
    region: str
    output_language: str
    project_context: Dict[str, Any]
    analysis_data: Dict[str, Any]
    round: int
    max_rounds: int
    rounds: List[Dict[str, Any]]
    judge: Dict[str, Any]
    completed_steps: List[str]
    failed_steps: List[str]
    current_step: str
    progress: int
    completed: bool
    error: Optional[str]
