# Research: Entra ID + Keycloak Coexistence

**Date**: 2025-12-11  
**Status**: Complete  
**Branch**: `001-migrate-entraid-auth`

---

## Q1: Migration Strategy

**Clarification from spec**: Should we support coexistence (Keycloak + Entra ID) or cut over immediately?

**Decision**: **Coexistence (side-by-side) with admin-controlled cutover/rollback**

**Rationale**: 
- Minimizes risk of downtime; allows rollback if issues emerge
- Provides time for user testing and feedback
- Allows gradual user migration (canary rollout possible)
- Allows maintaining both providers until full confidence in Entra ID is achieved
- Feature flag allows quick disable if Entra validation fails

**Alternatives considered**:
- **B - Immediate cutover**: Faster but risky; no rollback path if Entra token validation fails
- **C - Phased canary**: More complex; requires user routing logic; consider post-Phase 1 if needed

**Implementation impact**:
- Backend accepts tokens from both Keycloak and Entra while both are enabled
- Each provider can be enabled/disabled independently (coexistence, cutover, rollback)
- Token source detected primarily by `iss` claim in JWT

---

## Q2: Roles/Claims Mapping

**Clarification from spec**: Where should roles be sourced from in Entra?

**Decision**: **Entra App Roles assigned to Groups** (users get roles via group assignment)

**Rationale**:
- App roles provide a stable, explicit authorization model for the application
- Assigning app roles to groups keeps day-to-day user management group-based
- Tokens can carry app roles consistently (e.g., `roles` claim), minimizing custom mapping logic

**Alternatives considered**:
- **A - App roles only**: Less flexible for organizational role management; app roles are typically predefined
- **C - Custom claims mapping**: Requires custom provisioning logic; more admin overhead

**Implementation impact**:
- Entra tokens should include application roles (typically in the `roles` claim)
- Authorization checks should use a consistent internal role model across providers
- Keycloak roles/claims should be mapped to the same internal role names during coexistence

---

## Q3: User Provisioning / Sync

**Clarification from spec**: Which user provisioning approach should we use?

**Decision**: **Identity-provider managed only** (no user sync / no local persistence)

**Rationale**:
- Avoids introducing a local user database or synchronization workflow
- Keeps Entra/Keycloak as the source of truth for identity and group/role assignment
- Reduces operational and security surface area

**Alternatives considered**:
- **A - IdP-managed only**: May lose user context; harder to audit who has logged in
- **B - Periodic sync**: More complex; requires sync job, handles conflicts, slower to propagate changes

**Implementation impact**:
- No persistence required for authentication/authorization
- Logging provides audit visibility without storing identities

---

## Technology Choices

### Backend Token Validation: PyJWT + python-jose

**Decision**: Use existing `python-jose` (already in codebase); add `PyJWT` as fallback

**Rationale**:
- `python-jose` already integrated in `app/auth/service.py`; minimal changes needed
- `PyJWT` supports RS256 (RSA signing); both libraries handle JWKS caching
- Entra ID uses RS256; both libraries can validate

**Implementation**:
- Refactor `KeycloakAuthService` → `JWTAuthService` (generic)
- Support multiple token issuer configurations (Keycloak, Entra ID)
- Cache JWKS from both issuers separately

---

### Frontend Token Acquisition: MSAL.js

**Decision**: Use `@azure/msal-browser` for SPA token acquisition

**Rationale**:
- Microsoft-provided library; best support for Entra ID flows
- Handles authorization code flow + PKCE automatically
- Built-in token caching and refresh
- Integrates with React via `@azure/msal-react`

**Alternatives considered**:
- `passport.js`: Server-side; not suitable for SPA
- Generic OpenID Connect library: More manual setup; MSAL is more feature-complete

**Implementation**:
- Replace Keycloak config in `frontend/src/env.ts` with Entra ID config
- Create `AuthProvider.tsx` using `MsalProvider`
- Hooks: `useIsAuthenticated()`, `useAccount()`, `useAcquireTokenSilent()`

---

### Infrastructure Automation: Azure CLI + Graph (scripts)

**Decision**: Use the repo’s Entra scripts under `infra/scripts/entra/`

**Rationale**:
- Scripts are explicit, repeatable, and keep parameters provided at runtime (no hidden defaults)
- Scripts handle nested Graph application configuration in an idempotent way

**Alternatives considered**:
- Pure Bash: No state management; harder to track what's deployed
- Pure Terraform: `azuread_` provider still maturing; bash scripts more reliable for groups/users
- Azure Bicep: Less familiar to team; Terraform already in use

**Implementation**:
- `infra/scripts/entra/create-entra-apps.sh`: App registrations (SPA + API + S2S), scopes, app roles
- `infra/scripts/entra/create-entra-groups.sh`: Security groups for role values
- `infra/scripts/entra/assign-entra-app-roles-to-groups.sh`: Assign app roles to groups
- `infra/scripts/entra/add-users-to-groups.sh`: Add users to groups

---

### Coexistence Middleware: Token Source Detection

**Decision**: Detect token issuer (`iss` claim); route to appropriate validator

**Rationale**:
- Simple and reliable: JWT `iss` claim uniquely identifies issuer
- Keycloak: `iss` = `https://dev.loginproxy.gov.bc.ca/auth/realms/standard`
- Entra ID: `iss` = `https://login.microsoftonline.com/{tenant-id}/v2.0`

**Implementation**:
```python
def get_token_issuer(token: str) -> str:
    """Extract issuer from JWT without validation."""
    payload = jwt.get_unverified_claims(token)
    return payload.get("iss", "")

def validate_token_coexistence(token: str):
    issuer = get_token_issuer(token)
    if "login.microsoftonline.com" in issuer:
        return validate_entra_token(token)
    elif "dev.loginproxy.gov.bc.ca" in issuer:
        return validate_keycloak_token(token)
    else:
        raise UnauthorizedError(f"Unknown issuer: {issuer}")
```

---

## Token Validation Caching

**Decision**: In-memory LRU cache for JWKS; 24-hour TTL with background refresh

**Rationale**:
- JWKS is public; no secrets; safe to cache
- 24-hour TTL balances between key rotation and caching benefits
- Background refresh avoids cache expiry during high traffic
- LRU cache prevents unbounded memory (limit: 10 JWKSets)

**Implementation**:
```python
from functools import lru_cache
import asyncio

class JWKSCache:
    """Thread-safe JWKS caching with TTL."""
    _cache = {}
    _ttl = 86400  # 24 hours
    
    @staticmethod
    async def get_jwks(jwks_uri: str, issuer: str):
        """Fetch and cache JWKS."""
        if issuer in JWKSCache._cache:
            cached, timestamp = JWKSCache._cache[issuer]
            if time.time() - timestamp < JWKSCache._ttl:
                return cached
        # Fetch fresh
        jwks = await fetch_jwks(jwks_uri)
        JWKSCache._cache[issuer] = (jwks, time.time())
        return jwks
```

---

## Security Considerations

### Secret Management
- **Entra client secret**: Stored in Azure Key Vault, passed as env var at deploy time
- **Keycloak client secret**: Remains in Key Vault until deprecation
- No secrets in code or Terraform state

### Token Expiry & Refresh
- Entra ID tokens: 1-hour expiry (standard)
- Frontend: MSAL.js handles refresh transparently via silent acquisition
- Backend: Validates `exp` claim; rejects expired tokens

### Claims Validation
- Mandatory claims: `iss`, `sub`, `aud`, `exp`, `iat`
- Audience validation: Entra `aud` = API client ID (configured)
- Issuer validation: Must match configured issuer URL

---

## Testing Strategy

### Unit Tests
- Token validation with valid/expired/invalid signatures
- Role extraction/normalization across providers (Entra `roles` claim; Keycloak role claims)
- Coexistence: both Keycloak and Entra tokens accepted
- Provider enable/disable feature flags (cutover/rollback)
- Error handling: missing claims, wrong issuer, etc.

### Integration Tests
- End-to-end auth flow with Entra test app
- Protected endpoint access with Entra token
- Role-based access control: allowed/denied based on application roles (assigned to users via groups)

### Manual Testing
- Dev: MSAL.js token acquisition and API calls
- Staging: Keycloak + Entra coexistence; admin can toggle
- Production: Full cutover validation before disabling Keycloak

---

## Deliverables Summary

| Item | Owner | Status |
|------|-------|--------|
| `data-model.md` | Design Phase 1 | Complete |
| `contracts/auth-api.md` | Design Phase 1 | Complete |
| `quickstart.md` | Design Phase 1 | Complete |
| `infra/scripts/entra/*` | Implementation | Complete |
| `api-ms-agent/app/auth/service.py` (refactor) | Implementation | TBD |
| `frontend/src/service/auth-service.ts` (new) | Implementation | TBD |
| Integration tests | Implementation | TBD |
| Migration runbook | Implementation | TBD |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Entra token validation fails in production | Feature flag allows quick disable; rollback to Keycloak only |
| Users locked out during transition | Coexistence period; both providers active until cutover |
| JWKS caching stale keys | Background refresh + manual override capability |
| App role assignments misconfigured | Pre-production testing with test users across all role groups; verify `roles` claim in access token |
| Token clock skew issues | Support ±5s clock skew in validation |

