from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence

from app.schemas.analysis_context import (
    ContextReadinessStatus,
    ProjectContextPacketV3,
    clean_text,
    comparison_key,
    unique_texts,
)
from app.services.context_confidence_gate import (
    context_confidence_gate,
)
from app.services.domain_integrity_guard import (
    normalize_output_language,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)
from app.services.clarification_answer_projector import (
    clarification_answer_projector,
)
from app.schemas.analysis_context import clean_structured_text


class IdeaReadinessChecker:
    """
    Adaptateur de compatibilité Sprint 3.

    La compréhension et le score ne sont plus recalculés ici :

    - ProjectContextExtractor construit ProjectContextPacketV3 ;
    - ContextConfidenceGate décide si les agents peuvent démarrer.

    Les anciennes clés sont conservées afin de ne pas casser :

    - startup_evaluator_graph ;
    - project_intelligence_layer ;
    - le frontend ;
    - les rapports et tests Sprint 3.
    """

    MIN_READY_SCORE = (
        context_confidence_gate
        .policy
        .cautious_score
    )

    def evaluate(
        self,
        *,
        title: str = "",
        description: str = "",
        industry: str = "",
        target_region: str = "",
        output_language: str = "fr",
        project_context: Dict[str, Any] | None = None,
        analysis_data: Dict[str, Any] | None = None,
        clarification_answers: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Évalue une idée et retourne un payload compatible Sprint 3.

        Le service peut :

        - reconstruire un packet depuis les champs bruts ;
        - réutiliser un ProjectContextPacketV3 déjà persisté ;
        - refuser un packet provenant d'un ancien projet ;
        - conserver les anciennes clés publiques.
        """
        language = normalize_output_language(
            output_language
        )

        project_context = dict(
            project_context or {}
        )

        analysis_data = dict(
            analysis_data or {}
        )

        # NORMALIZED_EXPLICIT_CLARIFICATION_FACTS
        # Input hygiene only.
        # Resolved/unresolved semantic authority remains in
        # ClarificationAnswerProjector.
        clarification_answers = {
            clean_text(
                raw_field
            ):
            clean_text(
                raw_answer
            )
            for raw_field, raw_answer
            in dict(
                clarification_answers
                or {}
            ).items()
            if clean_text(
                raw_field
            )
            and clean_text(
                raw_answer
            )
        }

        title = clean_text(
            title
            or project_context.get(
                "project_name"
            )
            or project_context.get(
                "title"
            )
        )

        description = clean_structured_text(
            description
            or project_context.get(
                "description"
            )
        )

        industry = clean_text(
            industry
            or project_context.get(
                "industry"
            )
        )

        target_region = clean_text(
            target_region
            or project_context.get(
                "target_region"
            )
            or project_context.get(
                "market_region"
            )
        )

        packet = None

        if not clarification_answers:
            packet = self._existing_packet(
                title=title,
                description=description,
                project_context=project_context,
                analysis_data=analysis_data,
            )

        if packet is None:
            packet = (
                project_context_extractor
                .extract(
                    title=title,
                    description=description,
                    industry=industry,
                    target_region=target_region,
                    output_language=language,
                    project_context=(
                        project_context
                    ),
                    analysis_data=analysis_data,
                )
            )

        # CLARIFICATION_PROJECTOR_HANDOFF
        if clarification_answers:
            packet = (
                clarification_answer_projector
                .apply(
                    packet,
                    clarification_answers,
                )
            )

        packet = (
            context_confidence_gate
            .apply(
                packet
            )
        )

        confidence = packet.confidence

        ready_for_agents = (
            context_confidence_gate
            .should_run_agents(
                confidence
            )
        )

        detected = self._detected(
            packet
        )

        questions = list(
            confidence
            .clarification_questions
        )

        # FIELD_BOUND_CLARIFICATION_ITEMS
        #
        # ContextConfidenceGate already owns:
        # - field ordering;
        # - localized question wording.
        #
        # IdeaReadiness only binds identity to presentation.
        clarification_fields = list(
            dict.fromkeys(
                [
                    *confidence.missing_fields,
                    *confidence.ambiguous_fields,
                    *confidence.blockers,
                ]
            )
        )

        # ContextConfidenceGate intentionally limits the human-facing
        # clarification surface (currently at most ten questions).
        #
        # Diagnostics remain complete in missing_fields /
        # ambiguous_fields / blockers. clarification_items identify only
        # the questions that the gate actually exposes to the user.
        clarification_fields = (
            clarification_fields[
                :len(
                    questions
                )
            ]
        )

        missing_keys = set(
            confidence.missing_fields
        )

        ambiguous_keys = set(
            confidence.ambiguous_fields
        )

        clarification_items = []

        for field, question in zip(
            clarification_fields,
            questions,
        ):
            if field in missing_keys:
                kind = "missing"

            elif field in ambiguous_keys:
                kind = "ambiguous"

            else:
                kind = "blocking"

            clarification_items.append(
                {
                    "field":
                        field,

                    "kind":
                        kind,

                    "question":
                        question,
                }
            )

        return {
            # Ancienne valeur conservée pour les
            # consommateurs Sprint 3.
            "format": (
                "idea_readiness_v1_"
                "context_confidence"
            ),

            # Nouvelle identité canonique.
            "canonical_format": (
                "idea_readiness_v3_"
                "project_context"
            ),

            "schema_version": (
                packet.schema_version
            ),

            "status": (
                confidence.status.value
            ),

            "score": (
                confidence.score
            ),

            "ready_for_agents": (
                ready_for_agents
            ),

            "threshold": (
                self.MIN_READY_SCORE
            ),

            "detected": detected,

            "missing_fields": list(
                confidence.missing_fields
            ),

            "ambiguous_fields": list(
                confidence.ambiguous_fields
            ),

            "blockers": list(
                confidence.blockers
            ),

            "assumptions": (
                self._assumptions(
                    packet
                )
            ),

            "questions": questions,

            "clarification_questions": (
                questions
            ),

            "suggested_options": (
                self._suggested_options(
                    packet
                )
            ),

            "checklist": (
                self._checklist(
                    packet
                )
            ),

            "scoring_details": (
                self._scoring_details(
                    packet
                )
            ),

            "recommendation": (
                self._recommendation(
                    status=confidence.status,
                    language=packet.language,
                    blockers=(
                        confidence.blockers
                    ),
                    ambiguous_fields=(
                        confidence
                        .ambiguous_fields
                    ),
                )
            ),

            "reasons": list(
                confidence.reasons
            ),

            "output_language": (
                packet.language
            ),

            "project_context_packet": (
                packet.model_dump(
                    mode="json"
                )
            ),

            "legacy_project_context": (
                packet.to_legacy_dict()
            ),

            "context_confidence": (
                confidence.model_dump(
                    mode="json"
                )
            ),
            "clarification_items": (
                clarification_items
            ),

        }

    def evaluate_packet(
        self,
        packet: ProjectContextPacketV3,
    ) -> Dict[str, Any]:
        """
        Évalue directement un packet canonique.
        """
        return self.evaluate(
            title=packet.project_name,
            description=packet.description,
            industry=(
                packet.industry_user_input
            ),
            target_region=(
                packet.target_region
            ),
            output_language=(
                packet.language
            ),
            project_context={
                "project_context_packet": (
                    packet.model_dump(
                        mode="json"
                    )
                )
            },
        )

    def evaluate_mapping(
        self,
        data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Évalue un packet sérialisé provenant de Redis
        ou de la base de données.
        """
        packet = (
            ProjectContextPacketV3
            .model_validate(
                dict(
                    data
                )
            )
        )

        return self.evaluate_packet(
            packet
        )

    def _existing_packet(
        self,
        *,
        title: str,
        description: str,
        project_context: Mapping[str, Any],
        analysis_data: Mapping[str, Any],
    ) -> ProjectContextPacketV3 | None:
        """
        Réutilise un packet existant uniquement s'il
        correspond au projet courant.

        Cette protection évite qu'un ancien run ou un
        autre projet contamine l'analyse.
        """
        candidates: List[Any] = [
            analysis_data.get(
                "project_context_packet"
            ),
            project_context.get(
                "project_context_packet"
            ),
        ]

        if (
            project_context.get(
                "schema_version"
            )
            == "project_context_v3"
        ):
            candidates.append(
                project_context
            )

        for candidate in candidates:
            if not isinstance(
                candidate,
                Mapping,
            ):
                continue

            try:
                packet = (
                    ProjectContextPacketV3
                    .model_validate(
                        dict(
                            candidate
                        )
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if (
                title
                and comparison_key(
                    packet.project_name
                )
                != comparison_key(
                    title
                )
            ):
                continue

            if description:
                expected_description = (
                    comparison_key(
                        description
                    )
                )

                packet_description = (
                    comparison_key(
                        packet.description
                    )
                )

                if (
                    expected_description
                    and packet_description
                    and expected_description
                    != packet_description
                ):
                    continue

            return packet

        return None

    def _detected(
        self,
        packet: ProjectContextPacketV3,
    ) -> Dict[str, Any]:
        """
        Produit les anciennes clés `detected`
        à partir du packet canonique.
        """
        confidence = packet.confidence

        primary_workflow = (
            packet.primary_workflow
        )

        explicit_business_model = (
            "business_model"
            not in confidence
            .ambiguous_fields
        )

        target_users = (
            packet.actor_names(
                explicit_only=True
            )
            or packet.actor_names()
        )

        main_use_case = (
            primary_workflow.sentence
            if primary_workflow
            else ""
        )

        return {
            "project_name": (
                packet.project_name
            ),

            "description_length": len(
                packet.description
            ),

            "sector": (
                packet
                .industry_user_input
            ),

            "sector_labels": list(
                packet.sector_labels
            ),

            "target_region": (
                packet.target_region
            ),

            "target_users": (
                target_users
            ),

            "actors": [
                actor.model_dump(
                    mode="json"
                )
                for actor in packet.actors
            ],

            "problem": clean_text(
                packet.problem.pain
            ),

            "solution": clean_text(
                packet.solution.mechanism
            ),

            "main_use_case": (
                main_use_case
            ),

            "priority_workflow": (
                main_use_case
            ),

            "priority_workflows": [
                workflow.sentence
                for workflow
                in packet
                .priority_workflows
                if workflow.sentence
            ],

            "business_model": (
                "; ".join(
                    packet
                    .business_model_hypotheses
                )
                if explicit_business_model
                else ""
            ),

            "business_model_hypotheses": (
                list(
                    packet
                    .business_model_hypotheses
                )
            ),

            "mvp_scope": (
                "; ".join(
                    packet.mvp_scope
                )
            ),

            "mvp_scope_items": list(
                packet.mvp_scope
            ),

            "project_archetype": (
                packet.primary_archetype
            ),

            "secondary_archetypes": (
                list(
                    packet
                    .secondary_archetypes
                )
            ),

            "constraints": list(
                packet.constraints
            ),

            "success_metrics": list(
                packet.success_metrics
            ),

            "regulatory_flags": list(
                packet.regulatory_flags
            ),

            "has_problem_signal": bool(
                packet.problem.pain
            ),

            "has_solution_signal": bool(
                packet.solution.mechanism
            ),

            "has_target_signal": bool(
                target_users
            ),

            "has_workflow_signal": bool(
                primary_workflow
            ),

            "has_business_signal": (
                explicit_business_model
            ),

            "has_mvp_signal": bool(
                packet.mvp_scope
            ),
        }

    def _assumptions(
        self,
        packet: ProjectContextPacketV3,
    ) -> List[str]:
        """
        Produit uniquement des hypothèses prudentes.

        Un champ absent ne devient jamais un fait confirmé.
        """
        labels = self._texts(
            packet.language
        )

        assumptions = list(
            packet.assumptions
        )

        ambiguous_fields = set(
            packet
            .confidence
            .ambiguous_fields
        )

        for field_name in (
            "business_model",
            "target_region",
            "mvp_scope",
            "success_metrics",
        ):
            if (
                field_name
                in ambiguous_fields
            ):
                assumptions.append(
                    labels[
                        "assumption_"
                        + field_name
                    ]
                )

        return unique_texts(
            assumptions
        )

    def _checklist(
        self,
        packet: ProjectContextPacketV3,
    ) -> List[Dict[str, Any]]:
        """
        Checklist compatible avec le frontend existant.
        """
        confidence = (
            packet.confidence
        )

        unresolved_fields = {
            *confidence.missing_fields,
            *confidence.ambiguous_fields,
            *confidence.blockers,
        }

        required_fields = {
            "project_name",
            "problem",
            "solution",
            "actors",
            "priority_workflow",
        }

        return [
            {
                "key": key,
                "label": label,
                "checked": (
                    key
                    not in unresolved_fields
                ),
                "required": (
                    key
                    in required_fields
                ),
            }
            for key, label
            in self._checklist_labels(
                packet.language
            )
        ]

    def _suggested_options(
        self,
        packet: ProjectContextPacketV3,
    ) -> Dict[str, List[str]]:
        """
        Suggestions de formulaire basées sur
        l'archétype du projet.

        Elles ne constituent pas des conclusions marché.
        """
        texts = self._texts(
            packet.language
        )

        archetypes = {
            comparison_key(
                packet.primary_archetype
            ),
            *(
                comparison_key(
                    value
                )
                for value
                in packet
                .secondary_archetypes
            ),
        }

        business_models: List[str] = []

        if (
            comparison_key(
                "hardware_iot"
            )
            in archetypes
        ):
            business_models.extend(
                texts[
                    "models_hardware"
                ]
            )

        if (
            comparison_key(
                "two_sided_marketplace"
            )
            in archetypes
        ):
            business_models.extend(
                texts[
                    "models_marketplace"
                ]
            )

        if (
            comparison_key(
                "b2b_workflow_saas"
            )
            in archetypes
        ):
            business_models.extend(
                texts[
                    "models_saas"
                ]
            )

        business_models.extend(
            texts[
                "models_generic"
            ]
        )

        return {
            "target_region": list(
                texts["regions"]
            ),

            "target_users": (
                packet.actor_names(
                    explicit_only=True
                )
                or packet.actor_names()
            ),

            "business_model": (
                unique_texts(
                    business_models
                )[:8]
            ),

            "mvp_scope": list(
                texts["mvp_options"]
            ),

            "success_metrics": list(
                texts[
                    "metric_options"
                ]
            ),
        }

    def _scoring_details(
        self,
        packet: ProjectContextPacketV3,
    ) -> Dict[str, Any]:
        """
        Conserve les anciennes clés de scoring.

        Il n'existe désormais qu'une seule source de vérité :
        ContextConfidenceGate.
        """
        confidence = (
            packet.confidence
        )

        return {
            "source": (
                "context_confidence_gate_v1"
            ),

            "schema_version": (
                packet.schema_version
            ),

            "raw_score": (
                confidence.score
            ),

            "penalty": 0.0,

            "final_score": (
                confidence.score
            ),

            "status": (
                confidence.status.value
            ),

            "ready_threshold": (
                context_confidence_gate
                .policy
                .ready_score
            ),

            "cautious_threshold": (
                context_confidence_gate
                .policy
                .cautious_score
            ),

            "clarification_threshold": (
                context_confidence_gate
                .policy
                .clarification_score
            ),

            "missing_count": len(
                confidence
                .missing_fields
            ),

            "ambiguous_count": len(
                confidence
                .ambiguous_fields
            ),

            "blocker_count": len(
                confidence.blockers
            ),

            "explicit_actor_count": sum(
                actor.is_explicit
                for actor
                in packet.actors
            ),

            "workflow_count": len(
                packet
                .priority_workflows
            ),

            "context_only": True,

            "market_validation_included": (
                False
            ),
        }

    def _recommendation(
        self,
        *,
        status: ContextReadinessStatus,
        language: str,
        blockers: Sequence[str],
        ambiguous_fields: Sequence[str],
    ) -> str:
        """
        Produit une recommandation utilisateur.
        """
        texts = self._texts(
            language
        )

        if (
            status
            == ContextReadinessStatus.READY
        ):
            return texts[
                "recommendation_ready"
            ]

        if (
            status
            == ContextReadinessStatus
            .READY_CAUTIOUS
        ):
            return texts[
                "recommendation_cautious"
            ]

        fields = unique_texts(
            [
                *blockers,
                *ambiguous_fields,
            ]
        )

        suffix = (
            (
                f" {texts['fields_label']}: "
                f"{', '.join(fields)}."
            )
            if fields
            else ""
        )

        return (
            texts[
                "recommendation_blocked"
            ]
            + suffix
        )

    def _checklist_labels(
        self,
        language: str,
    ) -> List[tuple[str, str]]:
        return list(
            self._texts(
                language
            )["checklist"]
        )

    def _texts(
        self,
        language: str,
    ) -> Dict[str, Any]:
        """
        Textes frontend et suggestions dans
        la langue de l'analyse.
        """
        if language == "en":
            return {
                "assumption_business_model": (
                    "The revenue model is not confirmed "
                    "and must be validated."
                ),

                "assumption_target_region": (
                    "The launch region is not confirmed "
                    "and must not be inferred."
                ),

                "assumption_mvp_scope": (
                    "The first testable scope remains "
                    "to be defined."
                ),

                "assumption_success_metrics": (
                    "The pilot success metrics remain "
                    "to be defined."
                ),

                "recommendation_ready": (
                    "The project context is complete "
                    "enough to run the agents. Market "
                    "evidence must still be verified "
                    "separately."
                ),

                "recommendation_cautious": (
                    "The analysis may start cautiously. "
                    "Remaining ambiguities must stay "
                    "explicit and must not be presented "
                    "as facts."
                ),

                "recommendation_blocked": (
                    "Complete the blocking context fields "
                    "before starting the market and "
                    "strategy analysis."
                ),

                "fields_label": "Fields",

                "regions": [
                    "Tunisia",
                    "North Africa",
                    "France",
                    "Europe",
                    "Global",
                ],

                "models_hardware": [
                    (
                        "Hardware sale + "
                        "software subscription"
                    ),
                    (
                        "Equipment rental + "
                        "maintenance"
                    ),
                ],

                "models_marketplace": [
                    "Commission per transaction",
                    "Provider subscription",
                ],

                "models_saas": [
                    (
                        "Monthly subscription "
                        "per organization"
                    ),
                    "Subscription per user",
                    "Freemium + paid plans",
                ],

                "models_generic": [
                    "Direct sale",
                    "Usage-based pricing",
                    "Professional services",
                ],

                "mvp_options": [
                    "One target segment",
                    "One end-to-end workflow",
                    "One measurable outcome",
                    "One launch region",
                    (
                        "A manual pilot before "
                        "automation"
                    ),
                ],

                "metric_options": [
                    "Task completion rate",
                    "Time saved",
                    "Pilot retention",
                    "Error reduction",
                    "Willingness to pay",
                ],

                "checklist": [
                    (
                        "project_name",
                        "Project name is clear",
                    ),
                    (
                        "problem",
                        "The main problem is specific",
                    ),
                    (
                        "solution",
                        (
                            "The solution mechanism "
                            "is concrete"
                        ),
                    ),
                    (
                        "actors",
                        (
                            "Users, buyers, and operators "
                            "are identified"
                        ),
                    ),
                    (
                        "priority_workflow",
                        (
                            "The main workflow "
                            "is actionable"
                        ),
                    ),
                    (
                        "target_region",
                        (
                            "The launch region "
                            "is defined"
                        ),
                    ),
                    (
                        "project_archetype",
                        (
                            "The project archetype "
                            "is specific"
                        ),
                    ),
                    (
                        "business_model",
                        (
                            "The business model "
                            "is explicit"
                        ),
                    ),
                    (
                        "mvp_scope",
                        (
                            "The MVP scope is separated "
                            "from the workflow"
                        ),
                    ),
                    (
                        "constraints",
                        (
                            "The main constraints "
                            "are listed"
                        ),
                    ),
                    (
                        "success_metrics",
                        (
                            "Success metrics "
                            "are measurable"
                        ),
                    ),
                ],
            }

        if language == "ar":
            return {
                "assumption_business_model": (
                    "نموذج الإيرادات غير مؤكد "
                    "ويجب التحقق منه."
                ),

                "assumption_target_region": (
                    "منطقة الإطلاق غير مؤكدة "
                    "ولا يجب افتراضها."
                ),

                "assumption_mvp_scope": (
                    "لا يزال نطاق أول نسخة قابلة "
                    "للاختبار بحاجة إلى تحديد."
                ),

                "assumption_success_metrics": (
                    "لا تزال مؤشرات نجاح التجربة "
                    "بحاجة إلى تحديد."
                ),

                "recommendation_ready": (
                    "سياق المشروع مكتمل بما يكفي "
                    "لتشغيل وكلاء التحليل، لكن يجب "
                    "التحقق من أدلة السوق بشكل منفصل."
                ),

                "recommendation_cautious": (
                    "يمكن بدء التحليل بحذر، مع إبقاء "
                    "النقاط الغامضة واضحة وعدم عرضها "
                    "كحقائق."
                ),

                "recommendation_blocked": (
                    "يجب استكمال معلومات السياق "
                    "الأساسية قبل بدء تحليل السوق "
                    "والاستراتيجية."
                ),

                "fields_label": "الحقول",

                "regions": [
                    "تونس",
                    "شمال أفريقيا",
                    "فرنسا",
                    "أوروبا",
                    "السوق العالمي",
                ],

                "models_hardware": [
                    (
                        "بيع الجهاز مع "
                        "اشتراك برمجي"
                    ),
                    (
                        "تأجير الجهاز مع "
                        "الصيانة"
                    ),
                ],

                "models_marketplace": [
                    "عمولة على كل معاملة",
                    "اشتراك لمقدمي الخدمة",
                ],

                "models_saas": [
                    "اشتراك شهري للمؤسسة",
                    "اشتراك لكل مستخدم",
                    (
                        "نسخة مجانية مع "
                        "خطط مدفوعة"
                    ),
                ],

                "models_generic": [
                    "بيع مباشر",
                    "تسعير حسب الاستخدام",
                    "خدمات مهنية",
                ],

                "mvp_options": [
                    "شريحة مستخدمين واحدة",
                    (
                        "مسار استخدام رئيسي "
                        "واحد"
                    ),
                    (
                        "نتيجة واحدة قابلة "
                        "للقياس"
                    ),
                    "منطقة إطلاق واحدة",
                    (
                        "تجربة يدوية قبل "
                        "الأتمتة"
                    ),
                ],

                "metric_options": [
                    "نسبة إكمال المهمة",
                    "الوقت الموفر",
                    "استمرار مستخدمي التجربة",
                    "انخفاض الأخطاء",
                    "الاستعداد للدفع",
                ],

                "checklist": [
                    (
                        "project_name",
                        "اسم المشروع واضح",
                    ),
                    (
                        "problem",
                        (
                            "المشكلة الرئيسية "
                            "محددة"
                        ),
                    ),
                    (
                        "solution",
                        "آلية الحل واضحة",
                    ),
                    (
                        "actors",
                        (
                            "المستخدمون والمشترون "
                            "والمشغلون محددون"
                        ),
                    ),
                    (
                        "priority_workflow",
                        (
                            "مسار الاستخدام الرئيسي "
                            "قابل للتنفيذ"
                        ),
                    ),
                    (
                        "target_region",
                        "منطقة الإطلاق محددة",
                    ),
                    (
                        "project_archetype",
                        "نوع المشروع محدد",
                    ),
                    (
                        "business_model",
                        "نموذج الإيرادات واضح",
                    ),
                    (
                        "mvp_scope",
                        (
                            "نطاق النسخة الأولى "
                            "منفصل عن مسار الاستخدام"
                        ),
                    ),
                    (
                        "constraints",
                        "القيود الرئيسية محددة",
                    ),
                    (
                        "success_metrics",
                        (
                            "مؤشرات النجاح "
                            "قابلة للقياس"
                        ),
                    ),
                ],
            }

        return {
            "assumption_business_model": (
                "Le modèle économique n’est pas "
                "confirmé et doit être validé."
            ),

            "assumption_target_region": (
                "La région de lancement n’est pas "
                "confirmée et ne doit pas être déduite."
            ),

            "assumption_mvp_scope": (
                "Le périmètre de la première version "
                "testable reste à définir."
            ),

            "assumption_success_metrics": (
                "Les indicateurs de succès du pilote "
                "restent à définir."
            ),

            "recommendation_ready": (
                "Le contexte du projet est suffisamment "
                "complet pour lancer les agents. Les "
                "preuves marché restent à vérifier "
                "séparément."
            ),

            "recommendation_cautious": (
                "L’analyse peut commencer avec prudence. "
                "Les ambiguïtés restantes doivent rester "
                "explicites et ne pas être présentées "
                "comme des faits."
            ),

            "recommendation_blocked": (
                "Complétez les informations de contexte "
                "bloquantes avant de lancer l’analyse "
                "marché et stratégique."
            ),

            "fields_label": (
                "Champs concernés"
            ),

            "regions": [
                "Tunisie",
                "Afrique du Nord",
                "France",
                "Europe",
                "Global",
            ],

            "models_hardware": [
                (
                    "Vente du matériel + "
                    "abonnement logiciel"
                ),
                (
                    "Location du matériel + "
                    "maintenance"
                ),
            ],

            "models_marketplace": [
                "Commission par transaction",
                "Abonnement des prestataires",
            ],

            "models_saas": [
                (
                    "Abonnement mensuel "
                    "par organisation"
                ),
                "Abonnement par utilisateur",
                (
                    "Freemium avec "
                    "plans payants"
                ),
            ],

            "models_generic": [
                "Vente directe",
                "Paiement à l’usage",
                "Services professionnels",
            ],

            "mvp_options": [
                "Un seul segment cible",
                (
                    "Un seul workflow "
                    "de bout en bout"
                ),
                (
                    "Un seul résultat "
                    "mesurable"
                ),
                (
                    "Une seule région "
                    "de lancement"
                ),
                (
                    "Un pilote manuel "
                    "avant automatisation"
                ),
            ],

            "metric_options": [
                (
                    "Taux d’accomplissement "
                    "de la tâche"
                ),
                "Temps économisé",
                (
                    "Rétention pendant "
                    "le pilote"
                ),
                "Réduction des erreurs",
                "Volonté de payer",
            ],

            "checklist": [
                (
                    "project_name",
                    (
                        "Le nom du projet "
                        "est clair"
                    ),
                ),
                (
                    "problem",
                    (
                        "Le problème principal "
                        "est précis"
                    ),
                ),
                (
                    "solution",
                    (
                        "Le mécanisme de solution "
                        "est concret"
                    ),
                ),
                (
                    "actors",
                    (
                        "Les utilisateurs, acheteurs "
                        "et opérateurs sont identifiés"
                    ),
                ),
                (
                    "priority_workflow",
                    (
                        "Le workflow principal "
                        "est actionnable"
                    ),
                ),
                (
                    "target_region",
                    (
                        "La région de lancement "
                        "est définie"
                    ),
                ),
                (
                    "project_archetype",
                    (
                        "L’archétype du projet "
                        "est spécifique"
                    ),
                ),
                (
                    "business_model",
                    (
                        "Le modèle économique "
                        "est explicite"
                    ),
                ),
                (
                    "mvp_scope",
                    (
                        "Le MVP est séparé "
                        "du workflow principal"
                    ),
                ),
                (
                    "constraints",
                    (
                        "Les contraintes principales "
                        "sont indiquées"
                    ),
                ),
                (
                    "success_metrics",
                    (
                        "Les indicateurs de succès "
                        "sont mesurables"
                    ),
                ),
            ],
        }


idea_readiness_checker = (
    IdeaReadinessChecker()
)
