"""
FastAPI server for Strategic Build Planner

Minimal service facade over the CLI logic.
Endpoints: /ingest, /draft, /publish, /meeting/apply, /qa/grade
"""

import os
import json
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from functools import lru_cache

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Import shared library modules
from .lib.schema import PLAN_SCHEMA, APQP_CHECKLIST
from agent import StrategicBuildPlannerAgent
from agent.tools.confluence import (
    ConfluenceConfigError,
    confluence_create_child,
    confluence_search_family,
)
from .lib.asana import AsanaConfigError, create_tasks as create_asana_tasks
from .lib.rendering import render_plan_md
from .lib.vectorstore import (
    create_vector_store, delete_vector_store
)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Strategic Build Planner API",
    description="Manufacturing-ready Strategic Build Plans for stainless steel sheet-metal fabrication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions = {}

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
CONFIG = {
    "openai_model_plan": os.getenv("OPENAI_MODEL_PLAN", "o4-mini"),
    "confluence_base": os.getenv("CONFLUENCE_BASE_URL"),
    "confluence_email": os.getenv("CONFLUENCE_EMAIL"),
    "confluence_token": os.getenv("CONFLUENCE_API_TOKEN"),
    "confluence_space": os.getenv("CONFLUENCE_SPACE_KEY"),
    "confluence_parent": os.getenv("CONFLUENCE_PARENT_PAGE_ID"),
}

# Initialize shared agent wrapper
planner_agent = StrategicBuildPlannerAgent(
    openai_client,
    model=CONFIG["openai_model_plan"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
METRICS_DIR = BASE_DIR / "outputs" / "metrics"


# --------------------
# Pydantic Models
# --------------------
class IngestResponse(BaseModel):
    session_id: str
    message: str
    file_count: int
    file_names: list[str]


class DraftRequest(BaseModel):
    session_id: str
    project_name: str
    customer: Optional[str] = None
    family: Optional[str] = None


class DraftResponse(BaseModel):
    plan_json: dict
    plan_markdown: str
    source_file_names: list[str]
    vector_store_id: str


class PublishRequest(BaseModel):
    customer: str
    family: str
    project: str
    markdown: str
    parent_page_id: Optional[str] = None


class PublishResponse(BaseModel):
    page_id: str
    url: str
    title: str


class AsanaTaskModel(BaseModel):
    name: str
    notes: Optional[str] = None
    due_on: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    source_hint: Optional[str] = None
    plan_url: Optional[str] = None


class MeetingApplyRequest(BaseModel):
    session_id: Optional[str] = None
    plan_json: dict
    transcript_texts: list[str]


class MeetingApplyResponse(BaseModel):
    updated_plan_json: dict
    updated_plan_markdown: str
    changes_summary: str
    suggested_tasks: list[AsanaTaskModel]


class QAGradeRequest(BaseModel):
    plan_json: dict


class QAGradeResponse(BaseModel):
    score: float
    reasons: list[str]
    fixes: list[str]


class AsanaTasksRequest(BaseModel):
    project_id: str
    plan_json: dict
    tasks: Optional[list[AsanaTaskModel]] = None
    plan_url: Optional[str] = None


class AsanaTasksResponse(BaseModel):
    created: list[dict]


UNKNOWN_MARKERS = ("UNKNOWN", "TBD", "T.B.D.")
DELTA_MARKERS = ("delta", "change", "gap", "follow-up", "update")


def _has_unknown(value: Any) -> bool:
    if isinstance(value, str):
        upper = value.upper()
        return any(marker in upper for marker in UNKNOWN_MARKERS)
    return False


def _has_delta(value: Any) -> bool:
    if isinstance(value, str):
        lower = value.lower()
        return any(marker in lower for marker in DELTA_MARKERS)
    return False


def _generate_followup_tasks(plan_json: dict) -> List[Dict[str, Optional[str]]]:
    tasks: List[Dict[str, Optional[str]]] = []
    seen: set[tuple[str, str]] = set()

    def add_task(name: str, notes: str, *, source_hint: Optional[str] = None, due_on: Optional[str] = None,
                 assignee: Optional[str] = None, priority: str = "TBD") -> None:
        key = (name, notes)
        if key in seen:
            return
        seen.add(key)
        task: Dict[str, Optional[str]] = {
            "name": name,
            "notes": notes,
            "source_hint": source_hint,
            "priority": priority,
        }
        if due_on:
            task["due_on"] = due_on
        if assignee:
            task["assignee"] = assignee
        tasks.append(task)

    # Requirements with unknowns or deltas
    for requirement in plan_json.get("requirements", []):
        text = requirement.get("requirement", "")
        if _has_unknown(text) or _has_delta(text):
            topic = requirement.get("topic", "Requirement")
            add_task(
                f"Clarify requirement: {topic}",
                text,
                source_hint=requirement.get("source_hint") or topic,
            )

    # Summary-level UNKNOWN strings
    for field in [
        "summary",
        "process_flow",
        "tooling_fixturing",
        "quality_plan",
        "materials_finishes",
        "pack_ship",
    ]:
        value = plan_json.get(field)
        if isinstance(value, str) and (_has_unknown(value) or _has_delta(value)):
            add_task(
                f"Update {field.replace('_', ' ')}",
                value,
                source_hint=field,
            )

    # CTQs or cost levers with placeholders
    for collection_name in ["ctqs", "cost_levers"]:
        for item in plan_json.get(collection_name, []):
            if isinstance(item, str) and (_has_unknown(item) or _has_delta(item)):
                add_task(
                    f"Refine {collection_name[:-1]} detail",
                    item,
                    source_hint=collection_name,
                )

    # Risks missing mitigations or UNKNOWN data
    for risk in plan_json.get("risks", []):
        mitigation = risk.get("mitigation", "")
        if _has_unknown(mitigation) or not mitigation:
            add_task(
                f"Define mitigation for risk: {risk.get('risk', 'Unnamed risk')}",
                mitigation or "Mitigation missing",
                source_hint=risk.get("risk"),
                due_on=risk.get("due_date"),
                assignee=risk.get("owner"),
            )

    # Open questions are explicit follow-ups
    for idx, question in enumerate(plan_json.get("open_questions", []), start=1):
        add_task(
            f"Resolve open question #{idx}",
            question,
            source_hint="open_questions",
        )

    if not tasks:
        add_task(
            "Review Strategic Build Plan",
            "No UNKNOWN values detected; review plan with manufacturing SMEs for additional improvement opportunities.",
        )

    return tasks


@lru_cache(maxsize=1)
def _load_eval_assets() -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    rubric_path = BASE_DIR / "evals" / "rubric.json"
    gold_dir = BASE_DIR / "evals" / "gold"

    if not rubric_path.exists():
        raise RuntimeError("Eval rubric not found. Ensure evals/rubric.json is present.")

    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    gold_examples: List[Dict[str, Any]] = []
    if gold_dir.exists():
        for path in sorted(gold_dir.glob("*.json")):
            gold_examples.append(json.loads(path.read_text(encoding="utf-8")))

    return rubric, gold_examples


def _log_metric(entry: Dict[str, Any]) -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_file = METRICS_DIR / "qa_metrics.jsonl"
    with metrics_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


# --------------------
# Helper Functions
# --------------------
def get_temp_dir() -> Path:
    """Get or create temp directory for file storage"""
    temp_dir = Path(tempfile.gettempdir()) / "strategic_build_planner"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


# --------------------
# Endpoints
# --------------------
@app.get("/")
async def root():
    return {
        "message": "Strategic Build Planner API",
        "version": "1.0.0",
        "endpoints": [
            "/ingest",
            "/draft",
            "/publish",
            "/meeting/apply",
            "/qa/grade"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_files(
    files: list[UploadFile] = File(...),
    customer: Optional[str] = Form(None),
    family: Optional[str] = Form(None),
    cql: Optional[str] = Form(None)
):
    """
    Upload files and create a session for plan generation.
    
    Returns a session ID that can be used in /draft endpoint.
    """
    session_id = str(uuid.uuid4())
    session_dir = get_temp_dir() / session_id
    session_dir.mkdir(exist_ok=True)
    
    file_names = []
    file_paths = []
    
    for upload_file in files:
        # Save uploaded file
        filename = upload_file.filename or f"uploaded_{len(file_names)+1}"
        file_path = session_dir / filename
        content = await upload_file.read()
        file_path.write_bytes(content)
        
        file_names.append(filename)
        file_paths.append(str(file_path))
    
    # Store session data
    sessions[session_id] = {
        "customer": customer,
        "family": family,
        "cql": cql,
        "file_paths": file_paths,
        "file_names": file_names,
        "created_at": datetime.now().isoformat()
    }
    
    return IngestResponse(
        session_id=session_id,
        message=f"Uploaded {len(files)} file(s) successfully",
        file_count=len(files),
        file_names=file_names
    )


@app.post("/draft", response_model=DraftResponse)
async def draft_plan(request: DraftRequest):
    """
    Generate Strategic Build Plan from ingested files.
    
    Uses OpenAI Vector Store + Responses API with structured outputs.
    """
    # Get session data
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    file_paths = session["file_paths"]
    project_name = request.project_name
    
    try:
        # Create vector store with files
        vector_store_id, source_file_names = create_vector_store(
            openai_client,
            project_name,
            file_paths
        )
        
        # Generate plan using Strategic Build Planner Agent
        plan_json = planner_agent.draft_plan(
            vector_store_id=vector_store_id,
            project_name=project_name,
            customer=request.customer,
            family=request.family,
        )
        
        # Override customer/project if provided
        if request.customer:
            plan_json["customer"] = request.customer
        if request.family:
            plan_json["project"] = request.family
        
        # Render to Markdown
        plan_markdown = render_plan_md(plan_json)
        
        # Store vector_store_id in session for cleanup
        session["vector_store_id"] = vector_store_id
        
        return DraftResponse(
            plan_json=plan_json,
            plan_markdown=plan_markdown,
            source_file_names=source_file_names,
            vector_store_id=vector_store_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {str(e)}")


@app.post("/publish", response_model=PublishResponse)
async def publish_to_confluence(request: PublishRequest):
    """
    Publish Strategic Build Plan to Confluence.
    
    Resolves family page (parent) and creates child page with v2 API.
    """
    if not CONFIG["confluence_base"]:
        raise HTTPException(status_code=400, detail="Confluence not configured")
    
    try:
        # Resolve parent page ID
        parent_id = request.parent_page_id or CONFIG["confluence_parent"]

        # If family is provided, search for it
        if request.family and not parent_id:
            search_result = confluence_search_family(
                f'type=page AND title~"{request.family}"',
                limit=1,
            )
            if search_result:
                parent_id = search_result["page_id"]
        
        # Convert Markdown to basic HTML (simple approach)
        # In production, use a proper markdown-to-confluence converter
        storage_html = "<p>" + "</p><p>".join(
            line for line in request.markdown.splitlines()
        ) + "</p>"
        
        # Create page title
        title = f"Strategic Build Plan — {request.project}"
        
        page = confluence_create_child(parent_id, title, storage_html)

        return PublishResponse(
            page_id=page["page_id"],
            url=page["url"],
            title=page.get("title", title)
        )
        
    except ConfluenceConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}")


@app.post("/meeting/apply", response_model=MeetingApplyResponse)
async def apply_meeting_notes(request: MeetingApplyRequest):
    """
    Apply meeting transcripts to existing plan.
    
    Merges decisions and action items from meeting notes into the plan.
    """
    try:
        updated_plan_json = planner_agent.apply_meeting_notes(
            plan_json=request.plan_json,
            transcript_texts=request.transcript_texts,
        )

        changes_summary = "Meeting notes applied successfully"
        suggested_tasks_raw = _generate_followup_tasks(updated_plan_json)
        suggested_tasks = [
            AsanaTaskModel(**{k: v for k, v in task.items() if v is not None})
            for task in suggested_tasks_raw
        ]

        return MeetingApplyResponse(
            updated_plan_json=updated_plan_json,
            updated_plan_markdown=render_plan_md(updated_plan_json),
            changes_summary=changes_summary,
            suggested_tasks=suggested_tasks,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Meeting apply failed: {str(e)}")


@app.post("/qa/grade", response_model=QAGradeResponse)
async def grade_plan_quality(request: QAGradeRequest):
    """
    Grade plan quality against rubric.
    
    Evaluates: Completeness, Specificity, Actionability, Manufacturability, Risk
    """
    try:
        rubric, gold_examples = _load_eval_assets()
        grade_result = planner_agent.evaluate_plan(request.plan_json, rubric, gold_examples)

        fixes = grade_result.get("fixes", [])
        minimum_fixes = max(int(rubric.get("minimum_fixes", 3)), 3)
        fallback_fix = "Assign owners and due dates for any remaining UNKNOWN items."
        while len(fixes) < minimum_fixes:
            fixes.append(fallback_fix)

        reasons = grade_result.get("reasons", []) or ["Review plan sections against rubric dimensions."]
        score = float(grade_result.get("score", 0.0))

        _log_metric({
            "timestamp": datetime.utcnow().isoformat(),
            "score": score,
            "project": request.plan_json.get("project"),
            "customer": request.plan_json.get("customer"),
        })

        return QAGradeResponse(
            score=score,
            reasons=reasons,
            fixes=fixes,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA grading failed: {str(e)}")


@app.post("/asana/tasks", response_model=AsanaTasksResponse)
async def create_asana_tasks_endpoint(request: AsanaTasksRequest):
    """Create Asana tasks derived from the Strategic Build Plan."""
    try:
        if request.tasks:
            tasks_payload = [task.model_dump(exclude_none=True) for task in request.tasks]
        else:
            tasks_payload = _generate_followup_tasks(request.plan_json)

        if not tasks_payload:
            tasks_payload = _generate_followup_tasks(request.plan_json)

        created = create_asana_tasks(
            request.project_id,
            tasks_payload,
            default_plan_url=request.plan_url,
        )
        return AsanaTasksResponse(created=created)

    except AsanaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Asana task creation failed: {str(e)}")


# --------------------
# Cleanup endpoint (optional)
# --------------------
@app.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """Delete session and cleanup temporary files"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete temp files
    session_dir = get_temp_dir() / session_id
    if session_dir.exists():
        import shutil
        shutil.rmtree(session_dir)
    
    # Delete vector store if exists
    if "vector_store_id" in session:
        delete_vector_store(openai_client, session["vector_store_id"])
    
    # Remove from sessions
    del sessions[session_id]
    
    return {"message": "Session cleaned up successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
