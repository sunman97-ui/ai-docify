"""
Defines the tool schema used to submit generated docstrings to the
functions.generate_one_docstring tool when operating in Function Calling
mode. The module provides a single constant, DOCSTRING_TOOL_SCHEMA,
which encodes a JSON Schema-like specification used to validate calls
that submit generated NumPy-style docstrings for module-level or
function-level documentation.

Attributes
----------
DOCSTRING_TOOL_SCHEMA : list of dict
    The schema describing the function tool accepted by the outer
    environment. Each entry is a mapping with a top-level 'type' key
    and a 'function' value that contains the following fields:

    - name (str): The exact name of the target function or class. Use
      '__module__' for module-level docstrings.
    - description (str): Human-readable description of what the tool
      does.
    - strict (bool): When true, the tool requires strict adherence to
      the provided schema.
    - parameters (dict): A JSON Schema-like object that specifies the
      expected properties for the tool payload. In this module the
      parameters require 'name' and 'body' properties and disallow
      additionalProperties.
"""

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
