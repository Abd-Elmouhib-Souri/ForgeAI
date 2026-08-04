from __future__ import annotations

import asyncio

from app.agents.bmc_agent import BMCAgent
from app.agents.financial_estimation_agent import FinancialEstimationAgent
from app.agents.swot_agent import SWOTAgent
from app.services.project_intelligence_layer import project_intelligence_layer


GREENWATCH_DESCRIPTION = """GreenWatch est un robot autonome destiné aux propriétaires de serres,
aux pépinières et aux coopératives agricoles en Tunisie.

Le problème actuel est que l’inspection manuelle des cultures demande
beaucoup de temps et permet parfois de détecter trop tard les plantes
malades, les feuilles desséchées et les signes de manque d’eau.

Le robot inspecte régulièrement les cultures avec une caméra et des
capteurs, détecte les anomalies, puis transmet les résultats à un
tableau de bord avec des alertes.

Les premiers utilisateurs ciblés sont les propriétaires de serres,
les responsables de pépinières et les coopératives agricoles.

Le MVP sera limité à une seule serre et devra détecter trois catégories :
plante saine, plante malade et manque d’eau.

Le modèle économique combine la location du robot, la maintenance
et un abonnement mensuel au tableau de bord.

Les contraintes principales sont le coût du matériel, l’autonomie
de la batterie, la précision de la détection, la connectivité dans
les serres et la maintenance du robot.

Le pilote sera considéré comme réussi si le robot couvre toute la serre,
détecte correctement au moins 85 % des anomalies et réduit le temps
d’inspection manuelle."""


def _state() -> tuple[dict, dict]:
    intelligence = project_intelligence_layer.build(
        title="GreenWatch Robot",
        description=GREENWATCH_DESCRIPTION,
        industry="Agriculture intelligente et robotique",
        target_region="Tunisie",
        output_language="fr",
    )
    structured = intelligence["structured_project_context"]
    context = project_intelligence_layer.merge_into_project_context(
        base_project_context={},
        intelligence=intelligence,
    )
    state = {
        "title": "GreenWatch Robot",
        "description": GREENWATCH_DESCRIPTION,
        "industry": "Agriculture intelligente et robotique",
        "region": "Tunisie",
        "output_language": "fr",
        "project_context": context,
        "project_intelligence": intelligence,
        "structured_project_context": structured,
        "analysis_data": {
            "project_intelligence": intelligence,
            "structured_project_context": structured,
        },
    }
    return structured, state


def test_greenwatch_context_separates_workflow_mvp_metrics_and_constraints():
    structured, _ = _state()

    assert structured["project_archetype"] == "hardware_iot"
    assert structured["target_users"] == [
        "les propriétaires de serres",
        "les responsables de pépinières",
        "les coopératives agricoles",
    ]
    assert structured["priority_workflows"][:3] == [
        "inspecter régulièrement les cultures avec une caméra et des capteurs",
        "détecter les anomalies",
        "transmettre les résultats à un tableau de bord avec des alertes",
    ]
    assert "85 %" not in structured["mvp_scope"]
    assert any("85 %" in item for item in structured["success_metrics"])
    assert "la maintenance du robot" in structured["constraints"]
    assert structured["actors"]["supply_side"] == ""


def test_greenwatch_finance_has_budget_range_and_breakdown():
    _, state = _state()
    finance = asyncio.run(FinancialEstimationAgent().run(state))

    assert finance["format"] == "financial_estimation_v6_archetype_aware"
    assert finance["currency"] == "TND"
    assert finance["mvp_budget_min"] > 0
    assert finance["mvp_budget_max"] > finance["mvp_budget_min"]
    assert len(finance["budget_breakdown"]) >= 6
    assert any("Composants" in item for item in finance["initial_costs"])
    assert finance["budget_basis"] == "internal_planning_assumption"


def test_greenwatch_bmc_has_nine_non_empty_blocks_and_specific_workflow():
    _, state = _state()
    bmc = asyncio.run(BMCAgent().run(state))

    for key in (
        "customer_segments",
        "value_propositions",
        "channels",
        "customer_relationships",
        "revenue_streams",
        "key_resources",
        "key_activities",
        "key_partnerships",
        "cost_structure",
    ):
        assert bmc[key], key

    joined = str(bmc).lower()
    assert "inspecter régulièrement les cultures" in joined
    assert "réaliser l’opération terrain principale" not in joined
    assert "fournisseurs de composants" in joined


def test_greenwatch_swot_separates_internal_and_external_factors():
    _, state = _state()
    swot = asyncio.run(SWOTAgent().run(state))

    assert len(swot["strengths"]) >= 3
    assert len(swot["weaknesses"]) >= 3
    assert len(swot["opportunities"]) >= 3
    assert len(swot["threats"]) >= 3

    threats = " ".join(swot["threats"]).lower()
    weaknesses = " ".join(swot["weaknesses"]).lower()
    assert "caméras fixes" in threats
    assert "composants importés" in threats
    assert "maintenance" in weaknesses
    assert "réaliser l’opération terrain principale" not in str(swot).lower()