"""
File classification and ignore pattern utilities for extraction.
"""

import re
from typing import List, Optional, Pattern, Tuple


def is_ignored(filename: str, ignore_patterns: List[Pattern]) -> bool:
    """
    Return True if filename matches any ignore pattern.
    """
    return any(pat.search(filename) for pat in ignore_patterns)


def load_classifiers_from_json(json_path: str) -> Tuple[list, list]:
    """
    Load classifiers and ignore patterns from a JSON file.
    """
    import json

    with open(json_path, "r") as f:
        data = json.load(f)
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
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Classify a filename using regex classifiers and ontology. Returns (class_name, class_uri, confidence).
    """
    if is_ignored(filename, ignore_patterns):
        return None, None, "ignored"
    for class_name, regex in classifiers:
        if regex.search(filename):
            if not ontology_class_cache or class_name in ontology_class_cache:
                try:
                    class_uri = str(ontology.get_class(class_name))
                    return class_name, class_uri, "high"
                except Exception:
                    pass
    if default_class:
        try:
            class_uri = str(ontology.get_class(default_class))
        except Exception:
            class_uri = None
        return default_class, class_uri, "low"
    return None, None, "unknown"
