from typing import Any, Dict, List, Optional, TypedDict


class DebateRoundModerator(TypedDict, total=False):
    role: str
    round: int
    topic: str
    focus: str
    key_question: str
    data_sources: List[str]


class DebateRoundSummary(TypedDict, total=False):
    validated_points: List[str]
    remaining_risks: List[str]
    decision: str
    synthesis: str


class DebateRoomState(TypedDict, total=False):
    project_id: int
    title: str
    description: str
    industry: str
    region: str

    # Language Lock.
    output_language: str

    # Project Context Lock.
    project_context: Dict[str, Any]

    analysis_data: Dict[str, Any]

    round: int
    max_rounds: int

    debate_plan: List[Dict[str, Any]]

    round_topic: str
    round_focus: str
    round_question: str
    round_data_sources: List[str]
    critic_role: str

    rounds: List[Dict[str, Any]]

    pending_moderator: Dict[str, Any]
    pending_defender: Dict[str, Any]
    pending_round_summary: Dict[str, Any]

    judge: Dict[str, Any]

    completed_steps: List[str]
    failed_steps: List[str]

    current_step: str
    progress: int
    completed: bool
    error: Optional[str]