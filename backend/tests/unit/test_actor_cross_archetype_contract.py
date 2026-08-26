from app.schemas.analysis_context import (
    ActorRole,
)
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


DEMAND_ROLES = {
    ActorRole.USER,
    ActorRole.OPERATOR,
    ActorRole.BUYER,
    ActorRole.BENEFICIARY,
}


def _packet(
    *,
    title: str,
    description: str,
    industry: str,
    region: str,
):
    return project_context_extractor.extract(
        title=title,
        description=description,
        industry=industry,
        target_region=region,
        output_language="en",
    )


def _actors(
    description: str,
    *,
    title: str = "Actor Contract",
    industry: str = "Software / Services",
    region: str = "Europe",
):
    return list(
        _packet(
            title=title,
            description=description,
            industry=industry,
            region=region,
        ).actors
    )


def _names_for_roles(
    actors,
    roles,
):
    return {
        comparison_key(
            actor.name
        )
        for actor in actors
        if actor.role in roles
    }


def _has_actor(
    actors,
    *,
    name: str,
    roles,
) -> bool:
    expected = comparison_key(
        name
    )

    return expected in _names_for_roles(
        actors,
        set(
            roles
        ),
    )


def test_inverse_primary_user_declaration_materializes_user() -> None:
    actors = _actors(
        (
            "StockOps is an internal warehouse application. "
            "Warehouse operators are the primary users."
        ),
        title="StockOps",
        industry="Internal Enterprise Software",
        region="Germany",
    )

    assert _has_actor(
        actors,
        name="warehouse operators",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_operational_subject_using_product_materializes_user() -> None:
    actors = _actors(
        (
            "GreenSense is an IoT monitoring device. "
            "The farm manager uses the device and dashboard "
            "to monitor greenhouse conditions."
        ),
        title="GreenSense",
        industry="AgriTech / IoT Hardware",
        region="Tunisia",
    )

    assert _has_actor(
        actors,
        name="farm manager",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_operational_reviewer_materializes_internal_user() -> None:
    actors = _actors(
        (
            "StockOps is an internal warehouse application. "
            "A warehouse supervisor reviews discrepancies "
            "and validates inventory corrections."
        ),
        title="StockOps",
        industry="Internal Enterprise Software",
        region="Germany",
    )

    assert _has_actor(
        actors,
        name="warehouse supervisor",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_professional_service_requester_materializes_demand_actor() -> None:
    actors = _actors(
        (
            "MaintPro provides preventive maintenance services. "
            "The hotel facility manager requests a maintenance visit."
        ),
        title="MaintPro",
        industry="B2B Professional Services / Maintenance",
        region="Italy",
    )

    assert _has_actor(
        actors,
        name="hotel facility manager",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_professional_service_executor_materializes_provider_without_marketplace() -> None:
    actors = _actors(
        (
            "MaintPro provides preventive maintenance services. "
            "A MaintPro technician performs the inspection "
            "and maintenance work."
        ),
        title="MaintPro",
        industry="B2B Professional Services / Maintenance",
        region="Italy",
    )

    assert _has_actor(
        actors,
        name="MaintPro technician",
        roles={
            ActorRole.PROVIDER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_modal_payment_relation_keeps_only_actor_subject() -> None:
    actors = _actors(
        (
            "MealMate is a subscription application. "
            "The household user can choose to pay "
            "for a monthly premium subscription."
        ),
        title="MealMate",
        industry="Consumer Mobile App",
        region="United Kingdom",
    )

    assert _has_actor(
        actors,
        name="household user",
        roles={
            ActorRole.PAYER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]

    assert all(
        comparison_key(
            actor.name
        )
        != comparison_key(
            "household user can choose to"
        )
        for actor in actors
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_purchase_decision_phrase_materializes_decision_maker() -> None:
    actors = _actors(
        (
            "GreenSense is an IoT monitoring device. "
            "The farm owner is the main purchasing decision maker "
            "and authorizes the equipment purchase."
        ),
        title="GreenSense",
        industry="AgriTech / IoT Hardware",
        region="Tunisia",
    )

    assert _has_actor(
        actors,
        name="farm owner",
        roles={
            ActorRole.DECISION_MAKER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_direct_decision_maker_relation_remains_supported() -> None:
    actors = _actors(
        (
            "The plant director is the main decision maker "
            "for purchasing and deploying the software."
        ),
        title="ShiftFlow",
        industry="B2B SaaS",
        region="France",
    )

    assert _has_actor(
        actors,
        name="plant director",
        roles={
            ActorRole.DECISION_MAKER,
        },
    )


def test_direct_payment_relation_remains_supported() -> None:
    actors = _actors(
        (
            "The manufacturing company pays "
            "a monthly subscription for the software."
        ),
        title="ShiftFlow",
        industry="B2B SaaS",
        region="France",
    )

    assert _has_actor(
        actors,
        name="manufacturing company",
        roles={
            ActorRole.PAYER,
        },
    )


def test_product_subject_is_not_materialized_as_human_actor() -> None:
    actors = _actors(
        (
            "GreenSense is an IoT monitoring device. "
            "The device measures temperature and humidity "
            "and sends readings to the dashboard."
        ),
        title="GreenSense",
        industry="AgriTech / IoT Hardware",
        region="Tunisia",
    )

    actor_keys = {
        comparison_key(
            actor.name
        )
        for actor in actors
    }

    assert comparison_key(
        "device"
    ) not in actor_keys


def test_cross_archetype_packets_do_not_materialize_pronoun_actors() -> None:
    descriptions = (
        (
            "MealMate is a subscription application. "
            "The household user creates a meal plan. "
            "They can pay for a premium subscription."
        ),
        (
            "GreenSense is an IoT monitoring device. "
            "The farm manager uses the dashboard. "
            "They receive alerts."
        ),
        (
            "MaintPro provides maintenance services. "
            "The hotel facility manager requests a visit. "
            "They confirm completion."
        ),
    )

    pronouns = {
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "je",
        "tu",
        "il",
        "elle",
        "on",
        "nous",
        "vous",
        "ils",
        "elles",
    }

    for description in descriptions:
        actors = _actors(
            description
        )

        actor_keys = {
            comparison_key(
                actor.name
            )
            for actor in actors
        }

        assert not (
            actor_keys
            & pronouns
        ), [
            actor.model_dump(
                mode="json"
            )
            for actor in actors
        ]


def test_full_iot_packet_preserves_user_and_decision_authorities() -> None:
    packet = _packet(
        title="GreenSense",
        description=(
            "GreenSense is an IoT monitoring device for greenhouse farms. "
            "Farm managers currently inspect conditions manually. "
            "The farm manager uses the device and dashboard "
            "to monitor greenhouse conditions. "
            "The farm purchases the monitoring device. "
            "The farm owner is the main purchasing decision maker "
            "and authorizes the equipment purchase."
        ),
        industry="AgriTech / IoT Hardware",
        region="Tunisia",
    )

    actors = list(
        packet.actors
    )

    assert _has_actor(
        actors,
        name="farm manager",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]

    assert _has_actor(
        actors,
        name="farm owner",
        roles={
            ActorRole.DECISION_MAKER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_full_professional_service_packet_preserves_client_provider_and_payer() -> None:
    packet = _packet(
        title="MaintPro",
        description=(
            "MaintPro provides preventive maintenance services to hotels. "
            "Hotels often experience unexpected equipment breakdowns. "
            "The hotel facility manager requests a maintenance visit. "
            "A MaintPro technician performs the inspection and maintenance work. "
            "The hotel confirms completion of the visit. "
            "The hotel pays MaintPro for the maintenance service. "
            "The hotel general manager is the main decision maker "
            "for approving the maintenance contract."
        ),
        industry="B2B Professional Services / Maintenance",
        region="Italy",
    )

    actors = list(
        packet.actors
    )

    assert _has_actor(
        actors,
        name="hotel facility manager",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]

    assert _has_actor(
        actors,
        name="MaintPro technician",
        roles={
            ActorRole.PROVIDER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]

    assert _has_actor(
        actors,
        name="hotel",
        roles={
            ActorRole.PAYER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]



def test_actor_first_singular_primary_user_declaration() -> None:
    actors = _actors(
        (
            "StockOps is an internal warehouse application. "
            "The warehouse supervisor is the primary user."
        ),
        title="StockOps",
        industry="Internal Enterprise Software",
        region="Germany",
    )

    assert _has_actor(
        actors,
        name="warehouse supervisor",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_actor_first_key_user_declaration_materializes_user() -> None:
    actors = _actors(
        (
            "ReviewDesk is an internal workflow tool. "
            "Quality reviewers are the key users."
        ),
        title="ReviewDesk",
        industry="Internal Enterprise Software",
        region="France",
    )

    assert _has_actor(
        actors,
        name="quality reviewers",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_actor_first_french_primary_user_declaration_materializes_user() -> None:
    actors = _actors(
        (
            "StockOps est une application interne. "
            "Les operateurs logistiques sont les utilisateurs principaux."
        ),
        title="StockOps",
        industry="Internal Enterprise Software",
        region="France",
    )

    assert _has_actor(
        actors,
        name="operateurs logistiques",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_ordinary_are_predicate_is_not_primary_user_declaration() -> None:
    actors = _actors(
        (
            "Warehouse operators are responsible "
            "for physical inventory counts."
        ),
        title="StockOps",
        industry="Internal Enterprise Software",
        region="Germany",
    )

    actor_names = {
        comparison_key(
            actor.name
        )
        for actor in actors
    }

    assert comparison_key(
        "warehouse operators"
    ) not in actor_names



def test_generic_operational_subject_materializes_user() -> None:
    actors = _actors(
        (
            "The operations coordinator uses the dashboard "
            "to review daily activity."
        ),
    )

    assert _has_actor(
        actors,
        name="operations coordinator",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_generic_requester_materializes_user() -> None:
    actors = _actors(
        (
            "The service coordinator requests an intervention."
        ),
    )

    assert _has_actor(
        actors,
        name="service coordinator",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_generic_reviewer_materializes_user() -> None:
    actors = _actors(
        (
            "A quality supervisor reviews exceptions "
            "and validates corrections."
        ),
    )

    assert _has_actor(
        actors,
        name="quality supervisor",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_french_operational_subject_materializes_user() -> None:
    actors = _actors(
        (
            "Le responsable operationnel utilise le tableau de bord "
            "et examine les anomalies."
        ),
    )

    assert _has_actor(
        actors,
        name="responsable operationnel",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_product_using_data_does_not_become_user_actor() -> None:
    actors = _actors(
        (
            "The device uses sensor data to calculate temperature."
        ),
    )

    actor_names = {
        comparison_key(
            actor.name
        )
        for actor in actors
    }

    assert comparison_key(
        "device"
    ) not in actor_names


def test_platform_requesting_token_does_not_become_user_actor() -> None:
    actors = _actors(
        (
            "The platform requests an API token automatically."
        ),
    )

    actor_names = {
        comparison_key(
            actor.name
        )
        for actor in actors
    }

    assert comparison_key(
        "platform"
    ) not in actor_names


def test_system_reviewing_records_does_not_become_user_actor() -> None:
    actors = _actors(
        (
            "The system reviews records automatically."
        ),
    )

    actor_names = {
        comparison_key(
            actor.name
        )
        for actor in actors
    }

    assert comparison_key(
        "system"
    ) not in actor_names



def test_french_supervisor_operational_subject_materializes_user() -> None:
    actors = _actors(
        (
            "Le superviseur qualite examine les anomalies "
            "et valide les corrections."
        ),
    )

    assert _has_actor(
        actors,
        name="superviseur qualite",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_french_coordinator_requester_materializes_user() -> None:
    actors = _actors(
        (
            "Le coordinateur de service demande une intervention."
        ),
    )

    assert _has_actor(
        actors,
        name="coordinateur de service",
        roles=DEMAND_ROLES,
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]



def test_generic_non_marketplace_service_executor_is_provider() -> None:
    actors = _actors(
        (
            "A field technician performs the requested service."
        ),
        title="Service Contract",
        industry="Professional Services",
        region="Europe",
    )

    assert _has_actor(
        actors,
        name="field technician",
        roles={
            ActorRole.PROVIDER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_modified_execution_object_still_materializes_provider() -> None:
    actors = _actors(
        (
            "A technician performs the inspection "
            "and maintenance work."
        ),
        title="Service Contract",
        industry="Professional Services",
        region="Europe",
    )

    assert _has_actor(
        actors,
        name="technician",
        roles={
            ActorRole.PROVIDER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_french_non_marketplace_service_executor_is_provider() -> None:
    actors = _actors(
        (
            "Le technicien realise l'inspection "
            "et les travaux de maintenance."
        ),
        title="Service Contract",
        industry="Professional Services",
        region="France",
    )

    assert _has_actor(
        actors,
        name="technicien",
        roles={
            ActorRole.PROVIDER,
        },
    ), [
        actor.model_dump(
            mode="json"
        )
        for actor in actors
    ]


def test_technical_execution_subjects_do_not_become_provider() -> None:
    descriptions = (
        "The platform performs the matching service.",
        "The system executes the processing work.",
        "The device performs the measurement work.",
    )

    forbidden = {
        "platform",
        "system",
        "device",
    }

    for description in descriptions:
        actors = _actors(
            description,
            title="Technical Control",
            industry="Software / Hardware",
            region="Europe",
        )

        provider_names = {
            comparison_key(
                actor.name
            )
            for actor in actors
            if actor.role == ActorRole.PROVIDER
        }

        assert not (
            provider_names
            & forbidden
        ), [
            actor.model_dump(
                mode="json"
            )
            for actor in actors
        ]
