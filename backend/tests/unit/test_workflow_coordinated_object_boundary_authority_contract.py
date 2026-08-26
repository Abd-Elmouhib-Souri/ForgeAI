from __future__ import annotations

import inspect

from app.services.project_context_extractor import (
    ProjectContextExtractor,
    project_context_extractor,
)


def _raw_action_objects(
    sentence: str,
) -> list[tuple[str, str]]:
    output: list[
        tuple[str, str]
    ] = []

    occurrences = (
        project_context_extractor
        ._workflow_action_occurrences(
            sentence
        )
    )

    for item in occurrences:
        output.append(
            (
                item["action"],
                project_context_extractor
                ._action_object(
                    sentence,
                    item["match"],
                ),
            )
        )

    return output


def _packet_workflows(
    sentence: str,
) -> list[
    tuple[str, str, str]
]:
    packet = (
        project_context_extractor
        .extract(
            title=(
                "Coordinated Workflow Object "
                "Boundary Probe"
            ),
            description=sentence,
            industry="Generic Operations",
            target_region="Europe",
            output_language="en",
        )
    )

    return [
        (
            workflow.action,
            workflow.actor,
            workflow.object,
        )
        for workflow
        in packet.priority_workflows
    ]


def test_en_same_subject_second_action_closes_first_object() -> None:
    assert _raw_action_objects(
        (
            "The customer books a service "
            "and pays the fee."
        )
    ) == [
        (
            "r\u00e9server",
            "a service",
        ),
        (
            "payer",
            "the fee",
        ),
    ]


def test_en_new_subject_second_action_closes_first_object() -> None:
    assert _raw_action_objects(
        (
            "The customer books a service "
            "and the company pays the fee."
        )
    ) == [
        (
            "r\u00e9server",
            "a service",
        ),
        (
            "payer",
            "the fee",
        ),
    ]


def test_en_request_then_new_subject_approval_has_clean_objects() -> None:
    assert _raw_action_objects(
        (
            "The customer requests a service "
            "and the manager approves the request."
        )
    ) == [
        (
            "demander",
            "a service",
        ),
        (
            "approuver",
            "the request",
        ),
    ]


def test_fr_same_subject_second_action_closes_first_object() -> None:
    assert _raw_action_objects(
        (
            "Le client reserve un service "
            "et paie la facture."
        )
    ) == [
        (
            "r\u00e9server",
            "un service",
        ),
        (
            "payer",
            "la facture",
        ),
    ]


def test_fr_new_subject_second_action_closes_first_object() -> None:
    assert _raw_action_objects(
        (
            "Le client reserve un service "
            "et l'entreprise paie la facture."
        )
    ) == [
        (
            "r\u00e9server",
            "un service",
        ),
        (
            "payer",
            "la facture",
        ),
    ]


def test_fr_request_then_new_subject_approval_has_clean_objects() -> None:
    assert _raw_action_objects(
        (
            "Le client demande une intervention "
            "et le responsable approuve la demande."
        )
    ) == [
        (
            "demander",
            "une intervention",
        ),
        (
            "approuver",
            "la demande",
        ),
    ]


def test_en_then_sequence_closes_first_object() -> None:
    assert _raw_action_objects(
        (
            "The customer requests a service "
            "then pays the fee."
        )
    ) == [
        (
            "demander",
            "a service",
        ),
        (
            "payer",
            "the fee",
        ),
    ]


def test_fr_puis_sequence_closes_first_object() -> None:
    assert _raw_action_objects(
        (
            "Le client demande une intervention "
            "puis paie le service."
        )
    ) == [
        (
            "demander",
            "une intervention",
        ),
        (
            "payer",
            "le service",
        ),
    ]


def test_en_compound_object_is_preserved_without_second_action() -> None:
    assert _raw_action_objects(
        (
            "The customer books transport "
            "and accommodation."
        )
    ) == [
        (
            "r\u00e9server",
            "transport and accommodation",
        ),
    ]


def test_fr_compound_object_is_preserved_without_second_action() -> None:
    assert _raw_action_objects(
        (
            "Le client reserve le transport "
            "et l'hebergement."
        )
    ) == [
        (
            "r\u00e9server",
            "le transport et l'hebergement",
        ),
    ]


def test_packet_new_subject_coordination_has_clean_workflow_boundaries() -> None:
    assert _packet_workflows(
        (
            "The customer books a service "
            "and the company pays the fee."
        )
    ) == [
        (
            "book",
            "customer",
            "a service",
        ),
        (
            "pay",
            "company",
            "the fee",
        ),
    ]


def test_packet_french_new_subject_coordination_has_clean_boundaries() -> None:
    assert _packet_workflows(
        (
            "Le client reserve un service "
            "et l'entreprise paie la facture."
        )
    ) == [
        (
            "book",
            "client",
            "un service",
        ),
        (
            "pay",
            "entreprise",
            "la facture",
        ),
    ]


def test_object_boundary_reuses_workflow_action_authority() -> None:
    source = inspect.getsource(
        ProjectContextExtractor._action_object
    )

    assert (
        "_workflow_action_occurrences"
        in source
    )


def test_object_boundary_has_no_project_specific_rule() -> None:
    source = (
        inspect.getsource(
            ProjectContextExtractor._action_object
        )
        .lower()
    )

    forbidden = (
        "shiftflow",
        "mealmate",
        "stockops",
        "greensense",
        "maintpro",
        "repairlink",
        "greenhouse",
        "hotel",
    )

    assert all(
        token not in source
        for token in forbidden
    )
