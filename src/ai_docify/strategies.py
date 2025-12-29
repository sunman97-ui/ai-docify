"""
Defines the tool schemas (strategies) for Function Calling mode.
"""

DOCSTRING_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "generate_docstrings",
            "description": "Submits generated docstrings for the provided Python code.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "functions": {
                        "type": "array",
                        "description": "A list of functions to document.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The exact name of the function (or __module__)."
                                },
                                "body": {
                                    "type": "string", 
                                    "description": "The full NumPy-style docstring content."
                                }
                            },
                            "required": ["name", "body"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["functions"],
                "additionalProperties": False
            }
        }
    }
]