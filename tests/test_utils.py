import pytest
from unittest.mock import patch, MagicMock
from src.ai_docify.utils import calculate_token_cost, estimate_cost


# --- Tests for calculate_token_cost ---


def test_calculate_token_cost_basic():
    """Test standard cost calculation."""
    # 1 million tokens at $5.00
    assert calculate_token_cost(1_000_000, 5.0) == 5.0
    # 500 tokens at $1.00 per million
    assert calculate_token_cost(500, 1.0) == 0.0005


def test_calculate_token_cost_zero_price():
    """Test that zero price returns zero cost."""
    assert calculate_token_cost(1000, 0.0) == 0.0


def test_calculate_token_cost_negative_price():
    """Test that negative price returns zero (safety check)."""
    assert calculate_token_cost(1000, -10.0) == 0.0


# --- Tests for estimate_cost ---


@patch("src.ai_docify.utils.get_model_price")
@patch("src.ai_docify.utils.prepare_llm_payload")
@patch("src.ai_docify.utils.tiktoken")
def test_estimate_cost_paid_model(
    mock_tiktoken, mock_prepare_payload, mock_get_model_price
):
    """Test estimation flow for a paid model (e.g., OpenAI)."""
    # 1. Setup Mocks
    mock_get_model_price.return_value = {"input_cost_per_million": 10.0}

    # Mock payload: 2 messages
    mock_prepare_payload.return_value = {
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]
    }

    # Mock Tokenizer
    mock_encoding = MagicMock()
    # Simulate "sys" + "usr" = 6 tokens
    mock_encoding.encode.return_value = [1, 2, 3, 4, 5, 6]
    mock_tiktoken.encoding_for_model.return_value = mock_encoding

    # 2. Execute
    result = estimate_cost(
        "file_content", "openai", "gpt-4", mode="rewrite", function=None
    )

    # 3. Verify Logic
    # Token count = len(encode("sysusr")) + (len(messages) * 4)
    #             = 6 + (2 * 4) = 14 tokens

    expected_tokens = 6 + 8
    expected_cost = (expected_tokens / 1_000_000) * 10.0

    assert result["tokens"] == expected_tokens
    assert result["input_cost"] == pytest.approx(expected_cost)
    assert result["currency"] == "USD"

    # Verify calls
    mock_get_model_price.assert_called_with("openai", "gpt-4")
    mock_prepare_payload.assert_called_with(
        "file_content", mode="rewrite", function=None
    )
    mock_tiktoken.encoding_for_model.assert_called_with("gpt-4")


@patch("src.ai_docify.utils.get_model_price")
@patch("src.ai_docify.utils.prepare_llm_payload")
@patch("src.ai_docify.utils.tiktoken")
def test_estimate_cost_free_model(
    mock_tiktoken, mock_prepare_payload, mock_get_model_price
):
    """Test estimation flow for a free/local model."""
    mock_get_model_price.return_value = {"input_cost_per_million": 0.0}
    mock_prepare_payload.return_value = {
        "messages": [{"role": "user", "content": "test"}]
    }

    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1]
    mock_tiktoken.encoding_for_model.return_value = mock_encoding

    result = estimate_cost("content", "ollama", "llama2")

    assert result["input_cost"] == 0.0
    assert result["currency"] == "Free/Local"


@patch("src.ai_docify.utils.tiktoken")
def test_estimate_cost_tiktoken_fallback(mock_tiktoken):
    """Test fallback to cl100k_base if model encoding not found."""
    mock_tiktoken.encoding_for_model.side_effect = KeyError("Model not found")

    mock_fallback = MagicMock()
    mock_fallback.encode.return_value = []
    mock_tiktoken.get_encoding.return_value = mock_fallback

    with patch("src.ai_docify.utils.get_model_price") as mock_get_price, patch(
        "src.ai_docify.utils.prepare_llm_payload"
    ) as mock_prepare:

        mock_get_price.return_value = {"input_cost_per_million": 0.0}
        mock_prepare.return_value = {"messages": []}

        estimate_cost("content", "provider", "unknown-model")

        mock_tiktoken.get_encoding.assert_called_with("cl100k_base")
