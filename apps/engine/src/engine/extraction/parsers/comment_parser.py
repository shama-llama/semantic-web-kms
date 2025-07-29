"""Defines the CommentParser class for extracting comments from source code."""

import re
from typing import Any


class CommentParser:
    """
    Parses source code and extracts comments.
    """

    def extract_comments(self, code: str, ext: str) -> list[dict[str, Any]]:
        """
        Extracts comments from source code based on file extension.
        """
        if ext == ".py":
            return self._extract_python_comments(code)
        if ext in {".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs"}:
            return self._extract_c_style_comments(code)
        if ext in {".sh", ".rb", ".pl"}:
            return self._extract_hash_comments(code)
        return []

    def _extract_python_comments(self, code: str) -> list[dict[str, Any]]:
        """
        Extracts comments from Python code.
        """
        comments = []
        # Single-line comments
        for match in re.finditer(r"#.*", code):
            line = code[: match.start()].count("\n") + 1
            comments.append({
                "raw": match.group().lstrip("#").strip(),
                "start_line": line,
                "end_line": line,
            })
        # Docstrings
        for match in re.finditer(r'"""(.*?)"""', code, re.DOTALL):
            start_line = code[: match.start()].count("\n") + 1
            end_line = code[: match.end()].count("\n") + 1
            comments.append({
                "raw": match.group(1).strip(),
                "start_line": start_line,
                "end_line": end_line,
            })
        return comments

    def _extract_c_style_comments(self, code: str) -> list[dict[str, Any]]:
        """
        Extracts comments from C-style languages (JavaScript, Java, etc.).
        """
        comments = []
        # Single-line comments
        for match in re.finditer(r"//.*", code):
            line = code[: match.start()].count("\n") + 1
            comments.append({
                "raw": match.group().lstrip("//").strip(),
                "start_line": line,
                "end_line": line,
            })
        # Multi-line comments
        for match in re.finditer(r"/\*(.*?)\*/", code, re.DOTALL):
            start_line = code[: match.start()].count("\n") + 1
            end_line = code[: match.end()].count("\n") + 1
            comments.append({
                "raw": match.group(1).strip(),
                "start_line": start_line,
                "end_line": end_line,
            })
        return comments

    def _extract_hash_comments(self, code: str) -> list[dict[str, Any]]:
        """
        Extracts comments from languages that use '#' for comments (Shell, Ruby, etc.).
        """
        comments = []
        for match in re.finditer(r"#.*", code):
            line = code[: match.start()].count("\n") + 1
            comments.append({
                "raw": match.group().lstrip("#").strip(),
                "start_line": line,
                "end_line": line,
            })
        return comments
