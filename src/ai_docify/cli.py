import os
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.prompt import Confirm
from dotenv import load_dotenv
from .generator import generate_documentation
from .utils import estimate_cost
from .config import validate_model

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
    # This prevents using random models or typos
    if not validate_model(provider, model):
        console.print(f"[bold red]Error:[/bold red] Model '[cyan]{model}[/]' is not configured for provider '[cyan]{provider}[/]' in your pricing.json.")
        sys.exit(1)

    console.print(f"🤖 [bold green]ai-docify[/]: Checking [cyan]{filepath}[/]")

    try:
        # Read the input file
        path_obj = Path(filepath)
        with open(path_obj, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 2. Cost Estimation
        # Uses the new nested config logic
        estimates = estimate_cost(original_content, provider, model)
        tokens = estimates["tokens"]
        cost = estimates["input_cost"]
        
        console.print("\n📊 [bold]Estimation:[/bold]")
        console.print(f"   Tokens: [cyan]{tokens}[/]")
        
        if estimates["currency"] == "USD":
            console.print(f"   Est. Cost: [green]${cost:.5f}[/]")
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
            documented_content = generate_documentation(
                file_content=original_content,
                provider=provider,
                model=model,
                api_key=api_key
            )

        if documented_content.startswith("Error"):
            console.print(f"[bold red]{documented_content}[/]")
            return

        # 5. Write to 'ai_output' folder
        # Ensures source directories stay clean
        output_dir = Path("ai_output")
        output_dir.mkdir(exist_ok=True)
        
        output_filename = f"{path_obj.stem}.doc.py"
        output_path = output_dir / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(documented_content)

        console.print(f"\n✅ Successfully generated documentation!")
        console.print(f"   Output saved to: [bold yellow]{output_path}[/]")

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred in the CLI: {e}[/]")

if __name__ == "__main__":
    main()