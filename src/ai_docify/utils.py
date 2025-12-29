import tiktoken
from .config import get_model_price
from .builder import build_messages

def estimate_cost(file_content: str, provider: str, model: str) -> dict:
    """
    Calculates token count for the FULL prompt (System + User + Code).
    """
    price_info = get_model_price(provider, model)
    
    # 1. Build the full message structure exactly as the API will see it
    messages = build_messages(file_content)
    
    # Combine all content to count tokens
    full_text = ""
    for msg in messages:
        full_text += msg["content"]
    
    # 2. Count Tokens
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback for models tiktoken doesn't explicitly know yet
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # We add a small buffer (overhead per message) usually ~3-4 tokens per msg
    token_count = len(encoding.encode(full_text)) + (len(messages) * 4)

    # 3. Calculate Cost
    estimated_cost = 0.0
    input_price = price_info.get("input_cost_per_million", 0)
    
    if input_price > 0:
        estimated_cost = (token_count / 1_000_000) * input_price

    return {
        "tokens": token_count,
        "input_cost": estimated_cost,
        "currency": "USD" if input_price > 0 else "Free/Local"
    }