# Strategic Build Planner - Claude Code Project Guide

**Project**: APQP Manufacturing Planning Tool for Northern Manufacturing Co., Inc.
**Tech Stack**: FastAPI + React + OpenAI Responses API
**Status**: MVP in development (~40% complete)

---

## Quick Reference

### Start Development
```bash
# Activate environment
.\.venv\Scripts\Activate.ps1

# Start backend (port 8000)
cd backend && uvicorn app.main:app --reload

# API docs at http://localhost:8000/docs
```

### Key Directories
- `backend/app/` - FastAPI application
- `backend/app/routers/` - API endpoints
- `backend/app/services/` - Business logic (OpenAI, document processing)
- `backend/app/models/` - Pydantic schemas
- `backend/app/prompts/` - AI system prompts
- `inputs/` - Test documents (gitignored)
- `outputs/` - Generated plans (gitignored)

---

## Project Overview

### What It Does
1. **Ingests** manufacturing documents (PDFs, quotes, drawings) via file upload
2. **Analyzes** using OpenAI Responses API with Vector Stores
3. **Generates** Strategic Build Plans in JSON + Markdown
4. **Publishes** to Confluence under Family of Parts hierarchy
5. **Creates** Asana tasks from action items

### Architecture
```
POST /api/ingest → Upload files → Create Vector Store → Return session_id
POST /api/draft  → Generate plan from Vector Store → Return JSON + Markdown
POST /api/publish → Publish to Confluence → Return page URL
POST /api/qa/grade → Score plan quality → Return rubric results
```

---

## Coding Standards

### Python (Backend)
- **Format**: `black .` (line length 88)
- **Type hints**: Required on all functions
- **Async**: Use `async def` for all I/O operations
- **Error handling**: Wrap external API calls in try/except
- **Docstrings**: Google style

### Example Endpoint Pattern
```python
@router.post("/draft", response_model=PlanResponse)
async def generate_draft(request: DraftRequest) -> PlanResponse:
    """Generate Strategic Build Plan from vector store."""
    try:
        plan = await openai_service.draft_plan(request.vector_store_id)
        return PlanResponse(success=True, plan=plan)
    except OpenAIError as e:
        raise HTTPException(status_code=502, detail=str(e))
```

### Testing
- Unit tests: `pytest backend/app/tests/ -v`
- Coverage: `pytest --cov=app backend/app/tests/`
- Mock external APIs (OpenAI, Confluence, Asana)

---

## OpenAI Integration

### Vector Store Workflow
1. Upload files to OpenAI Files API
2. Create Vector Store with file IDs
3. Use Vector Store in Responses API with file_search tool
4. Apply structured JSON schema for output validation

### Key Service Methods
- `openai_service.create_vector_store()` - Create store from uploaded files
- `openai_service.draft_plan()` - Generate plan using Responses API
- `openai_service.delete_vector_store()` - Cleanup expired stores

### Structured Output
Uses Pydantic model `StrategicBuildPlan` with strict JSON enforcement.
Schema in: `backend/app/models/plan_schema.py`

---

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=sk-proj-...  # Required for AI features
```

Optional:
```
CONFLUENCE_BASE_URL=...     # For publishing
CONFLUENCE_API_TOKEN=...
ASANA_TOKEN=...             # For task creation
```

---

## Development Epics

| Epic | Description | Status |
|------|-------------|--------|
| EPIC-1 | Core Services Setup | ~80% done |
| EPIC-2 | Draft Engine & JSON Generation | Not started |
| EPIC-3 | Confluence Integration | Not started |
| EPIC-4 | Meeting Transcript Processing | Not started |
| EPIC-5 | React Frontend MVP | Not started |
| EPIC-6 | QA Grading System | Not started |
| EPIC-7 | Polish & Documentation | Not started |

---

## Common Tasks

### Add New Endpoint
1. Create router in `backend/app/routers/`
2. Define Pydantic request/response models
3. Implement async handler with error handling
4. Add to `main.py` with `app.include_router()`
5. Write tests in `backend/app/tests/`

### Test with Sample Data
```bash
# Test ingest endpoint
curl -X POST http://localhost:8000/api/ingest \
  -F "project_name=Test" \
  -F "files=@inputs/sample.pdf"
```

### Browser Verification
Use Chrome automation tools to:
- Navigate to http://localhost:8000/docs
- Test API endpoints interactively
- Verify response data

---

## Files to Know

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app setup |
| `backend/app/models/plan_schema.py` | StrategicBuildPlan model |
| `backend/app/services/openai_service.py` | OpenAI API wrapper |
| `backend/app/services/document_processor.py` | PDF/DOCX extraction |
| `backend/app/routers/ingest.py` | File upload endpoint |
| `backend/app/prompts/draft_prompt.py` | Plan generation prompt |
| `PROJECT_PLAN.md` | 2-week implementation roadmap |
| `BUILD_STATUS.md` | Current progress tracking |

---

## Before Committing

- [ ] Run `black backend/` to format
- [ ] Run `pytest backend/app/tests/ -v`
- [ ] Check `.env` is NOT staged: `git status`
- [ ] Update BUILD_STATUS.md if completing an epic
