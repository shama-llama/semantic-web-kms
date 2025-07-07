"""
Ontology wrapper for class/property lookup and superclass traversal.
"""

import json
import os
from typing import List, Optional, Set

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS


class CommonOntology:
    """
    Unified ontology wrapper for class/property lookup and superclass traversal.
    """

    def __init__(self, ontology_path: str, cache_path: Optional[str] = None):
        self.graph = Graph()
        if ontology_path is None:
            raise ValueError("ontology_path must not be None")
        self.graph.parse(ontology_path, format="xml")
        self.available_classes: Set[str] = set()
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                cache = json.load(f)
                self.available_classes = set(cache.get("classes", []))

    def get_class(self, class_name: str) -> URIRef:
        """
        Return the URI for a class by name, or raise KeyError if not found.
        """
        uri = self._find_class_by_name(class_name)
        if uri:
            return uri
        raise KeyError(f"Class '{class_name}' not found in ontology.")

    def get_property(self, prop_name: str) -> URIRef:
        """
        Return the URI for a property by name, or raise KeyError if not found.
        """
        uri = self._find_property_by_name(prop_name)
        if uri:
            return uri
        raise KeyError(f"Property '{prop_name}' not found in ontology.")

    def get_superclass_chain(self, class_uri: Optional[str]) -> List[str]:
        """
        Return the full superclass chain for a class URI, up to the root.
        """
        if not class_uri:
            return []
        chain = []
        current = URIRef(class_uri)
        visited = set()
        while True:
            superclass = self.graph.value(current, RDFS.subClassOf)
            if superclass and superclass not in visited:
                chain.append(str(superclass))
                visited.add(URIRef(str(superclass)))
                current = URIRef(str(superclass))
            else:
                break
        return chain

    def _find_class_by_name(self, class_name: str) -> Optional[URIRef]:
        for s in self.graph.subjects(RDF.type, OWL.Class):
            label = self.graph.value(s, RDFS.label)
            if label and str(label).lower() == class_name.lower():
                return URIRef(str(s))
            if (
                str(s).split("#")[-1] == class_name
                or str(s).split("/")[-1] == class_name
            ):
                return URIRef(str(s))
        return None

    def _find_property_by_name(self, prop_name: str) -> Optional[URIRef]:
        for s in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            label = self.graph.value(s, RDFS.label)
            if label and str(label).lower() == prop_name.lower():
                return URIRef(str(s))
            if str(s).split("#")[-1] == prop_name or str(s).split("/")[-1] == prop_name:
                return URIRef(str(s))
        for s in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            label = self.graph.value(s, RDFS.label)
            if label and str(label).lower() == prop_name.lower():
                return URIRef(str(s))
            if str(s).split("#")[-1] == prop_name or str(s).split("/")[-1] == prop_name:
                return URIRef(str(s))
        return None
