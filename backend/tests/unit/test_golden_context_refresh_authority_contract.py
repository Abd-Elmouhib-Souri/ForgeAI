from __future__ import annotations

from app.services.project_context_extractor import (
    ProjectContextExtractor,
    comparison_key,
)


def extract(
    description: str,
    *,
    language: str = "en",
    project_context=None,
    analysis_data=None,
):
    return ProjectContextExtractor().extract(
        title="UniversalRefreshContract",
        description=description,
        industry="B2B operations",
        target_region="",
        output_language=language,
        project_context=(
            project_context
            or {}
        ),
        idea_readiness={},
        analysis_data=(
            analysis_data
            or {}
        ),
    )


def joined(
    values,
) -> str:
    return comparison_key(
        " | ".join(
            str(value)
            for value in (
                values
                or []
            )
        )
    )


# ============================================================
# G-R1 — NARRATIVE CANONICAL FIELD GRAMMAR
# ============================================================

def test_french_narrative_input_and_output_are_canonical():
    packet = extract(
        (
            "Le service aide les équipes à suivre leurs opérations. "
            "Les données d'entrée principales sont les identifiants, "
            "les statuts et les dates des dossiers. "
            "Les sorties principales sont un score de priorité, "
            "une alerte et une action recommandée."
        ),
        language="fr",
    )

    assert (
        "identifiants"
        in joined(
            packet.input_data
        )
    )

    assert (
        "score de priorite"
        in joined(
            packet.output_decision
        )
    )


def test_english_narrative_input_and_output_are_canonical():
    packet = extract(
        (
            "The service supports an operational review process. "
            "The main input data are identifiers, current status "
            "and event timestamps. "
            "The main outputs are a risk score and a recommended action."
        ),
        language="en",
    )

    assert (
        "identifiers"
        in joined(
            packet.input_data
        )
    )

    assert (
        "risk score"
        in joined(
            packet.output_decision
        )
    )


def test_narrative_human_oversight_is_canonical():
    packet = extract(
        (
            "The system detects anomalies and proposes a next action. "
            "Every recommendation must be reviewed by a human supervisor "
            "before execution."
        ),
        language="en",
    )

    assert (
        "human supervisor"
        in joined(
            packet.human_oversight
        )
    )


def test_narrative_maintenance_model_is_canonical():
    packet = extract(
        (
            "Le service collecte les mesures des équipements. "
            "La solution doit prévoir un processus de maintenance "
            "comprenant diagnostic, vérification, remplacement "
            "et reprise du service."
        ),
        language="fr",
    )

    maintenance = joined(
        packet.maintenance_model
    )

    assert (
        "diagnostic"
        in maintenance
    )

    assert (
        "remplacement"
        in maintenance
    )


# ============================================================
# G-R2 — FRESH DESCRIPTION OUTRANKS STALE DERIVED PROJECTION
# ============================================================

def test_stale_locked_revenue_solution_cannot_override_fresh_operation():
    stale_context = {
        "context_locked": True,
        "solution": (
            "The customer pays the invoice and "
            "the service charges a fee."
        ),
        "solution_type": "transaction fee",
    }

    packet = extract(
        (
            "A business service connects customer teams with "
            "qualified providers. "
            "Customer teams publish a request describing the need. "
            "Qualified providers review requests and submit proposals. "
            "The customer compares proposals, selects a provider "
            "and tracks completion."
        ),
        project_context=stale_context,
    )

    solution = comparison_key(
        packet.solution.mechanism
    )

    operational = any(
        marker in solution
        for marker in (
            "connect",
            "publish",
            "request",
            "provider",
            "proposal",
            "select",
            "track",
        )
    )

    revenue_only = (
        (
            "pays"
            in solution
            or "fee"
            in solution
        )
        and not operational
    )

    assert operational
    assert not revenue_only


# ============================================================
# G-R3 — FRESH EXPLICIT ACTOR RELATION OUTRANKS STALE IDENTITY
# ============================================================

def test_fresh_explicit_payer_supersedes_stale_locked_payer_identity():
    stale_context = {
        "context_locked": True,
        "target_users": [
            (
                "client organization is the economic "
                "payer and"
            ),
        ],
        "actors": {
            "payer": (
                "client organization is the economic "
                "payer and"
            ),
        },
        "payer_actor_names": [
            (
                "client organization is the economic "
                "payer and"
            ),
        ],
    }

    packet = extract(
        (
            "The client organization is the economic payer "
            "and pays the subscription directly. "
            "Operational staff use the application daily."
        ),
        project_context=stale_context,
    )

    payer_names = [
        comparison_key(
            value
        )
        for value in (
            packet.payer_actor_names
            or []
        )
    ]

    assert (
        "client organization"
        in payer_names
    )

    assert all(
        "economic payer and"
        not in value
        for value in payer_names
    )


# ============================================================
# G-R4 — STALE NEGATIVE WORKFLOW CANNOT RESURRECT
# ============================================================

def test_stale_locked_negative_capability_is_not_reintroduced_as_workflow():
    stale_context = {
        "context_locked": True,
        "priority_workflow": (
            "control industrial machines directly"
        ),
        "priority_workflows": [
            "control industrial machines directly",
        ],
    }

    packet = extract(
        (
            "The software records operational events "
            "and supports shift handovers. "
            "The software does not directly control "
            "any industrial machine."
        ),
        project_context=stale_context,
    )

    workflows = joined(
        [
            workflow.sentence
            for workflow
            in packet.priority_workflows
        ]
    )

    assert not (
        "control industrial machines directly"
        in workflows
    )


# ============================================================
# G-R5 — CLARIFICATION SIDE FACTS OWN TRANSACTION SIDES
# ============================================================

def test_explicit_clarification_sides_materialize_two_sided_transaction():
    project_context = {
        "clarification_facts": {
            "supply_side": (
                "qualified service providers"
            ),
            "demand_side": (
                "customer operations teams"
            ),
        },
    }

    packet = extract(
        (
            "Customer operations teams publish a service request. "
            "Qualified service providers review requests "
            "and submit proposals. "
            "The customer selects a provider and confirms completion."
        ),
        project_context=project_context,
    )

    transaction = (
        packet.transaction_unit
    )

    assert (
        "qualified service providers"
        in comparison_key(
            transaction.supply_actor
        )
    )

    assert (
        "customer operations teams"
        in comparison_key(
            transaction.demand_actor
        )
    )

    assert (
        transaction.has_two_sides
        is True
    )


# Golden stale negative-determiner workflow authority.
#
# A legacy derived workflow cannot become positive canonical truth
# when its own action object explicitly means zero / none.
#
# This covers semantic morphology, not any project or industry.

def test_stale_negative_determiner_workflow_cannot_resurrect():
    cases = (
        (
            "fr",
            (
                "Le logiciel enregistre les ?v?nements op?rationnels. "
                "Le logiciel ne commande directement "
                "aucune machine industrielle."
            ),
            (
                "commander directement "
                "aucune machine industrielle"
            ),
            "aucune machine industrielle",
        ),
        (
            "en",
            (
                "The software records operational events. "
                "The software controls "
                "no industrial machine directly."
            ),
            (
                "control no industrial machine directly"
            ),
            "no industrial machine",
        ),
    )

    for (
        language,
        description,
        stale_workflow,
        forbidden_fragment,
    ) in cases:

        packet = extract(
            description,
            language=language,
            project_context={
                "context_locked": True,
                "priority_workflow":
                    stale_workflow,
                "priority_workflows": [
                    stale_workflow,
                ],
            },
        )

        workflow_text = joined(
            [
                workflow.sentence
                for workflow
                in packet.priority_workflows
            ]
        )

        assert (
            comparison_key(
                forbidden_fragment
            )
            not in workflow_text
        ), {
            "language": language,
            "stale_workflow": stale_workflow,
            "actual_workflows": [
                workflow.model_dump(
                    mode="json"
                )
                for workflow
                in packet.priority_workflows
            ],
        }
