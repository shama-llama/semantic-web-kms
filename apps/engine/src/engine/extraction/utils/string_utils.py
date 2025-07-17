"""String and text processing utility functions for extraction."""

import re
from typing import List


def calculate_token_count(raw_code: str) -> int:
    """
    Count lexical tokens in code by splitting on whitespace and delimiters.

    Args:
        raw_code: Source code as a string.
    Returns:
        Number of tokens (int).
    """
    if not raw_code:
        return 0
    lines = raw_code.split("\n")
    code_lines = []
    for line in lines:
        if "#" in line:
            line = line.split("#")[0]
        if "//" in line:
            line = line.split("//")[0]
        code_lines.append(line)
    code_text = " ".join(code_lines)
    tokens = re.split(r"[\s\(\)\[\]\{\}\.,;:+\-*/=<>!&|^~%]+", code_text)
    tokens = [token for token in tokens if token.strip()]
    return len(tokens)


def calculate_line_count(raw_code: str) -> int:
    """
    Count the number of lines in a string.

    Args:
        raw_code: Source code as a string.
    Returns:
        Number of lines (int).
    """
    if not raw_code:
        return 0
    return len(raw_code.split("\n"))


def extract_imported_names(import_text: str) -> List[str]:
    """
    Extract imported names from import statements.

    Args:
        import_text: Raw import statement text.
    Returns:
        List of imported names.
    """
    names = []
    if import_text.startswith("import "):
        parts = import_text.split()
        if len(parts) >= 2:
            module = parts[1]
            names.append(module)
    elif import_text.startswith("from "):
        if " import " in import_text:
            parts = import_text.split(" import ")
            if len(parts) == 2:
                imported_part = parts[1].strip()
                for name in imported_part.split(","):
                    name = name.strip()
                    if name:
                        names.append(name)
    return names
