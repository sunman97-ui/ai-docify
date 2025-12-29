"""
Defines the tool schemas (strategies) for Function Calling mode.
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
