"""
Utilities for estimating token usage and monetary cost for LLM payloads.

This module provides helpers to calculate monetary cost from a token count and
to estimate token usage and cost for a payload constructed for an LLM. It
relies on centralized configuration and payload generation utilities to ensure
estimates match the actual generation behavior.
"""

from __future__ import annotations
import json
from typing import Any, Dict, Optional
import tiktoken
from .config import get_model_price
from .generator import prepare_llm_payload


# --- Helper Functions ------------------------------------------------------


def calculate_token_cost(tokens: int, price_per_million: float) -> float:
    """
    Calculate cost based on token count and price.

    Parameters
    ----------
    tokens : int
        Number of tokens.
    price_per_million : float
        Price per one million tokens.

    Returns
    -------
    float
        Estimated monetary cost for the given token count.
    """
    if price_per_million <= 0:
        return 0.0
    return (tokens / 1_000_000) * price_per_million


# --- Cost Estimation ------------------------------------------------------


def estimate_cost(
    file_content: str,
    provider: str,
    model: str,
    mode: str = "rewrite",
    function: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estimate token count and cost using the exact payload logic used for generation.

    Parameters
    ----------
    file_content : str
        The textual content of the file to be processed by the LLM.
    provider : str
        The provider identifier used to look up pricing information.
    model : str
        The model identifier used to select the tokenizer/encoding.
    mode : str
        Mode passed to the payload preparer (e.g., "rewrite", "summarize").
    function : str, optional
        The specific function being targeted, if any.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing:
        - "tokens": int number of estimated tokens,
        - "input_cost": float estimated cost for input tokens,
        - "currency": str currency or indicator (e.g., "USD" or "Free/Local").
    """
    price_info = get_model_price(provider, model)

    # 1. Get the authoritative payload from generator
    payload = prepare_llm_payload(file_content, mode=mode, function=function)

    messages = payload.get("messages", [])
    tools = payload.get("tools")

    # 2. Serialize for token counting
    # Concatenate message content
    full_text = "".join(msg["content"] for msg in messages)

    # Append tool schema if present (serialize structure for token estimation)
    if tools:
        full_text += json.dumps(tools)

    # 3. Count Tokens
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to a sensible default encoding when model-specific one is missing
        encoding = tiktoken.get_encoding("cl100k_base")

    # Add message overhead (approx 4 tokens per message for OpenAI-style protocols)
    # The overhead accounts for structural tokens
    # (role/name/delimiters) not present in raw content.
    token_count = len(encoding.encode(full_text)) + (len(messages) * 4)

    # 4. Calculate Cost
    input_price = price_info.get("input_cost_per_million", 0.0)
    estimated_cost = calculate_token_cost(token_count, input_price)

    return {
        "tokens": token_count,
        "input_cost": estimated_cost,
        "currency": "USD" if input_price > 0 else "Free/Local",
    }
