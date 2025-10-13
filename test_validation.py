"""
Test validation module for pre-flight checks.

Verifies that sessions are properly validated before agent execution.
"""

import logging
from server.lib.validation import (
    validate_session_for_agents,
    get_validation_checklist,
    ValidationLevel,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_valid_session():
    """Test a complete, valid session"""
    print("\n" + "=" * 60)
    print("TEST 1: Valid Session")
    print("=" * 60)

    session = {
        "session_id": "test-123",
        "project_name": "ACME Bracket",
        "customer": "ACME Corp",
        "family": "Brackets",
        "vector_store_id": "vs_abc123",
        "context_pack": {
            "sources": [
                {"id": "src1", "kind": "drawing"},
                {"id": "src2", "kind": "po"},
            ],
            "facts": [
                {"id": "fact1", "claim": "Material: 304 SS"},
                {"id": "fact2", "claim": "Thickness: 0.125in"},
            ],
        },
        "uploaded_files": ["drawing.pdf", "po.pdf"],
    }

    result = validate_session_for_agents(session)

    print(f"Ready: {result.is_ready}")
    print(f"Completeness: {result.completeness_score}%")
    print(f"Errors: {len(result.to_dict()['errors'])}")
    print(f"Warnings: {len(result.to_dict()['warnings'])}")

    assert result.is_ready, "Session should be ready"
    assert result.completeness_score >= 70, f"Score should be >=70%, got {result.completeness_score}%"
    assert not result.has_errors(), "Should have no errors"

    print("✓ Valid session passed all checks")


def test_missing_files():
    """Test session without uploaded files"""
    print("\n" + "=" * 60)
    print("TEST 2: Missing Files")
    print("=" * 60)

    session = {
        "session_id": "test-456",
        "project_name": "Test Project",
        "customer": "Test Customer",
    }

    result = validate_session_for_agents(session)

    print(f"Ready: {result.is_ready}")
    print(f"Completeness: {result.completeness_score}%")
    print(f"Errors: {len(result.to_dict()['errors'])}")

    assert not result.is_ready, "Session should NOT be ready without files"
    assert result.has_errors(), "Should have errors"

    errors = result.to_dict()['errors']
    assert any("vector_store" in str(e).lower() for e in errors), "Should have vector store error"

    print("✓ Missing files correctly detected as error")


def test_missing_project_name():
    """Test session without project name"""
    print("\n" + "=" * 60)
    print("TEST 3: Missing Project Name")
    print("=" * 60)

    session = {
        "session_id": "test-789",
        "vector_store_id": "vs_xyz",
        "context_pack": {
            "sources": [{"id": "src1"}],
            "facts": [],
        },
    }

    result = validate_session_for_agents(session)

    print(f"Ready: {result.is_ready}")
    print(f"Errors: {len(result.to_dict()['errors'])}")

    assert not result.is_ready, "Session should NOT be ready without project name"

    errors = result.to_dict()['errors']
    assert any("project" in str(e).lower() for e in errors), "Should have project name error"

    print("✓ Missing project name correctly detected")


def test_completeness_scoring():
    """Test completeness scoring algorithm"""
    print("\n" + "=" * 60)
    print("TEST 4: Completeness Scoring")
    print("=" * 60)

    # Minimal session (should score low)
    minimal = {
        "session_id": "min",
        "project_name": "Min Project",
        "vector_store_id": "vs_1",
        "context_pack": {"sources": [{"id": "s1"}], "facts": []},
        "uploaded_files": ["file1.pdf"],
    }

    result_min = validate_session_for_agents(minimal)
    score_min = result_min.completeness_score

    # Complete session (should score high)
    complete = {
        "session_id": "complete",
        "project_name": "Complete Project",
        "customer": "Complete Customer",
        "family": "Complete Family",
        "vector_store_id": "vs_2",
        "context_pack": {
            "sources": [{"id": f"s{i}"} for i in range(5)],
            "facts": [{"id": f"f{i}", "claim": f"Fact {i}"} for i in range(20)],
        },
        "uploaded_files": [f"file{i}.pdf" for i in range(5)],
    }

    result_complete = validate_session_for_agents(complete)
    score_complete = result_complete.completeness_score

    print(f"Minimal score: {score_min}%")
    print(f"Complete score: {score_complete}%")

    assert score_min < score_complete, "Complete session should score higher"
    assert score_complete >= 80, f"Complete session should score >=80%, got {score_complete}%"

    print("✓ Completeness scoring working correctly")


def test_checklist():
    """Test checklist generation"""
    print("\n" + "=" * 60)
    print("TEST 5: Checklist Generation")
    print("=" * 60)

    session = {
        "session_id": "checklist-test",
        "project_name": "Test Project",
        "vector_store_id": "vs_test",
        "context_pack": {"sources": [{"id": "s1"}], "facts": []},
        "uploaded_files": ["file.pdf"],
    }

    checklist = get_validation_checklist(session)

    print(f"Checklist items: {len(checklist)}")
    for item in checklist:
        status_icon = "✓" if item["status"] == "complete" else "✗"
        req_icon = "(required)" if item["required"] else "(optional)"
        print(f"  {status_icon} {item['item']} {req_icon}: {item['detail']}")

    assert len(checklist) >= 4, "Should have at least 4 checklist items"

    # Check that required items are marked
    required_items = [item for item in checklist if item["required"]]
    assert len(required_items) >= 2, "Should have at least 2 required items"

    print("✓ Checklist generation working correctly")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING VALIDATION MODULE")
    print("=" * 60)

    try:
        test_valid_session()
        test_missing_files()
        test_missing_project_name()
        test_completeness_scoring()
        test_checklist()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
