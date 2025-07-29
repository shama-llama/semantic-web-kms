"""Defines core data models used in the extraction pipeline."""

from dataclasses import dataclass, field
from pathlib import Path

from .git import Commit


class LazyFileContent:
    """Lazy loading wrapper for file content to reduce memory usage."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._content = None
        self._size = None

    @property
    def content(self) -> bytes:
        """Load file content only when accessed."""
        if self._content is None:
            try:
                self._content = self.file_path.read_bytes()
            except Exception:
                self._content = b""
        return self._content

    @property
    def size(self) -> int:
        """Get file size without loading content."""
        if self._size is None:
            try:
                self._size = self.file_path.stat().st_size
            except Exception:
                self._size = 0
        return self._size

    def clear(self):
        """Clear loaded content to free memory."""
        self._content = None


@dataclass
class File:
    """
    Represents a file discovered in the source directory.
    Maps to DigitalInformationCarrier in the ontology.

    Attributes:
        path (Path): Absolute path to the file.
        relative_path (Path): Path relative to the repository root.
        organization_name (str): Name of the organization this file belongs to.
        repository_name (str): Name of the repository this file belongs to.
        content_bytes (bytes): Raw content of the file (lazy loaded).
        extension (str): File extension (e.g., '.py', '.md').
        size_bytes (int): Size of the file in bytes.
        creation_timestamp (str): ISO 8601 creation timestamp.
        modification_timestamp (str): ISO 8601 last modification timestamp.
        ontology_class (str): Ontology class name assigned to this file.
        class_uri (str): URI for the ontology class.
    """

    path: Path
    relative_path: Path
    organization_name: str  # Name of the organization this file belongs to
    repository_name: str
    content_bytes: LazyFileContent
    extension: str
    size_bytes: int
    creation_timestamp: str
    modification_timestamp: str
    ontology_class: str = ""
    class_uri: str = ""

    def __post_init__(self):
        """Initialize lazy content wrapper."""
        if not isinstance(self.content_bytes, LazyFileContent):
            self.content_bytes = LazyFileContent(self.path)

    def get_content(self) -> bytes:
        """Get file content (lazy loaded)."""
        return self.content_bytes.content

    def clear_content(self):
        """Clear loaded content to free memory."""
        self.content_bytes.clear()


@dataclass
class Repository:
    """
    Represents a code repository discovered in the input directory.

    Attributes:
        name (str): Name of the repository.
        path (Path): Absolute path to the repository root.
        remote_url (Optional[str]): Remote URL if available (e.g., from git config).
        commits (List[Commit]): List of commits in the repository.
    """

    name: str
    path: Path
    remote_url: str | None = None
    commits: list[Commit] = field(default_factory=list)


@dataclass
class Content:
    """
    Represents an InformationContentEntity - the content borne by a DigitalInformationCarrier.
    Maps to InformationContentEntity in the ontology.

    Attributes:
        path (Path): Reference to the file that bears this content (for linking).
        organization_name (str): Reference to organization (for linking).
        repository_name (str): Reference to repository (for linking).
        ontology_class (str): Ontology class name for this content entity.
        class_uri (str): URI for the ontology class.
        content (str | None): Extracted content text (for specific classes like ConfigurationSetting, Log).
        relative_path (Path | None): Path relative to repository root.
        programming_language (str | None): Programming language for code files.
        line_count (int | None): Number of lines for code files.
        asset_metadata (dict | None): Metadata for media files (width, height, format, etc.).
        dependencies (list | None): List of dependencies for build files.
        frameworks (list | None): List of frameworks used in code files.
        special_content (list | None): Special content data (dockerfile base images, license identifiers, etc.).
    """

    path: Path
    organization_name: str  # Reference to organization (for linking)
    repository_name: str
    ontology_class: str = ""
    class_uri: str = ""
    content: str | None = None
    relative_path: Path | None = None
    programming_language: str | None = None
    line_count: int | None = None
    asset_metadata: dict | None = None
    dependencies: list | None = None
    frameworks: list | None = None
    special_content: list | None = None
