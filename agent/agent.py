"""Strategic Build Planner Agent using the OpenAI Agents SDK."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Dict, List, Optional

from openai import OpenAI

from server.lib.schema import APQP_CHECKLIST, PLAN_SCHEMA
from server.lib.rendering import render_plan_md
from server.lib.vectorstore import create_vector_store, delete_vector_store

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


def _extract_text(response: Any) -> str:
    """Extract textual content from a Response object."""
    chunks: List[str] = []

    if hasattr(response, "output"):
        for item in response.output or []:
            contents = getattr(item, "content", [])
            for block in contents:
                text = getattr(block, "text", None)
                if text is None and hasattr(block, "annotations"):
                    text = getattr(block, "value", None)
                if text and isinstance(text, str):
                    chunks.append(text)
                elif text and hasattr(text, "value"):
                    chunks.append(text.value)
    elif hasattr(response, "content"):
        for block in response.content or []:
            text = getattr(block, "text", None)
            if text and hasattr(text, "value"):
                chunks.append(text.value)

    return "\n".join(chunks).strip()


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
    model: str = os.getenv("OPENAI_MODEL_PLAN", "o4-mini")

    def _create_agent(self, vector_store_id: Optional[str] = None):
        tools: List[Dict[str, Any]] = [{"type": "file_search"}]
        tool_resources: Dict[str, Any] = {}
        if vector_store_id:
            tool_resources = {"file_search": {"vector_store_ids": [vector_store_id]}}

        agents_api: Any = getattr(self.client, "agents", None)
        if agents_api is None:
            raise RuntimeError("OpenAI client does not support Agents yet. Update the openai package.")

        agent = agents_api.create(
            name="Strategic Build Planner Agent",
            instructions=PROMPT_HEADER,
            model=self.model,
            tools=tools,
            tool_resources=tool_resources or None,
        )
        return agent

    def _create_response(self, agent_id: str, prompt: str, response_format: Dict[str, Any]) -> Any:
        responses_api: Any = getattr(self.client, "responses", None)
        if responses_api is None:
            raise RuntimeError("OpenAI client does not support Responses yet. Update the openai package.")

        return responses_api.create(
            agent_id=agent_id,
            input=[{"role": "user", "content": prompt}],
            response_format=response_format,
        )

    def draft_plan(
        self,
        vector_store_id: str,
        project_name: str,
        customer: Optional[str] = None,
        family: Optional[str] = None,
    ) -> Dict[str, Any]:
        agent = self._create_agent(vector_store_id=vector_store_id)

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

        response = self._create_response(
            agent_id=agent.id,
            prompt=user_prompt,
            response_format={
                "type": "json_schema",
                "json_schema": PLAN_SCHEMA,
            },
        )

        plan_json = json.loads(_extract_text(response))
        getattr(self.client, "agents").delete(agent.id)
        return plan_json

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

        agent = self._create_agent()
        response = self._create_response(
            agent_id=agent.id,
            prompt=meeting_prompt,
            response_format={
                "type": "json_schema",
                "json_schema": PLAN_SCHEMA,
            },
        )
        updated_plan = json.loads(_extract_text(response))
        getattr(self.client, "agents").delete(agent.id)
        return updated_plan

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

        agent = self._create_agent()
        response = self._create_response(
            agent_id=agent.id,
            prompt=prompt,
            response_format={
                "type": "json_schema",
                "json_schema": EVAL_SCHEMA,
            },
        )
        result = json.loads(_extract_text(response))
        getattr(self.client, "agents").delete(agent.id)
        return result


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
