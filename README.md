# Azure AI POC - Multi-Agent Platform

A production-ready FastAPI backend providing intelligent agent capabilities with two complementary implementations:

1. **Multi-Tenant LangGraph Platform** (`/api`) - Production-ready agent optimization with Agent Lightning
2. **Microsoft Agent Framework Platform** (`/api-ms-agent`) - MAF-based multi-agent orchestration and research

## 🏗️ Platform Architectures

### 1. Multi-Tenant Platform (`/api`) - LangGraph + Agent Lightning ⚠️ **DEPRECATED**
> **Note**: This LangGraph-based implementation is deprecated. Please use the Microsoft Agent Framework platform (`/api-ms-agent`) for new projects.

A production-ready multi-tenant backend providing:
- **Multi-tenant Architecture**: Complete tenant isolation for data, authentication, and resource management
- **Document Management**: Upload, process, and manage documents with Azure Blob Storage and Cosmos DB
- **AI Chat**: Chat functionality powered by Azure OpenAI with context-aware responses
- **Authentication**: Secure JWT-based authentication with tenant isolation
- **Observability**: Comprehensive monitoring with OpenTelemetry, Prometheus metrics, and structured logging

#### Agent Lightning ⚡
An autonomous agent optimization platform that continuously improves LangGraph agent performance through:
- **Autonomous Optimization**: Automatically identifies and applies performance improvements
- **ROI Tracking**: Monitors cost savings, latency improvements, and success rate increases
- **Performance Monitoring**: Real-time metrics collection and analysis
- **Multi-Agent Management**: Deploy and manage multiple optimized agents per tenant
- **Cost Control**: Per-tenant cost limits, rate limiting, and audit logging

### 2. Microsoft Agent Framework Platform (`/api-ms-agent`) - MAF
A MAF-based intelligent agent system providing:
- **Built-in ChatAgent**: ReAct-style reasoning with tool support (no custom loops)
- **WorkflowBuilder**: Deterministic multi-step workflows with explicit executors
- **Multi-Agent Orchestration**: Coordinate specialized agents for complex queries
- **MCP Tool Wrappers**: Model Context Protocol integration for BC government APIs (OrgBook, Geocoder, Parks)
- **Source Attribution**: MANDATORY traceability for all LLM responses

#### MAF Agent Types
1. **ChatAgent** - General-purpose conversational AI with RAG support
2. **Orchestrator Agent** - Multi-agent coordinator for BC government data queries
3. **Workflow Research Agent** - Deterministic 3-phase workflow (Planning → Research → Synthesis) with optional human-in-the-loop

## 🚀 Quick Start

### ✅ MAF Platform (`/api-ms-agent`) - **RECOMMENDED**
```bash
cd api-ms-agent
uv sync

# Option 1: Manual configuration
cp .env.example .env

# Option 2: Automated Azure key sync (requires Azure CLI + jq)
./sync-azure-keys.sh --resource-group <your-resource-group>

uv run fastapi dev app/main.py --port 4000
```

## 📚 API Endpoints

### Multi-Tenant Platform (`/api`)
- **Documents**: `/api/v1/documents/*` - Upload, manage documents
- **Chat**: `/api/v1/chat/*` - AI chat with LangGraph agents
uv run fastapi dev app/main.py --port 4000
```

### ⚠️ Multi-Tenant Platform (`/api`) - **DEPRECATED (Maintenance Only)**
```bash
cd api
uv sync
cp .env.example .env  # Configure your Azure services
uv run fastapi dev app/main.py --port 3000
```

## 📚 API Endpoints

### ✅ MAF Platform (`/api-ms-agent`) - **RECOMMENDED**
```bash
- **Documents**: `/api/v1/documents/*` - Document upload and indexing

### ⚠️ Multi-Tenant Platform (`/api`) - **DEPRECATED**
- **Documents**: `/api/v1/documents/*` - Upload, manage documents
# Agent Lightning tests only
uv run pytest tests/integration/test_agent_lightning*.py -v
```

## 🔧 Development

### ⚠️ Multi-Tenant Platform - **DEPRECATED**-cov-report=html

# Agent Lightning tests only
uv run pytest tests/integration/test_agent_lightning*.py -v
```

### MAF Platform
```bash
cd api-ms-agent
uv run pytest -v

# Specific test suites
uv run pytest tests/test_chat.py tests/test_workflow_research.py -v
```

## 🔧 Development

### Code Quality (Both Platforms)

**Linting:**
```bash
cd api  # or api-ms-agent
uv run ruff check .
```

**Formatting:**
```bash
uv run ruff format .
```

**Type Checking:**
```bash
uv run mypy app/
```

### Project Structure

```
azure-ai-poc/
├── api/                          # ⚠️ DEPRECATED - Multi-tenant LangGraph platform
│   ├── app/
│   │   ├── auth/                 # Authentication logic
│   │   ├── core/                 # Core utilities and configurations
│   │   │   ├── agent_lightning_*.py  # Agent Lightning modules
│   │   │   ├── performance.py    # Performance optimization
│   │   │   └── optimization_roi_calculator.py  # ROI calculations
│   │   ├── middleware/           # Custom middleware
│   │   ├── models/               # Data models
│   │   │   ├── tenant_models.py  # Multi-tenant models
│   │   │   └── optimization_models.py  # Agent Lightning models
│   │   ├── routers/              # API endpoints
│   │   │   ├── agent_lightning*.py  # Agent Lightning endpoints
│   │   │   └── chat.py           # LangGraph chat endpoints (deprecated)
│   │   └── services/             # Business logic
│   │       ├── advanced_agent_service.py  # LangGraph agents (deprecated)
│   │       └── optimization_analytics_service.py  # Analytics
│   ├── tests/                    # Test suite
│   └── docs/                     # Documentation
│       └── AGENT_LIGHTNING_SETUP.md
│
├── api-ms-agent/                 # ✅ RECOMMENDED - Microsoft Agent Framework platform
│   ├── app/
│   │   ├── auth/                 # Keycloak authentication
│   │   ├── config.py             # Settings (supports managed identity)
│   │   ├── routers/              # API endpoints
│   │   │   ├── chat.py           # MAF ChatAgent with RAG
│   │   │   ├── orchestrator.py   # Multi-agent coordinator
│   │   │   └── workflow_research.py  # WorkflowBuilder research
│   │   └── services/             # Agent services
│   │       ├── chat_agent.py     # Built-in ChatAgent
│   │       ├── orchestrator_agent.py  # MAF orchestration
│   │       ├── workflow_research_agent.py  # Workflow executors
│   │       └── mcp/              # MCP tool wrappers
│   │           ├── orgbook_mcp.py    # BC business registry
│   │           ├── geocoder_mcp.py   # BC address lookup
│   │           └── parks_mcp.py      # BC parks data
│   ├── tests/                    # Test suite
│   ├── sync-azure-keys.sh        # Automated Azure credential sync
│   └── README.md                 # Detailed MAF documentation
│
├── frontend/                     # React frontend
├── infra/                        # Terraform infrastructure
└── docker-compose.yml
```

## 🔑 Key Technologies

### Common Infrastructure
**Platform-Specific

**MAF Platform (`/api-ms-agent`) - RECOMMENDED:**
- **agent-framework** (Microsoft Agent Framework SDK)
- **WorkflowBuilder** for deterministic workflows
- **@ai_function** decorators for tool definitions
- **MCP Protocol** for BC government API integration
- **Keycloak** for authentication

**Multi-Tenant Platform (`/api`) - DEPRECATED:**
- **LangGraph** for agent workflow orchestration (deprecated)
- **LangChain** for RAG and tool integration
- **OpenTelemetry** for observability
- **Prometheus** for metrics collection
- **JWT-based multi-tenant auth**
**Multi-Tenant Platform (`/api`):**
- **LangGraph** for agent workflow orchestration
- **LangChain** for RAG and tool integration
- **OpenTelemetry** for observability
- **Prometheus** for metrics collection
- **JWT-based multi-tenant auth**

**MAF Platform (`/api-ms-agent`):**
- **agent-framework** (Microsoft Agent Framework SDK)
- **WorkflowBuilder** for deterministic workflows
- **@ai_function** decorators for tool definitions
- **MCP Protocol** for BC government API integration
- **Keycloak** for authentication

## 🔐 Security Features

### Multi-Tenant Platform
- Multi-tenant data isolation
- Per-tenant cost tracking and limits
- Rate limiting and audit logging
- JWT-based authentication

### MAF Platform (`/api-ms-agent`) Authentication

The MAF backend supports **Keycloak + Microsoft Entra ID** JWT validation (coexistence).

- Configure auth via `api-ms-agent/.env` using [api-ms-agent/.env.example](api-ms-agent/.env.example)
- Toggle providers with `KEYCLOAK_ENABLED` and `ENTRA_ENABLED`
- Entra authorization uses the access token `roles` claim (app roles). Protected endpoints typically require `ai-poc-participant`.
- OpenTelemetry security monitoring

### Frontend Authentication (Entra SSO)

The React SPA (`/frontend`) uses MSAL.js to authenticate users with Microsoft Entra ID and acquire access tokens for API calls.

- Configure Entra values in `frontend/.env` (see `frontend/.env.example`)
- Required variables: `VITE_ENTRA_TENANT_ID`, `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_AUTHORITY`, `VITE_API_SCOPES`
- Tokens are cached in `sessionStorage` and injected into API requests as `Authorization: Bearer <token>`
- User name and roles (from the token `roles` claim) are displayed in the header after login

Setup guide: [frontend/ENTRA_ID_SETUP.md](frontend/ENTRA_ID_SETUP.md)

- Rate limiting and audit logging
- JWT-based authentication
- OpenTelemetry security monitoring

## 📖 Documentation*: See `/infra/` for Terraform deployment configurations
- **Frontend**: See `/frontend/` for React application setup

## 🎯 Use Cases

### ⚠️ When to Use Multi-Tenant Platform (`/api`) - **DEPRECATED**
> **Migration Recommendation**: Migrate to MAF Platform (`/api-ms-agent`) for new development.
## 📖 Documentation

- **✅ MAF Platform (RECOMMENDED)**: See `/api-ms-agent/README.md` for detailed MAF architecture and patterns
- **⚠️ Multi-Tenant Platform (DEPRECATED)**: See `/api/docs/AGENT_LIGHTNING_SETUP.md` for Agent Lightning setup (maintenance only)
- **Infrastructure**: See `/infra/` for Terraform deployment configurations
- **Frontend**: See `/frontend/` for React application setup
### ✅ When to Use MAF Platform (`/api-ms-agent`) - **RECOMMENDED**
- Need Microsoft Agent Framework's built-in patterns
- Require deterministic workflow orchestration (WorkflowBuilder)
- Want ReAct-style agents without custom loops (built-in ChatAgent)
- Need MCP protocol integration for external APIs
- Building BC government data integration applications
- Want human-in-the-loop approval workflows

## 💡 Example Usage

## 💡 Example Usage

### ✅ MAF Platform - Orchestrator Query (RECOMMENDED)
curl -X POST http://localhost:4000/api/v1/orchestrator/query \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "Find information about TELUS Communications Inc"}'

# Start research workflow with approval
curl -X POST http://localhost:4000/api/v1/research/workflow/start \
  -d '{
    "topic": "Research climate impacts in BC, require approval",
    "require_approval": true
  }'
```

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
    "require_approval": true
  }'
```

### ⚠️ Multi-Tenant Platform - Agent Lightning (DEPRECATED)
```bash
# Start autonomous optimization
curl -X POST http://localhost:3000/api/v1/agent-lightning/optimize \
  -H "Authorization: Bearer <token>" \
  -d '{"tenant_id": "tenant-123"}'

# Get optimization metrics
curl http://localhost:3000/api/v1/agent-lightning/metrics?tenant_id=tenant-123
```

## 📄 License