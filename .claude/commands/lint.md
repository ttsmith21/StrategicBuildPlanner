---
allowed-tools: Bash(black:*), Bash(python:*)
description: Format Python code with black
---

# Lint and Format Code

Run code formatters to ensure consistent style.

## Format Python with Black
```bash
cd backend && ../.venv/Scripts/black app/
```

## Check formatting without changes
```bash
cd backend && ../.venv/Scripts/black --check app/
```

## Format specific file
```bash
../.venv/Scripts/black backend/app/routers/ingest.py
```

## Configuration
Black uses default settings:
- Line length: 88 characters
- Python 3.11+ syntax
