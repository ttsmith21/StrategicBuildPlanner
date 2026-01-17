"""
Strategic Build Plan Data Models
Pydantic schemas for structured plan output
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence level for extracted information"""

    HIGH = "high"  # 0.8-1.0
    MEDIUM = "medium"  # 0.5-0.79
    LOW = "low"  # 0.2-0.49
    UNKNOWN = "unknown"  # 0.0-0.19


class SourceHint(BaseModel):
    """Reference to source document"""

    document: str = Field(..., description="Document name or Confluence page title")
    page: Optional[int] = Field(None, description="Page number (for PDFs)")
    section: Optional[str] = Field(None, description="Section or heading")


class KeyPoint(BaseModel):
    """Single key point with source and confidence"""

    text: str = Field(..., description="The key point or information")
    source_hint: Optional[SourceHint] = None
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0"
    )
    confidence_level: ConfidenceLevel = Field(..., description="Categorized confidence")


class QualityPlan(BaseModel):
    """Quality Plan section"""

    control_plan_items: List[KeyPoint] = Field(default_factory=list)
    inspection_strategy: List[KeyPoint] = Field(default_factory=list)
    quality_metrics: List[KeyPoint] = Field(default_factory=list)
    ppap_requirements: List[KeyPoint] = Field(default_factory=list)


class Purchasing(BaseModel):
    """Purchasing section"""

    raw_materials: List[KeyPoint] = Field(default_factory=list)
    suppliers: List[KeyPoint] = Field(default_factory=list)
    lead_times: List[KeyPoint] = Field(default_factory=list)
    cost_estimates: List[KeyPoint] = Field(default_factory=list)


class HistoryReview(BaseModel):
    """History Review section"""

    previous_projects: List[KeyPoint] = Field(default_factory=list)
    lessons_learned: List[KeyPoint] = Field(default_factory=list)
    recurring_issues: List[KeyPoint] = Field(default_factory=list)


class BuildStrategy(BaseModel):
    """Build Strategy section"""

    manufacturing_process: List[KeyPoint] = Field(default_factory=list)
    tooling_requirements: List[KeyPoint] = Field(default_factory=list)
    capacity_planning: List[KeyPoint] = Field(default_factory=list)
    make_vs_buy_decisions: List[KeyPoint] = Field(default_factory=list)


class ExecutionStrategy(BaseModel):
    """Execution Strategy section"""

    timeline: List[KeyPoint] = Field(default_factory=list)
    milestones: List[KeyPoint] = Field(default_factory=list)
    resource_allocation: List[KeyPoint] = Field(default_factory=list)
    risk_mitigation: List[KeyPoint] = Field(default_factory=list)


class ReleasePlan(BaseModel):
    """Release Plan section"""

    release_criteria: List[KeyPoint] = Field(default_factory=list)
    validation_steps: List[KeyPoint] = Field(default_factory=list)
    production_ramp: List[KeyPoint] = Field(default_factory=list)


class Shipping(BaseModel):
    """Shipping section"""

    packaging_requirements: List[KeyPoint] = Field(default_factory=list)
    shipping_methods: List[KeyPoint] = Field(default_factory=list)
    delivery_schedule: List[KeyPoint] = Field(default_factory=list)


class Note(BaseModel):
    """APQP or meeting note"""

    timestamp: Optional[datetime] = None
    content: str
    source_hint: Optional[SourceHint] = None
    action_items: List[str] = Field(default_factory=list)


class AsanaTask(BaseModel):
    """Asana task to be created"""

    title: str
    description: str
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    assignee_hint: Optional[str] = Field(None, description="Suggested assignee name")
    due_date_hint: Optional[str] = Field(None, description="Suggested due date")
    asana_gid: Optional[str] = Field(None, description="Asana task ID after creation")
    asana_url: Optional[str] = Field(None, description="Asana task URL")


class StrategicBuildPlan(BaseModel):
    """Complete Strategic Build Plan"""

    # Metadata
    project_name: str = Field(..., description="Project/part name")
    customer: str = Field(..., description="Customer name")
    family_of_parts: str = Field(..., description="Family of Parts designation")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Plan sections
    keys_to_project: List[KeyPoint] = Field(default_factory=list)
    quality_plan: QualityPlan = Field(default_factory=QualityPlan)
    purchasing: Purchasing = Field(default_factory=Purchasing)
    history_review: HistoryReview = Field(default_factory=HistoryReview)
    build_strategy: BuildStrategy = Field(default_factory=BuildStrategy)
    execution_strategy: ExecutionStrategy = Field(default_factory=ExecutionStrategy)
    release_plan: ReleasePlan = Field(default_factory=ReleasePlan)
    shipping: Shipping = Field(default_factory=Shipping)

    # Notes and tasks
    apqp_notes: List[Note] = Field(default_factory=list)
    customer_meeting_notes: List[Note] = Field(default_factory=list)
    asana_todos: List[AsanaTask] = Field(default_factory=list)

    # Confluence metadata
    confluence_page_id: Optional[str] = None
    confluence_page_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "ACME Bracket Assembly",
                "customer": "ACME Corporation",
                "family_of_parts": "Structural Brackets",
                "keys_to_project": [
                    {
                        "text": "High-volume production required: 50,000 units/year",
                        "source_hint": {"document": "RFQ_ACME_2025.pdf", "page": 3},
                        "confidence": 0.95,
                        "confidence_level": "high",
                    }
                ],
            }
        }
