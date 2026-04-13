"""
Hermes WebUI - Test Fixtures
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Disable auth for tests by default
os.environ["HERMES_TEST_MODE"] = "1"


@pytest.fixture(autouse=True)
def disable_auth():
    """Disable authentication for all tests by default."""
    from auth import set_auth_enabled
    set_auth_enabled(False)
    yield
    set_auth_enabled(True)


@pytest.fixture
def client():
    """FastAPI test client with auth disabled."""
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client():
    """FastAPI test client with auth enabled."""
    from fastapi.testclient import TestClient
    from auth import set_auth_enabled, get_or_create_token
    from app import app

    set_auth_enabled(True)
    token = get_or_create_token()
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c
    set_auth_enabled(False)


@pytest.fixture
def token():
    """Get or create an auth token."""
    from auth import get_or_create_token
    return get_or_create_token()
