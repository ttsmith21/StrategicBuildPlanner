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

    def generate_meeting_prep(
        self,
        vector_store_id: str,
        project_name: str,
        customer: Optional[str] = None,
        family: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate pre-meeting materials: Project Brief + Meeting Agenda.

        Returns dict with:
        - project_brief: Markdown-formatted brief (2-3 pages)
        - agenda_topics: List of APQP topics with prompts/facts/questions
        - lessons_learned: Summary from Confluence pages
        - critical_questions: Key questions to answer in meeting
        """
        prep_schema = {
            "name": "MeetingPrep",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "project_brief": {"type": "string"},
                    "agenda_topics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "discussion_prompts": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "known_facts": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "open_questions": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "suggested_duration_minutes": {"type": "integer"},
                            },
                            "required": ["name", "discussion_prompts", "known_facts", "open_questions", "suggested_duration_minutes"],
                            "additionalProperties": False,
                        }
                    },
                    "lessons_learned": {"type": "string"},
                    "critical_questions": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                },
                "required": ["project_brief", "agenda_topics", "lessons_learned", "critical_questions"],
            },
            "strict": True,
        }

        user_prompt = dedent(
            f"""
            Generate materials to prepare the team for an APQP meeting.

            Project: {project_name}
            Customer: {customer or 'UNKNOWN'}
            Family of Parts: {family or 'UNKNOWN'}

            Tasks:
            1. Read all uploaded documents using file_search
            2. Generate a Project Brief (2-3 pages, Markdown format) covering:
               - Project overview (customer, part family, scope)
               - Key facts from documents (materials, quantities, critical specs)
               - Relevant lessons learned from Confluence history
               - Open questions that need discussion

            3. Create a Meeting Agenda with 8 APQP topics:
               - Keys to the Project (15 min) - What 3-5 things matter most?
               - Quality Plan (15 min) - CTQs, inspection, hold points
               - Purchasing Risks (10 min) - Long-leads, vendor requirements
               - Build Strategy (15 min) - Flow, tooling, fixtures
               - Schedule (10 min) - Timeline, dependencies
               - Engineering Routing (10 min) - Process steps overview
               - Execution Strategy (10 min) - Material handling, staging
               - Shipping/Packaging (5 min) - Protection, logistics

            For each topic include:
            - discussion_prompts: Questions to guide discussion (3-5 items)
            - known_facts: What we already know from documents (2-4 items)
            - open_questions: What needs to be answered (2-4 items)
            - suggested_duration_minutes: Time allocation

            4. Summarize lessons_learned from Confluence pages if present

            5. List critical_questions (top 5-10 most important) that MUST be answered in the meeting

            Format: Presentation-ready for projector display at meeting start.
            """
        ).strip()

        return self._run_structured_task(
            instructions=PROMPT_HEADER,
            prompt=user_prompt,
            schema=prep_schema,
            vector_store_id=vector_store_id,
        )

    def apply_meeting_notes(
        self,
        plan_json: Dict[str, Any],
        transcript_texts: List[str],
    ) -> Dict[str, Any]:
        meeting_prompt = dedent(
            f"""
            Generate a Strategic Build Plan from the APQP meeting notes.

            CRITICAL REQUIREMENTS:

            1. EXTRACT "KEYS TO THE PROJECT" (1-5 bullets):
               - Must identify the 3-5 most critical success factors
               - These are STRATEGIC INSIGHTS, not obvious facts
               - Focus on what makes/loses money, critical dependencies, risks
               - Examples of GOOD keys:
                 ✓ "Passivation cert required before shipment - blocks order if missed"
                 ✓ "Fixture cost ($12k) needs 250pc order to hit margin target"
                 ✓ "Customer 2-week lead but material is 8 weeks - need buffer stock"
               - Examples of BAD keys (too obvious/vague):
                 ✗ "Part is made of stainless steel"
                 ✗ "Quality is important"
                 ✗ "We need to weld it"

            2. FILTER DETAIL LEVELS:
               - STRATEGIC → Include in plan (decisions, risks, mitigations, cost levers)
               - REFERENCE → Cite document, don't copy (dimension callouts, material specs)
               - EXCLUDE → Don't include (meeting logistics, obvious facts)

            3. ENSURE ALL 8 APQP DIMENSIONS ARE COVERED:
               - Keys to the Project (1-5 bullets) ← MOST IMPORTANT
               - Quality Plan (CTQs, inspection, hold points)
               - Purchasing Risks (long-leads, mitigations)
               - Build Strategy (flow, tooling, fixtures)
               - Schedule (timeline, dependencies)
               - Engineering Routing (process steps)
               - Execution Strategy (material handling)
               - Shipping/Packaging (protection, logistics)

            4. MARK CONFIDENCE:
               - Meeting discussion → confidence: 0.95
               - From documents → confidence: 0.90
               - Inferred/assumed → confidence: 0.50
               - Unknown → "UNKNOWN" with confidence: 0.0

            Current plan (if exists):
            {json.dumps(plan_json, indent=2) if plan_json else "{}"}

            Meeting notes:
            {'\n\n'.join(transcript_texts)}

            Generate complete Strategic Build Plan focusing on STRATEGIC INSIGHTS.
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
