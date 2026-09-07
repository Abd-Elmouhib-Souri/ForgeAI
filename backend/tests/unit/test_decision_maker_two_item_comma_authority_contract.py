from __future__ import annotations

from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _decision_keys(
    description: str,
) -> set[str]:

    extractor = ProjectContextExtractor()

    return {
        comparison_key(
            name
        )
        for name, role
        in extractor._declared_actor_roles(
            description
        )
        if (
            role == ActorRole.DECISION_MAKER
            and comparison_key(
                name
            )
        )
    }


def test_english_plural_decision_relation_splits_two_item_comma_list():
    actual = _decision_keys(
        "The primary decision makers are "
        "the operations manager, "
        "the administrative director."
    )

    assert actual == {
        comparison_key(
            "operations manager"
        ),
        comparison_key(
            "administrative director"
        ),
    }


def test_french_plural_decision_relation_preserves_two_item_comma_list():
    actual = _decision_keys(
        "Les principaux decideurs sont "
        "le responsable des operations, "
        "le directeur administratif."
    )

    assert actual == {
        comparison_key(
            "responsable des operations"
        ),
        comparison_key(
            "directeur administratif"
        ),
    }


def test_two_item_explicit_conjunction_remains_valid():
    actual = _decision_keys(
        "The primary decision makers are "
        "the operations manager and "
        "the administrative director."
    )

    assert actual == {
        comparison_key(
            "operations manager"
        ),
        comparison_key(
            "administrative director"
        ),
    }


def test_oxford_decision_list_remains_valid():
    actual = _decision_keys(
        "The primary decision makers are "
        "the operations manager, "
        "the administrative director, "
        "and the finance director."
    )

    assert actual == {
        comparison_key(
            "operations manager"
        ),
        comparison_key(
            "administrative director"
        ),
        comparison_key(
            "finance director"
        ),
    }


def test_internal_conjunction_is_not_split():
    actual = _decision_keys(
        "The primary decision maker is "
        "the research and development director."
    )

    assert actual == {
        comparison_key(
            "research and development director"
        ),
    }


def test_internal_comma_in_singular_title_is_not_promoted_to_list():
    actual = _decision_keys(
        "The primary decision maker is "
        "the research, development and innovation director."
    )

    assert actual == {
        comparison_key(
            "research, development and innovation director"
        ),
    }


def test_plural_two_item_comma_preserves_internal_conjunction():
    actual = _decision_keys(
        "The primary decision makers are "
        "the research and development director, "
        "the administrative director."
    )

    assert actual == {
        comparison_key(
            "research and development director"
        ),
        comparison_key(
            "administrative director"
        ),
    }


def test_conditional_decision_tail_is_not_materialized_as_unconditional():
    actual = _decision_keys(
        "The primary decision makers are "
        "the operations manager, "
        "the administrative director "
        "and optionally the general manager "
        "for small businesses."
    )

    assert comparison_key(
        "operations manager"
    ) in actual

    assert comparison_key(
        "administrative director"
    ) in actual

    assert all(
        "optionally"
        not in value
        for value in actual
    )

    assert all(
        "general manager"
        not in value
        for value in actual
    )
