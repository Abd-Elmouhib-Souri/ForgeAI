from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from app.agents.solution_architect_agent import (
    SolutionArchitectAgent,
    SolutionArchitectGenerationError,
)
from app.llm.provider import LLMProvider
from app.schemas.analysis_context import ProjectContextPacketV3
from app.schemas.solution_architecture import CanonicalSolutionArchitectureV1
from app.services.solution_architecture_canonical_assembler import (
    solution_architecture_canonical_assembler,
)
from app.services.solution_architecture_context_builder import (
    solution_architecture_context_builder,
)
from app.services.solution_architecture_core import (
    SolutionArchitectureCoreError,
    UMLCompletionService,
    database_design_builder,
    plantuml_structural_validator,
)
from app.services.solution_architecture_policy import architecture_policy_authority

logger = logging.getLogger(__name__)

# Cle de namespace dans project.analysis_data - meme convention que
# "project_manager" (app/routers/project_manager.py), pour coherence.
ANALYSIS_DATA_KEY = "solution_architecture"

# Le LLM est non-deterministe : une meme requete peut echouer une fois et
# reussir la suivante (JSON mal imbrique, PlantUML invalide, complexite non
# justifiee). On retente automatiquement plutot que de renvoyer une erreur
# a l'utilisateur des la premiere variation du modele.
MAX_GENERATION_ATTEMPTS = 3


class SolutionArchitecturePlanError(Exception):
    """Erreur metier typee : jamais une exception Python brute exposee a l'API."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _build_packet(analysis_data: Mapping[str, Any] | None) -> ProjectContextPacketV3:
    # Meme garde que project_management_plan_service._build_context :
    # jamais de generation sans contexte canonique valide en amont.
    if not isinstance(analysis_data, Mapping):
        raise SolutionArchitecturePlanError(
            "analysis_required",
            "Completez l'analyse du projet avant de generer son architecture technique.",
        )
    packet_raw = analysis_data.get("project_context_packet")
    if not isinstance(packet_raw, Mapping):
        raise SolutionArchitecturePlanError(
            "project_context_missing",
            "Le contexte canonique du projet est manquant ; relancez l'analyse.",
        )
    try:
        return ProjectContextPacketV3.model_validate(packet_raw)
    except (TypeError, ValueError) as exc:
        raise SolutionArchitecturePlanError(
            "project_context_invalid",
            "Le contexte canonique du projet est invalide ; relancez l'analyse.",
        ) from exc


async def _generate_once(
    *,
    project_id: int,
    context,
) -> CanonicalSolutionArchitectureV1:
    """Une seule tentative du pipeline LLM-dependant : agent -> policy -> UML -> DB -> canonical."""
    agent = SolutionArchitectAgent(llm=LLMProvider())

    # 1. Le LLM propose ; il ne devient jamais l'autorite canonique.
    try:
        candidate = await agent.generate_candidate_architecture(context=context)
    except SolutionArchitectGenerationError as exc:
        raise SolutionArchitecturePlanError(
            "generation_retryable",
            str(exc),
        ) from exc

    # 2. Les politiques valident AVANT toute verite canonique.
    policy_result = architecture_policy_authority.evaluate(
        context=context,
        candidate=candidate,
    )
    if not policy_result.accepted:
        reasons = "; ".join(issue.message for issue in policy_result.errors)
        raise SolutionArchitecturePlanError(
            "generation_retryable",
            reasons or "L'architecture proposee viole une regle de coherence.",
        )

    # 3. UML : ne reparer que les diagrammes manquants/invalides, preserver
    # les valides (contrat "targeted retry" S5-G3, deja certifie GREEN).
    uml_completion = UMLCompletionService(
        agent=agent,
        validator=plantuml_structural_validator,
    )
    try:
        uml_bundle = await uml_completion.complete(context=context, candidate=candidate)
    except (SolutionArchitectureCoreError, SolutionArchitectGenerationError) as exc:
        raise SolutionArchitecturePlanError(
            "generation_retryable",
            str(exc),
        ) from exc

    # 4. Base de donnees : projection deterministe, jamais de faux SQL si
    # not_applicable.
    try:
        database_design = database_design_builder.build(candidate=candidate.database)
    except (TypeError, SolutionArchitectureCoreError) as exc:
        raise SolutionArchitecturePlanError(
            "generation_retryable",
            str(exc),
        ) from exc

    # 5. Assemblage canonique final - seule source de verite persistee.
    return solution_architecture_canonical_assembler.assemble(
        context=context,
        candidate=candidate,
        uml=uml_bundle,
        database=database_design,
    )


async def generate(
    *,
    project_id: int,
    analysis_data: Mapping[str, Any] | None,
) -> CanonicalSolutionArchitectureV1:
    """
    Pipeline complet Sprint 5 :
    Packet -> Context -> Agent (candidate) -> Policy -> UML completion ->
    Database -> Canonical assembly.

    Le contexte est deterministe et calcule une seule fois. Seule la partie
    LLM-dependante (agent/policy/UML) est retentee jusqu'a
    MAX_GENERATION_ATTEMPTS fois : le LLM est non-deterministe, une
    variation de tirage suffit souvent a passer une contrainte qu'un essai
    precedent a violee, sans jamais assouplir la contrainte elle-meme.
    """
    packet = _build_packet(analysis_data)

    # Contexte technique deterministe - aucune intelligence LLM ici, calcule
    # une seule fois pour toutes les tentatives.
    context = solution_architecture_context_builder.build(packet=packet)

    last_error: SolutionArchitecturePlanError | None = None
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        try:
            canonical = await _generate_once(project_id=project_id, context=context)
            if attempt > 1:
                logger.info(
                    "solution_architect.generation_succeeded_after_retry",
                    extra={"project_id": project_id, "attempt": attempt},
                )
            return canonical
        except SolutionArchitecturePlanError as exc:
            last_error = exc
            logger.warning(
                "solution_architect.generation_attempt_failed project_id=%s attempt=%s code=%s message=%s",
                project_id, attempt, exc.code, str(exc),
            )
            continue

    logger.error(
        "solution_architect.generation_failed_all_attempts",
        extra={"project_id": project_id, "attempts": MAX_GENERATION_ATTEMPTS},
    )
    raise SolutionArchitecturePlanError(
        "generation_temporarily_unavailable",
        (
            "Le service de generation d'architecture n'a pas produit de resultat valide "
            f"apres {MAX_GENERATION_ATTEMPTS} tentatives. "
            f"Derniere cause : {last_error}"
        ),
    )


def is_stale(
    *,
    canonical: CanonicalSolutionArchitectureV1,
    analysis_data: Mapping[str, Any] | None,
) -> bool:
    """
    Fraicheur = le fingerprint stocke correspond-il au contexte reconstruit
    maintenant ? Seule l'empreinte SHA256 deterministe fait foi.
    """
    try:
        packet = _build_packet(analysis_data)
    except SolutionArchitecturePlanError:
        return True
    context = solution_architecture_context_builder.build(packet=packet)
    return context.upstream_context_fingerprint != canonical.context_fingerprint


def serialize(canonical: CanonicalSolutionArchitectureV1) -> dict[str, Any]:
    return {
        "envelope_version": 1,
        "canonical": canonical.model_dump(mode="json"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def deserialize_current(
    envelope: Mapping[str, Any] | None,
) -> CanonicalSolutionArchitectureV1 | None:
    if not isinstance(envelope, Mapping):
        return None
    canonical_raw = envelope.get("canonical")
    if not isinstance(canonical_raw, Mapping):
        return None
    return CanonicalSolutionArchitectureV1.model_validate(canonical_raw)









