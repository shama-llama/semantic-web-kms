"""
File and repository utility functions and data models for extraction.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def get_repo_dirs(input_dir: str, excluded_dirs: Set[str]) -> List[str]:
    """
    List repository directories, excluding those in excluded_dirs.
    """
    return [
        d
        for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d)) and d not in excluded_dirs
    ]


def count_total_files(
    repo_dirs: List[str], input_dir: str, excluded_dirs: Set[str]
) -> int:
    """
    Count the total number of files in all repositories, excluding files in excluded directories.
    """
    total = 0
    for repo in repo_dirs:
        repo_path = os.path.join(input_dir, repo)
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            total += len(filenames)
    return total


def get_repo_file_map(input_dir: str, excluded_dirs: Set[str]) -> Dict[str, List[Any]]:
    """
    Map each repo to its files as (rel_path, abs_path, fname) tuples.
    """
    repo_dirs = get_repo_dirs(input_dir, excluded_dirs)
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
    input_dir: str,
    excluded_dirs: Set[str],
    progress,
    extract_task,
) -> List[FileRecord]:
    """
    Build a list of file records for all files in the repositories, excluding specified directories.
    """
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
                progress.advance(extract_task)
    return file_records


def create_file_record(
    file_id: int,
    repo: str,
    rel_path: str,
    abs_path: str,
    fname: str,
    file_classifiers: list,
    file_ignore_patterns: list,
    ontology,
    ontology_class_cache: set,
    default_class: str = "DigitalInformationCarrier",
) -> dict:
    """
    Build a record for a file, including categorization and metadata.
    """
    import os
    from datetime import datetime
    from pathlib import Path

    from .classification_utils import classify_file

    file_class, file_class_uri, confidence = classify_file(
        fname,
        file_classifiers,
        file_ignore_patterns,
        ontology,
        ontology_class_cache,
        default_class=default_class,
    )
    stat = os.stat(abs_path)
    creation_time = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%dT%H:%M:%S")
    modification_time = datetime.fromtimestamp(stat.st_mtime).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    return {
        "id": file_id,
        "repository": repo,
        "path": rel_path,
        "filename": fname,
        "ontology_class": file_class,
        "class_uri": file_class_uri,
        "description": f"A file of type {file_class}",
        "confidence": confidence,
        "extension": Path(fname).suffix,
        "size_bytes": os.path.getsize(abs_path),
        "abs_path": abs_path,
        "creation_timestamp": creation_time,
        "modification_timestamp": modification_time,
    }


def read_code_bytes(abs_path: str) -> Optional[bytes]:
    """
    Read a file as bytes, returning None if the file cannot be read.
    Args:
        abs_path: Absolute path to the file.
    Returns:
        File contents as bytes, or None if reading fails.
    """
    try:
        with open(abs_path, "rb") as f:
            return f.read()
    except Exception:
        return None
