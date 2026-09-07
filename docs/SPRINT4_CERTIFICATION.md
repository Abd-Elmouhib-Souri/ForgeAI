# ForgeAI Sprint 4 Certification

Certification date: 2026-09-02

## Status

Sprint 4 product implementation, technical certification and documentation are complete through S4.35.

- S4.32 Full Backend: CLOSED_GREEN
- S4.33 Frontend Certification: CLOSED_GREEN
- S4.34 Docker / Alembic / Security: CLOSED_GREEN
- S4.35 Documentation: CLOSED_GREEN
- S4.36 Checkpoint / Tag / Push: pending explicit Git publication decision

No commit, tag or push is created by this document.

## Product objective

Sprint 4 introduces the AI Product Manager workflow while preserving ForgeAI's universal analysis architecture.

The platform must remain capable of analyzing arbitrary ideas across arbitrary sectors, regions and countries.

No production correction may be specialized only for one fixture, example, sector, country, region or project.

## Architecture invariant

ForgeAI follows this authority chain:

    User input
    -> Canonical project context
    -> LLM proposals
    -> Policies validate
    -> Deterministic engines decide
    -> Persisted versioned plan
    -> Frontend displays

The correction method is:

    Symptom
    -> First Wrong Layer
    -> REAL RED contract
    -> Canonical authority
    -> Universal invariant
    -> Minimal central patch
    -> Targeted regression
    -> Positive / negative / anti-overfit tests
    -> Cross-domain
    -> Cross-country
    -> Metamorphic
    -> Golden
    -> Blind
    -> Full regression

## Sprint 4 Product Manager capabilities

Certified Sprint 4 capabilities include:

- project-management context construction from canonical project facts;
- Product Owner backlog generation;
- canonical backlog policy;
- scope inclusion and exclusion authority;
- MoSCoW priorities;
- Story Points;
- dependencies;
- Scrum Master advice;
- deterministic sprint planning;
- editable planning settings;
- story locks;
- deterministic replan;
- velocity forecasting;
- burndown;
- project-management metrics;
- versioned project-management plan;
- stale or obsolete context detection;
- persistence;
- owner-protected project-manager API;
- frontend Product Manager section.

## Clarification authority

Clarification answers are part of canonical project context.

The certified flow is:

    needs_clarification
    -> user answers structured clarification items
    -> answers are persisted
    -> canonical context is enriched
    -> backend revalidates readiness
    -> ready_for_agents

Saving clarification answers does not automatically launch the full analysis.

## Universal validation

Sprint 4 was validated beyond a single project example.

The certification sequence included:

- cross-domain validation;
- cross-country validation;
- metamorphic validation;
- fault injection;
- Golden UAT;
- Blind UAT;
- full backend regression;
- frontend certification;
- Docker / Alembic / Security certification.

## Backend certification

Final full backend regression:

    1987 passed

Security P1 final backend matrix:

    9 passed

The security contracts cover:

- refresh-token cookie security;
- OAuth bearer transport;
- TOTP protection at rest;
- secret-bearing URL logging;
- current authenticated account-state enforcement;
- refresh-token cookie deletion semantics;
- runtime TOTP behavior;
- runtime cookie behavior;
- runtime current-user behavior.

## Frontend certification

Certified evidence:

- Node frontend contracts: 14 passed;
- standalone clarification authority contract: GREEN;
- UTF-8 production-source contract: GREEN;
- TypeScript: GREEN;
- ESLint: 0 errors and 13 pre-existing warnings;
- Next.js production build: GREEN;
- generated production routes: 21/21;
- frontend OAuth bearer-transport security contract: GREEN.

## Security baseline

### Refresh-token cookies

Refresh-token cookie behavior is centralized.

The invariant is environment-aware:

- explicit local or test HTTP may use a non-Secure development cookie;
- local HTTPS uses Secure;
- production, staging and unknown environments fail secure.

Refresh-token lifecycle remains HttpOnly.

### OAuth

The OAuth callback does not place bearer access tokens in redirect URL query parameters.

The frontend completes OAuth authentication through:

    POST /auth/refresh

### TOTP

Persisted TOTP secrets use:

    fernet:v1:

Raw TOTP secrets are not the persistent representation.

Unknown or invalid stored representations fail closed.

The certified deployment database contained:

- 0 legacy unprotected TOTP secrets;
- 0 enabled 2FA accounts without a protected secret.

### Authenticated account state

Canonical current-user authorization re-checks:

- `is_active`;
- `is_email_verified`.

### Token-bearing links

Verification and reset capability links remain valid application mechanisms.

The security invariant is that token-bearing URLs are not printed to logs.

## Docker certification

Required runtime services were present and running:

- backend;
- postgres;
- redis;
- chromadb.

Container dependency validation reported no broken requirements.

The host and backend container copies of the certified security source files were byte-identical.

## Alembic certification

Migration inventory:

    14 revisions

Certified database revision:

    8b24c1a0f3e7

The revision was both:

- Alembic head;
- current PostgreSQL database revision.

## Certified security identities

Backend static security contract:

    0A597365BE95BBC6DAFBD2130FFB6CAD6C8754B6BE0528478F924142F899060D

Backend runtime security contract:

    747BFA02C6987A0E9C5469090C94AA487CC1103079DCF6599B69F600600A90BF

Frontend security contract:

    59346975ADF74326C1B8C3E464369987AA9F56AB0B445002B1875F8E05B5862D

## Certified security product identities

`backend/app/security.py`

    B6D12925AA4CE846D318AF14C6C0790CF04BF22C303B4CED248DADFF49F36D70

`backend/app/routers/auth.py`

    A484438B9D54B61B2682C0E32A406055C587FBF7A2929536E3AF0DC7B03FE6D6

`backend/app/routers/admin.py`

    8142DD6CDF382CB5527C9E1F01D67DCCE41E56276B656596EAF221A001AF9A18

`backend/app/security_policy.py`

    AF61ECE0918B1F90BA5E5C0A586B9767615B0B167C86E5DD21F23734ADE07035

`frontend/lib/auth-context.tsx`

    491A3DA82655224149B66954F7E730CA68712F4243FCE85E7A004BC181F3C6A5

`frontend/app/oauth/callback/page.tsx`

    84FF0A3CBAD953645C0D020F78F45EC6D6C0F4DF07FB5B9A7541D8E24517536C

## Git baseline

Certification was performed on:

Branch:

    sprint4-ai-project-manager

HEAD:

    65e9302ea66db48d1ec28ae02e66444905e12df7

The repository already contains unrelated and historical unstaged and untracked work.

The certification process intentionally does not clean, stage, commit, tag or push that work.

## Historical checkpoint

`docs/PRE_SPRINT4_CHECKPOINT.md` is the historical pre-Sprint-4 baseline.

It must remain unchanged by Sprint 4 documentation closeout.

## Next step

S4.36 is the final Sprint 4 checkpoint.

Before any Git publication action:

1. review the exact Sprint 4 change set;
2. distinguish intended Sprint 4 files from unrelated historical worktree changes;
3. decide explicitly what should be staged;
4. certify the staged set;
5. only then decide whether to commit, tag and push.

No `git add .` should be used.
