"""File-backed session store for plans, snapshots, and chat history."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Required


class SessionMessage(TypedDict, total=False):
    ts: float
    role: str  # "user" | "assistant" | "system"
    text: str
    meta: Dict[str, Any]


class SessionSnapshot(TypedDict, total=False):
    ts: float
    plan_json: Dict[str, Any]
    context_pack: Dict[str, Any]
    vector_store_id: Optional[str]
    note: Optional[str]


class SessionRecord(TypedDict, total=False):
    session_id: Required[str]
    project_name: Optional[str]
    created_ts: Required[float]
    updated_ts: Required[float]
    messages: Required[List[SessionMessage]]
    snapshots: Required[List[SessionSnapshot]]


class SessionStore:
    def __init__(self, root_dir: Path) -> None:
        self.root = root_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, sid: str) -> Path:
        return self.root / f"{sid}.json"

    def create(self, project_name: Optional[str] = None, *, session_id: Optional[str] = None) -> SessionRecord:
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        rec: SessionRecord = {
            "session_id": sid,
            "project_name": project_name,
            "created_ts": now,
            "updated_ts": now,
            "messages": [],
            "snapshots": [],
        }
        self._path(sid).write_text(json.dumps(rec, indent=2), encoding="utf-8")
        return rec

    def get(self, sid: str) -> Optional[SessionRecord]:
        p = self._path(sid)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save(self, rec: SessionRecord, *, session_id: Optional[str] = None) -> None:
        rec["updated_ts"] = time.time()
        sid = session_id or rec.get("session_id") or "unknown"
        self._path(str(sid)).write_text(json.dumps(rec, indent=2), encoding="utf-8")

    def rename(self, sid: str, project_name: str) -> Optional[SessionRecord]:
        rec = self.get(sid)
        if not rec:
            return None
        rec["project_name"] = project_name
        self._save(rec, session_id=sid)
        return rec

    def add_message(self, sid: str, role: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Optional[SessionRecord]:
        rec = self.get(sid)
        if not rec:
            return None
        msgs = rec.get("messages") or []
        msgs.append({"ts": time.time(), "role": role, "text": text, "meta": meta or {}})
        rec["messages"] = msgs
        self._save(rec, session_id=sid)
        return rec

    def list_messages(self, sid: str, limit: int = 200) -> List[SessionMessage]:
        rec = self.get(sid)
        if not rec:
            return []
        msgs = rec.get("messages") or []
        return msgs[-limit:]

    def save_snapshot(
        self,
        sid: str,
        *,
        plan_json: Dict[str, Any],
        context_pack: Dict[str, Any],
        vector_store_id: Optional[str],
        note: Optional[str] = None,
    ) -> Optional[SessionRecord]:
        rec = self.get(sid)
        if not rec:
            return None
        snaps = rec.get("snapshots") or []
        snaps.append(
            {
                "ts": time.time(),
                "plan_json": plan_json,
                "context_pack": context_pack,
                "vector_store_id": vector_store_id,
                "note": note,
            }
        )
        rec["snapshots"] = snaps
        self._save(rec, session_id=sid)
        return rec

    def list_recent(self, limit: int = 20) -> List[SessionRecord]:
        items: List[SessionRecord] = []
        for f in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                items.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
            if len(items) >= limit:
                break
        return items
