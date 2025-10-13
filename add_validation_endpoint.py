"""
Script to add validation endpoint to server/main.py

This will insert the validation code after the QA endpoint.
"""

import re

# Read the file
with open("server/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Define the new code to insert
validation_code = '''

# ============================================================================
# Validation Endpoint
# ============================================================================

class ValidateRequest(BaseModel):
    """Request for session validation"""
    session_id: str


class ValidateResponse(BaseModel):
    """Response with validation results"""
    is_ready: bool
    completeness_score: int
    issues: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    checklist: List[Dict[str, Any]]


@app.post("/validate", response_model=ValidateResponse)
async def validate_session(request: ValidateRequest):
    """
    Validate a session for agent execution readiness.

    Returns validation results including:
    - is_ready: Whether session can run agents
    - completeness_score: 0-100% data quality score
    - issues: All validation issues (errors, warnings, suggestions)
    - checklist: User-friendly checklist for UI
    """
    from .lib.validation import validate_session_for_agents, get_validation_checklist

    LOGGER.info("=== /validate called for session %s ===", request.session_id)

    # Get session
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Run validation
    result = validate_session_for_agents(session)
    checklist = get_validation_checklist(session)

    LOGGER.info(
        "Validation result: ready=%s, score=%d%%, errors=%d, warnings=%d",
        result.is_ready,
        result.completeness_score,
        len(result.to_dict()["errors"]),
        len(result.to_dict()["warnings"])
    )

    return ValidateResponse(
        is_ready=result.is_ready,
        completeness_score=result.completeness_score,
        issues=result.to_dict()["issues"],
        errors=result.to_dict()["errors"],
        warnings=result.to_dict()["warnings"],
        suggestions=result.to_dict()["suggestions"],
        checklist=checklist,
    )
'''

# Find the location to insert (after QA endpoint)
# Look for the QAGradeRequest class and the endpoint that uses it
qa_endpoint_pattern = r'(@app\.post\("/qa/grade".*?\n(?:async )?def .*?\):.*?(?=\n@app\.|$))'

# Find all endpoints
matches = list(re.finditer(qa_endpoint_pattern, content, re.DOTALL))

if matches:
    # Insert after the last match (QA endpoint)
    last_match = matches[-1]
    insert_pos = last_match.end()

    # Insert the validation code
    new_content = content[:insert_pos] + validation_code + content[insert_pos:]

    # Write back
    with open("server/main.py", "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✓ Validation endpoint added successfully")
    print(f"  Inserted at position {insert_pos}")
    print(f"  File size: {len(content)} → {len(new_content)} bytes (+{len(new_content) - len(content)})")
else:
    print("✗ Could not find insertion point (QA endpoint)")
    print("  Please add validation endpoint manually")
