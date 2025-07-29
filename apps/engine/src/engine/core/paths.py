"""Path utilities for Semantic Web KMS."""

import json
import re
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from engine import config as config_pkg
from engine.core.config import settings as app_settings

# --- Constants for internal project structure ---

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
ONTOLOGY_DIR = DATA_DIR / "ontologies"

# --- Constants derived from external configuration ---

OUTPUT_DIR = PROJECT_ROOT / app_settings.OUTPUT_DIR_BASE
LOGS_DIR = OUTPUT_DIR / "logs"

# Pre-compiled regular expressions for performance

_URI_UNSAFE_CHARS_PATTERN = re.compile(r"[^\w\-./]")
_URI_MULTIPLE_UNDERSCORES_PATTERN = re.compile(r"_+")
_URI_LEADING_TRAILING_UNDERSCORES_PATTERN = re.compile(r"(^_+|_+$)")

_PATH_UNSAFE_CHARS_PATTERN = re.compile(r"[^\w\-.]")


# --- Configuration Loading ---


@cache
def _load_config_json(filename: str) -> dict[str, Any]:
    """
    Load a JSON configuration file from the package data.

    This is a private helper function to avoid repeating file-loading logic.
    Using @lru_cache to cache results in memory, avoiding repeated file I/O.

    Args:
        filename: The name of the JSON file in the `engine.config` package.

    Returns:
        The content of the JSON file as a dictionary.

    Raises:
        FileNotFoundError: If the config file is missing.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = resources.files(config_pkg) / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_carrier_types() -> dict[str, Any]:
    """
    Load carrier types from the config JSON file.

    Returns:
        A dictionary containing carrier types loaded from the config file.
    """
    return _load_config_json("carrier_types.json")


def get_content_types() -> dict[str, Any]:
    """
    Load content types from the config JSON file.

    Returns:
        A dictionary containing content types loaded from the config file.
    """
    return _load_config_json("content_types.json")


def get_language_mapping() -> dict[str, Any]:
    """
    Load language mapping from the config JSON file.

    Returns:
        A dictionary containing language mappings loaded from the config file.
    """
    return _load_config_json("language_mapping.json")


def get_code_queries() -> dict[str, Any]:
    """
    Load code queries from the config JSON file.

    Returns:
        A dictionary containing code queries loaded from the config file.
    """
    return _load_config_json("code_queries.json")


def get_excluded_directories() -> dict[str, Any]:
    """
    Load excluded directories from the config JSON file.

    Returns:
        A dictionary containing excluded directories loaded from the config file.
    """
    return _load_config_json("excluded_directories.json")


def get_ontology_cache() -> dict[str, Any]:
    """
    Load the ontology cache from the config JSON file.

    Returns:
        A dictionary containing the ontology cache loaded from the config file.
    """
    return _load_config_json("ontology_cache.json")


# --- Path Management ---


class PathManager:
    """
    Manages input and output paths for a processing session.

    This class avoids the use of global state for the input directory, making
    the code more predictable, testable, and maintainable. An instance of this
    class can be passed through your application's context.
    """

    def __init__(self, input_dir: str | Path):
        """
        Initialize PathManager with the given input directory.

        Args:
            input_dir: The input directory as a string or Path.

        Raises:
            FileNotFoundError: If the input directory does not exist.
        """
        self.input_dir = Path(input_dir).resolve()
        if not self.input_dir.is_dir():
            raise FileNotFoundError(f"Input directory does not exist: {self.input_dir}")

    def get_input_path(self, filename: str | Path) -> Path:
        """Return the absolute path for a file in the input directory."""
        return self.input_dir / filename

    @staticmethod
    def get_output_path(filename: str | Path) -> Path:
        """Return the absolute path for a file in the output directory."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return OUTPUT_DIR / filename

    @staticmethod
    def get_log_path(filename: str | Path) -> Path:
        """Return the absolute path for a file in the logs directory."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return LOGS_DIR / filename

    @staticmethod
    def get_web_dev_ontology_path() -> Path:
        """Return the path to wdo.owl."""
        return ONTOLOGY_DIR / "wdo.owl"

    @staticmethod
    def get_basic_formal_ontology_path() -> Path:
        """Return the path to bfo.owl."""
        return ONTOLOGY_DIR / "bfo.owl"


# --- String and Path Sanitization ---


def uri_safe_string(text: str) -> str:
    """
    Convert a string to a URI-safe format.

    Replaces spaces and most non-alphanumeric characters with underscores.
    Forward slashes and periods are preserved for file paths.

    Args:
        text: The input string to convert.

    Returns:
        The URI-safe version of the input string.
    """
    if not text:
        return ""

    uri_safe = _URI_UNSAFE_CHARS_PATTERN.sub("_", text)
    uri_safe = _URI_MULTIPLE_UNDERSCORES_PATTERN.sub("_", uri_safe)
    uri_safe = _URI_LEADING_TRAILING_UNDERSCORES_PATTERN.sub("", uri_safe)
    return uri_safe


def uri_safe_file_path(file_path: str | Path) -> str:
    """
    Convert a file path into a URI-safe string.

    This function sanitizes each component of the path individually while
    preserving the directory separators.

    Args:
        file_path: The file path to convert.

    Returns:
        The URI-safe version of the file path.
    """
    if not file_path:
        return ""

    path = Path(file_path)
    safe_parts = []
    for component in path.parts:
        safe_component = _PATH_UNSAFE_CHARS_PATTERN.sub("_", component)
        safe_component = _URI_MULTIPLE_UNDERSCORES_PATTERN.sub("_", safe_component)
        safe_component = _URI_LEADING_TRAILING_UNDERSCORES_PATTERN.sub(
            "", safe_component
        )
        safe_parts.append(safe_component)

    return "/".join(safe_parts)
