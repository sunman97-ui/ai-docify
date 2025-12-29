import json
from pathlib import Path

def load_template() -> dict:
    """Loads the documentation prompt template from the JSON file."""
    # Looks for docstring_generator.json in templates folder
    template_path = Path(__file__).parent / "templates" / "docstring_generator.json"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at: {template_path}")
        
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_messages(file_content: str) -> list[dict]:
    """
    Constructs the full list of messages (System + User) to be sent to the LLM.
    """
    template = load_template()
    
    # CHANGED: Access key only once now
    prompt_details = template["Code Comment & Docstring Generator"]
    
    system_prompt = prompt_details["system_prompt"]
    user_prompt = prompt_details["user_prompt"].format(raw_text=file_content)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]