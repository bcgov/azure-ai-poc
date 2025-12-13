# API MS Agent

A FastAPI backend powered by **Microsoft Agent Framework (MAF)** for intelligent chat, multi-agent orchestration, and workflow-based research capabilities.

## 🏗️ Architecture Overview

This application leverages **Microsoft Agent Framework** to provide:

- **Built-in ChatAgent**: ReAct-style reasoning with tool support (no custom loops needed)
- **WorkflowBuilder**: Deterministic multi-step workflows with explicit executors
- **MCP Tool Wrappers**: Model Context Protocol integration for BC government APIs
- **Multi-Agent Orchestration**: Coordinate specialized agents for complex queries
- **Source Attribution**: MANDATORY traceability for all LLM responses

### Agent Types

1. **ChatAgent** (`/api/v1/chat/`)
   - General-purpose conversational AI with RAG support
   - Uses MAF's built-in `ChatAgent` with `@ai_function` tools
   - Automatic ReAct reasoning loop (no custom code)
   - Supports document Q&A with Azure AI Search vector embeddings

2. **Orchestrator Agent** (`/api/v1/orchestrator/`)
   - Multi-agent coordinator for BC government data
   - Uses MAF's built-in `ChatAgent` with MCP tools:
     - **OrgBook MCP**: BC business registry searches
     - **Geocoder MCP**: BC address lookup and coordinates
     - **Parks MCP**: BC provincial parks information
   - Automatically selects and invokes appropriate tools

3. **Workflow Research Agent** (`/api/v1/research/workflow/`)
   - Explicit `WorkflowBuilder` with executor pattern
   - Deterministic 3-phase workflow: Planning → Research → Synthesis
   - Optional human-in-the-loop approval
   - Stateful execution with Cosmos DB persistence

## 🚀 Setup

### Prerequisites

- Python 3.13+
- Azure OpenAI account (gpt-4o, text-embedding-3-large)
- Azure Cosmos DB (for chat history and workflow state)
- Azure AI Search (for vector embeddings)
- Azure Document Intelligence (optional, for document parsing)

### Installation

1. Install dependencies with `uv`:
```bash
uv sync
```

2. Configure environment variables:
```bash
# Option 1: Manual setup
cp .env.example .env
# Edit .env with your Azure service credentials

# Option 2: Automated sync (requires Azure CLI + jq)
./sync-azure-keys.sh --resource-group <your-resource-group>
```

The `sync-azure-keys.sh` script automatically queries Azure for API keys and updates your `.env` file:
- Azure OpenAI API key
- Cosmos DB key
- Azure AI Search key
- Document Intelligence key

3. Start the development server:
```bash
uv run fastapi dev app/main.py --port 4000
```

## 📚 API Endpoints

### Chat Agent
- `POST /api/v1/chat/` - Conversational AI with optional RAG context
- `GET /api/v1/chat/health` - Health check

### Orchestrator Agent
- `POST /api/v1/orchestrator/query` - Query BC government data (businesses, addresses, parks)

### Workflow Research Agent
- `POST /api/v1/research/workflow/start` - Start a new research workflow
- `POST /api/v1/research/workflow/run/{run_id}` - Execute workflow steps
- `GET /api/v1/research/workflow/run/{run_id}/status` - Check workflow status
- `POST /api/v1/research/workflow/run/{run_id}/approve` - Send approval (if required)

### Documents
- `POST /api/v1/documents/upload` - Upload and index documents for RAG
- `GET /api/v1/documents/` - List uploaded documents
- `DELETE /api/v1/documents/{document_id}` - Delete a document

### Health
- `GET /` - Root endpoint
- `GET /health` - Application health check


## 🔧 Configuration

Key settings in `.env`:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# LLM Configuration (token optimization)
LLM_TEMPERATURE=0.1              # Low temp for high-confidence responses
LLM_MAX_OUTPUT_TOKENS=900        # Cap output tokens to control costs

# Cosmos DB (chat history + workflow state)
COSMOS_DB_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_DB_KEY=<key>
COSMOS_DB_DATABASE_NAME=azure-ai-poc

# Azure AI Search (vector embeddings)
AZURE_SEARCH_ENDPOINT=https://<service>.search.windows.net
AZURE_SEARCH_KEY=<key>
AZURE_SEARCH_INDEX_NAME=documents-index

# Document Intelligence (optional)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=<key>

# Environment (local uses API keys, cloud uses managed identity)
ENVIRONMENT=local
```


## 📦 Key Dependencies

- **agent-framework** : Microsoft Agent Framework SDK
- **fastapi** : Web framework
- **openai** : Azure OpenAI client
- **azure-cosmos** : Cosmos DB SDK
- **azure-search-documents** : Azure AI Search SDK
- **azure-ai-documentintelligence** : Document parsing
- **pydantic-settings** : Configuration management

## 🔐 Security Features

- **Keycloak Authentication**: JWT-based auth with role-based access control
- **Source Attribution**: MANDATORY for all LLM responses (traceability)
- **Token Optimization**: Max output tokens capped at 900, context trimming enabled
- **Insufficient Information Handling**: AI explicitly states when it lacks sufficient data
- **Managed Identity Support**: Automatic credential management in cloud environments

## 🛡️ Authentication (Keycloak + Microsoft Entra ID)

This API supports validating JWT access tokens from **either** Keycloak or Microsoft Entra ID.

### Role requirement

Protected endpoints expect the caller to have the `ai-poc-participant` role.

- **Keycloak**: role can come from common Keycloak role claim layouts (normalized server-side).
- **Entra ID**: role comes from the access token `roles` claim (app roles).

### Configuration

Use [api-ms-agent/.env.example](.env.example) as the source-of-truth for variable names.

Common auth variables:

```bash
# Enable/disable providers
KEYCLOAK_ENABLED=true
ENTRA_ENABLED=true

# Keycloak settings
KEYCLOAK_URL=https://<keycloak-host>
KEYCLOAK_REALM=<realm>
KEYCLOAK_CLIENT_ID=<client-id>

# Entra settings
ENTRA_TENANT_ID=<tenant-guid>
ENTRA_CLIENT_ID=<api-app-client-id>

# Optional overrides (defaults derived from tenant id)
ENTRA_ISSUER=https://login.microsoftonline.com/<tenant-guid>/v2.0
ENTRA_JWKS_URI=https://login.microsoftonline.com/<tenant-guid>/discovery/v2.0/keys

# JWKS caching
JWKS_CACHE_TTL_SECONDS=86400
```

### Structured auth errors

Auth failures return JSON with stable keys:

```json
{ "detail": "...", "code": "auth.*", "timestamp": "..." }
```

## 🏛️ Architecture Patterns (MAF MANDATORY)

### 1. Use Built-in ChatAgent (NOT Custom ReAct Loops)
```python
from agent_framework import ChatAgent, ai_function

@ai_function
async def my_tool(param: str) -> str:
    """Tool description for LLM."""
    return "result"

agent = ChatAgent(
    chat_client=OpenAIChatClient(credential=credential),
    instructions="You are a helpful assistant.",
    tools=[my_tool],  # MAF handles ReAct internally
)

result = await agent.run("user query")  # Built-in reasoning
```

### 2. Use WorkflowBuilder for Multi-Step Orchestration
```python
from agent_framework import WorkflowBuilder, Executor, Case, Default

workflow = (
    WorkflowBuilder()
    .set_start_executor(router)
    .add_switch_case_edge_group(
        router,
        [
            Case(condition=lambda s: s.condition_a, target=executor_a),
            Case(condition=lambda s: s.condition_b, target=executor_b),
            Default(target=default_executor),
        ],
    )
    .add_edge(executor_a, synthesizer)
    .build()
)
```

### 3. MCP Tool Wrappers for API Integration
All external API calls are wrapped as MCP tools for:
- Unified interface across different APIs
- Observability and debugging
- Reusability across agents
- Plug-and-play orchestration

## 📖 Additional Resources

- [Microsoft Agent Framework Documentation](https://github.com/microsoft/agent-framework)
- [MAF DevUI Integration](https://github.com/microsoft/agent-framework-devui)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)

## 📄 License

See parent repository for license information.
