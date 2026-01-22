"""
API Response Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class FileUploadResponse(BaseModel):
    """Response for individual file upload"""

    filename: str
    file_id: str
    size_bytes: int
    char_count: Optional[int] = None
    word_count: Optional[int] = None
    error: Optional[str] = None


class IngestResponse(BaseModel):
    """Response for document ingestion"""

    session_id: str = Field(..., description="Unique session identifier")
    vector_store_id: str = Field(..., description="OpenAI Vector Store ID")
    project_name: str
    files_processed: List[FileUploadResponse]
    total_files: int
    successful_uploads: int
    failed_uploads: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class DraftRequest(BaseModel):
    """Request to draft a Strategic Build Plan"""

    session_id: str = Field(..., description="Session ID from ingestion")
    vector_store_id: str = Field(..., description="Vector Store ID")
    project_name: str
    customer: str
    family_of_parts: str
    additional_context: Optional[str] = Field(
        None, description="Any additional instructions or context"
    )


class DraftResponse(BaseModel):
    """Response with drafted plan"""

    plan_json: Dict[str, Any] = Field(..., description="Strategic Build Plan as JSON")
    plan_markdown: str = Field(..., description="Plan rendered as Markdown")
    session_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PublishRequest(BaseModel):
    """Request to publish plan to Confluence"""

    plan_json: Dict[str, Any]
    customer: str
    family_of_parts: str
    project_name: str
    parent_page_id: Optional[str] = Field(None, description="Optional parent page ID")


class PublishResponse(BaseModel):
    """Response after publishing to Confluence"""

    page_id: str
    page_url: str
    page_title: str
    published_at: datetime = Field(default_factory=datetime.utcnow)


class MeetingApplyRequest(BaseModel):
    """Request to apply meeting transcript to existing plan"""

    plan_json: Dict[str, Any] = Field(
        ..., description="Current Strategic Build Plan JSON"
    )
    transcript: str = Field(..., description="Meeting transcript text")
    meeting_type: str = Field(
        default="customer",
        description="Type: 'customer', 'internal', 'kickoff', 'review'",
    )
    meeting_date: Optional[str] = Field(
        None, description="Meeting date (ISO format or natural)"
    )
    attendees: Optional[List[str]] = Field(None, description="List of attendee names")


class MeetingApplyResponse(BaseModel):
    """Response after applying meeting transcript"""

    plan_json: Dict[str, Any] = Field(
        ..., description="Updated Strategic Build Plan JSON"
    )
    plan_markdown: str = Field(..., description="Updated plan as Markdown")
    changes_summary: List[str] = Field(
        default_factory=list, description="Summary of changes made"
    )
    new_action_items: int = Field(
        default=0, description="Number of new Asana tasks created"
    )
    new_notes: int = Field(default=0, description="Number of notes added")
    applied_at: datetime = Field(default_factory=datetime.utcnow)


class DimensionScores(BaseModel):
    """Individual dimension scores for QA grading"""

    completeness: int = Field(..., ge=0, le=20, description="Completeness score (0-20)")
    specificity: int = Field(..., ge=0, le=20, description="Specificity score (0-20)")
    actionability: int = Field(
        ..., ge=0, le=20, description="Actionability score (0-20)"
    )
    manufacturability: int = Field(
        ..., ge=0, le=20, description="Manufacturability score (0-20)"
    )
    risk_coverage: int = Field(
        ..., ge=0, le=20, description="Risk coverage score (0-20)"
    )


class QAGradeRequest(BaseModel):
    """Request to grade a Strategic Build Plan"""

    plan_json: Dict[str, Any] = Field(
        ..., description="Strategic Build Plan JSON to grade"
    )


class QAGradeResponse(BaseModel):
    """QA grading response with scores and feedback"""

    overall_score: int = Field(..., ge=0, le=100, description="Overall score (0-100)")
    dimension_scores: DimensionScores = Field(..., description="Scores by dimension")
    grade: str = Field(
        ...,
        description="Grade label (Excellent, Good, Acceptable, Needs Work, Incomplete)",
    )
    strengths: List[str] = Field(default_factory=list, description="Plan strengths")
    improvements: List[str] = Field(
        default_factory=list, description="Suggested improvements"
    )
    critical_gaps: List[str] = Field(
        default_factory=list, description="Critical blocking issues"
    )
    graded_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Post-Meeting Review Models
# ============================================================================


class MissingItem(BaseModel):
    """Item from transcript missing from the plan"""

    category: str = Field(
        ..., description="Category: decision, action_item, requirement, question, risk"
    )
    content: str = Field(..., description="What is missing")
    transcript_excerpt: str = Field(..., description="Relevant quote from transcript")
    importance: str = Field(..., description="Importance: critical, important, minor")


class Discrepancy(BaseModel):
    """Discrepancy between transcript and plan"""

    topic: str = Field(..., description="What the discrepancy is about")
    transcript_says: str = Field(..., description="What was said in the meeting")
    plan_says: str = Field(..., description="What the plan currently states")
    severity: str = Field(..., description="Severity: major, minor")


class CapturedItem(BaseModel):
    """Item correctly captured in the plan"""

    topic: str = Field(..., description="What was captured correctly")
    plan_location: str = Field(..., description="Which section of the plan")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class CompareRequest(BaseModel):
    """Request to compare transcript against plan"""

    transcript: str = Field(..., description="Meeting transcript text")
    confluence_page_id: str = Field(
        ..., description="Confluence page ID to compare against"
    )
    meeting_type: str = Field(default="kickoff", description="Meeting type for context")


class ComparisonResponse(BaseModel):
    """Response from transcript-to-plan comparison"""

    coverage_score: float = Field(
        ..., ge=0, le=100, description="How well the plan covers transcript content"
    )
    missing_items: List[MissingItem] = Field(
        default_factory=list, description="Items from transcript not in plan"
    )
    discrepancies: List[Discrepancy] = Field(
        default_factory=list, description="Conflicts between transcript and plan"
    )
    captured_items: List[CapturedItem] = Field(
        default_factory=list, description="Items correctly documented"
    )
    summary: str = Field(..., description="Brief overall assessment")
    compared_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessDimensionScores(BaseModel):
    """Individual dimension scores for process grading"""

    discussion_coverage: int = Field(
        ..., ge=0, le=20, description="Discussion coverage score (0-20)"
    )
    stakeholder_participation: int = Field(
        ..., ge=0, le=20, description="Stakeholder participation score (0-20)"
    )
    decision_quality: int = Field(
        ..., ge=0, le=20, description="Decision quality score (0-20)"
    )
    action_assignment: int = Field(
        ..., ge=0, le=20, description="Action assignment score (0-20)"
    )
    risk_discussion: int = Field(
        ..., ge=0, le=20, description="Risk discussion score (0-20)"
    )


class ProcessGradeRequest(BaseModel):
    """Request to grade APQP meeting process quality"""

    transcript: str = Field(..., description="Meeting transcript text")
    meeting_type: str = Field(default="kickoff", description="Type of meeting")
    expected_attendees: Optional[List[str]] = Field(
        None, description="Optional list of expected attendees"
    )


class ProcessGradeResponse(BaseModel):
    """Response from APQP process grading"""

    overall_score: int = Field(..., ge=0, le=100, description="Overall score (0-100)")
    dimension_scores: ProcessDimensionScores = Field(
        ..., description="Scores by dimension"
    )
    grade: str = Field(
        ...,
        description="Grade label (Excellent, Good, Acceptable, Needs Work, Incomplete)",
    )
    strengths: List[str] = Field(default_factory=list, description="Process strengths")
    improvements: List[str] = Field(
        default_factory=list, description="Suggested improvements"
    )
    topics_discussed: List[str] = Field(
        default_factory=list, description="APQP topics that were discussed"
    )
    topics_missing: List[str] = Field(
        default_factory=list, description="APQP topics that were not discussed"
    )
    graded_at: datetime = Field(default_factory=datetime.utcnow)
