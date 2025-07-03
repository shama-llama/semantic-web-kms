"""Utility to generate a JSON cache of ontology classes and properties from the WDO ontology."""

import json
import os

from app.core.paths import get_web_dev_ontology_path
from app.ontology.wdo import WDOOntology

# Output path for the cache
ONTOLOGY_PATH = get_web_dev_ontology_path()
CACHE_PATH = os.path.join(os.path.dirname(ONTOLOGY_PATH), "ontology_cache.json")


def get_local_name(uri):
    """Extract the local name from a URI (after # or /)."""
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rstrip("/").split("/")[-1]


def main():
    """Generate and write a JSON cache of ontology classes and properties."""
    ontology = WDOOntology(ONTOLOGY_PATH)

    # Classes
    class_uris = ontology.get_all_classes()
    classes = sorted({get_local_name(uri) for uri in class_uris})

    # Object Properties
    from rdflib.namespace import OWL

    object_prop_uris = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.ObjectProperty)
    ]
    object_properties = sorted({get_local_name(uri) for uri in object_prop_uris})

    # Data Properties
    data_prop_uris = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.DatatypeProperty)
    ]
    data_properties = sorted({get_local_name(uri) for uri in data_prop_uris})

    # Annotation Properties
    annotation_prop_uris = [
        str(s)
        for s in ontology.graph.subjects(predicate=None, object=OWL.AnnotationProperty)
    ]
    annotation_properties = sorted(
        {get_local_name(uri) for uri in annotation_prop_uris}
    )

    cache = {
        "classes": classes,
        "object_properties": object_properties,
        "data_properties": data_properties,
        "annotation_properties": annotation_properties,
    }

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"Ontology cache updated: {CACHE_PATH}")


if __name__ == "__main__":
    main()
