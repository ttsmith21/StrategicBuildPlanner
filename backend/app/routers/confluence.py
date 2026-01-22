"""
Confluence Router - Search, Navigation, and Page Management API

Provides endpoints for:
- Searching pages by job number (e.g., F12345)
- Browsing the Confluence hierarchy (Customer → Family → Project)
- Reading page content for context
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.confluence import ConfluenceService

router = APIRouter(prefix="/api/confluence", tags=["confluence"])

# Initialize service
confluence_service = ConfluenceService()


# ============================================================================
# Response Models
# ============================================================================


class PageSummary(BaseModel):
    """Summary of a Confluence page"""

    id: str
    title: str
    url: str
    space_key: Optional[str] = None


class HierarchyPage(BaseModel):
    """Page in hierarchy with children indicator"""

    id: str
    title: str
    url: str
    has_children: bool
    type: str  # customer, family, project, unknown


class PageWithAncestors(BaseModel):
    """Full page with content and ancestor chain"""

    id: str
    title: str
    content: str
    version: int
    url: str
    ancestors: List[dict]


class PageContent(BaseModel):
    """Page content (HTML and text)"""

    id: str
    title: str
    content_html: str
    content_text: str
    version: int


# ============================================================================
# Search Endpoints
# ============================================================================


@router.get("/search", response_model=List[PageSummary])
async def search_pages(
    q: str = Query(
        ..., description="Search query (job number like F12345, or keywords)"
    ),
    space: str = Query("KB", description="Confluence space key"),
):
    """
    Search for Confluence pages by job number or keywords

    **Examples:**
    - `/api/confluence/search?q=F12345` - Find pages for job F12345
    - `/api/confluence/search?q=Acme%20Corp` - Search for customer name
    - `/api/confluence/search?q=brackets&space=KB` - Search in Knowledge Base

    Returns matching pages with ID, title, and URL.
    """
    try:
        results = await confluence_service.search_by_job_number(q, space_key=space)
        return results
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ============================================================================
# Hierarchy Browsing Endpoints
# ============================================================================


@router.get("/hierarchy", response_model=List[HierarchyPage])
async def get_hierarchy(
    parent_id: Optional[str] = Query(
        None, description="Parent page ID. Omit for top-level pages."
    ),
    space: str = Query("KB", description="Confluence space key"),
):
    """
    Browse Confluence page hierarchy

    **Usage:**
    1. Call without parent_id to get top-level pages (Customers)
    2. Call with parent_id to get children (Family of Parts → Projects)

    **Response includes:**
    - `has_children`: Whether the page can be expanded
    - `type`: Inferred type (customer/family/project/unknown)

    **Example flow:**
    ```
    GET /hierarchy              → [Acme Corp, Beta Industries, ...]
    GET /hierarchy?parent_id=123 → [Brackets Family, Enclosures Family, ...]
    GET /hierarchy?parent_id=456 → [F12345 - Widget Project, F12346, ...]
    ```
    """
    try:
        pages = await confluence_service.get_space_hierarchy(
            space_key=space, parent_id=parent_id
        )
        return pages
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get hierarchy: {str(e)}"
        )


# ============================================================================
# Page Content Endpoints
# ============================================================================


@router.get("/page/{page_id}", response_model=PageWithAncestors)
async def get_page(page_id: str):
    """
    Get a Confluence page with its content and ancestor chain

    **Returns:**
    - Page content in Confluence storage format (HTML)
    - Version number for update operations
    - Ancestors: Parent pages up to the root (for context)

    **Use cases:**
    - Load existing checklist for editing
    - Get context from Customer/Family pages
    - Read project requirements before generating checklist
    """
    try:
        page = await confluence_service.get_page_with_ancestors(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page {page_id} not found")
        return page
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get page: {str(e)}")


@router.get("/page/{page_id}/text")
async def get_page_text(page_id: str):
    """
    Get page content as plain text (for AI analysis)

    Strips HTML tags from Confluence storage format.
    Useful for:
    - Feeding existing page content to AI for context
    - Extracting requirements from Customer/Family pages
    """
    try:
        text = await confluence_service.get_page_content_text(page_id)
        if text is None:
            raise HTTPException(status_code=404, detail=f"Page {page_id} not found")
        return {"page_id": page_id, "text": text}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get page text: {str(e)}"
        )


@router.get("/page/{page_id}/context")
async def get_page_context(page_id: str):
    """
    Get full context for a project page: the page plus all ancestor content

    **Returns content from:**
    - The project page itself
    - Family of Parts parent page
    - Customer parent page

    **Use case:**
    When generating a checklist, this provides all the context about
    customer requirements, family-level standards, and project-specific info.
    """
    try:
        # Get page with ancestors
        page = await confluence_service.get_page_with_ancestors(page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page {page_id} not found")

        context = {
            "project": {
                "id": page["id"],
                "title": page["title"],
                "text": await confluence_service.get_page_content_text(page_id),
            },
            "ancestors": [],
        }

        # Get text content for each ancestor
        for ancestor in page.get("ancestors", []):
            ancestor_text = await confluence_service.get_page_content_text(
                ancestor["id"]
            )
            context["ancestors"].append(
                {
                    "id": ancestor["id"],
                    "title": ancestor["title"],
                    "text": ancestor_text,
                }
            )

        return context

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get page context: {str(e)}"
        )
