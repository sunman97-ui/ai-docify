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
    "--mode",
    type=click.Choice(["rewrite", "inject"], case_sensitive=False),
    default="rewrite",
    help=(
        "Operation mode. 'rewrite' (Default) regenerates the file."
        "'inject' uses function calling to insert docs safely"
        "(Requires compatible model)."
    ),
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def main(filepath, provider, model, mode, yes):
    """
    Generates NumPy/Sphinx style docstrings for a Python file.
    """
    console = Console()

    # 1. Validate Configuration
    if not validate_model(provider, model):
        console.print(
            f"[bold red]Error:[/bold red] Model '[cyan]{model}[/]'"
            f"' is not configured for provider '[cyan]{provider}[/]'"
            f" in your pricing.json."
        )
        sys.exit(1)

    console.print(
        f"🤖 [bold green]ai-docify[/]: Checking [cyan]{filepath}[/]"
        f" in [yellow]{mode.upper()}[/] mode"
    )

    try:
        path_obj = Path(filepath)
        with open(path_obj, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 2. Cost Estimation (Pre-Flight)
        # PASS THE MODE HERE
        estimates = estimate_cost(original_content, provider, model, mode=mode)
        console.print("\n📊 [bold]Estimation (Input Only):[/bold]")
        console.print(f"   Tokens: [cyan]{estimates['tokens']}[/]")

        if estimates["currency"] == "USD":
            console.print(f"   Est. Cost: [green]${estimates['input_cost']:.5f}[/]")
        else:
            console.print("   Est. Cost: [bold blue]Free (Local/Ollama)[/]")

        # 3. Confirmation
        if not yes:
            console.print("")
            if not Confirm.ask("Do you want to proceed?"):
                console.print("[yellow]Aborted by user.[/]")
                return

        # 4. Generate documentation
        api_key = os.getenv("OPENAI_API_KEY")

        with console.status(
            f"Generating docs using [cyan]{model}[/]...", spinner="dots"
        ):
            # UNPACK THE TUPLE
            documented_content, usage_stats = generate_documentation(
                file_content=original_content,
                provider=provider,
                model=model,
                api_key=api_key,
                mode=mode,  # PASS THE MODE
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

        console.print("\n✅ Successfully generated documentation!")
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

            if reasoning_tokens > 0:
                console.print(
                    f"   (Includes [yellow]{reasoning_tokens}[/] reasoning tokens)"
                )

            console.print(f"   Total Cost:       [bold green]${total_cost:.5f}[/]")
        else:
            console.print("\n📉 [bold]Final Usage Report:[/bold]")
            console.print(f"   Output Tokens: [cyan]{out_tokens}[/]")
            console.print("   Total Cost:    [bold blue]Free[/]")

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred in the CLI: {e}[/]")


if __name__ == "__main__":
    main()
