# ForgeAI

ForgeAI is an AI-powered SaaS platform that transforms a project or startup idea into structured project intelligence, business validation, startup evaluation and actionable planning artifacts.

## Current Status

- Sprint 0 through Sprint 4 product implementation: complete.
- S4.32 full backend regression: 1987 passed.
- S4.33 frontend certification: CLOSED_GREEN.
- S4.34 Docker / Alembic / Security: CLOSED_GREEN.
- S4.35 documentation closeout: CLOSED_GREEN.
- S4.36 checkpoint / tag / push: pending.
- No commit, tag or push is performed automatically by the certification workflow.


## Sprint 4 - AI Project Manager

Sprint 4 adds the Product Manager AI layer on top of the canonical project context.

Certified capabilities include:

- canonical project-management context derived from project authority;
- Product Owner backlog generation;
- deterministic backlog policy and scope enforcement;
- MoSCoW prioritization;
- Story Points;
- dependency graph handling;
- deterministic sprint planning;
- editable sprint settings;
- story locks;
- deterministic replan;
- velocity forecasting;
- burndown and project-management metrics;
- Scrum Master advice;
- versioned project-management plans;
- obsolete-context detection;
- owner-protected project-manager API routes;
- frontend Product Manager integration.

The clarification flow remains part of the canonical input authority:

    needs_clarification
    -> user answers clarification items
    -> durable canonical project context is enriched
    -> context is revalidated
    -> ready_for_agents

Unknown or missing project facts are not silently replaced by country-, sector- or fixture-specific defaults.

## Sprint 4 Certification

Sprint 4 certification evidence:

- backend full regression: 1987 passed;
- frontend Node contracts: 14 passed;
- frontend UTF-8 production-source contract: GREEN;
- TypeScript: GREEN;
- ESLint: 0 errors, 13 pre-existing warnings;
- Next.js production build: GREEN, 21/21 routes generated;
- Docker runtime: backend, postgres, redis and chromadb running;
- Alembic database revision: `8b24c1a0f3e7` current and head;
- backend Security P1 contracts: 9 passed;
- frontend OAuth bearer-transport security contract: GREEN;
- TOTP deployment guard: no legacy unprotected secret and no enabled account without a protected secret.

The detailed certification and handoff authority is:

- `docs/SPRINT4_CERTIFICATION.md`

S4.36 checkpoint / tag / push is still pending and requires an explicit Git publication decision.

## Sprint 4 Security Baseline

The certified security invariants are:

- refresh-token cookies use centralized policy with HttpOnly semantics and environment-aware Secure behavior;
- production, staging and unknown environments fail secure for the refresh cookie;
- OAuth callback transport does not put bearer access tokens in the redirect URL or query string;
- the frontend completes OAuth login through `/auth/refresh`;
- TOTP secrets are stored with the `fernet:v1:` protected representation rather than raw secrets;
- stored TOTP values fail closed if the protected representation cannot be revealed;
- authenticated-user access re-checks `is_active` and `is_email_verified`;
- verification and reset capability URLs may contain their purpose-built token, but token-bearing URLs are not printed to application logs.

## Main Stack

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Redis
- ChromaDB
- LangChain / LangGraph
- Gemini / Groq provider abstraction

### Frontend
- Next.js
- React
- TypeScript

### Infrastructure
- Docker
- Docker Compose

## Environment

Real `.env` files are never committed.

Templates:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.example`

Create local copies and provide your own secret values.

## Backend Dependencies

Runtime:

    pip install -r backend/requirements.txt

Development / QA:

    pip install -r backend/requirements-dev.txt

## Frontend

    cd frontend
    npm ci
    npm run dev

## Backend Docker

    docker compose up -d --build backend

## Quality Method

ForgeAI uses a canonical authority methodology:

    Reproduce
    -> First Wrong Layer
    -> REAL RED contract
    -> Canonical authority
    -> Universal invariant
    -> Minimal central patch
    -> Targeted regression
    -> Positive / negative / anti-overfit validation
    -> Cross-domain regression
    -> Cross-country regression
    -> Metamorphic validation
    -> Golden UAT
    -> Blind UAT
    -> Full regression

Corrections must remain universal. A production rule must never be introduced only to satisfy one fixture, project, sector, country or region.

The architecture principle is:

    LLM proposes
    -> Policies validate
    -> Deterministic engines decide
    -> Frontend displays

## Known Sprint 3 Debt

The pre-Sprint-4 checkpoint intentionally preserves documented semantic hardening debt around archetype and query authority.

Sprint 4 must consume canonical project facts as primary authority.

---

ForgeAI — Pre-Sprint-4 checkpoint
26 August 2026
