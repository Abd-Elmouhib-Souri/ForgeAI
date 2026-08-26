
from __future__ import annotations

import pytest

from app.services.project_intelligence_layer import (
    project_intelligence_layer as pil,
)


CASES = (
    {
        "name": "MARKETPLACE",
        "title": "MarketplaceOps",
        "industry": "Marketplace B2B interventions techniques",
        "region": "Tunisie",
        "users": [
            "responsable maintenance",
            "entreprise cliente",
            "prestataire",
        ],
        "problem": (
            "les entreprises ont des difficultes "
            "a trouver et comparer des prestataires "
            "techniques fiables"
        ),
        "solution": (
            "marketplace B2B de mise en relation "
            "pour interventions techniques"
        ),
        "mvp": (
            "demande, propositions, choix et suivi "
            "d'une intervention"
        ),
        "workflows": [
            "publier une demande",
            "comparer les propositions",
            "choisir un prestataire",
        ],
        "expected_any": (
            "marketplace",
            "intervention",
            "prestataire",
        ),
        "forbidden": (),
    },
    {
        "name": "IOT",
        "title": "WaterMonitor",
        "industry": "IoT gestion de consommation d'eau",
        "region": "Tunisie",
        "users": [
            "responsable maintenance",
        ],
        "problem": (
            "detection tardive des anomalies "
            "de consommation d'eau"
        ),
        "solution": (
            "capteurs connectes et alertes "
            "de consommation anormale"
        ),
        "mvp": (
            "mesure, detection d'anomalie, "
            "alerte et verification"
        ),
        "workflows": [
            "mesurer la consommation",
            "detecter une anomalie",
            "recevoir une alerte",
        ],
        "expected_any": (
            "iot",
            "consommation",
            "capteur",
            "anomalie",
        ),
        "forbidden": (),
    },
    {
        "name": "SAAS_HANDOFF",
        "title": "ShiftOps",
        "industry": "SaaS B2B operations industrielles",
        "region": "France",
        "users": [
            "operateurs de production",
            "responsable de production",
        ],
        "problem": (
            "perte d'information lors "
            "des passations entre equipes"
        ),
        "solution": (
            "logiciel de passation structuree "
            "entre equipes de production"
        ),
        "mvp": (
            "enregistrement et consultation "
            "des informations de passation"
        ),
        "workflows": [
            "enregistrer un incident",
            "examiner la passation",
            "consulter les informations",
        ],
        "expected_any": (
            "operations industrielles",
            "production",
            "passation",
            "incident",
        ),
        "forbidden": (
            "commander directement aucune machine",
            "control industrial machines",
        ),
    },
    {
        "name": "RETAIL_STOCK",
        "title": "StockOps",
        "industry": "RetailTech gestion de stock",
        "region": "Tunisie",
        "users": [
            "responsable stock",
            "gerant du magasin",
        ],
        "problem": (
            "ruptures et surstocks causes "
            "par un suivi manuel du stock"
        ),
        "solution": (
            "suivi de stock et recommandations "
            "de reapprovisionnement"
        ),
        "mvp": (
            "alerte stock, verification et "
            "suggestion de reapprovisionnement"
        ),
        "workflows": [
            "consulter l'alerte",
            "verifier la situation",
            "preparer une suggestion de reapprovisionnement",
        ],
        "expected_any": (
            "retailtech",
            "stock",
            "reapprovisionnement",
        ),
        "forbidden": (
            "commande fournisseur necessite",
        ),
    },
)


def build(case):
    readiness = {
        "score": 1.0,
        "ready_for_agents": True,
        "status": "ready",
        "missing_fields": [],
        "ambiguous_fields": [],
        "blockers": [],
    }

    canonical = {
        "context_locked": True,
        "title": case["title"],
        "project_name": case["title"],
        "industry": case["industry"],
        "sector": case["industry"],
        "target_region": case["region"],
        "market_region": case["region"],
        "target_users": list(case["users"]),
        "problem": case["problem"],
        "solution": case["solution"],
        "business_model": "abonnement B2B",
        "mvp_scope": case["mvp"],
        "priority_workflows": list(
            case["workflows"]
        ),
    }

    return pil.build(
        title=case["title"],
        description=(
            "Secondary prose must not replace "
            "locked canonical search semantics."
        ),
        industry=case["industry"],
        target_region=case["region"],
        output_language="fr",
        project_context=canonical,
        idea_readiness=readiness,
        analysis_data={
            "idea_readiness": readiness,
        },
    )


def query_text(planner):
    values = [
        *(
            planner.get("queries")
            or []
        ),
    ]

    for items in (
        planner.get("queries_by_intent")
        or {}
    ).values():
        if isinstance(items, list):
            values.extend(items)

    return " | ".join(
        str(value)
        for value in values
    ).casefold()


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=[
        case["name"]
        for case in CASES
    ],
)
def test_query_domain_follows_locked_project_semantics(
    case,
):
    intelligence = build(case)

    planner = (
        intelligence.get(
            "query_planner"
        )
        or {}
    )

    text = query_text(
        planner
    )

    assert (
        case["region"].casefold()
        in text
    ), planner

    assert any(
        marker.casefold()
        in text
        for marker
        in case["expected_any"]
    ), planner

    assert (
        "workforce scheduling"
        not in text
    ), planner

    for forbidden in case["forbidden"]:
        assert (
            forbidden.casefold()
            not in text
        ), planner


def test_unrelated_projects_do_not_collapse_to_one_search_domain():
    domains = []

    for case in CASES:
        intelligence = build(
            case
        )

        planner = (
            intelligence.get(
                "query_planner"
            )
            or {}
        )

        base_context = str(
            planner.get(
                "base_context"
            )
            or ""
        )

        domain = (
            base_context
            .split("|", 1)[0]
            .strip()
            .casefold()
        )

        assert domain

        domains.append(
            domain
        )

    assert len(
        set(domains)
    ) == len(
        CASES
    ), domains
