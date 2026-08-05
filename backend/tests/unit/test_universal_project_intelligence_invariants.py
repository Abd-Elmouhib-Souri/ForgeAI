from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pytest

from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
    comparison_key,
)
from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def _resolve_backend_app_root() -> Path:
    """
    Résout le dossier Python `app` dans les deux environnements :

    - conteneur Docker : /app/app
    - dépôt local : <repo>/backend/app
    """
    container_root = Path("/app/app")

    if container_root.is_dir():
        return container_root

    current_file = Path(__file__).resolve()

    for parent in current_file.parents:
        candidate = parent / "app"

        if (
            parent.name == "backend"
            and candidate.is_dir()
        ):
            return candidate

        candidate = parent / "backend" / "app"

        if candidate.is_dir():
            return candidate

    raise RuntimeError(
        "Impossible de localiser le package backend/app "
        f"depuis {current_file}"
    )


BACKEND_APP_ROOT = _resolve_backend_app_root()


INDUSTRIAL_MARKETPLACE_DESCRIPTION = """
ReUseHub Tunisie est une marketplace B2B d'économie circulaire.

Le problème est que des entreprises conservent des stocks industriels
inutilisés alors que d'autres entreprises recherchent les mêmes pièces,
matériaux ou équipements à un prix raisonnable.

Les premiers clients ciblés sont les entreprises vendeuses de stocks
industriels inutilisés et les entreprises acheteuses de pièces,
matériaux ou équipements industriels.

Une entreprise vendeuse publie un lot avec sa référence, sa quantité,
son état, sa localisation et son prix. Une entreprise acheteuse recherche
un lot compatible, compare les informations, réserve le lot et conclut
la transaction avec le vendeur.

Le MVP couvrira une seule catégorie de pièces industrielles en Tunisie.

Le modèle économique envisagé est une commission par transaction terminée.
"""


INCOMPLETE_MARKETPLACE_DESCRIPTION = """
ReUseHub Tunisie est une marketplace B2B qui permet à des entreprises
vendeuses de publier leurs stocks industriels inutilisés et à des entreprises
acheteuses de rechercher puis réserver des lots compatibles.

Le problème est que les stocks dormants occupent de l'espace et immobilisent
de l'argent, tandis que d'autres entreprises recherchent ces produits à prix
réduit.

Les premiers clients ciblés sont les entreprises vendeuses de stocks
industriels et les entreprises acheteuses de pièces et matériaux.

Le vendeur publie un lot et l'acheteur le réserve après comparaison.

Le MVP couvrira une catégorie de produits en Tunisie.

Le modèle économique envisagé est une commission par transaction.

Le responsable du paiement, l'organisation du transport, la vérification
de l'état des produits et la gestion des litiges ne sont pas encore définis.
"""


def _normalized_contains(
    values: Iterable[str],
    expected: str,
) -> bool:
    expected_key = comparison_key(expected)

    return any(
        expected_key in comparison_key(value)
        or comparison_key(value) in expected_key
        for value in values
    )


def _actor_matching(
    actors: Iterable[ActorContext],
    expected: str,
) -> ActorContext:
    expected_key = comparison_key(expected)

    for actor in actors:
        actor_key = comparison_key(actor.name)

        if (
            expected_key in actor_key
            or actor_key in expected_key
        ):
            return actor

    raise AssertionError(
        f"Acteur introuvable : {expected!r}. "
        f"Acteurs reçus : {[actor.name for actor in actors]!r}"
    )


def _source(path: str) -> str:
    source_path = BACKEND_APP_ROOT / path

    assert source_path.is_file(), (
        f"Fichier de production introuvable : {source_path}"
    )

    return source_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def _joined_normalized(values: Iterable[str]) -> str:
    return " ".join(
        comparison_key(value)
        for value in values
        if value
    )


def test_industrial_marketplace_preserves_explicit_supply_and_demand_roles() -> None:
    """
    Un vendeur explicitement fourni ne doit jamais être reclassé comme acheteur.

    Ce test reproduit la perte de rôles observée dans le rapport ReUseHub.
    """
    packet = project_context_extractor.extract(
        title="ReUseHub Tunisie",
        description=INDUSTRIAL_MARKETPLACE_DESCRIPTION,
        industry="Économie circulaire / Marketplace B2B",
        target_region="Tunisie",
        output_language="fr",
    )

    seller = _actor_matching(
        packet.actors,
        "entreprises vendeuses de stocks industriels inutilisés",
    )

    buyer = _actor_matching(
        packet.actors,
        "entreprises acheteuses de pièces",
    )

    assert seller.is_explicit is True
    assert buyer.is_explicit is True

    assert seller.role == ActorRole.PROVIDER, (
        "Le côté offre explicite a été perdu ou reclassé. "
        f"Rôle reçu : {seller.role!r}"
    )

    assert buyer.role in {
        ActorRole.BUYER,
        ActorRole.USER,
    }

    legacy_actors = (
        packet.to_legacy_dict().get("actors")
        or {}
    )

    assert legacy_actors.get(
        ActorRole.PROVIDER.value
    ) == seller.name


def test_industrial_marketplace_exposes_a_project_specific_transaction_unit() -> None:
    """
    Le contrat universel doit exposer l'unité transactionnelle.

    Elle ne peut pas être remplacée par une formule générique comme
    « suivre la qualité de mise en relation et la confiance ».
    """
    packet = project_context_extractor.extract(
        title="ReUseHub Tunisie",
        description=INDUSTRIAL_MARKETPLACE_DESCRIPTION,
        industry="Économie circulaire / Marketplace B2B",
        target_region="Tunisie",
        output_language="fr",
    )

    transaction_unit = getattr(
        packet,
        "transaction_unit",
        "",
    )

    if hasattr(transaction_unit, "model_dump"):
        transaction_text = str(
            transaction_unit.model_dump(
                mode="json",
            )
        )
    else:
        transaction_text = str(
            transaction_unit or ""
        )

    transaction_key = comparison_key(
        transaction_text
    )

    assert transaction_key, (
        "ProjectContextPacketV3 ne publie pas encore transaction_unit."
    )

    assert any(
        term in transaction_key
        for term in (
            "lot",
            "stock industriel",
            "piece industrielle",
            "materiau industriel",
        )
    )

    assert any(
        term in transaction_key
        for term in (
            "publier",
            "publication",
        )
    )

    assert any(
        term in transaction_key
        for term in (
            "reserver",
            "acheter",
            "transaction",
            "accord",
        )
    )

    forbidden_generic_phrases = {
        comparison_key(
            "suivre la qualité de mise en relation et la confiance"
        ),
        comparison_key(
            "réaliser la transaction principale côté demande"
        ),
    }

    assert not any(
        phrase and phrase in transaction_key
        for phrase in forbidden_generic_phrases
    )


def test_marketplace_critical_unknowns_block_agent_execution() -> None:
    """
    Un score numérique suffisant ne doit pas masquer des inconnues
    opérationnelles critiques propres à une marketplace.
    """
    result = idea_readiness_checker.evaluate(
        title="ReUseHub Tunisie",
        description=INCOMPLETE_MARKETPLACE_DESCRIPTION,
        industry="Économie circulaire / Marketplace B2B",
        target_region="Tunisie",
        output_language="fr",
    )

    blockers = list(
        result.get("blockers")
        or []
    )

    blocker_key = _joined_normalized(
        blockers
    )

    assert result["ready_for_agents"] is False, (
        "L'analyse a été autorisée malgré des responsabilités critiques "
        "de paiement, transport, vérification et litige non définies."
    )

    assert any(
        marker in blocker_key
        for marker in (
            "payment responsibility",
            "responsabilite paiement",
            "responsable paiement",
            "payment flow",
        )
    ), blockers

    assert any(
        marker in blocker_key
        for marker in (
            "fulfillment",
            "logistics",
            "logistique",
            "transport",
            "delivery model",
        )
    ), blockers

    assert any(
        marker in blocker_key
        for marker in (
            "trust model",
            "verification",
            "confiance",
            "dispute",
            "litige",
        )
    ), blockers


def test_context_packet_contract_exposes_blocking_fields_and_archetype_confidence() -> None:
    """
    Le contrat canonique doit distinguer :
    - champs manquants généraux ;
    - champs bloquants ;
    - confiance de l'archétype ;
    - contradictions critiques.
    """
    model_fields = set(
        ProjectContextPacketV3.model_fields
    )

    assert "blocking_missing_fields" in model_fields
    assert "archetype_confidence" in model_fields
    assert "critical_contradictions" in model_fields
    assert "transaction_unit" in model_fields


def test_project_intelligence_layer_does_not_decide_readiness() -> None:
    """
    IdeaReadinessChecker + ContextConfidenceGate doivent être l'unique
    autorité de readiness.
    """
    source = _source(
        "services/project_intelligence_layer.py"
    )

    forbidden_patterns = (
        r'["\']ready_for_agents["\']\s*:\s*score\s*>=',
        r'["\']ready_for_agents["\']\s*:\s*[^,\n]*0\.75',
    )

    for pattern in forbidden_patterns:
        assert re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        ) is None, (
            "ProjectIntelligenceLayer recalcule encore ready_for_agents "
            f"avec la règle interdite : {pattern}"
        )


def test_startup_graph_never_forces_ready_for_agents_true() -> None:
    """
    Le graph doit propager la décision canonique, jamais la remplacer.
    """
    source = _source(
        "agents/startup_evaluator_graph.py"
    )

    assert re.search(
        r'["\']ready_for_agents["\']\s*:\s*True',
        source,
    ) is None, (
        "StartupEvaluatorGraph contient encore un override "
        "`ready_for_agents: True`."
    )


@pytest.mark.parametrize(
    ("relative_path", "forbidden_phrase"),
    [
        (
            "agents/startup_evaluator_graph.py",
            "progression de l’agriculture de précision et du suivi continu",
        ),
        (
            "agents/persona_builder_agent.py",
            "Demande directe par téléphone ou dans la rue",
        ),
        (
            "agents/persona_builder_agent.py",
            "Dispatch et support manuels",
        ),
        (
            "agents/bmc_agent.py",
            "Lancement concentré par zone, segment et plage horaire",
        ),
        (
            "agents/startup_score_agent.py",
            "zone géographique et une plage horaire limitée",
        ),
    ],
)
def test_general_agents_do_not_embed_domain_specific_fallbacks(
    relative_path: str,
    forbidden_phrase: str,
) -> None:
    """
    Les exemples agricoles et taxi doivent vivre dans des paquets spécialisés,
    pas dans les agents métier généraux.
    """
    source = comparison_key(
        _source(relative_path)
    )

    assert comparison_key(
        forbidden_phrase
    ) not in source, (
        f"Fallback métier spécifique encore présent dans {relative_path}: "
        f"{forbidden_phrase}"
    )


def test_non_agricultural_marketplace_packet_has_no_foreign_domain_terms() -> None:
    """
    Le contexte canonique d'une marketplace industrielle ne doit contenir
    aucun terme agricole ou taxi non fourni par l'utilisateur.
    """
    packet = project_context_extractor.extract(
        title="ReUseHub Tunisie",
        description=INDUSTRIAL_MARKETPLACE_DESCRIPTION,
        industry="Économie circulaire / Marketplace B2B",
        target_region="Tunisie",
        output_language="fr",
    )

    serialized = comparison_key(
        str(
            packet.model_dump(
                mode="json",
            )
        )
    )

    forbidden_terms = (
        "agriculture de precision",
        "robot agricole",
        "serre agricole",
        "chauffeur",
        "passager",
        "taxi dispatch",
        "maraude",
        "plage horaire",
    )

    for term in forbidden_terms:
        assert comparison_key(
            term
        ) not in serialized, (
            f"Contamination inter-domaine détectée : {term}"
        )