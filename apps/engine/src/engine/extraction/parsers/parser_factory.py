"""Defines a factory for creating language-specific parsers."""

from typing import Optional, Type

from .base_parser import BaseCodeParser
from .csharp_parser import CSharpParser
from .go_parser import GoParser
from .java_parser import JavaParser
from .javascript_parser import JavaScriptParser
from .php_parser import PHPParser
from .python_parser import PythonParser
from .ruby_parser import RubyParser
from .rust_parser import RustParser
from .typescript_parser import TypeScriptParser

# Mapping from language names (and common aliases) to parser classes
PARSER_MAP: dict[str, Type[BaseCodeParser]] = {
    "python": PythonParser,
    "javascript": JavaScriptParser,
    "typescript": TypeScriptParser,
    "java": JavaParser,
    "csharp": CSharpParser,
    "go": GoParser,
    "rust": RustParser,
    "php": PHPParser,
    "ruby": RubyParser,
}


class ParserFactory:
    """
    Factory class to get the appropriate parser for a given language.
    """

    @staticmethod
    def get_parser(language: str) -> Optional[Type[BaseCodeParser]]:
        """
        Returns the parser class for the given language.

        Args:
            language: The name of the programming language.

        Returns:
            The parser class, or None if no parser is available.
        """
        return PARSER_MAP.get(language.lower())
