---
allowed-tools: Bash(uvicorn:*), Bash(python:*)
description: Start the FastAPI backend server on port 8000
---

# Start Backend Server

Start the FastAPI development server with auto-reload.

## Command
```bash
cd backend && ../.venv/Scripts/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## After starting:
- API available at: http://localhost:8000
- Interactive docs at: http://localhost:8000/docs
- Health check at: http://localhost:8000/health

## Verify it's running:
```bash
curl http://localhost:8000/health
```
