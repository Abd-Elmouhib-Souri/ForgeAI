from app.services.project_intelligence_layer import (
    project_intelligence_layer,
)


def test_mvp_scope_is_not_an_explicit_workflow_source():
    cases = (
        (
            "fr",
            "enregistrer les dossiers",
        ),
        (
            "en",
            "record cases",
        ),
    )

    for language, scope in cases:
        result = (
            project_intelligence_layer
            ._extract_explicit_workflows(
                description="",
                solution="",
                mvp_scope=scope,
                language=language,
            )
        )

        assert result == []


def test_priority_workflows_never_pad_from_mvp_scope():
    cases = (
        (
            "fr",
            "Le premier MVP doit inclure uniquement "
            "l'enregistrement des dossiers et les alertes.",
            [
                "suivre les interventions",
                "notifier les utilisateurs",
            ],
        ),
        (
            "en",
            "The first MVP must include only "
            "case recording and alerts.",
            [
                "track interventions",
                "notify users",
            ],
        ),
    )

    for language, scope, workflows in cases:
        result = (
            project_intelligence_layer
            ._priority_workflows(
                explicit_mvp=scope,
                mvp_scope=scope,
                solution="",
                use_case_terms=[],
                language=language,
                archetype_workflows=workflows,
            )
        )

        assert result == workflows

        normalized = " ".join(
            result
        ).casefold()

        for forbidden in (
            "premier mvp",
            "first mvp",
            "inclure uniquement",
            "include only",
            "enregistrement des dossiers",
            "case recording",
        ):
            assert forbidden not in normalized


def test_priority_workflow_fallback_uses_use_case_not_scope():
    result = (
        project_intelligence_layer
        ._priority_workflows(
            explicit_mvp=(
                "The first MVP must include only dashboards."
            ),
            mvp_scope=(
                "The first MVP must include only dashboards."
            ),
            solution="",
            use_case_terms=[
                "record inspection",
            ],
            language="en",
            archetype_workflows=[],
        )
    )

    assert result
    assert result[0] == "record inspection"

    normalized = " ".join(
        result
    ).casefold()

    assert "dashboard" not in normalized
    assert "first mvp" not in normalized
