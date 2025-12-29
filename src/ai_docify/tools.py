import ast


def insert_docstrings_to_source(original_source: str, docstring_map: dict) -> str:
    """
    Parses source, removes old docstrings, and inserts new ones safely using AST.
    Returns the modified source code string.
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
            and isinstance(tree.body[0].value, (ast.Str, ast.Constant))
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
                    and isinstance(node.body[0].value, (ast.Str, ast.Constant))
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
