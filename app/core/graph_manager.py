"""Graph management utilities for RDF graphs and ontologies."""

from typing import Any, Dict

from rdflib import Graph


class GraphManager:
    """Manage an RDF graph using the provided ontology."""

    def __init__(self, ontology: Any) -> None:
        """
        Initialize the GraphManager with an ontology and bind its namespaces.

        Args:
            ontology (Any): The ontology object containing namespaces to bind.
        Raises:
            AttributeError: If the ontology does not have a 'namespaces' attribute.
        """
        self.ontology = ontology
        self.graph = Graph()
        for prefix, ns in ontology.namespaces.items():
            self.graph.bind(prefix, ns)

    def add_triple(self, s: Any, p: Any, o: Any) -> None:
        """
        Add a triple (subject, predicate, object) to the graph.

        Args:
            s (Any): The subject of the triple (must be an rdflib term).
            p (Any): The predicate of the triple (must be an rdflib term).
            o (Any): The object of the triple (must be an rdflib term).
        Returns:
            None
        Raises:
            TypeError: If the triple is not valid for rdflib.Graph.add().
        """
        self.graph.add((s, p, o))

    def serialize(self, path: str, fmt: str = "turtle") -> None:
        """
        Serialize the graph to a file in the specified format.

        Args:
            path (str): The file path to serialize the graph to.
            fmt (str, optional): The serialization format (default: "turtle").
        Returns:
            None
        Raises:
            Exception: If serialization fails or the format is not supported by rdflib.
        """
        self.graph.serialize(destination=path, format=fmt)

    def stats(self) -> Dict[str, int]:
        """
        Return statistics about the graph, including triple, subject, predicate, and object counts.

        Returns:
            Dict[str, int]: A dictionary with counts of total triples, subjects, predicates, and objects.
        """
        return {
            "total_triples": len(self.graph),
            "subjects": len(set(self.graph.subjects())),
            "predicates": len(set(self.graph.predicates())),
            "objects": len(set(self.graph.objects())),
        }
