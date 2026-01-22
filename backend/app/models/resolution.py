"""
Conflict Resolution Models
For quote vs. checklist conflict resolution workflow
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ResolutionType(str, Enum):
    """Types of conflict resolution"""

    CUSTOMER_SPEC = "customer_spec"  # Keep the customer requirement
    QUOTE = "quote"  # Accept the vendor's quote assumption
    AI_SUGGESTION = "ai_suggestion"  # Use AI-generated resolution
    ACTION_ITEM = "action_item"  # Create action item for vendor discussion
    CUSTOM = "custom"  # User enters custom resolution text


class ActionItemDetails(BaseModel):
    """Details for creating an Asana action item"""

    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    assignee_hint: Optional[str] = Field(None, description="Suggested assignee name")
    due_date_hint: Optional[str] = Field(
        None, description="Suggested due date (natural language or ISO)"
    )
    priority: str = Field(default="medium", description="Priority: high, medium, low")


class ConflictResolution(BaseModel):
    """Resolution for a single conflict"""

    conflict_index: int = Field(
        ..., description="Index of the conflict in the comparison array"
    )
    resolution_type: ResolutionType = Field(
        ..., description="Type of resolution chosen"
    )
    resolved_value: Optional[str] = Field(
        None, description="The final text to use (auto-populated based on type)"
    )
    custom_text: Optional[str] = Field(
        None, description="Custom resolution text (when type is 'custom')"
    )
    action_item: Optional[ActionItemDetails] = Field(
        None, description="Action item details (when type is 'action_item')"
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the resolution"
    )


class ResolveConflictsRequest(BaseModel):
    """Request to resolve conflicts and update checklist"""

    checklist: Dict[str, Any] = Field(..., description="Original checklist")
    comparison: Dict[str, Any] = Field(..., description="Comparison results")
    resolutions: List[ConflictResolution] = Field(
        ..., description="List of resolutions for each conflict"
    )


class CreatedActionItem(BaseModel):
    """Action item that was created"""

    conflict_index: int
    title: str
    asana_task_id: Optional[str] = None
    asana_task_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResolutionSummary(BaseModel):
    """Summary of resolution actions taken"""

    total_resolved: int = Field(default=0, description="Total conflicts resolved")
    kept_customer_spec: int = Field(default=0, description="Count using customer spec")
    accepted_quote: int = Field(default=0, description="Count accepting quote")
    used_ai_suggestion: int = Field(default=0, description="Count using AI suggestion")
    action_items_created: int = Field(
        default=0, description="Count of action items created"
    )
    custom_resolutions: int = Field(
        default=0, description="Count of custom resolutions"
    )


class ResolveConflictsResponse(BaseModel):
    """Response after resolving conflicts"""

    updated_checklist: Dict[str, Any] = Field(
        ..., description="Checklist with resolutions applied"
    )
    action_items: List[CreatedActionItem] = Field(
        default_factory=list, description="Action items created"
    )
    resolution_summary: ResolutionSummary = Field(
        ..., description="Summary of resolutions"
    )
    resolved_at: datetime = Field(default_factory=datetime.utcnow)
