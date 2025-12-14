#!/bin/bash
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S.%3N')
echo -e "\033[0;32m$TIMESTAMP | info | Starting FastAPI application...\033[0m"

# Start the FastAPI application with uvicorn
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --server-header \
    --date-header \
    --log-level 'critical' \
    --limit-concurrency 1000 \
    --no-access-log