# Azure AI POC - Multi-Tenant Agent Platform

A production-ready multi-tenant FastAPI backend providing document management, AI chat functionality, and Agent Lightning - an autonomous agent optimization platform.

## 🚀 Features

### Core Platform
- **Multi-tenant Architecture**: Complete tenant isolation for data, authentication, and resource management
- **Document Management**: Upload, process, and manage documents with Azure Blob Storage and Cosmos DB
- **AI Chat**: Chat functionality powered by Azure OpenAI with context-aware responses
- **Authentication**: Secure JWT-based authentication with tenant isolation
- **Observability**: Comprehensive monitoring with OpenTelemetry, Prometheus metrics, and structured logging

### Agent Lightning ⚡
An autonomous agent optimization platform that continuously improves LangGraph agent performance through:

- **Autonomous Optimization**: Automatically identifies and applies performance improvements
- **ROI Tracking**: Monitors cost savings, latency improvements, and success rate increases
- **Performance Monitoring**: Real-time metrics collection and analysis
- **Multi-Agent Management**: Deploy and manage multiple optimized agents per tenant
- **Cost Control**: Per-tenant cost limits, rate limiting, and audit logging



## 🧪 Testing

### Run All Tests

```bash
cd api
uv run pytest -v
```

### Run with Coverage

```bash
uv run pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run Specific Test Suite

```bash
# Agent Lightning tests only
uv run pytest tests/integration/test_agent_lightning*.py tests/integration/test_*optimization*.py -v

# Unit tests only
uv run pytest tests/unit -v
```


## 🔧 Development

### Code Quality Tools

**Linting:**
```bash
cd api
uv run ruff check .
```

**Type Checking:**
```bash
uv run mypy app/
```

**Formatting:**
```bash
uv run ruff format .
```

### Project Structure

```
azure-ai-poc/
├── api/                          # FastAPI backend
│   ├── app/
│   │   ├── auth/                 # Authentication logic
│   │   ├── core/                 # Core utilities and configurations
│   │   │   ├── agent_lightning_*.py  # Agent Lightning modules
│   │   │   ├── performance.py    # Performance optimization
│   │   │   └── optimization_roi_calculator.py  # ROI calculations
│   │   ├── middleware/           # Custom middleware
│   │   │   └── agent_lightning_error_handler.py  # Error handling
│   │   ├── models/               # Data models
│   │   ├── routers/              # API endpoints
│   │   │   └── agent_lightning*.py  # Agent Lightning endpoints
│   │   └── services/             # Business logic
│   │       └── optimization_analytics_service.py  # Analytics
│   ├── tests/                    # Test suite
│   │   ├── integration/          # Integration tests
│   │   └── unit/                 # Unit tests
│   └── docs/                     # Documentation
│       └── AGENT_LIGHTNING_SETUP.md  # Agent Lightning guide
├── frontend/                     # React frontend
├── infra/                        # Terraform infrastructure
└── docker-compose.yml
```


## 📄 License

See [LICENSE](LICENSE) file for details.
