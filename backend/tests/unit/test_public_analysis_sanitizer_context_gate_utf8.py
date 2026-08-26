from __future__ import annotations

from app.services.public_analysis_sanitizer import (
    sanitize_analysis_data_for_public,
)


def test_public_sanitizer_preserves_context_questions() -> None:
    analysis_data = {
        "output_language": "fr",
        "idea_readiness": {
            "status": "needs_clarification",
            "score": 0.64,
            "ready_for_agents": False,
            "missing_fields": ["problem"],
            "ambiguous_fields": [
                "business_model",
                "constraints",
            ],
            "blockers": ["problem"],
            "questions": [
                (
                    "Quel problème concret, fréquent et coûteux "
                    "souhaitez-vous résoudre ?"
                ),
                (
                    "Qui paiera et selon quel modèle de revenu ?"
                ),
                (
                    "Quelles contraintes techniques, financières, "
                    "opérationnelles ou réglementaires sont déjà connues ?"
                ),
            ],
            "clarification_questions": [
                (
                    "Quel problème concret, fréquent et coûteux "
                    "souhaitez-vous résoudre ?"
                ),
                (
                    "Qui paiera et selon quel modèle de revenu ?"
                ),
                (
                    "Quelles contraintes techniques, financières, "
                    "opérationnelles ou réglementaires sont déjà connues ?"
                ),
            ],
            "recommendation": (
                "Complétez les informations avant de lancer l’analyse."
            ),
        },
        "context_confidence": {
            "score": 0.64,
            "status": "needs_clarification",
            "missing_fields": ["problem"],
            "ambiguous_fields": [
                "business_model",
                "constraints",
            ],
            "blockers": ["problem"],
            "clarification_questions": [
                (
                    "Quel problème concret, fréquent et coûteux "
                    "souhaitez-vous résoudre ?"
                ),
                (
                    "Qui paiera et selon quel modèle de revenu ?"
                ),
                (
                    "Quelles contraintes techniques, financières, "
                    "opérationnelles ou réglementaires sont déjà connues ?"
                ),
            ],
            "ready_for_agents": False,
        },
    }

    public_data = sanitize_analysis_data_for_public(
        analysis_data,
        project_context={
            "title": "Student App",
            "description": (
                "Je veux créer une application pour les étudiants."
            ),
            "industry": "Éducation",
            "market_region": "",
            "output_language": "fr",
        },
    )

    assert public_data is not None

    readiness = public_data["idea_readiness"]
    confidence = public_data["context_confidence"]

    assert len(readiness["questions"]) == 3
    assert len(readiness["clarification_questions"]) == 3
    assert len(confidence["clarification_questions"]) == 3

    assert readiness["missing_fields"] == ["problem"]
    assert readiness["ambiguous_fields"] == [
        "business_model",
        "constraints",
    ]
    assert readiness["blockers"] == ["problem"]


def test_public_sanitizer_repairs_common_utf8_mojibake() -> None:
    public_data = sanitize_analysis_data_for_public(
        {
            "output_language": "fr",
            "summary": (
                "Ã‰tape de lâ€™analyse : Pays/RÃ©gion cible."
            ),
        },
        project_context={
            "title": "Projet",
            "description": "Description",
            "industry": "SaaS",
            "market_region": "",
            "output_language": "fr",
        },
    )

    assert public_data is not None
    assert public_data["summary"] == (
        "Étape de l’analyse : Pays/Région cible."
    )


def test_public_sanitizer_still_hides_technical_keys() -> None:
    public_data = sanitize_analysis_data_for_public(
        {
            "output_language": "fr",
            "debug": {"secret": True},
            "raw_response": "private",
            "summary": "Résumé public",
        },
        project_context={
            "title": "Projet",
            "description": "Description",
            "industry": "SaaS",
            "market_region": "",
            "output_language": "fr",
        },
    )

    assert public_data is not None
    assert "debug" not in public_data
    assert "raw_response" not in public_data
    assert public_data["summary"] == "Résumé public"


def test_public_sanitizer_preserves_structured_clarification_items_across_domain_guard(
    monkeypatch,
) -> None:
    """
    clarification_items are a deterministic public authority contract.

    DomainIntegrityGuard may sanitize unrelated business prose, but it must
    never break the canonical field <-> kind <-> question identity emitted
    by IdeaReadinessChecker / ContextConfidenceGate.
    """
    from copy import deepcopy

    import app.services.public_analysis_sanitizer as sanitizer_module

    clarification_items = [
        {
            "field": "priority_workflow",
            "kind": "missing",
            "question": (
                "What end-to-end action must "
                "the user complete?"
            ),
        },
        {
            "field": "business_model",
            "kind": "ambiguous",
            "question": (
                "Who will pay and through "
                "which revenue model?"
            ),
        },
        {
            "field": "mvp_scope",
            "kind": "ambiguous",
            "question": (
                "What is the exact scope of "
                "the first testable version?"
            ),
        },
        {
            "field": "constraints",
            "kind": "ambiguous",
            "question": (
                "Which technical, financial, operational, "
                "or regulatory constraints are already known?"
            ),
        },
    ]

    clarification_questions = [
        item["question"]
        for item in clarification_items
    ]

    analysis_data = {
        "output_language": "en",
        "idea_readiness": {
            "status": "needs_clarification",
            "score": 0.35,
            "ready_for_agents": False,
            "missing_fields": [
                "priority_workflow",
            ],
            "ambiguous_fields": [
                "business_model",
                "mvp_scope",
                "constraints",
            ],
            "blockers": [
                "priority_workflow",
            ],
            "questions": deepcopy(
                clarification_questions
            ),
            "clarification_questions": deepcopy(
                clarification_questions
            ),
            "clarification_items": deepcopy(
                clarification_items
            ),
            "recommendation": (
                "Complete the missing project context "
                "before starting the analysis."
            ),
        },
        "context_confidence": {
            "score": 0.35,
            "status": "needs_clarification",
            "missing_fields": [
                "priority_workflow",
            ],
            "ambiguous_fields": [
                "business_model",
                "mvp_scope",
                "constraints",
            ],
            "blockers": [
                "priority_workflow",
            ],
            "clarification_questions": deepcopy(
                clarification_questions
            ),
            "ready_for_agents": False,
        },
    }

    def force_guard_failure(
        *,
        data,
        project_context,
    ):
        return {
            "is_valid": False,
        }

    def destructive_guard_sanitizer(
        *,
        data,
        project_context,
    ):
        damaged = deepcopy(
            data
        )

        items = (
            damaged
            .get(
                "idea_readiness",
                {},
            )
            .get(
                "clarification_items",
                [],
            )
        )

        assert len(items) == 4

        # Reproduce the exact class of corruption discovered by
        # Lot 1D.2B runtime integration.
        items[0]["field"] = ""
        items[1]["question"] = ""
        items[2]["question"] = ""
        items[3]["question"] = ""

        return damaged

    monkeypatch.setattr(
        sanitizer_module.domain_integrity_guard,
        "validate_object",
        force_guard_failure,
    )

    monkeypatch.setattr(
        sanitizer_module.domain_integrity_guard,
        "sanitize_object",
        destructive_guard_sanitizer,
    )

    public_data = (
        sanitizer_module
        .sanitize_analysis_data_for_public(
            analysis_data,
            project_context={
                "title": "Generic digital service",
                "description": "A digital service.",
                "industry": "Digital services",
                "market_region": "France",
                "output_language": "en",
            },
        )
    )

    assert public_data is not None

    assert (
        public_data[
            "idea_readiness"
        ][
            "clarification_items"
        ]
        == clarification_items
    ), (
        "PUBLIC_SANITIZER_MUTATED_STRUCTURED_"
        "CLARIFICATION_AUTHORITY"
    )
