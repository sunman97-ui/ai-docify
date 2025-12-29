import pytest
import json
from unittest.mock import patch, mock_open

from src.ai_docify.config.config import (
    load_config,
    validate_model,
    get_model_price,
)

# --- Test Data ---
MOCK_CONFIG = {
    "openai": {
        "gpt-4": {"input_cost_per_million": 10.0, "output_cost_per_million": 30.0},
        "gpt-3.5-turbo": {"input_cost_per_million": 0.5, "output_cost_per_million": 1.5},
    },
    "ollama": {
        "llama2": {"input_cost_per_million": 0.0, "output_cost_per_million": 0.0}
    },
}

# --- Tests for load_config ---

@patch("src.ai_docify.config.config.CONFIG_PATH")
def test_load_config_success(mock_path):
    """Test successful loading of a valid config file."""
    mock_path.exists.return_value = True
    mock_file_content = json.dumps(MOCK_CONFIG)
    
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
        config = load_config()
        assert config == MOCK_CONFIG
        mock_file.assert_called_with(mock_path, "r", encoding="utf-8")

@patch("src.ai_docify.config.config.CONFIG_PATH")
def test_load_config_file_not_found(mock_path):
    """Test that FileNotFoundError is raised if config file does not exist."""
    mock_path.exists.return_value = False
    with pytest.raises(FileNotFoundError):
        load_config()

# --- Tests for validate_model ---

@patch("src.ai_docify.config.config.load_config")
def test_validate_model_valid(mock_load_config):
    """Test validation with a valid provider and model."""
    mock_load_config.return_value = MOCK_CONFIG
    assert validate_model("openai", "gpt-4") is True
    assert validate_model("ollama", "llama2") is True

@patch("src.ai_docify.config.config.load_config")
def test_validate_model_invalid_provider(mock_load_config):
    """Test validation with an invalid provider."""
    mock_load_config.return_value = MOCK_CONFIG
    assert validate_model("invalid-provider", "gpt-4") is False

@patch("src.ai_docify.config.config.load_config")
def test_validate_model_invalid_model(mock_load_config):
    """Test validation with an invalid model for a valid provider."""
    mock_load_config.return_value = MOCK_CONFIG
    assert validate_model("openai", "invalid-model") is False

@patch("src.ai_docify.config.config.load_config")
def test_validate_model_case_insensitive(mock_load_config):
    """Test that provider validation is case-insensitive."""
    mock_load_config.return_value = MOCK_CONFIG
    assert validate_model("OpenAI", "gpt-4") is True

# --- Tests for get_model_price ---

@patch("src.ai_docify.config.config.load_config")
def test_get_model_price_valid(mock_load_config):
    """Test retrieving price for a valid provider and model."""
    mock_load_config.return_value = MOCK_CONFIG
    price = get_model_price("openai", "gpt-4")
    assert price == {"input_cost_per_million": 10.0, "output_cost_per_million": 30.0}

@patch("src.ai_docify.config.config.load_config")
def test_get_model_price_invalid_provider(mock_load_config):
    """Test retrieving price for an invalid provider."""
    mock_load_config.return_value = MOCK_CONFIG
    price = get_model_price("invalid-provider", "gpt-4")
    assert price == {}

@patch("src.ai_docify.config.config.load_config")
def test_get_model_price_invalid_model(mock_load_config):
    """Test retrieving price for an invalid model."""
    mock_load_config.return_value = MOCK_CONFIG
    price = get_model_price("openai", "invalid-model")
    assert price == {}
