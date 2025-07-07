import json
import os
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from app.core.paths import (
    get_excluded_directories_path,
    get_input_path,
    get_output_path,
)


def discover_supported_files(
    INPUT_DIR: Path, excluded_dirs: Set[str], language_mapping: Dict[str, str]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Discover files in INPUT_DIR with extensions in language_mapping, skipping excluded_dirs."""
    supported_files: List[Dict[str, Any]] = []
    repo_dirs = [
        d.name
        for d in INPUT_DIR.iterdir()
        if d.is_dir() and d.name not in excluded_dirs
    ]
    for repo in repo_dirs:
        repo_path = INPUT_DIR / repo
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirpath = Path(dirpath)
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in language_mapping:
                    abs_path = dirpath / fname
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
    """Load excluded directories from config file."""
    excluded_dirs_path = Path(get_excluded_directories_path())
    with excluded_dirs_path.open("r") as f:
        return set(json.load(f))


def get_input_and_output_paths() -> Tuple[Path, Path]:
    """Get input and output directory paths."""
    INPUT_DIR = Path(get_input_path(""))
    TTL_PATH = Path(get_output_path("web_development_ontology.ttl"))
    return INPUT_DIR, TTL_PATH


def load_and_discover_files(
    language_mapping: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[str], Path, Path]:
    """Load excluded dirs, input/output paths, and discover supported files."""
    excluded_dirs = load_excluded_dirs()
    INPUT_DIR, TTL_PATH = get_input_and_output_paths()
    supported_files, repo_dirs = discover_supported_files(
        INPUT_DIR, excluded_dirs, language_mapping
    )
    return supported_files, repo_dirs, INPUT_DIR, TTL_PATH
