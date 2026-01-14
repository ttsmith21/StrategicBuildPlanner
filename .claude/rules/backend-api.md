---
paths:
  - "backend/**/*.py"
  - "app/**/*.py"
---

# FastAPI Backend Standards

## Endpoint Pattern

All endpoints must include:
- Type hints on parameters and returns
- Docstring with usage description
- Error handling with try/except
- Request/response validation with Pydantic

```python
@router.post("/example", response_model=ExampleResponse)
async def example_endpoint(request: ExampleRequest) -> ExampleResponse:
    """Brief description of what this endpoint does."""
    try:
        result = await service.do_something(request.param)
        return ExampleResponse(success=True, data=result)
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Async I/O

Use `async def` for all functions calling external APIs:
- OpenAI Responses API
- Confluence REST API
- Asana API
- Database operations

Use `asyncio.gather()` for parallel calls when appropriate.

## Error Handling

Include context in error messages:
```python
raise HTTPException(
    status_code=502,
    detail=f"OpenAI API error: {str(e)}. Check OPENAI_API_KEY."
)
```

## Pydantic Models

Define all request/response models in `app/models/`:
```python
from pydantic import BaseModel, Field

class DraftRequest(BaseModel):
    vector_store_id: str = Field(..., description="OpenAI Vector Store ID")
    customer: str = Field(..., min_length=1)
    family_of_parts: str = Field(..., min_length=1)
```

## File Organization

- Routers: `app/routers/` - One file per resource (ingest.py, draft.py, publish.py)
- Services: `app/services/` - Business logic and external API wrappers
- Models: `app/models/` - Pydantic schemas
- Prompts: `app/prompts/` - AI system prompts

## Testing

- Write unit tests for all service methods
- Mock external APIs with `unittest.mock` or `pytest-mock`
- Test both success and error paths
- Aim for 80%+ coverage on services and routers
