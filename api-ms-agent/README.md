# API MS Agent

A simple FastAPI backend with Microsoft Agent Framework for chat functionality.

## Setup

1. Create and activate virtual environment:
```bash
uv sync
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

3. Run the development server:
```bash
uv run fastapi dev app/main.py --port 3001
```

## API Endpoints

### Chat
- `POST /api/v1/chat/` - Send a message to the chat agent
- `GET /api/v1/chat/health` - Chat service health check

### Health
- `GET /` - Root endpoint
- `GET /health` - Application health check

## Example Request

```bash
curl -X POST http://localhost:3001/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## Development

Run tests:
```bash
uv run pytest
```

Run linter:
```bash
uv run ruff check .
```

Format code:
```bash
uv run ruff format .
```
