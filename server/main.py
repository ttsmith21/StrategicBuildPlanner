"""
FastAPI server for Strategic Build Planner

Minimal service facade over the CLI logic.
Endpoints: /ingest, /draft, /publish, /meeting/apply, /qa/grade
"""

import os
import json
import logging
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Literal, Tuple
from datetime import datetime
from functools import lru_cache

import requests
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Import shared library modules
from .lib.schema import PLAN_SCHEMA, APQP_CHECKLIST, ContextPack, Fact, Citation, Source
from .lib.context_pack import build_source_registry, freeze_context_pack
from .agents.coordinator import run_specialists as coordinator_run_specialists
from agent import StrategicBuildPlannerAgent
from agent.tools.confluence import (
    ConfluenceConfigError,
    confluence_create_child,
    confluence_search_family,
)
from .lib.confluence import search_pages, get_page_summary
from .lib.asana import (
    AsanaConfigError,
    create_tasks as create_asana_tasks,
    list_projects as asana_list_projects,
    create_project as asana_create_project,
    list_teams as asana_list_teams,
    list_workspaces as asana_list_workspaces,
    detect_default_workspace_gid as asana_detect_default_workspace_gid,
    _fingerprint,
    fingerprint as asana_fingerprint,
)
from .lib.rendering import render_plan_md
from .lib.session_store import SessionStore
from .lib.vectorstore import (
    create_vector_store, delete_vector_store, append_files_to_vector_store
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Strategic Build Planner API",
    description="Manufacturing-ready Strategic Build Plans for stainless steel sheet-metal fabrication",
    version="1.0.0"
)

# CORS middleware
allowed_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:4173",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions = {}

LOGGER = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
CONFIG = {
    "openai_model_plan": os.getenv("OPENAI_MODEL_PLAN", "gpt-5"),
    "confluence_base": os.getenv("CONFLUENCE_BASE_URL"),
    "confluence_email": os.getenv("CONFLUENCE_EMAIL"),
    "confluence_token": os.getenv("CONFLUENCE_API_TOKEN"),
    "confluence_space": os.getenv("CONFLUENCE_SPACE_KEY"),
    "confluence_parent": os.getenv("CONFLUENCE_PARENT_PAGE_ID"),
    "confluence_customer_label": os.getenv("CONFLUENCE_CUSTOMER_LABEL"),
    "confluence_customer_parent": os.getenv("CONFLUENCE_CUSTOMER_PARENT_ID"),
    "confluence_family_label": os.getenv("CONFLUENCE_FAMILY_LABEL"),
    "confluence_family_parent": os.getenv("CONFLUENCE_FAMILY_PARENT_ID"),
}

# Initialize shared agent wrapper
planner_agent = StrategicBuildPlannerAgent(
    openai_client,
    model=CONFIG["openai_model_plan"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
METRICS_DIR = BASE_DIR / "outputs" / "metrics"
SESSIONS_DIR = BASE_DIR / "outputs" / "sessions"
session_store = SessionStore(SESSIONS_DIR)


# --------------------
# Pydantic Models
# --------------------
class IngestResponse(BaseModel):
    session_id: str
    message: str
    file_count: int
    file_names: list[str]
    vector_store_id: str
    context_pack: ContextPack


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
    context_pack: ContextPack


class AgentsRunRequest(BaseModel):
    session_id: Optional[str] = None
    plan_json: Optional[dict] = None
    vector_store_id: Optional[str] = None
    context_pack: Optional[dict] = None


class AgentsRunResponse(BaseModel):
    plan_json: dict
    plan_markdown: str
    tasks_suggested: list[dict]
    tasks: Optional[dict] = None
    qa: dict
    conflicts: list[dict]
    # Additional helpful fields for frontend cohesion
    context_pack: Optional[dict] = None
    session_id: Optional[str] = None
    vector_store_id: Optional[str] = None
    snapshot_id: Optional[str] = None


class PublishRequest(BaseModel):
    customer: str
    project: str
    markdown: str
    parent_page_id: Optional[str] = None
    family_name: Optional[str] = None
    family: Optional["FamilySelection"] = None


class PublishResponse(BaseModel):
    page_id: str
    url: str
    title: str
    space_key: Optional[str] = None
    parent_id: Optional[str] = None


class AsanaTaskModel(BaseModel):
    name: str
    notes: Optional[str] = None
    due_on: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    source_hint: Optional[str] = None
    plan_url: Optional[str] = None
    section: Optional[str] = None
    fingerprint: Optional[str] = None


class MeetingPrepRequest(BaseModel):
    """Request for meeting prep generation"""
    session_id: str


class MeetingAgendaTopic(BaseModel):
    """Single APQP topic for meeting agenda"""
    name: str
    discussion_prompts: list[str]
    known_facts: list[str]
    open_questions: list[str]
    suggested_duration_minutes: int


class MeetingAgenda(BaseModel):
    """Structured meeting agenda"""
    topics: list[MeetingAgendaTopic]
    total_duration_minutes: int


class MeetingPrepResponse(BaseModel):
    """Meeting preparation materials"""
    project_brief_markdown: str
    meeting_agenda: MeetingAgenda
    lessons_learned_summary: Optional[str] = None
    critical_questions: list[str]


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
    blocked: bool = False


# --------------------
# On-demand rendering endpoint (render markdown from a plan_json and optional context_pack)
# --------------------

class RenderRequest(BaseModel):
    plan_json: dict
    context_pack: Optional[dict] = None


class RenderResponse(BaseModel):
    plan_markdown: str


@app.post("/render", response_model=RenderResponse)
async def render_plan_endpoint(req: RenderRequest):
    try:
        payload = dict(req.plan_json)
        if req.context_pack and "context_pack" not in payload:
            # Validate minimally to enforce schema shape and avoid typos
            try:
                cp = ContextPack.model_validate(req.context_pack)
                payload["context_pack"] = cp.model_dump()
            except Exception:
                # Fall back to raw insertion if validation fails
                payload["context_pack"] = req.context_pack
        md = render_plan_md(payload)
        return RenderResponse(plan_markdown=md)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to render markdown: {exc}")


class AsanaTasksRequest(BaseModel):
    project_id: str
    plan_json: dict
    tasks: Optional[list[AsanaTaskModel]] = None
    plan_url: Optional[str] = None


class AsanaTasksResponse(BaseModel):
    created: list[dict]
    skipped: list[dict]


class ConfluencePageSummary(BaseModel):
    id: str
    title: str
    url: str
    space_key: Optional[str] = None


class FamilySelection(BaseModel):
    page_id: str
    space_key: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None


class AsanaProjectSummary(BaseModel):
    gid: str
    name: str
    url: Optional[str] = None
    archived: Optional[bool] = False
    team: Optional[Dict[str, Optional[str]]] = None


class AsanaTeamSummary(BaseModel):
    gid: str
    name: str


class AsanaProjectCreateRequest(BaseModel):
    name: str
    team_gid: Optional[str] = None
    private: bool = True


class AsanaProjectCreateResponse(BaseModel):
    gid: str
    name: str
    url: Optional[str] = None
    team: Optional[Dict[str, Optional[str]]] = None


class AuthStatusResponse(BaseModel):
    ok: bool
    reason: Optional[str] = None


class VersionInfo(BaseModel):
    version: str
    build_sha: str
    build_time: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    schema_version: Optional[str] = None


class AsanaWorkspaceSummary(BaseModel):
    gid: str
    name: Optional[str] = None
    is_organization: Optional[bool] = None


class AsanaWorkspaceDetectResponse(BaseModel):
    ok: bool
    workspace_gid: Optional[str] = None
    reason: Optional[str] = None


class DebugProbeRequest(BaseModel):
    vector_store_id: str
    query: str = "List the files and provide one 200-character excerpt."


class DebugProbeResponse(BaseModel):
    vector_store_id: str
    output_text: Optional[str] = None
    error: Optional[str] = None


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


_OWNER_GROUP_ORDER = ("ENG", "QA", "BUY", "SCHED", "LEGAL")
_OWNER_GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ENG": ("ENGINEER", "PROCESS", "ROUTING", "WELD", "FIXTURE", "PROGRAM"),
    "QA": ("QUALITY", "QA", "INSPECTION", "CTQ", "PPAP", "AUDIT"),
    "BUY": ("BUY", "PURCHAS", "SUPPL", "PROCURE", "VENDOR"),
    "SCHED": ("SCHED", "TIMELINE", "PLAN", "DEADLINE"),
    "LEGAL": ("LEGAL", "CONTRACT", "TERMS", "NDA"),
}


def _normalize_owner_hint(owner_hint: Optional[str]) -> str:
    if owner_hint:
        normalized = owner_hint.strip().upper()
        if normalized in _OWNER_GROUP_ORDER:
            return normalized
        for group, tokens in _OWNER_GROUP_KEYWORDS.items():
            if any(token in normalized for token in tokens):
                return group
    return "ENG"


def _group_tasks_by_owner_hint(tasks: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    grouped: dict[str, List[Dict[str, Optional[str]]]] = {key: [] for key in _OWNER_GROUP_ORDER}
    extra: List[Dict[str, Optional[str]]] = []
    for task in tasks:
        group = _normalize_owner_hint(task.get("owner_hint"))
        enriched = dict(task)
        enriched["owner_hint"] = group
        if group in grouped:
            grouped[group].append(enriched)
        else:
            extra.append(enriched)
    ordered: List[Dict[str, Optional[str]]] = []
    for key in _OWNER_GROUP_ORDER:
        ordered.extend(grouped[key])
    ordered.extend(extra)
    return ordered


def _generate_followup_tasks(plan_json: dict) -> List[Dict[str, Optional[str]]]:
    tasks: List[Dict[str, Optional[str]]] = []
    seen: set[tuple[str, str]] = set()

    def add_task(
        name: str,
        notes: str,
        *,
        source_hint: Optional[str] = None,
        due_on: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: str = "TBD",
        section: Optional[str] = None,
        owner_hint: Optional[str] = None,
    ) -> None:
        key = (name, notes)
        if key in seen:
            return
        seen.add(key)
        task: Dict[str, Optional[str]] = {
            "name": name,
            "notes": notes,
            "source_hint": source_hint,
            "priority": priority,
            "section": section,
        }
        if due_on:
            task["due_on"] = due_on
        if assignee:
            task["assignee"] = assignee
        normalized_owner = _normalize_owner_hint(owner_hint)
        if normalized_owner:
            task["owner_hint"] = normalized_owner
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
                section="requirements",
                owner_hint="ENG",
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
                section=field,
                owner_hint="ENG",
            )

    # CTQs or cost levers with placeholders
    for collection_name in ["ctqs", "cost_levers"]:
        for item in plan_json.get(collection_name, []):
            if isinstance(item, str) and (_has_unknown(item) or _has_delta(item)):
                add_task(
                    f"Refine {collection_name[:-1]} detail",
                    item,
                    source_hint=collection_name,
                    section=collection_name,
                    owner_hint="ENG",
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
                section="risks",
                owner_hint="QA",
            )

    # Open questions are explicit follow-ups
    for idx, question in enumerate(plan_json.get("open_questions", []), start=1):
        add_task(
            f"Resolve open question #{idx}",
            question,
            source_hint="open_questions",
            section="open_questions",
            owner_hint="ENG",
        )

    if not tasks:
        add_task(
            "Review Strategic Build Plan",
            "No UNKNOWN values detected; review plan with manufacturing SMEs for additional improvement opportunities.",
            section="general",
            owner_hint="ENG",
        )

    return tasks


_SOURCE_LABEL_HINTS: dict[str, tuple[str, ...]] = {
    "drawing": ("drawing", "print", ".dwg", ".dxf"),
    "po": ("po", "purchase order"),
    "quote": ("quote", "proposal"),
    "itp": ("itp", "inspection", "test plan"),
    "sow_spec": ("sow", "statement of work", "project spec", "project standard"),
    "customer_spec": ("customer spec", "flowdown"),
    "generic_spec": ("spec", "specification"),
    "meeting_notes": ("meeting", "minutes", "notes"),
    "lessons_learned": ("lessons", "retro"),
    "other": ("other",),
}


def _infer_source_labels(name: str) -> list[str]:
    labels: set[str] = set()
    lower_name = name.lower()
    for label, hints in _SOURCE_LABEL_HINTS.items():
        if any(hint in lower_name for hint in hints):
            labels.add(label)
    return sorted(labels)


def _build_uploaded_source_entries(session: dict) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    file_paths: list[str] = session.get("file_paths", [])
    file_names: list[str] = session.get("file_names", [])
    customer = session.get("customer")
    family = session.get("family")
    for idx, (path_str, name) in enumerate(zip(file_paths, file_names), start=1):
        entry = {
            "id": f"upload-{idx}",
            "filename": name,
            "path": path_str,
            "title": name,
            "customer": customer,
            "family": family,
            "labels": _infer_source_labels(name),
        }
        entries.append(entry)
    return entries


def _maybe_fetch_family_pages(session: dict) -> list[dict[str, Any]]:
    stored_page = session.get("family_page")
    if isinstance(stored_page, dict):
        entry = dict(stored_page)
        labels = entry.get("labels")
        if not isinstance(labels, list):
            entry["labels"] = ["family"]
        return [entry]

    page_id = session.get("family_page_id") or session.get("family")
    if not isinstance(page_id, str):
        return []
    if not (CONFIG.get("confluence_base") and CONFIG.get("confluence_email") and CONFIG.get("confluence_token")):
        return []
    try:
        summary = get_page_summary(
            CONFIG["confluence_base"],
            CONFIG["confluence_email"],
            CONFIG["confluence_token"],
            page_id,
        )
    except Exception:
        return []

    entry = {
        "id": summary["id"],
        "title": summary.get("title", summary["id"]),
        "url": summary.get("url"),
        "space_key": summary.get("space_key"),
        "labels": ["family", "confluence"],
        "customer": session.get("customer"),
        "family": session.get("family"),
    }
    return [entry]


@app.get("/asana/workspaces", response_model=list[AsanaWorkspaceSummary])
async def asana_workspaces():
    try:
        items = asana_list_workspaces()
        return [
            AsanaWorkspaceSummary(
                gid=str(item.get("gid")),
                name=item.get("name"),
                is_organization=item.get("is_organization"),
            )
            for item in items
        ]
    except AsanaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Asana workspaces list failed") from e


@app.get("/asana/workspace/auto", response_model=AsanaWorkspaceDetectResponse)
async def asana_workspace_auto():
    try:
        ws = asana_detect_default_workspace_gid()
        if ws:
            return AsanaWorkspaceDetectResponse(ok=True, workspace_gid=str(ws))
        return AsanaWorkspaceDetectResponse(ok=False, reason="No workspaces visible to this token")
    except AsanaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Asana workspace auto-detect failed") from e


def _pick_source_id(sources: list[Source], preferred_kinds: list[str]) -> Optional[str]:
    for kind in preferred_kinds:
        for source in sources:
            if source.kind == kind:
                return source.id
    return sources[0].id if sources else None


def _build_candidate_facts(plan_json: dict, sources: list[Source]) -> list[Fact]:
    facts: list[Fact] = []
    if not sources:
        return facts

    applies_if: dict[str, str] = {}
    customer = plan_json.get("customer")
    if isinstance(customer, str) and customer:
        applies_if["customer"] = customer
    family = plan_json.get("project")
    if isinstance(family, str) and family:
        applies_if["family"] = family

    def add_fact(
        topic: str,
        claim: Optional[str],
        authority: Literal["mandatory", "conditional", "reference", "internal"],
        precedence: int,
        preferred_kinds: list[str],
    ) -> None:
        if not claim or not isinstance(claim, str):
            return
        trimmed = claim.strip()
        if not trimmed:
            return
        source_id = _pick_source_id(sources, preferred_kinds)
        if not source_id:
            return
        fact_id = f"fact-{len(facts) + 1}"
        facts.append(
            Fact(
                id=fact_id,
                claim=trimmed,
                topic=topic,
                citation=Citation(source_id=source_id, page_ref=None, passage_sha=None),
                authority=authority,
                precedence_rank=precedence,
                applies_if=applies_if or None,
                status="proposed",
                confidence_model=0.75,
            )
        )

    materials_claim = plan_json.get("materials_finishes")
    if isinstance(materials_claim, dict):
        materials_claim = json.dumps(materials_claim, ensure_ascii=False)
    add_fact(
        "Materials",
        materials_claim,
        authority="mandatory",
        precedence=1,
        preferred_kinds=["drawing", "customer_spec", "itp"],
    )

    ctqs = plan_json.get("ctqs")
    if not isinstance(ctqs, list) or not ctqs:
        quality_plan_section = plan_json.get("quality_plan")
        if isinstance(quality_plan_section, dict):
            ctqs = quality_plan_section.get("ctqs")
    if isinstance(ctqs, list) and ctqs:
        first_ctq = ctqs[0] if isinstance(ctqs[0], str) else json.dumps(ctqs[0], ensure_ascii=False)
        add_fact(
            "CTQs",
            first_ctq,
            authority="conditional",
            precedence=2,
            preferred_kinds=["itp", "drawing", "customer_spec"],
        )

    quality_plan_value = plan_json.get("quality_plan")
    if isinstance(quality_plan_value, dict):
        snippets: list[str] = []
        ctq_list = quality_plan_value.get("ctqs") or []
        if ctq_list:
            snippets.append("CTQs: " + "; ".join(str(item) for item in ctq_list))
        inspection_levels = quality_plan_value.get("inspection_levels") or []
        if inspection_levels:
            snippets.append("Inspection: " + ", ".join(str(item) for item in inspection_levels))
        passivation = quality_plan_value.get("passivation")
        if passivation:
            snippets.append(f"Passivation: {passivation}")
        hold_points = quality_plan_value.get("hold_points") or []
        if hold_points:
            snippets.append("Hold points: " + "; ".join(str(item) for item in hold_points))
        quality_plan_summary = " | ".join(snippets)
    else:
        quality_plan_summary = quality_plan_value

    add_fact(
        "Quality Plan",
        quality_plan_summary,
        authority="reference",
        precedence=4,
        preferred_kinds=["generic_spec", "lessons_learned", "supplier_qm"],
    )

    if not facts:
        summary_claim = plan_json.get("summary") or "Strategic build plan draft baseline."
        add_fact(
            "Summary",
            summary_claim,
            authority="reference",
            precedence=5,
            preferred_kinds=[source.kind for source in sources],
        )

    return facts

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
            "/healthz",
            "/version",
            "/ingest",
            "/draft",
            "/publish",
            "/meeting/apply",
            "/qa/grade",
            "/confluence/customers",
            "/confluence/families",
            "/asana/projects",
            "/asana/tasks",
            "/asana/teams",
            "/asana/workspaces",
            "/asana/workspace/auto",
            "/sessions",
            "/sessions/{id}",
            "/sessions/{id}/messages",
        ]
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
@app.get("/version", response_model=VersionInfo)
async def version():
    return VersionInfo(
        version=app.version,
        build_sha=os.getenv("GIT_SHA", "dev"),
        build_time=os.getenv("BUILD_TIMESTAMP"),
        model=CONFIG.get("openai_model_plan"),
        prompt_version=os.getenv("PROMPT_VERSION"),
        schema_version=os.getenv("PLAN_SCHEMA_VERSION") or PLAN_SCHEMA.get("$id"),
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/debug/probe_vector_store", response_model=DebugProbeResponse)
async def debug_probe_vector_store(request: DebugProbeRequest):
    """Probe file_search on a vector_store_id using the server's OpenAI credentials."""
    try:
        assistant = openai_client.beta.assistants.create(
            name="Probe",
            instructions="Return a short plain text result only.",
            model=CONFIG.get("openai_model_plan") or "gpt-5",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [request.vector_store_id]}},
        )
        thread = openai_client.beta.threads.create()
        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=request.query,
        )
        run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            temperature=0.0,
            timeout=60,
        )
        # Extract last assistant message text
        msgs = openai_client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=5)
        for m in msgs.data:
            for part in getattr(m, "content", []) or []:
                if getattr(part, "type", None) == "text":
                    t = getattr(part, "text", None)
                    if t and getattr(t, "value", None):
                        return DebugProbeResponse(vector_store_id=request.vector_store_id, output_text=t.value)
        return DebugProbeResponse(vector_store_id=request.vector_store_id, output_text=None)
    except Exception as e:
        return DebugProbeResponse(vector_store_id=request.vector_store_id, error=str(e))


def _require_confluence_config() -> None:
    missing = [
        key
        for key in ("confluence_base", "confluence_email", "confluence_token", "confluence_space")
        if not CONFIG.get(key)
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Confluence configuration missing: " + ", ".join(missing),
        )


def _confluence_auth_status() -> AuthStatusResponse:
    required = {
        "CONFLUENCE_BASE_URL": CONFIG.get("confluence_base"),
        "CONFLUENCE_EMAIL": CONFIG.get("confluence_email"),
        "CONFLUENCE_API_TOKEN": CONFIG.get("confluence_token"),
        "CONFLUENCE_SPACE_KEY": CONFIG.get("confluence_space"),
    }
    missing = [env for env, value in required.items() if not value]
    if missing:
        return AuthStatusResponse(ok=False, reason="Missing: " + ", ".join(missing))
    return AuthStatusResponse(ok=True)


def _asana_auth_status() -> AuthStatusResponse:
    required_envs = {
        "ASANA_ACCESS_TOKEN": os.getenv("ASANA_ACCESS_TOKEN"),
        "ASANA_WORKSPACE_GID": os.getenv("ASANA_WORKSPACE_GID"),
    }
    missing = [env for env, value in required_envs.items() if not value]
    if missing:
        return AuthStatusResponse(ok=False, reason="Missing: " + ", ".join(missing))
    return AuthStatusResponse(ok=True)


@app.get("/auth/confluence/check", response_model=AuthStatusResponse)
async def auth_check_confluence():
    return _confluence_auth_status()


@app.get("/auth/asana/check", response_model=AuthStatusResponse)
async def auth_check_asana():
    return _asana_auth_status()


@app.get("/confluence/customers", response_model=list[ConfluencePageSummary])
async def list_confluence_customers(q: str = ""):
    _require_confluence_config()
    try:
        return search_pages(
            CONFIG["confluence_base"],
            CONFIG["confluence_email"],
            CONFIG["confluence_token"],
            CONFIG["confluence_space"],
            q,
            label=CONFIG.get("confluence_customer_label"),
            parent_id=CONFIG.get("confluence_customer_parent"),
        )
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Confluence search failed") from e


@app.get("/confluence/families", response_model=list[ConfluencePageSummary])
async def list_confluence_families(q: str = "", parent_id: Optional[str] = None):
    _require_confluence_config()
    try:
        return search_pages(
            CONFIG["confluence_base"],
            CONFIG["confluence_email"],
            CONFIG["confluence_token"],
            CONFIG["confluence_space"],
            q,
            label=CONFIG.get("confluence_family_label"),
            parent_id=parent_id or CONFIG.get("confluence_family_parent"),
        )
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Confluence search failed") from e


@app.get("/confluence/page/{page_id}", response_model=ConfluencePageSummary)
async def get_confluence_page_summary(page_id: str):
    _require_confluence_config()
    try:
        summary = get_page_summary(
            CONFIG["confluence_base"],
            CONFIG["confluence_email"],
            CONFIG["confluence_token"],
            page_id,
        )
        return summary
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Confluence lookup failed") from e


@app.post("/ingest", response_model=IngestResponse)
async def ingest_files(
    files: list[UploadFile] = File(...),
    project_name: Optional[str] = Form(None),
    customer: Optional[str] = Form(None),
    family: Optional[str] = Form(None),
    cql: Optional[str] = Form(None),
    files_meta: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    vector_store_id: Optional[str] = Form(None),
    append: Optional[bool] = Form(True),
):
    """
    Upload files, create vector store, and build context pack.
    
    Returns everything needed to run specialist agents directly - no draft required!
    """
    # Determine session behavior: create new or append to existing
    creating_new_session = not session_id
    if creating_new_session:
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
    
    try:
        # Create or append to vector store
        source_file_names: list[str] = []
        if vector_store_id and append:
            # Append to existing vector store
            source_file_names = append_files_to_vector_store(openai_client, vector_store_id, file_paths)
        else:
            # Create new vector store (requires a project name)
            if not project_name:
                project_name = sessions.get(session_id, {}).get("project_name") or "Untitled Project"
            vector_store_id, source_file_names = create_vector_store(
                openai_client,
                project_name,
                file_paths
            )
        
        # Build context pack (required for specialist agents)
        uploaded_entries = _build_uploaded_source_entries({"file_names": file_names, "file_paths": file_paths})
        meta_dict: Optional[dict[str, Any]] = None
        if isinstance(files_meta, str) and files_meta.strip():
            try:
                meta_dict = json.loads(files_meta)
            except Exception:
                LOGGER.warning("files_meta provided but could not be parsed as JSON; ignoring overrides")
        confluence_entries = []
        if cql or family:
            try:
                confluence_entries = _maybe_fetch_family_pages({"cql": cql, "family": family})
            except Exception as e:
                LOGGER.warning(f"Failed to fetch Confluence pages: {e}")
        
        # Merge newly uploaded sources into prior context if appending
        sources = build_source_registry(uploaded_entries, confluence_entries, files_meta=meta_dict)
        project_context: Dict[str, Any] = {
            "name": project_name or sessions.get(session_id, {}).get("project_name"),
            "customer": customer,
            "family": family,
            "generated_at": datetime.now().isoformat(),
            "vector_store_id": vector_store_id,
        }
        context_pack = freeze_context_pack(sources, [], project_context)
        
        # Store session data with vector store and context pack (in-memory)
        if creating_new_session or session_id not in sessions:
            sessions[session_id] = {
                "project_name": project_name,
                "customer": customer,
                "family": family,
                "cql": cql,
                "file_paths": file_paths,
                "file_names": file_names,
                "files_meta": meta_dict,
                "vector_store_id": vector_store_id,
                "context_pack": context_pack.model_dump(),
                "created_at": datetime.now().isoformat()
            }
        else:
            # Append mode: extend file lists and update vector_store_id/context
            sessions[session_id]["file_paths"] = (sessions[session_id].get("file_paths") or []) + file_paths
            sessions[session_id]["file_names"] = (sessions[session_id].get("file_names") or []) + file_names
            sessions[session_id]["vector_store_id"] = vector_store_id
            sessions[session_id]["context_pack"] = context_pack.model_dump()
        # Also create a persistent session record for resumability
        if creating_new_session:
            session_store.create(project_name=project_name, session_id=session_id)
        session_store.save_snapshot(session_id, plan_json={}, context_pack=context_pack.model_dump(), vector_store_id=vector_store_id, note="post-ingest")
        
        return IngestResponse(
            session_id=session_id,
            message=(
                f"Appended {len(files)} file(s) to session" if not creating_new_session and append
                else f"Uploaded {len(files)} file(s) and created vector store successfully"
            ),
            file_count=len(files),
            file_names=(sessions.get(session_id, {}).get("file_names") or file_names),
            vector_store_id=vector_store_id,
            context_pack=context_pack
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


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

        # Render to Markdown (initial)
        plan_markdown = render_plan_md(plan_json)

        uploaded_entries = _build_uploaded_source_entries(session)
        confluence_entries = _maybe_fetch_family_pages(session)
        sources = build_source_registry(uploaded_entries, confluence_entries, files_meta=session.get("files_meta"))
        candidate_facts = _build_candidate_facts(plan_json, sources)
        project_context: Dict[str, Any] = {
            "name": project_name,
            "customer": plan_json.get("customer"),
            "family": request.family or session.get("family"),
            "generated_at": datetime.now().isoformat(),
            "vector_store_id": vector_store_id,
        }
        context_pack = freeze_context_pack(sources, candidate_facts, project_context)

        # Re-render Markdown with context sources for visualization
        try:
            render_payload = dict(plan_json)
            render_payload["context_pack"] = context_pack.model_dump()
            plan_markdown = render_plan_md(render_payload)
        except Exception:
            pass

        # Store vector_store_id in session for cleanup
        session["vector_store_id"] = vector_store_id
        session["context_pack"] = context_pack.model_dump()
        session["plan_json"] = deepcopy(plan_json)
        session["plan_markdown"] = plan_markdown

        return DraftResponse(
            plan_json=plan_json,
            plan_markdown=plan_markdown,
            source_file_names=source_file_names,
            vector_store_id=vector_store_id,
            context_pack=context_pack,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {str(e)}")


@app.post("/agents/run", response_model=AgentsRunResponse)
async def run_specialist_agents(request: AgentsRunRequest):
    """
    Run specialist agents to build or refine a Strategic Build Plan.
    
    Can work in two modes:
    1. Build from scratch: Provide session_id after /ingest (no draft needed!)
    2. Refine existing: Provide plan_json to refine an existing draft
    """
    LOGGER.info("=== /agents/run called ===")
    LOGGER.info("Request: session_id=%s, has_vector_store=%s, has_context_pack=%s, has_plan_json=%s",
                request.session_id, bool(request.vector_store_id), bool(request.context_pack), bool(request.plan_json))
    
    session: Optional[dict] = None
    if request.session_id:
        session = sessions.get(request.session_id)
        # If session not found but we have direct parameters, just log a warning and continue
        if session is None and (not request.vector_store_id or not request.context_pack):
            LOGGER.warning("Session %s not found and required parameters missing", request.session_id)
            raise HTTPException(status_code=404, detail="Session not found and required parameters missing")

    vector_store_id = request.vector_store_id or (session.get("vector_store_id") if session else None)
    plan_json_input = request.plan_json or (deepcopy(session.get("plan_json")) if session else None)
    context_pack_input = request.context_pack or (session.get("context_pack") if session else None)

    if not vector_store_id or context_pack_input is None:
        raise HTTPException(status_code=400, detail="vector_store_id and context_pack are required (run /ingest first)")
    
    # If no plan_json provided, create an empty base structure for specialists to fill
    if plan_json_input is None:
        project_name = session.get("project_name", "Unknown Project") if session else "Unknown Project"
        customer = session.get("customer", "") if session else ""
        family = session.get("family", "") if session else ""
        
        plan_json_input = {
            "project": project_name,
            "customer": customer,
            "revision": "A",
            "summary": "",
            "requirements": [],
            "process_flow": "",
            "tooling_fixturing": "",
            "materials_finishes": "",
            "ctqs": [],
            "risks": [],
            "open_questions": [],
            "cost_levers": [],
            "pack_ship": "",
            "source_files_used": [],
        }

    try:
        context_pack_model = ContextPack.model_validate(context_pack_input)
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=400, detail=f"Invalid context pack payload: {exc}") from exc

    coordinator_result = coordinator_run_specialists(plan_json_input, context_pack_model, vector_store_id)

    plan_json = coordinator_result.get("plan_json", {})
    tasks_suggested = coordinator_result.get("tasks_suggested", [])
    qa_payload = coordinator_result.get("qa", {})
    conflicts = coordinator_result.get("conflicts", [])

    # Fallback: if plan remains too sparse after specialists, draft a baseline from vector store
    try:
        qp = plan_json.get("quality_plan") or {}
        ei = plan_json.get("engineering_instructions") or {}
        sparse = not any([
            plan_json.get("requirements"),
            qp.get("ctqs"),
            qp.get("inspection_levels"),
            plan_json.get("materials_finishes"),
            plan_json.get("process_flow"),
            ei.get("exceptional_steps"),
            ei.get("dfm_actions"),
            ei.get("quality_routing"),
        ])
    except Exception:
        sparse = False

    if sparse:
        LOGGER.info("/agents/run: Specialist outputs were sparse; invoking baseline draft fallback...")
        try:
            prev_plan = plan_json
            draft_customer = (session.get("customer") if session else None) or plan_json.get("customer")
            draft_family = (session.get("family") if session else None) or plan_json.get("project")
            draft_project = (session.get("project_name") if session else None) or plan_json.get("project") or "Untitled Project"
            fallback_plan = planner_agent.draft_plan(
                vector_store_id=vector_store_id,
                project_name=draft_project,
                customer=draft_customer,
                family=draft_family,
            )
            if isinstance(fallback_plan, dict) and fallback_plan:
                # Preserve synthesizer outputs from coordinator if present
                if isinstance(prev_plan, dict):
                    if prev_plan.get("keys"):
                        fallback_plan["keys"] = prev_plan.get("keys")
                    if prev_plan.get("open_questions_curated") and prev_plan.get("open_questions"):
                        fallback_plan["open_questions_curated"] = True
                        fallback_plan["open_questions"] = prev_plan.get("open_questions")
                plan_json = fallback_plan
                # Reset tasks/conflicts to empty; specialists can be re-run upstream in a later pass if needed
                tasks_suggested = tasks_suggested or []
                conflicts = conflicts or []
                qa_payload = qa_payload or {}
        except Exception as exc:
            LOGGER.warning("Baseline draft fallback failed: %s", exc)
    
    # Render markdown from the plan JSON (include context sources for visualization)
    render_payload = dict(plan_json)
    try:
        # Non-destructive: attach context sources for renderer if not already present
        if "context_pack" not in render_payload and context_pack_model is not None:
            render_payload["context_pack"] = context_pack_model.model_dump()
    except Exception:
        pass
    plan_markdown = render_plan_md(render_payload)

    snapshot_id: Optional[str] = None
    if session is not None and request.session_id:
        session["plan_json"] = deepcopy(plan_json)
        session["context_pack"] = context_pack_model.model_dump()
        try:
            rec = session_store.save_snapshot(
                request.session_id,
                plan_json=plan_json,
                context_pack=context_pack_model.model_dump(),
                vector_store_id=vector_store_id,
                note="agents/run",
            )
            snapshot_id = str(len(rec.get("snapshots", []))) if rec else None
        except Exception as e:
            LOGGER.warning("Failed to persist snapshot: %s", e)

    return AgentsRunResponse(
        plan_json=plan_json,
        plan_markdown=plan_markdown,
        tasks_suggested=tasks_suggested,
        tasks={"suggested": tasks_suggested, "created": [], "skipped": []},
        qa=qa_payload,
        conflicts=conflicts,
        context_pack=context_pack_model.model_dump(),
        session_id=request.session_id,
        vector_store_id=vector_store_id,
        snapshot_id=snapshot_id,
    )


# --------------------
# Session persistence endpoints
# --------------------

class SessionCreateRequest(BaseModel):
    project_name: Optional[str] = None
    session_id: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    project_name: Optional[str] = None


class SessionRecordModel(BaseModel):
    session_id: str
    project_name: Optional[str] = None
    created_ts: float
    updated_ts: float
    messages: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []


@app.post("/sessions", response_model=SessionCreateResponse)
async def create_session(req: SessionCreateRequest):
    try:
        rec = session_store.create(project_name=req.project_name, session_id=req.session_id)
        return SessionCreateResponse(session_id=rec["session_id"], project_name=rec.get("project_name"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")


@app.get("/sessions", response_model=list[SessionRecordModel])
async def list_sessions(limit: int = 20):
    try:
        items = session_store.list_recent(limit=limit)
        return [SessionRecordModel(**item) for item in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {e}")


@app.get("/sessions/{session_id}", response_model=SessionRecordModel)
async def get_session(session_id: str):
    rec = session_store.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionRecordModel(**rec)


class SessionMessageRequest(BaseModel):
    role: str
    text: str
    meta: Optional[dict[str, Any]] = None


@app.post("/sessions/{session_id}/messages", response_model=SessionRecordModel)
async def add_session_message(session_id: str, msg: SessionMessageRequest):
    rec = session_store.add_message(session_id, msg.role, msg.text, meta=msg.meta)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionRecordModel(**rec)


class SessionRenameRequest(BaseModel):
    project_name: str


@app.patch("/sessions/{session_id}", response_model=SessionRecordModel)
async def rename_session(session_id: str, payload: SessionRenameRequest):
    rec = session_store.rename(session_id, payload.project_name)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionRecordModel(**rec)


@app.post("/publish", response_model=PublishResponse)
async def publish_to_confluence(request: PublishRequest):
    """
    Publish Strategic Build Plan to Confluence.
    
    Resolves family page (parent) and creates child page with v2 API.
    """
    if not CONFIG["confluence_base"] or not CONFIG["confluence_email"] or not CONFIG["confluence_token"]:
        raise HTTPException(status_code=400, detail="Confluence not configured")

    try:
        family_selection = request.family
        parent_id = request.parent_page_id or CONFIG["confluence_parent"]
        target_space = CONFIG.get("confluence_space")

        if family_selection:
            parent_id = family_selection.page_id
            if family_selection.space_key:
                target_space = family_selection.space_key
        elif request.family_name and not parent_id:
            search_result = confluence_search_family(
                f'type=page AND title~"{request.family_name}"',
                limit=1,
            )
            if search_result:
                parent_id = search_result["page_id"]

        if not parent_id:
            raise HTTPException(status_code=400, detail="A Confluence parent page must be selected")

        if not target_space:
            raise HTTPException(status_code=400, detail="Confluence space key not configured")

        # Convert Markdown to basic HTML (simple approach)
        storage_html = "<p>" + "</p><p>".join(
            line for line in request.markdown.splitlines()
        ) + "</p>"

        title = f"Strategic Build Plan — {request.project}"

        page = confluence_create_child(parent_id, title, storage_html, space_key=target_space)

        return PublishResponse(
            page_id=page["page_id"],
            url=page["url"],
            title=page.get("title", title),
            space_key=target_space,
            parent_id=parent_id,
        )

    except ConfluenceConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        if status_code == 401:
            detail = "Confluence authentication failed (401). Check CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN."
        elif status_code == 403:
            detail = "Confluence returned 403 Forbidden. Ensure the API token has permission to edit the space/parent."
        elif status_code == 404:
            detail = "Confluence resource not found (404). Verify parent page ID and space key."
        else:
            detail = f"Confluence API error ({status_code})."
        raise HTTPException(status_code=status_code, detail=detail) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}") from e


@app.post("/meeting/prep", response_model=MeetingPrepResponse)
async def generate_meeting_prep(request: MeetingPrepRequest):
    """
    Generate pre-meeting materials: Project Brief + Meeting Agenda.

    This prepares the team for the APQP meeting by:
    1. Summarizing uploaded documents and Confluence lessons learned
    2. Creating structured agenda with discussion prompts per APQP dimension
    3. Identifying critical questions to address in the meeting
    """
    LOGGER.info("=== /meeting/prep called for session %s ===", request.session_id)

    # Get session
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Get session data
        project_name = session.get("project_name", "Unknown Project")
        customer = session.get("customer", "")
        family = session.get("family", "")
        vector_store_id = session.get("vector_store_id")

        if not vector_store_id:
            raise HTTPException(status_code=400, detail="No files uploaded - run /ingest first")

        # Generate meeting prep materials using agent
        prep_materials = planner_agent.generate_meeting_prep(
            vector_store_id=vector_store_id,
            project_name=project_name,
            customer=customer,
            family=family,
        )

        # Build response model
        agenda_topics = []
        for topic in prep_materials.get("agenda_topics", []):
            agenda_topics.append(MeetingAgendaTopic(
                name=topic.get("name", ""),
                discussion_prompts=topic.get("discussion_prompts", []),
                known_facts=topic.get("known_facts", []),
                open_questions=topic.get("open_questions", []),
                suggested_duration_minutes=topic.get("suggested_duration_minutes", 10),
            ))

        total_duration = sum(t.suggested_duration_minutes for t in agenda_topics)

        return MeetingPrepResponse(
            project_brief_markdown=prep_materials.get("project_brief", ""),
            meeting_agenda=MeetingAgenda(
                topics=agenda_topics,
                total_duration_minutes=total_duration
            ),
            lessons_learned_summary=prep_materials.get("lessons_learned", None),
            critical_questions=prep_materials.get("critical_questions", []),
        )

    except Exception as e:
        LOGGER.error(f"Meeting prep generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Meeting prep generation failed: {str(e)}")


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
        suggested_tasks_raw = _group_tasks_by_owner_hint(_generate_followup_tasks(updated_plan_json))
        suggested_tasks: List[AsanaTaskModel] = []
        allowed_keys = {"name", "notes", "due_on", "assignee", "priority", "source_hint", "plan_url", "section", "fingerprint"}
        for task in suggested_tasks_raw:
            enriched = {**task}
            fingerprint = _fingerprint(task)
            enriched["fingerprint"] = fingerprint
            filtered = {k: v for k, v in enriched.items() if k in allowed_keys and v is not None}
            suggested_tasks.append(AsanaTaskModel(**filtered))

        # Persist snapshot if session provided
        try:
            if request.session_id:
                session_store.save_snapshot(
                    request.session_id,
                    plan_json=updated_plan_json,
                    context_pack=sessions.get(request.session_id, {}).get("context_pack") or {},
                    vector_store_id=sessions.get(request.session_id, {}).get("vector_store_id"),
                    note="meeting/apply",
                )
        except Exception:
            pass

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

        threshold = 70.0
        return QAGradeResponse(
            score=score,
            reasons=reasons,
            fixes=fixes,
            blocked=score < threshold,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA grading failed: {str(e)}")



# ============================================================================
# Validation Endpoint
# ============================================================================

class ValidateRequest(BaseModel):
    """Request for session validation"""
    session_id: str


class ValidateResponse(BaseModel):
    """Response with validation results"""
    is_ready: bool
    completeness_score: int
    issues: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    checklist: List[Dict[str, Any]]


@app.post("/validate", response_model=ValidateResponse)
async def validate_session(request: ValidateRequest):
    """
    Validate a session for agent execution readiness.

    Returns validation results including:
    - is_ready: Whether session can run agents
    - completeness_score: 0-100% data quality score
    - issues: All validation issues (errors, warnings, suggestions)
    - checklist: User-friendly checklist for UI
    """
    from .lib.validation import validate_session_for_agents, get_validation_checklist

    LOGGER.info("=== /validate called for session %s ===", request.session_id)

    # Get session
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Run validation
    result = validate_session_for_agents(session)
    checklist = get_validation_checklist(session)

    LOGGER.info(
        "Validation result: ready=%s, score=%d%%, errors=%d, warnings=%d",
        result.is_ready,
        result.completeness_score,
        len(result.to_dict()["errors"]),
        len(result.to_dict()["warnings"])
    )

    return ValidateResponse(
        is_ready=result.is_ready,
        completeness_score=result.completeness_score,
        issues=result.to_dict()["issues"],
        errors=result.to_dict()["errors"],
        warnings=result.to_dict()["warnings"],
        suggestions=result.to_dict()["suggestions"],
        checklist=checklist,
    )

@app.get("/asana/projects", response_model=list[AsanaProjectSummary])
async def list_asana_projects(q: str = ""):
    try:
        return asana_list_projects(q)
    except AsanaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Asana project search failed") from e


@app.get("/asana/teams", response_model=list[AsanaTeamSummary])
async def list_asana_teams(q: str = ""):
    try:
        return asana_list_teams(q)
    except AsanaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Asana team lookup failed") from e


@app.post("/asana/projects", response_model=AsanaProjectCreateResponse)
async def create_asana_project_endpoint(request: AsanaProjectCreateRequest):
    try:
        created = asana_create_project(request.name, team_gid=request.team_gid, private=request.private)
        return created
    except AsanaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail="Asana project creation failed") from e


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

        tasks_payload = _group_tasks_by_owner_hint(tasks_payload)

        plan_fingerprints: Set[str] = set()
        for todo in (request.plan_json.get("asana_todos") or []):
            if isinstance(todo, dict):
                existing = todo.get("fingerprint")
                if isinstance(existing, str) and existing:
                    plan_fingerprints.add(existing[:12])
                    continue
                title = todo.get("name") or todo.get("title")
                source = todo.get("source_hint") or todo.get("source")
                section = todo.get("section")
                if any((title, source, section)):
                    plan_fingerprints.add(asana_fingerprint(title, source, section))

        result = create_asana_tasks(
            request.project_id,
            tasks_payload,
            default_plan_url=request.plan_url,
            known_fingerprints=plan_fingerprints,
        )
        return AsanaTasksResponse(created=result["created"], skipped=result["skipped"])

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
