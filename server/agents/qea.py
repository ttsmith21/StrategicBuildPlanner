"""Quality Extractor Agent client wrapper."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, List

from openai import OpenAI

from ..lib.context_pack import ContextPack
from .prompts import QEA_SYSTEM

LOGGER = logging.getLogger(__name__)

_SPEC_REQUIREMENT_SCHEMA: dict[str, Any] = {
    "name": "SpecRequirementList",
    "schema": {
        "type": "object",
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "topic",
                        "requirement",
                        "authority",
                        "precedence_rank",
                        "confidence",
                        "citation",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "topic": {"type": "string"},
                        "requirement": {"type": "string"},
                        "authority": {
                            "type": "string",
                            "enum": ["mandatory", "conditional", "reference", "internal"],
                        },
                        "precedence_rank": {"type": "integer"},
                        "applies_if": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "nullable": True,
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "citation": {
                            "type": "object",
                            "required": ["source_id", "page_ref", "passage_sha"],
                            "properties": {
                                "source_id": {"type": "string"},
                                "page_ref": {"type": ["string", "null"]},
                                "passage_sha": {"type": ["string", "null"]},
                            },
                            "additionalProperties": False,
                        },
                    },
                },
            }
        },
        "required": ["requirements"],
        "additionalProperties": False,
    },
}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=api_key)


def _response_to_requirements(response: Any) -> List[dict[str, Any]]:
    if response is None:
        return []

    # Direct JSON payload (as dict)
    if isinstance(response, dict):
        container = response.get("output_json") or response.get("json") or response.get("requirements")
        if isinstance(container, list):
            return container
        if isinstance(container, dict) and "requirements" in container:
            reqs = container["requirements"]
            return reqs if isinstance(reqs, list) else []

    # Responses API python client structures
    output_blocks = getattr(response, "output", None)
    if output_blocks:
        for block in output_blocks:
            content = getattr(block, "content", None)
            if not content and isinstance(block, dict):
                content = block.get("content")
            if not content:
                continue
            for item in content:
                item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
                if item_type == "output_json":
                    data = getattr(item, "json", None)
                    if data is None and isinstance(item, dict):
                        data = item.get("json")
                    if isinstance(data, dict):
                        reqs = data.get("requirements")
                        if isinstance(reqs, list):
                            return reqs
                    if isinstance(data, list):
                        return data
                if item_type == "text":
                    text_value = getattr(item, "text", None)
                    if text_value is None and isinstance(item, dict):
                        text_value = item.get("text")
                    if isinstance(text_value, str):
                        try:
                            parsed = json.loads(text_value)
                        except json.JSONDecodeError:
                            continue
                        reqs = parsed.get("requirements") if isinstance(parsed, dict) else parsed
                        if isinstance(reqs, list):
                            return reqs

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError:
            LOGGER.debug("Failed to parse output_text as JSON: %s", output_text)
        else:
            reqs = parsed.get("requirements") if isinstance(parsed, dict) else parsed
            if isinstance(reqs, list):
                return reqs

    dump_method = getattr(response, "model_dump", None)
    dumped = dump_method() if callable(dump_method) else None
    if isinstance(dumped, dict):
        return _response_to_requirements(dumped)

    return []


def run_qea(vector_store_id: str | None, context_pack: ContextPack) -> List[dict[str, Any]]:
    """Execute the Quality Extractor Agent and return structured requirements."""
    if not vector_store_id:
        LOGGER.info("run_qea called without a vector store id; returning empty result.")
        return []

    client = _get_client()
    model = os.getenv("OPENAI_MODEL_QEA", os.getenv("OPENAI_MODEL_PLAN", "o4-mini"))

    context_payload = context_pack.model_dump()
    context_json = json.dumps(context_payload, ensure_ascii=False, indent=2)

    user_instructions = (
        "Use the context pack to align requirement topics with the existing question bank. "
        "Return deterministic order (sorted by topic, then precedence_rank)."
    )

    request_payload: dict[str, Any] = {
        "model": model,
        "temperature": 0.1,
        "input": [
            {"role": "system", "content": QEA_SYSTEM},
            {
                "role": "user",
                "content": "Context Pack (JSON):\n"
                + context_json
                + "\n\n"
                + user_instructions,
            },
        ],
        "tools": [{"type": "file_search"}],
        "tool_resources": {"file_search": {"vector_store_ids": [vector_store_id]}},
        "response_format": {"type": "json_schema", "json_schema": _SPEC_REQUIREMENT_SCHEMA},
    }

    response = client.responses.create(**request_payload)

    requirements = _response_to_requirements(response)
    if not isinstance(requirements, list):
        LOGGER.warning("QEA returned unexpected payload; defaulting to empty list.")
        return []

    # Ensure deterministic ordering as instructed
    requirements_sorted = sorted(
        requirements,
        key=lambda item: (
            str(item.get("topic", "")),
            int(item.get("precedence_rank", 0)),
            str(item.get("requirement", "")),
        ),
    )
    return requirements_sorted
