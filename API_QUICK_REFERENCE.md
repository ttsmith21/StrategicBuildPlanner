# Strategic Build Planner API - Quick Reference

**Server:** http://localhost:8001  
**Docs:** http://localhost:8001/docs

---

## 🚀 Quick Start

```powershell
# Start server
python run_server.py

# Run tests
python test_server_api.py
```

---

## 📡 API Endpoints

### 1. Health Check
```bash
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2025-10-09T19:21:46.353586"
}
```

---

### 2. Upload Files
```bash
POST /ingest
Content-Type: multipart/form-data

Form Data:
  files: <file1>
  files: <file2>
  customer: "ACME Corp"
  family: "Bracket Assembly"

Response:
{
  "session_id": "uuid-string",
  "message": "Uploaded 2 file(s) successfully",
  "file_count": 2,
  "file_names": ["drawing.pdf", "notes.txt"]
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/ingest \
  -F "files=@inputs/drawing.pdf" \
  -F "files=@meetings/notes.txt" \
  -F "customer=ACME Corp"
```

---

### 3. Generate Plan
```bash
POST /draft
Content-Type: application/json

Body:
{
  "session_id": "uuid-from-ingest",
  "project_name": "ACME Bracket Manufacturing",
  "customer": "ACME Corporation"
}

Response:
{
  "plan_json": { /* Strategic Build Plan */ },
  "plan_markdown": "# Strategic Build Plan...",
  "source_file_names": ["drawing.pdf"],
  "vector_store_id": "vs_abc123"
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/draft \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "project_name": "ACME Bracket Manufacturing"
  }'
```

---

### 4. Publish to Confluence
```bash
POST /publish
Content-Type: application/json

Body:
{
  "customer": "ACME Corp",
  "family": "Bracket Assembly",
  "project": "ACME Bracket Manufacturing",
  "markdown": "# Strategic Build Plan...",
  "parent_page_id": "123456789"  // optional
}

Response:
{
  "page_id": "987654321",
  "url": "https://domain.atlassian.net/wiki/spaces/KB/pages/987654321/...",
  "title": "Strategic Build Plan — ACME Bracket Manufacturing"
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/publish \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "ACME Corp",
    "project": "ACME Bracket Manufacturing",
    "markdown": "# Plan content..."
  }'
```

---

### 5. Apply Meeting Notes
```bash
POST /meeting/apply
Content-Type: application/json

Body:
{
  "plan_json": { /* Current plan */ },
  "transcript_texts": [
    "Meeting notes content...",
    "Follow-up notes..."
  ]
}

Response:
{
  "updated_plan_json": { /* Updated plan */ },
  "updated_plan_markdown": "# Updated Strategic Build Plan...",
  "changes_summary": "Meeting notes applied successfully"
}
```

---

### 6. Grade Plan Quality
```bash
POST /qa/grade
Content-Type: application/json

Body:
{
  "plan_json": { /* Plan to grade */ }
}

Response:
{
  "score": 82.5,
  "reasons": [
    "APQP sections largely complete but tooling plan lacks finish partner",
    "Risk register references owners and due dates",
    "Material spec aligns with customer drawing rev B"
  ],
  "fixes": [
    "Assign owner + due date for UNKNOWN passivation vendor",
    "Quantify takt assumption for Form → Weld cell",
    "Add mitigation plan for supply chain delta on 316L sheet"
  ]
}
```

---

### 7. Run Specialist Agents
```bash
POST /agents/run
Content-Type: application/json

Body:
{
  "session_id": "uuid-from-ingest",
  "vector_store_id": "vs_abc123",
  "plan_json": { /* Current plan */ }
}

Response:
{
  "plan_json": { /* Patched plan JSON */ },
  "deltas": [
    {
      "topic": "Materials",
      "delta_type": "non_standard",
      "recommended_action": "Escalate to quality for disposition",
      "owner_hint": "QA"
    }
  ],
  "ema_patch": {
    "engineering_instructions": {
      "routing": [...]
    }
  },
  "tasks_suggested": [
    { "name": "Resolve open question #1", "owner_hint": "ENG" }
  ],
  "qa": {
    "score": 84.5,
    "blocked": true,
    "summary": "Finish cell missing passivation plan",
    "fixes": ["Specify passivation vendor or mark none"]
  }
}
```

This endpoint orchestrates QEA, QDD, and EMA agents using the context pack precedence matrix. Plan-level fingerprints and owner buckets (ENG/QA/BUY/SCHED/LEGAL) are returned so the web UI can group follow-up work. When `qa.blocked` is true the frontend disables Confluence publishing.

### 8. Create Asana Tasks
```bash
POST /asana/tasks
Content-Type: application/json

Body:
{
  "project_id": "1201234567890",
  "plan_json": { /* Plan used to derive tasks */ }
}

Response:
{
  "created": [
    { "gid": "120123456", "name": "Mitigate risk: Tooling lead time", "permalink_url": "https://app.asana.com/..." },
    { "gid": "120123457", "name": "Resolve open question #1", "permalink_url": "https://app.asana.com/..." }
  ]
}
```

When no explicit `tasks` array is provided, the API will auto-derive tasks from the plan's `risks` and `open_questions` fields.

---

### 9. Cleanup Session
```bash
DELETE /session/{session_id}

Response:
{
  "message": "Session cleaned up successfully"
}
```

**cURL:**
```bash
curl -X DELETE http://localhost:8001/session/YOUR_SESSION_ID
```

---

## 🔄 Full Workflow Example

```bash
# 1. Upload files
SESSION_ID=$(curl -X POST http://localhost:8001/ingest \
  -F "files=@inputs/drawing.pdf" \
  -F "customer=ACME Corp" | jq -r '.session_id')

# 2. Generate plan
curl -X POST http://localhost:8001/draft \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"project_name\":\"ACME Bracket\"}" \
  > plan.json

# 3. Grade quality
curl -X POST http://localhost:8001/qa/grade \
  -H "Content-Type: application/json" \
  -d @plan.json | jq '.overall_score'

# 4. Publish to Confluence
MARKDOWN=$(jq -r '.plan_markdown' plan.json)
curl -X POST http://localhost:8001/publish \
  -H "Content-Type: application/json" \
  -d "{\"customer\":\"ACME Corp\",\"project\":\"ACME Bracket\",\"markdown\":$MARKDOWN}"

# 5. Cleanup
curl -X DELETE http://localhost:8001/session/$SESSION_ID
```

---

## 🎨 React/TypeScript Example

```typescript
import { useState } from 'react';

interface IngestResponse {
  session_id: string;
  file_count: number;
  file_names: string[];
}

interface DraftResponse {
  plan_json: any;
  plan_markdown: string;
  source_file_names: string[];
  vector_store_id: string;
}

function StrategicBuildPlanner() {
  const [sessionId, setSessionId] = useState<string>('');
  const [plan, setPlan] = useState<any>(null);
  
  const handleUpload = async (files: FileList) => {
    const formData = new FormData();
    Array.from(files).forEach(f => formData.append('files', f));
    formData.append('customer', 'ACME Corp');
    
    const res = await fetch('http://localhost:8001/ingest', {
      method: 'POST',
      body: formData
    });
    const data: IngestResponse = await res.json();
    setSessionId(data.session_id);
  };
  
  const handleGenerate = async () => {
    const res = await fetch('http://localhost:8001/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        project_name: 'ACME Bracket Manufacturing'
      })
    });
    const data: DraftResponse = await res.json();
    setPlan(data);
  };
  
  const handlePublish = async () => {
    const res = await fetch('http://localhost:8001/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer: 'ACME Corp',
        project: 'ACME Bracket',
        markdown: plan.plan_markdown
      })
    });
    const { url } = await res.json();
    window.open(url, '_blank');
  };
  
  return (
    <div>
      <input type="file" multiple onChange={e => handleUpload(e.target.files!)} />
      <button onClick={handleGenerate}>Generate Plan</button>
      {plan && <button onClick={handlePublish}>Publish to Confluence</button>}
    </div>
  );
}
```

---

## 📦 Response Models

### Strategic Build Plan JSON

```json
{
  "project": "Project Name",
  "customer": "Customer Name",
  "revision": "Rev A",
  "summary": "Executive summary...",
  "requirements": [
    {
      "topic": "Material",
      "requirement": "304 SS, 0.125\" thick",
      "source_hint": "drawing.pdf",
      "confidence": 0.95
    }
  ],
  "process_flow": "Blank → Form → Weld → Finish → Inspect",
  "tooling_fixturing": "Press brake tooling, weld fixtures",
  "quality_plan": "CMM inspection, Cpk ≥ 1.67",
  "materials_finishes": "304 SS, #4 brushed finish",
  "ctqs": ["Overall length: 12.5\" ±0.015\""],
  "risks": [
    {
      "risk": "Tooling lead time",
      "impact": "Delayed first article",
      "mitigation": "Order tooling early",
      "owner": "Engineering",
      "due_date": "2025-10-20"
    }
  ],
  "open_questions": ["What is annual volume?"],
  "cost_levers": ["Material nesting optimization"],
  "pack_ship": "Cardboard boxes, 10 per box",
  "source_files_used": ["drawing.pdf", "notes.txt"]
}
```

---

## 🛠️ Environment Variables

```env
# Required
OPENAI_API_KEY=sk-***
OPENAI_MODEL_PLAN=o4-mini

# Optional (for /publish endpoint)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@company.com
CONFLUENCE_API_TOKEN=your-token
CONFLUENCE_SPACE_KEY=KB
CONFLUENCE_PARENT_PAGE_ID=123456789
```

---

## 🔍 Troubleshooting

**Server won't start:**
```powershell
# Check if port is in use
netstat -ano | findstr :8001

# Kill process if needed
taskkill /F /PID <pid>
```

**Import errors:**
```powershell
# Reinstall dependencies
pip install -r requirements.txt
```

**Confluence 404 errors:**
- Check `CONFLUENCE_BASE_URL` has no trailing slash
- Verify `CONFLUENCE_SPACE_KEY` is correct
- Ensure API token has proper permissions

---

## 📖 Full Documentation

- **API Guide:** `server/README.md`
- **Acceptance Tests:** `SERVER_ACCEPTANCE_TESTS.md`
- **Implementation Summary:** `FASTAPI_IMPLEMENTATION_SUMMARY.md`
- **Interactive Docs:** http://localhost:8001/docs (when server running)

---

**Quick Links:**
- Health: http://localhost:8001/health
- API Docs: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
