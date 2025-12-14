# Research: Container Apps infra decisions

## Decision 1: Module pattern
- Decision: Implement `infra/modules/container-apps` mirroring existing module conventions (inputs, outputs, tags, depends_on).
- Rationale: Repository already organizes services as modules; keeping same pattern ensures maintainability and consistent lifecycle.
- Alternatives: Add Container Apps directly at root `main.tf` (rejected due to inconsistency and maintainability).

## Decision 2: Network integration
- Decision: Use existing `module.network` output `container_apps_subnet_id` and integrate Container Apps Environment into that subnet.
- Rationale: Network module already exposes subnet and NSG rules; keeps networking consistent and secure.
- Alternatives: Deploy Container Apps publicly without VNet (rejected for private backend and security needs).

## Decision 3: Monitoring
- Decision: Associate Container Apps Environment with existing Log Analytics workspace (`module.monitoring.log_analytics_workspace_id`) for logs/metrics.
- Rationale: Monitoring module is already provisioned and used across repo; centralizes telemetry.

## Decision 4: Image source and CI
- Decision: Use repository's existing CI/GHA build/push workflows to publish container images; this plan will not modify CI workflows.
- Rationale: User clarified CI is already present and out-of-scope; limits blast radius.

## Decision 5: Secrets and identities
- Decision: Use SystemAssigned identity for Container App and grant necessary role assignments to access Key Vault, Cognitive Services, etc., as required (follow pattern used for `module.backend`).
- Rationale: Existing modules use managed identities and role assignments for secure access to resources.

## Decision 6: Scaling defaults
- Decision: Provide module variables for `min_replicas`, `max_replicas`, and autoscale rules based on CPU or request metrics (defaults conservative: min=1, max=5).
- Rationale: Reasonable defaults reduce risk; teams can tune later.

## Open item (low risk)
- Clarify desired autoscale triggers/thresholds for production (defer to Phase 1 or operations team).
