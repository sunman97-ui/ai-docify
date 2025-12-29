import pytest
import json
from unittest.mock import patch, mock_open

from src.ai_docify.builder import load_template, build_messages

# --- Test Data ---
MOCK_TEMPLATE = {
    "rewrite": {
        "system_prompt": "You are a helpful assistant that rewrites Python files to add docstrings.",
        "user_prompt": "Rewrite the following Python file to add docstrings:\n\n{raw_text}",
    },
    "inject": {
        "system_prompt": "You are a helpful assistant that generates docstrings for Python functions.",
        "user_prompt": "Generate a docstring for the following Python function:\n\n{raw_text}",
    },
}

# --- Tests for load_template ---

@patch("src.ai_docify.builder.Path.exists", return_value=True)
@patch("builtins.open")
def test_load_template_success(mock_open, mock_exists):
    """Test successful loading of a valid template file."""
    mock_file_content = json.dumps(MOCK_TEMPLATE)
    mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content
    
    template = load_template()
    
    assert template == MOCK_TEMPLATE

@patch("src.ai_docify.builder.Path.exists", return_value=False)
def test_load_template_file_not_found(mock_exists):
    """Test that FileNotFoundError is raised if template file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_template()

# --- Tests for build_messages ---

@patch("src.ai_docify.builder.load_template")
def test_build_messages_rewrite_mode(mock_load_template):
    """Test message building with the 'rewrite' mode."""
    mock_load_template.return_value = MOCK_TEMPLATE
    file_content = "def my_func(): pass"
    messages = build_messages(file_content, mode="rewrite")
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == MOCK_TEMPLATE["rewrite"]["system_prompt"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == MOCK_TEMPLATE["rewrite"]["user_prompt"].format(raw_text=file_content)

@patch("src.ai_docify.builder.load_template")
def test_build_messages_inject_mode(mock_load_template):
    """Test message building with the 'inject' mode."""
    mock_load_template.return_value = MOCK_TEMPLATE
    file_content = "def my_func(): pass"
    messages = build_messages(file_content, mode="inject")
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == MOCK_TEMPLATE["inject"]["system_prompt"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == MOCK_TEMPLATE["inject"]["user_prompt"].format(raw_text=file_content)

@patch("src.ai_docify.builder.load_template")
def test_build_messages_fallback_to_rewrite(mock_load_template):
    """Test that an invalid mode falls back to 'rewrite'."""
    mock_load_template.return_value = MOCK_TEMPLATE
    file_content = "def my_func(): pass"
    messages = build_messages(file_content, mode="invalid_mode")
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == MOCK_TEMPLATE["rewrite"]["system_prompt"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == MOCK_TEMPLATE["rewrite"]["user_prompt"].format(raw_text=file_content)
