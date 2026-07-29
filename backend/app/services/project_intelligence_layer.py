# ============================================================
# backend/app/services/project_intelligence_layer.py
# ============================================================
#
# ProjectIntelligenceLayer V2 — Structured Context + Real Source Query Planner
#
# Objectifs :
# - transformer l'idée utilisateur en contexte structuré exploitable ;
# - extraire strong_keywords / weak_terms_to_ignore ;
# - générer des requêtes de recherche par intention ;
# - mieux couvrir plusieurs secteurs réels ;
# - ne pas hardcoder de résultats pour un projet précis ;
# - ne pas inventer de concurrents ;
# - aider ForgeCrawler à trouver des sources réelles si elles existent ;
# - garder le fallback honnête si aucune source fiable n'est trouvée.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


class ProjectIntelligenceLayer:
    DEFAULT_WEAK_TERMS = {
        "app",
        "application",
        "platform",
        "plateforme",
        "digital",
        "mobile",
        "service",
        "solution",
        "tool",
        "outil",
        "business",
        "startup",
        "online",
        "website",
        "dashboard",
        "management",
        "manage",
        "create",
        "help",
        "short",
        "lite",
        "system",
        "système",
        "systeme",
        "user",
        "users",
        "client",
        "clients",
        "customer",
        "customers",
        "data",
        "software",
        "logiciel",
        "saas",
    }

    OLD_DEMO_FORBIDDEN_TERMS = {
        "pharmacy",
        "pharmacie",
        "medicine delivery",
        "medicine stock",
        "stock medicaments",
        "stock médicaments",
        "stock trading",
        "trading",
        "crypto",
        "tiktok",
        "super app",
        "ecommerce marketplace",
        "robot agricole",
        "agrobot",
        "greenhouse robot",
        "fintech wallet",
        "orange max it",
    }

    SECTOR_PROFILES = {
        "edtech": {
            "strong_terms": [
                "training center",
                "training centers",
                "private training center",
                "instructor",
                "independent instructor",
                "course management",
                "learner registration",
                "learner progress",
                "attendance tracking",
                "certificate generation",
                "vocational training",
                "professional training",
                "lms",
                "learning management system",
                "centre de formation",
                "centres de formation",
                "formateur indépendant",
                "inscription apprenant",
                "suivi apprenant",
                "suivi de présence",
                "certificat",
                "formation professionnelle",
            ],
            "weak_terms": [
                "course",
                "courses",
                "learning",
                "education",
                "school",
                "student",
                "students",
                "learn",
                "training",
                "edtech",
            ],
            "forbidden_terms": [
                "food delivery",
                "grocery delivery",
                "stock trading",
                "crypto",
                "doctor appointment",
                "greenhouse robot",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia training center management software",
                    "Tunisia LMS for private training centers",
                    "Tunisia course registration attendance certificate software",
                    "centre de formation Tunisie logiciel gestion apprenants certificats",
                ],
                "adjacent_solutions": [
                    "North Africa LMS small training centers",
                    "course management software independent instructors",
                    "attendance certificate management training providers",
                ],
                "market_sources": [
                    "Tunisia vocational training private centers digital transformation",
                    "Tunisia EdTech startups training centers",
                    "formation professionnelle privée Tunisie digitalisation",
                ],
                "pricing": [
                    "LMS pricing small training centers",
                    "course management SaaS pricing instructors",
                ],
            },
        },
        "hrtech": {
            "strong_terms": [
                "employee training",
                "corporate training",
                "skills tracking",
                "training management",
                "competency tracking",
                "hr training platform",
                "formation employés",
                "gestion compétences",
                "suivi formation",
            ],
            "weak_terms": [
                "hr",
                "career",
                "job",
                "talent",
                "employee",
            ],
            "forbidden_terms": [
                "payroll only",
                "recruitment only",
                "job board only",
                "food delivery",
                "grocery delivery",
            ],
            "queries": {
                "direct_competitors": [
                    "HR training management software Tunisia",
                    "skills tracking platform Tunisia",
                ],
                "adjacent_solutions": [
                    "training management system small companies",
                    "competency tracking SaaS",
                ],
                "market_sources": [
                    "HRTech Tunisia training digitalization",
                    "corporate training platforms North Africa",
                ],
                "pricing": [
                    "training management software pricing",
                    "HR training SaaS pricing",
                ],
            },
        },
        "healthtech": {
            "strong_terms": [
                "doctor appointment",
                "medical appointment",
                "clinic booking",
                "patient scheduling",
                "healthcare booking",
                "telemedicine",
                "medical office",
                "cabinet médical",
                "rendez-vous médecin",
                "prise de rendez-vous médical",
                "clinique",
                "patient",
                "médecin",
            ],
            "weak_terms": [
                "health",
                "medical",
                "doctor",
                "clinic",
                "booking",
                "appointment",
            ],
            "forbidden_terms": [
                "food delivery",
                "grocery delivery",
                "mobile wallet",
                "social network",
                "general super app",
                "stock trading",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia doctor appointment booking platform",
                    "Tunisia medical appointment booking app",
                    "prise rendez-vous médecin Tunisie plateforme",
                    "cabinet médical réservation patient Tunisie",
                ],
                "adjacent_solutions": [
                    "clinic appointment management software MENA",
                    "patient scheduling software medical office",
                ],
                "market_sources": [
                    "Tunisia digital health appointment booking",
                    "HealthTech Tunisia medical booking",
                ],
                "pricing": [
                    "clinic appointment booking software pricing",
                    "medical scheduling SaaS pricing",
                ],
            },
        },
        "agritech": {
            "strong_terms": [
                "agritech",
                "smart agriculture",
                "farm management",
                "crop monitoring",
                "agricultural traceability",
                "farm records",
                "agriculture software",
                "digital agriculture",
                "agriculture intelligente",
                "gestion agricole",
                "suivi agricole",
                "traçabilité agricole",
                "logiciel agricole",
            ],
            "weak_terms": [
                "agriculture",
                "farm",
                "plant",
                "camera",
                "monitoring",
            ],
            "forbidden_terms": [
                "stock trading",
                "pharmacy",
                "course platform",
                "medical appointment",
                "grocery delivery",
            ],
            "queries": {
                "direct_competitors": [
                    "AgriTech Tunisia farm management software",
                    "Tunisia agriculture software",
                    "logiciel agricole Tunisie",
                    "Tunisia smart agriculture platform",
                ],
                "adjacent_solutions": [
                    "farm management software Africa",
                    "agriculture traceability software",
                    "digital agriculture management platform",
                ],
                "market_sources": [
                    "Tunisia smart agriculture digital transformation",
                    "AgriTech Tunisia startups agriculture",
                    "digital agriculture Tunisia market",
                ],
                "pricing": [
                    "farm management software pricing",
                    "agritech SaaS pricing",
                ],
            },
        },
        "robotics": {
            "strong_terms": [
                "robot",
                "robotics",
                "autonomous robot",
                "inspection robot",
                "mobile robot",
                "computer vision robot",
                "robot autonome",
                "robot inspection",
                "robot mobile",
                "vision par ordinateur",
            ],
            "weak_terms": [
                "robot",
                "camera",
                "sensor",
                "automation",
            ],
            "forbidden_terms": [
                "stock trading",
                "doctor appointment",
                "course platform",
                "grocery delivery",
            ],
            "queries": {
                "direct_competitors": [
                    "inspection robot startup",
                    "autonomous inspection robot agriculture",
                    "robot inspection serre agricole Tunisie",
                ],
                "adjacent_solutions": [
                    "greenhouse inspection robot",
                    "crop monitoring robot",
                    "computer vision agriculture robot",
                ],
                "market_sources": [
                    "agricultural robotics market North Africa",
                    "smart farming robotics Tunisia",
                ],
                "pricing": [
                    "inspection robot prototype cost",
                    "agriculture robot cost",
                ],
            },
        },
        "fintech": {
            "strong_terms": [
                "payment processing",
                "invoice payment",
                "digital wallet",
                "merchant payment",
                "online payment tracking",
                "paiement en ligne",
                "suivi paiement",
                "portefeuille numérique",
            ],
            "weak_terms": [
                "payment",
                "finance",
                "money",
                "wallet",
                "bank",
            ],
            "forbidden_terms": [
                "stock trading",
                "crypto speculation",
                "casino",
                "gambling",
                "food delivery",
                "course platform",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia online payment tracking SaaS",
                    "Tunisia merchant payment platform",
                    "Tunisia payment gateway merchants",
                ],
                "adjacent_solutions": [
                    "payment tracking software small business",
                    "invoice payment SaaS",
                    "merchant payment software",
                ],
                "market_sources": [
                    "Tunisia fintech payment digitalization",
                    "online payments Tunisia SMEs",
                ],
                "pricing": [
                    "payment SaaS pricing",
                    "merchant payment gateway pricing Tunisia",
                ],
            },
        },
        "ecommerce": {
            "strong_terms": [
                "ecommerce",
                "e-commerce",
                "online store",
                "online marketplace",
                "marketplace",
                "order management",
                "product catalog",
                "online ordering",
                "customer reorder",
                "payment tracking",
                "cash on delivery",
                "commerce en ligne",
                "place de marché",
                "place de marche",
                "commande en ligne",
                "catalogue produits",
                "suivi commande",
                "paiement à la livraison",
                "paiement a la livraison",
                "paiement en ligne",
            ],
            "weak_terms": [
                "shop",
                "store",
                "products",
                "items",
                "buy",
                "sell",
                "commerce",
            ],
            "forbidden_terms": [
                "stock trading",
                "crypto",
                "casino",
                "gambling",
                "medical appointment",
                "doctor appointment",
                "greenhouse robot",
                "course platform",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia online grocery delivery app",
                    "Tunisia supermarket delivery platform",
                    "Tunisie livraison courses application",
                    "Tunisie courses en ligne livraison",
                    "Tunis grocery delivery marketplace",
                    "Sousse grocery delivery supermarket app",
                    "Sfax grocery delivery supermarket app",
                ],
                "adjacent_solutions": [
                    "Tunisia ecommerce marketplace local shops delivery",
                    "Tunisia retail delivery marketplace",
                    "Tunisie marketplace commerces de proximité livraison",
                    "Tunisie marketplace commerces de proximite livraison",
                    "Tunisie livraison produits supermarchés épiceries",
                    "Tunisie livraison produits supermarches epiceries",
                    "North Africa grocery delivery app",
                    "MENA grocery delivery marketplace",
                ],
                "market_sources": [
                    "Tunisia ecommerce market online grocery delivery",
                    "Tunisia retail digital transformation grocery delivery",
                    "Tunisie ecommerce livraison courses marché",
                    "Tunisie ecommerce livraison courses marche",
                    "Tunisie commerce en ligne livraison dernier kilometre",
                ],
                "pricing": [
                    "grocery delivery marketplace commission model",
                    "online grocery delivery SaaS pricing",
                    "retail marketplace commission pricing",
                ],
            },
        },
        "retailtech": {
            "strong_terms": [
                "retailtech",
                "retail technology",
                "local retailers",
                "small retailers",
                "supermarkets",
                "grocery stores",
                "inventory",
                "stock online",
                "delivery slots",
                "retail order management",
                "commerce de proximité",
                "commerce de proximite",
                "épiceries",
                "epiceries",
                "supérettes",
                "superettes",
                "gestion commandes",
                "gestion stock",
                "créneaux livraison",
                "creneaux livraison",
            ],
            "weak_terms": [
                "retail",
                "store",
                "shop",
                "seller",
                "merchant",
            ],
            "forbidden_terms": [
                "stock trading",
                "crypto",
                "pharmacy stock management",
                "patient scheduling",
                "lms",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia retail delivery app local shops",
                    "Tunisie application livraison commerces locaux",
                    "Tunisie épicerie en ligne livraison",
                    "Tunisie epicerie en ligne livraison",
                    "Tunisia supermarket online ordering platform",
                ],
                "adjacent_solutions": [
                    "retail order management software small shops",
                    "inventory ordering delivery software small retailers",
                    "commerce de proximité digitalisation Tunisie",
                    "commerce de proximite digitalisation Tunisie",
                ],
                "market_sources": [
                    "Tunisia retail digitalization ecommerce",
                    "Tunisie commerce détail digitalisation",
                    "Tunisie commerce detail digitalisation",
                    "Tunisia last mile delivery ecommerce retail",
                ],
                "pricing": [
                    "retail marketplace commission model",
                    "delivery marketplace merchant subscription pricing",
                ],
            },
        },
        "grocery": {
            "strong_terms": [
                "grocery delivery",
                "online grocery",
                "supermarket delivery",
                "fresh products delivery",
                "household items delivery",
                "grocery marketplace",
                "courses en ligne",
                "livraison courses",
                "livraison supermarché",
                "livraison supermarche",
                "produits frais",
                "épicerie en ligne",
                "epicerie en ligne",
            ],
            "weak_terms": [
                "food",
                "delivery",
                "products",
                "fresh",
            ],
            "forbidden_terms": [
                "restaurant delivery only",
                "ride hailing",
                "stock trading",
                "crypto",
                "lms",
                "medical booking",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia grocery delivery app",
                    "Tunisie livraison courses en ligne",
                    "Tunisia supermarket delivery online",
                    "Tunis online grocery delivery",
                    "Carrefour Tunisia online delivery groceries",
                    "Monoprix Tunisia online delivery",
                ],
                "adjacent_solutions": [
                    "online grocery delivery Africa benchmark",
                    "MENA online grocery delivery apps",
                    "Instacart grocery delivery benchmark",
                    "Carrefour online grocery delivery benchmark",
                ],
                "market_sources": [
                    "online grocery delivery market Tunisia",
                    "Tunisia ecommerce grocery delivery trend",
                    "North Africa online grocery market",
                ],
                "pricing": [
                    "online grocery marketplace commission fees",
                    "grocery delivery subscription pricing",
                ],
            },
        },
        "delivery": {
            "strong_terms": [
                "delivery",
                "last mile delivery",
                "delivery slots",
                "order delivery",
                "cash on delivery",
                "delivery tracking",
                "livraison",
                "dernier kilometre",
                "créneaux livraison",
                "creneaux livraison",
                "suivi livraison",
                "paiement à la livraison",
                "paiement a la livraison",
            ],
            "weak_terms": [
                "fast",
                "home",
                "nearby",
                "local",
            ],
            "forbidden_terms": [
                "ride sharing",
                "taxi app",
                "crypto",
                "stock trading",
                "doctor appointment",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia delivery app groceries",
                    "Tunisie application livraison courses",
                    "Tunisia last mile delivery ecommerce groceries",
                ],
                "adjacent_solutions": [
                    "last mile delivery marketplace North Africa",
                    "delivery management platform local shops",
                    "cash on delivery ecommerce Tunisia",
                ],
                "market_sources": [
                    "Tunisia last mile delivery market ecommerce",
                    "Tunisia cash on delivery ecommerce",
                ],
                "pricing": [
                    "last mile delivery marketplace commission model",
                    "delivery platform pricing merchants",
                ],
            },
        },
        "marketplace": {
            "strong_terms": [
                "marketplace",
                "two sided marketplace",
                "merchant onboarding",
                "shop onboarding",
                "order marketplace",
                "commission model",
                "place de marché",
                "place de marche",
                "mise en relation",
                "onboarding commerçants",
                "onboarding commercants",
                "modèle commission",
                "modele commission",
            ],
            "weak_terms": [
                "platform",
                "users",
                "buyers",
                "sellers",
            ],
            "forbidden_terms": [
                "crypto marketplace",
                "stock trading",
                "nft marketplace",
                "casino",
                "gambling",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia marketplace local shops delivery",
                    "Tunisie marketplace commerces locaux livraison",
                    "Tunisia ecommerce marketplace groceries",
                ],
                "adjacent_solutions": [
                    "local commerce marketplace North Africa",
                    "marketplace for small retailers delivery",
                    "merchant onboarding marketplace delivery",
                ],
                "market_sources": [
                    "Tunisia marketplace ecommerce local shops",
                    "Tunisie marketplace ecommerce commerces",
                ],
                "pricing": [
                    "marketplace commission model merchants",
                    "two sided marketplace pricing model",
                ],
            },
        },
        "beekeeping": {
            "strong_terms": [
                "beekeeping",
                "apiary management",
                "hive inspection",
                "hive records",
                "honey harvest",
                "honey traceability",
                "beekeeping software",
                "beekeeper records",
                "apiculture",
                "gestion ruches",
                "inspection ruches",
                "récolte miel",
                "recolte miel",
                "traçabilité miel",
                "tracabilite miel",
                "registre rucher",
            ],
            "weak_terms": [
                "honey",
                "bee",
                "bees",
                "farm",
                "agriculture",
            ],
            "forbidden_terms": [
                "greenhouse robot",
                "crop disease camera",
                "stock trading",
                "clinic booking",
                "course platform",
                "food delivery",
                "grocery delivery",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia beekeeping management software",
                    "Tunisie logiciel gestion ruches apiculture",
                    "Tunisia honey traceability software",
                ],
                "adjacent_solutions": [
                    "apiary management software",
                    "hive inspection records app",
                    "honey traceability software",
                    "beekeeping software cooperative management",
                ],
                "market_sources": [
                    "Tunisia beekeeping honey traceability",
                    "Tunisie apiculture traçabilité miel",
                    "Tunisie apiculture tracabilite miel",
                    "digital agriculture beekeeping software Africa",
                ],
                "pricing": [
                    "apiary management software pricing",
                    "beekeeping software subscription pricing",
                ],
            },
        },
        "traceability": {
            "strong_terms": [
                "traceability",
                "product traceability",
                "food traceability",
                "batch tracking",
                "quality records",
                "certification records",
                "traçabilité",
                "tracabilite",
                "suivi lots",
                "registre qualité",
                "registre qualite",
                "certification",
            ],
            "weak_terms": [
                "quality",
                "records",
                "tracking",
            ],
            "forbidden_terms": [
                "stock trading",
                "crypto",
                "patient scheduling",
                "lms",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia food traceability software agriculture",
                    "Tunisie logiciel traçabilité produits agricoles",
                    "Tunisie logiciel tracabilite produits agricoles",
                ],
                "adjacent_solutions": [
                    "food traceability software small producers",
                    "batch tracking software agriculture",
                    "agricultural product traceability software",
                ],
                "market_sources": [
                    "Tunisia food traceability agriculture",
                    "Tunisie traçabilité alimentaire agriculture",
                    "Tunisie tracabilite alimentaire agriculture",
                ],
                "pricing": [
                    "food traceability software pricing",
                    "batch tracking SaaS pricing",
                ],
            },
        },
    }

    def build(
        self,
        *,
        title: str = "",
        description: str = "",
        industry: str = "",
        target_region: str = "",
        output_language: str = "fr",
        project_context: Dict[str, Any] | None = None,
        idea_readiness: Dict[str, Any] | None = None,
        analysis_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)
        project_context = project_context or {}
        idea_readiness = idea_readiness or {}
        analysis_data = analysis_data or {}

        title = self._clean_text(
            title
            or project_context.get("project_name")
            or project_context.get("title")
            or ""
        )

        description = self._clean_text(
            description
            or project_context.get("description")
            or ""
        )

        industry = self._clean_text(
            industry
            or project_context.get("industry")
            or ""
        )

        target_region = self._clean_text(
            target_region
            or project_context.get("market_region")
            or project_context.get("target_region")
            or "Tunisie"
        )

        detected_from_readiness = idea_readiness.get("detected") or {}

        target_users = self._extract_target_users(
            description=description,
            project_context=project_context,
            detected=detected_from_readiness,
        )

        problem = self._first_available_text(
            detected_from_readiness.get("problem"),
            project_context.get("problem"),
            project_context.get("core_problem"),
            self._extract_sentence(description, self.PROBLEM_HINTS()),
        )

        solution = self._first_available_text(
            detected_from_readiness.get("solution"),
            project_context.get("solution"),
            project_context.get("solution_type"),
            self._extract_sentence(description, self.SOLUTION_HINTS()),
        )

        main_use_case = self._first_available_text(
            detected_from_readiness.get("main_use_case"),
            project_context.get("main_use_case"),
            project_context.get("use_case"),
            solution,
        )

        business_model = self._first_available_text(
            detected_from_readiness.get("business_model"),
            project_context.get("business_model"),
            self._extract_sentence(description, self.BUSINESS_HINTS()),
        )

        mvp_scope = self._first_available_text(
            detected_from_readiness.get("mvp_scope"),
            project_context.get("mvp_scope"),
            self._extract_sentence(description, self.MVP_HINTS()),
        )

        value_proposition = self._build_value_proposition(
            title=title,
            target_users=target_users,
            problem=problem,
            solution=solution,
            language=language,
        )

        sector_tags = self._sector_tags(industry)
        sector_profile = self._sector_profile(sector_tags)

        strong_keywords = self._strong_keywords(
            title=title,
            industry=industry,
            target_region=target_region,
            target_users=target_users,
            problem=problem,
            solution=solution,
            main_use_case=main_use_case,
            business_model=business_model,
            mvp_scope=mvp_scope,
            sector_profile=sector_profile,
            project_context=project_context,
        )

        weak_terms_to_ignore = self._weak_terms_to_ignore(
            sector_profile=sector_profile,
        )

        forbidden_offtopic_terms = self._forbidden_offtopic_terms(
            sector_profile=sector_profile,
            sector_tags=sector_tags,
        )

        must_match_terms = self._must_match_terms(
            title=title,
            target_users=target_users,
            problem=problem,
            solution=solution,
            strong_keywords=strong_keywords,
        )

        structured_project_context = {
            "project_name": title,
            "title": title,
            "description": description,
            "sector": industry,
            "industry": industry,
            "sector_tags": sector_tags,
            "target_region": target_region,
            "market_region": target_region,
            "target_users": target_users,
            "problem": problem,
            "core_problem": problem,
            "solution": solution,
            "solution_type": solution,
            "main_use_case": main_use_case,
            "business_model": business_model,
            "mvp_scope": mvp_scope,
            "value_proposition": value_proposition,
            "output_language": language,
            "context_locked": True,
        }

        source_acceptance_rules = self._source_acceptance_rules(
            language=language,
            target_region=target_region,
        )

        query_planner = self._query_planner(
            title=title,
            industry=industry,
            target_region=target_region,
            target_users=target_users,
            problem=problem,
            solution=solution,
            main_use_case=main_use_case,
            business_model=business_model,
            strong_keywords=strong_keywords,
            sector_profile=sector_profile,
            language=language,
        )

        context_confidence = self._context_confidence(
            title=title,
            industry=industry,
            target_region=target_region,
            target_users=target_users,
            problem=problem,
            solution=solution,
            business_model=business_model,
            mvp_scope=mvp_scope,
            idea_readiness=idea_readiness,
        )

        agent_context_packet = {
            "format": "project_intelligence_packet_v2_real_source_discovery",
            "structured_project_context": structured_project_context,
            "strong_keywords": strong_keywords,
            "must_match_terms": must_match_terms,
            "weak_terms_to_ignore": weak_terms_to_ignore,
            "forbidden_offtopic_terms": forbidden_offtopic_terms,
            "source_acceptance_rules": source_acceptance_rules,
            "query_planner": query_planner,
            "context_confidence": context_confidence,
            "agent_instructions": self._agent_instructions(language),
            "public_report_rules": self._public_report_rules(language),
            "output_language": language,
            "context_locked": True,
        }

        return {
            "format": "project_intelligence_layer_v2_real_source_discovery",
            "status": "completed",
            "output_language": language,
            "context_locked": True,
            "structured_project_context": structured_project_context,
            "strong_keywords": strong_keywords,
            "must_match_terms": must_match_terms,
            "weak_terms_to_ignore": weak_terms_to_ignore,
            "forbidden_offtopic_terms": forbidden_offtopic_terms,
            "source_acceptance_rules": source_acceptance_rules,
            "query_planner": query_planner,
            "context_confidence": context_confidence,
            "agent_context_packet": agent_context_packet,
        }

    def merge_into_project_context(
        self,
        *,
        base_project_context: Dict[str, Any] | None,
        intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        base_project_context = dict(base_project_context or {})
        structured = intelligence.get("structured_project_context") or {}

        merged = {
            **base_project_context,
            **structured,
            "project_intelligence": intelligence,
            "agent_context_packet": intelligence.get("agent_context_packet") or {},
            "strong_keywords": intelligence.get("strong_keywords") or [],
            "must_match_terms": intelligence.get("must_match_terms") or [],
            "weak_terms_to_ignore": intelligence.get("weak_terms_to_ignore") or [],
            "forbidden_offtopic_terms": intelligence.get("forbidden_offtopic_terms") or [],
            "source_acceptance_rules": intelligence.get("source_acceptance_rules") or {},
            "query_planner": intelligence.get("query_planner") or {},
            "context_confidence": intelligence.get("context_confidence") or {},
            "context_locked": True,
        }

        anchor_terms = self._unique(
            self._safe_list(base_project_context.get("anchor_terms"))
            + intelligence.get("strong_keywords", [])
            + intelligence.get("must_match_terms", [])
        )

        merged["anchor_terms"] = anchor_terms[:60]

        return merged

    @staticmethod
    def PROBLEM_HINTS() -> set[str]:
        return {
            "problem",
            "problème",
            "probleme",
            "struggle",
            "difficult",
            "hard",
            "manual",
            "scattered",
            "fragmented",
            "inefficient",
            "lack",
            "manque",
            "pain",
            "risk",
            "risque",
            "slow",
            "cost",
            "coût",
            "cout",
        }

    @staticmethod
    def SOLUTION_HINTS() -> set[str]:
        return {
            "solution",
            "platform",
            "plateforme",
            "app",
            "application",
            "saas",
            "robot",
            "dashboard",
            "system",
            "tool",
            "helps",
            "aide",
            "manage",
            "gérer",
            "gerer",
            "track",
            "suivre",
            "automate",
            "create",
            "créer",
            "creer",
            "detect",
            "détecter",
            "detecter",
        }

    @staticmethod
    def BUSINESS_HINTS() -> set[str]:
        return {
            "subscription",
            "abonnement",
            "pricing",
            "price",
            "prix",
            "freemium",
            "commission",
            "paid",
            "pay",
            "payer",
            "revenue",
            "revenu",
            "business model",
            "modèle économique",
            "modele economique",
            "monthly",
            "mensuel",
        }

    @staticmethod
    def MVP_HINTS() -> set[str]:
        return {
            "mvp",
            "first version",
            "première version",
            "premiere version",
            "prototype",
            "pilot",
            "pilote",
            "beta",
            "minimum",
            "core features",
            "features",
            "fonctionnalités",
            "fonctionnalites",
        }

    def _extract_target_users(
        self,
        *,
        description: str,
        project_context: Dict[str, Any],
        detected: Dict[str, Any],
    ) -> List[str]:
        candidates = (
            self._safe_list(detected.get("target_users"))
            + self._safe_list(project_context.get("target_users"))
            + self._safe_list(project_context.get("target_market"))
        )

        if candidates:
            return self._unique(candidates)[:10]

        patterns = [
            r"(?:first target users are|target users are|target users include)\s+(.+?)(?:\.|\n|$)",
            r"(?:the first target users are)\s+(.+?)(?:\.|\n|$)",
            r"(?:users are|customers are|clients are)\s+(.+?)(?:\.|\n|$)",
            r"(?:les utilisateurs cibles sont|les premiers utilisateurs sont|les clients cibles sont)\s+(.+?)(?:\.|\n|$)",
            r"(?:la cible est|les cibles sont)\s+(.+?)(?:\.|\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description, flags=re.IGNORECASE)

            if not match:
                continue

            return self._split_items(match.group(1))[:10]

        return []

    def _extract_sentence(self, text: str, hints: set[str]) -> str:
        clean_text = self._clean_text(text)

        if not clean_text:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+|\n+", clean_text)

        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            sentence = self._clean_text(sentence)
            lower = sentence.lower()

            if len(sentence) < 20:
                continue

            score = sum(1 for hint in hints if hint in lower)

            if score > best_score:
                best_score = score
                best_sentence = sentence

        return best_sentence if best_score > 0 else ""

    def _sector_tags(self, industry: str) -> List[str]:
        lower = self._clean_text(industry).lower()

        tags: List[str] = []

        mapping = {
            "edtech": ["edtech", "education", "training", "learning"],
            "education": ["edtech", "education", "training", "learning"],
            "training": ["edtech", "training"],
            "lms": ["edtech", "lms"],
            "hrtech": ["hrtech", "hr", "training", "skills"],
            "hr tech": ["hrtech", "hr", "training", "skills"],
            "healthtech": ["healthtech", "health", "medical"],
            "health tech": ["healthtech", "health", "medical"],
            "medtech": ["healthtech", "medical"],
            "agritech": ["agritech", "agriculture"],
            "agri tech": ["agritech", "agriculture"],
            "agriculture": ["agritech", "agriculture"],
            "beekeeping": ["agritech", "beekeeping", "traceability"],
            "honey": ["agritech", "beekeeping", "traceability"],
            "traceability": ["traceability"],
            "robot": ["robotics"],
            "robotics": ["robotics"],
            "fintech": ["fintech", "payment"],
            "payment": ["fintech", "payment"],
            "e-commerce": ["ecommerce", "marketplace", "retailtech"],
            "ecommerce": ["ecommerce", "marketplace", "retailtech"],
            "commerce": ["ecommerce", "marketplace"],
            "marketplace": ["marketplace", "ecommerce"],
            "retailtech": ["retailtech", "ecommerce"],
            "retail tech": ["retailtech", "ecommerce"],
            "retail": ["retailtech", "ecommerce"],
            "grocery": ["grocery", "delivery", "ecommerce", "retailtech"],
            "groceries": ["grocery", "delivery", "ecommerce", "retailtech"],
            "supermarket": ["grocery", "retailtech", "ecommerce"],
            "delivery": ["delivery", "marketplace"],
            "livraison": ["delivery", "marketplace"],
        }

        for key, values in mapping.items():
            if key in lower:
                tags.extend(values)

        if not tags and lower:
            tags.extend(self._split_items(lower))

        return self._unique(tags)[:16]

    def _sector_profile(self, sector_tags: List[str]) -> Dict[str, Any]:
        profile = {
            "strong_terms": [],
            "weak_terms": [],
            "forbidden_terms": [],
            "queries": {
                "direct_competitors": [],
                "adjacent_solutions": [],
                "market_sources": [],
                "pricing": [],
            },
        }

        for tag in sector_tags:
            tag_lower = tag.lower()

            if tag_lower not in self.SECTOR_PROFILES:
                continue

            sector_profile = self.SECTOR_PROFILES[tag_lower]

            profile["strong_terms"].extend(sector_profile.get("strong_terms", []))
            profile["weak_terms"].extend(sector_profile.get("weak_terms", []))
            profile["forbidden_terms"].extend(sector_profile.get("forbidden_terms", []))

            for intent, queries in (sector_profile.get("queries") or {}).items():
                profile["queries"].setdefault(intent, [])
                profile["queries"][intent].extend(queries)

        profile["strong_terms"] = self._unique(profile["strong_terms"])
        profile["weak_terms"] = self._unique(profile["weak_terms"])
        profile["forbidden_terms"] = self._unique(profile["forbidden_terms"])

        for intent, queries in profile["queries"].items():
            profile["queries"][intent] = self._unique(queries)

        return profile

    def _strong_keywords(
        self,
        *,
        title: str,
        industry: str,
        target_region: str,
        target_users: List[str],
        problem: str,
        solution: str,
        main_use_case: str,
        business_model: str,
        mvp_scope: str,
        sector_profile: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:
        candidates: List[str] = []

        candidates.extend(self._project_name_terms(title))
        candidates.extend(self._split_items(industry))
        candidates.extend(self._safe_list(target_region))
        candidates.extend(target_users)
        candidates.extend(self._important_phrases(problem))
        candidates.extend(self._important_phrases(solution))
        candidates.extend(self._important_phrases(main_use_case))
        candidates.extend(self._important_phrases(business_model))
        candidates.extend(self._important_phrases(mvp_scope))
        candidates.extend(self._safe_list(project_context.get("anchor_terms")))
        candidates.extend(self._safe_list(project_context.get("strong_keywords")))
        candidates.extend(sector_profile.get("strong_terms", []))

        cleaned: List[str] = []

        for candidate in candidates:
            item = self._clean_text(candidate)

            if not item:
                continue

            if len(item) < 3:
                continue

            cleaned.append(item)

        return self._unique(cleaned)[:100]

    def _must_match_terms(
        self,
        *,
        title: str,
        target_users: List[str],
        problem: str,
        solution: str,
        strong_keywords: List[str],
    ) -> List[str]:
        candidates: List[str] = []

        title_terms = self._project_name_terms(title)

        if title_terms:
            candidates.extend(title_terms[:3])

        candidates.extend(target_users[:4])
        candidates.extend(self._important_phrases(problem)[:4])
        candidates.extend(self._important_phrases(solution)[:4])
        candidates.extend(strong_keywords[:12])

        result = []

        for item in candidates:
            clean = self._clean_text(item)

            if not clean:
                continue

            if clean.lower() in self.DEFAULT_WEAK_TERMS:
                continue

            result.append(clean)

        return self._unique(result)[:24]

    def _weak_terms_to_ignore(self, *, sector_profile: Dict[str, Any]) -> List[str]:
        weak_terms = set(self.DEFAULT_WEAK_TERMS)

        for term in sector_profile.get("weak_terms", []):
            weak_terms.add(str(term).lower())

        return sorted(weak_terms)

    def _forbidden_offtopic_terms(
        self,
        *,
        sector_profile: Dict[str, Any],
        sector_tags: List[str],
    ) -> List[str]:
        tag_set = {str(tag).lower() for tag in sector_tags}

        forbidden = set(self.OLD_DEMO_FORBIDDEN_TERMS)
        allowed_when_relevant = set()

        if tag_set.intersection({"ecommerce", "retailtech", "grocery", "delivery", "marketplace"}):
            allowed_when_relevant.update(
                {
                    "ecommerce marketplace",
                    "food delivery",
                    "payment",
                    "online payment",
                    "mobile payment",
                }
            )

        if tag_set.intersection({"fintech", "payment"}):
            allowed_when_relevant.update(
                {
                    "fintech wallet",
                    "mobile wallet",
                    "payment super app",
                    "payment",
                    "online payment",
                }
            )

        if tag_set.intersection({"healthtech", "medical"}):
            allowed_when_relevant.update(
                {
                    "doctor appointment",
                    "clinic booking",
                    "patient scheduling",
                    "medical appointment",
                }
            )

        if tag_set.intersection({"agritech", "agriculture", "robotics"}):
            allowed_when_relevant.update(
                {
                    "robot agricole",
                    "agrobot",
                    "greenhouse robot",
                    "greenhouse inspection",
                    "crop monitoring",
                    "farm robot",
                }
            )

        if tag_set.intersection({"edtech", "hrtech", "training", "lms"}):
            allowed_when_relevant.update(
                {
                    "course platform",
                    "training center management",
                    "lms",
                }
            )

        if tag_set.intersection({"beekeeping", "traceability"}):
            allowed_when_relevant.update(
                {
                    "honey",
                    "beekeeping",
                    "traceability",
                    "food traceability",
                }
            )

        forbidden -= allowed_when_relevant

        for term in sector_profile.get("forbidden_terms", []):
            clean = str(term).lower()

            if clean not in allowed_when_relevant:
                forbidden.add(clean)

        if "healthtech" not in tag_set and "medical" not in tag_set:
            forbidden.update({"doctor appointment", "clinic booking", "patient scheduling"})

        if not tag_set.intersection({"edtech", "hrtech", "training", "lms"}):
            forbidden.update({"course platform", "training center management", "lms"})

        if not tag_set.intersection({"agritech", "agriculture", "robotics"}):
            forbidden.update({"greenhouse inspection", "crop monitoring", "farm robot"})

        if not tag_set.intersection(
            {"fintech", "payment", "ecommerce", "retailtech", "grocery", "delivery", "marketplace"}
        ):
            forbidden.update({"mobile wallet", "payment super app", "stock trading"})

        forbidden -= allowed_when_relevant

        return sorted(forbidden)

    def _important_phrases(self, text: str) -> List[str]:
        clean = self._clean_text(text)

        if not clean:
            return []

        phrases: List[str] = []

        chunks = re.split(r",|;|\band\b|\bet\b|\bor\b|\bou\b|\.", clean, flags=re.IGNORECASE)

        for chunk in chunks:
            chunk = self._clean_text(chunk)

            if len(chunk) < 4:
                continue

            words = [word for word in re.split(r"\s+", chunk) if len(word) >= 3]

            if len(words) >= 2:
                phrases.append(" ".join(words[:8]))

            for size in (2, 3, 4):
                for i in range(0, max(0, len(words) - size + 1)):
                    phrases.append(" ".join(words[i : i + size]))

        return self._unique(phrases)[:35]

    def _project_name_terms(self, title: str) -> List[str]:
        title = self._clean_text(title)

        if not title:
            return []

        terms = [title]

        camel_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", title)
        if camel_split != title:
            terms.append(camel_split)

        parts = [
            part.strip()
            for part in re.split(r"\s+|-|_", camel_split)
            if len(part.strip()) >= 3
        ]

        terms.extend(parts)

        if len(parts) >= 2:
            terms.append(" ".join(parts[:2]))

        return self._unique(terms)

    def _query_planner(
        self,
        *,
        title: str,
        industry: str,
        target_region: str,
        target_users: List[str],
        problem: str,
        solution: str,
        main_use_case: str,
        business_model: str,
        strong_keywords: List[str],
        sector_profile: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        target_short = self._short_query_phrase(" ".join(target_users[:2]), max_words=8)
        problem_short = self._short_query_phrase(problem, max_words=10)
        solution_short = self._short_query_phrase(solution, max_words=10)
        use_case_short = self._short_query_phrase(main_use_case or solution, max_words=10)
        primary_terms = self._short_query_phrase(" ".join(str(item) for item in strong_keywords[:8]), max_words=12)

        base_context = self._clean_text(
            " ".join(
                [
                    title,
                    industry,
                    target_region,
                    target_short,
                    use_case_short,
                ]
            )
        )

        direct_competitor_queries = [
            f"{title} competitors {target_region}",
            f"{industry} competitors {target_region} {target_short}",
            f"{use_case_short} {target_region} competitors",
            f"{solution_short} {target_region} alternatives",
            f"{primary_terms} {target_region} competitors",
        ]

        adjacent_solution_queries = [
            f"{use_case_short} software",
            f"{problem_short} solution {industry}",
            f"{target_short} management software {industry}",
            f"{solution_short} benchmark",
            f"{primary_terms} alternatives",
        ]

        market_source_queries = [
            f"{industry} market {target_region}",
            f"{industry} startups {target_region}",
            f"{target_region} digital transformation {industry}",
            f"{target_short} market needs {target_region}",
            f"{primary_terms} market {target_region}",
        ]

        pricing_queries = [
            f"{use_case_short} pricing",
            f"{industry} SaaS pricing",
            f"{solution_short} subscription pricing",
            f"{primary_terms} pricing",
        ]

        validation_queries = [
            f"{problem_short} {target_region}",
            f"{target_short} pain points {target_region}",
            f"{industry} adoption barriers {target_region}",
        ]

        sector_queries = sector_profile.get("queries") or {}

        direct_competitor_queries.extend(sector_queries.get("direct_competitors", []))
        adjacent_solution_queries.extend(sector_queries.get("adjacent_solutions", []))
        market_source_queries.extend(sector_queries.get("market_sources", []))
        pricing_queries.extend(sector_queries.get("pricing", []))

        if language == "fr":
            direct_competitor_queries.extend(
                [
                    f"{industry} concurrents {target_region}",
                    f"{use_case_short} concurrents {target_region}",
                    f"{solution_short} alternatives {target_region}",
                    f"{target_region} application similaire {industry}",
                ]
            )

            adjacent_solution_queries.extend(
                [
                    f"{use_case_short} logiciel",
                    f"{problem_short} solution {target_region}",
                    f"{target_short} logiciel gestion {industry}",
                    f"{solution_short} benchmark international",
                ]
            )

            market_source_queries.extend(
                [
                    f"{industry} marché {target_region}",
                    f"{industry} startups {target_region}",
                    f"{target_region} transformation digitale {industry}",
                    f"{target_short} besoins marché {target_region}",
                ]
            )

            pricing_queries.extend(
                [
                    f"{use_case_short} tarifs",
                    f"{industry} prix SaaS",
                    f"{solution_short} abonnement prix",
                ]
            )

        return {
            "format": "query_planner_v2_real_source_discovery",
            "base_context": base_context,
            "primary_search_terms": strong_keywords[:24],
            "queries_by_intent": {
                "direct_competitors": self._clean_queries(direct_competitor_queries),
                "adjacent_solutions": self._clean_queries(adjacent_solution_queries),
                "market_sources": self._clean_queries(market_source_queries),
                "pricing": self._clean_queries(pricing_queries),
                "field_validation": self._clean_queries(validation_queries),
            },
            "search_strategy": self._search_strategy(language),
            "output_language": language,
        }

    def _short_query_phrase(self, value: str, max_words: int = 10) -> str:
        clean = self._clean_text(value)

        if not clean:
            return ""

        words = [
            word
            for word in re.split(r"\s+", clean)
            if word.strip()
        ]

        return " ".join(words[:max_words])

    def _clean_queries(self, queries: List[str]) -> List[str]:
        cleaned = []

        for query in queries:
            clean = self._clean_text(query)

            if not clean:
                continue

            clean = re.sub(r"\s+", " ", clean).strip()

            if len(clean) < 8:
                continue

            if len(clean.split()) > 18:
                clean = " ".join(clean.split()[:18])

            cleaned.append(clean)

        return self._unique(cleaned)[:16]

    def _search_strategy(self, language: str) -> Dict[str, Any]:
        if language == "en":
            return {
                "direct_competitors": "Search for real solutions solving the same use case for the same or very similar target users. Do not invent names.",
                "adjacent_solutions": "Accept related solutions only if the relationship to the project can be clearly explained.",
                "market_sources": "Prefer local or regional market evidence. Generic global sources are secondary.",
                "benchmarks": "International benchmarks may be used only as benchmarks, not as local competitors.",
                "pricing": "Use pricing only as benchmark. Do not infer profitability without validation.",
            }

        return {
            "direct_competitors": "Chercher des solutions réelles qui résolvent le même cas d’usage pour la même cible ou une cible très proche. Ne pas inventer de noms.",
            "adjacent_solutions": "Accepter les solutions proches seulement si le lien avec le projet est clairement explicable.",
            "market_sources": "Prioriser les preuves locales ou régionales. Les sources globales génériques sont secondaires.",
            "benchmarks": "Les benchmarks internationaux peuvent être utilisés comme benchmarks, pas comme concurrents locaux.",
            "pricing": "Utiliser les prix comme benchmark uniquement. Ne pas conclure à la rentabilité sans validation.",
        }

    def _source_acceptance_rules(
        self,
        *,
        language: str,
        target_region: str,
    ) -> Dict[str, Any]:
        if language == "en":
            no_source_message = "No verified relevant source found."
            public_rule = "Weak or generic sources must be rejected instead of displayed."
        else:
            no_source_message = "Aucune source pertinente vérifiée trouvée."
            public_rule = "Une source faible ou générique doit être rejetée au lieu d’être affichée."

        return {
            "format": "source_acceptance_rules_v2_real_source_discovery",
            "public_display_threshold": 0.70,
            "internal_use_threshold": 0.50,
            "rejection_threshold": 0.50,
            "minimum_required_signals": {
                "direct_competitor": [
                    "same_or_close_target_user",
                    "same_or_close_use_case",
                    "same_or_close_solution_category",
                    "local_or_clear_target_region",
                ],
                "adjacent_solution": [
                    "clear_contextual_link",
                    "relevant_target_or_use_case",
                ],
                "market_source": [
                    "sector_relevance",
                    "regional_or_target_relevance",
                ],
                "benchmark": [
                    "same_solution_category_or_operating_model",
                ],
            },
            "public_rule": public_rule,
            "no_source_message": no_source_message,
            "target_region": target_region,
            "never_display": [
                "source with only weak generic term matches",
                "source unrelated to target user",
                "source unrelated to use case",
                "source from forbidden off-topic domain",
                "source that cannot be explained as relevant",
            ],
        }

    def _context_confidence(
        self,
        *,
        title: str,
        industry: str,
        target_region: str,
        target_users: List[str],
        problem: str,
        solution: str,
        business_model: str,
        mvp_scope: str,
        idea_readiness: Dict[str, Any],
    ) -> Dict[str, Any]:
        missing_fields: List[str] = []
        ambiguous_fields: List[str] = []

        if not title:
            missing_fields.append("project_name")

        if not industry:
            missing_fields.append("sector")

        if not target_region:
            ambiguous_fields.append("target_region")

        if not target_users:
            missing_fields.append("target_users")

        if not problem:
            missing_fields.append("problem")

        if not solution:
            missing_fields.append("solution")

        if not business_model:
            ambiguous_fields.append("business_model")

        if not mvp_scope:
            ambiguous_fields.append("mvp_scope")

        readiness_score = float(idea_readiness.get("score") or 0)

        base_score = 1.0
        base_score -= 0.10 * len(missing_fields)
        base_score -= 0.04 * len(ambiguous_fields)

        if readiness_score > 0:
            base_score = (base_score + readiness_score) / 2

        score = round(max(0.0, min(1.0, base_score)), 2)

        return {
            "format": "context_confidence_v2",
            "score": score,
            "missing_fields": self._unique(missing_fields),
            "ambiguous_fields": self._unique(ambiguous_fields),
            "ready_for_agents": score >= 0.75,
            "ready_for_strict_source_search": score >= 0.80,
            "readiness_score": readiness_score,
        }

    def _agent_instructions(self, language: str) -> Dict[str, str]:
        if language == "en":
            return {
                "global": "Use only the structured project context. Do not introduce unrelated sectors or demo examples.",
                "forgecrawler": "Search using strong keywords and query planner. Reject weak, generic or parachuted sources. Never invent competitors.",
                "personas": "Build personas from target users, problem and use case. Avoid generic empty profiles.",
                "debate": "Review the project like a company validation committee. Each role must add distinct analysis.",
                "fact_checker": "Separate sourced claims, estimated claims and field-validation-required claims.",
            }

        return {
            "global": "Utiliser uniquement le contexte structuré du projet. Ne pas introduire de secteurs ou exemples démo hors sujet.",
            "forgecrawler": "Chercher avec les mots-clés forts et le query planner. Rejeter les sources faibles, génériques ou parachutées. Ne jamais inventer de concurrents.",
            "personas": "Construire les personas à partir des cibles, du problème et du cas d’usage. Éviter les profils génériques vides.",
            "debate": "Évaluer le projet comme un comité de validation d’entreprise. Chaque rôle doit ajouter une analyse distincte.",
            "fact_checker": "Séparer les affirmations sourcées, estimées et celles nécessitant une validation terrain.",
        }

    def _public_report_rules(self, language: str) -> Dict[str, Any]:
        if language == "en":
            return {
                "hide_rejected_sources": True,
                "show_source_relevance_score": False,
                "show_no_source_message": True,
                "avoid_generic_language": True,
                "mandatory_limitations": [
                    "Assumptions must be listed.",
                    "Weak sources must not be shown as proof.",
                    "Field validation must be recommended when evidence is limited.",
                ],
            }

        return {
            "hide_rejected_sources": True,
            "show_source_relevance_score": False,
            "show_no_source_message": True,
            "avoid_generic_language": True,
            "mandatory_limitations": [
                "Les hypothèses doivent être listées.",
                "Les sources faibles ne doivent pas être affichées comme preuves.",
                "Une validation terrain doit être recommandée lorsque les preuves sont limitées.",
            ],
        }

    def _build_value_proposition(
        self,
        *,
        title: str,
        target_users: List[str],
        problem: str,
        solution: str,
        language: str,
    ) -> str:
        target = ", ".join(target_users[:3]) if target_users else (
            "target users" if language == "en" else "utilisateurs cibles"
        )

        if language == "en":
            return (
                f"{title or 'The project'} helps {target} solve a specific operational problem "
                f"by using: {solution or 'the proposed solution'}."
            )

        return (
            f"{title or 'Le projet'} aide {target} à résoudre un problème opérationnel précis "
            f"grâce à : {solution or 'la solution proposée'}."
        )

    def _first_available_text(self, *values: Any) -> str:
        for value in values:
            clean = self._clean_text(value)

            if clean:
                return clean

        return ""

    def _safe_list(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            result = []

            for item in value:
                clean = self._clean_text(item)

                if clean:
                    result.append(clean)

            return result

        if isinstance(value, str):
            clean = self._clean_text(value)

            if not clean:
                return []

            if "," in clean or ";" in clean or "/" in clean:
                return self._split_items(clean)

            return [clean]

        clean = self._clean_text(value)

        return [clean] if clean else []

    def _split_items(self, value: str) -> List[str]:
        clean = self._clean_text(value)

        if not clean:
            return []

        parts = re.split(r",|;|\band\b|\bet\b|\+|/", clean, flags=re.IGNORECASE)

        result = []

        for part in parts:
            item = self._clean_text(part)

            if len(item) >= 3:
                result.append(item)

        return self._unique(result)

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""

        text = str(value)
        text = text.replace("â€™", "'")
        text = text.replace("Ã©", "é")
        text = text.replace("Ã¨", "è")
        text = text.replace("Ãª", "ê")
        text = text.replace("Ã ", "à")
        text = text.replace("Ã¢", "â")
        text = text.replace("Ã®", "î")
        text = text.replace("Ã´", "ô")
        text = text.replace("Ã¹", "ù")
        text = text.replace("Ã»", "û")
        text = text.replace("Ã§", "ç")
        text = text.replace("Â", "")
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            clean = self._clean_text(value)

            if not clean:
                continue

            key = clean.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result


project_intelligence_layer = ProjectIntelligenceLayer()