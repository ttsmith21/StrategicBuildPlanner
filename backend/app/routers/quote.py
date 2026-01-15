"""
Quote Router - Upload and compare vendor quotes against customer requirements

Workflow:
1. POST /api/quote/extract - Upload quote PDF, extract assumptions
2. POST /api/quote/compare - Compare quote assumptions against checklist
3. POST /api/quote/merge-preview - Generate merge preview with conflict highlights
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.quote_comparison_service import QuoteComparisonService
from app.services.document_processor import DocumentProcessor

router = APIRouter(prefix="/api/quote", tags=["quote"])

# Initialize services
quote_service = QuoteComparisonService()
doc_processor = DocumentProcessor()

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class QuoteAssumptions(BaseModel):
    """Extracted quote assumptions"""

    vendor_name: Optional[str] = None
    quote_number: Optional[str] = None
    project_name: Optional[str] = None
    assumptions: list
    general_notes: list
    extracted_at: str


class ComparisonRequest(BaseModel):
    """Request to compare quote against checklist"""

    quote_assumptions: dict
    checklist: dict


class ComparisonStats(BaseModel):
    """Statistics from comparison"""

    total_matches: int
    total_conflicts: int
    quote_only_count: int
    checklist_only_count: int
    high_severity_conflicts: int


class ComparisonResult(BaseModel):
    """Full comparison result"""

    project_name: Optional[str] = None
    vendor_name: Optional[str] = None
    quote_number: Optional[str] = None
    matches: list
    conflicts: list
    quote_only: list
    checklist_only: list
    statistics: ComparisonStats
    compared_at: str


class MergePreviewRequest(BaseModel):
    """Request to generate merge preview"""

    checklist: dict
    quote_assumptions: dict
    comparison: dict


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/extract", response_model=QuoteAssumptions)
async def extract_quote_assumptions(
    file: UploadFile = File(..., description="Quote PDF file"),
    project_name: str = Form(None, description="Project name for context"),
):
    """
    Extract assumptions and notes from a vendor quote PDF

    **Process:**
    1. Upload the quote PDF (vendor's quote with Important Notes & Assumptions)
    2. AI extracts and categorizes all assumptions
    3. Returns structured data for comparison

    **Extracted categories:**
    - Material Standards
    - Fabrication Process
    - Quality Inspections
    - Dimensional Tolerances
    - Finishing Requirements
    - Packaging & Shipping
    - Documentation
    """
    try:
        # Read uploaded file
        content = await file.read()
        filename = file.filename or "quote.pdf"

        logger.info(f"Processing quote file: {filename} ({len(content)} bytes)")

        # Extract text from PDF
        text = doc_processor.extract_text(content, filename)
        if not text:
            raise HTTPException(
                status_code=400, detail="Could not extract text from PDF"
            )

        logger.info(f"Extracted {len(text)} characters from quote")

        # Extract assumptions using AI
        result = await quote_service.extract_quote_assumptions(
            quote_text=text, project_name=project_name
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract quote assumptions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to extract quote: {str(e)}"
        )


@router.post("/compare", response_model=ComparisonResult)
async def compare_quote_with_checklist(request: ComparisonRequest):
    """
    Compare quote assumptions against checklist requirements

    **Input:**
    - `quote_assumptions`: Output from /extract endpoint
    - `checklist`: Checklist result from /api/checklist endpoint

    **Output identifies:**
    - **Matches**: Quote assumptions that align with customer requirements
    - **Conflicts**: Quote contradicts customer requirements (flagged by severity)
    - **Quote-only**: Assumptions in quote not in customer docs
    - **Checklist-only**: Customer requirements not addressed in quote

    **Critical for:**
    - Identifying specification mismatches before manufacturing
    - Ensuring vendor understands all customer requirements
    - Catching welding code, material, or testing conflicts early
    """
    try:
        result = await quote_service.compare_with_checklist(
            quote_assumptions=request.quote_assumptions,
            checklist=request.checklist,
        )
        return result

    except Exception as e:
        logger.error(f"Failed to compare quote: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/merge-preview")
async def generate_merge_preview(request: MergePreviewRequest):
    """
    Generate a preview of checklist merged with quote information

    **Shows:**
    - Checklist items with conflict highlights (red)
    - Items where quote matches (green)
    - Quote additions that could be added
    - Unaddressed requirements that need vendor confirmation

    **Use this to:**
    - Review before publishing to Confluence
    - Identify what needs discussion with vendor
    - See final checklist state after merge
    """
    try:
        result = await quote_service.generate_merge_preview(
            checklist=request.checklist,
            quote_assumptions=request.quote_assumptions,
            comparison=request.comparison,
        )
        return result

    except Exception as e:
        logger.error(f"Failed to generate merge preview: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Merge preview failed: {str(e)}"
        )


@router.post("/full-workflow")
async def full_quote_comparison_workflow(
    quote_file: UploadFile = File(..., description="Quote PDF file"),
    checklist: str = Form(..., description="Checklist JSON as string"),
    project_name: str = Form(None, description="Project name"),
):
    """
    Run the complete quote comparison workflow in one call

    **Steps:**
    1. Extract assumptions from quote PDF
    2. Compare against provided checklist
    3. Generate merge preview

    **Returns all results:**
    - Extracted quote assumptions
    - Comparison results with conflicts
    - Merge preview

    This is a convenience endpoint that combines /extract, /compare,
    and /merge-preview into a single call.
    """
    import json

    try:
        # Parse checklist JSON
        try:
            checklist_data = json.loads(checklist)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid checklist JSON")

        # Step 1: Extract quote
        content = await quote_file.read()
        filename = quote_file.filename or "quote.pdf"
        text = doc_processor.extract_text(content, filename)

        if not text:
            raise HTTPException(
                status_code=400, detail="Could not extract text from quote PDF"
            )

        quote_assumptions = await quote_service.extract_quote_assumptions(
            quote_text=text, project_name=project_name
        )

        # Step 2: Compare
        comparison = await quote_service.compare_with_checklist(
            quote_assumptions=quote_assumptions, checklist=checklist_data
        )

        # Step 3: Merge preview
        merge_preview = await quote_service.generate_merge_preview(
            checklist=checklist_data,
            quote_assumptions=quote_assumptions,
            comparison=comparison,
        )

        return {
            "quote_assumptions": quote_assumptions,
            "comparison": comparison,
            "merge_preview": merge_preview,
            "workflow_complete": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full workflow failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")
