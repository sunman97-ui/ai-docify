from typing import Tuple, Dict, Any
from openai import OpenAI, OpenAIError
from rich.console import Console
from .builder import build_messages

console = Console()

def generate_documentation(
    file_content: str, provider: str, model: str, api_key: str | None
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates documentation and returns the code AND detailed usage statistics.
    Returns: (documented_code, usage_dict)
    """
    try:
        if provider == "ollama":
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            console.print(f"Connecting to local Ollama with model [cyan]{model}[/]...")
        else: 
            if not api_key:
                return "Error: OPENAI_API_KEY is not set.", {}
            client = OpenAI(api_key=api_key)
            console.print(f"Connecting to OpenAI with model [cyan]{model}[/]...")

        messages = build_messages(file_content)

        console.print("Generating documentation... (this may take a moment)")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        # 1. Extract Content
        documented_code = response.choices[0].message.content

        # 2. Extract Detailed Token Usage
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0  
        }
        
        if response.usage:
            usage["input_tokens"] = response.usage.prompt_tokens
            usage["output_tokens"] = response.usage.completion_tokens
            
            # Check for reasoning tokens (common in 'o1', 'o3', 'gpt-5' series)
            if hasattr(response.usage, 'completion_tokens_details'):
                details = response.usage.completion_tokens_details
                # Safety check: some libs use dicts, others use objects
                if isinstance(details, dict):
                     usage["reasoning_tokens"] = details.get('reasoning_tokens', 0)
                else:
                     usage["reasoning_tokens"] = getattr(details, 'reasoning_tokens', 0)

        # 3. Clean the response
        if documented_code.startswith("```python"):
            documented_code = documented_code[len("```python"):].lstrip()
        if documented_code.endswith("```"):
            documented_code = documented_code[:-len("```")].rstrip()

        return documented_code, usage

    except OpenAIError as e:
        return f"Error from API: {e}", {}
    except Exception as e:
        return f"An unexpected error occurred: {e}", {}