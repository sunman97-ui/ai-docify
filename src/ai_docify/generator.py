"""
Utilities for generating and injecting NumPy-style docstrings into
Python source files using a large language model (LLM). Centralizes
prompt and template loading, payload construction for the LLM, API
interaction, and post-processing including injecting generated
docstrings back into source.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from openai import OpenAI, OpenAIError
from rich.console import Console

# Internal imports
from .tools import insert_docstrings_to_source

# --- Logger Setup ---
logger = logging.getLogger(__name__)


# --- Constants & Schemas ---
DOCSTRING_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "generate_one_docstring",
            "description": "Submits a single generated docstring for a specific"
            "function or for the module-level documentation in Python code.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The exact name of the function or class. "
                        "For module-level docstrings, use '__module__'.",
                    },
                    "body": {
                        "type": "string",
                        "description": "The full NumPy-style docstring content.",
                    },
                },
                "required": ["name", "body"],
                "additionalProperties": False,
            },
        },
    }
]


# --- Exceptions ---
class AIDocifyError(Exception):
    """
    Custom exception for AI-Docify specific errors.
    """

    pass


# --- Helper Functions ---
def _load_template() -> dict:
    """
    Load the JSON prompt template from disk.

    Returns
    -------
    dict
        The loaded JSON template as a dictionary.
    """
    template_path = Path(__file__).parent / "templates" / "docstring_generator.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Payload Construction ---
def prepare_llm_payload(file_content: str, mode: str = "rewrite") -> Dict[str, Any]:
    """
    Construct the exact payload (messages + optional tools) for the LLM.

    Parameters
    ----------
    file_content : str
        The raw source file content to be included in the LLM prompt.
    mode : str, optional
        Mode of operation; one of "rewrite" or "inject" (default is
        "rewrite").

    Returns
    -------
    Dict[str, Any]
        A payload dictionary containing the messages and, for "inject"
        mode, a tools schema.
    """
    template = _load_template()
    prompt_details = template.get(mode, template.get("rewrite"))

    system_prompt = prompt_details["system_prompt"]
    user_prompt = prompt_details["user_prompt"].format(raw_text=file_content)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    payload: Dict[str, Any] = {"messages": messages}

    if mode == "inject":
        payload["tools"] = DOCSTRING_TOOL_SCHEMA

    return payload


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
    Generate documentation for Python source.

    Parameters
    ----------
    file_content : str
        The Python source code to document.
    provider : str
        The backend provider identifier (e.g., "openai" or "ollama").
    model : str
        The model name to request from the provider.
    api_key : str | None
        API key for authentication with the provider (required for
        OpenAI).
    mode : str, optional
        Operation mode: "rewrite" returns a full rewritten source string;
        "inject" returns the original source with docstrings injected
        (default "rewrite").
    console : Optional[Console], optional
        Optional Rich Console for user-facing messages (default creates a
        new Console).

    Returns
    -------
    Tuple[str, Dict[str, Any]]
        A tuple of (resulting_source_or_text, usage_stats) where usage_stats
        is a mapping containing token usage keys ("input_tokens",
        "output_tokens", "reasoning_tokens").
    """
    if console is None:
        console = Console()

    # Initialize empty usage stats
    usage: Dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
    }

    try:
        # 1. Initialize Client
        if provider == "ollama":
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            logger.info("Connecting to local Ollama with model %s", model)
        else:
            if not api_key:
                raise AIDocifyError("API key is required for OpenAI")
            client = OpenAI(api_key=api_key)
            logger.info("Connecting to OpenAI with model %s", model)

        # 2. Prepare Payload (Centralized Logic)
        try:
            payload = prepare_llm_payload(file_content, mode=mode)
        except Exception as e:
            raise AIDocifyError(f"Error building messages: {e}") from e

        # 3. Call API
        kwargs = {"model": model, **payload}

        logger.info("Generating documentation (%s mode)", mode)
        console.print(f"Generating documentation ({mode} mode)...")

        try:
            response = client.chat.completions.create(**kwargs)
        except OpenAIError as e:
            raise AIDocifyError(f"API error: {e}") from e

        # 4. Extract Usage
        if response.usage:
            usage["input_tokens"] = response.usage.prompt_tokens
            usage["output_tokens"] = response.usage.completion_tokens
            # Handle varied shapes of completion_tokens_details (may be dict or object)
            if hasattr(response.usage, "completion_tokens_details"):
                details = response.usage.completion_tokens_details
                # If dict-like, pull reasoning_tokens key; otherwise, use attribute access
                if isinstance(details, dict):
                    usage["reasoning_tokens"] = details.get("reasoning_tokens", 0)
                else:
                    usage["reasoning_tokens"] = getattr(details, "reasoning_tokens", 0)

        # 5. Process Response
        if mode == "rewrite":
            content = response.choices[0].message.content
            if not content:
                raise AIDocifyError("Invalid API response: missing content")

            # Strip markdown fences if the model wrapped the code block
            if content.startswith("```python"):
                content = content[
                    9:
                ].lstrip()  # remove the opening triple-backticks and language tag
            if content.endswith("```"):
                content = content[:-3].rstrip()  # remove closing triple-backticks

            return content, usage

        elif mode == "inject":
            msg = response.choices[0].message
            if not msg.tool_calls:
                raise AIDocifyError("Model did not return any valid tool calls")

            docstring_map: Dict[str, str] = {}
            for tool_call in msg.tool_calls:
                if tool_call.function.name == "generate_one_docstring":
                    args = json.loads(tool_call.function.arguments)
                    if args.get("name") and args.get("body"):
                        docstring_map[args["name"]] = args["body"]

            if not docstring_map:
                raise AIDocifyError("No valid docstrings were generated")

            final_code = insert_docstrings_to_source(file_content, docstring_map)
            return final_code, usage

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise AIDocifyError(f"{e}") from e
