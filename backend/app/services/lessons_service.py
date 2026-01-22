"""
Lessons Learned Service - Extract insights from historical Confluence pages
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.services.confluence import ConfluenceService
from app.prompts.lessons_prompt import LESSONS_SYSTEM_PROMPT, build_lessons_prompt

logger = logging.getLogger(__name__)


class LessonsService:
    """Service for extracting lessons learned from historical Confluence documentation"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            logger.warning(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable to enable lessons extraction."
            )
            self.openai_client = None
        self.confluence_service = ConfluenceService()
        self.model = os.getenv("OPENAI_LESSONS_MODEL", "gpt-4o")
        self.max_content_tokens = 8000  # Truncate content to avoid token limits

    def _ensure_openai_client(self):
        """Ensure OpenAI client is initialized"""
        if not self.openai_client:
            raise ValueError(
                "OpenAI client not configured. "
                "Please set OPENAI_API_KEY environment variable."
            )

    async def extract_lessons(
        self,
        page_id: str,
        checklist: Dict[str, Any],
        max_siblings: int = 3,
    ) -> Dict[str, Any]:
        """
        Extract lessons learned from historical pages related to a project.

        Args:
            page_id: Confluence page ID of the current project
            checklist: Current project checklist (for context)
            max_siblings: Maximum number of sibling pages to analyze

        Returns:
            Dict with insights, sibling_pages_analyzed, family_page, customer_page,
            skipped, skip_reason
        """
        try:
            # Get page with ancestors to understand hierarchy
            page = await self.confluence_service.get_page_with_ancestors(page_id)
            if not page:
                return self._skipped_response("Page not found")

            ancestors = page.get("ancestors", [])
            if not ancestors:
                return self._skipped_response(
                    "No parent pages found - cannot determine hierarchy"
                )

            # Identify family page (immediate parent) and customer page (grandparent)
            # Ancestors are ordered from root to immediate parent
            family_page = None
            customer_page = None

            if len(ancestors) >= 1:
                # Last ancestor is the immediate parent (family page)
                family_page = ancestors[-1]

            if len(ancestors) >= 2:
                # Second to last is the grandparent (customer page)
                customer_page = ancestors[-2]

            # Get sibling pages (other children of the family page)
            sibling_pages = []
            if family_page:
                sibling_pages = await self._get_sibling_pages(
                    family_page["id"], page_id, max_siblings
                )

            # If no siblings and no family content, skip
            if not sibling_pages and not family_page:
                return self._skipped_response(
                    "No historical data available for this project"
                )

            # Fetch content for analysis
            sibling_content = []
            for sibling in sibling_pages:
                content = await self.confluence_service.get_page_content_text(
                    sibling["id"]
                )
                if content:
                    sibling_content.append(
                        {
                            "id": sibling["id"],
                            "title": sibling["title"],
                            "content": self._truncate_content(content),
                        }
                    )

            family_content = None
            family_page_info = None
            if family_page:
                content = await self.confluence_service.get_page_content_text(
                    family_page["id"]
                )
                if content:
                    family_content = self._truncate_content(content)
                    family_page_info = {
                        "id": family_page["id"],
                        "title": family_page.get("title", "Unknown"),
                    }

            customer_content = None
            customer_page_info = None
            if customer_page:
                content = await self.confluence_service.get_page_content_text(
                    customer_page["id"]
                )
                if content:
                    customer_content = self._truncate_content(content)
                    customer_page_info = {
                        "id": customer_page["id"],
                        "title": customer_page.get("title", "Unknown"),
                    }

            # Check if we have any content to analyze
            if not sibling_content and not family_content and not customer_content:
                return self._skipped_response("No content found in related pages")

            # Extract checklist categories
            checklist_categories = []
            if checklist and "categories" in checklist:
                checklist_categories = [
                    cat.get("name", "") for cat in checklist.get("categories", [])
                ]

            # Build project context
            project_context = f"Project: {page.get('title', 'Unknown')}"
            if checklist:
                project_context += f"\nCustomer: {checklist.get('customer', 'Unknown')}"
                project_context += (
                    f"\nProject Name: {checklist.get('project_name', 'Unknown')}"
                )

            # Run AI analysis
            insights = await self._run_ai_analysis(
                project_context=project_context,
                checklist_categories=checklist_categories,
                sibling_content=sibling_content,
                family_content=family_content,
                customer_content=customer_content,
            )

            return {
                "insights": insights,
                "sibling_pages_analyzed": [
                    {"id": s["id"], "title": s["title"]} for s in sibling_content
                ],
                "family_page": family_page_info,
                "customer_page": customer_page_info,
                "skipped": False,
                "skip_reason": None,
            }

        except Exception as e:
            logger.error(f"Error extracting lessons: {str(e)}")
            return self._skipped_response(f"Error during extraction: {str(e)}")

    async def _get_sibling_pages(
        self,
        family_page_id: str,
        current_page_id: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get sibling pages (other children of the family page).

        Args:
            family_page_id: ID of the parent (family) page
            current_page_id: ID of current page to exclude
            limit: Maximum number of siblings to return

        Returns:
            List of sibling page dicts with id, title
        """
        try:
            # Get all children of the family page
            children = await self.confluence_service.get_space_hierarchy(
                parent_id=family_page_id
            )

            # Filter out the current page and take top N
            siblings = [
                child for child in children if child.get("id") != current_page_id
            ]

            # Sort by title (could sort by modified date if available)
            siblings.sort(key=lambda x: x.get("title", ""), reverse=True)

            return siblings[:limit]

        except Exception as e:
            logger.warning(f"Error getting sibling pages: {str(e)}")
            return []

    async def _run_ai_analysis(
        self,
        project_context: str,
        checklist_categories: List[str],
        sibling_content: List[Dict],
        family_content: Optional[str],
        customer_content: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Run AI analysis to extract lessons learned.

        Returns:
            List of insight dicts
        """
        self._ensure_openai_client()

        try:
            user_prompt = build_lessons_prompt(
                project_context=project_context,
                checklist_categories=checklist_categories,
                sibling_content=sibling_content,
                family_content=family_content,
                customer_content=customer_content,
            )

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": LESSONS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=4000,
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            insights = result.get("insights", [])

            # Add unique IDs to each insight
            for i, insight in enumerate(insights):
                insight["id"] = f"insight_{i}"
                # Ensure all required fields exist
                insight.setdefault("category", "Best Practice")
                insight.setdefault("title", "Untitled Insight")
                insight.setdefault("description", "")
                insight.setdefault("recommendation", "")
                insight.setdefault("source_excerpt", "")
                insight.setdefault("relevance_score", 0.5)

            # Sort by relevance score
            insights.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

            logger.info(f"Extracted {len(insights)} lessons learned")
            return insights

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return []

    def _truncate_content(self, content: str) -> str:
        """Truncate content to avoid token limits (rough estimate: 4 chars = 1 token)"""
        max_chars = self.max_content_tokens * 4
        if len(content) > max_chars:
            return content[:max_chars] + "\n\n[Content truncated...]"
        return content

    def _skipped_response(self, reason: str) -> Dict[str, Any]:
        """Generate a skipped response"""
        return {
            "insights": [],
            "sibling_pages_analyzed": [],
            "family_page": None,
            "customer_page": None,
            "skipped": True,
            "skip_reason": reason,
        }
