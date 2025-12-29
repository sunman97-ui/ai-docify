"""
cost_estimator.py

Utility functions for estimating token usage and monetary cost for
LLM prompts based on provider/model pricing information.

The primary public function, `estimate_cost`, constructs the full prompt,
counts tokens—including optional tool-schema injection—and translates the
token count into a cost figure using provider-specific pricing metadata.
"""

from __future__ import annotations
import json
from typing import Any, Dict
import tiktoken
from .config import get_model_price
from .builder import build_messages
from .strategies import DOCSTRING_TOOL_SCHEMA


def estimate_cost(
    file_content: str,
    provider: str,
    model: str,
    mode: str = "rewrite",
) -> Dict[str, Any]:
    """
    Estimate the token count and monetary cost for a prompt.

    This helper bundles the entire workflow required for cost estimation:
    message construction, optional tool-schema injection, tokenization using
    the correct encoding, and price conversion through provider metadata.

    Parameters
    ----------
    file_content : str
        The source text that will populate the user message.
    provider : str
        Name of the LLM provider (e.g., ``"openai"``) used for price lookup.
    model : str
        Model identifier (e.g., ``"gpt-4"``) used for encoding selection and
        cost calculation.
    mode : str, default="rewrite"
        Prompt-construction strategy. When set to ``"inject"``, the function
        appends the tool schema to the prompt, increasing the token count.

    Returns
    -------
    dict
        A dictionary containing:

        ``"tokens"`` : int
            Total number of tokens in the prompt.
        ``"input_cost"`` : float
            Estimated cost in U.S. dollars for the input prompt.
        ``"currency"`` : str
            ``"USD"`` for paid models, or ``"Free/Local"`` when no cost is
            associated.
    """
    # ------------------------------------------------------------------------- #
    # --- Pricing Metadata Lookup --------------------------------------------- #
    # ------------------------------------------------------------------------- #
    price_info: Dict[str, Any] = get_model_price(provider, model)

    # ------------------------------------------------------------------------- #
    # --- Prompt Construction -------------------------------------------------- #
    # ------------------------------------------------------------------------- #
    # 1. Build messages according to the selected mode (loads the correct
    #    system/user prompt template).
    messages = build_messages(file_content, mode=mode)

    # Concatenate all message content for tokenization.
    full_text = "".join(msg["content"] for msg in messages)

    # 2. Append tool schema when operating in "inject" mode to reflect the
    #    actual prompt sent to the LLM.
    if mode == "inject":
        full_text += json.dumps(DOCSTRING_TOOL_SCHEMA)

    # ------------------------------------------------------------------------- #
    # --- Token Counting ------------------------------------------------------- #
    # ------------------------------------------------------------------------- #
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to a generic encoding when model-specific rules are missing.
        encoding = tiktoken.get_encoding("cl100k_base")

    # Each chat message wrapper contributes 4 additional tokens (OpenAI format).
    token_count: int = len(encoding.encode(full_text)) + (len(messages) * 4)

    # ------------------------------------------------------------------------- #
    # --- Cost Calculation ----------------------------------------------------- #
    # ------------------------------------------------------------------------- #
    input_price: float = price_info.get("input_cost_per_million", 0.0)

    estimated_cost: float = 0.0
    if input_price > 0:
        # Convert price per million tokens to price for the current prompt.
        estimated_cost = (token_count / 1_000_000) * input_price

    # ------------------------------------------------------------------------- #
    # --- Result Assembly ------------------------------------------------------ #
    # ------------------------------------------------------------------------- #
    return {
        "tokens": token_count,
        "input_cost": estimated_cost,
        "currency": "USD" if input_price > 0 else "Free/Local",
    }


__all__: list[str] = ["estimate_cost"]
