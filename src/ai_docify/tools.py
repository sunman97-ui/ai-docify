"""
Utilities to safely insert or replace docstrings in Python source code using
the AST module. Provides functionality to remove existing docstrings and
insert new, well-indented docstring blocks for module-level and function-level
definitions based on a mapping from names to docstring text. The primary
consumer function parses the source into an AST, identifies existing docstring
nodes to remove, and schedules well-formatted insertions without shifting line
indices prematurely.
"""

import ast


def insert_docstrings_to_source(original_source: str, docstring_map: dict) -> str:
    """
    Parse a Python source string, remove existing docstrings, and insert new
    docstrings from a provided mapping using the AST module.

    Parameters
    ----------
    original_source : str
        The full Python source code to modify. This should be a single string
        containing one or more module-level and function definitions. The function
        will return the original string unchanged if the source cannot be parsed
        as valid Python.

    docstring_map : dict
        A mapping from target names to docstring text. The special key
        "__module__" (str) is used for the module-level docstring; other keys
        should match function names (str) present in the source. Values are raw
        docstring text (str) which may or may not already include surrounding
        triple quotes; the implementation will clean and reformat them.

    Returns
    -------
    str
        The modified source code with old docstrings removed and new docstrings
        inserted. If the original source is syntactically invalid, the original
        source string is returned unchanged.
    """
    lines = original_source.splitlines(keepends=True)
    try:
        tree = ast.parse("".join(lines))
    except SyntaxError:
        # Fallback: If code is unparsable, we can't inject safely.
        return original_source

    lines_to_delete = set()
    insertions = []  # List of (index_to_insert_at, text)

    # --- HELPER: Docstring Cleanup ---
    def clean_docstring(raw_text: str, indent_level: int) -> str:
        """
        Format raw docstring text into a properly indented triple-quoted block suitable
        for insertion into source code.

        Parameters
        ----------
        raw_text : str
            The raw docstring content to format. This may already include surrounding
            triple quotes (single or double); if so, the surrounding quotes will be
            removed before reformatting.

        indent_level : int
            The number of spaces to prefix each non-empty line of the formatted
            docstring with. This should match the indentation of the surrounding
            code block (for example, 4 for a standard function body).

        Returns
        -------
        str
            A string containing the cleaned and formatted docstring block, including
            opening and closing triple quotes and terminating newlines. The returned
            block is ready to be inserted into the source code at the chosen index.
        """
        indent = " " * indent_level
        cleaned = raw_text.strip()

        # Remove existing quotes if LLM added them (Common LLM quirk)
        if cleaned.startswith('"""') and cleaned.endswith('"""') and len(cleaned) >= 6:
            cleaned = cleaned[3:-3].strip()
        elif (
            cleaned.startswith("'''") and cleaned.endswith("'''") and len(cleaned) >= 6
        ):
            cleaned = cleaned[3:-3].strip()

        formatted = f'{indent}"""\n'
        for line in cleaned.split("\n"):
            # Preserve empty lines correctly
            if line.strip():
                formatted += f"{indent}{line}\n"
            else:
                formatted += "\n"
        formatted += f'{indent}"""\n'
        return formatted

    # --- 1. MODULE LEVEL DOCSTRING ---
    # Handles top-level file documentation if the key "__module__" is present
    if "__module__" in docstring_map:
        # Check for existing module docstring (always the first expression)
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
        ):
            old_doc = tree.body[0]
            # Mark old lines for deletion
            for i in range(old_doc.lineno - 1, old_doc.end_lineno):
                lines_to_delete.add(i)

        # Prepare new one (Module docstring has 0 indentation)
        new_doc = clean_docstring(docstring_map["__module__"], 0)
        insertions.append((0, new_doc))

    # --- 2. FUNCTION DOCSTRINGS ---
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name in docstring_map:

                # A. DETECT & MARK EXISTING DOCSTRING FOR DELETION
                # Check if the first statement in the function is a string
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):

                    old_doc = node.body[0]
                    # Mark all lines of the old docstring for deletion
                    for i in range(old_doc.lineno - 1, old_doc.end_lineno):
                        lines_to_delete.add(i)

                # B. PREPARE NEW DOCSTRING
                # Indent matches the function body (standard is 4 spaces)
                indent_level = node.col_offset + 4
                new_doc = clean_docstring(docstring_map[node.name], indent_level)

                # C. PLAN INSERTION
                # The insertion point is the line number of the first statement
                # in the function body.
                # We subtract 1 to get the correct 0-based list index.
                insertion_index = node.body[0].lineno - 1
                insertions.append((insertion_index, new_doc))

    # --- 3. EXECUTE CHANGES ---

    # A. Nullify deleted lines (replace with None so indices don't shift yet)
    for idx in lines_to_delete:
        if 0 <= idx < len(lines):
            lines[idx] = None

    # B. Insert new lines
    # Sort in reverse order (bottom to top) to ensure insertion indices remain valid
    insertions.sort(key=lambda x: x[0], reverse=True)

    for idx, text in insertions:
        # Ensure we don't insert out of bounds
        if 0 <= idx <= len(lines):
            lines.insert(idx, text)

    # C. Filter Nones and Join
    return "".join([line for line in lines if line is not None])
