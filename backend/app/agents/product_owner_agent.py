from __future__ import annotations

import json

from pydantic import ValidationError

from app.llm.json_response import (
    JSONResponseError,
    extract_json_object,
)
from app.llm.provider import LLMProvider
from app.schemas.project_management import (
    CandidateBacklogV1,
    ProjectManagementContextV1,
)


from app.services.candidate_backlog_authority import (
    candidate_backlog_authority_validator,
)


class ProductOwnerGenerationError(RuntimeError):
    """
    Stable failure raised by Product Owner candidate generation.

    The error exposes deterministic machine-readable codes and never
    substitutes a fabricated backlog when generation or validation fails.
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
        ).strip()

        self.details = list(
            details
            or []
        )

        super().__init__(
            message
        )


class ProductOwnerAgent:
    """
    Sprint 4 AI Product Owner candidate generator.

    Authority boundary:
    - consumes only ProjectManagementContextV1;
    - proposes only CandidateBacklogV1;
    - never owns final priority, Story Points, sprint assignment,
      canonical identifiers, architecture or technology decisions.

    Provider execution is deliberately separated from this first
    structural implementation. Runtime generation is enabled only after
    provider/failure contracts are certified.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
    ) -> None:
        # Dependency is optional so prompt construction stays deterministic
        # and testable without API credentials or network access.
        #
        # The central provider will be used by the runtime generation layer;
        # this class does not duplicate provider fallback/rate-limit logic.
        self._llm = llm

    def build_prompt(
        self,
        context: ProjectManagementContextV1,
    ) -> str:
        """
        Build the candidate-generation prompt from canonical PM context only.

        This method is deterministic and does not mutate the context.
        """

        if not isinstance(
            context,
            ProjectManagementContextV1,
        ):
            raise TypeError(
                "context must be a "
                "ProjectManagementContextV1"
            )

        canonical_context = context.model_dump(
            mode="json"
        )

        context_json = json.dumps(
            canonical_context,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        return (
            "You are the AI Product Owner candidate generator for ForgeAI.\n"
            "\n"
            "ROLE BOUNDARY\n"
            "- Propose backlog candidates only.\n"
            "- Do not make final planning or implementation decisions.\n"
            "- Do not invent users, workflows, scope, constraints, risks, "
            "or business facts.\n"
            "- Use only the canonical project-management context below.\n"
            "\n"
            "MANDATORY HASH BINDING\n"
            f"- source_context_hash: {context.source_context_hash}\n"
            f"- context_hash: {context.context_hash}\n"
            "- The candidate backlog must preserve both hashes exactly.\n"
            "- Every candidate story must preserve source_context_hash "
            "exactly.\n"
            "\n"
            "SCOPE GUARDRAILS\n"
            "- scope_exclusions are negative constraints, never positive "
            "feature justification.\n"
            "- Unknown, unsupported or ambiguous information must not become "
            "a positive backlog requirement.\n"
            "- Candidate provenance must reference only canonical context "
            "facts.\n"
            "\n"
            "CANDIDATE-ONLY OUTPUT\n"
            "- Propose epics, features, user stories and acceptance criteria.\n"
            "- Candidate priority is advisory only.\n"
            "- Candidate complexity is advisory only.\n"
            "- Candidate dependencies are advisory only.\n"
            "- Do not assign final Story Points.\n"
            "- Do not assign sprint numbers.\n"
            "- Do not assign canonical backlog identifiers.\n"
            "- Do not make architecture, stack or database decisions.\n"
            "\n"
            "OUTPUT FORMAT\n"
            "- Return one JSON object compatible with CandidateBacklogV1.\n"
            "- Return JSON only.\n"
            "- Do not wrap the response in Markdown fences.\n"
            "\n"
            "CANONICAL PROJECT MANAGEMENT CONTEXT\n"
            f"{context_json}\n"
        )

    async def generate_candidate_backlog(
        self,
        context: ProjectManagementContextV1,
    ) -> CandidateBacklogV1:
        """
        Generate one strict candidate backlog.

        The LLM proposes candidate planning content only.
        Pydantic validates its structure.
        CandidateBacklogAuthorityValidator validates its binding to the
        canonical ProjectManagementContextV1.

        This layer never assigns final priority, Story Points, canonical
        backlog identifiers or sprint placement.
        """

        if not isinstance(
            context,
            ProjectManagementContextV1,
        ):
            raise TypeError(
                "context must be a "
                "ProjectManagementContextV1"
            )

        provider = self._llm

        if provider is None:
            try:
                provider = LLMProvider()

            except Exception as exc:
                raise ProductOwnerGenerationError(
                    "generation_temporarily_unavailable",
                    (
                        "Product Owner generation "
                        "provider is unavailable."
                    ),
                ) from exc

        prompt = self.build_prompt(
            context=context,
        )

        try:
            raw_response = await provider.invoke(
                prompt,
                "product_owner_candidate_backlog",
            )

        except Exception as exc:
            raise ProductOwnerGenerationError(
                "generation_temporarily_unavailable",
                (
                    "Product Owner candidate generation "
                    "is temporarily unavailable."
                ),
            ) from exc

        try:
            payload = extract_json_object(
                raw_response
            )

            candidate = (
                CandidateBacklogV1.model_validate(
                    payload
                )
            )

        except (
            JSONResponseError,
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise ProductOwnerGenerationError(
                "invalid_model_response",
                (
                    "Product Owner model response "
                    "does not satisfy CandidateBacklogV1."
                ),
            ) from exc

        authority = (
            candidate_backlog_authority_validator.validate(
                context=context,
                candidate=candidate,
            )
        )

        if not authority.is_valid:
            raise ProductOwnerGenerationError(
                "candidate_authority_rejected",
                (
                    "Product Owner candidate backlog "
                    "failed canonical authority validation."
                ),
                details=list(
                    authority.error_codes
                ),
            )

        return candidate
