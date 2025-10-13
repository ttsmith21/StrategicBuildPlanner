"""Asana helpers shared across server endpoints and agent tools."""

from __future__ import annotations

import os
import hashlib
from typing import Dict, List, Optional, Set, Tuple

import requests


class AsanaConfigError(RuntimeError):
    """Raised when Asana configuration is incomplete."""


def _load_asana_config() -> Dict[str, str]:
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token:
        raise AsanaConfigError("ASANA_ACCESS_TOKEN must be set in the environment.")

    return {
        "token": token,
        "base_url": os.getenv("ASANA_BASE_URL", "https://app.asana.com/api/1.0"),
    }


def _get_workspace_gid() -> str:
    workspace = os.getenv("ASANA_WORKSPACE_GID")
    if not workspace:
        raise AsanaConfigError("ASANA_WORKSPACE_GID must be set in the environment.")
    return workspace


def fingerprint(title: Optional[str], source: Optional[str] = None, section: Optional[str] = None) -> str:
    """Derive a stable fingerprint for an Asana task suggestion."""

    parts = [
        (title or "").strip(),
        (source or "").strip(),
        (section or "").strip(),
    ]
    basis = "|".join(parts)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def _fingerprint(task: Dict[str, Optional[str]]) -> str:
    name = task.get("name") or task.get("title")
    source = task.get("source_hint") or task.get("source")
    section = task.get("section")
    existing = task.get("fingerprint")
    if isinstance(existing, str) and existing:
        return existing[:12]
    return fingerprint(name, source, section)


def _build_task_payload(task: Dict[str, Optional[str]], project_id: str, default_plan_url: Optional[str]) -> Tuple[Dict[str, object], str]:
    name = task.get("name") or "Strategic Build Planner TODO"
    notes_fragments: List[str] = []

    if task.get("notes"):
        notes_fragments.append(str(task["notes"]))

    if task.get("source_hint"):
        notes_fragments.append(f"Source: {task['source_hint']}")

    plan_url = task.get("plan_url") or default_plan_url
    if plan_url:
        notes_fragments.append(f"Plan: {plan_url}")

    priority = task.get("priority") or "TBD"
    notes_fragments.append(f"Priority: {priority}")

    notes = "\n".join(notes_fragments).strip()

    data_payload: Dict[str, object] = {
        "name": name,
        "notes": notes,
        "projects": [project_id],
    }

    payload: Dict[str, object] = {"data": data_payload}

    due_on = task.get("due_on")
    if due_on:
        data_payload["due_on"] = due_on

    assignee = task.get("assignee")
    if assignee:
        data_payload["assignee"] = assignee

    return payload, _fingerprint(task)


def create_tasks(
    project_id: str,
    tasks: List[Dict[str, Optional[str]]],
    default_plan_url: Optional[str] = None,
    known_fingerprints: Optional[Set[str]] = None,
) -> Dict[str, List[Dict[str, Optional[str]]]]:
    """Create tasks in Asana under the given project.

    Args:
        project_id: The Asana project identifier (gid).
        tasks: A list of dicts containing minimal task information.
        default_plan_url: Optional plan URL appended to task notes if not specified per task.

    Returns:
        A list of created task summaries ({gid, name, permalink_url}).
    """
    cfg = _load_asana_config()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {cfg['token']}",
        "Content-Type": "application/json",
    })

    created: List[Dict[str, Optional[str]]] = []
    skipped: List[Dict[str, Optional[str]]] = []
    fingerprints = set(known_fingerprints or set())

    for task in tasks:
        payload, task_fingerprint = _build_task_payload(task, project_id, default_plan_url)
        if task_fingerprint in fingerprints:
            skipped.append({**task, "fingerprint": task_fingerprint})
            continue
        response = session.post(f"{cfg['base_url']}/tasks", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json().get("data", {})
        created.append({
            "gid": data.get("gid"),
            "name": data.get("name"),
            "permalink_url": data.get("permalink_url"),
            "fingerprint": task_fingerprint,
        })
        fingerprints.add(task_fingerprint)

    return {"created": created, "skipped": skipped}


def list_projects(query: str = "", limit: int = 20) -> List[Dict[str, object]]:
    """List projects in the configured workspace filtered by an optional query."""
    cfg = _load_asana_config()
    workspace = _get_workspace_gid()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {cfg['token']}",
    })

    params = {
        "workspace": workspace,
        "limit": 50,
        "opt_fields": "name,permalink_url,team.gid,team.name,archived",
    }
    response = session.get(f"{cfg['base_url']}/projects", params=params, timeout=30)
    response.raise_for_status()
    data = response.json().get("data", [])

    results: List[Dict[str, object]] = []
    lowered_query = query.lower() if query else ""
    for project in data:
        name = project.get("name", "")
        if project.get("archived"):
            continue
        if lowered_query and lowered_query not in name.lower():
            continue
        results.append({
            "gid": project.get("gid"),
            "name": name,
            "url": project.get("permalink_url"),
            "team": project.get("team"),
            "archived": project.get("archived"),
        })
        if len(results) >= limit:
            break

    return results


def list_teams(query: str = "") -> List[Dict[str, Optional[str]]]:
    """List teams for the configured organization/workspace."""
    cfg = _load_asana_config()
    organization = os.getenv("ASANA_ORGANIZATION_GID") or _get_workspace_gid()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {cfg['token']}",
    })

    params = {
        "organization": organization,
        "limit": 100,
        "opt_fields": "name",
    }
    response = session.get(f"{cfg['base_url']}/teams", params=params, timeout=30)
    response.raise_for_status()
    data = response.json().get("data", [])

    lowered_query = query.lower() if query else ""
    results: List[Dict[str, Optional[str]]] = []
    for team in data:
        name = team.get("name", "")
        if lowered_query and lowered_query not in name.lower():
            continue
        results.append({
            "gid": team.get("gid"),
            "name": name,
        })

    return results


def create_project(name: str, *, team_gid: Optional[str] = None, private: bool = True) -> Dict[str, object]:
    """Create a new project in Asana."""
    cfg = _load_asana_config()
    workspace = _get_workspace_gid()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {cfg['token']}",
        "Content-Type": "application/json",
    })

    payload: Dict[str, object] = {
        "name": name,
        "workspace": workspace,
    }
    if team_gid:
        payload["team"] = team_gid
    if private is not None:
        payload["public"] = not private

    response = session.post(f"{cfg['base_url']}/projects", json=payload, timeout=30)
    response.raise_for_status()
    data = response.json().get("data", {})
    return {
        "gid": data.get("gid"),
        "name": data.get("name"),
        "url": data.get("permalink_url"),
        "team": data.get("team"),
    }


def list_workspaces() -> List[Dict[str, Optional[str]]]:
    """List workspaces/organizations visible to the current token.

    Returns a list of { gid, name, is_organization }.
    """
    cfg = _load_asana_config()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {cfg['token']}",
    })

    response = session.get(f"{cfg['base_url']}/workspaces", timeout=30)
    response.raise_for_status()
    data = response.json().get("data", [])

    results: List[Dict[str, Optional[str]]] = []
    for ws in data:
        results.append({
            "gid": ws.get("gid"),
            "name": ws.get("name"),
            "is_organization": ws.get("is_organization"),
        })
    return results


def detect_default_workspace_gid() -> Optional[str]:
    """Return ASANA_WORKSPACE_GID from env, or the first available workspace gid from Asana API."""
    try:
        env_ws = os.getenv("ASANA_WORKSPACE_GID")
        if env_ws:
            return env_ws
        workspaces = list_workspaces()
        return workspaces[0]["gid"] if workspaces else None
    except Exception:
        return None


__all__ = [
    "AsanaConfigError",
    "create_tasks",
    "list_projects",
    "list_teams",
    "create_project",
    "list_workspaces",
    "detect_default_workspace_gid",
    "_fingerprint",
    "fingerprint",
]
