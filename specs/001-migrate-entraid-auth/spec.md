# Feature Specification: Add MS Entra ID Authentication alongside Keycloak

**Feature Branch**: `001-migrate-entraid-auth`  
**Created**: 2025-12-11  
**Status**: Draft  
**Input**: User description: "Add MS Entra ID for authentication along with Keycloak side-by-side"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin enables Entra ID alongside Keycloak (Priority: P1)

An administrator configures the application to accept tokens issued by MS Entra ID while continuing to accept Keycloak tokens during a transition period.

**Why this priority**: This enables a safe migration path without locking out existing users and integrations.

**Independent Test**: Configure Entra ID values in environment, restart the service, and verify token validation succeeds for valid Entra tokens and valid Keycloak tokens, and rejects invalid tokens.

**Acceptance Scenarios**:

1. **Given** Entra ID configuration is present, **When** the backend receives a valid Entra-issued token, **Then** the request is accepted when token is valid and required claims are present.
2. **Given** Keycloak configuration is present, **When** the backend receives a valid Keycloak-issued token, **Then** the request is accepted when token is valid and required claims are present.
3. **Given** an invalid token or wrong issuer/audience, **When** the backend receives a request, **Then** it responds with an HTTP 401/403 as appropriate.

---

### User Story 2 - Users authenticate via Entra SSO or existing Keycloak (Priority: P2)

Application users sign in via MS Entra ID SSO or continue using Keycloak during migration and can access application features based on role/claim mappings.

**Why this priority**: This provides users with a single sign-on experience and keeps authorization consistent across services.

**Independent Test**: Obtain a bearer token from Entra and a bearer token from Keycloak and call the same protected API endpoint to verify access based on roles and claims.

**Acceptance Scenarios**:

1. **Given** a user with a valid Entra ID account and correct roles, **When** the user authenticates and calls a protected API, **Then** the API returns status 200 and the expected data.
2. **Given** a user without required roles/claims, **When** the user calls the protected API, **Then** the API returns HTTP 403 Forbidden.

---

### User Story 3 - Cutover and rollback control (Priority: P3)

Maintain the ability to control cutover and rollback (including keeping both providers enabled), so migration can be phased without downtime.

**Why this priority**: To minimize downtime and provide a safe migration path while ensuring users are not locked out.

**Independent Test**: Configure backend to accept tokens from both Keycloak and Entra ID, test both sources for valid/invalid tokens, and verify graceful failover.

**Acceptance Scenarios**:

1. **Given** both Keycloak and Entra ID are configured and enabled, **When** the user authenticates with either provider, **Then** the app accepts valid tokens from either provider.
2. **Given** an admin disables Keycloak acceptance (cutover), **When** a request contains a Keycloak token, **Then** the request is rejected with HTTP 401/403.
3. **Given** an admin re-enables Keycloak acceptance (rollback), **When** a request contains a Keycloak token, **Then** the request is accepted if valid.

---

### Edge Cases

- Transition period: users with old Keycloak tokens may need to re-authenticate; ensure token refresh expectations are documented.
- Claim name mismatches: name and role claim formats may differ between Keycloak and Entra; map and verify expected claim keys.
- Invalid or missing claims: if roles are missing, ensure default deny policy and provide clear error message.
- Token clock skew: support small clock-skew allowance when validating token times to avoid false rejections.
- Deleted users: if a user no longer exists in Entra, requests with valid tokens should be denied and logs generated for audit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate and accept JWTs issued by MS Entra ID (Azure AD) and Keycloak during a transition period.
- **FR-002**: System MUST validate token signatures using each provider’s published signing keys and enforce issuer/audience claims per provider configuration.
- **FR-003**: System MUST support role/claim-based authorization using a consistent application role model across providers.
- **FR-004**: System MUST provide configuration options for Entra ID settings (tenant, audience/client IDs, authority/issuer) without removing existing Keycloak settings.
- **FR-005**: System MUST include logging and audit events for successful and failed authentication and authorization checks and include which provider was used.
- **FR-006**: System MUST allow an administrator to enable/disable acceptance of Entra tokens and Keycloak tokens independently (to support coexistence, cutover, and rollback).

### Decisions (captured)

- **Migration strategy**: Coexistence (Keycloak + Entra ID side-by-side) until an admin-controlled cutover.
- **Roles/claims mapping**: Use Entra **app roles**, assigned to **groups** for users; applications use application roles for client-credentials flows.
- **User provisioning and sync**: Identity-provider managed only; no user sync to a local database.

### Key Entities *(include if feature involves data)*

- **User**: Represents a person authenticated by an identity provider. Attributes: user_id, email, display_name, roles/claims.
- **Token**: JWT containing issuer, subject, audience, issued-at/expiry, and role/claim attributes.
- **Role Mapping**: A configuration entity that maps identity provider claims/groups to application roles.
- **EntraConfig**: Tenant and application configuration items (tenant_id, client_id, authority, JWKS URI).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of representative API calls protected by authentication continue to succeed after migration with valid Entra tokens.
- **SC-002**: Admin can change Entra configuration values via environment and redeploy without code changes, and authentication updates without downtime.
- **SC-003**: Authorization enforcement is consistent for role-based access; 100% of role-based acceptance tests pass for users with mapped roles.
- **SC-004**: New authentication integration reduces authentication-related errors in logs by at least 80% for affected endpoints compared to pre-migration error volume, after cutover.

## Assumptions

- An Entra ID tenant and required admin permissions are available to register an application and issue client credentials.
- Roles used by the application are available or can be configured within Entra ID (app roles / group assignments).
- Secrets (client id/secret) can be stored in one of the supported secrets stores and set as environment variables during deploy.
- Existing Keycloak tokens will remain accepted during the coexistence period until an admin-controlled cutover.

## Non-functional Considerations

- Security: Token validation must use strong cryptography; use short expiry and log failure reasons for auditing.
- Operational: Provide clear rollout plan, with testing and canary rollout, and rollback procedure.
- Documentation: Update README and infra variable docs to document Entra settings and clearly describe coexistence/cutover behavior.

## Deliverables

- Backend: Token validation and role/claim mapping support for Entra ID and Keycloak side-by-side.
- Frontend: Add Entra SSO support without breaking existing Keycloak flows during migration.
- Infra: Terraform updates to set Entra ID variables and secrets for applications and frontends.
- Tests: Integration tests for token validation, claims mapping, and protected endpoint access with Entra tokens.

## Next Steps

1. Confirm and document the coexistence configuration strategy per environment.
2. Update backend authentication to validate both issuers and enforce consistent authorization.
3. Add Entra SSO support in the frontend while keeping Keycloak working.
4. Define a cutover procedure and rollback procedure.
5. Update docs and run integration tests to validate success criteria.
