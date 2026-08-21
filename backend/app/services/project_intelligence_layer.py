# ============================================================
# backend/app/services/project_intelligence_layer.py
# ============================================================
#
# ProjectIntelligenceLayer V3 — Structured Context + Generic Evidence Query Planner
#
# Objectifs :
# - transformer l'idée utilisateur en contexte structuré exploitable ;
# - extraire strong_keywords / weak_terms_to_ignore ;
# - générer des requêtes de recherche par intention ;
# - mieux couvrir plusieurs secteurs réels ;
# - ne pas hardcoder de résultats pour un projet précis ;
# - ne pas inventer de concurrents ;
# - aider ForgeCrawler à trouver des sources réelles si elles existent ;
# - garder le fallback honnête si aucune source fiable n'est trouvée ;
# - ne jamais décider si les agents peuvent être lancés.
# ============================================================

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language
from app.services.project_archetype_resolver import project_archetype_resolver
from app.services.scope_polarity import is_scope_exclusion_statement

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

    # Generic lexical guards used when the idea does not match a predefined
    # sector profile. They deliberately remove sentence glue, business-model
    # wording and vague product words from source-discovery concepts.
    CONCEPT_STOP_WORDS = {
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
        "business", "monthly", "low", "high", "possible", "possible",
        "aide", "aider", "avec", "avant", "besoin", "besoins", "car",
        "ce", "ces", "cette", "comme", "dans", "de", "des", "du", "elle",
        "elles", "en", "est", "et", "être", "etre", "leur", "leurs", "les",
        "mais", "notre", "nous", "ou", "par", "pas", "peut", "peuvent",
        "plus", "pour", "qui", "sans", "sont", "sur", "très", "tres", "un",
        "une", "utilise", "utiliser", "utilisent", "vos", "votre",
        "premier", "première", "premiere", "petit", "petite", "simples",
        "problème", "probleme", "problèmes", "problemes", "modèle", "modele",
        "mensuel", "faible", "élevé", "eleve",
    }

    GENERIC_CONCEPT_TERMS = {
        "app", "application", "platform", "plateforme", "digital", "mobile",
        "service", "solution", "tool", "outil", "business", "startup",
        "online", "website", "dashboard", "management", "manage", "create",
        "help", "system", "système", "systeme", "user", "users", "client",
        "clients", "customer", "customers", "data", "software", "logiciel",
        "saas", "product", "produit", "market", "marché", "marche",
        "industry", "industrie", "company", "companies", "entreprise",
        "subscription", "abonnement", "pricing", "price", "prix",
    }

    QUERY_AUDIENCE_TERMS = {
        "businesses", "business", "owners", "owner", "teams", "team",
        "users", "user", "customers", "customer", "clients", "client",
        "companies", "company", "organizations", "organisation",
        "organisations", "people", "professionals", "professional",
    }

    QUERY_INTENT_TERMS = {
        "competitor", "competitors", "concurrent", "concurrents", "alternative",
        "alternatives", "software", "logiciel", "platform", "plateforme",
        "market", "marché", "marche", "report", "rapport", "study", "étude",
        "etude", "statistics", "statistiques", "pricing", "price", "tarif",
        "tarifs", "benchmark", "survey", "adoption", "demand", "demande",
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
        "workforce": {
            "strong_terms": [
                "workforce scheduling",
                "employee scheduling",
                "shift planning",
                "shift scheduling",
                "attendance tracking",
                "leave requests",
                "schedule changes",
                "rotating shifts",
                "payroll export",
                "employee notifications",
                "planning des equipes",
                "planning des équipes",
                "gestion des horaires",
                "suivi de presence",
                "suivi de présence",
                "demandes de conge",
                "demandes de congé",
            ],
            "weak_terms": [
                "human resources",
                "hr",
                "employee",
                "employees",
                "workforce",
                "management",
            ],
            "forbidden_terms": [
                "recruitment only",
                "job board only",
                "training only",
                "food delivery",
                "grocery delivery",
            ],
            "queries": {
                "direct_competitors": [
                    "Tunisia workforce scheduling software",
                    "Tunisia employee shift planning attendance software",
                    "Tunisie logiciel planning horaires presence conges",
                    "Tunisia HR software shifts attendance leave payroll export",
                ],
                "adjacent_solutions": [
                    "North Africa employee scheduling software SMEs",
                    "workforce management attendance leave software MENA",
                    "shift planning software restaurants factories retail",
                ],
                "market_sources": [
                    "Tunisia SME workforce management digitalization",
                    "Tunisia employee scheduling attendance digital adoption",
                    "Tunisie PME gestion horaires presence digitalisation",
                ],
                "pricing": [
                    "employee scheduling software pricing small business",
                    "workforce management SaaS pricing per employee",
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
        "mobility": {
            "strong_terms": [
                "taxi booking", "ride hailing", "e hailing",
                "taxi dispatch", "urban mobility", "ride request",
                "application reservation taxi", "commande taxi",
                "mise en relation taxi chauffeur", "prise en charge passager",
            ],
            "weak_terms": ["transport", "destination", "region", "région"],
            "forbidden_terms": [
                "transport management system", "freight management",
                "warehouse management", "maritime logistics", "fleet logistics",
            ],
            "queries": {
                "direct_competitors": [
                    "taxi booking app Tunisia",
                    "ride hailing Tunisia",
                    "application réservation taxi Tunisie",
                    "commander taxi application Tunisie",
                ],
                "adjacent_solutions": [
                    "taxi dispatch software North Africa",
                    "urban mobility booking platform",
                    "e hailing platform Africa",
                ],
                "market_sources": [
                    "Tunisia taxi regulation digital platform",
                    "Tunisie mobilité urbaine taxi numérique",
                ],
                "pricing": [
                    "ride hailing commission model",
                    "taxi booking platform take rate",
                ],
            },
        },
        "recruitment": {
            "strong_terms": [
                "internship platform", "internship job board",
                "student recruitment", "internship applications",
                "plateforme stages", "offres de stage étudiants",
                "candidature stage", "recrutement étudiants",
            ],
            "weak_terms": ["student", "students", "étudiant", "étudiants", "job"],
            "forbidden_terms": [
                "workforce scheduling", "payroll software", "employee attendance",
                "course management", "learning management system",
            ],
            "queries": {
                "direct_competitors": [
                    "internship platform Tunisia",
                    "student internship job board Tunisia",
                    "plateforme stages étudiants Tunisie",
                ],
                "adjacent_solutions": [
                    "graduate recruitment platform North Africa",
                    "university career services software",
                ],
                "market_sources": [
                    "Tunisia student internships employability",
                    "Tunisie stages étudiants entreprises",
                ],
                "pricing": [
                    "job board employer listing pricing",
                    "internship platform employer subscription",
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
        """Build one canonical, source-discovery-ready project packet.

        The method is deliberately deterministic. It does not invent a sector,
        competitor or market fact. Predefined sector profiles enrich known
        categories, while the generic concept extractor keeps the same pipeline
        usable for ideas outside those profiles.
        """
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
            description or project_context.get("description") or ""
        )
        industry = self._clean_text(
            industry or project_context.get("industry") or ""
        )
        target_region = self._clean_text(
            target_region
            or project_context.get("market_region")
            or project_context.get("target_region")
            or ""
        )

        detected = idea_readiness.get("detected") or {}
        explicit_economic_buyer = self._extract_economic_buyer_from_description(description)
        target_users = self._extract_target_users(
            description=description,
            project_context=project_context,
            detected=detected,
        )

        explicit_problem = self._extract_labeled_section(
            description,
            labels=("the problem is", "problem:", "main problem:", "le problème est", "le probleme est", "problème :", "probleme :"),
            stop_labels=("the solution is", "solution:", "the first target users", "target users", "the mvp", "mvp", "the business model", "business model", "la solution est", "solution :", "les utilisateurs cibles", "le mvp", "modèle économique", "modele economique"),
        )
        explicit_solution = self._extract_labeled_section(
            description,
            labels=("the solution is", "solution:", "proposed solution:", "la solution est", "solution :", "solution proposée :", "solution proposee :"),
            stop_labels=("the first target users", "target users", "the mvp", "mvp", "the business model", "business model", "les utilisateurs cibles", "les premiers utilisateurs", "le mvp", "modèle économique", "modele economique"),
        )
        explicit_mvp = self._extract_labeled_section(
            description,
            labels=(
                "the first version would focus only on",
                "the first version would focus on",
                "the first version focuses on",
                "the mvp should focus on",
                "mvp should focus on",
                "the mvp will be limited to",
                "the mvp is limited to",
                "mvp limited to",
                "the mvp is",
                "mvp:",
                "la premiere version se concentrerait uniquement sur",
                "la première version se concentrerait uniquement sur",
                "la premiere version se concentre sur",
                "la première version se concentre sur",
                "le mvp doit se concentrer sur",
                "le mvp sera limité à",
                "le mvp sera limite a",
                "le mvp est limité à",
                "le mvp est limite a",
                "mvp limité à",
                "mvp limite a",
                "le mvp est",
                "mvp :",
            ),
            stop_labels=(
                "it would not initially include",
                "it will not initially include",
                "the main operational user",
                "main operational user",
                "the primary operational user",
                "primary operational user",
                "the economic buyer",
                "economic buyer",
                "the business model",
                "business model",
                "the main constraints",
                "main constraints",
                "the pilot will be considered successful if",
                "the pilot is successful if",
                "success will be measured by",
                "elle n'inclurait pas initialement",
                "elle n’inclurait pas initialement",
                "l'utilisateur opérationnel",
                "l’utilisateur opérationnel",
                "l'acheteur économique",
                "l’acheteur économique",
                "le modèle économique",
                "le modele economique",
                "modèle économique",
                "modele economique",
                "les contraintes principales",
                "les contraintes",
                "le pilote sera considéré comme réussi si",
                "le pilote sera considere comme reussi si",
                "le pilote est réussi si",
                "la réussite sera mesurée par",
            ),
        )
        explicit_business_model = self._extract_labeled_section(
            description,
            labels=("the business model can be", "the business model is", "business model:", "le modèle économique peut être", "le modele economique peut etre", "le modèle économique est", "modele economique :"),
            stop_labels=(),
        )
        explicit_constraints = self._extract_labeled_section(
            description,
            labels=(
                "the main constraints are",
                "main constraints:",
                "constraints:",
                "les contraintes principales sont",
                "les contraintes sont",
                "contraintes :",
            ),
            stop_labels=(
                "the pilot will be considered successful if",
                "the pilot is successful if",
                "success will be measured by",
                "le pilote sera considéré comme réussi si",
                "le pilote sera considere comme reussi si",
                "le pilote est réussi si",
                "la réussite sera mesurée par",
            ),
        )
        explicit_success = self._extract_labeled_section(
            description,
            labels=(
                "the pilot will be considered successful if",
                "the pilot is successful if",
                "success will be measured by",
                "success criteria:",
                "le pilote sera considéré comme réussi si",
                "le pilote sera considere comme reussi si",
                "le pilote est réussi si",
                "la réussite sera mesurée par",
                "critères de réussite :",
                "criteres de reussite :",
            ),
            stop_labels=(),
        )

        problem = self._first_available_text(
            explicit_problem,
            project_context.get("problem"),
            project_context.get("core_problem"),
            detected.get("problem"),
            self._extract_sentence(description, self.PROBLEM_HINTS()),
        )
        solution = self._first_available_text(
            explicit_solution,
            project_context.get("solution"),
            project_context.get("solution_type"),
            detected.get("solution"),
            self._extract_sentence(description, self.SOLUTION_HINTS()),
        )
        main_use_case = (
            self._first_available_non_scope_exclusion(
                detected.get("main_use_case"),
                project_context.get("main_use_case"),
                project_context.get("use_case"),
                solution,
            )
        )
        business_model = self._first_available_text(
            explicit_business_model,
            project_context.get("business_model"),
            detected.get("business_model"),
            self._extract_sentence(description, self.BUSINESS_HINTS()),
        )
        mvp_scope = (
            self._first_available_non_scope_exclusion(
                explicit_mvp,
                project_context.get("mvp_scope"),
                detected.get("mvp_scope"),
                self._extract_sentence(
                    description,
                    self.MVP_HINTS(),
                ),
            )
        )

        explicit_workflows = self._extract_explicit_workflows(
            description=description,
            solution=solution,
            mvp_scope=mvp_scope,
            language=language,
        )
        explicit_success_metrics = self._split_evidence_items(explicit_success)
        explicit_constraint_items = self._split_evidence_items(explicit_constraints)

        # Resolve the project operating model before building generic business
        # outputs. This prevents a marketplace, hardware product or consumer
        # transaction from being forced into the B2B workflow template.
        archetype_context = project_archetype_resolver.resolve(
            title=title,
            description=description,
            industry=industry,
            target_region=target_region,
            output_language=language,
            target_users=target_users,
            problem=problem,
            solution=solution,
            business_model=business_model,
            # Workflow authority belongs to ProjectContextExtractor.
            # PIL must not promote its own search/use-case inference
            # into resolver-owned structured workflow fields.
            workflows=[],
        )

        # The structured packet must expose a concise revenue hypothesis, not
        # the whole idea sentence that happened to contain the word
        # "commission" or "subscription".
        business_model = self._first_available_text(
            archetype_context.get("business_model_hypothesis"),
            business_model,
        )

        inferred_targets = self._safe_list(archetype_context.get("target_users"))
        if not target_users or self._roles_are_too_generic(target_users):
            target_users = inferred_targets

        inferred_workflows = self._safe_list(
            archetype_context.get("priority_workflows")
        )
        if explicit_workflows and archetype_context.get("project_archetype") == "hardware_iot":
            inferred_workflows = self._unique(
                explicit_workflows
                + [
                    item
                    for item in inferred_workflows
                    if not self._is_generic_workflow(item)
                ]
            )[:6]
        elif explicit_workflows and self._workflows_are_generic(inferred_workflows):
            inferred_workflows = explicit_workflows
        elif explicit_workflows:
            inferred_workflows = self._unique(inferred_workflows + explicit_workflows)[:6]
        if inferred_workflows:
            main_use_case = inferred_workflows[0]

        if not business_model:
            business_model = self._clean_text(
                archetype_context.get("business_model_hypothesis")
            )

        # MVP scope is a product-scope declaration, not a synonym for
        # a workflow or use case.
        #
        # Project Intelligence may infer workflows for search and
        # analysis support, but it must never promote those inferred
        # actions into canonical MVP scope when the user has not
        # actually declared a first-version boundary.
        #
        # Keep an absent MVP absent. Readiness may surface it as an
        # unknown/ambiguous field without inventing product scope.
        sector_tags = self._sector_tags(industry)
        sector_profile = self._sector_profile(sector_tags)

        target_terms = self._extract_concepts(
            values=target_users,
            max_items=20,
            prefer_short=True,
        )
        # Canonical workflows and solution semantics may enrich
        # search concepts. MVP/product scope must remain separate.
        #
        # Example:
        #   "The first MVP must include only X"
        # is product scope, not a primary use case.
        use_case_terms = self._extract_concepts(
            values=[
                main_use_case,
                *inferred_workflows,
                solution,
            ],
            max_items=16,
            prefer_short=False,
        )
        solution_terms = self._extract_concepts(
            values=[
                solution,
            ],
            max_items=14,
            prefer_short=False,
        )
        problem_terms = self._extract_concepts(
            values=[problem],
            max_items=10,
            prefer_short=False,
        )

        # Functional concepts must not be satisfied by the region or target
        # name alone. This is essential for direct-competitor validation.
        region_noise = self._extract_concepts(
            values=self._region_noise_values(target_region),
            max_items=16,
            prefer_short=True,
        )
        title_noise = self._extract_concepts(
            values=[title],
            max_items=8,
            prefer_short=True,
        )
        raw_target_noise = self._extract_concepts(
            values=target_users,
            max_items=36,
            prefer_short=True,
        )
        target_terms = self._remove_context_noise(target_terms, region_noise + title_noise)
        functional_noise = raw_target_noise + region_noise + title_noise
        use_case_terms = self._remove_context_noise(use_case_terms, functional_noise)
        solution_terms = self._remove_context_noise(solution_terms, functional_noise)
        problem_terms = self._remove_context_noise(problem_terms, functional_noise)

        domain_concepts = self._domain_concepts(
            industry=industry,
            description=description,
            sector_profile=sector_profile,
            project_context=project_context,
            use_case_terms=use_case_terms,
            solution_terms=solution_terms,
            target_terms=target_terms,
        )
        domain_concepts = self._unique(
            self._safe_list(archetype_context.get("search_terms"))
            + domain_concepts
        )[:32]
        search_concepts = self._rank_search_concepts(
            domain_concepts=domain_concepts,
            use_case_terms=use_case_terms,
            solution_terms=solution_terms,
            target_terms=target_terms,
            problem_terms=problem_terms,
        )

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
            search_concepts=search_concepts,
        )
        must_match_terms = self._must_match_terms(
            search_concepts=search_concepts,
            domain_concepts=domain_concepts,
            use_case_terms=use_case_terms,
            solution_terms=solution_terms,
        )
        weak_terms_to_ignore = self._weak_terms_to_ignore(
            sector_profile=sector_profile,
        )
        forbidden_offtopic_terms = self._forbidden_offtopic_terms(
            sector_profile=sector_profile,
            sector_tags=sector_tags,
        )

        solution_category = self._best_solution_category(
            solution_terms=solution_terms,
            domain_concepts=domain_concepts,
            industry=industry,
        )
        value_proposition = self._build_value_proposition(
            title=title,
            target_users=target_users,
            problem=problem,
            solution=solution,
            language=language,
        )
        search_workflows = self._priority_workflows(
            explicit_mvp=explicit_mvp,
            mvp_scope=mvp_scope,
            solution=solution,
            use_case_terms=use_case_terms,
            language=language,
            archetype_workflows=inferred_workflows,
        )
        primary_target = target_users[0] if target_users else ""
        secondary_targets = target_users[1:4]
        economic_buyer = self._economic_buyer(
            explicit_buyer=explicit_economic_buyer,
            target_users=target_users,
            industry=industry,
            language=language,
            archetype_context=archetype_context,
        )
        actors = self._merge_actor_context(
            archetype_context=archetype_context,
            target_users=target_users,
            economic_buyer=economic_buyer,
            language=language,
        )
        success_metrics = self._unique(
            explicit_success_metrics
            + self._safe_list(archetype_context.get("success_metrics"))
        )[:12]
        constraints = self._unique(
            explicit_constraint_items
            + self._safe_list(project_context.get("constraints"))
            + self._safe_list(archetype_context.get("constraints"))
        )[:12]

        structured_project_context = {
            "project_name": title,
            "title": title,
            "description": description,
            "sector": industry,
            "industry": industry,
            "sector_tags": sector_tags,
            "project_archetype": archetype_context.get("project_archetype"),
            "vertical": archetype_context.get("vertical"),
            "business_motion": archetype_context.get("business_motion"),
            "interaction_model": archetype_context.get("interaction_model"),
            "validation_unit": archetype_context.get("validation_unit"),
            "actors": actors,
            "success_metrics": success_metrics,
            "constraints": constraints,
            "risk_dimensions": self._unique(
                self._safe_list(archetype_context.get("risk_dimensions"))
                + constraints
            )[:16],
            "evidence_needs": archetype_context.get("evidence_needs") or [],
            "archetype_confidence": archetype_context.get("confidence"),
            "target_region": target_region,
            "market_region": target_region,
            "target_users": target_users,
            "primary_target": primary_target,
            "secondary_targets": secondary_targets,
            "economic_buyer": economic_buyer,
            "target_terms": target_terms,
            "problem": problem,
            "core_problem": problem,
            "problem_keywords": problem_terms,
            "solution": solution,
            "solution_type": solution_category or solution,
            "solution_category": solution_category,
            "solution_terms": solution_terms,
            # Search/use-case inference is non-authoritative here.
            # Canonical priority workflows are built later by
            # ProjectContextExtractor.
            "main_use_case": main_use_case,
            "priority_workflow": "",
            "priority_workflows": [],
            "use_cases": use_case_terms,
            "use_case_terms": use_case_terms,
            "domain_concepts": domain_concepts,
            "search_concepts": search_concepts,
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
            search_concepts=search_concepts,
            domain_concepts=domain_concepts,
            use_case_terms=search_workflows + use_case_terms,
            solution_terms=solution_terms,
            target_terms=target_terms,
            archetype_context=archetype_context,
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
            "format": "project_intelligence_packet_v4_archetype_aware",
            "structured_project_context": structured_project_context,
            "archetype_context": archetype_context,
            "strong_keywords": strong_keywords,
            "must_match_terms": must_match_terms,
            "domain_concepts": domain_concepts,
            "search_concepts": search_concepts,
            "target_terms": target_terms,
            "use_case_terms": use_case_terms,
            "solution_terms": solution_terms,
            "problem_keywords": problem_terms,
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
            "format": "project_intelligence_layer_v4_archetype_aware",
            "status": "completed",
            "output_language": language,
            "context_locked": True,
            "structured_project_context": structured_project_context,
            "archetype_context": archetype_context,
            "strong_keywords": strong_keywords,
            "must_match_terms": must_match_terms,
            "domain_concepts": domain_concepts,
            "search_concepts": search_concepts,
            "target_terms": target_terms,
            "use_case_terms": use_case_terms,
            "solution_terms": solution_terms,
            "problem_keywords": problem_terms,
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
            "domain_concepts": intelligence.get("domain_concepts") or [],
            "search_concepts": intelligence.get("search_concepts") or [],
            "target_terms": intelligence.get("target_terms") or [],
            "use_case_terms": intelligence.get("use_case_terms") or [],
            "solution_terms": intelligence.get("solution_terms") or [],
            "problem_keywords": intelligence.get("problem_keywords") or [],
            "weak_terms_to_ignore": intelligence.get("weak_terms_to_ignore") or [],
            "forbidden_offtopic_terms": intelligence.get("forbidden_offtopic_terms") or [],
            "source_acceptance_rules": intelligence.get("source_acceptance_rules") or {},
            "query_planner": intelligence.get("query_planner") or {},
            "context_confidence": intelligence.get("context_confidence") or {},
            "context_locked": True,
        }

        merged["anchor_terms"] = self._unique(
            self._safe_list(base_project_context.get("anchor_terms"))
            + intelligence.get("domain_concepts", [])
            + intelligence.get("use_case_terms", [])
            + intelligence.get("solution_terms", [])
            + intelligence.get("must_match_terms", [])
        )[:60]
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
            "paper",
            "excel",
            "spreadsheet",
            "whatsapp",
            "outdated",
            "administrative burden",
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
        # Explicit role statements always win over heuristic sentence matches.
        explicit_roles = self._extract_actor_roles_from_description(description)
        if explicit_roles:
            return explicit_roles[:8]

        candidates = (
            self._safe_list(project_context.get("target_users"))
            + self._safe_list(project_context.get("target_market"))
            + self._safe_list(detected.get("target_users"))
        )
        valid_candidates = [
            item for item in candidates if self._is_actor_phrase(item)
        ]
        if valid_candidates:
            return self._unique(valid_candidates)[:8]

        patterns = [
            r"(?:first target users are|target users are|target users include)\s+(.+?)(?:\.|\n|$)",
            r"(?:the first target users are)\s+(.+?)(?:\.|\n|$)",
            r"(?:users are|customers are|clients are)\s+(.+?)(?:\.|\n|$)",
            r"(?:les utilisateurs cibles sont|les premiers utilisateurs sont|les premiers utilisateurs ciblés sont|les clients cibles sont)\s+(.+?)(?:\.|\n|$)",
            r"(?:la cible est|les cibles sont)\s+(.+?)(?:\.|\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, flags=re.IGNORECASE)
            if not match:
                continue
            items = [item for item in self._split_items(match.group(1)) if self._is_actor_phrase(item)]
            if items:
                return items[:8]
        return []

    def _roles_are_too_generic(self, values: List[str]) -> bool:
        if not values:
            return True
        generic = {
            "target user", "target users", "user", "users",
            "utilisateur cible", "utilisateurs cibles", "client", "clients",
            "economic buyer", "acheteur economique", "acheteur économique",
        }
        useful = []
        for value in values:
            normalized = self._normalize_concept(value)
            if not normalized or normalized in generic:
                continue
            if len(normalized.split()) > 14:
                continue
            useful.append(normalized)
        return not useful

    def _extract_actor_roles_from_description(self, description: str) -> List[str]:
        patterns = [
            r"(?:the\s+)?(?:main|primary)\s+operational\s+user\s+(?:is|would\s+be|will\s+be)\s+(.+?)(?:\.|,\s+but|\n|$)",
            r"(?:the\s+)?(?:main|primary)\s+(?:daily\s+)?user\s+(?:is|would\s+be|will\s+be)\s+(.+?)(?:\.|,\s+but|\n|$)",
            r"(?:l['’]utilisateur\s+opérationnel\s+principal|l['’]utilisateur\s+principal)\s+(?:est|serait)\s+(.+?)(?:\.|,\s+mais|\n|$)",
        ]
        roles: List[str] = []
        for pattern in patterns:
            match = re.search(pattern, description, flags=re.IGNORECASE)
            if match:
                candidate = self._clean_actor_phrase(match.group(1))
                if self._is_actor_phrase(candidate):
                    roles.append(candidate)
        buyer = self._extract_economic_buyer_from_description(description)
        if buyer and self._is_actor_phrase(buyer):
            roles.append(buyer)
        return self._unique(roles)

    def _extract_economic_buyer_from_description(self, description: str) -> str:
        patterns = [
            r"(?:the\s+)?economic\s+buyer\s+(?:is|would\s+be|will\s+be|would\s+probably\s+be|is\s+probably)\s+(.+?)(?:\.|,\s+but|\n|$)",
            r"(?:the\s+)?budget\s+owner\s+(?:is|would\s+be|will\s+be)\s+(.+?)(?:\.|,\s+but|\n|$)",
            r"(?:l['’]acheteur\s+économique|le\s+détenteur\s+du\s+budget)\s+(?:est|serait)\s+(.+?)(?:\.|,\s+mais|\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, flags=re.IGNORECASE)
            if match:
                candidate = self._clean_actor_phrase(match.group(1))
                if self._is_actor_phrase(candidate):
                    return candidate
        return ""

    def _clean_actor_phrase(self, value: str) -> str:
        text = self._clean_text(value).strip(" .,:;-")
        text = re.sub(r"^(?:the|a|an|le|la|les|un|une)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(?:probably|possibly|likely)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+(?:responsible for|who manages|in charge of)\s+.+$", "", text, flags=re.IGNORECASE)
        return text.strip(" .,:;-")

    def _is_actor_phrase(self, value: Any) -> bool:
        text = self._clean_actor_phrase(str(value or ""))
        if not text or len(text.split()) > 14:
            return False
        normalized = self._normalize_concept(text)
        tool_terms = {
            "excel", "spreadsheet", "spreadsheets", "whatsapp", "paper", "notebook",
            "notebooks", "software", "platform", "application", "app", "monthly export",
        }
        action_markers = {
            "still prepare", "prepare weekly", "needs to verify", "would focus",
            "focus only", "the first version", "before developing", "struggle to",
        }
        actor_markers = {
            "user", "users", "customer", "customers", "client", "clients", "manager",
            "owner", "assistant", "supervisor", "employee", "employees", "worker", "workers",
            "company", "companies", "business", "businesses", "cooperative", "coopérative", "coopératives", "producer", "producteur", "producteurs",
            "beekeeper", "farmer", "doctor", "patient", "student", "teacher", "restaurant",
            "factory", "factories", "workshop", "workshops", "retailer", "retail",
            "responsable", "directeur", "proprietaire", "propriétaire", "employe", "employé",
            "entreprise", "entreprises", "coordinateur", "coordinateurs",
        }
        if any(marker in normalized for marker in action_markers):
            return False
        if all(term in normalized for term in ("excel", "whatsapp")):
            return False
        if normalized in tool_terms or any(normalized.startswith(f"{term} ") for term in tool_terms):
            return False
        return any(marker in normalized for marker in actor_markers)

    def _extract_labeled_section(
        self,
        text: str,
        *,
        labels: tuple[str, ...],
        stop_labels: tuple[str, ...],
    ) -> str:
        clean = self._clean_text(text)
        if not clean:
            return ""

        lowered = clean.lower()
        starts: list[tuple[int, str]] = []
        for label in labels:
            index = lowered.find(label.lower())
            if index >= 0:
                starts.append((index, label))
        if not starts:
            return ""

        start_index, label = min(starts, key=lambda item: item[0])
        content_start = start_index + len(label)
        end_index = len(clean)
        for stop in stop_labels:
            index = lowered.find(stop.lower(), content_start)
            if index >= 0:
                end_index = min(end_index, index)

        value = clean[content_start:end_index].strip(" \t\n:;.-")
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            return ""
        return value[0].upper() + value[1:] if len(value) > 1 else value.upper()

    def _hint_matches(
        self,
        text: str,
        hint: str,
    ) -> bool:
        """
        Match semantic hints only as complete words / expressions.

        A short hint such as "tool" must match "tool", but must never
        match a product name such as "ToolShare". The same protection
        applies universally to app/platform/system and every other
        hint used by the intelligence layer.
        """
        normalized_text = self._clean_text(
            text
        ).casefold()

        normalized_hint = self._clean_text(
            hint
        ).casefold()

        if (
            not normalized_text
            or not normalized_hint
        ):
            return False

        return bool(
            re.search(
                rf"(?<!\w)"
                rf"{re.escape(normalized_hint)}"
                rf"(?!\w)",
                normalized_text,
                flags=re.IGNORECASE,
            )
        )

    def _extract_sentence(
        self,
        text: str,
        hints: set[str],
    ) -> str:
        clean_text = self._clean_text(
            text
        )

        if not clean_text:
            return ""

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            clean_text,
        )

        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            sentence = self._clean_text(
                sentence
            )

            if len(sentence) < 20:
                continue

            score = sum(
                1
                for hint in hints
                if self._hint_matches(
                    sentence,
                    hint,
                )
            )

            if score > best_score:
                best_score = score
                best_sentence = sentence

        return (
            best_sentence
            if best_score > 0
            else ""
        )

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
            "human resources": ["workforce"],
            "workforce": ["workforce"],
            "workforce management": ["workforce"],
            "workforce scheduling": ["workforce"],
            "employee scheduling": ["workforce"],
            "shift planning": ["workforce"],
            "shift scheduling": ["workforce"],
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
            "transport": ["mobility"],
            "mobility": ["mobility"],
            "mobilité": ["mobility"],
            "mobilite": ["mobility"],
            "taxi": ["mobility", "marketplace"],
            "ride hailing": ["mobility", "marketplace"],
            "recruitment": ["recruitment", "marketplace"],
            "recrutement": ["recruitment", "marketplace"],
            "internship": ["recruitment", "marketplace"],
            "stage": ["recruitment", "marketplace"],
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
        search_concepts: List[str] | None = None,
    ) -> List[str]:
        """Return search-safe business concepts, never sentence fragments.

        Business-model wording, project names and region names are excluded from
        the strong list. They remain available elsewhere in the context but may
        not count as source relevance evidence.
        """
        candidates: List[str] = []
        candidates.extend(search_concepts or [])
        candidates.extend(self._safe_list(project_context.get("domain_concepts")))
        candidates.extend(self._safe_list(project_context.get("search_concepts")))
        candidates.extend(self._safe_list(project_context.get("anchor_terms")))

        region_tokens = set(self._concept_tokens(target_region))
        title_tokens = set(self._concept_tokens(title))
        result: List[str] = []

        for candidate in candidates:
            clean = self._normalize_concept(candidate)
            if not self._is_specific_concept(clean):
                continue
            tokens = set(self._concept_tokens(clean))
            if tokens and tokens.issubset(region_tokens | title_tokens):
                continue
            result.append(clean)

        return self._unique(result)[:48]

    def _must_match_terms(
        self,
        *,
        search_concepts: List[str],
        domain_concepts: List[str],
        use_case_terms: List[str],
        solution_terms: List[str],
    ) -> List[str]:
        """Return a compact evidence gate, not a bag of every project word."""
        candidates = (
            domain_concepts[:8]
            + use_case_terms[:8]
            + solution_terms[:6]
            + search_concepts[:12]
        )
        return self._unique(
            [
                self._normalize_concept(item)
                for item in candidates
                if self._is_specific_concept(item)
            ]
        )[:20]

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
        """Compatibility wrapper around the professional concept extractor."""
        return self._extract_concepts(
            values=[text],
            max_items=24,
            prefer_short=False,
        )

    def _extract_concepts(
        self,
        *,
        values: List[Any],
        max_items: int,
        prefer_short: bool,
    ) -> List[str]:
        candidates: List[str] = []
        occurrence: Dict[str, int] = {}

        for raw_value in values:
            for raw in self._safe_list(raw_value):
                normalized = self._normalize_concept(raw)
                if not normalized:
                    continue

                clauses = re.split(
                    r"[,;:|/]|\\b(?:and|or|et|ou|where|who|that|which|pour|afin de)\\b",
                    normalized,
                    flags=re.IGNORECASE,
                )
                for clause in clauses:
                    tokens = self._concept_tokens(clause)
                    if not tokens:
                        continue
                    clean_tokens = [
                        token for token in tokens
                        if token not in self.CONCEPT_STOP_WORDS
                        and token not in self.GENERIC_CONCEPT_TERMS
                        and len(token) >= 3
                    ]
                    if not clean_tokens:
                        continue

                    # Single terms preserve niche nouns; two- and three-word
                    # phrases preserve meaning such as "invoice reconciliation".
                    for size in (3, 2, 1):
                        for index in range(0, len(clean_tokens) - size + 1):
                            phrase = " ".join(clean_tokens[index:index + size])
                            if not self._is_specific_concept(phrase):
                                continue
                            occurrence[phrase] = occurrence.get(phrase, 0) + 1

        candidates = list(occurrence)
        candidates.sort(
            key=lambda item: (
                occurrence[item],
                1 if 2 <= len(item.split()) <= 3 else 0,
                -abs(len(item.split()) - (2 if prefer_short else 3)),
                len(item),
            ),
            reverse=True,
        )
        return self._unique(candidates)[:max_items]

    def _domain_concepts(
        self,
        *,
        industry: str,
        description: str,
        sector_profile: Dict[str, Any],
        project_context: Dict[str, Any],
        use_case_terms: List[str],
        solution_terms: List[str],
        target_terms: List[str],
    ) -> List[str]:
        project_text = self._normalize_concept(
            " ".join([industry, description, " ".join(use_case_terms + solution_terms + target_terms)])
        )
        candidates: List[str] = []

        # Existing structured concepts have priority.
        candidates.extend(self._safe_list(project_context.get("domain_concepts")))
        candidates.extend(self._safe_list(project_context.get("search_concepts")))

        # Sector profiles enrich matching projects, but a profile term is kept
        # only when the idea or industry shares at least one meaningful token.
        project_tokens = set(self._concept_tokens(project_text))
        for term in sector_profile.get("strong_terms", []):
            term_tokens = set(self._concept_tokens(term))
            meaningful = {
                token for token in term_tokens
                if token not in self.GENERIC_CONCEPT_TERMS
                and token not in self.CONCEPT_STOP_WORDS
            }
            if meaningful and meaningful & project_tokens:
                candidates.append(term)

        candidates.extend(self._extract_concepts(
            values=[industry], max_items=8, prefer_short=True
        ))
        candidates.extend(use_case_terms[:8])
        candidates.extend(solution_terms[:8])

        return self._unique([
            self._normalize_concept(item)
            for item in candidates
            if self._is_specific_concept(item)
        ])[:24]

    def _rank_search_concepts(
        self,
        *,
        domain_concepts: List[str],
        use_case_terms: List[str],
        solution_terms: List[str],
        target_terms: List[str],
        problem_terms: List[str],
    ) -> List[str]:
        weighted = (
            domain_concepts[:16]
            + use_case_terms[:14]
            + solution_terms[:12]
            + target_terms[:8]
            + problem_terms[:6]
        )
        return self._unique([
            self._normalize_concept(item)
            for item in weighted
            if self._is_specific_concept(item)
        ])[:36]

    def _best_solution_category(
        self,
        *,
        solution_terms: List[str],
        domain_concepts: List[str],
        industry: str,
    ) -> str:
        for item in solution_terms + domain_concepts:
            if 2 <= len(item.split()) <= 4 and self._is_specific_concept(item):
                return item
        return self._normalize_concept(industry)

    def _pick_query_concept(
        self,
        primary: List[str],
        fallback: List[str],
        index: int,
    ) -> str:
        selected_pool = primary if any(self._is_specific_concept(item) for item in primary) else fallback
        pool = [item for item in selected_pool if self._is_specific_concept(item)]
        pool = self._unique(pool)
        pool.sort(
            key=lambda item: (
                1 if not (set(self._concept_tokens(item)) & self.QUERY_AUDIENCE_TERMS) else 0,
                1 if 2 <= len(item.split()) <= 3 else 0,
                len(item.split()),
                len(item),
            ),
            reverse=True,
        )
        if not pool:
            return "business workflow"
        return pool[min(index, len(pool) - 1)]

    def _remove_context_noise(
        self,
        concepts: List[str],
        noise_concepts: List[str],
    ) -> List[str]:
        noise_tokens = {
            token
            for concept in noise_concepts
            for token in self._concept_tokens(concept)
        }
        result: List[str] = []
        for concept in concepts:
            remaining = [
                token
                for token in self._concept_tokens(concept)
                if token not in noise_tokens
            ]
            if not remaining:
                continue
            clean = " ".join(remaining)
            if not self._is_specific_concept(clean):
                continue
            result.append(clean)
        result.sort(
            key=lambda item: (
                1 if 2 <= len(item.split()) <= 3 else 0,
                len(item.split()),
                len(item),
            ),
            reverse=True,
        )
        return self._unique(result)

    def _region_noise_values(self, region: str) -> List[str]:
        clean = self._normalize_concept(region)
        values = [clean] if clean else []
        aliases = {
            "tunisie": ["tunisia", "tunisian", "tunisien", "tunisienne"],
            "tunisia": ["tunisie", "tunisian", "tunisien", "tunisienne"],
            "france": ["french", "français", "francais", "française", "francaise"],
            "germany": ["german", "allemagne", "allemand"],
            "allemagne": ["germany", "german", "allemand"],
            "morocco": ["maroc", "moroccan", "marocain"],
            "maroc": ["morocco", "moroccan", "marocain"],
            "algeria": ["algérie", "algerie", "algerian", "algérien", "algerien"],
            "algérie": ["algeria", "algerie", "algerian", "algérien", "algerien"],
        }
        for key, items in aliases.items():
            if key in clean:
                values.extend(items)
        return self._unique(values)

    def _pick_market_domain_concept(
        self,
        primary: List[str],
        fallback: List[str],
    ) -> str:
        pool = self._unique([
            item for item in primary + fallback
            if self._is_specific_concept(item)
        ])
        workflow_verbs = {
            "track", "record", "register", "export", "generate", "create",
            "follow", "manage", "suivi", "enregistrer", "générer", "generer",
        }
        preferred = [
            item for item in pool
            if len(item.split()) == 2
            and not (set(self._concept_tokens(item)) & workflow_verbs)
            and not (set(self._concept_tokens(item)) & self.QUERY_AUDIENCE_TERMS)
        ]
        if preferred:
            return preferred[0]
        single_word = [
            item for item in pool
            if len(item.split()) == 1
            and not (set(self._concept_tokens(item)) & self.QUERY_AUDIENCE_TERMS)
        ]
        if single_word:
            return single_word[0]
        return pool[0] if pool else "business sector"

    def _relevant_profile_queries(
        self,
        queries: List[str],
        concepts: List[str],
        limit: int,
    ) -> List[str]:
        concept_tokens = {
            token for concept in concepts for token in self._concept_tokens(concept)
            if token not in self.GENERIC_CONCEPT_TERMS
            and token not in self.CONCEPT_STOP_WORDS
        }
        result: List[str] = []
        for query in queries:
            query_tokens = set(self._concept_tokens(query))
            if concept_tokens and not (query_tokens & concept_tokens):
                continue
            result.append(query)
            if len(result) >= limit:
                break
        return result

    def _select_balanced_queries(
        self,
        queries_by_intent: Dict[str, List[str]],
        max_queries: int,
    ) -> List[str]:
        order = [
            "direct_competitors",
            "local_solutions",
            "official_sources",
            "market_sources",
            "adjacent_solutions",
            "pricing",
            "field_validation",
        ]
        selected: List[str] = []
        cursor = 0
        while len(selected) < max_queries:
            added = False
            for intent in order:
                values = queries_by_intent.get(intent) or []
                if cursor < len(values):
                    candidate = values[cursor]
                    if candidate not in selected:
                        selected.append(candidate)
                        added = True
                        if len(selected) >= max_queries:
                            break
            if not added:
                break
            cursor += 1
        return selected

    def _normalize_query(self, value: Any) -> str:
        text = self._normalize_concept(value)
        tokens: List[str] = []
        seen = set()
        for token in self._concept_tokens(text):
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)
        return " ".join(tokens[:9])

    def _normalize_concept(self, value: Any) -> str:
        text = self._clean_text(value).lower()
        text = text.replace("’", "'")
        text = re.sub(r"[^a-z0-9à-ÿ' -]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" -")
        return text

    def _concept_tokens(self, value: Any) -> List[str]:
        normalized = self._normalize_concept(value)
        return [
            token for token in re.split(r"[\s-]+", normalized)
            if token
        ]

    def _is_specific_concept(self, value: Any) -> bool:
        clean = self._normalize_concept(value)
        if not clean:
            return False
        tokens = [
            token for token in self._concept_tokens(clean)
            if token not in self.CONCEPT_STOP_WORDS
            and token not in self.GENERIC_CONCEPT_TERMS
        ]
        if not tokens:
            return False
        if len(tokens) == 1 and len(tokens[0]) < 4:
            return False
        return True

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
        search_concepts: List[str] | None = None,
        domain_concepts: List[str] | None = None,
        use_case_terms: List[str] | None = None,
        solution_terms: List[str] | None = None,
        target_terms: List[str] | None = None,
        archetype_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Create short, intent-specific and workflow-balanced queries.

        The planner never lets a secondary feature represent the full project.
        It combines a domain anchor, an exact target or a concrete workflow and
        the region. Discovery and verification intents remain separate.
        """
        del title, problem, business_model
        search_concepts = search_concepts or strong_keywords
        domain_concepts = domain_concepts or search_concepts
        use_case_terms = use_case_terms or search_concepts
        solution_terms = solution_terms or search_concepts
        target_terms = target_terms or []
        archetype_context = archetype_context or {}

        region = self._short_query_phrase(target_region, max_words=2)
        industry_parts = [
            self._normalize_concept(part)
            for part in re.split(r"[/|,;]+", industry)
            if self._normalize_concept(part)
        ]
        generic_industry_parts = {
            "agritech", "edtech", "fintech", "healthtech", "legaltech",
            "technology", "technologie", "software", "saas", "traceability",
            "tracabilite", "digital", "human resources", "sme saas",
        }
        specific_industry = next(
            (part for part in industry_parts if part not in generic_industry_parts),
            "",
        )
        archetype_terms = self._safe_list(archetype_context.get("search_terms"))
        archetype_domain = self._pick_market_domain_concept(
            archetype_terms,
            archetype_terms,
        )
        domain = archetype_domain or specific_industry or self._pick_market_domain_concept(domain_concepts, search_concepts)
        target = self._pick_query_concept(target_terms, [], 0)

        def useful(values: List[str], limit: int = 4) -> List[str]:
            blocked_leads = {
                "generate", "create", "manage", "track", "record", "receive",
                "help", "simple", "basic", "software", "platform", "solution",
            }
            result: List[str] = []
            ranked_values = sorted(
                values,
                key=lambda value: (
                    1 if any(token in self._normalize_concept(value) for token in ("hive", "inspection", "treatment", "harvest", "contract", "maintenance", "renewal", "shift", "schedule", "attendance", "leave", "payroll")) else 0,
                    -1 if any(token in self._normalize_concept(value) for token in ("export", "generate", "sheet", "pricing")) else 0,
                    -len(self._concept_tokens(value)),
                ),
                reverse=True,
            )
            for value in ranked_values:
                clean = self._normalize_concept(value)
                tokens = self._concept_tokens(clean)
                if not tokens or tokens[0] in blocked_leads and len(tokens) == 1:
                    continue
                if clean in {"traceability sheets", "generate traceability sheets"}:
                    continue
                if len(tokens) > 5:
                    clean = " ".join(tokens[:5])
                if self._is_specific_concept(clean) and clean not in result:
                    result.append(clean)
                if len(result) >= limit:
                    break
            return result

        workflows = useful(use_case_terms, 5)
        solutions = useful(solution_terms, 4)
        anchors = useful(domain_concepts, 5)
        if not domain:
            domain = anchors[0] if anchors else self._normalize_query(industry)
        primary_workflow = workflows[0] if workflows else (solutions[0] if solutions else domain)
        secondary_workflow = workflows[1] if len(workflows) > 1 else (solutions[1] if len(solutions) > 1 else domain)

        archetype_queries = archetype_context.get("search_queries") or {}
        direct = (
            self._safe_list(archetype_queries.get("local_fr"))[:3]
            + self._safe_list(archetype_queries.get("local_en"))[:3]
            + [
                f"{domain} management software {region}",
                f"{target} {domain} application {region}" if target else f"{domain} application {region}",
                f"{primary_workflow} software {region}",
            ]
        )
        local_solutions = (
            self._safe_list(archetype_queries.get("all"))[:3]
            + [
                f"{region} {domain} application platform",
                f"{region} {target} digital platform" if target else f"{region} {domain} startup",
            ]
        )
        adjacent = [
            f"{domain} workflow software",
            f"{secondary_workflow} platform",
            f"{domain} technology solutions",
        ]
        official = [
            f"{region} {domain} statistics official",
            f"{region} {domain} ministry report",
        ]
        market = [
            f"{region} {domain} market report",
            f"{region} {domain} association cooperative",
            f"{region} {domain} digital adoption study",
        ]
        pricing = [
            f"{domain} software pricing",
            f"{primary_workflow} SaaS pricing",
        ]
        validation = [
            f"{region} {target} workflow survey" if target else f"{region} {domain} user survey",
            f"{region} {domain} adoption barriers",
        ]

        profile_queries = sector_profile.get("queries") or {}
        direct.extend(self._relevant_profile_queries(
            profile_queries.get("direct_competitors", []), search_concepts, 2
        ))
        adjacent.extend(self._relevant_profile_queries(
            profile_queries.get("adjacent_solutions", []), search_concepts, 2
        ))
        market.extend(self._relevant_profile_queries(
            profile_queries.get("market_sources", []), domain_concepts, 2
        ))
        pricing.extend(self._relevant_profile_queries(
            profile_queries.get("pricing", []), search_concepts, 1
        ))

        if language == "fr":
            direct.append(f"logiciel {domain} {region}")
            local_solutions.append(f"application {domain} {region}")
            official.append(f"statistiques officielles {domain} {region}")

        queries_by_intent = {
            "direct_competitors": self._clean_queries(direct, max_queries=5),
            "local_solutions": self._clean_queries(local_solutions, max_queries=4),
            "official_sources": self._clean_queries(official, max_queries=3),
            "market_sources": self._clean_queries(market, max_queries=4),
            "adjacent_solutions": self._clean_queries(adjacent, max_queries=4),
            "pricing": self._clean_queries(pricing, max_queries=2),
            "field_validation": self._clean_queries(validation, max_queries=2),
        }

        return {
            "format": "query_planner_v5_archetype_aware",
            "project_archetype": archetype_context.get("project_archetype"),
            "vertical": archetype_context.get("vertical"),
            "base_context": self._clean_text(
                " | ".join(item for item in [domain, target, primary_workflow, region] if item)
            ),
            "primary_search_terms": search_concepts[:24],
            "domain_concepts": domain_concepts[:16],
            "use_case_terms": use_case_terms[:16],
            "solution_terms": solution_terms[:16],
            "target_terms": target_terms[:12],
            "priority_workflows": workflows[:5],
            "queries_by_intent": queries_by_intent,
            "queries": self._select_balanced_queries(queries_by_intent, max_queries=8),
            "verification_queries": self._unique(
                queries_by_intent["official_sources"] + queries_by_intent["field_validation"]
            )[:4],
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

    def _clean_queries(
        self,
        queries: List[str],
        max_queries: int = 8,
    ) -> List[str]:
        cleaned: List[str] = []
        for query in queries:
            clean = self._normalize_query(query)
            if len(clean.split()) < 3 or len(clean.split()) > 9:
                continue
            specific = [
                token for token in self._concept_tokens(clean)
                if token not in self.GENERIC_CONCEPT_TERMS
                and token not in self.QUERY_INTENT_TERMS
                and token not in self.CONCEPT_STOP_WORDS
            ]
            if not specific:
                continue
            cleaned.append(clean)
        return self._unique(cleaned)[:max_queries]

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
            "format": "source_acceptance_rules_v3_claim_aware_evidence",
            "public_display_threshold": 0.70,
            "internal_use_threshold": 0.50,
            "rejection_threshold": 0.50,
            "minimum_required_signals": {
                "direct_competitor": [
                    "same_or_close_target_user",
                    "same_or_close_use_case",
                    "same_or_close_solution_category",
                    "local_or_clear_target_region",
                    "explicit_product_page_signal",
                    "domain_plus_use_case_evidence",
                ],
                "adjacent_solution": [
                    "clear_contextual_link",
                    "relevant_target_or_use_case",
                ],
                "market_source": [
                    "sector_relevance",
                    "regional_or_target_relevance",
                    "claim_compatible_evidence_category",
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
        """
        Produit un diagnostic non autoritaire de qualité du contexte
        destiné à la planification des recherches et à l'observabilité.

        Cette méthode ne décide jamais si les agents peuvent être lancés.
        La décision canonique appartient exclusivement à
        IdeaReadinessChecker et ContextConfidenceGate.

        La clé publique ``context_confidence`` est conservée pour la
        compatibilité avec les consommateurs Sprint 3, mais son contenu
        est désormais explicitement descriptif et non décisionnel.
        """
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

        canonical_readiness_score = float(
            idea_readiness.get("score")
            or 0
        )

        base_score = 1.0
        base_score -= (
            0.10
            * len(missing_fields)
        )
        base_score -= (
            0.04
            * len(ambiguous_fields)
        )

        if canonical_readiness_score > 0:
            base_score = (
                base_score
                + canonical_readiness_score
            ) / 2

        score = round(
            max(
                0.0,
                min(
                    1.0,
                    base_score,
                ),
            ),
            2,
        )

        return {
            "format": (
                "context_confidence_v3_"
                "non_authoritative"
            ),
            "score": score,
            "missing_fields": self._unique(
                missing_fields
            ),
            "ambiguous_fields": self._unique(
                ambiguous_fields
            ),
            "readiness_score": (
                canonical_readiness_score
            ),
            "purpose": (
                "source_discovery_diagnostics"
            ),
            "authority": "none",
            "decision_owner": (
                "idea_readiness_checker+"
                "context_confidence_gate"
            ),
            "non_authoritative": True,
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

    def _split_evidence_items(self, value: Any) -> List[str]:
        text = self._clean_text(value)
        if not text:
            return []
        parts = re.split(
            r"[;\n]|,(?=\s*(?:et|and|ou|or)?\s*[a-zA-ZÀ-ÿ0-9])|"
            r"\s+(?:et|and)\s+(?=(?:(?:la|le|l['’]|the)\s+)?(?:réduit|reduit|détecte|detecte|couvre|mesure|améliore|ameliore|maintenance|réparation|reparation|reduces|detects|covers|measures|improves|maintenance|repair)\b)",
            text,
            flags=re.IGNORECASE,
        )
        result: List[str] = []
        for part in parts:
            clean = re.sub(r"^(?:et|and|ou|or)\s+", "", part.strip(" .,:;-"), flags=re.IGNORECASE)
            if len(clean) < 3:
                continue
            result.append(clean)
        return self._unique(result)[:12]

    def _workflows_are_generic(self, workflows: List[str]) -> bool:
        if not workflows:
            return True
        generic_markers = {
            "core action",
            "core workflow",
            "main field operation",
            "perform the main field operation",
            "réaliser l'opération terrain principale",
            "réaliser l’opération terrain principale",
            "opération terrain principale",
            "gérer le flux principal",
            "manage the core workflow",
        }
        normalized = [self._normalize_concept(item) for item in workflows]
        return all(
            any(self._normalize_concept(marker) in item for marker in generic_markers)
            or len(item.split()) < 3
            for item in normalized
        )

    def _is_generic_workflow(self, value: Any) -> bool:
        normalized = self._normalize_concept(value)
        generic_markers = (
            "core action",
            "core workflow",
            "main field operation",
            "operation terrain principale",
            "opération terrain principale",
            "realiser l operation terrain principale",
            "réaliser l opération terrain principale",
            "manage the core workflow",
            "gerer le flux principal",
            "gérer le flux principal",
        )
        return not normalized or any(
            self._normalize_concept(marker) in normalized
            for marker in generic_markers
        )

    def _extract_explicit_workflows(
        self,
        *,
        description: str,
        solution: str,
        mvp_scope: str,
        language: str,
    ) -> List[str]:
        # Canonical invariant:
        # MVP/product scope is not workflow authority.
        #
        # Keep ``mvp_scope`` in the signature for compatibility,
        # but do not parse it as an explicit user workflow.
        text = self._clean_text(
            ". ".join(
                [
                    solution,
                    description,
                ]
            )
        )
        if not text:
            return []
        lowered_text = text.lower()
        workflow_stop_markers = (
            "les premiers utilisateurs ciblés",
            "les utilisateurs cibles",
            "the first target users",
            "target users are",
            "le modèle économique",
            "the business model",
            "les contraintes principales",
            "the main constraints",
            "le pilote sera considéré comme réussi si",
            "the pilot will be considered successful if",
        )
        stop_positions = [
            lowered_text.find(marker)
            for marker in workflow_stop_markers
            if lowered_text.find(marker) >= 0
        ]
        if stop_positions:
            text = text[: min(stop_positions)].strip()

        clauses = re.split(
            r"(?<=[.!?])\s+|[;\n]+|,\s+(?:puis|then|et|and)\s+|"
            r",\s*(?=(?:détecte|detecte|transmet|signale|envoie|inspecte|surveille|detects|sends|reports|monitors)\b)",
            text,
            flags=re.IGNORECASE,
        )
        mappings_fr = (
            (r"^inspecte\s+", "inspecter "),
            (r"^surveille\s+", "surveiller "),
            (r"^détecte\s+", "détecter "),
            (r"^detecte\s+", "détecter "),
            (r"^transmet\s+", "transmettre "),
            (r"^signale\s+", "signaler "),
            (r"^envoie\s+", "envoyer "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+inspecte\s+", "inspecter "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+surveille\s+", "surveiller "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+détecte\s+", "détecter "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+transmet\s+", "transmettre "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+signale\s+", "signaler "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+envoie\s+", "envoyer "),
            (r"^(?:le|la|les|un|une|l['’])?\s*(?:robot|application|plateforme|système|solution|outil)\s+permet de\s+", ""),
        )
        mappings_en = (
            (r"^inspects\s+", "inspect "),
            (r"^monitors\s+", "monitor "),
            (r"^detects\s+", "detect "),
            (r"^sends\s+", "send "),
            (r"^reports\s+", "report "),
            (r"^(?:the|a|an)?\s*(?:robot|application|platform|system|solution|tool)\s+inspects\s+", "inspect "),
            (r"^(?:the|a|an)?\s*(?:robot|application|platform|system|solution|tool)\s+monitors\s+", "monitor "),
            (r"^(?:the|a|an)?\s*(?:robot|application|platform|system|solution|tool)\s+detects\s+", "detect "),
            (r"^(?:the|a|an)?\s*(?:robot|application|platform|system|solution|tool)\s+sends\s+", "send "),
            (r"^(?:the|a|an)?\s*(?:robot|application|platform|system|solution|tool)\s+reports\s+", "report "),
            (r"^(?:the|a|an)?\s*(?:robot|application|platform|system|solution|tool)\s+allows\s+", ""),
        )
        action_verbs = (
            r"^(inspecter|surveiller|détecter|transmettre|signaler|envoyer|alerter|classer|mesurer|enregistrer|suivre|gérer|réserver|publier|consulter|maintenir|diagnostiquer)\b"
            if language != "en"
            else r"^(inspect|monitor|detect|send|report|alert|classify|measure|record|track|manage|book|publish|review|maintain|diagnose)\b"
        )
        mappings = mappings_en if language == "en" else mappings_fr
        result: List[str] = []
        for clause in clauses:
            clean = clause.strip(" .,:;-")

            if is_scope_exclusion_statement(
                clean
            ):
                continue

            if len(clean) < 8 or len(clean.split()) > 22:
                continue
            lowered = clean.lower()
            for pattern, replacement in mappings:
                updated = re.sub(pattern, replacement, lowered, flags=re.IGNORECASE)
                if updated != lowered:
                    lowered = updated
                    break
            lowered = re.sub(r"^(?:et|and|puis|then)\s+", "", lowered).strip()
            if not re.match(action_verbs, lowered, flags=re.IGNORECASE):
                continue
            if any(marker in lowered for marker in ("sera considéré", "considered successful", "modèle économique", "business model", "contraintes principales")):
                continue
            result.append(lowered)
        return self._unique(result)[:6]


    def _merge_actor_context(
        self,
        *,
        archetype_context: Dict[str, Any],
        target_users: List[str],
        economic_buyer: str,
        language: str,
    ) -> Dict[str, Any]:
        """
        Preserve actor information without assigning business roles.

        Demand, supply, payer, operator and technical-maintainer roles
        belong to the canonical context authority. List position,
        archetype or sector must never create those roles here.
        """
        actors = dict(
            archetype_context.get("actors")
            or {}
        )

        for role in (
            "demand_side",
            "supply_side",
            "operator_or_partner",
            "payer",
        ):
            actors.setdefault(role, "")

        if economic_buyer:
            actors["payer"] = economic_buyer

        actors["explicit_targets"] = list(
            actors.get("explicit_targets")
            or target_users
            or []
        )

        # Compatibility metadata only; no role assignment.
        actors["target_users"] = list(
            target_users
            or []
        )

        return actors

    def _priority_workflows(
        self,
        *,
        explicit_mvp: str,
        mvp_scope: str,
        solution: str,
        use_case_terms: List[str],
        language: str,
        archetype_workflows: List[str] | None = None,
    ) -> List[str]:
        raw_items: List[str] = []
        result: List[str] = []

        candidate_archetype_workflows = list(archetype_workflows or [])
        # Specific archetype workflows are authoritative. Generic placeholders
        # are replaced by actions extracted from the user's own description.
        if not self._workflows_are_generic(candidate_archetype_workflows):
            for item in candidate_archetype_workflows:
                workflow = self._clean_text(item).strip(" .,:;-")
                if not workflow or workflow.casefold() in {value.casefold() for value in result}:
                    continue
                result.append(workflow)
                if len(result) >= 6:
                    break

        # Never manufacture workflow authority from MVP/product
        # scope merely because fewer than three workflows exist.
        #
        # Search-oriented use-case terms remain a cautious fallback
        # only when no workflow authority survived.
        if not result:
            raw_items.extend(
                use_case_terms
            )

        if (
            not result
            and self._workflows_are_generic(
                candidate_archetype_workflows
            )
        ):
            raw_items.extend(
                candidate_archetype_workflows
            )

        for item in raw_items:
            if is_scope_exclusion_statement(
                item
            ):
                continue

            workflow = self._normalize_workflow_label(item, language)
            if not workflow or workflow.casefold() in {value.casefold() for value in result}:
                continue
            result.append(workflow)
            if len(result) >= 6:
                break

        if not result and solution:
            fallback = self._normalize_workflow_label(solution, language)
            if fallback:
                result.append(fallback)
        return result

    def _normalize_workflow_label(self, value: Any, language: str) -> str:
        clean = self._clean_text(value).strip(" .,:;-")
        if not clean:
            return ""
        normalized = self._normalize_concept(clean)
        meta_markers = {
            "the first version would focus", "first version would focus", "focus only on",
            "before developing", "needs to verify", "the idea is to", "la premiere version",
            "la première version", "se concentrerait", "avant de developper", "avant de développer",
        }
        for marker in meta_markers:
            normalized = normalized.replace(self._normalize_concept(marker), " ")
        normalized = re.sub(r"\s+", " ", normalized).strip(" .,:;-")
        if not normalized or len(normalized.split()) > 12:
            return ""

        en_rules = [
            (("shift planning", "shift scheduling", "weekly schedules", "weekly schedule"), "create weekly shift schedules"),
            (("attendance", "attendance tracking"), "record attendance"),
            (("leave requests", "leave request", "time off requests"), "manage leave requests"),
            (("payroll preparation", "payroll export", "monthly export"), "export monthly attendance data for payroll preparation"),
            (("schedule changes", "shift changes"), "notify employees about schedule changes"),
            (("hive inspections", "hive inspection"), "record hive inspections"),
            (("treatments", "treatment history"), "track treatments"),
            (("harvest batches", "harvest batch"), "track harvest batches"),
            (("traceability sheets", "traceability document", "traceability pdf"), "export a traceability document"),
            (("hive history",), "retrieve hive history"),
        ]
        fr_rules = [
            (("planning des equipes", "planning des équipes", "planning des horaires", "horaires hebdomadaires"), "créer le planning hebdomadaire des équipes"),
            (("presence", "présence", "suivi de presence", "suivi de présence"), "enregistrer les présences"),
            (("demandes de conge", "demandes de congé"), "gérer les demandes de congé"),
            (("export paie", "preparation de la paie", "préparation de la paie"), "exporter les données mensuelles pour la paie"),
            (("changements de planning", "changements d horaires"), "notifier les changements de planning"),
        ]
        rules = en_rules if language == "en" else fr_rules
        for needles, label in rules:
            if any(needle in normalized for needle in needles):
                return label

        verbs_en = r"^(record|register|track|link|export|review|retrieve|manage|monitor|generate|create|notify|approve|request|confirm|schedule|plan)\b"
        verbs_fr = r"^(enregistrer|suivre|relier|exporter|consulter|gérer|gerer|surveiller|générer|generer|créer|creer|notifier|approuver|demander|confirmer|planifier)\b"
        if language == "en" and re.match(verbs_en, normalized):
            return normalized
        if language == "fr" and re.match(verbs_fr, normalized):
            return normalized
        return (f"manage {normalized}" if language == "en" else f"gérer {normalized}")


    def _economic_buyer(
        self,
        *,
        explicit_buyer: str,
        target_users: List[str],
        industry: str,
        language: str,
        archetype_context: Dict[str, Any] | None = None,
    ) -> str:
        """
        Preserve an explicitly established payer only.

        ProjectIntelligenceLayer is not an actor-role authority.
        A target user, organization or industry label must never be
        promoted automatically to economic buyer.
        """
        if (
            explicit_buyer
            and self._is_actor_phrase(explicit_buyer)
        ):
            return self._clean_actor_phrase(
                explicit_buyer
            )

        archetype_context = (
            archetype_context
            or {}
        )

        payer = self._clean_text(
            (
                archetype_context.get("actors")
                or {}
            ).get("payer")
        )

        return payer

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

    def _first_available_non_scope_exclusion(
        self,
        *values: Any,
    ) -> str:
        """
        Return the first usable value that is not an explicit
        MVP/product-scope exclusion.

        Project Intelligence may use this value for search/use-case
        enrichment, but exclusions must never become positive use cases
        or MVP scope.
        """
        for value in values:
            clean = self._clean_text(
                value
            )

            if not clean:
                continue

            if is_scope_exclusion_statement(
                clean
            ):
                continue

            return clean

        return ""


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
        legacy_replacements = {
            "\u00e2\u20ac\u2122": "'",
            "\u00c3\u00a9": "é",
            "\u00c3\u00a8": "è",
            "\u00c3\u00aa": "ê",
            "\u00c3\u00a0": "à",
            "\u00c3\u00a2": "â",
            "\u00c3\u00ae": "î",
            "\u00c3\u00b4": "ô",
            "\u00c3\u00b9": "ù",
            "\u00c3\u00bb": "û",
            "\u00c3\u00a7": "ç",
            "\u00c2": "",
        }
        for legacy, repaired in legacy_replacements.items():
            text = text.replace(legacy, repaired)
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