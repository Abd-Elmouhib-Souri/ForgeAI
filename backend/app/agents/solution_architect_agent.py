from __future__ import annotations

import json

from pydantic import ValidationError

from app.llm.json_response import (
    JSONResponseError,
    extract_json_object,
)
from app.llm.provider import LLMProvider
from app.schemas.solution_architecture import (
    CandidateSolutionArchitectureV1,
    SolutionArchitectureContextV1,
    CandidateUMLDiagramV1,
)


class SolutionArchitectGenerationError(
    RuntimeError
):
    """
    Stable fail-closed error for Solution Architect candidate generation.
    """

    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        self.code = str(
            code
        ).strip()

        self.message = str(
            message
        ).strip()

        super().__init__(
            self.message
        )


class SolutionArchitectAgent:
    """
    Solution Architect candidate-generation boundary.

    Authority:
    - consumes only SolutionArchitectureContextV1;
    - proposes only CandidateSolutionArchitectureV1;
    - never constructs CanonicalSolutionArchitectureV1;
    - never owns deterministic architecture policy;
    - never owns rendering or Kroki access.
    """

    def __init__(
        self,
        *,
        llm: LLMProvider,
    ) -> None:
        self._llm = llm


    def build_prompt(
        self,
        *,
        context: SolutionArchitectureContextV1,
    ) -> str:
        """
        Build a deterministic candidate-only Solution Architect prompt.

        Canonical project context is input authority.
        The LLM proposes only. Policies and deterministic services retain
        final authority.
        """

        if not isinstance(
            context,
            SolutionArchitectureContextV1,
        ):
            raise TypeError(
                "context must be a SolutionArchitectureContextV1"
            )

        context_json = json.dumps(
            context.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        candidate_schema_json = json.dumps(
            CandidateSolutionArchitectureV1
            .model_json_schema(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        return (
            "You are the ForgeAI Solution Architect candidate generator.\n"
            "\n"
            "AUTHORITY BOUNDARY\n"
            "- Consume only the canonical SolutionArchitectureContextV1 below.\n"
            "- Produce a CandidateSolutionArchitectureV1 candidate only.\n"
            "- Candidate output has no canonical authority.\n"
            "- Deterministic policies and validators decide final architecture truth.\n"
            "- Never invent user facts, actors, workflows, scope or constraints.\n"
            "- Unknown information remains unknown.\n"
            "\n"
            "UNIVERSALITY\n"
            "- The recommendation must work from context, not project names, sectors or countries.\n"
            "- Do not force irrelevant technical layers.\n"
            "- You must not force web, cloud, database, microservices, containers, or any named technology without contextual support.\n"
            "- A technical layer may be not_applicable.\n"
            "\n"
            "ARCHITECTURE\n"
            "- Propose a contextual architecture style with rationale, quality attributes, constraints, risks and alternatives.\n"
            "- Advanced distributed complexity requires explicit scale, availability, integration or deployment evidence.\n"
            "\n"
            "TECHNOLOGY STACK\n"
            "- Recommend only technically relevant layers.\n"
            "- Use recommended, conditional or not_applicable honestly.\n"
            "- Give a justification for every proposed layer.\n"
            "\n"
            "UML\n"
            "- UML source syntax is PlantUML.\n"
            "- Candidate UML may be partial; ForgeAI validates and repairs only missing or invalid required diagram types later.\n"
            "- Never fabricate actors or workflows merely to fill a diagram.\n"
            "\n"
            "DATABASE\n"
            "- Database status may be recommended, conditional or not_applicable.\n"
            "- If persistent structured storage is not justified, use not_applicable and do not invent tables.\n"
            "- If database is applicable, provide a SQL dialect and structured project-domain entities.\n"
            "- Every applicable entity must contain real project-domain columns.\n"
            "- Identify primary-key columns explicitly.\n"
            "- Represent real relationships through foreign_keys with source column, referenced table and referenced column.\n"
            "- Do not describe the internal ForgeAI database; describe the user's project database only.\n"
            "\n"
            "OUTPUT\n"
            "- Return JSON only.\n"
            "- No Markdown fences.\n"
            "- Follow CandidateSolutionArchitectureV1 JSON schema exactly.\n"
            "- Copy no provider-owned canonical decision.\n"
            "\n"
            f"SOURCE_CONTEXT_FINGERPRINT = {context.upstream_context_fingerprint}\n"
            f"PROJECT_NAME = {context.project_name}\n"
            "\n"
            "CANDIDATE JSON SCHEMA\n"
            f"{candidate_schema_json}\n"
            "\n"
            "CANONICAL TECHNICAL CONTEXT\n"
            f"{context_json}\n"
        )


    async def generate_uml_diagram(
        self,
        *,
        context: SolutionArchitectureContextV1,
        diagram_type: str,
    ) -> CandidateUMLDiagramV1:
        """
        Generate exactly one requested UML candidate for bounded repair.

        This method has no canonical or renderer authority.
        """

        if not isinstance(
            context,
            SolutionArchitectureContextV1,
        ):
            raise TypeError(
                "context must be a SolutionArchitectureContextV1"
            )

        allowed = {
            "use_case",
            "class",
            "sequence",
            "activity",
        }

        if diagram_type not in allowed:
            raise ValueError(
                "unsupported UML diagram type"
            )

        context_json = json.dumps(
            context.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        prompt = (
            "You are repairing exactly one missing or invalid UML diagram for ForgeAI.\n"
            "Return JSON only and no Markdown fences.\n"
            "Use PlantUML only.\n"
            "Use only actors, workflows, scope and constraints from the canonical context.\n"
            "Do not add another diagram type.\n"
            "Do not invent domain facts.\n"
            f"REQUESTED_DIAGRAM_TYPE = {diagram_type}\n"
            f"SOURCE_CONTEXT_FINGERPRINT = {context.upstream_context_fingerprint}\n"
            "REQUIRED JSON FIELDS = diagram_type, syntax, source\n"
            "syntax must be plantuml.\n"
            "CANONICAL TECHNICAL CONTEXT\n"
            f"{context_json}\n"
        )

        try:
            raw_response = await self._llm.invoke(
                prompt,
                "solution_architect_uml_repair",
            )

        except Exception as exc:
            raise SolutionArchitectGenerationError(
                "generation_temporarily_unavailable",
                (
                    "Solution Architect UML repair "
                    "is temporarily unavailable."
                ),
            ) from exc

        try:
            payload = extract_json_object(
                raw_response
            )

            bound_payload = dict(
                payload
            )

            bound_payload[
                "diagram_type"
            ] = diagram_type

            bound_payload[
                "syntax"
            ] = "plantuml"

            diagram = (
                CandidateUMLDiagramV1
                .model_validate(
                    bound_payload
                )
            )

        except (
            JSONResponseError,
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise SolutionArchitectGenerationError(
                "invalid_model_response",
                (
                    "Solution Architect UML repair response "
                    "does not satisfy CandidateUMLDiagramV1."
                ),
            ) from exc

        return diagram

    async def generate_candidate_architecture(
        self,
        *,
        context: SolutionArchitectureContextV1,
    ) -> CandidateSolutionArchitectureV1:
        """
        Generate one typed candidate architecture.

        LLM proposes candidate content.
        ForgeAI owns source-context fingerprint binding.
        Pydantic owns structural validation.
        Later deterministic authorities own canonical decisions.
        """

        if not isinstance(
            context,
            SolutionArchitectureContextV1,
        ):
            raise TypeError(
                "context must be a SolutionArchitectureContextV1"
            )

        prompt = self.build_prompt(
            context=context
        )

        try:
            raw_response = await self._llm.invoke(
                prompt,
                "solution_architect_candidate_architecture",
            )

        except Exception as exc:
            raise SolutionArchitectGenerationError(
                "generation_temporarily_unavailable",
                (
                    "Solution Architect candidate generation "
                    "is temporarily unavailable."
                ),
            ) from exc

        try:
            payload = extract_json_object(
                raw_response
            )

            candidate_payload = dict(
                payload
            )

            # ForgeAI owns canonical context binding.
            candidate_payload[
                "source_context_fingerprint"
            ] = (
                context
                .upstream_context_fingerprint
            )

            candidate = (
                CandidateSolutionArchitectureV1
                .model_validate(
                    candidate_payload
                )
            )

        except (
            JSONResponseError,
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise SolutionArchitectGenerationError(
                "invalid_model_response",
                (
                    "Solution Architect model response does not "
                    "satisfy CandidateSolutionArchitectureV1."
                ),
            ) from exc

        return candidate
