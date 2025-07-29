"""Defines data models for documentation entities used in the extraction pipeline."""

from dataclasses import dataclass, field


@dataclass
class Heading:
    """
    Represents a heading in a document (e.g., Markdown heading).

    Attributes:
        level (int): Heading level (e.g., 1 for '#', 2 for '##').
        text (str): Text of the heading.
        line_number (int): Line number where the heading appears.
    """

    level: int | None = None
    text: str | None = None
    line_number: int | None = None


@dataclass
class Document:
    """
    Represents a document (e.g., Markdown file).

    Attributes:
        title (str): Title of the document.
        content (str): Full text content of the document.
        headings (List[Heading]): List of headings in the document.
        path (Optional[str]): Path to the document file, if available.
    """

    content: str
    title: str | None = None
    headings: list[Heading] = field(default_factory=list)
    path: str | None = None
    elements: list["MarkdownElement"] = field(default_factory=list)


@dataclass
class CodeComment:
    """
    Represents a comment extracted from a source code file.
    """

    file_path: str
    comment: str
    start_line: int
    end_line: int


@dataclass
class MarkdownElement:
    """
    Represents a parsed markdown element for triple generation.
    """

    type: str
    content: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    level: int | None = None
    children: list["MarkdownElement"] = field(default_factory=list)
    token_index: int | None = None
    tag: str | None = None
