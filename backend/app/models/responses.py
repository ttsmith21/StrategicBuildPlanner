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
    additional_context: Optional[str] = Field(None, description="Any additional instructions or context")


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


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
