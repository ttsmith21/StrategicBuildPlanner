---
allowed-tools: Bash(curl:*), Bash(python:*)
description: Test API endpoints with curl commands
---

# Test API Endpoints

Manual API endpoint testing using curl.

## Prerequisites
Backend must be running on http://localhost:8000

## Health Check
```bash
curl -s http://localhost:8000/health | python -m json.tool
```

## Test Ingest Endpoint
```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "project_name=Test Project" \
  -F "files=@inputs/sample_project_test.txt"
```

## View API Documentation
Open in browser: http://localhost:8000/docs

## Expected responses:
- Health: `{"status": "healthy", "service": "Strategic Build Planner API", "version": "0.1.0"}`
- Ingest: Returns `session_id` and `vector_store_id`
