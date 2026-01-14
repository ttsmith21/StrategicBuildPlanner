"""
Draft Router - Strategic Build Plan Generation
"""

import logging
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.services.openai_service import OpenAIService
from app.models.responses import DraftRequest, DraftResponse, ErrorResponse
from app.models.plan_schema import StrategicBuildPlan
from app.prompts.draft_prompt import DRAFT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter()


def plan_to_markdown(plan: dict) -> str:
    """
    Convert Strategic Build Plan JSON to Markdown format

    Args:
        plan: Plan dictionary

    Returns:
        Markdown formatted string
    """
    md_lines = []

    # Header
    md_lines.append(f"# Strategic Build Plan: {plan.get('project_name', 'Unknown')}")
    md_lines.append("")
    md_lines.append(f"**Customer:** {plan.get('customer', 'Unknown')}")
    md_lines.append(f"**Family of Parts:** {plan.get('family_of_parts', 'Unknown')}")
    md_lines.append(f"**Generated:** {plan.get('generated_at', datetime.utcnow().isoformat())}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    def render_key_points(key_points: list, section_name: str) -> list:
        """Render a list of key points as markdown"""
        lines = []
        if not key_points:
            lines.append(f"*No {section_name.lower()} recorded yet.*")
            return lines

        for kp in key_points:
            confidence = kp.get('confidence', 0)
            confidence_level = kp.get('confidence_level', 'unknown')
            text = kp.get('text', '')

            # Confidence indicator
            if confidence >= 0.8:
                conf_icon = "🟢"
            elif confidence >= 0.5:
                conf_icon = "🟡"
            else:
                conf_icon = "🔴"

            lines.append(f"- {conf_icon} {text}")

            # Source hint
            source = kp.get('source_hint')
            if source:
                source_parts = []
                if source.get('document'):
                    source_parts.append(source['document'])
                if source.get('page'):
                    source_parts.append(f"pg. {source['page']}")
                if source.get('section'):
                    source_parts.append(f"§{source['section']}")
                if source_parts:
                    lines.append(f"  - *Source: {', '.join(source_parts)} (confidence: {confidence:.0%})*")

        return lines

    # Keys to Project
    md_lines.append("## 🔑 Keys to Project")
    md_lines.append("")
    md_lines.extend(render_key_points(plan.get('keys_to_project', []), "keys"))
    md_lines.append("")

    # Quality Plan
    md_lines.append("## ✅ Quality Plan")
    md_lines.append("")
    quality = plan.get('quality_plan', {})

    if quality.get('control_plan_items'):
        md_lines.append("### Control Plan Items")
        md_lines.extend(render_key_points(quality['control_plan_items'], "control plan items"))
        md_lines.append("")

    if quality.get('inspection_strategy'):
        md_lines.append("### Inspection Strategy")
        md_lines.extend(render_key_points(quality['inspection_strategy'], "inspection items"))
        md_lines.append("")

    if quality.get('quality_metrics'):
        md_lines.append("### Quality Metrics")
        md_lines.extend(render_key_points(quality['quality_metrics'], "metrics"))
        md_lines.append("")

    if quality.get('ppap_requirements'):
        md_lines.append("### PPAP Requirements")
        md_lines.extend(render_key_points(quality['ppap_requirements'], "PPAP items"))
        md_lines.append("")

    # Purchasing
    md_lines.append("## 🛒 Purchasing")
    md_lines.append("")
    purchasing = plan.get('purchasing', {})

    if purchasing.get('raw_materials'):
        md_lines.append("### Raw Materials")
        md_lines.extend(render_key_points(purchasing['raw_materials'], "materials"))
        md_lines.append("")

    if purchasing.get('suppliers'):
        md_lines.append("### Suppliers")
        md_lines.extend(render_key_points(purchasing['suppliers'], "suppliers"))
        md_lines.append("")

    if purchasing.get('lead_times'):
        md_lines.append("### Lead Times")
        md_lines.extend(render_key_points(purchasing['lead_times'], "lead times"))
        md_lines.append("")

    if purchasing.get('cost_estimates'):
        md_lines.append("### Cost Estimates")
        md_lines.extend(render_key_points(purchasing['cost_estimates'], "estimates"))
        md_lines.append("")

    # History Review
    md_lines.append("## 📜 History Review")
    md_lines.append("")
    history = plan.get('history_review', {})

    if history.get('previous_projects'):
        md_lines.append("### Previous Projects")
        md_lines.extend(render_key_points(history['previous_projects'], "projects"))
        md_lines.append("")

    if history.get('lessons_learned'):
        md_lines.append("### Lessons Learned")
        md_lines.extend(render_key_points(history['lessons_learned'], "lessons"))
        md_lines.append("")

    if history.get('recurring_issues'):
        md_lines.append("### Recurring Issues")
        md_lines.extend(render_key_points(history['recurring_issues'], "issues"))
        md_lines.append("")

    # Build Strategy
    md_lines.append("## 🏭 Build Strategy")
    md_lines.append("")
    build = plan.get('build_strategy', {})

    if build.get('manufacturing_process'):
        md_lines.append("### Manufacturing Process")
        md_lines.extend(render_key_points(build['manufacturing_process'], "processes"))
        md_lines.append("")

    if build.get('tooling_requirements'):
        md_lines.append("### Tooling Requirements")
        md_lines.extend(render_key_points(build['tooling_requirements'], "tooling"))
        md_lines.append("")

    if build.get('capacity_planning'):
        md_lines.append("### Capacity Planning")
        md_lines.extend(render_key_points(build['capacity_planning'], "capacity items"))
        md_lines.append("")

    if build.get('make_vs_buy_decisions'):
        md_lines.append("### Make vs. Buy Decisions")
        md_lines.extend(render_key_points(build['make_vs_buy_decisions'], "decisions"))
        md_lines.append("")

    # Execution Strategy
    md_lines.append("## 📅 Execution Strategy")
    md_lines.append("")
    execution = plan.get('execution_strategy', {})

    if execution.get('timeline'):
        md_lines.append("### Timeline")
        md_lines.extend(render_key_points(execution['timeline'], "timeline items"))
        md_lines.append("")

    if execution.get('milestones'):
        md_lines.append("### Milestones")
        md_lines.extend(render_key_points(execution['milestones'], "milestones"))
        md_lines.append("")

    if execution.get('resource_allocation'):
        md_lines.append("### Resource Allocation")
        md_lines.extend(render_key_points(execution['resource_allocation'], "resources"))
        md_lines.append("")

    if execution.get('risk_mitigation'):
        md_lines.append("### Risk Mitigation")
        md_lines.extend(render_key_points(execution['risk_mitigation'], "risks"))
        md_lines.append("")

    # Release Plan
    md_lines.append("## 🚀 Release Plan")
    md_lines.append("")
    release = plan.get('release_plan', {})

    if release.get('release_criteria'):
        md_lines.append("### Release Criteria")
        md_lines.extend(render_key_points(release['release_criteria'], "criteria"))
        md_lines.append("")

    if release.get('validation_steps'):
        md_lines.append("### Validation Steps")
        md_lines.extend(render_key_points(release['validation_steps'], "steps"))
        md_lines.append("")

    if release.get('production_ramp'):
        md_lines.append("### Production Ramp")
        md_lines.extend(render_key_points(release['production_ramp'], "ramp items"))
        md_lines.append("")

    # Shipping
    md_lines.append("## 📦 Shipping")
    md_lines.append("")
    shipping = plan.get('shipping', {})

    if shipping.get('packaging_requirements'):
        md_lines.append("### Packaging Requirements")
        md_lines.extend(render_key_points(shipping['packaging_requirements'], "packaging"))
        md_lines.append("")

    if shipping.get('shipping_methods'):
        md_lines.append("### Shipping Methods")
        md_lines.extend(render_key_points(shipping['shipping_methods'], "methods"))
        md_lines.append("")

    if shipping.get('delivery_schedule'):
        md_lines.append("### Delivery Schedule")
        md_lines.extend(render_key_points(shipping['delivery_schedule'], "schedule"))
        md_lines.append("")

    # Asana Tasks
    asana_todos = plan.get('asana_todos', [])
    if asana_todos:
        md_lines.append("## ✅ Action Items (Asana Tasks)")
        md_lines.append("")
        for task in asana_todos:
            priority = task.get('priority', 'medium')
            priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
            md_lines.append(f"- [ ] {priority_icon} **{task.get('title', 'Task')}**")
            if task.get('description'):
                md_lines.append(f"  - {task['description']}")
            if task.get('assignee_hint'):
                md_lines.append(f"  - *Assignee: {task['assignee_hint']}*")
            if task.get('due_date_hint'):
                md_lines.append(f"  - *Due: {task['due_date_hint']}*")
        md_lines.append("")

    # Notes
    apqp_notes = plan.get('apqp_notes', [])
    if apqp_notes:
        md_lines.append("## 📝 APQP Notes")
        md_lines.append("")
        for note in apqp_notes:
            if note.get('timestamp'):
                md_lines.append(f"**{note['timestamp']}**")
            md_lines.append(f"{note.get('content', '')}")
            md_lines.append("")

    meeting_notes = plan.get('customer_meeting_notes', [])
    if meeting_notes:
        md_lines.append("## 🤝 Customer Meeting Notes")
        md_lines.append("")
        for note in meeting_notes:
            if note.get('timestamp'):
                md_lines.append(f"**{note['timestamp']}**")
            md_lines.append(f"{note.get('content', '')}")
            md_lines.append("")

    # Footer
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("*Generated by Strategic Build Planner - Northern Manufacturing Co., Inc.*")

    return "\n".join(md_lines)


@router.post("/draft", response_model=DraftResponse)
async def generate_draft(request: DraftRequest):
    """
    Generate a Strategic Build Plan from ingested documents

    **Process:**
    1. Connect to the Vector Store from ingestion
    2. Run OpenAI Responses API with file search
    3. Generate structured JSON plan
    4. Convert to Markdown for preview
    5. Return both formats

    **Prerequisites:**
    - Must have a valid session_id and vector_store_id from /api/ingest
    """
    try:
        logger.info(
            f"Generating draft for project: {request.project_name}, "
            f"customer: {request.customer}, "
            f"vector_store: {request.vector_store_id}"
        )

        # Initialize OpenAI service
        openai_service = OpenAIService()

        # Build user prompt
        user_prompt = f"""Generate a comprehensive Strategic Build Plan for:

**Project:** {request.project_name}
**Customer:** {request.customer}
**Family of Parts:** {request.family_of_parts}

{f"Additional Context: {request.additional_context}" if request.additional_context else ""}

Analyze all uploaded documents in the Vector Store and extract:
- Critical project requirements and constraints
- Quality requirements and PPAP needs
- Material specifications and suppliers
- Historical context from similar projects
- Manufacturing process recommendations
- Timeline and milestone suggestions
- Risks and mitigation strategies
- Action items that need resolution

Return the complete StrategicBuildPlan JSON structure with all sections populated.
For any missing or unclear information, flag it with low confidence and create an Asana task.
"""

        # Generate plan using OpenAI
        plan_data = await openai_service.generate_plan(
            vector_store_id=request.vector_store_id,
            system_prompt=DRAFT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
            max_tokens=16000
        )

        # Validate and enhance plan data
        plan_data['project_name'] = request.project_name
        plan_data['customer'] = request.customer
        plan_data['family_of_parts'] = request.family_of_parts
        plan_data['generated_at'] = datetime.utcnow().isoformat()

        # Validate against Pydantic model (will raise if invalid)
        try:
            validated_plan = StrategicBuildPlan(**plan_data)
            plan_json = validated_plan.model_dump(mode='json')
        except Exception as validation_error:
            logger.warning(f"Plan validation warning: {validation_error}")
            # Use the raw data if validation fails
            plan_json = plan_data

        # Convert to Markdown
        plan_markdown = plan_to_markdown(plan_json)

        logger.info(
            f"Draft generated successfully for '{request.project_name}' "
            f"({len(plan_json.get('keys_to_project', []))} key points, "
            f"{len(plan_json.get('asana_todos', []))} action items)"
        )

        return DraftResponse(
            plan_json=plan_json,
            plan_markdown=plan_markdown,
            session_id=request.session_id,
            generated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Draft generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate draft: {str(e)}"
        )
