# ============================================================
# backend/app/services/source_relevance_gate.py
# ============================================================
#
# SourceRelevanceGate V2 — Claim-Aware Evidence Validator
#
# Principles:
# - search_query is acquisition metadata, never evidence;
# - project name and region never prove business relevance;
# - a local page about the sector is not automatically a competitor;
# - direct competitors require explicit product-page and workflow evidence;
# - market context, market size, demand, problem evidence and pricing are
#   separate categories;
# - weak sources are retained only internally or rejected;
# - no source or competitor is invented.
# ============================================================

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Sequence, Set
from urllib.parse import urlparse

from app.services.source_role_resolver import source_role_resolver


@dataclass
class SourceRelevanceDecision:
    source_relevance_score: float
    public_display: bool
    internal_only: bool
    rejected: bool

    source_type: str
    source_role: str
    canonical_category: str
    comparison_scope: str
    region_match: str
    is_direct_competitor: bool
    technology_supplier: bool
    canonical_source_id: str
    confidence: str

    matched_strong_terms: List[str]
    matched_weak_terms: List[str]
    matched_forbidden_terms: List[str]

    matched_domain_terms: List[str]
    matched_sector_terms: List[str]
    matched_target_terms: List[str]
    matched_use_case_terms: List[str]
    matched_solution_terms: List[str]

    product_evidence_signals: List[str]
    market_evidence_signals: List[str]
    evidence_categories: List[str]

    same_or_close_target_user: bool
    same_or_close_sector: bool
    target_match_level: str
    is_product_page: bool
    same_or_close_use_case: bool
    same_or_close_solution_category: bool
    clear_contextual_link: bool
    sector_mismatch: bool
    mismatch_terms: List[str]

    why_relevant: str
    public_reason: str
    rejection_reason: str


class SourceRelevanceGate:
    PUBLIC_DISPLAY_THRESHOLD = 0.70
    INTERNAL_USE_THRESHOLD = 0.50
    DIRECT_COMPETITOR_THRESHOLD = 0.82

    DEFAULT_WEAK_TERMS = {
        "app", "application", "platform", "plateforme", "digital", "mobile",
        "service", "solution", "tool", "outil", "business", "startup",
        "online", "website", "dashboard", "management", "manage", "create",
        "help", "short", "lite", "system", "software", "logiciel", "saas",
        "user", "users", "customer", "customers", "client", "clients",
        "data", "product", "market", "industry", "company", "companies",
        "quality", "tracking", "records", "record", "monitoring",
    }

    CONTEXT_STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "because", "been",
        "before", "being", "between", "by", "can", "could", "do", "does",
        "for", "from", "had", "has", "have", "how", "if", "in", "into",
        "is", "it", "its", "many", "may", "more", "most", "need", "needs",
        "new", "of", "on", "or", "our", "out", "should", "still", "than",
        "that", "the", "their", "them", "these", "they", "this", "those",
        "through", "to", "too", "use", "used", "uses", "using", "very",
        "was", "we", "were", "what", "when", "where", "which", "who",
        "with", "without", "would", "your", "first", "small", "simple",
        "basic", "lightweight", "main", "real", "existing", "current",
        "problem", "problems", "solution", "solutions", "model", "models",
        "business", "monthly", "low", "high", "possible",
        "avec", "avant", "besoin", "besoins", "car", "ce", "ces", "cette",
        "comme", "dans", "de", "des", "du", "elle", "elles", "en", "est",
        "et", "être", "etre", "leur", "leurs", "les", "mais", "notre",
        "nous", "ou", "par", "pas", "peut", "peuvent", "plus", "pour",
        "qui", "sans", "sont", "sur", "très", "tres", "un", "une",
        "utilise", "utiliser", "utilisent", "vos", "votre", "premier",
        "première", "premiere", "petit", "petite", "problème", "probleme",
        "problèmes", "problemes", "modèle", "modele", "mensuel", "faible",
    }

    # Universal engine: cross-domain rejection must come from the current
    # project packet and semantic vertical checks, never from hard-coded demo
    # projects. A static blacklist made valid agriculture, pharmacy and health
    # projects reject their own evidence.
    DEFAULT_FORBIDDEN_DEMO_TERMS: Set[str] = set()

    # Product-breadth labels are not cross-domain evidence. They may appear in
    # valid local product pages (for example a ride-hailing service that also
    # markets itself as a "super app"). They must never reject a source solely
    # because they occur in the body text.
    SOFT_FORBIDDEN_TERMS = {
        "super app",
    }

    HARD_OFF_TOPIC_TERMS = {
        "football", "soccer", "transfermarkt", "weather", "météo", "meteo",
        "tourism", "tourisme", "hotel", "flight", "casino", "gambling",
        "forex", "lyrics", "movie", "minecraft", "phone lookup", "telecom",
        "speed test", "undressme", "ragnarok", "kaggle notebook",
        "yandex maps", "google translate",
    }

    SEARCH_OR_SOCIAL_DOMAINS = {
        "google.com", "bing.com", "duckduckgo.com", "facebook.com",
        "instagram.com", "linkedin.com", "youtube.com", "youtu.be", "x.com",
        "twitter.com", "tiktok.com", "pinterest.com", "reddit.com",
        "yandex.com", "kaggle.com",
    }

    DIRECTORY_HINTS = {
        "directory", "annuaire", "list of", "top companies", "best companies",
        "companies in", "capterra", "g2", "tracxn", "f6s", "crunchbase",
        "clutch", "product hunt", "alternatives and competitors",
    }

    ARTICLE_OR_LIST_HINTS = {
        "top 5", "top 10", "top 20", "best apps", "best software", "guide",
        "blog", "article", "list of", "ranking", "comparison", "comparatif",
        "classement", "meilleurs", "meilleures", "market forecast",
        "market report", "industry report", "statistics", "statistiques",
        "trends", "tendances", "study", "étude", "etude", "analysis",
        "research", "news", "review", "reviews", "forum", "community",
        "discussion", "how to", "what is", "why ",
    }

    ARTICLE_TITLE_PATTERNS = (
        r"^\s*\d+\s+(?:best|top)\b",
        r"^\s*(?:top|best)\s+\d+\b",
        r"^\s*(?:best|top)\b.*\b(?:apps?|software|tools?|platforms?|solutions?)\b",
        r"^\s*(?:how to|what is|why|guide to|analysis of|study of|review of)\b",
        r"\b(?:best|top)\b.*\b(?:apps?|software|tools?|platforms?|solutions?)\b",
    )

    ARTICLE_URL_HINTS = {
        "/blog/", "/blogs/", "/article/", "/articles/", "/guide/", "/guides/",
        "/post/", "/posts/", "/report/", "/reports/", "/outlook/",
        "/statistics/", "/statistiques/", "/market/", "/industry-report/",
        "/publication/", "/publications/", "/news/", "/stories/",
        "/forum/", "/forums/", "/topic/", "/topics/", "/t/",
        "/journal/", "/journals/", "/academy/", "/learn/", "/resources/",
        "/recordkeeping/", "/checklist/", "/tutorial/", "/tutorials/",
    }

    PRODUCT_LISTING_DOMAINS = {
        "apps.apple.com", "play.google.com", "appsource.microsoft.com",
        "marketplace.atlassian.com", "chromewebstore.google.com",
    }

    MARKET_SOURCE_DOMAINS = {
        "statista.com", "6wresearch.com", "datareportal.com",
        "mordorintelligence.com", "grandviewresearch.com",
        "fortunebusinessinsights.com", "researchandmarkets.com",
        "worldbank.org", "fao.org", "oecd.org", "ins.tn",
    }

    COMMERCIAL_MARKET_REPORT_DOMAINS = {
        "statista.com", "6wresearch.com", "mordorintelligence.com",
        "grandviewresearch.com", "fortunebusinessinsights.com",
        "researchandmarkets.com", "growthmarketreports.com",
    }

    LOCAL_ECOSYSTEM_HINTS = {
        "accelerator", "accélérateur", "accelerateur", "incubator",
        "incubateur", "challenge", "innovation program", "programme d'innovation",
        "startup program", "ecosystem", "écosystème", "ecosysteme",
        "association", "cluster", "network", "réseau", "reseau",
        "competition", "concours", "call for projects", "appel à projets",
        "startups", "investors", "investisseurs", "innovation event",
        "forum", "conference", "conférence", "salon professionnel",
    }

    JOB_LISTING_HINTS = {
        "job", "jobs", "career", "careers", "vacancy", "vacancies",
        "recruitment", "recrutement", "emploi", "emplois", "offre d'emploi",
        "offres d'emploi", "poste à pourvoir", "candidature", "apply now",
        "responsable intelligence artificielle", "job description",
    }

    JOB_URL_HINTS = {
        "/jobs/", "/job/", "/careers/", "/career/", "/vacancies/",
        "/recruitment/", "/recrutement/", "/emploi/", "/emplois/",
        "/offres-emploi/", "/offre-emploi/",
    }

    SOLUTION_ANNOUNCEMENT_HINTS = {
        "solution", "platform", "plateforme", "software", "logiciel",
        "application", "automation", "automatisation", "robot", "robotique",
        "technology", "technologie", "system", "système", "service",
    }


    RECRUITMENT_CONTEXT_TERMS = {
        'application candidate',
        'candidature',
        'career service',
        'employer',
        'internship',
        'internships',
        'job board',
        'recruiter',
        'recruitment',
        'recrutement',
        'stage',
        'stages',
    }

    RESEARCH_DOMAINS = {
        "researchgate.net", "academia.edu", "sciencedirect.com",
        "springer.com", "nature.com", "mdpi.com", "frontiersin.org",
        "tandfonline.com", "wiley.com", "nih.gov", "pubmed.ncbi.nlm.nih.gov",
    }

    PRODUCT_PAGE_SIGNALS = {
        "features", "feature", "fonctionnalités", "fonctionnalites", "pricing",
        "plans", "subscription", "free trial", "start free", "sign up",
        "signup", "log in", "login", "book a demo", "request demo", "our product",
        "our platform", "our software", "customers", "case studies", "integrations",
        "download app", "available on", "get started", "contact sales",
    }

    PRICING_SIGNALS = {
        "pricing", "price", "prices", "plans", "subscription", "monthly",
        "annual", "per month", "per user", "tarif", "tarifs", "abonnement",
        "mensuel", "annuel", "par mois", "par utilisateur",
    }

    MARKET_SIZE_SIGNALS = {
        "market size", "market value", "market revenue", "market share",
        "cagr", "forecast", "outlook", "industry size", "addressable market",
        "number of businesses", "number of users", "number of farms",
        "nombre d'entreprises", "nombre d'utilisateurs", "taille du marché",
        "taille du marche", "valeur du marché", "valeur du marche",
        "chiffre d'affaires du marché", "prévisions", "previsions",
    }

    DEMAND_SIGNALS = {
        "demand", "adoption", "willingness to pay", "consumer preference",
        "customer preference", "purchase intention",
        "usage rate", "adoption rate", "demande", "adoption", "volonté de payer",
        "volonte de payer", "préférences", "preferences", "enquete",
        "repondants",
    }

    PROBLEM_CONTEXT_SIGNALS = {
        "challenge", "pain point", "difficulty", "barrier", "risk", "disease",
        "pest", "loss", "manual process", "fragmented", "inefficient", "problem",
        "besoin", "difficulté", "difficulte", "obstacle", "risque", "maladie",
        "ravageur", "perte", "processus manuel", "fragmenté", "fragmente",
    }

    REGULATION_SIGNALS = {
        "law", "regulation", "government", "ministry", "official", "standard",
        "compliance", "certification", "réglementation", "reglementation",
        "ministère", "ministere", "loi", "norme", "conformité", "conformite",
    }

    REGIONAL_MARKERS = {
        "africa", "afrique", "mena", "maghreb", "north africa",
        "afrique du nord", "middle east", "moyen orient",
    }

    GENERIC_TARGET_TERMS = {
        "user", "users", "customer", "customers", "client", "clients",
        "business", "businesses", "company", "companies", "organization",
        "organizations", "organisation", "organisations", "professional",
        "professionals", "producer", "producers", "group", "groups",
        "farm", "farms", "agriculture", "agricultural", "rural", "small",
        "independent", "operator", "operators", "team", "teams",
    }

    DOCUMENT_HOST_DOMAINS = {
        "scribd.com",
        "www.scribd.com",
        "slideshare.net",
        "www.slideshare.net",
        "academia.edu",
        "www.academia.edu",
        "researchgate.net",
        "www.researchgate.net",
    }

    def evaluate_source(
        self,
        *,
        source: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = self._build_context(project_context)
        source_text = self._normalize(self._source_text(source))
        title_url_text = self._normalize(
            f"{self._safe_text(source.get('title'))} {self._safe_text(source.get('url'))}"
        )
        job_listing_mismatch = bool(
            self._looks_like_job_listing(source)
            and not self._project_is_recruitment_context(context)
        )

        matched_domain = self._matched_terms(source_text, context["domain_terms"])
        matched_sector = self._matched_terms(source_text, context.get("sector_terms") or [])
        matched_target = self._matched_terms(source_text, context["target_terms"])
        matched_use_case = self._matched_terms(source_text, context["use_case_terms"])
        matched_solution = self._matched_terms(source_text, context["solution_terms"])
        matched_weak = self._matched_terms(source_text, context["weak_terms"])
        raw_matched_forbidden = self._matched_terms(source_text, context["forbidden_terms"])

        product_signals = self._matched_terms(source_text, self.PRODUCT_PAGE_SIGNALS)
        pricing_signals = self._matched_terms(source_text, self.PRICING_SIGNALS)
        market_size_signals = self._matched_terms(source_text, self.MARKET_SIZE_SIGNALS)
        demand_signals = self._matched_terms(source_text, self.DEMAND_SIGNALS)
        problem_signals = self._matched_terms(source_text, self.PROBLEM_CONTEXT_SIGNALS)
        regulation_signals = self._matched_terms(source_text, self.REGULATION_SIGNALS)

        off_topic = self._matched_terms(title_url_text, self.HARD_OFF_TOPIC_TERMS)
        source_type = self._classify_source_type(
            source=source,
            normalized_text=source_text,
            matched_domain_terms=matched_domain,
            product_signals=product_signals,
            pricing_signals=pricing_signals,
            regulation_signals=regulation_signals,
        )
        region_match = self._classify_region(source, source_text, context)

        target_match_level = self._target_match_level(
            matched_target=matched_target,
            available_target_terms=context["target_terms"],
        )
        same_target = target_match_level == "exact"
        same_sector = self._semantic_group_match(
            matched_sector,
            context.get("sector_terms") or [],
            allow_two_single_terms=True,
        )
        same_use_case = self._semantic_group_match(
            matched_use_case,
            context["use_case_terms"],
            allow_two_single_terms=True,
        )
        same_solution = self._semantic_group_match(
            matched_solution,
            context["solution_terms"],
            allow_two_single_terms=True,
        )
        # A source can describe the same operation with a shorter phrase than
        # the project packet. Exact target + exact solution + one workflow
        # anchor is sufficient and avoids rejecting valid local products merely
        # because the page uses another language or a shorter call to action.
        if not same_use_case and matched_use_case and same_target and same_solution:
            same_use_case = True

        article_like = self._looks_like_article_or_list(source)
        is_product_page = bool(
            not article_like
            and (
                len(product_signals) >= 2
                or self._pricing_path(source.get("url") or "")
                or (
                    target_match_level == "exact"
                    and same_use_case
                    and same_solution
                    and self._contains_any(
                        source_text,
                        {"software", "app", "application", "platform", "saas", "dashboard", "product"},
                    )
                )
            )
        )

        # Product classification is target-aware. Generic agricultural software
        # remains adjacent to a beekeeping product unless the exact target and
        # workflow are both present. Editorial pages can never be products.
        if article_like:
            source_type = "market_article"
        elif source_type in {"competitor", "pricing_page"} and target_match_level != "exact":
            source_type = "adjacent_solution"
        elif source_type in {"adjacent_solution", "irrelevant"} and is_product_page and same_use_case and same_solution and target_match_level == "exact":
            source_type = "competitor"

        ai_type = str(source.get("ai_source_type") or "").strip().lower()
        ai_confidence = self._safe_float(source.get("ai_classifier_confidence"), 0.0)
        ai_product_page = bool(source.get("ai_product_page"))
        ai_same_workflow = bool(source.get("ai_same_workflow"))
        ai_same_sector = bool(source.get("ai_same_sector"))

        # AI is advisory and may improve recall, but it can never create a
        # direct competitor by itself. It may only confirm page shape, sector
        # proximity or workflow proximity when deterministic domain evidence
        # is already present.
        if ai_confidence >= 0.72 and ai_product_page and matched_domain and not article_like:
            is_product_page = True
        if ai_confidence >= 0.78 and ai_same_sector and matched_domain:
            same_sector = True
        if ai_confidence >= 0.80 and ai_same_workflow and matched_domain:
            same_use_case = True

        strong_deterministic_product_match = bool(
            source_type in {"competitor", "pricing_page", "adjacent_solution"}
            and is_product_page
            and matched_domain
            and (same_use_case or same_solution)
        )
        protected_local_evidence = bool(
            region_match == "local"
            and matched_domain
            and source_type in {
                "market_article",
                "directory",
                "official_source",
                "regulation",
                "local_ecosystem",
            }
        )
        if (
            ai_type == "irrelevant"
            and ai_confidence >= 0.90
            and not strong_deterministic_product_match
            and not protected_local_evidence
        ):
            source_type = "irrelevant"
        elif ai_type == "local_ecosystem" and ai_confidence >= 0.70 and region_match == "local" and matched_domain:
            source_type = "local_ecosystem"
        elif ai_type == "official_source" and ai_confidence >= 0.70 and self._looks_official_domain(self._domain(source.get("url") or "")):
            source_type = "official_source"
        elif ai_type == "technology_benchmark" and ai_confidence >= 0.70 and matched_domain:
            source_type = "technology_benchmark"
        elif (
            ai_type == "adjacent_solution"
            and ai_confidence >= 0.65
            and matched_domain
            and not article_like
        ):
            source_type = "adjacent_solution"
        elif (
            ai_type in {"market_evidence", "market_article"}
            and ai_confidence >= 0.65
            and matched_domain
            and not is_product_page
        ):
            source_type = "market_article"

        if (
            region_match == "local"
            and matched_domain
            and self._contains_any(source_text, self.LOCAL_ECOSYSTEM_HINTS)
            and not is_product_page
        ):
            source_type = "local_ecosystem"

        local_solution_announcement = self._looks_like_local_solution_announcement(
            source=source,
            normalized_text=source_text,
            region_match=region_match,
            matched_domain_terms=matched_domain,
            same_use_case=same_use_case,
            same_solution=same_solution,
        )
        if local_solution_announcement:
            # A provider may announce a real adjacent solution through its own
            # blog. It remains an adjacent solution, never a direct competitor,
            # until exact target/workflow/product evidence is verified.
            source_type = "adjacent_solution"
            is_product_page = False

        if job_listing_mismatch:
            source_type = "irrelevant"
            is_product_page = False

        # Document-host pages can provide context, but they are not products or
        # adjacent solutions unless a separately verified product page exists.
        source_domain = self._domain(source.get("url") or "")
        document_host = any(
            source_domain == domain
            or source_domain.endswith(f".{domain}")
            for domain in self.DOCUMENT_HOST_DOMAINS
            if not domain.startswith("www.")
        )
        if document_host:
            source_type = "market_article"
            is_product_page = False
            same_use_case = False
            same_solution = False
            same_target = False
            target_match_level = "none"

        # Sector mismatch is kept as neutral compatibility metadata.
        # Competitor and benchmark classification is now driven entirely by
        # positive project semantics, operation equivalence and geography.
        mismatch_terms = []
        sector_mismatch = False

        role_decision = source_role_resolver.resolve(
            source=source,
            decision={
                "source_type": source_type,
                "region_match": region_match,
                "is_product_page": is_product_page,
                "same_or_close_target_user": same_target,
                "same_or_close_use_case": same_use_case,
                "same_or_close_solution_category": same_solution,
                "sector_mismatch": sector_mismatch,
            },
            project_context=project_context,
        )
        consumer_operation = bool(role_decision.get("consumer_operation"))
        operation_equivalent = bool(role_decision.get("operation_equivalent"))
        source_role = str(role_decision.get("source_role") or "irrelevant")
        canonical_category = str(
            role_decision.get("canonical_category") or "irrelevant"
        )
        comparison_scope = str(role_decision.get("comparison_scope") or "irrelevant")
        technology_supplier = bool(role_decision.get("technology_supplier"))
        canonical_source_id = str(role_decision.get("canonical_source_id") or "")
        source_type = str(role_decision.get("legacy_source_type") or source_type)

        if job_listing_mismatch:
            source_type = "irrelevant"
            source_role = "irrelevant"
            canonical_category = "irrelevant"
            comparison_scope = "irrelevant"
            technology_supplier = False
            canonical_source_id = ""

        ai_adjacent_confirmation = bool(
            ai_type == "adjacent_solution"
            and ai_confidence >= 0.75
            and ai_product_page
            and ai_same_sector
            and matched_domain
            and not article_like
        )
        matched_use_case_set = set(
            matched_use_case
        )
        matched_solution_set = set(
            matched_solution
        )

        # A compact local product page may expose only one workflow
        # token while still providing independent business-domain
        # evidence. This is sufficient for adjacent evidence, but
        # never sufficient by itself for direct-competitor identity.
        distinctive_domain_anchor = any(
            term not in matched_use_case_set
            and term not in matched_solution_set
            for term in matched_domain
        )

        compact_local_operation_evidence = bool(
            source_role == "adjacent_solution"
            and is_product_page
            and consumer_operation
            and distinctive_domain_anchor
            and (
                matched_use_case
                or matched_solution
            )
            and not sector_mismatch
        )

        local_adjacent_evidence = bool(
            source_type == "adjacent_solution"
            and source_role == "adjacent_solution"
            and region_match == "local"
            and matched_domain
            and (
                same_use_case
                or same_solution
                or ai_adjacent_confirmation
                or local_solution_announcement
                or compact_local_operation_evidence
            )
        )

        if operation_equivalent and source_role == "direct_competitor":
            # Operational equivalence establishes workflow and solution
            # proximity from deterministic project semantics. It does not
            # invent an exact target-user identity.
            same_use_case = True
            same_solution = True
            is_product_page = True
            source_type = "competitor"

        semantic_equivalence_evidence = bool(
            operation_equivalent
            and source_role == "direct_competitor"
            and region_match == "local"
            and consumer_operation
            and not sector_mismatch
        )

        matched_forbidden = self._blocking_forbidden_terms(
            terms=raw_matched_forbidden,
            title_url_text=title_url_text,
            source_role=source_role,
            region_match=region_match,
            strong_business_match=bool(
                (matched_domain or semantic_equivalence_evidence)
                and (same_target or consumer_operation)
                and (same_use_case or same_solution)
            ),
        )

        evidence_categories = self._evidence_categories(
            source=source,
            source_type=source_type,
            region_match=region_match,
            matched_domain_terms=matched_domain,
            same_use_case=same_use_case,
            same_solution=same_solution,
            product_signals=product_signals,
            pricing_signals=pricing_signals,
            market_size_signals=market_size_signals,
            demand_signals=demand_signals,
            problem_signals=problem_signals,
            regulation_signals=regulation_signals,
            local_adjacent_evidence=local_adjacent_evidence,
        )

        if semantic_equivalence_evidence and not evidence_categories:
            evidence_categories = ["solution_benchmark"]

        clear_contextual_link = bool(
            (matched_domain and (same_use_case or same_solution))
            or (
                region_match == "local"
                and consumer_operation
                and matched_domain
            )
            or semantic_equivalence_evidence
            or (
                source_type in {
                    "market_article",
                    "regulation",
                    "official_source",
                    "local_ecosystem",
                }
                and matched_domain
                and evidence_categories
            )
            or local_adjacent_evidence
            or (
                source_type == "technology_benchmark"
                and matched_domain
                and evidence_categories
            )
        )

        score = self._score(
            source=source,
            source_type=source_type,
            region_match=region_match,
            matched_domain_terms=matched_domain,
            matched_sector_terms=matched_sector,
            matched_target_terms=matched_target,
            matched_use_case_terms=matched_use_case,
            matched_solution_terms=matched_solution,
            matched_weak_terms=matched_weak,
            matched_forbidden_terms=matched_forbidden,
            off_topic_terms=off_topic,
            same_target=same_target,
            same_sector=same_sector,
            same_use_case=same_use_case,
            same_solution=same_solution,
            clear_contextual_link=clear_contextual_link,
            product_signals=product_signals,
            evidence_categories=evidence_categories,
        )

        if (
            operation_equivalent
            and source_role == "direct_competitor"
            and region_match == "local"
        ):
            # Deterministic operational equivalence already established
            # that this live source performs the project's core workflow.
            # Preserve a moderate evidence floor for compact product pages
            # that expose only a subset of canonical terminology.
            score = max(score, 0.60)

        is_direct_competitor = self._is_direct_competitor(
            score=score,
            source_type=source_type,
            source_role=source_role,
            region_match=region_match,
            matched_domain_terms=matched_domain,
            same_target=same_target,
            same_sector=same_sector,
            same_use_case=same_use_case,
            same_solution=same_solution,
            product_signals=product_signals,
            title_url_text=title_url_text,
            consumer_operation=consumer_operation,
            operation_equivalent=operation_equivalent,
        )

        rejection_reason = self._rejection_reason(
            score=score,
            source_type=source_type,
            source_role=source_role,
            region_match=region_match,
            matched_domain_terms=matched_domain,
            matched_forbidden_terms=matched_forbidden,
            off_topic_terms=off_topic,
            clear_contextual_link=clear_contextual_link,
            same_use_case=same_use_case,
            same_solution=same_solution,
            product_signals=product_signals,
            evidence_categories=evidence_categories,
            local_adjacent_evidence=local_adjacent_evidence,
            semantic_equivalence_evidence=semantic_equivalence_evidence,
        )
        rejected = bool(rejection_reason)
        display_threshold = self.PUBLIC_DISPLAY_THRESHOLD
        if source_role == "direct_competitor" and region_match == "local":
            display_threshold = 0.58
        elif source_type == "local_ecosystem" and region_match == "local":
            display_threshold = 0.28
        elif source_type in {"official_source", "regulation"}:
            display_threshold = 0.50
        elif source_type == "market_article" and region_match == "local":
            display_threshold = 0.36
        elif source_type == "market_article":
            display_threshold = 0.42
        elif source_type == "adjacent_solution" and region_match == "local":
            display_threshold = 0.32
        elif source_role in {
            "technology_provider",
            "regional_benchmark",
            "international_benchmark",
        } or source_type == "technology_benchmark":
            display_threshold = 0.40

        public_display = bool(
            not rejected
            and score >= display_threshold
            and clear_contextual_link
            and evidence_categories
        )
        internal_threshold = self.INTERNAL_USE_THRESHOLD
        if source_type == "technology_benchmark":
            internal_threshold = 0.20
        elif source_type == "local_ecosystem":
            internal_threshold = 0.22
        elif source_type == "adjacent_solution" and region_match == "local":
            internal_threshold = 0.24
        elif source_type == "market_article" and region_match == "local":
            internal_threshold = 0.28
        elif source_type == "market_article":
            internal_threshold = 0.35
        internal_only = bool(
            not rejected
            and not public_display
            and score >= internal_threshold
        )

        matched_strong = self._unique(
            matched_domain + matched_use_case + matched_solution + matched_target
        )
        market_evidence_signals = self._unique(
            market_size_signals + demand_signals + problem_signals + regulation_signals
        )
        confidence = self._confidence(
            score=score,
            public_display=public_display,
            is_direct_competitor=is_direct_competitor,
            evidence_categories=evidence_categories,
            matched_domain_terms=matched_domain,
        )
        public_reason = self._public_reason(
            source_type=source_type,
            source_role=source_role,
            canonical_category=canonical_category,
            region_match=region_match,
            evidence_categories=evidence_categories,
            output_language=str(project_context.get("output_language") or "fr"),
        )
        why_relevant = self._why_relevant(
            source_type=source_type,
            source_role=source_role,
            canonical_category=canonical_category,
            comparison_scope=comparison_scope,
            region_match=region_match,
            matched_domain_terms=matched_domain,
            matched_target_terms=matched_target,
            matched_use_case_terms=matched_use_case,
            matched_solution_terms=matched_solution,
            product_signals=product_signals,
            evidence_categories=evidence_categories,
            is_direct_competitor=is_direct_competitor,
            public_display=public_display,
            internal_only=internal_only,
            rejection_reason=rejection_reason,
        )
        return asdict(SourceRelevanceDecision(
            source_relevance_score=round(score, 2),
            public_display=public_display,
            internal_only=internal_only,
            rejected=rejected,
            source_type=source_type,
            source_role=source_role,
            canonical_category=canonical_category,
            comparison_scope=comparison_scope,
            region_match=region_match,
            is_direct_competitor=is_direct_competitor,
            technology_supplier=technology_supplier,
            canonical_source_id=canonical_source_id,
            confidence=confidence,
            matched_strong_terms=matched_strong[:24],
            matched_weak_terms=matched_weak[:20],
            matched_forbidden_terms=matched_forbidden[:20],
            matched_domain_terms=matched_domain[:16],
            matched_sector_terms=matched_sector[:12],
            matched_target_terms=matched_target[:12],
            matched_use_case_terms=matched_use_case[:16],
            matched_solution_terms=matched_solution[:16],
            product_evidence_signals=product_signals[:16],
            market_evidence_signals=market_evidence_signals[:16],
            evidence_categories=evidence_categories[:12],
            same_or_close_target_user=same_target,
            same_or_close_sector=same_sector,
            target_match_level=target_match_level,
            is_product_page=is_product_page,
            same_or_close_use_case=same_use_case,
            same_or_close_solution_category=same_solution,
            clear_contextual_link=clear_contextual_link,
            sector_mismatch=sector_mismatch,
            mismatch_terms=mismatch_terms[:12],
            why_relevant=why_relevant,
            public_reason=public_reason,
            rejection_reason=rejection_reason,
        ))

    def filter_sources(
        self,
        *,
        sources: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        public_sources: List[Dict[str, Any]] = []
        internal_sources: List[Dict[str, Any]] = []
        rejected_sources: List[Dict[str, Any]] = []

        for source in sources:
            if not isinstance(source, dict):
                continue
            decision = self.evaluate_source(
                source=source,
                project_context=project_context,
            )
            enriched = {**source, **decision}
            if decision["public_display"]:
                public_sources.append(enriched)
            elif decision["internal_only"]:
                internal_sources.append(enriched)
            else:
                rejected_sources.append(enriched)

        for items in (public_sources, internal_sources, rejected_sources):
            items.sort(
                key=lambda item: float(item.get("source_relevance_score") or 0),
                reverse=True,
            )

        return {
            "public_sources": public_sources,
            "internal_sources": internal_sources,
            "rejected_sources": rejected_sources,
            "public_sources_count": len(public_sources),
            "internal_sources_count": len(internal_sources),
            "rejected_sources_count": len(rejected_sources),
        }

    # ========================================================
    # Context construction
    # ========================================================

    def _build_context(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
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

        title = self._safe_text(
            structured.get("project_name")
            or structured.get("title")
            or project_context.get("project_name")
            or project_context.get("title")
        )
        region = self._safe_text(
            structured.get("target_region")
            or structured.get("market_region")
            or project_context.get("target_region")
            or project_context.get("market_region")
        )

        weak_terms = set(self.DEFAULT_WEAK_TERMS)
        weak_terms.update(self._normalized_list(
            project_context.get("weak_terms_to_ignore")
            or packet.get("weak_terms_to_ignore")
        ))

        sector_raw: List[Any] = [
            structured.get("sector"),
            structured.get("industry"),
            project_context.get("sector"),
            project_context.get("industry"),
        ]
        domain_raw: List[Any] = [
            project_context.get("domain_concepts"),
            project_context.get("search_concepts"),
            packet.get("domain_concepts"),
            packet.get("search_concepts"),
            structured.get("domain_concepts"),
            structured.get("search_concepts"),
            structured.get("sector_tags"),
            structured.get("vertical"),
            structured.get("project_archetype"),
            project_context.get("strong_keywords"),
            packet.get("strong_keywords"),
            project_context.get("must_match_terms"),
            packet.get("must_match_terms"),
            structured.get("sector"),
            structured.get("industry"),
        ]
        target_raw: List[Any] = [
            project_context.get("target_terms"), packet.get("target_terms"),
            structured.get("target_terms"), structured.get("target_users"),
            project_context.get("target_users"), project_context.get("target_market"),
        ]

        explicit_use_case_raw: List[Any] = [
            project_context.get("use_case_terms"), packet.get("use_case_terms"),
            structured.get("use_case_terms"), structured.get("use_cases"),
            structured.get("priority_workflows"),
        ]
        use_case_raw = (
            explicit_use_case_raw
            if any(self._flatten_strings(value) for value in explicit_use_case_raw)
            else [structured.get("main_use_case"), project_context.get("main_use_case")]
        )

        explicit_solution_raw: List[Any] = [
            project_context.get("solution_terms"), packet.get("solution_terms"),
            structured.get("solution_terms"), structured.get("solution_category"),
        ]
        solution_raw = (
            explicit_solution_raw
            if any(self._flatten_strings(value) for value in explicit_solution_raw)
            else [structured.get("solution_type"), project_context.get("solution_type")]
        )
        problem_raw: List[Any] = [
            project_context.get("problem_keywords"), packet.get("problem_keywords"),
            structured.get("problem_keywords"), structured.get("problem"),
        ]

        title_terms = self._concept_terms([title], weak_terms, max_items=12)
        region_terms = self._region_aliases(region)
        target_terms = self._concept_terms(target_raw, weak_terms, max_items=36)
        target_terms = self._remove_noise_terms(target_terms, region_terms + title_terms)

        functional_noise = region_terms + title_terms + target_terms
        use_case_terms = self._remove_noise_terms(
            self._concept_terms(use_case_raw, weak_terms, max_items=48),
            functional_noise,
        )
        solution_terms = self._remove_noise_terms(
            self._concept_terms(solution_raw, weak_terms, max_items=42),
            functional_noise,
        )
        problem_terms = self._remove_noise_terms(
            self._concept_terms(problem_raw, weak_terms, max_items=30),
            region_terms + title_terms,
        )
        sector_terms = self._remove_noise_terms(
            self._concept_terms(sector_raw, weak_terms, max_items=24),
            region_terms + title_terms + target_terms,
        )
        domain_terms = self._remove_noise_terms(
            self._concept_terms(domain_raw, weak_terms, max_items=64),
            region_terms + title_terms + target_terms,
        )




        forbidden = set(self.DEFAULT_FORBIDDEN_DEMO_TERMS)
        forbidden.update(self._normalized_list(
            project_context.get("forbidden_offtopic_terms")
            or packet.get("forbidden_offtopic_terms")
        ))
        current_project_text = self._normalize(" ".join(
            [title, region] + domain_terms + target_terms + use_case_terms + solution_terms
        ))
        forbidden = {
            term for term in forbidden
            if term and not self._term_matches(term, current_project_text)
        }

        return {
            "title": title,
            "region": region,
            "region_aliases": self._region_aliases(region),
            "domain_terms": self._unique(domain_terms)[:48],
            "sector_terms": self._unique(sector_terms)[:20],
            "target_terms": self._unique(target_terms)[:30],
            "use_case_terms": self._unique(use_case_terms)[:36],
            "solution_terms": self._unique(solution_terms)[:32],
            "problem_terms": self._unique(problem_terms)[:24],
            "weak_terms": weak_terms,
            "forbidden_terms": forbidden,
        }

    def _concept_terms(
        self,
        values: Sequence[Any],
        weak_terms: Set[str],
        max_items: int,
    ) -> List[str]:
        terms: List[str] = []
        for value in values:
            for item in self._flatten_strings(value):
                normalized = self._normalize(item)
                if not normalized:
                    continue
                tokens = [
                    token for token in self._tokens(normalized)
                    if token not in weak_terms
                    and token not in self.CONTEXT_STOP_WORDS
                    and len(token) >= 3
                ]
                if not tokens:
                    continue
                # Keep original compact phrases and meaningful 2/3-grams. Full
                # sentences are never used as one evidence term.
                if 1 <= len(tokens) <= 4:
                    terms.append(" ".join(tokens))
                for size in (3, 2, 1):
                    for index in range(0, len(tokens) - size + 1):
                        phrase = " ".join(tokens[index:index + size])
                        if self._useful_term(phrase, weak_terms):
                            terms.append(phrase)
        terms = self._unique(terms)
        terms.sort(
            key=lambda item: (
                1 if 2 <= len(item.split()) <= 3 else 0,
                len(item.split()),
                len(item),
            ),
            reverse=True,
        )
        return terms[:max_items]

    def _remove_noise_terms(
        self,
        terms: List[str],
        noise_terms: List[str],
    ) -> List[str]:
        noise_tokens = {
            token
            for term in noise_terms
            for token in self._tokens(term)
        }
        result: List[str] = []
        for term in terms:
            remaining = [token for token in self._tokens(term) if token not in noise_tokens]
            if not remaining:
                continue
            candidate = " ".join(remaining)
            if self._useful_term(candidate, set(self.DEFAULT_WEAK_TERMS)):
                result.append(candidate)
        return self._unique(result)


    # ========================================================
    # Classification and evidence categories
    # ========================================================

    def _classify_source_type(
        self,
        *,
        source: Dict[str, Any],
        normalized_text: str,
        matched_domain_terms: List[str],
        product_signals: List[str],
        pricing_signals: List[str],
        regulation_signals: List[str],
    ) -> str:
        domain = self._domain(source.get("url") or "")

        if self._is_search_or_social_domain(domain):
            return "irrelevant"

        # Editorial pages, reports, forums and listicles are evidence pages,
        # never product competitors. This rule must run before product-signal
        # detection because articles frequently mention features and pricing.
        if self._looks_like_article_or_list(source):
            title_url = self._normalize(
                f"{source.get('title', '')} {source.get('url', '')}"
            )
            if self._contains_any(title_url, self.DIRECTORY_HINTS):
                return "directory"
            return "market_article"

        if self._is_market_source_domain(domain) or self._is_research_domain(domain):
            return "market_article"

        if regulation_signals and self._looks_official_domain(domain):
            return "regulation"
        if self._looks_official_domain(domain) and matched_domain_terms:
            return "official_source"

        # Official app stores are treated as product pages when the listing
        # contains real project-domain concepts.
        if self._domain_in(domain, self.PRODUCT_LISTING_DOMAINS):
            return "competitor" if matched_domain_terms else "irrelevant"

        if pricing_signals and self._pricing_path(source.get("url") or ""):
            return "pricing_page"

        if len(product_signals) >= 2 and matched_domain_terms:
            return "competitor"

        if matched_domain_terms and self._contains_any(
            normalized_text,
            {"platform", "software", "application", "app", "solution", "tool", "system"},
        ):
            return "adjacent_solution"

        if matched_domain_terms and self._contains_any(
            normalized_text,
            self.PROBLEM_CONTEXT_SIGNALS | self.DEMAND_SIGNALS | self.MARKET_SIZE_SIGNALS,
        ):
            return "market_article"

        return "irrelevant"

    def _evidence_categories(
        self,
        *,
        source: Dict[str, Any],
        source_type: str,
        region_match: str,
        matched_domain_terms: List[str],
        same_use_case: bool,
        same_solution: bool,
        product_signals: List[str],
        pricing_signals: List[str],
        market_size_signals: List[str],
        demand_signals: List[str],
        problem_signals: List[str],
        regulation_signals: List[str],
        local_adjacent_evidence: bool,
    ) -> List[str]:
        if not matched_domain_terms:
            return []

        domain = self._domain(source.get("url") or "")
        authoritative = bool(
            self._looks_official_domain(domain)
            or self._is_research_domain(domain)
        ) and not self._domain_in(domain, self.COMMERCIAL_MARKET_REPORT_DOMAINS)
        categories: List[str] = []

        if source_type == "regulation" and regulation_signals and self._looks_official_domain(domain):
            categories.append("regulation")
        if source_type == "official_source":
            categories.append("official_context")
        if source_type == "local_ecosystem":
            categories.extend(["local_ecosystem", "ecosystem_signal"])

        if market_size_signals and source_type in {"market_article", "directory", "regulation", "official_source"}:
            categories.append("market_size" if authoritative else "market_size_claim")

        if demand_signals and source_type in {"market_article", "directory", "regulation", "official_source"}:
            categories.append("market_demand" if authoritative else "market_demand_claim")

        if problem_signals and source_type in {"market_article", "regulation", "official_source"}:
            categories.append("problem_context")

        if source_type in {"competitor", "pricing_page", "adjacent_solution", "technology_benchmark"} and (
            same_use_case or same_solution
        ):
            categories.append("solution_benchmark")
        elif source_type == "technology_benchmark" and matched_domain_terms:
            categories.append("technology_benchmark")

        # Locality, target labels and repeated sector vocabulary are not sufficient.
        # A public adjacent solution must have deterministic workflow/solution
        # proximity or a high-confidence AI classification confirming both
        # product shape and sector proximity.
        if local_adjacent_evidence:
            categories.append("adjacent_solution")

        if source_type in {"competitor", "pricing_page"} and product_signals and (
            same_use_case or same_solution
        ):
            categories.append("competitor_product")

        if source_type == "pricing_page" or (
            pricing_signals and source_type in {"competitor", "adjacent_solution"}
        ):
            categories.append("pricing")

        if region_match in {"local", "regional"} and source_type in {
            "market_article", "directory", "regulation", "official_source", "adjacent_solution", "local_ecosystem"
        }:
            categories.append("regional_context")

        if source_type == "market_article":
            categories.append("workflow_context" if problem_signals else "sector_context")
            if region_match == "local":
                categories.append("local_market_signal")
            if self._contains_any(
                self._source_text(source),
                {"notebook", "paper", "spreadsheet", "excel", "whatsapp", "manual process", "record keeping", "recordkeeping"},
            ):
                categories.append("current_alternatives")

        return self._unique(categories)

    def _is_direct_competitor(
        self,
        *,
        score: float,
        source_type: str,
        source_role: str,
        region_match: str,
        matched_domain_terms: List[str],
        same_target: bool,
        same_sector: bool,
        same_use_case: bool,
        same_solution: bool,
        product_signals: List[str],
        title_url_text: str,
        consumer_operation: bool,
        operation_equivalent: bool,
    ) -> bool:
        if source_role != "direct_competitor":
            return False

        if source_type not in {"competitor", "pricing_page"}:
            return False

        minimum_score = (
            0.58
            if (
                consumer_operation
                or operation_equivalent
            )
            else self.DIRECT_COMPETITOR_THRESHOLD
        )

        if (
            region_match != "local"
            or score < minimum_score
        ):
            return False

        # SourceRoleResolver is authoritative for the business
        # relationship. Do not re-require lexical target identity
        # after it has already established a direct local operation.
        #
        # The gate keeps only page/evidence safeguards here.
        product_or_operation_evidence = bool(
            len(product_signals) >= 2
            or self._pricing_path(title_url_text)
            or consumer_operation
            or operation_equivalent
        )

        if not product_or_operation_evidence:
            return False

        return True

    def _classify_region(
        self,
        source: Dict[str, Any],
        normalized_text: str,
        context: Dict[str, Any],
    ) -> str:
        domain = self._domain(source.get("url") or "")
        for marker in context.get("region_aliases") or []:
            if marker == ".tn" and domain.endswith(".tn"):
                return "local"
            if marker and self._term_matches(marker, normalized_text):
                return "local"
        if any(self._term_matches(marker, normalized_text) for marker in self.REGIONAL_MARKERS):
            return "regional"
        return "international" if domain else "unknown"

    def _blocking_forbidden_terms(
        self,
        *,
        terms: List[str],
        title_url_text: str,
        source_role: str,
        region_match: str,
        strong_business_match: bool,
    ) -> List[str]:
        """Block real cross-domain contamination without punishing product breadth.

        Project-intelligence packets may mark broad labels such as ``super app``
        as off-topic. A valid local product can legitimately use that label while
        still offering the exact workflow under analysis. When the source has a
        strong target/workflow match and has already resolved to a product-like
        role, a soft forbidden term blocks only when it also contaminates the
        title or URL. Weak or unrelated sources keep the strict behaviour.
        """
        clean_terms = self._unique(terms)
        if not clean_terms:
            return []

        soft_terms = [
            term for term in clean_terms
            if self._normalize(term) in self.SOFT_FORBIDDEN_TERMS
        ]
        hard_terms = [
            term for term in clean_terms
            if self._normalize(term) not in self.SOFT_FORBIDDEN_TERMS
        ]

        # Hard cross-domain terms always remain blocking.
        blockers = list(hard_terms)

        # A soft breadth label is only suspicious when it contaminates the
        # title/URL and the source has no exact business/workflow match.
        # Body-only occurrences never reject a valid product source.
        if not strong_business_match:
            blockers.extend(
                term for term in soft_terms
                if self._term_matches(term, title_url_text)
            )

        return self._unique(blockers)

    # ========================================================
    # Scoring and decisions
    # ========================================================

    def _score(
        self,
        *,
        source: Dict[str, Any],
        source_type: str,
        region_match: str,
        matched_domain_terms: List[str],
        matched_sector_terms: List[str],
        matched_target_terms: List[str],
        matched_use_case_terms: List[str],
        matched_solution_terms: List[str],
        matched_weak_terms: List[str],
        matched_forbidden_terms: List[str],
        off_topic_terms: List[str],
        same_target: bool,
        same_sector: bool,
        same_use_case: bool,
        same_solution: bool,
        clear_contextual_link: bool,
        product_signals: List[str],
        evidence_categories: List[str],
    ) -> float:
        """Return a calibrated evidence score rather than a saturated count.

        The score measures source usefulness for this project, not truth of the
        startup idea. Caps are type-specific so a listicle can never score like
        an official product page and a directory can never appear high-confidence.
        """
        score = 0.0

        score += min(0.26, 0.065 * len(matched_domain_terms))
        score += min(0.08, 0.04 * len(matched_sector_terms))
        score += min(0.10, 0.04 * len(matched_use_case_terms))
        score += min(0.10, 0.04 * len(matched_solution_terms))
        score += min(0.06, 0.03 * len(matched_target_terms))

        if same_target:
            score += 0.04
        if same_sector:
            score += 0.05
        if same_use_case:
            score += 0.08
        if same_solution:
            score += 0.08
        if clear_contextual_link:
            score += 0.05

        score += min(0.12, 0.035 * len(evidence_categories))
        if "market_size" in evidence_categories:
            score += 0.10
        if "market_demand" in evidence_categories:
            score += 0.07
        if "problem_context" in evidence_categories:
            score += 0.05
        if "competitor_product" in evidence_categories:
            score += 0.08
        if "pricing" in evidence_categories:
            score += 0.03
        if "adjacent_solution" in evidence_categories:
            score += 0.08
        if "ecosystem_signal" in evidence_categories:
            score += 0.06
        if "local_market_signal" in evidence_categories:
            score += 0.06

        domain = self._domain(source.get("url") or "")
        if source_type == "market_article" and (
            self._is_market_source_domain(domain) or self._is_research_domain(domain)
        ):
            score += 0.12
        if (
            "market_size" in evidence_categories
            and "market_demand" in evidence_categories
        ):
            score += 0.12
        if region_match == "local" and (
            "market_size" in evidence_categories
            or "market_demand" in evidence_categories
            or "problem_context" in evidence_categories
        ):
            score += 0.06

        if source_type in {"competitor", "pricing_page"}:
            score += min(0.08, 0.02 * len(product_signals))
        elif source_type == "adjacent_solution":
            score += 0.04
        elif source_type == "technology_benchmark":
            score -= 0.03
        elif source_type == "local_ecosystem":
            score += 0.03
        elif source_type in {"regulation", "official_source"}:
            score += 0.04
        elif source_type == "market_article":
            score += 0.02
        elif source_type == "directory":
            score -= 0.04
        elif source_type == "irrelevant":
            score -= 0.35

        if region_match == "local":
            score += 0.03
        elif region_match == "regional":
            score += 0.015

        if source.get("text_extracted"):
            score += 0.02

        if matched_forbidden_terms:
            score -= 0.70
        if off_topic_terms:
            score -= 0.75
        if matched_weak_terms and not matched_domain_terms:
            score -= 0.35
        if not evidence_categories:
            score -= 0.20

        # Type-specific ceilings preserve discrimination.
        caps = {
            "competitor": 0.95,
            "pricing_page": 0.93,
            "adjacent_solution": 0.86,
            "technology_benchmark": 0.76,
            "local_ecosystem": 0.78,
            "official_source": 0.88,
            "regulation": 0.84,
            "market_article": 0.80 if (
                "market_size" in evidence_categories
                or "market_demand" in evidence_categories
            ) else 0.74,
            "directory": 0.68,
            "irrelevant": 0.35,
        }
        score = min(score, caps.get(source_type, 0.80))
        return max(0.0, min(1.0, score))

    def _rejection_reason(
        self,
        *,
        score: float,
        source_type: str,
        source_role: str,
        region_match: str,
        matched_domain_terms: List[str],
        matched_forbidden_terms: List[str],
        off_topic_terms: List[str],
        clear_contextual_link: bool,
        same_use_case: bool,
        same_solution: bool,
        product_signals: List[str],
        evidence_categories: List[str],
        local_adjacent_evidence: bool,
        semantic_equivalence_evidence: bool,
    ) -> str:
        if matched_forbidden_terms:
            return "Rejected because the source matches forbidden off-topic terms."
        if off_topic_terms:
            return "Rejected because the title or URL is clearly off-topic."
        if source_type == "irrelevant" or source_role == "irrelevant":
            return "Rejected because no relevant evidence type could be established."
        if not matched_domain_terms and not semantic_equivalence_evidence:
            return "Rejected because no project-specific domain concept was found."
        if not clear_contextual_link:
            return "Rejected because the contextual link to the exact project is insufficient."

        if source_type in {"competitor", "pricing_page"}:
            if not product_signals and source_role != "direct_competitor":
                return "Rejected because no explicit product-page signal was found."
            if not same_use_case and not same_solution:
                return "Rejected because the source does not match the use case or solution category."
        elif source_type == "adjacent_solution":
            if (
                not local_adjacent_evidence
                and not same_use_case
                and not same_solution
            ):
                return "Rejected because the adjacent-solution link is too weak."
        elif source_type == "technology_benchmark":
            if not evidence_categories:
                return "Rejected because no technology-benchmark evidence was established."

        if not evidence_categories:
            return "Rejected because the source cannot support a defined evidence category."

        minimum_score = self.INTERNAL_USE_THRESHOLD
        if source_type == "local_ecosystem":
            minimum_score = 0.22
        elif source_type == "technology_benchmark":
            minimum_score = 0.20
        elif source_type == "adjacent_solution" and region_match == "local":
            minimum_score = 0.24
        elif source_type in {"official_source", "regulation"}:
            minimum_score = 0.40
        elif source_type == "market_article" and region_match == "local":
            minimum_score = 0.28
        elif source_type == "market_article":
            minimum_score = 0.35
        if score < minimum_score:
            return "Rejected because source relevance is below the internal threshold."
        return ""

    def _confidence(
        self,
        *,
        score: float,
        public_display: bool,
        is_direct_competitor: bool,
        evidence_categories: List[str],
        matched_domain_terms: List[str],
    ) -> str:
        if is_direct_competitor and score >= 0.86:
            return "high"
        if public_display and score >= 0.78 and len(matched_domain_terms) >= 2:
            return "high"
        if public_display and evidence_categories:
            return "medium"
        return "low"

    def _public_reason(
        self,
        *,
        source_type: str,
        source_role: str,
        canonical_category: str,
        region_match: str,
        evidence_categories: List[str],
        output_language: str,
    ) -> str:
        del source_type, source_role, evidence_categories
        language = str(output_language or "fr").lower()
        local = region_match == "local"

        if language == "en":
            labels = {
                "direct_competitor": "Verified direct competitor",
                "adjacent_solution": "Adjacent solution",
                "technology_benchmark": "Technology benchmark",
                "market_evidence": "Market evidence",
                "ecosystem_actor": "Ecosystem actor",
            }
            base = labels.get(canonical_category, "Relevant external source")
            location = "local" if local else region_match
            return f"{base} retained as {location} evidence."

        if canonical_category == "direct_competitor":
            return "Concurrent direct local vérifié." if local else "Concurrent direct vérifié."
        if canonical_category == "adjacent_solution":
            return "Solution adjacente locale retenue." if local else "Solution adjacente retenue comme benchmark."
        if canonical_category == "technology_benchmark":
            return "Benchmark technologique local retenu." if local else "Benchmark technologique international retenu."
        if canonical_category == "market_evidence":
            return "Preuve de marché locale retenue." if local else "Preuve de marché externe retenue."
        if canonical_category == "ecosystem_actor":
            return "Acteur local de l’écosystème retenu." if local else "Acteur de l’écosystème retenu."
        return "Source externe pertinente retenue."

    def _why_relevant(
        self,
        *,
        source_type: str,
        source_role: str,
        canonical_category: str,
        comparison_scope: str,
        region_match: str,
        matched_domain_terms: List[str],
        matched_target_terms: List[str],
        matched_use_case_terms: List[str],
        matched_solution_terms: List[str],
        product_signals: List[str],
        evidence_categories: List[str],
        is_direct_competitor: bool,
        public_display: bool,
        internal_only: bool,
        rejection_reason: str,
    ) -> str:
        if rejection_reason:
            return rejection_reason
        parts = [
            f"type={source_type}",
            f"role={source_role}",
            f"category={canonical_category}",
            f"scope={comparison_scope}",
            f"region={region_match}",
            f"evidence={','.join(evidence_categories)}",
            f"domain_terms={','.join(matched_domain_terms[:5])}",
        ]
        if matched_target_terms:
            parts.append(f"target_terms={','.join(matched_target_terms[:3])}")
        if matched_use_case_terms:
            parts.append(f"use_case_terms={','.join(matched_use_case_terms[:3])}")
        if matched_solution_terms:
            parts.append(f"solution_terms={','.join(matched_solution_terms[:3])}")
        if product_signals:
            parts.append(f"product_signals={','.join(product_signals[:3])}")
        if is_direct_competitor:
            parts.append("direct_competitor=true")
        parts.append("public_display=true" if public_display else "internal_only=true")
        return " | ".join(parts)

    # ========================================================
    # Text and URL helpers
    # ========================================================

    def _source_text(self, source: Dict[str, Any]) -> str:
        # search_query is intentionally excluded. A query contains project words
        # by construction and therefore cannot be considered source evidence.
        return " ".join([
            self._safe_text(source.get("title")),
            self._safe_text(source.get("url")),
            self._safe_text(source.get("snippet")),
            self._safe_text(source.get("extracted_text_preview")),
        ])

    def _matched_terms(self, text: str, terms: Iterable[str]) -> List[str]:
        result: List[str] = []
        for term in terms or []:
            clean = self._normalize(term)
            if not clean or len(clean) < 3:
                continue
            if self._term_matches(clean, text):
                result.append(clean)
        return self._unique(result)

    def _target_match_level(
        self,
        *,
        matched_target: List[str],
        available_target_terms: List[str],
    ) -> str:
        del available_target_terms
        if not matched_target:
            return "none"

        distinctive: List[str] = []
        for term in matched_target:
            tokens = [token for token in self._tokens(term) if token not in self.GENERIC_TARGET_TERMS]
            if len(tokens) >= 1:
                distinctive.append(term)

        if any(len(item.split()) >= 2 for item in distinctive):
            return "exact"
        if len({item for item in distinctive if " " not in item}) >= 1:
            return "exact"
        return "adjacent"

    def _semantic_group_match(
        self,
        matched: List[str],
        available: List[str],
        allow_two_single_terms: bool = False,
    ) -> bool:
        if any(len(item.split()) >= 2 for item in matched):
            return True
        if allow_two_single_terms and len({item for item in matched if " " not in item}) >= 2:
            return True
        if not allow_two_single_terms and matched:
            return True
        return bool(matched and len(available) <= 2)

    def _project_is_recruitment_context(self, context: Dict[str, Any]) -> bool:
        project_text = self._normalize(
            " ".join(
                list(context.get("domain_terms") or [])
                + list(context.get("sector_terms") or [])
                + list(context.get("target_terms") or [])
                + list(context.get("use_case_terms") or [])
                + list(context.get("solution_terms") or [])
            )
        )
        return self._contains_any(
            project_text,
            self.RECRUITMENT_CONTEXT_TERMS,
        )

    def _looks_like_job_listing(self, source: Dict[str, Any]) -> bool:
        title = self._normalize(source.get("title", ""))
        url = self._safe_text(source.get("url")).lower()
        path = urlparse(url).path.lower()
        title_url = self._normalize(f"{title} {url}")

        if any(marker in path for marker in self.JOB_URL_HINTS):
            return True
        if self._contains_any(title_url, self.JOB_LISTING_HINTS):
            # Avoid rejecting market articles merely mentioning employment.
            return bool(
                title.startswith(("emploi ", "job ", "offre d'emploi"))
                or "responsable " in title
                or "apply now" in title_url
                or "/job" in path
                or "/career" in path
                or "/offres-emploi" in path
            )
        return False

    def _looks_like_local_solution_announcement(
        self,
        *,
        source: Dict[str, Any],
        normalized_text: str,
        region_match: str,
        matched_domain_terms: List[str],
        same_use_case: bool,
        same_solution: bool,
    ) -> bool:
        if region_match != "local" or not matched_domain_terms:
            return False
        if self._looks_like_job_listing(source):
            return False

        title = self._normalize(source.get("title", ""))
        url = self._safe_text(source.get("url")).lower()
        domain = self._domain(url)
        if not domain or self._is_search_or_social_domain(domain):
            return False
        if self._is_market_source_domain(domain) or self._is_research_domain(domain):
            return False

        # Generic reports, rankings and market pages are evidence, not named
        # solutions. Provider announcements may use a /blog/ URL.
        if self._contains_any(
            title,
            {
                "market size", "market report", "industry report", "top 10",
                "top 15", "best software", "study", "étude", "résultats du projet",
                "newsletter", "emploi", "job",
            },
        ):
            return False

        solution_signal = self._contains_any(
            f"{title} {normalized_text[:1200]}",
            self.SOLUTION_ANNOUNCEMENT_HINTS,
        )
        # A local provider announcement still needs concrete workflow
        # or solution proximity. Repeated sector/domain vocabulary alone
        # must never promote a page into a public adjacent solution.
        semantic_proximity = bool(
            same_use_case or same_solution
        )
        named_solution = bool(
            re.search(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", self._safe_text(source.get("title")))
        )
        return bool(solution_signal and semantic_proximity and named_solution)

    def _looks_like_article_or_list(self, source: Dict[str, Any]) -> bool:
        title = self._normalize(source.get("title", ""))
        url = self._safe_text(source.get("url")).lower()
        title_url = self._normalize(f"{title} {url}")
        domain = self._domain(url)

        if self._contains_any(title_url, self.ARTICLE_OR_LIST_HINTS):
            return True

        if any(re.search(pattern, title, flags=re.IGNORECASE) for pattern in self.ARTICLE_TITLE_PATTERNS):
            return True

        if any(marker in url for marker in self.ARTICLE_URL_HINTS):
            return True

        if domain.startswith("forum.") or domain.startswith("blog."):
            return True

        # Common editorial/forum slugs, including compound slugs such as
        # /a-new-beekeepers-journal/ where a simple /journal/ marker is absent.
        path = urlparse(url).path.lower()
        if re.search(
            r"/(?:[^/]*-)?(?:forum|forums|topic|topics|discussion|community|journal|"
            r"guide|guides|checklist|recordkeeping|review|reviews|tutorial|academy|learn|resources)"
            r"(?:-[^/]*)?(?:/|$)",
            path,
        ):
            return True

        return False

    def _pricing_path(self, url: str) -> bool:
        path = urlparse(str(url)).path.lower()
        return any(marker in path for marker in (
            "/pricing", "/prices", "/plans", "/tarif", "/tarifs", "/abonnement"
        ))

    def _looks_official_domain(self, domain: str) -> bool:
        official_markers = (
            ".gov", ".gov.tn", ".gouv.fr", ".edu", ".ac.",
            "ministry", "ministere", "ministère", "statistics", "statistique",
            "ins.tn", "fao.org", "worldbank.org", "oecd.org", "europa.eu",
        )
        return any(marker in domain for marker in official_markers)

    def _is_market_source_domain(self, domain: str) -> bool:
        return self._domain_in(domain, self.MARKET_SOURCE_DOMAINS)

    def _is_research_domain(self, domain: str) -> bool:
        return self._domain_in(domain, self.RESEARCH_DOMAINS)

    def _is_search_or_social_domain(self, domain: str) -> bool:
        return self._domain_in(domain, self.SEARCH_OR_SOCIAL_DOMAINS)

    def _domain_in(self, domain: str, domains: Iterable[str]) -> bool:
        return any(domain == item or domain.endswith("." + item) for item in domains)

    def _contains_any(self, text: str, terms: Iterable[str]) -> bool:
        return any(self._term_matches(self._normalize(term), text) for term in terms)

    def _term_matches(self, term: str, text: str) -> bool:
        clean = self._normalize(term)
        if not clean or not text:
            return False
        pattern = rf"(?<![a-z0-9à-ÿ]){re.escape(clean)}(?![a-z0-9à-ÿ])"
        return re.search(pattern, text) is not None

    def _region_aliases(self, region: str) -> List[str]:
        normalized = self._normalize(region)
        aliases = [normalized] if normalized else []
        if "tunisie" in normalized or "tunisia" in normalized:
            aliases.extend(["tunisia", "tunisie", "tunisian", "tunisien", ".tn"])
        if "france" in normalized:
            aliases.extend(["france", "french", "français", "francais", ".fr"])
        return self._unique(aliases)

    def _domain(self, url: str) -> str:
        try:
            return urlparse(str(url)).netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def _flatten_strings(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            result: List[str] = []
            for item in value:
                result.extend(self._flatten_strings(item))
            return result
        if isinstance(value, dict):
            result: List[str] = []
            for item in value.values():
                result.extend(self._flatten_strings(item))
            return result
        text = self._safe_text(value)
        if not text:
            return []
        if any(separator in text for separator in (",", ";", "/", "|")):
            return [part.strip() for part in re.split(r"[,;/|]+", text) if part.strip()]
        return [text]

    def _normalized_list(self, value: Any) -> List[str]:
        return self._unique([
            self._normalize(item) for item in self._flatten_strings(value)
            if self._normalize(item)
        ])

    def _tokens(self, value: Any) -> List[str]:
        return [
            token for token in re.split(r"[^a-z0-9à-ÿ]+", self._normalize(value))
            if token
        ]

    def _useful_term(self, term: str, weak_terms: Set[str]) -> bool:
        tokens = [
            token for token in self._tokens(term)
            if token not in weak_terms and token not in self.CONTEXT_STOP_WORDS
        ]
        if not tokens:
            return False
        return not (len(tokens) == 1 and len(tokens[0]) < 4)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    def _safe_text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _normalize(self, value: Any) -> str:
        text = self._safe_text(value).lower().replace("’", "'")
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _unique(self, values: Iterable[str]) -> List[str]:
        result: List[str] = []
        seen: Set[str] = set()
        for value in values:
            clean = self._normalize(value)
            if not clean or clean in seen:
                continue
            seen.add(clean)
            result.append(clean)
        return result


source_relevance_gate = SourceRelevanceGate()