"""
Lessons Learned Router - Extract insights from historical Confluence pages
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.lessons_service import LessonsService

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

# Lazy initialization - service created on first request
_lessons_service = None


def get_lessons_service() -> LessonsService:
    """Get or create the lessons service instance."""
    global _lessons_service
    if _lessons_service is None:
        _lessons_service = LessonsService()
    return _lessons_service


# ============================================================================
# Request/Response Models
# ============================================================================


class LessonsExtractRequest(BaseModel):
    """Request to extract lessons learned from historical pages"""

    page_id: str = Field(..., description="Confluence page ID of the current project")
    checklist: Dict[str, Any] = Field(
        default={}, description="Current project checklist for context"
    )
    max_siblings: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of sibling pages to analyze",
    )


class LessonInsight(BaseModel):
    """A single lesson learned insight"""

    id: str = Field(..., description="Unique identifier for this insight")
    category: str = Field(
        ...,
        description="Category: Quality Issue, Risk Warning, Best Practice, Customer Feedback, Process Improvement",
    )
    title: str = Field(..., description="Brief title for the insight")
    description: str = Field(
        ..., description="Detailed description of what was learned"
    )
    recommendation: str = Field(
        ..., description="Recommended action for current project"
    )
    source_excerpt: Optional[str] = Field(
        None, description="Relevant excerpt from source document"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)"
    )


class PageReference(BaseModel):
    """Reference to a Confluence page"""

    id: str
    title: str


class LessonsExtractResponse(BaseModel):
    """Response from lessons learned extraction"""

    insights: List[LessonInsight] = Field(
        default_factory=list, description="Extracted lessons learned"
    )
    sibling_pages_analyzed: List[PageReference] = Field(
        default_factory=list, description="Sibling pages that were analyzed"
    )
    family_page: Optional[PageReference] = Field(
        None, description="Family (parent) page that was analyzed"
    )
    customer_page: Optional[PageReference] = Field(
        None, description="Customer (grandparent) page that was analyzed"
    )
    skipped: bool = Field(default=False, description="Whether extraction was skipped")
    skip_reason: Optional[str] = Field(
        None, description="Reason for skipping extraction"
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/extract", response_model=LessonsExtractResponse)
async def extract_lessons(request: LessonsExtractRequest) -> LessonsExtractResponse:
    """
    Extract lessons learned from historical Confluence pages.

    Analyzes sibling projects (other children of the family page), the family page itself,
    and the customer page to identify actionable insights for the current project.

    **Process:**
    1. Get page hierarchy from Confluence (ancestors)
    2. Identify family page (parent) and customer page (grandparent)
    3. Find sibling projects (other children of family page)
    4. Fetch content from each page
    5. Run AI analysis to extract lessons learned
    6. Return insights sorted by relevance

    **Response includes:**
    - `insights`: List of lessons learned with category, description, recommendation
    - `sibling_pages_analyzed`: Which sibling pages were used
    - `family_page`: The family/parent page analyzed
    - `customer_page`: The customer/grandparent page analyzed
    - `skipped`: True if extraction was skipped (no data available)
    - `skip_reason`: Why extraction was skipped

    **Usage:**
    Call this endpoint after the Compare phase, before Publish.
    The frontend will display insights for user review and acceptance.
    Accepted lessons are passed to the Publish phase for injection into Confluence.
    """
    try:
        service = get_lessons_service()
        result = await service.extract_lessons(
            page_id=request.page_id,
            checklist=request.checklist,
            max_siblings=request.max_siblings,
        )

        # Convert to response model
        return LessonsExtractResponse(
            insights=[
                LessonInsight(
                    id=i.get("id", f"insight_{idx}"),
                    category=i.get("category", "Best Practice"),
                    title=i.get("title", "Untitled"),
                    description=i.get("description", ""),
                    recommendation=i.get("recommendation", ""),
                    source_excerpt=i.get("source_excerpt"),
                    relevance_score=i.get("relevance_score", 0.5),
                )
                for idx, i in enumerate(result.get("insights", []))
            ],
            sibling_pages_analyzed=[
                PageReference(id=p["id"], title=p["title"])
                for p in result.get("sibling_pages_analyzed", [])
            ],
            family_page=(
                PageReference(**result["family_page"])
                if result.get("family_page")
                else None
            ),
            customer_page=(
                PageReference(**result["customer_page"])
                if result.get("customer_page")
                else None
            ),
            skipped=result.get("skipped", False),
            skip_reason=result.get("skip_reason"),
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to extract lessons: {str(e)}"
        )
