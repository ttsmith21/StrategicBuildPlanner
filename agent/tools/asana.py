"""Asana tool adapters for Strategic Build Planner agent."""

from __future__ import annotations

from typing import Dict, List, Optional

from server.lib.asana import AsanaConfigError, create_tasks


def asana_create_tasks(
    project_id: str,
    tasks: List[Dict[str, Optional[str]]],
    plan_url: Optional[str] = None,
) -> Dict[str, List[Dict[str, Optional[str]]]]:
    """Create tasks in Asana using the shared library helper."""

    result = create_tasks(project_id, tasks, default_plan_url=plan_url)
    return result


__all__ = ["asana_create_tasks", "AsanaConfigError"]
