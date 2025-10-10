# Strategic Build Planner MVP — API + Web + Agent + QA + Asana

## What’s in this PR

* **CLI**: multi-`--meeting`, outputs `.md + .json`, Confluence v2 publish (spaceId + parentId).
* **API (FastAPI)**: `/ingest`, `/draft`, `/publish`, `/meeting/apply`, `/qa/grade`, `/asana/tasks` plus new `/healthz` and `/version` probes.
* **Agent layer**: built-in `file_search` + tools for Confluence (search/create child) and Asana (create tasks with fingerprint dedupe).
* **Web (Vite+React)**: Upload (left), Plan preview (center), Actions panel (right): Draft, Apply Notes, Publish (Browse), Create Tasks, QA Grade with duplicate-task toasts.
* **QA**: `evals/rubric.json` + gold set; metrics to `outputs/metrics/qa_metrics.jsonl`.
* **Safety**: `.gitignore` blocks `inputs/`, `outputs/`, `meetings/`; pre-commit hook present.

## Env

* API: `OPENAI_API_KEY`, `CONFLUENCE_*`, `ASANA_*`
* Web: `VITE_API_BASE_URL=http://localhost:8000`

## Acceptance criteria

* Draft plan shows **source_hint + confidence** and marks UNKNOWNs.
* Publish creates/updates **child page under Family of Parts** and returns a **clickable URL** (canonical `_links.webui` fallback safe).
* Apply meeting notes updates plan; QA Grade returns `{score, fixes[]}` and logs metrics.
* Create Tasks posts Asana cards with plan links, fingerprint dedupes, and reports `{created, skipped}`.

## Follow-ups (next PR)

* Swap right panel to **ChatKit** actions.
* Vector store auto-cleanup (>7 days).
* CI guard to block tracked files under `inputs/ /outputs/ /meetings/`.

---

## Screenshots / GIFs

_Add walkthrough of Draft → Publish → Browse → QA → Asana once smoke test is executed._
