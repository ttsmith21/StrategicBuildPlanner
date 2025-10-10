# Strategic Build Planner (APQP Assistant)

A production-ready AI assistant that ingests procurement documents (POs, quotes, drawings) and Confluence knowledge to draft **Strategic Build Plans** for stainless sheet-metal fabrication using OpenAI's **Responses API** with **Vector Stores** and **Structured Outputs**.

**Northern Manufacturing Co., Inc.**

---

## 🎯 What It Does

1. **Ingests** project documents (PDFs, DOCX, TXT) and Confluence pages via CQL
2. **Analyzes** using OpenAI's vector search and reasoning models (o4-mini)
3. **Drafts** a manufacturing-ready Strategic Build Plan with:
   - Contract/commercial analysis (PO vs Quote deltas)
   - Technical requirements (materials, finishes, tolerances, welding)
   - Process flow and tooling strategy
   - Quality plan (CTQs, inspection, PPAP)
   - Risk register with mitigations
   - Cost levers and open questions
4. **Outputs** structured JSON + Markdown
5. **Publishes** to Confluence (optional)

---

## 🚀 Quick Start (Windows - No WSL Required!)

### Prerequisites

- **Python 3.11+** (you have 3.13 ✅)
- **OpenAI API key** ([Get one here](https://platform.openai.com/api-keys))
- **Confluence Cloud** (optional, for knowledge base integration)

### Installation

```powershell
# 1. Virtual environment already created ✅
# 2. Install dependencies
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configure environment
Copy-Item .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env` with your credentials:

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...your-key...
OPENAI_MODEL_PLAN=o4-mini
OPENAI_MODEL_TRANSCRIBE=whisper-1

# Confluence (Cloud)
CONFLUENCE_BASE_URL=https://northernmfg.atlassian.net
CONFLUENCE_EMAIL=your-email@northernmfg.com
CONFLUENCE_API_TOKEN=your-api-token
CONFLUENCE_SPACE_KEY=KB
CONFLUENCE_PARENT_PAGE_ID=123456789
```

**Get Confluence API Token**: [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

---

## 📖 Usage Examples

### Basic: Local Files Only

```powershell
python apqp_starter.py `
  --project "ACME Bracket Rev B" `
  --files .\inputs\PO.pdf .\inputs\Quote.pdf .\inputs\Drawing.pdf
```

### With Confluence Context

```powershell
python apqp_starter.py `
  --project "XYZ Enclosure" `
  --files .\inputs\PO.pdf .\inputs\Spec.pdf `
  --cql 'space = KB AND label = "customer-acme" AND type = page'
```

### With Meeting Transcript + Publish

```powershell
python apqp_starter.py `
  --project "Project Alpha" `
  --files .\inputs\*.pdf `
  --meeting .\meetings\kickoff-transcript.txt `
  --publish
```

---

## 📁 Project Structure

```
StrategicBuildPlanner/
├── .venv/                      # Virtual environment ✅
├── inputs/                     # Place your PDFs here
├── outputs/                    # Generated plans (MD + JSON)
├── meetings/                   # Meeting transcripts (optional)
├── apqp_starter.py             # Main application
├── requirements.txt            # Dependencies
├── .env                        # Your secrets (not in git)
├── .env.example                # Template
└── README.md                   # This file
```

---

## 🔧 How It Works

### 1. **Vector Store Creation**
- Uploads all input files to OpenAI's Vector Store
- Fetches relevant Confluence pages via CQL (if configured)
- Adds meeting transcripts (if provided)

### 2. **Structured Reasoning**
- Uses OpenAI's **Responses API** with **o4-mini** reasoning model
- Enforces a strict JSON schema (no hallucinated fields!)
- Includes stainless sheet-metal APQP checklist in system prompt

### 3. **Output Generation**
- JSON with all plan data (for programmatic use)
- Markdown (human-readable, ready for Confluence)
- Optional: Direct publish to Confluence as a child page

## Context Pack & Precedence

Every draft stores a **Context Pack** that fuses uploaded files, Confluence pages, and agent-generated facts. When facts disagree, the system promotes the highest-precedence, highest-authority source to `canonical` and marks the rest as `proposed` or `superseded`.

| Source kind       | Authority   | Precedence rank |
|-------------------|-------------|-----------------|
| drawing           | mandatory   | 1               |
| po                | mandatory   | 1               |
| itp               | mandatory   | 2               |
| quote             | conditional | 2               |
| customer_spec     | mandatory   | 3               |
| supplier_qm       | conditional | 4               |
| generic_spec      | reference   | 5               |
| email             | internal    | 20              |
| lessons_learned   | internal    | 99              |
| (everything else) | reference   | 10              |

Lower numbers win; mandatory sources beat conditional, reference, and internal notes. The matrix lives in `server/lib/context_pack.py` and drives the precedence column surfaced in the web UI.

## Specialist Agents & QA (/agents/run)

Once a draft exists, call `POST /agents/run` to orchestrate three specialist passes:

- **QEA** (Quality Evidence Aggregator) augments the context pack with authoritative facts.
- **QDD** (Quality Delta Detector) compares the augmented context to `server/lib/baseline_quality.json` and surfaces non-standard deltas grouped by owner buckets (ENG/QA/BUY/SCHED/LEGAL).
- **EMA** (Engineering Methods Assistant) proposes routing, fixture, and CTQ updates.

The endpoint returns the patched plan, suggested tasks, and a QA gate. If the score falls below 85, the UI blocks publishing until the recommended fixes are addressed.

---

## 📋 APQP Coverage (Stainless Sheet-Metal)

The AI assistant is pre-trained to cover:

### Contract/Commercial
- PO vs Quote deltas (quantities, pricing, terms)
- Customer quality flowdowns (ISO/AS, certifications, PPAP level)
- Regulatory requirements (RoHS/REACH, ITAR/EAR, DFARS)

### Technical Requirements
- Material specifications (304/316/321, thickness, temper, mill certs)
- Finishes (passivation ASTM A967/A380, bead blast, heat tint removal)
- Weld symbols (AWS D1.6), sequences, distortion control
- GD&T features, tolerances, datum strategy
- Tube vs flat considerations (ovalization, fishmouth, miters)

### Manufacturing Plan
- Process flow (blank → form → trim → weld → finish → inspect → pack)
- Tooling strategy (press brake, punches, dies, fixtures)
- Cell layout, robotics, bottlenecks
- SPC/CPk on CTQs, gage R&R, control plans
- Risk register with mitigations

### Missing Items → Open Questions
- Anything not found in documents is flagged as an **Open Question** with actionable asks

---

## 🎓 Understanding the Technology

### OpenAI Responses API
- Successor to Assistants API
- Built-in **Vector Stores** for document search
- **Structured Outputs** (strict JSON schema enforcement)
- [Migration Guide](https://platform.openai.com/docs/assistants/migration)

### Confluence Cloud REST API
- **v1 Search**: CQL queries to find pages
- **v2 Pages**: Fetch body content in `storage` format
- [API Documentation](https://developer.atlassian.com/cloud/confluence/rest/)

### Why o4-mini?
- Fast reasoning model optimized for structured tasks
- Cost-effective for production use
- [Model Documentation](https://platform.openai.com/docs/models/o4-mini)

---

## 🔒 Security & Data Privacy

### OpenAI API
- **Business data is NOT used for training** by default
- [Enterprise Privacy Policy](https://openai.com/enterprise-privacy/)
- Use dedicated API keys, not personal accounts

### Confluence
- Use dedicated service account API tokens
- Scope access appropriately (read-only for queries, write for publishing)
- Rotate tokens quarterly
- [API Token Management](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)

### Local Development
- Never commit `.env` to version control (already in `.gitignore`)
- Use environment-specific configurations
- Review all AI-generated output before publishing to Confluence

---

## 🛠️ Customization

### Add Northern-Specific Requirements

Edit the `APQP_CHECKLIST` in `apqp_starter.py`:

```python
APQP_CHECKLIST = [
    # ... existing items ...
    "5-axis laser constraints for tube cutting",
    "Robotic weld cell availability (Cell 1 vs Cell 2)",
    "Passivation vendor requirements (Vendor X certification)",
]
```

### Modify Output Schema

Edit `PLAN_SCHEMA` to add custom fields:

```python
"properties": {
    # ... existing fields ...
    "northern_specific": {
        "type": "object",
        "properties": {
            "weld_cell_assignment": {"type": "string"},
            "laser_program_complexity": {"type": "string"}
        }
    }
}
```

### Change Output Template

Edit the `JINJA_TEMPLATE` for custom Markdown formatting.

---

## 🚀 Next Steps & Iterations

### Phase 1 (MVP) ✅
- [x] Ingest PDFs + Confluence
- [x] Generate structured plans
- [x] Markdown + JSON output
- [x] Optional Confluence publishing

### Phase 2 (Enhancements)
- [ ] Coverage gate (PASS/NEEDS-INFO status)
- [ ] Interactive checklist (✅/❓ for each APQP item)
- [ ] Better source citations (clickable links back to Confluence)
- [ ] Auto-labeling of published pages

### Phase 3 (Advanced)
- [x] **FastAPI REST API Server** - Service facade over CLI (`server/main.py`)
- [x] **API Endpoints**: `/ingest`, `/draft`, `/publish`, `/meeting/apply`, `/qa/grade`
- [x] **Interactive API Docs** - Swagger UI at `/docs`
- [ ] Realtime API for live meeting assistance
- [ ] Audio transcription (Whisper API)
- [ ] Drawing symbol extraction (vision models)
- [ ] Web dashboard (React frontend)

---

## 🌐 FastAPI Server (NEW!)

### Run the API Server

```powershell
# Start server with auto-reload
python run_server.py

# Server runs at: http://localhost:8001
# API Docs: http://localhost:8001/docs
```

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ingest` | POST | Upload files, create session |
| `/draft` | POST | Generate Strategic Build Plan |
| `/publish` | POST | Publish plan to Confluence |
| `/meeting/apply` | POST | Apply meeting notes to plan |
| `/qa/grade` | POST | Grade plan quality (5 dimensions) |
| `/session/{id}` | DELETE | Cleanup session |

### Quick API Example

```bash
# 1. Upload files
curl -X POST http://localhost:8001/ingest \
  -F "files=@inputs/drawing.pdf" \
  -F "customer=ACME Corp"

# 2. Generate plan (use session_id from step 1)
curl -X POST http://localhost:8001/draft \
  -H "Content-Type: application/json" \
  -d '{"session_id":"YOUR_SESSION_ID","project_name":"ACME Bracket"}'

# 3. View in browser: http://localhost:8001/docs
```

**See `server/README.md` for complete API documentation.**

---

## 📞 Support & Resources

### Confluence Setup
- **Space**: `KB` (Knowledge Base) at https://northernmfg.atlassian.net/wiki/spaces/KB/overview
- **Structure**: Customer → Family of Parts → Job# → APQP Notes → Strategic Build Plan
- **Labels**: Use `customer-<name>` and `family-of-parts-<family>` for CQL queries

### CQL Query Examples

```sql
-- Customer-specific pages
space = KB AND label = "customer-acme" AND type = page

-- Family of parts
space = KB AND label = "family-of-parts-brackets" AND type = page

-- Combined
space = KB AND (label = "customer-acme" OR label = "family-of-parts-brackets") AND type = page
```

### Getting Help
- OpenAI API: [platform.openai.com/docs](https://platform.openai.com/docs)
- Confluence API: [developer.atlassian.com/cloud/confluence/rest/](https://developer.atlassian.com/cloud/confluence/rest/)
- Python/VS Code: Check `.vscode/tasks.json` for one-click commands

---

## ✅ Current Status

- ✅ Native Windows setup (no WSL!)
- ✅ Python 3.13 virtual environment
- ✅ Production-ready code with Responses API
- ✅ VS Code tasks configured
- 🔄 Ready for updated dependencies install and `.env` configuration!

---

**Next Steps:**
1. Run: `pip install -r requirements.txt` (install updated dependencies)
2. Edit `.env` with your OpenAI API key
3. Place test PDFs in `inputs/` folder
4. Run: `python apqp_starter.py --project "Test" --files .\inputs\*.pdf`

---

**Built for Northern Manufacturing Co., Inc.**  
_Stainless sheet-metal fabrication excellence_
