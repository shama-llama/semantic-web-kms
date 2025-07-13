"""Path utilities for Semantic Web KMS core modules."""

import os
import re
from typing import Optional

from app.core.config import (
    BASIC_FORMAL_ONTOLOGY_PATH,
    CARRIER_TYPES_PATH,
    CODE_QUERIES_PATH,
    CONTENT_TYPES_PATH,
    EXCLUDED_DIRECTORIES_PATH,
    LANGUAGE_MAPPING_PATH,
    LOG_DIR,
    MAPPINGS_DIR,
    ONTOLOGY_CACHE_FILENAME,
    OUTPUT_DIR,
    WEB_DEV_ONTOLOGY_PATH,
)

_current_input_dir: Optional[str] = None


def set_input_dir(path: str) -> None:
    """
    Set the current input directory for extractors to use.

    Args:
        path (str): The input directory path to set.
    Returns:
        None
    """
    global _current_input_dir
    _current_input_dir = path


def get_input_dir() -> str:
    """
    Get the current input directory. Must be set by set_input_dir() before use.

    Returns:
        str: The input directory to use.

    Raises:
        RuntimeError: If the input directory has not been set.
    """
    if _current_input_dir is None:
        raise RuntimeError(
            "Input directory not set. Call set_input_dir(path) before using get_input_dir()."
        )
    return _current_input_dir


def get_input_path(filename: str) -> str:
    """
    Return the absolute path for a file in the input directory.

    Args:
        filename (str): The name of the file.

    Returns:
        str: The absolute path to the file in the input directory.

    Raises:
        RuntimeError: If the input directory has not been set.
    """
    return os.path.join(get_input_dir(), filename)


def get_output_path(filename: str) -> str:
    """
    Return the absolute path for a file in the output directory.

    Args:
        filename (str): The name of the file.

    Returns:
        str: The absolute path to the file in the output directory.
    """
    return os.path.join(OUTPUT_DIR, filename)


def get_log_path(filename: str) -> str:
    """
    Return the absolute path for a file in the logs directory.

    Args:
        filename (str): The name of the log file.

    Returns:
        str: The absolute path to the log file in the logs directory.
    """
    return os.path.join(LOG_DIR, filename)


def get_language_mapping_path() -> str:
    """
    Return the path to language_mapping.json.

    Returns:
        str: The path to the language mapping JSON file.
    """
    return LANGUAGE_MAPPING_PATH


def get_code_queries_path() -> str:
    """
    Return the path to code_queries.json.

    Returns:
        str: The path to the code queries JSON file.
    """
    return CODE_QUERIES_PATH


def get_carrier_extensions_path() -> str:
    """
    Return the path to file_extensions.json.

    Returns:
        str: The path to the file extensions JSON file.
    """
    return CARRIER_TYPES_PATH


def get_excluded_directories_path() -> str:
    """
    Return the path to excluded_directories.json.

    Returns:
        str: The path to the excluded directories JSON file.
    """
    return EXCLUDED_DIRECTORIES_PATH


def get_content_types_path() -> str:
    """
    Return the path to content_types.json.

    Returns:
        str: The path to the content types JSON file.
    """
    return CONTENT_TYPES_PATH


def get_web_dev_ontology_path() -> str:
    """
    Return the path to wdo.owl.

    Returns:
        str: The path to the web development ontology OWL file.
    """
    return WEB_DEV_ONTOLOGY_PATH


def get_basic_formal_ontology_path() -> str:
    """
    Return the path to bfo.owl.

    Returns:
        str: The path to the basic formal ontology OWL file.
    """
    return BASIC_FORMAL_ONTOLOGY_PATH


def get_carrier_types_path() -> str:
    """
    Return the absolute path to the carrier_types.json file.

    Returns:
        str: The absolute path to the carrier types JSON file.
    """
    return os.path.join(MAPPINGS_DIR, "carrier_types.json")


def get_ontology_cache_path() -> str:
    """
    Return the full path to the ontology cache JSON file.

    Returns:
        str: The full path to the ontology cache JSON file.
    """
    return os.path.join(MAPPINGS_DIR, ONTOLOGY_CACHE_FILENAME)


def uri_safe_string(text: str) -> str:
    """
    Convert a string to URI-safe format by replacing problematic characters with underscores.

    Args:
        text (str): The input string to convert.

    Returns:
        str: The URI-safe version of the input string.
    """
    if not text:
        return ""

    # Replace spaces and other problematic characters with underscores
    # This includes: spaces, tabs, newlines, and other whitespace
    # Also includes: \, :, *, ?, ", <, >, |, and other filesystem-incompatible chars
    # Note: We preserve forward slashes for file paths
    uri_safe = re.sub(r"[^\w\-./]", "_", str(text))

    # Replace multiple consecutive underscores with a single one
    uri_safe = re.sub(r"_+", "_", uri_safe)

    # Remove leading/trailing underscores
    uri_safe = re.sub(r"(^_+|_+$)", "", uri_safe)

    return uri_safe


def uri_safe_file_path(file_path: str) -> str:
    """
    Convert a file path to URI-safe format while preserving directory structure.

    Args:
        file_path (str): The file path to convert.

    Returns:
        str: The URI-safe version of the file path with preserved directory structure.
    """
    if not file_path:
        return ""

    # Split the path into components
    path_components = file_path.split("/")

    # Make each component URI-safe while preserving the structure
    safe_components = []
    for component in path_components:
        if component:
            # Replace problematic characters in each component, but preserve dots
            safe_component = re.sub(r"[^\w\-.]", "_", component)
            # Replace multiple consecutive underscores with a single one
            safe_component = re.sub(r"_+", "_", safe_component)
            # Remove leading/trailing underscores
            safe_component = re.sub(r"(^_+|_+$)", "", safe_component)
            safe_components.append(safe_component)

    # Rejoin with forward slashes
    return "/".join(safe_components)
