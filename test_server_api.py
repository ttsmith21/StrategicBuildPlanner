#!/usr/bin/env python3
"""
Test script for Strategic Build Planner API

Tests all endpoints in sequence to verify functionality.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8001"
TEST_FILES = [
    "inputs/sample_project_test.txt",
    "meetings/kickoff.txt"
]

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_result(success, message):
    status = "✓" if success else "✗"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {message}")

def test_health():
    """Test health endpoint"""
    print_header("TEST 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print_result(True, f"Health check passed: {data['status']}")
        return True
    except Exception as e:
        print_result(False, f"Health check failed: {e}")
        return False

def test_ingest():
    """Test file ingestion"""
    print_header("TEST 2: File Ingestion")
    try:
        files = []
        for fpath in TEST_FILES:
            if not Path(fpath).exists():
                print_result(False, f"Test file not found: {fpath}")
                return None
            files.append(('files', open(fpath, 'rb')))
        
        data = {
            'customer': 'ACME Corporation',
            'family': 'Bracket Assembly'
        }
        
        response = requests.post(f"{BASE_URL}/ingest", files=files, data=data)
        response.raise_for_status()
        result = response.json()
        
        print_result(True, f"Ingested {result['file_count']} files")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Files: {', '.join(result['file_names'])}")
        
        # Close file handles
        for _, f in files:
            f.close()
        
        return result['session_id']
    except Exception as e:
        print_result(False, f"Ingest failed: {e}")
        return None

def test_draft(session_id):
    """Test plan generation"""
    print_header("TEST 3: Plan Generation (Draft)")
    try:
        payload = {
            "session_id": session_id,
            "project_name": "ACME Bracket Test - API",
            "customer": "ACME Corporation"
        }
        
        print("  ⏳ Generating plan (this may take 30-60 seconds)...")
        response = requests.post(
            f"{BASE_URL}/draft",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        plan = result['plan_json']
        print_result(True, "Plan generated successfully")
        print(f"  Project: {plan['project']}")
        print(f"  Customer: {plan['customer']}")
        print(f"  Requirements: {len(plan['requirements'])}")
        print(f"  Risks: {len(plan['risks'])}")
        print(f"  Vector Store ID: {result['vector_store_id']}")
        print(f"  Markdown length: {len(result['plan_markdown'])} chars")
        
        return result
    except Exception as e:
        print_result(False, f"Draft generation failed: {e}")
        return None

def test_qa_grade(plan_result):
    """Test QA grading"""
    print_header("TEST 4: QA Grading")
    try:
        payload = {
            "plan_json": plan_result['plan_json']
        }
        
        print("  ⏳ Grading plan quality...")
        response = requests.post(
            f"{BASE_URL}/qa/grade",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        print_result(True, f"QA Grading completed")
        print(f"  Overall Score: {result['overall_score']:.1f}/100")
        print("\n  Dimension Scores:")
        for dim in result['dimensions']:
            print(f"    - {dim['dimension']}: {dim['score']}/100")
            if dim['reasons']:
                print(f"      Reasons: {dim['reasons'][0]}")
            if dim['fixes']:
                print(f"      Fixes: {dim['fixes'][0]}")
        
        return result
    except Exception as e:
        print_result(False, f"QA grading failed: {e}")
        return None

def test_meeting_apply(plan_result):
    """Test meeting notes application"""
    print_header("TEST 5: Meeting Notes Application")
    try:
        meeting_text = """
        # Follow-up Meeting - October 10, 2025
        
        Decision: Changed delivery date to Q2 2026.
        Action: Engineering to complete DFM review by Oct 20.
        Risk: Tooling lead time extended by 2 weeks.
        """
        
        payload = {
            "plan_json": plan_result['plan_json'],
            "transcript_texts": [meeting_text]
        }
        
        print("  ⏳ Applying meeting notes to plan...")
        response = requests.post(
            f"{BASE_URL}/meeting/apply",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        print_result(True, "Meeting notes applied")
        print(f"  Changes: {result['changes_summary']}")
        
        return result
    except Exception as e:
        print_result(False, f"Meeting apply failed: {e}")
        return None

def test_publish(plan_result):
    """Test Confluence publishing"""
    print_header("TEST 6: Confluence Publishing")
    
    # Check if Confluence is configured
    if not os.getenv("CONFLUENCE_BASE_URL"):
        print_result(False, "Skipped - Confluence not configured in .env")
        return None
    
    try:
        payload = {
            "customer": "ACME Corporation",
            "family": "Bracket Assembly",
            "project": "ACME Bracket Test - API",
            "markdown": plan_result['plan_markdown']
        }
        
        print("  ⏳ Publishing to Confluence...")
        response = requests.post(
            f"{BASE_URL}/publish",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        
        print_result(True, "Published to Confluence")
        print(f"  Page ID: {result['page_id']}")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        
        return result
    except Exception as e:
        print_result(False, f"Publish failed: {e}")
        # This is expected if Confluence credentials are placeholders
        if "404" in str(e) or "401" in str(e):
            print("  ℹ This is expected with placeholder Confluence credentials")
        return None

def test_cleanup(session_id):
    """Test session cleanup"""
    print_header("TEST 7: Session Cleanup")
    try:
        response = requests.delete(f"{BASE_URL}/session/{session_id}")
        response.raise_for_status()
        result = response.json()
        
        print_result(True, result['message'])
        return True
    except Exception as e:
        print_result(False, f"Cleanup failed: {e}")
        return False

def main():
    print_header("Strategic Build Planner API - Integration Tests")
    print(f"Target: {BASE_URL}")
    print(f"Test files: {', '.join(TEST_FILES)}")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests in sequence
    results = {
        'health': False,
        'ingest': False,
        'draft': False,
        'qa_grade': False,
        'meeting_apply': False,
        'publish': False,
        'cleanup': False
    }
    
    # 1. Health check
    results['health'] = test_health()
    if not results['health']:
        print("\n❌ Server not responding. Please start server first:")
        print("   python run_server.py")
        sys.exit(1)
    
    # 2. Ingest
    session_id = test_ingest()
    if not session_id:
        print("\n❌ Ingest failed. Cannot continue tests.")
        sys.exit(1)
    results['ingest'] = True
    
    # 3. Draft
    plan_result = test_draft(session_id)
    if not plan_result:
        print("\n❌ Draft generation failed. Cannot continue tests.")
        sys.exit(1)
    results['draft'] = True
    
    # 4. QA Grade
    qa_result = test_qa_grade(plan_result)
    results['qa_grade'] = qa_result is not None
    
    # 5. Meeting Apply
    meeting_result = test_meeting_apply(plan_result)
    results['meeting_apply'] = meeting_result is not None
    
    # 6. Publish (optional - may fail without valid Confluence)
    publish_result = test_publish(plan_result)
    results['publish'] = publish_result is not None
    
    # 7. Cleanup
    results['cleanup'] = test_cleanup(session_id)
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_status in results.items():
        print_result(passed_status, test_name.replace('_', ' ').title())
    
    print(f"\n{'='*70}")
    if passed == total:
        print(f"  🎉 ALL TESTS PASSED ({passed}/{total})")
    else:
        print(f"  ⚠ {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
