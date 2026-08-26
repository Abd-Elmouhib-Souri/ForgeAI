# ForgeAI

ForgeAI is an AI-powered SaaS platform that transforms a project or startup idea into structured project intelligence, business validation, startup evaluation and actionable planning artifacts.

## Current Status

- Sprint 0 → Sprint 3 implemented
- Sprint 3 functional scope frozen
- Sprint 4 — AI Project Manager: CONDITIONAL GO

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

ForgeAI follows a canonical authority methodology:

    Reproduce
    -> First Wrong Layer
    -> RED Contract
    -> Minimal Universal Patch
    -> Targeted Regression
    -> Cross-Archetype Regression
    -> Golden UAT
    -> Blind UAT

Corrections must remain universal and must not be hardcoded for a single idea, sector, country or fixture.

## Known Sprint 3 Debt

The pre-Sprint-4 checkpoint intentionally preserves documented semantic hardening debt around archetype and query authority.

Sprint 4 must consume canonical project facts as primary authority.

---

ForgeAI — Pre-Sprint-4 checkpoint
26 August 2026
