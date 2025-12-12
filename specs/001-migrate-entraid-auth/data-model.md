# Data Model: Entra ID Authentication

**Date**: 2025-12-11  
**Status**: Complete  
**Branch**: `001-migrate-entraid-auth`

---

## Entities

### EntraUser

Represents a user authenticated via MS Entra ID.

**Fields**:
- `object_id` (str, unique): Entra user unique identifier
- `email` (str, unique): User email
- `display_name` (str): Full name
- `groups` (List[str]): Entra security group IDs (from token `groups` claim)
- `roles` (List[str]): Mapped application roles (derived from groups)
- `created_at` (datetime): First login timestamp
- `last_login` (datetime): Most recent login

**Validation Rules**:
- `object_id` must be non-empty UUID
- `email` must be valid email format
- `groups` must be non-empty list (at least one group assigned in Entra)
- `roles` computed from `groups` via `RoleMapping` entity

**State Transitions**:
1. **Not exists** → **Exists** (first login via Entra)
2. **Exists** → **Updated** (groups/roles change on subsequent login)
3. **Inactive** → **Active** (re-login after period of inactivity)

**Example**:
```json
{
  "object_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@bcgov.ca",
  "display_name": "John Doe",
  "groups": ["11111111-1111-1111-1111-111111111111"],
  "roles": ["document_reviewer"],
  "created_at": "2025-12-11T10:00:00Z",
  "last_login": "2025-12-11T15:30:00Z"
}
```

---

### EntraToken (JWT Claims)

Represents the structure of MS Entra ID tokens validated by the backend.

**Claims** (OIDC standard + custom):
- `iss` (str): Issuer URL (e.g., `https://login.microsoftonline.com/{tenant-id}/v2.0`)
- `sub` (str): Subject (Entra object_id)
- `aud` (str): Audience (API client ID)
- `exp` (int): Token expiration time (Unix timestamp)
- `iat` (int): Issued at time (Unix timestamp)
- `oid` (str): Entra object ID (same as `sub`)
- `email` (str): User email
- `name` (str): Display name
- `groups` (List[str]): Security group IDs (must request in app registration optional claims)
- `scp` (str): Delegated permissions (scopes) separated by space

**Validation Rules**:
- `exp` must be > current time
- `iat` must be < current time
- `iss` must match configured Entra tenant
- `aud` must match configured API client ID
- `sub` must be non-empty UUID
- `groups` must be present (if group-based RBAC enforced)

**Example**:
```json
{
  "iss": "https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "22222222-2222-2222-2222-222222222222",
  "exp": 1702401600,
  "iat": 1702398000,
  "oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@bcgov.ca",
  "name": "John Doe",
  "groups": ["11111111-1111-1111-1111-111111111111"],
  "scp": "api://read api://write"
}
```

---

### RoleMapping

Configuration entity mapping Entra security groups to application roles.

**Fields**:
- `group_id` (str, unique): Entra security group ID (Azure AD object ID)
- `group_name` (str): Display name of the group
- `app_role` (str): Application role (e.g., `admin`, `document_reviewer`, `guest`)
- `description` (str): Purpose of the role
- `permissions` (List[str]): Granular permissions (future expansion)
- `created_at` (datetime): When mapping was created
- `created_by` (str): Admin who created the mapping

**Validation Rules**:
- `group_id` must be valid UUID
- `app_role` must match defined enum (admin, document_reviewer, guest, etc.)
- `group_id` and `app_role` combination must be unique (no duplicates)

**Example**:
```json
{
  "group_id": "11111111-1111-1111-1111-111111111111",
  "group_name": "Document Reviewers",
  "app_role": "document_reviewer",
  "description": "Users who can review and approve documents",
  "permissions": ["document.read", "document.comment", "document.review"],
  "created_at": "2025-12-11T09:00:00Z",
  "created_by": "admin@bcgov.ca"
}
```

---

### EntraConfig

Application configuration for Entra ID token validation.

**Fields**:
- `tenant_id` (str): Azure AD tenant ID
- `client_id_api` (str): API client ID (app registration)
- `client_id_spa` (str): SPA client ID (app registration)
- `authority` (str): Authority URL for token validation
- `jwks_uri` (str): JWKS endpoint for public key discovery
- `scopes` (List[str]): Delegated scopes defined in app registration
- `enable_entra_id` (bool): Feature flag to enable/disable Entra authentication
- `enable_keycloak` (bool): Feature flag to enable/disable Keycloak (coexistence)

**Validation Rules**:
- `tenant_id` must be non-empty UUID
- `client_id_api` must be non-empty UUID
- `authority` must be valid HTTPS URL
- At least one of `enable_entra_id` or `enable_keycloak` must be true

**Example**:
```json
{
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "client_id_api": "22222222-2222-2222-2222-222222222222",
  "client_id_spa": "33333333-3333-3333-3333-333333333333",
  "authority": "https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0",
  "jwks_uri": "https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/discovery/v2.0/keys",
  "scopes": ["api://read", "api://write"],
  "enable_entra_id": true,
  "enable_keycloak": true
}
```

---

## Relationships

```text
EntraUser (1) ──── (many) RoleMapping
   |
   |
   ├─ object_id (PK)
   └─ groups (FK) ─→ RoleMapping.group_id

RoleMapping (many) ──── (1) EntraConfig
   |
   ├─ group_id (FK)
   └─ app_role ──→ EntraConfig.scopes (permission inference)

EntraToken (JWT)
   ├─ iss ──→ EntraConfig.authority (validation)
   ├─ aud ──→ EntraConfig.client_id_api (validation)
   └─ groups (claims) ──→ RoleMapping.group_id (mapping)
```

---

## Storage

### Backend (Python)

**Where**: Cosmos DB (existing)

**Collections**:
- `users`: EntraUser documents (partitioned by email)
- `role_mappings`: RoleMapping documents (partitioned by app_role)
- `audit_logs`: Auth events (login, role changes)

**Indexes**:
- `users`: PK (object_id), composite (email, last_login)
- `role_mappings`: PK (group_id, app_role)

### Frontend (Browser)

**Where**: Browser `sessionStorage` / `localStorage`

**Keys**:
- `entra_access_token`: Current access token (session-scoped)
- `entra_id_token`: ID token (session-scoped)
- `entra_user`: Cached user info (name, email)
- `entra_roles`: Cached roles (for offline UI decisions)

**Cache TTL**: Token expiry (1 hour); roles refresh on each API call

---

## Security & Validation

### Token Validation Pipeline

```
1. Receive JWT
2. Extract header (no validation required)
3. Get unverified claims (extract `iss`)
4. Fetch JWKS from issuer (cached, 24h TTL)
5. Verify signature using JWKS
6. Validate mandatory claims (exp, iat, iss, aud, sub)
7. Extract groups from token
8. Look up RoleMapping for each group
9. Return EntraUser with mapped roles
```

### Access Control

**Decorator**: `@require_role("document_reviewer")`

```python
@app.get("/documents/{doc_id}")
@require_role("document_reviewer")
async def get_document(doc_id: str, user: EntraUser = Depends(get_current_user)):
    # Only users with document_reviewer role can access
    ...
```

### Audit Logging

All auth events logged with structured format:

```json
{
  "timestamp": "2025-12-11T15:30:45.123Z",
  "event_type": "auth.login",
  "user_object_id": "550e8400-e29b-41d4-a716-446655440000",
  "issuer": "entra_id",
  "groups": ["11111111-1111-1111-1111-111111111111"],
  "roles_assigned": ["document_reviewer"],
  "status": "success",
  "remote_ip": "192.0.2.1"
}
```

---

## Migration Path

### Phase 1: Coexistence (Keycloak + Entra)

1. RoleMapping created for existing Keycloak groups
2. Both Keycloak and Entra tokens accepted
3. Users auto-provisioned on first Entra login
4. Admin can toggle `enable_entra_id` / `enable_keycloak` flags

### Phase 2: Gradual Cutover

1. Keycloak deprecated (flag set to false)
2. New users must use Entra (SPA redirects to Entra login)
3. Existing Keycloak tokens invalidated after grace period (e.g., 30 days)

### Phase 3: Cleanup

1. Keycloak realm decommissioned
2. RoleMapping for Keycloak removed
3. `enable_keycloak` flag removed from config

