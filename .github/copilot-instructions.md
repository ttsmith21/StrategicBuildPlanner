## StrategicBuildPlanner — rules for AI coding agents

Use this as your operating guide to be productive immediately in this repo.

### Architecture in 6 bullets
- API service: `server/main.py` (FastAPI). It orchestrates ingestion ➝ specialist agents ➝ QA ➝ publish. Always use Pydantic request/response models with `response_model=...` and raise `HTTPException` on failures.
- Specialist agents: `server/agents/*` run via `coordinator.run_specialists()`. Each agent returns an `AgentPatch` and may add `AgentTask`s and `conflicts`. Ownership is enforced by `_AGENT_OWNERSHIP` (e.g., QMA→`quality_plan`, EMA→`engineering_instructions`).
- Shared libs: `server/lib/*`
  - `schema.py`: JSON/Pydantic schemas (plan, QA, agent patch/tasks)
  - `context_pack.py`: builds source registry and freezes a Context Pack with precedence/authority rules
  - `vectorstore.py`: OpenAI vector store create/append/delete
  - `rendering.py`: Jinja2 renderer of plan_markdown
  - `asana.py`, `confluence.py`: REST clients and helpers
- Agent wrapper: `agent/agent.py` uses OpenAI Assistants (beta) with `file_search` and strict JSON schema. Missing data must be the literal string `"UNKNOWN"`.
- Sessions & snapshots: file-backed `SessionStore` saves to `outputs/sessions/*.json` with snapshots of `plan_json`, `context_pack`, and `vector_store_id`.
- Frontend: `web/` (Vite React). Calls the FastAPI endpoints; client examples in `web/src/api.ts`.

### Data flow and why it’s structured this way
1) `/ingest` saves uploads to a temp dir, creates or appends to an OpenAI vector store, then builds a Context Pack via `build_source_registry()` + `freeze_context_pack()` so downstream agents have a canonicalized view of sources and facts.
2) `/agents/run` runs QMA → PMA → SCA → EMA, then synthesizers (Open Questions, Keys) and the QA gate (SBP-QA). It returns `plan_json`, `plan_markdown`, `tasks_suggested`, `conflicts`, `qa`. If outputs are sparse, it falls back to a baseline `draft_plan()` using the vector store.
3) `/publish` uses Confluence v2 (via `agent/tools/confluence.py`) to create a child page; minimal HTML is assembled from Markdown.
4) `/qa/grade` evaluates plan quality against `evals/rubric.json` and logs to `outputs/metrics/qa_metrics.jsonl`.

### Source precedence and labels (Context Pack)
- Kind→precedence rank and authority live in `server/lib/context_pack.py` (e.g., drawing/po: 1 mandatory; itp/quote/sow: 2; customer_spec: 3; generic_spec: 5; email/internal: 20). Lower rank wins; mandatory beats conditional/reference.
- Upload entries infer labels from filenames; you can override per-file behavior by passing `files_meta` to `/ingest` (keys are lowercase filenames) with `doc_type`, `authority`, `precedence_rank`.

### Critical workflows (PowerShell on Windows)
- One-time setup: VS Code Tasks → “Full Setup (All Steps)” (creates `.venv`, installs deps, copies `.env.example`).
- Run API dev server: VS Code Task “Run API server” or `python run_server.py` (serves at http://localhost:8001; docs at /docs).
- E2E API test: `python test_server_api.py` (exercises ingest → agents → QA → publish → cleanup; doesn’t require the web UI).
- Demo run (legacy CLI): Task “Run: APQP Assistant (Demo)” or `python apqp_starter.py ...` (kept for compatibility; server endpoints are the primary interface).

### Project-specific conventions you must follow
- Always return or persist `vector_store_id` and `context_pack`; `/agents/run` requires them. Typical flow: call `/ingest` first, then `/agents/run`.
- Missing or ambiguous facts must be encoded as `"UNKNOWN"` (upper-case); follow-up tasks are generated from these markers.
- Tasks carry an `owner_hint` grouped into ENG/QA/BUY/SCHED/LEGAL; fingerprints are computed to dedupe (`asana.fingerprint`).
- When rendering, include `context_pack` in the plan payload for source visualization: see `/render` endpoint and `render_plan_md()`.
- New endpoints: define Pydantic models, set `response_model`, add CORS-safe behavior, and log meaningful errors.
- New specialists: implement `run_<agent>(plan, context_pack, vector_store_id) -> AgentPatch`, update `_AGENT_OWNERSHIP` in `coordinator.py`, and append to the run order.

### Integration points
- OpenAI: `openai_client.beta.assistants/threads/runs` with `file_search` bound to `vector_store_id`.
- Confluence: v2 API via `agent/tools/confluence.py` (space resolution, parent selection, create child page). Publishing requires `CONFLUENCE_*` env vars.
- Asana: `server/lib/asana.py` supports listing projects/teams/workspaces and creating tasks from plan TODOs.

### Good examples to copy
- Endpoint patterns: `/agents/run`, `/ingest`, `/qa/grade` in `server/main.py`.
- Context Pack build: `_build_uploaded_source_entries()` → `build_source_registry()` → `freeze_context_pack()` in `server/main.py` + `server/lib/context_pack.py`.
- Coordinator and patch/ownership pattern: `server/agents/coordinator.py`.

Questions or unclear areas? Tell me which section needs more detail (e.g., adding a new agent, Confluence publish nuances, or web client patterns), and I’ll expand this file.
