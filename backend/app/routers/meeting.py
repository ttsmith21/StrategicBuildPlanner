"""
Meeting Router - Process Meeting Transcripts and Apply to Strategic Build Plans
"""

import logging
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from openai import OpenAI
import os

from app.models.responses import MeetingApplyRequest, MeetingApplyResponse
from app.models.plan_schema import StrategicBuildPlan
from app.prompts.draft_prompt import MEETING_SYSTEM_PROMPT
from app.routers.draft import plan_to_markdown

logger = logging.getLogger(__name__)

router = APIRouter()


def count_action_items(plan: dict) -> int:
    """Count total action items in plan"""
    return len(plan.get("asana_todos", []))


def count_notes(plan: dict) -> int:
    """Count total notes in plan"""
    apqp = len(plan.get("apqp_notes", []))
    meeting = len(plan.get("customer_meeting_notes", []))
    return apqp + meeting


@router.post("/apply", response_model=MeetingApplyResponse)
async def apply_meeting_transcript(request: MeetingApplyRequest):
    """
    Apply a meeting transcript to an existing Strategic Build Plan

    **Process:**
    1. Parse the transcript for decisions, action items, and requirements
    2. Extract assignees and due dates from natural language
    3. Merge new information into the existing plan
    4. Create Asana tasks for action items and unknowns
    5. Return the updated plan

    **What gets extracted:**
    - **Decisions** → Added to APQP Notes or Customer Meeting Notes
    - **Action Items** → Created as Asana tasks with assignees/due dates
    - **Open Questions** → Created as Asana tasks for resolution
    - **Requirements** → Added to relevant plan sections
    - **Timeline Changes** → Updated in Execution Strategy
    - **Technical Clarifications** → Updated in Build Strategy or Quality Plan

    **Meeting Types:**
    - `customer` - External customer meetings (goes to customer_meeting_notes)
    - `internal` - Internal team meetings (goes to apqp_notes)
    - `kickoff` - Project kickoff (both notes + keys_to_project)
    - `review` - Design/quality review (quality_plan updates)
    """
    try:
        logger.info(
            f"Processing meeting transcript: type={request.meeting_type}, "
            f"date={request.meeting_date}, "
            f"transcript_length={len(request.transcript)} chars"
        )

        # Get initial counts for comparison
        initial_action_items = count_action_items(request.plan_json)
        initial_notes = count_notes(request.plan_json)

        # Build the user prompt
        attendee_info = ""
        if request.attendees:
            attendee_info = f"\n**Attendees:** {', '.join(request.attendees)}"

        date_info = ""
        if request.meeting_date:
            date_info = f"\n**Meeting Date:** {request.meeting_date}"

        user_prompt = f"""Process this {request.meeting_type} meeting transcript and merge the information into the existing Strategic Build Plan.

**Current Plan:**
```json
{json.dumps(request.plan_json, indent=2, default=str)}
```
{date_info}{attendee_info}

**Meeting Transcript:**
{request.transcript}

**Instructions:**
1. Extract all decisions, action items, requirements, and clarifications
2. Merge into the appropriate plan sections
3. For action items, create Asana tasks with:
   - Title format: [APQP] {{action}}
   - Assignee hint from phrases like "John will...", "Sarah to..."
   - Due date hint from "by EOW", "next week", etc.
   - Priority based on urgency keywords
4. Add meeting notes to {'customer_meeting_notes' if request.meeting_type == 'customer' else 'apqp_notes'}
5. If new info conflicts with existing plan, add a note and flag it

Return the complete updated StrategicBuildPlan JSON.
"""

        # Call OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL_PLAN", "gpt-4o-2024-08-06")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": MEETING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=16000,
        )

        # Parse the response
        updated_plan_data = json.loads(response.choices[0].message.content)

        # Validate and enhance plan data
        try:
            validated_plan = StrategicBuildPlan(**updated_plan_data)
            plan_json = validated_plan.model_dump(mode="json")
        except Exception as validation_error:
            logger.warning(f"Plan validation warning: {validation_error}")
            plan_json = updated_plan_data

        # Calculate changes
        final_action_items = count_action_items(plan_json)
        final_notes = count_notes(plan_json)

        new_action_items = final_action_items - initial_action_items
        new_notes = final_notes - initial_notes

        # Build changes summary
        changes_summary = []
        if new_action_items > 0:
            changes_summary.append(f"Added {new_action_items} new action item(s)")
        if new_notes > 0:
            changes_summary.append(f"Added {new_notes} new meeting note(s)")

        # Check for section updates
        for section in [
            "keys_to_project",
            "quality_plan",
            "purchasing",
            "build_strategy",
            "execution_strategy",
        ]:
            old_section = request.plan_json.get(section, {})
            new_section = plan_json.get(section, {})
            if old_section != new_section:
                changes_summary.append(f"Updated {section.replace('_', ' ')}")

        if not changes_summary:
            changes_summary.append("No significant changes detected")

        # Convert to Markdown
        plan_markdown = plan_to_markdown(plan_json)

        logger.info(
            f"Meeting transcript processed: "
            f"+{new_action_items} action items, +{new_notes} notes"
        )

        return MeetingApplyResponse(
            plan_json=plan_json,
            plan_markdown=plan_markdown,
            changes_summary=changes_summary,
            new_action_items=max(0, new_action_items),
            new_notes=max(0, new_notes),
            applied_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meeting processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process meeting transcript: {str(e)}"
        )


@router.post("/upload", response_model=MeetingApplyResponse)
async def upload_and_apply_transcript(
    plan_json: str = Form(..., description="Current plan as JSON string"),
    transcript_file: UploadFile = File(..., description="Transcript file (.txt)"),
    meeting_type: str = Form(default="customer"),
    meeting_date: str = Form(default=None),
    attendees: str = Form(default=None, description="Comma-separated attendee names"),
):
    """
    Upload a transcript file and apply it to the plan

    Alternative to the JSON endpoint - accepts a file upload.

    **Supported formats:** .txt, .md
    """
    try:
        # Validate file type
        if not transcript_file.filename.endswith((".txt", ".md")):
            raise HTTPException(
                status_code=400, detail="Only .txt and .md files are supported"
            )

        # Read transcript
        content = await transcript_file.read()
        transcript = content.decode("utf-8")

        # Parse plan JSON
        try:
            plan_data = json.loads(plan_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid plan_json: {str(e)}")

        # Parse attendees
        attendees_list = None
        if attendees:
            attendees_list = [a.strip() for a in attendees.split(",")]

        # Create request and delegate to main handler
        request = MeetingApplyRequest(
            plan_json=plan_data,
            transcript=transcript,
            meeting_type=meeting_type,
            meeting_date=meeting_date,
            attendees=attendees_list,
        )

        return await apply_meeting_transcript(request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcript upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process transcript file: {str(e)}"
        )
