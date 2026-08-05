from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Any, Dict, Iterable, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


_SPACE_RE = re.compile(r"\s+")

_GENERIC_ACTORS = {
    "client",
    "clients",
    "customer",
    "customers",
    "user",
    "users",
    "utilisateur",
    "utilisateurs",
    "business owner",
    "owner",
    "operator",
    "operateur",
    "opérateur",
    "field operator",
    "operateur terrain",
    "opérateur terrain",
    "operational buyer",
    "acheteur operationnel",
    "acheteur opérationnel",
}


def clean_text(value: Any) -> str:
    """
    Nettoie une valeur textuelle sans inventer de contenu.

    - supprime les caractères NUL ;
    - réduit les espaces multiples ;
    - supprime les espaces au début et à la fin.
    """
    if value is None:
        return ""

    return _SPACE_RE.sub(
        " ",
        str(value).replace("\x00", " "),
    ).strip()


def comparison_key(value: Any) -> str:
    """
    Crée une clé normalisée utilisée uniquement pour les comparaisons.

    La valeur originale n'est jamais remplacée par cette clé.
    """
    text = unicodedata.normalize(
        "NFKD",
        clean_text(value).casefold(),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return _SPACE_RE.sub(
        " ",
        text,
    ).strip()


def unique_texts(
    values: Optional[Iterable[Any]],
) -> List[str]:
    """
    Nettoie et déduplique une liste tout en conservant son ordre.
    """
    output: List[str] = []
    seen: set[str] = set()

    for value in values or []:
        text = clean_text(value)
        key = comparison_key(text)

        if not text or not key or key in seen:
            continue

        seen.add(key)
        output.append(text)

    return output


def normalize_language(value: Any) -> str:
    """
    Normalise les langues actuellement prises en charge par ForgeAI.
    """
    aliases = {
        "fr": "fr",
        "francais": "fr",
        "french": "fr",
        "en": "en",
        "english": "en",
        "anglais": "en",
        "ar": "ar",
        "arabic": "ar",
        "arabe": "ar",
    }

    return aliases.get(
        comparison_key(value or "fr"),
        "fr",
    )


class ContextReadinessStatus(str, Enum):
    READY = "ready"
    READY_CAUTIOUS = "ready_cautious"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    OUT_OF_SCOPE = "out_of_scope"


class ActorRole(str, Enum):
    USER = "user"
    BENEFICIARY = "beneficiary"
    BUYER = "buyer"
    PAYER = "payer"
    DECISION_MAKER = "decision_maker"
    OPERATOR = "operator"
    PROVIDER = "provider"
    MAINTAINER = "maintainer"
    PARTNER = "partner"
    REGULATORY_BLOCKER = "regulatory_blocker"
    OTHER = "other"


class ActorContext(BaseModel):
    """
    Représente un acteur réel du projet.

    Exemple :
    - utilisateur ;
    - acheteur ;
    - payeur ;
    - opérateur ;
    - mainteneur ;
    - partenaire.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=180,
    )

    role: ActorRole = ActorRole.OTHER

    description: str = ""

    is_explicit: bool = False

    decision_power: Literal[
        "unknown",
        "low",
        "medium",
        "high",
    ] = "unknown"

    buying_power: Literal[
        "unknown",
        "low",
        "medium",
        "high",
    ] = "unknown"

    @field_validator(
        "name",
        "description",
        mode="before",
    )
    @classmethod
    def clean_fields(
        cls,
        value: Any,
    ) -> str:
        return clean_text(value)

    @computed_field
    @property
    def is_generic(self) -> bool:
        """
        Indique si le nom de l'acteur est trop générique.

        Ce signal sera utilisé plus tard par le Context Extractor
        et le Persona Builder.
        """
        return comparison_key(self.name) in _GENERIC_ACTORS


class ProblemContext(BaseModel):
    """
    Structure universelle du problème.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    actors_affected: List[str] = Field(
        default_factory=list,
    )

    pain: str = ""
    frequency: str = ""
    severity: str = ""

    current_alternatives: List[str] = Field(
        default_factory=list,
    )

    consequences: List[str] = Field(
        default_factory=list,
    )

    @field_validator(
        "pain",
        "frequency",
        "severity",
        mode="before",
    )
    @classmethod
    def clean_fields(
        cls,
        value: Any,
    ) -> str:
        return clean_text(value)

    @field_validator(
        "actors_affected",
        "current_alternatives",
        "consequences",
        mode="before",
    )
    @classmethod
    def clean_lists(
        cls,
        value: Any,
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            value = [value]

        return unique_texts(value)


class SolutionContext(BaseModel):
    """
    Structure universelle de la solution.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    mechanism: str = ""
    core_value: str = ""
    delivery_mode: str = ""

    required_capabilities: List[str] = Field(
        default_factory=list,
    )

    differentiators: List[str] = Field(
        default_factory=list,
    )

    @field_validator(
        "mechanism",
        "core_value",
        "delivery_mode",
        mode="before",
    )
    @classmethod
    def clean_fields(
        cls,
        value: Any,
    ) -> str:
        return clean_text(value)

    @field_validator(
        "required_capabilities",
        "differentiators",
        mode="before",
    )
    @classmethod
    def clean_lists(
        cls,
        value: Any,
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            value = [value]

        return unique_texts(value)


class WorkflowContext(BaseModel):
    """
    Représente une vraie action métier.

    Une limitation de périmètre comme :
        "limité à une serre"
        "première version dans une ville"
        "MVP pour cinq utilisateurs"

    ne doit jamais être placée dans ce modèle.

    Ces informations doivent être placées dans :
        ProjectContextPacketV3.mvp_scope
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    name: str = ""

    actor: str = ""
    action: str = ""
    object: str = ""
    result: str = ""
    output: str = ""
    frequency: str = ""

    is_explicit: bool = False

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    @field_validator(
        "name",
        "actor",
        "action",
        "object",
        "result",
        "output",
        "frequency",
        mode="before",
    )
    @classmethod
    def clean_fields(
        cls,
        value: Any,
    ) -> str:
        return clean_text(value)

    @computed_field
    @property
    def sentence(self) -> str:
        """
        Produit une représentation textuelle du workflow.
        """
        if self.name:
            return self.name

        base = clean_text(
            " ".join(
                part
                for part in (
                    self.action,
                    self.object,
                )
                if part
            )
        )

        if self.result:
            if base:
                base = f"{base} afin de {self.result}"
            else:
                base = self.result

        if self.output:
            if base:
                base = f"{base} et produire {self.output}"
            else:
                base = self.output

        return clean_text(base)

    @computed_field
    @property
    def is_actionable(self) -> bool:
        """
        Un workflow est exploitable lorsqu'il contient une action
        et au moins un objet, résultat ou livrable.
        """
        return bool(
            self.action
            and (
                self.object
                or self.result
                or self.output
            )
        )


class TransactionUnitContext(BaseModel):
    """
    Décrit l'unité de valeur ou d'échange principale du projet.

    Cette structure est universelle. Elle peut représenter :

    - un lot industriel échangé dans une marketplace ;
    - une réservation de service ;
    - une commande e-commerce ;
    - une intervention de maintenance ;
    - un dossier traité dans un SaaS ;
    - une opération terrain réalisée par un équipement ;
    - une analyse produite par un outil d'intelligence artificielle.

    Elle ne doit jamais être remplacée par une formule générique comme
    « transaction principale » lorsque l'objet réel est identifiable.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    name: str = ""

    description: str = ""

    object: str = ""

    supply_actor: str = ""

    demand_actor: str = ""

    initiation_action: str = ""

    completion_action: str = ""

    value_exchanged: str = ""

    payment_responsibility: str = ""

    fulfillment_responsibility: str = ""

    fulfillment_mode: str = ""

    trust_mechanism: str = ""

    dispute_responsibility: str = ""

    is_explicit: bool = False

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    @field_validator(
        "name",
        "description",
        "object",
        "supply_actor",
        "demand_actor",
        "initiation_action",
        "completion_action",
        "value_exchanged",
        "payment_responsibility",
        "fulfillment_responsibility",
        "fulfillment_mode",
        "trust_mechanism",
        "dispute_responsibility",
        mode="before",
    )
    @classmethod
    def clean_fields(
        cls,
        value: Any,
    ) -> str:
        return clean_text(value)

    @computed_field
    @property
    def sentence(self) -> str:
        """
        Produit une représentation lisible de l'unité transactionnelle.
        """
        if self.description:
            return self.description

        if self.name:
            return self.name

        base = clean_text(
            " ".join(
                part
                for part in (
                    self.initiation_action,
                    self.object,
                )
                if part
            )
        )

        if self.completion_action:
            if base:
                base = (
                    f"{base}, puis "
                    f"{self.completion_action}"
                )
            else:
                base = self.completion_action

        return clean_text(base)

    @computed_field
    @property
    def has_named_object(self) -> bool:
        """
        Indique si l'objet réel de la transaction est identifié.
        """
        return bool(
            self.object
            or self.name
        )

    @computed_field
    @property
    def has_two_sides(self) -> bool:
        """
        Indique si les deux côtés de l'échange sont identifiés.
        """
        return bool(
            self.supply_actor
            and self.demand_actor
        )


class ContextConfidence(BaseModel):
    """
    Résultat du gate de qualité du contexte.
    """

    model_config = ConfigDict(
        extra="ignore",
    )

    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    status: ContextReadinessStatus = (
        ContextReadinessStatus.INSUFFICIENT_CONTEXT
    )

    missing_fields: List[str] = Field(
        default_factory=list,
    )

    ambiguous_fields: List[str] = Field(
        default_factory=list,
    )

    blockers: List[str] = Field(
        default_factory=list,
    )

    clarification_questions: List[str] = Field(
        default_factory=list,
    )

    reasons: List[str] = Field(
        default_factory=list,
    )

    @field_validator(
        "missing_fields",
        "ambiguous_fields",
        "blockers",
        "clarification_questions",
        "reasons",
        mode="before",
    )
    @classmethod
    def clean_lists(
        cls,
        value: Any,
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            value = [value]

        return unique_texts(value)

    @model_validator(mode="after")
    def derive_status(
        self,
    ) -> "ContextConfidence":
        """
        Déduit le statut à partir du score, des champs manquants,
        des ambiguïtés et des blocages.

        READY signifie que le contexte est suffisamment complet
        et qu'aucune ambiguïté importante ne reste.

        READY_CAUTIOUS signifie que l'analyse peut commencer,
        mais que certaines hypothèses devront rester explicites.
        """
        if (
            self.status
            == ContextReadinessStatus.OUT_OF_SCOPE
        ):
            return self

        has_missing_fields = bool(
            self.missing_fields
        )

        has_ambiguities = bool(
            self.ambiguous_fields
        )

        has_blockers = bool(
            self.blockers
        )

        if (
            self.score >= 0.80
            and not has_blockers
            and not has_missing_fields
            and not has_ambiguities
        ):
            status = (
                ContextReadinessStatus.READY
            )

        elif (
            self.score >= 0.75
            and not has_blockers
        ):
            status = (
                ContextReadinessStatus.READY_CAUTIOUS
            )

        elif self.score >= 0.50:
            status = (
                ContextReadinessStatus.NEEDS_CLARIFICATION
            )

        else:
            status = (
                ContextReadinessStatus.INSUFFICIENT_CONTEXT
            )

        object.__setattr__(
            self,
            "status",
            status,
        )

        return self

    @computed_field
    @property
    def ready_for_agents(self) -> bool:
        return self.status in {
            ContextReadinessStatus.READY,
            ContextReadinessStatus.READY_CAUTIOUS,
        }


class ProjectContextPacketV3(BaseModel):
    """
    Contrat canonique universel partagé par tous les agents ForgeAI.

    Tous les agents devront lire ce même objet afin d'éviter :
    - les acteurs contradictoires ;
    - les workflows différents ;
    - les termes métier interdits par erreur ;
    - les personas génériques ;
    - les recherches web incohérentes.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    schema_version: Literal[
        "project_context_v3"
    ] = "project_context_v3"

    project_name: str = ""
    description: str = ""
    language: str = "fr"
    target_region: str = ""
    industry_user_input: str = ""

    sector_labels: List[str] = Field(
        default_factory=list,
    )

    primary_archetype: str = (
        "generic_digital_product"
    )

    archetype_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    secondary_archetypes: List[str] = Field(
        default_factory=list,
    )

    critical_contradictions: List[str] = Field(
        default_factory=list,
    )

    risk_domains: List[str] = Field(
        default_factory=list,
    )

    problem: ProblemContext = Field(
        default_factory=ProblemContext,
    )

    solution: SolutionContext = Field(
        default_factory=SolutionContext,
    )

    actors: List[ActorContext] = Field(
        default_factory=list,
    )

    payer_actor_names: List[str] = Field(
        default_factory=list,
    )

    decision_maker_actor_names: List[str] = Field(
        default_factory=list,
    )

    partner_actor_names: List[str] = Field(
        default_factory=list,
    )

    blocker_actor_names: List[str] = Field(
        default_factory=list,
    )

    priority_workflows: List[WorkflowContext] = Field(
        default_factory=list,
    )

    transaction_unit: TransactionUnitContext = Field(
        default_factory=TransactionUnitContext,
    )

    mvp_scope: List[str] = Field(
        default_factory=list,
    )

    deployment_environment: List[str] = Field(
        default_factory=list,
    )

    success_metrics: List[str] = Field(
        default_factory=list,
    )

    business_model_hypotheses: List[str] = Field(
        default_factory=list,
    )

    constraints: List[str] = Field(
        default_factory=list,
    )

    regulatory_flags: List[str] = Field(
        default_factory=list,
    )

    domain_terms: List[str] = Field(
        default_factory=list,
    )

    use_case_terms: List[str] = Field(
        default_factory=list,
    )

    solution_terms: List[str] = Field(
        default_factory=list,
    )

    target_terms: List[str] = Field(
        default_factory=list,
    )

    forbidden_adjacent_domains: List[str] = Field(
        default_factory=list,
    )

    assumptions: List[str] = Field(
        default_factory=list,
    )

    blocking_missing_fields: List[str] = Field(
        default_factory=list,
    )

    validation_warnings: List[str] = Field(
        default_factory=list,
    )

    confidence: ContextConfidence = Field(
        default_factory=ContextConfidence,
    )

    @field_validator(
        "project_name",
        "description",
        "target_region",
        "industry_user_input",
        "primary_archetype",
        mode="before",
    )
    @classmethod
    def clean_fields(
        cls,
        value: Any,
    ) -> str:
        return clean_text(value)

    @field_validator(
        "language",
        mode="before",
    )
    @classmethod
    def clean_language(
        cls,
        value: Any,
    ) -> str:
        return normalize_language(value)

    @field_validator(
        "sector_labels",
        "secondary_archetypes",
        "critical_contradictions",
        "risk_domains",
        "payer_actor_names",
        "decision_maker_actor_names",
        "partner_actor_names",
        "blocker_actor_names",
        "mvp_scope",
        "deployment_environment",
        "success_metrics",
        "business_model_hypotheses",
        "constraints",
        "regulatory_flags",
        "domain_terms",
        "use_case_terms",
        "solution_terms",
        "target_terms",
        "forbidden_adjacent_domains",
        "assumptions",
        "blocking_missing_fields",
        "validation_warnings",
        mode="before",
    )
    @classmethod
    def clean_string_lists(
        cls,
        value: Any,
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            value = [value]

        return unique_texts(value)

    @field_validator(
        "actors",
        mode="before",
    )
    @classmethod
    def normalize_actors(
        cls,
        value: Any,
    ) -> List[Any]:
        """
        Accepte le nouveau format et l'ancien dictionnaire
        généré par ProjectArchetypeResolver.
        """
        if value is None:
            return []

        role_aliases = {
            "demand_side": ActorRole.USER.value,
            "primary_user": ActorRole.USER.value,
            "supply_side": ActorRole.PROVIDER.value,
            "operator_or_partner": ActorRole.PARTNER.value,
        }

        valid_roles = {
            actor_role.value
            for actor_role in ActorRole
        }

        if isinstance(value, dict):
            output: List[Dict[str, Any]] = []

            for raw_role, raw_actor in value.items():
                role = role_aliases.get(
                    str(raw_role),
                    str(raw_role),
                )

                if role not in valid_roles:
                    role = ActorRole.OTHER.value

                actors = (
                    raw_actor
                    if isinstance(
                        raw_actor,
                        (
                            list,
                            tuple,
                            set,
                        ),
                    )
                    else [raw_actor]
                )

                for actor in actors:
                    actor_name = clean_text(actor)

                    if not actor_name:
                        continue

                    output.append(
                        {
                            "name": actor_name,
                            "role": role,
                        }
                    )

            return output

        actors = (
            value
            if isinstance(
                value,
                (
                    list,
                    tuple,
                    set,
                ),
            )
            else [value]
        )

        output: List[Any] = []

        for actor in actors:
            if isinstance(actor, str):
                actor_name = clean_text(actor)

                if actor_name:
                    output.append(
                        {
                            "name": actor_name,
                            "role": ActorRole.OTHER.value,
                        }
                    )

            elif isinstance(actor, dict):
                actor_name = clean_text(
                    actor.get("name")
                )

                if actor_name:
                    output.append(actor)

            elif isinstance(actor, ActorContext):
                output.append(actor)

        return output

    @field_validator(
        "priority_workflows",
        mode="before",
    )
    @classmethod
    def normalize_workflows(
        cls,
        value: Any,
    ) -> List[Any]:
        """
        Accepte une chaîne, une liste de chaînes ou des objets structurés.
        """
        if value is None:
            return []

        workflows = (
            value
            if isinstance(
                value,
                (
                    list,
                    tuple,
                    set,
                ),
            )
            else [value]
        )

        output: List[Any] = []

        for workflow in workflows:
            if isinstance(workflow, str):
                workflow_name = clean_text(workflow)

                if workflow_name:
                    output.append(
                        {
                            "name": workflow_name,
                        }
                    )

            elif isinstance(
                workflow,
                (
                    dict,
                    WorkflowContext,
                ),
            ):
                output.append(workflow)

        return output

    @field_validator(
        "transaction_unit",
        mode="before",
    )
    @classmethod
    def normalize_transaction_unit(
        cls,
        value: Any,
    ) -> Any:
        """
        Accepte le nouveau format structuré ainsi qu'une ancienne chaîne.

        Une chaîne existante est conservée comme nom et description.
        """
        if value is None:
            return {}

        if isinstance(value, str):
            text = clean_text(value)

            if not text:
                return {}

            return {
                "name": text,
                "description": text,
            }

        if isinstance(
            value,
            (
                dict,
                TransactionUnitContext,
            ),
        ):
            return value

        return {}

    @model_validator(mode="after")
    def enforce_invariants(
        self,
    ) -> "ProjectContextPacketV3":
        """
        Applique les protections générales du contexte.
        """
        warnings = list(
            self.validation_warnings
        )

        core_terms = unique_texts(
            self.sector_labels
            + self.domain_terms
            + self.use_case_terms
            + self.solution_terms
            + self.target_terms
        )

        core_keys = {
            comparison_key(term)
            for term in core_terms
        }

        removed_forbidden_terms = [
            term
            for term in self.forbidden_adjacent_domains
            if comparison_key(term) in core_keys
        ]

        safe_forbidden_terms = [
            term
            for term in self.forbidden_adjacent_domains
            if comparison_key(term) not in core_keys
        ]

        object.__setattr__(
            self,
            "forbidden_adjacent_domains",
            safe_forbidden_terms,
        )

        if removed_forbidden_terms:
            warnings.append(
                "Removed project core terms from "
                "forbidden_adjacent_domains: "
                + ", ".join(
                    removed_forbidden_terms
                )
            )

        scope_keys = {
            comparison_key(item)
            for item in self.mvp_scope
        }

        workflow_keys = {
            comparison_key(
                workflow.sentence
            )
            for workflow in self.priority_workflows
            if workflow.sentence
        }

        if scope_keys & workflow_keys:
            warnings.append(
                "A priority workflow duplicates the MVP "
                "scope and must be re-extracted."
            )

        explicit_actors_exist = any(
            actor.is_explicit
            for actor in self.actors
        )

        if explicit_actors_exist:
            generic_inferred_actors = [
                actor.name
                for actor in self.actors
                if (
                    not actor.is_explicit
                    and actor.is_generic
                )
            ]

            if generic_inferred_actors:
                warnings.append(
                    "Generic inferred actors remain despite "
                    "explicit actors: "
                    + ", ".join(
                        generic_inferred_actors
                    )
                )

        if (
            self.transaction_unit.supply_actor
            and self.transaction_unit.demand_actor
            and comparison_key(
                self.transaction_unit.supply_actor
            )
            == comparison_key(
                self.transaction_unit.demand_actor
            )
        ):
            warnings.append(
                "Transaction supply and demand actors "
                "must not be identical."
            )

        object.__setattr__(
            self,
            "validation_warnings",
            unique_texts(warnings),
        )

        return self

    @computed_field
    @property
    def ready_for_agents(self) -> bool:
        """
        Retourne la décision canonique disponible dans le packet.

        Les champs bloquants et les contradictions critiques
        ne peuvent jamais être ignorés, même si l'ancien objet
        ContextConfidence indique READY ou READY_CAUTIOUS.
        """
        return bool(
            self.confidence.ready_for_agents
            and not self.blocking_missing_fields
            and not self.critical_contradictions
        )

    @computed_field
    @property
    def primary_workflow(
        self,
    ) -> Optional[WorkflowContext]:
        """
        Retourne en priorité le premier workflow réellement actionnable.
        """
        for workflow in self.priority_workflows:
            if workflow.is_actionable:
                return workflow

        if self.priority_workflows:
            return self.priority_workflows[0]

        return None

    def actor_names(
        self,
        *,
        explicit_only: bool = False,
    ) -> List[str]:
        """
        Retourne les noms d'acteurs sans doublons.
        """
        return unique_texts(
            actor.name
            for actor in self.actors
            if (
                actor.name
                and (
                    actor.is_explicit
                    or not explicit_only
                )
            )
        )

    def to_legacy_dict(
        self,
    ) -> Dict[str, Any]:
        """
        Produit temporairement les anciennes clés utilisées par
        les agents Sprint 3.

        Cela permet d'intégrer le nouveau contrat progressivement
        sans casser immédiatement les agents existants.
        """
        workflow_sentences = unique_texts(
            workflow.sentence
            for workflow in self.priority_workflows
            if workflow.sentence
        )

        target_users = (
            self.actor_names(
                explicit_only=True,
            )
            or self.actor_names()
        )

        actors: Dict[str, str] = {}

        for actor in self.actors:
            actors.setdefault(
                actor.role.value,
                actor.name,
            )

        industry = (
            self.industry_user_input
            or (
                self.sector_labels[0]
                if self.sector_labels
                else ""
            )
        )

        main_workflow = (
            workflow_sentences[0]
            if workflow_sentences
            else ""
        )

        combined_blockers = unique_texts(
            [
                *self.blocking_missing_fields,
                *self.confidence.blockers,
            ]
        )

        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "title": self.project_name,
            "description": self.description,
            "output_language": self.language,
            "industry": industry,
            "market_region": self.target_region,
            "target_region": self.target_region,
            "project_archetype": self.primary_archetype,
            "archetype_confidence": (
                self.archetype_confidence
            ),
            "secondary_archetypes": list(
                self.secondary_archetypes
            ),
            "critical_contradictions": list(
                self.critical_contradictions
            ),
            "problem": self.problem.pain,
            "solution": self.solution.mechanism,
            "target_users": target_users,
            "actors": actors,
            "actor_details": [
                actor.model_dump(
                    mode="json",
                    exclude={
                        "is_generic",
                    },
                )
                for actor in self.actors
            ],
            "priority_workflow": main_workflow,
            "main_use_case": main_workflow,
            "priority_workflows": workflow_sentences,
            "transaction_unit": (
                self.transaction_unit.model_dump(
                    mode="json",
                )
            ),
            "transaction_unit_text": (
                self.transaction_unit.sentence
            ),
            "mvp_scope": ", ".join(
                self.mvp_scope
            ),
            "mvp_scope_items": list(
                self.mvp_scope
            ),
            "deployment_environment": list(
                self.deployment_environment
            ),
            "success_metrics": list(
                self.success_metrics
            ),
            "business_model": "; ".join(
                self.business_model_hypotheses
            ),
            "constraints": list(
                self.constraints
            ),
            "regulatory_flags": list(
                self.regulatory_flags
            ),
            "domain_terms": list(
                self.domain_terms
            ),
            "use_case_terms": list(
                self.use_case_terms
            ),
            "solution_terms": list(
                self.solution_terms
            ),
            "target_terms": list(
                self.target_terms
            ),
            "forbidden_adjacent_domains": list(
                self.forbidden_adjacent_domains
            ),
            "assumptions": list(
                self.assumptions
            ),
            "context_confidence": (
                self.confidence.model_dump(
                    mode="json",
                )
            ),
            "missing_fields": list(
                self.confidence.missing_fields
            ),
            "ambiguous_fields": list(
                self.confidence.ambiguous_fields
            ),
            "blocking_missing_fields": list(
                self.blocking_missing_fields
            ),
            "blockers": combined_blockers,
            "ready_for_agents": (
                self.ready_for_agents
            ),
            "validation_warnings": list(
                self.validation_warnings
            ),
        }