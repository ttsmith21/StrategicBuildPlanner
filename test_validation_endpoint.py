"""
Test the /validate endpoint with a real session.
"""

import requests
import json
from pathlib import Path

# Find the most recent session
sessions_dir = Path("outputs/sessions")
session_files = sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

if not session_files:
    print("No sessions found")
    exit(1)

# Load session to get ID
with open(session_files[0], 'r', encoding='utf-8') as f:
    session_data = json.load(f)
    session_id = session_data.get("session_id")

if not session_id:
    print("No session_id in session file")
    exit(1)

print(f"Testing validation for session: {session_id}")
print("=" * 60)

# Call the validation endpoint
try:
    response = requests.post(
        "http://localhost:8001/validate",
        json={"session_id": session_id},
        timeout=10
    )

    if response.status_code == 200:
        result = response.json()

        print(f"Ready: {result['is_ready']}")
        print(f"Completeness Score: {result['completeness_score']}%")
        print(f"\nErrors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  - {error['field']}: {error['message']}")

        print(f"\nWarnings: {len(result['warnings'])}")
        for warning in result['warnings']:
            print(f"  - {warning['field']}: {warning['message']}")

        print(f"\nSuggestions: {len(result['suggestions'])}")
        for suggestion in result['suggestions']:
            print(f"  - {suggestion['field']}: {suggestion['message']}")

        print(f"\nChecklist:")
        for item in result['checklist']:
            status = "COMPLETE" if item['status'] == 'complete' else "INCOMPLETE"
            req = "REQUIRED" if item['required'] else "OPTIONAL"
            print(f"  [{status}] {item['item']} ({req})")
            print(f"      {item['detail']}")

        print("\n" + "=" * 60)
        if result['is_ready']:
            print("SESSION IS READY FOR AGENTS")
        else:
            print("SESSION NOT READY - Fix errors above")
        print("=" * 60)

    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to server at http://localhost:8001")
    print("Make sure the server is running with: python run_server.py")
except Exception as e:
    print(f"ERROR: {e}")
