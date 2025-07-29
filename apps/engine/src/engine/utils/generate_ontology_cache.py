"""Utility to generate a JSON cache of classes and properties from the WDO ontology."""

import json
import re
from typing import Any

from engine.core.paths import PathManager
from engine.ontology.wdo import WDOOntology

ONTOLOGY_PATH: str = str(PathManager.get_web_dev_ontology_path())
CACHE_PATH = PathManager.get_web_dev_ontology_path().parent / "ontology_cache.json"


def get_local_name(uri: str) -> str:
    """
    Extract the local name from a URI (after # or /).

    Args:
        uri (str): The URI string.

    Returns:
        str: The local name as a string.

    Raises:
        None.

    Example:
        >>> get_local_name('http://example.org#ClassName')
        'ClassName'
    """
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rstrip("/").split("/")[-1]


def is_valid_class_name(name: str) -> bool:
    """
    Check if a class name is valid (not a hash-like name).

    Args:
        name (str): The class name string.

    Returns:
        bool: True if the name is valid, False otherwise.

    Raises:
        None.

    Example:
        >>> is_valid_class_name('Nabcdef0123456789abcdef0123456789')
        False
        >>> is_valid_class_name('Person')
        True
    """
    # Filter out hash-like names (32+ character hex strings)
    return not re.match(r"^N[a-f0-9]{32}$", name)


def main() -> None:
    """
    Generate and write a JSON cache of ontology classes and properties.

    This function loads the WDO ontology, extracts all class and property names
    (object, data, annotation), filters out hash-like class names, and writes the
    results to a JSON cache file.

    Args:
        None.

    Returns:
        None.

    Raises:
        IOError: If writing the cache file fails.
        OSError: If writing the cache file fails.
        Exception: If ontology loading or processing fails.

    Side Effects:
        Writes a JSON file to CACHE_PATH and prints a status message.
    """
    ontology: WDOOntology = WDOOntology(ONTOLOGY_PATH)

    # Classes - filter out hash-like names
    class_uris: list[str] = ontology.get_all_classes()
    classes: list[str] = sorted({
        get_local_name(uri)
        for uri in class_uris
        if is_valid_class_name(get_local_name(uri))
    })

    # Object Properties
    from rdflib.namespace import OWL

    object_prop_uris: list[str] = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.ObjectProperty)
    ]
    object_properties: list[str] = sorted({
        get_local_name(uri) for uri in object_prop_uris
    })

    # Data Properties
    data_prop_uris: list[str] = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.DatatypeProperty)
    ]
    data_properties: list[str] = sorted({get_local_name(uri) for uri in data_prop_uris})

    # Annotation Properties
    annotation_prop_uris: list[str] = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.AnnotationProperty)
    ]
    annotation_properties: list[str] = sorted({
        get_local_name(uri) for uri in annotation_prop_uris
    })

    cache: dict[str, Any] = {
        "classes": classes,
        "object_properties": object_properties,
        "data_properties": data_properties,
        "annotation_properties": annotation_properties,
    }

    try:
        with CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        print(f"Ontology cache updated: {CACHE_PATH}")
    except OSError as e:
        print(f"Failed to write ontology cache: {e}")
        raise


if __name__ == "__main__":
    main()
