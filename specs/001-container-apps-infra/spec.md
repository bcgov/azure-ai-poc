# Feature Specification: Add Container Apps to infra

**Feature Branch**: `001-container-apps-infra`  
**Created**: 2025-12-14  
**Status**: Draft  
**Input**: User description: "add container apps to infra to deploy backend into container apps"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Deploy backend to Container Apps (Priority: P1)

As an infrastructure or platform engineer, I want the backend services to be buildable and deployable to Azure Container Apps so that the team can run the backend as containerized workloads in a managed serverless container platform.

**Why this priority**: Enables a deployable, scalable production environment for the backend and reduces operational overhead compared to self-managed VMs/VMSS.

**Independent Test**: Build the backend container image, deploy it to a new Container App environment, and confirm the HTTP health endpoint responds as expected.

**Acceptance Scenarios**:

1. **Given** a built container image and infra credentials, **When** the deployment job runs, **Then** a Container App resource is created and the backend becomes reachable on its configured ingress endpoint.
2. **Given** the deployed Container App, **When** traffic increases, **Then** the Container App scales according to configured scaling rules and remains healthy.

---

### User Story 2 - [Brief Title] (Priority: P2)

### User Story 2 - GitHub Actions / CI integration (Priority: P2)

As a developer, I want the repository CI/CD pipelines to build images and publish to the container registry and deploy to the Container Apps environment so deployments can be automated and reproducible.

**Why this priority**: Automates deployments and reduces manual steps for releases.

**Independent Test**: Trigger CI pipeline for a test branch that builds the image, pushes to the registry, and performs a deploy; verify the Container App is updated and passes health checks.

**Acceptance Scenarios**:

1. **Given** a PR merge to the main branch, **When** CI runs, **Then** a new image is built, pushed to the registry, and the Container App is updated to the new image with zero-downtime where possible.

---

### User Story 3 - Observability & configuration (Priority: P3)

As an SRE, I want logging, metrics, and configuration (secrets, environment variables) to be available and manageable for Container Apps so we can monitor and operate the backend in production.

**Why this priority**: Observability is required to operate services and detect regressions or outages.

**Independent Test**: Deploy with logging/metrics configured; confirm logs are present in the chosen logging sink and metrics show expected telemetry (request counts, latency).

**Acceptance Scenarios**:

1. **Given** deployment with App Insights or Log Analytics configured, **When** requests are made to the backend, **Then** traces/metrics and logs appear in the configured workspace.
2. **Given** secrets configured via Key Vault integration, **When** the Container App starts, **Then** it reads secrets through environment variables and connects to required backing services.

---

### Edge Cases

- What happens if the Container App environment region lacks requested SKUs or resource quotas? The deployment should fail early with clear error messages and guidance to retry in a supported region or request quota increases.
- How does system handle failures to pull images (missing image or registry auth issues)? The deploy step should fail and surface the registry error in CI logs; runtime should remain on the last successful revision.
- What happens during secrets rotation? New secrets should apply to new revisions without exposing secrets in logs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The infrastructure must provision an Azure Container Apps environment (Container Apps Environment / Log Analytics workspace / VNet as required) and be configurable via the repository's Infrastructure-as-Code conventions.
- **FR-002**: The infra must provision one or more Container App resources for backend services, with configurable CPU/memory, scaling rules, and ingress settings.
- **FR-003**: CI pipelines must build container images and push to the configured container registry. (Note: repository `GitHub Actions` build/push workflows already exist; modifying CI to perform automated infra deploys is out of scope for this change.)
- **FR-004**: Deployments must support secret injection via Azure Key Vault or built-in Container Apps secrets with no secrets written to logs.
- **FR-005**: Observability resources (Log Analytics workspace, Application Insights or equivalent) must be provisioned and integrated to capture logs and metrics from Container Apps.
- **FR-006**: The infra changes must be idempotent and suitable for inclusion in existing Terraform workflow and state management.
- **FR-007**: Rollback to the last known good revision must be possible via CI or Terraform orchestration.

### Key Entities *(include if feature involves data)*

- **ContainerAppEnvironment**: Represents the managed environment that runs Container Apps; attributes: name, region, log_analytics_workspace, vnet_config.
- **ContainerAppService**: Represents a specific backend Container App instance; attributes: image, cpu, memory, revisions, ingress, scale_rules, secrets.
- **CI Pipeline**: Represents the workflow that builds/pushes images and triggers deployments; attributes: triggers, registry, service principal credentials, deployment job.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A deployed Container App for the backend is reachable and returns 2xx on health endpoints in at least 3 consecutive checks within 5 minutes of deployment (P1).
- **SC-002**: CI pipeline completes image build, push, and deploy in under 15 minutes for standard changes (P2).
- **SC-003**: Logs and metrics are visible in the configured workspace within 5 minutes of first request after deployment (P3).
- **SC-004**: Rollback to the previous revision succeeds and restores healthy responses within 10 minutes when triggered from CI or manual operation (P2).

## Assumptions

- Azure subscription has permissions to create Container Apps, Log Analytics workspaces, and container registries.
- Standard security practices apply: service principals / managed identities are used for registry and infra operations.
- The existing Infrastructure-as-Code codebase is the preferred place to add infra resources; changes will follow current repo conventions.
- Existing CI/GitHub Actions build and publish workflows already exist and will not be modified as part of this change; this work is Terraform/infra-only.

## Clarifications

### Session 2025-12-14

- Q: Should we modify CI/GitHub Actions to perform automated deploys as part of this work, or keep builds/workflows unchanged and only add Terraform infra? → A: Option A (keep CI/GHA unchanged; only Terraform changes are needed).

## Out of Scope

- Migrating or re-architecting application code to suit containers beyond minimal Dockerfile adjustments (app code changes are separate tasks).
- Replacing existing production hosting if not explicitly requested; the initial change targets enabling Container Apps and deploying backend to it as an option.
- Modifying existing CI/GitHub Actions workflows to add automated infra deploys (this change is Terraform-only; CI may be updated later in a follow-up task).
