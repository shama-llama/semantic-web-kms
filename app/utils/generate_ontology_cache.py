"""Utility to generate a JSON cache of ontology classes and properties from the WDO ontology."""

import json
import re
from typing import Any, Dict, List

from app.core.paths import get_ontology_cache_path, get_web_dev_ontology_path
from app.ontology.wdo import WDOOntology

# Output path for the cache
ONTOLOGY_PATH: str = get_web_dev_ontology_path()
CACHE_PATH: str = get_ontology_cache_path()


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
    if re.match(r"^N[a-f0-9]{32}$", name):
        return False
    return True


def main() -> None:
    """
    Generate and write a JSON cache of ontology classes and properties.

    This function loads the WDO ontology, extracts all class and property names (object, data, annotation),
    filters out hash-like class names, and writes the results to a JSON cache file.

    Args:
        None.

    Returns:
        None.

    Raises:
        IOError: If writing the cache file fails.
        Exception: If ontology loading or processing fails.

    Side Effects:
        Writes a JSON file to CACHE_PATH and prints a status message.
    """
    ontology: WDOOntology = WDOOntology(ONTOLOGY_PATH)

    # Classes - filter out hash-like names
    class_uris: List[str] = ontology.get_all_classes()
    classes: List[str] = sorted(
        {
            get_local_name(uri)
            for uri in class_uris
            if is_valid_class_name(get_local_name(uri))
        }
    )

    # Object Properties
    from rdflib.namespace import OWL

    object_prop_uris: List[str] = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.ObjectProperty)
    ]
    object_properties: List[str] = sorted(
        {get_local_name(uri) for uri in object_prop_uris}
    )

    # Data Properties
    data_prop_uris: List[str] = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.DatatypeProperty)
    ]
    data_properties: List[str] = sorted({get_local_name(uri) for uri in data_prop_uris})

    # Annotation Properties
    annotation_prop_uris: List[str] = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.AnnotationProperty)
    ]
    annotation_properties: List[str] = sorted(
        {get_local_name(uri) for uri in annotation_prop_uris}
    )

    cache: Dict[str, Any] = {
        "classes": classes,
        "object_properties": object_properties,
        "data_properties": data_properties,
        "annotation_properties": annotation_properties,
    }

    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"Ontology cache updated: {CACHE_PATH}")
    except IOError as e:
        print(f"Failed to write ontology cache: {e}")
        raise


if __name__ == "__main__":
    main()
