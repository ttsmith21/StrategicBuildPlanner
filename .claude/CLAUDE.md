# Strategic Build Planner - Claude Code Project Guide

**Project**: APQP Manufacturing Planning Tool for Northern Manufacturing Co., Inc.
**Tech Stack**: FastAPI + React + OpenAI Responses API
**Status**: MVP in development (~40% complete)

---

## Quick Reference

### Start Development
```bash
# Backend (port 8000) - run from project root
cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend (port 5173) - run from project root
cd frontend && npm run dev

# API docs at http://localhost:8000/docs
# Frontend at http://localhost:5173
```

**Note for Claude Code**: When starting servers via Bash, use Unix-style paths (`/c/Users/...`) not Windows paths (`C:\Users\...`).

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
- **Smoke tests**: `python run_smoke_tests.py` (17 end-to-end API tests)
- **Quick smoke tests**: `python run_smoke_tests.py --quick` (skip slow AI tests)
- Unit tests: `pytest backend/ -v` (test files in backend root)
- Coverage: `pytest --cov=app backend/`
- Mock external APIs (OpenAI, Confluence, Asana)

---

## OpenAI Integration

### SDK Version & Imports
- Using OpenAI SDK v1.54+
- Beta types (VectorStore, etc.) import from `openai.types.beta`, NOT `openai.types`
- Example: `from openai.types.beta import VectorStore`

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

### Backend (`.env` in project root)
```
OPENAI_API_KEY=sk-proj-...  # Required for AI features
CORS_ORIGINS=...            # Optional: comma-separated allowed origins
```

Optional:
```
CONFLUENCE_BASE_URL=...     # For publishing
CONFLUENCE_API_TOKEN=...
ASANA_TOKEN=...             # For task creation
```

### Frontend (`frontend/.env.local`)
```
VITE_API_URL=http://localhost:8000  # Backend API URL - MUST match backend port!
```

**Important**: If frontend gets connection errors, verify `VITE_API_URL` port matches where backend is running.

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

## Git Workflow (IMPORTANT)

**Claude Code must follow this workflow automatically without being asked.**

### For New Features
1. **Create a feature branch** before making changes:
   ```bash
   git checkout -b feature/descriptive-name
   ```
2. **Commit frequently** with logical groupings (don't batch all changes into one commit)
3. **Test before committing** - verify the backend starts and endpoints work
4. **Push branch** when feature is complete and tested

### Commit Guidelines
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- Keep commits focused (one logical change per commit)
- Include `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>` in commit messages

### When to Commit
- After completing a new service or router
- After fixing a bug
- After significant refactoring
- Before switching to a different task

### Branch Naming
- `feature/` - New features (e.g., `feature/confluence-search`)
- `fix/` - Bug fixes (e.g., `fix/checklist-timeout`)
- `refactor/` - Code improvements (e.g., `refactor/optimize-batching`)

### Before Pushing
- [ ] Run `black backend/` to format
- [ ] Verify backend starts without errors
- [ ] Test new endpoints work
- [ ] Check `.env` is NOT staged

---

## Before Committing

- [ ] Run `black backend/` to format
- [ ] Run `pytest backend/ -v`
- [ ] **Start backend** to verify no import errors: `cd backend && uvicorn app.main:app`
- [ ] Check `.env` is NOT staged: `git status`
- [ ] Update BUILD_STATUS.md if completing an epic
