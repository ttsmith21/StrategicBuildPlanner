"""Strategic Build Planner Agent using the OpenAI Agents SDK."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Dict, List, Optional

from openai import OpenAI  # type: ignore

from server.lib.schema import APQP_CHECKLIST, PLAN_SCHEMA
from server.lib.rendering import render_plan_md

PROMPT_HEADER = dedent(
    """
    You are the Strategic Build Planner Agent for Northern Manufacturing Co., Inc.
    Draft and maintain Strategic Build Plans for stainless sheet-metal fabrication projects.

    Core expectations:
    - Follow the official Strategic Build Plan template and JSON schema.
    - Maximize recall: leverage every uploaded document via file_search.
    - Every requirement/action includes source_hint (filename) and confidence (0-1).
    - When information is missing or ambiguous, write the string "UNKNOWN".
    - Convert gaps/unknowns/deltas into actionable Asana-ready TODOs with owners when possible.
    - Highlight manufacturing risks and mitigations; note open questions precisely.
    - All dates in ISO format (YYYY-MM-DD).
    """
).strip()


EVAL_SCHEMA = {
    "name": "PlanEvaluation",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 100},
            "reasons": {
                "type": "array",
                "items": {"type": "string"},
            },
            "fixes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["score", "reasons", "fixes"],
    },
    "strict": True,
}


@dataclass
class StrategicBuildPlannerAgent:
    """Agent wrapper around the OpenAI Agents SDK."""

    client: OpenAI
    model: str = os.getenv("OPENAI_MODEL_PLAN", "gpt-4.1-mini")

    def _run_structured_task(
        self,
        *,
        instructions: str,
        prompt: str,
        schema: Dict[str, Any],
        vector_store_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        beta = getattr(self.client, "beta", None)
        if beta is None or not hasattr(beta, "assistants"):
            raise RuntimeError("OpenAI client does not support Assistants yet. Update the openai package.")

        assistants = beta.assistants
        threads = getattr(beta, "threads", None)
        if threads is None or not hasattr(threads, "create"):
            raise RuntimeError("OpenAI client does not expose beta.threads API; update the openai package.")

        tools: Optional[List[Dict[str, Any]]] = None
        tool_resources: Optional[Dict[str, Any]] = None
        if vector_store_id:
            tools = [{"type": "file_search"}]
            tool_resources = {"file_search": {"vector_store_ids": [vector_store_id]}}

        assistant = assistants.create(
            name="Strategic Build Planner Agent",
            instructions=instructions,
            model=self.model,
            tools=tools,
            tool_resources=tool_resources,
        )

        try:
            thread = threads.create()
            message_api = getattr(threads, "messages", None)
            run_api = getattr(threads, "runs", None)
            if message_api is None or run_api is None:
                raise RuntimeError("OpenAI client does not expose beta.threads APIs; update the openai package.")

            message_api.create(
                thread_id=thread.id,
                role="user",
                content=prompt,
            )

            run = run_api.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id,
                response_format={
                    "type": "json_schema",
                    "json_schema": schema,
                },
                timeout=300,
            )

            if getattr(run, "status", None) != "completed":
                raise RuntimeError(f"OpenAI run failed with status: {getattr(run, 'status', 'unknown')}")

            messages = message_api.list(thread_id=thread.id, order="desc", limit=5)
            for message in messages.data:
                for content in getattr(message, "content", []):
                    text_block = getattr(content, "text", None)
                    value = getattr(text_block, "value", None) if text_block else None
                    if value:
                        return json.loads(value)

            raise ValueError("OpenAI response did not contain JSON text content")
        finally:
            try:
                assistants.delete(assistant.id)
            except Exception:
                pass

    def draft_plan(
        self,
        vector_store_id: str,
        project_name: str,
        customer: Optional[str] = None,
        family: Optional[str] = None,
    ) -> Dict[str, Any]:
        checklist = "\n".join(f"- {item}" for item in APQP_CHECKLIST)
        user_prompt = dedent(
            f"""
            Project: {project_name}
            Customer: {customer or 'UNKNOWN'}
            Family of Parts: {family or 'UNKNOWN'}

            Tasks:
            1. Use file_search to read every uploaded document.
            2. Produce StrategicBuildPlan JSON strictly following the provided schema.
            3. Populate source_files_used with the exact filenames leveraged.
            4. Ensure every requirement includes source_hint and confidence.
            5. Unknown data must be the string "UNKNOWN".
            6. Summarize gaps as Asana-ready TODOs in cost_levers or open_questions.

            APQP checklist for completeness:
            {checklist}
            """
        ).strip()

        return self._run_structured_task(
            instructions=PROMPT_HEADER,
            prompt=user_prompt,
            schema=PLAN_SCHEMA,
            vector_store_id=vector_store_id,
        )

    def apply_meeting_notes(
        self,
        plan_json: Dict[str, Any],
        transcript_texts: List[str],
    ) -> Dict[str, Any]:
        meeting_prompt = dedent(
            f"""
            Update the following Strategic Build Plan with new meeting notes.
            Preserve all existing content unless the meeting explicitly changes it.
            Mark updated confidence at 0.95 when the meeting confirms details.

            Current plan JSON:
            {json.dumps(plan_json, indent=2)}

            Meeting notes:
            {'\n\n'.join(transcript_texts)}
            """
        ).strip()

        return self._run_structured_task(
            instructions=PROMPT_HEADER,
            prompt=meeting_prompt,
            schema=PLAN_SCHEMA,
        )

    def evaluate_plan(
        self,
        plan_json: Dict[str, Any],
        rubric: Dict[str, Any],
        gold_examples: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = dedent(
            f"""
            You are the quality gate for Strategic Build Plans.
            Evaluate the plan against this rubric and anonymized gold exemplars.

            Rubric:
            {json.dumps(rubric, indent=2)}

            Gold Exemplars:
            {json.dumps(gold_examples, indent=2)}

            For the provided plan, return JSON with:
            - score: single number 0-100 (higher is better)
            - reasons: bullet-style strings citing rubric alignment
            - fixes: at least 3 specific improvements with owners or next steps

            Be decisive. Penalize UNKNOWN fields or missing risk mitigations.

            Plan JSON:
            {json.dumps(plan_json, indent=2)}
            """
        ).strip()

        return self._run_structured_task(
            instructions=PROMPT_HEADER,
            prompt=prompt,
            schema=EVAL_SCHEMA,
        )


def run_draft(
    client: OpenAI,
    vector_store_id: str,
    project_name: str,
    customer: Optional[str] = None,
    family: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience helper to draft a plan via the Strategic Build Planner Agent."""
    agent = StrategicBuildPlannerAgent(client)
    plan_json = agent.draft_plan(
        vector_store_id=vector_store_id,
        project_name=project_name,
        customer=customer,
        family=family,
    )
    return plan_json


__all__ = [
    "StrategicBuildPlannerAgent",
    "run_draft",
    "render_plan_md",
]
