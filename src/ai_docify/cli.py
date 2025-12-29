"""
CLI tool to generate NumPy/Sphinx style docstrings for Python source files.

This module provides a Click-based command line interface that:
- Validates model/provider configuration.
- Estimates token usage and cost.
- Optionally prompts the user for confirmation.
- Calls the documentation generator and writes the result to ai_output/.
- Prints a final usage/cost report.

The script relies on the local project's generator, utils, and config modules
to perform the core AI and pricing work.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm

from .generator import generate_documentation, AIDocifyError
from .utils import estimate_cost, calculate_token_cost
from .config import get_model_price, validate_model

load_dotenv()


# --- File I/O Helpers ---
def read_file(filepath: str) -> str:
    """
    Read the contents of a file as UTF-8 text.

    Parameters
    ----------
    filepath : str
        Path to the file to read.

    Returns
    -------
    str
        The file contents.
    """
    path_obj: Path = Path(filepath)
    try:
        with path_obj.open("r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise IOError(f"Failed to read file {filepath}: {e}") from e


def write_output_file(output_dir: Path, filename: str, content: str) -> Path:
    """
    Write content to a file inside an output directory, ensuring the directory exists.

    Parameters
    ----------
    output_dir : pathlib.Path
        Directory where the output file will be written.
    filename : str
        The filename to write inside output_dir.
    content : str
        The content to write to the file.

    Returns
    -------
    pathlib.Path
        The full path to the written file.
    """
    output_dir.mkdir(exist_ok=True)
    output_path: Path = output_dir / filename
    try:
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)
        return output_path
    except OSError as e:
        raise IOError(f"Failed to write file {output_path}: {e}") from e


# --- Secure API Key Handling ---
def get_api_key(provider: str) -> Optional[str]:
    """
    Securely retrieve API key for the specified provider.

    Parameters
    ----------
    provider : str
        The provider name to get the API key for.

    Returns
    -------
    Optional[str]
        The API key if found, None otherwise.
    """
    if provider.lower() == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return api_key
    elif provider.lower() == "ollama":
        # Ollama is local, no API key needed
        return "ollama"
    return None


# --- Console Helpers ---
def print_estimation(console: Console, estimates: Dict[str, Any]) -> None:
    """
    Print a pre-flight estimation of tokens and cost.

    Parameters
    ----------
    console : rich.console.Console
        Console object to print to.
    estimates : dict
        Estimation dictionary returned from estimate_cost().

    Returns
    -------
    None
        This function prints to the console and returns nothing.
    """
    console.print("\n📊 [bold]Estimation (Input Only):[/bold]")
    console.print(f"   Tokens: [cyan]{estimates.get('tokens')}[/]")

    if estimates.get("currency") == "USD":
        console.print(f"   Est. Cost: [green]${estimates.get('input_cost', 0):.5f}[/]")
    else:
        console.print("   Est. Cost: [bold blue]Free (Local/Ollama)[/]")


def prompt_confirmation(console: Console) -> bool:
    """
    Prompt the user for confirmation using a yes/no dialog.

    Parameters
    ----------
    console : rich.console.Console
        Console object to use for prompting.

    Returns
    -------
    bool
        True if the user confirmed, False otherwise.
    """
    console.print("")
    return Confirm.ask("Do you want to proceed?")


def print_final_usage_report(
    console: Console, usage_stats: Dict[str, int], provider: str, model: str
) -> None:
    """
    Print the final usage report with token counts and estimated cost.

    Parameters
    ----------
    console : rich.console.Console
        Console object to print to.
    usage_stats : dict
        Dictionary with keys 'input_tokens', 'output_tokens', 'reasoning_tokens'.
    provider : str
        Provider name used for pricing lookup.
    model : str
        Model name used for pricing lookup.

    Returns
    -------
    None
        This function prints the final usage and cost report to the console.
    """
    try:
        price_info = get_model_price(provider, model)
        input_price = price_info.get("input_cost_per_million", 0)
        output_price = price_info.get("output_cost_per_million", 0)

        in_tokens = usage_stats.get("input_tokens", 0)
        out_tokens = usage_stats.get("output_tokens", 0)
        reasoning_tokens = usage_stats.get("reasoning_tokens", 0)

        total_cost = 0.0
        console.print("\n📉 [bold]Final Usage Report:[/bold]")

        if input_price > 0:
            input_cost = calculate_token_cost(in_tokens, input_price)
            output_cost = calculate_token_cost(out_tokens, output_price)
            total_cost = input_cost + output_cost

            console.print(f"   Input Tokens:     [cyan]{in_tokens}[/]")
            console.print(f"   Output Tokens:    [cyan]{out_tokens}[/]")

            if reasoning_tokens > 0:
                console.print(
                    f"   (Includes [yellow]{reasoning_tokens}[/] reasoning tokens)"
                )

            console.print(f"   Total Cost:       [bold green]${total_cost:.5f}[/]")
        else:
            # Local or free providers: only show tokens and Free
            console.print(f"   Output Tokens: [cyan]{out_tokens}[/]")
            console.print("   Total Cost:    [bold blue]Free[/]")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not generate usage report: {e}[/]")


# --- CLI Entry Point ---
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
@click.option(
    "--output-dir", default="ai_output", help="Directory to save output files."
)
def main(
    filepath: str, provider: str, model: str, mode: str, yes: bool, output_dir: str
) -> None:
    """
    Generate NumPy/Sphinx style docstrings for a Python file via an AI model.

    Parameters

    ----------

    filepath : str
        Path to the Python file to document.

    provider : str
        AI provider name (e.g., 'openai', 'ollama').

    model : str
        Model name as configured in pricing.json.

    mode : str
        Operation mode, either 'rewrite' or 'inject'.

    yes : bool
        If True, skip the confirmation prompt and proceed automatically.

    EXAMPLE USAGE:

    --------------

    ai-docify src/my_script.py --provider openai --model gpt-5-mini --mode rewrite

    \f
    Returns
    -------
    None
        The function performs I/O and prints status; it does not return a value.
    """
    console = Console()

    try:
        # --- 1. Validate Configuration ---
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

        # --- 2. Read file content ---
        try:
            original_content = read_file(filepath)
        except IOError as e:
            console.print(f"[bold red]Error reading file:[/] {e}")
            sys.exit(1)

        # --- 3. Cost Estimation (Pre-Flight) ---
        try:
            # Pass the selected mode to the estimator
            # so it can account for mode-specific tokens.
            estimates = estimate_cost(original_content, provider, model, mode=mode)
            print_estimation(console, estimates)
        except Exception as e:
            console.print(f"[bold yellow]Warning: Could not estimate cost: {e}[/]")
            if not yes:
                if not prompt_confirmation(console):
                    console.print("[yellow]Aborted by user.[/]")
                    return

        # --- 4. Confirmation ---
        if not yes:
            if not prompt_confirmation(console):
                console.print("[yellow]Aborted by user.[/]")
                return

        # --- 5. Generate documentation ---
        # Secure API key handling
        api_key = get_api_key(provider)
        if provider.lower() == "openai" and not api_key:
            console.print(
                "[bold red]Error: OPENAI_API_KEY environment variable is not set.[/]"
            )
            sys.exit(1)

        output_dir_path = Path(output_dir)

        with console.status(
            f"Generating docs using [cyan]{model}[/]...", spinner="dots"
        ):
            try:
                # generate_documentation returns (documented_content, usage_stats)
                documented_content, usage_stats = generate_documentation(
                    file_content=original_content,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    mode=mode,
                    console=console,
                )
            except AIDocifyError as e:
                console.print(f"[bold red]Error generating documentation: {e}[/]")
                sys.exit(1)

        # --- 6. Write output to output directory ---
        try:
            path_obj = Path(filepath)
            output_filename = f"{path_obj.stem}.doc.py"
            output_path = write_output_file(
                output_dir_path, output_filename, documented_content
            )

            console.print("\n✅ Successfully generated documentation!")
            console.print(f"   Output saved to: [bold yellow]{output_path}[/]")
        except IOError as e:
            console.print(f"[bold red]Error writing output file: {e}[/]")
            sys.exit(1)

        # --- 7. Final Usage Report (Post-Flight) ---
        print_final_usage_report(console, usage_stats, provider, model)

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred in the CLI: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
