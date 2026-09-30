# ForgeAI

ForgeAI transforme une idée de projet ou de startup en dossier complet et argumenté :
étude de marché, concurrence, SWOT, Business Model Canvas, estimation financière, personas,
vérification des faits, score et verdict, plan produit (backlog, sprints), architecture de la
solution (stack, base de données, diagrammes UML), puis exports PDF, Word et PowerPoint.

Principe : **les agents d'IA proposent, des règles déterministes valident et décident, l'interface affiche.**
Une analyse ne démarre que si le contexte du projet est assez clair ; sinon, ForgeAI pose d'abord des questions.

Ce guide explique, pas à pas, comment installer ForgeAI sur votre machine à partir du dépôt,
obtenir toutes les clés d'API utilisées, puis accéder à la plateforme en tant qu'**utilisateur**
et en tant qu'**administrateur**.

---

## Sommaire

1. [Ce que contient la plateforme](#1-ce-que-contient-la-plateforme)
2. [Prérequis](#2-prérequis)
3. [Cloner le dépôt](#3-cloner-le-dépôt)
4. [Obtenir les clés d'API](#4-obtenir-les-clés-dapi)
5. [Installer et démarrer](#5-installer-et-démarrer)
6. [Accéder à la plateforme en tant qu'utilisateur](#6-accéder-à-la-plateforme-en-tant-quutilisateur)
7. [Accéder à la console d'administration](#7-accéder-à-la-console-dadministration)
8. [Utilisation au quotidien](#8-utilisation-au-quotidien)
9. [Tests](#9-tests)
10. [Dépannage](#10-dépannage)
11. [Sécurité](#11-sécurité)

---

## 1. Ce que contient la plateforme

**Espace utilisateur** (entrepreneurs, étudiants, consultants) :
inscription par e-mail ou avec Google, création de projets, questions de clarification,
analyse complète par des agents d'IA, rapport, plan produit, architecture et exports.

**Console d'administration** : tableau de bord, utilisateurs, projets, analyses (diagnostic
lisible étape par étape, relance), erreurs, santé du système (chaque service testé pour de vrai)
et journal d'audit inaltérable. Elle a sa propre API, n'écoute que sur la machine locale
et exige une double authentification (2FA).

| Service | Rôle | Adresse sur votre machine |
|---|---|---|
| `frontend` (Next.js, lancé avec npm) | espace utilisateur + console admin | http://localhost:3000 |
| `backend` (FastAPI) | API publique, exécute les analyses | http://localhost:8000 (documentation : http://localhost:8000/docs) |
| `backend-admin` (FastAPI) | API de la console admin | http://127.0.0.1:8002 (jamais exposée au réseau) |
| `postgres` | base de données | port 5432 |
| `redis` | limites de tentatives de connexion, cache | port 6379 |
| `chromadb` | base vectorielle | port 8001 |

Le backend, l'API admin, PostgreSQL, Redis et ChromaDB tournent dans **Docker**.
Le frontend se lance à part avec **npm**.

---

## 2. Prérequis

| Outil | Version | Téléchargement | Vérification |
|---|---|---|---|
| Git | récente | https://git-scm.com/downloads | `git --version` |
| Docker Desktop (avec Docker Compose v2) | récente | https://www.docker.com/products/docker-desktop/ | `docker compose version` |
| Node.js | **20.9 ou plus** (LTS conseillée) | https://nodejs.org/ | `node --version` |
| Python | 3.10 ou plus | https://www.python.org/downloads/ | `python --version` |

- **Windows** : Docker Desktop utilise WSL 2 ; acceptez son installation au premier lancement,
  puis **démarrez Docker Desktop** avant toute commande `docker`.
- Python ne sert qu'au script qui prépare la configuration (étape 5.1). Aucun paquet à installer.
- Prévoyez environ **10 Go** libres (images Docker et dépendances).

---

## 3. Cloner le dépôt

Le dépôt est **privé**. Il faut d'abord y être invité :

1. Créez un compte GitHub si besoin : https://github.com/signup
2. Donnez votre identifiant GitHub au propriétaire du dépôt, qui vous invite
   (Settings → Collaborators → Add people).
3. Acceptez l'invitation reçue par e-mail, ou sur https://github.com/notifications

Clonez ensuite le dépôt (branche `main`) :

```
git clone https://github.com/Abd-Elmouhib-Souri/ForgeAI.git
cd ForgeAI
```

Git vous demande de vous connecter à GitHub la première fois (une fenêtre de navigateur s'ouvre
sous Windows). Si un mot de passe est demandé en ligne de commande, utilisez un
*personal access token* et non votre mot de passe GitHub : https://github.com/settings/tokens

> Clonez dans un dossier **sans espaces ni accents** dans le chemin (par exemple `C:\projets\ForgeAI`).

---

## 4. Obtenir les clés d'API

ForgeAI utilise des services externes. Chacun a une offre gratuite suffisante pour tester.
**Chaque personne qui installe ForgeAI crée ses propres clés** : ne réutilisez pas celles de quelqu'un d'autre.

| Clé dans `.env` | Service | Obligatoire ? | À quoi elle sert |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini | **au moins une des deux** | agents d'IA de l'analyse |
| `GROQ_API_KEY` | Groq | **au moins une des deux** | agents d'IA (relais si Gemini est indisponible ou à court de quota) |
| `TAVILY_API_KEY` | Tavily | recommandée | recherche web des sources (concurrents, marché) |
| `GEMINI_SEARCH_CLASSIFIER_API_KEY` | Google Gemini | facultative | classement des sources trouvées |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud (OAuth) | facultatives | bouton « Continuer avec Google » |
| `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | Gmail (ou autre SMTP) | facultatives | envoi des e-mails (vérification, mot de passe oublié) |

Avoir **les deux** clés d'IA est conseillé : si l'une atteint sa limite gratuite, l'autre prend le relais.

Les secrets **internes** (JWT, session, clé de chiffrement 2FA, mot de passe PostgreSQL,
jeton ChromaDB) ne sont pas à créer : le script de l'étape 5.1 les génère.

Le rendu des diagrammes UML utilise le service public Kroki (https://kroki.io) : aucune clé
n'est nécessaire. Le texte des diagrammes lui est envoyé ; pour un usage confidentiel,
Kroki peut être installé localement et désigné par `KROKI_BASE_URL`.

### 4.1 Google Gemini (`GEMINI_API_KEY`)

1. Ouvrez https://aistudio.google.com/apikey et connectez-vous avec un compte Google.
2. Acceptez les conditions de Google AI Studio si elles s'affichent.
3. Cliquez sur **Create API key** (Créer une clé API), puis choisissez ou créez un projet Google Cloud.
4. Copiez la clé (elle commence par `AIza`).
5. Collez-la dans `.env` : `GEMINI_API_KEY=AIza...`
6. Facultatif : collez la même clé dans `GEMINI_SEARCH_CLASSIFIER_API_KEY` pour que Gemini classe aussi les sources.

L'offre gratuite a des limites par minute et par jour. Si les analyses échouent pour « quota »,
attendez le lendemain ou ajoutez la clé Groq.

### 4.2 Groq (`GROQ_API_KEY`)

1. Ouvrez https://console.groq.com et créez un compte (e-mail, Google ou GitHub).
2. Allez dans **API Keys** : https://console.groq.com/keys
3. Cliquez sur **Create API Key**, donnez-lui un nom (par exemple `ForgeAI`) et validez.
4. Copiez la clé **immédiatement** : elle ne sera plus affichée ensuite (elle commence par `gsk_`).
5. Collez-la dans `.env` : `GROQ_API_KEY=gsk_...`

### 4.3 Tavily, recherche web (`TAVILY_API_KEY`)

1. Ouvrez https://app.tavily.com et créez un compte.
2. Votre clé s'affiche sur le tableau de bord, section **API Keys** (elle commence par `tvly-`).
3. Collez-la dans `.env` : `TAVILY_API_KEY=tvly-...`

Sans clé Tavily, la recherche passe automatiquement par DuckDuckGo : l'analyse fonctionne,
mais avec moins de sources.

### 4.4 Connexion avec Google (facultatif)

Nécessaire seulement pour le bouton « Continuer avec Google ».

1. Ouvrez https://console.cloud.google.com et créez un projet (par exemple `ForgeAI`)
   avec le sélecteur de projet en haut de la page.
2. Configurez l'écran de consentement : https://console.cloud.google.com/apis/credentials/consent
   - type d'utilisateurs : **Externe** ;
   - nom de l'application : `ForgeAI`, e-mail d'assistance : le vôtre ;
   - dans **Utilisateurs de test** (Audience), ajoutez les adresses Gmail qui pourront se connecter
     tant que l'application est en mode test.
3. Créez les identifiants : https://console.cloud.google.com/apis/credentials
   - **Créer des identifiants** → **ID client OAuth** → type **Application Web** ;
   - **Origines JavaScript autorisées** : `http://localhost:3000`
   - **URI de redirection autorisés** : `http://localhost:8000/auth/google/callback`
     (exactement la valeur de `GOOGLE_REDIRECT_URI` dans `.env`).
4. Copiez l'**ID client** et le **Code secret du client** (il commence par `GOCSPX-`) :
   ```
   GOOGLE_CLIENT_ID=....apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-...
   ```

### 4.5 Envoi des e-mails avec Gmail (facultatif)

Sans SMTP, ForgeAI fonctionne quand même en développement : le contenu des e-mails,
lien compris, est écrit dans le journal du backend (voir 6.2). Pour recevoir de vrais e-mails :

1. Activez la **validation en deux étapes** de votre compte Google :
   https://myaccount.google.com/signinoptions/twosv
2. Créez un **mot de passe d'application** : https://myaccount.google.com/apppasswords
   - nom : `ForgeAI` → **Créer** ;
   - Google affiche 16 lettres (4 groupes de 4) : c'est la seule fois où il est visible.
3. Renseignez `.env` (sans espaces dans le mot de passe) :
   ```
   SMTP_USERNAME=votre.adresse@gmail.com
   SMTP_FROM_EMAIL=votre.adresse@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop
   ```
   N'utilisez **jamais** le mot de passe habituel de votre compte Google.

Autre fournisseur (Brevo, Mailgun, Outlook…) : remplacez aussi `SMTP_HOST` et `SMTP_PORT`
par les valeurs qu'il indique.

Les premiers e-mails arrivent souvent dans le dossier **Spam** : marquez-les « Non spam ».

---

## 5. Installer et démarrer

Toutes les commandes sont à lancer **depuis le dossier du dépôt** (`ForgeAI`).
Elles sont identiques sous Windows (PowerShell), macOS et Linux.

### 5.1 Préparer la configuration

```
python scripts/init_env.py
```

Le script crée deux fichiers à partir des modèles du dépôt :

- `.env` : configuration du backend, de l'API admin, de PostgreSQL et de ChromaDB ;
- `frontend/.env.local` : adresses des deux API pour le frontend.

Il génère au hasard tous les secrets internes, puis liste les clés d'API qu'il vous reste à fournir.
Il n'écrase jamais un `.env` existant : pour tout régénérer, supprimez d'abord `.env` et `frontend/.env.local`.

Ouvrez ensuite `.env` (par exemple `notepad .env` sous Windows) et collez vos clés
obtenues à l'étape 4. Enregistrez.

> Vérifiez que vous modifiez bien le `.env` **de ce dossier** : sa première ligne est
> `# ForgeAI : modèle de configuration`.

### 5.2 Démarrer les services

```
docker compose up -d --build
docker compose ps
```

La première fois, Docker télécharge les images et installe les dépendances Python :
comptez de 5 à 15 minutes. `docker compose ps` doit montrer 5 services « Up »,
PostgreSQL « healthy ».

### 5.3 Créer les tables de la base

```
docker compose exec backend alembic upgrade head
```

La dernière ligne doit mentionner `f4a2b6c8d013` (ou une version plus récente).
À relancer après chaque mise à jour du code (voir 8.3).

### 5.4 Créer le premier administrateur

```
docker compose exec backend python -m app.scripts.create_admin
```

Répondez aux questions :

- **e-mail** de l'administrateur (les majuscules sont ignorées) ;
- **nom complet** ;
- **mot de passe** : au moins **12 caractères**, saisi deux fois. **Rien ne s'affiche pendant la saisie**, c'est normal.

Le message `Compte … créé.` confirme la création. Si l'e-mail appartient déjà à un compte
(par exemple créé avec Google), ce compte devient administrateur.
Seule une personne qui contrôle le serveur peut lancer cette commande, et elle est inscrite au journal d'audit.

Si la saisie masquée ne fonctionne pas dans votre terminal, passez le mot de passe
par une variable (il restera dans l'historique du terminal : effacez-le ensuite avec `Clear-History` sous PowerShell) :

```
docker compose exec -e FORGEAI_ADMIN_PASSWORD="VotreMotDePasseLong" backend python -m app.scripts.create_admin --email vous@exemple.com --name "Prénom Nom"
```

### 5.5 Lancer le frontend

Dans un **nouveau terminal**, laissé ouvert tant que vous utilisez la plateforme :

```
cd frontend
npm ci
npm run dev
```

`npm ci` installe les dépendances (1 à 2 minutes, la première fois seulement).
La plateforme est prête quand le terminal affiche `Ready` et `http://localhost:3000`.

### 5.6 Vérifier que tout fonctionne

Connectez-vous à la console (section 7) et ouvrez **Santé du système**, puis cliquez sur « Tester maintenant ».
Chaque service y est réellement contacté :

- **Opérationnel** : PostgreSQL, Migrations de la base, File des analyses, API publique, Redis,
  ChromaDB, Espace disque, et Gemini et/ou Groq selon vos clés ;
- **Non configuré** : normal pour les services facultatifs que vous n'avez pas renseignés
  (Tavily, SMTP, connexion Google) ;
- **Hors service** ou **Dégradé** : le message de la carte dit quoi corriger
  (clé invalide, modèle introuvable, migrations en retard…).

---

## 6. Accéder à la plateforme en tant qu'utilisateur

Adresse : **http://localhost:3000**

### 6.1 Créer un compte

1. Ouvrez http://localhost:3000/register.
2. Renseignez votre nom, votre e-mail, votre profil (entrepreneur, étudiant ou consultant) et un mot de passe
   d'au moins 8 caractères.
3. Un e-mail de vérification est envoyé (voir 6.2). Tant que l'adresse n'est pas vérifiée, la connexion est refusée.

Avec la connexion Google configurée (4.4), le bouton **Continuer avec Google** crée et vérifie le compte directement.

### 6.2 Vérifier l'adresse e-mail

- **SMTP configuré** : ouvrez l'e-mail « Vérifiez votre adresse email — ForgeAI » (regardez aussi les Spam)
  et cliquez sur le lien.
- **Sans SMTP** : le lien est écrit dans le journal du backend. Affichez-le avec :
  ```
  docker compose logs backend
  ```
  Cherchez « SMTP non configuré », copiez le lien `http://localhost:3000/verify-email?token=…`
  et ouvrez-le dans le navigateur. Sous PowerShell, pour n'afficher que les liens :
  ```
  docker compose logs backend | Select-String "verify-email"
  ```
  Si vous avez demandé un nouvel e-mail, utilisez le **dernier** lien : les précédents ne sont plus valables.

La page affiche « Email vérifié avec succès ». Connectez-vous sur http://localhost:3000/login.

**Mot de passe oublié** : lien « Mot de passe oublié ? » sur la page de connexion. Le lien de
réinitialisation arrive par e-mail ou, sans SMTP, dans le journal du backend (même méthode).
Un compte créé avec Google peut ainsi se définir un mot de passe.

### 6.3 Créer un projet et lancer l'analyse

1. **Nouveau projet** : titre, secteur, pays ou région cible (facultatif), description.
   Plus la description est complète (problème, cible, solution, modèle économique, MVP,
   ce que vous voulez valider), moins ForgeAI posera de questions.
2. La **langue du rapport** suit le bouton FR / EN de l'interface.
3. Lancez l'analyse. Si le contexte n'est pas assez clair, ForgeAI affiche d'abord des
   **questions de clarification** : répondez-y, puis « Enregistrer et revérifier ».
4. La progression s'affiche en direct. Une analyse complète prend de quelques minutes à une vingtaine de minutes
   selon les quotas des fournisseurs d'IA.
5. Consultez ensuite le rapport, le plan produit et l'architecture, puis exportez en **PDF**, **Word** ou **PowerPoint**.

Exemple de description qui passe directement :

> Problème : chaque année, des milliers d'étudiants en Tunisie cherchent un stage obligatoire sans réponse,
> tandis que beaucoup de PME n'ont pas le temps de trier les candidatures. Cible : étudiants des écoles d'ingénieurs
> et PME de moins de 50 salariés. Solution : une plateforme web de mise en relation avec correspondance automatique
> par compétences et prise de rendez-vous. Modèle économique : gratuit pour les étudiants, abonnement mensuel
> pour les entreprises, licence annuelle pour les écoles. MVP : profils, offres, correspondance, messagerie.
> À valider : la volonté de payer des PME, la taille du marché et les concurrents.

---

## 7. Accéder à la console d'administration

Adresse : **http://localhost:3000/admin/login**

Les comptes administrateurs ne se créent pas par l'inscription publique : le premier se crée
avec la commande de l'étape 5.4, les suivants depuis la console (Utilisateurs → **Ajouter un admin**).

### 7.1 Première connexion : activer la double authentification

1. Installez une application d'authentification sur votre téléphone :
   Google Authenticator, Microsoft Authenticator, Authy…
2. Connectez-vous avec l'e-mail et le mot de passe de l'administrateur.
3. La console affiche un **QR code** (et la clé en texte, si vous ne pouvez pas scanner) :
   scannez-le avec l'application.
4. Saisissez le code à 6 chiffres affiché par l'application : la 2FA est activée
   et vous arrivez sur le tableau de bord.

### 7.2 Connexions suivantes

E-mail, mot de passe **et** code à 6 chiffres de l'application.

- La session admin dure **15 minutes** (compte à rebours en bas du menu), puis il faut se reconnecter.
- Chaque **action sensible** (changer un rôle, désactiver ou supprimer un compte, supprimer un projet,
  relancer une analyse…) redemande un code 2FA.
- Après 5 tentatives de connexion échouées, la connexion est bloquée 15 minutes.
- Toutes les connexions et actions admin sont inscrites au **journal d'audit**, qui ne peut être ni modifié ni supprimé.

### 7.3 Pages de la console

| Page | Contenu |
|---|---|
| Tableau de bord | chiffres clés de la plateforme |
| Utilisateurs | recherche, filtres, rôles, activation, renvoi de l'e-mail de vérification, ajout d'un admin, export CSV |
| Projets | tous les projets, recherche, suppression, export CSV |
| Analyses IA | suivi, relance, **diagnostic** (chaque étape, sources, preuves, erreurs, données brutes) |
| Erreurs | analyses en échec |
| Santé du système | test réel de chaque service et de chaque modèle d'IA configuré |
| Journal d'audit | qui a fait quoi, quand et depuis où ; export CSV |

---

## 8. Utilisation au quotidien

### 8.1 Arrêter et redémarrer

```
docker compose stop            # arrêter (les données sont conservées)
docker compose up -d           # redémarrer
```

Puis, dans un autre terminal : `cd frontend` et `npm run dev`.

### 8.2 Après une modification de `.env`

Les conteneurs ne lisent `.env` qu'à leur création : un simple `restart` ne suffit pas.

```
docker compose up -d --force-recreate backend backend-admin
```

Après une modification de `frontend/.env.local`, arrêtez `npm run dev` (Ctrl+C) et relancez-le.

### 8.3 Mettre à jour le code

```
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
cd frontend
npm ci
npm run dev
```

### 8.4 Tout réinitialiser

```
docker compose down -v
```

Supprime les conteneurs **et toutes les données** (comptes, projets, analyses). Irréversible.
Refaites ensuite les étapes 5.2 à 5.4.

---

## 9. Tests

Backend (dans le conteneur) :

```
docker compose exec backend python -m pip install -r requirements-dev.txt
docker compose exec backend python -m pytest -q
```

Frontend :

```
cd frontend
node --test "tests/*.test.mjs"
```

---

## 10. Dépannage

| Symptôme | Cause et solution |
|---|---|
| `docker` : commande introuvable, ou erreur de connexion au démon | Docker Desktop n'est pas démarré : lancez-le et attendez « Engine running ». |
| `Conflict. The container name "/forgeai_postgres" is already in use` | Une autre installation de ForgeAI existe sur la machine. Arrêtez-la (`docker compose stop` dans son dossier), puis supprimez ses conteneurs : `docker rm forgeai_backend_admin forgeai_backend forgeai_chroma forgeai_redis forgeai_postgres`. Ses données restent dans ses volumes. |
| Un port est déjà pris (5432, 6379, 8000, 8001, 8002, 3000) | Arrêtez le programme qui l'occupe. Pour l'API admin, vous pouvez changer `ADMIN_API_PORT` dans `.env` et `NEXT_PUBLIC_ADMIN_API_URL` dans `frontend/.env.local`. |
| `service "backend" is not running` | `docker compose up -d` a échoué : lisez son message, puis `docker compose logs backend`. |
| Le backend redémarre en boucle | Une variable obligatoire manque dans `.env` : `docker compose logs backend` la nomme. Sur un dépôt sans `.env`, relancez `python scripts/init_env.py`. |
| `create_admin` : « Mot de passe trop court » | Il faut **au moins 12 caractères** pour un administrateur. |
| Pas d'e-mail reçu | Regardez les **Spam**. Dans `docker compose logs backend`, « envoyé à » confirme l'envoi, « Échec de l'envoi » donne la raison, « SMTP non configuré » signifie que `.env` n'est pas pris en compte (voir 8.2). |
| Connexion utilisateur refusée juste après l'inscription | L'adresse e-mail n'est pas encore vérifiée (voir 6.2). |
| L'analyse échoue tout de suite | Clé d'IA absente, invalide ou quota atteint : **Santé du système** indique laquelle, et les modèles introuvables. Ajoutez l'autre clé d'IA ou attendez la réinitialisation du quota. |
| « Continuer avec Google » échoue | Sans `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, c'est normal : utilisez l'inscription par e-mail. Sinon, vérifiez l'URI de redirection (4.4) et que votre adresse figure parmi les utilisateurs de test. |
| Page blanche ou erreur réseau dans le navigateur | `npm run dev` n'est pas lancé, ou le backend ne répond pas : vérifiez http://localhost:8000/health |
| Accents mal affichés par `Get-Content` sous PowerShell | Affichage seulement : ajoutez `-Encoding utf8`. |

---

## 11. Sécurité

- **Ne committez jamais** `.env` ni `frontend/.env.local` (ils sont ignorés par git).
- Ne partagez pas vos clés et ne les montrez pas dans des captures d'écran. Une clé qui a été affichée
  ou envoyée quelque part doit être **remplacée** (révoquez-la dans la console du fournisseur, créez-en une nouvelle).
- L'API admin n'écoute que sur `127.0.0.1`. En production, elle se place derrière un VPN,
  et le repli « e-mails dans le journal » est désactivé (`ENVIRONMENT=production`).
- Remplacez toutes les clés de développement avant une mise en production.
