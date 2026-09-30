# ForgeAI

ForgeAI transforme une idée de projet ou de startup en dossier complet : étude de marché,
concurrence, SWOT, Business Model Canvas, estimation financière, personas, score et verdict,
plan produit (backlog, sprints), architecture de la solution, et exports PDF, Word et PowerPoint.
Des agents d'IA proposent, des règles déterministes valident et décident, l'interface affiche.

Le projet comprend deux espaces :

- **l'espace utilisateur** : inscription, projets, analyses, rapports, exports ;
- **la console d'administration** : utilisateurs, projets, analyses (diagnostic, relance),
  erreurs, santé du système, journal d'audit. Elle est protégée par une double authentification (2FA).

## Architecture

| Service | Rôle | Adresse sur votre machine |
|---|---|---|
| `frontend` (Next.js, lancé avec npm) | espace utilisateur + console admin | http://localhost:3000 |
| `backend` (FastAPI) | API publique, exécute les analyses | http://localhost:8000 (documentation : `/docs`) |
| `backend-admin` (FastAPI) | API admin séparée | http://127.0.0.1:8002 (jamais exposée au réseau) |
| `postgres` | base de données | port 5432 |
| `redis` | limites de connexion, cache | port 6379 |
| `chromadb` | base vectorielle | port 8001 |

Le backend, l'API admin, PostgreSQL, Redis et ChromaDB tournent dans Docker.
Le frontend se lance à part avec npm.

## Prérequis

- **Git**
- **Docker Desktop**, avec Docker Compose v2 (commande `docker compose`)
- **Node.js 20.9 ou plus récent** (pour le frontend)
- **Python 3.10 ou plus récent**, uniquement pour le script qui prépare la configuration
- Une clé d'API **Gemini** (https://aistudio.google.com/apikey) et/ou **Groq**
  (https://console.groq.com/keys). Les deux sont gratuites ; au moins une est nécessaire pour lancer une analyse.

## Installation

Les commandes sont les mêmes sous Windows (PowerShell), macOS et Linux.

### 1. Cloner le dépôt

```
git clone https://github.com/Abd-Elmouhib-Souri/ForgeAI.git
cd ForgeAI
```

### 2. Préparer la configuration

```
python scripts/init_env.py
```

Le script crée `.env` et `frontend/.env.local` à partir des modèles. Il génère au hasard tous les
secrets internes (JWT, session, clé de chiffrement 2FA, mot de passe PostgreSQL, jeton ChromaDB),
puis affiche la liste des clés d'API qu'il vous reste à fournir. Il n'écrase jamais un `.env` existant.

Ouvrez ensuite `.env` et collez vos clés :

| Clé | Nécessaire ? |
|---|---|
| `GEMINI_API_KEY` et/ou `GROQ_API_KEY` | **oui, au moins une** (analyses) |
| `TAVILY_API_KEY` | recommandée (recherche de sources). Sans clé, mettez `ENABLE_TAVILY_SEARCH=false` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | facultatives (bouton « Continuer avec Google ») |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | facultatives (voir « E-mails » plus bas) |

`.env` est ignoré par git : ne le committez jamais et ne le partagez pas.

### 3. Démarrer les services

```
docker compose up -d --build
```

La première construction prend plusieurs minutes (installation des dépendances Python).

### 4. Créer les tables

```
docker compose exec backend alembic upgrade head
```

À relancer après chaque mise à jour du code qui ajoute une migration. La page
« Santé du système » signale une base en retard.

### 5. Créer le premier administrateur

```
docker compose exec backend python -m app.scripts.create_admin
```

Répondez aux questions : e-mail, nom, mot de passe (au moins 12 caractères, saisi deux fois).
Si l'e-mail appartient déjà à un compte, celui-ci devient administrateur. Seule une personne qui
contrôle le serveur peut lancer cette commande, et l'opération est inscrite au journal d'audit.

### 6. Lancer le frontend

```
cd frontend
npm ci
npm run dev
```

## Premiers pas

**Console d'administration** : http://localhost:3000/admin/login

À la première connexion, la console affiche un QR code. Scannez-le avec une application
d'authentification (Google Authenticator, Microsoft Authenticator…), puis saisissez le code à 6 chiffres.
Ce code est ensuite demandé à chaque connexion et avant chaque action sensible.

Ouvrez ensuite **Santé du système** : chaque service y est testé pour de vrai. On y voit
la base, les migrations, Redis, ChromaDB, l'API publique et les modèles Gemini/Groq configurés.
Tout doit être « Opérationnel », sauf les services facultatifs que vous n'avez pas configurés.

**Espace utilisateur** : http://localhost:3000

1. Créez un compte sur http://localhost:3000/register.
2. Vérifiez l'adresse e-mail avec le lien reçu (voir « E-mails » ci-dessous si SMTP n'est pas configuré).
3. Connectez-vous, créez un projet, lancez l'analyse et suivez sa progression.

## E-mails

Avec SMTP configuré dans `.env` (par exemple un mot de passe d'application Gmail), les e-mails
de vérification et de mot de passe oublié sont envoyés normalement.

**Sans SMTP, en développement** (`ENVIRONMENT=development`), aucun e-mail ne part : son contenu,
lien compris, est écrit dans le journal du backend. Pour le retrouver :

```
docker compose logs backend
```

Cherchez « SMTP non configuré » et ouvrez le lien dans votre navigateur. En production, ce repli
est désactivé : l'envoi échoue et l'échec est journalisé.

## Tests

```
docker compose exec backend python -m pip install -r requirements-dev.txt
docker compose exec backend python -m pytest -q
cd frontend
node --test "tests/*.test.mjs"
```

## Arrêter, redémarrer, réinitialiser

```
docker compose stop            # arrêter (les données sont conservées)
docker compose up -d           # redémarrer
docker compose down -v         # tout supprimer, base comprise (irréversible)
```

## Dépannage

- **Un port est déjà pris** (5432, 6379, 8000, 8001, 8002, 3000) : arrêtez le programme qui l'occupe.
  Pour l'API admin, vous pouvez aussi changer `ADMIN_API_PORT` dans `.env`, et
  `NEXT_PUBLIC_ADMIN_API_URL` dans `frontend/.env.local`.
- **Le backend redémarre en boucle** : `docker compose logs backend`. Une variable obligatoire
  manque souvent dans `.env` ; relancez `python scripts/init_env.py` sur un dépôt sans `.env`.
- **« Analyse échouée » immédiatement** : clé d'IA absente, invalide ou quota atteint.
  La page Santé du système indique laquelle, ainsi que les modèles introuvables.
- **Le bouton « Continuer avec Google » échoue** : c'est normal sans `GOOGLE_CLIENT_ID` /
  `GOOGLE_CLIENT_SECRET`. Utilisez l'inscription par e-mail.

## Sécurité

- Ne committez jamais `.env` ni `frontend/.env.local` (ils sont ignorés par git).
- L'API admin n'écoute que sur `127.0.0.1`. En production, elle se place derrière un VPN.
- Changez toutes les clés d'API avant une mise en production.
