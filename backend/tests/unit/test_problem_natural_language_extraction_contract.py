from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _extract_problem(
    description: str,
    *,
    language: str = "fr",
) -> str:
    packet = project_context_extractor.extract(
        title="Natural Problem Contract",
        description=description,
        industry="software and services",
        target_region="France",
        output_language=language,
    )

    return packet.problem.pain


def test_french_natural_difficulty_and_consequence_is_problem() -> None:
    """
    A user must not be forced to write
    'Le problème principal est...'.

    A natural sentence expressing difficulty plus operational
    consequence is explicit problem evidence.
    """

    description = """
    Une plateforme met en relation des entreprises avec des
    professionnels disponibles.

    Il est souvent difficile de comparer rapidement les disponibilités,
    les prix et la fiabilité des intervenants, ce qui peut prolonger
    l'arrêt d'un équipement et perturber l'activité.

    La plateforme permet ensuite de demander une intervention.
    """

    pain = _extract_problem(
        description,
        language="fr",
    )

    normalized = comparison_key(
        pain
    )

    assert pain, (
        "Natural French pain statement was lost."
    )

    assert (
        "difficile de comparer"
        in normalized
    ), pain

    assert (
        "prolonger"
        in normalized
        or "perturber"
        in normalized
    ), pain


def test_french_operational_harm_without_problem_label_is_problem() -> None:
    """
    Declarative operational harm is still a problem even when
    no literal 'problème' or 'difficulté' label is present.
    """

    description = """
    Un service aide les petites entreprises à trouver des prestataires.

    La recherche d'un intervenant fiable reste lente et incertaine
    pour les petites entreprises et retarde leurs opérations.

    La solution centralise les demandes dans une interface web.
    """

    pain = _extract_problem(
        description,
        language="fr",
    )

    normalized = comparison_key(
        pain
    )

    assert pain, (
        "Operational harm without an explicit problem label "
        "must still be recognized."
    )

    assert (
        "lente"
        in normalized
        and "incertaine"
        in normalized
    ), pain


def test_english_natural_operational_pain_is_problem() -> None:
    """
    Natural English pain expressions must obey the same universal
    contract as French ones.
    """

    description = """
    ShiftFlow is a workforce coordination tool for small factories.

    Coordinating last-minute shift changes is slow and error-prone
    for supervisors and creates avoidable scheduling conflicts.

    The application lets supervisors publish schedules and employees
    submit change requests.
    """

    pain = _extract_problem(
        description,
        language="en",
    )

    normalized = comparison_key(
        pain
    )

    assert pain, (
        "Natural English operational pain was lost."
    )

    assert (
        "slow"
        in normalized
        and "error prone"
        in normalized
    ), pain


def test_feature_scope_sentence_is_not_promoted_to_problem() -> None:
    """
    Adding broader natural-language recognition must not turn
    capabilities or MVP scope into artificial pain.
    """

    description = """
    Le MVP comprend la comparaison des disponibilités et des prix.

    Les utilisateurs peuvent filtrer les prestataires et consulter
    leurs profils.

    La plateforme affiche ensuite les résultats dans un tableau
    de bord.
    """

    pain = _extract_problem(
        description,
        language="fr",
    )

    assert pain == "", pain


def test_solution_capability_is_not_promoted_to_problem() -> None:
    """
    A positive solution mechanism is not a problem merely because
    it describes an operational action.
    """

    description = """
    La plateforme permet aux entreprises de comparer rapidement
    les prestataires disponibles.

    Les utilisateurs peuvent ensuite sélectionner un prestataire
    et envoyer une demande.

    Le service fonctionne sur le web et sur mobile.
    """

    pain = _extract_problem(
        description,
        language="fr",
    )

    assert pain == "", pain


def test_readiness_does_not_request_problem_when_natural_pain_is_explicit() -> None:
    """
    Integration contract:
    once the canonical extractor recognizes explicit natural pain,
    readiness must not invent a missing 'problem' clarification.
    Other marketplace blockers may legitimately remain.
    """

    description = """
    RepairLink est une marketplace B2B qui met en relation des
    entreprises avec des techniciens de maintenance.

    Lorsqu'un équipement professionnel tombe en panne, les entreprises
    cherchent souvent un technicien par téléphone ou bouche-à-oreille.

    Il est souvent difficile de comparer rapidement les disponibilités,
    les prix et la fiabilité des intervenants, ce qui peut prolonger
    l'arrêt de l'équipement et perturber l'activité.

    Les techniciens proposent un prix et un délai.
    L'entreprise cliente choisit ensuite une proposition.

    L'entreprise cliente paie l'intervention.
    RepairLink prélève une commission par intervention terminée.
    """

    result = idea_readiness_checker.evaluate(
        title="RepairLink Contract",
        description=description,
        industry="B2B Marketplace / Maintenance Services",
        target_region="Tunisie",
        output_language="fr",
        analysis_data={},
    )

    packet = dict(
        result.get(
            "project_context_packet"
        )
        or {}
    )

    problem = dict(
        packet.get("problem")
        or {}
    )

    missing_fields = list(
        result.get("missing_fields")
        or []
    )

    blockers = list(
        result.get("blockers")
        or []
    )

    assert problem.get("pain"), problem

    assert (
        "problem"
        not in missing_fields
    ), result

    assert (
        "problem"
        not in blockers
    ), result
