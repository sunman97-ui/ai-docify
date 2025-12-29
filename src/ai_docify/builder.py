import json
from pathlib import Path


def load_template() -> dict:
    """Loads the documentation prompt template from the JSON file."""
    template_path = Path(__file__).parent / "templates" / "docstring_generator.json"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_messages(file_content: str, mode: str = "rewrite") -> list[dict]:
    """
    Constructs the messages for the LLM based on the selected mode.
    """
    template = load_template()

    # 1. Select the correct prompt based on mode ('rewrite' or 'inject')
    # Fallback to 'rewrite' if something goes wrong, though CLI prevents this.
    prompt_details = template.get(mode, template.get("rewrite"))

    system_prompt = prompt_details["system_prompt"]
    user_prompt = prompt_details["user_prompt"].format(raw_text=file_content)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
