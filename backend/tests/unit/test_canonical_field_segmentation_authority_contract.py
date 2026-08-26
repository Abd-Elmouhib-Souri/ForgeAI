from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    ProjectContextPacketV3,
)
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def extract(
    description: str,
    *,
    language: str = "en",
    industry: str = "B2B software",
    region: str = "Canada",
):
    return project_context_extractor.extract(
        title="UniversalSemanticProbe",
        description=description,
        industry=industry,
        target_region=region,
        output_language=language,
    )


def normalized(value) -> str:
    if isinstance(
        value,
        str,
    ):
        return comparison_key(
            value
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return comparison_key(
            " | ".join(
                str(item)
                for item
                in value
            )
        )

    return comparison_key(
        str(
            value
            or ""
        )
    )


def test_packet_schema_exposes_canonical_intelligence_requirements():
    """
    The readiness gate already treats these concepts as canonical
    requirements. The canonical packet therefore needs a structured
    home for them instead of relying only on raw-description markers.
    """

    required_fields = {
        "input_data",
        "output_decision",
        "human_oversight",
        "maintenance_model",
    }

    actual = set(
        ProjectContextPacketV3
        .model_fields
    )

    assert required_fields.issubset(
        actual
    ), {
        "missing":
            sorted(
                required_fields
                - actual
            ),
        "actual":
            sorted(
                actual
            ),
    }


def test_solution_field_stops_at_following_semantic_labels():
    packet = extract(
        (
            "Proposed solution: the platform centralizes service requests "
            "and detects records requiring action. "
            "Input data: record identifier, status, date and priority. "
            "Main outputs: alerts, prioritized records and a recommended action. "
            "Human oversight: an operations coordinator reviews every "
            "recommendation before execution. "
            "Priority workflow: an employee creates a record, the platform "
            "evaluates it and the coordinator approves the next action. "
            "Business model: monthly SaaS subscription. "
            "Payment: the client company pays the subscription. "
            "Deployment environment: cloud web application used from "
            "the client's offices. "
            "Business hypothesis: the customer pays if the time saving "
            "is demonstrated."
        )
    )

    mechanism = normalized(
        packet.solution.mechanism
    )

    forbidden = (
        "input data",
        "main outputs",
        "human oversight",
        "priority workflow",
        "business model",
        "payment",
        "deployment environment",
        "business hypothesis",
    )

    for marker in forbidden:
        assert (
            marker
            not in mechanism
        ), packet.solution.mechanism


def test_deployment_field_does_not_absorb_business_hypothesis():
    packet = extract(
        (
            "Deployment environment: cloud web application used from "
            "the client's offices. "
            "Business hypothesis: customers will subscribe if the "
            "operational benefit is demonstrated."
        )
    )

    deployment = normalized(
        packet.deployment_environment
    )

    assert (
        "business hypothesis"
        not in deployment
    ), packet.deployment_environment


@pytest.mark.parametrize(
    (
        "description",
        "industry",
        "region",
    ),
    [
        (
            (
                "EventLink is a B2B marketplace for event organizers "
                "that need qualified audiovisual providers. "
                "Organizers publish a service request with the event date, "
                "location and technical requirements. "
                "Verified providers review requests and submit an offer "
                "with a price and delivery schedule. "
                "The organizer compares offers, selects a provider, follows "
                "service preparation and confirms completion. "
                "The client company pays for the service and EventLink takes "
                "a commission on each completed transaction. "
                "The MVP includes request publication, provider matching, "
                "offers, acceptance, service tracking, ratings and disputes."
            ),
            "Marketplace B2B / Event services",
            "Belgium",
        ),
        (
            (
                "CalibMatch is a B2B marketplace for laboratories that need "
                "qualified calibration providers. "
                "Laboratories publish a calibration request describing the "
                "equipment, required standard and deadline. "
                "Approved providers submit quotations and available slots. "
                "The laboratory compares proposals, selects a provider, "
                "tracks the service and confirms completion. "
                "The customer pays the calibration invoice and CalibMatch "
                "charges a commission per completed transaction. "
                "The MVP supports requests, matching, quotations, acceptance, "
                "tracking, provider ratings and dispute handling."
            ),
            "Marketplace B2B / Laboratory services",
            "Canada",
        ),
    ],
)
def test_marketplace_operational_mechanism_outranks_revenue_sentence(
    description,
    industry,
    region,
):
    packet = extract(
        description,
        language="en",
        industry=industry,
        region=region,
    )

    mechanism = normalized(
        packet.solution.mechanism
    )

    revenue_markers = (
        "commission",
        "pays",
        "payment",
        "invoice",
        "charges",
        "subscription",
        "pricing",
    )

    operational_markers = (
        "marketplace",
        "request",
        "provider",
        "matching",
        "offer",
        "quotation",
        "service",
        "tracking",
    )

    revenue_only = (
        any(
            marker in mechanism
            for marker
            in revenue_markers
        )
        and not any(
            marker in mechanism
            for marker
            in operational_markers
        )
    )

    assert not revenue_only, (
        packet.solution.mechanism
    )


# U7-A canonical requirement materialization authority.
#
# Merely adding field names to ProjectContextPacketV3 is not enough.
# Explicit project facts must be materialized into those fields and
# consumed by the canonical readiness gate.

from app.schemas.analysis_context import (
    ProjectContextPacketV3,
)
from app.services.context_confidence_gate import (
    ContextConfidenceGate,
)


def _u7a_joined_text(value) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        raw = " | ".join(
            str(item)
            for item in value
            if str(item).strip()
        )
    else:
        raw = str(value)

    return comparison_key(
        raw
    )


@pytest.mark.parametrize(
    (
        "language",
        "description",
        "expected",
    ),
    [
        (
            "en",
            (
                "Proposed solution: the service analyzes operational records "
                "and recommends the next action. "
                "Input data: record identifier, current status, date and priority. "
                "Main outputs: risk score and recommended intervention. "
                "Human oversight: an operations supervisor validates the "
                "recommendation before execution. "
                "Maintenance model: the internal IT team maintains the service. "
                "Deployment environment: cloud web application used in offices."
            ),
            {
                "input_data": "record identifier",
                "output_decision": "risk score",
                "human_oversight": "operations supervisor",
                "maintenance_model": "internal it team",
            },
        ),
        (
            "fr",
            (
                "Solution propos\u00e9e : le service analyse les dossiers "
                "op\u00e9rationnels et recommande l'action suivante. "
                "Donn\u00e9es d'entr\u00e9e : identifiant du dossier, "
                "statut actuel, date et priorit\u00e9. "
                "Sorties principales : score de risque et intervention "
                "recommand\u00e9e. "
                "Contr\u00f4le humain : un superviseur des op\u00e9rations "
                "valide la recommandation avant ex\u00e9cution. "
                "Mod\u00e8le de maintenance : l'\u00e9quipe informatique "
                "interne maintient le service. "
                "Environnement de d\u00e9ploiement : application web cloud "
                "utilis\u00e9e dans les bureaux."
            ),
            {
                "input_data": "identifiant du dossier",
                "output_decision": "score de risque",
                "human_oversight": "superviseur des operations",
                "maintenance_model": "equipe informatique interne",
            },
        ),
    ],
)
def test_explicit_canonical_requirement_fields_are_materialized(
    language,
    description,
    expected,
):
    packet = extract(
        description,
        language=language,
    )

    payload = packet.model_dump(
        mode="json",
    )

    for field_name, expected_fragment in expected.items():
        assert (
            field_name
            in payload
        ), {
            "missing_field": field_name,
            "actual_fields": sorted(
                payload
            ),
        }

        actual = _u7a_joined_text(
            payload.get(
                field_name
            )
        )

        assert actual, {
            "field": field_name,
            "value": payload.get(
                field_name
            ),
        }

        assert (
            comparison_key(
                expected_fragment
            )
            in actual
        ), {
            "field": field_name,
            "expected_fragment": expected_fragment,
            "actual": payload.get(
                field_name
            ),
        }


def test_context_gate_consumes_canonical_requirement_fields():
    packet = ProjectContextPacketV3(
        input_data=[
            "operational record",
        ],
        output_decision=[
            "recommended next action",
        ],
        human_oversight=[
            "analyst validates every recommendation",
        ],
        maintenance_model=[
            "internal IT team maintains the service",
        ],
    )

    gate = ContextConfidenceGate()

    for requirement in (
        "input_data",
        "output_decision",
        "human_oversight",
        "maintenance_model",
    ):
        assert (
            gate._requirement_is_present(
                packet,
                requirement,
            )
            is True
        ), {
            "requirement": requirement,
            "packet": packet.model_dump(
                mode="json",
            ),
        }
