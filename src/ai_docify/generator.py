"""
Utilities for generating or injecting docstrings into Python source code using an LLM.

This module provides a single high-level function, generate_documentation, which
communicates with an OpenAI-compatible API (including local Ollama instances)
to either rewrite an entire file with added documentation or to generate and
inject docstrings for individual symbols using a tool schema.
"""

import json
import logging
import sys
from typing import Tuple, Dict, Any, Optional
from openai import OpenAI, OpenAIError
from rich.console import Console
from .builder import build_messages
from .strategies import DOCSTRING_TOOL_SCHEMA
from .tools import insert_docstrings_to_source

# Configure logging with proper format and level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("ai_docify.log")],
)

logger = logging.getLogger(__name__)


# Custom exception class for better error handling
class AIDocifyError(Exception):
    """Custom exception for AI-Docify specific errors."""

    pass


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

    Raises
    ------
    AIDocifyError
        If there's an error with the API call or processing the response.
    """
    if console is None:
        console = Console()

    # Initialize empty usage stats in case of early return
    usage: Dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
    }

    try:
        # --- Client Initialization ---
        if provider == "ollama":
            try:
                client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
                logger.info("Connecting to local Ollama with model %s", model)
                console.print(
                    f"Connecting to local Ollama with model [cyan]{model}[/]..."
                )
            except Exception as e:
                logger.error("Failed to initialize Ollama client: %s", e)
                raise AIDocifyError(f"Failed to initialize Ollama client: {e}") from e
        else:
            if not api_key:
                logger.error("API key is required for OpenAI but was not provided")
                raise AIDocifyError("API key is required for OpenAI")

            try:
                client = OpenAI(api_key=api_key)
                logger.info("Connecting to OpenAI with model %s", model)
                console.print(f"Connecting to OpenAI with model [cyan]{model}[/]...")
            except Exception as e:
                logger.error("Failed to initialize OpenAI client: %s", e)
                raise AIDocifyError(f"Failed to initialize OpenAI client: {e}") from e

        try:
            messages = build_messages(file_content, mode=mode)
        except FileNotFoundError as e:
            logger.error("Failed to load template: %s", e)
            raise AIDocifyError(f"Failed to load template: {e}") from e
        except Exception as e:
            logger.error("Error building messages: %s", e)
            raise AIDocifyError(f"Error building messages: {e}") from e

        # --- API CALL PREPARATION ---
        kwargs = {
            "model": model,
            "messages": messages,
        }

        # If Inject Mode: Attach tools. Do NOT force a call, allow multiple calls.
        if mode == "inject":
            kwargs["tools"] = DOCSTRING_TOOL_SCHEMA

        logger.info("Generating documentation (%s mode)", mode)
        console.print(f"Generating documentation ({mode} mode)...")

        try:
            response = client.chat.completions.create(**kwargs)
        except OpenAIError as e:
            logger.error("API error: %s", e)
            raise AIDocifyError(f"API error: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during API call: %s", e)
            raise AIDocifyError(f"Unexpected error during API call: {e}") from e

        # --- USAGE EXTRACTION ---
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

        logger.info("API response received. Processing output...")

        # --- RESPONSE HANDLING ---
        if mode == "rewrite":
            if (
                not hasattr(response.choices[0], "message")
                or not response.choices[0].message.content
            ):
                logger.error("Invalid API response: missing message content")
                raise AIDocifyError("Invalid API response: missing message content")

            documented_code = response.choices[0].message.content

            # Trim fenced code blocks if present.
            if documented_code.startswith("```python"):
                # remove the opening fence and any leading whitespace/newline
                documented_code = documented_code[len("```python") :].lstrip()
            if documented_code.endswith("```"):
                # remove the closing fence and any trailing whitespace/newline
                documented_code = documented_code[: -len("```")].rstrip()

            logger.info("Successfully processed rewrite mode response")
            return documented_code, usage

        elif mode == "inject":
            if not hasattr(response.choices[0], "message"):
                logger.error("Invalid API response: missing message")
                raise AIDocifyError("Invalid API response: missing message")

            tool_calls = response.choices[0].message.tool_calls

            if not tool_calls:
                logger.error("Model did not return any valid tool calls")
                raise AIDocifyError("Model did not return any valid tool calls")

            docstring_map: Dict[str, str] = {}
            try:
                for tool_call in tool_calls:
                    if tool_call.function.name != "generate_one_docstring":
                        logger.warning(
                            "Unexpected tool call name: %s", tool_call.function.name
                        )
                        continue

                    args = json.loads(tool_call.function.arguments)

                    name = args.get("name")
                    body = args.get("body")

                    if not name:
                        logger.warning("Missing 'name' in tool call arguments")
                        continue

                    if not body:
                        logger.warning(
                            "Missing 'body' in tool call arguments for %s", name
                        )
                        continue

                    docstring_map[name] = body
                    logger.info("Processed docstring for: %s", name)

                if not docstring_map:
                    logger.error("No valid docstrings were generated")
                    raise AIDocifyError("No valid docstrings were generated")

                try:
                    final_code = insert_docstrings_to_source(
                        file_content, docstring_map
                    )
                    logger.info(
                        "Successfully injected %d docstrings", len(docstring_map)
                    )
                    return final_code, usage
                except Exception as e:
                    logger.error("Error inserting docstrings: %s", e)
                    raise AIDocifyError(f"Error inserting docstrings: {e}") from e

            except json.JSONDecodeError as e:
                logger.error("Failed to decode AI JSON response: %s", e)
                raise AIDocifyError(f"Failed to decode AI JSON response: {e}") from e
            except (AttributeError, TypeError) as e:
                logger.error("Malformed tool call arguments: %s", e)
                raise AIDocifyError(f"Malformed tool call arguments: {e}") from e
            except KeyError as e:
                logger.error("Missing required key in tool arguments: %s", e)
                raise AIDocifyError(
                    f"Missing required key in tool arguments: {e}"
                ) from e
            except Exception as e:
                logger.error("Unexpected error in inject mode: %s", e)
                raise AIDocifyError(f"Unexpected error in inject mode: {e}") from e

    except OpenAIError as e:
        logger.error("OpenAI API error: %s", e)
        raise AIDocifyError(f"OpenAI API error: {e}") from e
    except AIDocifyError:
        # Re-raise AIDocifyError without wrapping to preserve the original
        raise
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise AIDocifyError(f"Unexpected error: {e}") from e
