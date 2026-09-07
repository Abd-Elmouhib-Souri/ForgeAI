from __future__ import annotations

from app.schemas.analysis_context import (
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _extractor() -> ProjectContextExtractor:

    return ProjectContextExtractor()


def test_causative_difficulty_statement_is_problem_authority_en() -> None:

    sentence = (
        "Fragmented coordination makes it difficult to "
        "track cases, assign specialists, and monitor deadlines."
    )

    assert (
        _extractor()
        ._is_problem_sentence(
            sentence
        )
    )


def test_causative_difficulty_statement_is_problem_authority_fr() -> None:

    sentence = (
        "Une coordination fragmentee rend difficile "
        "le suivi des dossiers, l'affectation des intervenants "
        "et le controle des delais."
    )

    assert (
        _extractor()
        ._is_problem_sentence(
            sentence
        )
    )


def test_positive_ease_statement_is_not_problem_authority() -> None:

    sentence = (
        "The platform makes it easy to track cases "
        "and assign specialists."
    )

    assert not (
        _extractor()
        ._is_problem_sentence(
            sentence
        )
    )


def test_problem_action_fragment_cannot_materialize_as_actor() -> None:

    description = (
        "Operations managers are the primary users. "
        "Current coordination is fragmented. "
        "This makes it difficult to track cases, "
        "assign specialists, monitor deadlines, "
        "and keep evidence of completed work."
    )

    packet = (
        _extractor()
        .extract(
            title="Neutral Coordination Product",
            description=description,
            industry="Business software",
            target_region="International",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )

    actor_keys = [
        comparison_key(
            actor.name
        )
        for actor
        in (
            packet.actors
            or []
        )
    ]

    workflow_actor_keys = [
        comparison_key(
            workflow.actor
        )
        for workflow
        in (
            packet.priority_workflows
            or []
        )
        if workflow.actor
    ]

    assert (
        "assign specialists"
        not in actor_keys
    ), actor_keys

    assert (
        "assign specialists"
        not in workflow_actor_keys
    ), workflow_actor_keys
