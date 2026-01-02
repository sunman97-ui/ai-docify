"""
Utilities to remove top-level and nested docstring expressions from Python
source code by parsing and modifying the AST, then unparsing the modified
tree. This module provides an AST node transformer and a convenience function
to obtain code with docstrings stripped.
"""

import ast
import astunparse


class DocstringStripper(ast.NodeTransformer):
    """
    AST NodeTransformer that removes leading docstring expressions from modules,
    functions (synchronous and asynchronous), and classes.

    This transformer detects an initial Expr node containing a Str or Constant
    string as the first statement of a node body and removes that statement. It
    then continues visiting child nodes so the same transformation is applied
    recursively.
    """

    def _remove_docstring_expr(self, node):
        """
        Remove a leading docstring expression from a node's body if present.

        Parameters
        ----------
        node : ast.AST
            An AST node that has a body attribute (for example, Module, FunctionDef,
            or ClassDef). If the first statement in node.body is an Expr node whose
            value is a string constant, that statement will be removed.

        Returns
        -------
        ast.AST
            The possibly modified AST node with the leading docstring Expr removed
            when present; otherwise the original node is returned.
        """
        if node.body and isinstance(node.body[0], ast.Expr):
            expr_value = node.body[0].value
            if isinstance(expr_value, ast.Constant) and isinstance(
                expr_value.value, str
            ):
                node.body = node.body[1:]
        return node

    def visit_Module(self, node):
        """
        Visit a Module node and remove its leading docstring expression.

        Parameters
        ----------
        node : ast.Module
            The module AST node to inspect and modify. If the module contains a top-
            level string literal as the first statement it will be removed.

        Returns
        -------
        ast.Module
            The modified module node after removing the leading docstring and visiting
            child nodes.
        """
        node = self._remove_docstring_expr(node)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        """
        Visit a FunctionDef node and remove its leading docstring expression.

        Parameters
        ----------
        node : ast.FunctionDef
            The function definition AST node to inspect. If the function body begins
            with an Expr node containing a string constant, that Expr will be removed.

        Returns
        -------
        ast.FunctionDef
            The modified FunctionDef node after removing the leading docstring and
            visiting any nested nodes.
        """
        node = self._remove_docstring_expr(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        """
        Visit an AsyncFunctionDef node and remove its leading docstring expression.

        Parameters
        ----------
        node : ast.AsyncFunctionDef
            The asynchronous function definition AST node to inspect. If the async
            function body begins with an Expr node containing a string constant, that
            Expr will be removed.

        Returns
        -------
        ast.AsyncFunctionDef
            The modified AsyncFunctionDef node after removing the leading docstring
            and visiting any nested nodes.
        """
        node = self._remove_docstring_expr(node)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        """
        Visit a ClassDef node and remove its leading docstring expression.

        Parameters
        ----------
        node : ast.ClassDef
            The class definition AST node to inspect. If the class body begins with an
            Expr node containing a string constant, that Expr will be removed.

        Returns
        -------
        ast.ClassDef
            The modified ClassDef node after removing the leading docstring and
            visiting child nodes.
        """
        node = self._remove_docstring_expr(node)
        self.generic_visit(node)
        return node


def strip_docstrings(source_code: str) -> str:
    """
    Remove all leading docstring expressions from Python source code and return
    the resulting source code as a string.

    Parameters
    ----------
    source_code : str
        Python source code to process. The function parses this string into an
        AST, applies DocstringStripper to remove leading docstring Expr nodes, and
        unparses the modified AST back to source code.

    Returns
    -------
    str
        The source code with leading docstring expressions removed.
    """
    tree = ast.parse(source_code)
    stripper = DocstringStripper()
    stripped_tree = stripper.visit(tree)
    return astunparse.unparse(stripped_tree)
