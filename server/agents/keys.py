"""Keys Synthesizer Agent

Generates 1–5 concise, numbered "Keys to the Project" based on the current
plan snapshot and the available context pack. Runs after specialists and before
QA so the rubric can see the keys.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from ..lib.schema import AgentPatch, ContextPack
from .base_threads import run_json_schema_thread

LOGGER = logging.getLogger(__name__)

_SCHEMA: Dict[str, Any] = {
    "name": "KeysSynthesizer",
    "schema": {
        "type": "object",
        "required": ["keys"],
        "additionalProperties": False,
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 5,
            }
        },
    },
}


SYSTEM_PROMPT = (
    "You are the Keys Synthesizer for a Strategic Build Plan. "
    "Read the provided plan snapshot and context pack and produce the top 1–5 terse, actionable bullets "
    "that summarize what truly matters for manufacturing readiness. Focus on concrete requirements, risks, and gating items. "
    "Avoid generic statements. Each bullet should be one sentence, under 160 characters, and must cite nothing; just the distilled takeaway."
)


def _get_model() -> str:
    return os.getenv("OPENAI_MODEL_KEYS", os.getenv("OPENAI_MODEL_PLAN", "gpt-5"))


def run_keys(plan_json: Dict[str, Any], context_pack: ContextPack, vector_store_id: str | None) -> AgentPatch:
    """Run the keys synthesizer and return an AgentPatch updating summary/keys."""

    if not vector_store_id:
        # No vector store; synthesize from plan only using a simple heuristic.
        keys = _fallback_from_plan(plan_json)
        return AgentPatch(patch={"summary": _enumerated(keys), "keys": keys})

    user_payload: Dict[str, Any] = {
        "plan_snapshot": plan_json,
        "context_pack": context_pack.model_dump(),
        "instructions": "Return only the JSON with an array named 'keys' (1–5 strings).",
    }

    try:
        data = run_json_schema_thread(
            model=_get_model(),
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_payload,
            json_schema=_SCHEMA,
            vector_store_id=vector_store_id,
            temperature=0.1,
            timeout_s=120.0,
        )
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.warning("Keys agent failed: %s", exc)
        keys = _fallback_from_plan(plan_json)
        return AgentPatch(patch={"summary": _enumerated(keys), "keys": keys})

    keys: List[str] = []
    if isinstance(data, dict) and isinstance(data.get("keys"), list):
        keys = [str(x).strip() for x in data["keys"] if isinstance(x, (str, int, float))]
        keys = [k for k in keys if k]
    if not keys:
        keys = _fallback_from_plan(plan_json)

    keys = _sanitize_keys(keys)
    return AgentPatch(patch={"summary": _enumerated(keys), "keys": keys})


def _enumerated(items: List[str]) -> str:
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items[:5]))


def _fallback_from_plan(plan: Dict[str, Any]) -> List[str]:
    # Heuristic extraction of a few keys if the agent cannot run
    keys: List[str] = []
    qp = plan.get("quality_plan") or {}
    ei = plan.get("engineering_instructions") or {}
    reqs = plan.get("requirements") or []

    # Requirement-driven key
    for r in reqs:
        topic = str(r.get("topic") or "").strip()
        requirement = str(r.get("requirement") or "").strip()
        if topic and requirement:
            keys.append(f"{topic}: {requirement}")
            break

    # Quality-related key
    ctqs = qp.get("ctqs") or []
    if ctqs:
        keys.append(f"CTQs: {', '.join(ctqs[:3])}{'…' if len(ctqs) > 3 else ''}")

    # Engineering exception or quality op placement
    exc = (ei.get("exceptional_steps") or [])
    if exc:
        wc = str(exc[0].get("workcenter") or "non‑standard step")
        keys.append(f"Non‑standard step at {wc}; validate method and QC")
    qops = (ei.get("quality_routing") or [])
    if qops and len(keys) < 5:
        first = qops[0]
        op = str(first.get("quality_operation") or "quality hold")
        wc = str(first.get("workcenter") or "")
        tail = f" at {wc}" if wc else ""
        keys.append(f"Place {op}{tail} and record objective evidence")

    # Purchasing long-leads
    purch = plan.get("purchasing") or {}
    ll = purch.get("long_leads") or []
    if ll and len(keys) < 5:
        item = str(ll[0].get("item") or "long‑lead item")
        keys.append(f"Long‑lead: {item}; place RFQ/PO to protect schedule")

    if not keys:
        keys = ["Review drawings/specs and confirm CTQs, hold points, and supply constraints"]
    return keys[:5]


def _sanitize_keys(keys: List[str]) -> List[str]:
    """Normalize, dedupe, and clamp keys to short, punchy bullets.

    Rules:
    - Remove leading bullets/numbering ("- ", "1.", "1)" etc.)
    - Collapse whitespace
    - Trim to <= 160 chars, appending ellipsis if truncated
    - Drop empty duplicates, keep original order
    """
    seen = set()
    out: List[str] = []
    for raw in keys[:5]:
        s = str(raw).strip()
        # strip leading bullets/numbering
        for prefix in ("- ", "• ", "* ", "— ", "– "):
            if s.startswith(prefix):
                s = s[len(prefix):].lstrip()
        # numeric prefixes
        if len(s) > 2 and s[0].isdigit() and (s[1:3] in (". ", ") ")):
            s = s[3:].lstrip()
        elif len(s) > 1 and s[0].isdigit() and s[1] in (".", ")"):
            s = s[2:].lstrip()
        # collapse whitespace
        s = " ".join(s.split())
        # clamp length
        if len(s) > 160:
            s = s[:157].rstrip() + "…"
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= 5:
            break
    return out
