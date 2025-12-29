import pytest
import json
from unittest.mock import MagicMock, patch
from openai import OpenAIError

# Using the requested import path
from src.ai_docify.generator import generate_documentation, AIDocifyError

@pytest.fixture
def mock_console():
    """Fixture for a mocked Rich Console to capture print output."""
    return MagicMock()

@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_ollama_connection(mock_openai, mock_console):
    """Test that Ollama provider initializes OpenAI client with local base_url."""
    # Setup mock return to avoid crash on chat.completions.create
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="code"))
    ]
    
    generate_documentation(
        file_content="pass",
        provider="ollama",
        model="llama2",
        api_key=None,
        mode="rewrite",
        console=mock_console
    )
    
    # Verify OpenAI init args for Ollama
    mock_openai.assert_called_with(base_url="http://localhost:11434/v1", api_key="ollama")

@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_openai_connection(mock_openai, mock_console):
    """Test that OpenAI provider initializes client with api_key."""
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="code"))
    ]

    generate_documentation(
        file_content="pass",
        provider="openai",
        model="gpt-4",
        api_key="sk-test",
        mode="rewrite",
        console=mock_console
    )

    mock_openai.assert_called_with(api_key="sk-test")

def test_generate_documentation_missing_api_key(mock_console):
    """Test error when API key is missing for non-Ollama provider."""
    with pytest.raises(AIDocifyError, match="API key is required for OpenAI"):
        generate_documentation(
            file_content="pass",
            provider="openai",
            model="gpt-4",
            api_key=None,
            console=mock_console
        )

@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_rewrite_success(mock_openai, mock_console):
    """Test successful rewrite mode with markdown stripping."""
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    
    # Simulate markdown code block response
    mock_response.choices[0].message.content = "```python\ndef foo(): pass\n```"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    # Mock reasoning tokens attribute
    mock_response.usage.completion_tokens_details.reasoning_tokens = 5
    
    mock_client.chat.completions.create.return_value = mock_response

    doc_code, usage = generate_documentation(
        file_content="def foo(): pass",
        provider="openai",
        model="gpt-4",
        api_key="sk-test",
        mode="rewrite",
        console=mock_console
    )

    # Check markdown stripping
    assert doc_code == "def foo(): pass"
    # Check usage stats
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 20
    assert usage["reasoning_tokens"] == 5

@patch("src.ai_docify.generator.insert_docstrings_to_source")
@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_inject_success(mock_openai, mock_insert, mock_console):
    """Test inject mode parsing tool calls and calling insertion logic."""
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    
    # Mock tool call
    tool_call = MagicMock()
    tool_call.function.name = "generate_one_docstring"
    tool_call.function.arguments = json.dumps({
        "name": "my_func",
        "body": '"""Docstring"""'
    })
    
    mock_response.choices[0].message.tool_calls = [tool_call]
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock insertion result
    mock_insert.return_value = "def my_func():\n    \"\"\"Docstring\"\"\"\n    pass"

    doc_code, usage = generate_documentation(
        file_content="def my_func(): pass",
        provider="openai",
        model="gpt-4",
        api_key="sk-test",
        mode="inject",
        console=mock_console
    )

    # Verify insert was called with correct map
    mock_insert.assert_called_once()
    call_args = mock_insert.call_args
    # args[0] is file_content, args[1] is docstring_map
    assert call_args[0][1] == {"my_func": '"""Docstring"""'}
    assert "Docstring" in doc_code

@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_api_error(mock_openai, mock_console):
    """Test handling of OpenAIError."""
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = OpenAIError("API Down")

    with pytest.raises(AIDocifyError, match="API error: API Down"):
        generate_documentation(
            file_content="pass",
            provider="openai",
            model="gpt-4",
            api_key="sk-test",
            console=mock_console
        )