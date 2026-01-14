---
description: Verify API and UI in Chrome browser
---

# Browser Verification Workflow

Use Chrome automation to verify the application works correctly.

## Prerequisites
- Backend running on http://localhost:8000
- Chrome browser with Claude extension

## Steps

### 1. Verify API Documentation
Navigate to http://localhost:8000/docs and verify:
- Swagger UI loads correctly
- All endpoints are listed
- Try the health endpoint interactively

### 2. Test Ingest Endpoint
In Swagger UI:
1. Expand POST /api/ingest
2. Click "Try it out"
3. Enter project_name: "Test"
4. Upload a test file
5. Execute and verify response

### 3. Check Response Data
Verify the response contains:
- session_id (UUID format)
- vector_store_id (starts with "vs_")
- files_processed array with status

### 4. Console Verification
Check browser console for:
- No JavaScript errors
- Network requests completing successfully

## Using Chrome Tools
```
mcp__claude-in-chrome__navigate - Go to URL
mcp__claude-in-chrome__read_page - Read page content
mcp__claude-in-chrome__computer - Take screenshots
mcp__claude-in-chrome__find - Find elements
```
