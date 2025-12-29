import pytest
import json
from unittest.mock import MagicMock, patch
from openai import OpenAIError

# Updated imports to reflect flat structure
from src.ai_docify.generator import (
    generate_documentation,
    prepare_llm_payload,
    DOCSTRING_TOOL_SCHEMA,
    AIDocifyError,
)

# --- Test Data ---
MOCK_TEMPLATE = {
    "rewrite": {
        "system_prompt": "System Rewrite",
        "user_prompt": "User Rewrite: {raw_text}",
    },
    "inject": {
        "system_prompt": "System Inject",
        "user_prompt": "User Inject: {raw_text}",
    },
}


@pytest.fixture
def mock_console():
    """Fixture for a mocked Rich Console to capture print output."""
    return MagicMock()


# --- Part 1: Schema & Payload Tests (Formerly test_strategies/test_builder) ---


def test_docstring_tool_schema_structure():
    """Test the structure of the tool schema constant."""
    assert isinstance(DOCSTRING_TOOL_SCHEMA, list)
    assert len(DOCSTRING_TOOL_SCHEMA) == 1
    tool = DOCSTRING_TOOL_SCHEMA[0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "generate_one_docstring"
    assert tool["function"]["strict"] is True


@patch("src.ai_docify.generator.Path.exists", return_value=True)
@patch("builtins.open")
def test_prepare_llm_payload_rewrite(mock_open_func, mock_exists):
    """Test payload construction for rewrite mode."""
    mock_open_func.return_value.__enter__.return_value.read.return_value = json.dumps(
        MOCK_TEMPLATE
    )

    file_content = "def foo(): pass"
    payload = prepare_llm_payload(file_content, mode="rewrite")

    assert "messages" in payload
    assert "tools" not in payload
    assert payload["messages"][0]["content"] == "System Rewrite"
    assert payload["messages"][1]["content"] == "User Rewrite: def foo(): pass"


@patch("src.ai_docify.generator.Path.exists", return_value=True)
@patch("builtins.open")
def test_prepare_llm_payload_inject(mock_open_func, mock_exists):
    """Test payload construction for inject mode (should include tools)."""
    mock_open_func.return_value.__enter__.return_value.read.return_value = json.dumps(
        MOCK_TEMPLATE
    )

    file_content = "def foo(): pass"
    payload = prepare_llm_payload(file_content, mode="inject")

    assert "messages" in payload
    assert "tools" in payload
    assert payload["tools"] == DOCSTRING_TOOL_SCHEMA


# --- Part 2: Generator Execution Tests ---


@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_ollama_connection(mock_openai, mock_console):
    """Test that Ollama provider initializes OpenAI client with local base_url."""
    # Setup mock to avoid crash
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
        console=mock_console,
    )

    mock_openai.assert_called_with(
        base_url="http://localhost:11434/v1", api_key="ollama"
    )


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
        console=mock_console,
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
            console=mock_console,
        )


@patch("src.ai_docify.generator.prepare_llm_payload")
@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_rewrite_success(
    mock_openai, mock_prepare, mock_console
):
    """Test successful rewrite mode with markdown stripping."""
    # Mock payload
    mock_prepare.return_value = {"messages": []}

    mock_client = mock_openai.return_value
    mock_response = MagicMock()

    # Simulate markdown code block response
    mock_response.choices[0].message.content = "```python\ndef foo(): pass\n```"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    # Mock reasoning tokens
    mock_response.usage.completion_tokens_details.reasoning_tokens = 5

    mock_client.chat.completions.create.return_value = mock_response

    doc_code, usage = generate_documentation(
        file_content="def foo(): pass",
        provider="openai",
        model="gpt-4",
        api_key="sk-test",
        mode="rewrite",
        console=mock_console,
    )

    assert doc_code == "def foo(): pass"
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 20
    assert usage["reasoning_tokens"] == 5


@patch("src.ai_docify.generator.insert_docstrings_to_source")
@patch("src.ai_docify.generator.prepare_llm_payload")
@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_inject_success(
    mock_openai, mock_prepare, mock_insert, mock_console
):
    """Test inject mode parsing tool calls and calling insertion logic."""
    # Mock payload
    mock_prepare.return_value = {"messages": [], "tools": []}

    mock_client = mock_openai.return_value
    mock_response = MagicMock()

    # Mock tool call
    tool_call = MagicMock()
    tool_call.function.name = "generate_one_docstring"
    tool_call.function.arguments = json.dumps(
        {"name": "my_func", "body": '"""Docstring"""'}
    )

    mock_response.choices[0].message.tool_calls = [tool_call]
    mock_client.chat.completions.create.return_value = mock_response

    # Mock insertion result
    mock_insert.return_value = 'def my_func():\n    """Docstring"""\n    pass'

    doc_code, usage = generate_documentation(
        file_content="def my_func(): pass",
        provider="openai",
        model="gpt-4",
        api_key="sk-test",
        mode="inject",
        console=mock_console,
    )

    # Verify insert was called
    mock_insert.assert_called_once()
    call_args = mock_insert.call_args
    assert call_args[0][1] == {"my_func": '"""Docstring"""'}
    assert "Docstring" in doc_code


@patch("src.ai_docify.generator.prepare_llm_payload")
@patch("src.ai_docify.generator.OpenAI")
def test_generate_documentation_api_error(mock_openai, mock_prepare, mock_console):
    """Test handling of OpenAIError."""
    mock_prepare.return_value = {"messages": []}
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = OpenAIError("API Down")

    with pytest.raises(AIDocifyError, match="API error: API Down"):
        generate_documentation(
            file_content="pass",
            provider="openai",
            model="gpt-4",
            api_key="sk-test",
            console=mock_console,
        )
