---
paths:
  - "backend/app/tests/**/*.py"
  - "**/*test*.py"
---

# Testing Standards

## Unit Test Pattern (pytest)

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_openai_client():
    with patch('app.services.openai_service.OpenAI') as mock:
        yield mock

@pytest.mark.asyncio
async def test_service_method_success(mock_openai_client):
    # Arrange: Setup mocks and test data
    mock_openai_client.return_value.some_method.return_value = {"data": "value"}

    # Act: Call function under test
    service = SomeService()
    result = await service.do_something("input")

    # Assert: Verify behavior
    assert result.status == "success"
    mock_openai_client.return_value.some_method.assert_called_once()
```

## Mocking External APIs

Always mock:
- OpenAI API calls
- Confluence API calls
- Asana API calls
- File system operations (when testing document processing)

```python
@pytest.fixture
def mock_openai():
    with patch('app.services.openai_service.OpenAI') as mock:
        mock.return_value.beta.vector_stores.create.return_value = MagicMock(id="vs_123")
        yield mock
```

## Test File Location

- Unit tests: `backend/app/tests/test_*.py`
- Fixtures: `backend/app/tests/conftest.py`
- Integration tests: `backend/app/tests/integration/`

## Running Tests

```bash
# All tests
pytest backend/app/tests/ -v

# With coverage
pytest backend/app/tests/ -v --cov=app --cov-report=html

# Specific test file
pytest backend/app/tests/test_openai_service.py -v

# Show print statements
pytest backend/app/tests/ -v -s
```

## Test Naming

Use descriptive test names:
- `test_<method>_<scenario>_<expected_result>`
- Example: `test_create_vector_store_with_valid_files_returns_store_id`
- Example: `test_draft_plan_with_invalid_store_raises_error`

## Coverage Requirements

- Minimum 80% coverage on `services/` and `routers/`
- All error paths must be tested
- Edge cases (empty inputs, large files) should be covered
