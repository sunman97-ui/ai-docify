import json
import tiktoken
from .config import get_model_price
from .builder import build_messages
from .strategies import DOCSTRING_TOOL_SCHEMA

def estimate_cost(file_content: str, provider: str, model: str, mode: str = "rewrite") -> dict:
    """
    Calculates token count for the FULL prompt (System + User + Code + [Tools]).
    """
    price_info = get_model_price(provider, model)
    
    # 1. Build messages using the specific mode (loads correct prompt)
    messages = build_messages(file_content, mode=mode)
    
    full_text = ""
    for msg in messages:
        full_text += msg["content"]
        
    # 2. Add Tool Schema cost if in 'inject' mode
    if mode == "inject":
        full_text += json.dumps(DOCSTRING_TOOL_SCHEMA)

    # 3. Count Tokens
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    token_count = len(encoding.encode(full_text)) + (len(messages) * 4)

    # 4. Calculate Cost
    estimated_cost = 0.0
    input_price = price_info.get("input_cost_per_million", 0)
    
    if input_price > 0:
        estimated_cost = (token_count / 1_000_000) * input_price

    return {
        "tokens": token_count,
        "input_cost": estimated_cost,
        "currency": "USD" if input_price > 0 else "Free/Local"
    }