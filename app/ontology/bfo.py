import os

from rdflib import OWL, RDF, RDFS, Graph, Namespace, URIRef

from app.core.paths import get_basic_formal_ontology_path


class BFOOntology:
    """Wrapper for the Basic Formal Ontology (BFO) using rdflib."""

    BFO_NAMESPACE = "http://purl.obolibrary.org/obo/"
    BFO_OWL_PATH = get_basic_formal_ontology_path()
    ENTITY_URI = URIRef(f"{BFO_NAMESPACE}BFO_0000001")

    def __init__(self, owl_path=None):
        """Initialize the BFO ontology, parsing the OWL file."""
        self.ontology_path = owl_path or os.path.abspath(self.BFO_OWL_PATH)
        self.graph = Graph()
        self.graph.parse(self.ontology_path)
        self.namespace = Namespace(self.BFO_NAMESPACE)

    def is_bfo_class(self, uri):
        """Return True if the URI is a BFO class (top-level or otherwise)."""
        return str(uri).startswith(self.BFO_NAMESPACE)

    def get_label(self, uri):
        """Return the rdfs:label for a BFO class URI, if present."""
        label = self.graph.value(URIRef(uri), RDFS.label)
        return str(label) if label else None

    def get_top_level_classes(self):
        """Return all direct subclasses of 'entity' (BFO_0000001) as (uri, label) tuples."""
        top_level = []
        for s in self.graph.subjects(RDFS.subClassOf, self.ENTITY_URI):
            if (s, RDF.type, OWL.Class) in self.graph:
                label = self.get_label(s)
                top_level.append((str(s), label))
        return top_level
