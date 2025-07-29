"""A factory for creating code parsers based on file extension."""

from ..parsers.base_parser import BaseCodeParser
from ..parsers.csharp_parser import CSharpParser
from ..parsers.go_parser import GoParser
from ..parsers.java_parser import JavaParser
from ..parsers.javascript_parser import JavaScriptParser
from ..parsers.php_parser import PHPParser
from ..parsers.python_parser import PythonParser
from ..parsers.ruby_parser import RubyParser
from ..parsers.rust_parser import RustParser
from ..parsers.typescript_parser import TypeScriptParser

PARSER_MAP = {
    ".py": PythonParser,
    ".java": JavaParser,
    ".js": JavaScriptParser,
    ".ts": TypeScriptParser,
    ".cs": CSharpParser,
    ".go": GoParser,
    ".rb": RubyParser,
    ".php": PHPParser,
    ".rs": RustParser,
}


def get_parser(file_extension: str) -> BaseCodeParser | None:
    """
    Returns the appropriate parser for a given file extension.

    Args:
        file_extension (str): The file extension (e.g., '.py').

    Returns:
        An instance of a BaseCodeParser, or None if no parser is found.
    """
    parser_class = PARSER_MAP.get(file_extension)
    if parser_class:
        return parser_class()
    return None 