"""File discovery utilities for supported source files."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from app.core.paths import (
    get_excluded_directories_path,
    get_input_dir,
    get_output_path,
)


def discover_supported_files(
    excluded_dirs: Set[str], language_mapping: Dict[str, str]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Discover files in the input directory with extensions in language_mapping, skipping excluded_dirs.

    Args:
        excluded_dirs: Set of directory names to exclude.
        language_mapping: Dict mapping file extensions to language names.
    Returns:
        Tuple of (list of supported file dicts, list of repository directory names).
    """
    input_dir = Path(get_input_dir())
    supported_files: List[Dict[str, Any]] = []
    repo_dirs = [
        d.name
        for d in input_dir.iterdir()
        if d.is_dir() and d.name not in excluded_dirs
    ]
    for repo in repo_dirs:
        repo_path = input_dir / repo
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirpath_path = Path(dirpath)
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in language_mapping:
                    abs_path = dirpath_path / fname
                    rel_path = abs_path.relative_to(repo_path)
                    supported_files.append(
                        {
                            "repository": repo,
                            "path": str(rel_path),
                            "extension": ext,
                            "abs_path": str(abs_path),
                        }
                    )
    return supported_files, repo_dirs


def load_excluded_dirs() -> Set[str]:
    """
    Load excluded directories from config file.

    Args:
        None
    Returns:
        Set of excluded directory names.
    Raises:
        FileNotFoundError: If the excluded directories config file does not exist.
        json.JSONDecodeError: If the config file is not valid JSON.
    """
    excluded_dirs_path = Path(get_excluded_directories_path())
    with excluded_dirs_path.open("r") as f:
        return set(json.load(f))


def get_input_and_output_paths() -> Tuple[Path, Path]:
    """
    Get input and output directory paths.

    Args:
        None
    Returns:
        Tuple of (input directory Path, output TTL file Path).
    """
    input_dir = Path(get_input_dir())
    ttl_path = Path(get_output_path("web_development_ontology.ttl"))
    return input_dir, ttl_path


def load_and_discover_files(
    language_mapping: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[str], Path, Path]:
    """
    Load excluded dirs, input/output paths, and discover supported files.

    Args:
        language_mapping: Dict mapping file extensions to language names.
    Returns:
        Tuple of (supported files, repo dirs, input dir, output TTL path).
    """
    excluded_dirs = load_excluded_dirs()
    input_dir, ttl_path = get_input_and_output_paths()
    supported_files, repo_dirs = discover_supported_files(
        excluded_dirs, language_mapping
    )
    return supported_files, repo_dirs, input_dir, ttl_path
