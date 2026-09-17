from __future__ import annotations

import re

from app.agents.solution_architect_agent import (
    SolutionArchitectAgent,
)
from app.schemas.solution_architecture import (
    CandidateDatabaseDesignV1,
    CandidateSolutionArchitectureV1,
    CandidateUMLDiagramV1,
    DatabaseColumnV1,
    DatabaseDesignV1,
    DatabaseForeignKeyV1,
    DatabaseTableV1,
    SolutionArchitectureContextV1,
    UMLDiagramBundleV1,
    UMLDiagramV1,
)


class SolutionArchitectureCoreError(
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


class PlantUMLStructuralValidator:
    """
    Cheap deterministic validation before external rendering.

    Kroki/compiler validation remains a later independent gate.
    """

    REQUIRED_TYPES = (
        "use_case",
        "class",
        "sequence",
        "activity",
    )

    _REMOTE_INCLUDE_RE = re.compile(
        r"(?im)^\s*!include(?:url)?\s+https?://"
    )

    def validate(
        self,
        *,
        diagram_type: str,
        source: str,
    ) -> bool:
        if (
            diagram_type
            not in
            self.REQUIRED_TYPES
        ):
            return False

        text = str(
            source
            or ""
        ).strip()

        if not text:
            return False

        if not text.startswith(
            "@startuml"
        ):
            return False

        if not text.endswith(
            "@enduml"
        ):
            return False

        if self._REMOTE_INCLUDE_RE.search(
            text
        ):
            return False

        if diagram_type == "use_case":
            has_actor = bool(
                re.search(
                    r"(?im)^\s*actor\b",
                    text,
                )
            )

            has_use_case = bool(
                re.search(
                    r"(?im)^\s*usecase\b",
                    text,
                )
                or
                re.search(
                    r"\([^()\n]+\)",
                    text,
                )
            )

            return (
                has_actor
                and
                has_use_case
            )

        if diagram_type == "class":
            return bool(
                re.search(
                    (
                        r"(?im)^\s*"
                        r"(?:abstract\s+class|class|interface|enum)\b"
                    ),
                    text,
                )
            )

        if diagram_type == "sequence":
            return bool(
                re.search(
                    r"(?:--?>|<--?)",
                    text,
                )
            )

        if diagram_type == "activity":
            has_start = bool(
                re.search(
                    r"(?im)^\s*start\s*$",
                    text,
                )
            )

            has_end = bool(
                re.search(
                    r"(?im)^\s*(?:stop|end)\s*$",
                    text,
                )
            )

            return (
                has_start
                and
                has_end
            )

        return False


class UMLCompletionService:
    """
    Complete the exact four CORE UML diagrams.

    Already-valid diagrams are preserved.
    Only missing or structurally invalid types are regenerated.
    """

    REQUIRED_TYPES = (
        "use_case",
        "class",
        "sequence",
        "activity",
    )

    def __init__(
        self,
        *,
        agent: SolutionArchitectAgent,
        validator: (
            PlantUMLStructuralValidator
            |
            None
        ) = None,
    ) -> None:
        self._agent = agent

        self._validator = (
            validator
            or
            PlantUMLStructuralValidator()
        )

    async def complete(
        self,
        *,
        context: SolutionArchitectureContextV1,
        candidate: CandidateSolutionArchitectureV1,
    ) -> UMLDiagramBundleV1:
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

        if (
            candidate.source_context_fingerprint
            !=
            context.upstream_context_fingerprint
        ):
            raise SolutionArchitectureCoreError(
                "context_fingerprint_mismatch",
                (
                    "Candidate architecture is not bound "
                    "to this canonical context."
                ),
            )

        selected: dict[
            str,
            CandidateUMLDiagramV1,
        ] = {}

        for diagram in candidate.uml_diagrams:
            if (
                diagram.diagram_type
                in selected
            ):
                continue

            if self._validator.validate(
                diagram_type=(
                    diagram.diagram_type
                ),
                source=diagram.source,
            ):
                selected[
                    diagram.diagram_type
                ] = diagram

        for diagram_type in self.REQUIRED_TYPES:
            if diagram_type in selected:
                continue

            repaired = (
                await
                self._agent
                .generate_uml_diagram(
                    context=context,
                    diagram_type=diagram_type,
                )
            )

            if not self._validator.validate(
                diagram_type=diagram_type,
                source=repaired.source,
            ):
                raise SolutionArchitectureCoreError(
                    "invalid_uml_after_repair",
                    (
                        "Targeted UML repair did not produce "
                        "a structurally valid "
                        f"{diagram_type} diagram."
                    ),
                )

            selected[
                diagram_type
            ] = repaired

        canonical = {
            diagram_type:
                UMLDiagramV1(
                    diagram_type=diagram_type,
                    syntax="plantuml",
                    source=selected[
                        diagram_type
                    ].source,
                    validation_status="valid",
                )
            for diagram_type
            in self.REQUIRED_TYPES
        }

        return UMLDiagramBundleV1(
            use_case=canonical[
                "use_case"
            ],
            class_diagram=canonical[
                "class"
            ],
            sequence=canonical[
                "sequence"
            ],
            activity=canonical[
                "activity"
            ],
        )


class DatabaseDesignBuilder:
    """
    Deterministic structured DB -> SQL projection.

    The LLM may propose domain entities and columns.
    This builder owns validation and SQL serialization.
    """

    _IDENTIFIER_RE = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    _TYPE_RE = re.compile(
        (
            r"^[A-Za-z][A-Za-z0-9_]*"
            r"(?:\s+[A-Za-z][A-Za-z0-9_]*)*"
            r"(?:\(\s*\d+\s*(?:,\s*\d+\s*)?\))?$"
        )
    )

    _SAFE_DEFAULT_RE = re.compile(
        (
            r"^(?:"
            r"NULL|TRUE|FALSE|CURRENT_TIMESTAMP|"
            r"-?\d+(?:\.\d+)?|"
            r"'[^']*'"
            r")$"
        ),
        re.IGNORECASE,
    )

    _ON_DELETE = {
        "CASCADE",
        "SET NULL",
        "RESTRICT",
        "NO ACTION",
    }

    def _identifier(
        self,
        value: str,
        *,
        label: str,
    ) -> str:
        text = str(
            value
            or ""
        ).strip()

        if not self._IDENTIFIER_RE.fullmatch(
            text
        ):
            raise SolutionArchitectureCoreError(
                "invalid_database_identifier",
                (
                    f"Invalid {label}: "
                    f"{text!r}"
                ),
            )

        return text

    def _data_type(
        self,
        value: str,
    ) -> str:
        text = " ".join(
            str(
                value
                or ""
            ).strip().split()
        )

        if not self._TYPE_RE.fullmatch(
            text
        ):
            raise SolutionArchitectureCoreError(
                "invalid_database_type",
                (
                    "Unsafe or invalid SQL data type: "
                    f"{text!r}"
                ),
            )

        return text.upper()

    @staticmethod
    def _quote(
        identifier: str,
    ) -> str:
        return (
            '"'
            + identifier
            + '"'
        )

    def build(
        self,
        *,
        candidate: CandidateDatabaseDesignV1,
    ) -> DatabaseDesignV1:
        if not isinstance(
            candidate,
            CandidateDatabaseDesignV1,
        ):
            raise TypeError(
                "candidate must be a CandidateDatabaseDesignV1"
            )

        if (
            candidate.status
            ==
            "not_applicable"
        ):
            if candidate.entities:
                raise SolutionArchitectureCoreError(
                    "database_not_applicable_conflict",
                    (
                        "A not-applicable database proposal "
                        "must not contain entities."
                    ),
                )

            return DatabaseDesignV1(
                status="not_applicable",
                dialect=None,
                sql=None,
                table_definitions=[],
                tables=[],
                relationships=[],
                validation_status="not_applicable",
                assumptions=[],
                warnings=list(
                    candidate.warnings
                ),
            )

        dialect = str(
            candidate.dialect
            or ""
        ).strip()

        if not dialect:
            raise SolutionArchitectureCoreError(
                "database_dialect_missing",
                (
                    "An applicable database proposal "
                    "must provide a SQL dialect."
                ),
            )

        if not candidate.entities:
            raise SolutionArchitectureCoreError(
                "database_entities_missing",
                (
                    "An applicable database proposal "
                    "must contain at least one entity."
                ),
            )

        entity_map = {}

        for entity in candidate.entities:
            table_name = self._identifier(
                entity.name,
                label="table name",
            )

            table_key = (
                table_name.casefold()
            )

            if table_key in entity_map:
                raise SolutionArchitectureCoreError(
                    "duplicate_database_table",
                    (
                        f"Duplicate table: "
                        f"{table_name}"
                    ),
                )

            if not entity.columns:
                raise SolutionArchitectureCoreError(
                    "database_columns_missing",
                    (
                        "Applicable table "
                        f"{table_name!r} "
                        "has no columns."
                    ),
                )

            columns = []
            column_map = {}

            for column in entity.columns:
                column_name = self._identifier(
                    column.name,
                    label="column name",
                )

                column_key = (
                    column_name.casefold()
                )

                if (
                    column_key
                    in column_map
                ):
                    raise SolutionArchitectureCoreError(
                        "duplicate_database_column",
                        (
                            f"Duplicate column "
                            f"{column_name!r} "
                            f"in table {table_name!r}."
                        ),
                    )

                default = (
                    str(
                        column.default
                    ).strip()
                    if (
                        column.default
                        is not None
                    )
                    else
                    None
                )

                if (
                    default is not None
                    and
                    not self._SAFE_DEFAULT_RE.fullmatch(
                        default
                    )
                ):
                    raise SolutionArchitectureCoreError(
                        "unsafe_database_default",
                        (
                            "Unsafe SQL default for "
                            f"{table_name}.{column_name}."
                        ),
                    )

                canonical_column = DatabaseColumnV1(
                    name=column_name,
                    data_type=self._data_type(
                        column.data_type
                    ),
                    nullable=bool(
                        column.nullable
                    ),
                    primary_key=bool(
                        column.primary_key
                    ),
                    unique=bool(
                        column.unique
                    ),
                    default=default,
                )

                columns.append(
                    canonical_column
                )

                column_map[
                    column_key
                ] = canonical_column

            if not any(
                column.primary_key
                for column
                in columns
            ):
                raise SolutionArchitectureCoreError(
                    "database_primary_key_missing",
                    (
                        f"Table {table_name!r} "
                        "must define a primary key."
                    ),
                )

            entity_map[
                table_key
            ] = {
                "name":
                    table_name,
                "description":
                    entity.description,
                "columns":
                    columns,
                "column_map":
                    column_map,
                "foreign_keys":
                    list(
                        entity.foreign_keys
                    ),
            }

        relationships = []

        canonical_fk_by_table = {}

        for table_key in sorted(
            entity_map
        ):
            item = entity_map[
                table_key
            ]

            table_name = item[
                "name"
            ]

            canonical_fks = []

            for foreign_key in sorted(
                item[
                    "foreign_keys"
                ],
                key=lambda value: (
                    value.column.casefold(),
                    value.references_table.casefold(),
                    value.references_column.casefold(),
                ),
            ):
                column_name = self._identifier(
                    foreign_key.column,
                    label="foreign-key column",
                )

                target_table = self._identifier(
                    foreign_key.references_table,
                    label="referenced table",
                )

                target_column = self._identifier(
                    foreign_key.references_column,
                    label="referenced column",
                )

                if (
                    column_name.casefold()
                    not in
                    item[
                        "column_map"
                    ]
                ):
                    raise SolutionArchitectureCoreError(
                        "unknown_foreign_key_column",
                        (
                            "Unknown foreign-key column "
                            f"{table_name}.{column_name}."
                        ),
                    )

                target = entity_map.get(
                    target_table.casefold()
                )

                if target is None:
                    raise SolutionArchitectureCoreError(
                        "unknown_foreign_key_target_table",
                        (
                            "Unknown referenced table "
                            f"{target_table!r}."
                        ),
                    )

                if (
                    target_column.casefold()
                    not in
                    target[
                        "column_map"
                    ]
                ):
                    raise SolutionArchitectureCoreError(
                        "unknown_foreign_key_target_column",
                        (
                            "Unknown referenced column "
                            f"{target_table}.{target_column}."
                        ),
                    )

                on_delete = (
                    str(
                        foreign_key.on_delete
                        or ""
                    )
                    .strip()
                    .upper()
                    or
                    None
                )

                if (
                    on_delete is not None
                    and
                    on_delete not in
                    self._ON_DELETE
                ):
                    raise SolutionArchitectureCoreError(
                        "invalid_on_delete_action",
                        (
                            "Unsupported ON DELETE action: "
                            f"{on_delete!r}."
                        ),
                    )

                canonical_fk = (
                    DatabaseForeignKeyV1(
                        column=column_name,
                        references_table=target_table,
                        references_column=target_column,
                        on_delete=on_delete,
                    )
                )

                canonical_fks.append(
                    canonical_fk
                )

                relationships.append(
                    (
                        f"{table_name}.{column_name}"
                        " -> "
                        f"{target_table}.{target_column}"
                    )
                )

            canonical_fk_by_table[
                table_key
            ] = canonical_fks

        canonical_tables = []
        create_statements = []

        for table_key in sorted(
            entity_map
        ):
            item = entity_map[
                table_key
            ]

            table_name = item[
                "name"
            ]

            ordered_columns = sorted(
                item[
                    "columns"
                ],
                key=lambda value:
                    value.name.casefold(),
            )

            sql_columns = []

            for column in ordered_columns:
                parts = [
                    self._quote(
                        column.name
                    ),
                    column.data_type,
                ]

                if not column.nullable:
                    parts.append(
                        "NOT NULL"
                    )

                if column.primary_key:
                    parts.append(
                        "PRIMARY KEY"
                    )

                if (
                    column.unique
                    and
                    not column.primary_key
                ):
                    parts.append(
                        "UNIQUE"
                    )

                if (
                    column.default
                    is not None
                ):
                    parts.extend(
                        [
                            "DEFAULT",
                            column.default,
                        ]
                    )

                sql_columns.append(
                    (
                        "    "
                        +
                        " ".join(
                            parts
                        )
                    )
                )

            create_statements.append(
                (
                    "CREATE TABLE "
                    f"{self._quote(table_name)} (\n"
                    +
                    ",\n".join(
                        sql_columns
                    )
                    +
                    "\n);"
                )
            )

            canonical_tables.append(
                DatabaseTableV1(
                    name=table_name,
                    description=item[
                        "description"
                    ],
                    columns=ordered_columns,
                    foreign_keys=(
                        canonical_fk_by_table[
                            table_key
                        ]
                    ),
                )
            )

        alter_statements = []

        for table in canonical_tables:
            for foreign_key in table.foreign_keys:
                constraint_name = (
                    "fk_"
                    + table.name
                    + "_"
                    + foreign_key.column
                    + "_"
                    + foreign_key.references_table
                    + "_"
                    + foreign_key.references_column
                )[
                    :63
                ]

                constraint_name = (
                    self._identifier(
                        constraint_name,
                        label="constraint name",
                    )
                )

                statement = (
                    "ALTER TABLE "
                    f"{self._quote(table.name)} "
                    "ADD CONSTRAINT "
                    f"{self._quote(constraint_name)} "
                    "FOREIGN KEY "
                    f"({self._quote(foreign_key.column)}) "
                    "REFERENCES "
                    f"{self._quote(foreign_key.references_table)} "
                    f"({self._quote(foreign_key.references_column)})"
                )

                if foreign_key.on_delete:
                    statement += (
                        " ON DELETE "
                        +
                        foreign_key.on_delete
                    )

                alter_statements.append(
                    statement
                    +
                    ";"
                )

        sql = "\n\n".join(
            [
                *create_statements,
                *sorted(
                    alter_statements
                ),
            ]
        )

        return DatabaseDesignV1(
            status=candidate.status,
            dialect=dialect,
            sql=sql,
            table_definitions=(
                canonical_tables
            ),
            tables=[
                table.name
                for table
                in canonical_tables
            ],
            relationships=sorted(
                relationships
            ),
            validation_status="valid",
            assumptions=[],
            warnings=list(
                candidate.warnings
            ),
        )


plantuml_structural_validator = (
    PlantUMLStructuralValidator()
)

database_design_builder = (
    DatabaseDesignBuilder()
)
