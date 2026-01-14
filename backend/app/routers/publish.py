"""
Publish Router - Confluence Publishing for Strategic Build Plans
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.services.confluence import ConfluenceService
from app.models.responses import PublishRequest, PublishResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/publish", response_model=PublishResponse)
async def publish_to_confluence(request: PublishRequest):
    """
    Publish a Strategic Build Plan to Confluence

    **Process:**
    1. Search for Family of Parts parent page by label
    2. Convert plan JSON to Confluence storage format (HTML)
    3. Create new page under the parent
    4. Return Confluence page URL

    **Prerequisites:**
    - Confluence credentials configured in .env
    - Family of Parts page must exist with label `family-of-parts-{slug}`

    **Page Hierarchy:**
    ```
    Space (e.g., OPS)
    └── Customer
        └── Family of Parts (parent - found by label)
            └── Strategic Build Plan - {project_name} (created)
    ```
    """
    try:
        logger.info(
            f"Publishing plan to Confluence: {request.project_name}, "
            f"customer: {request.customer}, "
            f"family: {request.family_of_parts}"
        )

        # Initialize Confluence service
        confluence = ConfluenceService()

        # Find parent page (Family of Parts)
        parent_page = await confluence.find_family_of_parts_page(
            request.family_of_parts
        )

        parent_id = None
        if parent_page:
            parent_id = parent_page["id"]
            logger.info(f"Found parent page: {parent_page['title']} ({parent_id})")
        else:
            logger.warning(
                f"No Family of Parts page found for '{request.family_of_parts}'. "
                f"Creating page at space root."
            )

        # Use provided parent_page_id if specified (override auto-detection)
        if request.parent_page_id:
            parent_id = request.parent_page_id
            logger.info(f"Using explicitly provided parent_page_id: {parent_id}")

        # Convert plan to Confluence storage format
        plan_content = confluence.plan_to_confluence_storage(request.plan_json)

        # Generate page title
        page_title = f"Strategic Build Plan - {request.project_name}"

        # Create the page
        result = await confluence.create_page(
            title=page_title,
            content=plan_content,
            parent_id=parent_id
        )

        logger.info(
            f"Successfully published to Confluence: {result['title']} "
            f"({result['id']}) - {result['url']}"
        )

        return PublishResponse(
            page_id=result["id"],
            page_url=result["url"],
            page_title=result["title"],
            published_at=datetime.utcnow()
        )

    except ValueError as e:
        # Confluence not configured
        logger.error(f"Confluence configuration error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Confluence publish failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish to Confluence: {str(e)}"
        )


@router.put("/publish/{page_id}", response_model=PublishResponse)
async def update_confluence_page(page_id: str, request: PublishRequest):
    """
    Update an existing Strategic Build Plan page in Confluence

    **Process:**
    1. Convert updated plan JSON to Confluence storage format
    2. Update the existing page
    3. Return updated page URL

    **Prerequisites:**
    - Page must already exist in Confluence
    - Confluence credentials configured in .env
    """
    try:
        logger.info(f"Updating Confluence page: {page_id}")

        # Initialize Confluence service
        confluence = ConfluenceService()

        # Convert plan to Confluence storage format
        plan_content = confluence.plan_to_confluence_storage(request.plan_json)

        # Generate page title
        page_title = f"Strategic Build Plan - {request.project_name}"

        # Update the page
        result = await confluence.update_page(
            page_id=page_id,
            title=page_title,
            content=plan_content
        )

        logger.info(
            f"Successfully updated Confluence page: {result['title']} "
            f"({result['id']}) - version {result.get('version')}"
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
        logger.error(f"Confluence update failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Confluence page: {str(e)}"
        )


@router.get("/publish/search")
async def search_confluence_pages(
    query: str,
    limit: int = 10
):
    """
    Search Confluence pages using CQL

    **Example queries:**
    - `space = OPS AND type = page`
    - `label = "family-of-parts-brackets"`
    - `title ~ "Strategic Build Plan"`

    **Returns:**
    List of matching pages with id, title, url
    """
    try:
        confluence = ConfluenceService()
        pages = await confluence.search_pages(query, limit=limit)

        return {
            "query": query,
            "count": len(pages),
            "pages": pages
        }

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Confluence search failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
