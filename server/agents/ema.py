"""Engineering Manager Agent wrapper."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI

from ..lib.context_pack import ContextPack
from .prompts import EMA_SYSTEM

LOGGER = logging.getLogger(__name__)

_ENGINEERING_INSTRUCTIONS_SCHEMA: Dict[str, Any] = {
    "name": "EngineeringInstructions",
    "schema": {
        "type": "object",
        "required": ["engineering_instructions"],
        "additionalProperties": False,
        "properties": {
            "engineering_instructions": {
                "type": "object",
                "required": [
                    "routing",
                    "fixtures",
                    "programs",
                    "ctqs_for_routing",
                    "open_items",
                ],
                "additionalProperties": False,
                "properties": {
                    "routing": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "op_no",
                                "workcenter",
                                "input",
                                "program",
                                "notes",
                                "qc",
                                "sources",
                            ],
                            "additionalProperties": False,
                            "properties": {
                                "op_no": {"type": "integer"},
                                "workcenter": {"type": "string"},
                                "input": {"type": "string"},
                                "program": {"type": "string"},
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
                                            "page_ref": {
                                                "type": ["string", "null"],
                                            },
                                            "passage_sha": {
                                                "type": ["string", "null"],
                                            },
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
                            "required": ["name", "purpose", "citations"],
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "purpose": {"type": "string"},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["source_id"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {
                                                "type": ["string", "null"],
                                            },
                                            "passage_sha": {
                                                "type": ["string", "null"],
                                            },
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
                            "required": ["machine", "program_id", "notes", "citations"],
                            "additionalProperties": False,
                            "properties": {
                                "machine": {"type": "string"},
                                "program_id": {"type": "string"},
                                "notes": {"type": "string"},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["source_id"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {
                                                "type": ["string", "null"],
                                            },
                                            "passage_sha": {
                                                "type": ["string", "null"],
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "ctqs_for_routing": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["ctq", "measurement_plan", "citations"],
                            "additionalProperties": False,
                            "properties": {
                                "ctq": {"type": "string"},
                                "measurement_plan": {"type": "string"},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["source_id"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {
                                                "type": ["string", "null"],
                                            },
                                            "passage_sha": {
                                                "type": ["string", "null"],
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "open_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["issue", "owner", "due", "citations"],
                            "additionalProperties": False,
                            "properties": {
                                "issue": {"type": "string"},
                                "owner": {"type": "string"},
                                "due": {"type": ["string", "null"]},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["source_id"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {
                                                "type": ["string", "null"],
                                            },
                                            "passage_sha": {
                                                "type": ["string", "null"],
                                            },
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
}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=api_key)


def _empty_instructions() -> Dict[str, Any]:
    return {
        "engineering_instructions": {
            "routing": [],
            "fixtures": [],
            "programs": [],
            "ctqs_for_routing": [],
            "open_items": [],
        }
    }


def _summarize_context(context_pack: ContextPack, plan_json: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "project": plan_json.get("project"),
        "customer": plan_json.get("customer"),
        "ctqs": plan_json.get("ctqs", []),
        "canonical_facts": [],
        "reference_facts": [],
        "deltas": [],
    }

    for fact in context_pack.facts:
        entry = {
            "topic": fact.topic,
            "claim": fact.claim,
            "status": fact.status,
            "authority": fact.authority,
            "precedence_rank": fact.precedence_rank,
            "citation": {
                "source_id": fact.citation.source_id,
                "page_ref": fact.citation.page_ref,
                "passage_sha": fact.citation.passage_sha,
            },
        }
        if fact.status == "canonical":
            summary["canonical_facts"].append(entry)
        elif fact.status == "proposed":
            summary["reference_facts"].append(entry)
        else:
            summary.setdefault("suppressed_facts", []).append(entry)

        topic_lower = fact.topic.lower()
        if any(keyword in topic_lower for keyword in ("passivation", "inspection", "ctq", "long lead", "long-lead")):
            summary["deltas"].append(entry)

    return summary


def _response_to_instructions(response: Any) -> Dict[str, Any]:
    if response is None:
        return {}

    if isinstance(response, dict):
        engineering = response.get("engineering_instructions")
        if isinstance(engineering, dict):
            return {"engineering_instructions": engineering}

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
                        engineering = data.get("engineering_instructions")
                        if isinstance(engineering, dict):
                            return {"engineering_instructions": engineering}
                if item_type == "text":
                    text_value = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                    if isinstance(text_value, str):
                        try:
                            parsed = json.loads(text_value)
                        except json.JSONDecodeError:
                            continue
                        engineering = parsed.get("engineering_instructions") if isinstance(parsed, dict) else None
                        if isinstance(engineering, dict):
                            return {"engineering_instructions": engineering}

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError:
            LOGGER.debug("EMA output_text not JSON: %s", output_text)
        else:
            engineering = parsed.get("engineering_instructions") if isinstance(parsed, dict) else None
            if isinstance(engineering, dict):
                return {"engineering_instructions": engineering}

    dump_method = getattr(response, "model_dump", None)
    dumped = dump_method() if callable(dump_method) else None
    if isinstance(dumped, dict):
        return _response_to_instructions(dumped)

    return {}


def run_ema(plan_json: Dict[str, Any], context_pack: ContextPack, vector_store_id: str | None) -> Dict[str, Any]:
    if not vector_store_id:
        LOGGER.info("run_ema invoked without vector store; returning empty instructions.")
        return _empty_instructions()

    client = _get_client()
    model = os.getenv("OPENAI_MODEL_EMA", os.getenv("OPENAI_MODEL_PLAN", "o4-mini"))

    context_summary = _summarize_context(context_pack, plan_json)
    context_json = json.dumps(context_summary, ensure_ascii=False, indent=2)
    plan_json_str = json.dumps(plan_json, ensure_ascii=False, indent=2)

    user_payload = (
        "Context Summary:\n"
        + context_json
        + "\n\nCurrent Plan JSON:\n"
        + plan_json_str
        + "\n\nProduce engineering instructions only."
    )

    request_payload: Dict[str, Any] = {
        "model": model,
        "temperature": 0.2,
        "input": [
            {"role": "system", "content": EMA_SYSTEM},
            {"role": "user", "content": user_payload},
        ],
        "tools": [{"type": "file_search"}],
        "tool_resources": {"file_search": {"vector_store_ids": [vector_store_id]}},
        "response_format": {"type": "json_schema", "json_schema": _ENGINEERING_INSTRUCTIONS_SCHEMA},
    }

    response = client.responses.create(**request_payload)

    instructions = _response_to_instructions(response)
    if not instructions:
        LOGGER.warning("EMA returned no structured instructions; defaulting to empty structure.")
        return _empty_instructions()

    engineering = instructions.get("engineering_instructions")
    if not isinstance(engineering, dict):
        return _empty_instructions()

    # Ensure all required arrays exist even if omitted by the model
    for key in ["routing", "fixtures", "programs", "ctqs_for_routing", "open_items"]:
        engineering.setdefault(key, [])
    return {"engineering_instructions": engineering}
