import pytest
from unittest.mock import MagicMock
import sys
import os

# Ensure src is in path so we can import ai_docify
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


@pytest.fixture
def mock_openai_client(mocker):
    """
    Fixture to mock the OpenAI client.
    This prevents actual API calls during testing.
    """
    # We mock the module where the client is instantiated or used.
    # Assuming usage inside generator.py or similar.
    # For now, we return a generic mock that tests can configure.
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def sample_python_code():
    """Returns a string of valid Python code for testing parsing/rewriting."""
    return "def hello():\n    print('world')"
