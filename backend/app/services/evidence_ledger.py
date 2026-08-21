from __future__ import annotations

import hashlib
import re
import unicodedata
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable
from urllib.parse import urlparse


@dataclass
class EvidenceClaim:
    claim_id: str
    path: str
    category: str
    claim: str
    source_ids: list[str]
    status: str
    confidence: str
    public_text: str
    evidence_status: str
    claim_kind: str
    validation_required: bool


@dataclass(frozen=True)
class ClaimSpec:
    claim_id: str
    path: str
    category: str
    value: Any


class EvidenceLedger:
    """Canonical claim-to-evidence registry and publication policy.

    Source Intelligence V8 uses role-aware evidence categories such as
    ``market_size_claim`` and ``technology_benchmark``. This ledger normalizes
    those categories before matching claims. It remains conservative: a
    benchmark proves feasibility, not local demand; a market-report landing
    page is a market signal, not an independently verified market size.
    """

    # Canonical Evidence Ledger contract.
    #
    # ``status`` is temporarily retained as a backward-compatible alias
    # of ``evidence_status``. Consumers must not introduce another
    # evidence-status vocabulary.
    CANONICAL_EVIDENCE_STATUSES = (
        "sourced",
        "estimated",
        "not_confirmed",
    )

    CANONICAL_CLAIM_KINDS = (
        "evidence_claim",
        "hypothesis",
        "estimate",
        "recommendation",
        "audit_conclusion",
        "project_input",
    )

    PRECISE_NUMBER_RE = re.compile(
        r"(?:\b\d[\d\s,.]*\b|thousands?|hundreds?|millions?|billions?|"
        r"milliers?|centaines?|millions?|milliards?|\b\d+(?:[.,]\d+)?\s*%\b|"
        r"\b(?:TND|EUR|USD|GBP|MAD|DZD)\b)",
        re.IGNORECASE,
    )
    NUMBER_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)?")

    CATEGORY_ALIASES: dict[str, set[str]] = {
        "market_size": {"market_size", "market_size_claim"},
        "market_demand": {
            "market_demand",
            "market_demand_claim",
            "local_market_signal",
            "adoption_signal",
        },
        "market_context": {
            "regional_context",
            "sector_context",
            "local_market_signal",
        },
        "problem_context": {
            "problem_context",
            "workflow_context",
            "current_alternatives",
        },
        "solution_benchmark": {
            "solution_benchmark",
            "technology_benchmark",
            "competitor_product",
        },
        "solution_hypothesis": {
            "solution_benchmark",
            "technology_benchmark",
            "competitor_product",
        },
        "competitor_product": {"competitor_product", "direct_competitor"},
        "local_competition": {"competitor_product", "direct_competitor"},
        "pricing": {"pricing", "pricing_signal"},
        "regulation": {"regulation", "regulatory_evidence"},
        "finance": {"finance"},
    }

    CORE_CONFIDENCE_CATEGORIES = (
        "problem_context",
        "solution_benchmark",
        "competitor_product",
        "local_competition",
        "market_size",
        "market_demand",
        "pricing",
        "regulation",
        "finance",
    )

    LOW_METHODOLOGY_DOMAINS = {
        "scribd.com",
        "www.scribd.com",
        "marketsandmarkets.com",
        "www.marketsandmarkets.com",
        "marketresearchfuture.com",
        "www.marketresearchfuture.com",
        "snsinsider.com",
        "www.snsinsider.com",
        "rootsanalysis.com",
        "www.rootsanalysis.com",
        "ensun.io",
        "www.ensun.io",
        "fdatabot.com",
        "www.fdatabot.com",
    }

    SEMANTIC_STOPWORDS = {
        "avec", "dans", "pour", "plus", "moins", "cette", "cela", "comme",
        "ainsi", "afin", "entre", "sans", "sous", "vers", "leur", "leurs",
        "notre", "votre", "une", "des", "les", "aux", "sur", "est", "sont",
        "etre", "peut", "doit", "ajouter", "integrer", "developper",
        "envisager", "permettre", "faciliter", "reduire", "solution",
        "projet", "produit", "systeme", "technologie", "agriculture",
        "agricole", "agricoles", "robot", "robots", "intelligente",
        "intelligent", "tunisie", "tunisien", "tunisienne", "using", "with",
        "from", "into", "that", "this", "these", "those", "their", "about",
        "could", "should", "would", "allow", "enable", "develop", "integrate",
        "add", "solution", "project", "product", "system", "technology",
        "agriculture", "agricultural", "robot", "robots", "tunisia",
    }

    SOLUTION_CONCEPT_GROUPS: tuple[set[str], ...] = (
        {
            "recharge", "charging", "charge", "induction", "solaire",
            "solar", "photovoltaic", "photovoltaïque", "station",
        },
        {
            "pulverisation", "pulvérisation", "spraying", "spray",
            "pesticide", "traitement", "intrants",
        },
        {
            "crda", "commissariat", "ministere", "ministère",
            "partenariat", "partnership", "institutionnel", "institutional",
        },
        {
            "maintenance", "maintain", "support", "reparation", "réparation",
        },
        {
            "lorawan", "connectivite", "connectivité", "wifi", "4g", "5g",
            "telemetrie", "télémétrie",
        },
    )

    NON_CONFIRMATION_MARKERS = (
        "non confirmé",
        "non confirmée",
        "non confirmés",
        "non confirmées",
        "pas confirmé",
        "pas confirmée",
        "ne sont pas présentes",
        "n’est pas vérifiée",
        "n'est pas vérifiée",
        "ne sont pas vérifiées",
        "insufficiently verified",
        "not confirmed",
        "not verified",
        "no compatible evidence",
        "insufficient evidence",
        "aucune tendance de marché",
        "no market trend",
    )

    CAUTIOUS_SIGNAL_PREFIXES = (
        "signal à valider",
        "signal local à valider",
        "signal secondaire",
        "signal to validate",
        "local signal to validate",
        "secondary market signal",
    )

    ANALYTICAL_PATH_PREFIXES = (
        "market_study.market_overview",
        "market_study.local_context",
    )

    # Presentation-only labels added when analytical claims are
    # projected back into public market-study fields.
    #
    # These labels are NOT part of canonical claim authority.
    # Keeping the registry path-scoped prevents unrelated claims
    # from being rewritten merely because they begin with words
    # such as "Recommendation" or "Hypothesis".
    PUBLICATION_PREFIXES_BY_PATH = {
        "market_study.market_overview": (
            "Hypoth\u00e8se \u00e0 valider :",
            "Hypothesis to validate:",
        ),
        "market_study.local_context": (
            "Recommandation :",
            "Recommendation:",
        ),
        "market_study.local_feasibility": (
            "Conclusion prudente :",
            "Cautious conclusion:",
        ),
    }

    def build(self, analysis_data: dict[str, Any]) -> dict[str, Any]:
        data = analysis_data or {}
        raw_sources = self._sources(data)
        sources: list[dict[str, Any]] = []
        by_category: dict[str, list[dict[str, Any]]] = {}

        for raw_source in raw_sources:
            source = dict(raw_source)
            source_id = self._source_id(source)
            source["source_id"] = source_id
            source["evidence_categories"] = self._normalized_evidence_categories(
                source
            )
            source["evidence_quality"] = self._source_evidence_quality(source)
            source["methodology_visible"] = self._methodology_visible(source)
            sources.append(source)

            for category in source["evidence_categories"]:
                by_category.setdefault(category, []).append(source)

        claims = [
            self._claim(spec, by_category)
            for spec in self._claim_specs(data)
            if self._has_text(spec.value)
        ]
        confidence = self._confidence_by_category(by_category, sources)

        return {
            # Keep the historic format for frontend and test compatibility.
            "format": "evidence_ledger_v2_claim_aware",
            "schema_version": "evidence_ledger_v3_role_aware",
            "status_contract": "canonical_evidence_status_v1",
            "canonical_evidence_statuses": list(
                self.CANONICAL_EVIDENCE_STATUSES
            ),
            "claims": [asdict(item) for item in claims],
            "source_index": {
                self._source_id(source): self._compact_source(source)
                for source in sources
            },
            "confidence_by_category": confidence,
            "source_summary": self._source_summary(sources),
        }

    def sanitize_public_claims(
        self,
        analysis_data: dict[str, Any],
    ) -> dict[str, Any]:
        data = deepcopy(analysis_data or {})
        ledger = self.build(data)
        data["evidence_ledger"] = ledger
        confidence = ledger["confidence_by_category"]
        data["evidence_confidence"] = confidence
        data["overall_evidence_confidence"] = confidence[
            "overall_evidence_confidence"
        ]
        data["search_coverage"] = confidence.get("search_coverage", "low")
        data["source_relevance_confidence"] = confidence.get(
            "source_relevance_confidence", "low"
        )

        debate_judge = ((data.get("debate_room") or {}).get("judge") or {})
        startup_score = data.get("startup_score") or {}
        canonical_verdict = self._canonical_verdict(
            debate_judge.get("verdict_code")
            or debate_judge.get("verdict")
            or startup_score.get("canonical_verdict_code")
            or startup_score.get("verdict_code")
            or startup_score.get("verdict")
        )
        data["verdict_code"] = canonical_verdict

        language = self._language(data)
        claims_by_path = {
            item["path"]: item for item in ledger.get("claims") or []
        }
        market = dict(data.get("market_study") or {})

        market["market_size"] = self._publish_or_neutralize(
            claims_by_path.get("market_study.market_size"),
            language=language,
            neutral_key="market_size",
        )
        market["market_overview"] = self._publish_or_neutralize(
            claims_by_path.get("market_study.market_overview"),
            language=language,
            neutral_key="global_market",
            allow_estimated=True,
        )

        for key in ("global_potential", "global_market_assessment"):
            if key in market:
                market[key] = self._publish_or_neutralize(
                    claims_by_path.get(f"market_study.{key}"),
                    language=language,
                    neutral_key="global_market",
                    allow_estimated=True,
                )

        for key in ("local_context", "local_feasibility"):
            if key in market:
                market[key] = self._publish_or_neutralize(
                    claims_by_path.get(f"market_study.{key}"),
                    language=language,
                    neutral_key="local_market",
                    allow_estimated=True,
                )

        trend_claims = [
            item
            for path, item in claims_by_path.items()
            if path.startswith("market_study.market_trends[")
        ]
        published_trends = self._publish_claim_list(
            trend_claims,
            language=language,
        )
        if trend_claims:
            market["market_trends"] = published_trends or [
                self._neutral_text(language, "market_trends")
            ]
            market["trends"] = list(market["market_trends"])

        demand_claims = [
            item
            for path, item in claims_by_path.items()
            if path.startswith("market_study.demand_drivers[")
        ]
        published_demand = self._publish_claim_list(
            demand_claims,
            language=language,
        )
        if demand_claims:
            market["demand_drivers"] = published_demand or [
                self._neutral_text(language, "market_demand")
            ]

        market["data_confidence"] = confidence.get(
            "overall_evidence_confidence", "low"
        )
        market["confidence_level"] = confidence.get(
            "overall_evidence_confidence", "low"
        )
        data["market_study"] = market

        crawler = dict(data.get("forgecrawler") or {})
        if crawler:
            crawler["search_coverage"] = confidence.get(
                "search_coverage", "low"
            )
            crawler["discovery_confidence"] = confidence.get(
                "discovery_confidence", "low"
            )
            crawler["source_relevance_confidence"] = confidence.get(
                "source_relevance_confidence", "low"
            )
            crawler["confidence_level"] = confidence.get(
                "overall_evidence_confidence", "low"
            )
            crawler["overall_evidence_confidence"] = confidence.get(
                "overall_evidence_confidence", "low"
            )
            data["forgecrawler"] = crawler

        competitive = dict(data.get("competitive_analysis") or {})
        if competitive:
            competitive["search_coverage"] = confidence.get(
                "search_coverage", "low"
            )
            competitive["source_relevance_confidence"] = confidence.get(
                "source_relevance_confidence", "low"
            )
            competitive["source_confidence"] = confidence.get(
                "overall_evidence_confidence", "low"
            )
            competitive["confidence_level"] = confidence.get(
                "overall_evidence_confidence", "low"
            )
            competitive["confidence_by_category"] = confidence
            data["competitive_analysis"] = competitive

        fact_check = dict(data.get("fact_check_report") or {})
        if fact_check:
            fact_check["global_confidence"] = confidence.get(
                "overall_evidence_confidence", "low"
            )
            fact_check["confidence_level"] = confidence.get(
                "overall_evidence_confidence", "low"
            )
            data["fact_check_report"] = fact_check

        return data

    def _claim_specs(self, data: dict[str, Any]) -> list[ClaimSpec]:
        market = data.get("market_study") or {}
        financial = data.get("financial_estimation") or {}

        problem = (
            data.get("problem")
            or data.get("identified_problem")
            or market.get("market_problem")
        )
        solution = (
            data.get("proposed_solution")
            or data.get("solution")
        )

        specs = [
            ClaimSpec(
                "problem_relevance",
                "problem",
                "problem_context",
                problem,
            ),
            ClaimSpec(
                "solution_feasibility",
                "proposed_solution",
                "solution_benchmark",
                solution,
            ),
            ClaimSpec(
                "market_size",
                "market_study.market_size",
                "market_size",
                market.get("market_size"),
            ),
            ClaimSpec(
                "market_overview",
                "market_study.market_overview",
                "market_demand",
                market.get("market_overview"),
            ),
            ClaimSpec(
                "global_potential",
                "market_study.global_potential",
                "market_demand",
                market.get("global_potential"),
            ),
            ClaimSpec(
                "global_market_assessment",
                "market_study.global_market_assessment",
                "market_demand",
                market.get("global_market_assessment")
                or data.get("global_market_assessment"),
            ),
            ClaimSpec(
                "local_context",
                "market_study.local_context",
                "market_context",
                market.get("local_context"),
            ),
            ClaimSpec(
                "local_feasibility",
                "market_study.local_feasibility",
                "market_context",
                market.get("local_feasibility")
                or data.get("local_market_assessment"),
            ),
            ClaimSpec(
                "financial_budget",
                "financial_estimation.estimated_mvp_budget",
                "finance",
                financial.get("estimated_mvp_budget")
                or financial.get("mvp_budget_estimate")
                or financial.get("budget_mvp_estimate")
                or financial.get("budget_estimate"),
            ),
            ClaimSpec(
                "financial_roi",
                "financial_estimation.roi_outlook",
                "finance",
                financial.get("roi_outlook"),
            ),
            ClaimSpec(
                "financial_infrastructure",
                "financial_estimation.infrastructure_costs",
                "finance",
                financial.get("infrastructure_costs"),
            ),
        ]

        for index, value in enumerate(
            self._as_list(market.get("market_trends") or market.get("trends"))
        ):
            specs.append(
                ClaimSpec(
                    f"market_trend_{index + 1}",
                    f"market_study.market_trends[{index}]",
                    "market_demand",
                    value,
                )
            )

        for index, value in enumerate(
            self._as_list(market.get("demand_drivers"))
        ):
            specs.append(
                ClaimSpec(
                    f"demand_driver_{index + 1}",
                    f"market_study.demand_drivers[{index}]",
                    "market_demand",
                    value,
                )
            )

        for index, value in enumerate(
            self._as_list(data.get("improvement_suggestions"))
        ):
            specs.append(
                ClaimSpec(
                    f"solution_hypothesis_{index + 1}",
                    f"improvement_suggestions[{index}]",
                    "solution_hypothesis",
                    value,
                )
            )

        return specs

    @classmethod
    def _strip_publication_prefixes(
        cls,
        path: str,
        value: Any,
    ) -> str:
        """Remove presentation-only prefixes from canonical text.

        Public sanitization may run more than once during a pipeline.
        Canonical claim authority must therefore never absorb labels
        previously added only for presentation.

        Repeated historical prefixes are collapsed completely so the
        transformation converges back to the underlying claim text.
        """

        text = str(
            value
            or ""
        ).strip()

        if not text:
            return ""

        prefixes = (
            cls.PUBLICATION_PREFIXES_BY_PATH.get(
                str(path or "").strip(),
                (),
            )
        )

        if not prefixes:
            return text

        while text:
            matched = False
            folded = text.casefold()

            for raw_prefix in prefixes:
                prefix = str(
                    raw_prefix
                    or ""
                ).strip()

                if not prefix:
                    continue

                if not folded.startswith(
                    prefix.casefold()
                ):
                    continue

                text = text[
                    len(prefix):
                ].lstrip()

                matched = True
                break

            if not matched:
                break

        return text

    def _claim(
        self,
        spec: ClaimSpec,
        by_category: dict[str, list[dict[str, Any]]],
    ) -> EvidenceClaim:
        accepted_categories = self.CATEGORY_ALIASES.get(
            spec.category,
            {spec.category},
        )
        compatible: list[dict[str, Any]] = []
        for category in accepted_categories:
            compatible.extend(by_category.get(category, []))
        compatible = self._dedupe_sources(compatible)

        if spec.category == "local_competition":
            compatible = [
                source
                for source in compatible
                if str(source.get("region_match") or "").lower() == "local"
                and (
                    bool(source.get("is_product_page"))
                    or str(source.get("canonical_category") or "").lower()
                    == "direct_competitor"
                    or bool(source.get("is_direct_competitor"))
                )
            ]

        claim_text = self._strip_publication_prefixes(
            spec.path,
            self._text(spec.value),
        )
        normalized_claim = self._normalize_semantic_text(claim_text)
        non_confirmation = any(
            marker in normalized_claim
            for marker in (
                self._normalize_semantic_text(item)
                for item in self.NON_CONFIRMATION_MARKERS
            )
        )
        cautious_signal = any(
            normalized_claim.startswith(self._normalize_semantic_text(prefix))
            for prefix in self.CAUTIOUS_SIGNAL_PREFIXES
        )

        if spec.claim_id in {
            "problem_relevance",
            "solution_feasibility",
        }:
            # Evidence-category compatibility only identifies candidate
            # sources. It does not prove the exact factual claim.
            compatible = self._filter_semantically_compatible_sources(
                claim_text,
                compatible,
                strict=True,
            )

        elif spec.category == "solution_hypothesis":
            compatible = self._filter_semantically_compatible_sources(
                claim_text,
                compatible,
                strict=True,
            )

        elif (
            spec.path.startswith("market_study.market_trends[")
            or spec.path.startswith("market_study.demand_drivers[")
        ):
            compatible = self._filter_semantically_compatible_sources(
                claim_text,
                compatible,
                strict=False,
            )

        # Global claims require international market evidence with visible
        # methodology. Local initiatives cannot prove a global trend.
        if spec.path in {
            "market_study.global_potential",
            "market_study.global_market_assessment",
        }:
            compatible = [
                source
                for source in compatible
                if str(source.get("region_match") or "").lower()
                == "international"
                and str(source.get("source_type") or "").lower()
                in {"market_article", "official_source", "regulation"}
                and (
                    str(source.get("evidence_quality") or "").lower() == "high"
                    or bool(source.get("methodology_visible"))
                )
            ]

        # These are analytical or project-derived narratives, not facts proven
        # by broad market pages.
        if spec.path in {
            "market_study.market_overview",
            "market_study.local_context",
        }:
            compatible = []

        if spec.path == "market_study.local_feasibility":
            compatible = [
                source
                for source in compatible
                if str(source.get("region_match") or "").lower() == "local"
            ]

        # Internal financial estimates must never inherit generic market or
        # pricing sources. Only direct quotes/cost records should be added by a
        # dedicated financial evidence workflow.
        precise = bool(self.PRECISE_NUMBER_RE.search(claim_text))
        internal_estimate = spec.path.startswith("financial_estimation.")
        if internal_estimate:
            compatible = []

        if precise and not internal_estimate:
            compatible = [
                source
                for source in compatible
                if self._source_supports_numbers(source, claim_text)
            ]

        source_ids = [self._source_id(source) for source in compatible]
        quality = self._aggregate_evidence_quality(compatible)

        if non_confirmation:
            status = "not_confirmed"
            confidence = "low"

        elif spec.category == "solution_hypothesis":
            # A product or strategy hypothesis is explicitly analytical.
            # It is not an externally verified fact.
            status = "estimated"
            confidence = "low" if not source_ids else "medium"

        elif internal_estimate:
            # Internal planning estimates remain estimates even without
            # external evidence. They must never masquerade as sourced facts.
            status = "estimated"
            confidence = "low"

        elif spec.path in self.ANALYTICAL_PATH_PREFIXES:
            # Project framing, recommendations and cautious audit conclusions
            # are analytical outputs, not factual external claims.
            status = "estimated"
            confidence = "low" if not source_ids else quality

        elif cautious_signal and source_ids:
            # A cautious signal backed by compatible evidence remains an
            # estimate/signal rather than becoming a fully sourced assertion.
            status = "estimated"
            confidence = quality

        elif source_ids:
            status = "sourced"
            confidence = quality

        else:
            # An external factual claim without compatible evidence is not
            # an estimate. Its truth is simply not confirmed.
            status = "not_confirmed"
            confidence = "low"

        if status not in self.CANONICAL_EVIDENCE_STATUSES:
            raise ValueError(
                f"Unsupported canonical evidence status: {status}"
            )

        claim_kind = self._claim_kind(
            spec
        )

        validation_required = self._validation_required(
            status=status,
            claim_kind=claim_kind,
        )

        return EvidenceClaim(
            claim_id=spec.claim_id,
            path=spec.path,
            category=spec.category,
            claim=claim_text,
            source_ids=source_ids,
            # Legacy compatibility alias.
            status=status,
            confidence=confidence,
            public_text=claim_text,
            # Canonical semantic fields.
            evidence_status=status,
            claim_kind=claim_kind,
            validation_required=validation_required,
        )

    def _claim_kind(
        self,
        spec: ClaimSpec,
    ) -> str:
        """Classify claim semantics independently from evidence strength."""

        if spec.path == "market_study.local_context":
            return "recommendation"

        if spec.path == "market_study.local_feasibility":
            return "audit_conclusion"

        if spec.path == "market_study.market_overview":
            return "project_input"

        if spec.path.startswith("financial_estimation."):
            return "estimate"

        if spec.category == "solution_hypothesis":
            return "hypothesis"

        return "evidence_claim"

    def _validation_required(
        self,
        *,
        status: str,
        claim_kind: str,
    ) -> bool:
        """Keep validation need separate from evidence status."""

        if claim_kind in {
            "recommendation",
            "project_input",
        }:
            return False

        # Audit conclusions may summarize evidence, but they do not
        # escape evidence requirements. An unsupported local feasibility
        # conclusion still requires validation.
        return status != "sourced"

    def _publish_or_neutralize(
        self,
        claim: dict[str, Any] | None,
        *,
        language: str,
        neutral_key: str,
        allow_estimated: bool = False,
    ) -> str:
        if claim and claim.get("status") == "sourced":
            return str(
                claim.get("public_text") or claim.get("claim") or ""
            ).strip()

        if claim and allow_estimated and claim.get("status") == "estimated":
            text = str(
                claim.get("public_text") or claim.get("claim") or ""
            ).strip()
            if text and not self.PRECISE_NUMBER_RE.search(text):
                path = str(claim.get("path") or "")
                normalized = self._normalize_semantic_text(text)
                if any(
                    normalized.startswith(
                        self._normalize_semantic_text(prefix)
                    )
                    for prefix in self.CAUTIOUS_SIGNAL_PREFIXES
                ):
                    return text
                if path == "market_study.local_context":
                    prefix = (
                        "Recommandation : "
                        if language != "en"
                        else "Recommendation: "
                    )
                elif path == "market_study.local_feasibility":
                    prefix = (
                        "Conclusion prudente : "
                        if language != "en"
                        else "Cautious conclusion: "
                    )
                elif path == "market_study.market_overview":
                    prefix = (
                        "Hypothèse à valider : "
                        if language != "en"
                        else "Hypothesis to validate: "
                    )
                else:
                    prefix = (
                        "Signal à valider : "
                        if language != "en"
                        else "Signal to validate: "
                    )
                canonical_text = (
                    self._strip_publication_prefixes(
                        path,
                        text,
                    )
                )

                if not canonical_text:
                    return self._neutral_text(
                        language,
                        neutral_key,
                    )

                return prefix + canonical_text

        return self._neutral_text(language, neutral_key)

    def _publish_claim_list(
        self,
        claims: list[dict[str, Any]],
        *,
        language: str,
    ) -> list[str]:
        result: list[str] = []
        for claim in claims:
            text = str(
                claim.get("public_text") or claim.get("claim") or ""
            ).strip()
            if not text:
                continue
            if claim.get("status") == "sourced":
                result.append(text)
            elif (
                claim.get("status") == "estimated"
                and not self.PRECISE_NUMBER_RE.search(text)
            ):
                normalized = self._normalize_semantic_text(text)
                if any(
                    normalized.startswith(
                        self._normalize_semantic_text(prefix)
                    )
                    for prefix in self.CAUTIOUS_SIGNAL_PREFIXES
                ):
                    result.append(text)
                elif claim.get("source_ids"):
                    prefix = (
                        "Signal à valider : "
                        if language != "en"
                        else "Signal to validate: "
                    )
                    result.append(prefix + text)
        return self._unique(result)

    @staticmethod
    def _neutral_text(language: str, key: str) -> str:
        english = {
            "market_size": "The exact addressable market size is not verified by the retained sources and must be confirmed with official, category-compatible data.",
            "global_market": "The retained evidence does not confirm a global growth or demand claim for this exact project category. Treat global potential as a hypothesis until stronger market evidence is added.",
            "local_market": "The retained evidence does not confirm the level of local demand, adoption or market readiness. Validate these points with official local sources and field interviews.",
            "market_trends": "No market trend is sufficiently supported by the retained evidence; verify trends with official or independent sector data.",
            "market_demand": "Local demand and willingness to pay are not confirmed by the retained evidence and require field validation.",
        }
        french = {
            "market_size": "La taille exacte du marché adressable n’est pas vérifiée par les sources retenues et doit être confirmée avec des données officielles compatibles.",
            "global_market": "Les preuves retenues ne confirment pas une croissance ou une demande mondiale pour cette catégorie précise. Le potentiel global reste une hypothèse à valider.",
            "local_market": "Les preuves retenues ne confirment pas le niveau de demande locale, d’adoption ou de maturité du marché. Ces points exigent des sources locales officielles et des entretiens terrain.",
            "market_trends": "Aucune tendance de marché n’est suffisamment soutenue par les preuves retenues ; elle doit être vérifiée avec des données sectorielles officielles ou indépendantes.",
            "market_demand": "La demande locale et la volonté de payer ne sont pas confirmées par les preuves retenues et exigent une validation terrain.",
        }
        return (english if language == "en" else french).get(key, "")

    def _confidence_by_category(
        self,
        by_category: dict[str, list[dict[str, Any]]],
        sources: list[dict[str, Any]],
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        for category in self.CORE_CONFIDENCE_CATEGORIES:
            accepted = self.CATEGORY_ALIASES.get(category, {category})
            matches: list[dict[str, Any]] = []
            for item in accepted:
                matches.extend(by_category.get(item, []))
            matches = self._dedupe_sources(matches)

            if category == "local_competition":
                matches = [
                    source
                    for source in matches
                    if str(source.get("region_match") or "").lower()
                    == "local"
                    and (
                        bool(source.get("is_product_page"))
                        or bool(source.get("is_direct_competitor"))
                    )
                ]

            result[category] = self._quality_level(matches)

        result["discovery_confidence"] = self._level(
            len(sources),
            high_at=5,
            medium_at=2,
        )
        result["search_coverage"] = result["discovery_confidence"]

        relevance_scores = [
            float(source.get("source_relevance_score") or 0.0)
            for source in sources
            if isinstance(source.get("source_relevance_score"), (int, float))
        ]
        average_relevance = (
            sum(relevance_scores) / len(relevance_scores)
            if relevance_scores
            else 0.0
        )
        if len(sources) >= 6 and average_relevance >= 0.72:
            relevance_level = "high"
        elif len(sources) >= 2 and average_relevance >= 0.50:
            relevance_level = "medium"
        else:
            relevance_level = "low"
        result["source_relevance_confidence"] = relevance_level

        local_sources = [
            source
            for source in sources
            if str(source.get("region_match") or "").lower() == "local"
            and any(
                category
                in {
                    "competitor_product",
                    "solution_benchmark",
                    "technology_benchmark",
                    "regional_context",
                    "sector_context",
                    "problem_context",
                    "market_size",
                    "market_size_claim",
                    "market_demand",
                    "market_demand_claim",
                    "local_market_signal",
                    "regulation",
                }
                for category in source.get("evidence_categories") or []
            )
        ]
        result["local_market_confidence"] = self._quality_level(local_sources)
        result["market_size_confidence"] = result.get("market_size", "low")
        result["market_demand_confidence"] = result.get("market_demand", "low")
        result["customer_validation_confidence"] = "low"
        result["financial_confidence"] = result.get("finance", "low")

        core = [result[key] for key in self.CORE_CONFIDENCE_CATEGORIES]
        high = core.count("high")
        medium = core.count("medium")
        if (
            high >= 5
            and result["market_size"] != "low"
            and result["market_demand"] != "low"
        ):
            overall = "high"
        elif (
            high + medium >= 5
            and result["problem_context"] != "low"
            and result["solution_benchmark"] != "low"
        ):
            overall = "medium"
        else:
            overall = "low"
        result["overall_evidence_confidence"] = overall
        return result

    def _normalized_evidence_categories(
        self,
        source: dict[str, Any],
    ) -> list[str]:
        categories = self._as_list(source.get("evidence_categories"))
        source_type = str(source.get("source_type") or "").strip().lower()
        source_role = str(source.get("source_role") or "").strip().lower()
        canonical = str(
            source.get("canonical_category")
            or source.get("source_category")
            or ""
        ).strip().lower()

        if (
            source_type == "market_article"
            or source_role == "market_evidence"
            or canonical == "market_evidence"
        ):
            categories = [
                category
                for category in categories
                if str(category).strip().lower()
                not in {"pricing", "pricing_signal", "finance"}
            ]

        if source.get("is_direct_competitor") or canonical == "direct_competitor":
            categories.extend(["competitor_product", "direct_competitor"])
        if source_type == "adjacent_solution" or canonical == "adjacent_solution":
            categories.append("solution_benchmark")
        if (
            source_type == "technology_benchmark"
            or source_role in {"technology_provider", "technology_benchmark"}
            or canonical == "technology_benchmark"
        ):
            categories.extend(["technology_benchmark", "solution_benchmark"])
        if (
            source_type == "market_article"
            or source_role == "market_evidence"
            or canonical == "market_evidence"
        ):
            categories.append("sector_context")
        if str(source.get("region_match") or "").lower() == "local" and (
            source_type == "market_article"
            or source_role in {"market_evidence", "ecosystem_actor"}
        ):
            categories.extend(["regional_context", "local_market_signal"])
        if source.get("pricing_found") and source_type in {
            "pricing_page",
            "competitor",
            "adjacent_solution",
        }:
            categories.append("pricing")

        return self._unique(categories)

    @staticmethod
    def _repair_text_encoding(value: Any) -> str:
        text = str(value or "")
        if not any(marker in text for marker in ("├", "ΓÇ", "Ã", "â€")):
            return text
        try:
            repaired = text.encode("cp437").decode("utf-8")
            if repaired:
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        return text

    @classmethod
    def _normalize_semantic_text(cls, value: Any) -> str:
        raw = unicodedata.normalize(
            "NFKD",
            cls._repair_text_encoding(value),
        )
        without_accents = "".join(
            character
            for character in raw
            if not unicodedata.combining(character)
        )
        return " ".join(without_accents.casefold().split())

    @classmethod
    def _semantic_tokens(cls, value: Any) -> set[str]:
        normalized = cls._normalize_semantic_text(value)
        return {
            token
            for token in re.findall(r"[a-z0-9]{3,}", normalized)
            if token not in cls.SEMANTIC_STOPWORDS
        }

    @classmethod
    def _source_semantic_blob(cls, source: dict[str, Any]) -> str:
        return cls._normalize_semantic_text(
            " ".join(
                str(source.get(key) or "")
                for key in (
                    "title",
                    "snippet",
                    "extracted_text_preview",
                    "why_relevant",
                    "source_type",
                    "source_role",
                    "canonical_category",
                )
            )
        )

    @classmethod
    def _filter_semantically_compatible_sources(
        cls,
        claim_text: str,
        sources: list[dict[str, Any]],
        *,
        strict: bool,
    ) -> list[dict[str, Any]]:
        """Keep evidence that addresses the precise claim, not only its broad category.

        A technology benchmark does not automatically support every proposed
        feature. Likewise, a generic market article does not automatically
        support every trend. Distinctive claim concepts must be visible in the
        source title, snippet, extracted preview or relevance explanation.
        """

        claim_normalized = cls._normalize_semantic_text(claim_text)
        claim_tokens = cls._semantic_tokens(claim_text)
        active_groups = [
            {
                cls._normalize_semantic_text(term)
                for term in group
                if cls._normalize_semantic_text(term)
            }
            for group in cls.SOLUTION_CONCEPT_GROUPS
            if any(
                cls._normalize_semantic_text(term) in claim_normalized
                for term in group
            )
        ]

        compatible: list[dict[str, Any]] = []
        for source in sources:
            source_blob = cls._source_semantic_blob(source)
            source_tokens = cls._semantic_tokens(source_blob)

            if active_groups and not all(
                any(term in source_blob for term in group)
                for group in active_groups
            ):
                continue

            overlap = claim_tokens & source_tokens
            has_distinctive_overlap = any(
                len(token) >= 8 for token in overlap
            )

            if active_groups:
                compatible.append(source)
                continue

            minimum_overlap = 2 if strict else 1
            if len(overlap) >= minimum_overlap or has_distinctive_overlap:
                compatible.append(source)

        return cls._dedupe_sources(compatible)

    def _source_supports_numbers(
        self,
        source: dict[str, Any],
        claim_text: str,
    ) -> bool:
        claim_numbers = {
            token.replace(",", ".")
            for token in self.NUMBER_TOKEN_RE.findall(claim_text)
        }
        if not claim_numbers:
            return True

        source_blob = " ".join(
            str(source.get(key) or "")
            for key in (
                "title",
                "snippet",
                "extracted_text_preview",
                "why_relevant",
            )
        )
        source_numbers = {
            token.replace(",", ".")
            for token in self.NUMBER_TOKEN_RE.findall(source_blob)
        }
        return claim_numbers.issubset(source_numbers)

    def _source_evidence_quality(self, source: dict[str, Any]) -> str:
        explicit = str(
            source.get("evidence_quality")
            or source.get("methodology_quality")
            or ""
        ).strip().lower()
        if explicit in {"low", "medium", "high"}:
            return explicit

        domain = self._source_domain(source)
        source_type = str(source.get("source_type") or "").lower()
        source_role = str(source.get("source_role") or "").lower()

        if domain in self.LOW_METHODOLOGY_DOMAINS:
            return "low"
        if source_type in {"regulation", "official_evidence"}:
            return "high"
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return "high"
        if domain.endswith(".org") or source_role in {
            "official_evidence",
            "regional_benchmark",
        }:
            return "medium"
        if source_type in {
            "technology_benchmark",
            "adjacent_solution",
            "competitor",
            "pricing_page",
        }:
            return "medium"
        if source_type in {"market_article", "directory"}:
            return "low"
        return "low"

    def _methodology_visible(self, source: dict[str, Any]) -> bool:
        if source.get("methodology_visible") is not None:
            return bool(source.get("methodology_visible"))
        blob = " ".join(
            str(source.get(key) or "")
            for key in ("title", "snippet", "extracted_text_preview")
        ).lower()
        negative_markers = (
            "without visible methodology",
            "methodology not visible",
            "methodology unavailable",
            "méthodologie non visible",
            "méthodologie absente",
            "méthodologie indisponible",
        )
        if any(marker in blob for marker in negative_markers):
            return False
        markers = (
            "methodology",
            "méthodologie",
            "sample size",
            "échantillon",
            "survey of",
            "enquête auprès",
            "official statistics",
            "statistiques officielles",
        )
        return any(marker in blob for marker in markers)

    def _aggregate_evidence_quality(
        self,
        sources: list[dict[str, Any]],
    ) -> str:
        if not sources:
            return "low"
        qualities = [
            str(source.get("evidence_quality") or "low").lower()
            for source in sources
        ]
        if qualities.count("high") >= 2:
            return "high"
        if "high" in qualities or qualities.count("medium") >= 2:
            return "medium"
        if "medium" in qualities:
            return "medium"
        return "low"

    def _quality_level(self, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return "low"
        weights = {"high": 1.0, "medium": 0.6, "low": 0.25}
        total = sum(
            weights.get(str(source.get("evidence_quality") or "low"), 0.25)
            for source in sources
        )
        has_high = any(
            source.get("evidence_quality") == "high" for source in sources
        )
        if total >= 1.8 and has_high:
            return "high"
        if total >= 0.6:
            return "medium"
        return "low"

    def _source_summary(self, sources: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "retained": len(sources),
            "grounded": sum(bool(item.get("grounded")) for item in sources),
            "local": sum(
                str(item.get("region_match") or "").lower() == "local"
                for item in sources
            ),
            "products": sum(bool(item.get("is_product_page")) for item in sources),
            "high_quality": sum(
                item.get("evidence_quality") == "high" for item in sources
            ),
            "medium_quality": sum(
                item.get("evidence_quality") == "medium" for item in sources
            ),
            "low_quality": sum(
                item.get("evidence_quality") == "low" for item in sources
            ),
            "methodology_visible": sum(
                bool(item.get("methodology_visible")) for item in sources
            ),
        }

    @staticmethod
    def _level(count: int, *, high_at: int = 2, medium_at: int = 1) -> str:
        if count >= high_at:
            return "high"
        if count >= medium_at:
            return "medium"
        return "low"

    @staticmethod
    def _sources(data: dict[str, Any]) -> list[dict[str, Any]]:
        crawler = data.get("forgecrawler") or {}
        competitive = data.get("competitive_analysis") or {}
        rows = competitive.get("sources") or crawler.get("sources") or []
        return [
            dict(row)
            for row in rows
            if isinstance(row, dict)
            and not row.get("rejected")
            and not row.get("internal_only")
            and bool(row.get("public_display", True))
        ]

    @staticmethod
    def _source_id(source: dict[str, Any]) -> str:
        key = str(source.get("url") or source.get("title") or "")
        return "src_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

    def _compact_source(self, source: dict[str, Any]) -> dict[str, Any]:
        compact = {
            key: source.get(key)
            for key in (
                "title",
                "url",
                "provider",
                "grounded",
                "source_type",
                "source_role",
                "canonical_category",
                "region_match",
                "target_match_level",
                "is_product_page",
                "is_direct_competitor",
                "evidence_categories",
                "source_relevance_score",
                "evidence_quality",
                "methodology_visible",
                "why_relevant",
                "snippet",
            )
        }
        compact["source_id"] = self._source_id(source)
        return compact

    @staticmethod
    def _dedupe_sources(
        rows: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(row.get("url") or row.get("title") or "").strip().lower()
            if key:
                result[key] = row
        return list(result.values())

    @staticmethod
    def _source_domain(source: dict[str, Any]) -> str:
        try:
            return urlparse(str(source.get("url") or "")).netloc.lower()
        except Exception:
            return ""

    @staticmethod
    def _canonical_verdict(value: Any) -> str:
        normalized = (
            str(value or "")
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if "insufficient" in normalized or "preuve_insuffisante" in normalized:
            return "insufficient_evidence"
        if (
            "conditional" in normalized
            or "conditionnel" in normalized
            or "sous_conditions" in normalized
        ):
            return "conditional_go"
        if "pivot" in normalized:
            return "pivot"
        if (
            "no_go" in normalized
            or "nogo" in normalized
            or "stop" in normalized
            or "abandon" in normalized
        ):
            return "no_go"
        if normalized == "go" or normalized.startswith("go_"):
            return "go"
        return "conditional_go"

    @staticmethod
    def _language(data: dict[str, Any]) -> str:
        value = str(
            data.get("output_language")
            or (data.get("project_context_meta") or {}).get("output_language")
            or "fr"
        ).lower()
        return "en" if value.startswith("en") else "fr"

    @staticmethod
    def _has_text(value: Any) -> bool:
        if isinstance(value, (list, tuple, set)):
            return any(str(item or "").strip() for item in value)
        return bool(str(value or "").strip())

    @classmethod
    def _text(cls, value: Any) -> str:
        if isinstance(value, (list, tuple, set)):
            return "; ".join(
                cls._repair_text_encoding(item).strip()
                for item in value
                if str(item).strip()
            )
        return cls._repair_text_encoding(value).strip()

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        if value is None:
            return []
        return [value]

    @staticmethod
    def _unique(values: Iterable[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            clean = str(value or "").strip()
            if not clean:
                continue
            key = clean.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(clean)
        return result


evidence_ledger = EvidenceLedger()