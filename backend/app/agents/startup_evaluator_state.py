from typing import Any, Dict, List, Optional, TypedDict


class StartupEvaluatorState(TypedDict, total=False):
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

    completed_steps: List[str]
    failed_steps: List[str]

    current_step: str
    progress: int

    error: Optional[str]
    partial_completion: bool