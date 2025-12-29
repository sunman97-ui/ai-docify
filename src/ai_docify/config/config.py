"""
Utilities for loading and querying model pricing configuration.

This module provides helpers to load a JSON-based pricing registry located
alongside this file (pricing.json), and to query whether a given provider
and model are present and to obtain the pricing details for a specific
model. The configuration is expected to be a mapping keyed by provider
identifiers (lowercased) to per-model pricing dictionaries.
"""

import json
import logging
from pathlib import Path
from rich.console import Console

# Since this file is IN the config folder, we just look in the same directory
CONFIG_PATH = Path(__file__).parent / "pricing.json"

# Get a module-specific logger
logger = logging.getLogger(__name__)

# Default minimal configuration for fallback
DEFAULT_CONFIG = {
    "openai": {
        "gpt-5-mini": {"input_cost_per_million": 0.25, "output_cost_per_million": 2.0}
    },
    "ollama": {
        "llama3.1:8b": {"input_cost_per_million": 0.0, "output_cost_per_million": 0.0}
    },
}


def load_config() -> dict:
    """
    Load the full configuration registry from the pricing.json file located in
    the same directory as this module.

    Parameters
    ----------
    None

    Returns
    -------
    dict
        Parsed JSON configuration as a mapping from provider keys (str) to their
        pricing data (dict). If the pricing.json file is missing, this function
        will use a minimal default configuration.
    """
    console = Console()

    if not CONFIG_PATH.exists():
        logger.warning(
            "Configuration file not found at: %s. Using default configuration.",
            CONFIG_PATH,
        )
        console.print(f"[yellow]Warning: pricing.json not found at {CONFIG_PATH}.[/]")
        console.print(
            "[yellow]Using minimal default configuration. "
            "Please create a proper config file for production use.[/]"
        )
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info("Successfully loaded configuration from %s", CONFIG_PATH)
            return config
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in configuration file: %s", e)
        console.print(f"[red]Error: Invalid JSON in pricing.json: {e}[/]")
        console.print("[yellow]Using default configuration as fallback.[/]")
        return DEFAULT_CONFIG
    except Exception as e:
        logger.error("Error loading configuration: %s", e)
        console.print(f"[red]Error loading pricing.json: {e}[/]")
        console.print("[yellow]Using default configuration as fallback.[/]")
        return DEFAULT_CONFIG


def validate_model(provider: str, model: str) -> bool:
    """
    Check whether a model is defined for a given provider in the pricing
    configuration.

    Parameters
    ----------
    provider : str
        Provider identifier to look up; lookup is performed case-insensitively
        by lowercasing this value before querying the configuration.
    model : str
        Model name to check for existence within the provider's pricing
        dictionary.

    Returns
    -------
    bool
        True if the provider exists in the configuration and the specified
        model is present for that provider; otherwise False.
    """
    try:
        config = load_config()
        # Handle case-insensitivity safely
        provider_key = provider.lower() if provider else ""
        provider_config = config.get(provider_key)

        if not provider_config:
            logger.warning("Provider '%s' not found in configuration", provider_key)
            return False

        is_valid = model in provider_config
        if not is_valid:
            logger.warning(
                "Model '%s' not found for provider '%s'", model, provider_key
            )
        return is_valid
    except Exception as e:
        logger.error("Error validating model: %s", e)
        return False


def get_model_price(provider: str, model: str) -> dict:
    """
    Return the pricing dictionary for a specific model under a provider.

    Parameters
    ----------
    provider : str
        Provider identifier to look up; this value is lowercased before
        performing the lookup in the loaded configuration.
    model : str
        Model name whose pricing dictionary should be returned.

    Returns
    -------
    dict
        The pricing dictionary for the requested model if found; otherwise an
        empty dict when either the provider or model is not present in the
        configuration.
    """
    try:
        config = load_config()
        provider_key = provider.lower() if provider else ""
        model_price = config.get(provider_key, {}).get(model, {})

        if not model_price:
            logger.warning(
                "No pricing information found for %s/%s", provider_key, model
            )

        return model_price
    except Exception as e:
        logger.error("Error retrieving model price: %s", e)
        return {}
