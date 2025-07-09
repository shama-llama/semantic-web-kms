"""Ontology wrapper for class/property lookup and superclass traversal."""

import json
import os
from typing import Optional, Set

from rdflib import URIRef

from app.ontology.base import BaseOntology


class CommonOntology(BaseOntology):
    """
    Unified ontology wrapper for class/property lookup and superclass traversal.

    Inherits from BaseOntology to avoid code duplication.
    """

    def __init__(self, ontology_path: str, cache_path: Optional[str] = None):
        """
        Initialize CommonOntology with ontology and optional cache path.

        Args:
            ontology_path: Path to the ontology file.
            cache_path: Optional path to a JSON cache of classes.
        """
        super().__init__(ontology_path)
        self.available_classes: Set[str] = set()
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                cache = json.load(f)
                self.available_classes = set(cache.get("classes", []))

    def get_class(self, class_name: str) -> URIRef:
        """
        Return the URI for a class by name.

        Args:
            class_name: Name of the class to look up.
        Returns:
            URIRef for the class.
        Raises:
            KeyError: If the class is not found in the ontology.
        """
        uri = self.get_class_uri(class_name)
        if uri:
            return uri
        raise KeyError(f"Class '{class_name}' not found in ontology.")

    def get_property(self, prop_name: str) -> URIRef:
        """
        Return the URI for a property by name.

        Args:
            prop_name: Name of the property to look up.
        Returns:
            URIRef for the property.
        Raises:
            KeyError: If the property is not found in the ontology.
        """
        uri = self.get_property_uri(prop_name)
        if uri:
            return uri
        raise KeyError(f"Property '{prop_name}' not found in ontology.")
