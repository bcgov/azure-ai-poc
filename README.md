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

**[📖 Full Agent Lightning Documentation →](api/docs/AGENT_LIGHTNING_SETUP.md)**

## 📋 Prerequisites

- **Python 3.13+** (uses `uv` for dependency management)
- **Docker & Docker Compose** (for local development)
- **Azure Account** with the following resources:
  - Azure OpenAI Service
  - Azure Cosmos DB
  - Azure Blob Storage
  - Azure Application Insights (optional, for production monitoring)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd azure-ai-poc
```

### 2. Set Up Environment Variables

Create `.env` files in both `api/` and `frontend/` directories:

**`api/.env`:**
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Cosmos DB
AZURE_COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
AZURE_COSMOS_KEY=your-cosmos-key
AZURE_COSMOS_DATABASE_NAME=ai-poc-db

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER_NAME=documents

# Application Settings
SECRET_KEY=your-secret-key-for-jwt-signing
ENVIRONMENT=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Agent Lightning (Optional)
AGENT_LIGHTNING_COST_LIMIT_USD=1000.0  # Default per-tenant monthly limit
AGENT_LIGHTNING_RATE_LIMIT_PER_MIN=60   # General requests per minute
AGENT_LIGHTNING_OPTIMIZATION_RATE_LIMIT_PER_HOUR=10  # Optimization requests per hour
```

**`frontend/.env`:**
```bash
VITE_API_URL=http://localhost:8000
```

### 3. Install Dependencies

**Backend (API):**
```bash
cd api
uv sync --all-extras  # Installs all dependencies including dev tools
```

**Frontend:**
```bash
cd frontend
npm install
```

## 🚀 Running the Application

### Option 1: Docker Compose (Recommended for Development)

```bash
# Start all services (API + Frontend + Cosmos DB Emulator)
docker-compose up

# API available at: http://localhost:8000
# Frontend available at: http://localhost:5173
# Cosmos DB Emulator: https://localhost:8081
```

### Option 2: Local Development (without Docker)

**Start Cosmos DB Emulator:**
```bash
docker run --detach --publish 8081:8081 --publish 1234:1234 \
  mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview
```

**Start API:**
```bash
cd api
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Start Frontend:**
```bash
cd frontend
npm run dev
```

## 📚 API Documentation

Once the API is running, access the interactive documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

#### Documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents` - List user's documents
- `GET /api/documents/{id}` - Get document details
- `DELETE /api/documents/{id}` - Delete document

#### Chat
- `POST /api/chat` - Send chat message and get AI response

#### Agent Lightning ⚡
- `POST /api/agent-lightning/agents` - Deploy optimized agent
- `GET /api/agent-lightning/agents` - List deployed agents
- `POST /api/agent-lightning/optimize/{agent_name}` - Trigger optimization
- `GET /api/agent-lightning/metrics/{agent_name}` - Get agent metrics
- `GET /api/agent-lightning/roi/{agent_name}` - Get ROI analytics

**[📖 Full Agent Lightning API Reference →](api/docs/AGENT_LIGHTNING_SETUP.md#api-endpoints)**

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

### Test Coverage Summary

- **Agent Lightning Observability**: 100% coverage
- **Agent Lightning Metrics**: 100% coverage
- **ROI Calculator**: 100% coverage
- **Optimization Analytics**: 96% coverage
- **Error Handler**: 96% coverage
- **Performance Module**: 96% coverage
- **Security Module**: 99% coverage

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

## 🔒 Security

### Authentication
- JWT-based authentication with HS256 algorithm
- Secure password hashing with bcrypt
- Token expiration and refresh mechanisms

### Multi-Tenant Isolation
- Database-level tenant isolation
- API-level tenant filtering
- Resource access controls

### Agent Lightning Security
- **Input Validation**: Regex-based validation for all inputs
- **Rate Limiting**: 60 requests/min general, 10 optimizations/hour per tenant
- **Cost Controls**: Configurable per-tenant monthly cost limits ($1000 default)
- **Audit Logging**: All optimization decisions and security events logged

## 📊 Monitoring & Observability

### Metrics (Prometheus)
Access metrics at: http://localhost:8000/metrics

Key metrics:
- `agent_lightning_optimization_duration_seconds` - Optimization latency
- `agent_lightning_cost_total` - Total costs per tenant/agent
- `agent_lightning_success_rate` - Agent success rates
- `http_requests_total` - HTTP request counts

### Tracing (OpenTelemetry)
- Distributed tracing for all API requests
- Automatic instrumentation for FastAPI and HTTPX
- Export to Azure Application Insights or Jaeger

### Logging (Structlog)
- Structured JSON logging
- Tenant-aware log correlation
- Configurable log levels per environment

## 🚢 Deployment

### Azure Deployment

**Prerequisites:**
- Azure subscription
- Terraform installed
- Azure CLI authenticated

**Deploy Infrastructure:**
```bash
cd infra
terraform init
terraform plan
terraform apply
```

**Deploy Application:**
```bash
# Build and push Docker images
docker build -t your-registry.azurecr.io/api:latest ./api
docker push your-registry.azurecr.io/api:latest

# Deploy to Azure Container Apps or AKS
az containerapp update --name api-app --image your-registry.azurecr.io/api:latest
```

### Environment Variables for Production

Ensure these are configured in your production environment:
- Set `ENVIRONMENT=production`
- Use Azure Key Vault for secrets
- Configure Application Insights for monitoring
- Enable HTTPS and proper CORS settings

**[📖 Full Deployment Guide →](api/docs/AGENT_LIGHTNING_SETUP.md#deployment)**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow

1. Create tests for new features
2. Ensure all tests pass (`uv run pytest`)
3. Run linting (`uv run ruff check .`)
4. Update documentation as needed

## 📄 License

See [LICENSE](LICENSE) file for details.

## 📞 Support

For issues and questions:
- **Agent Lightning Documentation**: [api/docs/AGENT_LIGHTNING_SETUP.md](api/docs/AGENT_LIGHTNING_SETUP.md)
- **GitHub Issues**: [Create an issue](../../issues)
- **API Documentation**: http://localhost:8000/docs

## 🔗 Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)