import pytest
from src.ai_docify.strategies import DOCSTRING_TOOL_SCHEMA

def test_docstring_tool_schema_structure():
    """Test the structure and content of the DOCSTRING_TOOL_SCHEMA constant."""
    assert isinstance(DOCSTRING_TOOL_SCHEMA, list)
    assert len(DOCSTRING_TOOL_SCHEMA) == 1
    
    tool = DOCSTRING_TOOL_SCHEMA[0]
    assert isinstance(tool, dict)
    assert "type" in tool
    assert tool["type"] == "function"
    assert "function" in tool
    
    function_schema = tool["function"]
    assert isinstance(function_schema, dict)
    
    expected_keys = ["name", "description", "strict", "parameters"]
    for key in expected_keys:
        assert key in function_schema
        
    assert function_schema["name"] == "generate_one_docstring"
    assert function_schema["strict"] is True
    
    parameters = function_schema["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["type"] == "object"
    assert "properties" in parameters
    
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    assert "name" in properties
    assert "body" in properties
    
    assert properties["name"]["type"] == "string"
    assert properties["body"]["type"] == "string"
    
    assert "required" in parameters
    assert parameters["required"] == ["name", "body"]
    assert "additionalProperties" in parameters
    assert parameters["additionalProperties"] is False
