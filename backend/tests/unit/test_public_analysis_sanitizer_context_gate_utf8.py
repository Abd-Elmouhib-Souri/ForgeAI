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