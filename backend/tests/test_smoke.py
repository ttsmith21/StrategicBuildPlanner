"""
Smoke Test Suite for Strategic Build Planner
Run with: pytest backend/tests/test_smoke.py -v

Prerequisites:
- Backend server running on localhost:8000
- Environment variables configured (.env)
- Test PDF files available (optional, uses existing vector stores if not)
"""

import pytest
import httpx
import os
import json
from pathlib import Path

# Configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TIMEOUT = 180.0  # 3 minutes for AI operations

# Test data - update these for your environment
TEST_CONFLUENCE_PAGE_ID = "807043074"  # F12346-TEST
TEST_PROJECT_NAME = "SmokeTest"


class TestResults:
    """Collect test results for summary report"""
    passed = 0
    failed = 0
    skipped = 0
    details = []


@pytest.fixture(scope="module")
def client():
    """HTTP client for API requests"""
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.fixture(scope="module")
def vector_store_id(client):
    """Create a vector store for tests that need one, or use existing"""
    # Try to use an existing vector store from a previous ingest
    # This avoids needing test files for every run
    test_file = Path("C:/Users/tsmith/Desktop/2025-10745_V2.pdf")

    if test_file.exists():
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/ingest",
                files={"files": ("test.pdf", f, "application/pdf")},
                data={"project_name": TEST_PROJECT_NAME}
            )
        if response.status_code == 200:
            return response.json()["vector_store_id"]

    # Skip tests requiring vector store if no file available
    pytest.skip("No test file available for vector store creation")


# =============================================================================
# Category 1: Health & Basic Endpoints
# =============================================================================

class TestHealthEndpoints:
    """Basic health and configuration endpoints"""

    def test_api_docs_accessible(self, client):
        """API documentation should be accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
        TestResults.passed += 1

    def test_openapi_schema(self, client):
        """OpenAPI schema should be available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        TestResults.passed += 1


# =============================================================================
# Category 2: Checklist Endpoints
# =============================================================================

class TestChecklistEndpoints:
    """Checklist generation and management"""

    def test_get_prompts(self, client):
        """GET /api/checklist/prompts - Should return category prompts"""
        response = client.get("/api/checklist/prompts")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 6, "Should have at least 6 categories"
        TestResults.passed += 1
        TestResults.details.append(f"Prompts: {len(data['categories'])} categories")

    def test_generate_checklist(self, client, vector_store_id):
        """POST /api/checklist - Should generate checklist from vector store"""
        response = client.post(
            "/api/checklist",
            json={
                "vector_store_id": vector_store_id,
                "project_name": TEST_PROJECT_NAME
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0

        # Quality check: should find some requirements
        stats = data.get("statistics", {})
        total = stats.get("total_prompts", 0)
        assert total >= 30, f"Should have at least 30 prompts, got {total}"
        TestResults.passed += 1
        TestResults.details.append(f"Checklist: {total} prompts processed")

    def test_checklist_invalid_vector_store(self, client):
        """POST /api/checklist with invalid vector_store_id should fail gracefully"""
        response = client.post(
            "/api/checklist",
            json={
                "vector_store_id": "vs_invalid_12345",
                "project_name": "Test"
            }
        )
        # Should return error, not crash
        assert response.status_code in [400, 404, 500]
        TestResults.passed += 1


# =============================================================================
# Category 3: Quote Endpoints
# =============================================================================

class TestQuoteEndpoints:
    """Quote extraction and comparison"""

    def test_extract_quote(self, client):
        """POST /api/quote/extract - Should extract assumptions from PDF"""
        test_file = Path("C:/Users/tsmith/Desktop/2025-10745_V2.pdf")
        if not test_file.exists():
            pytest.skip("Test quote PDF not available")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/quote/extract",
                files={"file": ("quote.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "vendor_name" in data
        assert "assumptions" in data
        assert len(data["assumptions"]) >= 10, "Should extract at least 10 assumptions"
        TestResults.passed += 1
        TestResults.details.append(f"Quote: {len(data['assumptions'])} assumptions extracted")

    def test_compare_quote_to_checklist(self, client):
        """POST /api/quote/compare - Should compare quote to checklist"""
        response = client.post(
            "/api/quote/compare",
            json={
                "checklist": {
                    "project_name": "Test",
                    "categories": [{
                        "id": "mat",
                        "name": "Material",
                        "items": [{
                            "prompt_id": "m1",
                            "question": "MTR Requirements",
                            "answer": "MTRs required for all materials",
                            "status": "requirement_found"
                        }]
                    }]
                },
                "quote_assumptions": {
                    "vendor_name": "Test Vendor",
                    "quote_number": "Q-123",
                    "assumptions": [{
                        "category_id": "mat",
                        "text": "MTRs provided for base materials only",
                        "implication": "No MTRs for consumables"
                    }]
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "conflicts" in data
        assert "statistics" in data
        TestResults.passed += 1


# =============================================================================
# Category 4: Confluence Endpoints
# =============================================================================

class TestConfluenceEndpoints:
    """Confluence integration"""

    def test_search_confluence(self, client):
        """GET /api/confluence/search - Should search for pages"""
        response = client.get("/api/confluence/search", params={"q": "F12346"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        TestResults.passed += 1
        TestResults.details.append(f"Confluence search: {len(data)} results")

    def test_get_hierarchy(self, client):
        """GET /api/confluence/hierarchy - Should return page hierarchy"""
        response = client.get("/api/confluence/hierarchy")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should return hierarchy items"
        TestResults.passed += 1

    def test_get_page(self, client):
        """GET /api/confluence/page/{id} - Should return page content"""
        response = client.get(f"/api/confluence/page/{TEST_CONFLUENCE_PAGE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        TestResults.passed += 1

    def test_get_page_invalid_id(self, client):
        """GET /api/confluence/page/{invalid} - Should return 404"""
        response = client.get("/api/confluence/page/999999999")
        assert response.status_code in [404, 400]
        TestResults.passed += 1


# =============================================================================
# Category 5: Lessons Learned Endpoints
# =============================================================================

class TestLessonsEndpoints:
    """Lessons learned extraction"""

    def test_extract_lessons(self, client):
        """POST /api/lessons/extract - Should extract insights from sibling pages"""
        response = client.post(
            "/api/lessons/extract",
            json={
                "page_id": TEST_CONFLUENCE_PAGE_ID,
                "checklist": {"categories": []},
                "max_siblings": 3
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "insights" in data
        assert "sibling_pages_analyzed" in data

        # If not skipped, should have insights
        if not data.get("skipped"):
            insights = data["insights"]
            assert len(insights) >= 1, "Should extract at least 1 insight"

            # Check insight structure
            if insights:
                insight = insights[0]
                assert "category" in insight
                assert "title" in insight
                assert "relevance_score" in insight

        TestResults.passed += 1
        TestResults.details.append(f"Lessons: {len(data.get('insights', []))} insights")

    def test_extract_lessons_no_page(self, client):
        """POST /api/lessons/extract with invalid page should handle gracefully"""
        response = client.post(
            "/api/lessons/extract",
            json={
                "page_id": "999999999",
                "checklist": {"categories": []},
                "max_siblings": 3
            }
        )
        # Should return skipped=true or error, not crash
        assert response.status_code in [200, 400, 404]
        TestResults.passed += 1


# =============================================================================
# Category 6: Publish Endpoints
# =============================================================================

class TestPublishEndpoints:
    """Publishing to Confluence"""

    def test_publish_checklist(self, client):
        """POST /api/publish/checklist - Should publish to Confluence"""
        response = client.post(
            "/api/publish/checklist",
            json={
                "page_id": TEST_CONFLUENCE_PAGE_ID,
                "checklist": {
                    "project_name": "SmokeTest",
                    "customer": "Test Customer",
                    "categories": [{
                        "id": "test",
                        "name": "Test Category",
                        "items": [{
                            "prompt_id": "t1",
                            "question": "Test Question",
                            "answer": "Test Answer",
                            "status": "requirement_found"
                        }]
                    }]
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "page_url" in data
        TestResults.passed += 1
        TestResults.details.append(f"Publish: {data.get('page_url', 'success')}")


# =============================================================================
# Category 7: QA Endpoints
# =============================================================================

class TestQAEndpoints:
    """Quality assurance grading"""

    def test_get_rubric(self, client):
        """GET /api/qa/rubric - Should return grading rubric"""
        response = client.get("/api/qa/rubric")
        assert response.status_code == 200
        data = response.json()
        assert "dimensions" in data
        assert "total_points" in data
        TestResults.passed += 1


# =============================================================================
# Category 8: Ingest Endpoints
# =============================================================================

class TestIngestEndpoints:
    """File ingestion"""

    def test_ingest_no_files(self, client):
        """POST /api/ingest with no files should return 422"""
        response = client.post(
            "/api/ingest",
            data={"project_name": "Test"}
        )
        assert response.status_code == 422
        TestResults.passed += 1

    def test_ingest_with_file(self, client):
        """POST /api/ingest with file should return vector_store_id"""
        test_file = Path("C:/Users/tsmith/Desktop/2025-10745_V2.pdf")
        if not test_file.exists():
            pytest.skip("Test PDF not available")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/ingest",
                files={"files": ("test.pdf", f, "application/pdf")},
                data={"project_name": "IngestTest"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "vector_store_id" in data
        assert "session_id" in data
        TestResults.passed += 1


# =============================================================================
# Summary Report
# =============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Print summary after all tests"""
    print("\n" + "=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {TestResults.passed}")
    print(f"Failed: {TestResults.failed}")
    print(f"Skipped: {TestResults.skipped}")
    print("\nDetails:")
    for detail in TestResults.details:
        print(f"  - {detail}")
    print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
