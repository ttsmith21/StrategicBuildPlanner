"""
QA Router - Quality Assurance Grading for Strategic Build Plans
"""

import logging
import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from openai import OpenAI

from app.models.responses import QAGradeRequest, QAGradeResponse, DimensionScores
from app.prompts.qa_prompt import QA_SYSTEM_PROMPT

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


@router.post("/grade", response_model=QAGradeResponse)
async def grade_plan(request: QAGradeRequest):
    """
    Grade a Strategic Build Plan using AI-powered QA analysis

    **Grading Dimensions (20 points each, 100 total):**

    1. **Completeness** - Are all sections filled with real data?
    2. **Specificity** - Are statements concrete (quantities, dates, specs)?
    3. **Actionability** - Can the team execute based on this plan?
    4. **Manufacturability** - Does it reflect realistic manufacturing constraints?
    5. **Risk Coverage** - Are risks identified with mitigations?

    **Grade Scale:**
    - 90-100: Excellent - Ready for execution
    - 80-89: Good - Minor improvements needed
    - 70-79: Acceptable - Several gaps to address
    - 60-69: Needs Work - Significant improvements required
    - <60: Incomplete - Major revision needed

    **Returns:**
    - Overall score and dimension breakdown
    - Strengths and improvement suggestions
    - Critical gaps (blocking issues)
    """
    try:
        logger.info(
            f"Grading plan: {request.plan_json.get('project_name', 'Unknown')}"
        )

        # Build user prompt
        user_prompt = f"""Grade the following Strategic Build Plan according to the rubric.

**Plan to Grade:**
```json
{json.dumps(request.plan_json, indent=2, default=str)}
```

Evaluate each dimension carefully and provide:
1. Scores for each of the 5 dimensions (0-20 each)
2. 2-3 specific strengths
3. 3-5 actionable improvement suggestions
4. Any critical gaps that block execution

Return your analysis as JSON matching the specified format.
"""

        # Call OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL_PLAN", "gpt-4o-2024-08-06")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=4000
        )

        # Parse the response
        grade_data = json.loads(response.choices[0].message.content)

        # Extract dimension scores
        dim_scores = grade_data.get("dimension_scores", {})
        dimension_scores = DimensionScores(
            completeness=dim_scores.get("completeness", 10),
            specificity=dim_scores.get("specificity", 10),
            actionability=dim_scores.get("actionability", 10),
            manufacturability=dim_scores.get("manufacturability", 10),
            risk_coverage=dim_scores.get("risk_coverage", 10)
        )

        # Calculate overall score
        overall_score = grade_data.get("overall_score")
        if overall_score is None:
            overall_score = (
                dimension_scores.completeness +
                dimension_scores.specificity +
                dimension_scores.actionability +
                dimension_scores.manufacturability +
                dimension_scores.risk_coverage
            )

        # Get grade label
        grade_label = grade_data.get("grade") or get_grade_label(overall_score)

        logger.info(
            f"Plan graded: {overall_score}/100 ({grade_label}) - "
            f"C:{dimension_scores.completeness} S:{dimension_scores.specificity} "
            f"A:{dimension_scores.actionability} M:{dimension_scores.manufacturability} "
            f"R:{dimension_scores.risk_coverage}"
        )

        return QAGradeResponse(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            grade=grade_label,
            strengths=grade_data.get("strengths", []),
            improvements=grade_data.get("improvements", []),
            critical_gaps=grade_data.get("critical_gaps", []),
            graded_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"QA grading failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grade plan: {str(e)}"
        )


@router.get("/rubric")
async def get_grading_rubric():
    """
    Get the QA grading rubric

    Returns the scoring criteria for each dimension to help
    users understand how plans are evaluated.
    """
    return {
        "total_points": 100,
        "dimensions": {
            "completeness": {
                "max_points": 20,
                "description": "Are all required sections filled with real data?",
                "scoring": {
                    "18-20": "All sections populated with multiple data points, no critical gaps",
                    "14-17": "Most sections complete, minor gaps in non-critical areas",
                    "10-13": "Several sections sparse or missing",
                    "6-9": "Major sections empty or placeholder text",
                    "0-5": "Majority of plan is empty or generic"
                }
            },
            "specificity": {
                "max_points": 20,
                "description": "Are statements concrete and actionable?",
                "scoring": {
                    "18-20": "Precise details (quantities, dates, specs, part numbers)",
                    "14-17": "Mix of specific and general statements",
                    "10-13": "Mostly high-level, lacks operational detail",
                    "6-9": "Vague and generic throughout",
                    "0-5": "No actionable details"
                },
                "examples": {
                    "bad": "Customer requires quality parts",
                    "good": "Customer requires Cpk >= 1.67 per Q1 2025 agreement"
                }
            },
            "actionability": {
                "max_points": 20,
                "description": "Can the team execute based on this plan?",
                "scoring": {
                    "18-20": "Clear next steps, assigned owners, timelines for all critical items",
                    "14-17": "Most items have action plans, some ownership gaps",
                    "10-13": "High-level strategy but lacks execution details",
                    "6-9": "Few actionable next steps",
                    "0-5": "No clear path forward"
                },
                "checklist": [
                    "Asana tasks created for unknowns",
                    "Timeline with specific dates",
                    "Assigned owners or departments",
                    "Dependencies identified"
                ]
            },
            "manufacturability": {
                "max_points": 20,
                "description": "Does it reflect realistic manufacturing constraints?",
                "scoring": {
                    "18-20": "Thoughtful make/buy analysis, tooling plans, capacity check",
                    "14-17": "Basic manufacturing considerations addressed",
                    "10-13": "Some manufacturing gaps",
                    "6-9": "Unrealistic or incomplete manufacturing strategy",
                    "0-5": "No evidence of manufacturing planning"
                },
                "red_flags": [
                    "No tooling plan for custom parts",
                    "Ignoring lead times",
                    "Unrealistic timelines",
                    "Missing capacity analysis"
                ]
            },
            "risk_coverage": {
                "max_points": 20,
                "description": "Are risks identified and mitigated?",
                "scoring": {
                    "18-20": "Comprehensive risk analysis with mitigations",
                    "14-17": "Key risks identified with some mitigation plans",
                    "10-13": "Basic risk awareness, limited mitigation",
                    "6-9": "Few risks mentioned",
                    "0-5": "No risk analysis"
                },
                "common_risks": [
                    "Long-lead items",
                    "Single-source suppliers",
                    "New processes/untested methods",
                    "Tight timelines",
                    "Customer-specific requirements"
                ]
            }
        },
        "grade_scale": {
            "90-100": "Excellent - Ready for execution",
            "80-89": "Good - Minor improvements needed",
            "70-79": "Acceptable - Several gaps to address",
            "60-69": "Needs Work - Significant improvements required",
            "<60": "Incomplete - Major revision needed"
        }
    }
