# API Contracts: Entra ID + Keycloak Authentication

**Date**: 2025-12-11  
**Status**: Complete  
**Branch**: `001-migrate-entraid-auth`

---

## Overview

Authentication changes are internal to the backend auth service; no new public API endpoints are added.
All existing endpoints remain available; their behavior changes only in that they now accept Entra ID tokens in addition to (during coexistence) Keycloak tokens.

This document specifies:
1. **Token Format**: JWT structure expected by all protected endpoints
2. **Protected Endpoints**: Behavior with Entra ID tokens
3. **Error Responses**: Auth-related error codes and messages

---

## OpenAPI Schema Fragment

### SecurityScheme: BearerToken

```yaml
components:
  securitySchemes:
    BearerToken:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT token issued by MS Entra ID or Keycloak (during coexistence phase).
        Token must include:
        - iss: Issuer (https://login.microsoftonline.com/{tenant}/v2.0 for Entra)
        - sub: Subject (user object ID)
        - aud: Audience (must match API client ID)
        - exp: Expiration (must be in future)
        - roles: Application roles used for role-based access control

security:
  - BearerToken: []
```

### Example Protected Endpoint

```yaml
paths:
  /api/documents:
    get:
      summary: List documents
      operationId: list_documents
      security:
        - BearerToken: []
      responses:
        200:
          description: List of documents
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Document'
        401:
          $ref: '#/components/responses/Unauthorized'
        403:
          $ref: '#/components/responses/Forbidden'
```

---

## Error Responses

### 401 Unauthorized

**Trigger**: Missing, invalid, or expired token

**Response Body**:
```json
{
  "detail": "Invalid authentication credentials",
  "code": "auth.invalid_token",
  "timestamp": "2025-12-11T15:30:45.123Z"
}
```

**Possible reasons**:
- Token missing from `Authorization: Bearer <token>` header
- Token signature invalid (wrong issuer key)
- Token expired (`exp` claim in past)
- Token format invalid (not a valid JWT)

---

### 403 Forbidden

**Trigger**: User lacks required role/permissions

**Response Body**:
```json
{
  "detail": "Insufficient permissions: requires 'document_reviewer' role",
  "code": "auth.insufficient_role",
  "required_role": "document_reviewer",
  "user_roles": ["guest"],
  "timestamp": "2025-12-11T15:30:45.123Z"
}
```

**Possible reasons**:
- User authenticated but not assigned required role
- Token does not contain the required application role

---

### 422 Unprocessable Entity

**Trigger**: Token claims invalid or missing

**Response Body**:
```json
{
  "detail": "Token validation failed: missing 'roles' claim",
  "code": "auth.missing_claim",
  "missing_claim": "roles",
  "timestamp": "2025-12-11T15:30:45.123Z"
}
```

**Possible reasons**:
- Token missing required authorization claims (e.g., missing `roles` when a role is required)
- Issuer (`iss`) claim doesn't match a configured provider
- Audience (`aud`) doesn't match configured API audience

---

## Contract Examples

### Example 1: Protected Endpoint with Role Check

**Request**:
```bash
GET /api/documents/123 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGc...
Accept: application/json
```

**Token Contents** (decoded JWT):
```json
{
  "iss": "https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "22222222-2222-2222-2222-222222222222",
  "exp": 1702401600,
  "iat": 1702398000,
  "email": "user@bcgov.ca",
  "roles": ["ai-poc-participant"],
  "scp": "api://read"
}
```

**Response** (200 OK):
```json
{
  "id": "123",
  "title": "Sample Document",
  "status": "approved",
  "created_by": "user@bcgov.ca"
}
```

---

### Example 2: Missing Token (401)

**Request**:
```bash
GET /api/documents HTTP/1.1
Host: api.example.com
```

**Response** (401 Unauthorized):
```json
{
  "detail": "Invalid authentication credentials",
  "code": "auth.invalid_token",
  "timestamp": "2025-12-11T15:30:45.123Z"
}
```

---

### Example 3: Insufficient Role (403)

**Request**:
```bash
GET /api/documents/123/approve HTTP/1.1
Authorization: Bearer eyJhbGc...
```

**Token Contents**:
```json
{
  "roles": ["ai-poc-participant"],
  "scp": "api://read"
}
```

**Response** (403 Forbidden):
```json
{
  "detail": "Insufficient permissions: requires 'document_reviewer' role",
  "code": "auth.insufficient_role",
  "required_role": "document_reviewer",
  "user_roles": ["guest"],
  "timestamp": "2025-12-11T15:30:45.123Z"
}
```

---

## Backward Compatibility

### During Coexistence Phase

The API accepts tokens from **both** Entra ID and Keycloak:

- **Entra Token**: `iss` = `https://login.microsoftonline.com/{tenant}/v2.0`
- **Keycloak Token**: `iss` = `https://dev.loginproxy.gov.bc.ca/auth/realms/standard`

The same endpoint validates both token types; behavior is identical.

### After Keycloak Deprecation

Only Entra tokens accepted; Keycloak tokens return 401 Unauthorized.

---

## Token Validation Algorithm (OpenAPI Notes)

For reference, the backend implements this algorithm:

1. **Extract JWT**: Get `Authorization: Bearer <token>`
2. **Decode header**: No validation (identifies algorithm)
3. **Get unverified claims**: Extracts `iss` to determine issuer
4. **Fetch JWKS**: From issuer's JWKS endpoint (cached)
5. **Verify signature**: Using JWKS public key
6. **Validate claims**:
   - `exp` > now (token not expired)
   - `iat` ≤ now (token already issued)
   - `iss` matches configured issuer
   - `aud` matches API client ID
   - `sub` is non-empty UUID
7. **Extract roles**: From the token’s application roles claim (and normalize per provider)
8. **Return user object**: With roles for downstream authorization checks

---

## Future Extensions

### Optional Claims in Entra Token

To add additional claims to Entra tokens (e.g., department, cost center), configure optional claims in the app registration:

```yaml
optionalClaims:
  accessToken:
    - name: "department"
      essential: false
    - name: "cost_center"
      essential: false
```

These claims will appear in the token and can be accessed by the backend.

### Custom Scopes

To add fine-grained scopes (e.g., `api://documents.read`, `api://documents.write`), define them in the Entra app registration and include them in the `scp` claim.

---

## Implementation Notes

- All protected endpoints MUST use the `@require_auth` decorator (included token validation)
- Role-based checks use `@require_role("role_name")` decorator
- All responses include `timestamp` for traceability
- Error codes follow pattern: `auth.*` for auth-specific errors
- JWKS is cached with 24-hour TTL; manual refresh available via `/admin/cache/refresh`

