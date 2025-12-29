# Project Codebase Audit Context
# Root: C:\Users\adm!n\software\ai-docify

--- pyproject.toml ---
```toml
[project]
name = "ai-docify"
version = "0.1.0"
description = "A simple CLI tool for generating safe, high-quality, NumPy/Sphinx style docstrings."
requires-python = ">=3.8"
dependencies = [
    "click",
    "openai",
    "python-dotenv",
    "rich",
    "pytest",
    "tiktoken"
]

[project.scripts]
ai-docify = "ai_docify.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

# CRITICAL: This ensures the JSON template is packaged with the code
[tool.setuptools.package-data]
ai_docify = ["templates/*.json", "config/*.json"]
```

--- src\ai_docify\builder.py ---
```python
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
```

--- src\ai_docify\cli.py ---
```python
import os
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.prompt import Confirm
from dotenv import load_dotenv
from .generator import generate_documentation
from .utils import estimate_cost
from .config import validate_model, get_model_price 

load_dotenv()

@click.command()
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option(
    "--provider",
    required=True,
    type=click.Choice(["openai", "ollama"], case_sensitive=False),
    help="The AI provider (Must be defined in pricing.json).",
)
@click.option(
    "--model",
    required=True,
    help="The specific model name (Must be defined in pricing.json).",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt."
)
def main(filepath, provider, model, yes):
    """
    Generates NumPy/Sphinx style docstrings for a Python file.
    """
    console = Console()
    
    # 1. Validate Configuration
    if not validate_model(provider, model):
        console.print(f"[bold red]Error:[/bold red] Model '[cyan]{model}[/]' is not configured for provider '[cyan]{provider}[/]' in your pricing.json.")
        sys.exit(1)

    console.print(f"🤖 [bold green]ai-docify[/]: Checking [cyan]{filepath}[/]")

    try:
        path_obj = Path(filepath)
        with open(path_obj, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 2. Cost Estimation (Pre-Flight)
        estimates = estimate_cost(original_content, provider, model)
        console.print("\n📊 [bold]Estimation (Input Only):[/bold]")
        console.print(f"   Tokens: [cyan]{estimates['tokens']}[/]")
        
        if estimates["currency"] == "USD":
            console.print(f"   Est. Cost: [green]${estimates['input_cost']:.5f}[/]")
        else:
            console.print(f"   Est. Cost: [bold blue]Free (Local/Ollama)[/]")

        # 3. Confirmation
        if not yes:
            console.print("") 
            if not Confirm.ask("Do you want to proceed?"):
                console.print("[yellow]Aborted by user.[/]")
                return

        # 4. Generate documentation
        api_key = os.getenv("OPENAI_API_KEY")
        
        with console.status(f"Generating docs using [cyan]{model}[/]...", spinner="dots"):
            # UNPACK THE TUPLE HERE
            documented_content, usage_stats = generate_documentation(
                file_content=original_content,
                provider=provider,
                model=model,
                api_key=api_key
            )

        if documented_content.startswith("Error"):
            console.print(f"[bold red]{documented_content}[/]")
            return

        # 5. Write to 'ai_output' folder
        output_dir = Path("ai_output")
        output_dir.mkdir(exist_ok=True)
        
        output_filename = f"{path_obj.stem}.doc.py"
        output_path = output_dir / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(documented_content)

        console.print(f"\n✅ Successfully generated documentation!")
        console.print(f"   Output saved to: [bold yellow]{output_path}[/]")

        # 6. Final Usage Report (Post-Flight)
        price_info = get_model_price(provider, model)
        input_price = price_info.get("input_cost_per_million", 0)
        output_price = price_info.get("output_cost_per_million", 0)

        in_tokens = usage_stats.get("input_tokens", 0)
        out_tokens = usage_stats.get("output_tokens", 0)
        reasoning_tokens = usage_stats.get("reasoning_tokens", 0) 
        
        total_cost = 0.0
        if input_price > 0:
            input_cost = (in_tokens / 1_000_000) * input_price
            output_cost = (out_tokens / 1_000_000) * output_price
            total_cost = input_cost + output_cost

            console.print("\n📉 [bold]Final Usage Report:[/bold]")
            console.print(f"   Input Tokens:     [cyan]{in_tokens}[/]")
            console.print(f"   Output Tokens:    [cyan]{out_tokens}[/]")
            
            # Show reasoning tokens if they exist
            if reasoning_tokens > 0:
                console.print(f"   (Includes [yellow]{reasoning_tokens}[/] reasoning tokens)")
                
            console.print(f"   Total Cost:       [bold green]${total_cost:.5f}[/]")
        else:
            console.print("\n📉 [bold]Final Usage Report:[/bold]")
            console.print(f"   Output Tokens: [cyan]{out_tokens}[/]")
            console.print(f"   Total Cost:    [bold blue]Free[/]")

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred in the CLI: {e}[/]")

if __name__ == "__main__":
    main()
```

--- src\ai_docify\generator.py ---
```python
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
```

--- src\ai_docify\utils.py ---
```python
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
```

--- src\ai_docify\__init__.py ---
```python

```

--- src\ai_docify\config\config.py ---
```python
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
```

--- src\ai_docify\config\pricing.json ---
```json
{
  "openai": {
    "gpt-5-mini": {
      "input_cost_per_million": 0.25,
      "output_cost_per_million": 2.00
    },
    "gpt-5-nano": {
      "input_cost_per_million": 0.05,
      "output_cost_per_million": 0.40
    }
  },
  "ollama": {
    "llama3.1:8b": {
      "input_cost_per_million": 0.0,
      "output_cost_per_million": 0.0
    }
  }
}
```

--- src\ai_docify\config\__init__.py ---
```python
from .config import load_config, validate_model, get_model_price
```

--- src\ai_docify\templates\docstring_generator.json ---
```json
{
        "Code Comment & Docstring Generator": {
            "category": "Python Related",
            "output_type": "text",
            "metadata": {
                "version": "2.0",
                "complexity_level": "advanced",
                "description": "Analyzes a Python script and adds explanatory comments and PEP 257 compliant docstrings using a specific, professional style."
            },
            "variables": {
                "raw_text": {
                    "type": "file",
                    "accepts": [
                        ".py"
                    ],
                    "description": "The Python script file to be documented.",
                    "required": true
                }
            },
            "system_prompt": "You are an expert Python Documentation Engineer. Your ONLY output is executable Python code. You never explain your work or chat. You strictly enforce NumPy/Sphinx documentation standards.",
            "user_prompt": "I will provide you with a Python script. Your task is to rewrite the script to include professional documentation while preserving all original logic.\n\n### STRICT STYLE GUIDELINES ###\n\n1. **Module Docstring**: The file MUST start with a high-level docstring summarizing the module's purpose.\n\n2. **NumPy Style Docstrings**: Every function and class must have a docstring following this exact format:\n   \"\"\"\n   Short summary.\n\n   Parameters\n   ----------\n   param_name : type\n       Description of the parameter.\n\n   Returns\n   -------\n   type\n       Description of the return value.\n   \"\"\"\n\n3. **Type Inference**: You MUST infer types for 'Parameters' and 'Returns' even if they are missing in the signature (e.g., denote as 'int | float' or 'Any').\n\n4. **Visual Separation**: Group logical sections of functions using ASCII-art headers, exactly like this:\n   # --- Section Name ---\n\n5. **Inline Comments**: Add concise inline comments only for complex logic, explaining the 'why', not the 'what'.\n\n### INPUT CODE ###\n```python\n{raw_text}\n```\n\n### RESPONSE FORMAT ###\nReturn ONLY the valid Python code inside a markdown block.",
            "examples": [],
            "validation_criteria": "The output must be the complete, original Python script with added docstrings and comments, strictly following the NumPy/Sphinx style."
        }
    }
```

