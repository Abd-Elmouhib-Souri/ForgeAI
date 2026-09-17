from __future__ import annotations

import re

from app.schemas.solution_architecture import (
    ArchitectureRecommendationV1,
    CandidateSolutionArchitectureV1,
    CanonicalSolutionArchitectureV1,
    DatabaseDesignV1,
    SolutionArchitectureContextV1,
    TechnologyLayerDecisionV1,
    TechnologyStackV1,
    UMLDiagramBundleV1,
)
from app.services.solution_architecture_policy import (
    architecture_policy_authority,
)


class SolutionArchitectureCanonicalAssemblyError(
    RuntimeError
):
    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        self.code = code

        super().__init__(
            message
        )


class SolutionArchitectureCanonicalAssembler:
    """
    Deterministic candidate-to-canonical projection.

    Candidate generation, policy validation, UML generation, database
    generation and rendering remain separate authorities.
    """

    _SLOT_ALIASES = {
        "frontend": {
            "frontend",
            "front end",
            "presentation layer",
            "ui layer",
            "user interface",
        },

        "backend": {
            "backend",
            "back end",
            "application backend",
            "server application",
        },

        "database": {
            "database",
            "data store",
            "datastore",
            "persistence layer",
        },

        "infrastructure": {
            "infrastructure",
            "deployment infrastructure",
            "hosting infrastructure",
            "cloud infrastructure",
        },
    }

    def __init__(
        self,
        *,
        policy_authority=(
            architecture_policy_authority
        ),
    ) -> None:
        self._policy_authority = (
            policy_authority
        )

    @staticmethod
    def _normalize_layer_name(
        value: str,
    ) -> str:
        return " ".join(
            re.sub(
                r"[_\-]+",
                " ",
                str(
                    value
                    or ""
                ).casefold(),
            ).split()
        )

    @staticmethod
    def _stable_strings(
        *values,
    ) -> list[str]:
        output = []
        seen = set()

        for collection in values:
            for value in (
                collection
                or []
            ):
                text = str(
                    value
                    or ""
                ).strip()

                if not text:
                    continue

                key = text.casefold()

                if key in seen:
                    continue

                seen.add(
                    key
                )

                output.append(
                    text
                )

        return output

    def _slot_for(
        self,
        layer_name: str,
    ) -> str | None:
        normalized = (
            self._normalize_layer_name(
                layer_name
            )
        )

        for slot, aliases in (
            self._SLOT_ALIASES
            .items()
        ):
            if normalized in aliases:
                return slot

        return None

    @staticmethod
    def _decision_from_candidate(
        candidate_layer,
    ) -> TechnologyLayerDecisionV1:
        return TechnologyLayerDecisionV1(
            status=(
                candidate_layer.status
            ),
            technology=(
                candidate_layer.technology
            ),
            justification=(
                candidate_layer.justification
            ),
            alternatives=list(
                candidate_layer.alternatives
            ),
            conditions=list(
                candidate_layer.conditions
            ),
        )

    @staticmethod
    def _unrepresented_slot(
        slot: str,
    ) -> TechnologyLayerDecisionV1:
        return TechnologyLayerDecisionV1(
            status="not_applicable",
            technology=None,
            justification=(
                "No candidate technical layer mapped to "
                f"the canonical {slot} reporting slot. "
                "No technology is fabricated."
            ),
            alternatives=[],
            conditions=[],
        )

    def _project_stack(
        self,
        candidate_stack,
    ) -> TechnologyStackV1:
        fixed = {}
        additional = {}

        additional_keys = set()

        for layer in (
            candidate_stack.layers
        ):
            normalized = (
                self._normalize_layer_name(
                    layer.layer
                )
            )

            if not normalized:
                raise (
                    SolutionArchitectureCanonicalAssemblyError(
                        "empty_technical_layer_name",
                        (
                            "Candidate stack contains an "
                            "empty technical layer name."
                        ),
                    )
                )

            decision = (
                self._decision_from_candidate(
                    layer
                )
            )

            slot = self._slot_for(
                layer.layer
            )

            if slot is not None:
                if slot in fixed:
                    raise (
                        SolutionArchitectureCanonicalAssemblyError(
                            "ambiguous_canonical_stack_slot",
                            (
                                "Multiple candidate layers map "
                                f"to canonical slot {slot!r}."
                            ),
                        )
                    )

                fixed[
                    slot
                ] = decision

                continue

            if (
                normalized
                in
                additional_keys
            ):
                raise (
                    SolutionArchitectureCanonicalAssemblyError(
                        "duplicate_additional_stack_layer",
                        (
                            "Duplicate normalized project-specific "
                            "technical layer."
                        ),
                    )
                )

            additional_keys.add(
                normalized
            )

            additional[
                str(
                    layer.layer
                ).strip()
            ] = decision

        ordered_additional = {
            key:
                additional[
                    key
                ]
            for key
            in sorted(
                additional,
                key=lambda value:
                    self._normalize_layer_name(
                        value
                    ),
            )
        }

        return TechnologyStackV1(
            frontend=(
                fixed.get(
                    "frontend"
                )
                or
                self._unrepresented_slot(
                    "frontend"
                )
            ),

            backend=(
                fixed.get(
                    "backend"
                )
                or
                self._unrepresented_slot(
                    "backend"
                )
            ),

            database=(
                fixed.get(
                    "database"
                )
                or
                self._unrepresented_slot(
                    "database"
                )
            ),

            infrastructure=(
                fixed.get(
                    "infrastructure"
                )
                or
                self._unrepresented_slot(
                    "infrastructure"
                )
            ),

            additional_layers=(
                ordered_additional
            ),
        )

    @staticmethod
    def _validate_uml(
        uml: UMLDiagramBundleV1,
    ) -> None:
        diagrams = (
            uml.use_case,
            uml.class_diagram,
            uml.sequence,
            uml.activity,
        )

        for diagram in diagrams:
            if (
                diagram.validation_status
                !=
                "valid"
            ):
                raise (
                    SolutionArchitectureCanonicalAssemblyError(
                        "uml_bundle_not_validated",
                        (
                            "Canonical assembly requires "
                            "all four UML diagrams to be valid."
                        ),
                    )
                )

    @staticmethod
    def _validate_database(
        *,
        candidate,
        stack: TechnologyStackV1,
        database: DatabaseDesignV1,
    ) -> None:
        candidate_database = (
            candidate.database
        )

        if candidate_database is None:
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "candidate_database_missing",
                    (
                        "Canonical database truth cannot be "
                        "assembled without candidate database intent."
                    ),
                )
            )

        candidate_na = (
            candidate_database.status
            ==
            "not_applicable"
        )

        canonical_na = (
            database.status
            ==
            "not_applicable"
        )

        if (
            candidate_na
            !=
            canonical_na
        ):
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "database_candidate_consistency_error",
                    (
                        "Candidate database status and validated "
                        "database status disagree."
                    ),
                )
            )

        stack_na = (
            stack.database.status
            ==
            "not_applicable"
        )

        if (
            stack_na
            !=
            canonical_na
        ):
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "database_stack_consistency_error",
                    (
                        "Canonical stack database decision and "
                        "validated database design disagree."
                    ),
                )
            )

    def assemble(
        self,
        *,
        context: SolutionArchitectureContextV1,
        candidate: CandidateSolutionArchitectureV1,
        uml: UMLDiagramBundleV1,
        database: DatabaseDesignV1,
    ) -> CanonicalSolutionArchitectureV1:
        if not isinstance(
            context,
            SolutionArchitectureContextV1,
        ):
            raise TypeError(
                "context must be a SolutionArchitectureContextV1"
            )

        if not isinstance(
            candidate,
            CandidateSolutionArchitectureV1,
        ):
            raise TypeError(
                "candidate must be a CandidateSolutionArchitectureV1"
            )

        if not isinstance(
            uml,
            UMLDiagramBundleV1,
        ):
            raise TypeError(
                "uml must be a UMLDiagramBundleV1"
            )

        if not isinstance(
            database,
            DatabaseDesignV1,
        ):
            raise TypeError(
                "database must be a DatabaseDesignV1"
            )

        # Presence validation happens before policy only to prevent
        # fabricating required candidate content. No canonical value is
        # created at this stage.
        if candidate.architecture is None:
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "candidate_architecture_missing",
                    (
                        "Canonical architecture cannot be "
                        "fabricated from a missing candidate."
                    ),
                )
            )

        if candidate.stack is None:
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "candidate_stack_missing",
                    (
                        "Canonical stack cannot be fabricated "
                        "from a missing candidate."
                    ),
                )
            )

        if candidate.database is None:
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "candidate_database_missing",
                    (
                        "Canonical database truth requires "
                        "candidate database intent."
                    ),
                )
            )

        if candidate.confidence is None:
            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "candidate_confidence_missing",
                    (
                        "Canonical confidence cannot be "
                        "fabricated."
                    ),
                )
            )

        policy_result = (
            self._policy_authority
            .evaluate(
                context=context,
                candidate=candidate,
            )
        )

        if (
            policy_result.accepted
            is not True
        ):
            codes = []

            for issue in (
                policy_result.errors
                or []
            ):
                code = str(
                    getattr(
                        issue,
                        "code",
                        "",
                    )
                    or ""
                ).strip()

                if code:
                    codes.append(
                        code
                    )

            suffix = (
                (
                    ": "
                    +
                    ", ".join(
                        codes
                    )
                )
                if codes
                else
                ""
            )

            raise (
                SolutionArchitectureCanonicalAssemblyError(
                    "policy_rejected",
                    (
                        "Architecture policy rejected "
                        "the candidate"
                        +
                        suffix
                    ),
                )
            )

        architecture = (
            ArchitectureRecommendationV1
            .model_validate(
                candidate
                .architecture
                .model_dump(
                    mode="json"
                )
            )
        )

        stack = (
            self._project_stack(
                candidate.stack
            )
        )

        self._validate_uml(
            uml
        )

        self._validate_database(
            candidate=candidate,
            stack=stack,
            database=database,
        )

        assumptions = (
            self._stable_strings(
                context.assumptions,
                candidate.assumptions,
            )
        )

        warnings = (
            self._stable_strings(
                candidate.warnings
            )
        )

        return CanonicalSolutionArchitectureV1(
            schema_version=(
                "canonical_solution_architecture_v1"
            ),

            context_fingerprint=(
                context
                .upstream_context_fingerprint
            ),

            architecture=architecture,

            stack=stack,

            uml=uml.model_copy(
                deep=True
            ),

            database=database.model_copy(
                deep=True
            ),

            assumptions=assumptions,

            warnings=warnings,

            confidence=(
                candidate.confidence
            ),
        )


solution_architecture_canonical_assembler = (
    SolutionArchitectureCanonicalAssembler()
)
