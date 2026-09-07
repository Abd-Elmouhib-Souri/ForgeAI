# ForgeAI Frontend

ForgeAI's frontend is the web interface for project analysis, clarification, reporting and the Sprint 4 Product Manager AI workflow.

## Runtime

The certified Sprint 4 frontend runtime uses Next.js 16.3.1.

Install dependencies:

    npm ci

Run the development server:

    npm run dev

## Project workflow

The project interface exposes the canonical analysis journey, including:

- project creation and editing;
- context validation;
- direct clarification answers;
- canonical context revalidation;
- analysis launch when `ready_for_agents` is satisfied;
- report and debate-room views;
- Product Manager AI planning.

The Product Manager section consumes backend project-management authority rather than recreating planning decisions in the UI.

Sprint 4 functionality includes backlog presentation, priorities, Story Points, dependencies, sprint assignments, settings, story locks, deterministic replan, velocity, burndown and project-management metrics.

## Clarification authority

When a project needs clarification, the frontend allows the user to answer each clarification item directly.

The flow is:

    needs_clarification
    -> answer clarification items
    -> persist canonical answers
    -> consume backend revalidation
    -> ready_for_agents

Saving clarification answers does not implicitly launch agents.

## Authentication and security

The browser does not consume bearer access tokens from OAuth URL parameters.

OAuth completion uses the refresh-token cookie and calls:

    POST /auth/refresh

Refresh-token lifecycle behavior is controlled by the backend security policy.

## Certification commands

Run frontend Node contracts:

    node --test tests/*.test.mjs

Run the standalone clarification authority contract:

    node tests/clarification-authority.contract.mjs

Run the UTF-8 contract:

    node --test tests/utf8-display.contract.test.mjs

Run TypeScript validation:

    npx tsc --noEmit

Run ESLint:

    npm run lint

Run the production build:

    npm run build

Sprint 4 certification produced:

- frontend Node contracts: 14 passed;
- UTF-8 production-source contract: GREEN;
- TypeScript: GREEN;
- ESLint: 0 errors, 13 pre-existing warnings;
- Next.js production build: GREEN, 21/21 routes generated;
- frontend Security P1 contract: GREEN.

## Project documentation

Project-level setup, architecture and operational status:

- `../README.md`

Sprint 4 certification and handoff:

- `../docs/SPRINT4_CERTIFICATION.md`
