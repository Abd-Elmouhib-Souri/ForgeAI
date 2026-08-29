from __future__ import annotations

import json
from copy import deepcopy

import pytest

from app.agents.product_owner_agent import (
    ProductOwnerAgent,
    ProductOwnerGenerationError,
)
from app.schemas.analysis_context import (
    ActorContext,
    ActorRole,
    ProjectContextPacketV3,
    WorkflowContext,
)
from app.schemas.project_management import (
    CandidateBacklogV1,
    ProjectManagementContextV1,
)
from app.services.project_management_context_builder import (
    project_management_context_builder,
)


class FakeLLM:
    def __init__(
        self,
        *,
        response=None,
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls = []

    async def invoke(
        self,
        prompt: str,
        task_type: str = "general",
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "task_type": task_type,
            }
        )

        if self.error is not None:
            raise self.error

        return self.response


def make_context(
    *,
    project_id: str,
    project_name: str,
    language: str,
    target_region: str,
    industry: str,
    actor_name: str,
    decision_maker_name: str,
    workflow_name: str,
    action: str,
    object_name: str,
    result: str,
    mvp_scope: str,
    exclusion: str,
) -> ProjectManagementContextV1:

    packet = ProjectContextPacketV3(
        project_name=project_name,

        language=language,

        target_region=target_region,

        industry_user_input=industry,

        actors=[
            ActorContext(
                name=actor_name,
                role=ActorRole.USER,
                is_explicit=True,
            ),
            ActorContext(
                name=decision_maker_name,
                role=ActorRole.DECISION_MAKER,
                is_explicit=True,
            ),
        ],

        priority_workflows=[
            WorkflowContext(
                name=workflow_name,
                actor=actor_name,
                action=action,
                object=object_name,
                result=result,
                is_explicit=True,
                confidence=1.0,
            ),
        ],

        mvp_scope=[
            mvp_scope,
        ],

        scope_exclusions=[
            exclusion,
        ],
    )

    return (
        project_management_context_builder.build(
            packet=packet,
            project_id=project_id,
            decision=None,
        )
    )


def make_payload(
    context: ProjectManagementContextV1,
    *,
    actor_name: str,
    workflow_name: str,
    mvp_scope: str,
    title: str,
) -> dict:

    return {
        "schema_version":
            "candidate_backlog_v1",

        "source_context_hash":
            context.source_context_hash,

        "context_hash":
            context.context_hash,

        "epics": [
            {
                "candidate_key":
                    "epic_core",

                "title":
                    "Core workflow",

                "description":
                    "Support the validated core workflow.",

                "business_goal":
                    "Deliver the validated operational outcome.",

                "provenance_refs": [
                    f"workflow:{workflow_name}",
                ],
            },
        ],

        "features": [
            {
                "candidate_key":
                    "feature_core",

                "epic_key":
                    "epic_core",

                "title":
                    title,

                "description":
                    "Implement the validated MVP capability.",

                "business_value":
                    "Support the explicit project workflow.",

                "provenance_refs": [
                    f"mvp_scope:{mvp_scope}",
                ],
            },
        ],

        "stories": [
            {
                "candidate_key":
                    "story_core",

                "epic_key":
                    "epic_core",

                "feature_key":
                    "feature_core",

                "actor_ref":
                    actor_name,

                "title":
                    title,

                "capability":
                    title,

                "benefit":
                    "complete the validated workflow",

                "story":
                    (
                        f"As {actor_name}, I want to "
                        f"{title.lower()} so that the "
                        "validated workflow can be completed."
                    ),

                "business_value":
                    "Support the validated operational objective.",

                "acceptance_criteria": [
                    {
                        "statement":
                            (
                                "Given the validated workflow, "
                                "when the actor performs the "
                                "capability, then the expected "
                                "result is recorded."
                            ),

                        "candidate_testable":
                            True,

                        "source_ref":
                            f"workflow:{workflow_name}",
                    },
                ],

                "candidate_priority":
                    "must",

                "candidate_priority_rationale":
                    (
                        "The capability belongs to the "
                        "explicit MVP workflow."
                    ),

                "candidate_complexity":
                    "medium",

                "candidate_complexity_rationale":
                    (
                        "The candidate requires controlled "
                        "workflow state handling."
                    ),

                "candidate_complexity_factors": {
                    'business_logic': 'unknown',
                    'integration_complexity': 'unknown',
                    'data_complexity': 'unknown',
                    'ui_complexity': 'unknown',
                    'security': 'unknown',
                    'external_dependency': 'unknown',
                    'uncertainty': 'unknown',
                    'testing_burden': 'unknown',
                    'regulatory_risk': 'unknown',
                    'hardware_dependency': 'unknown',
                },
                "candidate_dependencies":
                    [],

                "provenance_refs": [
                    f"actor:{actor_name}",
                    f"workflow:{workflow_name}",
                    f"mvp_scope:{mvp_scope}",
                ],

                "source_context_hash":
                    context.source_context_hash,

                "warnings":
                    [],
            },
        ],

        "warnings":
            [],
    }


def payload_json(
    context,
    *,
    actor_name,
    workflow_name,
    mvp_scope,
    title,
):
    return json.dumps(
        make_payload(
            context,
            actor_name=actor_name,
            workflow_name=workflow_name,
            mvp_scope=mvp_scope,
            title=title,
        ),
        ensure_ascii=False,
    )


def scenarios():

    return [
        {
            "project_id":
                "universal-logistics",

            "project_name":
                "Dock Coordination",

            "language":
                "en",

            "target_region":
                "Egypt",

            "industry":
                "Warehouse operations",

            "actor_name":
                "Dock Coordinator",

            "decision_maker_name":
                "Operations Director",

            "workflow_name":
                "dock_request_review",

            "action":
                "review",

            "object_name":
                "truck appointment request",

            "result":
                "dock appointment confirmed",

            "mvp_scope":
                "Truck appointment review",

            "exclusion":
                "Automatic freight payments",

            "title":
                "Review truck appointment request",
        },

        {
            "project_id":
                "universal-iot",

            "project_name":
                "Equipment Monitoring",

            "language":
                "en",

            "target_region":
                "Germany",

            "industry":
                "Industrial IoT",

            "actor_name":
                "Maintenance Technician",

            "decision_maker_name":
                "Plant Manager",

            "workflow_name":
                "equipment_alert_review",

            "action":
                "review",

            "object_name":
                "equipment alert",

            "result":
                "maintenance action recorded",

            "mvp_scope":
                "Equipment alert review",

            "exclusion":
                "Autonomous machinery shutdown",

            "title":
                "Review equipment alert",
        },

        {
            "project_id":
                "universal-internal",

            "project_name":
                "Internal Approval Flow",

            "language":
                "en",

            "target_region":
                "United Kingdom",

            "industry":
                "Internal operations",

            "actor_name":
                "Operations Analyst",

            "decision_maker_name":
                "Department Manager",

            "workflow_name":
                "request_approval",

            "action":
                "review",

            "object_name":
                "internal request",

            "result":
                "approval decision recorded",

            "mvp_scope":
                "Internal request approval",

            "exclusion":
                "Public marketplace listings",

            "title":
                "Review internal request",
        },

        {
            "project_id":
                "universal-service-fr",

            "project_name":
                "Coordination Service",

            "language":
                "fr",

            "target_region":
                "Tunisie",

            "industry":
                "Coordination de services",

            "actor_name":
                "Coordinateur",

            "decision_maker_name":
                "Responsable des opérations",

            "workflow_name":
                "validation_demande",

            "action":
                "valider",

            "object_name":
                "demande de service",

            "result":
                "décision enregistrée",

            "mvp_scope":
                "Validation des demandes de service",

            "exclusion":
                "Paiement automatique",

            "title":
                "Valider une demande de service",
        },
    ]


def build_scenario(
    scenario,
):

    context = make_context(
        **{
            key: scenario[key]
            for key in (
                "project_id",
                "project_name",
                "language",
                "target_region",
                "industry",
                "actor_name",
                "decision_maker_name",
                "workflow_name",
                "action",
                "object_name",
                "result",
                "mvp_scope",
                "exclusion",
            )
        }
    )

    response = payload_json(
        context,
        actor_name=scenario[
            "actor_name"
        ],
        workflow_name=scenario[
            "workflow_name"
        ],
        mvp_scope=scenario[
            "mvp_scope"
        ],
        title=scenario[
            "title"
        ],
    )

    return context, response


# ============================================================
# CROSS-DOMAIN
# ============================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    scenarios(),
)
async def test_product_owner_accepts_valid_candidates_across_domains(
    scenario,
) -> None:

    context, response = build_scenario(
        scenario
    )

    provider = FakeLLM(
        response=response
    )

    result = await ProductOwnerAgent(
        llm=provider
    ).generate_candidate_backlog(
        context=context
    )

    assert isinstance(
        result,
        CandidateBacklogV1,
    )

    assert (
        result.source_context_hash
        ==
        context.source_context_hash
    )

    assert (
        result.context_hash
        ==
        context.context_hash
    )

    assert len(
        provider.calls
    ) == 1

    assert (
        provider.calls[0][
            "task_type"
        ]
        ==
        "product_owner_candidate_backlog"
    )


# ============================================================
# LANGUAGE / REGION / NEGATIVE SCOPE
# ============================================================


def test_french_context_is_preserved_in_prompt() -> None:

    scenario = scenarios()[3]

    context, _ = build_scenario(
        scenario
    )

    prompt = ProductOwnerAgent().build_prompt(
        context=context
    )

    assert "Tunisie" in prompt
    assert "fr" in prompt

    assert (
        "Validation des demandes de service"
        in prompt
    )

    assert (
        "Paiement automatique"
        in prompt
    )

    assert (
        context.source_context_hash
        in prompt
    )

    assert (
        context.context_hash
        in prompt
    )


# ============================================================
# DETERMINISM
# ============================================================


def test_equivalent_reconstructed_context_has_identical_prompt() -> None:

    scenario = scenarios()[0]

    context, _ = build_scenario(
        scenario
    )

    reconstructed = (
        ProjectManagementContextV1.model_validate(
            context.model_dump(
                mode="python"
            )
        )
    )

    agent = ProductOwnerAgent()

    assert (
        agent.build_prompt(
            context=context
        )
        ==
        agent.build_prompt(
            context=reconstructed
        )
    )


@pytest.mark.asyncio
async def test_same_context_same_candidate_is_deterministic() -> None:

    scenario = scenarios()[1]

    context, response = build_scenario(
        scenario
    )

    first = await ProductOwnerAgent(
        llm=FakeLLM(
            response=response
        )
    ).generate_candidate_backlog(
        context=context
    )

    second = await ProductOwnerAgent(
        llm=FakeLLM(
            response=response
        )
    ).generate_candidate_backlog(
        context=context
    )

    assert (
        first.model_dump(
            mode="json"
        )
        ==
        second.model_dump(
            mode="json"
        )
    )


# ============================================================
# METAMORPHIC HASH / STALE CANDIDATE
# ============================================================


@pytest.mark.asyncio
async def test_real_scope_change_rejects_old_candidate() -> None:

    scenario = scenarios()[0]

    old_context, old_response = (
        build_scenario(
            scenario
        )
    )

    changed = deepcopy(
        scenario
    )

    changed[
        "mvp_scope"
    ] = (
        "Truck appointment review "
        "and manual exception handling"
    )

    new_context, _ = build_scenario(
        changed
    )

    assert (
        old_context.source_context_hash
        !=
        new_context.source_context_hash
    )

    assert (
        old_context.context_hash
        !=
        new_context.context_hash
    )

    with pytest.raises(
        ProductOwnerGenerationError
    ) as exc_info:

        await ProductOwnerAgent(
            llm=FakeLLM(
                response=old_response
            )
        ).generate_candidate_backlog(
            context=new_context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_project_id_change_preserves_source_hash_but_invalidates_candidate_context_hash() -> None:

    scenario = scenarios()[2]

    old_context, old_response = (
        build_scenario(
            scenario
        )
    )

    changed = deepcopy(
        scenario
    )

    changed[
        "project_id"
    ] = (
        "universal-internal-copy"
    )

    new_context, _ = build_scenario(
        changed
    )

    assert (
        old_context.source_context_hash
        ==
        new_context.source_context_hash
    )

    assert (
        old_context.context_hash
        !=
        new_context.context_hash
    )

    with pytest.raises(
        ProductOwnerGenerationError
    ) as exc_info:

        await ProductOwnerAgent(
            llm=FakeLLM(
                response=old_response
            )
        ).generate_candidate_backlog(
            context=new_context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


# ============================================================
# UNIVERSAL NEGATIVE AUTHORITY
# ============================================================


@pytest.mark.asyncio
async def test_exclusion_cannot_gain_positive_authority_in_another_domain() -> None:

    scenario = scenarios()[1]

    context, _ = build_scenario(
        scenario
    )

    payload = make_payload(
        context,
        actor_name=scenario[
            "actor_name"
        ],
        workflow_name=scenario[
            "workflow_name"
        ],
        mvp_scope=scenario[
            "mvp_scope"
        ],
        title=scenario[
            "title"
        ],
    )

    payload[
        "stories"
    ][0][
        "provenance_refs"
    ] = [
        (
            "scope_exclusion:"
            +
            scenario[
                "exclusion"
            ]
        )
    ]

    provider = FakeLLM(
        response=json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    with pytest.raises(
        ProductOwnerGenerationError
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "candidate_authority_rejected"
    )


@pytest.mark.asyncio
async def test_query_or_archetype_cannot_gain_planning_authority() -> None:

    scenario = scenarios()[2]

    context, _ = build_scenario(
        scenario
    )

    for bad_ref in (
        "query:employee scheduling software",
        "archetype:two_sided_marketplace",
    ):

        payload = make_payload(
            context,
            actor_name=scenario[
                "actor_name"
            ],
            workflow_name=scenario[
                "workflow_name"
            ],
            mvp_scope=scenario[
                "mvp_scope"
            ],
            title=scenario[
                "title"
            ],
        )

        payload[
            "stories"
        ][0][
            "provenance_refs"
        ] = [
            bad_ref
        ]

        provider = FakeLLM(
            response=json.dumps(
                payload,
                ensure_ascii=False,
            )
        )

        with pytest.raises(
            ProductOwnerGenerationError
        ) as exc_info:

            await ProductOwnerAgent(
                llm=provider
            ).generate_candidate_backlog(
                context=context
            )

        assert (
            exc_info.value.code
            ==
            "candidate_authority_rejected"
        )


# ============================================================
# PROVIDER FAILURE IS DOMAIN-AGNOSTIC
# ============================================================


@pytest.mark.asyncio
async def test_provider_failure_remains_fail_closed_for_iot_context() -> None:

    scenario = scenarios()[1]

    context, _ = build_scenario(
        scenario
    )

    provider = FakeLLM(
        error=TimeoutError(
            "provider timeout"
        )
    )

    with pytest.raises(
        ProductOwnerGenerationError
    ) as exc_info:

        await ProductOwnerAgent(
            llm=provider
        ).generate_candidate_backlog(
            context=context
        )

    assert (
        exc_info.value.code
        ==
        "generation_temporarily_unavailable"
    )


# ============================================================
# CONTEXT IMMUTABILITY ACROSS DOMAINS
# ============================================================


@pytest.mark.asyncio
async def test_generation_never_mutates_canonical_pm_context() -> None:

    for scenario in scenarios():

        context, response = build_scenario(
            scenario
        )

        before = context.model_dump(
            mode="json"
        )

        await ProductOwnerAgent(
            llm=FakeLLM(
                response=response
            )
        ).generate_candidate_backlog(
            context=context
        )

        assert (
            context.model_dump(
                mode="json"
            )
            ==
            before
        )