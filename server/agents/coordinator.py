"""Coordinator for specialist agents in the Strategic Build Planner."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from ..lib.asana import fingerprint as task_fingerprint
from ..lib.schema import (
    AgentPatch,
    AgentTask,
    ContextPack,
    EngineeringInstructions,
    ExecutionStrategy,
    PurchasingPlan,
    QualityPlan,
    SchedulePlan,
)
from .ema import run_ema
from .pma import run_pma
from .qma import run_qma
from .sbpqa import run_sbpqa
from .sca import run_sca

LOGGER = logging.getLogger(__name__)

_AGENT_OWNERSHIP: Dict[str, set[str]] = {
    "qma": {"quality_plan"},
    "pma": {"purchasing"},
    "sca": {"release_plan", "execution_strategy"},
    "ema": {"engineering_instructions"},
}


def _normalize_plan(plan_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base: Dict[str, Any] = deepcopy(plan_json) if isinstance(plan_json, dict) else {}
    base.setdefault("project", base.get("project") or "")
    base.setdefault("customer", base.get("customer") or "")
    base.setdefault("revision", base.get("revision") or "")
    base.setdefault("summary", base.get("summary") or "")
    base.setdefault("requirements", base.get("requirements") or [])
    base.setdefault("process_flow", base.get("process_flow") or "")
    base.setdefault("tooling_fixturing", base.get("tooling_fixturing") or "")
    base.setdefault("materials_finishes", base.get("materials_finishes") or "")
    base.setdefault("ctqs", base.get("ctqs") or [])
    base.setdefault("risks", base.get("risks") or [])
    base.setdefault("open_questions", base.get("open_questions") or [])
    base.setdefault("cost_levers", base.get("cost_levers") or [])
    base.setdefault("pack_ship", base.get("pack_ship") or "")
    base.setdefault("source_files_used", base.get("source_files_used") or [])

    if not isinstance(base.get("quality_plan"), dict):
        base["quality_plan"] = QualityPlan().model_dump()
    if not isinstance(base.get("purchasing"), dict):
        base["purchasing"] = PurchasingPlan().model_dump()
    if not isinstance(base.get("release_plan"), dict):
        base["release_plan"] = SchedulePlan().model_dump()
    if not isinstance(base.get("execution_strategy"), dict):
        base["execution_strategy"] = ExecutionStrategy().model_dump()
    if not isinstance(base.get("engineering_instructions"), dict):
        base["engineering_instructions"] = EngineeringInstructions().model_dump()

    return base


def _coerce_context_pack(payload: Any) -> ContextPack:
    if isinstance(payload, ContextPack):
        return payload
    if isinstance(payload, dict):
        try:
            return ContextPack.model_validate(payload)
        except ValidationError as exc:
            LOGGER.warning("Failed to validate context pack payload; using empty stub. Error: %s", exc)
    return ContextPack(project={}, sources=[], facts=[])


def _apply_patch(plan: Dict[str, Any], patch: AgentPatch, allowed_keys: set[str]) -> None:
    if not isinstance(patch, AgentPatch):
        return
    for section, value in patch.patch.items():
        if section not in allowed_keys:
            LOGGER.debug("Skipping unauthorized section '%s' in patch", section)
            continue
        plan[section] = value


def _task_to_dict(task: AgentTask) -> Dict[str, Any]:
    payload = {
        "name": task.name,
        "notes": task.notes,
        "owner_hint": task.owner_hint,
        "due_on": task.due_date,
        "source_hint": task.source_hint,
    }
    payload["fingerprint"] = task_fingerprint(payload["name"], payload.get("source_hint"), payload.get("owner_hint"))
    return payload


def _merge_tasks(existing: List[Dict[str, Any]], new_tasks: List[AgentTask]) -> List[Dict[str, Any]]:
    seen = {task.get("fingerprint") for task in existing if task.get("fingerprint")}
    merged = list(existing)
    for task in new_tasks:
        payload = _task_to_dict(task)
        fp = payload.get("fingerprint")
        if fp and fp in seen:
            continue
        if fp:
            seen.add(fp)
        merged.append(payload)
    return merged


def run_specialists(
    plan_json: Optional[Dict[str, Any]],
    context_pack_payload: Any,
    vector_store_id: Optional[str],
) -> Dict[str, Any]:
    """Run specialist agents sequentially and return merged output."""
    LOGGER.info("coordinator_run_specialists: Starting agent workflow...")

    context_pack = _coerce_context_pack(context_pack_payload)
    plan = _normalize_plan(plan_json)

    tasks: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    LOGGER.info("coordinator: Running QMA...")
    qma_patch = run_qma(plan, context_pack, vector_store_id)
    _apply_patch(plan, qma_patch, _AGENT_OWNERSHIP["qma"])
    tasks = _merge_tasks(tasks, qma_patch.tasks)
    conflicts.extend([conflict.model_dump() for conflict in qma_patch.conflicts])

    LOGGER.info("coordinator: Running PMA...")
    pma_patch = run_pma(plan, context_pack, vector_store_id)
    _apply_patch(plan, pma_patch, _AGENT_OWNERSHIP["pma"])
    tasks = _merge_tasks(tasks, pma_patch.tasks)
    conflicts.extend([conflict.model_dump() for conflict in pma_patch.conflicts])

    sca_patch = run_sca(plan, context_pack, vector_store_id)
    _apply_patch(plan, sca_patch, _AGENT_OWNERSHIP["sca"])
    tasks = _merge_tasks(tasks, sca_patch.tasks)
    conflicts.extend([conflict.model_dump() for conflict in sca_patch.conflicts])

    ema_patch = run_ema(plan, context_pack, vector_store_id)
    _apply_patch(plan, ema_patch, _AGENT_OWNERSHIP["ema"])
    tasks = _merge_tasks(tasks, ema_patch.tasks)
    conflicts.extend([conflict.model_dump() for conflict in ema_patch.conflicts])

    qa_result = run_sbpqa(plan, context_pack, vector_store_id)

    return {
        "plan_json": plan,
        "tasks_suggested": tasks,
        "qa": qa_result,
        "conflicts": conflicts,
    }
