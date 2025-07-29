from abc import ABC, abstractmethod
from typing import List
from tree_sitter import Parser, Language
from ..models.code import CodeConstruct

class BaseCodeParser(ABC):
    """
    Abstract base class defining the contract for all language parsers.
    Each parser (Java, Python, etc.) must inherit from this class and implement its abstract methods.
    """
    def __init__(self):
        self.parser = Parser()
        self.parser.language = self.get_language()

    @abstractmethod
    def get_language(self) -> Language:
        """
        Returns the tree-sitter language object for this parser.
        Example: return Language(tsjava.language())
        """
        pass

    @abstractmethod
    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the file to parse.
            file_path (str): The path to the file being parsed.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        pass 