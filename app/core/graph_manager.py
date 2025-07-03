from typing import Any, Dict

from rdflib import Graph


class GraphManager:
    """Manage an RDF graph using the provided ontology."""

    def __init__(self, ontology: Any) -> None:
        """Initialize the GraphManager with an ontology and bind its namespaces."""
        self.ontology = ontology
        self.graph = Graph()
        for prefix, ns in ontology.namespaces.items():
            self.graph.bind(prefix, ns)

    def add_triple(self, s: Any, p: Any, o: Any) -> None:
        """Add a triple (subject, predicate, object) to the graph."""
        self.graph.add((s, p, o))

    def serialize(self, path: str, fmt: str = "turtle") -> None:
        """Serialize the graph to a file in the specified format (default: turtle)."""
        self.graph.serialize(destination=path, format=fmt)

    def stats(self) -> Dict[str, int]:
        """Return statistics about the graph: total triples, subjects, predicates, and objects."""
        return {
            "total_triples": len(self.graph),
            "subjects": len(set(self.graph.subjects())),
            "predicates": len(set(self.graph.predicates())),
            "objects": len(set(self.graph.objects())),
        }
