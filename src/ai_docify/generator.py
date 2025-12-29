"""
Utilities for generating or injecting docstrings into Python source code using an LLM.

This module provides a single high-level function, generate_documentation, which
communicates with an OpenAI-compatible API (including local Ollama instances)
to either rewrite an entire file with added documentation or to generate and
inject docstrings for individual symbols using a tool schema.
"""

import json
import logging
from typing import Tuple, Dict, Any, Optional
from openai import OpenAI, OpenAIError
from rich.console import Console
from .builder import build_messages
from .strategies import DOCSTRING_TOOL_SCHEMA
from .tools import insert_docstrings_to_source


# --- Public API ---
def generate_documentation(
    file_content: str,
    provider: str,
    model: str,
    api_key: str | None,
    mode: str = "rewrite",
    console: Optional[Console] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate documentation for Python source either by rewriting the file or by
    injecting generated docstrings.

    Parameters
    ----------
    file_content : str
        The full source code of the Python file to document.
    provider : str
        The provider identifier, e.g., "ollama" for local Ollama or other for OpenAI.
    model : str
        The model name to request from the provider.
    api_key : str | None
        The API key for remote providers. Use None for local providers like Ollama.
    mode : str, optional
        Operation mode; either "rewrite" to return a rewritten file with
        documentation or "inject" to insert docstrings into existing code.
        Default is "rewrite".
    console : Optional[Console], optional
        Console instance for output. If None, a new Console is created.

    Returns
    -------
    Tuple[str, Dict[str, Any]]
        A tuple with the first element being either the documented code (str) or
        an error message (str), and the second being a usage dictionary with keys
        "input_tokens", "output_tokens", and "reasoning_tokens" (values are ints).
    """
    if console is None:
        console = Console()
    try:
        # --- Client Initialization ---
        if provider == "ollama":
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            console.print(f"Connecting to local Ollama with model [cyan]{model}[/]...")
        else:
            if not api_key:
                return "Error: OPENAI_API_KEY is not set.", {}
            client = OpenAI(api_key=api_key)
            console.print(f"Connecting to OpenAI with model [cyan]{model}[/]...")

        messages = build_messages(file_content, mode=mode)

        # --- API CALL PREPARATION ---
        kwargs = {
            "model": model,
            "messages": messages,
        }

        # If Inject Mode: Attach tools. Do NOT force a call, allow multiple calls.
        if mode == "inject":
            kwargs["tools"] = DOCSTRING_TOOL_SCHEMA

        console.print(f"Generating documentation ({mode} mode)...")

        response = client.chat.completions.create(**kwargs)

        # --- USAGE EXTRACTION ---
        usage: Dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
        }
        if response.usage:
            usage["input_tokens"] = response.usage.prompt_tokens
            usage["output_tokens"] = response.usage.completion_tokens
            # completion_tokens_details may be either a dict or an object with attributes
            if hasattr(response.usage, "completion_tokens_details"):
                details = response.usage.completion_tokens_details
                # If dict-like, prefer dict access; otherwise attribute access.
                if isinstance(details, dict):
                    usage["reasoning_tokens"] = details.get("reasoning_tokens", 0)
                else:
                    usage["reasoning_tokens"] = getattr(details, "reasoning_tokens", 0)

        # --- RESPONSE HANDLING ---
        if mode == "rewrite":
            documented_code = response.choices[0].message.content

            # Trim fenced code blocks if present.
            if documented_code.startswith("```python"):
                # remove the opening fence and any leading whitespace/newline
                documented_code = documented_code[len("```python") :].lstrip()
            if documented_code.endswith("```"):
                # remove the closing fence and any trailing whitespace/newline
                documented_code = documented_code[: -len("```")].rstrip()

            return documented_code, usage

        elif mode == "inject":
            tool_calls = response.choices[0].message.tool_calls

            if not tool_calls:
                return "Error: Model did not return any valid tool calls.", usage

            docstring_map: Dict[str, str] = {}
            try:
                for tool_call in tool_calls:
                    if tool_call.function.name != "generate_one_docstring":
                        continue

                    args = json.loads(tool_call.function.arguments)

                    name = args.get("name")
                    body = args.get("body")

                    if name and body:
                        docstring_map[name] = body

                if not docstring_map:
                    return (
                        "Error: Valid tool calls received, but no valid name/body pairs"
                        "were found.",
                        usage,
                    )

                final_code = insert_docstrings_to_source(file_content, docstring_map)
                return final_code, usage

            except json.JSONDecodeError:
                return (
                    "Error: Failed to decode AI JSON response from tool arguments.",
                    usage,
                )
            except (AttributeError, TypeError) as e:
                return f"Error: Malformed tool call arguments from AI: {e}", usage
            except KeyError as e:
                return (
                    f"Error: AI response missing required key in tool arguments: {e}",
                    usage,
                )
            except Exception as e:
                return f"Error during inject mode processing: {e}", usage

    except OpenAIError as e:
        console.print(f"[bold red]API Error (details logged): {type(e).__name__}[/]")
        logging.error(f"OpenAI API error: {e}")
        return "Error from API: Check logs for details.", {}
    except Exception as e:
        console.print(
            f"[bold red]Unexpected error (details logged): {type(e).__name__}[/]"
        )
        logging.error(f"Unexpected error: {e}")
        return "An unexpected error occurred: Check logs for details.", {}
