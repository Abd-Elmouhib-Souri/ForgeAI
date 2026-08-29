from __future__ import annotations

import importlib

import pytest
from pydantic import (
    BaseModel,
    ValidationError,
)


MODULE_NAME = (
    "app.schemas.project_management"
)

REQUIRED_TYPES = (
    "CandidateAcceptanceCriterionV1",
    "CandidateEpicV1",
    "CandidateFeatureV1",
    "CandidateUserStoryV1",
    "CandidateBacklogV1",
)


def module():
    return importlib.import_module(
        MODULE_NAME
    )


def type_exists(
    name: str,
) -> bool:
    return hasattr(
        module(),
        name,
    )


def require_types() -> None:

    missing = [
        name
        for name in REQUIRED_TYPES
        if not type_exists(
            name
        )
    ]

    if missing:
        pytest.skip(
            "Blocked by CandidateBacklogV1 "
            f"schema family: {missing}"
        )


def model(
    name: str,
):
    return getattr(
        module(),
        name,
    )


def hash_value(
    character: str = "a",
) -> str:
    return (
        character
        *
        64
    )


def epic_payload():
    return {
        "candidate_key": "epic_operations",
        "title": "Core Operations",
        "description": (
            "Support the validated core operation."
        ),
        "business_goal": (
            "Complete the primary workflow reliably."
        ),
        "provenance_refs": [
            "workflow:request_review",
        ],
    }


def feature_payload():
    return {
        "candidate_key": "feature_request_review",
        "epic_key": "epic_operations",
        "title": "Request review",
        "description": (
            "Allow the canonical operator "
            "to review incoming requests."
        ),
        "business_value": (
            "Reduce processing delay."
        ),
        "provenance_refs": [
            "workflow:request_review",
            "mvp_scope:request_review",
        ],
    }


def acceptance_criterion_payload():
    return {
        "statement": (
            "Given a pending request, "
            "when the operator reviews it, "
            "then the decision is recorded."
        ),
        "candidate_testable": True,
        "source_ref": (
            "workflow:request_review"
        ),
    }


def story_payload():
    return {
        "candidate_key": "story_review_request",
        "epic_key": "epic_operations",
        "feature_key": "feature_request_review",

        "actor_ref": "Operator",

        "title": "Review incoming request",

        "capability": (
            "review an incoming request"
        ),

        "benefit": (
            "reduce processing delays"
        ),

        "story": (
            "As an Operator, I want to review "
            "an incoming request so that "
            "processing delays are reduced."
        ),

        "business_value": (
            "Faster operational processing."
        ),

        "acceptance_criteria": [
            acceptance_criterion_payload(),
        ],

        "candidate_priority": "must",

        "candidate_priority_rationale": (
            "The workflow cannot complete "
            "without request review."
        ),

        "candidate_complexity": "medium",

        "candidate_complexity_rationale": (
            "Requires workflow state handling."
        ),

        "candidate_complexity_factors": {
            'business_logic': 'unknown',
            'integration_complexity': 'unknown',
            'data_complexity': 'unknown',
            'ui_complexity': 'unknown',
            'security': 'unknown',
            'external_dependency': 'unknown',
            'uncertainty': 'unknown',
            'testing_burden': 'unknown',
            'regulatory_risk': 'unknown',
            'hardware_dependency': 'unknown',
        },
        "candidate_dependencies": [],

        "provenance_refs": [
            "actor:Operator",
            "workflow:request_review",
            "mvp_scope:request_review",
        ],

        "source_context_hash": hash_value(
            "a"
        ),

        "warnings": [],
    }


def backlog_payload():
    return {
        "schema_version": (
            "candidate_backlog_v1"
        ),

        "source_context_hash": hash_value(
            "a"
        ),

        "context_hash": hash_value(
            "b"
        ),

        "epics": [
            epic_payload(),
        ],

        "features": [
            feature_payload(),
        ],

        "stories": [
            story_payload(),
        ],

        "warnings": [],
    }


# ============================================================
# FIRST WRONG LAYER
# ============================================================


def test_candidate_backlog_schema_family_exists() -> None:

    missing = [
        name
        for name in REQUIRED_TYPES
        if not type_exists(
            name
        )
    ]

    assert not missing, (
        "Missing canonical Sprint 4 "
        "candidate backlog schemas: "
        f"{missing}"
    )


# ============================================================
# PYDANTIC / STRICTNESS
# ============================================================


@pytest.mark.parametrize(
    "name",
    REQUIRED_TYPES,
)
def test_candidate_types_are_pydantic_models(
    name,
) -> None:

    require_types()

    value = model(
        name
    )

    assert issubclass(
        value,
        BaseModel,
    )


@pytest.mark.parametrize(
    (
        "name",
        "payload",
    ),
    (
        (
            "CandidateEpicV1",
            epic_payload,
        ),
        (
            "CandidateFeatureV1",
            feature_payload,
        ),
        (
            "CandidateUserStoryV1",
            story_payload,
        ),
        (
            "CandidateAcceptanceCriterionV1",
            acceptance_criterion_payload,
        ),
        (
            "CandidateBacklogV1",
            backlog_payload,
        ),
    ),
)
def test_candidate_models_forbid_unknown_fields(
    name,
    payload,
) -> None:

    require_types()

    value = payload()
    value[
        "unexpected_authority"
    ] = "forbidden"

    with pytest.raises(
        ValidationError
    ):
        model(
            name
        ).model_validate(
            value
        )


# ============================================================
# BACKLOG CONTRACT
# ============================================================


def test_candidate_backlog_has_narrow_candidate_only_surface() -> None:

    require_types()

    fields = set(
        model(
            "CandidateBacklogV1"
        ).model_fields
    )

    assert fields == {
        "schema_version",
        "source_context_hash",
        "context_hash",
        "epics",
        "features",
        "stories",
        "warnings",
    }


def test_candidate_backlog_schema_version_is_stable() -> None:

    require_types()

    cls = model(
        "CandidateBacklogV1"
    )

    assert (
        cls.model_fields[
            "schema_version"
        ].default
        ==
        "candidate_backlog_v1"
    )


# ============================================================
# EPIC / FEATURE CONTRACT
# ============================================================


def test_candidate_epic_does_not_own_canonical_id() -> None:

    require_types()

    fields = set(
        model(
            "CandidateEpicV1"
        ).model_fields
    )

    assert "candidate_key" in fields
    assert "provenance_refs" in fields

    assert "id" not in fields


def test_candidate_feature_does_not_own_canonical_id() -> None:

    require_types()

    fields = set(
        model(
            "CandidateFeatureV1"
        ).model_fields
    )

    assert "candidate_key" in fields
    assert "epic_key" in fields
    assert "provenance_refs" in fields

    assert "id" not in fields
    assert "epic_id" not in fields


# ============================================================
# STORY AUTHORITY BOUNDARY
# ============================================================


def test_candidate_story_surface_is_advisory_not_canonical() -> None:

    require_types()

    fields = set(
        model(
            "CandidateUserStoryV1"
        ).model_fields
    )

    required = {
        "candidate_key",
        "epic_key",
        "feature_key",
        "actor_ref",
        "title",
        "capability",
        "benefit",
        "story",
        "business_value",
        "acceptance_criteria",
        "candidate_priority",
        "candidate_priority_rationale",
        "candidate_complexity",
        "candidate_complexity_rationale",
        "candidate_complexity_factors",
        "candidate_dependencies",
        "provenance_refs",
        "source_context_hash",
        "warnings",
    }

    assert not (
        required
        -
        fields
    )

    forbidden = {
        "id",
        "epic_id",
        "feature_id",
        "priority",
        "story_points",
        "sprint",
        "sprint_id",
        "sprint_number",
        "scope_status",
        "locked",
        "canonical",
    }

    assert not (
        forbidden
        &
        fields
    )


def test_candidate_priority_is_not_final_story_priority() -> None:

    require_types()

    cls = model(
        "CandidateUserStoryV1"
    )

    item = cls.model_validate(
        story_payload()
    )

    assert (
        item.candidate_priority
        ==
        "must"
    )

    assert not hasattr(
        item,
        "priority",
    )


def test_candidate_complexity_is_not_story_points() -> None:

    require_types()

    cls = model(
        "CandidateUserStoryV1"
    )

    item = cls.model_validate(
        story_payload()
    )

    assert (
        item.candidate_complexity
        ==
        "medium"
    )

    assert not hasattr(
        item,
        "story_points",
    )


# ============================================================
# PROVENANCE / HASH BINDING
# ============================================================


def test_candidate_story_requires_provenance() -> None:

    require_types()

    payload = story_payload()

    payload[
        "provenance_refs"
    ] = []

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateUserStoryV1"
        ).model_validate(
            payload
        )


def test_candidate_epic_requires_provenance() -> None:

    require_types()

    payload = epic_payload()

    payload[
        "provenance_refs"
    ] = []

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateEpicV1"
        ).model_validate(
            payload
        )


def test_candidate_feature_requires_provenance() -> None:

    require_types()

    payload = feature_payload()

    payload[
        "provenance_refs"
    ] = []

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateFeatureV1"
        ).model_validate(
            payload
        )


@pytest.mark.parametrize(
    "field",
    (
        "source_context_hash",
        "context_hash",
    ),
)
def test_backlog_hashes_must_be_sha256_hex(
    field,
) -> None:

    require_types()

    payload = backlog_payload()

    payload[
        field
    ] = "not-a-hash"

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateBacklogV1"
        ).model_validate(
            payload
        )


def test_story_source_context_hash_must_be_sha256_hex() -> None:

    require_types()

    payload = story_payload()

    payload[
        "source_context_hash"
    ] = "bad"

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateUserStoryV1"
        ).model_validate(
            payload
        )


# ============================================================
# ACCEPTANCE CRITERIA
# ============================================================


def test_acceptance_criterion_has_no_canonical_id() -> None:

    require_types()

    fields = set(
        model(
            "CandidateAcceptanceCriterionV1"
        ).model_fields
    )

    assert fields == {
        "statement",
        "candidate_testable",
        "source_ref",
    }


def test_story_requires_at_least_one_acceptance_criterion() -> None:

    require_types()

    payload = story_payload()

    payload[
        "acceptance_criteria"
    ] = []

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateUserStoryV1"
        ).model_validate(
            payload
        )


def test_candidate_epic_rejects_missing_provenance_field() -> None:

    require_types()

    payload = epic_payload()
    payload.pop(
        "provenance_refs"
    )

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateEpicV1"
        ).model_validate(
            payload
        )


def test_candidate_feature_rejects_missing_provenance_field() -> None:

    require_types()

    payload = feature_payload()
    payload.pop(
        "provenance_refs"
    )

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateFeatureV1"
        ).model_validate(
            payload
        )


def test_candidate_story_rejects_missing_provenance_field() -> None:

    require_types()

    payload = story_payload()
    payload.pop(
        "provenance_refs"
    )

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateUserStoryV1"
        ).model_validate(
            payload
        )


def test_candidate_story_rejects_missing_acceptance_criteria_field() -> None:

    require_types()

    payload = story_payload()
    payload.pop(
        "acceptance_criteria"
    )

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateUserStoryV1"
        ).model_validate(
            payload
        )


# ============================================================
# NO FIXED BACKLOG CARDINALITY
# ============================================================


def test_candidate_schema_does_not_hardcode_epic_or_story_counts() -> None:

    require_types()

    cls = model(
        "CandidateBacklogV1"
    )

    empty = {
        "schema_version": (
            "candidate_backlog_v1"
        ),

        "source_context_hash": hash_value(
            "a"
        ),

        "context_hash": hash_value(
            "b"
        ),

        "epics": [],
        "features": [],
        "stories": [],
        "warnings": [],
    }

    result = cls.model_validate(
        empty
    )

    assert result.epics == []
    assert result.features == []
    assert result.stories == []


# ============================================================
# MUTABLE DEFAULT ISOLATION
# ============================================================


def test_candidate_backlog_mutable_defaults_are_isolated() -> None:

    require_types()

    cls = model(
        "CandidateBacklogV1"
    )

    first = cls(
        source_context_hash=hash_value(
            "a"
        ),
        context_hash=hash_value(
            "b"
        ),
    )

    second = cls(
        source_context_hash=hash_value(
            "a"
        ),
        context_hash=hash_value(
            "b"
        ),
    )

    first.warnings.append(
        "first-only"
    )

    assert second.warnings == []


# ============================================================
# EXPLICIT NON-AUTHORITY
# ============================================================


@pytest.mark.parametrize(
    "field",
    (
        "priority",
        "story_points",
        "sprint_number",
        "scope_status",
        "locked",
        "architecture",
        "tech_stack",
        "database_schema",
    ),
)
def test_candidate_story_rejects_final_or_architecture_authority(
    field,
) -> None:

    require_types()

    payload = story_payload()

    payload[
        field
    ] = "forbidden"

    with pytest.raises(
        ValidationError
    ):
        model(
            "CandidateUserStoryV1"
        ).model_validate(
            payload
        )