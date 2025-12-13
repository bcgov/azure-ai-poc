# Implementation Plan: Add MS Entra ID Authentication alongside Keycloak

**Branch**: `001-migrate-entraid-auth` | **Date**: 2025-12-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification in [spec.md](spec.md)

## Summary

Add Microsoft Entra ID as an additional authentication/authorization provider while keeping Keycloak working during a transition period.
The backend must accept and validate JWTs from both issuers, with admin-controlled enable/disable flags for safe cutover and rollback.
Authorization must remain consistent across providers by using a single application role model (Entra app roles assigned to groups; Keycloak roles mapped to the same app roles).

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**:
- Backend: FastAPI, httpx, python-jose, PyJWT (already added)
- Frontend: React (Vite), existing Keycloak client, MSAL (already added)
**Storage**: N/A for auth (no persistence of auth data; identity providers remain source-of-truth)
**Testing**:
- Backend: pytest (+ pytest-asyncio)
- Frontend: vitest + Playwright (existing)
**Target Platform**: Containerized web app deployed to Azure
**Project Type**: Web application (backend + frontend)
**Performance Goals**:
- API p95 response time ≤ 500ms for standard requests; p99 ≤ 2s
**Constraints**:
- No auth persistence layer (no local user DB for auth); configuration-driven only
- No secrets committed; secrets provided via secure deployment mechanisms
- Must support coexistence, cutover, and rollback without downtime
**Scale/Scope**:
- Supports existing users/integrations on Keycloak while enabling Entra SSO users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality: ruff / ESLint pass for touched code
- Type Safety: align with strict typing expectations where configured (avoid adding untyped core modules)
- Test-First: add/extend tests for new auth behavior (multi-issuer validation; cutover flags)
- Security: JWT validation must enforce issuer/audience/signature and deny-by-default on authorization
- Observability: log auth success/failure with provider identifier (no PII beyond necessary)

No constitution violations are required for this feature.

## Project Structure

### Documentation (this feature)

```text
specs/001-migrate-entraid-auth/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auth-api.md
└── tasks.md
```

### Source Code (repository root)

```text
api-ms-agent/
├── app/
│   ├── auth/
│   ├── core/
│   ├── middleware/
│   └── routers/
└── tests/

frontend/
├── src/
│   ├── service/
│   └── ...
└── e2e/

infra/
└── scripts/
   └── entra/
```

**Structure Decision**: Web app with FastAPI backend in `api-ms-agent/` and Vite/React frontend in `frontend/`.

## Phase 0: Outline & Research (Complete)

Research is captured in [research.md](research.md) and aligns to the updated spec:
- Migration strategy: coexistence with admin-controlled cutover/rollback
- Roles mapping: Entra app roles (assigned to groups) and a consistent internal role model
- Provisioning: IdP-managed only (no sync to local DB)

## Phase 1: Design & Contracts (Complete)

Artifacts updated/maintained under `specs/001-migrate-entraid-auth/`:
- [data-model.md](data-model.md): conceptual entities for multi-issuer auth and role model
- [contracts/auth-api.md](contracts/auth-api.md): bearer token contract + error semantics
- [quickstart.md](quickstart.md): developer/operator setup for coexistence

**Agent context update**:
- Run the agent context update script after Phase 1 doc updates to keep `.github/copilot-instructions.md` in sync.

## Phase 2: Implementation Planning (Stop point for /speckit.plan)

High-level delivery sequence (detailed tasks tracked in [tasks.md](tasks.md)):

1. **Backend multi-issuer validation (P1)**
  - Detect issuer from unverified claims
  - Validate token against the configured provider (Keycloak or Entra)
  - Enforce issuer/audience/signature and expiry
  - Gate acceptance with independent feature flags for each provider

2. **Authorization consistency (P1)**
  - Define a single internal role model
  - Entra: rely on `roles` claim (app roles) for user flows; support application roles for client-credentials flows
  - Keycloak: map existing Keycloak roles/claims into the same internal role model

3. **Frontend coexistence (P2)**
  - Add Entra SSO via MSAL without breaking existing Keycloak login during migration
  - Ensure API calls include the correct bearer token

4. **Cutover + rollback procedure (P3)**
  - Document configuration steps to disable Keycloak acceptance
  - Keep rollback path by re-enabling Keycloak acceptance

5. **Testing + observability (all phases)**
  - Add tests for both issuers + toggles
  - Add structured logging for auth outcomes with provider identifier
