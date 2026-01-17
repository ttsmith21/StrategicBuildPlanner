"""
Pytest configuration and shared fixtures for smoke tests
"""

import pytest
import httpx
import os

# Test configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TIMEOUT = 180.0  # 3 minutes for AI operations


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (AI operations)"
    )
    config.addinivalue_line(
        "markers", "requires_confluence: marks tests requiring Confluence access"
    )
    config.addinivalue_line(
        "markers", "requires_openai: marks tests requiring OpenAI API"
    )


@pytest.fixture(scope="session")
def api_client():
    """Shared HTTP client for all tests"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def check_server_running(api_client):
    """Verify server is running before tests"""
    try:
        response = api_client.get("/docs")
        if response.status_code != 200:
            pytest.exit("Backend server not responding correctly")
    except httpx.ConnectError:
        pytest.exit(f"Cannot connect to backend at {BASE_URL}. Is the server running?")


def pytest_collection_modifyitems(config, items):
    """Skip slow tests unless --runslow is passed"""
    if not config.getoption("--runslow", default=False):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
