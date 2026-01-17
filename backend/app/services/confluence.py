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
        # Support both CONFLUENCE_URL and CONFLUENCE_BASE_URL for compatibility
        self.url = os.getenv("CONFLUENCE_URL") or os.getenv("CONFLUENCE_BASE_URL")
        self.email = os.getenv("CONFLUENCE_EMAIL")
        self.token = os.getenv("CONFLUENCE_API_TOKEN")
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "KB")

        if not all([self.url, self.email, self.token]):
            logger.warning(
                "Confluence credentials not fully configured. "
                "Set CONFLUENCE_URL (or CONFLUENCE_BASE_URL), CONFLUENCE_EMAIL, and CONFLUENCE_API_TOKEN."
            )
            self.client = None
        else:
            self.client = Confluence(
                url=self.url, username=self.email, password=self.token, cloud=True
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
        self, cql_query: str, limit: int = 25
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
                page_url = f"{self.url}/spaces/{self.space_key}/pages/{page_id}"

                pages.append(
                    {
                        "id": page_id,
                        "title": title,
                        "url": page_url,
                        "space_key": content.get("space", {}).get(
                            "key", self.space_key
                        ),
                    }
                )

            logger.info(f"CQL search found {len(pages)} pages: {cql_query}")
            return pages

        except Exception as e:
            logger.error(f"Confluence search failed: {str(e)}")
            raise

    async def find_family_of_parts_page(
        self, family_of_parts: str
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
            logger.info(
                f"Found Family of Parts page: {pages[0]['title']} ({pages[0]['id']})"
            )
            return pages[0]

        logger.warning(f"No Family of Parts page found with label: {label}")
        return None

    async def create_page(
        self,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None,
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
                representation="storage",
            )

            page_id = result.get("id")
            page_url = f"{self.url}/spaces/{space}/pages/{page_id}"

            logger.info(f"Created Confluence page: {title} ({page_id})")

            return {
                "id": page_id,
                "title": result.get("title"),
                "url": page_url,
                "version": result.get("version", {}).get("number", 1),
            }

        except Exception as e:
            logger.error(f"Failed to create Confluence page: {str(e)}")
            raise

    async def update_page(
        self, page_id: str, title: str, content: str
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
                page_id=page_id, title=title, body=content, representation="storage"
            )

            page_url = f"{self.url}/spaces/{self.space_key}/pages/{page_id}"

            logger.info(f"Updated Confluence page: {title} ({page_id})")

            return {
                "id": page_id,
                "title": result.get("title"),
                "url": page_url,
                "version": result.get("version", {}).get("number"),
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
                page_id=page_id, expand="body.storage,version"
            )

            if result:
                return {
                    "id": result.get("id"),
                    "title": result.get("title"),
                    "content": result.get("body", {})
                    .get("storage", {})
                    .get("value", ""),
                    "version": result.get("version", {}).get("number", 1),
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
        html_parts.append(
            f"""
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p><strong>Customer:</strong> {self._escape_html(plan.get('customer', 'Unknown'))}</p>
    <p><strong>Family of Parts:</strong> {self._escape_html(plan.get('family_of_parts', 'Unknown'))}</p>
    <p><strong>Generated:</strong> {plan.get('generated_at', 'Unknown')}</p>
  </ac:rich-text-body>
</ac:structured-macro>
"""
        )

        # Keys to Project
        html_parts.append(
            self._render_section("Keys to Project", plan.get("keys_to_project", []))
        )

        # Quality Plan
        quality = plan.get("quality_plan", {})
        html_parts.append("<h2>Quality Plan</h2>")
        if quality.get("control_plan_items"):
            html_parts.append(
                self._render_subsection(
                    "Control Plan Items", quality["control_plan_items"]
                )
            )
        if quality.get("inspection_strategy"):
            html_parts.append(
                self._render_subsection(
                    "Inspection Strategy", quality["inspection_strategy"]
                )
            )
        if quality.get("quality_metrics"):
            html_parts.append(
                self._render_subsection("Quality Metrics", quality["quality_metrics"])
            )
        if quality.get("ppap_requirements"):
            html_parts.append(
                self._render_subsection(
                    "PPAP Requirements", quality["ppap_requirements"]
                )
            )

        # Purchasing
        purchasing = plan.get("purchasing", {})
        html_parts.append("<h2>Purchasing</h2>")
        if purchasing.get("raw_materials"):
            html_parts.append(
                self._render_subsection("Raw Materials", purchasing["raw_materials"])
            )
        if purchasing.get("suppliers"):
            html_parts.append(
                self._render_subsection("Suppliers", purchasing["suppliers"])
            )
        if purchasing.get("lead_times"):
            html_parts.append(
                self._render_subsection("Lead Times", purchasing["lead_times"])
            )
        if purchasing.get("cost_estimates"):
            html_parts.append(
                self._render_subsection("Cost Estimates", purchasing["cost_estimates"])
            )

        # History Review
        history = plan.get("history_review", {})
        html_parts.append("<h2>History Review</h2>")
        if history.get("previous_projects"):
            html_parts.append(
                self._render_subsection(
                    "Previous Projects", history["previous_projects"]
                )
            )
        if history.get("lessons_learned"):
            html_parts.append(
                self._render_subsection("Lessons Learned", history["lessons_learned"])
            )
        if history.get("recurring_issues"):
            html_parts.append(
                self._render_subsection("Recurring Issues", history["recurring_issues"])
            )

        # Build Strategy
        build = plan.get("build_strategy", {})
        html_parts.append("<h2>Build Strategy</h2>")
        if build.get("manufacturing_process"):
            html_parts.append(
                self._render_subsection(
                    "Manufacturing Process", build["manufacturing_process"]
                )
            )
        if build.get("tooling_requirements"):
            html_parts.append(
                self._render_subsection(
                    "Tooling Requirements", build["tooling_requirements"]
                )
            )
        if build.get("capacity_planning"):
            html_parts.append(
                self._render_subsection("Capacity Planning", build["capacity_planning"])
            )
        if build.get("make_vs_buy_decisions"):
            html_parts.append(
                self._render_subsection(
                    "Make vs. Buy Decisions", build["make_vs_buy_decisions"]
                )
            )

        # Execution Strategy
        execution = plan.get("execution_strategy", {})
        html_parts.append("<h2>Execution Strategy</h2>")
        if execution.get("timeline"):
            html_parts.append(
                self._render_subsection("Timeline", execution["timeline"])
            )
        if execution.get("milestones"):
            html_parts.append(
                self._render_subsection("Milestones", execution["milestones"])
            )
        if execution.get("resource_allocation"):
            html_parts.append(
                self._render_subsection(
                    "Resource Allocation", execution["resource_allocation"]
                )
            )
        if execution.get("risk_mitigation"):
            html_parts.append(
                self._render_subsection("Risk Mitigation", execution["risk_mitigation"])
            )

        # Release Plan
        release = plan.get("release_plan", {})
        html_parts.append("<h2>Release Plan</h2>")
        if release.get("release_criteria"):
            html_parts.append(
                self._render_subsection("Release Criteria", release["release_criteria"])
            )
        if release.get("validation_steps"):
            html_parts.append(
                self._render_subsection("Validation Steps", release["validation_steps"])
            )
        if release.get("production_ramp"):
            html_parts.append(
                self._render_subsection("Production Ramp", release["production_ramp"])
            )

        # Shipping
        shipping = plan.get("shipping", {})
        html_parts.append("<h2>Shipping</h2>")
        if shipping.get("packaging_requirements"):
            html_parts.append(
                self._render_subsection(
                    "Packaging Requirements", shipping["packaging_requirements"]
                )
            )
        if shipping.get("shipping_methods"):
            html_parts.append(
                self._render_subsection(
                    "Shipping Methods", shipping["shipping_methods"]
                )
            )
        if shipping.get("delivery_schedule"):
            html_parts.append(
                self._render_subsection(
                    "Delivery Schedule", shipping["delivery_schedule"]
                )
            )

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
        html_parts.append(
            """
<hr/>
<p><em>Generated by Strategic Build Planner - Northern Manufacturing Co., Inc.</em></p>
"""
        )

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
        html = "<ac:task-list>\n"

        for task in tasks:
            title = self._escape_html(task.get("title", "Task"))
            description = self._escape_html(task.get("description", ""))
            priority = task.get("priority", "medium")

            priority_label = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(
                priority, "MEDIUM"
            )

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
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")

    def checklist_to_confluence_storage(self, checklist: Dict[str, Any]) -> str:
        """
        Convert Pre-Meeting Checklist to Confluence storage format (HTML)

        Args:
            checklist: Checklist dictionary with categories and items

        Returns:
            Confluence storage format HTML string
        """
        html_parts = []

        # Header with project info
        html_parts.append(
            f"""
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p><strong>Project:</strong> {self._escape_html(checklist.get('project_name', 'Unknown'))}</p>
    <p><strong>Customer:</strong> {self._escape_html(checklist.get('customer', 'N/A'))}</p>
    <p><strong>Generated:</strong> {checklist.get('created_at', 'Unknown')}</p>
  </ac:rich-text-body>
</ac:structured-macro>
"""
        )

        # Statistics summary
        stats = checklist.get("statistics", {})
        html_parts.append(
            f"""
<ac:structured-macro ac:name="panel">
  <ac:parameter ac:name="title">Checklist Summary</ac:parameter>
  <ac:rich-text-body>
    <table>
      <tr>
        <td><strong>Total Items:</strong></td>
        <td>{stats.get('total_prompts', 0)}</td>
        <td><strong>Requirements Found:</strong></td>
        <td>{stats.get('requirements_found', 0)}</td>
      </tr>
      <tr>
        <td><strong>No Requirements:</strong></td>
        <td>{stats.get('no_requirements', 0)}</td>
        <td><strong>Coverage:</strong></td>
        <td>{stats.get('coverage_percentage', 0)}%</td>
      </tr>
    </table>
  </ac:rich-text-body>
</ac:structured-macro>
"""
        )

        # Resolution Summary (if resolutions were applied)
        resolution_summary = checklist.get("resolution_summary", {})
        if checklist.get("resolutions_applied") or resolution_summary.get("total_resolved", 0) > 0:
            html_parts.append(
                f"""
<ac:structured-macro ac:name="panel">
  <ac:parameter ac:name="title">Quote Comparison Resolutions</ac:parameter>
  <ac:parameter ac:name="bgColor">#e3fcef</ac:parameter>
  <ac:rich-text-body>
    <table>
      <tr>
        <td><strong>Total Resolved:</strong></td>
        <td>{resolution_summary.get('total_resolved', 0)}</td>
        <td><strong>Kept Customer Spec:</strong></td>
        <td>{resolution_summary.get('kept_customer_spec', 0)}</td>
      </tr>
      <tr>
        <td><strong>Accepted Quote:</strong></td>
        <td>{resolution_summary.get('accepted_quote', 0)}</td>
        <td><strong>AI Suggestion:</strong></td>
        <td>{resolution_summary.get('used_ai_suggestion', 0)}</td>
      </tr>
      <tr>
        <td><strong>Action Items:</strong></td>
        <td>{resolution_summary.get('action_items_created', 0)}</td>
        <td><strong>Custom:</strong></td>
        <td>{resolution_summary.get('custom_resolutions', 0)}</td>
      </tr>
    </table>
  </ac:rich-text-body>
</ac:structured-macro>
"""
            )

        # Render each category
        for category in checklist.get("categories", []):
            html_parts.append(self._render_checklist_category(category))

        # Footer
        html_parts.append(
            """
<hr/>
<p><em>Pre-Meeting Checklist generated by Strategic Build Planner - Northern Manufacturing Co., Inc.</em></p>
<p><em>Review all items during the APQP kickoff meeting and update as decisions are made.</em></p>
"""
        )

        return "\n".join(html_parts)

    # =========================================================================
    # Template Filling Methods (for updating existing pages with checklist data)
    # =========================================================================

    # Mapping between checklist categories and template section headings
    TEMPLATE_SECTION_MAP = {
        "Material Standards": ["Material Restrictions", "Welding Code & Materials"],
        "Fabrication Process Standards": ["Build Strategy"],
        "Welding & NDE Requirements": ["Welding Code & Materials", "MTRs", "Quality Plan"],
        "Quality Documentation": ["Quality Plan (ITP)"],
        "Painting & Coating": ["Finishing / cosmetic strategy"],
        "Dimensional & Tolerances": ["Quality Plan"],
        "Testing Requirements": ["Quality Plan", "Positive Material Inspection"],
        "Packaging & Shipping": ["Packaging strategy"],
    }

    async def fill_template_with_checklist(
        self,
        page_id: str,
        checklist: Dict[str, Any],
        quote_assumptions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fill an existing Confluence template page with checklist data.

        Args:
            page_id: ID of the template page to update
            checklist: Checklist dictionary with categories and items
            quote_assumptions: Optional list of quote assumptions to add

        Returns:
            Dict with updated page info (id, title, url, version)
        """
        self._ensure_client()

        # Get existing page content
        page = await self.get_page(page_id)
        if not page:
            raise ValueError(f"Page {page_id} not found")

        existing_content = page.get("content", "")
        page_title = page.get("title", "")

        logger.info(f"Filling template for page: {page_title} ({page_id})")

        # Build checklist data by category for easy lookup
        checklist_by_category = {}
        for category in checklist.get("categories", []):
            cat_name = category.get("name", "")
            items_with_answers = [
                item for item in category.get("items", [])
                if item.get("answer") and item.get("status") == "requirement_found"
            ]
            if items_with_answers:
                checklist_by_category[cat_name] = items_with_answers

        # Update the content
        updated_content = self._inject_checklist_into_template(
            existing_content, checklist_by_category, quote_assumptions
        )

        # Update the page
        result = await self.update_page(page_id, page_title, updated_content)

        logger.info(f"Successfully updated template page: {page_title}")
        return result

    def _inject_checklist_into_template(
        self,
        content: str,
        checklist_by_category: Dict[str, List[Dict]],
        quote_assumptions: Optional[List[str]] = None,
    ) -> str:
        """
        Inject checklist data into template content.

        Strategy:
        1. Find section headings (h2, h3) in the content
        2. For each section, find matching checklist categories
        3. Insert checklist items after the section heading
        4. Add quote assumptions to a dedicated section
        """
        # Add quote assumptions section if provided
        if quote_assumptions:
            content = self._add_quote_assumptions_section(content, quote_assumptions)

        # For each checklist category, find matching template sections and inject data
        for category_name, items in checklist_by_category.items():
            template_sections = self.TEMPLATE_SECTION_MAP.get(category_name, [])

            for section_name in template_sections:
                content = self._inject_items_into_section(
                    content, section_name, category_name, items
                )

        return content

    def _add_quote_assumptions_section(
        self, content: str, assumptions: List[str]
    ) -> str:
        """Add or update quote assumptions bullet list in the content."""
        # Build the assumptions HTML
        assumptions_html = "<ul>\n"
        for assumption in assumptions:
            assumptions_html += f'<li>{self._escape_html(assumption)} <strong>[Quote]</strong></li>\n'
        assumptions_html += "</ul>\n"

        # Look for existing [Quote] section or assumptions marker
        # Try to find a section that already has [Quote] markers
        quote_pattern = r'(<ul>[\s\S]*?\[Quote\][\s\S]*?</ul>)'
        if re.search(quote_pattern, content):
            # Replace existing quote assumptions section
            content = re.sub(quote_pattern, assumptions_html, content, count=1)
        else:
            # Look for "Assumptions" or similar heading and add after it
            assumption_heading_pattern = r'(<h[23][^>]*>.*?[Aa]ssumptions?.*?</h[23]>)'
            match = re.search(assumption_heading_pattern, content)
            if match:
                # Insert after the heading
                insert_pos = match.end()
                content = content[:insert_pos] + "\n" + assumptions_html + content[insert_pos:]
            else:
                # Add at the beginning after any info panel
                info_panel_end = content.find('</ac:structured-macro>')
                if info_panel_end > 0:
                    insert_pos = info_panel_end + len('</ac:structured-macro>')
                    assumptions_section = f"""
<h2>Quote Assumptions</h2>
{assumptions_html}
"""
                    content = content[:insert_pos] + assumptions_section + content[insert_pos:]

        return content

    def _inject_items_into_section(
        self,
        content: str,
        section_name: str,
        category_name: str,
        items: List[Dict],
    ) -> str:
        """Inject checklist items into a specific template section.

        Supports multiple section formats:
        1. Heading tags: <h2>Section Name</h2>, <h3>Section Name</h3>
        2. Bold text: <strong>Section Name:</strong>, <b>Section Name:</b>
        3. Table cells with bold: <td><strong>Section Name</strong></td>
        """
        escaped_name = re.escape(section_name)

        # Try multiple patterns to find the section
        patterns = [
            # Pattern 1: h2/h3 headings
            rf'(<h[23][^>]*>[^<]*{escaped_name}[^<]*</h[23]>)',
            # Pattern 2: Bold text with colon (inline label style)
            rf'(<strong>{escaped_name}:?</strong>)',
            rf'(<b>{escaped_name}:?</b>)',
            # Pattern 3: Paragraph containing bold section name
            rf'(<p[^>]*><strong>{escaped_name}:?</strong>)',
            # Pattern 4: Table cell with bold
            rf'(<td[^>]*><strong>{escaped_name}</strong></td>)',
            # Pattern 5: Any tag containing the section name as text
            rf'(<[^>]+>[^<]*{escaped_name}[^<]*</[^>]+>)',
        ]

        match = None
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                logger.debug(f"Found section '{section_name}' with pattern: {pattern[:50]}...")
                break

        if not match:
            logger.debug(f"Section '{section_name}' not found in template")
            return content

        # Build the items HTML - use compact format for inline sections
        items_html = f" <em>[From {category_name}]</em> "

        # For heading-style sections, use block format
        if match.group(0).startswith('<h'):
            items_html = f"\n<p><strong>From {category_name}:</strong></p>\n<ul>\n"
            for item in items:
                question = self._escape_html(item.get("question", ""))
                answer = self._escape_html(item.get("answer", ""))
                resolution = item.get("resolution")

                if resolution:
                    res_note = resolution.get("note", "")
                    items_html += f'<li><strong>{question}:</strong> {answer} <em>({res_note})</em></li>\n'
                else:
                    items_html += f'<li><strong>{question}:</strong> {answer}</li>\n'
            items_html += "</ul>\n"
            insert_pos = match.end()
        else:
            # For inline sections (bold labels), append values after the label
            # Find what comes after the matched element
            inline_values = []
            for item in items:
                answer = self._escape_html(item.get("answer", ""))
                inline_values.append(answer)

            # Join multiple values with semicolons
            values_text = "; ".join(inline_values)
            items_html = f" {values_text}"

            # Find the end of the current value (look for next tag or end of line)
            insert_pos = match.end()

            # Skip any existing content until we hit a line break or new section
            remaining = content[insert_pos:]
            # Find where to insert (after any existing text, before next element)
            next_tag = re.search(r'<(?:p|br|div|h[123456]|strong|table|tr|td)', remaining, re.IGNORECASE)
            if next_tag:
                # Check if there's text content between match and next tag
                between = remaining[:next_tag.start()]
                if between.strip():
                    # There's existing content, append with separator
                    items_html = f"; {values_text}"
                    insert_pos = insert_pos + next_tag.start()
                else:
                    # Insert right after the label
                    pass

        content = content[:insert_pos] + items_html + content[insert_pos:]

        return content

    # =========================================================================
    # Search & Navigation Methods (for Confluence workflow)
    # =========================================================================

    async def search_by_job_number(
        self, job_number: str, space_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for Confluence pages by job number (e.g., F12345)

        Args:
            job_number: Job number to search for (e.g., "F12345", "F-12345")
            space_key: Space to search in (defaults to KB for Knowledge Base)

        Returns:
            List of matching pages with id, title, url, space_key
        """
        self._ensure_client()
        space = space_key or "KB"  # Default to Knowledge Base space

        # Normalize job number - allow flexible matching
        # Search title and content for the job number
        cql = f'space = "{space}" AND (title ~ "{job_number}" OR text ~ "{job_number}")'
        logger.info(f"Searching for job number: {job_number} in space {space}")

        return await self.search_pages(cql, limit=20)

    async def get_space_hierarchy(
        self, space_key: Optional[str] = None, parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get page hierarchy for browsing - returns children of a parent page

        Args:
            space_key: Space key (defaults to KB)
            parent_id: Parent page ID. If None, returns top-level pages in the space.

        Returns:
            List of page dicts with id, title, has_children, type (customer/family/project)
        """
        self._ensure_client()
        space = space_key or "KB"

        try:
            if parent_id:
                # Get children of a specific page
                children = self.client.get_page_child_by_type(
                    page_id=parent_id, type="page", start=0, limit=100
                )
            else:
                # Get top-level pages in the space
                # First get the space's homepage, then get its children
                try:
                    space_info = self.client.get_space(space, expand="homepage")
                    homepage_id = space_info.get("homepage", {}).get("id")
                    if homepage_id:
                        children = self.client.get_page_child_by_type(
                            page_id=homepage_id, type="page", start=0, limit=100
                        )
                    else:
                        # Fallback: just get all pages in the space
                        cql = f'space = "{space}" AND type = page'
                        results = self.client.cql(cql, limit=50)
                        children = [r.get("content", r) for r in results.get("results", [])]
                except Exception as e:
                    logger.warning(f"Could not get space homepage: {e}")
                    # Fallback: just get all pages in the space
                    cql = f'space = "{space}" AND type = page'
                    results = self.client.cql(cql, limit=50)
                    children = [r.get("content", r) for r in results.get("results", [])]

            pages = []
            for child in children:
                page_id = child.get("id")
                title = child.get("title", "Untitled")

                # Check if this page has children
                has_children = False
                try:
                    child_check = self.client.get_page_child_by_type(
                        page_id=page_id, type="page", start=0, limit=1
                    )
                    has_children = len(child_check) > 0
                except Exception:
                    pass

                # Determine page type based on hierarchy depth or labels
                page_type = self._determine_page_type(page_id, title, parent_id)

                pages.append(
                    {
                        "id": page_id,
                        "title": title,
                        "url": f"{self.url}/spaces/{space}/pages/{page_id}",
                        "has_children": has_children,
                        "type": page_type,
                    }
                )

            logger.info(
                f"Found {len(pages)} child pages for parent={parent_id or 'root'}"
            )
            return pages

        except Exception as e:
            logger.error(f"Failed to get hierarchy: {str(e)}")
            raise

    def _determine_page_type(
        self, page_id: str, title: str, parent_id: Optional[str]
    ) -> str:
        """
        Determine if a page is a customer, family, or project page
        Based on hierarchy: Customer → Family of Parts → Project
        """
        # If no parent, it's likely a customer page
        if not parent_id:
            return "customer"

        # Could check labels or depth for more accurate typing
        # For now, use simple heuristics
        title_lower = title.lower()
        if "family" in title_lower or "parts" in title_lower:
            return "family"
        if any(
            pattern in title_lower
            for pattern in ["project", "job", "quote", "order", "f-", "f1", "f2"]
        ):
            return "project"

        return "unknown"

    async def get_page_with_ancestors(
        self, page_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a page with its full ancestor chain (for context)

        Args:
            page_id: Page ID

        Returns:
            Page dict with content, plus ancestors list
        """
        self._ensure_client()

        try:
            # Get page with ancestors expanded
            result = self.client.get_page_by_id(
                page_id=page_id, expand="body.storage,version,ancestors"
            )

            if not result:
                return None

            # Build ancestors list
            ancestors = []
            for ancestor in result.get("ancestors", []):
                ancestors.append(
                    {
                        "id": ancestor.get("id"),
                        "title": ancestor.get("title"),
                    }
                )

            return {
                "id": result.get("id"),
                "title": result.get("title"),
                "content": result.get("body", {}).get("storage", {}).get("value", ""),
                "version": result.get("version", {}).get("number", 1),
                "ancestors": ancestors,
                "url": f"{self.url}/spaces/{self.space_key}/pages/{page_id}",
            }

        except Exception as e:
            logger.error(f"Failed to get page with ancestors: {str(e)}")
            return None

    async def get_page_content_text(self, page_id: str) -> Optional[str]:
        """
        Get page content as plain text (for AI analysis)

        Args:
            page_id: Page ID

        Returns:
            Plain text content extracted from Confluence storage format
        """
        page = await self.get_page(page_id)
        if not page:
            return None

        # Strip HTML tags from storage format
        html_content = page.get("content", "")
        # Basic HTML stripping - could be enhanced with BeautifulSoup
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _render_checklist_category(self, category: Dict[str, Any]) -> str:
        """Render a checklist category as HTML"""
        html = f"<h2>{self._escape_html(category.get('name', 'Category'))}</h2>\n"

        items = category.get("items", [])
        if not items:
            html += "<p><em>No items in this category.</em></p>\n"
            return html

        # Count requirements found
        found = sum(1 for i in items if i.get("status") == "requirement_found")
        html += f"<p><em>{found} of {len(items)} requirements found</em></p>\n"

        # Check if any items have resolutions
        has_resolutions = any(item.get("resolution") for item in items)

        html += "<table>\n"
        if has_resolutions:
            html += (
                "<tr><th>Status</th><th>Question</th><th>Answer</th><th>Source</th><th>Resolution</th></tr>\n"
            )
        else:
            html += (
                "<tr><th>Status</th><th>Question</th><th>Answer</th><th>Source</th></tr>\n"
            )

        for item in items:
            status = item.get("status", "unknown")
            question = self._escape_html(item.get("question", ""))
            answer = self._escape_html(item.get("answer", "N/A"))
            source = self._escape_html(item.get("source", ""))
            resolution = item.get("resolution")

            # Status indicator
            if status == "requirement_found":
                status_html = '<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Green</ac:parameter><ac:parameter ac:name="title">Found</ac:parameter></ac:structured-macro>'
            elif status == "no_requirement":
                status_html = '<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Grey</ac:parameter><ac:parameter ac:name="title">None</ac:parameter></ac:structured-macro>'
            else:
                status_html = '<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Red</ac:parameter><ac:parameter ac:name="title">Error</ac:parameter></ac:structured-macro>'

            if has_resolutions:
                # Show resolution info if present
                if resolution:
                    res_type = resolution.get("type", "")
                    res_note = resolution.get("note", "")
                    res_html = f'<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Blue</ac:parameter><ac:parameter ac:name="title">{self._escape_html(res_type)}</ac:parameter></ac:structured-macro><br/><small>{self._escape_html(res_note)}</small>'
                else:
                    res_html = ""
                html += f"<tr><td>{status_html}</td><td><strong>{question}</strong></td><td>{answer}</td><td><em>{source}</em></td><td>{res_html}</td></tr>\n"
            else:
                html += f"<tr><td>{status_html}</td><td><strong>{question}</strong></td><td>{answer}</td><td><em>{source}</em></td></tr>\n"

        html += "</table>\n"
        return html
