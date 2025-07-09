import pytest

from app.extraction.utils import string_utils


def test_calculate_token_count_basic():
    """Test token count for simple code with various delimiters."""
    code = "def foo(x, y): return x + y"
    assert string_utils.calculate_token_count(code) == 7


def test_calculate_token_count_empty():
    """Test token count for empty string."""
    assert string_utils.calculate_token_count("") == 0


def test_calculate_token_count_with_comments():
    """Test token count ignores comments in code."""
    code = "a = 1 # comment\nb = 2 // another"
    assert string_utils.calculate_token_count(code) == 4


def test_calculate_line_count_basic():
    """Test line count for multi-line string."""
    code = "a = 1\nb = 2\nc = 3"
    assert string_utils.calculate_line_count(code) == 3


def test_calculate_line_count_empty():
    """Test line count for empty string."""
    assert string_utils.calculate_line_count("") == 0


def test_extract_imported_names_import():
    """Test extracting names from 'import' statement."""
    assert string_utils.extract_imported_names("import os") == ["os"]


def test_extract_imported_names_from_import():
    """Test extracting names from 'from ... import ...' statement."""
    assert string_utils.extract_imported_names("from math import sqrt, pow") == [
        "sqrt",
        "pow",
    ]


def test_extract_imported_names_invalid():
    """Test extracting names from invalid import statement returns empty list."""
    assert string_utils.extract_imported_names("print('hello')") == []
