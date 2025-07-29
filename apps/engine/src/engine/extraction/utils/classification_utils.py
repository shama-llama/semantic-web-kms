"""File classification and ignore pattern utilities for extraction."""

import json
import re
from pathlib import Path
from re import Pattern


def is_ignored(filename: str, ignore_patterns: list[Pattern]) -> bool:
    """
    Check if the filename matches any ignore pattern.

    Args:
        filename (str): The name or path of the file to check.
        ignore_patterns (List[Pattern]): List of compiled regex patterns to
            match against.

    Returns:
        bool: True if the filename matches any ignore pattern, False otherwise.
    """
    return any(pat.search(filename) for pat in ignore_patterns)


def load_classifiers_from_json(json_path: str) -> tuple[list, list]:
    """
    Load file classifiers and ignore patterns from a JSON file.

    Args:
        json_path (str): Path to the JSON file with classifiers and ignore
            patterns.

    Returns:
        Tuple[list, list]:
            - List of (class_name, compiled regex) pairs for classification.
            - List of compiled regex patterns for files to ignore.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the JSON file is malformed.
    """
    with Path(json_path).open() as f:
        data = json.load(f)
    classifiers = [(c["class"], re.compile(c["regex"])) for c in data["classifiers"]]
    ignore_patterns = [re.compile(p) for p in data.get("ignore_patterns", [])]
    return classifiers, ignore_patterns


def load_classifiers_from_dict(data: dict) -> tuple[list, list]:
    """
    Load file classifiers and ignore patterns from a dict (already loaded JSON).

    Args:
        data (dict): The loaded JSON content with classifiers and ignore patterns.

    Returns:
        Tuple[list, list]:
            - List of (class_name, compiled regex) pairs for classification.
            - List of compiled regex patterns for files to ignore.
    """
    classifiers = [(c["class"], re.compile(c["regex"])) for c in data["classifiers"]]
    ignore_patterns = [re.compile(p) for p in data.get("ignore_patterns", [])]
    return classifiers, ignore_patterns


def classify_file(
    filename: str,
    classifiers: list,
    ignore_patterns: list,
    ontology,
    ontology_class_cache: set = set(),
    default_class: str = "",
) -> tuple:
    """
    Classify a file based on its filename using regex patterns.

    Args:
        filename: Name of the file to classify.
        classifiers: List of (class_name, regex) tuples for classification.
        ignore_patterns: List of compiled regex patterns for files to ignore.
        ontology: Ontology object for class URI lookup.
        ontology_class_cache: Set of valid class names in ontology.
        default_class: Default class to assign if no match found.

    Returns:
        Tuple of (class_name, class_uri, confidence) or (None, None, "ignored").
    """
    if is_ignored(filename, ignore_patterns):
        return None, None, "ignored"
    for class_name, regex in classifiers:
        if regex.search(filename) and (
            not ontology_class_cache or class_name in ontology_class_cache
        ):
            try:
                class_uri = ontology.get_class(class_name)
                return class_name, class_uri, "high"
            except Exception as e:
                # Log the error but continue processing
                print(f"Warning: Could not get class URI for {class_name}: {e}")
    if default_class:
        try:
            class_uri = ontology.get_class(default_class)
        except Exception:
            class_uri = None
        return default_class, class_uri, "low"
    return None, None, "unknown"
