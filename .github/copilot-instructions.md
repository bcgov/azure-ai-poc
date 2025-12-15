# azure-ai-poc Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-14

## Active Technologies
- Python 3.13 (api-ms-agent) + TypeScript (frontend) + FastAPI, httpx, openai (Azure), azure-cosmos, agent-framework, structlog (001-optimize-agent-performance)
- Azure Cosmos DB (chat history, metadata, workflow persistence); Azure Search / Document Intelligence as dependencies (001-optimize-agent-performance)

- Terraform (HCL) - follow existing infra patterns and module versions in `infra/modules/`. + Azure Provider (`azurerm`), Log Analytics workspace (module `monitoring`), Network module (module `network`), Container Registry (existing CI published images), existing backend image variable (`api_image`). (001-container-apps-infra)

## Project Structure

```text
src/
tests/
```

## Commands

# Add commands for Terraform (HCL) - follow existing infra patterns and module versions in `infra/modules/`.

## Code Style

Terraform (HCL) - follow existing infra patterns and module versions in `infra/modules/`.: Follow standard conventions

## Recent Changes
- 001-optimize-agent-performance: Added Python 3.13 (api-ms-agent) + TypeScript (frontend) + FastAPI, httpx, openai (Azure), azure-cosmos, agent-framework, structlog

- 001-container-apps-infra: Added Terraform (HCL) - follow existing infra patterns and module versions in `infra/modules/`. + Azure Provider (`azurerm`), Log Analytics workspace (module `monitoring`), Network module (module `network`), Container Registry (existing CI published images), existing backend image variable (`api_image`).

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
