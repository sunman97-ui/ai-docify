"""
Utilities for loading and querying model pricing configuration.

This module provides helpers to load a JSON-based pricing registry located
alongside this file (pricing.json), and to query whether a given provider
and model are present and to obtain the pricing details for a specific
model. The configuration is expected to be a mapping keyed by provider
identifiers (lowercased) to per-model pricing dictionaries.
"""

import json
from pathlib import Path

# Since this file is IN the config folder, we just look in the same directory
CONFIG_PATH = Path(__file__).parent / "pricing.json"


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
        will raise a FileNotFoundError.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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
    config = load_config()
    # Handle case-insensitivity safely
    provider_key = provider.lower() if provider else ""
    provider_config = config.get(provider_key)

    if not provider_config:
        return False

    return model in provider_config


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
    config = load_config()
    provider_key = provider.lower() if provider else ""
    return config.get(provider_key, {}).get(model, {})
