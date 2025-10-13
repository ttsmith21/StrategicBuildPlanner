"""Coordinator for specialist agents in the Strategic Build Planner."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
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
from .keys import run_keys
from .openq import run_open_questions
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


async def _run_specialists_parallel(
    plan: Dict[str, Any],
    context_pack: ContextPack,
    vector_store_id: Optional[str],
) -> tuple[List[AgentPatch], List[Dict[str, Any]]]:
    """Run specialist agents in parallel using ThreadPoolExecutor.

    Returns: (patches, all_conflicts)
    """
    LOGGER.info("coordinator: Running specialist agents in parallel...")

    loop = asyncio.get_event_loop()

    # Create tasks for parallel execution
    with ThreadPoolExecutor(max_workers=4) as executor:
        qma_future = loop.run_in_executor(executor, run_qma, plan, context_pack, vector_store_id)
        pma_future = loop.run_in_executor(executor, run_pma, plan, context_pack, vector_store_id)
        sca_future = loop.run_in_executor(executor, run_sca, plan, context_pack, vector_store_id)
        ema_future = loop.run_in_executor(executor, run_ema, plan, context_pack, vector_store_id)

        # Wait for all to complete
        patches = await asyncio.gather(qma_future, pma_future, sca_future, ema_future, return_exceptions=True)

    # Collect results, handling any exceptions
    successful_patches = []
    all_conflicts = []

    agent_names = ["QMA", "PMA", "SCA", "EMA"]
    for i, result in enumerate(patches):
        if isinstance(result, Exception):
            LOGGER.error(f"coordinator: {agent_names[i]} failed: {result}")
            # Create empty patch to continue
            successful_patches.append(AgentPatch(patch={}, tasks=[], conflicts=[]))
        elif isinstance(result, AgentPatch):
            successful_patches.append(result)
            all_conflicts.extend([conflict.model_dump() for conflict in result.conflicts])
        else:
            LOGGER.warning(f"coordinator: {agent_names[i]} returned unexpected type: {type(result)}")
            successful_patches.append(AgentPatch(patch={}, tasks=[], conflicts=[]))

    return successful_patches, all_conflicts


def run_specialists(
    plan_json: Optional[Dict[str, Any]],
    context_pack_payload: Any,
    vector_store_id: Optional[str],
) -> Dict[str, Any]:
    """Run specialist agents sequentially and return merged output."""
    LOGGER.info("coordinator_run_specialists: Starting agent workflow...")

    context_pack = _coerce_context_pack(context_pack_payload)
    plan = _normalize_plan(plan_json)

    # Compute a source signature and detect newly added/changed sources.
    # Source schema fields: id (required), rev (optional), title (required)
    def _sources_signature(cp: ContextPack) -> list[str]:
        sigs: list[str] = []
        try:
            for s in (cp.sources or []):
                try:
                    sid = getattr(s, "id", None) if not isinstance(s, dict) else s.get("id")
                    rev = getattr(s, "rev", None) if not isinstance(s, dict) else s.get("rev")
                    title = getattr(s, "title", None) if not isinstance(s, dict) else s.get("title")
                except Exception:
                    sid, rev, title = None, None, None
                # Prefer stable id, fall back to title
                key = (sid or title or "source")
                sigs.append(f"{key}@{rev or ''}")
        except Exception:
            pass
        return sigs

    def _detect_changed_sources(prev: list[str] | None, curr: list[str] | None) -> list[str]:
        prev_set = set(prev or [])
        return [sig for sig in (curr or []) if sig not in prev_set]

    current_sigs = _sources_signature(context_pack)
    previous_sigs: list[str] = plan.get("source_files_used") or []
    changed_sigs = _detect_changed_sources(previous_sigs, current_sigs)
    
    if changed_sigs:
        LOGGER.info("coordinator: changed/new sources detected: %s", changed_sigs)
    # Attach a lightweight hint into project payload so downstream agents can optionally react
    try:
        project_meta = context_pack.project or {}
        hints = project_meta.get("hints") or {}
        hints["sources_signature"] = current_sigs
        if changed_sigs:
            hints["changed_sources"] = changed_sigs
        project_meta["hints"] = hints
        context_pack.project = project_meta
    except Exception as exc:
        LOGGER.debug("coordinator: failed to attach source hints to context project: %s", exc)

    tasks: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    # Run specialists in parallel for 3x speedup
    try:
        patches, all_conflicts = asyncio.run(_run_specialists_parallel(plan, context_pack, vector_store_id))
        qma_patch, pma_patch, sca_patch, ema_patch = patches
        conflicts.extend(all_conflicts)
    except Exception as exc:
        LOGGER.error(f"coordinator: Parallel execution failed: {exc}. Falling back to sequential.")
        # Fallback to sequential execution
        LOGGER.info("coordinator: Running QMA...")
        qma_patch = run_qma(plan, context_pack, vector_store_id)
        conflicts.extend([conflict.model_dump() for conflict in qma_patch.conflicts])

        LOGGER.info("coordinator: Running PMA...")
        pma_patch = run_pma(plan, context_pack, vector_store_id)
        conflicts.extend([conflict.model_dump() for conflict in pma_patch.conflicts])

        LOGGER.info("coordinator: Running SCA...")
        sca_patch = run_sca(plan, context_pack, vector_store_id)
        conflicts.extend([conflict.model_dump() for conflict in sca_patch.conflicts])

        LOGGER.info("coordinator: Running EMA...")
        ema_patch = run_ema(plan, context_pack, vector_store_id)
        conflicts.extend([conflict.model_dump() for conflict in ema_patch.conflicts])

    # Apply patches with ownership enforcement
    _apply_patch(plan, qma_patch, _AGENT_OWNERSHIP["qma"])
    tasks = _merge_tasks(tasks, qma_patch.tasks)

    _apply_patch(plan, pma_patch, _AGENT_OWNERSHIP["pma"])
    tasks = _merge_tasks(tasks, pma_patch.tasks)

    _apply_patch(plan, sca_patch, _AGENT_OWNERSHIP["sca"])
    tasks = _merge_tasks(tasks, sca_patch.tasks)

    _apply_patch(plan, ema_patch, _AGENT_OWNERSHIP["ema"])
    tasks = _merge_tasks(tasks, ema_patch.tasks)

    # Synthesizers: Open Questions (only if empty) then Keys (1–5)
    try:
        oq_patch = run_open_questions(plan)
        if isinstance(oq_patch, AgentPatch):
            plan.update(oq_patch.patch)
    except Exception as exc:  # pragma: no cover - resilience
        LOGGER.warning("Open questions synthesizer failed: %s", exc)

    try:
        keys_patch = run_keys(plan, context_pack, vector_store_id)
        if isinstance(keys_patch, AgentPatch):
            plan.update(keys_patch.patch)
    except Exception as exc:  # pragma: no cover - resilience
        LOGGER.warning("Keys synthesizer failed: %s", exc)

    qa_result = run_sbpqa(plan, context_pack, vector_store_id)

    # Persist the full source signature used for this run so future runs can diff
    try:
        plan["source_files_used"] = current_sigs
    except Exception:
        pass

    return {
        "plan_json": plan,
        "tasks_suggested": tasks,
        "qa": qa_result,
        "conflicts": conflicts,
    }
