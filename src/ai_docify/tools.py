"""
Utilities to safely insert or replace docstrings in Python source code using
the AST module.

This module exposes a single function to parse Python source text, detect
module-, class-, and function-level docstrings, and insert or replace them
based on a provided mapping of symbol names to docstring text.
"""

import ast
from typing import Dict, List, Set, Tuple


# --- Helper Functions ---
def _clean_docstring(raw_text: str, indent_level: int) -> str:
    """
    Short summary.

    Parameters
    ----------
    raw_text : str
        The raw docstring text to clean and format.
    indent_level : int
        Number of spaces to use as indentation for the formatted docstring.

    Returns
    -------
    str
        The cleaned and properly indented docstring including triple quotes
        and trailing newline.
    """
    indent = " " * indent_level
    cleaned = raw_text.strip()

    # Remove surrounding triple quotes if present (LLM outputs etc.)
    if cleaned.startswith('"""') and cleaned.endswith('"""') and len(cleaned) >= 6:
        cleaned = cleaned[3:-3].strip()
    elif cleaned.startswith("'''") and cleaned.endswith("'''") and len(cleaned) >= 6:
        cleaned = cleaned[3:-3].strip()

    formatted_lines: List[str] = [f'{indent}"""']
    for line in cleaned.split("\n"):
        if line.strip():
            formatted_lines.append(f"{indent}{line}")
        else:
            formatted_lines.append("")  # preserve blank line inside docstring
    formatted_lines.append(f'{indent}"""')
    # Join with newline and ensure final newline
    return "\n".join(formatted_lines) + "\n"


# --- Main API ---
def insert_docstrings_to_source(
    original_source: str, docstring_map: Dict[str, str]
) -> str:
    """
    Parse a Python source string and insert new docstrings.
    Supports functions, async functions, classes, and the module docstring.

    Parameters
    ----------
    original_source : str
        The Python source code to modify.
    docstring_map : Dict[str, str]
        Mapping from symbol names to desired docstring text. Use "__module__"
        as the key to target the module-level docstring.

    Returns
    -------
    str
        The modified source code with inserted/replaced docstrings. If the
        original source cannot be parsed due to a SyntaxError, the original
        source string is returned unchanged.
    """
    lines: List[str] = original_source.splitlines(keepends=True)
    try:
        tree = ast.parse("".join(lines))
    except SyntaxError:
        return original_source

    lines_to_delete: Set[int] = set()
    insertions: List[Tuple[int, str]] = []

    # --- Module-level docstring insertion ---
    if "__module__" in docstring_map:
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
        ):
            old_doc = tree.body[0]
            # Mark the existing module docstring lines for deletion
            for i in range(old_doc.lineno - 1, old_doc.end_lineno):
                lines_to_delete.add(i)

        new_doc = _clean_docstring(docstring_map["__module__"], 0)
        insertions.append((0, new_doc))

    # --- Symbol docstrings (Functions & Classes) ---
    target_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

    for node in ast.walk(tree):
        if isinstance(node, target_types):
            if node.name in docstring_map:
                # Detect & mark existing docstring if present
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):
                    old_doc = node.body[0]
                    for i in range(old_doc.lineno - 1, old_doc.end_lineno):
                        lines_to_delete.add(i)

                # Standard indent: node.col_offset + 4 (covers methods inside classes)
                indent_level = node.col_offset + 4
                new_doc = _clean_docstring(docstring_map[node.name], indent_level)

                # Insert at the line index of the first statement in the body
                insertion_index = node.body[0].lineno - 1
                insertions.append((insertion_index, new_doc))

    # --- Execute changes ---
    for idx in lines_to_delete:
        if 0 <= idx < len(lines):
            lines[idx] = None

    # Sort insertions in reverse order to avoid shifting indices while inserting
    insertions.sort(key=lambda x: x[0], reverse=True)

    for idx, text in insertions:
        if 0 <= idx <= len(lines):
            lines.insert(idx, text)

    # Reconstruct source skipping removed lines
    return "".join([line for line in lines if line is not None])
