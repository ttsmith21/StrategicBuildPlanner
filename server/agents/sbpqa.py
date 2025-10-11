"""Strategic Build Plan QA Agent wrapper."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from openai import OpenAI

from ..lib.context_pack import ContextPack
from .prompts import SBPQA_SYSTEM

LOGGER = logging.getLogger(__name__)

_QA_SCHEMA: Dict[str, Any] = {
    "name": "StrategicBuildPlanQA",
    "schema": {
        "type": "object",
        "required": ["score", "reasons", "fixes", "blocked"],
        "additionalProperties": False,
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 100},
            "reasons": {"type": "array", "items": {"type": "string"}},
            "fixes": {"type": "array", "items": {"type": "string"}},
            "blocked": {"type": "boolean"},
        },
    },
}

_DEFAULT_RESULT: Dict[str, Any] = {
    "score": 0.0,
    "reasons": ["QA agent did not execute"],
    "fixes": ["Re-run specialist agents"],
    "blocked": True,
}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=api_key)


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
                            LOGGER.debug("SBP-QA text block not JSON: %s", text_value)
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            LOGGER.debug("SBP-QA output_text not JSON: %s", output_text)
    dump_method = getattr(response, "model_dump", None)
    if callable(dump_method):
        dumped = dump_method()
        if isinstance(dumped, dict):
            return dumped
    return {}


def run_sbpqa(
    plan_json: Dict[str, Any],
    context_pack: ContextPack,
    vector_store_id: str | None,
) -> Dict[str, Any]:
    """Execute the Strategic Build Plan QA agent and return the gating result."""

    if not vector_store_id:
        LOGGER.info("run_sbpqa invoked without vector store; returning default blocked result.")
        return dict(_DEFAULT_RESULT)

    try:
        client = _get_client()
    except RuntimeError as exc:
        LOGGER.warning("SBP-QA cannot initialize OpenAI client: %s", exc)
        return dict(_DEFAULT_RESULT)

    model = os.getenv("OPENAI_MODEL_SBPQA", os.getenv("OPENAI_MODEL_PLAN", "gpt-4.1-mini"))
    payload = {
        "plan_snapshot": plan_json,
        "context_pack": context_pack.model_dump(),
        "instructions": "Return the QA verdict JSON only.",
    }

    request_payload: Dict[str, Any] = {
        "model": model,
        "temperature": 0.0,
        "input": [
            {"role": "system", "content": SBPQA_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            },
        ],
        "tools": [{"type": "file_search"}],
        "tool_resources": {"file_search": {"vector_store_ids": [vector_store_id]}},
        "response_format": {"type": "json_schema", "json_schema": _QA_SCHEMA},
    }

    try:
        response = client.responses.create(**request_payload)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("SBP-QA call failed: %s", exc)
        return dict(_DEFAULT_RESULT)

    data = _extract_json(response)
    if not isinstance(data, dict):
        LOGGER.warning("SBP-QA returned non-dict payload; defaulting to blocked result.")
        return dict(_DEFAULT_RESULT)

    score = data.get("score")
    reasons = data.get("reasons")
    fixes = data.get("fixes")
    blocked = data.get("blocked")

    if not isinstance(score, (int, float)):
        return dict(_DEFAULT_RESULT)
    if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
        return dict(_DEFAULT_RESULT)
    if not isinstance(fixes, list) or not all(isinstance(item, str) for item in fixes):
        return dict(_DEFAULT_RESULT)
    if not isinstance(blocked, bool):
        return dict(_DEFAULT_RESULT)

    return {
        "score": float(score),
        "reasons": reasons,
        "fixes": fixes,
        "blocked": blocked,
    }
