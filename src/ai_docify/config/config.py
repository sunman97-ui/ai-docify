import json
from pathlib import Path

# Since this file is IN the config folder, we just look in the same directory
CONFIG_PATH = Path(__file__).parent / "pricing.json"


def load_config() -> dict:
    """Loads the full configuration registry."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_model(provider: str, model: str) -> bool:
    """Checks if the model is defined in the configuration for the given provider."""
    config = load_config()
    # Handle case-insensitivity safely
    provider_key = provider.lower() if provider else ""
    provider_config = config.get(provider_key)

    if not provider_config:
        return False

    return model in provider_config


def get_model_price(provider: str, model: str) -> dict:
    """Returns the pricing dict for a specific model."""
    config = load_config()
    provider_key = provider.lower() if provider else ""
    return config.get(provider_key, {}).get(model, {})
