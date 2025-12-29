"""
my_test.py

Lightweight arithmetic helpers with thorough documentation.

This module provides two simple utilities:
- add(a, b): return the sum of two numbers
- subtract(x, y): return the difference between two numbers

The implementation emphasizes readability and documentation quality by
including NumPy/Sphinx-style docstrings for each public function and a
comprehensive module docstring describing the module's purpose and
responsibilities.
"""

# --- Public API: Arithmetic helpers ---

__all__ = ["add", "subtract"]

def add(a, b):
    """
    Add two numbers.

    Parameters
    ----------
    a : numeric
        First addend.
    b : numeric
        Second addend.

    Returns
    -------
    numeric
        The sum of a and b.

    Notes
    -----
    This function uses Python's built-in addition operator. It supports any
    numeric types that define __add__ (e.g., int, float, Decimal, Fraction).
    """
    # Compute the sum using Python's built-in addition operator.
    return a + b


def subtract(x, y):
    """
    Subtract one number from another.

    Parameters
    ----------
    x : numeric
        Minuend.
    y : numeric
        Subtrahend.

    Returns
    -------
    numeric
        The difference x - y.

    Notes
    -----
    Uses the standard subtraction operator. Compatible with all numeric types
    that implement __sub__.
    """
    # Subtract the second value (subtrahend) from the first (minuend).
    return x - y