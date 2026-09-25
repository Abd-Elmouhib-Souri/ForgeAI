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


# Exact key synonyms observed in real model answers -> contract field names.
# Only KEY renames: values are never created, changed or guessed, and a
# canonical key already present always wins over its synonym.
_COLUMN_KEY_ALIASES = {"type": "data_type", "datatype": "data_type", "sql_type": "data_type"}
_FOREIGN_KEY_KEY_ALIASES = {
    "source_column": "column",
    "from_column": "column",
    "referenced_table": "references_table",
    "reference_table": "references_table",
    "ref_table": "references_table",
    "referenced_column": "references_column",
    "reference_column": "references_column",
    "ref_column": "references_column",
}


def _rename_keys(item, aliases):
    if not isinstance(item, dict):
        return item
    renamed = dict(item)
    for alias, canonical in aliases.items():
        if alias in renamed and canonical not in renamed:
            renamed[canonical] = renamed.pop(alias)
    return renamed


def normalize_candidate_field_aliases(payload):
    """Rename known database key synonyms in a raw candidate payload."""
    if not isinstance(payload, dict):
        return payload
    database = payload.get("database")
    if not isinstance(database, dict) or not isinstance(database.get("entities"), list):
        return payload
    entities = []
    for entity in database["entities"]:
        if isinstance(entity, dict):
            entity = dict(entity)
            if isinstance(entity.get("columns"), list):
                entity["columns"] = [_rename_keys(c, _COLUMN_KEY_ALIASES) for c in entity["columns"]]
            if isinstance(entity.get("foreign_keys"), list):
                entity["foreign_keys"] = [_rename_keys(f, _FOREIGN_KEY_KEY_ALIASES) for f in entity["foreign_keys"]]
        entities.append(entity)
    return {**payload, "database": {**database, "entities": entities}}


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
            "- Use EXACTLY these layer names for the four core responsibilities: frontend, backend, database, infrastructure (at most one layer each). Put every client surface (web app, mobile app, tablet or kiosk screen) under frontend, and hosting/deployment under infrastructure. Mark a core layer not_applicable only when the context truly has no such responsibility.\n"
            "- Any other technical concern (for example realtime messaging, cache, offline sync, payments) is an additional layer with its own descriptive name.\n"
            "- Use recommended, conditional or not_applicable honestly.\n"
            "- Give a justification for every proposed layer.\n"
            "- Every layer marked recommended or conditional MUST include a non-empty technology field naming the actual technology (e.g. \"PostgreSQL\", \"React\"). Never leave it blank or generic.\n"
            "\n"
            "UML\n"
            "- UML source syntax is PlantUML.\n"
            "- Candidate UML may be partial; ForgeAI validates and repairs only missing or invalid required diagram types later.\n"
            "- Never fabricate actors or workflows merely to fill a diagram.\n"
            "- Every use_case diagram MUST contain at least one actor and one use case, drawn strictly from the actors and priority_workflows already present in the canonical context below. An empty container is never valid.\n"
            "\n"
            "DATABASE\n"
            "- Database status may be recommended, conditional or not_applicable.\n"
            "- If persistent structured storage is not justified, use not_applicable and do not invent tables.\n"
            "- If database is applicable, provide a SQL dialect and structured project-domain entities.\n"
            "- Every applicable entity must contain real project-domain columns.\n"
            "- Every entity needs name, description, columns and foreign_keys.\n"
            "- Every column uses exactly: name, data_type, nullable, primary_key, unique (never \"type\").\n"
            "- Identify primary-key columns explicitly with primary_key=true.\n"
            "- Every foreign key uses exactly: column, references_table, references_column (never source_column/referenced_table/referenced_column).\n"
            "- Do not describe the internal ForgeAI database; describe the user's project database only.\n"
            "\n"
            "OUTPUT\n"
            "- Return JSON only.\n"
            "- No Markdown fences.\n"
            "- Follow CandidateSolutionArchitectureV1 JSON schema exactly.\n"
            "- Copy no provider-owned canonical decision.\n"
            "\n"
            f"CONTEXT_BINDING_HASH = {context.upstream_context_fingerprint}\n"
            f"PROJECT_NAME = {context.project_name}\n"
            "\n"
            "EXAMPLE OF CORRECT TOP-LEVEL JSON SHAPE "
            "(structure only, do not reuse these values; "
            "architecture, stack, uml_diagrams, database, warnings, "
            "assumptions and confidence are ALL SIBLING FIELDS at the "
            "TOP LEVEL, never nested inside architecture):\n"
            "{\"schema_version\":\"candidate_solution_architecture_v1\","
            "\"source_context_fingerprint\":\"<sha256>\","
            "\"architecture\":{\"style\":\"modular_monolith\","
            "\"rationale\":[\"...\"],\"quality_attributes\":[],"
            "\"constraints_addressed\":[],\"risks\":[],\"alternatives\":[]},"
            "\"stack\":{\"layers\":[{\"layer\":\"frontend\","
            "\"status\":\"recommended\",\"technology\":\"<technology>\","
            "\"justification\":\"...\"},{\"layer\":\"backend\","
            "\"status\":\"recommended\",\"technology\":\"<technology>\","
            "\"justification\":\"...\"},{\"layer\":\"database\","
            "\"status\":\"recommended\",\"technology\":\"<technology>\","
            "\"justification\":\"...\"},{\"layer\":\"infrastructure\","
            "\"status\":\"recommended\",\"technology\":\"<technology>\","
            "\"justification\":\"...\"}]},"
            "\"uml_diagrams\":[{\"diagram_type\":\"class\","
            "\"syntax\":\"plantuml\",\"source\":\"@startuml\\n...\\n@enduml\"}],"
            "\"database\":{\"status\":\"recommended\",\"rationale\":\"...\","
            "\"dialect\":\"postgresql\",\"entities\":[{\"name\":\"<table>\",\"description\":\"...\","
            "\"columns\":[{\"name\":\"id\",\"data_type\":\"INTEGER\",\"primary_key\":true,\"nullable\":false},"
            "{\"name\":\"<other_table>_id\",\"data_type\":\"INTEGER\",\"nullable\":false}],"
            "\"foreign_keys\":[{\"column\":\"<other_table>_id\",\"references_table\":\"<other_table>\","
            "\"references_column\":\"id\"}]}]},"
            "\"warnings\":[],\"assumptions\":[],\"confidence\":0.7}\n"
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

        plantuml_examples = {
            "use_case": (
                "@startuml\n"
                "actor User\n"
                "actor Admin\n"
                "rectangle System {\n"
                "  User --> (Search item)\n"
                "  User --> (Place order)\n"
                "  Admin --> (Manage catalog)\n"
                "}\n"
                "@enduml"
            ),
            "class": (
                "@startuml\n"
                "class User {\n"
                "  +id: int\n"
                "  +login()\n"
                "}\n"
                "class Order {\n"
                "  +id: int\n"
                "  +date: datetime\n"
                "}\n"
                "User \"1\" --> \"many\" Order\n"
                "@enduml"
            ),
            "sequence": (
                "@startuml\n"
                "actor User\n"
                "participant API\n"
                "participant Database\n"
                "User -> API: request\n"
                "API -> Database: query\n"
                "Database --> API: result\n"
                "API --> User: response\n"
                "@enduml"
            ),
            "activity": (
                "@startuml\n"
                "start\n"
                ":User opens app;\n"
                "if (Logged in?) then (yes)\n"
                "  :Show dashboard;\n"
                "else (no)\n"
                "  :Show login;\n"
                "endif\n"
                "stop\n"
                "@enduml"
            ),
        }

        prompt = (
            "You are repairing exactly one missing or invalid UML diagram for ForgeAI.\n"
            "Return JSON only and no Markdown fences.\n"
            "Use PlantUML only.\n"
            "Use only actors, workflows, scope and constraints from the canonical context.\n"
            "Do not add another diagram type.\n"
            "Do not invent domain facts.\n"
            f"REQUESTED_DIAGRAM_TYPE = {diagram_type}\n"
            f"CONTEXT_BINDING_HASH = {context.upstream_context_fingerprint}\n"
            "REQUIRED JSON FIELDS = diagram_type, syntax, source\n"
            "syntax must be plantuml.\n"
            "EXAMPLE OF VALID PLANTUML SYNTAX FOR THIS DIAGRAM TYPE "
            "(structure only, do not reuse these facts):\n"
            f"{plantuml_examples[diagram_type]}\n"
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

            # Deterministic key-synonym repair (renames only, never content):
            # models often write "type" / "source_column" for our fields.
            candidate_payload = normalize_candidate_field_aliases(
                candidate_payload
            )

            # ForgeAI owns canonical context binding.
            candidate_payload[
                "source_context_fingerprint"
            ] = (
                context
                .upstream_context_fingerprint
            )

            # ForgeAI owns the contract version exactly like the context
            # binding above: the LLM never decides which schema version
            # its own output claims (a missing/typo'd literal used to
            # reject an otherwise valid candidate).
            candidate_payload[
                "schema_version"
            ] = "candidate_solution_architecture_v1"

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
            preview_start = str(raw_response or "")[:300]
            preview_end = str(raw_response or "")[-300:]
            print(
                f"CANDIDATE_RAW_RESPONSE_INVALID length={len(str(raw_response or ''))} "
                f"start={preview_start!r} end={preview_end!r}",
                flush=True,
            )
            raise SolutionArchitectGenerationError(
                "invalid_model_response",
                (
                    "Solution Architect model response does not "
                    f"satisfy CandidateSolutionArchitectureV1. Detail: {exc}"
                ),
            ) from exc

        return candidate














