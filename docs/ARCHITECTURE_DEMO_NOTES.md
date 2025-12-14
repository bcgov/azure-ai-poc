# Presenter Notes – Azure AI POC Architecture Demo (15 min + 15 min Q&A)

These notes are for the presenter only. The shareable version is: `docs/ARCHITECTURE_DEMO.md`.

---

## 1) 15-minute show & tell script (minute-by-minute)

**00:00–01:00 — Set the frame**
- “Azure AI POC is a multi-agent platform: chat + tool orchestration + document grounding.”
- “Today we’re on `main`: Keycloak is the auth provider; deprecated `api/` is intentionally out of scope.”

**01:00–04:00 — Architecture overview (use Section 2 diagram)**
- Point out the deployed services:
  - Frontend (Caddy serves SPA + proxies `/api/*`)
  - Backend (`api-ms-agent` FastAPI + Microsoft Agent Framework)
  - (Optional, local only) Proxy (Caddy reverse-proxy to Azure services for local development)
- Why proxy exists (one sentence): “Azure PaaS is private-only (private endpoints; no public access outside the VNet), so the local proxy helps developers reach those endpoints during local development.”

**04:00–06:00 — Repo tour (use Section 3 diagram)**
- The four folders:
  - `api-ms-agent/` backend
  - `frontend/` React UI
  - `proxy/` Azure service proxy
  - `infra/` Terraform

**06:00–08:00 — Security model (Keycloak)**
- Frontend: Keycloak JS handles login + refresh.
- Backend: validates JWT (JWKS + audience + exp) and enforces roles via FastAPI dependencies.
- One line: “Frontend gating is UX; backend authz is the enforcement boundary.”

**08:00–13:00 — Capabilities demo**
Pick ONE of these as your primary live demo (the other becomes Q&A/backup):
- **Option A (recommended): Orchestrator**
  - Demo goal: show tool calling with clear source attribution.
- **Option B: Document grounding**
  - Demo goal: upload doc → index → ask a grounded question.

Suggested pacing:
- 2–3 minutes: Orchestrator query (MCP tool selection + response).
- 2–3 minutes: Document ingestion + grounded Q&A.

**13:00–15:00 — Azure deployment posture**
- Terraform provisions: VNet/subnets, App Insights/Log Analytics, OpenAI, Search, Cosmos, Document Intelligence, and compute.
- Backend/API is deployed on **Azure Container Apps (ACA)**.
- Frontend remains on **App Service (container)**.
- Backend uses managed identity (system-assigned when enabled) with RBAC assignments for Cosmos/OpenAI/Search.
- Close with: “Hosting shifted to ACA for the API, but the logical architecture stayed the same.”

---

## 2) Demo checklist (pre-flight)

- Backend reachable: `GET /health` returns healthy.
- Frontend can authenticate via Keycloak.
- (Optional, local only) Proxy health: `GET /healthz` on proxy.
- Azure dependencies configured in environment (or synced via `api-ms-agent/sync-azure-keys.sh`).
- Have 1 prepared document for upload (PDF/Doc) and 2 prepared questions.

---

## 3) Q&A prompts (15 minutes)

### Likely questions and crisp answers

**Q: Why have a separate proxy service?**
- A: “It’s a local-development bridge only. Azure PaaS is private-only (private endpoints; no public access outside the VNet), so the local proxy helps developers access those endpoints with consistent behavior (timeouts, WebSocket support, header stripping).”

**Q: Where is the authorization boundary?**
- A: “The backend. Frontend gating is UX only; backend validates JWT and enforces roles.”

**Q: How do you handle secrets?**
- A: “Local uses `.env`; in Azure we prefer managed identity and platform RBAC. The repo also includes an Azure key sync script for development.”

**Q: Why move the backend to ACA?**
- A: “It’s a better fit for container-native operations: revisions, scaling rules, and cleaner separation of runtime from deployment. The logical architecture stays the same.”

---

## 4) If asked about Entra (paused work) – safe talking points

Keep it short and non-committal:
- “There is a paused spike/branch exploring Entra tokens alongside Keycloak.”
- “The main complexity is deciding an authorization model for both user and service-to-service callers.”
- “We can either keep Entra as an authz source (app roles) or use Entra for authn only and store authz in our own DB—trade-offs depend on governance needs.”

---

## 5) Common gotchas (so you don’t get derailed)

- If a request returns 401/403 unexpectedly, verify the token audience and role claims.
- If document grounding looks weak, confirm the index is populated and embeddings are configured.
- If local Azure service calls fail, check the proxy’s configured endpoints and environment variables.
