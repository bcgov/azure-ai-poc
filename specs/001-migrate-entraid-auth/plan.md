# Implementation Plan: Migrate to MS Entra ID for Authentication

**Branch**: `001-migrate-entraid-auth` | **Date**: 2025-12-11 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-migrate-entraid-auth/spec.md`

## Summary

Migrate the azure-ai-poc application from Keycloak-based JWT authentication to MS Entra ID (Azure AD) for both the API backend (`api-ms-agent`) and frontend SPA. The migration includes:

1. **Backend (api-ms-agent)**: Update auth service to validate tokens issued by Entra ID with configurable claims/role mapping
2. **Infrastructure**: Create Entra ID app registrations (SPA client + API/service-to-service client) via Terraform and bash automation scripts
3. **RBAC/Groups**: Automate creation of Entra ID security groups, role assignments, and user provisioning via Azure CLI
4. **Frontend**: Update SPA configuration to acquire tokens from Entra ID via MSAL.js
5. **Coexistence**: Support both Keycloak and Entra ID during transition (feature-flag controlled)

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, Pydantic, python-jose/PyJWT, httpx, azure-identity, msal (frontend)  
**Storage**: Cosmos DB, Azure Search (no auth layer changes needed)  
**Testing**: pytest (backend), vitest (frontend), integration tests with token validation  
**Target Platform**: Linux (Azure Container Apps/App Service)  
**Project Type**: Web application (FastAPI backend + React frontend)  
**Performance Goals**: JWT validation < 10ms, token caching with TTL, JWKS refresh every 24h  
**Constraints**: No downtime during migration, backward-compat with Keycloak tokens during coexistence phase  
**Scale/Scope**: Multi-tenant, 100+ users, 50+ API endpoints, role-based access control with custom claims

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality
✅ **PASS**: Python backend uses ruff + mypy; Frontend uses ESLint + TypeScript strict mode.  
✅ **PASS**: Type annotations required for all auth/security modules.

### Test-First Development
✅ **PASS**: Auth changes require token validation tests, role mapping tests, integration tests with both Keycloak and Entra.  
⚠️ **NOTE**: Backend auth module currently has 45% coverage; post-migration must reach 75%+ for core auth module.

### Type Safety & Static Analysis
✅ **PASS**: Pydantic models for all Entra token claims; python-jose for token validation.

### User Experience & Security
✅ **PASS**: No user-facing UX changes; auth is transparent to users.  
✅ **PASS**: Azure security best practices: managed identities, private endpoints, secret management via Azure Key Vault.

### Performance & Observability
✅ **PASS**: Structured logging for token validation/claims; OpenTelemetry tracing for auth flows.  
✅ **PASS**: Target: JWT validation < 10ms (no external calls if JWKS cached).

**GATE RESULT**: ✅ **PASS** - No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-migrate-entraid-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output (TBD)
├── data-model.md        # Phase 1 output (TBD)
├── quickstart.md        # Phase 1 output (TBD)
├── contracts/           # Phase 1 output (TBD)
├── checklists/
│   └── requirements.md
└── spec.md
```

### Source Code

#### Backend (api-ms-agent)

```text
api-ms-agent/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── service.py             # ← JWT validation, claims mapping
│   │   ├── models.py              # ← EntraUser, TokenClaims
│   │   └── dependencies.py        # ← FastAPI dependency injection
│   ├── middleware/
│   │   └── auth_middleware.py     # ← Token validation middleware
│   ├── config.py                  # ← Entra config (env vars)
│   └── main.py
├── tests/
│   ├── test_auth_entra.py         # ← Token validation tests
│   ├── test_role_mapping.py       # ← Claims mapping tests
│   └── test_auth_coexistence.py   # ← Keycloak + Entra tests
└── pyproject.toml
```

#### Frontend

```text
frontend/
├── src/
│   ├── service/
│   │   └── auth-service.ts        # ← MSAL.js integration
│   ├── components/
│   │   └── AuthProvider.tsx       # ← Auth context provider
│   └── env.ts                     # ← Entra config (env vars)
├── index.html
└── vite.config.ts
```

#### Infrastructure

```text
infra/
├── modules/
│   ├── entra-id/
│   │   ├── main.tf                # ← App registrations (SPA + API)
│   │   ├── variables.tf           # ← Tenant, client IDs
│   │   └── outputs.tf             # ← JWKS URI, scopes
│   ├── backend/
│   │   └── main.tf                # ← Updated with ENTRA_* vars
│   └── frontend/
│       └── main.tf                # ← Updated with Entra config
├── scripts/
│   ├── create-entra-resources.sh  # ← Create apps, groups, roles
│   ├── add-users-to-groups.sh     # ← User provisioning
│   └── cleanup-keycloak.sh        # ← Post-migration cleanup
├── main.tf
└── terraform.tfvars
```

**Structure Decision**: Web application with existing FastAPI backend + React frontend. Changes are localized to auth services and infrastructure configuration. No new microservices; coexistence layer added via feature flag in auth middleware.

## Complexity Tracking

> No Constitution Check violations; no complexity exceptions needed.

---

## Phase 0: Research (COMPLETE)

**Status**: ✅ COMPLETE  

**Output**: [research.md](research.md)

**Key Decisions Made**:

1. **Migration strategy clarification** (from spec)
   - Decision: [Awaiting user input - A/B/C]
   - Rationale: [TBD]
   - Impact on design: [TBD]

2. **Roles/claims mapping approach** (from spec)
   - Decision: [Awaiting user input - A/B/C]
   - Rationale: [TBD]
   - Impact on design: [TBD]

3. **User provisioning strategy** (from spec)
   - Decision: [Awaiting user input - A/B/C]
   - Rationale: [TBD]
   - Impact on design: [TBD]

4. **Terraform vs Bash for Entra automation**
   - Decision: [TBD]
   - Best practice for azurerm provider app registrations
   - Alternatives: Azure CLI scripts, Azure Bicep

5. **Token caching and JWKS refresh strategy**
   - Decision: [TBD]
   - Redis vs in-memory caching
   - TTL and refresh patterns

6. **Coexistence middleware design**
   - Decision: [TBD]
   - Token source detection (iss claim)
   - Fallback order (Entra → Keycloak during transition)

**Output**: research.md with all decisions and rationale

---

## Phase 0: Research (COMPLETE)

**Status**: ✅ COMPLETE  

**Output**: [research.md](research.md)

**Key Decisions Made**:

1. **Migration strategy**: A - Coexistence with feature flag (phased migration)
   - Minimizes risk; allows rollback
   - Both Keycloak and Entra accepted during transition
   - Feature flag controls cutover

2. **Roles/claims mapping**: B - Groups mapping + A - App roles
   - Entra security groups mapped to app roles
   - Fallback to app roles for fine-grained permissions

3. **User provisioning**: C - Just-in-time (JIT) provisioning
   - Users auto-provisioned on first Entra login
   - No scheduled sync; reduces operational overhead

4. **Infrastructure automation**: Terraform + Bash
   - Terraform for app registrations (desired state)
   - Bash scripts for groups/user assignments (imperative)

5. **Token validation**: PyJWT + python-jose
   - Detect issuer from `iss` claim
   - Route to appropriate validator (Keycloak vs Entra)

6. **Coexistence middleware**: Token source detection
   - Check `iss` claim to identify issuer
   - Gracefully handle both providers

7. **JWKS caching**: In-memory LRU with 24h TTL
   - Prevents token validation latency
   - Background refresh prevents expiry

---

## Phase 1: Design & Contracts (COMPLETE)

**Status**: ✅ COMPLETE  

**Deliverables**:
- [data-model.md](data-model.md): Auth entities (EntraUser, EntraToken, RoleMapping, EntraConfig)
- [contracts/auth-api.md](contracts/auth-api.md): OpenAPI spec, error responses, contract examples
- [quickstart.md](quickstart.md): Dev setup, code examples, testing guide

---

## Next Steps

1. **User input required**: Respond with clarification choices (Q1, Q2, Q3 from spec) to proceed to Phase 0 research
2. **Phase 0**: Resolve research tasks in research.md
3. **Phase 1**: Generate design artifacts (data-model, contracts, quickstart, agent context)
4. **Phase 2** (by `/speckit.tasks`): Generate implementation tasks for:
   - Backend auth service updates
   - Frontend MSAL.js integration
   - Terraform + bash automation scripts
   - Integration tests
   - Migration runbook (Keycloak → Entra cutover)

