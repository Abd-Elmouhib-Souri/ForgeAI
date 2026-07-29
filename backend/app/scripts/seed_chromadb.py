"""
backend/app/scripts/seed_chromadb.py
======================================
Script de seed pour ChromaDB — Sprint 2, section 2.4 du plan.

Charge des données de référence (tailles de marché par secteur, exemples de
startups, patterns SWOT/BMC génériques) dans la collection "market_reference"
pour que l'agent AI Business Analyst (RAG) ait un contexte réel à interroger,
au lieu de laisser le LLM inventer des chiffres.

SOURCES DES DONNÉES DE MARCHÉ (recherchées le 12/07/2026) :
- HealthTech/Télémédecine : Fortune Business Insights, Precedence Research,
  Mordor Intelligence, Research and Markets (voir doc_id health_tech_market)
- Fintech : Fortune Business Insights, Expert Market Research, IMARC Group,
  Polaris Market Research (voir doc_id fintech_market)
- E-commerce : Grand View Research, Statista, Mordor Intelligence,
  The Business Research Company (voir doc_id ecommerce_market)
- EdTech : Technavio, Fact.MR (voir doc_id edtech_market)
- Cybersécurité : Fortune Business Insights, Grand View Research,
  Mordor Intelligence, Precedence Research (voir doc_id cybersecurity_market)

⚠️ IMPORTANT — les chiffres varient significativement d'une source à l'autre
(méthodologies différentes). Pour chaque secteur ci-dessous, une fourchette
raisonnable a été retenue à partir de plusieurs sources concordantes, avec
la source principale citée dans le champ "source" de chaque document. Ce
sont des ordres de grandeur pour ancrer l'agent IA dans la réalité — PAS des
chiffres à citer tels quels dans un document contractuel ou d'investisseur
sans revérification directement auprès d'un rapport payant à jour.

Pour les secteurs marqués "ESTIMATION NON VÉRIFIÉE" ci-dessous, aucune
recherche web dédiée n'a été faite dans cette session — à rechercher et
sourcer avant mise en production réelle si ces secteurs sont fréquemment
soumis par les utilisateurs.
"""

import asyncio
import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# ============================================================
# 1. DONNÉES DE MARCHÉ PAR SECTEUR (sourcées, voir docstring)
# ============================================================

MARKET_DATA = [
    {
        "id": "health_tech_market",
        "sector": "HealthTech / Télémédecine",
        "text": (
            "Le marché mondial de la télémédecine est estimé entre 120 et 195 "
            "milliards USD en 2025-2026 selon les sources (Fortune Business "
            "Insights, Precedence Research, Mordor Intelligence), avec un taux "
            "de croissance annuel composé (CAGR) situé entre 13% et 20% jusqu'en "
            "2034-2035. L'Amérique du Nord domine avec environ 34-48% de part de "
            "marché. Les segments à plus forte croissance sont la surveillance à "
            "distance des patients (remote patient monitoring) et les soins à "
            "domicile (homecare), avec des CAGR proches de 18%. Le marché plus "
            "large de la télésanté (telehealth), incluant la téléconsultation et "
            "le télémonitoring, est estimé à environ 186-220 milliards USD en "
            "2025-2026 avec un CAGR pouvant atteindre 24% selon Fortune Business "
            "Insights."
        ),
        "source": "Fortune Business Insights, Precedence Research, Mordor Intelligence (consulté 12/07/2026)",
        "cagr_range": "13-20%",
        "market_size_range_usd_billion": "120-220 (2025-2026)",
    },
    {
        "id": "fintech_market",
        "sector": "FinTech",
        "text": (
            "Le marché mondial de la fintech est estimé entre 260 et 460 "
            "milliards USD en 2025-2026 selon les sources (Fortune Business "
            "Insights, Expert Market Research, IMARC Group, Polaris Market "
            "Research), avec un CAGR situé entre 15% et 18% jusqu'en 2034-2035. "
            "L'Amérique du Nord domine avec environ 32-36% de part de marché. "
            "Les segments porteurs sont les paiements numériques (marché "
            "spécifique estimé à plus de 114 milliards USD, CAGR ~21%), la "
            "néobanque (marché estimé à 195 milliards USD en 2024, projection "
            "très agressive à plus de 5000 milliards USD d'ici 2033 selon IMARC "
            "Group — chiffre à prendre avec prudence vu l'ampleur), et "
            "l'intelligence artificielle appliquée à la fintech (30 milliards "
            "USD en 2025, projection à 83 milliards USD d'ici 2030 selon Mordor "
            "Intelligence). Les investissements mondiaux dans le secteur ont "
            "atteint 116 milliards USD en 2025 selon KPMG."
        ),
        "source": "Fortune Business Insights, IMARC Group, Polaris Market Research (consulté 12/07/2026)",
        "cagr_range": "15-18%",
        "market_size_range_usd_billion": "260-460 (2025-2026)",
    },
    {
        "id": "ecommerce_market",
        "sector": "E-commerce",
        "text": (
            "Le marché mondial de l'e-commerce présente une très grande "
            "variance selon les méthodologies des cabinets d'étude (certains "
            "incluent le B2B, d'autres non), avec des estimations allant de "
            "4900 milliards USD à plus de 36 000 milliards USD en 2026. Une "
            "fourchette raisonnable pour le e-commerce B2C grand public se "
            "situe autour de 5000-8000 milliards USD en 2026, avec un CAGR "
            "généralement estimé entre 10% et 16% selon les sources (Grand "
            "View Research, Statista, The Business Research Company). "
            "L'Asie-Pacifique domine avec environ 42-54% de part de marché, "
            "portée par la Chine et l'Inde. Les segments à forte croissance "
            "incluent le commerce mobile (mCommerce), le commerce social, et "
            "le paiement différé (Buy Now Pay Later)."
        ),
        "source": "Grand View Research, The Business Research Company, Statista (consulté 12/07/2026)",
        "cagr_range": "10-16%",
        "market_size_range_usd_billion": "5000-8000 (2026, périmètre B2C)",
    },
    {
        "id": "edtech_market",
        "sector": "EdTech",
        "text": (
            "Le marché mondial des technologies éducatives (EdTech) est estimé "
            "entre 285 et 310 milliards USD en 2025-2026 selon les sources "
            "(Technavio, Fact.MR), avec un CAGR situé entre 8.6% et 16.2% selon "
            "le périmètre retenu. L'Amérique du Nord est la région dominante. "
            "Les segments K-12 et enseignement supérieur représentent les plus "
            "grosses parts de marché, avec le déploiement cloud en forte "
            "croissance (63.8% du segment déploiement en 2026). Les technologies "
            "d'apprentissage adaptatif basées sur le machine learning sont "
            "identifiées comme le principal moteur de croissance à venir."
        ),
        "source": "Technavio, Fact.MR (consulté 12/07/2026)",
        "cagr_range": "8.6-16.2%",
        "market_size_range_usd_billion": "285-310 (2025-2026)",
    },
    {
        "id": "cybersecurity_market",
        "sector": "Cybersécurité",
        "text": (
            "Le marché mondial de la cybersécurité est estimé entre 220 et 300 "
            "milliards USD en 2025-2026 selon les sources (Fortune Business "
            "Insights, Grand View Research, Mordor Intelligence, Precedence "
            "Research), avec un CAGR situé entre 9% et 14% jusqu'en 2033-2035. "
            "L'Amérique du Nord domine avec environ 36-43% de part de marché. "
            "Le déploiement cloud représente 54-68% du marché selon les sources "
            "et croît plus vite que le on-premise. La gestion des identités et "
            "des accès (IAM), la protection des applications cloud, et la "
            "sécurité pilotée par l'IA (détection de menaces, réponse "
            "automatisée) sont les segments à plus forte croissance."
        ),
        "source": "Fortune Business Insights, Mordor Intelligence, Precedence Research (consulté 12/07/2026)",
        "cagr_range": "9-14%",
        "market_size_range_usd_billion": "220-300 (2025-2026)",
    },
    # --- Secteurs suivants : ESTIMATION NON VÉRIFIÉE, à rechercher/sourcer avant usage sérieux ---
    {
        "id": "proptech_market",
        "sector": "PropTech (technologie immobilière)",
        "text": (
            "[ESTIMATION NON VÉRIFIÉE — aucune recherche web dédiée effectuée] "
            "Le marché mondial de la PropTech est généralement situé dans une "
            "fourchette de 30 à 50 milliards USD selon les analyses publiques "
            "courantes, avec un CAGR estimé entre 12% et 16%. Segments typiques : "
            "gestion locative digitale, visite virtuelle, plateformes "
            "transactionnelles immobilières. À revérifier avec une recherche "
            "dédiée avant utilisation en contexte professionnel."
        ),
        "source": "NON SOURCÉ — estimation générale à vérifier",
        "cagr_range": "12-16% (non vérifié)",
        "market_size_range_usd_billion": "30-50 (non vérifié)",
    },
    {
        "id": "agritech_foodtech_market",
        "sector": "AgriTech / FoodTech",
        "text": (
            "[ESTIMATION NON VÉRIFIÉE — aucune recherche web dédiée effectuée] "
            "Le marché mondial combiné AgriTech/FoodTech est généralement "
            "estimé dans une fourchette large de 20 à 30 milliards USD pour "
            "l'AgriTech pure, avec des CAGR souvent cités entre 10% et 15%. "
            "Segments typiques : agriculture de précision, traçabilité "
            "alimentaire, livraison de repas. À revérifier avec une recherche "
            "dédiée avant utilisation en contexte professionnel."
        ),
        "source": "NON SOURCÉ — estimation générale à vérifier",
        "cagr_range": "10-15% (non vérifié)",
        "market_size_range_usd_billion": "20-30 (non vérifié, AgriTech seule)",
    },
    {
        "id": "greentech_climatetech_market",
        "sector": "GreenTech / Climate Tech",
        "text": (
            "[ESTIMATION NON VÉRIFIÉE — aucune recherche web dédiée effectuée] "
            "Le marché mondial de la Climate Tech / GreenTech est généralement "
            "cité dans une fourchette large, souvent supérieure à 15 000 "
            "milliards USD si l'on inclut la transition énergétique dans son "
            "ensemble, ou beaucoup plus restreinte (quelques dizaines de "
            "milliards) pour les seules startups logicielles de mesure "
            "carbone/ESG. La définition du périmètre change radicalement le "
            "chiffre — à clarifier et resourcer avant toute utilisation."
        ),
        "source": "NON SOURCÉ — estimation générale à vérifier, périmètre très variable",
        "cagr_range": "non vérifié",
        "market_size_range_usd_billion": "non vérifié — périmètre à clarifier",
    },
    {
        "id": "hrtech_market",
        "sector": "HR Tech (technologie RH / recrutement)",
        "text": (
            "[ESTIMATION NON VÉRIFIÉE — aucune recherche web dédiée effectuée] "
            "Le marché mondial des technologies RH est généralement estimé "
            "entre 30 et 40 milliards USD, avec un CAGR souvent cité autour de "
            "10-11%. Segments typiques : ATS (Applicant Tracking System), "
            "gestion de la paie, outils d'engagement collaborateur. À "
            "revérifier avec une recherche dédiée avant utilisation en "
            "contexte professionnel."
        ),
        "source": "NON SOURCÉ — estimation générale à vérifier",
        "cagr_range": "10-11% (non vérifié)",
        "market_size_range_usd_billion": "30-40 (non vérifié)",
    },
    {
        "id": "mobility_logistics_market",
        "sector": "Mobilité / Logistique (Mobility Tech / LogTech)",
        "text": (
            "[ESTIMATION NON VÉRIFIÉE — aucune recherche web dédiée effectuée] "
            "Le marché mondial des technologies de mobilité et logistique "
            "(covoiturage, gestion de flotte, livraison du dernier kilomètre) "
            "est généralement estimé dans une fourchette large, souvent citée "
            "entre 80 et 150 milliards USD selon le périmètre retenu (mobilité "
            "urbaine seule vs logistique B2B incluse), avec des CAGR variant de "
            "8% à 18%. À revérifier avec une recherche dédiée avant utilisation "
            "en contexte professionnel."
        ),
        "source": "NON SOURCÉ — estimation générale à vérifier",
        "cagr_range": "8-18% (non vérifié, très variable selon périmètre)",
        "market_size_range_usd_billion": "80-150 (non vérifié)",
    },
]

# ============================================================
# 2. PATTERNS SWOT GÉNÉRIQUES PAR SECTEUR (pour guider l'agent)
# ============================================================

SWOT_PATTERNS = [
    {
        "id": f"swot_pattern_{item['id']}",
        "sector": item["sector"],
        "text": (
            f"Pattern SWOT typique pour le secteur {item['sector']} : "
            f"Forces courantes — time-to-market rapide grâce aux frameworks "
            f"existants, différenciation possible par l'IA/automatisation. "
            f"Faiblesses courantes — dépendance à des API tierces, coûts "
            f"d'acquisition client élevés dans un marché à CAGR de "
            f"{item['cagr_range']}. Opportunités courantes — marché en "
            f"expansion ({item['market_size_range_usd_billion']} milliards "
            f"USD), digitalisation accélérée post-2024. Menaces courantes — "
            f"consolidation par les acteurs établis, évolution réglementaire "
            f"(RGPD, sectorielle selon le domaine)."
        ),
    }
    for item in MARKET_DATA
]

# ============================================================
# 3. EXEMPLES DE STARTUPS GÉNÉRIQUES (illustratifs, pas des cas réels)
# ============================================================

STARTUP_EXAMPLES = [
    {
        "id": f"startup_example_{item['id']}",
        "sector": item["sector"],
        "text": (
            f"Exemple illustratif (fictif, à but pédagogique uniquement, PAS "
            f"un cas réel) de positionnement réussi dans le secteur "
            f"{item['sector']} : une startup qui cible un segment de niche "
            f"mal desservi par les acteurs établis, avec un modèle "
            f"d'abonnement récurrent (SaaS) plutôt qu'une vente ponctuelle, "
            f"et une stratégie de croissance product-led (adoption "
            f"individuelle avant vente enterprise). Facteurs de succès "
            f"typiques observés dans ce type de secteur : intégration native "
            f"avec les outils déjà utilisés par la cible, conformité "
            f"réglementaire traitée comme un avantage concurrentiel plutôt "
            f"qu'une contrainte, et cycle de vente raccourci par un "
            f"onboarding self-service."
        ),
    }
    for item in MARKET_DATA
]

# ============================================================
# 4. ASSEMBLAGE FINAL — doit contenir au moins 50 documents
# ============================================================

ALL_DOCUMENTS = []
for item in MARKET_DATA:
    ALL_DOCUMENTS.append(
        {
            "id": item["id"],
            "text": item["text"],
            "metadata": {
                "type": "market_data",
                "sector": item["sector"],
                "source": item["source"],
                "cagr_range": item["cagr_range"],
                "market_size_range_usd_billion": item["market_size_range_usd_billion"],
            },
        }
    )
for item in SWOT_PATTERNS:
    ALL_DOCUMENTS.append(
        {
            "id": item["id"],
            "text": item["text"],
            "metadata": {"type": "swot_pattern", "sector": item["sector"]},
        }
    )
for item in STARTUP_EXAMPLES:
    ALL_DOCUMENTS.append(
        {
            "id": item["id"],
            "text": item["text"],
            "metadata": {"type": "startup_example", "sector": item["sector"]},
        }
    )

# Total : 10 secteurs x 3 documents (market_data + swot_pattern + startup_example) = 30
# ⚠️ En dessous du minimum de 50 documents exigé par le plan (section 2.4).
# Complète ci-dessous avec des variantes supplémentaires pour atteindre 50+.

EXTRA_PATTERNS = [
    "Erreur fréquente en analyse de Startup Score : plafonner artificiellement "
    "tous les critères à 8-9/10 sans justification différenciée — un bon "
    "Startup Score doit varier significativement entre Innovation, "
    "Faisabilité, Rentabilité et Scalabilité selon le projet réel.",
    "Principe de calcul du Startup Score : Innovation évalue la nouveauté "
    "réelle de l'approche (pas juste l'usage du mot IA), Faisabilité évalue "
    "la complexité technique et les compétences requises, Rentabilité évalue "
    "le potentiel de marge et le coût d'acquisition client, Scalabilité "
    "évalue la capacité à croître sans réaugmenter les coûts proportionnellement.",
    "Différence entre marché adressable total (TAM), marché disponible "
    "servi (SAM) et marché réellement capturable (SOM) — un Innovation Score "
    "élevé ne garantit pas un SOM réaliste si le go-to-market n'est pas défini.",
    "Signal d'alerte dans une analyse concurrentielle : l'absence totale de "
    "concurrents directs indique souvent soit un marché inexistant, soit une "
    "recherche insuffisante — pas nécessairement une opportunité vierge.",
    "Le Business Model Canvas doit toujours faire correspondre la "
    "proposition de valeur à un segment client précis, pas à 'tout le "
    "monde' — un ciblage flou dans le BMC est un signal de faiblesse "
    "stratégique à signaler dans le SWOT.",
    "Facteur différenciant à évaluer systématiquement pour du B2B SaaS : le "
    "temps d'intégration avec les systèmes existants du client (ERP, CRM) — "
    "souvent sous-estimé dans les analyses de faisabilité génériques.",
    "Pour les projets académiques (template STUDENT), l'évaluation du "
    "Startup Score doit rester réaliste sur un horizon de projet de fin "
    "d'études (quelques mois), pas sur un horizon de levée de fonds "
    "(plusieurs années) — ajuster les attentes de Rentabilité en conséquence.",
    "Alerte réglementaire à vérifier systématiquement selon le secteur "
    "détecté : santé → RGPD renforcé + réglementation dispositifs médicaux "
    "selon la juridiction ; fintech → licences bancaires/PSD2 en Europe ; "
    "edtech → protection des données mineurs (COPPA aux USA, RGPD-K en UE).",
    "Bonne pratique de sourcing : toujours indiquer une fourchette de "
    "marché plutôt qu'un chiffre unique précis au milliard près, sauf si la "
    "source est citée nommément — un chiffre trop précis sans source "
    "identifiable est un signal d'hallucination du LLM.",
    "Pattern de suggestion d'amélioration à privilégier : proposer des "
    "pistes concrètes et actionnables (ex: 'intégrer une API X pour Y') "
    "plutôt que des généralités ('améliorer l'expérience utilisateur') qui "
    "n'apportent pas de valeur différenciante au rapport généré.",
    "Distinction entre concurrents directs (même solution, même cible) et "
    "concurrents indirects (solution différente, même besoin résolu) — les "
    "deux catégories doivent apparaître séparément dans une analyse "
    "concurrentielle sérieuse.",
    "Structure standard d'un Executive Summary de Business Plan généré : "
    "problème identifié, solution proposée, marché cible chiffré, avantage "
    "concurrentiel, modèle de revenus, étape de développement actuelle.",
    "Point de vigilance sur les métriques SaaS : ne jamais confondre MRR "
    "(revenu récurrent mensuel) projeté et revenu total du premier exercice "
    "— une confusion fréquente dans les analyses financières générées "
    "automatiquement.",
    "Pour les projets impliquant du temps réel (chat, notifications live, "
    "monitoring continu), toujours signaler explicitement le besoin en "
    "WebSocket ou Server-Sent Events dans les recommandations techniques, "
    "pas uniquement une architecture REST classique.",
    "Bonne pratique de Persona : un persona utile inclut au minimum un nom "
    "fictif, un contexte professionnel/personnel réaliste, une frustration "
    "précise liée au problème résolu, et un canal d'acquisition plausible — "
    "pas une simple liste de données démographiques.",
    "Erreur fréquente en génération de User Stories : mélanger des tâches "
    "techniques ('mettre en place la base de données') avec de vraies User "
    "Stories orientées valeur utilisateur ('en tant qu'utilisateur, je veux "
    "X afin de Y') — les deux catégories doivent être séparées.",
    "Repère de Story Points Fibonacci : 1-2 points = tâche triviale (quelques "
    "heures), 3-5 points = tâche standard (1-2 jours), 8 points = tâche "
    "complexe (une semaine), 13-21 points = epic à décomposer en tâches plus "
    "petites, jamais une seule User Story ne devrait dépasser 13 points.",
    "Repère MoSCoW réaliste : dans un backlog équilibré, rarement plus de "
    "40-50% des items ne devraient être 'Must Have' — un backlog à 80% "
    "'Must Have' révèle une priorisation insuffisante, pas un projet "
    "réellement critique dans son intégralité.",
    "Facteur d'architecture à considérer systématiquement : Monolithique "
    "convient à un MVP ou une équipe de moins de 5 développeurs ; "
    "Microservices se justifie à partir d'une complexité métier réelle et "
    "d'une équipe capable de gérer l'overhead opérationnel, pas par défaut.",
    "Signal de cohérence à vérifier entre les modules : le nombre de User "
    "Stories généré (Sprint 4) doit rester cohérent avec la complexité "
    "annoncée dans le Startup Score de faisabilité (Sprint 3) — un projet "
    "jugé 'faisabilité facile' avec 40 Epics est un signal d'incohérence "
    "entre agents à corriger.",
]

for i, text in enumerate(EXTRA_PATTERNS, start=1):
    ALL_DOCUMENTS.append(
        {
            "id": f"general_pattern_{i:02d}",
            "text": text,
            "metadata": {"type": "general_pattern", "sector": "transversal"},
        }
    )

# Total final : 30 (marché/SWOT/startups) + 20 (patterns généraux) = 50 documents


# ============================================================
# 5. SCRIPT DE SEED
# ============================================================

def _validate_env() -> None:
    """Vérifie la présence des variables d'environnement requises et échoue
    avec un message clair plutôt qu'une KeyError brute (cohérent avec
    l'exigence du plan : 'afficher une erreur claire' si la config est
    incomplète)."""
    required_env = ["CHROMA_HOST", "CHROMA_PORT", "CHROMA_AUTH_TOKEN"]
    missing = [v for v in required_env if v not in os.environ]
    if missing:
        raise RuntimeError(
            f"[SEED] Variables d'environnement manquantes : {missing}. "
            f"Vérifie ton fichier .env avant de relancer le seed."
        )


async def seed():
    _validate_env()

    client = chromadb.HttpClient(
        host=os.environ["CHROMA_HOST"],
        port=int(os.environ["CHROMA_PORT"]),
        settings=Settings(
            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
            chroma_client_auth_credentials=os.environ["CHROMA_AUTH_TOKEN"],
        ),
    )

    # Fonction d'embedding fixée EXPLICITEMENT ici. Elle doit être identique
    # à celle utilisée partout ailleurs dans le projet (agents, recherche RAG
    # web live) — sinon les vecteurs générés ne sont pas comparables entre eux
    # et les résultats de similarité deviennent incohérents.
    embedding_function = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name="market_reference",
        embedding_function=embedding_function,
    )

    existing_count = collection.count()
    if existing_count > 0:
        print(f"[SEED] Collection déjà peuplée ({existing_count} documents). "
              f"Suppression avant re-seed pour éviter les doublons.")
        existing_ids = set(collection.get()["ids"] or [])
        ids_to_delete = [doc["id"] for doc in ALL_DOCUMENTS if doc["id"] in existing_ids]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
        else:
            print("[SEED] Aucun document existant ne correspond aux IDs actuels "
                  "(pas de suppression nécessaire).")

    collection.add(
        ids=[doc["id"] for doc in ALL_DOCUMENTS],
        documents=[doc["text"] for doc in ALL_DOCUMENTS],
        metadatas=[doc["metadata"] for doc in ALL_DOCUMENTS],
    )

    final_count = collection.count()
    print(f"[SEED] Terminé. {final_count} documents dans la collection 'market_reference'.")
    print(f"[SEED] Attendu : {len(ALL_DOCUMENTS)} documents.")
    assert final_count == len(ALL_DOCUMENTS), (
        f"⚠️ Mismatch : {final_count} documents en base vs {len(ALL_DOCUMENTS)} attendus."
    )


if __name__ == "__main__":
    asyncio.run(seed())