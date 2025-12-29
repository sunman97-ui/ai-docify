import json
from typing import Tuple, Dict, Any
from openai import OpenAI, OpenAIError
from rich.console import Console
from .builder import build_messages
from .strategies import DOCSTRING_TOOL_SCHEMA
from .tools import insert_docstrings_to_source

console = Console()


def generate_documentation(
    file_content: str,
    provider: str,
    model: str,
    api_key: str | None,
    mode: str = "rewrite",
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates documentation based on the selected mode.
    Returns: (final_code_content, usage_dict)
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
        usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
        if response.usage:
            usage["input_tokens"] = response.usage.prompt_tokens
            usage["output_tokens"] = response.usage.completion_tokens
            if hasattr(response.usage, "completion_tokens_details"):
                details = response.usage.completion_tokens_details
                if isinstance(details, dict):
                    usage["reasoning_tokens"] = details.get("reasoning_tokens", 0)
                else:
                    usage["reasoning_tokens"] = getattr(details, "reasoning_tokens", 0)

        # --- RESPONSE HANDLING ---

        if mode == "rewrite":
            documented_code = response.choices[0].message.content
            if documented_code.startswith("```python"):
                documented_code = documented_code[len("```python") :].lstrip()
            if documented_code.endswith("```"):
                documented_code = documented_code[: -len("```")].rstrip()
            return documented_code, usage

        elif mode == "inject":
            tool_calls = response.choices[0].message.tool_calls

            if not tool_calls:
                return "Error: Model did not return any valid tool calls.", usage

            docstring_map = {}
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
        return f"Error from API: {e}", {}
    except Exception as e:
        return f"An unexpected error occurred: {e}", {}
