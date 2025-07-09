"""File and repository utility functions and data models for extraction."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.core.paths import get_input_dir


def get_repo_dirs(excluded_dirs: Set[str]) -> List[str]:
    """
    List repository directories, excluding those in excluded_dirs.

    Args:
        excluded_dirs: Set of directory names to exclude.
    Returns:
        List of repository directory names.
    """
    input_dir = get_input_dir()
    return [
        d
        for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d)) and d not in excluded_dirs
    ]


def count_total_files(repo_dirs: List[str], excluded_dirs: Set[str]) -> int:
    """
    Count the total number of files in all repositories, excluding files in excluded directories.

    Args:
        repo_dirs: List of repository directory names.
        excluded_dirs: Set of directory names to exclude.
    Returns:
        Total number of files as an integer.
    """
    input_dir = get_input_dir()
    total = 0
    for repo in repo_dirs:
        repo_path = os.path.join(input_dir, repo)
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            total += len(filenames)
    return total


def get_repo_file_map(excluded_dirs: Set[str]) -> Dict[str, List[Any]]:
    """
    Map each repo to its files as (rel_path, abs_path, fname) tuples.

    Args:
        excluded_dirs: Set of directory names to exclude.
    Returns:
        Dict mapping repo name to list of (rel_path, abs_path, fname) tuples.
    """
    input_dir = get_input_dir()
    repo_dirs = get_repo_dirs(excluded_dirs)
    repo_file_map: Dict[str, List[Any]] = {}
    for repo in repo_dirs:
        repo_path = os.path.join(input_dir, repo)
        repo_file_map[repo] = []
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            for fname in filenames:
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, repo_path)
                repo_file_map[repo].append((rel_path, abs_path, fname))
    return repo_file_map


@dataclass
class FileRecord:
    """
    File metadata for extraction and RDF generation.

    Attributes:
        id: Unique file identifier.
        repository: Repository name.
        path: Relative file path within the repository.
        filename: File name.
        extension: File extension.
        size_bytes: File size in bytes.
        abs_path: Absolute file path.
        ontology_class: Ontology class (optional).
        class_uri: Ontology class URI (optional).
        creation_timestamp: File creation timestamp (optional).
        modification_timestamp: File modification timestamp (optional).
    """

    id: int
    repository: str
    path: str
    filename: str
    extension: str
    size_bytes: int
    abs_path: str
    ontology_class: str = ""
    class_uri: str = ""
    creation_timestamp: Optional[str] = None
    modification_timestamp: Optional[str] = None


def build_file_records(
    repo_dirs: List[str],
    excluded_dirs: Set[str],
    progress,
    extract_task,
) -> List[FileRecord]:
    """
    Build a list of file records for all files in the repositories, excluding specified directories.

    Args:
        repo_dirs: List of repository directory names.
        excluded_dirs: Set of directory names to exclude.
        progress: Progress bar object for tracking.
        extract_task: Task ID for progress bar.
    Returns:
        List of FileRecord objects.
    """
    input_dir = get_input_dir()
    file_records: List[FileRecord] = []
    file_id = 1
    for repo in repo_dirs:
        repo_path = os.path.join(input_dir, repo)
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            for fname in filenames:
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, repo_path)
                ext = Path(fname).suffix
                file_records.append(
                    FileRecord(
                        id=file_id,
                        repository=repo,
                        path=rel_path,
                        filename=fname,
                        extension=ext,
                        size_bytes=os.path.getsize(abs_path),
                        abs_path=abs_path,
                    )
                )
                file_id += 1
                if progress is not None and extract_task is not None:
                    progress.advance(extract_task)
    return file_records


def make_file_record(
    file_id: int,
    repo: str,
    rel_path: str,
    abs_path: str,
    fname: str,
    size_bytes: int,
    extension: Optional[str] = None,
    ontology_class: str = "",
    class_uri: str = "",
    creation_timestamp: str = "",
    modification_timestamp: str = "",
) -> dict:
    """
    Create a dictionary representing a file record with metadata.

    Args:
        file_id: Unique file identifier.
        repo: Repository name.
        rel_path: Relative file path within the repository.
        abs_path: Absolute file path.
        fname: File name.
        size_bytes: File size in bytes.
        extension: File extension (optional).
        ontology_class: Ontology class (optional).
        class_uri: Ontology class URI (optional).
        creation_timestamp: File creation timestamp (optional).
        modification_timestamp: File modification timestamp (optional).
    Returns:
        dict: File record with all metadata fields.
    """
    from pathlib import Path

    return {
        "id": file_id,
        "repository": repo,
        "path": rel_path,
        "filename": fname,
        "extension": extension if extension is not None else Path(fname).suffix,
        "size_bytes": size_bytes,
        "abs_path": abs_path,
        "ontology_class": ontology_class,
        "class_uri": class_uri,
        "creation_timestamp": creation_timestamp or "",
        "modification_timestamp": modification_timestamp or "",
    }


def read_code_bytes(abs_path: str) -> Optional[bytes]:
    """
    Read a file as bytes, returning None if the file cannot be read.

    Args:
        abs_path: Absolute path to the file.
    Returns:
        File contents as bytes, or None if reading fails.
    Raises:
        OSError: If the file cannot be opened (caught and suppressed).
    """
    try:
        with open(abs_path, "rb") as f:
            return f.read()
    except Exception:
        return None
