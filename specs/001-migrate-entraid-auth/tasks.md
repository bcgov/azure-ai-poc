# Implementation Tasks: Add MS Entra ID Authentication alongside Keycloak

**Branch**: `001-migrate-entraid-auth` | **Date**: 2025-12-12  
**Feature**: Add MS Entra ID alongside Keycloak for authentication and authorization (coexistence + cutover/rollback)  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

---

## Overview

This document outlines all implementation tasks organized by user story and priority. Each task is independently executable and follows the checklist format for tracking progress.

**Total Tasks**: 45  
**Phases**: 5 (Setup → Foundational → US1 → US2 → US3 → Polish)  
**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1) = Admin can configure and test Entra auth

---

## Phase 1: Setup & Prerequisites

**Goal**: Initialize infrastructure, Entra ID app registrations, and project dependencies.  
**Duration**: ~2 hours  
**Prerequisites**: Azure subscription, admin access to Entra ID

### Infrastructure & Entra ID Setup

- [x] T001 Implement Entra app automation (SPA + API + service-to-service) via `infra/scripts/entra/create-entra-apps.sh`
- [x] T002 [P] Implement Entra group automation for role values via `infra/scripts/entra/create-entra-groups.sh`
- [x] T003 [P] Implement app-role assignment automation via `infra/scripts/entra/assign-entra-app-roles-to-groups.sh`
- [x] T004 [P] Implement user-to-group automation via `infra/scripts/entra/add-users-to-groups.sh`
- [x] T005 Create `.env.example` for both backend and frontend with Entra configuration variables

Note: Running these scripts is an operator step (per environment) and is documented in `infra/scripts/entra/README.md`.

### Backend Dependencies

- [x] T006 [P] Add `PyJWT` to `api-ms-agent/pyproject.toml` (already has `python-jose`)
- [x] T007 [P] Run `uv sync` in `api-ms-agent/` to install dependencies

### Frontend Dependencies

- [x] T008 [P] Install MSAL.js libraries: `npm install @azure/msal-browser @azure/msal-react` in `frontend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Establish core authentication service supporting multiple issuers (Keycloak + Entra).  
**Duration**: ~4 hours  
**Dependencies**: Phase 1 complete  
**Parallel Opportunities**: Backend and frontend tasks can run in parallel

### Backend Auth Service Refactoring

- [x] T009 Refactor `api-ms-agent/app/auth/service.py` to support multiple token issuers
  - Rename `KeycloakAuthService` → `JWTAuthService`
  - Add `_validate_entra_token()` and `_validate_keycloak_token()` methods
  - Implement issuer detection from JWT `iss` claim
  - Add JWKS caching with 24-hour TTL

- [x] T010 Create role mapping configuration in `api-ms-agent/app/auth/role_mapping.py`
  - Normalize provider-specific role claims into a single internal role list
  - Entra: rely on `roles` claim (app roles)
  - Keycloak: map existing Keycloak role claims to the same internal role names (if needed)

- [x] T011 Update `api-ms-agent/app/auth/models.py` to support Entra token claims
  - Ensure `EntraUser` model exists with fields: object_id, email, display_name, roles
  - Add Pydantic validation for UUID and email formats

- [x] T012 Update `api-ms-agent/app/auth/dependencies.py` with multi-issuer support
  - Update `get_current_user()` to call refactored `JWTAuthService`
  - Update error handling to distinguish between missing token, invalid signature, expired token
  - Ensure structured logging captures token validation success/failure

- [x] T013 Add configuration in `api-ms-agent/app/config.py` for Entra ID settings
  - `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_ISSUER`, `ENTRA_JWKS_URI`
  - `KEYCLOAK_ENABLED`, `ENTRA_ENABLED` (feature flags)
  - Update validation: at least one auth provider must be enabled

### Backend Integration Tests (Token Validation)

- [x] T014 [P] Create `api-ms-agent/tests/test_auth_entra_token_validation.py`
  - Test valid Entra token acceptance with correct issuer, audience, claims
  - Test invalid signature rejection
  - Test expired token rejection
  - Test missing mandatory claims rejection
  - Test JWKS caching behavior

- [x] T015 [P] Create `api-ms-agent/tests/test_auth_keycloak_token_validation.py`
  - Mirror tests for Keycloak tokens to ensure backward compatibility

- [x] T016 [P] Create `api-ms-agent/tests/test_auth_coexistence.py`
  - Test both providers enabled: valid tokens from both accepted
  - Test one provider disabled: tokens from disabled provider rejected
  - Test feature flag toggle: disable/enable Entra ID via config

### Frontend Configuration

- [x] T017 [P] Create `frontend/src/env.ts` with Entra configuration
  - Export `VITE_ENTRA_TENANT_ID`, `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_AUTHORITY`
  - Export `VITE_API_SCOPES`, `VITE_REDIRECT_URI`
  - Support .env file loading via Vite

---

## Phase 3: User Story 1 - Admin Configures Entra ID (P1)

**Goal**: Backend can validate Entra ID tokens; admin can test authentication via curl/Postman.  
**Duration**: ~3 hours  
**Independent Test**: Generate Entra test token, call protected endpoint, verify 200 or 401/403 as expected  
**Acceptance Criteria**:
- Valid Entra token + correct role → HTTP 200
- Invalid Entra token → HTTP 401
- Expired Entra token → HTTP 401
- Missing role → HTTP 403

### Implementation Tasks

- [x] T018 [US1] Add Entra-specific error messages to `api-ms-agent/app/auth/service.py`
  - Return structured error responses with `detail`, `code`, `timestamp`
  - Log token validation failures with issuer, subject, expiry for audit

- [x] T019 [US1] Implement role-based access control decorator in `api-ms-agent/app/auth/dependencies.py`
  - Create `require_role(role: str)` dependency for use in endpoints
  - Validate user has required role; return 403 if not

- [x] T020 [US1] Update at least 2 existing protected endpoints to use new auth
  - Example: `api-ms-agent/app/routers/documents.py` or equivalent
  - Apply `@require_role()` decorator where appropriate
  - Ensure backward compatibility with Keycloak tokens during coexistence

### Testing Tasks (US1)

- [x] T021 [P] [US1] Create integration test `api-ms-agent/tests/test_protected_endpoint_entra.py`
  - Test protected endpoint with valid Entra token → 200 OK
  - Test protected endpoint with invalid token → 401 Unauthorized
  - Test protected endpoint with missing role → 403 Forbidden
  - Test role enforcement: required role present/absent in the `roles` claim

- [x] T022 [P] [US1] Create manual test guide in `specs/001-migrate-entraid-auth/testing-guide-us1.md`
  - Steps to generate Entra test token (jq + curl)
  - Steps to call protected endpoint with token
  - Expected success/failure responses

### Documentation Tasks (US1)

- [x] T023 [US1] Update `README.md`: Document Entra ID configuration steps for admins
  - Required environment variables: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, etc.
  - Feature flags: `ENTRA_ENABLED`, `KEYCLOAK_ENABLED`

- [x] T024 [US1] Update `api-ms-agent/README.md` with Entra token validation details
  - Supported token issuers
  - JWKS refresh strategy
  - Role mapping location

---

## Phase 4: User Story 2 - Users Authenticate via Entra ID SSO (P2)

**Goal**: Frontend SPA can acquire tokens from Entra ID; users can log in and access protected APIs.  
**Duration**: ~4 hours  
**Independent Test**: Frontend login flow → acquire token → call protected API → verify data returned  
**Acceptance Criteria**:
- User can log in via Entra SSO
- Access token obtained and cached
- Protected API calls include valid token in Authorization header
- User roles displayed in UI (if applicable)

### Frontend Auth Service

- [x] T025 [US2] Create `frontend/src/service/auth-service.ts` (MSAL.js integration)
  - Initialize `PublicClientApplication` with Entra config
  - Implement `acquireToken()` for silent + interactive flows
  - Implement `login()`, `logout()`, `getUser()` functions
  - Support sessionStorage token caching

- [x] T026 [US2] Create `frontend/src/components/AuthProvider.tsx` (React context)
  - Wrap app with `MsalProvider`
  - Export custom hooks: `useAuth()`, `useIsAuthenticated()`, `useUserRoles()`
  - Initialize MSAL on app startup

- [x] T027 [US2] Update `frontend/src/main.tsx` to wrap app with AuthProvider
  - Import and use `AuthProvider` component
  - Ensure MSAL initialization before rendering routes

- [x] T028 [US2] Create API client wrapper in `frontend/src/service/api-client.ts`
  - Auto-inject Entra access token in `Authorization: Bearer` header
  - Refresh token on 401 response
  - Log API errors with structured format

### Frontend UI Components

- [x] T029 [US2] Create login/logout UI in `frontend/src/components/LoginButton.tsx`
  - Display current user (if authenticated)
  - Show "Login" button if not authenticated
  - Show "Logout" button if authenticated

- [x] T030 [P] [US2] Update navigation/header to include AuthProvider status
  - Show authenticated user email/name
  - Show user roles (from token or Entra claims)

- [x] T031 [P] [US2] Create protected route wrapper in `frontend/src/components/ProtectedRoute.tsx`
  - Check `useIsAuthenticated()`
  - Redirect to login if not authenticated
  - Allow navigation if authenticated

### Testing Tasks (US2)

- [x] T032 [P] [US2] Create frontend auth tests in `frontend/src/__tests__/auth.test.ts`
  - Test token acquisition from Entra (mock MSAL)
  - Test login/logout flow
  - Test API client injects token in requests
  - Test token refresh on 401

- [x] T033 [P] [US2] Create E2E test in `frontend/e2e/auth.spec.ts` (Playwright)
  - Navigate to app
  - Click login button
  - Authenticate with test Entra account
  - Verify redirected to home page
  - Call protected API and verify success

### Documentation Tasks (US2)

- [x] T034 [US2] Update `README.md`: Document user login flow
  - Redirect to Entra SSO
  - Token acquisition via MSAL.js
  - Role-based UI rendering

- [x] T035 [US2] Create `frontend/ENTRA_ID_SETUP.md`
  - Step-by-step: Create Entra app registration (SPA)
  - Configure redirect URIs
  - Define app roles on the API app registration and assign them (user/group assignment)

---

## Phase 5: User Story 3 - Coexistence & Rollback (P3)

**Goal**: Both Keycloak and Entra ID authentication work; admin can switch providers via config.  
**Duration**: ~3 hours  
**Independent Test**: Enable/disable providers via feature flags; test both work independently  
**Acceptance Criteria**:
- Both Keycloak and Entra enabled: both token types accepted
- Only Entra enabled: Keycloak tokens rejected (401)
- Only Keycloak enabled: Entra tokens rejected (401)
- Admin can toggle without code changes

### Implementation Tasks

- [x] T036 [US3] Ensure feature flags `KEYCLOAK_ENABLED` and `ENTRA_ENABLED` control token validation
  - Update `api-ms-agent/app/auth/service.py` to check flags before accepting token
  - Return 401 if both disabled
  - Return 401 if issuer's flag is disabled

- [x] T037 [US3] Create migration checklist in `infra/MIGRATION_CHECKLIST.md`
  - Pre-migration: test both providers enabled
  - During migration: monitor error rates
  - Post-migration: disable Keycloak flag

- [x] T038 [US3] Document rollback procedure in `infra/ROLLBACK.md`
  - Steps to disable Entra and re-enable Keycloak
  - Clear instructions for on-call engineer

### Testing Tasks (US3)

- [x] T039 [P] [US3] Create coexistence test in `api-ms-agent/tests/test_coexistence.py`
  - Test both providers enabled: valid tokens from both providers accepted
  - Test Entra disabled, Keycloak enabled: only Keycloak tokens accepted
  - Test Keycloak disabled, Entra enabled: only Entra tokens accepted
  - Test both disabled: all tokens rejected (safety check)

- [x] T040 [P] [US3] Create manual coexistence test guide in `specs/001-migrate-entraid-auth/testing-guide-us3.md`
  - Steps to generate tokens from both Keycloak and Entra
  - Steps to toggle feature flags and verify behavior

### Infrastructure Tasks (US3)

- [x] T041 [US3] Update `infra/modules/backend/main.tf` to pass feature flags as env vars
  - Add `KEYCLOAK_ENABLED`, `ENTRA_ENABLED` to Container App/App Service config
  - Document default values (both enabled during transition)

- [x] T042 [P] [US3] Create migration runbook in `infra/MIGRATION_RUNBOOK.md`
  - 1-week coexistence phase checklist
  - User communication template
  - Cutover date trigger criteria

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Production-ready: logging, monitoring, documentation complete, security validated.  
**Duration**: ~3 hours

### Logging & Observability

- [x] T043 Add structured logging for all auth events in `api-ms-agent/app/middleware/auth_middleware.py`
  - Log token validation success: user ID, role, issuer, timestamp
  - Log token validation failure: reason (expired, invalid sig, wrong issuer), timestamp
  - Export logs to Application Insights (or similar)

- [x] T044 [P] Add metrics endpoint for auth: `api-ms-agent/app/routers/metrics.py`
  - Count: successful auth, failed auth, role denial
  - Latency: token validation time
  - Expose Prometheus format for monitoring

### Security & Compliance

- [x] T045 Create security checklist in `infra/SECURITY_CHECKLIST.md`
  - Verify token signing uses RS256 (not HS256)
  - Verify no secrets in logs or error messages
  - Verify JWKS endpoint is HTTPS-only
  - Verify token expiry < 1 hour

### Final Documentation

- [x] T046 Update main `README.md` with new auth architecture overview
  - Document Keycloak + Entra coexistence and cutover/rollback flags
  - Add Entra ID authentication section
  - Link to ENTRA_ID_SETUP.md in both README files

- [x] T047 [P] Create troubleshooting guide in `docs/ENTRA_ID_TROUBLESHOOTING.md`
  - "Token validation fails" → check issuer, audience, expiry, JWKS
  - "User locked out" → check Entra app role assignment (often via group assignment)
  - "Roles claim missing" → verify the user/group is assigned an app role on the API enterprise application

---

## Dependency Graph & Execution Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ├─→ Phase 3 (US1: Admin Config)
    │   ├─→ Phase 4 (US2: User Auth)
    │   │   └─→ Phase 5 (US3: Coexistence)
    │   │
    │   └─→ Tests for US1
    │
    └─→ Tests for US2 & US3 (parallel with US2/US3 implementation)
        
Phase 6 (Polish)
    ↑
    └─ Runs after all user stories complete
```

## Parallel Execution Opportunities

### Backend Tasks (Can run in parallel within phase)
- Phase 1: T002, T003 (Entra setup) can run in parallel with T006, T007 (deps)
- Phase 2: T014, T015, T016 (tests) can run in parallel with T009-T013 (service)

### Frontend Tasks (Can run in parallel with backend)
- Phase 2: T017 (config) runs in parallel with backend refactor
- Phase 4: T025, T026, T027 (MSAL setup) run in parallel with T028-T031 (UI)
- Phase 4: T032, T033 (tests) run in parallel with implementation

### Example Daily Cadence

**Day 1** (Setup + Foundations):
- Run: T001-T008 (setup)
- Run in parallel:
  - T009-T013 (backend service)
  - T017 (frontend config)

**Day 2** (US1 + US2 Parallel):
- Run T014-T016 (backend tests) while completing T009-T013
- Run T018-T024 (US1 implementation) while T025-T031 (US2 implementation)
- Run T032-T035 (US2 tests + docs) in parallel

**Day 3** (US3 + Polish):
- Run T036-T042 (US3 implementation + infra)
- Run T039-T040 (US3 tests) in parallel
- Run T043-T047 (polish) once all implementations complete

---

## MVP Scope (Minimum Viable Product)

**Phases to Complete**: 1 + 2 + 3  
**Task Count**: T001-T024 (24 tasks)  
**Time Estimate**: ~9 hours  
**Outcome**: Admin can configure Entra ID and test token validation; no frontend yet

**MVP Excludes**:
- Frontend login (Phase 4)
- Coexistence feature flags (Phase 3)
- Production logging/monitoring (Phase 6)

---

## Success Criteria by Phase

| Phase | Success Criteria | Verification |
|-------|-----------------|--------------|
| 1 | Entra apps created, deps installed | `az ad app list`, `pip list` |
| 2 | Auth service supports multi-issuer, tests pass | `pytest api-ms-agent/tests/` |
| 3 | Protected endpoint accessible with Entra token | `curl -H "Auth: Bearer $TOKEN" http://localhost:4000/api/...` |
| 4 | Frontend login → token acquisition → API call | Playwright E2E test pass |
| 5 | Feature flags toggle providers | Environment config change + test |
| 6 | All logs structured, metrics exposed | App Insights / Prometheus scrape |

---

## File Checklist

**Backend**: api-ms-agent/
- [ ] app/auth/service.py (refactored, multi-issuer)
- [ ] app/auth/models.py (EntraUser with roles)
- [ ] app/auth/dependencies.py (updated for Entra)
- [ ] app/auth/role_mapping.py (new, provider role normalization)
- [ ] app/config.py (Entra config + feature flags)
- [ ] app/middleware/auth_middleware.py (logging)
- [ ] app/routers/metrics.py (new, auth metrics)
- [ ] tests/test_auth_*.py (3 test files)
- [x] pyproject.toml (PyJWT added)
- [ ] README.md (updated with Entra section)

**Frontend**: frontend/
- [ ] src/env.ts (new, Entra config)
- [ ] src/service/auth-service.ts (new, MSAL.js)
- [ ] src/service/api-client.ts (new, token injection)
- [ ] src/components/AuthProvider.tsx (new)
- [ ] src/components/LoginButton.tsx (new)
- [ ] src/components/ProtectedRoute.tsx (new)
- [ ] src/main.tsx (updated with AuthProvider)
- [ ] src/__tests__/auth.test.ts (new)
- [ ] e2e/auth.spec.ts (new, Playwright)
- [x] package.json (MSAL libs added)
- [ ] ENTRA_ID_SETUP.md (new)

**Infrastructure**: infra/
- [x] scripts/entra/create-entra-apps.sh (complete)
- [x] scripts/entra/create-entra-groups.sh (complete)
- [x] scripts/entra/assign-entra-app-roles-to-groups.sh (complete)
- [x] scripts/entra/add-users-to-groups.sh (complete)
- [ ] MIGRATION_CHECKLIST.md (new)
- [ ] ROLLBACK.md (new)
- [ ] MIGRATION_RUNBOOK.md (new)
- [ ] SECURITY_CHECKLIST.md (new)

**Documentation**: /
- [ ] README.md (updated with Entra auth section)
- [ ] .env.example (new, Entra vars)
- [ ] docs/ENTRA_ID_TROUBLESHOOTING.md (new)

---

## Next Steps

1. **Start Phase 1** (Setup): Run Entra app creation scripts; install dependencies
2. **Start Phase 2** (Foundations): Begin backend service refactor; can run in parallel with Phase 1
3. **Daily Standup**: Track task completion, unblock dependencies
4. **MVP Validation**: After Phase 3, admin can test Entra auth before proceeding to Phase 4
5. **Code Review**: Each task includes PR requirements (passing tests, linting, type checks)

