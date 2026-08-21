import pytest

from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


@pytest.mark.parametrize(
    "text",
    [
        "Le MVP ne doit pas inclure une flotte logistique propre.",
        "Le MVP ne doit pas comprendre la gestion complète des stocks.",
        "La première version ne devra pas inclure le module de facturation.",
        "Le prototype ne devrait pas contenir les fonctions avancées.",
        "Le pilote ne peut pas inclure ce module.",
    ],
)
def test_french_modal_scope_negation_is_exclusion(
    text: str,
) -> None:
    assert is_scope_exclusion_statement(
        text
    )


@pytest.mark.parametrize(
    "text",
    [
        "Le MVP doit inclure une recherche avancée.",
        "Le MVP doit comprendre un tableau de bord.",
        "Le MVP ne doit pas seulement inclure les alertes, "
        "il doit aussi inclure les rapports.",
    ],
)
def test_french_modal_scope_positive_or_additive_is_not_exclusion(
    text: str,
) -> None:
    assert not is_scope_exclusion_statement(
        text
    )
