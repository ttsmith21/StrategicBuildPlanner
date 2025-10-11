"""Purchasing Manager Agent wrapper for specialist workflow."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI

from ..lib.context_pack import ContextPack
from ..lib.schema import AgentConflict, AgentPatch, AgentTask, PurchasingPlan
from .prompts import PMA_SYSTEM

LOGGER = logging.getLogger(__name__)

_PURCHASING_PATCH_SCHEMA: Dict[str, Any] = {
    "name": "PurchasingManagerPatch",
    "schema": {
        "type": "object",
        "required": ["patch", "tasks", "conflicts"],
        "additionalProperties": False,
        "properties": {
            "patch": {
                "type": "object",
                "required": ["purchasing"],
                "additionalProperties": False,
                "properties": {
                    "purchasing": {
                        "type": "object",
                        "required": ["long_leads", "coo_mtr", "alternates", "rfqs"],
                        "additionalProperties": False,
                        "properties": {
                            "long_leads": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["item"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "item": {"type": "string"},
                                        "lead_time": {"type": ["string", "null"]},
                                        "vendor_hint": {"type": ["string", "null"]},
                                        "citations": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "required": ["source_id"],
                                                "additionalProperties": False,
                                                "properties": {
                                                    "source_id": {"type": "string"},
                                                    "page_ref": {"type": ["string", "null"]},
                                                    "passage_sha": {"type": ["string", "null"]},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                            "coo_mtr": {"type": ["string", "null"]},
                            "alternates": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["item", "alternate"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "item": {"type": "string"},
                                        "alternate": {"type": "string"},
                                        "rationale": {"type": ["string", "null"]},
                                        "citations": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "required": ["source_id"],
                                                "additionalProperties": False,
                                                "properties": {
                                                    "source_id": {"type": "string"},
                                                    "page_ref": {"type": ["string", "null"]},
                                                    "passage_sha": {"type": ["string", "null"]},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                            "rfqs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["item"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "item": {"type": "string"},
                                        "vendor": {"type": ["string", "null"]},
                                        "due": {"type": ["string", "null"]},
                                        "citations": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "required": ["source_id"],
                                                "additionalProperties": False,
                                                "properties": {
                                                    "source_id": {"type": "string"},
                                                    "page_ref": {"type": ["string", "null"]},
                                                    "passage_sha": {"type": ["string", "null"]},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    }
                },
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "notes": {"type": ["string", "null"]},
                        "owner_hint": {"type": ["string", "null"]},
                        "due_date": {"type": ["string", "null"]},
                        "source_hint": {"type": ["string", "null"]},
                    },
                },
            },
            "conflicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["topic", "issue"],
                    "additionalProperties": False,
                    "properties": {
                        "topic": {"type": "string"},
                        "issue": {"type": "string"},
                        "citations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["source_id"],
                                "additionalProperties": False,
                                "properties": {
                                    "source_id": {"type": "string"},
                                    "page_ref": {"type": ["string", "null"]},
                                    "passage_sha": {"type": ["string", "null"]},
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=api_key)


def _blank_patch() -> AgentPatch:
    return AgentPatch(patch={"purchasing": PurchasingPlan().model_dump()}, tasks=[], conflicts=[])


def _summarize_context(plan_json: Dict[str, Any], context_pack: ContextPack) -> Dict[str, Any]:
    return {
        "project": plan_json.get("project"),
        "customer": plan_json.get("customer"),
        "revision": plan_json.get("revision"),
        "quality_plan": plan_json.get("quality_plan"),
        "existing_purchasing": plan_json.get("purchasing"),
        "release_plan": plan_json.get("release_plan"),
        "execution_strategy": plan_json.get("execution_strategy"),
        "facts": [fact.model_dump() for fact in context_pack.facts],
    }


def _extract_json(response: Any) -> Dict[str, Any]:
    if response is None:
        return {}
    if isinstance(response, dict):
        return response
    output_blocks = getattr(response, "output", None)
    if output_blocks:
        for block in output_blocks:
            content = getattr(block, "content", None) or (block.get("content") if isinstance(block, dict) else None)
            if not content:
                continue
            for item in content:
                item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
                if item_type == "output_json":
                    data = getattr(item, "json", None)
                    if data is None and isinstance(item, dict):
                        data = item.get("json")
                    if isinstance(data, dict):
                        return data
                if item_type == "text":
                    text_value = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                    if isinstance(text_value, str):
                        try:
                            return json.loads(text_value)
                        except json.JSONDecodeError:
                            LOGGER.debug("PMA text block not JSON: %s", text_value)
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            LOGGER.debug("PMA output_text not JSON: %s", output_text)
    dump_method = getattr(response, "model_dump", None)
    if callable(dump_method):
        dumped = dump_method()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _coerce_tasks(items: Any) -> List[AgentTask]:
    tasks: List[AgentTask] = []
    if not isinstance(items, list):
        return tasks
    for raw in items:
        if not isinstance(raw, dict) or not raw.get("name"):
            continue
        payload = {
            "name": str(raw.get("name")),
            "notes": raw.get("notes"),
            "owner_hint": raw.get("owner_hint"),
            "due_date": raw.get("due_date"),
            "source_hint": raw.get("source_hint"),
        }
        try:
            tasks.append(AgentTask(**payload))
        except TypeError as exc:
            LOGGER.debug("Skipping malformed task payload %s: %s", raw, exc)
    return tasks


def _coerce_conflicts(items: Any) -> List[AgentConflict]:
    conflicts: List[AgentConflict] = []
    if not isinstance(items, list):
        return conflicts
    for raw in items:
        if not isinstance(raw, dict):
            continue
        topic = raw.get("topic")
        issue = raw.get("issue")
        if not topic or not issue:
            continue
        payload = {
            "topic": str(topic),
            "issue": str(issue),
            "citations": raw.get("citations", []),
        }
        try:
            conflicts.append(AgentConflict(**payload))
        except TypeError as exc:
            LOGGER.debug("Skipping malformed conflict payload %s: %s", raw, exc)
    return conflicts


def _normalize_patch(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return PurchasingPlan().model_dump()
    plan = payload.get("purchasing")
    if not isinstance(plan, dict):
        return PurchasingPlan().model_dump()
    normalized = PurchasingPlan(**{
        "long_leads": plan.get("long_leads", []),
        "coo_mtr": plan.get("coo_mtr"),
        "alternates": plan.get("alternates", []),
        "rfqs": plan.get("rfqs", []),
    }).model_dump()
    return normalized


def run_pma(
    plan_json: Dict[str, Any],
    context_pack: ContextPack,
    vector_store_id: str | None,
) -> AgentPatch:
    """Execute the Purchasing Manager Agent and return its patch."""

    if not vector_store_id:
        LOGGER.info("run_pma invoked without vector store; returning blank patch.")
        return _blank_patch()

    try:
        client = _get_client()
    except RuntimeError as exc:
        LOGGER.warning("PMA cannot initialize OpenAI client: %s", exc)
        return _blank_patch()

    model = os.getenv("OPENAI_MODEL_PMA", os.getenv("OPENAI_MODEL_PLAN", "gpt-4.1-mini"))
    payload = {
        "plan_snapshot": plan_json,
        "context_pack": _summarize_context(plan_json, context_pack),
        "instructions": "Return only the purchasing patch JSON",
    }

    request_payload: Dict[str, Any] = {
        "model": model,
        "temperature": 0.1,
        "input": [
            {"role": "system", "content": PMA_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            },
        ],
        "tools": [{"type": "file_search"}],
        "tool_resources": {"file_search": {"vector_store_ids": [vector_store_id]}},
        "response_format": {"type": "json_schema", "json_schema": _PURCHASING_PATCH_SCHEMA},
    }

    try:
        response = client.responses.create(**request_payload)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("PMA call failed: %s", exc)
        return _blank_patch()

    data = _extract_json(response)
    if not isinstance(data, dict):
        LOGGER.warning("PMA returned non-dict payload; defaulting to blank patch.")
        return _blank_patch()

    patch_dict = _normalize_patch(data.get("patch"))
    tasks = _coerce_tasks(data.get("tasks"))
    conflicts = _coerce_conflicts(data.get("conflicts"))

    return AgentPatch(patch={"purchasing": patch_dict}, tasks=tasks, conflicts=conflicts)
