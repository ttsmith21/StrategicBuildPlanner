---
paths:
  - "backend/app/services/openai_service.py"
  - "**/*openai*.py"
---

# OpenAI Integration Standards

## Vector Store Workflow

1. **Upload files** to OpenAI Files API
2. **Create Vector Store** with file IDs
3. **Use in Responses API** with file_search tool
4. **Cleanup** expired stores (TTL: 7 days)

```python
# Create Vector Store
async def create_vector_store(self, file_paths: List[str]) -> str:
    # Upload files
    file_ids = []
    for path in file_paths:
        file = await self.client.files.create(file=open(path, "rb"), purpose="assistants")
        file_ids.append(file.id)

    # Create store
    store = await self.client.beta.vector_stores.create(file_ids=file_ids)
    return store.id
```

## Responses API with Structured Output

Use JSON schema enforcement for reliable outputs:

```python
response = await self.client.chat.completions.create(
    model="o4-mini",
    messages=[
        {"role": "system", "content": DRAFT_PROMPT},
        {"role": "user", "content": f"Generate plan for {customer}"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "strategic_build_plan",
            "strict": True,
            "schema": StrategicBuildPlan.model_json_schema()
        }
    }
)
```

## Error Handling

Handle OpenAI-specific errors:

```python
from openai import OpenAIError, RateLimitError, APIError

try:
    response = await self.client.chat.completions.create(...)
except RateLimitError:
    # Implement exponential backoff
    await asyncio.sleep(2 ** retry_count)
    # Retry...
except APIError as e:
    logger.error(f"OpenAI API error: {e}")
    raise HTTPException(status_code=502, detail="OpenAI service unavailable")
```

## Model Selection

- **o4-mini**: Primary model for plan generation (reasoning, structured output)
- **whisper-1**: Audio transcription (meeting recordings)

Configure via environment:
```
OPENAI_MODEL_PLAN=o4-mini
OPENAI_MODEL_TRANSCRIBE=whisper-1
```

## Cost Management

- Monitor token usage with response metadata
- Implement caching for repeated queries
- Use streaming for long responses
- Set max_tokens limits appropriately

## Testing OpenAI Integration

Always mock in unit tests:
```python
@pytest.fixture
def mock_openai_client():
    with patch('app.services.openai_service.OpenAI') as mock:
        # Mock vector store creation
        mock.return_value.beta.vector_stores.create.return_value = MagicMock(id="vs_test")
        # Mock chat completion
        mock.return_value.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"plan": "data"}'))]
        )
        yield mock
```
