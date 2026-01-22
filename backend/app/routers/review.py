"""
Review Router - Post-Meeting Review Endpoints
Handles transcript comparison and process grading
"""

import logging
import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException

from openai import OpenAI

from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.responses import (
    CompareRequest,
    ComparisonResponse,
    MissingItem,
    Discrepancy,
    CapturedItem,
    ProcessGradeRequest,
    ProcessGradeResponse,
    ProcessDimensionScores,
)


# Request/Response models for apply updates
class ApplyUpdatesRequest(BaseModel):
    """Request to apply updates to a Confluence page"""
    confluence_page_id: str = Field(..., description="Confluence page ID to update")
    missing_items: List[dict] = Field(default_factory=list, description="Missing items to add")
    discrepancies: List[dict] = Field(default_factory=list, description="Discrepancies to resolve")
    meeting_type: str = Field(default="kickoff", description="Meeting type for context")


class ApplyUpdatesResponse(BaseModel):
    """Response after applying updates"""
    success: bool
    page_id: str
    page_url: str
    items_added: int
    discrepancies_resolved: int
    updated_at: datetime
from app.prompts.comparison_prompt import (
    COMPARISON_SYSTEM_PROMPT,
    build_comparison_prompt,
)
from app.prompts.process_grade_prompt import (
    PROCESS_GRADE_SYSTEM_PROMPT,
    build_process_grade_prompt,
)
from app.services.confluence import ConfluenceService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_grade_label(score: int) -> str:
    """Convert numeric score to grade label"""
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Good"
    elif score >= 70:
        return "Acceptable"
    elif score >= 60:
        return "Needs Work"
    else:
        return "Incomplete"


@router.post("/compare", response_model=ComparisonResponse)
async def compare_transcript_to_plan(request: CompareRequest) -> ComparisonResponse:
    """
    Compare meeting transcript against a Confluence page/plan.

    Identifies:
    - Decisions mentioned in transcript but missing from plan
    - Action items discussed but not recorded
    - Discrepancies between transcript and documented content
    - Topics discussed that should be captured

    **Request:**
    - transcript: Meeting transcript text
    - confluence_page_id: Confluence page ID to compare against
    - meeting_type: Type of meeting (kickoff, review, customer, internal)

    **Returns:**
    - coverage_score: 0-100 score of how well the plan covers the transcript
    - missing_items: List of items from transcript not in plan
    - discrepancies: List of conflicts between transcript and plan
    - captured_items: List of items correctly documented
    - summary: Brief overall assessment
    """
    try:
        logger.info(
            f"Comparing transcript to Confluence page {request.confluence_page_id}"
        )

        # Get Confluence page content
        confluence = ConfluenceService()
        page_content = confluence.get_page_content_text(request.confluence_page_id)

        if not page_content:
            raise HTTPException(
                status_code=404,
                detail=f"Could not retrieve content from Confluence page {request.confluence_page_id}",
            )

        # Build prompts
        user_prompt = build_comparison_prompt(
            transcript=request.transcript,
            plan_content=page_content,
            meeting_type=request.meeting_type,
        )

        # Call OpenAI - use gpt-4o for review (gpt-5.2 has compatibility issues)
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = "gpt-4o"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        # Parse response - extract JSON from the response
        content = response.choices[0].message.content
        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        comparison_data = json.loads(content)

        # Build response objects
        missing_items = [
            MissingItem(
                category=item.get("category", "requirement"),
                content=item.get("content", ""),
                transcript_excerpt=item.get("transcript_excerpt", ""),
                importance=item.get("importance", "important"),
            )
            for item in comparison_data.get("missing_items", [])
        ]

        discrepancies = [
            Discrepancy(
                topic=item.get("topic", ""),
                transcript_says=item.get("transcript_says", ""),
                plan_says=item.get("plan_says", ""),
                severity=item.get("severity", "minor"),
            )
            for item in comparison_data.get("discrepancies", [])
        ]

        captured_items = [
            CapturedItem(
                topic=item.get("topic", ""),
                plan_location=item.get("plan_location", ""),
                confidence=item.get("confidence", 0.8),
            )
            for item in comparison_data.get("captured_items", [])
        ]

        coverage_score = comparison_data.get("coverage_score", 50.0)
        summary = comparison_data.get("summary", "Comparison complete.")

        logger.info(
            f"Comparison complete: coverage={coverage_score:.1f}%, "
            f"missing={len(missing_items)}, discrepancies={len(discrepancies)}, "
            f"captured={len(captured_items)}"
        )

        return ComparisonResponse(
            coverage_score=coverage_score,
            missing_items=missing_items,
            discrepancies=discrepancies,
            captured_items=captured_items,
            summary=summary,
            compared_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to compare transcript: {str(e)}"
        )


@router.post("/grade-process", response_model=ProcessGradeResponse)
async def grade_apqp_process(request: ProcessGradeRequest) -> ProcessGradeResponse:
    """
    Grade the quality of an APQP meeting process based on transcript.

    Evaluates 5 dimensions (20 points each = 100 total):
    1. **Discussion Coverage** - Were all APQP topics discussed?
    2. **Stakeholder Participation** - Did all parties contribute?
    3. **Decision Quality** - Were decisions clear and documented?
    4. **Action Assignment** - Were tasks assigned with owners/dates?
    5. **Risk Discussion** - Were risks identified and discussed?

    **Grade Scale:**
    - 90-100: Excellent - Highly effective meeting
    - 80-89: Good - Solid meeting, minor improvements possible
    - 70-79: Acceptable - Several areas to improve
    - 60-69: Needs Work - Significant meeting effectiveness issues
    - <60: Incomplete - Meeting did not achieve APQP objectives

    **Request:**
    - transcript: Meeting transcript text
    - meeting_type: Type of meeting (kickoff, review, customer, internal)
    - expected_attendees: Optional list of expected attendee names

    **Returns:**
    - overall_score: 0-100 total score
    - dimension_scores: Breakdown by each dimension
    - grade: Grade label
    - strengths: What the meeting did well
    - improvements: Suggested improvements
    - topics_discussed: APQP topics covered
    - topics_missing: APQP topics not covered
    """
    try:
        logger.info(f"Grading APQP process for {request.meeting_type} meeting")

        # Build prompts
        user_prompt = build_process_grade_prompt(
            transcript=request.transcript,
            meeting_type=request.meeting_type,
            expected_attendees=request.expected_attendees,
        )

        # Call OpenAI - use gpt-4o for review (gpt-5.2 has compatibility issues)
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = "gpt-4o"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": PROCESS_GRADE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        # Parse response - extract JSON from the response
        content = response.choices[0].message.content
        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        grade_data = json.loads(content)

        # Extract dimension scores
        dim_scores = grade_data.get("dimension_scores", {})
        dimension_scores = ProcessDimensionScores(
            discussion_coverage=dim_scores.get("discussion_coverage", 10),
            stakeholder_participation=dim_scores.get("stakeholder_participation", 10),
            decision_quality=dim_scores.get("decision_quality", 10),
            action_assignment=dim_scores.get("action_assignment", 10),
            risk_discussion=dim_scores.get("risk_discussion", 10),
        )

        # Calculate overall score
        overall_score = grade_data.get("overall_score")
        if overall_score is None:
            overall_score = (
                dimension_scores.discussion_coverage
                + dimension_scores.stakeholder_participation
                + dimension_scores.decision_quality
                + dimension_scores.action_assignment
                + dimension_scores.risk_discussion
            )

        # Get grade label
        grade_label = grade_data.get("grade") or get_grade_label(overall_score)

        logger.info(
            f"Process graded: {overall_score}/100 ({grade_label}) - "
            f"DC:{dimension_scores.discussion_coverage} SP:{dimension_scores.stakeholder_participation} "
            f"DQ:{dimension_scores.decision_quality} AA:{dimension_scores.action_assignment} "
            f"RD:{dimension_scores.risk_discussion}"
        )

        return ProcessGradeResponse(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            grade=grade_label,
            strengths=grade_data.get("strengths", []),
            improvements=grade_data.get("improvements", []),
            topics_discussed=grade_data.get("topics_discussed", []),
            topics_missing=grade_data.get("topics_missing", []),
            graded_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process grading failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to grade process: {str(e)}"
        )


@router.post("/apply-updates", response_model=ApplyUpdatesResponse)
async def apply_updates_to_plan(request: ApplyUpdatesRequest) -> ApplyUpdatesResponse:
    """
    Apply selected updates to a Confluence page.

    Takes missing items and discrepancies identified during comparison
    and adds them to the Confluence page in the appropriate sections.

    **Request:**
    - confluence_page_id: Page ID to update
    - missing_items: List of missing items to add (from comparison)
    - discrepancies: List of discrepancies to resolve (from comparison)
    - meeting_type: Meeting type for context

    **Returns:**
    - success: Whether the update was successful
    - page_id: The updated page ID
    - page_url: URL to the updated page
    - items_added: Number of items added
    - discrepancies_resolved: Number of discrepancies addressed
    """
    try:
        logger.info(f"Applying updates to Confluence page {request.confluence_page_id}")

        confluence = ConfluenceService()

        # Get current page content
        page = confluence.get_page(request.confluence_page_id)
        if not page:
            raise HTTPException(
                status_code=404,
                detail=f"Confluence page {request.confluence_page_id} not found"
            )

        current_content = page.get("body", {}).get("storage", {}).get("value", "")

        # Build update content using AI
        if request.missing_items or request.discrepancies:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = os.getenv("OPENAI_MODEL_PLAN", "gpt-4o-2024-08-06")

            update_prompt = f"""You are updating a Confluence page to add missing items from a meeting.

**Current Page Content:**
{current_content}

**Missing Items to Add:**
{json.dumps(request.missing_items, indent=2) if request.missing_items else "None"}

**Discrepancies to Resolve (use transcript version):**
{json.dumps(request.discrepancies, indent=2) if request.discrepancies else "None"}

**Instructions:**
1. Return the COMPLETE updated page content in Confluence storage format (HTML)
2. Add missing items in appropriate sections based on their category:
   - decision: Add to Decisions or Key Agreements section
   - action_item: Add to Action Items or Next Steps section
   - requirement: Add to Requirements or Specifications section
   - risk: Add to Risks or Concerns section
   - question: Add to Open Questions section
3. For discrepancies, update the text to match the transcript version
4. Preserve all existing content and formatting
5. Use proper Confluence HTML tags (p, ul, li, h2, h3, table, etc.)
6. Add items with clear bullet points showing they came from meeting review

Return ONLY the complete HTML content, no explanation."""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": update_prompt},
                ],
            )

            updated_content = response.choices[0].message.content.strip()

            # Clean up any markdown code blocks if present
            if updated_content.startswith("```"):
                lines = updated_content.split("\n")
                updated_content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            # Update the page
            result = confluence.update_page(
                page_id=request.confluence_page_id,
                title=page.get("title", "Updated Page"),
                content=updated_content,
            )

            page_url = f"{confluence.base_url}/pages/viewpage.action?pageId={request.confluence_page_id}"

            logger.info(
                f"Applied updates: {len(request.missing_items)} items added, "
                f"{len(request.discrepancies)} discrepancies resolved"
            )

            return ApplyUpdatesResponse(
                success=True,
                page_id=request.confluence_page_id,
                page_url=page_url,
                items_added=len(request.missing_items),
                discrepancies_resolved=len(request.discrepancies),
                updated_at=datetime.utcnow(),
            )
        else:
            # Nothing to update
            page_url = f"{confluence.base_url}/pages/viewpage.action?pageId={request.confluence_page_id}"
            return ApplyUpdatesResponse(
                success=True,
                page_id=request.confluence_page_id,
                page_url=page_url,
                items_added=0,
                discrepancies_resolved=0,
                updated_at=datetime.utcnow(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply updates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to apply updates: {str(e)}"
        )


@router.get("/process-rubric")
async def get_process_grading_rubric():
    """
    Get the APQP process grading rubric.

    Returns the scoring criteria for each dimension to help
    users understand how meetings are evaluated.
    """
    return {
        "total_points": 100,
        "dimensions": {
            "discussion_coverage": {
                "max_points": 20,
                "description": "Were all critical APQP topics discussed?",
                "scoring": {
                    "18-20": "All key topics covered with appropriate depth",
                    "14-17": "Most topics covered, minor gaps",
                    "10-13": "Several important topics missed",
                    "6-9": "Major APQP areas not discussed",
                    "0-5": "Meeting lacked APQP focus",
                },
                "key_topics": [
                    "Customer requirements",
                    "Quality requirements",
                    "Material specifications",
                    "Timeline and milestones",
                    "Tooling needs",
                    "Risk identification",
                ],
            },
            "stakeholder_participation": {
                "max_points": 20,
                "description": "Did all relevant parties contribute meaningfully?",
                "scoring": {
                    "18-20": "Active, balanced participation from all",
                    "14-17": "Most participants engaged",
                    "10-13": "Dominated by few voices",
                    "6-9": "Key stakeholders silent",
                    "0-5": "One-sided presentation",
                },
            },
            "decision_quality": {
                "max_points": 20,
                "description": "Were decisions clear, reasoned, and documented?",
                "scoring": {
                    "18-20": "Clear decisions with rationale",
                    "14-17": "Most decisions clear",
                    "10-13": "Decisions made but rationale unclear",
                    "6-9": "Decisions vague or deferred",
                    "0-5": "No real decisions made",
                },
            },
            "action_assignment": {
                "max_points": 20,
                "description": "Were action items assigned with owners and deadlines?",
                "scoring": {
                    "18-20": "All actions have owners, dates, deliverables",
                    "14-17": "Most actions assigned, some missing dates",
                    "10-13": "Actions identified but poorly assigned",
                    "6-9": "Vague 'someone should' statements",
                    "0-5": "No action tracking",
                },
            },
            "risk_discussion": {
                "max_points": 20,
                "description": "Were risks identified and mitigation discussed?",
                "scoring": {
                    "18-20": "Proactive risk identification with mitigation",
                    "14-17": "Key risks identified, some mitigation",
                    "10-13": "Some risk awareness, no mitigation",
                    "6-9": "Risks mentioned only when problems arise",
                    "0-5": "No risk discussion",
                },
                "common_risks": [
                    "Long-lead items",
                    "Single-source suppliers",
                    "New processes",
                    "Tight timelines",
                    "Customer-specific requirements",
                ],
            },
        },
        "grade_scale": {
            "90-100": "Excellent - Highly effective meeting",
            "80-89": "Good - Solid meeting, minor improvements possible",
            "70-79": "Acceptable - Several areas to improve",
            "60-69": "Needs Work - Significant issues",
            "<60": "Incomplete - Did not achieve APQP objectives",
        },
    }
