"""
Pre-flight validation and completeness checks for agent execution.

Ensures sessions have sufficient data before running expensive agent workflows.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

LOGGER = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Severity of validation issues"""
    ERROR = "error"      # Blocks execution
    WARNING = "warning"  # Allows execution but suboptimal
    INFO = "info"        # Suggestion for improvement


class ValidationIssue:
    """A validation issue found during pre-flight checks"""

    def __init__(
        self,
        level: ValidationLevel,
        field: str,
        message: str,
        suggestion: Optional[str] = None
    ):
        self.level = level
        self.field = field
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "field": self.field,
            "message": self.message,
            "suggestion": self.suggestion,
        }


class ValidationResult:
    """Result of validation with issues and scoring"""

    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.completeness_score: int = 0
        self.is_ready: bool = False

    def add_error(self, field: str, message: str, suggestion: Optional[str] = None):
        """Add a blocking error"""
        self.issues.append(ValidationIssue(ValidationLevel.ERROR, field, message, suggestion))

    def add_warning(self, field: str, message: str, suggestion: Optional[str] = None):
        """Add a warning"""
        self.issues.append(ValidationIssue(ValidationLevel.WARNING, field, message, suggestion))

    def add_info(self, field: str, message: str, suggestion: Optional[str] = None):
        """Add an informational message"""
        self.issues.append(ValidationIssue(ValidationLevel.INFO, field, message, suggestion))

    def has_errors(self) -> bool:
        """Check if there are any blocking errors"""
        return any(issue.level == ValidationLevel.ERROR for issue in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_ready": self.is_ready,
            "completeness_score": self.completeness_score,
            "issues": [issue.to_dict() for issue in self.issues],
            "errors": [issue.to_dict() for issue in self.issues if issue.level == ValidationLevel.ERROR],
            "warnings": [issue.to_dict() for issue in self.issues if issue.level == ValidationLevel.WARNING],
            "suggestions": [issue.to_dict() for issue in self.issues if issue.level == ValidationLevel.INFO],
        }


def validate_session_for_agents(session: Dict[str, Any]) -> ValidationResult:
    """
    Validate that a session is ready for agent execution.

    Checks:
    - Required fields present
    - Vector store created
    - Context pack available
    - Minimum data quality

    Args:
        session: Session data dictionary

    Returns:
        ValidationResult with issues and readiness status
    """
    result = ValidationResult()

    # Check critical requirements
    _check_required_fields(session, result)
    _check_vector_store(session, result)
    _check_context_pack(session, result)
    _check_project_metadata(session, result)

    # Calculate completeness score
    result.completeness_score = _calculate_completeness(session)

    # Determine if ready (no errors)
    result.is_ready = not result.has_errors()

    LOGGER.info(
        f"Validation: ready={result.is_ready}, score={result.completeness_score}%, "
        f"errors={len([i for i in result.issues if i.level == ValidationLevel.ERROR])}, "
        f"warnings={len([i for i in result.issues if i.level == ValidationLevel.WARNING])}"
    )

    return result


def _check_required_fields(session: Dict[str, Any], result: ValidationResult):
    """Check that required fields are present"""
    if not session.get("session_id"):
        result.add_error(
            "session_id",
            "Session ID is missing",
            "This is an internal error. Please create a new session."
        )


def _check_vector_store(session: Dict[str, Any], result: ValidationResult):
    """Check that vector store has been created"""
    vector_store_id = session.get("vector_store_id")

    if not vector_store_id:
        result.add_error(
            "vector_store_id",
            "No files have been uploaded",
            "Upload at least one document (drawing, PO, quote, etc.) before running agents."
        )
        return

    # Check if we have file information
    files = session.get("uploaded_files", [])
    if not files:
        result.add_warning(
            "uploaded_files",
            "File upload information missing",
            "Session may be from an older version. Consider re-uploading files."
        )
    elif len(files) < 2:
        result.add_info(
            "uploaded_files",
            f"Only {len(files)} file uploaded",
            "Consider uploading additional documents (drawings, specifications, etc.) for better results."
        )


def _check_context_pack(session: Dict[str, Any], result: ValidationResult):
    """Check that context pack has useful data"""
    context_pack = session.get("context_pack", {})

    if not context_pack:
        result.add_error(
            "context_pack",
            "Context pack is missing",
            "Run /ingest endpoint first to process documents."
        )
        return

    sources = context_pack.get("sources", [])
    facts = context_pack.get("facts", [])

    if not sources:
        result.add_warning(
            "context_pack.sources",
            "No sources detected in context pack",
            "Documents may not have been processed correctly. Try re-uploading."
        )

    if not facts:
        result.add_info(
            "context_pack.facts",
            "No facts extracted from documents",
            "Agents will work with less structured data. This is okay for simple projects."
        )
    elif len(facts) < 5:
        result.add_info(
            "context_pack.facts",
            f"Only {len(facts)} facts extracted",
            "Consider uploading more detailed documents for richer agent outputs."
        )


def _check_project_metadata(session: Dict[str, Any], result: ValidationResult):
    """Check project metadata fields"""
    project_name = session.get("project_name") or session.get("meta", {}).get("project")
    customer = session.get("customer") or session.get("meta", {}).get("customer")
    family = session.get("family") or session.get("meta", {}).get("family")

    if not project_name:
        result.add_error(
            "project_name",
            "Project name is required",
            "Provide a project name (e.g., 'ACME Bracket Assembly', 'RFQ-2024-001')."
        )

    if not customer:
        result.add_warning(
            "customer",
            "Customer name is recommended",
            "Specifying customer helps agents provide customer-specific recommendations."
        )

    if not family:
        result.add_info(
            "family",
            "Product family not specified",
            "Specifying family (e.g., 'Brackets', 'Vessels') helps with historical context."
        )


def _calculate_completeness(session: Dict[str, Any]) -> int:
    """
    Calculate a completeness score (0-100%).

    Weights:
    - Required fields (40%): session_id, vector_store, context_pack, project_name
    - Optional metadata (20%): customer, family
    - Data quality (40%): number of files, facts extracted
    """
    score = 0

    # Required fields (10% each, total 40%)
    if session.get("session_id"):
        score += 10
    if session.get("vector_store_id"):
        score += 10
    if session.get("context_pack"):
        score += 10
    if session.get("project_name") or session.get("meta", {}).get("project"):
        score += 10

    # Optional metadata (10% each, total 20%)
    if session.get("customer") or session.get("meta", {}).get("customer"):
        score += 10
    if session.get("family") or session.get("meta", {}).get("family"):
        score += 10

    # Data quality (40% total)
    files = session.get("uploaded_files", [])
    facts = session.get("context_pack", {}).get("facts", [])

    # Files: 0-20%
    if len(files) >= 5:
        score += 20
    elif len(files) >= 3:
        score += 15
    elif len(files) >= 2:
        score += 10
    elif len(files) >= 1:
        score += 5

    # Facts: 0-20%
    if len(facts) >= 20:
        score += 20
    elif len(facts) >= 10:
        score += 15
    elif len(facts) >= 5:
        score += 10
    elif len(facts) >= 1:
        score += 5

    return min(score, 100)


def get_validation_checklist(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get a user-friendly checklist for the UI.

    Returns list of checklist items with status.
    """
    checklist = []

    # Files uploaded
    files = session.get("uploaded_files", [])
    checklist.append({
        "item": "Upload documents",
        "status": "complete" if len(files) > 0 else "incomplete",
        "detail": f"{len(files)} file(s) uploaded" if files else "No files uploaded yet",
        "required": True,
    })

    # Project name
    project_name = session.get("project_name") or session.get("meta", {}).get("project")
    checklist.append({
        "item": "Set project name",
        "status": "complete" if project_name else "incomplete",
        "detail": project_name if project_name else "Not set",
        "required": True,
    })

    # Customer
    customer = session.get("customer") or session.get("meta", {}).get("customer")
    checklist.append({
        "item": "Specify customer",
        "status": "complete" if customer else "incomplete",
        "detail": customer if customer else "Not specified",
        "required": False,
    })

    # Family
    family = session.get("family") or session.get("meta", {}).get("family")
    checklist.append({
        "item": "Specify product family",
        "status": "complete" if family else "incomplete",
        "detail": family if family else "Not specified (optional)",
        "required": False,
    })

    # Context pack
    context_pack = session.get("context_pack", {})
    sources = context_pack.get("sources", [])
    checklist.append({
        "item": "Documents processed",
        "status": "complete" if sources else "incomplete",
        "detail": f"{len(sources)} source(s) detected" if sources else "Waiting for document processing",
        "required": True,
    })

    return checklist
