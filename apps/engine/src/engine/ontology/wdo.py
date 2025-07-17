"""This module provides the WDOOntology class."""

from app.core.paths import get_web_dev_ontology_path
from app.ontology.base import BaseOntology, register_ontology
from app.ontology.bfo import BFOOntology


class WDOOntology(BaseOntology):
    """
    Web Development Ontology (WDO) handler for semantic annotation.

    Loads the WDO ontology from OWL and provides dynamic class/property lookup and superclass traversal.
    Integrates with BFOOntology for top-level ancestor resolution. If no bfo_ontology is provided, one is instantiated by default.
    """

    def __init__(self, owl_path=None, bfo_ontology=None):
        """
        Initialize the WDO ontology, optionally with a BFO ontology instance.

        Args:
            owl_path (str, optional): Path to the WDO OWL file. If None, uses the default path.
            bfo_ontology (BFOOntology, optional): An instance of BFOOntology. If None, a new instance is created.

        Side Effects:
            Loads the ontology graph and sets up BFO integration.
        """
        if owl_path is None:
            owl_path = get_web_dev_ontology_path()
        if BaseOntology is not None:
            super().__init__(owl_path)
        if bfo_ontology is None:
            bfo_ontology = BFOOntology()
        self.bfo_ontology = bfo_ontology

    def get_class(self, class_name: str):
        """
        Return the URI for a class by name.

        Args:
            class_name (str): The class name to look up.

        Returns:
            URIRef: The URI for the class if found.

        Raises:
            KeyError: If the class is not found in the ontology.
        """
        uri = self.get_class_uri(class_name)
        if uri:
            return uri
        raise KeyError(f"Class '{class_name}' not found in ontology.")

    def get_property(self, prop_name: str):
        """
        Return the URI for a property by name.

        Args:
            prop_name (str): The property name to look up.

        Returns:
            URIRef: The URI for the property if found.

        Raises:
            KeyError: If the property is not found in the ontology.
        """
        uri = self.get_property_uri(prop_name)
        if uri:
            return uri
        raise KeyError(f"Property '{prop_name}' not found in ontology.")

    def get_top_level_bfo_ancestor(self, class_uri):
        """
        Return the top-level BFO ancestor for a given class URI, or None if not found.

        Args:
            class_uri (str or URIRef): The URI of the class to resolve.

        Returns:
            Optional[str]: The URI of the top-level BFO ancestor, or None if not found.
        """
        chain = self.get_superclass_chain(class_uri)
        for ancestor in chain:
            if self.bfo_ontology.is_bfo_class(ancestor):
                return ancestor
        return None


register_ontology("wdo", WDOOntology)
