# FastAPI Server for Strategic Build Planner

## Overview

Minimal FastAPI service facade over the CLI functionality. Provides REST API endpoints for the React UI to interact with the Strategic Build Planner.

## Architecture

```
server/
├── main.py              # FastAPI application with all endpoints
├── lib/                 # Shared library modules
│   ├── schema.py        # JSON schemas (PLAN_SCHEMA, QA_RUBRIC_SCHEMA, APQP_CHECKLIST)
│   ├── confluence.py    # Confluence Cloud REST API helpers
│   ├── rendering.py     # Markdown rendering with Jinja2
│   └── vectorstore.py   # OpenAI Vector Store management
├── requirements.txt     # Server-specific dependencies
└── __init__.py
```

## Installation

### 1. Install Dependencies

```bash
# From project root
pip install -r requirements.txt

# Or install server requirements only
pip install -r server/requirements.txt
```

### 2. Configure Environment

Ensure `.env` file has required variables:

```env
# OpenAI
OPENAI_API_KEY=sk-***
OPENAI_MODEL_PLAN=o4-mini

# Confluence (optional - only for /publish endpoint)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@company.com
CONFLUENCE_API_TOKEN=your-token
CONFLUENCE_SPACE_KEY=YOUR_SPACE
CONFLUENCE_PARENT_PAGE_ID=123456789
```

## Running the Server

### Option 1: Using run_server.py (Recommended)

```bash
python run_server.py
```

**With custom options:**
```bash
python run_server.py --host 127.0.0.1 --port 8080 --no-reload
```

### Option 2: Using uvicorn directly

```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8001
```

### Option 3: Running from Python

```python
import uvicorn
uvicorn.run("server.main:app", host="0.0.0.0", port=8001, reload=True)
```

The server will start at **http://localhost:8001**

## API Endpoints

### 1. **POST /ingest**
Upload files and create a session for plan generation.

**Request:**
- `files`: List of files (multipart/form-data)
- `customer` (optional): Customer name
- `family` (optional): Part family name
- `cql` (optional): Confluence CQL query

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "Uploaded 3 file(s) successfully",
  "file_count": 3,
  "file_names": ["drawing.pdf", "spec.docx", "notes.txt"]
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8001/ingest \
  -F "files=@inputs/sample.pdf" \
  -F "files=@meetings/kickoff.txt" \
  -F "customer=ACME Corp" \
  -F "family=Bracket Assembly"
```

---

### 2. **POST /draft**
Generate Strategic Build Plan from ingested files.

**Request Body:**
```json
{
  "session_id": "uuid-from-ingest",
  "project_name": "ACME Bracket Manufacturing",
  "customer": "ACME Corporation",
  "family": "Structural Brackets"
}
```

**Response:**
```json
{
  "plan_json": { /* Complete Strategic Build Plan JSON */ },
  "plan_markdown": "# Strategic Build Plan...",
  "source_file_names": ["drawing.pdf", "spec.docx"],
  "vector_store_id": "vs_abc123"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8001/draft \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "project_name": "ACME Bracket Test",
    "customer": "ACME Corporation"
  }'
```

---

### 3. **POST /publish**
Publish Strategic Build Plan to Confluence.

**Request Body:**
```json
{
  "customer": "ACME Corp",
  "family": "Bracket Family",
  "project": "ACME Bracket Manufacturing",
  "markdown": "# Strategic Build Plan...",
  "parent_page_id": "123456789"
}
```

**Response:**
```json
{
  "page_id": "987654321",
  "url": "https://your-domain.atlassian.net/wiki/spaces/KB/pages/987654321/...",
  "title": "Strategic Build Plan — ACME Bracket Manufacturing"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8001/publish \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "ACME Corp",
    "family": "Bracket Assembly",
    "project": "ACME Bracket Test",
    "markdown": "# Strategic Build Plan\n\nContent here..."
  }'
```

---

### 4. **POST /meeting/apply**
Apply meeting transcripts to existing plan.

**Request Body:**
```json
{
  "plan_json": { /* Existing plan JSON */ },
  "transcript_texts": [
    "Meeting notes content 1...",
    "Meeting notes content 2..."
  ],
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "updated_plan_json": { /* Updated plan JSON */ },
  "changes_summary": "Meeting notes applied successfully"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8001/meeting/apply \
  -H "Content-Type: application/json" \
  -d @meeting_request.json
```

---

### 5. **POST /qa/grade**
Grade plan quality against rubric.

**Request Body:**
```json
{
  "plan_json": { /* Plan JSON to grade */ }
}
```

**Response:**
```json
{
  "overall_score": 85.5,
  "dimensions": [
    {
      "dimension": "Completeness",
      "score": 90,
      "reasons": ["All APQP sections filled", "Good coverage of requirements"],
      "fixes": ["Add more specific timeline details"]
    },
    {
      "dimension": "Specificity",
      "score": 85,
      "reasons": ["Good use of tolerances and quantities"],
      "fixes": ["Add specific delivery dates"]
    },
    // ... more dimensions (Actionability, Manufacturability, Risk)
  ]
}
```

**Dimensions Evaluated:**
1. **Completeness** - Are all APQP sections filled? Any gaps?
2. **Specificity** - Concrete numbers vs vague statements?
3. **Actionability** - Clear owners, due dates, next steps?
4. **Manufacturability** - Realistic process flows, tooling, quality plans?
5. **Risk** - Are risks identified with proper mitigations?

**cURL Example:**
```bash
curl -X POST http://localhost:8001/qa/grade \
  -H "Content-Type: application/json" \
  -d @plan.json
```

---

### 6. **DELETE /session/{session_id}**
Cleanup session and temporary files.

**Response:**
```json
{
  "message": "Session cleaned up successfully"
}
```

**cURL Example:**
```bash
curl -X DELETE http://localhost:8001/session/your-session-id
```

---

## Interactive API Documentation

Once the server is running, access:

- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

These provide interactive API documentation and testing capabilities.

## Full Workflow Example

### 1. Ingest Files
```bash
curl -X POST http://localhost:8001/ingest \
  -F "files=@inputs/drawing.pdf" \
  -F "files=@meetings/kickoff.txt" \
  -F "customer=ACME Corp"
```

**Response:** Save the `session_id`

### 2. Generate Plan
```bash
curl -X POST http://localhost:8001/draft \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "project_name": "ACME Bracket Manufacturing"
  }' | jq . > plan_response.json
```

### 3. Grade Plan Quality
```bash
curl -X POST http://localhost:8001/qa/grade \
  -H "Content-Type: application/json" \
  -d @plan_response.json | jq .
```

### 4. Publish to Confluence
```bash
# Extract markdown from plan_response.json first
MARKDOWN=$(jq -r '.plan_markdown' plan_response.json)

curl -X POST http://localhost:8001/publish \
  -H "Content-Type: application/json" \
  -d "{
    \"customer\": \"ACME Corp\",
    \"family\": \"Bracket Assembly\",
    \"project\": \"ACME Bracket Manufacturing\",
    \"markdown\": $(echo $MARKDOWN | jq -Rs .)
  }"
```

### 5. Cleanup Session
```bash
curl -X DELETE http://localhost:8001/session/YOUR_SESSION_ID
```

## Testing with Postman

Import this collection structure:

1. Create new collection: "Strategic Build Planner API"
2. Add environment variables:
   - `base_url`: http://localhost:8001
   - `session_id`: (will be set by ingest response)
3. Add requests in order: ingest → draft → qa/grade → publish

## Production Considerations

### Session Storage
Current implementation uses in-memory dictionary. For production:
- Use Redis for session storage
- Implement session expiration (TTL)
- Add authentication/authorization

### File Storage
Current implementation uses temp directory. For production:
- Use S3/Azure Blob Storage
- Implement file cleanup scheduled jobs
- Add virus scanning for uploads

### Vector Store Management
- Implement cleanup jobs for old vector stores
- Track vector store costs
- Add rate limiting

### Error Handling
- Add request validation
- Implement retry logic for OpenAI calls
- Add comprehensive logging

### Security
- Add API key authentication
- Implement CORS properly (restrict origins)
- Add rate limiting
- Validate file types and sizes
- Sanitize HTML before publishing to Confluence

## Troubleshooting

### Server won't start
- Check if port 8001 is available: `netstat -ano | findstr :8001`
- Verify all dependencies installed: `pip list | grep -E "fastapi|uvicorn"`
- Check .env file exists and has OPENAI_API_KEY

### /publish returns 400
- Verify Confluence credentials in .env
- Check CONFLUENCE_BASE_URL format (no trailing slash)
- Ensure CONFLUENCE_SPACE_KEY is correct

### /draft timeout
- OpenAI API calls can take 30-60 seconds
- Increase timeout in client if needed
- Check OpenAI API key is valid and has credits

### Type hint warnings
- These are cosmetic (OpenAI SDK type definitions)
- Functionality works correctly
- Can be ignored safely

## Development

### Running Tests
```bash
# Unit tests (TODO)
pytest tests/

# Manual API tests
python test_server_api.py
```

### Adding New Endpoints
1. Add Pydantic models for request/response
2. Implement endpoint in `server/main.py`
3. Update this README with examples
4. Add to interactive docs

### Code Structure
- **server/main.py** - All API endpoints and FastAPI app
- **server/lib/schema.py** - JSON schemas and data structures
- **server/lib/confluence.py** - Confluence API integration
- **server/lib/rendering.py** - Template rendering
- **server/lib/vectorstore.py** - OpenAI Vector Store operations

## License

Northern Manufacturing Co., Inc.
