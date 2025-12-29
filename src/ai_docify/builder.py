"""
Utilities for loading a JSON-based docstring prompt template and for
constructing LLM-compatible message payloads.

This module provides helpers to read a JSON template from a
'templates/docstring_generator.json' file located adjacent to the module
and to build the ``system`` and ``user`` message objects used to prompt a
large language model (LLM). The functions are small, focused wrappers
intended for CLI or automation workflows that need a reproducible LLM
prompt composition.
"""

import json
from pathlib import Path


def load_template() -> dict:
    """
    Load the documentation prompt template from a JSON file located in the
    package templates directory.

    Parameters
    ----------
    None : None

    Returns
    -------
    dict
        Parsed JSON object representing the docstring prompt template.
        The returned dictionary is the direct result of ``json.load`` and is
        expected to contain keys such as the prompt modes (for example,
        ``'rewrite'`` and ``'inject'``) mapping to prompt definitions.
    """
    template_path = Path(__file__).parent / "templates" / "docstring_generator.json"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_messages(file_content: str, mode: str = "rewrite") -> list[dict]:
    """
    Construct messages for a large language model (LLM) from file content
    and a chosen mode.

    Parameters
    ----------
    file_content : str
        The raw content of the file to be documented or rewritten. This
        string will be injected into the template's user prompt at the
        placeholder expected by the template (for example, ``{raw_text}``).
    mode : str
        Mode determining which prompt to use from the template. Common
        values are ``'rewrite'`` (default) and ``'inject'``; if the provided
        mode is not found in the template, the function falls back to
        ``'rewrite'``.

    Returns
    -------
    list[dict]
        A list of message dictionaries suitable for consumption by most LLM
        APIs. Each dictionary contains the keys ``'role'`` (str) and
        ``'content'`` (str). The first element is the system prompt and the
        second element is the user prompt with ``file_content`` inserted.
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
