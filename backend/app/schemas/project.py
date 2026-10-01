from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_output_language(value: Optional[str]) -> str:
    cleaned = str(value or "fr").strip().lower()

    if cleaned in {"fr", "français", "francais", "french"}:
        return "fr"

    if cleaned in {"en", "english", "anglais"}:
        return "en"

    return "fr"


class ProjectCreate(BaseModel):
    title: str
    description: str
    industry: Optional[str] = None
    # A missing region must remain unknown for the context-confidence gate.
    # The creation page sends null when no region is chosen: same meaning.
    market_region: Optional[str] = ""

    # Language Lock.
    # fr => toute l’analyse doit sortir en français.
    # en => toute l’analyse doit sortir en anglais.
    output_language: str = Field(default="fr")

    @field_validator("output_language")
    @classmethod
    def validate_output_language(cls, value: Optional[str]) -> str:
        return normalize_output_language(value)

    @field_validator("market_region")
    @classmethod
    def unknown_region_stays_empty(cls, value: Optional[str]) -> str:
        # null, "" and blanks all mean "unknown": never a default country.
        return (value or "").strip()


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    market_region: Optional[str] = None
    output_language: Optional[str] = None
    status: Optional[str] = None

    @field_validator("output_language")
    @classmethod
    def validate_output_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return normalize_output_language(value)


class ProjectClarificationUpdate(BaseModel):
    """
    Durable answers keyed by canonical clarification field.

    An empty answer means remove the previously stored answer for that
    field. Question text is never used as persistence identity.
    """

    answers: Dict[str, str]

    @field_validator("answers")
    @classmethod
    def validate_answers(
        cls,
        value: Dict[str, str],
    ) -> Dict[str, str]:
        answers = dict(
            value
            or {}
        )

        if len(
            answers
        ) > 64:
            raise ValueError(
                "At most 64 clarification answers "
                "may be submitted at once."
            )

        normalized: Dict[str, str] = {}

        for raw_field, raw_answer in (
            answers.items()
        ):
            field = str(
                raw_field
                or ""
            ).strip()

            answer = str(
                raw_answer
                or ""
            ).strip()

            if not field:
                raise ValueError(
                    "Clarification field must not "
                    "be empty."
                )

            if len(
                field
            ) > 120:
                raise ValueError(
                    "Clarification field is too long."
                )

            if (
                not field.isascii()
                or not field[
                    0
                ].isalpha()
                or field.lower()
                != field
                or not field.replace(
                    "_",
                    "",
                ).isalnum()
            ):
                raise ValueError(
                    "Clarification field must be a "
                    "canonical lowercase identifier."
                )

            if len(
                answer
            ) > 4000:
                raise ValueError(
                    "Clarification answer is too long."
                )

            normalized[
                field
            ] = answer

        return normalized


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    industry: Optional[str] = None
    market_region: str = ""
    output_language: str = "fr"
    status: str
    startup_score: Optional[float] = None
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    analysis_status: str = "not_started"
    analysis_step: str = "idle"
    analysis_progress: int = 0
    analysis_data: Optional[Dict[str, Any]] = None
    clarification_context: Optional[Dict[str, Any]] = None
    analysis_error: Optional[str] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None


class ProjectAnalysisResponse(BaseModel):
    project_id: int
    analysis_status: str
    analysis_step: str = "idle"
    analysis_progress: int = 0
    analysis_data: Optional[Dict[str, Any]] = None
    clarification_context: Optional[Dict[str, Any]] = None
    analysis_error: Optional[str] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
