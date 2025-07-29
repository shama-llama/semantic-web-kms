"""Defines the ExtractionContext dataclass for a pipeline run."""

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdflib import Graph

from engine.extraction.models.core import File, Repository
from engine.extraction.models.git import Commit
from engine.extraction.utils.registries import (
    ContentRegistry,
    ContributorRegistry,
    FrameworkRegistry,
    SoftwarePackageRegistry,
)


@dataclass
class ExtractionContext:
    """
    Holds all shared state, configuration, and resources for a pipeline run.

    Attributes:
        graph (Graph): The RDF graph for serialization.
        input_dir (Path): Path to the input directory.
        output_ttl_path (Path): Path to the output TTL file.
        contributor_registry: Registry for contributors.
        framework_registry: Registry for frameworks.
        software_package_registry: Registry for software packages.
        content_registry: Registry for content entities.
        repositories (Dict[str, Repository]): Discovered repositories by name.
        files (List[File]): Discovered files.
        file_metadata (List[Dict[str, str]]): Minimal metadata for discovered files.
        commits (List[Commit]): Discovered commits.
        excluded_dirs (Set[str]): Set of directory names to exclude from processing.
        classification_cache (Dict[str, Any]): Cache for file classification results.
        ontology_lookup_cache (Dict[str, Any]): Cache for ontology lookups.
        content_cache (Dict[str, Any]): Cache for file content.
        language_cache (Dict[str, Any]): Cache for language mapping.
        batch_size (int): Batch size for processing files.
        _pipeline (Any): Reference to the pipeline instance.
    """

    graph: Graph
    input_dir: Path
    output_ttl_path: Path
    contributor_registry: ContributorRegistry = field(
        default_factory=ContributorRegistry
    )
    framework_registry: FrameworkRegistry = field(default_factory=FrameworkRegistry)
    software_package_registry: SoftwarePackageRegistry = field(
        default_factory=SoftwarePackageRegistry
    )
    content_registry: ContentRegistry = field(default_factory=ContentRegistry)
    ontology_cache: "Any" = field(default_factory=dict)
    class_cache: "Any" = field(default_factory=dict)
    prop_cache: "Any" = field(default_factory=dict)
    repositories: dict[str, Repository] = field(default_factory=dict)
    files: list[File] = field(default_factory=list)
    file_metadata: list[dict[str, str]] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    excluded_dirs: "set[str]" = field(default_factory=set)
    classification_cache: dict[str, Any] = field(default_factory=dict)
    ontology_lookup_cache: dict[str, Any] = field(default_factory=dict)
    content_cache: dict[str, Any] = field(default_factory=dict)
    language_cache: dict[str, Any] = field(default_factory=dict)
    batch_size: int = 500
    _pipeline: Any = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def add_files(self, new_files: list[File]) -> None:
        """Thread-safe method to add files to the context."""
        with self._lock:
            self.files.extend(new_files)

    def add_commits(self, new_commits: list[Commit]) -> None:
        """Thread-safe method to add commits to the context."""
        with self._lock:
            self.commits.extend(new_commits)

    def add_repository(self, name: str, repository: Repository) -> None:
        """Thread-safe method to add a repository to the context."""
        with self._lock:
            self.repositories[name] = repository

    def get_files(self) -> list[File]:
        """
        Thread-safe method to get a copy of the files list from the context.

        Returns:
            list[File]: Shallow copy of the list of File objects stored in context.
        """
        with self._lock:
            return self.files.copy()

    def get_commits(self) -> list[Commit]:
        """
        Thread-safe method to get a copy of the commits list from the context.

        Returns:
            list[Commit]: Shallow copy of the list of Commit objects stored in context.
        """
        with self._lock:
            return self.commits.copy()

    def get_repositories(self) -> dict[str, Repository]:
        """
        Thread-safe method to get a copy of the repositories dict from the context.

        Returns:
            dict[str, Repository]: Shallow copy of repositories stored in context.
        """
        with self._lock:
            return self.repositories.copy()
