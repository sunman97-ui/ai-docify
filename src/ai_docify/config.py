"""
Utilities for loading and querying model pricing configuration.

This module provides functions to load a JSON-based pricing configuration
located adjacent to this file, to validate whether a provider/model pair
is defined, and to retrieve pricing details for a specific model.
"""

# --- Imports ---
import json
import logging
from pathlib import Path

# --- Module-level Constants ---
# Pricing file is expected to be adjacent to this file
CONFIG_PATH = Path(__file__).parent / "pricing.json"

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "openai": {
        "gpt-5-mini": {"input_cost_per_million": 0.25, "output_cost_per_million": 2.0}
    },
    "ollama": {
        "llama3.1:8b": {"input_cost_per_million": 0.0, "output_cost_per_million": 0.0}
    },
}

# --- Helper Functions ---


def load_config() -> dict:
    """
    Load configuration from pricing.json.
    """
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # Log the error and fall back to defaults
        logger.error("Error loading configuration: %s", e)
        return DEFAULT_CONFIG


def validate_model(provider: str, model: str) -> bool:
    """
    Check if a model is defined in the configuration.

    Parameters
    ----------
    provider : str
        The provider name (e.g., "openai"). Case-insensitive; will be lowercased.
    model : str
        The model identifier to check (e.g., "gpt-5-mini").

    Returns
    -------
    bool
        True if the provider exists in the configuration and the model is defined
        for that provider, False otherwise.
    """
    config = load_config()
    provider_key = provider.lower() if provider else ""
    provider_config = config.get(provider_key)

    if not provider_config:
        return False
    return model in provider_config


def get_model_price(provider: str, model: str) -> dict:
    """
    Get pricing details for a specific model.

    Parameters
    ----------
    provider : str
        The provider name (e.g., "openai"). Case-insensitive; will be lowercased.
    model : str
        The model identifier whose pricing details are requested.

    Returns
    -------
    dict
        A dictionary containing pricing fields (for example,
        {"input_cost_per_million": 0.25, "output_cost_per_million": 2.0}).
        Returns an empty dict if the provider or model is not found.
    """
    config = load_config()
    provider_key = provider.lower() if provider else ""
    return config.get(provider_key, {}).get(model, {})
