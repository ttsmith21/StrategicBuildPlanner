"""
Confluence Service - API Integration for Publishing Strategic Build Plans
"""

import os
import re
import logging
from typing import List, Optional, Dict, Any
from atlassian import Confluence

logger = logging.getLogger(__name__)


class ConfluenceService:
    """Service for interacting with Confluence Cloud API"""

    def __init__(self):
        self.url = os.getenv("CONFLUENCE_URL")
        self.email = os.getenv("CONFLUENCE_EMAIL")
        self.token = os.getenv("CONFLUENCE_API_TOKEN")
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "OPS")

        if not all([self.url, self.email, self.token]):
            logger.warning(
                "Confluence credentials not fully configured. "
                "Set CONFLUENCE_URL, CONFLUENCE_EMAIL, and CONFLUENCE_API_TOKEN."
            )
            self.client = None
        else:
            self.client = Confluence(
                url=self.url,
                username=self.email,
                password=self.token,
                cloud=True
            )
            logger.info(f"Confluence client initialized for {self.url}")

    def _ensure_client(self):
        """Ensure Confluence client is initialized"""
        if not self.client:
            raise ValueError(
                "Confluence client not configured. "
                "Please set CONFLUENCE_URL, CONFLUENCE_EMAIL, and CONFLUENCE_API_TOKEN."
            )

    async def search_pages(
        self,
        cql_query: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for Confluence pages using CQL

        Args:
            cql_query: CQL query string (e.g., 'space = KB AND label = "family-of-parts"')
            limit: Maximum results to return

        Returns:
            List of page dictionaries with id, title, url
        """
        self._ensure_client()

        try:
            results = self.client.cql(cql_query, limit=limit)
            pages = []

            for result in results.get("results", []):
                content = result.get("content", result)
                page_id = content.get("id")
                title = content.get("title")

                # Build page URL
                page_url = f"{self.url}/wiki/spaces/{self.space_key}/pages/{page_id}"

                pages.append({
                    "id": page_id,
                    "title": title,
                    "url": page_url,
                    "space_key": content.get("space", {}).get("key", self.space_key)
                })

            logger.info(f"CQL search found {len(pages)} pages: {cql_query}")
            return pages

        except Exception as e:
            logger.error(f"Confluence search failed: {str(e)}")
            raise

    async def find_family_of_parts_page(
        self,
        family_of_parts: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the Family of Parts parent page by label

        Args:
            family_of_parts: Family name (e.g., "Structural Brackets")

        Returns:
            Page dict with id, title, url or None if not found
        """
        # Convert to slug format for label
        slug = self._to_slug(family_of_parts)
        label = f"family-of-parts-{slug}"

        cql = f'space = "{self.space_key}" AND label = "{label}" AND type = page'
        logger.info(f"Searching for Family of Parts page with label: {label}")

        pages = await self.search_pages(cql, limit=1)

        if pages:
            logger.info(f"Found Family of Parts page: {pages[0]['title']} ({pages[0]['id']})")
            return pages[0]

        logger.warning(f"No Family of Parts page found with label: {label}")
        return None

    async def create_page(
        self,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Confluence page

        Args:
            title: Page title
            content: Page content in Confluence storage format (HTML/XHTML)
            parent_id: Optional parent page ID
            space_key: Space key (defaults to configured space)

        Returns:
            Dict with page id, title, url
        """
        self._ensure_client()
        space = space_key or self.space_key

        try:
            result = self.client.create_page(
                space=space,
                title=title,
                body=content,
                parent_id=parent_id,
                type="page",
                representation="storage"
            )

            page_id = result.get("id")
            page_url = f"{self.url}/wiki/spaces/{space}/pages/{page_id}"

            logger.info(f"Created Confluence page: {title} ({page_id})")

            return {
                "id": page_id,
                "title": result.get("title"),
                "url": page_url,
                "version": result.get("version", {}).get("number", 1)
            }

        except Exception as e:
            logger.error(f"Failed to create Confluence page: {str(e)}")
            raise

    async def update_page(
        self,
        page_id: str,
        title: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Update an existing Confluence page

        Args:
            page_id: Page ID to update
            title: New page title
            content: New content in storage format

        Returns:
            Dict with page id, title, url, version
        """
        self._ensure_client()

        try:
            result = self.client.update_page(
                page_id=page_id,
                title=title,
                body=content,
                representation="storage"
            )

            page_url = f"{self.url}/wiki/spaces/{self.space_key}/pages/{page_id}"

            logger.info(f"Updated Confluence page: {title} ({page_id})")

            return {
                "id": page_id,
                "title": result.get("title"),
                "url": page_url,
                "version": result.get("version", {}).get("number")
            }

        except Exception as e:
            logger.error(f"Failed to update Confluence page: {str(e)}")
            raise

    async def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a Confluence page by ID

        Args:
            page_id: Page ID

        Returns:
            Page dict or None if not found
        """
        self._ensure_client()

        try:
            result = self.client.get_page_by_id(
                page_id=page_id,
                expand="body.storage,version"
            )

            if result:
                return {
                    "id": result.get("id"),
                    "title": result.get("title"),
                    "content": result.get("body", {}).get("storage", {}).get("value", ""),
                    "version": result.get("version", {}).get("number", 1)
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get Confluence page {page_id}: {str(e)}")
            return None

    def plan_to_confluence_storage(self, plan: Dict[str, Any]) -> str:
        """
        Convert Strategic Build Plan JSON to Confluence storage format (HTML)

        Args:
            plan: Plan dictionary

        Returns:
            Confluence storage format HTML string
        """
        html_parts = []

        # Header with metadata
        html_parts.append(f"""
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p><strong>Customer:</strong> {self._escape_html(plan.get('customer', 'Unknown'))}</p>
    <p><strong>Family of Parts:</strong> {self._escape_html(plan.get('family_of_parts', 'Unknown'))}</p>
    <p><strong>Generated:</strong> {plan.get('generated_at', 'Unknown')}</p>
  </ac:rich-text-body>
</ac:structured-macro>
""")

        # Keys to Project
        html_parts.append(self._render_section(
            "Keys to Project",
            plan.get("keys_to_project", [])
        ))

        # Quality Plan
        quality = plan.get("quality_plan", {})
        html_parts.append("<h2>Quality Plan</h2>")
        if quality.get("control_plan_items"):
            html_parts.append(self._render_subsection("Control Plan Items", quality["control_plan_items"]))
        if quality.get("inspection_strategy"):
            html_parts.append(self._render_subsection("Inspection Strategy", quality["inspection_strategy"]))
        if quality.get("quality_metrics"):
            html_parts.append(self._render_subsection("Quality Metrics", quality["quality_metrics"]))
        if quality.get("ppap_requirements"):
            html_parts.append(self._render_subsection("PPAP Requirements", quality["ppap_requirements"]))

        # Purchasing
        purchasing = plan.get("purchasing", {})
        html_parts.append("<h2>Purchasing</h2>")
        if purchasing.get("raw_materials"):
            html_parts.append(self._render_subsection("Raw Materials", purchasing["raw_materials"]))
        if purchasing.get("suppliers"):
            html_parts.append(self._render_subsection("Suppliers", purchasing["suppliers"]))
        if purchasing.get("lead_times"):
            html_parts.append(self._render_subsection("Lead Times", purchasing["lead_times"]))
        if purchasing.get("cost_estimates"):
            html_parts.append(self._render_subsection("Cost Estimates", purchasing["cost_estimates"]))

        # History Review
        history = plan.get("history_review", {})
        html_parts.append("<h2>History Review</h2>")
        if history.get("previous_projects"):
            html_parts.append(self._render_subsection("Previous Projects", history["previous_projects"]))
        if history.get("lessons_learned"):
            html_parts.append(self._render_subsection("Lessons Learned", history["lessons_learned"]))
        if history.get("recurring_issues"):
            html_parts.append(self._render_subsection("Recurring Issues", history["recurring_issues"]))

        # Build Strategy
        build = plan.get("build_strategy", {})
        html_parts.append("<h2>Build Strategy</h2>")
        if build.get("manufacturing_process"):
            html_parts.append(self._render_subsection("Manufacturing Process", build["manufacturing_process"]))
        if build.get("tooling_requirements"):
            html_parts.append(self._render_subsection("Tooling Requirements", build["tooling_requirements"]))
        if build.get("capacity_planning"):
            html_parts.append(self._render_subsection("Capacity Planning", build["capacity_planning"]))
        if build.get("make_vs_buy_decisions"):
            html_parts.append(self._render_subsection("Make vs. Buy Decisions", build["make_vs_buy_decisions"]))

        # Execution Strategy
        execution = plan.get("execution_strategy", {})
        html_parts.append("<h2>Execution Strategy</h2>")
        if execution.get("timeline"):
            html_parts.append(self._render_subsection("Timeline", execution["timeline"]))
        if execution.get("milestones"):
            html_parts.append(self._render_subsection("Milestones", execution["milestones"]))
        if execution.get("resource_allocation"):
            html_parts.append(self._render_subsection("Resource Allocation", execution["resource_allocation"]))
        if execution.get("risk_mitigation"):
            html_parts.append(self._render_subsection("Risk Mitigation", execution["risk_mitigation"]))

        # Release Plan
        release = plan.get("release_plan", {})
        html_parts.append("<h2>Release Plan</h2>")
        if release.get("release_criteria"):
            html_parts.append(self._render_subsection("Release Criteria", release["release_criteria"]))
        if release.get("validation_steps"):
            html_parts.append(self._render_subsection("Validation Steps", release["validation_steps"]))
        if release.get("production_ramp"):
            html_parts.append(self._render_subsection("Production Ramp", release["production_ramp"]))

        # Shipping
        shipping = plan.get("shipping", {})
        html_parts.append("<h2>Shipping</h2>")
        if shipping.get("packaging_requirements"):
            html_parts.append(self._render_subsection("Packaging Requirements", shipping["packaging_requirements"]))
        if shipping.get("shipping_methods"):
            html_parts.append(self._render_subsection("Shipping Methods", shipping["shipping_methods"]))
        if shipping.get("delivery_schedule"):
            html_parts.append(self._render_subsection("Delivery Schedule", shipping["delivery_schedule"]))

        # Action Items
        asana_todos = plan.get("asana_todos", [])
        if asana_todos:
            html_parts.append("<h2>Action Items</h2>")
            html_parts.append(self._render_action_items(asana_todos))

        # Notes
        apqp_notes = plan.get("apqp_notes", [])
        if apqp_notes:
            html_parts.append("<h2>APQP Notes</h2>")
            html_parts.append(self._render_notes(apqp_notes))

        meeting_notes = plan.get("customer_meeting_notes", [])
        if meeting_notes:
            html_parts.append("<h2>Customer Meeting Notes</h2>")
            html_parts.append(self._render_notes(meeting_notes))

        # Footer
        html_parts.append("""
<hr/>
<p><em>Generated by Strategic Build Planner - Northern Manufacturing Co., Inc.</em></p>
""")

        return "\n".join(html_parts)

    def _render_section(self, title: str, key_points: List[Dict]) -> str:
        """Render a main section with key points"""
        html = f"<h2>{self._escape_html(title)}</h2>\n"
        html += self._render_key_points(key_points)
        return html

    def _render_subsection(self, title: str, key_points: List[Dict]) -> str:
        """Render a subsection with key points"""
        html = f"<h3>{self._escape_html(title)}</h3>\n"
        html += self._render_key_points(key_points)
        return html

    def _render_key_points(self, key_points: List[Dict]) -> str:
        """Render a list of key points as HTML"""
        if not key_points:
            return "<p><em>No items recorded.</em></p>\n"

        html = "<ul>\n"
        for kp in key_points:
            text = self._escape_html(kp.get("text", ""))
            confidence = kp.get("confidence", 0)
            confidence_level = kp.get("confidence_level", "unknown")

            # Status macro based on confidence
            if confidence >= 0.8:
                status = "Green"
            elif confidence >= 0.5:
                status = "Yellow"
            else:
                status = "Red"

            html += f"""<li>
  <ac:structured-macro ac:name="status">
    <ac:parameter ac:name="colour">{status}</ac:parameter>
  </ac:structured-macro>
  {text}"""

            # Add source hint if available
            source = kp.get("source_hint")
            if source:
                source_parts = []
                if source.get("document"):
                    source_parts.append(source["document"])
                if source.get("page"):
                    source_parts.append(f"pg. {source['page']}")
                if source.get("section"):
                    source_parts.append(f"§{source['section']}")
                if source_parts:
                    html += f" <em>({', '.join(source_parts)} - {confidence:.0%})</em>"

            html += "</li>\n"

        html += "</ul>\n"
        return html

    def _render_action_items(self, tasks: List[Dict]) -> str:
        """Render action items as a task list"""
        html = '<ac:task-list>\n'

        for task in tasks:
            title = self._escape_html(task.get("title", "Task"))
            description = self._escape_html(task.get("description", ""))
            priority = task.get("priority", "medium")

            priority_label = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(priority, "MEDIUM")

            html += f"""<ac:task>
  <ac:task-status>incomplete</ac:task-status>
  <ac:task-body><strong>[{priority_label}]</strong> {title}"""

            if description:
                html += f" - {description}"

            if task.get("assignee_hint"):
                html += f" <em>(@{self._escape_html(task['assignee_hint'])})</em>"

            if task.get("due_date_hint"):
                html += f" <em>(Due: {self._escape_html(task['due_date_hint'])})</em>"

            html += "</ac:task-body>\n</ac:task>\n"

        html += "</ac:task-list>\n"
        return html

    def _render_notes(self, notes: List[Dict]) -> str:
        """Render notes section"""
        html = ""
        for note in notes:
            timestamp = note.get("timestamp", "")
            content = self._escape_html(note.get("content", ""))

            if timestamp:
                html += f"<p><strong>{timestamp}</strong></p>\n"
            html += f"<p>{content}</p>\n"

            action_items = note.get("action_items", [])
            if action_items:
                html += "<ul>\n"
                for item in action_items:
                    html += f"<li>{self._escape_html(item)}</li>\n"
                html += "</ul>\n"

        return html

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _to_slug(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')
