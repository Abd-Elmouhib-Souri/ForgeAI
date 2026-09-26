from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from app.agents.product_owner_agent import (
    ProductOwnerAgent,
    ProductOwnerGenerationError,
)
from app.agents.scrum_master_agent import (
    AIScrumMasterAgent,
    ScrumMasterGenerationError,
)
from app.schemas.analysis_context import ProjectContextPacketV3
from app.schemas.project_management import (
    BacklogLocksUpdateV1,
    CandidateBacklogV1,
    CanonicalBacklogV1,
    PlanningSettingsUpdateV1,
    PlanningSettingsV1,
    ProjectManagementMetricsV1,
    ProjectManagementPlanV1,
    SprintMetricV1,
    ScrumMasterAdviceV1,
)
from app.services.backlog_policy_engine import backlog_policy_engine
from app.services.dependency_graph_builder import (
    DependencyGraphBuilder,
    DependencyGraphV1,
)
from app.services.moscow_priority_policy import MoSCoWPriorityPolicy
from app.services.project_management_context_builder import (
    project_management_context_builder,
)
from app.services.project_management_decision_projector import (
    project_management_decision_projector,
)
from app.services.sprint_planning_engine import SprintPlanningEngine
from app.services.story_point_policy import StoryPointPolicy
from app.services.release_sizing_engine import ReleaseSizingEngine
from app.services.sprint_cadence_advisor import SprintCadenceAdvisor
from app.schemas.project_management import ReleasePlanningMetadataV1


class ProjectManagementPlanError(ValueError):
    """Typed, user-safe failure for project-manager orchestration."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ProjectManagementPlanService:
    """Orchestrates Sprint 4 authorities and durable plan revisions.

    The service intentionally has no hidden product-management policy.  It
    invokes the existing Product Owner, deterministic backlog policies,
    Scrum Master advisory agent and planner in their certified order.
    """

    _MAX_HISTORY = 12

    def __init__(self) -> None:
        self._priority_policy = MoSCoWPriorityPolicy()
        self._story_point_policy = StoryPointPolicy()
        self._dependency_builder = DependencyGraphBuilder()
        self._planner = SprintPlanningEngine()
        self._release_sizing = ReleaseSizingEngine(planner=self._planner)
        self._cadence_advisor = SprintCadenceAdvisor()

    @staticmethod
    def default_settings() -> PlanningSettingsV1:
        return PlanningSettingsV1(
            sprint_count_mode="auto",
            sprint_count=4,
            sprint_duration_mode="auto",
            sprint_duration_days=14,
            planned_velocity=20,
            team_size=3,
            capacity_adjustment=1.0,
            start_date=date.today().isoformat(),
            working_days=[0, 1, 2, 3, 4],
        )

    def settings_from_update(
        self,
        current: PlanningSettingsV1,
        update: PlanningSettingsUpdateV1,
    ) -> PlanningSettingsV1:
        payload = current.model_dump()

        update_payload = (
            update.model_dump(
                exclude_none=True
            )
        )

        # Count and duration are independently owned.
        #
        # Supplying an explicit value is a manual act unless the same
        # request explicitly gives the corresponding mode.
        if (
            "sprint_count"
            in update_payload
            and "sprint_count_mode"
            not in update_payload
        ):
            update_payload[
                "sprint_count_mode"
            ] = "manual"

        if (
            "sprint_duration_days"
            in update_payload
            and "sprint_duration_mode"
            not in update_payload
        ):
            update_payload[
                "sprint_duration_mode"
            ] = "manual"

        payload.update(
            update_payload
        )

        settings = (
            PlanningSettingsV1
            .model_validate(
                payload
            )
        )

        self._validate_settings(
            settings
        )

        return settings

    async def generate(
        self,
        *,
        project_id: int,
        analysis_data: Mapping[str, Any] | None,
        settings: PlanningSettingsV1 | None = None,
        revision: int = 1,
    ) -> ProjectManagementPlanV1:
        """Generate a fresh plan from the authoritative Sprint 3 packet."""
        context = self._build_context(
            project_id=project_id,
            analysis_data=analysis_data,
        )
        effective_settings = settings or self.default_settings()
        self._validate_settings(effective_settings)

        # Results from optional auto authorities.
        # Manual modes intentionally leave provenance absent.
        cadence = None
        sizing = None

        try:
            candidate = await ProductOwnerAgent().generate_candidate_backlog(context)
        except ProductOwnerGenerationError as exc:
            recoverable_codes = {
                "generation_temporarily_unavailable",
                "invalid_model_response",
                "candidate_authority_rejected",
            }

            if exc.code not in recoverable_codes:
                raise
            # A free-tier outage must not make automatic Sprint 4 generation
            # depend on a human pressing a retry button.  This bounded,
            # provenance-linked candidate is intentionally conservative; the
            # deterministic policy engines still own canonical IDs, priority,
            # points, dependencies and sprint assignment.
            candidate = self._build_deterministic_candidate(context)
        canonical = backlog_policy_engine.canonicalize(context, candidate)
        priority_result = self._priority_policy.apply(context, canonical)
        prioritized = priority_result.backlog
        estimated = self._story_point_policy.apply(context, prioritized).backlog
        graph = self._dependency_builder.build(estimated).graph

        # Resolve one stable cadence for this release.
        #
        # Duration does not scale Story Point capacity; it is a planning
        # rhythm / validation-cycle decision only.
        if (
            effective_settings.sprint_duration_mode
            == "auto"
        ):

            cadence = self._cadence_advisor.recommend(
                context=context,
                backlog=estimated,
            )

            effective_settings = (
                effective_settings.model_copy(
                    update={
                        "sprint_duration_days":
                            cadence
                            .recommended_sprint_duration_days,
                    },
                    deep=True,
                )
            )

            self._validate_settings(
                effective_settings
            )


        # No explicit settings means automatic release sizing.
        #
        # The neutral advice object carries no recommendation.
        # SprintPlanningEngine remains the deterministic planning authority.
        if (
            effective_settings.sprint_count_mode
            == "auto"
        ):

            sizing_advice = ScrumMasterAdviceV1(
                source_context_hash=(
                    estimated.source_context_hash
                ),
                context_hash=(
                    estimated.context_hash
                ),
                recommendations=[],
                warnings=[],
            )

            sizing = self._release_sizing.size(
                backlog=estimated,
                dependency_graph=graph,
                base_settings=effective_settings,
                advice=sizing_advice,
            )

            effective_settings = (
                effective_settings.model_copy(
                    update={
                        "sprint_count":
                            sizing
                            .recommended_sprint_count,
                    },
                    deep=True,
                )
            )

            self._validate_settings(
                effective_settings
            )

        try:
            # Advice rationales follow the project language, like the
            # Product Owner stories and the deterministic fallback.
            advice = await AIScrumMasterAgent(
                output_language=context.language,
            ).generate_advice(
                estimated,
                graph,
                effective_settings,
            )
        except ScrumMasterGenerationError as exc:
            recoverable_advisory_errors = {
                "generation_temporarily_unavailable": "scrum_master_advice_temporarily_unavailable",
                "invalid_model_response": "scrum_master_advice_invalid_model_response",
                "advice_authority_rejected": "scrum_master_advice_authority_rejected",
            }

            advice_warning = recoverable_advisory_errors.get(exc.code)

            if advice_warning is None:
                raise

            # Scrum Master output is advisory only. Invalid or rejected
            # advice is discarded; deterministic authorities retain control.
            advice = ScrumMasterAdviceV1(
                source_context_hash=estimated.source_context_hash,
                context_hash=estimated.context_hash,
                recommendations=[],
                warnings=[advice_warning],
            )
        planning = self._planner.plan(
            estimated,
            graph,
            effective_settings,
            advice,
        )
        release_planning = (
            self._build_release_planning_metadata(
                settings=effective_settings,
                sizing=sizing,
                cadence=cadence,
            )
        )

        return self._assemble_plan(
            context=context,
            backlog=estimated,
            graph=graph,
            advice=advice,
            planning=planning,
            settings=effective_settings,
            revision=revision,
            release_planning=release_planning,
            extra_warnings=priority_result.warnings,
        )

    @staticmethod
    def _build_deterministic_candidate(
        context,
    ) -> CandidateBacklogV1:
        """
        Deterministic recovery candidate for provider outage.

        Explicit canonical MVP-scope entries are already bounded product
        commitments.  Without a separate semantic binding authority, this
        fallback must not invent a merge between independent commitments.

        This is intentionally limited to the deterministic outage path.
        The normal AI Product Owner and CandidateBacklogAuthority remain free
        to accept a coherent Story covering several commitments.
        """

        actor = (
            context.primary_user_actor_names[0]
            if context.primary_user_actor_names
            else (
                context.actors[0].name
                if context.actors
                else "Utilisateur"
            )
        )

        actor_ref = (
            f"actor:{actor}"
        )

        warning = (
            "product_owner_ai_unavailable_"
            "deterministic_fallback"
        )

        french = (
            context.language
            .casefold()
            .startswith("fr")
        )

        scope_items: list[str] = []

        for raw_value in context.mvp_scope:

            value = str(
                raw_value
            ).strip()

            if (
                value
                and value not in scope_items
            ):

                scope_items.append(
                    value
                )

        scope_refs = [
            f"mvp_scope:{value}"
            for value
            in scope_items
        ]


        # =====================================================================
        # EXPLICIT MVP COMMITMENTS
        # =====================================================================

        if scope_items:

            if french:

                epic_title = (
                    "Livraison du p\u00e9rim\u00e8tre MVP"
                )

                business_goal = (
                    "Pr\u00e9server les engagements MVP explicites "
                    "pendant l'indisponibilit\u00e9 du Product Owner IA."
                )

                business_value = (
                    "Conserver un backlog tra\u00e7able et exploitable "
                    "sans inventer de regroupement fonctionnel."
                )

                benefit = (
                    "valider progressivement la valeur du MVP"
                )

            else:

                epic_title = (
                    "Explicit MVP scope delivery"
                )

                business_goal = (
                    "Preserve explicit MVP commitments while the "
                    "AI Product Owner is unavailable."
                )

                business_value = (
                    "Keep the fallback backlog traceable and usable "
                    "without inventing functional grouping."
                )

                benefit = (
                    "validate MVP value incrementally"
                )


            workflow_ref = ""

            if context.priority_workflows:

                workflow_name = str(
                    context.priority_workflows[0]
                    .name
                    or ""
                ).strip()

                if workflow_name:

                    workflow_ref = (
                        f"workflow:{workflow_name}"
                    )


            epic_refs = list(
                dict.fromkeys(
                    [
                        *(
                            [workflow_ref]
                            if workflow_ref
                            else []
                        ),
                        *scope_refs,
                    ]
                )
            )


            features = []
            stories = []


            for index, (
                scope_value,
                scope_ref,
            ) in enumerate(
                zip(
                    scope_items,
                    scope_refs,
                ),
                start=1,
            ):

                feature_key = (
                    f"feature_mvp_{index:03d}"
                )

                story_key = (
                    f"story_mvp_{index:03d}"
                )


                if french:

                    capability = (
                        "r\u00e9aliser l'engagement du "
                        "p\u00e9rim\u00e8tre MVP "
                        f"\u00ab {scope_value} \u00bb"
                    )

                    story_text = (
                        f"En tant que {actor}, "
                        f"je veux {capability} "
                        f"afin de {benefit}."
                    )

                    # Preserve all historical localized Unicode guarantees:
                    # r?aliser / p?rim?tre / ?tant donn? / r?sultat /
                    # enregistr? / tra?able / r?alis? / ? / ?.
                    criterion = (
                        "\u00c9tant donn\u00e9 l'engagement MVP explicite "
                        f"\u00ab {scope_value} \u00bb, "
                        "lorsque l'engagement est "
                        f"r\u00e9alis\u00e9 par {actor}, "
                        "alors le r\u00e9sultat correspondant "
                        "est enregistr\u00e9 et tra\u00e7able."
                    )

                else:

                    capability = (
                        "deliver the explicit MVP scope commitment "
                        f"'{scope_value}'"
                    )

                    story_text = (
                        f"As a {actor}, "
                        f"I want to {capability} "
                        f"so that I can {benefit}."
                    )

                    criterion = (
                        "Given the explicit MVP scope commitment "
                        f"'{scope_value}', "
                        f"when it is completed by {actor}, "
                        "then the corresponding outcome is "
                        "recorded and traceable."
                    )


                features.append(
                    {
                        "candidate_key":
                            feature_key,

                        "epic_key":
                            "epic_mvp",

                        "title":
                            scope_value,

                        "description":
                            capability,

                        "business_value":
                            business_value,

                        "provenance_refs": [
                            scope_ref,
                        ],
                    }
                )


                stories.append(
                    {
                        "candidate_key":
                            story_key,

                        "epic_key":
                            "epic_mvp",

                        "feature_key":
                            feature_key,

                        "actor_ref":
                            actor,

                        "title":
                            scope_value,

                        "capability":
                            capability,

                        "benefit":
                            benefit,

                        "story":
                            story_text,

                        "business_value":
                            business_value,

                        "acceptance_criteria": [
                            {
                                "statement":
                                    criterion,

                                "candidate_testable":
                                    True,

                                "source_ref":
                                    scope_ref,
                            }
                        ],

                        "candidate_priority":
                            "must",

                        "candidate_priority_rationale":
                            business_goal,

                        "candidate_complexity":
                            "unknown",

                        "candidate_complexity_rationale":
                            (
                                "AI candidate generation "
                                "is temporarily unavailable."
                            ),

                        "candidate_complexity_factors": {
                            "business_logic":
                                "low",

                            "integration_complexity":
                                "unknown",

                            "data_complexity":
                                "low",

                            "ui_complexity":
                                "low",

                            "security":
                                "unknown",

                            "external_dependency":
                                "unknown",

                            "uncertainty":
                                "high",

                            "testing_burden":
                                "unknown",

                            "regulatory_risk":
                                "unknown",

                            "hardware_dependency":
                                "none",
                        },

                        "candidate_dependencies":
                            [],

                        "provenance_refs": [
                            actor_ref,
                            scope_ref,
                        ],

                        "source_context_hash":
                            context.source_context_hash,

                        "warnings": [
                            warning,
                        ],
                    }
                )


            return (
                CandidateBacklogV1
                .model_validate(
                    {
                        "source_context_hash":
                            context.source_context_hash,

                        "context_hash":
                            context.context_hash,

                        "epics": [
                            {
                                "candidate_key":
                                    "epic_mvp",

                                "title":
                                    epic_title,

                                "description":
                                    business_goal,

                                "business_goal":
                                    business_goal,

                                "provenance_refs":
                                    epic_refs,
                            }
                        ],

                        "features":
                            features,

                        "stories":
                            stories,

                        "warnings": [
                            warning,
                        ],
                    }
                )
            )


        # =====================================================================
        # NO EXPLICIT POSITIVE MVP SCOPE
        # =====================================================================
        #
        # Do not manufacture filler Stories merely to increase cardinality.
        # Preserve the historical bounded single recovery unit.
        # =====================================================================

        if context.priority_workflows:

            focus = str(
                context.priority_workflows[0]
                .name
                or ""
            ).strip()

            source_ref = (
                f"workflow:{focus}"
            )

        else:

            focus = str(
                context.solution.core_value
                or context.problem.pain
                or "MVP core workflow"
            ).strip()

            source_ref = (
                f"solution:{focus}"
                if focus
                else actor_ref
            )


        if french:

            epic_title = (
                "Parcours MVP principal"
            )

            capability = (
                f"r\u00e9aliser le parcours "
                f"\u00ab {focus} \u00bb"
            )

            benefit = (
                "valider la valeur du MVP"
            )

            story_text = (
                f"En tant que {actor}, "
                f"je veux {capability} "
                f"afin de {benefit}."
            )

            criterion = (
                f"\u00c9tant donn\u00e9 le parcours "
                f"\u00ab {focus} \u00bb, "
                f"lorsqu'il est r\u00e9alis\u00e9 par {actor}, "
                "alors le r\u00e9sultat est enregistr\u00e9."
            )

            business_goal = (
                "Valider le parcours principal du MVP."
            )

            business_value = (
                "Tester la valeur du produit "
                "avec un flux tra\u00e7able."
            )

        else:

            epic_title = (
                "Core MVP workflow"
            )

            capability = (
                f"complete the '{focus}' workflow"
            )

            benefit = (
                "validate MVP value"
            )

            story_text = (
                f"As a {actor}, "
                f"I want to {capability} "
                f"so that I can {benefit}."
            )

            criterion = (
                f"Given the '{focus}' workflow, "
                f"when {actor} completes it, "
                "then the outcome is recorded."
            )

            business_goal = (
                "Validate the core MVP workflow."
            )

            business_value = (
                "Test product value through "
                "a traceable workflow."
            )


        return (
            CandidateBacklogV1
            .model_validate(
                {
                    "source_context_hash":
                        context.source_context_hash,

                    "context_hash":
                        context.context_hash,

                    "epics": [
                        {
                            "candidate_key":
                                "epic_mvp",

                            "title":
                                epic_title,

                            "description":
                                business_goal,

                            "business_goal":
                                business_goal,

                            "provenance_refs": [
                                source_ref,
                            ],
                        }
                    ],

                    "features": [
                        {
                            "candidate_key":
                                "feature_mvp_workflow",

                            "epic_key":
                                "epic_mvp",

                            "title":
                                focus,

                            "description":
                                capability,

                            "business_value":
                                business_value,

                            "provenance_refs": [
                                source_ref,
                            ],
                        }
                    ],

                    "stories": [
                        {
                            "candidate_key":
                                "story_mvp_workflow",

                            "epic_key":
                                "epic_mvp",

                            "feature_key":
                                "feature_mvp_workflow",

                            "actor_ref":
                                actor,

                            "title":
                                focus,

                            "capability":
                                capability,

                            "benefit":
                                benefit,

                            "story":
                                story_text,

                            "business_value":
                                business_value,

                            "acceptance_criteria": [
                                {
                                    "statement":
                                        criterion,

                                    "candidate_testable":
                                        True,

                                    "source_ref":
                                        source_ref,
                                }
                            ],

                            "candidate_priority":
                                "must",

                            "candidate_priority_rationale":
                                business_goal,

                            "candidate_complexity":
                                "unknown",

                            "candidate_complexity_rationale":
                                (
                                    "AI candidate generation "
                                    "is temporarily unavailable."
                                ),

                            "candidate_complexity_factors": {
                                "business_logic":
                                    "low",

                                "integration_complexity":
                                    "unknown",

                                "data_complexity":
                                    "low",

                                "ui_complexity":
                                    "low",

                                "security":
                                    "unknown",

                                "external_dependency":
                                    "unknown",

                                "uncertainty":
                                    "high",

                                "testing_burden":
                                    "low",

                                "regulatory_risk":
                                    "unknown",

                                "hardware_dependency":
                                    "none",
                            },

                            "candidate_dependencies":
                                [],

                            "provenance_refs": [
                                actor_ref,
                                source_ref,
                            ],

                            "source_context_hash":
                                context.source_context_hash,

                            "warnings": [
                                warning,
                            ],
                        }
                    ],

                    "warnings": [
                        warning,
                    ],
                }
            )
        )

    def replan(
        self,
        *,
        stored_plan: ProjectManagementPlanV1,
        settings: PlanningSettingsV1 | None = None,
    ) -> ProjectManagementPlanV1:
        """Re-run only the deterministic planner over a persisted plan.

        A lock is a hard user promise: if a new valid calculation would move
        a locked story, replan fails explicitly rather than silently moving it.
        """
        effective_settings = settings or stored_plan.settings
        self._validate_settings(effective_settings)
        backlog = CanonicalBacklogV1(
            source_context_hash=stored_plan.source_context_hash,
            context_hash=stored_plan.context_hash,
            epics=stored_plan.epics,
            features=stored_plan.features,
            stories=stored_plan.stories,
        )
        graph = DependencyGraphV1.model_validate(
            {
                "source_context_hash": stored_plan.source_context_hash,
                "context_hash": stored_plan.context_hash,
                "edges": stored_plan.dependencies,
                "hard_topological_order": self._dependency_builder.build(backlog).graph.hard_topological_order,
            }
        )
        advice = ScrumMasterAdviceV1(
            source_context_hash=stored_plan.source_context_hash,
            context_hash=stored_plan.context_hash,
            recommendations=stored_plan.scrum_master_advice,
        )
        planning = self._planner.plan(backlog, graph, effective_settings, advice)
        self._assert_locks_preserved(stored_plan, planning.assignments)

        release_planning = None

        if stored_plan.release_planning is not None:
            previous_release_planning = (
                stored_plan.release_planning
                if effective_settings == stored_plan.settings
                else None
            )

            release_planning = (
                self._build_release_planning_metadata(
                    settings=effective_settings,
                    previous=previous_release_planning,
                )
            )

        return self._assemble_plan(
            context=None,
            backlog=backlog,
            graph=graph,
            advice=advice,
            planning=planning,
            settings=effective_settings,
            revision=stored_plan.revision + 1,
            release_planning=release_planning,
            source_plan=stored_plan,
        )

    def update_locks(
        self,
        *,
        stored_plan: ProjectManagementPlanV1,
        update: BacklogLocksUpdateV1,
    ) -> ProjectManagementPlanV1:
        known_ids = {story.story_id for story in stored_plan.stories}
        requested_ids = {story_id.strip() for story_id in update.locked_story_ids if story_id.strip()}
        unknown_ids = sorted(requested_ids - known_ids)
        if unknown_ids:
            raise ProjectManagementPlanError(
                "unknown_story_lock",
                "Unknown Story IDs cannot be locked: " + ", ".join(unknown_ids),
            )

        stories = [
            story.model_copy(update={"locked": story.story_id in requested_ids}, deep=True)
            for story in stored_plan.stories
        ]
        backlog = CanonicalBacklogV1(
            source_context_hash=stored_plan.source_context_hash,
            context_hash=stored_plan.context_hash,
            epics=stored_plan.epics,
            features=stored_plan.features,
            stories=stories,
        )
        graph = DependencyGraphV1.model_validate(
            {
                "source_context_hash": stored_plan.source_context_hash,
                "context_hash": stored_plan.context_hash,
                "edges": stored_plan.dependencies,
                "hard_topological_order": self._dependency_builder.build(backlog).graph.hard_topological_order,
            }
        )
        advice = ScrumMasterAdviceV1(
            source_context_hash=stored_plan.source_context_hash,
            context_hash=stored_plan.context_hash,
            recommendations=stored_plan.scrum_master_advice,
        )
        # Locking changes no planning decision.  Preserve the existing result.
        planning = self._planning_from_plan(stored_plan)
        return self._assemble_plan(
            context=None,
            backlog=backlog,
            graph=graph,
            advice=advice,
            planning=planning,
            settings=stored_plan.settings,
            revision=stored_plan.revision + 1,
            source_plan=stored_plan,
        )

    def serialize_with_history(
        self,
        *,
        current: ProjectManagementPlanV1,
        previous_envelope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        history: list[dict[str, Any]] = []
        if isinstance(previous_envelope, Mapping):
            raw_history = previous_envelope.get("history")
            if isinstance(raw_history, list):
                history = [item for item in raw_history if isinstance(item, dict)]
            prior = previous_envelope.get("current")
            if isinstance(prior, Mapping):
                history.append(deepcopy(dict(prior)))
        return {
            "schema_version": "project_manager_persistence_v1",
            "current": current.model_dump(mode="json"),
            "history": history[-self._MAX_HISTORY :],
        }

    def deserialize_current(
        self, envelope: Mapping[str, Any] | None
    ) -> ProjectManagementPlanV1 | None:
        if not isinstance(envelope, Mapping):
            return None
        current = envelope.get("current")
        if not isinstance(current, Mapping):
            return None
        try:
            return ProjectManagementPlanV1.model_validate(current)
        except (TypeError, ValueError):
            return None

    def is_stale(
        self,
        *,
        plan: ProjectManagementPlanV1,
        project_id: int,
        analysis_data: Mapping[str, Any] | None,
    ) -> bool:
        try:
            context = self._build_context(project_id=project_id, analysis_data=analysis_data)
        except ProjectManagementPlanError:
            return True
        return context.context_hash != plan.context_hash

    def _build_context(self, *, project_id: int, analysis_data: Mapping[str, Any] | None):
        if not isinstance(analysis_data, Mapping):
            raise ProjectManagementPlanError(
                "analysis_required",
                "Complete the project analysis before generating its Agile plan.",
            )
        packet_raw = analysis_data.get("project_context_packet")
        if not isinstance(packet_raw, Mapping):
            raise ProjectManagementPlanError(
                "project_context_missing",
                "The canonical project context is missing; rerun the analysis first.",
            )
        try:
            packet = ProjectContextPacketV3.model_validate(packet_raw)
        except (TypeError, ValueError) as exc:
            raise ProjectManagementPlanError(
                "project_context_invalid",
                "The canonical project context is invalid; rerun the analysis first.",
            ) from exc
        from app.services.project_context_freshness import (
            project_context_freshness_authority,
        )

        freshness_meta = analysis_data.get(
            "project_context_meta"
        )

        if not (
            project_context_freshness_authority
            .is_current(
                packet=packet,
                metadata=freshness_meta,
            )
        ):
            raise ProjectManagementPlanError(
                "project_context_stale",
                "The canonical project context is stale; rerun the analysis before generating its Agile plan.",
            )

        debate_room = analysis_data.get("debate_room")
        judge = debate_room.get("judge") if isinstance(debate_room, Mapping) else None
        decision = project_management_decision_projector.project(debate_judge=judge)
        return project_management_context_builder.build(
            packet=packet,
            project_id=str(project_id),
            decision=decision,
        )

    @staticmethod
    def _validate_settings(settings: PlanningSettingsV1) -> None:
        if (
            type(settings.sprint_count) is not int
            or settings.sprint_count < 1
        ):
            raise ProjectManagementPlanError(
                "invalid_sprint_count",
                "Sprint count must be a positive integer.",
            )
        if not 1 <= settings.sprint_duration_days <= 31:
            raise ProjectManagementPlanError("invalid_sprint_duration", "Sprint duration must be between 1 and 31 days.")
        if not 1 <= settings.team_size <= 50:
            raise ProjectManagementPlanError("invalid_team_size", "Team size must be between 1 and 50.")
        if not 0 < settings.planned_velocity <= 500:
            raise ProjectManagementPlanError("invalid_velocity", "Planned velocity must be greater than 0 and at most 500.")
        if not 0 < settings.capacity_adjustment <= 2:
            raise ProjectManagementPlanError("invalid_capacity_adjustment", "Capacity adjustment must be greater than 0 and at most 2.")
        try:
            date.fromisoformat(settings.start_date)
        except ValueError as exc:
            raise ProjectManagementPlanError("invalid_start_date", "Start date must use YYYY-MM-DD.") from exc
        if not settings.working_days or any(day < 0 or day > 6 for day in settings.working_days):
            raise ProjectManagementPlanError("invalid_working_days", "Working days must contain identifiers from 0 to 6.")
        if len(set(settings.working_days)) != len(settings.working_days):
            raise ProjectManagementPlanError("invalid_working_days", "Working days must not contain duplicates.")

    def _assemble_plan(
        self,
        *,
        context,
        backlog,
        graph,
        advice,
        planning,
        settings,
        revision,
        release_planning=None,
        source_plan=None,
        extra_warnings=None,
    ) -> ProjectManagementPlanV1:

        metrics = self._build_metrics(
            backlog=backlog,
            planning=planning,
            settings=settings,
        )

        # Project utilization from the existing Story Point
        # accounting authority. Do not recount Story Points here.
        if release_planning is not None:

            release_capacity = float(
                release_planning
                .release_capacity_story_points
            )

            utilization = (
                float(
                    metrics
                    .assigned_story_points
                )
                /
                release_capacity
                if release_capacity > 0
                else 0.0
            )

            release_planning = (
                release_planning.model_copy(
                    update={
                        "capacity_utilization_ratio":
                            utilization,
                    },
                    deep=True,
                )
            )

        assumptions = (
            list(
                context.assumptions
            )
            if context is not None
            else list(
                source_plan.assumptions
                or []
            )
        )

        warnings = self._unique(
            [
                *(
                    list(
                        context.warnings
                    )
                    if context is not None
                    else []
                ),
                *list(
                    backlog.warnings
                ),
                *list(
                    graph.warnings
                ),
                *list(
                    advice.warnings
                ),
                *list(
                    planning.warnings
                ),
                *(
                    list(
                        source_plan.warnings
                    )
                    if source_plan is not None
                    else []
                ),
                *list(
                    extra_warnings
                    or []
                ),
            ]
        )

        return ProjectManagementPlanV1(
            generation_id=str(
                uuid4()
            ),
            revision=revision,
            context_hash=(
                backlog.context_hash
            ),
            source_context_hash=(
                backlog.source_context_hash
            ),
            generated_at=(
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            settings=settings,
            release_planning=(
                release_planning
            ),
            epics=backlog.epics,
            features=backlog.features,
            stories=backlog.stories,
            dependencies=[
                edge.model_dump(
                    mode="json"
                )
                for edge
                in graph.edges
            ],
            sprints=self._sprints(
                backlog,
                planning,
            ),
            overflow_story_ids=(
                planning
                .overflow_story_ids
            ),
            metrics=metrics,
            assumptions=assumptions,
            warnings=warnings,
            scrum_master_advice=(
                advice.recommendations
            ),
        )

    def _build_release_planning_metadata(
        self,
        *,
        settings,
        sizing=None,
        cadence=None,
        previous=None,
    ) -> ReleasePlanningMetadataV1:
        """
        Project already-resolved release decisions into the durable plan.

        This method is not a planning authority:
        - Sprint count remains owned by ReleaseSizingEngine;
        - cadence remains owned by SprintCadenceAdvisor;
        - per-Sprint Story Point capacity remains owned by
          SprintPlanningEngine;
        - Story Point accounting remains owned by
          ProjectManagementMetricsV1.
        """

        effective_capacity = (
            self._planner
            ._effective_sprint_capacity(
                settings
            )
        )

        release_capacity = (
            float(
                effective_capacity
            )
            *
            int(
                settings.sprint_count
            )
        )

        release_duration_days = (
            int(
                settings.sprint_count
            )
            *
            int(
                settings
                .sprint_duration_days
            )
        )


        recommended_sprint_count = None
        evaluated_sprint_counts = []
        sprint_count_reason = None


        if (
            settings.sprint_count_mode
            ==
            "auto"
        ):

            if sizing is not None:

                recommended_sprint_count = (
                    getattr(
                        sizing,
                        "recommended_sprint_count",
                        None,
                    )
                )

                evaluated_sprint_counts = list(
                    getattr(
                        sizing,
                        "evaluated_sprint_counts",
                        [],
                    )
                    or []
                )

                sprint_count_reason = (
                    getattr(
                        sizing,
                        "reason",
                        None,
                    )
                )

            elif (
                previous is not None
                and previous.sprint_count_mode
                ==
                "auto"
            ):

                recommended_sprint_count = (
                    previous
                    .recommended_sprint_count
                )

                evaluated_sprint_counts = list(
                    previous
                    .evaluated_sprint_counts
                )

                sprint_count_reason = (
                    previous
                    .sprint_count_reason
                )


        recommended_duration = None
        cadence_band = None
        cadence_confidence = None
        cadence_reason_codes = []
        cadence_evaluated_story_count = None


        if (
            settings.sprint_duration_mode
            ==
            "auto"
        ):

            if cadence is not None:

                recommended_duration = (
                    getattr(
                        cadence,
                        "recommended_sprint_duration_days",
                        None,
                    )
                )

                cadence_band = (
                    getattr(
                        cadence,
                        "cadence_band",
                        None,
                    )
                )

                cadence_confidence = (
                    getattr(
                        cadence,
                        "confidence",
                        None,
                    )
                )

                cadence_reason_codes = list(
                    getattr(
                        cadence,
                        "reason_codes",
                        [],
                    )
                    or []
                )

                cadence_evaluated_story_count = (
                    getattr(
                        cadence,
                        "evaluated_story_count",
                        None,
                    )
                )

            elif (
                previous is not None
                and previous.sprint_duration_mode
                ==
                "auto"
            ):

                recommended_duration = (
                    previous
                    .recommended_sprint_duration_days
                )

                cadence_band = (
                    previous
                    .cadence_band
                )

                cadence_confidence = (
                    previous
                    .cadence_confidence
                )

                cadence_reason_codes = list(
                    previous
                    .cadence_reason_codes
                )

                cadence_evaluated_story_count = (
                    previous
                    .cadence_evaluated_story_count
                )


        return ReleasePlanningMetadataV1(
            sprint_count_mode=(
                settings
                .sprint_count_mode
            ),
            effective_sprint_count=(
                settings
                .sprint_count
            ),
            recommended_sprint_count=(
                recommended_sprint_count
            ),
            sprint_count_reason=(
                sprint_count_reason
            ),
            evaluated_sprint_counts=(
                evaluated_sprint_counts
            ),
            sprint_duration_mode=(
                settings
                .sprint_duration_mode
            ),
            effective_sprint_duration_days=(
                settings
                .sprint_duration_days
            ),
            recommended_sprint_duration_days=(
                recommended_duration
            ),
            cadence_band=(
                cadence_band
            ),
            cadence_confidence=(
                cadence_confidence
            ),
            cadence_reason_codes=(
                cadence_reason_codes
            ),
            cadence_evaluated_story_count=(
                cadence_evaluated_story_count
            ),
            effective_sprint_capacity_story_points=(
                effective_capacity
            ),
            release_capacity_story_points=(
                release_capacity
            ),
            capacity_utilization_ratio=0.0,
            release_duration_days=(
                release_duration_days
            ),
        )

    @staticmethod
    def _planning_from_plan(plan: ProjectManagementPlanV1):
        from app.services.sprint_planning_engine import SprintPlanningResultV1
        assignments = [
            {"story_id": story_id, "sprint_number": sprint["sprint_number"]}
            for sprint in plan.sprints
            for story_id in sprint.get("story_ids", [])
        ]
        return SprintPlanningResultV1(
            source_context_hash=plan.source_context_hash,
            context_hash=plan.context_hash,
            sprint_count=plan.settings.sprint_count,
            assignments=assignments,
            overflow_story_ids=plan.overflow_story_ids,
        )

    @staticmethod
    def _assert_locks_preserved(previous, next_assignments) -> None:
        old_assignment = {
            story_id: sprint["sprint_number"]
            for sprint in previous.sprints
            for story_id in sprint.get("story_ids", [])
        }
        new_assignment = {item.story_id: item.sprint_number for item in next_assignments}
        moved = [
            story.story_id
            for story in previous.stories
            if story.locked and old_assignment.get(story.story_id) != new_assignment.get(story.story_id)
        ]
        if moved:
            raise ProjectManagementPlanError(
                "locked_story_would_move",
                "Unlock these Stories before this replan: " + ", ".join(sorted(moved)),
            )

    @staticmethod
    def _sprints(backlog, planning) -> list[dict[str, Any]]:
        points = {story.story_id: int(story.story_points or 0) for story in backlog.stories}
        assigned = {item.story_id: item.sprint_number for item in planning.assignments}
        return [
            {
                "sprint_number": number,
                "story_ids": [story_id for story_id, sprint in assigned.items() if sprint == number],
                "planned_story_points": sum(points[story_id] for story_id, sprint in assigned.items() if sprint == number),
            }
            for number in range(1, planning.sprint_count + 1)
        ]

    def _build_metrics(self, *, backlog, planning, settings) -> ProjectManagementMetricsV1:
        points = {story.story_id: int(story.story_points or 0) for story in backlog.stories}
        assigned_ids = {item.story_id for item in planning.assignments}
        total = sum(points.values())
        assigned = sum(points[story_id] for story_id in assigned_ids)
        sprint_metrics = []
        for sprint in self._sprints(backlog, planning):
            sprint_metrics.append(SprintMetricV1(
                sprint_number=sprint["sprint_number"],
                planned_story_points=sprint["planned_story_points"],
                planned_story_count=len(sprint["story_ids"]),
            ))
        days = max(1, settings.sprint_count * settings.sprint_duration_days)
        ideal = [round(total * (1 - day / days), 2) for day in range(days + 1)]
        return ProjectManagementMetricsV1(
            planned_velocity=settings.planned_velocity,
            projected_velocity=(assigned / settings.sprint_count if settings.sprint_count else 0),
            total_story_points=total,
            assigned_story_points=assigned,
            overflow_story_points=sum(points.get(story_id, 0) for story_id in planning.overflow_story_ids),
            sprint_metrics=sprint_metrics,
            ideal_burndown=ideal,
            planned_burndown=list(ideal),
        )

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if isinstance(value, str) and value.strip()))


project_management_plan_service = ProjectManagementPlanService()
