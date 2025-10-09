# Strategic Build Planner MVP - Implementation Plan

## 📋 Project Overview
**Goal:** Ingest project docs → AI drafts structured Strategic Build Plan → human edit → publish to Confluence → generate Asana tasks → QA grade.

**Timeline:** 2-week MVP sprint

---

## 🏗️ Architecture

### Backend Stack
- **Framework:** FastAPI (Python 3.11+)
- **AI:** OpenAI Responses API + File Search (Vector Store)
- **Integrations:** Confluence API v2, Asana API
- **Document Processing:** PyPDF2, python-docx
- **Storage:** SQLite for session state (optional for MVP)

### Frontend Stack
- **Framework:** React + Vite
- **UI Library:** shadcn/ui or Material-UI
- **State:** React Query + Context
- **Markdown:** react-markdown

### Project Structure
```
StrategicBuildPlanner/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py           # File upload & Vector Store
│   │   │   ├── draft.py            # Plan generation
│   │   │   ├── publish.py          # Confluence publishing
│   │   │   ├── meeting.py          # Transcript processing
│   │   │   └── qa.py               # QA grading
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── openai_service.py   # Responses API wrapper
│   │   │   ├── confluence.py       # Confluence API client
│   │   │   ├── asana_client.py     # Asana API client
│   │   │   └── vector_store.py     # Vector Store management
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── plan_schema.py      # Pydantic models
│   │   │   └── responses.py        # API response models
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── draft_prompt.py     # System prompts
│   │       └── qa_prompt.py        # QA rubric
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadZone.jsx
│   │   │   ├── PlanPreview.jsx
│   │   │   ├── ChatEdit.jsx
│   │   │   └── QAGrade.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   └── PlanBuilder.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── apqp_starter.py              # Legacy/CLI tool
├── inputs/                      # Local test docs
├── outputs/                     # Generated plans
└── README.md
```

---

## 📝 EPIC BREAKDOWN

### 🧩 EPIC 1: Setup & Infrastructure (Days 1-2)

#### Task 1.1: Initialize FastAPI backend project
**Priority:** P0 | **Estimate:** 2h
- [ ] Create `backend/` directory structure
- [ ] Setup FastAPI with CORS middleware
- [ ] Create endpoint stubs: `/ingest`, `/draft`, `/publish`, `/meeting/apply`, `/qa/grade`
- [ ] Add `.env.example` with keys: `OPENAI_API_KEY`, `CONFLUENCE_URL`, `CONFLUENCE_TOKEN`, `ASANA_TOKEN`
- [ ] Create `requirements.txt` with: `fastapi`, `uvicorn`, `openai`, `python-multipart`, `requests`, `pydantic`

#### Task 1.2: Implement Vector Store and File Search ingestion
**Priority:** P0 | **Estimate:** 4h
- [ ] Create `VectorStoreService` class
- [ ] Accept file uploads (PDF, DOCX, TXT) via `/ingest` endpoint
- [ ] Upload files to OpenAI Vector Store
- [ ] Implement Confluence page fetch by CQL query
- [ ] Add Confluence content to Vector Store
- [ ] Return `vector_store_id` for session

#### Task 1.3: Confluence integration layer
**Priority:** P0 | **Estimate:** 3h
- [ ] Create `ConfluenceClient` class
- [ ] Implement `search_pages(cql_query)` using v2 API with `body-format=storage`
- [ ] Implement `create_page(parent_id, title, content)` → returns page ID + URL
- [ ] Implement `update_page(page_id, content)` for edits
- [ ] Add error handling for auth failures

#### Task 1.4: Asana API integration
**Priority:** P0 | **Estimate:** 2h
- [ ] Create `AsanaClient` class
- [ ] Implement `create_task(title, description, priority, assignee_hint, project_id)`
- [ ] Add `ASANA_PROJECT_ID` to `.env`
- [ ] Handle assignee resolution (name → gid)
- [ ] Return task URL

---

### 🧩 EPIC 2: Core Draft Engine (Days 3-4)

#### Task 2.1: Define Strategic Build Plan JSON Schema
**Priority:** P0 | **Estimate:** 3h
- [ ] Create Pydantic model `StrategicBuildPlan` with sections:
  - `keys_to_project`: List[KeyPoint] (text, source_hint, confidence)
  - `quality_plan`: QualityPlan
  - `purchasing`: Purchasing
  - `history_review`: HistoryReview
  - `build_strategy`: BuildStrategy
  - `execution_strategy`: ExecutionStrategy
  - `release_plan`: ReleasePlan
  - `shipping`: Shipping
  - `apqp_notes`: List[Note]
  - `customer_meeting_notes`: List[Note]
  - `asana_todos`: List[Task]
- [ ] Add metadata: `customer`, `family_of_parts`, `project_name`, `generated_at`

#### Task 2.2: Prompt engineering for draft plan
**Priority:** P0 | **Estimate:** 4h
- [ ] Write system prompt in `prompts/draft_prompt.py`:
  ```
  You are Northern Manufacturing's APQP assistant specializing in strategic build planning.
  Your role: analyze project docs and draft a comprehensive Strategic Build Plan.
  
  INSTRUCTIONS:
  - Extract all relevant information from uploaded documents
  - Prioritize RECALL over precision (catch everything)
  - Include source hints (doc name, page, section)
  - Assign confidence scores (0.0-1.0)
  - Flag unknowns/gaps as "UNKNOWN" with confidence 0.0
  - Use structured JSON output matching the schema
  ```
- [ ] Add few-shot examples
- [ ] Test with sample project docs

#### Task 2.3: Generate plan JSON and Markdown
**Priority:** P0 | **Estimate:** 3h
- [ ] Create `/draft` endpoint accepting `vector_store_id`, `customer`, `family_of_parts`
- [ ] Call OpenAI Responses API with structured output
- [ ] Convert JSON to Markdown template (mirror Confluence structure)
- [ ] Return both JSON and Markdown

---

### 🧩 EPIC 3: Human-in-the-Loop Editing (Days 5-6)

#### Task 3.1: React UI – Upload & Preview Page
**Priority:** P0 | **Estimate:** 4h
- [ ] Initialize Vite + React project in `frontend/`
- [ ] Create `UploadZone` component with drag-drop
- [ ] Add input fields: Customer, Family of Parts
- [ ] Show file list + upload progress
- [ ] Display Markdown preview using `react-markdown`
- [ ] Add "Generate Plan" button

#### Task 3.2: Chat edit panel
**Priority:** P1 | **Estimate:** 5h
- [ ] Create `ChatEdit` component
- [ ] Implement chat interface (user input → AI response)
- [ ] Create `/edit` endpoint: accepts plan JSON + edit instruction
- [ ] Update plan JSON via model reasoning
- [ ] Live preview updates as user edits
- [ ] Add "Save Draft" functionality

---

### 🧩 EPIC 4: Confluence Publishing Flow (Days 7-8)

#### Task 4.1: Automatic page creation under Family of Parts
**Priority:** P0 | **Estimate:** 4h
- [ ] Create `/publish` endpoint accepting `plan_json`, `customer`, `family_of_parts`
- [ ] Search Confluence: `space = OPS AND label = "family-of-parts-{slug}"`
- [ ] Extract parent page ID
- [ ] Create child page: `Strategic Build Plan – {project_name}`
- [ ] Convert plan JSON → Confluence storage format (HTML)
- [ ] Publish page and return URL

#### Task 4.2: Implement "Browse to page" button
**Priority:** P1 | **Estimate:** 1h
- [ ] Add "View in Confluence" button to UI
- [ ] Open returned Confluence URL in new tab
- [ ] Show success toast with page link

---

### 🧩 EPIC 5: Meeting & Task Handling (Days 9-10)

#### Task 5.1: Meeting transcript apply
**Priority:** P1 | **Estimate:** 4h
- [ ] Create `/meeting/apply` endpoint accepting transcript `.txt`
- [ ] Extract decisions, action items, unknowns via model
- [ ] Merge into `apqp_notes` and `customer_meeting_notes`
- [ ] Identify deltas (new info conflicting with plan)
- [ ] Return updated plan JSON

#### Task 5.2: Asana task creation from unknowns
**Priority:** P1 | **Estimate:** 3h
- [ ] Parse unknowns/action items from plan
- [ ] Auto-generate Asana tasks:
  - Title: `[APQP] {action_item}`
  - Description: context + link to Confluence plan
  - Priority: inferred from urgency keywords
  - Assignee hint: extract from transcript
  - Due date hint: parse relative dates
- [ ] Create tasks via Asana API
- [ ] Add task URLs to `asana_todos` in plan

---

### 🧩 EPIC 6: QA Grade & Feedback (Days 11-12)

#### Task 6.1: Implement QA grader
**Priority:** P1 | **Estimate:** 4h
- [ ] Create `/qa/grade` endpoint accepting plan JSON
- [ ] Define rubric in `prompts/qa_prompt.py`:
  - **Completeness** (0-20): All sections filled, no placeholders
  - **Specificity** (0-20): Concrete details vs. vague statements
  - **Actionability** (0-20): Clear next steps, assigned owners
  - **Manufacturability** (0-20): Feasible build strategy
  - **Risk Coverage** (0-20): Identified risks + mitigations
- [ ] Model scores each dimension + overall (0-100)
- [ ] Generate fix suggestions list
- [ ] Return grade + fixes

#### Task 6.2: UI – Show grade & fix suggestions
**Priority:** P1 | **Estimate:** 2h
- [ ] Create `QAGrade` component
- [ ] Display numeric score with color coding (red <60, yellow 60-80, green >80)
- [ ] Show improvement bullets
- [ ] Add "Re-grade" button after edits

---

### 🧩 EPIC 7: Polish & Deployment (Days 13-14)

#### Task 7.1: Error handling & logging
**Priority:** P0 | **Estimate:** 3h
- [ ] Add try-except blocks to all endpoints
- [ ] Return user-friendly error messages
- [ ] Log errors with `logging` module
- [ ] Add health check endpoint `/health`

#### Task 7.2: Security & cleanup
**Priority:** P0 | **Estimate:** 2h
- [ ] Auto-delete Vector Store after 7 days (scheduled job)
- [ ] Add `.gitignore`: `*.env`, `inputs/*`, `outputs/*`, `__pycache__`
- [ ] Validate API keys on startup
- [ ] Add rate limiting (optional for MVP)

#### Task 7.3: Internal demo deployment
**Priority:** P1 | **Estimate:** 4h
- [ ] Deploy backend to local Windows server or Render.com
- [ ] Deploy frontend to Netlify/Vercel
- [ ] Create demo with real project docs
- [ ] Record walkthrough video
- [ ] Share with stakeholders

---

## 🎯 Success Metrics

- [ ] Generate plan for test project in <2 minutes
- [ ] Plan includes 80%+ of key info from docs (human validation)
- [ ] Successfully publishes to Confluence under correct parent
- [ ] Creates 3-5 Asana tasks from transcript
- [ ] QA grade >70 on initial draft
- [ ] Zero API key leaks in repo

---

## 📦 Deliverables

1. **Working FastAPI backend** with 6 core endpoints
2. **React frontend** with upload, preview, chat edit, QA display
3. **Confluence integration** with auto page creation
4. **Asana integration** with auto task generation
5. **Documentation**: README with setup instructions
6. **Demo video** showing end-to-end workflow

---

## 🔄 Next Steps (Post-MVP)

- [ ] Multi-tenancy (support multiple customers/families)
- [ ] Version history for plans
- [ ] Custom template support
- [ ] Advanced chat edit (voice input, suggested edits)
- [ ] Analytics dashboard (plans created, QA scores over time)
- [ ] Mobile-responsive UI

---

**Created:** October 9, 2025  
**Owner:** @ttsmith21  
**Status:** Planning → Ready for Development
