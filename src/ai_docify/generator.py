from openai import OpenAI, OpenAIError
from rich.console import Console
from .builder import build_messages

console = Console()

def generate_documentation(
    file_content: str, provider: str, model: str, api_key: str | None
) -> str:
    """
    Generates documentation using the centralized prompt builder.
    """
    try:
        if provider == "ollama":
            # Ollama typically runs locally without an API key
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            console.print(f"Connecting to local Ollama with model [cyan]{model}[/]...")
        else: # Default to openai
            if not api_key:
                return "Error: OPENAI_API_KEY is not set. Please set it in your .env file."
            client = OpenAI(api_key=api_key)
            console.print(f"Connecting to OpenAI with model [cyan]{model}[/]...")

        # --- NEW LOGIC: Use Builder ---
        messages = build_messages(file_content)

        console.print("Generating documentation... (this may take a moment)")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        documented_code = response.choices[0].message.content

        # Clean the response to get only the code block
        if documented_code.startswith("```python"):
            documented_code = documented_code[len("```python"):].lstrip()
        if documented_code.endswith("```"):
            documented_code = documented_code[:-len("```")].rstrip()

        return documented_code

    except OpenAIError as e:
        return f"Error from API: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"