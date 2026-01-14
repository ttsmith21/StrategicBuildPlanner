---
allowed-tools: Bash(pytest:*), Bash(python:*)
description: Run backend pytest suite with coverage report
---

# Run Backend Tests

Execute the full pytest test suite with coverage reporting.

## Run all tests
```bash
cd backend && ../.venv/Scripts/pytest app/tests/ -v
```

## Run with coverage
```bash
cd backend && ../.venv/Scripts/pytest app/tests/ -v --cov=app --cov-report=term-missing
```

## Run specific test file
```bash
cd backend && ../.venv/Scripts/pytest app/tests/test_ingest.py -v
```

## Run with output visible
```bash
cd backend && ../.venv/Scripts/pytest app/tests/ -v -s
```

## Expected results:
- All tests should pass
- Coverage should be >80% for services/ and routers/
