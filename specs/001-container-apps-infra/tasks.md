# Tasks for 001-container-apps-infra

## Phase 1 - Implementation (completed)
- [x] Create `infra/modules/container-apps` module (main.tf, variables.tf, outputs.tf, README)
- [x] Add module invocation to `infra/main.tf` and wire variables/outputs
- [x] Add module variables and document them in `data-model.md`
- [x] Add outputs for `backend_container_app_url` and `container_app_environment_id`
- [x] Add research.md, quickstart.md, and module contract
- [x] Update agent context via tools script

## Phase 1 - Follow-ups (todo)
- [x] Add role assignments for Container App managed identity (Key Vault, Cognitive Services) if required
- [x] Finalize autoscale trigger thresholds and defaults (coordinate with SRE)

## Phase 2 - Validation & Release
- [x] Run `terraform plan` in a dev subscription and validate resources
- [x] Add smoke tests to verify `backend_container_app_url` health endpoint
- [x] Add PR checklist entries for networking, security, SRE reviewers
- [x] Prepare `tasks.md` subtasks with estimates and owners

## Notes
- Changes implemented in repo but not committed by this task: none (implementation already committed on branch `001-container-apps-infra`).
- This file records current status; do not commit if you want to keep local-only edits (per instruction).