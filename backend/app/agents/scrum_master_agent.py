from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.llm.json_response import (
    JSONResponseError,
    extract_json_object,
)
from app.llm.output_language import structured_output_language_rules
from app.llm.provider import LLMProvider
from app.schemas.project_management import (
    CanonicalBacklogV1,
    PlanningSettingsV1,
    ScrumMasterAdviceV1,
)
from app.services.dependency_graph_builder import (
    DependencyGraphV1,
)


logger = logging.getLogger(__name__)


class ScrumMasterGenerationError(RuntimeError):
    """
    Typed AI Scrum Master generation failure.

    The agent is advisory only. A generation failure must never be
    converted into a fabricated sprint plan or deterministic decision.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: list[str] | None = None,
    ) -> None:
        self.code = str(
            code
            or ""
        ).strip()

        self.details = list(
            details
            or []
        )

        super().__init__(
            message
        )


class AIScrumMasterAgent:
    """
    Sprint 4 AI Scrum Master advisory layer.

    Authority boundary:

    The agent MAY recommend:
    - Story splitting;
    - sequencing concerns;
    - delivery risks;
    - overload risks;
    - parallelization opportunities;
    - critical dependency attention.

    The agent MUST NOT:
    - change canonical priority;
    - change Story Points;
    - create or mutate dependencies;
    - override a hard dependency;
    - assign Stories to Sprints;
    - move locked Stories;
    - add capabilities;
    - make architecture decisions;
    - calculate final Velocity or Burndown;
    - produce the final Sprint plan.

    SprintPlanningEngine remains the future deterministic planning
    authority.

    Runtime provider execution is deliberately blocked in this first
    structural implementation. It will be enabled only after the
    runtime, parsing, authority-binding and failure contracts are
    certified.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        output_language: str = "",
    ) -> None:
        # Composition follows AIProductOwnerAgent.
        #
        # Dependency injection keeps prompt tests deterministic and
        # avoids requiring credentials/network access for structural QA.
        #
        # Provider fallback/rate-limit behavior remains centralized in
        # LLMProvider and must never be duplicated here.
        self._llm = llm

        # Project output language ("fr"/"en"). Passed at construction so
        # build_prompt/generate_advice keep their single canonical input
        # shape. Empty keeps the legacy prompt (no language block).
        self._output_language = str(output_language or "").strip()

    @staticmethod
    def _validate_inputs(
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        planning_settings: PlanningSettingsV1,
    ) -> None:
        if not isinstance(
            backlog,
            CanonicalBacklogV1,
        ):
            raise TypeError(
                "backlog must be a CanonicalBacklogV1"
            )

        if not isinstance(
            dependency_graph,
            DependencyGraphV1,
        ):
            raise TypeError(
                "dependency_graph must be a DependencyGraphV1"
            )

        if not isinstance(
            planning_settings,
            PlanningSettingsV1,
        ):
            raise TypeError(
                "planning_settings must be a PlanningSettingsV1"
            )

        if (
            backlog.source_context_hash
            != dependency_graph.source_context_hash
        ):
            raise ScrumMasterGenerationError(
                "canonical_binding_mismatch",
                (
                    "Backlog and dependency graph "
                    "source_context_hash differ."
                ),
            )

        if (
            backlog.context_hash
            != dependency_graph.context_hash
        ):
            raise ScrumMasterGenerationError(
                "canonical_binding_mismatch",
                (
                    "Backlog and dependency graph "
                    "context_hash differ."
                ),
            )

    def build_prompt(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        planning_settings: PlanningSettingsV1,
    ) -> str:
        """
        Build one deterministic advisory prompt.

        Only canonical backlog data, the certified dependency graph and
        explicit planning settings are serialized into the prompt.

        No external RAG/search source is consulted here.
        """

        self._validate_inputs(
            backlog,
            dependency_graph,
            planning_settings,
        )

        payload: dict[str, Any] = {
            "canonical_backlog": backlog.model_dump(
                mode="json"
            ),
            "dependency_graph": dependency_graph.model_dump(
                mode="json"
            ),
            "planning_settings": planning_settings.model_dump(
                mode="json"
            ),
        }

        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
        output_shape_json = json.dumps(
            {
                "schema_version": "scrum_master_advice_v1",
                "source_context_hash": backlog.source_context_hash,
                "context_hash": backlog.context_hash,
                "recommendations": [
                    {
                        "recommendation_type": "split|sequencing|risk|overload|parallelization|critical_dependency",
                        "story_ids": ["canonical story ID from canonical_backlog"],
                        "rationale": "advisory rationale only",
                    }
                ],
                "warnings": [],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

        # Only the rationale is human-readable; recommendation_type values
        # and canonical story IDs must stay verbatim.
        language_rules = (
            structured_output_language_rules(
                self._output_language,
                translatable_fields=["recommendations[].rationale", "warnings"],
            )
            + "\n"
            if self._output_language
            else ""
        )

        return (
            "You are the AI Scrum Master advisory agent for ForgeAI.\n"
            "\n"
            "ROLE BOUNDARY\n"
            "- Produce recommendations only.\n"
            "- Never produce or mutate the final Sprint plan.\n"
            "- Never change canonical priority.\n"
            "- Never change Story Points.\n"
            "- Never add, remove or rewrite dependencies.\n"
            "- Never override a hard dependency.\n"
            "- Never assign a Story to a Sprint.\n"
            "- Never move a locked Story.\n"
            "- Never add a capability or requirement.\n"
            "- Never make architecture or stack decisions.\n"
            "- Never calculate final Velocity or Burndown.\n"
            "\n"
            "ALLOWED RECOMMENDATION TYPES\n"
            "- split\n"
            "- sequencing\n"
            "- risk\n"
            "- overload\n"
            "- parallelization\n"
            "- critical_dependency\n"
            "- Return at most five concise recommendations.\n"
            "\n"
            "CANONICAL BINDING\n"
            f"- source_context_hash: {backlog.source_context_hash}\n"
            f"- context_hash: {backlog.context_hash}\n"
            "- Preserve both hashes exactly in the output.\n"
            "- Refer only to canonical story IDs from the backlog.\n"
            "\n"
            "DEPENDENCY AUTHORITY\n"
            "- hard_dependency is a deterministic constraint.\n"
            "- soft_dependency may inform advice but is not a hard constraint.\n"
            "- hard_topological_order is authoritative for hard-DAG ordering.\n"
            "\n"
            "PLANNING SETTINGS\n"
            "- Settings are context for advice only.\n"
            "- Do not turn settings into final sprint assignments.\n"
            "\n"
            "OUTPUT FORMAT\n"
            "- Return one JSON object compatible with ScrumMasterAdviceV1.\n"
            "- recommendations must contain only structured advisory items.\n"
            "- The top-level keys must be exactly schema_version, source_context_hash, context_hash, recommendations, warnings.\n"
            "- Each recommendation must have exactly recommendation_type, story_ids and rationale.\n"
            "- An empty recommendations array is valid when no strictly supported advice exists.\n"
            "- Return JSON only.\n"
            "- Do not wrap the response in Markdown fences.\n"
            "\n"
            f"{language_rules}"
            "EXACT OUTPUT SHAPE (replace values only; preserve all keys)\n"
            f"{output_shape_json}\n"
            "\n"
            "CANONICAL SCRUM MASTER INPUT\n"
            f"{payload_json}\n"
        )

    async def generate_advice(
        self,
        backlog: CanonicalBacklogV1,
        dependency_graph: DependencyGraphV1,
        planning_settings: PlanningSettingsV1,
    ) -> ScrumMasterAdviceV1:
        """
        Generate strict advisory Scrum Master recommendations.

        The LLM proposes advisory observations only.

        Pydantic validates the structured output, then canonical
        binding guards verify that the generated advice still refers
        exclusively to the supplied canonical backlog.

        This method never decides:
        - canonical priority;
        - Story Points;
        - dependency mutations;
        - Sprint assignment;
        - architecture;
        - Velocity;
        - Burndown.
        """

        self._validate_inputs(
            backlog,
            dependency_graph,
            planning_settings,
        )

        provider = self._llm

        if provider is None:

            try:
                provider = LLMProvider()

            except Exception as exc:
                raise ScrumMasterGenerationError(
                    "generation_temporarily_unavailable",
                    (
                        "AI Scrum Master generation "
                        "provider is unavailable."
                    ),
                ) from exc

        prompt = self.build_prompt(
            backlog,
            dependency_graph,
            planning_settings,
        )

        try:
            raw_response = await provider.invoke(
                prompt,
                "scrum_master_advice",
            )

        except Exception as exc:
            raise ScrumMasterGenerationError(
                "generation_temporarily_unavailable",
                (
                    "AI Scrum Master advisory generation "
                    "is temporarily unavailable."
                ),
            ) from exc

        try:
            payload = extract_json_object(
                raw_response
            )

            advice = (
                ScrumMasterAdviceV1.model_validate(
                    payload
                )
            )

        except (
            JSONResponseError,
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise ScrumMasterGenerationError(
                "invalid_model_response",
                (
                    "AI Scrum Master model response "
                    "does not satisfy ScrumMasterAdviceV1."
                ),
            ) from exc

        authority_details: list[str] = []

        if (
            advice.source_context_hash
            != backlog.source_context_hash
        ):
            authority_details.append(
                "source_context_hash_mismatch"
            )

        if (
            advice.context_hash
            != backlog.context_hash
        ):
            authority_details.append(
                "context_hash_mismatch"
            )

        canonical_story_ids = {
            str(
                story.story_id
            ).strip()
            for story in backlog.stories
            if str(
                story.story_id
            ).strip()
        }

        unknown_story_ids = sorted(
            {
                story_id
                for recommendation
                in advice.recommendations
                for story_id
                in recommendation.story_ids
                if story_id
                not in canonical_story_ids
            }
        )

        if unknown_story_ids:
            authority_details.append(
                "unknown_story_reference"
            )

        if authority_details:
            raise ScrumMasterGenerationError(
                "advice_authority_rejected",
                (
                    "AI Scrum Master advice failed "
                    "canonical binding validation."
                ),
                details=authority_details,
            )

        advice = advice.model_copy(
            update={
                "recommendations": [
                    item
                    for item in advice.recommendations
                    if "candidate_priority"
                    not in item.rationale.casefold()
                ]
            }
        )

        return advice
