"""Shared beta.threads runner for specialist agents.

Provides a simple function to run a JSON-schema-constrained thread with
file_search tool access to a given vector store.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, Optional

from openai import OpenAI
from ..lib.retry import create_openai_retry_decorator

LOGGER = logging.getLogger(__name__)

# Create retry decorator for OpenAI calls (3 attempts, 2s initial delay)
retry_openai = create_openai_retry_decorator(max_attempts=3, initial_delay=2.0)


def _get_client() -> OpenAI:
    return OpenAI()


@retry_openai
def _create_assistant_with_retry(client: OpenAI, **kwargs) -> Any:
    """Create assistant with retry logic"""
    return client.beta.assistants.create(**kwargs)


@retry_openai
def _create_and_poll_with_retry(client: OpenAI, **kwargs) -> Any:
    """Create and poll run with retry logic"""
    return client.beta.threads.runs.create_and_poll(**kwargs)


def run_json_schema_thread(
    model: str,
    system_prompt: str,
    user_prompt: str | Dict[str, Any],
    json_schema: Dict[str, Any],
    *,
    vector_store_id: Optional[str] = None,
    temperature: float = 0.1,
    poll_interval_s: float = 0.5,
    timeout_s: float = 300.0,
) -> Dict[str, Any]:
    """Execute a beta.threads run with file_search and a JSON schema.

    Returns parsed dict output. Raises RuntimeError on failure or timeout.
    """
    client = _get_client()

    # Create an assistant so file_search and vector_store bind reliably
    tools = [{"type": "file_search"}]
    tool_resources = {"file_search": {"vector_store_ids": [vector_store_id]}} if vector_store_id else None

    LOGGER.info("Creating assistant with retry logic...")
    assistant = _create_assistant_with_retry(
        client,
        name="SBP Specialist Runner",
        instructions=system_prompt,
        model=model,
        tools=tools,
        tool_resources=tool_resources,
    )

    thread = client.beta.threads.create()

    content: str
    if isinstance(user_prompt, str):
        content = user_prompt
    else:
        content = json.dumps(user_prompt, ensure_ascii=False)

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=content,
    )

    # Start the run using the assistant, enforce JSON schema
    # Note: tool_resources are inherited from assistant, don't pass again
    LOGGER.info("Starting run with retry logic...")
    run = _create_and_poll_with_retry(
        client,
        thread_id=thread.id,
        assistant_id=assistant.id,
        response_format={"type": "json_schema", "json_schema": json_schema},
        temperature=temperature,
        timeout=timeout_s,
    )

    status = getattr(run, "status", None)

    if status != "completed":
        # Fallback to Responses API with file_search
        try:
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
                temperature=temperature,
                response_format={"type": "json_schema", "json_schema": json_schema},
            )
            # Try extracting JSON
            if getattr(resp, "output", None):
                for block in resp.output:
                    for item in getattr(block, "content", []) or []:
                        if getattr(item, "type", None) == "output_json":
                            data = getattr(item, "json", None) or getattr(item, "output", None)
                            if isinstance(data, dict):
                                return data
                        if getattr(item, "type", None) == "text":
                            t = getattr(item, "text", None)
                            if t and getattr(t, "value", None):
                                try:
                                    return json.loads(t.value)
                                except Exception:
                                    pass
            if getattr(resp, "output_text", None):
                try:
                    return json.loads(resp.output_text)
                except Exception:
                    pass
        except Exception:
            pass
        # If fallback failed, raise error
        try:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            last_error = getattr(r, "last_error", None)
            msg = last_error.get("message") if isinstance(last_error, dict) else None
        except Exception:
            msg = None
        raise RuntimeError(f"Agent run failed: {status}{' - ' + msg if msg else ''}")

    # Get most recent assistant message content
    msgs = client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=5)
    for m in msgs.data:
        # Iterate parts to find structured output
        for part in getattr(m, "content", []) or []:
            ptype = getattr(part, "type", None)
            if ptype == "output_json":
                payload = getattr(part, "output", None) or getattr(part, "json", None)
                if isinstance(payload, dict):
                    return payload
            if ptype == "output_text":
                text_val = getattr(part, "text", None)
                if text_val and getattr(text_val, "value", None):
                    try:
                        return json.loads(text_val.value)
                    except Exception:
                        pass
    # Fallback: try parse the entire message as JSON text
    for m in msgs.data:
        for part in getattr(m, "content", []) or []:
            text_val = getattr(part, "text", None)
            if text_val and getattr(text_val, "value", None):
                try:
                    return json.loads(text_val.value)
                except Exception:
                    continue

    # Clean up assistant before raising
    try:
        client.beta.assistants.delete(assistant.id)
    except Exception:
        pass
    raise RuntimeError("No JSON output found from agent thread")
