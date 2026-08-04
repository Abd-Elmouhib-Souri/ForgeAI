from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse


class SourceRoleResolver:
    """Resolve how a source relates to the current project.

    ``source_type`` describes the page shape. ``source_role`` describes the
    business relationship to the project. The two concepts are intentionally
    separated so that a white-label vendor, a market report and a consumer
    service cannot all become "competitors" merely because they mention the
    same sector words.
    """

    TECHNOLOGY_PROVIDER_SIGNALS = {
        "white label",
        "white-label",
        "ride hailing software",
        "taxi booking software",
        "taxi dispatch software",
        "dispatch platform",
        "software for taxi businesses",
        "software for taxi companies",
        "platform for operators",
        "fleet software",
        "launch your ride hailing",
        "start ride hailing company",
        "build your taxi app",
        "saas platform",
        "api integration",
    }

    CONSUMER_OPERATION_SIGNALS = {
        "book a ride",
        "book your ride",
        "request a ride",
        "ride with",
        "get a ride",
        "find a driver",
        "passenger app",
        "driver app",
        "available in tunisia",
        "available in tunisie",
        "commander un taxi",
        "reserver un taxi",
        "réserver un taxi",
        "demander une course",
        "pickup",
        "destination",
    }

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
        "étude de marché",
        "etude de marche",
        "taille du marché",
        "taille du marche",
        "prévisions du marché",
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

    MARKET_TYPES = {"market_article", "market_evidence"}
    OFFICIAL_TYPES = {"official_source", "regulation"}

    MOBILITY_VERTICALS = {
        "mobility_taxi",
        "taxi",
        "ride_hailing",
        "urban_mobility",
        "mobility",
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

    MOBILITY_OPERATION_SIGNALS = {
        "ride hailing",
        "taxi",
        "book a ride",
        "request a ride",
        "ride with",
        "passenger",
        "passengers",
        "driver",
        "drivers",
        "pickup",
        "destination",
        "commander un taxi",
        "reserver un taxi",
        "réserver un taxi",
        "demander une course",
    }

    def resolve(
        self,
        *,
        source: Dict[str, Any],
        decision: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = self._context(project_context)
        source_type = str(decision.get("source_type") or "irrelevant").strip().lower()
        region_match = str(decision.get("region_match") or "unknown").strip().lower()
        source_text = self._normalize(
            " ".join(
                str(source.get(key) or "")
                for key in ("title", "url", "snippet", "body", "extracted_text_preview")
            )
        )

        product_page = bool(decision.get("is_product_page"))
        same_target = bool(decision.get("same_or_close_target_user"))
        same_use_case = bool(decision.get("same_or_close_use_case"))
        same_solution = bool(decision.get("same_or_close_solution_category"))
        sector_mismatch = bool(decision.get("sector_mismatch"))

        market_evidence_page = self._is_market_evidence_page(source, source_text)
        consumer_operation = self._is_consumer_operation(source_text)
        technology_supplier = self._is_technology_supplier(
            source_text=source_text,
            archetype=context["project_archetype"],
            product_page=product_page,
            same_use_case=same_use_case,
            same_solution=same_solution,
        )

        operation_equivalent = self._is_operation_equivalent(
            source_text=source_text,
            context=context,
            consumer_operation=consumer_operation,
            technology_supplier=technology_supplier,
            sector_mismatch=sector_mismatch,
        )

        if operation_equivalent:
            same_target = True
            same_use_case = True
            same_solution = True

        product_or_operation = product_page or consumer_operation
        exact_business_match = bool(
            (same_target or consumer_operation)
            and (same_use_case or same_solution)
            and not sector_mismatch
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
        elif source_type in self.MARKET_TYPES or market_evidence_page:
            source_role = "market_evidence"
            comparison_scope = "evidence"
            legacy_type = "market_article"
        elif technology_supplier:
            source_role = "technology_provider"
            comparison_scope = "technology_benchmark"
            legacy_type = "technology_benchmark"
        elif source_type == "technology_benchmark":
            source_role = "technology_provider"
            comparison_scope = "technology_benchmark"
            legacy_type = "technology_benchmark"
            technology_supplier = True
        elif region_match == "local" and product_or_operation and exact_business_match:
            source_role = "direct_competitor"
            comparison_scope = "local_direct"
            legacy_type = "competitor"
        elif product_or_operation and exact_business_match:
            source_role = (
                "regional_benchmark"
                if region_match == "regional"
                else "international_benchmark"
            )
            comparison_scope = source_role
            legacy_type = "competitor"
        elif product_or_operation and not sector_mismatch:
            source_role = "adjacent_solution"
            comparison_scope = "local_adjacent" if region_match == "local" else "adjacent"
            legacy_type = "adjacent_solution"
        elif source_type == "adjacent_solution":
            source_role = "adjacent_solution"
            comparison_scope = "local_adjacent" if region_match == "local" else "adjacent"
            legacy_type = "adjacent_solution"
        else:
            source_role = "irrelevant"
            comparison_scope = "irrelevant"
            legacy_type = "irrelevant"

        canonical_category = self.ROLE_TO_CANONICAL_CATEGORY.get(
            source_role,
            "irrelevant",
        )

        return {
            "source_role": source_role,
            "canonical_category": canonical_category,
            "comparison_scope": comparison_scope,
            "technology_supplier": technology_supplier,
            "consumer_operation": consumer_operation,
            "market_evidence_page": market_evidence_page,
            "operation_equivalent": operation_equivalent,
            "legacy_source_type": legacy_type,
            "canonical_source_id": self._canonical_source_id(source),
            "role_reason": self._role_reason(
                source_role=source_role,
                region_match=region_match,
                same_target=same_target,
                same_use_case=same_use_case,
                same_solution=same_solution,
                technology_supplier=technology_supplier,
                consumer_operation=consumer_operation,
                market_evidence_page=market_evidence_page,
                operation_equivalent=operation_equivalent,
            ),
        }

    def _is_operation_equivalent(
        self,
        *,
        source_text: str,
        context: Dict[str, str],
        consumer_operation: bool,
        technology_supplier: bool,
        sector_mismatch: bool,
    ) -> bool:
        """Bridge short consumer copy to the exact marketplace workflow.

        Consumer ride-hailing pages often say only ``Book a ride``, ``pickup``
        and ``destination`` while the project packet contains a longer French
        workflow. The bridge is deliberately narrow: it applies only to a
        mobility/taxi project, a real consumer operation, and never to a
        white-label technology supplier or a cross-sector page.
        """
        if not consumer_operation or technology_supplier or sector_mismatch:
            return False

        archetype = str(context.get("project_archetype") or "").strip().lower()
        vertical = str(context.get("vertical") or "").strip().lower()

        if archetype not in {
            "two_sided_marketplace",
            "consumer_transactional_app",
            "regulated_service",
        }:
            return False

        if vertical not in self.MOBILITY_VERTICALS and not any(
            marker in vertical for marker in ("taxi", "ride", "mobility")
        ):
            return False

        operation_hits = sum(
            1
            for term in self.MOBILITY_OPERATION_SIGNALS
            if self._term_in_text(term, source_text)
        )
        return operation_hits >= 3

    def _is_market_evidence_page(self, source: Dict[str, Any], source_text: str) -> bool:
        domain = self._domain(str(source.get("url") or source.get("href") or ""))
        signal_hits = sum(
            1 for term in self.MARKET_PAGE_SIGNALS if self._term_in_text(term, source_text)
        )
        consumer_hits = sum(
            1 for term in self.CONSUMER_OPERATION_SIGNALS if self._term_in_text(term, source_text)
        )
        technology_hits = sum(
            1 for term in self.TECHNOLOGY_PROVIDER_SIGNALS if self._term_in_text(term, source_text)
        )

        if domain in self.MARKET_DOMAINS and signal_hits >= 1:
            return True
        if signal_hits >= 2 and consumer_hits == 0 and technology_hits == 0:
            return True
        return False

    def _is_consumer_operation(self, source_text: str) -> bool:
        hits = sum(
            1 for term in self.CONSUMER_OPERATION_SIGNALS if self._term_in_text(term, source_text)
        )
        technology_hits = sum(
            1 for term in self.TECHNOLOGY_PROVIDER_SIGNALS if self._term_in_text(term, source_text)
        )
        return hits >= 2 and technology_hits < 2

    def _is_technology_supplier(
        self,
        *,
        source_text: str,
        archetype: str,
        product_page: bool,
        same_use_case: bool,
        same_solution: bool,
    ) -> bool:
        if not product_page:
            return False
        if archetype not in {
            "two_sided_marketplace",
            "consumer_transactional_app",
            "ecommerce",
            "regulated_service",
        }:
            return False

        technology_hits = sum(
            1 for term in self.TECHNOLOGY_PROVIDER_SIGNALS if self._term_in_text(term, source_text)
        )
        consumer_hits = sum(
            1 for term in self.CONSUMER_OPERATION_SIGNALS if self._term_in_text(term, source_text)
        )

        if self._term_in_text("white label", source_text) or self._term_in_text("white-label", source_text):
            return True
        if technology_hits >= 2 and consumer_hits == 0:
            return True
        if technology_hits >= 1 and same_solution and not same_use_case and consumer_hits == 0:
            return True
        return False

    def _context(self, project_context: Dict[str, Any]) -> Dict[str, str]:
        intelligence = project_context.get("project_intelligence") or {}
        structured = (
            project_context.get("structured_project_context")
            or intelligence.get("structured_project_context")
            or {}
        )
        packet = (
            project_context.get("agent_context_packet")
            or intelligence.get("agent_context_packet")
            or {}
        )
        archetype_context = (
            project_context.get("archetype_context")
            or packet.get("archetype_context")
            or intelligence.get("archetype_context")
            or {}
        )
        return {
            "project_archetype": str(
                structured.get("project_archetype")
                or archetype_context.get("project_archetype")
                or "generic_digital_product"
            ).strip().lower(),
            "vertical": str(
                structured.get("vertical")
                or archetype_context.get("vertical")
                or "general"
            ).strip().lower(),
        }

    def _canonical_source_id(self, source: Dict[str, Any]) -> str:
        url = self._canonical_url(str(source.get("url") or source.get("href") or ""))
        fallback = self._normalize(
            f"{source.get('title', '')}|{source.get('canonical_vendor_domain', '')}"
        )
        seed = url or fallback or "unknown-source"
        return "src_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _canonical_url(value: str) -> str:
        try:
            parsed = urlparse(value.strip())
        except Exception:
            return ""
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        host = parsed.netloc.lower().split("@")[-1]
        if host.startswith("www."):
            host = host[4:]
        path = re.sub(r"/{2,}", "/", parsed.path or "/").rstrip("/")
        return urlunparse(("https", host, path, "", "", ""))

    @staticmethod
    def _domain(value: str) -> str:
        try:
            host = urlparse(value.strip()).netloc.lower().split("@")[-1]
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
            f"role={source_role} | region={region_match} | "
            f"target_match={str(same_target).lower()} | "
            f"use_case_match={str(same_use_case).lower()} | "
            f"solution_match={str(same_solution).lower()} | "
            f"consumer_operation={str(consumer_operation).lower()} | "
            f"technology_supplier={str(technology_supplier).lower()} | "
            f"market_evidence_page={str(market_evidence_page).lower()} | "
            f"operation_equivalent={str(operation_equivalent).lower()}"
        )

    @staticmethod
    def _normalize(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = text.lower().replace("’", "'")
        text = re.sub(r"[^a-z0-9' -]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _term_in_text(term: str, text: str) -> bool:
        normalized = SourceRoleResolver._normalize(term)
        if not normalized:
            return False
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text))


source_role_resolver = SourceRoleResolver()