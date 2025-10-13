"""Engineering Manager Agent wrapper for specialist workflow."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI

from ..lib.context_pack import ContextPack
from ..lib.schema import AgentConflict, AgentPatch, AgentTask, EngineeringInstructions
from .base_threads import run_json_schema_thread
from .prompts import EMA_SYSTEM

LOGGER = logging.getLogger(__name__)

_ENGINEERING_PATCH_SCHEMA: Dict[str, Any] = {
    "name": "EngineeringManagerPatch",
    "schema": {
        "type": "object",
        "required": ["patch", "tasks", "conflicts"],
        "additionalProperties": False,
        "properties": {
            "patch": {
                "type": "object",
                "required": ["engineering_instructions"],
                "additionalProperties": False,
                "properties": {
                    "engineering_instructions": {
                        "type": "object",
                        "required": [
                            "exceptional_steps",
                            "dfm_actions",
                            "quality_routing",
                        ],
                        "additionalProperties": True,
                        "properties": {
                            "routing": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["op_no", "workcenter"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "op_no": {"type": "integer"},
                                        "workcenter": {"type": "string"},
                                        "input": {"type": ["string", "null"]},
                                        "program": {"type": ["string", "null"]},
                                        "notes": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "qc": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "sources": {
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
                            "fixtures": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["id"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "id": {"type": "string"},
                                        "type": {"type": ["string", "null"]},
                                        "status": {"type": ["string", "null"]},
                                        "owner": {"type": ["string", "null"]},
                                        "due": {"type": ["string", "null"]},
                                        "sources": {
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
                            "programs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["machine", "file"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "machine": {"type": "string"},
                                        "file": {"type": "string"},
                                        "rev": {"type": ["string", "null"]},
                                        "notes": {"type": ["string", "null"]},
                                        "sources": {
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
                            "ctqs_for_routing": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "open_items": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "exceptional_steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["op_no", "workcenter"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "op_no": {"type": "integer"},
                                        "workcenter": {"type": "string"},
                                        "input": {"type": ["string", "null"]},
                                        "program": {"type": ["string", "null"]},
                                        "notes": {"type": "array", "items": {"type": "string"}},
                                        "qc": {"type": "array", "items": {"type": "string"}},
                                        "sources": {
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
                            "dfm_actions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["action"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "action": {"type": "string"},
                                        "target": {"type": ["string", "null"]},
                                        "rationale": {"type": ["string", "null"]},
                                        "sources": {
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
                            "quality_routing": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["op_no", "workcenter", "quality_operation"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "op_no": {"type": "integer"},
                                        "workcenter": {"type": "string"},
                                        "quality_operation": {"type": "string"},
                                        "notes": {"type": "array", "items": {"type": "string"}},
                                        "sources": {
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
    return AgentPatch(
        patch={"engineering_instructions": EngineeringInstructions().model_dump()},
        tasks=[],
        conflicts=[],
    )


def _summarize_context(plan_json: Dict[str, Any], context_pack: ContextPack) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "project": plan_json.get("project"),
        "customer": plan_json.get("customer"),
        "revision": plan_json.get("revision"),
        "quality_plan": plan_json.get("quality_plan"),
        "purchasing": plan_json.get("purchasing"),
        "release_plan": plan_json.get("release_plan"),
        "execution_strategy": plan_json.get("execution_strategy"),
        "canonical_facts": [],
        "reference_facts": [],
    }

    for fact in context_pack.facts:
        entry = {
            "topic": fact.topic,
            "claim": fact.claim,
            "status": fact.status,
            "authority": fact.authority,
            "precedence_rank": fact.precedence_rank,
            "citation": fact.citation.model_dump(),
        }
        if fact.status == "canonical":
            summary["canonical_facts"].append(entry)
        else:
            summary["reference_facts"].append(entry)

    return summary


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
                            LOGGER.debug("EMA text block was not JSON: %s", text_value)

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            LOGGER.debug("EMA output_text not JSON: %s", output_text)

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
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        if not name:
            continue
        payload = {
            "name": str(name),
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
        return EngineeringInstructions().model_dump()

    engineering = payload.get("engineering_instructions")
    if not isinstance(engineering, dict):
        return EngineeringInstructions().model_dump()

    normalized = EngineeringInstructions(**{
        "routing": engineering.get("routing", []),
        "fixtures": engineering.get("fixtures", []),
        "programs": engineering.get("programs", []),
        "ctqs_for_routing": engineering.get("ctqs_for_routing", []),
        "open_items": engineering.get("open_items", []),
        "exceptional_steps": engineering.get("exceptional_steps", []),
        "dfm_actions": engineering.get("dfm_actions", []),
        "quality_routing": engineering.get("quality_routing", []),
    }).model_dump()
    return normalized


def run_ema(
    plan_json: Dict[str, Any],
    context_pack: ContextPack,
    vector_store_id: str | None,
) -> AgentPatch:
    """Execute the Engineering Manager Agent and return its patch."""

    if not vector_store_id:
        LOGGER.info("run_ema invoked without vector store; returning blank patch.")
        return _blank_patch()

    model = os.getenv("OPENAI_MODEL_EMA", os.getenv("OPENAI_MODEL_PLAN", "gpt-5"))
    context_summary = _summarize_context(plan_json, context_pack)
    user_payload = {
        "plan_snapshot": plan_json,
        "context_summary": context_summary,
        "instructions": "Return only the engineering patch JSON. Do not modify other plan sections.",
    }

    try:
        data = run_json_schema_thread(
            model=model,
            system_prompt=EMA_SYSTEM,
            user_prompt=user_payload,
            json_schema=_ENGINEERING_PATCH_SCHEMA,
            vector_store_id=vector_store_id,
            temperature=0.15,
        )
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("EMA threads call failed: %s", exc)
        return _blank_patch()
    if not isinstance(data, dict):
        LOGGER.warning("EMA returned non-dict payload; defaulting to blank patch.")
        return _blank_patch()

    patch_dict = _normalize_patch(data.get("patch"))
    tasks = _coerce_tasks(data.get("tasks"))
    conflicts = _coerce_conflicts(data.get("conflicts"))

    return AgentPatch(patch={"engineering_instructions": patch_dict}, tasks=tasks, conflicts=conflicts)
