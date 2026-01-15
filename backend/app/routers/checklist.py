"""
Checklist Router - Pre-Meeting Checklist Generation API
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datetime import datetime
from app.services.checklist_service import ChecklistService
from app.services.confluence import ConfluenceService

router = APIRouter(prefix="/api/checklist", tags=["checklist"])

# Initialize service
checklist_service = ChecklistService()


class ChecklistRequest(BaseModel):
    """Request model for checklist generation"""
    vector_store_id: str
    project_name: str
    customer: Optional[str] = None
    category_ids: Optional[List[str]] = None


class ChecklistItem(BaseModel):
    """Individual checklist item"""
    prompt_id: str
    question: str
    prompt: str
    answer: Optional[str]
    source: Optional[str]
    status: str
    error: Optional[str]


class ChecklistCategory(BaseModel):
    """Category with items"""
    id: str
    name: str
    order: int
    items: List[ChecklistItem]


class ChecklistStats(BaseModel):
    """Checklist statistics"""
    total_prompts: int
    requirements_found: int
    no_requirements: int
    errors: int
    coverage_percentage: float


class ChecklistResponse(BaseModel):
    """Complete checklist response"""
    project_name: str
    customer: Optional[str]
    vector_store_id: str
    created_at: str
    generation_time_seconds: float
    categories: List[ChecklistCategory]
    statistics: ChecklistStats


class PromptCategory(BaseModel):
    """Category of prompts"""
    id: str
    name: str
    order: int
    prompts: List[dict]


class PromptsResponse(BaseModel):
    """Response with all prompts"""
    version: str
    description: str
    categories: List[PromptCategory]
    metadata: dict


@router.post("", response_model=ChecklistResponse)
async def generate_checklist(request: ChecklistRequest):
    """
    Generate a pre-meeting checklist by running all prompts against uploaded documents

    This endpoint runs all active prompts (or filtered by category) in parallel
    against the specified vector store. Each prompt queries the documents and
    extracts relevant requirements.

    **Rate limiting**: Prompts run with controlled concurrency (default 10)
    to avoid hitting OpenAI rate limits.

    **Typical duration**: 30-60 seconds for ~40 prompts with 10 concurrent.
    """
    try:
        result = await checklist_service.generate_checklist(
            vector_store_id=request.vector_store_id,
            project_name=request.project_name,
            customer=request.customer,
            category_ids=request.category_ids
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts", response_model=PromptsResponse)
async def get_prompts():
    """
    Get all checklist prompts

    Returns the complete prompt configuration including all categories and prompts.
    Use this for:
    - Displaying available prompts in the UI
    - Admin interface for editing prompts
    - Filtering which prompts to run
    """
    prompts = checklist_service.get_prompts()
    return prompts


@router.get("/prompts/active")
async def get_active_prompts():
    """
    Get only active prompts as a flat list

    Returns prompts that have active=true, with their category information.
    Useful for showing which prompts will actually run.
    """
    return checklist_service.get_active_prompts()


@router.put("/prompts")
async def update_prompts(prompts_data: dict):
    """
    Update the prompts configuration (Admin only)

    Replaces the entire prompts configuration. Use this to:
    - Add new prompts
    - Edit existing prompts
    - Enable/disable prompts
    - Reorder categories
    """
    success = checklist_service.save_prompts(prompts_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save prompts")
    return {"status": "success", "message": "Prompts updated"}


class PublishChecklistRequest(BaseModel):
    """Request to publish checklist to Confluence"""
    checklist: dict
    parent_page_id: Optional[str] = None


class PublishResponse(BaseModel):
    """Response after publishing"""
    page_id: str
    page_url: str
    page_title: str
    published_at: datetime


@router.post("/publish", response_model=PublishResponse)
async def publish_checklist_to_confluence(request: PublishChecklistRequest):
    """
    Publish a Pre-Meeting Checklist to Confluence

    **Process:**
    1. Convert checklist to Confluence storage format (HTML)
    2. Create new page with checklist content
    3. Return Confluence page URL

    **Prerequisites:**
    - Confluence credentials configured in .env
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        checklist = request.checklist
        if not checklist:
            raise HTTPException(status_code=400, detail="No checklist provided")

        project_name = checklist.get("project_name", "Unknown Project")
        logger.info(f"Publishing checklist to Confluence: {project_name}")

        # Initialize Confluence service
        confluence = ConfluenceService()

        # Convert checklist to Confluence storage format
        checklist_content = confluence.checklist_to_confluence_storage(checklist)

        # Generate page title
        page_title = f"Pre-Meeting Checklist - {project_name}"

        # Create the page
        result = await confluence.create_page(
            title=page_title,
            content=checklist_content,
            parent_id=request.parent_page_id
        )

        logger.info(
            f"Successfully published checklist to Confluence: {result['title']} "
            f"({result['id']}) - {result['url']}"
        )

        return PublishResponse(
            page_id=result["id"],
            page_url=result["url"],
            page_title=result["title"],
            published_at=datetime.utcnow()
        )

    except ValueError as e:
        logger.error(f"Confluence configuration error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Confluence checklist publish failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish checklist to Confluence: {str(e)}"
        )
# Force reload
