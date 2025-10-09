"""
Test script for the Ingest API endpoint

Usage:
    python test_ingest.py
"""

import requests
import json
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/ingest"
PROJECT_NAME = "Test ACME Bracket Project"

# Test files directory
TEST_FILES_DIR = Path(__file__).parent.parent.parent / "inputs"


def test_ingest_endpoint():
    """Test the /api/ingest endpoint"""
    
    print("🧪 Testing Ingest API Endpoint")
    print(f"API URL: {API_URL}")
    print(f"Project: {PROJECT_NAME}")
    print("-" * 60)
    
    # Find test files
    test_files = list(TEST_FILES_DIR.glob("*.pdf")) + \
                 list(TEST_FILES_DIR.glob("*.txt")) + \
                 list(TEST_FILES_DIR.glob("*.docx"))
    
    if not test_files:
        print("❌ No test files found in inputs/ directory")
        print("   Please add some PDF, TXT, or DOCX files to test with")
        return
    
    print(f"📄 Found {len(test_files)} test files:")
    for f in test_files:
        print(f"   - {f.name}")
    print()
    
    # Prepare multipart form data
    files = []
    for test_file in test_files:
        files.append(
            ('files', (test_file.name, open(test_file, 'rb'), 'application/octet-stream'))
        )
    
    data = {
        'project_name': PROJECT_NAME
    }
    
    try:
        print("📤 Uploading files...")
        response = requests.post(API_URL, data=data, files=files)
        
        # Close file handles
        for _, (_, file_obj, _) in files:
            file_obj.close()
        
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Files ingested successfully")
            print()
            print("📊 Results:")
            print(f"   Session ID: {result['session_id']}")
            print(f"   Vector Store ID: {result['vector_store_id']}")
            print(f"   Total Files: {result['total_files']}")
            print(f"   Successful: {result['successful_uploads']}")
            print(f"   Failed: {result['failed_uploads']}")
            print(f"   Expires: {result['expires_at']}")
            print()
            print("📄 Files Processed:")
            for file_info in result['files_processed']:
                status = "✅" if file_info.get('file_id') else "❌"
                print(f"   {status} {file_info['filename']}")
                if file_info.get('char_count'):
                    print(f"      - Characters: {file_info['char_count']:,}")
                    print(f"      - Words: {file_info['word_count']:,}")
                if file_info.get('error'):
                    print(f"      - Error: {file_info['error']}")
            print()
            print("💾 Save this for draft generation:")
            print(f"   SESSION_ID={result['session_id']}")
            print(f"   VECTOR_STORE_ID={result['vector_store_id']}")
            
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API")
        print("   Make sure the backend server is running:")
        print("   cd backend && python -m app.main")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")


def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing Health Check...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
            print()
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except:
        print("❌ Server is not responding")
        print("   Start the server with: cd backend && python -m app.main")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Strategic Build Planner - Ingest API Test")
    print("=" * 60)
    print()
    
    # Check if server is running
    if not test_health_check():
        exit(1)
    
    # Run ingest test
    test_ingest_endpoint()
    
    print()
    print("=" * 60)
