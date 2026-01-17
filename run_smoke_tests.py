#!/usr/bin/env python
"""
Smoke Test Runner for Strategic Build Planner

Usage:
    python run_smoke_tests.py           # Run all tests
    python run_smoke_tests.py --quick   # Run only fast tests
    python run_smoke_tests.py --verbose # Verbose output
    python run_smoke_tests.py --html    # Generate HTML report

Prerequisites:
    1. Backend server running: cd backend && python -m uvicorn app.main:app --port 8000
    2. Environment configured: .env file with API keys
    3. Test files available (optional): Desktop/*.pdf
"""

import subprocess
import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
TESTS_DIR = BACKEND_DIR / "tests"
RESULTS_FILE = PROJECT_ROOT / "smoke_test_results.json"


def check_prerequisites():
    """Check that all prerequisites are met"""
    print("=" * 60)
    print("SMOKE TEST RUNNER - Strategic Build Planner")
    print("=" * 60)
    print("\nChecking prerequisites...")

    errors = []

    # Check backend server
    try:
        import httpx
        response = httpx.get("http://localhost:8000/docs", timeout=5.0)
        if response.status_code == 200:
            print("  [OK] Backend server running on port 8000")
        else:
            errors.append("Backend server not responding correctly")
    except Exception as e:
        errors.append(f"Cannot connect to backend: {e}")
        print("  [FAIL] Backend server not running")

    # Check .env file
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print("  [OK] .env file found")
    else:
        errors.append(".env file not found")
        print("  [WARN] .env file not found")

    # Check test files (optional)
    test_pdf = Path("C:/Users/tsmith/Desktop/2025-10745_V2.pdf")
    if test_pdf.exists():
        print("  [OK] Test PDF files available")
    else:
        print("  [WARN] Test PDF files not found (some tests will be skipped)")

    # Check pytest installed
    try:
        import pytest
        print(f"  [OK] pytest {pytest.__version__} installed")
    except ImportError:
        errors.append("pytest not installed")
        print("  [FAIL] pytest not installed")

    # Check httpx installed
    try:
        import httpx
        print(f"  [OK] httpx installed")
    except ImportError:
        errors.append("httpx not installed (pip install httpx)")
        print("  [FAIL] httpx not installed")

    print()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease fix the errors above before running tests.")
        return False

    return True


def run_tests(quick=False, verbose=False, html_report=False):
    """Run the smoke tests"""
    print("\nRunning smoke tests...")
    print("-" * 60)

    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        str(TESTS_DIR / "test_smoke.py"),
        "-v" if verbose else "-q",
        "--tb=short",
    ]

    if not quick:
        cmd.append("--runslow")

    if html_report:
        report_file = PROJECT_ROOT / f"smoke_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        cmd.extend(["--html", str(report_file), "--self-contained-html"])

    # Add color output
    cmd.append("--color=yes")

    # Run tests
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    return result.returncode


def save_results(return_code, duration):
    """Save test results to JSON file"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "return_code": return_code,
        "status": "PASSED" if return_code == 0 else "FAILED",
        "duration_seconds": duration,
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {RESULTS_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Run smoke tests for Strategic Build Planner")
    parser.add_argument("--quick", action="store_true", help="Run only fast tests (skip AI operations)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--skip-prereq", action="store_true", help="Skip prerequisite checks")

    args = parser.parse_args()

    # Check prerequisites
    if not args.skip_prereq:
        if not check_prerequisites():
            sys.exit(1)

    # Run tests
    start_time = datetime.now()
    return_code = run_tests(quick=args.quick, verbose=args.verbose, html_report=args.html)
    duration = (datetime.now() - start_time).total_seconds()

    # Print summary
    print("\n" + "=" * 60)
    if return_code == 0:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print(f"Duration: {duration:.1f} seconds")
    print("=" * 60)

    sys.exit(return_code)


if __name__ == "__main__":
    main()
