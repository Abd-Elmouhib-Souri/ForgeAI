from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Dict, List, Sequence
from urllib.parse import urlparse, urlunparse


class SourceRoleResolver:
    """Resolve the business relationship between a source and a project.

    Page shape and business role are deliberately separated.

    The resolver is domain-neutral. Operational equivalence is derived from
    the project's semantic context and from explicit actions found in the
    source, never from hard-coded sector or vertical names.
    """

    # ================================================================
    # Generic technology-supplier semantics
    # ================================================================

    TECHNOLOGY_PROVIDER_STRONG_SIGNALS = {
        "white label",
        "technology provider",
        "solution provider",
        "developer platform",
        "developer api",
        "api integration",
        "integration platform",
        "software development kit",
        "sdk",
        "software for businesses",
        "software for companies",
        "software for operators",
        "platform for operators",
        "build your own",
        "launch your own",
        "reseller platform",
        "implementation partner",
        "systems integrator",
    }

    TECHNOLOGY_PROVIDER_SUPPORT_SIGNALS = {
        "api",
        "integration",
        "integrations",
        "request demo",
        "contact sales",
        "enterprise",
        "saas",
        "b2b",
        "developer",
        "developers",
        "customizable",
        "customisable",
        "deployment",
        "implementation",
    }

    # ================================================================
    # Generic market-evidence semantics
    # ================================================================

    MARKET_PAGE_SIGNALS = {
        "market size",
        "market report",
        "market forecast",
        "market growth",
        "market share",
        "industry report",
        "industry outlook",
        "growth analysis",
        "forecast 20",
        "cagr",
        "research and markets",
        "etude de marche",
        "taille du marche",
        "previsions du marche",
    }

    MARKET_DOMAINS = {
        "researchandmarkets.com",
        "mordorintelligence.com",
        "technavio.com",
        "techsciresearch.com",
        "coherentmarketinsights.com",
        "grandviewresearch.com",
        "fortunebusinessinsights.com",
        "marketdataforecast.com",
        "psmarketresearch.com",
        "straitsresearch.com",
        "statista.com",
    }

    MARKET_TYPES = {
        "market_article",
        "market_evidence",
    }

    OFFICIAL_TYPES = {
        "official_source",
        "regulation",
    }

    ROLE_TO_CANONICAL_CATEGORY = {
        "direct_competitor": "direct_competitor",
        "adjacent_solution": "adjacent_solution",
        "regional_benchmark": "technology_benchmark",
        "international_benchmark": "technology_benchmark",
        "technology_provider": "technology_benchmark",
        "market_evidence": "market_evidence",
        "official_evidence": "market_evidence",
        "directory": "market_evidence",
        "local_ecosystem": "ecosystem_actor",
        "irrelevant": "irrelevant",
    }

    # ================================================================
    # Generic operational action vocabulary
    # ================================================================

    OPERATION_ACTION_PATTERNS = (
        (
            "book",
            re.compile(
                r"\b(?:"
                r"book(?:s|ed|ing)?"
                r"|reserv(?:e|es|ed|ing)?"
                r"|reserv(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "request",
            re.compile(
                r"\b(?:"
                r"request(?:s|ed|ing)?"
                r"|demand(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "order",
            re.compile(
                r"\b(?:"
                r"order(?:s|ed|ing)?"
                r"|command(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "buy",
            re.compile(
                r"\b(?:"
                r"buy|buys|buying|bought"
                r"|purchas(?:e|es|ed|ing)"
                r"|achet(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "sell",
            re.compile(
                r"\b(?:"
                r"sell|sells|selling|sold"
                r"|vend(?:re|s|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "publish",
            re.compile(
                r"\b(?:"
                r"publish(?:es|ed|ing)?"
                r"|publ(?:ier|ie|ient)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "submit",
            re.compile(
                r"\b(?:"
                r"submit(?:s|ted|ting)?"
                r"|apply|applies|applied|applying"
                r"|soumet(?:tre|s|tent)?"
                r"|postul(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "schedule",
            re.compile(
                r"\b(?:"
                r"schedule(?:s|d|ing)?"
                r"|planif(?:ier|ie|ient)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "create",
            re.compile(
                r"\b(?:"
                r"create(?:s|d|ing)?"
                r"|cre(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "record",
            re.compile(
                r"\b(?:"
                r"record(?:s|ed|ing)?"
                r"|enregistr(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "approve",
            re.compile(
                r"\b(?:"
                r"approve(?:s|d|ing)?"
                r"|approuv(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "notify",
            re.compile(
                r"\b(?:"
                r"notify|notifies|notified|notifying"
                r"|notifi(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "track",
            re.compile(
                r"\b(?:"
                r"track(?:s|ed|ing)?"
                r"|suiv(?:re|i|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "monitor",
            re.compile(
                r"\b(?:"
                r"monitor(?:s|ed|ing)?"
                r"|surveill(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "detect",
            re.compile(
                r"\b(?:"
                r"detect(?:s|ed|ing)?"
                r"|detect(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "inspect",
            re.compile(
                r"\b(?:"
                r"inspect(?:s|ed|ing)?"
                r"|inspect(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "manage",
            re.compile(
                r"\b(?:"
                r"manage(?:s|d|ment|ing)?"
                r"|ger(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "connect",
            re.compile(
                r"\b(?:"
                r"connect(?:s|ed|ing)?"
                r"|match(?:es|ed|ing)?"
                r"|mettre en relation"
                r"|mise en relation"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "find",
            re.compile(
                r"\b(?:"
                r"find|finds|finding|found"
                r"|search(?:es|ed|ing)?"
                r"|trouv(?:er|e|ent)?"
                r"|recherch(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "send",
            re.compile(
                r"\b(?:"
                r"send|sends|sending|sent"
                r"|envoy(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "pay",
            re.compile(
                r"\b(?:"
                r"pay|pays|paid|paying|payment"
                r"|paiement"
                r"|pay(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "assign",
            re.compile(
                r"\b(?:"
                r"assign(?:s|ed|ing)?"
                r"|affect(?:er|e|ent)?"
                r")\b",
                re.IGNORECASE,
            ),
        ),
        (
            "export",
            re.compile(
                r"\bexport(?:s|ed|ing|er|e|ent)?\b",
                re.IGNORECASE,
            ),
        ),
    )

    GENERIC_SEMANTIC_TOKENS = {
        "app",
        "application",
        "applications",
        "platform",
        "plateforme",
        "software",
        "logiciel",
        "solution",
        "solutions",
        "service",
        "services",
        "system",
        "systems",
        "product",
        "products",
        "digital",
        "mobile",
        "online",
        "business",
        "businesses",
        "company",
        "companies",
        "entreprise",
        "entreprises",
        "technology",
        "technologie",
        "market",
        "marche",
        "local",
        "regional",
        "international",
        "tunisia",
        "tunisie",
        "create",
        "creer",
        "relation",
        "management",
        "gestion",
    }

    # ================================================================
    # Public API
    # ================================================================

    def resolve(
        self,
        *,
        source: Dict[str, Any],
        decision: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = self._context(
            project_context
        )

        source_type = str(
            decision.get("source_type")
            or "irrelevant"
        ).strip().lower()

        region_match = str(
            decision.get("region_match")
            or "unknown"
        ).strip().lower()

        source_text = self._normalize(
            " ".join(
                str(source.get(key) or "")
                for key in (
                    "title",
                    "url",
                    "snippet",
                    "body",
                    "extracted_text_preview",
                )
            )
        )

        product_page = bool(
            decision.get("is_product_page")
        )

        same_target = bool(
            decision.get(
                "same_or_close_target_user"
            )
        )

        same_use_case = bool(
            decision.get(
                "same_or_close_use_case"
            )
        )

        same_solution = bool(
            decision.get(
                "same_or_close_solution_category"
            )
        )

        sector_mismatch = bool(
            decision.get("sector_mismatch")
        )

        market_evidence_page = (
            self._is_market_evidence_page(
                source,
                source_text,
            )
        )

        technology_supplier = (
            self._is_technology_supplier(
                source_text=source_text,
                product_page=product_page,
                same_use_case=same_use_case,
                same_solution=same_solution,
            )
        )

        consumer_operation = (
            self._is_consumer_operation(
                source_text=source_text,
                context=context,
                technology_supplier=(
                    technology_supplier
                ),
                same_use_case=same_use_case,
                same_solution=same_solution,
            )
        )

        operation_equivalent = (
            self._is_operation_equivalent(
                source_text=source_text,
                context=context,
                consumer_operation=(
                    consumer_operation
                ),
                technology_supplier=(
                    technology_supplier
                ),
                sector_mismatch=sector_mismatch,
                same_use_case=same_use_case,
                same_solution=same_solution,
            )
        )

        # Operational equivalence establishes workflow/solution proximity.
        # It does not invent target identity.
        if operation_equivalent:
            same_use_case = True
            same_solution = True

        target_compatible = self._target_compatible(
            source_text=source_text,
            context=context,
            same_target=same_target,
        )

        target_evidence_available = bool(
            same_target
            or context.get(
                "target_terms"
            )
        )

        # Missing actor authority is UNKNOWN, not a proven mismatch.
        #
        # Actor compatibility belongs to local directness. It must not
        # erase a legitimate regional/international benchmark whose
        # workflow and solution are otherwise strongly comparable.
        target_not_mismatched = bool(
            target_compatible
            or not target_evidence_available
        )

        product_or_operation = bool(
            product_page
            or consumer_operation
        )

        operational_business_match = bool(
            (
                operation_equivalent
                or same_use_case
                or same_solution
            )
            and not sector_mismatch
        )

        # Upstream lexical/classifier proximity is useful evidence,
        # but cannot establish local direct competition on its own.
        #
        # Direct competition requires source-side corroboration:
        # either canonical operational equivalence, or evidence across
        # at least two independent semantic axes.
        #
        # Benchmark classification deliberately keeps the broader
        # operational_business_match contract.
        local_direct_overlap = (
            self._semantic_overlap(
                source_text=source_text,
                context=context,
            )
        )

        local_direct_corroborated = bool(
            operation_equivalent
            or (
                local_direct_overlap.get(
                    "semantic_axes",
                    0,
                )
                >= 2
            )
        )

        local_direct_match = bool(
            target_not_mismatched
            and operational_business_match
            and local_direct_corroborated
        )

        benchmark_match = (
            operational_business_match
        )

        if source_type in self.OFFICIAL_TYPES:
            source_role = "official_evidence"
            comparison_scope = "evidence"
            legacy_type = source_type

        elif source_type == "local_ecosystem":
            source_role = "local_ecosystem"
            comparison_scope = "ecosystem"
            legacy_type = source_type

        elif source_type == "directory":
            source_role = "directory"
            comparison_scope = "evidence"
            legacy_type = source_type

        elif (
            source_type in self.MARKET_TYPES
            or market_evidence_page
        ):
            source_role = "market_evidence"
            comparison_scope = "evidence"
            legacy_type = "market_article"

        elif technology_supplier:
            source_role = "technology_provider"
            comparison_scope = (
                "technology_benchmark"
            )
            legacy_type = (
                "technology_benchmark"
            )

        elif source_type == "technology_benchmark":
            source_role = "technology_provider"
            comparison_scope = (
                "technology_benchmark"
            )
            legacy_type = (
                "technology_benchmark"
            )
            technology_supplier = True

        elif (
            region_match == "local"
            and product_or_operation
            and local_direct_match
        ):
            source_role = "direct_competitor"
            comparison_scope = "local_direct"
            legacy_type = "competitor"

        elif (
            region_match in {
                "regional",
                "international",
            }
            and product_or_operation
            and benchmark_match
        ):
            source_role = (
                "regional_benchmark"
                if region_match == "regional"
                else "international_benchmark"
            )
            comparison_scope = source_role
            # Geography is comparison scope. A non-local equivalent
            # must never leak back as a local/direct competitor type.
            legacy_type = "adjacent_solution"

        elif (
            product_or_operation
            and not sector_mismatch
        ):
            source_role = "adjacent_solution"
            comparison_scope = (
                "local_adjacent"
                if region_match == "local"
                else "adjacent"
            )
            legacy_type = "adjacent_solution"

        elif source_type == "adjacent_solution":
            source_role = "adjacent_solution"
            comparison_scope = (
                "local_adjacent"
                if region_match == "local"
                else "adjacent"
            )
            legacy_type = "adjacent_solution"

        else:
            source_role = "irrelevant"
            comparison_scope = "irrelevant"
            legacy_type = "irrelevant"

        canonical_category = (
            self.ROLE_TO_CANONICAL_CATEGORY.get(
                source_role,
                "irrelevant",
            )
        )

        return {
            "source_role": source_role,
            "canonical_category": (
                canonical_category
            ),
            "comparison_scope": comparison_scope,
            "technology_supplier": (
                technology_supplier
            ),
            "consumer_operation": (
                consumer_operation
            ),
            "market_evidence_page": (
                market_evidence_page
            ),
            "operation_equivalent": (
                operation_equivalent
            ),
            "legacy_source_type": legacy_type,
            "canonical_source_id": (
                self._canonical_source_id(
                    source
                )
            ),
            "role_reason": self._role_reason(
                source_role=source_role,
                region_match=region_match,
                same_target=same_target,
                same_use_case=same_use_case,
                same_solution=same_solution,
                technology_supplier=(
                    technology_supplier
                ),
                consumer_operation=(
                    consumer_operation
                ),
                market_evidence_page=(
                    market_evidence_page
                ),
                operation_equivalent=(
                    operation_equivalent
                ),
            ),
        }

    # ================================================================
    # Universal operational equivalence
    # ================================================================

    def _target_compatible(
        self,
        *,
        source_text: str,
        context: Dict[str, Any],
        same_target: bool,
    ) -> bool:
        """
        Confirm target compatibility independently from workflow,
        solution and domain similarity.

        Operational equivalence must never invent actor identity.
        """

        if same_target:
            return True

        target_terms = self._unique_terms(
            context.get(
                "target_terms"
            )
            or []
        )

        if not target_terms:
            return False

        overlap = self._semantic_overlap(
            source_text=source_text,
            context=context,
        )

        # Exact/strong target phrase evidence remains authoritative.
        if overlap.get(
            "target_matches"
        ):
            return True

        source_tokens = set(
            self._significant_tokens(
                source_text
            )
        )

        if not source_tokens:
            return False

        # These broad heads are not sufficient by themselves to prove
        # business-actor compatibility. Exact target phrase matching
        # above may still confirm them.
        generic_actor_heads = {
            "user",
            "users",
            "utilisateur",
            "utilisateurs",
            "customer",
            "customers",
            "client",
            "clients",
            "consumer",
            "consumers",
            "company",
            "companies",
            "business",
            "businesses",
            "organization",
            "organizations",
            "organisation",
            "organisations",
            "enterprise",
            "enterprises",
            "entreprise",
            "entreprises",
            "individual",
            "individuals",
            "person",
            "people",
        }

        def forms(
            token: str,
        ) -> set[str]:
            values = {
                token
            }

            if (
                token.endswith(
                    "ies"
                )
                and len(
                    token
                ) > 4
            ):
                values.add(
                    token[:-3]
                    + "y"
                )

            elif (
                token.endswith(
                    "es"
                )
                and len(
                    token
                ) > 5
            ):
                values.add(
                    token[:-2]
                )

            elif (
                token.endswith(
                    "s"
                )
                and len(
                    token
                ) > 4
            ):
                values.add(
                    token[:-1]
                )

            return values

        source_forms: set[str] = set()

        for token in source_tokens:
            source_forms.update(
                forms(
                    token
                )
            )

        for target in target_terms:
            tokens = [
                token
                for token in self._significant_tokens(
                    target
                )
                if token
            ]

            if not tokens:
                continue

            # The final significant token normally carries the actor
            # role head: managers, supervisors, students, technicians,
            # responsables, op?rateurs, etc.
            head = tokens[-1]

            head_forms = forms(
                head
            )

            if (
                head_forms
                & generic_actor_heads
            ):
                continue

            if (
                head_forms
                & source_forms
            ):
                return True

        return False


    def _is_consumer_operation(
        self,
        *,
        source_text: str,
        context: Dict[str, Any],
        technology_supplier: bool,
        same_use_case: bool,
        same_solution: bool,
    ) -> bool:
        if technology_supplier:
            return False

        actions = self._operation_action_hits(
            source_text
        )

        if not actions:
            return False

        overlap = self._semantic_overlap(
            source_text=source_text,
            context=context,
        )

        # Upstream lexical/classifier proximity is only a hint.
        # Consumer-operation authority must be corroborated by evidence
        # found in the source itself.
        if overlap["strong_phrase_matches"]:
            return True

        if (
            overlap["semantic_axes"] >= 1
            and len(actions) >= 2
        ):
            return True

        if (
            len(overlap["token_overlap"]) >= 2
            and len(actions) >= 2
        ):
            return True

        return False

    def _is_operation_equivalent(
        self,
        *,
        source_text: str,
        context: Dict[str, Any],
        consumer_operation: bool,
        technology_supplier: bool,
        sector_mismatch: bool,
        same_use_case: bool,
        same_solution: bool,
    ) -> bool:
        """Resolve workflow equivalence from semantic evidence.

        No vertical or sector receives special treatment.

        A source must expose a real operation and enough project-specific
        semantic overlap to establish that it performs the same core job.
        """
        if (
            not consumer_operation
            or technology_supplier
            or sector_mismatch
        ):
            return False

        actions = self._operation_action_hits(
            source_text
        )

        if not actions:
            return False

        overlap = self._semantic_overlap(
            source_text=source_text,
            context=context,
        )

        # Upstream same-use-case / same-solution flags cannot establish
        # operational equivalence by themselves. The source must expose
        # project-specific workflow, use-case, solution, domain, target,
        # or sufficiently strong multi-action semantic evidence.
        if (
            overlap["workflow_matches"]
            or overlap["use_case_matches"]
        ):
            return True

        if (
            overlap["solution_matches"]
            and (
                overlap["domain_matches"]
                or overlap["target_matches"]
            )
        ):
            return True

        # Short live-service pages can expose a compact canonical
        # business-domain phrase plus limited operation detail.
        #
        # Two explicit source actions preserve the historical compact-page
        # fallback. With only one action, the action itself must also be
        # present in canonical workflow/use-case/solution context.
        context_operation_text = " ".join(
            self._text_values(
                context.get(
                    "use_case_terms"
                )
            )
            + self._text_values(
                context.get(
                    "workflow_terms"
                )
            )
            + self._text_values(
                context.get(
                    "solution_terms"
                )
            )
        )

        context_actions = set(
            self._operation_action_hits(
                context_operation_text
            )
        )

        shared_operation_actions = (
            set(actions)
            & context_actions
        )

        if (
            overlap["strong_domain_matches"]
            and (
                len(actions) >= 2
                or bool(
                    shared_operation_actions
                )
            )
        ):
            return True

        operational_semantic_axis = bool(
            overlap["workflow_matches"]
            or overlap["use_case_matches"]
            or overlap["solution_matches"]
        )

        if (
            overlap["semantic_axes"] >= 2
            and operational_semantic_axis
        ):
            return True

        if (
            len(overlap["token_overlap"]) >= 4
            and len(actions) >= 2
        ):
            return True

        return False

    def _semantic_overlap(
        self,
        *,
        source_text: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        domain_matches = (
            self._matched_context_terms(
                source_text,
                context.get(
                    "domain_concepts"
                ) or [],
            )
        )

        use_case_matches = (
            self._matched_context_terms(
                source_text,
                context.get(
                    "use_case_terms"
                ) or [],
            )
        )

        solution_matches = (
            self._matched_context_terms(
                source_text,
                context.get(
                    "solution_terms"
                ) or [],
            )
        )

        workflow_matches = (
            self._matched_context_terms(
                source_text,
                context.get(
                    "workflow_terms"
                ) or [],
            )
        )

        target_matches = (
            self._matched_context_terms(
                source_text,
                context.get(
                    "target_terms"
                ) or [],
            )
        )

        all_matches = self._unique_terms(
            domain_matches
            + use_case_matches
            + solution_matches
            + workflow_matches
            + target_matches
        )

        strong_phrase_matches = [
            term
            for term in all_matches
            if self._is_strong_phrase(
                term
            )
        ]

        strong_domain_matches = [
            term
            for term in domain_matches
            if self._is_strong_phrase(
                term
            )
        ]

        source_tokens = set(
            self._significant_tokens(
                source_text
            )
        )

        context_tokens = set()

        for key in (
            "domain_concepts",
            "use_case_terms",
            "solution_terms",
            "workflow_terms",
            "target_terms",
        ):
            for value in (
                context.get(key)
                or []
            ):
                context_tokens.update(
                    self._significant_tokens(
                        value
                    )
                )

        token_overlap = sorted(
            source_tokens
            & context_tokens
        )

        semantic_axes = sum(
            bool(values)
            for values in (
                domain_matches,
                use_case_matches,
                solution_matches,
                workflow_matches,
                target_matches,
            )
        )

        return {
            "domain_matches": domain_matches,
            "use_case_matches": (
                use_case_matches
            ),
            "solution_matches": (
                solution_matches
            ),
            "workflow_matches": (
                workflow_matches
            ),
            "target_matches": target_matches,
            "strong_phrase_matches": (
                strong_phrase_matches
            ),
            "strong_domain_matches": (
                strong_domain_matches
            ),
            "token_overlap": token_overlap,
            "semantic_axes": semantic_axes,
        }

    # ================================================================
    # Technology and market roles
    # ================================================================

    def _is_market_evidence_page(
        self,
        source: Dict[str, Any],
        source_text: str,
    ) -> bool:
        domain = self._domain(
            str(
                source.get("url")
                or source.get("href")
                or ""
            )
        )

        signal_hits = sum(
            1
            for term in self.MARKET_PAGE_SIGNALS
            if self._term_in_text(
                term,
                source_text,
            )
        )

        if (
            domain in self.MARKET_DOMAINS
            and signal_hits >= 1
        ):
            return True

        supplier_hits = len(
            self._technology_provider_hits(
                source_text
            )
        )

        operation_hits = len(
            self._operation_action_hits(
                source_text
            )
        )

        if (
            signal_hits >= 2
            and supplier_hits == 0
            and operation_hits < 2
        ):
            return True

        return False

    def _is_technology_supplier(
        self,
        *,
        source_text: str,
        product_page: bool,
        same_use_case: bool,
        same_solution: bool,
    ) -> bool:
        if not product_page:
            return False

        strong_hits = [
            term
            for term
            in self.TECHNOLOGY_PROVIDER_STRONG_SIGNALS
            if self._term_in_text(
                term,
                source_text,
            )
        ]

        support_hits = [
            term
            for term
            in self.TECHNOLOGY_PROVIDER_SUPPORT_SIGNALS
            if self._term_in_text(
                term,
                source_text,
            )
        ]

        if "white label" in strong_hits:
            return True

        if len(strong_hits) >= 2:
            return True

        if (
            strong_hits
            and (
                support_hits
                or same_solution
                or not same_use_case
            )
        ):
            return True

        return False

    def _technology_provider_hits(
        self,
        source_text: str,
    ) -> List[str]:
        return self._unique_terms(
            [
                term
                for term in (
                    self.TECHNOLOGY_PROVIDER_STRONG_SIGNALS
                    | self.TECHNOLOGY_PROVIDER_SUPPORT_SIGNALS
                )
                if self._term_in_text(
                    term,
                    source_text,
                )
            ]
        )

    # ================================================================
    # Context
    # ================================================================

    def _context(
        self,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        intelligence = (
            project_context.get(
                "project_intelligence"
            )
            or {}
        )

        structured = (
            project_context.get(
                "structured_project_context"
            )
            or intelligence.get(
                "structured_project_context"
            )
            or {}
        )

        packet = (
            project_context.get(
                "agent_context_packet"
            )
            or intelligence.get(
                "agent_context_packet"
            )
            or {}
        )

        archetype_context = (
            project_context.get(
                "archetype_context"
            )
            or packet.get(
                "archetype_context"
            )
            or intelligence.get(
                "archetype_context"
            )
            or {}
        )

        project_archetype = str(
            structured.get(
                "project_archetype"
            )
            or archetype_context.get(
                "project_archetype"
            )
            or "generic_digital_product"
        ).strip().lower()

        vertical = str(
            structured.get("vertical")
            or archetype_context.get(
                "vertical"
            )
            or "general"
        ).strip().lower()

        domain_concepts = (
            self._unique_terms(
                self._text_values(
                    structured.get(
                        "domain_concepts"
                    )
                )
                + self._text_values(
                    packet.get(
                        "domain_concepts"
                    )
                )
                + self._text_values(
                    project_context.get(
                        "domain_concepts"
                    )
                )
            )
        )

        if not domain_concepts:
            domain_concepts = (
                self._unique_terms(
                    self._text_values(
                        structured.get(
                            "search_concepts"
                        )
                    )
                    + self._text_values(
                        packet.get(
                            "search_concepts"
                        )
                    )
                )
            )

        if (
            not domain_concepts
            and vertical
            and vertical != "general"
        ):
            domain_concepts = [
                vertical
            ]

        use_case_terms = (
            self._unique_terms(
                self._text_values(
                    structured.get(
                        "use_case_terms"
                    )
                )
                + self._text_values(
                    structured.get(
                        "use_cases"
                    )
                )
                + self._text_values(
                    packet.get(
                        "use_case_terms"
                    )
                )
                + self._text_values(
                    project_context.get(
                        "use_case_terms"
                    )
                )
            )
        )

        workflow_terms = (
            self._unique_terms(
                self._text_values(
                    structured.get(
                        "priority_workflows"
                    )
                )
                + self._text_values(
                    packet.get(
                        "priority_workflows"
                    )
                )
                + self._text_values(
                    project_context.get(
                        "priority_workflows"
                    )
                )
            )
        )

        solution_terms = (
            self._unique_terms(
                self._text_values(
                    structured.get(
                        "solution_terms"
                    )
                )
                + self._text_values(
                    packet.get(
                        "solution_terms"
                    )
                )
                + self._text_values(
                    structured.get(
                        "solution_category"
                    )
                )
                + self._text_values(
                    project_context.get(
                        "solution_terms"
                    )
                )
            )
        )

        target_terms = (
            self._unique_terms(
                self._text_values(
                    structured.get(
                        "target_users"
                    )
                )
                + self._text_values(
                    packet.get(
                        "target_terms"
                    )
                )
                + self._text_values(
                    project_context.get(
                        "target_users"
                    )
                )
                + self._text_values(
                    project_context.get(
                        "target_terms"
                    )
                )
            )
        )

        return {
            "project_archetype": (
                project_archetype
            ),
            "vertical": vertical,
            "interaction_model": str(
                archetype_context.get(
                    "interaction_model"
                )
                or ""
            ).strip().lower(),
            "validation_unit": str(
                archetype_context.get(
                    "validation_unit"
                )
                or ""
            ).strip(),
            "domain_concepts": (
                domain_concepts
            ),
            "use_case_terms": (
                use_case_terms
            ),
            "workflow_terms": (
                workflow_terms
            ),
            "solution_terms": (
                solution_terms
            ),
            "target_terms": (
                target_terms
            ),
        }

    # ================================================================
    # Text helpers
    # ================================================================

    def _operation_action_hits(
        self,
        source_text: str,
    ) -> List[str]:
        output: List[str] = []

        for label, pattern in (
            self.OPERATION_ACTION_PATTERNS
        ):
            if pattern.search(
                source_text
            ):
                output.append(
                    label
                )

        return output

    def _matched_context_terms(
        self,
        source_text: str,
        values: Sequence[str],
    ) -> List[str]:
        output: List[str] = []

        for value in values:
            normalized = self._normalize(
                value
            )

            if len(normalized) < 3:
                continue

            if self._term_in_text(
                normalized,
                source_text,
            ):
                output.append(
                    value
                )

        return self._unique_terms(
            output
        )

    def _is_strong_phrase(
        self,
        value: str,
    ) -> bool:
        normalized = self._normalize(
            value
        )

        raw_tokens = [
            token
            for token in normalized.split()
            if len(token) >= 3
        ]

        significant = (
            self._significant_tokens(
                normalized
            )
        )

        return bool(
            len(raw_tokens) >= 2
            and significant
        )

    def _significant_tokens(
        self,
        value: str,
    ) -> List[str]:
        normalized = self._normalize(
            value
        )

        return [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                normalized,
            )
            if (
                len(token) >= 4
                and token
                not in self.GENERIC_SEMANTIC_TOKENS
            )
        ]

    @classmethod
    def _text_values(
        cls,
        value: Any,
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            cleaned = value.strip()
            return (
                [cleaned]
                if cleaned
                else []
            )

        if isinstance(value, dict):
            preferred_keys = (
                "name",
                "sentence",
                "action",
                "object",
                "result",
                "output",
            )

            preferred = []

            for key in preferred_keys:
                if key in value:
                    preferred.extend(
                        cls._text_values(
                            value.get(key)
                        )
                    )

            if preferred:
                return preferred

            output: List[str] = []

            for item in value.values():
                output.extend(
                    cls._text_values(
                        item
                    )
                )

            return output

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            output: List[str] = []

            for item in value:
                output.extend(
                    cls._text_values(
                        item
                    )
                )

            return output

        return []

    @classmethod
    def _unique_terms(
        cls,
        values: Sequence[str],
    ) -> List[str]:
        output: List[str] = []
        seen = set()

        for value in values:
            cleaned = str(
                value or ""
            ).strip()

            key = cls._normalize(
                cleaned
            )

            if (
                not cleaned
                or not key
                or key in seen
            ):
                continue

            seen.add(
                key
            )

            output.append(
                cleaned
            )

        return output

    # ================================================================
    # Source identity / diagnostics
    # ================================================================

    def _canonical_source_id(
        self,
        source: Dict[str, Any],
    ) -> str:
        url = self._canonical_url(
            str(
                source.get("url")
                or source.get("href")
                or ""
            )
        )

        fallback = self._normalize(
            f"{source.get('title', '')}|"
            f"{source.get('canonical_vendor_domain', '')}"
        )

        seed = (
            url
            or fallback
            or "unknown-source"
        )

        return (
            "src_"
            + hashlib.sha256(
                seed.encode("utf-8")
            ).hexdigest()[:20]
        )

    @staticmethod
    def _canonical_url(
        value: str,
    ) -> str:
        try:
            parsed = urlparse(
                value.strip()
            )
        except Exception:
            return ""

        if (
            parsed.scheme
            not in {"http", "https"}
            or not parsed.netloc
        ):
            return ""

        host = (
            parsed.netloc
            .lower()
            .split("@")[-1]
        )

        if host.startswith("www."):
            host = host[4:]

        path = re.sub(
            r"/{2,}",
            "/",
            parsed.path or "/",
        ).rstrip("/")

        return urlunparse(
            (
                "https",
                host,
                path,
                "",
                "",
                "",
            )
        )

    @staticmethod
    def _domain(
        value: str,
    ) -> str:
        try:
            host = (
                urlparse(
                    value.strip()
                )
                .netloc
                .lower()
                .split("@")[-1]
            )
        except Exception:
            return ""

        if host.startswith("www."):
            host = host[4:]

        return host.split(":")[0]

    def _role_reason(
        self,
        *,
        source_role: str,
        region_match: str,
        same_target: bool,
        same_use_case: bool,
        same_solution: bool,
        technology_supplier: bool,
        consumer_operation: bool,
        market_evidence_page: bool,
        operation_equivalent: bool,
    ) -> str:
        return (
            f"role={source_role} | "
            f"region={region_match} | "
            f"target_match={str(same_target).lower()} | "
            f"use_case_match={str(same_use_case).lower()} | "
            f"solution_match={str(same_solution).lower()} | "
            f"consumer_operation="
            f"{str(consumer_operation).lower()} | "
            f"technology_supplier="
            f"{str(technology_supplier).lower()} | "
            f"market_evidence_page="
            f"{str(market_evidence_page).lower()} | "
            f"operation_equivalent="
            f"{str(operation_equivalent).lower()}"
        )

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:
        text = unicodedata.normalize(
            "NFKD",
            str(value or ""),
        )

        text = "".join(
            char
            for char in text
            if not unicodedata.combining(
                char
            )
        )

        text = (
            text
            .lower()
            .replace("\u2019", "'")
            .replace("-", " ")
            .replace("_", " ")
        )

        text = re.sub(
            r"[^a-z0-9' ]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    @staticmethod
    def _term_in_text(
        term: str,
        text: str,
    ) -> bool:
        normalized = (
            SourceRoleResolver._normalize(
                term
            )
        )

        normalized_text = (
            SourceRoleResolver._normalize(
                text
            )
        )

        if not normalized:
            return False

        return bool(
            re.search(
                rf"(?<![a-z0-9])"
                rf"{re.escape(normalized)}"
                rf"(?![a-z0-9])",
                normalized_text,
            )
        )


source_role_resolver = SourceRoleResolver()
