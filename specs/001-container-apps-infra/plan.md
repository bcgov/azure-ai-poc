# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Provision an Azure Container Apps environment and Container App resource(s) for the backend service using the repository's existing Terraform patterns (module-based infra under `infra/modules/*`), integrate with existing network and monitoring modules, expose configurable scaling, ingress and secret injection, and leave CI/GHA build/publish workflows unchanged (Terraform-only change).

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Terraform (HCL) - follow existing infra patterns and module versions in `infra/modules/`.
**Primary Dependencies**: Azure Provider (`azurerm`), Log Analytics workspace (module `monitoring`), Network module (module `network`), Container Registry (existing CI published images), existing backend image variable (`api_image`).
**Storage**: not applicable for infra changes beyond Log Analytics and potential Key Vault for secrets.
**Testing**: Terraform plan/apply in non-prod subscription and local `az`/`terraform` validation; integration smoke tests hitting health endpoints.
**Target Platform**: Azure Container Apps running in a Container Apps Environment with VNet integration.
**Project Type**: Backend infra component; module will live under `infra/modules/container-apps` and be referenced from `infra/main.tf`.
**Performance Goals**: Default scaling to handle moderate load for backend (P95 latency and autoscale thresholds TBD in follow-up tasks).
**Constraints**: Use existing VNet subnet `container_apps_subnet_id` provided by `module.network` outputs; Log Analytics workspace integration via `module.monitoring`.
**Scale/Scope**: Support single backend service initially; addability for more services via module variables.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

- [GATE] The feature must not introduce changes that require additional platform subscriptions or elevated permissions outside the current subscription owner.
- [GATE] The feature must follow existing IaC conventions and avoid monolithic changes to the repo structure.
- [GATE] Sensitive values must utilize Key Vault or Terraform variable `sensitive` flags.

Gates: all satisfied — this plan follows existing module patterns in `infra/`, uses existing `module.network` subnet outputs and `module.monitoring` log analytics workspace, and uses the existing variable patterns for images and tags. No cross-subscription provisioning is required.

## Project Structure

### Project Structure Decision
- Add new module at `infra/modules/container-apps` following existing module conventions (main.tf, variables.tf, outputs.tf, README).
- Reference the new module from `infra/main.tf` with `depends_on = [module.network, module.monitoring]`.

## Plan Phases

### Phase 0: Research
- Create `research.md` capturing decisions about network integration, monitoring, identities, and scaling defaults. (done)

### Phase 1: Design & Implementation (High-level tasks)
1. Create `infra/modules/container-apps` module implementing Container Apps Environment and container app resources. (done)
2. Add module invocation in `infra/main.tf` and wire required variables/outputs. (done)
3. Add necessary variables to `infra/variables.tf` and document them in `data-model.md`. (module variables added; documented in `data-model.md`)
4. Add outputs for `backend_container_app_url` and environment id. (done)
5. Add role assignments and managed identity configuration mirroring patterns from other modules (e.g., `module.backend`) — TODO: add specific role assignments if required by services (Key Vault, Cognitive Services).
6. Create `specs/001-container-apps-infra/contracts/module-interface.md` and `quickstart.md`. (done)
7. Validate with `terraform plan` in a dev subscription and smoke-test backend health endpoint. (TODO)

### Phase 2: Tasks & PR
- Break tasks into `tasks.md`, prepare PR template entries, and ensure reviewers include networking, security, and SRE.

### Agent Context Update
- Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot` to add new module context to AI assistant knowledge base.

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
