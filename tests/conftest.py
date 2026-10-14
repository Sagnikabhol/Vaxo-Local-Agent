"""
Pytest configuration for Vaxo test suite.

Adds the project root to the Python path and provides shared fixtures.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from config.settings import Settings


@pytest.fixture
def settings():
    """Provide fresh settings for each test."""
    return Settings()


@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary database path for testing."""
    return str(tmp_path / "test_vaxo.db")
