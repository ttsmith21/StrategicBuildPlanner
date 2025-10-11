# Specialist Agents Testing Guide

## 🎯 Overview

Your Strategic Build Planner uses a **collaborative multi-agent approach**. Instead of a single AI creating the entire plan, **7 specialist agents** work together, each focusing on their domain of expertise:

| Agent | File | What It Does |
|-------|------|--------------|
| **QEA** | `server/agents/qea.py` | Quality Extractor Agent - Extracts requirements from specs |
| **QDD** | `server/agents/qdd.py` | Quality Delta Detector - Compares against baseline quality |
| **QMA** | `server/agents/qma.py` | Quality Manager Agent - Refines quality plan, CTQs, inspections |
| **PMA** | `server/agents/pma.py` | Purchasing Manager Agent - Sourcing, long-leads, coatings, machined parts |
| **EMA** | `server/agents/ema.py` | Engineering Manager Agent - Engineering instructions, routing, fixtures |
| **SCA** | `server/agents/sca.py` | Scheduling Agent - Release plan, milestones, "do early" list |
| **SBP-QA** | `server/agents/sbpqa.py` | Strategic Build Plan QA - Quality gate for the plan itself |

---

## 📋 **NEW Simplified Workflow** ⭐

### Old Way (Unnecessary):
```
Upload docs → Draft (single AI) → Refine with specialists
```

### **New Way (Direct to Specialists):**
```
Upload docs → Specialists build plan collaboratively
```

---

## 🧪 Test Workflow

### Step 1: Ingest Documents (Now Does Everything!)

Upload your project files - this now creates the vector store and context pack immediately:

```bash
curl -X POST http://localhost:8001/ingest \
  -F "project_name=Test Bracket Project" \
  -F "customer=ACME Corp" \
  -F "files=@inputs/sample_project_test.txt"
```

**Response now includes:**
- `session_id` - Use this for subsequent calls
- `vector_store_id` - References to uploaded files ✅ **NEW**
- `context_pack` - Canonical facts and sources ✅ **NEW**
- `file_names` - List of ingested files

**You can now skip directly to Step 2!**

---

### Step 2: Run Specialist Agents ⭐ **Direct from Ingest**

No draft needed! Run the specialists directly:

```bash
curl -X POST http://localhost:8001/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID_FROM_STEP_1"
  }'
```

**What happens inside:**
1. ✅ **QMA** patches `quality_plan` section (CTQs, inspections, passivation)
2. ✅ **PMA** patches `purchasing` section (long-leads, machined parts, coatings, restrictions)
3. ✅ **SCA** patches `release_plan` + `execution_strategy` (milestones, "do early" list)
4. ✅ **EMA** patches `engineering_instructions` (routing, fixtures, programs)
5. ✅ **SBP-QA** evaluates the final plan (score 0-100, fixes, blockers)

**Response includes:**
- `plan_json` - **Updated plan** with all specialist patches merged
- `tasks_suggested` - Actionable tasks from all agents (tagged BUY, ENG, QA, SCHED)
- `qa` - Quality assessment with score, reasons, fixes, blocked status
- `conflicts` - Any contradictions found between specialists

---

### Step 4: Review Results

Check the specialist outputs:

#### Quality Plan (from QMA)
```json
{
  "quality_plan": {
    "ctqs": ["Flatness ±0.005\"", "Surface finish Ra 32"],
    "inspection_levels": ["First Article", "In-Process 100%"],
    "passivation": "ASTM A967 Type 2",
    "hold_points": ["Post-weld inspection", "Final CMM scan"],
    "required_tests": ["Salt spray 96hr per ASTM B117"],
    "documentation": ["PPAP Level 3", "MTR required"],
    "metrology": ["CMM for GD&T", "Surface roughness tester"]
  }
}
```

#### Purchasing Plan (from PMA)
```json
{
  "purchasing": {
    "long_leads": [
      {
        "item": "316L Sheet 0.125\" thick",
        "lead_time": "8-10 weeks",
        "vendor_hint": "Service Steel"
      }
    ],
    "machined_parts": [
      {
        "part": "Mounting boss",
        "material": "17-4PH",
        "tolerances": "±0.002\"",
        "outsource_required": true
      }
    ],
    "coatings": [
      {
        "coating_type": "Passivation",
        "specification": "ASTM A967",
        "vendor_rfq_required": true
      }
    ],
    "restrictions": [
      {
        "restriction_type": "COO",
        "requirement": "DFARS compliant material",
        "compliance_action": "Request MTR with COO declaration"
      }
    ]
  }
}
```

#### Tasks (from all agents)
```json
{
  "tasks_suggested": [
    {
      "name": "RFQ – Passivation vendor per ASTM A967 Type 2",
      "owner_hint": "BUY",
      "notes": "Confirm citric acid method available",
      "due_on": "2025-10-20"
    },
    {
      "name": "Build weld fixture for tight flatness control",
      "owner_hint": "ENG",
      "notes": "Requires precision ground tooling plate"
    },
    {
      "name": "Schedule First Article Inspection with customer",
      "owner_hint": "SCHED",
      "priority": "HIGH"
    }
  ]
}
```

#### QA Scorecard (from SBP-QA)
```json
{
  "qa": {
    "score": 78.5,
    "reasons": [
      "Quality plan comprehensive with proper CTQ mapping",
      "Purchasing identified long-lead passivation vendor",
      "Engineering routing needs more detail on weld sequence"
    ],
    "fixes": [
      "Add specific weld sequencing to prevent distortion",
      "Define fixture acceptance criteria",
      "Clarify CMM inspection frequency"
    ],
    "blocked": false
  }
}
```

---

## 🧪 Testing in the UI

1. **Start the server** (already running at http://localhost:8001)

2. **Open the web UI** at http://localhost:5173

3. **Upload files** via the Ingest tab
   - Enter project name and customer
   - Upload your docs
   - Get session ID, vector store, and context pack **immediately** ✅

4. **Click "Run Specialist Agents"** button ⭐ **Direct from Ingest!**
   - No need to click "Draft" first!
   - Specialists build the plan collaboratively from scratch
   - Watch the progress indicator
   - See each agent's contribution in real-time
   - Review the complete plan with all specialist sections

5. **Review tasks** - Organized by owner (BUY, ENG, QA, SCHED)

6. **Check QA score** - See if the plan is ready to publish

7. **(Optional) Use Draft** - If you want a quick single-agent plan first, click "Draft" before "Run Specialist Agents"

---

## 🔍 What to Look For

### ✅ Success Indicators

- **QMA** should add specific CTQs, inspection methods, and passivation specs
- **PMA** should flag long-lead items, coatings, and machined parts
- **SCA** should create milestones and "do early" tasks
- **EMA** should provide detailed routing with fixture/tooling notes
- **SBP-QA** score should be above 70 (threshold for publish)

### ⚠️ Potential Issues

- **Score < 70**: Plan blocked from publishing; review "fixes" list
- **Empty patches**: Agent may not have found relevant data in docs
- **Conflicts**: Multiple sources contradict each other (manual resolution needed)
- **Missing tasks**: Agents didn't identify actionable items (may need better input docs)

---

## 📊 Current Architecture (As Implemented)

```
User uploads files
       ↓
[/ingest] → Creates vector_store_id + context_pack + session
       ↓    ✅ Everything ready for specialists!
       ↓
[/agents/run] → coordinator.run_specialists()
       ↓         ├─ QMA (quality_plan patch)
       ↓         ├─ PMA (purchasing patch)
       ↓         ├─ SCA (release_plan + execution_strategy patch)
       ↓         ├─ EMA (engineering_instructions patch)
       ↓         └─ SBP-QA (evaluates merged plan)
       ↓
       ↓         Complete plan returned with tasks + QA score
       ↓
[/qa/grade] → Optional: Re-evaluate plan
       ↓
[/publish] → Confluence page creation (if QA passed)
```

### **Optional: Use /draft for Quick Single-Agent Plan**

If you want a fast "monolithic" draft before specialists refine it:

```
[/ingest] → [/draft] → [/agents/run]
```

But **you don't need /draft anymore** - specialists can build from scratch!

---

## 🎯 Next Steps After Testing

Based on test results, you can:

1. **Tune agent prompts** in `server/agents/prompts/*.txt`
2. **Adjust QA thresholds** in SBP-QA scoring
3. **Add parallel execution** (optional optimization)
4. **Implement CRA** (Capability Review Agent) if needed
5. **Refine task generation** logic per agent

---

## 📝 Quick Test Commands

### **New Simplified Workflow** (2 steps):
```bash
# 1. Ingest (creates vector store + context pack)
SESSION=$(curl -s -X POST http://localhost:8001/ingest \
  -F "project_name=Test Bracket" \
  -F "customer=ACME Corp" \
  -F "files=@inputs/sample_project_test.txt" | jq -r '.session_id')

# 2. Run specialists (builds complete plan)
curl -s -X POST http://localhost:8001/agents/run \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\"}" \
  | jq '{qa: .qa, task_count: (.tasks_suggested | length), plan_sections: .plan_json | keys}'
```

### Old 3-step workflow (still works if you want a quick draft first):
```bash
# 1. Ingest
SESSION=$(curl -s -X POST http://localhost:8001/ingest \
  -F "project_name=Test" \
  -F "customer=ACME" \
  -F "files=@inputs/sample_project_test.txt" | jq -r '.session_id')

# 2. Draft (optional - creates base plan with single agent)
curl -s -X POST http://localhost:8001/draft \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"customer\": \"ACME\", \"project\": \"Bracket\"}" \
  | jq '.plan_json.project'

# 3. Run specialists (refines the draft)
curl -s -X POST http://localhost:8001/agents/run \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\"}" \
  | jq '{qa: .qa, task_count: (.tasks_suggested | length)}'
```

---

## 🐛 Troubleshooting

### Server not starting?
- Check `.env` has `OPENAI_API_KEY`
- Verify Python environment: `.venv\Scripts\python.exe --version`

### Agents returning empty patches?
- Check uploaded files have actual content
- Review agent prompts for relevance to your document types
- Enable debug logging: `LOGGER.setLevel(logging.DEBUG)`

### QA score always low?
- Review `server/agents/prompts/sbpqa.txt` rubric
- Check baseline quality file: `server/lib/baseline_quality.json`
- Inspect QA "reasons" and "fixes" for specific issues

---

**Ready to test?** Refresh your browser at http://localhost:5173 and try the full workflow! 🚀
