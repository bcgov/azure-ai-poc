# azure-ai-poc Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-11

## Active Technologies
- Python 3.13 (api-ms-agent), TypeScript 5.x (frontend) + FastAPI, Pydantic, python-jose/PyJWT, httpx, azure-identity, msal (frontend) (001-migrate-entraid-auth)
- Cosmos DB, Azure Search (no auth layer changes needed) (001-migrate-entraid-auth)

- Python 3.13 (api-ms-agent), TypeScript 5.x (frontend) + FastAPI, Pydantic, python-jose/pyjwt, httpx, azure-identity (for infra), azure-ad Terraform provider (001-migrate-entraid-auth)

## Project Structure

```text
api-ms-agent/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11 (backend), TypeScript 5.x (frontend): Follow standard conventions

## Recent Changes
- 001-migrate-entraid-auth: Added Python 3.11 (backend), TypeScript 5.x (frontend) + FastAPI, Pydantic, python-jose/PyJWT, httpx, azure-identity, msal (frontend)

- 001-migrate-entraid-auth: Added Python 3.11 (backend), TypeScript 5.x (frontend) + FastAPI, Pydantic, python-jose/pyjwt, httpx, azure-identity (for infra), azure-ad Terraform provider

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
